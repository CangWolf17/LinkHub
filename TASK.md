# Task: Security Hardening — DPAPI Encryption for API Key
## 🎯 Objective
使用 Windows DPAPI (via ctypes) 对 SQLite 中的 `llm_api_key` 进行加密存储，防止明文泄露，并修复 error message leak 风险。

## 📋 Execution Plan
- [x] Step 1: 创建 TASK.md
- [x] Step 2: 创建 `backend/app/core/crypto.py` — DPAPI encrypt/decrypt via ctypes
- [x] Step 3: 修改 `llm_router.py` — 写入加密、读取解密、GET 端点无需改动
- [x] Step 4: 修复 error message leak — test-connection / chat / embed / extract 端点
- [x] Step 5: 添加启动时迁移逻辑 — 检测并重加密已有明文 key
- [x] Step 6: 验证 — 重启服务后 API key 可正常解密并使用
