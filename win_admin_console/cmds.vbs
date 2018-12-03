dim fso: set fso = CreateObject("Scripting.FileSystemObject")
dim CurrentDirectory
CurrentDirectory = fso.GetAbsolutePathName(".")
Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "psexec", "-s -i cmd /T:4E /K cd " & CurrentDirectory, "", "runas", 1