@echo off
title LinkHub

set ROOT=%~dp0

echo [1/3] Starting backend on port 8147...
start "LinkHub-Backend" cmd /k "pushd %ROOT%backend ^&^& D:\Miniconda\python.exe main.py"

echo [2/3] Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

echo [3/3] Starting frontend on port 5173...
start "LinkHub-Frontend" cmd /k "pushd %ROOT%frontend ^&^& npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo  LinkHub started!
echo  Frontend : http://localhost:5173
echo  Backend  : http://127.0.0.1:8147
echo.

start http://localhost:5173

echo Press any key to close this window...
pause >nul