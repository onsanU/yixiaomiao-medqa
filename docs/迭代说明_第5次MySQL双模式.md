# 迭代说明 · 第5次迭代（问答存储 SQLite → MySQL 双模式）

| 项目 | 内容 |
|------|------|
| 项目名称 | 医疗健康智能问答助手（医小喵） |
| 迭代时间 | 2026-09-07 |
| 迭代类型 | 问答历史存储升级：SQLite → MySQL 双模式（.env 一键切换） |
| 参与角色 | 咪咪（AI辅助）+ 主人（点 UAC 配合 + MySQL 学习练手） |

---

## 一、本次迭代目标

医小喵此前问答历史存 SQLite（`data/chat_history.db`，裸 sqlite3）。主人在学 MySQL，想拿真实项目练手并用于答辩展示。本次目标：

1. **双模式架构**：SQLite 保持默认零配置不变；项目根 `.env` 设 `YXM_DB=mysql` 即切换 MySQL——稳、可回退、不破坏现有功能
2. **跨环境打通**：医小喵服务跑 WSL，MySQL 跑 Windows（D:\Project\MySQL，8.0.29 ZIP 版，服务 MySQL80）——解决 WSL ↔ Windows MySQL 的网络连通
3. **数据迁移**：SQLite 230 条历史完整迁入 MySQL（保留原 id，幂等可重跑）
4. **学习价值**：完整走一遍"真实项目换库"流程（驱动适配 / 占位符 / 编码 / 建库授权 / 防火墙 / 数据迁移），踩坑全记录

> 知识库 ChromaDB 向量库与本次无关（RAG 检索用，不迁移）。

---

## 二、完成内容

### 1. 🔌 依赖与配置
- `requirements.txt` 新增 `pymysql`、`python-dotenv`
- 新增 `.env.example`（配置样例）+ 实际 `.env`（当前 YXM_DB=mysql）
- 环境变量：`YXM_DB`(sqlite|mysql) / `YXM_DB_HOST` / `YXM_DB_PORT` / `YXM_DB_USER` / `YXM_DB_PASSWORD` / `YXM_DB_NAME`

### 2. 🗄️ `app/db.py` 重构为双模式统一层
- **连接工厂**：`connect()` 按 driver 返回 sqlite3 / pymysql 连接（mysql 走 utf8mb4 + DictCursor + autocommit）
- **占位符统一**：SQL 一律写 MySQL 风格 `%s`，SQLite 后端自动转 `?`（`_adapt()`）——业务代码无感
- **建表双分支**：mysql 用 `CREATE TABLE IF NOT EXISTS`（InnoDB + utf8mb4_unicode_ci + `user` 列索引）；sqlite 保留原逻辑（含旧表补 user 列迁移）
- **类型统一**：MySQL DATETIME 返回 datetime 对象 → `fetch_all()` 统一转字符串（与 SQLite TEXT 格式一致，前端/统计零改动）
- 公共底层 `execute / fetch_all / fetch_one` + 原 6 个业务函数（save/get/clear/count/list_users/driver）签名不变 → **main.py、tests 无感**

### 3. 🧩 `app/admin_api.py` 改用公共层
- 删除自带 sqlite3 连接（`_conn`/`DB_PATH`），改调 `db.fetch_all / fetch_one / execute`（SQL 同步改 %s）
- system 接口 DB 卡片：mysql 模式显示连接地址（host:port/库名），sqlite 显示文件大小

### 4. 🌐 跨环境网络打通（WSL ↔ Windows MySQL）
| 步骤 | 操作 | 坑 |
|------|------|-----|
| ① 监听放开 | my.ini `bind-address=127.0.0.1` → `0.0.0.0` | ZIP 版默认安全配置只监听本机；改后需重启服务 |
| ② 服务重启 | restart_mysql.bat（net stop/start MySQL80）UAC 提权 | 首次 bat 未执行成功 → 改用 `Start-Process -Verb RunAs -Wait` 直接提权命令重启成功 |
| ③ 防火墙放行 | `netsh advfirewall firewall add rule ... localport=3306`（UAC） | **最大隐形坑**：监听 0.0.0.0 后 Windows 防火墙拦 WSL NAT 连接，TCP 一直超时；放行后秒通 |
| ④ 账号授权 | `CREATE DATABASE yixiaomiao utf8mb4` + `yixiaomiao@'%'` 专用账号 + GRANT | root@localhost 不认 WSL 来源连接，必须建专用账号（不用 root/123456 学习密码） |
| ⑤ WSL 连接地址 | Windows 宿主 IP（`ip route` 网关 172.30.160.1） | WSL2 NAT 模式下不能用 localhost 连 Windows 服务 |

### 5. 📦 迁移脚本 `migrate_sqlite_to_mysql.py`
- 强制 mysql 后端 → 读 SQLite 全表 → 按原 id 逐条 INSERT（主键冲突自动跳过 = 幂等可重跑）
- 迁移结果：**230 条全量入库，0 跳过**，id 1-234 保留（AUTO_INCREMENT 接续 235 验证）

---

## 三、实测数据（2026-09-07 全链路验证）

| 验证项 | 结果 |
|--------|------|
| SQLite → MySQL 迁移 | 230 条全量入库、中文/emoji 完好、原 id 保留 ✅ |
| MySQL 写入接续 | 迁移后新问答 id=235（AUTO_INCREMENT 接续正确）✅ |
| /health | MySQL 模式 history_count 正确（230→234 随写入增长）✅ |
| 管理 API | stats(231/20用户/趋势14点/主题TOP1感冒) · type=image 29条全命中 · users TOP1 53条 · 详情 created_at 字符串化 ✅ |
| 管理台 system 页 | 正确显示「存储后端 MySQL · 172.30.160.1:3306/yixiaomiao · 记录数」✅ |
| pytest | **7 passed**（MySQL 模式下，写读删链路全过）✅ |
| SQLite 回退 | 临时 8001 实例 YXM_DB=sqlite → 230 条、管理 API 正常（双模式闭环）✅ |
| 聊天链路 | /chat 提问正常写入 MySQL（RAG 不受影响）✅ |

---

## 四、遇到的问题与解决（学习价值最高的部分）

| 问题 | 解决方案 |
|------|---------|
| WSL → Windows MySQL TCP 超时 | 三层排查：① my.ini bind-address=127.0.0.1 只监听本机 → 改 0.0.0.0 重启；② **Windows 防火墙拦 WSL NAT 连接**（监听放开后仍超时）→ netsh 放行 3306；③ 通后建 yixiaomiao@'%' 账号（root@localhost 不认远程） |
| UAC bat 点完没生效 | bat 有 pause 且可能报错被关 → 改用 `Start-Process -Verb RunAs -Wait powershell -Command 'net stop/start MySQL80'` 直接提权命令，成功 |
| TEXT 列默认值报错 (1101) | MySQL TEXT/BLOB 不能直接 `DEFAULT '[]'` → 用表达式默认值 `DEFAULT ('[]')`（8.0.13+） |
| MySQL DATETIME 返回对象、SQLite 返回字符串 | 双后端类型不一致 → `fetch_all()` 统一 strftime 转 `"%Y-%m-%d %H:%M:%S"`（一处修复，前端/统计全兼容） |
| 占位符差异（sqlite ? / mysql %s） | SQL 统一写 %s，`_adapt()` 在 sqlite 分支自动转 ? |
| 迁移脚本优雅失败 | MySQL 未连通时输出友好报错 + exit 1（不假装成功） |
| patch 误伤函数（guess_type 被吞） | 读文件核对当前结构 → 整段重写为正确三函数（教训：替换锚点要足够长且验证结果） |

---

## 五、迭代成果与下一步

**成果**：医小喵问答存储升级为 **SQLite/MySQL 双模式**——默认零配置不变，`.env` 一行切换；230 条历史无损迁移；管理台系统页实时显示当前 driver。对主人学习价值：完整走通"真实项目换数据库"全流程（驱动适配、占位符、utf8mb4、建库授权、跨 WSL/Windows 网络、防火墙、迁移幂等），答辩可讲的故事点充足。

**下一步**（待主人确认）：
- 知识库管理后台（在线增删改 27 主题，需动 RAG 向量重建链路，改动大待答辩后）
- Git 仓库同步本轮代码（后台 v0.3.1 + MySQL 双模式 v0.4.0 均未 commit）
- /admin 访问保护（上公网前必做，医疗记录隐私）
