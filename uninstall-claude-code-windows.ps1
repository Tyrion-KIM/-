Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[ClaudeCodeUninstall] $Message" -ForegroundColor Cyan
}

$script:UninstallActivity = "Claude Code Uninstall"
$script:UninstallStartTime = Get-Date
$script:UninstallProgressBarWidth = 36
$script:LastUninstallProgressLineLength = 0

function Format-DurationText {
  param(
    [int]$TotalSeconds
  )

  $safeSeconds = [Math]::Max(0, $TotalSeconds)
  $ts = [TimeSpan]::FromSeconds($safeSeconds)
  if ($ts.TotalHours -ge 1) {
    return "{0}h {1}m {2}s" -f [int]$ts.TotalHours, $ts.Minutes, $ts.Seconds
  }
  if ($ts.TotalMinutes -ge 1) {
    return "{0}m {1}s" -f [int]$ts.TotalMinutes, $ts.Seconds
  }
  return "{0}s" -f $ts.Seconds
}

function Set-UninstallProgress {
  param(
    [int]$Percent,
    [string]$Status
  )

  $boundedPercent = [Math]::Max(0, [Math]::Min($Percent, 100))
  $elapsedSeconds = [Math]::Max(0, [int]((Get-Date) - $script:UninstallStartTime).TotalSeconds)
  $statusText = $Status

  if ($boundedPercent -gt 0 -and $boundedPercent -lt 100 -and $elapsedSeconds -gt 0) {
    $estimatedTotalSeconds = [int][Math]::Ceiling(($elapsedSeconds * 100.0) / $boundedPercent)
    $secondsRemaining = [Math]::Max(0, $estimatedTotalSeconds - $elapsedSeconds)
    $statusText = "{0} | ETA: {1}" -f $Status, (Format-DurationText -TotalSeconds $secondsRemaining)
  } elseif ($boundedPercent -eq 100) {
    $statusText = "{0} | Elapsed: {1}" -f $Status, (Format-DurationText -TotalSeconds $elapsedSeconds)
  }

  $barWidth = [Math]::Max(10, $script:UninstallProgressBarWidth)
  $filledCount = [int][Math]::Floor(($boundedPercent / 100.0) * $barWidth)
  if ($filledCount -gt $barWidth) {
    $filledCount = $barWidth
  }

  if ($boundedPercent -ge 100) {
    $barBody = ("=" * $barWidth)
  } else {
    $leftFill = "=" * $filledCount
    $rightPad = " " * ($barWidth - $filledCount - 1)
    $barBody = "{0}>{1}" -f $leftFill, $rightPad
  }

  $line = "`r[{0}] {1,3}% | {2}" -f $barBody, $boundedPercent, $statusText
  if ($line.Length -lt $script:LastUninstallProgressLineLength) {
    $line = $line + (" " * ($script:LastUninstallProgressLineLength - $line.Length))
  }

  $script:LastUninstallProgressLineLength = $line.Length
  Write-Host -NoNewline $line
}

function Complete-UninstallProgress {
  Write-Host ""
}

function Remove-PathIfExists {
  param(
    [string]$Path,
    [string]$Label,
    [switch]$Directory
  )

  if (-not (Test-Path $Path)) {
    Write-Step "$Label not found."
    return
  }

  if ($Directory) {
    Remove-Item -Path $Path -Recurse -Force
  } else {
    Remove-Item -Path $Path -Force
  }

  Write-Step "$Label removed."
}

function Remove-RegistryKeyIfExists {
  param(
    [string]$RegistryPath,
    [string]$Label
  )

  if (-not (Test-Path $RegistryPath)) {
    Write-Step "$Label not found."
    return
  }

  Remove-Item -Path $RegistryPath -Recurse -Force
  Write-Step "$Label removed."
}

function Refresh-UserPath {
  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machinePath;$userPath"
}

function Uninstall-ClaudeCode {
  Set-UninstallProgress -Percent 35 -Status "Checking local Claude Code installation..."

  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Step "npm not found. Skipping package uninstall step."
    return
  }

  Refresh-UserPath

  if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Step "Claude Code command not found locally. Skipping npm uninstall step."
    return
  }

  Set-UninstallProgress -Percent 55 -Status "Removing Claude Code from npm global packages..."
  Write-Step "Uninstalling Claude Code from npm..."
  & npm uninstall -g @anthropic-ai/claude-code

  Refresh-UserPath

  if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Step "Claude command is still present after uninstall. It may come from another installation path."
  } else {
    Write-Step "Claude Code package removed."
  }
}

try {
  $script:UninstallStartTime = Get-Date
  Set-UninstallProgress -Percent 5 -Status "Preparing uninstall paths..."
  Write-Step "Starting Claude Code uninstall for Windows..."

  $configDir = Join-Path $env:APPDATA "ClaudeCode"
  $proxyConfigPath = Join-Path $configDir "proxy-config.json"
  $desktopPath = [Environment]::GetFolderPath("Desktop")
  $desktopShortcutPath = Join-Path $desktopPath "Claude Code.lnk"
  $dirBgContextMenuKey = "HKCU:\Software\Classes\Directory\Background\shell\ClaudeCode"
  $dirContextMenuKey = "HKCU:\Software\Classes\Directory\shell\ClaudeCode"

  Set-UninstallProgress -Percent 20 -Status "Removing desktop shortcut and Explorer context menu entries..."
  Remove-PathIfExists -Path $desktopShortcutPath -Label "Desktop shortcut"
  Remove-RegistryKeyIfExists -RegistryPath $dirBgContextMenuKey -Label "Explorer background context menu"
  Remove-RegistryKeyIfExists -RegistryPath $dirContextMenuKey -Label "Explorer directory context menu"

  Uninstall-ClaudeCode

  Set-UninstallProgress -Percent 75 -Status "Removing local Claude Code configuration..."
  $launcherPath = Join-Path $configDir "launch-claude-code.ps1"
  Remove-PathIfExists -Path $launcherPath -Label "Launcher script"
  Remove-PathIfExists -Path $proxyConfigPath -Label "Proxy config"
  Remove-PathIfExists -Path $configDir -Label "Claude Code config directory" -Directory

  Set-UninstallProgress -Percent 100 -Status "Uninstall completed."
  Write-Step "Claude Code uninstall completed."
}
finally {
  Complete-UninstallProgress
}