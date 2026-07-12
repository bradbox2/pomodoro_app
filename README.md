# 🍅 FocusFlow 3.1 - 智能番茄钟 (Master Documentation)

**FocusFlow** 是一款专为追求极致专注设计的桌面番茄钟应用。它集成了模块化设计、动态视觉特效、智能背景音乐、以及全方位的数据统计与分析功能。

---

## 🚀 快速上手 (Quick Start) - 仅需 1 分钟

### 1. 环境准备
确保你的电脑已安装 **Python 3.11+**。

### 2. 安装与运行
1. **创建并激活虚拟环境**:
   ```bash
   py -3.11 -m venv .venv
   # Windows 激活:
   .venv\Scripts\activate
   ```
2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
3. **启动应用**:
   ```bash
   .venv\Scripts\python.exe main.py
   ```

---

## 💡 使用指南 (User Guide)

## 💾 本地数据与迁移

FocusFlow 只使用本机 SQLite，不会连接 PocketBase、SSH 或任何云同步服务。可变用户数据默认保存在
`%LOCALAPPDATA%\FocusFlow`：数据库、`config.json`、备份、日志和导出的 HTML 报表都在这里。首次启动会从
项目目录的旧 `data/` 与 `config.json` 复制数据；原文件不会被删除，且已经存在的本地文件不会被覆盖。

需要将数据放在 U 盘、办公室电脑专用目录或备份目录时，可在启动前设置 `FOCUSFLOW_DATA_DIR`。迁移到另一台电脑时，
复制整个数据目录即可；也可以使用应用内的 Backup 和 Merge 功能恢复或合并数据库。

### GoalSifter 连接凭据

第二阶段启用时，用户需要手动填写 SSH Host alias 与 GoalSifter Bearer token。两者仅保存
在当前 Windows 用户的 `%LOCALAPPDATA%\FocusFlow\goalsifter_settings.json` 中；首次运行会生成带稳定
`device_id` 的文件。SSH 连接只建立到 VPS 回环地址的本地端口转发；应用不会、也不得通过 SSH 读取 VPS 上的
token 文件。Token 被撤销或更换后，必须在本机该文件（后续设置界面）中显式更新。

### 第一步：设置任务 (Setup)
*   **本地任务 / GoalSifter 任务**：本地页用于离线草稿与本地分类；第二个来源只读展示远端活跃 DW，不会改写远端 KR。
*   **本地 Project 管理**：本地分类可重命名、合并或删除空分类；旧的无效分类可以收敛成更少的可维护项目。
*   **预估番茄数**：本地草稿可继续保留较大的个人预估值用于进度显示；绑定 GoalSifter DW 时仍遵守 1–4 的契约口径。
*   **声音模式**：
    - **Ticking**: 经典计时器滴答声。
    - **Music**: 随机背景音乐（自动避开上一首，保持新鲜感）。
    - **Mute**: 仅视觉提醒。

### 第二步：开启专注 (Focus)
*   **视觉特效**：进入计时后，应用会根据主题开启“黑洞粒子”或“禅意专注”特效。
*   **专注透明度**：窗口自动变为半透明（可配置），帮助你无干扰地操作背景窗口。
*   **进度追踪**：底部展示实时完成进度（如：`🍅 🍅 🍅` 表示今日完成总数）。
*   **窗口尺寸**：首页和管理页按内容自适应，不再保留大面积空白；真正置顶的是 300×400 的计时页。

### 第三步：反馈与分析 (Analysis)
*   **中断记录**：若中途放弃，请记录中断原因（内部/外部），这对于后续优化工作流程至关重要。
*   **报表生成**：点击 **[Analysis]** 生成交互式 HTML 仪表盘。新版支持时间戳命名，不会覆盖旧报告。

---

## 🛠 核心功能详解 (Core Features)

### 🍅 番茄钟核心
- **经典循环**: 支持可配置的工作时长、短休息和长休息。
- **快速启动**: 一键启动最近使用的 3 个任务。
- **进度显示**: 实时展示当前任务完成情况与每日总产出。

### 🎨 视觉与交互体验
- **动态特效**: 采用 Pygame 渲染粒子系统。计时界面移除冗余信息，专注于倒计时。
- **一键换肤**: 首页 🌗 图标切换深/浅模式。
- **返回首页**: 计时中支持一键返回，并智能处理“任务切换”类中断。

### 📊 数据分析与报告 (Plotly 驱动)
- **Summary**: 项目/任务时间分布 + 双月日历热力图。
- **Time Analysis**: 周趋势、时段分布（早/午/晚）分析。
- **Interruptions**: 细化内外部中断原因饼图。
- **Focus & Mood**: 追踪专注度评分与心情波动关系。

### 💾 数据与配置管理
- **自动备份**: 采用滚动备份策略（bak1, bak2），仅在数据实际变化时触发。
- **Smart Config History**: 智能追踪配置项的重命名（ID 级映射），确保历史数据连续性。
- **数据库合并**: 支持安全地从其他 DB 文件合并番茄记录。

---

## 🏗 开发者指南 (Developer Documentation)

### 1. 文件职责与 AI 修改备注 (Crucial for Maintenance)

| 文件 | 职责说明 | AI 修改建议 / 禁忌 |
| :--- | :--- | :--- |
| **`main.py`** | **Controller**。初始化管理器，协调各模块逻辑流程。 | 修改主流程首选。**禁止直接包含 UI 创建代码**，所有 UI 更新需调用 `self.ui`。 |
| **`ui_manager.py`** | **View**。负责所有布局、按钮创建、样式更新及 Pygame 组件嵌入。 | 调整布局、增删组件的唯一文件。按钮 `command` 需指向 `main.py` 传递的函数。 |
| **`pomodoro_data_manager.py`** | **Model**。处理 SQLite 交互、CRUD 操作及版本迁移。 | 增加字段时需提升 `LATEST_DB_VERSION` 并编写迁移 SQL。 |
| **`analysis_manager.py`** | **Analysis**。处理 Pandas 数据分析并利用 Plotly 生成 HTML。 | 增加图表时需整合至 `_create_html_dashboard`。 |
| **`sound_manager.py`** | 管理 Pygame 音频流、背景音及智能随机播放逻辑。 | 修改切歌逻辑、添加新音效模式时操作此文件。 |
| **`app_config_manager.py`** | 统一管理 `config.json` 的加载与默认值生成。 | 处理配置读写逻辑时使用。 |
| **`visual_effects.py`** | 封装 Pygame 粒子特效（BlackHole, ZenFocus）。 | 优化渲染性能或修改粒子动画时使用。 |
| **`config.py`** | 全局**基础配置**（时长、颜色、尺寸、透明度）。 | 修改 `WORK_MIN` 或 `FOCUSED_TRANSPARENCY` 时直接编辑。 |
| **`%LOCALAPPDATA%\\FocusFlow\\config.json`** | 用户**动态配置**（中断原因分类、反馈心情列表）。 | 直接编辑此 JSON 即可动态增删 UI 中的选择项。 |

### 2. 数据库结构 (Schema)

*   **`projects`**: 存储项目名称。
*   **`tasks`**: 记录任务名、预估数、状态、声音偏好。
*   **`sessions`**: 记录每次会话的起止时间、类型、时长、评分、心情及中断原因。

### 3. 开发提示
*   **添加中断原因**: 编辑 `%LOCALAPPDATA%\\FocusFlow\\config.json` 中的 `interruptions` 字典。
*   **修改 UI 颜色**: 编辑 `ctk_theme_config.py` 中的 `ThemeManager` 常量。
*   **运行测试**: 核心逻辑测试脚本位于 `tests/` 目录；调试工具位于 `tools/`。
*   **本地分类边界**: `Project` 只代表本地组织分类，GoalSifter 的 `KR` 只读展示，不应在本地管理窗口里被改写。

---

## 📅 版本历史 (Version History)

### v3.1 (Latest)
- **架构**: 目录规范化（新增 `tools/`, `tests/`），依赖库版本锁定。
- **文档**: 代码全量添加类型提示（Type Hints）与 Docstrings。
- **报表**: 分析报告文件名新增时间戳，支持多版本并存。

### v3.0
- **核心**: 引入 `ConfigHistoryManager` 解决配置重命名导致的数据断档。
- **视觉**: 统一 `ctk_theme_config.py` 管理主题；新增浅色模式“禅意”效果。
- **交互**: 修复 Home 按钮计时冲突；优化音乐不重复随机播放逻辑。

### v2.x 早期版本
- 实现模块化重构、Pygame 黑洞粒子、以及 Plotly 交互式仪表盘初始版。

---
*Stay focused, stay productive.* 🍅
