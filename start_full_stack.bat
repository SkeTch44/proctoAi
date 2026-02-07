@echo off
echo ==========================================
echo      Starting ProctoAI Full Stack
echo ==========================================

echo [1/4] Starting Redis Server...
start "Redis Server" cmd /k "redis-server"

echo [2/4] Starting Backend (Flask)...
start "ProctoAI Backend" cmd /k "python backend/app.py"

echo [3/4] Starting Celery Worker...
start "ProctoAI Worker" cmd /k "run_celery.bat"

echo [4/4] Starting Frontend...
cd frontend
if exist package.json (
    start "ProctoAI Frontend" cmd /k "npm start"
) else (
    echo [WARNING] package.json not found in frontend directory!
    echo Attempting 'npm start' anyway...
    start "ProctoAI Frontend" cmd /k "npm start || echo Frontend start failed. Check package.json. & pause"
)

echo.
echo All services launch commands issued. Check individual windows for status.
echo.
pause
