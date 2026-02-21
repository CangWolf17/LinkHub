# Task: Phase 1 - 核心底层跑通 (基础环境 & 模块 A)
## 🎯 Objective
搭建后端 FastAPI 基础结构、SQLite 数据库 (开启 WAL 模式)，并实现安全的操作系统底层拉起模块 (OS Bridge)。

## 📋 Execution Plan
- [ ] Step 1: Initialize project directory structure (`backend/` & `frontend/`).
- [ ] Step 2: Setup Python virtual environment or configure dependencies (`requirements.txt` for FastAPI, Uvicorn, SQLAlchemy).
- [ ] Step 3: Implement SQLite Database Config & ORM Models (`portable_software`, `workspaces`, `system_settings`), ensuring `PRAGMA journal_mode=WAL;`.
- [ ] Step 4: Implement Module A (`os_router.py`) with strict path whitelisting and non-blocking detached process launching (`creationflags=subprocess.DETACHED_PROCESS`).
- [ ] Step 5: Test and verify Module A endpoints (`/api/os/launch`, `/api/os/open-dir`).