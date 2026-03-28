' Mouse Battery Monitor - Silent Startup Launcher
' Uses pythonw.exe to run without a console window.

Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strProjectDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))

strPythonw = strProjectDir & "\venv\Scripts\pythonw.exe"

If Not fso.FileExists(strPythonw) Then
    MsgBox "pythonw.exe not found. Please create venv first.", vbCritical, "Mouse Battery Monitor"
    WScript.Quit 1
End If

objShell.CurrentDirectory = strProjectDir
objShell.Run """" & strPythonw & """ -m app.main", 0, False
