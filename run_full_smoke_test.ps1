# PowerShell Script to Run Complete Smoke Test
# This script starts all services and runs the smoke test

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AI Proctored Exam Platform - Smoke Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Redis is running in WSL
Write-Host "[1/5] Checking Redis in WSL..." -ForegroundColor Yellow
$redisCheck = wsl bash -c "redis-cli -h 172.26.79.185 -p 6380 ping 2>&1"
if ($redisCheck -match "PONG") {
    Write-Host "✅ Redis is running" -ForegroundColor Green
} else {
    Write-Host "❌ Redis is not running. Starting Redis in WSL..." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this in WSL terminal:" -ForegroundColor Yellow
    Write-Host "  bash start_redis.sh" -ForegroundColor White
    Write-Host ""
    Write-Host "Or run this command:" -ForegroundColor Yellow
    Write-Host "  wsl bash start_redis.sh" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Start Redis now? (y/n)"
    if ($response -eq 'y') {
        wsl bash start_redis.sh
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Please start Redis manually and re-run this script" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Check if Ollama is running
Write-Host ""
Write-Host "[2/5] Checking Ollama LLM..." -ForegroundColor Yellow
try {
    $ollamaCheck = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama is not running (optional for smoke test)" -ForegroundColor Yellow
    Write-Host "   Questions will not generate, but infrastructure will be tested" -ForegroundColor Gray
}

# Step 3: Start Flask Backend
Write-Host ""
Write-Host "[3/5] Starting Flask Backend..." -ForegroundColor Yellow
$flaskJob = Start-Job -ScriptBlock {
    Set-Location "c:\Users\Sketch\Desktop\proctoAi"
    $env:CELERY_BROKER_URL = 'redis://172.26.79.185:6380/0'
    $env:FLASK_APP = 'backend.app'
    python -m flask run --host=127.0.0.1 --port=5000
}
Write-Host "✅ Flask started (Job ID: $($flaskJob.Id))" -ForegroundColor Green
Start-Sleep -Seconds 3

# Step 4: Start Celery Worker
Write-Host ""
Write-Host "[4/5] Starting Celery Worker..." -ForegroundColor Yellow
$celeryJob = Start-Job -ScriptBlock {
    Set-Location "c:\Users\Sketch\Desktop\proctoAi"
    $env:CELERY_BROKER_URL = 'redis://172.26.79.185:6380/0'
    celery -A backend.celery_app worker --loglevel=info --pool=solo
}
Write-Host "✅ Celery started (Job ID: $($celeryJob.Id))" -ForegroundColor Green
Start-Sleep -Seconds 3

# Step 5: Run Smoke Test
Write-Host ""
Write-Host "[5/5] Running Smoke Test..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

python tests\smoke_test_production.py

# Cleanup
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Cleaning up background jobs..." -ForegroundColor Yellow
Stop-Job -Id $flaskJob.Id
Stop-Job -Id $celeryJob.Id
Remove-Job -Id $flaskJob.Id
Remove-Job -Id $celeryJob.Id
Write-Host "✅ Cleanup complete" -ForegroundColor Green
Write-Host ""
Write-Host "Smoke test finished!" -ForegroundColor Cyan
