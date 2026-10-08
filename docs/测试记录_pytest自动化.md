# 测试记录 · Pytest 自动化测试

| 项目 | 内容 |
|------|------|
| 测试时间 | 2026-08-14 |
| 测试工具 | pytest 9.1.1 + FastAPI TestClient |
| 测试范围 | 7 个用例（接口层自动化） |
| 结果 | ✅ 7 passed（20.16s） |

## 用例明细

| # | 用例 | 验证内容 | 结果 |
|---|------|---------|------|
| 1 | test_health | 健康检查接口 /health | ✅ |
| 2 | test_topics | 知识主题列表 ≥20 个、含感冒、含图标 | ✅ |
| 3 | test_tip | 今日健康贴士返回主题+内容 | ✅ |
| 4 | test_chat_knowledge | 知识问答（感冒）返回回答+来源 | ✅ |
| 5 | test_chat_fantasy | 防幻觉：火星种土豆 → "暂无/咨询医生" | ✅ |
| 6 | test_chat_stream | 流式输出含 sources 和 delta 块 | ✅ |
| 7 | test_history_isolation | 用户历史隔离：A 的提问不出现在 B 的历史 | ✅ |

## 运行方式

```bash
cd /mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa
source ~/medqa-venv/bin/activate
python -m pytest tests/ -v
```
