' LinkHub Silent Launcher
' Starts backend and frontend with completely hidden CMD windows.
' Use start.bat --debug to show windows for troubleshooting.

Set WshShell = CreateObject("WScript.Shell")
strDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Start backend (hidden)
WshShell.Run "cmd /c """ & strDir & "\backend\run.bat""", 0, False

' Wait for backend to be ready
WScript.Sleep 3000

' Start frontend (hidden)
WshShell.Run "cmd /c """ & strDir & "\frontend\run.bat""", 0, False

' Wait for frontend to be ready
WScript.Sleep 3000

' Open browser
WshShell.Run "http://localhost:5173", 1, False
