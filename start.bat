@echo off
title LinkHub

:: Check for --debug flag
set "DEBUG_MODE=0"
for %%a in (%*) do (
    if /i "%%a"=="--debug" set "DEBUG_MODE=1"
)

:: Normal mode: launch via VBS (completely hidden windows)
if "%DEBUG_MODE%"=="0" (
    echo Launching LinkHub in silent mode...
    echo Use "start.bat --debug" to show console windows.
    start "" wscript.exe "%~dp0start.vbs"
    exit /b
)

:: Debug mode: show all windows for troubleshooting
echo [DEBUG MODE] Starting with visible console windows...
echo.

echo [1/3] Starting backend on port 8147...
start "LinkHub-Backend" cmd /k "%~dp0backend\run.bat"

echo [2/3] Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

echo [3/3] Starting frontend on port 5173...
start "LinkHub-Frontend" cmd /k "%~dp0frontend\run.bat"

timeout /t 3 /nobreak >nul

echo.
echo  LinkHub started! (Debug Mode)
echo  Frontend : http://localhost:5173
echo  Backend  : http://127.0.0.1:8147
echo  Logs     : http://localhost:5173/logs
echo.

start http://localhost:5173

echo Press any key to close this window...
pause >nul
