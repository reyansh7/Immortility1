@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0immortility.ps1" -Dev %*
exit /b %ERRORLEVEL%
