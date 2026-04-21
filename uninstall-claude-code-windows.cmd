@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%uninstall-claude-code-windows.ps1"

if not exist "%PS_SCRIPT%" (
  echo [ClaudeCodeUninstall] Missing script: %PS_SCRIPT%
  pause
  exit /b 1
)

echo [ClaudeCodeUninstall] Launching uninstaller...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo [ClaudeCodeUninstall] Uninstaller failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo [ClaudeCodeUninstall] Completed successfully.
pause
exit /b 0