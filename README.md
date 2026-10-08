# 🐱 医小喵 · 医疗健康智能问答助手

基于**本地大模型 + RAG 检索增强生成**的多模态健康智能问答系统。用户以聊天方式咨询常见健康问题，系统基于医疗知识库给出有依据的回答；还能**看图解读检查报告、语音提问、生成护理行动计划**，不联网也能用。

> ⚠️ 本助手仅供参考，不能替代专业医生诊断。紧急情况请及时就医。

## ✨ 功能特性

- 💬 **智能问答**：Qwen3.5 4B 本地大模型 + RAG，回答有知识库依据（27 主题 / 751 知识块）
- 📷 **AI 看图解读**：上传或 Ctrl+V 粘贴检查报告 / 化验单 / 症状照片 → OCR + 视觉模型（qwen2.5vl:3b）双通道自动分流解读；报告指标结构化 → ECharts 对比图，**超标自动标红**
- 📋 **护理行动计划**：问完病情一键生成结构化护理计划卡（可执行行动 / 危险信号 / 复查时间线），基于知识库生成、不涉及药物剂量
- 🎤 **语音输入**：SenseVoice 本地语音识别，浏览器录音即可提问（中文 + 标点）
- ⚡ **流式输出**：回答打字机式逐字显示（NDJSON）
- 📜 **问答历史**：按用户昵称隔离保存，可查看完整对话并继续追问
- 🎯 **个性化推荐**：根据历史提问推荐相关健康主题
- 💡 **今日健康贴士**：每日随机健康小知识
- 🛡️ **防幻觉机制**：知识库外问题如实说明，不胡编乱造；不诊断、不处方
- 📊 **管理后台**（`/admin`）：AdminLTE 数据看板（问答统计/趋势图表/热门主题/最新对话）、对话记录检索与清理、用户统计、系统状态监控（Ollama/ASR/DB/知识库）——资源全本地化，断网可用
- 🔐 **账号密码登录**（2026-09-07）：注册/登录后才能使用，历史跟账号走（注册同名自动接管旧记录）；密码 PBKDF2 加密存储、登录限流防爆破、token 7 天有效可吊销；首个注册账号自动为管理员，管理后台 `/admin` 需管理员登录，含「账号管理」页（重置密码/角色切换）

## 🧰 技术栈

| 组件 | 用途 |
|------|------|
| Ollama + Qwen3.5 4B | 主脑大模型：RAG 问答 / OCR 文字解读 / 护理计划（GPU 加速） |
| Ollama + Qwen2.5-VL 3B | 视觉模型：看图解读（100% GPU，keep_alive=0 用完即卸） |
| qwen3-embedding:0.6b + ChromaDB | 医疗知识向量检索 |
| LangChain | RAG 流程编排 |
| SenseVoiceSmall（独立微服务） | ASR 语音识别（127.0.0.1:8002） |
| RapidOCR | 图片文字提取（OCR 通道） |
| FastAPI + Uvicorn | 后端 API + 前端页面托管 |
| SQLite / MySQL 双模式 | 问答历史存储（默认 SQLite `data/chat_history.db`；项目根 `.env` 设 `YXM_DB=mysql` 切 MySQL，2026-09-07） |
| ECharts | 检查报告指标对比图渲染 |
| HTML/CSS/JS | 聊天界面（深色医疗科技风） |
| AdminLTE 4 | 管理后台界面（`/admin`，Bootstrap 5 模板本地化，数据看板/记录/用户/系统） |
| PBKDF2 + Token | 账号密码体系（密码哈希存储、会话令牌、登录限流/防枚举，2026-09-07） |

## 📁 目录结构

```
yixiaomiao-medqa/
├── app/                    # 后端代码
│   ├── main.py             # FastAPI 入口（/chat /chat/stream /vision/analyze /asr /plan
│   │                       #   /history /topics /tip + 猫咖 /cat/* /haiku /music/* + 管理台 /admin/api/*）
│   ├── admin_api.py        # 管理台 API（stats/records/users/system，2026-09-07 新增）
│   ├── rag.py              # RAG 核心（检索+生成，支持多轮/猫咖人设/桌宠/俳句）
│   ├── vision.py           # 📷 AI 看图（OCR + 视觉双通道，2026-09-02）
│   ├── plan.py             # 📋 护理行动计划生成（2026-09-02）
│   ├── asr_server.py       # 🎤 SenseVoice ASR 微服务（独立 8002 端口，2026-09-03）
│   ├── music.py            # 网易云音乐搜索代理（猫咖黑黑页 AI 推荐）
│   ├── auth.py             # 🔐 认证核心：PBKDF2 密码哈希 / token / 鉴权依赖
│   ├── auth_api.py         # 🔐 认证 API（/auth：注册/登录/登出/me/重置/角色，2026-09-07）
│   ├── db.py               # 用户问答历史（SQLite/MySQL 双模式统一层）
│   └── static/             # 前端聊天界面（深色医疗科技风 + ECharts）
│       └── admin/          # 管理后台（AdminLTE v4.9.1 本地化：看板/记录/用户/账号/系统 + vendor/ + login.html）
├── .env.example            # 存储后端切换配置样例（复制为 .env 生效；不建则默认 SQLite）
├── migrate_sqlite_to_mysql.py  # SQLite→MySQL 一次性迁移脚本（幂等，2026-09-07）
├── models/SenseVoiceSmall/ # SenseVoice 语音模型权重（funasr）
├── data/
│   ├── raw/                # 医疗知识资料（A+医学百科25篇 + 手写2篇）
│   ├── kb/                 # 向量知识库（build_kb.py 生成，已 gitignore）
│   └── chat_history.db     # 问答历史（已 gitignore）
├── demo/                   # 技术验证 demo（第1次迭代产物）
├── docs/                   # 课程文档（定位/需求/进度/迭代说明×3/测试记录×2）
├── tests/                  # Pytest 自动化测试
├── build_kb.py             # 知识库构建脚本
├── test_suite.py           # 全量测试脚本（32题）
├── start.sh                # 一键启动脚本（Ollama + ASR + API 三件套）
└── requirements.txt        # Python 依赖
```

## 🚀 快速开始

### 环境要求

- Linux/WSL，Python 3.10+
- [Ollama](https://ollama.com) 已安装（建议 ≥0.33，多模态/性能更优）
- RTX 显卡（有 GPU 更流畅，无 GPU 也能跑但慢）

### 第一步：安装依赖

```bash
# 主服务虚拟环境
python3 -m venv ~/medqa-venv
source ~/medqa-venv/bin/activate
pip install -r requirements.txt

# 语音 ASR 独立虚拟环境（可选，不用语音可跳过）
python3 -m venv ~/sensevoice-venv
~/sensevoice-venv/bin/pip install funasr modelscope
```

### 第二步：下载模型

```bash
ollama pull qwen3.5:4b          # 主脑（RAG/解读/护理计划）
ollama pull qwen2.5vl:3b        # 视觉（看图解读）
ollama pull qwen3-embedding:0.6b  # 向量嵌入
```

### 第三步：一键启动

```bash
bash start.sh
```

脚本自动拉起三件套：Ollama(11434) → SenseVoice ASR(8002) → API(8000)。

浏览器打开 http://localhost:8000 即可使用！**首次先注册账号**（第一个注册的自动成为管理员 ⭐），登录后可聊天/看图/录音/护理计划；聊天历史跟账号走。

管理后台（第4次迭代 + 第6次登录保护）：http://localhost:8000/admin/ → 需管理员登录（非管理员会被拦在登录页）——数据看板 / 对话记录 / 用户统计 / **账号管理**（重置密码·角色切换）/ 系统状态

### 存储双模式（第5次迭代，2026-09-07）
- **默认 SQLite**：`data/chat_history.db`，零配置（不建 .env 即可跑）
- **切 MySQL**：复制 `.env.example` 为 `.env`，设 `YXM_DB=mysql` 并填连接参数（Windows MySQL 需 `bind-address=0.0.0.0` + 建 `yixiaomiao` 库和专用账号，见 docs/迭代说明_第5次）
- 迁移：先配好 MySQL 连接，跑 `python migrate_sqlite_to_mysql.py`（幂等，保留原 id）
- 管理后台「系统状态」页会显示当前 driver 与连接地址

### 手动启动（备选）

```bash
# 终端1：启动 Ollama
ollama serve

# 终端2：启动 ASR（可选）
~/sensevoice-venv/bin/uvicorn app.asr_server:app --host 127.0.0.1 --port 8002

# 终端3：启动 API
cd /mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa
source ~/medqa-venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔌 API 一览

| 接口 | 说明 |
|------|------|
| POST /chat | 健康问答（带来源，非流式） |
| POST /chat/stream | 流式问答（NDJSON：sources → delta* → done） |
| POST /vision/analyze | 📷 AI 看图解读（base64 图片 → OCR/视觉双通道） |
| POST /asr | 🎤 语音转文字（转发 SenseVoice 8002） |
| POST /plan | 📋 护理行动计划生成 |
| GET /history · DELETE /history | 问答历史 + 个性化推荐 / 清空 |
| GET /topics · GET /tip | 知识主题列表 / 今日健康贴士 |
| GET /health | 健康检查 |
| POST /auth/register · /login | 🔐 注册（首个=管理员）/ 登录（限流+防枚举）→ token |
| POST /auth/logout · GET /auth/me | 🔐 登出（吊销）/ 当前账号（校验 token） |
| POST /auth/reset · /auth/role | 🔐 [管理员] 重置任意用户密码 / 切换角色（防自降级） |
| GET /admin/api/accounts | 📊 管理台：注册账号列表（含角色/注册时间/问答数，不含密码） |
| GET /admin/api/stats | 📊 管理台：数据看板统计（问答量/趋势/类型/主题/知识库） |
| GET /admin/api/records · /{id} · DELETE | 管理台：对话记录分页筛选 / 详情 / 删除 |
| GET /admin/api/users | 管理台：用户聚合统计 |
| GET /admin/api/system | 管理台：系统状态（Ollama / ASR / DB / 知识库） |

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
| 迭代说明（3次） | docs/迭代说明_第1次技术验证、第2次用户区分与追问、第3次多模态智能升级 |
| 测试数据+测试记录 | docs/测试记录_第2次迭代、docs/测试记录_pytest自动化 |
| 进度记录 | docs/03_项目进度记录.md（v1.0 基线 + v0.3.0 多模态升级） |
| 部署说明 | docs/部署说明.md、start.sh |
| Skill 文件（项目说明） | 本 README.md |
