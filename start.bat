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

echo [1/4] Starting backend on port 8147...
start "LinkHub-Backend" cmd /k "%~dp0backend\run.bat"

echo [2/4] Waiting for backend to be ready...
:wait_backend
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8147/api/health' -TimeoutSec 1 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } } catch { }; exit 1" >nul 2>&1
if errorlevel 1 goto wait_backend
echo     Backend is ready.

echo [3/4] Starting frontend on port 5173...
start "LinkHub-Frontend" cmd /k "%~dp0frontend\run.bat"

echo [4/4] Waiting for frontend to be ready...
:wait_frontend
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5173' -TimeoutSec 1 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } } catch { }; exit 1" >nul 2>&1
if errorlevel 1 goto wait_frontend
echo     Frontend is ready.

echo.
echo  LinkHub started! (Debug Mode)
echo  Frontend : http://localhost:5173
echo  Backend  : http://127.0.0.1:8147
echo  Logs     : http://localhost:5173/logs
echo.

start http://localhost:5173

echo Press any key to close this window...
pause >nul
