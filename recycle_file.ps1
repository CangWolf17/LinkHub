<#
.SYNOPSIS
    Efficiently moves files to the Windows Recycle Bin using Microsoft.VisualBasic.
    (v2.0 - Robust Error Handling & Reporting)

.DESCRIPTION
    This script utilizes the .NET [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile method
    to move files to the Recycle Bin.
    
    Improvements in v2.0:
    - Error Accumulation: Tracks successes and failures.
    - Final Report: Displays a summary at the end of execution.
    - Exit Codes: Returns exit code 1 if any file failed to recycle.
    - Pipeline Support: Fully supports piping objects or strings.

.PARAMETER FilePath
    One or more paths to files to recycle. Supports pipeline input.

.PARAMETER PathListFile
    A path to a text file containing a list of files to recycle.

#>
[CmdletBinding(DefaultParameterSetName="ByPath")]
param(
    [Parameter(Mandatory=$false, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true, Position=0, ParameterSetName="ByPath")]
    [Alias("FullName", "PSPath")]
    [string[]]$FilePath,

    [Parameter(Mandatory=$false, ValueFromRemainingArguments=$true, ParameterSetName="ByPath")]
    [string[]]$RemainingPaths,

    [Parameter(Mandatory=$false, ParameterSetName="ByList")]
    [string]$PathListFile
)

begin {
    $ErrorActionPreference = "Continue" # Changed to Continue to handle multiple files better
    
    # Track statistics
    $Stats = @{
        Total = 0
        Success = 0
        Failed = 0
        Skipped = 0
    }
    $FailedItems = New-Object System.Collections.Generic.List[string]

    try {
        Add-Type -AssemblyName "Microsoft.VisualBasic"
    }
    catch {
        Write-Error "CRITICAL: Failed to load Microsoft.VisualBasic assembly."
        exit 1
    }

    $TargetPaths = New-Object System.Collections.Generic.List[string]
}

process {
    # Collect all paths from both explicit and remaining arguments
    if ($FilePath) { $FilePath | ForEach-Object { $TargetPaths.Add($_) } }
    if ($RemainingPaths) { $RemainingPaths | ForEach-Object { $TargetPaths.Add($_) } }
}

end {
    # Handle List File
    if ($PathListFile) {
        if (Test-Path $PathListFile) {
            try {
                $fileContent = Get-Content $PathListFile -Encoding UTF8
                $TargetPaths.AddRange($fileContent)
            }
            catch {
                Write-Error "Failed to read list file: $PathListFile"
            }
        }
    }

    # Deduplicate and resolve wildcards
    $ResolvedPaths = New-Object System.Collections.Generic.List[string]
    foreach ($path in ($TargetPaths | Select-Object -Unique)) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        
        # Support wildcards
        try {
            $items = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
            if ($null -eq $items) {
                # Try with wildcard support if literal fails
                $items = Get-Item -Path $path -ErrorAction SilentlyContinue
            }

            if ($items) {
                $items | ForEach-Object { $ResolvedPaths.Add($_.FullName) }
            } else {
                Write-Warning "File or pattern not found: $path"
                $Stats.Skipped++
            }
        } catch {
            Write-Warning "Error resolving path: $path"
            $Stats.Skipped++
        }
    }

    $UniqueResolved = $ResolvedPaths | Select-Object -Unique
    $Stats.Total = $UniqueResolved.Count

    if ($Stats.Total -eq 0 -and $Stats.Skipped -eq 0) {
        Write-Warning "No valid files specified for deletion."
        exit 0
    }

    Write-Host "`n--- Starting Recycle Operation ($($Stats.Total) files) ---" -ForegroundColor Cyan

    foreach ($fullPath in $UniqueResolved) {
        try {
            if (Test-Path $fullPath) {
                [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
                    $fullPath,
                    [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                    [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin
                )
                $Stats.Success++
                Write-Host " [OK] " -NoNewline -ForegroundColor Green
                Write-Host "Recycled: $fullPath"
            }
        }
        catch {
            $Stats.Failed++
            Write-Error "FAILED: $fullPath ($($_))"
            $FailedItems.Add($fullPath)
        }
    }

    # Final Summary
    Write-Host "`n--- Operation Summary ---" -ForegroundColor Cyan
    Write-Host "Total   : $($Stats.Total)"
    Write-Host "Success : $($Stats.Success)" -ForegroundColor Green
    Write-Host "Skipped : $($Stats.Skipped)" -ForegroundColor Yellow
    
    if ($Stats.Failed -gt 0) {
        Write-Host "Failed  : $($Stats.Failed)" -ForegroundColor Red
        $FailedItems | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
        exit 1
    } else {
        Write-Host "Status  : All Operations Completed Successfully" -ForegroundColor Green
        exit 0
    }
}