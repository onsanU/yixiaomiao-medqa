# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 用户记录模块（环节⑥ + 第2次迭代：用户区分）
SQLite 保存问答历史：chat_history 表（id, user, question, answer, sources, created_at）
每个用户的历史相互独立（昵称区分）
"""
import sqlite3, os, json, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "chat_history.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT DEFAULT '游客',
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    # 迁移：旧表没有 user 列时补上
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_history)")]
    if "user" not in cols:
        conn.execute("ALTER TABLE chat_history ADD COLUMN user TEXT DEFAULT '游客'")
    conn.commit()
    return conn


def save_history(user: str, question: str, answer: str, sources: list) -> None:
    """保存一条问答记录（按用户）"""
    conn = _conn()
    conn.execute(
        "INSERT INTO chat_history (user, question, answer, sources, created_at) VALUES (?,?,?,?,?)",
        (user, question, answer, json.dumps(sources, ensure_ascii=False),
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_history(user: str, limit: int = 50) -> list:
    """获取某用户的最近问答历史（新的在前）"""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE user=? ORDER BY id DESC LIMIT ?",
        (user, limit)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["sources"] = json.loads(d["sources"])
        except (json.JSONDecodeError, TypeError):
            d["sources"] = []
        result.append(d)
    return result


def clear_history(user: str) -> int:
    """清空某用户的历史，返回删除条数"""
    conn = _conn()
    cur = conn.execute("DELETE FROM chat_history WHERE user=?", (user,))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def count_history(user: str = None) -> int:
    """历史总条数（user=None 时统计全部）"""
    conn = _conn()
    if user:
        n = conn.execute("SELECT COUNT(*) FROM chat_history WHERE user=?", (user,)).fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
    conn.close()
    return n


def list_users() -> list:
    """所有使用过的用户昵称"""
    conn = _conn()
    rows = conn.execute("SELECT DISTINCT user FROM chat_history").fetchall()
    conn.close()
    return [r["user"] for r in rows]
