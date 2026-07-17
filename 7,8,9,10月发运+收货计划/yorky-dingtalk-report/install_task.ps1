# 以当前用户身份注册每日 10:00 运行的计划任务
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$bat = Join-Path $here "run_daily.bat"
$taskName = "YorkyDingTalkReport"

# 若已存在先删除
$existing = schtasks /Query /TN $taskName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "任务已存在，先删除旧任务..."
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /TR "`"$bat`"" /SC DAILY /ST 10:00 /F | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "已注册任务 $taskName，每日 10:00 运行："
    Write-Host "  $bat"
    Write-Host "查看: schtasks /Query /TN $taskName /V /FO LIST"
} else {
    Write-Host "注册失败，请尝试以管理员身份运行 PowerShell。"
    exit 1
}
