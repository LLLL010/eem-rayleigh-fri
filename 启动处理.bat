@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0eem_tool.exe" "%~dp0."
set "RC=%ERRORLEVEL%"
echo.
if not defined EEM_NO_PAUSE pause
exit /b %RC%
