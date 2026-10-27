@echo off
if "%~1"=="" (echo Usage: recover-dev-fastcgi.cmd ^<PID^> & exit /b 2)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-fastcgi.ps1" -Action recover -ExpectedPid %1 -ConfirmRecovery
exit /b %ERRORLEVEL%
