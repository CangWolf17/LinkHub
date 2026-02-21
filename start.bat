@echo off
chcp 65001 >nul 2>&1
title LinkHub - Local Smart Dashboard

:: 切换到 bat 文件所在目录，无论从哪里调用都能正确定位
cd /d "%~dp0"

echo ========================================
echo   LinkHub - 正在启动...
echo ========================================
echo.

:: 启动后端 (FastAPI + Uvicorn)
echo [1/3] 启动后端服务 (port 8147)...
start "LinkHub-Backend" cmd /c "cd /d "%~dp0backend" && D:\Miniconda\python.exe main.py"

:: 等待后端就绪
echo [2/3] 等待后端就绪...
timeout /t 3 /nobreak >nul

:: 启动前端 (Vite dev server)
echo [3/3] 启动前端服务 (port 5173)...
start "LinkHub-Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

:: 等待前端就绪后打开浏览器
timeout /t 3 /nobreak >nul
echo.
echo ========================================
echo   LinkHub 已启动!
echo   前端: http://localhost:5173
echo   后端: http://127.0.0.1:8147
echo ========================================
echo.

start http://localhost:5173

echo 按任意键关闭此窗口 (后端和前端将继续运行)...
pause >nul
