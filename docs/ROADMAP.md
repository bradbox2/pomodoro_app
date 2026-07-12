# FocusFlow × GoalSifter 三阶段路线图

**更新日期：** 2026-07-12  
**当前状态：** 第一阶段已完成并通过本地验证；第二阶段已进入客户端落地，第三阶段仍待后续同步能力成熟后再推进。

## 架构原则

- FocusFlow 是 Windows 本地优先的专注执行客户端；GoalSifter 是任务、KR、积分与任务生命周期的权威系统。
- 仅 `dw`（深度工作）任务可绑定番茄钟；`ph`（突破）任务和提醒不进入 FocusFlow 的可启动番茄列表。
- 番茄完成记录必须是带稳定 UUID 的不可变事件。将来任何重试和多设备上传均以该 UUID 幂等去重，不能按任务名称或日期去重。
- VPS 当前只有静态 IP、没有 HTTPS；第二、三阶段的客户端通信采用 SSH 本地端口转发访问 VPS 上仅监听回环地址的服务，不公开无 TLS 的 HTTP API。
- FocusFlow 的本地“项目”仅是个人组织标签；跨系统关联必须使用 GoalSifter `task_id`，不能使用任务名或 KR 名称。

## 第一阶段：本地可运行与可迁移基础

**目标：** 得到不依赖 VPS、SSH、PocketBase 或网络的 Windows 本地版本；应用升级不覆盖个人数据，办公室电脑可以独立安装和使用。

**已完成：**

- 删除 PocketBase、SSH 隧道、旧 `SyncManager`、任务拉取、奖励上报与相关初始化脚本；运行时不再保留活动云同步引用。
- 新增 `AppPaths`：默认将可变数据存放到 `%LOCALAPPDATA%\\FocusFlow`，并支持 `FOCUSFLOW_DATA_DIR` 指定办公室电脑、U 盘或备份目录。
- 首次启动从旧项目根目录复制 `data/` 与 `config.json`；不会删除旧文件，也不会覆盖目标目录内已有文件。
- 数据库、动态配置、备份、日志和 HTML 报表分别落到用户数据目录及其 `backup/`、`logs/`、`exports/` 子目录。
- 两个启动脚本统一使用 `.venv\\Scripts\\pythonw.exe`；增加 `requirements-dev.txt`、pytest 配置及自动化/手工测试隔离。

**验证证据：** 2026-07-12 在项目 `.venv` 执行 `python -m pytest -q`，结果为 **15 passed**；关键生产模块 `compileall` 成功；生产 Python 源码检索未发现 PocketBase、SSH、`SyncManager`、`requests`、`dotenv` 或 `WEEKLY_BRIDGE` 引用。

**使用边界：** 本阶段各电脑的数据仍彼此独立。把整个 `%LOCALAPPDATA%\\FocusFlow` 目录复制到另一台电脑可迁移数据，但这不是自动同步，复制前应关闭两端应用。

## 第二阶段：GoalSifter 深度工作绑定

**目标：** 在不破坏离线使用的前提下，让 FocusFlow 显示并绑定 GoalSifter 的活跃 `dw` 任务，且只由 GoalSifter 结算任务番茄数和 EXP。

**实施范围：**

- 在 GoalSifter FastAPI 中提供桌面客户端专用的只读 DW 任务快照接口，以及番茄事件写入接口；服务继续只监听 VPS `127.0.0.1`。
- 每台 FocusFlow 通过用户配置的 SSH Host alias 建立本地端口转发；客户端绝不直接访问公网 HTTP，也不携带 GoalSifter SQLite 文件。
- 引入本地 `focus_items` 映射：已绑定项保存 `goalsifter_task_id`；未绑定项保存本地 UUID 和“草稿”状态。
- 本地草稿可立即开工；联网后用户显式选择“映射到已有 DW”或“创建新的 DW”。禁止静默自动创建云端任务。
- 完成番茄写入本地 Outbox，事件包含 `event_id`、`device_id`、`task_id`（可为空）、起止时间、时长和状态；服务器按 `event_id` 幂等处理。绑定 DW 后，服务端调用 GoalSifter 的正式记录路径，更新 `pomo_count`、`task_events` 与 EXP。

**验收标准：** 无网络时本地番茄可完成并入队；恢复 SSH 连接后同一事件只上传/计分一次；同名不同任务不串账；PH 与提醒不会出现在 FocusFlow 的云端任务选择器。

### 服务端契约已定稿并部署（2026-07-12）— 锁定，客户端按此开发

> **项目边界声明**：FocusFlow 与 GoalSifter 是两个独立开发的项目，只通过本节
> 契约通信。本文档只记录**契约事实**（端点、字段、状态码、语义）和**两项共享
> 部署坐标**；GoalSifter 的服务端实现（数据库结构、事务机制、代码组织、仓库
> 提交历史）不属于本文档，其变更记录以 GoalSifter 项目自己的文档为准。
> 客户端代码只允许依赖本节内容，不得依赖对方任何内部行为。

**共享部署坐标（仅此两项）：**
1. 服务地址：SSH 隧道 → `127.0.0.1:8000`
2. Bearer token 取值文件：VPS `/root/.openclaw/secrets/focusflow.env`

**客户端凭据规则（锁定）：** FocusFlow 首次配置时由用户手动粘贴 Bearer token，并仅将其保存到本机
`%LOCALAPPDATA%\\FocusFlow` 数据目录下的客户端配置。SSH 只负责建立端口转发；客户端不得通过 SSH
执行命令、读取或复制 VPS 的 `/root/.openclaw/secrets/focusflow.env`。更换或撤销 token 后，用户必须在
FocusFlow 本机配置中显式更新它。

**契约事实（不再变更）：**

- **端点**：
  - `GET /api/v1/focusflow/tasks` — 只读活跃 `dw` 快照；每项含 `task_id`、`task_name`、`kr_ref`、`pomo_estimate`、`pomo_count`、`status`、`created_at`、`last_event_at`。契约不含 `updated_at`；新鲜度以 `last_event_at` 判断。
  - `POST /api/v1/focusflow/pomo-events` — 事件字段：`event_id`、`device_id`、`task_id`、`started_at`、`ended_at`、`duration_minutes`、`status`（当前仅接受 `"completed"`）。响应：`{event_id, duplicate, task_id, pomo_count, exp_awarded}`；同一 `event_id` 重放返回 200 + `duplicate: true` + 当前 `pomo_count`，不重复计分。
  - `POST /api/v1/focusflow/tasks` — 显式创建 DW：`{name, pomo_estimate?}`。评级由服务端规则决定，请求不携带 filters/rating；任务名未通过服务端校验 → 422，客户端须提示用户回 GoalSifter（飞书/TTC）完成澄清后再绑定，不得在桌面端旁路。
- **认证**：每个请求带 `Authorization: Bearer <token>`；缺失/错误 → 401。
- **拒绝与重试语义**：`ph` 任务、不存在的 task_id、非活跃任务 → 422。凡未收到 `duplicate: true` 成功响应的事件，客户端可用**同一 `event_id`** 安全重试，服务端保证不重复计分。
- **网络边界**：公网侧对 `/api/v1/focusflow/` 一律 403；该前缀只能经 SSH 隧道访问，与本路线图的架构原则一致。

**客户端计分口径（契约层语义，2026-07-12 定稿）：**

- 一条事件 = 一个完成的番茄；每条被接受的事件响应中 `exp_awarded` 即本次入账积分，客户端无需也不得自行推算积分规则。
- 预估番茄数（`pomo_estimate`）契约范围 **1–4**，超出 422。本地草稿建议同口径（1–4），大任务在本地就引导拆分，避免同步时才冲突。预估不封顶实际完成数：超出预估的番茄照常上传、照常计分。
- "当天完成了多少番茄"没有查询接口，也不需要：服务端从事件流自行派生统计；FocusFlow 界面显示当日数量时从本地会话记录自算。
- 本地未绑定草稿的番茄**不产生服务端积分**（设计使然：只有进入 GoalSifter 的任务才计分）；绑定后补传的历史事件照常逐条计分，计入上传时所在的结算周期——跨周补传会把积分记到晚一周，介意就及时同步。
- 任务的"完成"由用户在 GoalSifter 侧操作，FocusFlow 不触发任务完成（锁定）。

## 第三阶段：办公室/家庭多客户端同步

**目标：** 至少两台 Windows 设备可安全地共享绑定关系、草稿任务和番茄事件，同时允许离线工作与同一任务的并行专注。

**实施范围：**

- 在 VPS 的回环地址部署 Focus Sync 服务及事件存储；所有客户端仍通过 SSH 隧道访问，SSH 密钥按设备单独配置且可撤销。
- 客户端维护 `device_id`、本地 Outbox 与 `sync_cursor`；采用拉取增量事件 → 幂等推送本地事件 → 更新游标的同步顺序。
- 会话按不可变事件合并：不同设备同时完成同一 DW 时均保留并累加；重复事件按 UUID 忽略。任务映射的冲突不做静默覆盖，显示“待选择映射”。
- 服务器保存事件审计、设备最后同步时间和失败原因；客户端显示离线、同步中、已同步、需要处理冲突四种状态。
- 完成旧本地数据导入工具、跨设备断网/重试/重复提交测试及恢复演练。

**验收标准：** 两台设备离线各完成番茄后可收敛为相同历史；重复同步不增加 GoalSifter 番茄或 EXP；撤销一个设备的 SSH 凭据不影响另一个设备；任何未绑定草稿都不会自动污染 GoalSifter 的任务清单。

## 现阶段下一步

~~第一阶段已冻结为本地稳定基线。开始第二阶段前，需要先在 GoalSifter v3 中定义并测试桌面专用 API 契约、SSH 设备接入规则和 `event_id` 幂等存储。~~
**（2026-07-12 更新）服务端契约已就绪；数据层（GoalSifterSettings / focus_items / focus_outbox / GoalSifterClient）及双来源选择界面已实现。**
UI 接入按 **Local-first 三段顺序**锁定（决策依据：VPS 生产端尚未充分投产验证，日常计时不得依赖远程；本地路径是绑定路径的子集，先做不返工）：

1. **本地任务计时 UI**（已实现）：默认来源为“本地任务”；本地分类仅是个人整理标签，可为空，番茄流程离线可用。
2. **"从 GoalSifter 选择"入口**（已实现）：第二个来源标签只读拉取 `GET /api/v1/focusflow/tasks` 的活跃 DW；KR 仅显示为远端上下文，绝不替代或写入本地分类；隧道不可用不阻塞本地计时。
3. **显式同步动作**（已实现）："绑定到已有 DW"、"创建并绑定 DW"（422 时引导回 GoalSifter 澄清）、"手动同步 Outbox"（接受或 `duplicate` 后清账）。同步永远是用户主动行为，不做后台自动同步。

**界面交互口径：** “本地任务 / GoalSifter 任务”是来源标签，不是旧的“编辑任务 / 本地草稿”分区。单击任务卡只设为当前任务；用户再按“开始”才启动计时，避免误触。

**本地任务管理口径（2026-07-12）：** 本地任务预估范围为 **1–99**，仅作为个人容量与进度显示；绑定或创建 GoalSifter DW 时仍必须为 **1–4**，超过 4 必须先拆分。本地无效任务通过“管理本地任务”窗口归档，保留历史会话；归档任务可恢复。管理窗口已支持本地 Project 的重命名、合并和删除空分类，合并时若存在同名 Task 会整笔拒绝，避免悄悄吞数据。

**窗口口径（2026-07-12）：** 首页与管理窗口是普通工作窗口，不再用固定大空白布局；首页会按控件请求尺寸自适应并受屏幕可用范围约束，仅番茄计时页切换为 `300×400` 的置顶紧凑窗口。任务切换仍通过计时页 Home 返回首页完成。

**首页与 Project 管理口径（2026-07-12）：** 首页与管理页只管理本地 Project，Project 的角色是个人分类，不再对应远端 KR；GoalSifter KR 始终只读。当前首页布局已重新收紧，Start 不再被截断，管理入口集中在本地任务窗口。

仍然不要恢复 PocketBase 或旧 `WEEKLY_BRIDGE` 任务接口。
