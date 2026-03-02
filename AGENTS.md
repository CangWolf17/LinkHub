# AGENTS.md

## 🤖 Context for AI Agents
**ALL** coding agents must read and strictly adhere to these instructions.

## 👤 User Preferences
- **User:** Tim
- **Language:** Chinese

## 🛡️ Critical Deletion Protocol
**ALL** file deletion operations must strictly follow this workflow:
1.  **Generate Command:** Create the deletion command using the project's dedicated recycle script but **DO NOT** execute it.
    *   **Tool:** `.\recycle_file.ps1`
    *   **Batching Strategy:** **ALWAYS** pass multiple files in a single command. **DO NOT** run the script inside a loop.
    *   **Syntax:** `powershell -ExecutionPolicy Bypass -File .\recycle_file.ps1 -FilePath "path1", "path2"`
    *   **List Input:** `powershell -ExecutionPolicy Bypass -File .\recycle_file.ps1 -PathListFile "list.txt"`
2.  **List Files:** Explicitly list every file that will be affected.
3.  **Request Confirmation:** Present the list and command to the user.
4.  **Execute Later:** Only execute in the **next** turn after confirmation.
5.  **Verify Result:** Check Exit Code (`0` = Success, `1` = Failure).

## 🧩 Complex Task Protocol (TASK.md)
For tasks involving **>3 steps** or modifying **multiple files**, agents **MUST**:
1.  **Initialize:** Create `TASK.md` in the root with a clear plan.
2.  **Track:** Update the file (`- [x]`) after completing each atomic step.
3.  **Focus:** Read `TASK.md` at the start of every turn to maintain context.
4.  **Cleanup:** Once all steps are marked `[x]`, immediately run the cleanup script **without asking for confirmation**:
    ```powershell
    powershell -ExecutionPolicy Bypass -Command "& '.\recycle_file.ps1' -FilePath 'TASK.md'"
    ```
    Verify exit code is `0`.

**Template:**
```markdown
# Task: {Task Name}
## 🎯 Objective
{One sentence goal}

## 📋 Execution Plan
- [ ] Step 1: {Description}
- [ ] Step 2: {Description}
```

## 🛠 Tech Stack & Style
- **Runtime:** Node.js / Python
- **Python Path:** D:\Miniconda\python.exe
- **Encoding:** Always handle files as UTF-8.
- **Style:** Adhere to project `.editorconfig` or `.prettierrc`.
