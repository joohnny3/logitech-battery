' Mouse Battery Monitor - Silent Startup Launcher
' Uses pythonw.exe to run without a console window.

Set objShell = CreateObject("WScript.Shell")
strProjectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName( _
    CreateObject("Scripting.FileSystemObject").GetParentFolderName( _
        WScript.ScriptFullName))

strPythonw = strProjectDir & "\venv\Scripts\pythonw.exe"

If Not CreateObject("Scripting.FileSystemObject").FileExists(strPythonw) Then
    MsgBox "找不到 pythonw.exe，請先建立 venv。", vbCritical, "Mouse Battery Monitor"
    WScript.Quit 1
End If

objShell.CurrentDirectory = strProjectDir
objShell.Run """" & strPythonw & """ -m app.main", 0, False
