@echo off
echo ==========================================
echo      Restarting ProctoAI Full Stack
echo ==========================================

echo [1/2] Stopping existing services...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM celery.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM redis-server.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/2] Starting services...
call start_full_stack.bat
