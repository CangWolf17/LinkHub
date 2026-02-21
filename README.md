# LinkHub

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **LinkHub** is an AI-Agent driven software project. This repository contains the core application logic and agent protocols for rapid, safe iteration.

## 📖 Table of Contents

- [About The Project](#about-the-project)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
- [AI Agent Protocols](#ai-agent-protocols)
- [Contributing](#contributing)

## 🌟 About The Project

*(Please edit `main.md` to define the detailed Product Requirements and features of LinkHub. The AI agent will read `main.md` to understand what to build next.)*

**Key Features:**
- [x] AI-Agent Integrated Workflow
- [x] Strict safety file deletion rules
- [ ] Core Business Logic (TBD)
- [ ] API Endpoints (TBD)
- [ ] Frontend Interface (TBD)

## 🏗️ Project Architecture

*(TBD based on `main.md` requirements)*
- **Runtime:** Node.js / Python
- **Frameworks:** [To be determined]
- **Database:** [To be determined]

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+) (Path configured in `AGENTS.md`)
- PowerShell (For running `recycle_file.ps1`)

### Installation
1. Clone the repo
   ```sh
   git clone https://github.com/your-username/LinkHub.git
   ```
2. Install dependencies (Once stack is decided)
   ```sh
   # npm install
   # or
   # pip install -r requirements.txt
   ```

## 🤖 AI Agent Protocols

This project is configured for optimal AI agent collaboration. **ALL agents MUST read `AGENTS.md` before making any changes.**

1. **Safety First:** Deletions are sent to the Recycle Bin via `recycle_file.ps1`.
2. **Context Driven:** The agent reads `GEMINI.md` for user context.
3. **Complex Tasks:** Multi-step operations are tracked in `TASK.md`.

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
