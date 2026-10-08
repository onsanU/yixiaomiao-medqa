# -*- coding: utf-8 -*-
"""
🐱 医小喵 · SQLite → MySQL 一次性数据迁移脚本（第5次迭代）

前置：MySQL 已建库建账号（见 .env.example），且 my.ini bind-address=0.0.0.0、WSL 可连通
用法：
    python migrate_sqlite_to_mysql.py
幂等：按原 id 插入，已存在（重复迁移）自动跳过；可反复执行。

迁移内容：data/chat_history.db 的 chat_history 表全量 → MySQL yixiaomiao 库同名表
（知识库 ChromaDB 不在此列，与 MySQL 无关）
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_DB = os.path.join(BASE, "data", "chat_history.db")

# 强制走 MySQL 后端（无视当前 .env 的 YXM_DB）
os.environ["YXM_DB"] = "mysql"
os.environ.setdefault("YXM_DB_HOST", "172.30.160.1")
os.environ.setdefault("YXM_DB_USER", "yixiaomiao")
os.environ.setdefault("YXM_DB_PASSWORD", "yxm123456")
os.environ.setdefault("YXM_DB_NAME", "yixiaomiao")

from app import db  # noqa: E402  必须在设置 YXM_DB 之后导入


def main():
    if db.driver() != "mysql":
        print("❌ 未进入 MySQL 模式（db.driver =", db.driver(), "），请检查 .env")
        sys.exit(1)

    # 1. 读 SQLite 全量
    if not os.path.exists(SRC_DB):
        print("❌ 找不到 SQLite 库:", SRC_DB)
        sys.exit(1)
    conn = sqlite3.connect(SRC_DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM chat_history ORDER BY id")]
    conn.close()
    print(f"① SQLite 读取 {len(rows)} 条（{SRC_DB}）")

    # 2. 目标库现状
    try:
        before = db.count_history()
        print(f"② MySQL 当前已有 {before} 条（{db.DB_HOST}:{db.DB_PORT}/{db.DB_NAME}）")
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}\n   请检查 MySQL 服务/账号/网络（见 .env.example 注释）")
        sys.exit(1)

    # 3. 逐条迁移（保留原 id；冲突即跳过 = 幂等）
    inserted, skipped = 0, 0
    for r in rows:
        try:
            db.execute(
                "INSERT INTO chat_history (id, user, question, answer, sources, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (r["id"], r["user"], r["question"], r["answer"], r["sources"], r["created_at"]))
            inserted += 1
        except Exception:
            skipped += 1  # 主键冲突（已迁移过）等
    after = db.count_history()
    print(f"③ 完成：插入 {inserted} 条，跳过 {skipped} 条（已存在）；MySQL 现有 {after} 条")

    if after >= len(rows) and inserted >= 0:
        print("✅ 迁移完成！现在把项目根 .env 的 YXM_DB 改为 mysql 即可切换")
    else:
        print("⚠️ 结果异常，请检查")


if __name__ == "__main__":
    main()
