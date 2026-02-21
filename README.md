# Local Smart Dashboard (LinkHub)

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **Local Smart Dashboard** (formerly LinkHub) is an AI-Agent driven software project designed as a **Localhost-Only** intelligent file and portable software management system. 

## 📖 Table of Contents

- [About The Project](#about-the-project)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
- [AI Agent Protocols](#ai-agent-protocols)
- [Contributing](#contributing)

## 🌟 About The Project

This application acts as a central hub on your local machine to manage portable software and workspaces securely and intelligently.

**Core Features:**
- **Software Quick Deployment:** Drag and drop archives for instant portable software deployment, extraction, database entry, and launch card generation.
- **Workspace Kanban:** Metadata tagging (notes, deadlines) for local directories with one-click OS Explorer launch.
- **Independent LLM Infrastructure:** Universal local API gateway for LLM capabilities, supporting dynamic toggling between Local (e.g., Ollama) and Cloud models.
- **🔥 LLM Debug Monitor:** A floating UI panel intercepting and displaying raw LLM input/output for complete transparency.

## 🏗️ Project Architecture

Strictly designed as a logically decoupled physical monolith for security and ease of deployment. 

- **Frontend:** Vue 3 (Composition API) + Tailwind CSS + Virtual Scrolling.
- **Backend:** Python 3.10+ + FastAPI + Uvicorn (Forced to `127.0.0.1`).
- **Relational DB:** SQLite3 (WAL mode enabled `PRAGMA journal_mode=WAL;`).
- **Vector DB:** ChromaDB (Local persistent mode).
- **Security:** Strict directory whitelists to prevent path traversal; background process launching (`subprocess.DETACHED_PROCESS` on Windows).

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+) (Path configured in `AGENTS.md`)
- PowerShell (For running `recycle_file.ps1`)

### Installation (WIP)
1. Clone the repo
   ```sh
   git clone https://github.com/CangWolf17/LinkHub.git
   ```
2. Setup Backend
   ```sh
   # pip install -r backend/requirements.txt
   # uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. Setup Frontend
   ```sh
   # cd frontend
   # npm install
   # npm run dev
   ```

## 🤖 AI Agent Protocols

This project is configured for optimal AI agent collaboration. **ALL agents MUST read `AGENTS.md` before making any changes.**

1. **Safety First:** Deletions are sent to the Recycle Bin via `recycle_file.ps1`.
2. **Context Driven:** The agent reads `main.md` for Product Requirements.
3. **Complex Tasks:** Multi-step operations are tracked in `TASK.md`.

## 📜 License

Distributed under the MIT License.
