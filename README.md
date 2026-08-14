# 🐱 医小喵 · 医疗健康智能问答助手

基于 **本地大模型 + RAG 检索增强生成** 的健康智能问答系统。用户以聊天方式咨询常见健康问题，系统基于医疗知识库给出有依据的回答，不联网也能用。

> ⚠️ 本助手仅供参考，不能替代专业医生诊断。紧急情况请及时就医。

## ✨ 功能特性

- 💬 **智能问答**：Qwen2.5 7B 本地大模型 + RAG，回答有知识库依据
- 🏥 **健康知识库**：27 个常见医疗主题（感冒/流感/失眠/高血压/糖尿病…），点击即问
- ⚡ **流式输出**：回答打字机式逐字显示
- 📜 **问答历史**：按用户昵称隔离保存，可查看完整对话并继续追问
- 🎯 **个性化推荐**：根据历史提问推荐相关健康主题
- 💡 **今日健康贴士**：每日随机健康小知识
- 🛡️ **防幻觉机制**：知识库外问题如实说明，不胡编乱造；不诊断、不处方

## 🧰 技术栈

| 组件 | 用途 |
|------|------|
| Ollama + Qwen2.5 7B | 本地大模型推理（GPU 加速） |
| qwen3-embedding:0.6b + ChromaDB | 医疗知识向量检索 |
| LangChain | RAG 流程编排 |
| FastAPI + Uvicorn | 后端 API + 前端页面托管 |
| SQLite | 问答历史存储 |
| HTML/CSS/JS | 聊天界面（深色医疗科技风） |

## 📁 目录结构

```
医疗健康智能问答助手/
├── app/                # 后端代码
│   ├── main.py         # FastAPI 入口（/chat /history /topics /tip /chat/stream）
│   ├── rag.py          # RAG 核心（检索+生成，支持多轮）
│   ├── db.py           # 用户问答历史（SQLite）
│   └── static/         # 前端聊天界面
├── data/
│   ├── raw/            # 医疗知识资料（A+医学百科25篇 + 手写2篇）
│   ├── kb/             # 向量知识库（build_kb.py 生成，已 gitignore）
│   └── chat_history.db # 问答历史（已 gitignore）
├── demo/               # 技术验证 demo（第1次迭代产物）
├── docs/               # 课程文档（定位/需求/进度/迭代说明×2/测试记录×2）
├── tests/              # Pytest 自动化测试
├── build_kb.py         # 知识库构建脚本
├── test_suite.py       # 全量测试脚本（32题）
├── start.sh            # 一键启动脚本
└── requirements.txt    # Python 依赖
```

## 🚀 快速开始

### 环境要求

- Linux/WSL，Python 3.10+
- [Ollama](https://ollama.com) 已安装
- RTX 显卡（有 GPU 更流畅，无 GPU 也能跑但慢）

### 第一步：安装依赖

```bash
python3 -m venv ~/medqa-venv
source ~/medqa-venv/bin/activate
pip install -r requirements.txt
```

### 第二步：下载模型

```bash
ollama pull qwen2.5:7b
ollama pull qwen3-embedding:0.6b
```

### 第三步：一键启动

```bash
bash start.sh
```

浏览器打开 http://localhost:8000 即可使用！

### 手动启动（备选）

```bash
# 终端1：启动 Ollama
ollama serve

# 终端2：启动 API
cd 医疗健康智能问答助手
source ~/medqa-venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🧪 测试

```bash
# 自动化接口测试（7用例）
python -m pytest tests/ -v

# 全量问答测试（32题，覆盖27主题+特殊边界）
python test_suite.py
```

## 📚 课程交付物清单

| 交付物 | 位置 |
|--------|------|
| 项目定位/需求文档 | docs/01、docs/02 |
| 迭代说明（2次） | docs/迭代说明_第1次、第2次 |
| 测试数据+测试记录 | docs/测试记录_第2次迭代、docs/测试记录_pytest自动化 |
| 部署说明 | docs/部署说明.md、start.sh |
| Skill 文件（项目说明） | 本 README.md |
