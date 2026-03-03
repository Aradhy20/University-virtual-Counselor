@echo off
title TMU Aditi - Full Backend Startup
echo ==========================================
echo  TMU University Counselor - Aditi Backend
echo ==========================================
echo.

REM --- 1. Start FastAPI server in background ---
echo [1/3] Starting FastAPI server on port 8000...
start "FastAPI Server" cmd /k ".venv_new\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul

REM --- 2. Start Cloudflare tunnel + auto-update Twilio ---
echo [2/3] Starting tunnel and updating Twilio webhook...
start "Cloudflare Tunnel" cmd /k ".venv_new\Scripts\python.exe scripts\start_and_update_tunnel.py"
timeout /t 12 /nobreak >nul

echo [3/3] Done! Both services are starting.
echo.
echo  FastAPI  : http://localhost:8000
echo  Tunnel   : Check the 'Cloudflare Tunnel' window for the URL
echo  Webhook  : /voice endpoint auto-updated in Twilio
echo.
echo Keep both windows open for the agent to work.
pause
