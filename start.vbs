' LinkHub Silent Launcher
' Starts backend and frontend with completely hidden CMD windows.
' Use start.bat --debug to show windows for troubleshooting.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Start backend (hidden)
WshShell.Run "cmd /c """ & strDir & "\backend\run.bat""", 0, False

' Poll backend health until ready (max 30s)
Dim http, ready, attempts
Set http = CreateObject("MSXML2.XMLHTTP")
ready = False
attempts = 0
Do While Not ready And attempts < 60
    WScript.Sleep 500
    attempts = attempts + 1
    On Error Resume Next
    http.open "GET", "http://127.0.0.1:8147/api/health", False
    http.send
    If Err.Number = 0 And http.status = 200 Then
        ready = True
    End If
    On Error GoTo 0
Loop

' Start frontend (hidden)
WshShell.Run "cmd /c """ & strDir & "\frontend\run.bat""", 0, False

' Poll frontend Vite dev server until ready (max 30s)
Dim ready2, attempts2
ready2 = False
attempts2 = 0
Do While Not ready2 And attempts2 < 60
    WScript.Sleep 500
    attempts2 = attempts2 + 1
    On Error Resume Next
    http.open "GET", "http://localhost:5173", False
    http.send
    If Err.Number = 0 And http.status = 200 Then
        ready2 = True
    End If
    On Error GoTo 0
Loop

' Open browser
WshShell.Run "http://localhost:5173", 1, False
