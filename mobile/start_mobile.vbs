' Sobe o servidor do celular SEM janela de console (duplo clique).
' Para encerrar: Gerenciador de Tarefas -> pythonw.exe, ou stop_mobile.ps1.
Set fso = CreateObject("Scripting.FileSystemObject")
raiz = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = raiz
sh.Run """" & raiz & "\.venv\Scripts\pythonw.exe"" -m mobile.run", 0, False
