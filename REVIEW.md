# 代码审查报告（LinkHub）

## 结论概览
- 代码结构清晰，模块边界明确（OS Bridge / Metadata / Installer / LLM / Search）。
- 安全基线整体良好，但仍存在少量安全面可收紧。
- 自动化测试脚本完善，已在本机服务运行时完成全量 Phase 测试并全部通过。

## New Feature
- 本地文件夹导入软件：支持从本地目录直接导入便携软件并建立索引。
  - 相关位置：`backend/app/routers/installer_router.py`、`backend/app/schemas/installer_schemas.py`、`frontend/src/views/SoftwareView.vue`、`frontend/src/api/index.ts`
- 关闭服务令牌保护：增加 shutdown token 机制，避免误触或非授权关闭。
  - 相关位置：`backend/app/core/config.py`、`backend/app/routers/system_router.py`、`frontend/src/views/SettingsView.vue`

## Bug Fix
- Archive path traversal hardening for 7z: validate member paths before extraction (parity with zip/tar).
  - 相关位置：`backend/app/routers/installer_router.py`
- Restrict browse-dir to allowed roots when whitelist exists (prevents arbitrary directory enumeration).
  - 相关位置：`backend/app/routers/os_router.py`
- Test scripts now respect existing LLM configuration and accept 200/502 when LLM is configured.
  - 相关位置：`backend/test_phase2.py`
- Semantic search test no longer assumes empty workspaces in real data.
  - 相关位置：`backend/test_phase3.py`
- Unified DB transaction strategy: removed auto-commit from `get_db` dependency layer; all write routes now use explicit `await db.commit()` to prevent race conditions between requests.
  - 相关位置：`backend/app/core/database.py`, all routers
- Added `llm_dir_context_enabled` system setting toggle (default: true); when disabled, directory context (README/config files) is not sent to LLM, preventing unintended sensitive data exposure.
  - 相关位置：`backend/app/routers/metadata_router.py`, `backend/app/routers/llm_router.py`, `backend/app/schemas/llm_schemas.py`
- Replaced one-shot `await file.read()` with 1 MB chunked streaming write for upload endpoint; added 512 MB hard limit returning HTTP 413 on overflow.
  - 相关位置：`backend/app/routers/installer_router.py`

## 主要风险与改进建议（按优先级）
~~1) **中优先级：LLM 目录上下文可能包含敏感信息**~~（已修复：新增 `llm_dir_context_enabled` 开关）

~~2) **中优先级：数据库事务策略不统一**~~（已修复：统一为路由显式 commit，`get_db` 仅负责异常 rollback）

~~3) **低优先级：上传大文件内存风险**~~（已修复：改为 1MB 分块流式写入，512MB 上限）
- Restrict browse-dir to allowed roots when whitelist exists (prevents arbitrary directory enumeration).
  - 相关位置：`backend/app/routers/os_router.py`
- Test scripts now respect existing LLM configuration and accept 200/502 when LLM is configured.
  - 相关位置：`backend/test_phase2.py`
- Semantic search test no longer assumes empty workspaces in real data.
  - 相关位置：`backend/test_phase3.py`

## 主要风险与改进建议（按优先级）
1) **中优先级：LLM 目录上下文可能包含敏感信息**
   - 生成描述时读取 README/配置等文件并发送给 LLM。
   - 建议：对目录范围做白名单限制、增加“禁止上传目录内容”开关、限制最大读取字节数。
   - 相关位置：`backend/app/routers/metadata_router.py`
2) **中优先级：数据库事务策略不统一**
   - `get_db` 依赖注入层自动 commit，而路由中也存在显式 commit。
   - 建议：统一为“路由显式 commit”或“依赖层统一 commit”，避免重复提交/掩盖错误。
   - 相关位置：`backend/app/core/database.py`
3) **低优先级：上传大文件内存风险**
   - 上传使用 `await file.read()` 一次性读入内存。
   - 建议：改为流式写入或限制上传大小。
   - 相关位置：`backend/app/routers/installer_router.py`

## 测试结果
已在服务运行状态下执行：
- `D:\Miniconda\python.exe backend/test_phase1.py`：9/9 通过 ✅
- `D:\Miniconda\python.exe backend/test_phase2.py`：23/23 通过 ✅
- `D:\Miniconda\python.exe backend/test_phase3.py`：16/16 通过 ✅

## 额外建议（可选）
- 前端拖拽文件夹体验可加引导提示/按钮，减少误解。
- LLM 监控记录请求体建议脱敏或增加开关。
- 语义搜索结果的 `Path.exists()` 可考虑延迟或分批，降低 I/O 峰值。
