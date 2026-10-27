@echo off
rem Fallback caso o .vbs seja bloqueado (Kaspersky). Mostra um flash de console.
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\m.rafael\.claude\hooks\voice-input\voice_hub.ps1"
