# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 管理台 API（2026-09-07 新增，配套 AdminLTE 管理端 app/static/admin/）

独立路由模块，不侵入主业务逻辑；main.py 注册：include_router(prefix="/admin/api")
只读统计为主 + 管理端删除能力，供后台页面 fetch 调用：

  GET    /admin/api/stats             数据看板统计（总量/用户/趋势/主题分布/类型分布）
  GET    /admin/api/records           对话记录分页（?page & size & user & kw & type）
  GET    /admin/api/records/{id}      单条记录详情
  DELETE /admin/api/records/{id}      删除单条记录
  DELETE /admin/api/records?user=xxx  清空某用户全部记录
  GET    /admin/api/users             用户聚合统计（?page & size）
  GET    /admin/api/system            系统状态（Ollama 模型 / ASR 服务 / DB 概况）
"""
import os
import json
import datetime
import glob

from fastapi import APIRouter, Query, Depends
import requests

from app import db  # 双模式读写层（sqlite 默认 / .env 切 mysql，2026-09-07）
from app.auth import current_admin  # 第6次迭代：管理 API 全部要求管理员登录

router = APIRouter()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw")

TYPE_LABEL = {"chat": "问答", "image": "看图解读", "plan": "护理计划", "cat": "猫咖对话"}
TYPE_COLOR = {"chat": "primary", "image": "success", "plan": "warning", "cat": "info"}


def guess_type(user, question):
    """按问题前缀/用户名推断记录类型（与 main.py 历史存储约定一致）"""
    q = question or ""
    if q.startswith("[📷图片]"):
        return "image"
    if q.startswith("[📋计划]"):
        return "plan"
    if str(user or "").startswith("猫咖-"):
        return "cat"
    return "chat"


def guess_topic(question):
    """知识主题归类 —— 延迟 import，与 main.py 的 TOPIC_KEYWORDS 保持单一数据源"""
    from app.main import TOPIC_KEYWORDS
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(k in question for k in kws):
            return topic
    return None


def _all_rows():
    """全量记录（倒序）+ 类型/主题标注。量级为千条内，内存处理足够"""
    rows = db.fetch_all("SELECT * FROM chat_history ORDER BY id DESC")
    for r in rows:
        try:
            r["sources"] = json.loads(r["sources"])
        except (json.JSONDecodeError, TypeError):
            r["sources"] = []
        r["type"] = guess_type(r.get("user"), r.get("question"))
        r["type_label"] = TYPE_LABEL[r["type"]]
        r["topic"] = guess_topic(r["question"]) if r["type"] == "chat" else None
    return rows


def _kb_files():
    return len(glob.glob(os.path.join(RAW_DIR, "web", "*.md"))
               + glob.glob(os.path.join(RAW_DIR, "manual", "*.md")))


def _kb_chunks():
    """向量库知识块数（读 Chroma 计数，失败返回 None）"""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=os.path.join(BASE, "data", "kb"))
        cols = client.list_collections()
        if cols:
            return cols[0].count()
    except Exception:
        pass
    return None


# ═══════════ 数据看板统计 ═══════════
@router.get("/stats")
def stats(_admin: dict = Depends(current_admin)):
    rows = _all_rows()
    total = len(rows)
    users = len({r["user"] for r in rows})
    today = datetime.date.today()
    today_key = today.strftime("%Y-%m-%d")
    today_n = sum(1 for r in rows if (r["created_at"] or "").startswith(today_key))

    # 近 14 天趋势（补全空日期）
    start = today - datetime.timedelta(days=13)
    counts = {}
    for r in rows:
        d = (r["created_at"] or "")[:10]
        if d and d >= start.isoformat():
            counts[d] = counts.get(d, 0) + 1
    trend = []
    for i in range(14):
        day = start + datetime.timedelta(days=i)
        trend.append({"date": day.strftime("%m-%d"), "count": counts.get(day.isoformat(), 0)})

    # 类型分布 + 主题分布
    type_cnt = {}
    topic_cnt = {}
    for r in rows:
        type_cnt[r["type"]] = type_cnt.get(r["type"], 0) + 1
        if r["topic"]:
            topic_cnt[r["topic"]] = topic_cnt.get(r["topic"], 0) + 1
    type_dist = [{"type": k, "label": TYPE_LABEL[k], "count": v}
                 for k, v in sorted(type_cnt.items(), key=lambda x: -x[1])]
    topic_dist = [{"topic": k, "count": v}
                  for k, v in sorted(topic_cnt.items(), key=lambda x: -x[1])]

    # 知识库概况：raw 资料篇数 + 向量库块数
    kb_files = _kb_files()
    kb_chunks = _kb_chunks()

    return {
        "total_questions": total,
        "total_users": users,
        "today_questions": today_n,
        "avg_per_user": round(total / users, 1) if users else 0,
        "trend": trend,
        "type_dist": type_dist,
        "topic_dist": topic_dist,
        "kb_files": kb_files,
        "kb_chunks": kb_chunks,
        "latest_at": rows[0]["created_at"] if rows else None,
    }


# ═══════════ 对话记录（分页 + 筛选） ═══════════
@router.get("/records")
def records(_admin: dict = Depends(current_admin),
            page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200),
            user: str = "", kw: str = "", type: str = ""):
    rows = _all_rows()
    if user:
        rows = [r for r in rows if r["user"] == user]
    if kw:
        rows = [r for r in rows if kw in r["question"] or kw in r["answer"]]
    if type and type != "all":
        rows = [r for r in rows if r["type"] == type]

    total = len(rows)
    start = (page - 1) * size
    items = []
    for r in rows[start:start + size]:
        items.append({
            "id": r["id"], "user": r["user"], "question": r["question"],
            "answer_preview": (r["answer"] or "")[:120],
            "type": r["type"], "type_label": r["type_label"],
            "sources": r["sources"], "created_at": r["created_at"],
            "topic": r["topic"],
        })
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/records/{rid}")
def record_detail(rid: int, _admin: dict = Depends(current_admin)):
    r = db.fetch_one("SELECT * FROM chat_history WHERE id=%s", (rid,))
    if not r:
        return {"error": "记录不存在"}
    try:
        r["sources"] = json.loads(r["sources"])
    except (json.JSONDecodeError, TypeError):
        r["sources"] = []
    r["type"] = guess_type(r.get("user"), r.get("question"))
    r["type_label"] = TYPE_LABEL[r["type"]]
    return r


@router.delete("/records/{rid}")
def delete_one(rid: int, _admin: dict = Depends(current_admin)):
    n = db.execute("DELETE FROM chat_history WHERE id=%s", (rid,))
    return {"deleted": n, "id": rid}


@router.delete("/records")
def delete_by_user(user: str = Query(...), _admin: dict = Depends(current_admin)):
    n = db.execute("DELETE FROM chat_history WHERE user=%s", (user,))
    return {"deleted": n, "user": user}


# ═══════════ 注册账号管理（第6次迭代：账号密码登录）═══════════
@router.get("/accounts")
def accounts(_admin: dict = Depends(current_admin),
             page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    """注册账号列表（username/role/注册时间/问答数）——不含密码哈希（安全）"""
    users_rows = db.fetch_all(
        "SELECT username, role, created_at FROM users ORDER BY id DESC")
    cnt = {}
    for r in db.fetch_all("SELECT user, COUNT(*) AS n FROM chat_history GROUP BY user"):
        cnt[r["user"]] = r["n"]
    total = len(users_rows)
    start = (page - 1) * size
    items = []
    for u in users_rows[start:start + size]:
        items.append({"username": u["username"], "role": u["role"],
                      "created_at": u["created_at"],
                      "question_count": cnt.get(u["username"], 0)})
    return {"total": total, "page": page, "size": size, "items": items}


# ═══════════ 用户聚合统计 ═══════════
@router.get("/users")
def users(_admin: dict = Depends(current_admin),
          page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    rows = _all_rows()
    agg = {}
    for r in rows:
        u = r["user"]
        a = agg.get(u)
        if a is None:
            a = {"user": u, "count": 0, "first_at": r["created_at"], "last_at": r["created_at"], "types": set()}
            agg[u] = a
        a["count"] += 1
        a["types"].add(r["type"])
        if r["created_at"] < a["first_at"]:
            a["first_at"] = r["created_at"]
        if r["created_at"] > a["last_at"]:
            a["last_at"] = r["created_at"]
    items = sorted(agg.values(), key=lambda x: -x["count"])
    total = len(items)
    start = (page - 1) * size
    for a in items[start:start + size]:
        a["types"] = sorted(a["types"])
        a["type_labels"] = [TYPE_LABEL[t] for t in a["types"]]
    return {"total": total, "page": page, "size": size,
            "items": items[start:start + size]}


# ═══════════ 系统状态 ═══════════
def _fmt_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


@router.get("/system")
def system(_admin: dict = Depends(current_admin)):
    # Ollama 模型
    ollama = {"ok": False, "models": []}
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.ok:
            data = r.json()
            ollama["ok"] = True
            for m in data.get("models", []):
                ollama["models"].append({
                    "name": m.get("name"), "size_gb": round(m.get("size", 0) / 1e9, 1),
                    "modified": (m.get("modified_at") or "")[:10],
                })
    except Exception:
        pass

    # ASR 微服务
    asr = {"ok": False, "detail": "未响应"}
    try:
        r = requests.get("http://127.0.0.1:8002/health", timeout=3)
        if r.ok:
            asr = {"ok": True, "detail": "正常"}
    except Exception:
        asr["detail"] = "未启动（127.0.0.1:8002）"

    # DB 概况
    db_info: dict = {"driver": db.driver()}
    if db.driver() == "mysql":
        db_info["path"] = f"{db.DB_HOST}:{db.DB_PORT}/{db.DB_NAME}"
    else:
        db_info["size"] = _fmt_size(os.path.getsize(db.DB_PATH)) if os.path.exists(db.DB_PATH) else "无"
        db_info["path"] = "data/chat_history.db"
    try:
        db_info["records"] = db.count_history()
    except Exception:
        db_info["records"] = 0

    kb_files = _kb_files()
    kb_chunks = _kb_chunks()

    return {
        "ollama": ollama,
        "asr": asr,
        "db": db_info,
        "kb_files": kb_files,
        "kb_chunks": kb_chunks,
        "api_version": "0.3.0 + admin(2026-09-07)",
        "api_url": "http://localhost:8000",
    }
