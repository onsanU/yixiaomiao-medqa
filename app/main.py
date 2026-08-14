# -*- coding: utf-8 -*-
"""
🐱 医小喵 · FastAPI 服务入口（环节③ + 环节⑥）
启动：cd 项目根目录 && uvicorn app.main:app --host 0.0.0.0 --port 8000
接口：
  POST   /chat     {"question": "..."} → {"answer": "...", "sources": [...]}
  GET    /history  → {"history": [...], "topics": [...]}  问答历史+个性化推荐
  DELETE /history  → {"deleted": n}                        清空历史
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os, json, random, glob
from app.rag import ask, stream_ask
from app import db

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="医小喵 API",
    description="医疗健康智能问答助手（RAG + Qwen2.5 本地部署）",
    version="0.3.0",
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


@app.get("/health")
def health():
    return {"status": "ok", "history_count": db.count_history()}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """健康问答接口（按用户保存历史，支持多轮追问）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    result = ask(req.question, history=history)
    db.save_history(req.user, req.question, result["answer"], result["sources"])
    return result


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """流式问答（NDJSON：先发sources，再逐块发delta，最后done）"""
    history = [{"role": h.role, "content": h.content} for h in req.history]
    sources, gen = stream_ask(req.question, history=history)

    def event_stream():
        yield json.dumps({"sources": sources}, ensure_ascii=False) + "\n"
        full = ""
        for delta in gen:
            full += delta
            yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
        db.save_history(req.user, req.question, full, sources)
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
def history(user: str = "游客", limit: int = 50):
    """某用户的问答历史 + 个性化主题推荐"""
    rows = db.get_history(user, limit)
    counts = {}
    for r in rows:
        q = r["question"]
        for topic, kws in TOPIC_KEYWORDS.items():
            if any(k in q for k in kws):
                counts[topic] = counts.get(topic, 0) + 1
    topics = [t for t, _ in sorted(counts.items(), key=lambda x: -x[1])[:3]]
    return {"history": rows, "topics": topics, "user": user}


@app.delete("/history")
def clear_history(user: str = "游客"):
    """清空某用户的历史"""
    n = db.clear_history(user)
    return {"deleted": n, "user": user}


# 静态页面（聊天界面），放在最后兜底
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
