# -*- coding: utf-8 -*-
"""
🐱 医小喵 · Pytest 自动化测试（环节⑦ + 第6次迭代适配：账号密码登录）
覆盖：健康检查 / 主题列表 / 今日贴士 / 登录鉴权 / 知识问答 / 防幻觉 / 流式输出 / 账号历史隔离
运行：source ~/medqa-venv/bin/activate && python -m pytest tests/ -v --tb=short

注：第6次迭代起 /chat /history 需登录（X-Auth-Token）——测试自动注册/登录固定账号，
   每次跑完自动清理这些账号产生的聊天记录（账号本身保留，避免 users 表无限膨胀）。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app
import app.db as db

client = TestClient(app)

# 固定测试账号（若首次注册成功即普通用户；已存在则直接登录）
TEST_ACCOUNTS = [("pytestA", "pytest123456"), ("pytestB", "pytest123456")]


def _auth(username: str, password: str) -> str:
    """注册（不存在时）或登录 → 返回 token"""
    r = client.post("/auth/register", json={"username": username, "password": password})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"账号准备失败: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def tokens():
    """模块级：两个测试账号的 token（聊天历史按账号隔离）"""
    return {u: _auth(u, p) for u, p in TEST_ACCOUNTS}


@pytest.fixture(autouse=True)
def _cleanup_history():
    """每个测试后清理测试账号产生的聊天记录（账号保留）"""
    yield
    for u, _ in TEST_ACCOUNTS:
        db.clear_history(u)


def _hdrs(token: str) -> dict:
    return {"X-Auth-Token": token}


def test_health():
    """健康检查接口（公开）"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_topics():
    """知识主题列表（公开，≥20个，含感冒）"""
    r = client.get("/topics")
    assert r.status_code == 200
    topics = r.json()["topics"]
    assert len(topics) >= 20
    names = [t["name"] for t in topics]
    assert "感冒" in names
    assert all(t["icon"] for t in topics)


def test_tip():
    """今日健康贴士（公开）"""
    r = client.get("/tip")
    assert r.status_code == 200
    data = r.json()
    assert data["topic"]
    assert data["text"]


def test_auth_required():
    """第6次迭代：/chat 无 token → 401"""
    r = client.post("/chat", json={"question": "感冒怎么办？"})
    assert r.status_code == 401


def test_auth_login_wrong_password():
    """登录错误密码 → 401"""
    r = client.post("/auth/login", json={"username": "pytestA", "password": "wrong-pass"})
    assert r.status_code == 401


def test_chat_knowledge(tokens):
    """知识主题问答（感冒，需登录）"""
    r = client.post("/chat", json={"question": "感冒了嗓子疼怎么办？"},
                    headers=_hdrs(tokens["pytestA"]))
    assert r.status_code == 200
    data = r.json()
    assert data["answer"], "回答不能为空"
    assert data["sources"], "应返回参考来源"


def test_chat_fantasy(tokens):
    """防幻觉：知识库外问题应诚实回答"""
    r = client.post("/chat", json={"question": "火星上能种土豆吗？"},
                    headers=_hdrs(tokens["pytestA"]))
    data = r.json()
    assert "暂无" in data["answer"] or "咨询医生" in data["answer"], \
        f"防幻觉失败：{data['answer'][:50]}"


def test_chat_stream(tokens):
    """流式输出接口（需登录）"""
    with client.stream("POST", "/chat/stream",
                       json={"question": "高血压饮食注意什么？"},
                       headers=_hdrs(tokens["pytestA"])) as r:
        body = "".join(r.iter_text())
    assert '"sources"' in body, "流式输出应包含 sources"
    assert '"delta"' in body, "流式输出应包含 delta 内容块"


def test_history_isolation(tokens):
    """账号历史隔离：A的提问不出现在B的历史里（token 决定归属）"""
    q = "痛风患者能喝酒吗？"
    client.post("/chat", json={"question": q}, headers=_hdrs(tokens["pytestA"]))
    rA = client.get("/history", headers=_hdrs(tokens["pytestA"]))
    rB = client.get("/history", headers=_hdrs(tokens["pytestB"]))
    assert rA.status_code == 200
    qsA = [h["question"] for h in rA.json()["history"]]
    qsB = [h["question"] for h in rB.json()["history"]]
    assert q in qsA, "A账号应看到自己的提问"
    assert q not in qsB, "B账号不应看到A的提问"


def test_me_after_login(tokens):
    """/auth/me 返回登录账号"""
    r = client.get("/auth/me", headers=_hdrs(tokens["pytestA"]))
    assert r.status_code == 200
    assert r.json()["username"] == "pytestA"
