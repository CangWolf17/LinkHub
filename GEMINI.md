# Gemini Context & Instructions

## 👤 User & Safety Protocols
- **User:** Tim
- **Language:** Chinese
- **Deletion Rules:**
  1.  **Plan:** Generate command & list files first.
  2.  **Confirm:** Ask user for permission.
  3.  **Execute:** Run only in the *next* turn.
  4.  **Method:** **Recycle Bin ONLY** via `recycle_file.ps1`.
  5.  **Script:** `powershell -ExecutionPolicy Bypass -File .\recycle_file.ps1 -FilePath "path1", "path2"` (Always use Batch/Array)
