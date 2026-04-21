Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[ClaudeCodeSetup] $Message" -ForegroundColor Cyan
}

$script:InstallActivity = "Claude Code Setup"

function Set-InstallProgress {
  param(
    [int]$Percent,
    [string]$Status
  )

  $boundedPercent = [Math]::Max(0, [Math]::Min($Percent, 100))
  Write-Progress -Activity $script:InstallActivity -Status $Status -PercentComplete $boundedPercent
}

function Complete-InstallProgress {
  Write-Progress -Activity $script:InstallActivity -Completed
}

function Refresh-UserPath {
  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machinePath;$userPath"
}

function Show-ProxyConfigDialog {
  param(
    [string]$DefaultUrl = "",
    [string]$DefaultKey = ""
  )

  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing

  $form = New-Object System.Windows.Forms.Form
  $form.Text = "Configure Proxy For Claude Code"
  $form.StartPosition = "CenterScreen"
  $form.Size = New-Object System.Drawing.Size(560, 260)
  $form.FormBorderStyle = "FixedDialog"
  $form.MaximizeBox = $false
  $form.MinimizeBox = $false
  $form.TopMost = $true

  $urlLabel = New-Object System.Windows.Forms.Label
  $urlLabel.Location = New-Object System.Drawing.Point(20, 20)
  $urlLabel.Size = New-Object System.Drawing.Size(500, 20)
  $urlLabel.Text = "Proxy URL (example: http://proxy.company.com:8080)"

  $urlInput = New-Object System.Windows.Forms.TextBox
  $urlInput.Location = New-Object System.Drawing.Point(20, 45)
  $urlInput.Size = New-Object System.Drawing.Size(510, 24)
  $urlInput.Text = $DefaultUrl

  $keyLabel = New-Object System.Windows.Forms.Label
  $keyLabel.Location = New-Object System.Drawing.Point(20, 85)
  $keyLabel.Size = New-Object System.Drawing.Size(500, 20)
  $keyLabel.Text = "Proxy Key / Token"

  $keyInput = New-Object System.Windows.Forms.TextBox
  $keyInput.Location = New-Object System.Drawing.Point(20, 110)
  $keyInput.Size = New-Object System.Drawing.Size(510, 24)
  $keyInput.Text = $DefaultKey
  $keyInput.UseSystemPasswordChar = $true

  $hint = New-Object System.Windows.Forms.Label
  $hint.Location = New-Object System.Drawing.Point(20, 145)
  $hint.Size = New-Object System.Drawing.Size(510, 30)
  $hint.Text = "Save: save URL/Key for launcher. Skip: continue without proxy settings."

  $saveButton = New-Object System.Windows.Forms.Button
  $saveButton.Text = "Save"
  $saveButton.Location = New-Object System.Drawing.Point(300, 180)
  $saveButton.Size = New-Object System.Drawing.Size(110, 30)
  $saveButton.DialogResult = [System.Windows.Forms.DialogResult]::OK

  $skipButton = New-Object System.Windows.Forms.Button
  $skipButton.Text = "Skip"
  $skipButton.Location = New-Object System.Drawing.Point(420, 180)
  $skipButton.Size = New-Object System.Drawing.Size(110, 30)
  $skipButton.DialogResult = [System.Windows.Forms.DialogResult]::Ignore

  $form.Controls.Add($urlLabel)
  $form.Controls.Add($urlInput)
  $form.Controls.Add($keyLabel)
  $form.Controls.Add($keyInput)
  $form.Controls.Add($hint)
  $form.Controls.Add($saveButton)
  $form.Controls.Add($skipButton)
  $form.AcceptButton = $saveButton

  $result = $form.ShowDialog()
  if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    return @{
      Save     = $true
      ProxyUrl = $urlInput.Text.Trim()
      ProxyKey = $keyInput.Text.Trim()
    }
  }

  return @{
    Save     = $false
    ProxyUrl = ""
    ProxyKey = ""
  }
}

function Ensure-NodeAndNpm {
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    Set-InstallProgress -Percent 45 -Status "npm is already available."
    Write-Step "npm already exists."
    return
  }

  Set-InstallProgress -Percent 45 -Status "Installing Node.js LTS with winget..."
  Write-Step "npm not found. Trying to install Node.js LTS with winget..."
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget not found. Please install Node.js manually, then rerun this script."
  }

  & winget install --id OpenJS.NodeJS.LTS --source winget --accept-package-agreements --accept-source-agreements --scope user --silent
  Refresh-UserPath

  Set-InstallProgress -Percent 55 -Status "Validating npm after Node.js installation..."
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js install finished but npm is still unavailable. Restart terminal and rerun script."
  }
}

function Ensure-GitInstalled {
  param(
    [string]$InstallerDir
  )

  if (Get-Command git -ErrorAction SilentlyContinue) {
    Set-InstallProgress -Percent 38 -Status "Git is already available."
    Write-Step "Git already exists."
    return
  }

  Set-InstallProgress -Percent 38 -Status "Installing Git for Windows from local installer..."
  Write-Step "git not found. Installing Git for Windows from local installer..."

  if (-not (Test-Path $InstallerDir)) {
    throw "Installer directory not found: $InstallerDir"
  }

  $gitInstaller = Get-ChildItem -Path $InstallerDir -Filter "Git-*-64-bit.exe" -File |
    Sort-Object Name -Descending |
    Select-Object -First 1

  if (-not $gitInstaller) {
    $gitInstaller = Get-ChildItem -Path $InstallerDir -Filter "Git-*.exe" -File |
      Sort-Object Name -Descending |
      Select-Object -First 1
  }

  if (-not $gitInstaller) {
    throw "Git installer exe not found in: $InstallerDir"
  }

  Write-Step "Using installer: $($gitInstaller.FullName)"
  & $gitInstaller.FullName /VERYSILENT /NORESTART /NOCANCEL /SP-
  $installerExitCode = $LASTEXITCODE
  if ($installerExitCode -ne 0) {
    throw "Git installer failed with exit code $installerExitCode"
  }

  Refresh-UserPath
  $gitCmdPath = "C:\Program Files\Git\cmd"
  if ((Test-Path $gitCmdPath) -and ($env:Path -notlike "*$gitCmdPath*")) {
    $env:Path = "$gitCmdPath;$env:Path"
  }

  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git installation finished but git is still unavailable. Restart terminal and rerun script."
  }
}

function Ensure-ClaudeCodeInstalled {
  if (Get-Command claude -ErrorAction SilentlyContinue) {
    Set-InstallProgress -Percent 75 -Status "Claude Code is already installed locally."
    Write-Step "Claude Code is already installed on this machine."
    return $true
  }

  Set-InstallProgress -Percent 40 -Status "Checking Node.js and npm..."
  Ensure-NodeAndNpm

  Set-InstallProgress -Percent 65 -Status "Installing Claude Code via npm..."
  Write-Step "Installing Claude Code globally via npm..."
  & npm install -g @anthropic-ai/claude-code

  $npmGlobalBin = Join-Path $env:APPDATA "npm"
  if ($env:Path -notlike "*$npmGlobalBin*") {
    $env:Path = "$npmGlobalBin;$env:Path"
  }

  if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw "Claude Code installation may have failed: command 'claude' not found."
  }

  Set-InstallProgress -Percent 75 -Status "Claude Code installation finished."
  Write-Step "Claude Code installation completed."
  return $false
}

function Save-ProxyConfig {
  param(
    [string]$ConfigPath,
    [hashtable]$Config
  )

  $dir = Split-Path -Parent $ConfigPath
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }

  ($Config | ConvertTo-Json -Depth 5) | Set-Content -Path $ConfigPath -Encoding UTF8
}

function Write-LauncherScript {
  param(
    [string]$LauncherPath,
    [string]$ProxyConfigPath
  )

  $launcherDir = Split-Path -Parent $LauncherPath
  if (-not (Test-Path $launcherDir)) {
    New-Item -ItemType Directory -Path $launcherDir | Out-Null
  }

  $content = @"
param(
  [string]`$TargetDir
)

`$configPath = '$($ProxyConfigPath.Replace("'", "''"))'
if (Test-Path `$configPath) {
  try {
    `$cfg = Get-Content -Raw -Path `$configPath | ConvertFrom-Json
    if (`$cfg.ProxyUrl) {
      `$env:HTTP_PROXY = `$cfg.ProxyUrl
      `$env:HTTPS_PROXY = `$cfg.ProxyUrl
      `$env:ALL_PROXY = `$cfg.ProxyUrl
      `$env:ANTHROPIC_BASE_URL = `$cfg.ProxyUrl
    }
    if (`$cfg.ProxyKey) {
      `$env:PROXY_API_KEY = `$cfg.ProxyKey
      `$env:ANTHROPIC_API_KEY = `$cfg.ProxyKey
    }
  } catch {
    `$errorMessage = `$_.Exception.Message
    Write-Host ("Failed to load proxy config: {0}" -f `$errorMessage) -ForegroundColor Yellow
  }
}

`$npmGlobalBin = Join-Path `$env:APPDATA "npm"
if (`$env:Path -notlike "*`$npmGlobalBin*") {
  `$env:Path = "`$npmGlobalBin;`$env:Path"
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Write-Host "Cannot find 'claude' command. Run setup installer again." -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

if (`$TargetDir -and (Test-Path -LiteralPath `$TargetDir -PathType Container)) {
  Set-Location -LiteralPath `$TargetDir
} else {
  Set-Location `$HOME
}

claude
"@

  Set-Content -Path $LauncherPath -Value $content -Encoding UTF8
}

function Register-ExplorerContextMenu {
  param(
    [string]$LauncherPath
  )

  $powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
  $menuText = "Open Claude Code Here"
  $baseBgKey = "HKCU:\Software\Classes\Directory\Background\shell\ClaudeCode"
  $baseDirKey = "HKCU:\Software\Classes\Directory\shell\ClaudeCode"

  if (-not (Test-Path $baseBgKey)) {
    New-Item -Path $baseBgKey -Force | Out-Null
  }
  Set-ItemProperty -Path $baseBgKey -Name "(Default)" -Value $menuText
  Set-ItemProperty -Path $baseBgKey -Name "Icon" -Value $powerShellPath
  $bgCommandKey = Join-Path $baseBgKey "command"
  if (-not (Test-Path $bgCommandKey)) {
    New-Item -Path $bgCommandKey -Force | Out-Null
  }
  Set-ItemProperty -Path $bgCommandKey -Name "(Default)" -Value "`"$powerShellPath`" -NoExit -ExecutionPolicy RemoteSigned -File `"$LauncherPath`" -TargetDir `"%V`""

  if (-not (Test-Path $baseDirKey)) {
    New-Item -Path $baseDirKey -Force | Out-Null
  }
  Set-ItemProperty -Path $baseDirKey -Name "(Default)" -Value $menuText
  Set-ItemProperty -Path $baseDirKey -Name "Icon" -Value $powerShellPath
  $dirCommandKey = Join-Path $baseDirKey "command"
  if (-not (Test-Path $dirCommandKey)) {
    New-Item -Path $dirCommandKey -Force | Out-Null
  }
  Set-ItemProperty -Path $dirCommandKey -Name "(Default)" -Value "`"$powerShellPath`" -NoExit -ExecutionPolicy RemoteSigned -File `"$LauncherPath`" -TargetDir `"%1`""
}

try {
  Set-InstallProgress -Percent 5 -Status "Starting setup..."
  Write-Step "Starting Claude Code setup for Windows..."

  Set-InstallProgress -Percent 10 -Status "Preparing user configuration paths..."
  $configDir = Join-Path $env:APPDATA "ClaudeCode"
  $proxyConfigPath = Join-Path $configDir "proxy-config.json"
  $launcherPath = Join-Path $configDir "launch-claude-code.ps1"
  $installerDir = $PSScriptRoot

  Set-InstallProgress -Percent 20 -Status "Loading existing proxy settings..."
  $defaultUrl = "http://192.168.160.145:8081"
  $defaultKey = ""
  if (Test-Path $proxyConfigPath) {
    try {
      $oldCfg = Get-Content -Raw -Path $proxyConfigPath | ConvertFrom-Json
      $defaultUrl = [string]$oldCfg.ProxyUrl
      $defaultKey = [string]$oldCfg.ProxyKey
    } catch {
      Write-Step "Existing proxy config is invalid and will be overwritten."
    }
  }

  Set-InstallProgress -Percent 30 -Status "Waiting for proxy configuration input..."
  $proxyInput = Show-ProxyConfigDialog -DefaultUrl $defaultUrl -DefaultKey $defaultKey
  if ($proxyInput.Save) {
    Save-ProxyConfig -ConfigPath $proxyConfigPath -Config @{
      ProxyUrl  = $proxyInput.ProxyUrl
      ProxyKey  = $proxyInput.ProxyKey
      UpdatedAt = (Get-Date).ToString("s")
      UpdatedBy = $env:USERNAME
      Machine   = $env:COMPUTERNAME
    }
    Write-Step "Proxy settings saved to $proxyConfigPath"
  } else {
    Write-Step "Proxy settings skipped for this run."
  }

  Set-InstallProgress -Percent 35 -Status "Checking local Git installation..."
  Ensure-GitInstalled -InstallerDir $installerDir

  Set-InstallProgress -Percent 40 -Status "Checking local Claude Code installation..."
  Ensure-ClaudeCodeInstalled | Out-Null

  Set-InstallProgress -Percent 85 -Status "Creating launcher and Explorer context menu..."
  Write-LauncherScript -LauncherPath $launcherPath -ProxyConfigPath $proxyConfigPath
  Register-ExplorerContextMenu -LauncherPath $launcherPath

  Set-InstallProgress -Percent 100 -Status "Setup completed."
  Write-Step "Setup completed. Right click any folder background and choose: Open Claude Code Here"
  Write-Host "Proxy config: $proxyConfigPath"
  Write-Host "Launcher script: $launcherPath"
  Write-Host "Explorer context menu: Open Claude Code Here"
}
finally {
  Complete-InstallProgress
}
