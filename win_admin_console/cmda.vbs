dim fso: set fso = CreateObject("Scripting.FileSystemObject")
dim CurrentDirectory
CurrentDirectory = fso.GetAbsolutePathName(".")
Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "cmd", "/T:4F /K cd " & CurrentDirectory, "", "runas", 1