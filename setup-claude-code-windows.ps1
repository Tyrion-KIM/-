Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[ClaudeCodeSetup] $Message" -ForegroundColor Cyan
}

$script:InstallActivity = "Claude Code Setup"
$script:InstallStartTime = Get-Date
$script:ProgressBarWidth = 36
$script:LastProgressLineLength = 0

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

function Set-InstallProgress {
  param(
    [int]$Percent,
    [string]$Status
  )

  $boundedPercent = [Math]::Max(0, [Math]::Min($Percent, 100))
  $elapsedSeconds = [Math]::Max(0, [int]((Get-Date) - $script:InstallStartTime).TotalSeconds)
  $secondsRemaining = -1
  $statusText = $Status

  if ($boundedPercent -gt 0 -and $boundedPercent -lt 100 -and $elapsedSeconds -gt 0) {
    $estimatedTotalSeconds = [int][Math]::Ceiling(($elapsedSeconds * 100.0) / $boundedPercent)
    $secondsRemaining = [Math]::Max(0, $estimatedTotalSeconds - $elapsedSeconds)
    $statusText = "{0} | ETA: {1}" -f $Status, (Format-DurationText -TotalSeconds $secondsRemaining)
  } elseif ($boundedPercent -eq 100) {
    $statusText = "{0} | Elapsed: {1}" -f $Status, (Format-DurationText -TotalSeconds $elapsedSeconds)
  }

  $barWidth = [Math]::Max(10, $script:ProgressBarWidth)
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
  if ($line.Length -lt $script:LastProgressLineLength) {
    $line = $line + (" " * ($script:LastProgressLineLength - $line.Length))
  }

  $script:LastProgressLineLength = $line.Length
  Write-Host -NoNewline $line
}

function Complete-InstallProgress {
  Write-Host ""
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

function Save-ClaudeSettings {
  param(
    [string]$AuthToken
  )

  if (-not $AuthToken) {
    return
  }

  $claudeDir = Join-Path $HOME ".claude"
  $settingsPath = Join-Path $claudeDir "settings.json"

  if (-not (Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir | Out-Null
  }

  $settings = [ordered]@{
    env = [ordered]@{
      ANTHROPIC_BASE_URL                       = "http://192.168.160.145:8081"
      ANTHROPIC_AUTH_TOKEN                     = $AuthToken
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
      CLAUDE_CODE_ATTRIBUTION_HEADER           = "0"
      ANTHROPIC_DEFAULT_HAIKU_MODEL            = "glm-5-turbo"
      ANTHROPIC_DEFAULT_OPUS_MODEL             = "glm-5.1"
      ANTHROPIC_DEFAULT_SONNET_MODEL           = "glm-5-turbo"
      ANTHROPIC_SMALL_FAST_MODEL               = "glm-5-turbo"
      ANTHROPIC_MODEL                          = "glm-5.1"
      ANTHROPIC_REASONING_MODEL                = "glm-5.1"
      API_TIMEOUT_MS                           = "3000000"
    }
  }

  ($settings | ConvertTo-Json -Depth 5) | Set-Content -Path $settingsPath -Encoding UTF8
  Write-Step "Claude settings saved to $settingsPath"
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

claude --bare
"@

  Set-Content -Path $LauncherPath -Value $content -Encoding UTF8
}

function Resolve-InstallIconLocation {
  param(
    [string]$InstallerDir,
    [string]$ConfigDir,
    [string]$FallbackIconLocation
  )

  if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir | Out-Null
  }

  function Convert-PngToIco {
    param(
      [string]$PngPath,
      [string]$IcoPath
    )

    Add-Type -AssemblyName System.Drawing

    $sourceImage = $null
    $canvas = $null
    $graphics = $null
    $icon = $null
    $fileStream = $null
    try {
      $sourceImage = [System.Drawing.Image]::FromFile($PngPath)
      $canvas = New-Object System.Drawing.Bitmap(256, 256)
      $graphics = [System.Drawing.Graphics]::FromImage($canvas)
      $graphics.Clear([System.Drawing.Color]::Transparent)
      $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $graphics.DrawImage($sourceImage, 0, 0, 256, 256)

      $hIcon = $canvas.GetHicon()
      $icon = [System.Drawing.Icon]::FromHandle($hIcon)
      $fileStream = [System.IO.File]::Open($IcoPath, [System.IO.FileMode]::Create)
      $icon.Save($fileStream)
      return $true
    } catch {
      Write-Step "PNG to ICO conversion skipped: $($_.Exception.Message)"
      return $false
    } finally {
      if ($fileStream) { $fileStream.Dispose() }
      if ($icon) { $icon.Dispose() }
      if ($graphics) { $graphics.Dispose() }
      if ($canvas) { $canvas.Dispose() }
      if ($sourceImage) { $sourceImage.Dispose() }
    }
  }

  if (Test-Path $InstallerDir) {
    $pngFile = Get-ChildItem -Path $InstallerDir -Filter "*.png" -File |
      Sort-Object Name |
      Select-Object -First 1
    if ($pngFile) {
      $generatedIcoPath = Join-Path $ConfigDir "launcher-icon.ico"
      if (Convert-PngToIco -PngPath $pngFile.FullName -IcoPath $generatedIcoPath) {
        return $generatedIcoPath
      }
    }

    $icoFile = Get-ChildItem -Path $InstallerDir -Filter "*.ico" -File |
      Sort-Object Name |
      Select-Object -First 1
    if ($icoFile) {
      return $icoFile.FullName
    }

    $exeFile = Get-ChildItem -Path $InstallerDir -Filter "*.exe" -File |
      Sort-Object Name |
      Select-Object -First 1
    if ($exeFile) {
      return "$($exeFile.FullName),0"
    }
  }

  return $FallbackIconLocation
}

function Register-ExplorerContextMenu {
  param(
    [string]$LauncherPath,
    [string]$IconLocation
  )

  $powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
  $menuText = "Open Claude Code Here"
  $baseBgKey = "HKCU:\Software\Classes\Directory\Background\shell\ClaudeCode"
  $baseDirKey = "HKCU:\Software\Classes\Directory\shell\ClaudeCode"

  if (-not (Test-Path $baseBgKey)) {
    New-Item -Path $baseBgKey -Force | Out-Null
  }
  Set-ItemProperty -Path $baseBgKey -Name "(Default)" -Value $menuText
  Set-ItemProperty -Path $baseBgKey -Name "Icon" -Value $IconLocation
  $bgCommandKey = Join-Path $baseBgKey "command"
  if (-not (Test-Path $bgCommandKey)) {
    New-Item -Path $bgCommandKey -Force | Out-Null
  }
  Set-ItemProperty -Path $bgCommandKey -Name "(Default)" -Value "`"$powerShellPath`" -NoExit -ExecutionPolicy RemoteSigned -File `"$LauncherPath`" -TargetDir `"%V`""

  if (-not (Test-Path $baseDirKey)) {
    New-Item -Path $baseDirKey -Force | Out-Null
  }
  Set-ItemProperty -Path $baseDirKey -Name "(Default)" -Value $menuText
  Set-ItemProperty -Path $baseDirKey -Name "Icon" -Value $IconLocation
  $dirCommandKey = Join-Path $baseDirKey "command"
  if (-not (Test-Path $dirCommandKey)) {
    New-Item -Path $dirCommandKey -Force | Out-Null
  }
  Set-ItemProperty -Path $dirCommandKey -Name "(Default)" -Value "`"$powerShellPath`" -NoExit -ExecutionPolicy RemoteSigned -File `"$LauncherPath`" -TargetDir `"%1`""
}

function Create-DesktopShortcut {
  param(
    [string]$LauncherPath,
    [string]$IconLocation
  )

  $desktopPath = [Environment]::GetFolderPath("Desktop")
  $shortcutPath = Join-Path $desktopPath "Claude Code.lnk"
  $powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

  $wsh = New-Object -ComObject WScript.Shell
  $shortcut = $wsh.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $powerShellPath
  $shortcut.Arguments = "-NoExit -ExecutionPolicy RemoteSigned -File `"$LauncherPath`""
  $shortcut.WorkingDirectory = $HOME
  $shortcut.WindowStyle = 1
  $shortcut.Description = "Launch Claude Code"
  $shortcut.IconLocation = $IconLocation
  $shortcut.Save()

  Write-Step "Desktop shortcut created: $shortcutPath"
}

try {
  $script:InstallStartTime = Get-Date
  Set-InstallProgress -Percent 5 -Status "Starting setup..."
  Write-Step "Starting Claude Code setup for Windows..."

  Set-InstallProgress -Percent 10 -Status "Preparing user configuration paths..."
  $configDir = Join-Path $env:APPDATA "ClaudeCode"
  $proxyConfigPath = Join-Path $configDir "proxy-config.json"
  $launcherPath = Join-Path $configDir "launch-claude-code.ps1"
  $installerDir = $PSScriptRoot
  $defaultIconLocation = "$(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'),0"
  $iconLocation = $defaultIconLocation

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
    Save-ClaudeSettings -AuthToken $proxyInput.ProxyKey
    Write-Step "Proxy settings saved to $proxyConfigPath"
  } else {
    Write-Step "Proxy settings skipped for this run."
  }

  Set-InstallProgress -Percent 35 -Status "Checking local Git installation..."
  Ensure-GitInstalled -InstallerDir $installerDir

  Set-InstallProgress -Percent 40 -Status "Checking local Claude Code installation..."
  Ensure-ClaudeCodeInstalled | Out-Null

  Set-InstallProgress -Percent 82 -Status "Creating launcher script..."
  Write-LauncherScript -LauncherPath $launcherPath -ProxyConfigPath $proxyConfigPath
  Set-InstallProgress -Percent 88 -Status "Registering Explorer context menu..."
  Register-ExplorerContextMenu -LauncherPath $launcherPath -IconLocation $iconLocation
  Set-InstallProgress -Percent 94 -Status "Creating desktop shortcut..."
  Create-DesktopShortcut -LauncherPath $launcherPath -IconLocation $iconLocation

  Set-InstallProgress -Percent 100 -Status "Setup completed."
  Write-Step "Setup completed. Use desktop shortcut or right click folder and choose: Open Claude Code Here"
  Write-Host "Proxy config: $proxyConfigPath"
  Write-Host "Launcher script: $launcherPath"
  Write-Host "Desktop shortcut: $([Environment]::GetFolderPath('Desktop'))\Claude Code.lnk"
  Write-Host "Icon source: $iconLocation"
  Write-Host "Explorer context menu: Open Claude Code Here"
}
finally {
  Complete-InstallProgress
}
