@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0hub_runtime\stop_instance.ps1"
exit /b %ERRORLEVEL%
