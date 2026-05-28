@echo off
title ICT Backtest

echo [1/2] Starting backend (port 8000)...
start "ICT Backend" cmd /k "cd /d D:\ict-backtest\backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend (port 3001)...
start "ICT Frontend" cmd /k "cd /d D:\ict-backtest\frontend && pnpm dev"

timeout /t 6 /nobreak >nul

echo Opening browser...
start "" "http://localhost:3001"

echo.
echo Both servers started. Close this window anytime.
pause
