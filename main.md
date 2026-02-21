------

# 🤖 Agent 开发指令：本地智能工作区与软件控制台 (Local Smart Dashboard)

## 1. 项目概述 (Project Context)

**总目标：** 开发一套**仅供本机浏览器访问 (Localhost Only)** 的智能文件与便携软件管理系统。

**核心解决痛点：**

1. **软件极速部署与启动：** 支持拖拽压缩包，一键完成便携软件的“解压-建档-入库-生成启动卡”，并通过 Web 界面极速检索与拉起。

2. **工作区智能看板：** 为本地文档目录添加元数据（备注、截止日期），实现看板式管理和一键打开本地系统资源管理器。

3. **独立的 LLM 基础设施与可视化：** 将大模型能力抽离为通用的本地 API 网关。支持动态配置（本地/云端模型切换），并在前端提供实时监控 LLM 原始输出的悬浮窗，确保 AI 行为完全可控。

   **架构与安全原则：** * **安全第一：** 绝不对局域网暴露端口，后端服务强制绑定 `127.0.0.1`；严格控制系统底层调用权限防范越界。

- **逻辑解耦，物理单体：** 后端采用 Python FastAPI，各模块在代码层级（Router）绝对解耦，但统一在同一个 `main.py` 进程中运行，降低本地部署与维护成本。

------

## 2. 核心技术栈与环境配置 (Tech Stack & Config)

- **前端 (Frontend):** Vue 3 (Composition API) + Tailwind CSS + 虚拟滚动 (Virtual Scrolling 应对海量卡片)。
- **后端 (Backend):** Python 3.10+ + FastAPI + Uvicorn (启动参数必须包含 `--host 127.0.0.1`)。
- **关系型数据库 (Relational DB):** SQLite3。**强制要求：** 在建立数据库连接时必须开启 WAL 模式以解决并发读写锁问题 (`PRAGMA journal_mode=WAL;`)。
- **向量数据库 (Vector DB):** ChromaDB (配置为本地持久化模式)。
- **文件处理 (File Handling):** Python 内置 `zipfile`, `rarfile` (可选), `shutil`。

------

## 3. 数据库结构设计 (Database Schema)

使用 SQLite 存储业务与配置数据，需包含以下三张核心表：

1. **`portable_software` (便携软件表):** * `id` (PK, UUID), `name` (名称), `executable_path` (启动绝对路径), `description` (LLM生成的用途描述), `tags` (标签)。
2. **`workspaces` (工作区表):** * `id` (PK, UUID), `name` (项目名称), `directory_path` (目录绝对路径), `description` (备注摘要), `deadline` (截止日期), `status` (状态)。
3. **`system_settings` (动态配置表 - 核心):** * 采用 Key-Value 结构：`key` (PK, String), `value` (String)。
   - 预设 Keys：`llm_base_url` (API地址), `llm_api_key` (密钥), `model_chat` (对话模型名称), `model_embedding` (向量模型名称)。

------

## 4. 核心后端模块规范 (Backend Modules Specification)

请创建独立的 Python Router 文件来实现以下模块，确保它们互不依赖业务逻辑。

### 模块 A: 操作系统安全桥接 (OS Bridge Router) - ⚠️ 高危模块

- **职责：** 封装系统底层的“唤醒”与“打开”操作。
- **安全红线 (防范路径遍历)：** 必须设置**基础白名单目录**（例如 `D:\PortableApps`, `E:\Workspaces`），拒绝执行任何不在白名单路径下或包含 `../` 的请求。
- **非阻塞执行 (防范后端卡死)：** 使用 `subprocess.Popen` 分离进程拉起程序（Windows 环境下必须使用 `creationflags=subprocess.DETACHED_PROCESS`），确保 API 立即返回 `200 OK`，绝不能阻塞后端主线程。
- **核心 API：**
  - `POST /api/os/launch` -> *Payload:* `{"target_path": "绝对路径"}`。执行前需校验后缀是否为合法的可执行文件。
  - `POST /api/os/open-dir` -> *Payload:* `{"target_path": "绝对路径"}`。调用系统资源管理器打开目录。

### 模块 B: 元数据与死链管理 (Metadata CRUD Router)

- **职责：** 处理 SQLite 业务数据的增删改查。
- **防僵尸数据 (Dead-link Check)：** 在返回 `GET` 列表数据前，必须对数据库中的路径执行轻量级的 `os.path.exists()` 校验。如果本地路径已丢失，需在返回的 JSON 对象中附加标记 `is_missing: true`。

### 模块 C: 通用大模型网关 (Universal LLM Gateway)

- **职责：** 纯粹的文本处理基建服务，动态加载 `system_settings` 中的配置，实例化对应的 OpenAI Client 或 LangChain 对象。实现任务级路由（如 Chat 走云端大模型，Embedding 走本地 Ollama 模型）。
- **数据透传要求：** API 返回结构必须包含 `raw_response` 字段，保留 LLM 返回的原始 JSON 或文本，供前端拦截调试。
- **核心 API：**
  - `POST /api/llm/chat` -> 标准多轮对话。
  - `POST /api/llm/embed` -> 文本转向量接口。
  - `POST /api/llm/extract` -> 结构化信息提取接口。

### 模块 D: 自动化安装中枢 (Auto-Installer Router)

- **职责：** 处理前端拖拽上传的压缩包，实现“解压即部署”。
- **工作流 (Pipeline)：**
  1. 接收文件 (`POST /api/installer/upload`)。
  2. 在设定的软件白名单目录下创建专属文件夹并完成解压。
  3. **启发式寻址：** 扫描解压目录，通过文件大小、名称关键字等规则，寻找核心的可执行文件 (`.exe`)。
  4. 调用 **模块 C** 根据软件名生成初步的描述。
  5. 调用 **模块 B** 将信息写入数据库。
  6. 返回前端安装成功状态及提取到的数据。

------

## 5. 前端交互核心需求 (Frontend UI/UX)

- **全局布局：** 顶部为支持自然语言的全局语义搜索栏；左侧为功能导航栏（包含：软件舱、工作区、设置）；右下角为悬浮窗。
- **LLM 动态配置面板 (Settings View)：**
  - 提供可视化表单管理大模型配置（API Key, Base URL, Chat 模型, Embedding 模型）。
  - 包含【🧪 测试连接】按钮，一键验证 LLM 网关连通性。全局顶部提供当前模型运行状态的微型 Badge 徽标。
- **拖拽安装区 (Dropzone)：** 在“便携软件舱”视图中提供显著的拖拽区域。拖入压缩包后展示进度条（上传 -> 解压 -> 分析 -> 完成），完成后自动无刷新新增一张软件卡片。
- **工作区看板 (Workspace Kanban)：** 采用卡片化布局展示项目文件夹。
  - **视觉警报：** 提取 `deadline` 字段，临近 3 天标橙，超期标红。
  - **死链处理：** 针对被标记为 `is_missing: true` 的卡片予以置灰提示，并提供一键【清理死链】按钮。
  - 提供【📂 打开目录】快捷按钮，直接请求模块 A。
- **🔥 LLM 神经监控悬浮窗 (LLM Debug Monitor)：** 页面右下角或侧边栏提供一个可折叠的半透明控制台。前端拦截并实时打印所有涉及模块 C（大模型网关）的 API 请求和响应。必须显示“User Prompt”以及后端的“LLM Raw Output”。

------

## 6. Agent 开发执行步骤 (Execution Plan)

> **Agent 提示：** 请严格按照以下阶段开发，确保每个阶段均可通过代码测试后再进行下一步。所有服务必须绑定在 `127.0.0.1`。

- **Phase 1: 核心底层跑通 (基础环境 & 模块 A)**
  - 搭建 FastAPI 基础结构，配置 SQLite 数据库与 ORM 模型 (`portable_software`, `workspaces`, `system_settings`)。
  - 实现 `os_router.py`，重点完成白名单校验和非阻塞拉起进程的代码，确保能安全唤醒本地程序。
- **Phase 2: 大模型基建与业务逻辑 (模块 B & C)**
  - 实现 `llm_router.py`，确保能动态读取数据库配置并成功调用大模型。
  - 实现 CRUD 接口与死链检测逻辑。
- **Phase 3: 自动化链条与语义搜索 (模块 D & ChromaDB)**
  - 实现 `installer_router.py`，编写文件解压和启发式寻找核心执行文件的自动化逻辑。
  - 接入 ChromaDB，实现“入库转向量”和“基于自然语言查向量”的搜索闭环。
- **Phase 4: Vue3 前端构建**
  - 优先实现 **LLM 动态配置面板** 和 **LLM Debug 悬浮窗** 以辅助后续全链路联调。
  - 开发拖拽上传组件、工作区看板和全局搜索 UI，完成前后端全面对接。

