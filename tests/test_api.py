# -*- coding: utf-8 -*-
"""
🐱 医小喵 · Pytest 自动化测试（环节⑦）
覆盖：健康检查 / 主题列表 / 今日贴士 / 知识问答 / 防幻觉 / 流式输出 / 用户隔离
运行：source ~/medqa-venv/bin/activate && python -m pytest tests/ -v --tb=short
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    """健康检查接口"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_topics():
    """知识主题列表（≥20个，含感冒）"""
    r = client.get("/topics")
    assert r.status_code == 200
    topics = r.json()["topics"]
    assert len(topics) >= 20
    names = [t["name"] for t in topics]
    assert "感冒" in names
    assert all(t["icon"] for t in topics)


def test_tip():
    """今日健康贴士"""
    r = client.get("/tip")
    assert r.status_code == 200
    data = r.json()
    assert data["topic"]
    assert data["text"]


def test_chat_knowledge():
    """知识主题问答（感冒）"""
    r = client.post("/chat", json={"question": "感冒了嗓子疼怎么办？", "user": "pytest用户"})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"], "回答不能为空"
    assert data["sources"], "应返回参考来源"


def test_chat_fantasy():
    """防幻觉：知识库外问题应诚实回答"""
    r = client.post("/chat", json={"question": "火星上能种土豆吗？", "user": "pytest用户"})
    data = r.json()
    assert "暂无" in data["answer"] or "咨询医生" in data["answer"], \
        f"防幻觉失败：{data['answer'][:50]}"


def test_chat_stream():
    """流式输出接口"""
    with client.stream("POST", "/chat/stream",
                       json={"question": "高血压饮食注意什么？", "user": "pytest用户"}) as r:
        body = "".join(r.iter_text())
    assert '"sources"' in body, "流式输出应包含 sources"
    assert '"delta"' in body, "流式输出应包含 delta 内容块"


def test_history_isolation():
    """用户历史隔离：A的问题不出现在B的历史里"""
    q = "痛风患者能喝酒吗？"
    client.post("/chat", json={"question": q, "user": "隔离测试A"})
    rA = client.get("/history", params={"user": "隔离测试A"})
    rB = client.get("/history", params={"user": "隔离测试B"})
    qsA = [h["question"] for h in rA.json()["history"]]
    qsB = [h["question"] for h in rB.json()["history"]]
    assert q in qsA, "A用户应看到自己的提问"
    assert q not in qsB, "B用户不应看到A的提问"
