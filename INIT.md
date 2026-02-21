# AI Agent Project Initialization

本期用于快速初始化 AI Agent 开发环境的标准配置文档。

---

## 1. Project Setup (Interactive)

初始化时，请遵循以下流程与用户交互并生成配置文件。

### 1.1 Collect User Context

**Agent Instruction:**
1.  **一次性**询问用户以下三个问题：
    *   "How would you like to be addressed?" (User Name)
    *   "What is your preferred language?" (Language)
    *   "What is the full path to your Python executable? (e.g., `D:\Miniconda\python.exe`)" (Python Path)

### 1.2 Generate Configuration Files

根据用户的回答，分别生成以下两个文件。

#### A. `GEMINI.md` (Context Memory)
*Replace `{{...}}` with user inputs.*

```markdown
# Gemini Context & Instructions

## 👤 User & Safety Protocols
- **User:** {{User_Name}}
- **Language:** {{User_Language}}
- **Deletion Rules:**
  1.  **Plan:** Generate command & list files first.
  2.  **Confirm:** Ask user for permission.
  3.  **Execute:** Run only in the *next* turn.
  4.  **Method:** **Recycle Bin ONLY** via `recycle_file.ps1`.
  5.  **Script:** `powershell -ExecutionPolicy Bypass -File .\recycle_file.ps1 -FilePath "path1", "path2"` (Always use Batch/Array)
```

#### B. `AGENTS.md` (Operational Protocols)
*Replace `{{Python_Path}}` with user input.*

```markdown
# AGENTS.md

## 🤖 Context for AI Agents
**ALL** coding agents must read and strictly adhere to these instructions.

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
4.  **Cleanup:** Delete the file **only** after user confirmation of success.

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
- **Python Path:** {{Python_Path}}
- **Encoding:** Always handle files as UTF-8.
- **Style:** Adhere to project `.editorconfig` or `.prettierrc`.
```

---

## 2. Essential Utility (`recycle_file.ps1`)

创建 `recycle_file.ps1`，用于提供安全、高效的批量删除功能。

```powershell
<#
.SYNOPSIS
    Efficiently moves files to the Windows Recycle Bin using Microsoft.VisualBasic.
    Supports batch processing, pipeline input, and list files.
#>
[CmdletBinding(DefaultParameterSetName="ByPath")]
param(
    [Parameter(Mandatory=$false, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true, Position=0, ParameterSetName="ByPath")]
    [Alias("FullName", "PSPath")]
    [string[]]$FilePath,

    [Parameter(Mandatory=$false, ParameterSetName="ByList")]
    [string]$PathListFile
)

begin {
    $ErrorActionPreference = "Stop"
    $Stats = @{ Total=0; Success=0; Failed=0; Skipped=0 }
    $FailedItems = New-Object System.Collections.Generic.List[string]

    try { Add-Type -AssemblyName "Microsoft.VisualBasic" }
    catch { Write-Error "CRITICAL: Failed to load Microsoft.VisualBasic assembly."; exit 1 }

    $TargetPaths = New-Object System.Collections.Generic.List[string]
}

process {
    if ($FilePath) { foreach ($path in $FilePath) { $TargetPaths.Add($path) } }
}

end {
    if ($PathListFile -and (Test-Path $PathListFile)) {
        try { $TargetPaths.AddRange((Get-Content $PathListFile -Encoding UTF8)) }
        catch { Write-Error "Failed to read list file: $PathListFile"; exit 1 }
    }

    $UniquePaths = $TargetPaths | Select-Object -Unique
    $Stats.Total = $UniquePaths.Count

    if ($Stats.Total -eq 0) { Write-Warning "No files specified."; exit 0 }

    Write-Host "---" -ForegroundColor Cyan

    foreach ($rawPath in $UniquePaths) {
        if ([string]::IsNullOrWhiteSpace($rawPath)) { $Stats.Skipped++; continue }
        try {
            $item = Get-Item -LiteralPath $rawPath -ErrorAction SilentlyContinue
            if ($null -eq $item) { $Stats.Skipped++; continue }
            
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
                $item.FullName,
                [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin
            )
            $Stats.Success++
        }
        catch {
            $Stats.Failed++
            Write-Error "FAILED: $rawPath ($($_))"
            $FailedItems.Add($rawPath)
        }
    }

    Write-Host "\n---" -ForegroundColor Cyan
    if ($Stats.Failed -gt 0) { exit 1 } else { exit 0 }
}
```