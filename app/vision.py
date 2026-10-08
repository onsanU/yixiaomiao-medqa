# -*- coding: utf-8 -*-
"""
🐱 医小喵 · AI 看图解读（视觉 + OCR 双保险，2026-09-02）

图片进来自动分流：
  - OCR 提取到足够文字（≥30 字，报告/化验单/说明书类）
    → OCR 文字通道：文字交给主脑 qwen3.5:4b 解读（文字推理不错位，最准）
  - OCR 文字太少（症状照片/无字图）
    → 视觉通道：qwen2.5vl:3b 看图（100% GPU，~10s，keep_alive=0 用完即卸）

依赖：medqa-venv 装 rapidocr-onnxruntime（CPU，模型 ~15MB）+ Ollama
（qwen2.5vl:3b 视觉 + qwen3.5:4b 主脑，均已在）
"""
import base64
import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434"
VISION_MODEL = "qwen2.5vl:3b"
TEXT_MODEL = "qwen3.5:4b-med3"   # 主脑（与 RAG 同款，解读 OCR 文字）2026-09-09升级5000条微调版(3000档备份 .bak-qwen35med3)
MAX_IMAGE_BYTES = 6 * 1024 * 1024
OCR_MIN_TEXT = 30           # OCR 文字 ≥30 字 → 走文字通道

# ── OCR 懒加载单例（首次调用才 import + 初始化，~4-8s）──
_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def ocr_extract_text(image_bytes: bytes) -> str:
    """RapidOCR 提取图片文字，按检测顺序拼成多行文本；失败返回空串"""
    try:
        result, _ = _get_ocr()(image_bytes)
        if not result:
            return ""
        return "\n".join(t[1] for t in result)
    except Exception:
        return ""


# ── 文字通道：OCR 文字 + 主脑解读 ──
TEXT_SYSTEM = """你是"医小喵"。用户上传了图片，以下是程序从图片中识别（OCR）出的文字内容，可能有个别错字、表格排版被打乱或顺序颠倒。

请你根据这些文字解读：如果是检查报告/化验单，先指出【项目 → 结果 → 参考范围】里超出范围的异常项，再解读含义。

要求：
1. 结合上下文纠正 OCR 错字（如"维果"可能是"结果"、"×位/儿"可能是"×10^9/L"）
2. 正常指标不必逐行罗列，一两句带过即可；重点说清异常项和可能提示
3. 回答保持简洁（300 字以内），不要输出超长的 markdown 表格
4. **OCR 文字中没出现的关键数值，绝对禁止猜测或推断**（禁止"推断约为""可能是xx""结合逻辑推测"这类编造），一律如实写"OCR 未能识别该项目的数值，请核对原始报告"
5. 解读仅供参考，不能作为诊断依据；发现明显异常或涉及严重症状，提醒用户及时就医、咨询医生
6. 文字太少、缺关键信息或无法判断时，如实说明"图片文字不完整/看不清"，绝不编造数值或结论"""


def chat_ollama(messages, model, keep_alive=None, think=None):
    """通用调 Ollama chat（返回回答文本或错误提示）"""
    payload = {"model": model, "messages": messages,
               "stream": False, "options": {"temperature": 0.1,
                                             "num_predict": 1200}}  # 上限防超长截断
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    if think is not None:
        payload["think"] = think  # qwen3 系思考模式开关（false=直接答，快且稳）
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return f"⚠️ 模型调用失败（HTTP {e.code}），请确认 Ollama 已启动、模型就绪喵~"
    except Exception as e:
        return f"⚠️ 模型调用出错：{e}"
    if "error" in data:
        return f"⚠️ 模型返回错误：{data['error']}"
    return (data.get("message", {}).get("content", "") or "").strip() or "（模型没有返回内容喵~）"


def _text_interpret(ocr_text: str, question: str) -> str:
    """OCR 文字通道：主脑 qwen3.5:4b 解读文字（think=False 关思考直接答，快且稳）"""
    q = question.strip() or "请解读这张图片里的内容"
    user_content = f"图片 OCR 识别出的文字内容如下：\n{ocr_text}\n\n用户问题：{q}\n请解读。"
    return chat_ollama(
        [{"role": "system", "content": TEXT_SYSTEM},
         {"role": "user", "content": user_content}],
        TEXT_MODEL,
        think=False,  # 关键：qwen3.5 默认爱思考，OCR 任务会想几千字烧光预算导致 content 空
    )


# ── 视觉通道：qwen2.5vl 看图 ──
VISION_SYSTEM = """你是"医小喵"的AI看图助手。用户会发来图片（可能是检查报告、化验单、症状照片、药品照片等），请你用中文解读。

要求：
1. 先客观描述图片里看到了什么（报告类型、关键指标或文字），再解读含义
2. 如果图片是表格类报告（血常规、化验单等），请逐行逐列认真辨认，先完整列出【项目、结果、参考范围】再判断，不要漏行、不要错位
3. 解读仅供参考，不能作为诊断依据；如发现明显异常或涉及严重症状，请提醒用户及时就医、咨询医生
4. 图片模糊、看不清或不确定的地方，必须如实说明"看不清/不确定"，绝不编造数值或结论
5. 如果图片与医疗无关，正常描述图片内容即可"""


def _vl_interpret(image_b64: str, question: str) -> str:
    """视觉通道：qwen2.5vl 看图（keep_alive=0 用完即卸，别占内存）"""
    q = question.strip() or "请解读这张图片里的内容"
    return chat_ollama(
        [{"role": "system", "content": VISION_SYSTEM},
         {"role": "user", "content": q, "images": [image_b64]}],
        VISION_MODEL,
        keep_alive=0,
    )


# ── 指标提取：OCR 文字 → 结构化 JSON（供前端画图）──
METRICS_SYSTEM = """你是数据提取器。从用户提供的 OCR 文字中提取化验/检查指标，只输出 JSON 数组，格式：
[{"name":"项目名(含缩写)","value":数值,"unit":"单位","ref_low":下限,"ref_high":上限}]

规则：
1. 只提取 OCR 文字中【结果数值】和【参考范围】都完整的项目；数值缺失的项目不要输出（禁止猜测编造）
2. value/ref_low/ref_high 必须是数字；无法解析为数字的项目剔除，不要输出
3. 参考范围如"3.5 - 9.5" → ref_low=3.5, ref_high=9.5；单向范围（如"0 - 8"）照常提取
4. 内容不是检验报告/没有可提取指标时，输出 []（空数组）
5. 只输出 JSON 数组本身，不要任何解释、前后缀或 markdown 代码块标记"""


def extract_metrics(ocr_text: str) -> list:
    """从 OCR 文字提取结构化指标列表；解析失败返回 []（前端不画图，安全降级）"""
    import json
    import re
    resp = chat_ollama(
        [{"role": "system", "content": METRICS_SYSTEM},
         {"role": "user", "content": f"OCR 文字：\n{ocr_text}"}],
        TEXT_MODEL, think=False,
    )
    if not resp or resp.startswith("⚠️"):
        return []
    m = re.search(r"\[[\s\S]*\]", resp)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for it in data:
        if not isinstance(it, dict):
            continue
        val = _to_float(it.get("value"))
        if val is None:
            continue
        out.append({"name": str(it.get("name", ""))[:30], "value": val,
                    "unit": str(it.get("unit", "")),
                    "ref_low": _to_float(it.get("ref_low")),
                    "ref_high": _to_float(it.get("ref_high"))})
    return out


def _to_float(x):
    """宽松转 float：None/空/无法解析 → None"""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ── 入口：自动分流 ──
def analyze_image(image_b64: str, question: str = "") -> dict:
    """解读图片 → {"answer": str, "mode": "ocr"|"vision", "metrics": [...]}"""
    try:
        raw = base64.b64decode(image_b64)
    except Exception:
        return {"answer": "⚠️ 图片数据格式不正确喵，请重新上传试试~", "mode": "vision", "metrics": []}
    if len(raw) > MAX_IMAGE_BYTES:
        return {"answer": "⚠️ 图片太大啦喵（超过 6MB），请换一张小一点的图片~", "mode": "vision", "metrics": []}

    # 先 OCR 扫一遍：文字够多 → 文字通道（报告类最准）
    ocr_text = ocr_extract_text(raw)
    if len(ocr_text.strip()) >= OCR_MIN_TEXT:
        return {"answer": _text_interpret(ocr_text, question),
                "mode": "ocr", "metrics": extract_metrics(ocr_text)}

    # 文字太少/无 → 视觉模型看图兜底（症状照片等）
    return {"answer": _vl_interpret(image_b64, question), "mode": "vision", "metrics": []}
