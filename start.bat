@echo off
title ICT Backtest

echo Stopping existing servers on 8000 / 3001...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%p /F >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do (
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [1/2] Starting backend (port 8000)...
start "ICT Backend" cmd /k "cd /d D:\ict-backtest\backend && .venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend (port 3001)...
start "ICT Frontend" cmd /k "cd /d D:\ict-backtest\frontend && pnpm dev --port 3001"

timeout /t 6 /nobreak >nul

echo Opening browser...
start "" "http://localhost:3001"

echo.
echo Both servers started. Close this window anytime.
pause
