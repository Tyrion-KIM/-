Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[ClaudeCodeUninstall] $Message" -ForegroundColor Cyan
}

$script:UninstallActivity = "Claude Code Uninstall"

function Set-UninstallProgress {
  param(
    [int]$Percent,
    [string]$Status
  )

  $boundedPercent = [Math]::Max(0, [Math]::Min($Percent, 100))
  Write-Progress -Activity $script:UninstallActivity -Status $Status -PercentComplete $boundedPercent
}

function Complete-UninstallProgress {
  Write-Progress -Activity $script:UninstallActivity -Completed
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
  Set-UninstallProgress -Percent 5 -Status "Preparing uninstall paths..."
  Write-Step "Starting Claude Code uninstall for Windows..."

  $configDir = Join-Path $env:APPDATA "ClaudeCode"
  $proxyConfigPath = Join-Path $configDir "proxy-config.json"
  $desktopPath = [Environment]::GetFolderPath("Desktop")
  $desktopShortcutPath = Join-Path $desktopPath "Claude Code.lnk"
  $startMenuProgramsPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
  $startMenuShortcutPath = Join-Path $startMenuProgramsPath "Claude Code.lnk"

  Set-UninstallProgress -Percent 20 -Status "Removing desktop and Start menu shortcuts..."
  Remove-PathIfExists -Path $desktopShortcutPath -Label "Desktop shortcut"
  Remove-PathIfExists -Path $startMenuShortcutPath -Label "Start menu shortcut"

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