# LinkHub

<p align="center">
  <strong>本地智能工作台 —— 便携软件与工作区管理中枢</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/platform-Windows-0078D6.svg" alt="Windows" />
  <img src="https://img.shields.io/badge/network-localhost%20only-critical.svg" alt="Localhost Only" />
</p>

---

## 简介

LinkHub 是一款 **仅限本机访问** 的智能文件与便携软件管理系统。它将散落在磁盘各处的绿色软件、项目工作区统一纳入管理，并通过 LLM 和语义搜索提供智能辅助能力。

后端强制绑定 `127.0.0.1:8147`，不暴露到局域网，确保安全。

## 核心功能

| 功能 | 说明 |
|------|------|
| **软件快速部署** | 拖拽上传压缩包，自动解压、启发式寻址主程序、写入数据库并生成启动卡片 |
| **批量扫描导入** | 一键扫描白名单目录，将已有便携软件和工作区目录批量导入 |
| **工作区看板** | 对本地目录添加备注、截止日期等元数据，一键在资源管理器中打开 |
| **语义搜索** | 基于 ChromaDB 向量索引，输入自然语言即可检索软件和工作区（仅 full 版） |
| **LLM 网关** | 统一的 LLM API 接入层，支持 OpenAI 兼容接口（本地 Ollama / 云端模型自由切换） |
| **LLM 调试监控** | 浮窗实时展示 LLM 请求/响应原始数据，完全透明 |
| **首次启动向导** | 首次打开时自动弹出设置向导，引导配置工作目录、LLM 和批量导入 |
| **API Key 加密** | 使用 Windows DPAPI 加密存储 API Key，不以明文落盘 |

## 快速开始（exe 版本）

### 下载

前往 [Releases](https://github.com/CangWolf17/LinkHub/releases) 下载最新版本：

| 版本 | 大小 | 说明 |
|------|------|------|
| **LinkHub-lite.exe** | ~37 MB | 精简版，不含 ChromaDB 语义搜索 |
| **LinkHub-full.zip** | ~500 MB | 完整版（ZIP 压缩包），含 ChromaDB 语义搜索 |

> 推荐先使用 **lite 版**。大部分功能（软件管理、工作区、LLM 描述生成等）均可正常使用，仅语义搜索功能不可用。

### 使用

1. **lite 版**：将 exe 放到任意目录（建议专门创建一个文件夹），双击运行
2. **full 版**：解压 ZIP 到任意目录，运行其中的 `LinkHub.exe`
3. 浏览器会自动打开 `http://127.0.0.1:8147`
4. 按照设置向导完成初始化配置

首次启动时会在 exe 所在目录自动创建：
- `data/` — 数据库文件（`linkhub.db`）
- `logs/` — 日志文件（`linkhub.log`）

> 删除 `data/` 目录可完全重置所有数据。

## 开发模式

如需从源码运行或参与开发：

### 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **操作系统** Windows（DPAPI 加密仅支持 Windows）

### 1. 克隆仓库

```bash
git clone https://github.com/CangWolf17/LinkHub.git
cd LinkHub
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

服务将运行在 `http://127.0.0.1:8147`。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173` 即可使用。

> Vite 开发服务器已配置代理，`/api` 请求自动转发至后端 `127.0.0.1:8147`。

### 构建打包

```bash
python build.py              # 打包 lite 版（不含 ChromaDB）
python build.py --full       # 打包 full 版（含 ChromaDB 语义搜索）
python build.py --all        # 同时打包两个版本
```

产物输出到 `dist/` 目录。

## 技术栈

```
前端    Vue 3 (Composition API) + TypeScript + Tailwind CSS v4 + Vue Router
后端    Python 3.10+ / FastAPI + Uvicorn（强制 127.0.0.1）
关系库  SQLite（通过 SQLAlchemy + aiosqlite 异步访问）
向量库  ChromaDB（可选，本地持久化，内置 all-MiniLM-L6-v2 embedding）
加密    Windows DPAPI（ctypes 调用 CryptProtectData/CryptUnprotectData）
打包    PyInstaller（单文件 exe，数据与程序分离）
```

## 项目结构

```
LinkHub/
├── backend/
│   ├── main.py                    # FastAPI 入口、生命周期管理、前端静态服务
│   ├── requirements.txt           # Python 依赖
│   └── app/
│       ├── core/
│       │   ├── config.py          # 配置（打包/开发模式路径检测）
│       │   ├── crypto.py          # DPAPI 加解密
│       │   ├── database.py        # SQLAlchemy 异步引擎
│       │   ├── vector_store.py    # ChromaDB 客户端（可选）
│       │   └── log_buffer.py      # 日志缓冲 & WebSocket 广播
│       ├── models/
│       │   └── models.py          # ORM 模型（Software / Workspace / SystemSetting）
│       ├── routers/
│       │   ├── system_router.py   # 初始化状态检测、白名单目录管理
│       │   ├── os_router.py       # 启动程序、打开目录
│       │   ├── metadata_router.py # 软件 & 工作区 CRUD + 批量扫描导入
│       │   ├── llm_router.py      # LLM 配置、对话、Embedding
│       │   ├── installer_router.py# 压缩包上传安装 + 批量扫描导入
│       │   └── search_router.py   # 语义搜索、索引统计、重建索引
│       └── schemas/               # Pydantic 请求/响应模型
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts             # Vite 配置（代理 /api → 后端）
│   └── src/
│       ├── api/                   # Axios HTTP 封装 + 全部 API 函数
│       ├── components/            # SetupWizard / SearchBar / SoftwareCard 等
│       ├── composables/           # useLlmMonitor 组合式函数
│       ├── layouts/               # AppLayout（侧边栏 + 顶栏 + 向导挂载）
│       ├── views/                 # SoftwareView / WorkspaceView / SettingsView
│       └── router/                # Vue Router 路由定义
│
├── build.py                       # PyInstaller 打包脚本（lite / full）
└── README.md
```

## 首次使用

启动后首次访问页面会自动弹出 **设置向导**：

1. **配置工作目录** — 设置白名单目录（LinkHub 只在这些目录中扫描管理）
2. **配置 LLM** — 填写 API Base URL、API Key 和模型名称（可跳过）
3. **批量导入** — 一键扫描已有的便携软件和工作区目录

之后可随时在 **设置页** 修改白名单目录、LLM 配置，或重新触发扫描导入。

## API 概览

所有 API 前缀为 `/api`，后端启动后可访问 `http://127.0.0.1:8147/docs` 查看完整的 Swagger 文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `GET` | `/system/init-status` | 系统初始化状态 |
| `GET/PUT` | `/system/allowed-dirs` | 白名单目录读写 |
| `POST` | `/system/shutdown` | 关闭服务 |
| `GET/POST` | `/metadata/software` | 软件列表 / 创建 |
| `GET/PUT/DELETE` | `/metadata/software/:id` | 软件详情 / 更新 / 删除 |
| `GET/POST` | `/metadata/workspaces` | 工作区列表 / 创建 |
| `POST` | `/metadata/workspaces/scan` | 批量扫描导入工作区 |
| `GET/PUT` | `/llm/config` | LLM 配置读写 |
| `POST` | `/llm/test-connection` | LLM 连接测试 |
| `POST` | `/installer/upload` | 上传压缩包安装软件 |
| `POST` | `/installer/scan-dirs` | 批量扫描导入软件 |
| `POST` | `/search` | 语义搜索（仅 full 版） |
| `POST` | `/search/reindex` | 重建向量索引（仅 full 版） |
| `POST` | `/os/launch` | 启动程序 |
| `POST` | `/os/open-dir` | 打开目录 |

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
