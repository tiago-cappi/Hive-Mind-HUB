' Lanca o Voice Hub sem mostrar janela de console.
' Window style 0 = oculto; a janela WinForms do voice_hub.ps1 ainda aparece.
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\m.rafael\.claude\hooks\voice-input\voice_hub.ps1""", 0, False
