# LinkHub

<p align="center">
  <strong>现代化本地软件与工作区管理仪表盘</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Tailwind-CSS%20v4-38B2AC?logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/SQLite-Async-003B57?logo=sqlite&logoColor=white" alt="SQLite" />
</p>

---

⚠️ **重要声明：本项目为个人自用工具，旨在解决作者在 Windows 环境下管理大量绿色便携软件和开发工作区的痛点。**

🧠 **AI 辅助编写声明：** 本项目的**全部代码（100%）**均由 AI 自动生成或辅助编写完成，作者仅负责架构设计和需求引导。特别感谢以下 AI 模型：
* **Claude Opus 4.6 / Sonnet 4.6**
* **Gemini 3 Flash**
* **Gemini 3.1 Pro**

---

## 🚀 核心功能

LinkHub 是一个只在 `localhost` 运行的本地 Web 服务，致力于将散落在磁盘各处的便携软件和项目代码统一纳入优雅的仪表盘中。

### 📦 便携软件管理
- **一键导入与启动**：扫描指定的白名单目录，一键将本地所有的绿色软件收录进库。
- **自动图标提取**：后端自动解析 `.exe` 文件并提取高清图标，无需手动寻找和上传。
- **右键菜单集成**：支持直接在卡片上右键打开所在文件夹、快速启动或删除。
- **权限自动提升**：启动需要管理员权限的软件时，自动触发 Windows UAC 提权。

### 📁 智能工作区
- **项目状态追踪**：对本地目录添加备注、截止日期等元数据，根据时间自动分为“进行中”、“已过期”、“已归档”。
- **文件系统深度集成**：支持浏览内嵌目录树，自动识别 `Junction`、`Symlink` 和 `.lnk` 快捷方式，并支持右键快捷定位源路径。

### 🤖 AI 赋能 (LLM 集成)
- **语义搜索 (Full 版)**：集成 ChromaDB 向量数据库，支持通过自然语言模糊搜索本地软件和工作区。
- **智能元数据填充**：接入大模型（支持本地 Ollama 或云端 API），一键生成准确的描述和标签。
- **批量清洗与生成**：支持多选卡片进行批量的 AI 信息生成，并在后台静默完成。
- **LLM 实时监控**：内置浮窗调试器，可随时查看底层请求和响应原始数据。

## ⚙️ 技术栈

* **前端**：Vue 3 (Composition API) + TypeScript + Vite + Tailwind CSS v4 + Lucide Icons。
* **后端**：Python 3.10+ + FastAPI + Uvicorn + SQLAlchemy (异步 SQLite)。
* **向量库**：ChromaDB (仅 Full 版包含，用于本地向量索引和语义搜索)。
* **系统交互**：纯 Python 深度调用 Windows Win32 API。

## 📦 下载与使用

您可以直接在 [Releases](https://github.com/CangWolf17/LinkHub/releases) 下载自动构建的可执行版本：

| 版本 | 说明 |
| :--- | :--- |
| **LinkHub-lite.exe** | 精简版，约 40MB。包含除语义搜索外的所有核心功能。 |
| **LinkHub-full.zip** | 完整版，约 500MB。包含 ChromaDB 向量数据库，支持语义搜索。 |

> **使用方法**：解压后双击运行 `LinkHub.exe`。程序会在同级目录创建 `data/` 文件夹用于存放数据库和配置。

## 📝 开发者指南

如需自行构建或进行二次开发：

### 1. 构建脚本
项目根目录下提供了 `build.py` 用于快速打包可执行文件：
```bash
python build.py              # 构建 Lite 版
python build.py --full       # 构建 Full 版
python build.py --all        # 同时构建两个版本
```

### 2. 源码运行
* **后端**: 在 `backend` 目录下运行 `pip install -r requirements.txt` 后执行 `python main.py`。
* **前端**: 在 `frontend` 目录下运行 `npm install` 后执行 `npm run dev`。

---
*License: MIT*