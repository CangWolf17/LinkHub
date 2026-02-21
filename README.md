# LinkHub

<p align="center">
  <strong>本地智能工作台 —— 便携软件与工作区管理中枢</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg" alt="Python" />
  <img src="https://img.shields.io/badge/node-18%2B-339933.svg" alt="Node.js" />
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
| **语义搜索** | 基于 ChromaDB 向量索引，输入自然语言即可检索软件和工作区 |
| **LLM 网关** | 统一的 LLM API 接入层，支持 OpenAI 兼容接口（本地 Ollama / 云端模型自由切换） |
| **LLM 调试监控** | 浮窗实时展示 LLM 请求/响应原始数据，完全透明 |
| **首次启动向导** | 首次打开时自动弹出设置向导，引导配置工作目录、LLM 和批量导入 |
| **API Key 加密** | 使用 Windows DPAPI 加密存储 API Key，不以明文落盘 |

## 技术栈

```
前端    Vue 3 (Composition API) + TypeScript + Tailwind CSS v4 + Vue Router
后端    Python 3.10+ / FastAPI + Uvicorn（强制 127.0.0.1）
关系库  SQLite（通过 SQLAlchemy + aiosqlite 异步访问）
向量库  ChromaDB（本地持久化，内置 all-MiniLM-L6-v2 embedding）
加密    Windows DPAPI（ctypes 调用 CryptProtectData/CryptUnprotectData）
```

## 项目结构

```
LinkHub/
├── backend/
│   ├── main.py                    # FastAPI 入口、生命周期管理
│   ├── requirements.txt           # Python 依赖
│   └── app/
│       ├── core/
│       │   ├── config.py          # 静态配置（端口、默认目录、后缀白名单）
│       │   ├── crypto.py          # DPAPI 加解密
│       │   ├── database.py        # SQLAlchemy 异步引擎
│       │   └── vector_store.py    # ChromaDB 客户端
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
└── README.md
```

## 快速部署

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

### 4. 生产构建（可选）

```bash
cd frontend
npm run build
```

构建产物输出到 `frontend/dist/`，可使用任意静态文件服务器托管，配合后端使用。

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
| `GET/POST` | `/metadata/software` | 软件列表 / 创建 |
| `GET/PUT/DELETE` | `/metadata/software/:id` | 软件详情 / 更新 / 删除 |
| `GET/POST` | `/metadata/workspaces` | 工作区列表 / 创建 |
| `POST` | `/metadata/workspaces/scan` | 批量扫描导入工作区 |
| `GET/PUT` | `/llm/config` | LLM 配置读写 |
| `POST` | `/llm/test-connection` | LLM 连接测试 |
| `POST` | `/installer/upload` | 上传压缩包安装软件 |
| `POST` | `/installer/scan-dirs` | 批量扫描导入软件 |
| `POST` | `/search` | 语义搜索 |
| `POST` | `/search/reindex` | 重建向量索引 |
| `POST` | `/os/launch` | 启动程序 |
| `POST` | `/os/open-dir` | 打开目录 |

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
