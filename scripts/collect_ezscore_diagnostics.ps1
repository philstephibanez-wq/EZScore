$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Repo "data\logs\EZScore_Diagnostics_$Stamp.zip"
$Tmp = Join-Path $env:TEMP "EZScore_Diagnostics_$Stamp"

New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

$Logs = Join-Path $Repo "data\logs"
if (Test-Path $Logs) {
    Copy-Item (Join-Path $Logs "*.log") $Tmp -ErrorAction SilentlyContinue
}

git -C $Repo status | Out-File (Join-Path $Tmp "git-status.txt") -Encoding utf8
git -C $Repo log -1 --oneline | Out-File (Join-Path $Tmp "git-head.txt") -Encoding utf8

Get-ChildItem (Join-Path $Repo "data\analysis") -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in ".json", ".txt", ".log" } |
    Select-Object FullName,Length,LastWriteTime |
    Format-Table -AutoSize |
    Out-String |
    Out-File (Join-Path $Tmp "analysis-files.txt") -Encoding utf8

Compress-Archive -Path (Join-Path $Tmp "*") -DestinationPath $Out -Force
Remove-Item $Tmp -Recurse -Force

Write-Host "Diagnostic cree : $Out"
