# -*- coding: utf-8 -*-
"""
🐱 医小喵 · FastAPI 服务入口（环节③ + 环节⑥）
启动：cd 项目根目录 && uvicorn app.main:app --host 0.0.0.0 --port 8000
接口：
  POST   /chat     {"question": "..."} → {"answer": "...", "sources": [...]}
  GET    /history  → {"history": [...], "topics": [...]}  问答历史+个性化推荐
  DELETE /history  → {"deleted": n}                        清空历史
"""
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json, random, glob
from app.rag import ask, stream_ask, ask_cat, stream_ask_cat, stream_ask_pet, gen_haiku, CAT_PROFILES
from app.vision import analyze_image
from app import db
from app.auth import current_user  # 第6次迭代：登录鉴权依赖

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="医小喵 API",
    description="医疗健康智能问答助手（RAG + Qwen3.5 4B 本地部署）",
    version="0.3.0",
)

# CORS：允许 file:// 页面（咪咪咖啡网页）直连调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 知识主题列表（带图标）
TOPICS = [
    ("感冒", "🤧"), ("流行性感冒", "🦠"), ("发烧", "🌡️"), ("咳嗽", "😮‍💨"),
    ("头痛", "🤕"), ("失眠", "😴"), ("高血压", "🩺"), ("糖尿病", "💉"),
    ("急性肠胃炎", "🤢"), ("过敏", "🌼"), ("口腔溃疡", "👄"), ("中暑", "☀️"),
    ("扭伤", "🦶"), ("近视", "👓"), ("颈椎病", "🧖"), ("鼻炎", "👃"),
    ("支气管炎", "🫁"), ("哮喘", "😮‍💨"), ("便秘", "🚽"), ("腹泻", "💩"),
    ("咽喉炎", "🗣️"), ("湿疹", "🩹"), ("荨麻疹", "🌿"), ("贫血", "🩸"),
    ("痛风", "🦵"), ("关节炎", "🦴"), ("脂肪肝", "🍺"),
]

# 个性化：问题关键词 → 知识主题
TOPIC_KEYWORDS = {
    "感冒": ["感冒"], "流行性感冒": ["流感"],
    "发烧": ["发烧", "发热", "体温", "高烧"],
    "咳嗽": ["咳嗽"], "头痛": ["头痛", "头疼", "偏头痛"],
    "失眠": ["失眠", "睡不", "睡不着", "入睡"],
    "高血压": ["高血压", "血压"],
    "糖尿病": ["糖尿病", "血糖"],
    "急性肠胃炎": ["肠胃炎", "胃肠", "拉肚子", "闹肚子"],
    "过敏": ["过敏"], "口腔溃疡": ["口腔溃疡", "溃疡", "口疮"],
    "中暑": ["中暑"], "扭伤": ["扭伤", "崴", "拉伤"],
    "近视": ["近视", "视力"], "颈椎病": ["颈椎", "脖子"],
    "鼻炎": ["鼻炎", "鼻塞"], "支气管炎": ["支气管炎", "支气管"],
    "哮喘": ["哮喘", "喘息"], "便秘": ["便秘"],
    "腹泻": ["腹泻", "拉肚"], "咽喉炎": ["咽喉", "嗓子", "喉咙", "咽炎"],
    "湿疹": ["湿疹"], "荨麻疹": ["荨麻疹"],
    "贫血": ["贫血"], "痛风": ["痛风", "尿酸"],
    "关节炎": ["关节炎", "关节疼", "关节痛"], "脂肪肝": ["脂肪肝"],
}


class HistoryItem(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    question: str
    user: str = "游客"
    history: list[HistoryItem] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


class VisionRequest(BaseModel):
    image: str  # base64（无 data: 前缀，前端已压缩）
    question: str = "请解读这张图片里的内容"
    user: str = "游客"


class AsrRequest(BaseModel):
    audio_b64: str = ""          # 前端录音 base64（无 data: 前缀）
    filename: str = "voice.webm" # 默认浏览器录音格式
    user: str = "游客"


class PlanRequest(BaseModel):
    question: str  # 用户原问题（用于知识库检索）
    user: str = "游客"


# ── 护理计划存储（第7次迭代：独立 plans 表 + 全量更新接口）──────
class PlanItemIn(BaseModel):
    text: str
    days: str = ""
    done: bool = False


class PlanUpdateRequest(BaseModel):
    condition: str = ""
    summary: str = ""
    level: str = "自我管理"
    items: list[PlanItemIn] = []
    dangers: list[str] = []
    timeline: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok", "history_count": db.count_history()}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, u: dict = Depends(current_user)):
    """健康问答接口（按登录账号保存历史，支持多轮追问；需登录）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    result = ask(req.question, history=history)
    db.save_history(u["username"], req.question, result["answer"], result["sources"])
    return result


@app.post("/vision/analyze")
def vision_analyze(req: VisionRequest, u: dict = Depends(current_user)):
    """📷 AI 看图解读（检查报告/化验单/症状照片等，非流式；需登录）

    body: {"image": "<base64>", "question": "可选问题"}（归属登录账号，不再收 user）
    自动分流：OCR 文字够多 → 文字解读（OCR+大模型）；否则 → 视觉模型看图
    → {"answer": "解读", "sources": [...]}，同时按账号存历史
    """
    result = analyze_image(req.image, req.question)
    answer = result["answer"]
    metrics = result.get("metrics", [])
    if result.get("mode") == "ocr":
        src_label = "📄 AI文字解读（OCR提取+大模型）"
    else:
        src_label = "🖼️ AI看图解读（qwen2.5vl:3b）"
    q_label = ("[📷图片] " + req.question.strip())[:60]
    db.save_history(u["username"], q_label, answer, [src_label])
    # metrics：结构化指标（前端据此渲染 ECharts 对比图）；存历史时只存文字 answer
    return {"answer": answer, "sources": [src_label], "metrics": metrics}


@app.post("/asr")
def asr_api(req: AsrRequest, u: dict = Depends(current_user)):
    """🎤 语音转文字（SenseVoice 微服务 127.0.0.1:8002，2026-09-03 新增；需登录）

    body: {"audio_b64": "<base64>", "filename": "voice.webm"}
    前端录音(webm) → base64 上传 → 转发 ASR 微服务 → {"text": "识别文字"}
    """
    if not req.audio_b64:
        return {"error": "缺少音频数据"}
    import base64, requests
    try:
        raw = base64.b64decode(req.audio_b64)
    except Exception:
        return {"error": "音频 base64 解码失败"}
    if not raw:
        return {"error": "音频数据为空"}

    try:
        r = requests.post(
            "http://127.0.0.1:8002/asr",
            files={"file": (req.filename or "voice.webm", raw)},
            timeout=300,  # 2026-09-08: 120→300，拖放长音频识别慢时不误杀
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "ASR 服务未启动（127.0.0.1:8002）"}
    except Exception as e:
        return {"error": f"ASR 服务异常: {e}"}


@app.post("/plan")
def plan_api(req: PlanRequest, u: dict = Depends(current_user)):
    """📋 护理行动计划（按需生成 + 独立入库，主人点按钮才触发；需登录）

    body: {"question": "用户原问题"}
    检索知识库 → qwen3.5:4b 生成结构化计划 → 存 plans 表（按账号）→
    {condition, summary, level, items, dangers, timeline, plan_id}
    """
    from app.plan import gen_plan
    plan = gen_plan(req.question)
    if "error" in plan:
        return plan
    # 第7次迭代：独立存 plans 表（不再混进问答历史），返回 plan_id
    pid = db.save_plan(u["username"], req.question.strip()[:200], plan)
    return {**plan, "plan_id": pid}


# ── 📋 我的护理计划（第7次迭代：查看/编辑/打卡/删除，按账号隔离）────
@app.get("/plans")
def plans_list(limit: int = 100, u: dict = Depends(current_user)):
    """我的护理计划列表（新的在前，带完成度；仅当前登录账号）"""
    return {"plans": db.list_plans(u["username"], limit)}


@app.get("/plans/{plan_id}")
def plan_detail(plan_id: int, u: dict = Depends(current_user)):
    """单条计划详情（含全部行动项与打卡状态）"""
    plan = db.get_plan(plan_id, u["username"])
    if not plan:
        return {"error": "计划不存在或无权访问"}
    return plan


@app.put("/plans/{plan_id}")
def plan_update(plan_id: int, req: PlanUpdateRequest, u: dict = Depends(current_user)):
    """更新计划：编辑标题/摘要/等级、增删条目、改打卡状态（全量提交 items）"""
    data = req.model_dump()
    if db.replace_plan(plan_id, u["username"], data):
        return {"ok": True, "plan": db.get_plan(plan_id, u["username"])}
    return {"error": "计划不存在或无权访问"}


@app.delete("/plans/{plan_id}")
def plan_delete(plan_id: int, u: dict = Depends(current_user)):
    """删除整条计划（连行动项一起删）"""
    if db.delete_plan(plan_id, u["username"]):
        return {"ok": True}
    return {"error": "计划不存在或无权访问"}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, u: dict = Depends(current_user)):
    """流式问答（NDJSON：先发sources，再逐块发delta，最后done；需登录）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    sources, gen = stream_ask(req.question, history=history)
    username = u["username"]  # 提前绑定，避免流式闭包引用依赖对象

    def event_stream():
        yield json.dumps({"sources": sources}, ensure_ascii=False) + "\n"
        full = ""
        for delta in gen:
            full += delta
            yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
        db.save_history(username, req.question, full, sources)
        yield json.dumps({"done": True}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/topics")
def topics():
    """知识主题列表（供前端渲染主题卡片）"""
    return {"topics": [{"name": n, "icon": i} for n, i in TOPICS]}


@app.get("/tip")
def tip():
    """每日健康小贴士：随机取一条知识库资料的首段"""
    files = (glob.glob(os.path.join(BASE, "data/raw/web/*.md"))
             + glob.glob(os.path.join(BASE, "data/raw/manual/*.md")))
    path = random.choice(files)
    name = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    paras = [ln.strip() for ln in lines
             if ln.strip() and not ln.startswith("#") and not ln.startswith(">")]
    text = paras[0][:100] if paras else "保持规律作息，均衡饮食，适度运动，健康每一天~"
    return {"topic": name, "text": text}


@app.get("/history")
def history(limit: int = 50, u: dict = Depends(current_user)):
    """某登录账号的问答历史 + 个性化主题推荐（user 取自登录态）"""
    rows = db.get_history(u["username"], limit)
    counts = {}
    for r in rows:
        q = r["question"]
        for topic, kws in TOPIC_KEYWORDS.items():
            if any(k in q for k in kws):
                counts[topic] = counts.get(topic, 0) + 1
    topics = [t for t, _ in sorted(counts.items(), key=lambda x: -x[1])[:3]]
    return {"history": rows, "topics": topics, "user": u["username"]}


@app.delete("/history")
def clear_history(u: dict = Depends(current_user)):
    """清空某登录账号的历史"""
    n = db.clear_history(u["username"])
    return {"deleted": n, "user": u["username"]}


@app.get("/cat/topics")
def cat_topics():
    """猫咖人设信息（4只猫的 id/名字/性格/擅长领域）"""
    return {"cats": list(CAT_PROFILES.values())}


@app.get("/haiku")
def haiku():
    """🎨 我的绘卷：AI 生成三行俳句（中文三行 + 日文假名三行）"""
    return gen_haiku()


@app.post("/cat/chat", response_model=ChatResponse)
def cat_chat(cat_id: str, req: ChatRequest):
    """猫咖人设问答（非流式）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    result = ask_cat(cat_id, req.question, history=history)
    db.save_history(f"猫咖-{cat_id}-{req.user}", req.question, result["answer"], result["sources"])
    return result


@app.post("/cat/chat/stream")
def cat_chat_stream(cat_id: str, req: ChatRequest):
    """猫咖人设流式问答（NDJSON：先发sources，再逐块发delta，最后done）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    sources, gen = stream_ask_cat(cat_id, req.question, history=history)

    def event_stream():
        yield json.dumps({"sources": sources}, ensure_ascii=False) + "\n"
        full = ""
        for delta in gen:
            full += delta
            yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
        db.save_history(f"猫咖-{cat_id}-{req.user}", req.question, full, sources)
        yield json.dumps({"done": True}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


# ═══ 🎵 网易云音乐搜索代理（黑黑页面 AI 音乐推荐）═══
from app import music


@app.get("/music/search")
def music_search(kw: str, limit: int = 6):
    """搜索歌曲：?kw=轻音乐&limit=6 → {"songs": [{id,name,artist,duration}]}"""
    try:
        return {"songs": music.search_songs(kw, min(limit, 20))}
    except Exception as e:
        return {"songs": [], "error": str(e)}


@app.get("/music/url")
def music_url(id: int):
    """取歌曲播放地址（有时效）：?id=xxx → {"url": "https://...mp3"}"""
    try:
        r = music.get_song_url(id)
        if not r:
            return {"url": None, "error": "无法获取播放地址（可能是付费歌曲）"}
        return r
    except Exception as e:
        return {"url": None, "error": str(e)}


# ═══ 🐾 桌宠对话（性格驱动，纯聊天，不知道就诚实说）═══
class PetChatRequest(BaseModel):
    question: str
    name: str = "桌宠"
    personality: str = "可爱"
    history: list = []


@app.post("/pet/chat/stream")
def pet_chat_stream(req: PetChatRequest):
    """桌宠流式对话（NDJSON：delta...done）"""
    gen = stream_ask_pet(req.name, req.personality, req.question, history=req.history)

    def event_stream():
        for delta in gen:
            yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
        yield json.dumps({"done": True}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


# ═══ 🐱 管理台 API（AdminLTE 后台配套，2026-09-07 新增）═══
# 注册顺序必须在根挂载 "/" 之前，否则 /admin/api/* 会被静态兜底吞掉
from app import admin_api
app.include_router(admin_api.router, prefix="/admin/api")

# ═══ 🔐 账号体系 API（第6次迭代：注册/登录/登出/me + 管理员重置）═══
from app import auth_api
app.include_router(auth_api.router, prefix="/auth")

# 猫咖网页挂载（方案B：让其他电脑能直接访问咪咪咖啡网页，同源免CORS）
# 注意：必须放在根挂载 "/" 之前，否则会被根挂载吞掉路由
CAFE_DIR = "/mnt/d/Project/JXprojiect/Hermes-project/project/咪咪咖啡网页/MeowCafe"
if os.path.isdir(CAFE_DIR):
    app.mount("/cafe", StaticFiles(directory=CAFE_DIR, html=True), name="cafe")

# 静态页面（聊天界面），放在最后兜底
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
