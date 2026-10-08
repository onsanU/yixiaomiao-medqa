# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 用户记录模块（环节⑥ + 第2次迭代：用户区分 + 第5次迭代：MySQL 双模式）
SQLite 保存问答历史：chat_history 表（id, user, question, answer, sources, created_at）
每个用户的历史相互独立（昵称区分）

【双模式存储（2026-09-07）】
- 默认 SQLite：data/chat_history.db，零配置（原行为不变）
- 项目根 .env 设 `YXM_DB=mysql` 即切换 MySQL（连接参数见下方 YXM_DB_*）
- SQL 统一写 MySQL 风格 %s 占位符，SQLite 后端自动转 ?，业务代码无感
"""
import os
import json
import sqlite3
import datetime

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, ".env"))  # .env 不存在则静默跳过

# ── 存储后端配置（环境变量，默认 SQLite）────────────────────
DB_DRIVER = os.getenv("YXM_DB", "sqlite").strip().lower()  # sqlite | mysql
DB_HOST = os.getenv("YXM_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("YXM_DB_PORT", "3306"))
DB_USER = os.getenv("YXM_DB_USER", "yixiaomiao")
DB_PASSWORD = os.getenv("YXM_DB_PASSWORD", "")
DB_NAME = os.getenv("YXM_DB_NAME", "yixiaomiao")
DB_PATH = os.path.join(BASE, "data", "chat_history.db")


def driver() -> str:
    """当前存储后端：'sqlite' 或 'mysql'"""
    return DB_DRIVER


def _adapt(sql: str) -> str:
    """统一 %s 占位符 → SQLite 的 ?（参数化防注入）"""
    return sql.replace("%s", "?") if DB_DRIVER == "sqlite" else sql


def _ensure_schema(conn) -> None:
    """幂等建表（含旧库迁移）。mysql 建索引 user；sqlite 保留原 ALTER 迁移逻辑"""
    if DB_DRIVER == "mysql":
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user VARCHAR(100) NOT NULL DEFAULT '游客',
                question TEXT NOT NULL,
                answer MEDIUMTEXT NOT NULL,
                sources TEXT DEFAULT ('[]'),
                created_at DATETIME NOT NULL,
                INDEX idx_chat_user (user)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(200) NOT NULL,
                role VARCHAR(10) NOT NULL DEFAULT 'user',
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                token_hash CHAR(64) NOT NULL UNIQUE,
                username VARCHAR(100) NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL,
                INDEX idx_sess_user (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                question TEXT NOT NULL,
                `condition` VARCHAR(200) DEFAULT '',
                summary TEXT NOT NULL,
                level VARCHAR(50) DEFAULT '自我管理',
                dangers TEXT NOT NULL,
                timeline TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                INDEX idx_plans_user (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS plan_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plan_id INT NOT NULL,
                text TEXT NOT NULL,
                days VARCHAR(100) DEFAULT '',
                done TINYINT(1) DEFAULT 0,
                sort INT DEFAULT 0,
                INDEX idx_pi_plan (plan_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
        return
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            question TEXT NOT NULL,
            condition TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            level TEXT DEFAULT '自我管理',
            dangers TEXT DEFAULT '[]',
            timeline TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            days TEXT DEFAULT '',
            done INTEGER DEFAULT 0,
            sort INTEGER DEFAULT 0
        )
    """)
    # 迁移：旧表没有 user 列时补上
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_history)")]
    if "user" not in cols:
        conn.execute("ALTER TABLE chat_history ADD COLUMN user TEXT DEFAULT '游客'")
    conn.commit()


def connect():
    """按当前后端返回连接（sqlite3.Connection / pymysql.Connection），行均可按列名取值"""
    if DB_DRIVER == "mysql":
        import pymysql
        conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                               password=DB_PASSWORD, database=DB_NAME,
                               charset="utf8mb4", autocommit=True,
                               cursorclass=pymysql.cursors.DictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


# ── 统一读写层（admin_api 等模块共用）─────────────────────
def execute(sql: str, params: tuple = ()) -> int:
    """写操作（INSERT/DELETE…），返回影响行数"""
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params)
        if DB_DRIVER == "sqlite":
            conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple = ()) -> list:
    """读操作，返回 dict 列表。datetime 值统一转字符串（MySQL 返回对象 / SQLite 本就是 str）"""
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params)
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            for k, v in d.items():
                if isinstance(v, datetime.datetime):
                    d[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(d)
        return rows
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple = ()):
    """读单行 dict，无结果返回 None"""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


# ── 业务函数（签名保持，main.py / tests 无感）────────────────
def save_history(user: str, question: str, answer: str, sources: list) -> None:
    """保存一条问答记录（按用户）"""
    execute(
        "INSERT INTO chat_history (user, question, answer, sources, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user, question, answer, json.dumps(sources, ensure_ascii=False),
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


def get_history(user: str, limit: int = 50) -> list:
    """获取某用户的最近问答历史（新的在前）"""
    rows = fetch_all(
        "SELECT * FROM chat_history WHERE user=%s ORDER BY id DESC LIMIT %s",
        (user, limit))
    for r in rows:
        try:
            r["sources"] = json.loads(r["sources"])
        except (json.JSONDecodeError, TypeError):
            r["sources"] = []
    return rows


def clear_history(user: str) -> int:
    """清空某用户的历史，返回删除条数"""
    return execute("DELETE FROM chat_history WHERE user=%s", (user,))


def count_history(user: str = None) -> int:
    """历史总条数（user=None 时统计全部）"""
    if user:
        r = fetch_one("SELECT COUNT(*) AS n FROM chat_history WHERE user=%s", (user,))
    else:
        r = fetch_one("SELECT COUNT(*) AS n FROM chat_history")
    return r["n"] if r else 0


def list_users() -> list:
    """所有使用过的用户昵称"""
    return [r["user"] for r in fetch_all("SELECT DISTINCT user FROM chat_history")]


# ── 账号体系（第6次迭代：账号密码登录，2026-09-07）──────────────
def _now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_user(username: str, password_hash: str, role: str = "user") -> bool:
    """注册用户（用户名唯一，冲突返回 False）。首个用户由 auth 层提升为 admin"""
    try:
        n = execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (%s, %s, %s, %s)",
            (username, password_hash, role, _now_str()))
        return n == 1
    except Exception:
        return False


def get_user(username: str):
    """按用户名取用户（含 password_hash / role / created_at）"""
    return fetch_one("SELECT * FROM users WHERE username=%s", (username,))


def count_users() -> int:
    r = fetch_one("SELECT COUNT(*) AS n FROM users")
    return r["n"] if r else 0


def update_user(username: str, password_hash: str = None, role: str = None) -> bool:
    """更新用户（管理后台重置密码 / 改角色）；None 字段不动"""
    sets, params = [], []
    if password_hash is not None:
        sets.append("password_hash=%s"); params.append(password_hash)
    if role is not None:
        sets.append("role=%s"); params.append(role)
    if not sets:
        return False
    params.append(username)
    return execute(f"UPDATE users SET {', '.join(sets)} WHERE username=%s", tuple(params)) > 0  # type: ignore[arg-type]


def create_session(token_hash: str, username: str, expires_at: str) -> bool:
    """建登录会话（token 只存 sha256 哈希，防库泄露直接可用）"""
    try:
        n = execute(
            "INSERT INTO sessions (token_hash, username, expires_at, created_at) VALUES (%s, %s, %s, %s)",
            (token_hash, username, expires_at, _now_str()))
        return n == 1
    except Exception:
        return False


def get_session_user(token_hash: str):
    """按 token 哈希查有效会话（未过期），返回用户名；无效/过期返回 None"""
    row = fetch_one("SELECT * FROM sessions WHERE token_hash=%s", (token_hash,))
    if not row:
        return None
    if row["expires_at"] < _now_str():  # 同格式字符串可直接比较
        execute("DELETE FROM sessions WHERE token_hash=%s", (token_hash,))
        return None
    return row["username"]


def delete_session(token_hash: str) -> None:
    """登出：吊销会话"""
    execute("DELETE FROM sessions WHERE token_hash=%s", (token_hash,))


def delete_user_sessions(username: str) -> None:
    """吊销某用户全部会话（管理员重置密码后强制重新登录）"""
    execute("DELETE FROM sessions WHERE username=%s", (username,))


# ── 护理计划（第7次迭代：计划独立存储，按账号隔离，2026-09-08）────────
def _plan_row_to_dict(row: dict) -> dict:
    """主表行 → 接口 dict（json 列解析）"""
    d = dict(row)
    for k in ("dangers", "timeline"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[k] = []
    d.pop("username", None)
    return d


def save_plan(username: str, question: str, plan: dict) -> int:
    """新建护理计划（主表 + 条目一次事务写入），返回 plan_id

    plan: {"condition","summary","level","items":[{text,days}],"dangers":[],"timeline":[]}
    """
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(
            "INSERT INTO plans (username, question, `condition`, summary, level, dangers, timeline, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"),
            (username, question, plan.get("condition", ""), plan.get("summary", ""),
             plan.get("level", "自我管理"),
             json.dumps(plan.get("dangers", []), ensure_ascii=False),
             json.dumps(plan.get("timeline", []), ensure_ascii=False), _now_str()))
        pid = cur.lastrowid
        if pid is None:
            raise RuntimeError("plan insert failed: no lastrowid")
        for i, it in enumerate(plan.get("items") or []):
            cur.execute(_adapt(
                "INSERT INTO plan_items (plan_id, text, days, done, sort) VALUES (%s, %s, %s, %s, %s)"),
                (pid, (it.get("text") or "").strip(), str(it.get("days", "") or ""),
                 1 if it.get("done") else 0, i))
        if DB_DRIVER == "sqlite":
            conn.commit()
        return pid
    finally:
        conn.close()


def get_plan(plan_id: int, username: str) -> dict | None:
    """取某用户的一条完整计划（含 items 列表），越权/不存在返回 None"""
    row = fetch_one("SELECT * FROM plans WHERE id=%s AND username=%s", (plan_id, username))
    if not row:
        return None
    plan = _plan_row_to_dict(row)
    items = fetch_all(
        "SELECT id, text, days, done, sort FROM plan_items WHERE plan_id=%s ORDER BY sort, id",
        (plan_id,))
    plan["items"] = [dict(it, done=bool(it["done"])) for it in items]
    return plan


def list_plans(username: str, limit: int = 100) -> list:
    """某用户的计划列表（新的在前），带完成度统计"""
    rows = fetch_all(
        "SELECT p.id, p.question, p.`condition`, p.level, p.created_at, "
        "COUNT(pi.id) AS total, COALESCE(SUM(pi.done), 0) AS done "
        "FROM plans p LEFT JOIN plan_items pi ON pi.plan_id = p.id "
        "WHERE p.username=%s GROUP BY p.id ORDER BY p.id DESC LIMIT %s",
        (username, limit))
    for r in rows:
        r["total"] = int(r["total"] or 0)
        r["done"] = int(r["done"] or 0)
        r["progress"] = round(r["done"] / r["total"] * 100) if r["total"] else 0
    return rows


def replace_plan(plan_id: int, username: str, data: dict) -> bool:
    """全量更新一条计划（主表元信息 + items 重建），仅限本人；返回是否命中"""
    if not fetch_one("SELECT id FROM plans WHERE id=%s AND username=%s", (plan_id, username)):
        return False
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(
            "UPDATE plans SET `condition`=%s, summary=%s, level=%s, dangers=%s, timeline=%s "
            "WHERE id=%s AND username=%s"),
            (data.get("condition", ""), data.get("summary", ""),
             data.get("level", "自我管理"),
             json.dumps(data.get("dangers", []), ensure_ascii=False),
             json.dumps(data.get("timeline", []), ensure_ascii=False),
             plan_id, username))
        cur.execute(_adapt("DELETE FROM plan_items WHERE plan_id=%s"), (plan_id,))
        for i, it in enumerate(data.get("items") or []):
            cur.execute(_adapt(
                "INSERT INTO plan_items (plan_id, text, days, done, sort) VALUES (%s, %s, %s, %s, %s)"),
                (plan_id, (it.get("text") or "").strip(), str(it.get("days", "") or ""),
                 1 if it.get("done") else 0, i))
        if DB_DRIVER == "sqlite":
            conn.commit()
        return True
    finally:
        conn.close()


def delete_plan(plan_id: int, username: str) -> bool:
    """删除一条计划（连 items），仅限本人；返回是否命中"""
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_adapt("DELETE FROM plan_items WHERE plan_id=%s"), (plan_id,))
        cur.execute(_adapt("DELETE FROM plans WHERE id=%s AND username=%s"),
                    (plan_id, username))
        n = cur.rowcount
        if DB_DRIVER == "sqlite":
            conn.commit()
        return n > 0
    finally:
        conn.close()
