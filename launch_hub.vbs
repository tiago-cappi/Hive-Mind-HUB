' Abre somente a instalação onde este script está salvo.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
hubRoot = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = hubRoot
pyw = fso.BuildPath(hubRoot, ".venv\Scripts\pythonw.exe")
script = fso.BuildPath(hubRoot, "launch.py")
sh.Run """" & pyw & """ """ & script & """", 0, False
