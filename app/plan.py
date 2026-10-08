# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 护理行动计划生成（2026-09-02 新增）

用户点"📋 生成护理计划"时调用：检索知识库 → 主脑 qwen3.5:4b（think=False）
生成结构化护理计划 JSON，帮助用户不仅看懂病情、更做好后续管理。

安全设计：
- 内容必须基于知识库检索结果（沿用 RAG 防幻觉体系）
- 不涉及药物剂量；危险信号没把握就写通用就医提醒
- think=False 防 qwen3 超长思考烧光预算（OCR 通道踩过的坑）
"""
import json
import re

from app.vision import chat_ollama, TEXT_MODEL, OLLAMA_URL  # noqa: F401 复用公共调用

PLAN_SYSTEM = """你是"医小喵"的健康管理规划师。用户刚咨询过健康问题，现在需要一份"后续护理行动计划"，帮助用户不仅看懂病情、更能做好后续管理。

请根据【参考资料】和用户问题生成计划，只输出 JSON，格式：
{"condition":"病种/主题名","summary":"1-2句总结（含是否需要就医的明确提示）","level":"需要就医|建议复查|自我管理","items":[{"text":"具体可执行行动","days":"执行时段，如 每天/第1-7天"}],"dangers":["危险信号1（出现即就医）","..."],"timeline":[{"when":"时间点，如 现在/1周后/1月后","what":"该做什么"}]}

要求：
1. items 给 3-7 条具体行动（用药提醒/饮食/运动/监测/作息/情绪），要可执行，不要空泛口号
2. dangers 1-4 条"出现即就医"的危险信号，必须来自参考资料；参考资料没提危险信号时，写"症状加重或持续不缓解时，及时就医"
3. timeline 2-4 个节点（如 现在 → 3天后 → 1周后 → 1月后 的复查/观察节奏）
4. 只根据参考资料生成，资料里没有的内容不要编造；绝不涉及具体药物剂量（只写"遵医嘱用药"）
5. 只输出 JSON 本身，不要任何解释、前后缀或代码块标记"""


def gen_plan(question: str, k: int = 3) -> dict:
    """生成护理计划 JSON；失败返回 {"error": 提示文本}"""
    from app.rag import vectorstore  # 延迟导入（避免循环：rag 不 import plan）

    try:
        docs = vectorstore.similarity_search(question, k=k)
        context = "\n".join(d.page_content for d in docs)
    except Exception as e:
        return {"error": f"知识库检索失败：{e}"}
    if not context.strip():
        return {"error": "知识库中没有相关内容，无法生成可靠计划，建议咨询医生喵~"}

    user_content = f"用户问题：{question}\n\n【参考资料】\n{context}\n\n请生成护理行动计划 JSON。"
    resp = chat_ollama(
        [{"role": "system", "content": PLAN_SYSTEM},
         {"role": "user", "content": user_content}],
        TEXT_MODEL, think=False,
    )
    if not resp or resp.startswith("⚠️"):
        return {"error": resp or "计划生成失败，请稍后再试喵~"}

    m = re.search(r"\{[\s\S]*\}", resp)
    if not m:
        return {"error": "计划格式解析失败，请重试喵~"}
    try:
        plan = json.loads(m.group(0))
    except Exception:
        return {"error": "计划格式解析失败，请重试喵~"}

    # 结构兜底
    plan.setdefault("condition", question[:20])
    plan.setdefault("summary", "")
    plan.setdefault("level", "自我管理")
    plan.setdefault("items", [])
    plan.setdefault("dangers", [])
    plan.setdefault("timeline", [])
    if not plan["items"]:
        return {"error": "未能生成有效行动项，请重试喵~"}
    plan["items"] = [{"text": str(i.get("text", ""))[:60],
                      "days": str(i.get("days", "每天"))[:20]}
                     for i in plan["items"] if isinstance(i, dict) and i.get("text")]
    plan["dangers"] = [str(d)[:80] for d in plan["dangers"][:4]]
    plan["timeline"] = [{"when": str(t.get("when", ""))[:15],
                         "what": str(t.get("what", ""))[:80]}
                        for t in plan["timeline"][:4] if isinstance(t, dict)]
    return plan
