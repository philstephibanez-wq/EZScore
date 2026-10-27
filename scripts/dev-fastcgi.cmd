@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-fastcgi.ps1" %1
exit /b %ERRORLEVEL%
