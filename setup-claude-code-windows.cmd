@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%setup-claude-code-windows.ps1"

if not exist "%PS_SCRIPT%" (
  echo [ClaudeCodeSetup] Missing script: %PS_SCRIPT%
  pause
  exit /b 1
)

echo [ClaudeCodeSetup] Launching installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo [ClaudeCodeSetup] Installer failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo [ClaudeCodeSetup] Completed successfully.
pause
exit /b 0
