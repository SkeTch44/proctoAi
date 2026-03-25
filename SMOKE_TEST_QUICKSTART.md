# Quick Start Guide for Smoke Test

## Option 1: Automated (Recommended)

### Step 1: Start Redis in WSL
Open WSL terminal and run:
```bash
cd /mnt/c/Users/Sketch/Desktop/proctoAi
bash start_redis.sh
```

### Step 2: Run Full Smoke Test
Open PowerShell and run:
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
.\run_full_smoke_test.ps1
```

This will:
- ✅ Check Redis connectivity
- ✅ Start Flask backend
- ✅ Start Celery worker
- ✅ Run smoke test
- ✅ Clean up background jobs

---

## Option 2: Manual (For Debugging)

### Terminal 1 (WSL): Start Redis
```bash
bash start_redis.sh
```

### Terminal 2 (PowerShell): Start Flask
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
$env:FLASK_APP='backend.app'
python -m flask run --host=127.0.0.1 --port=5000
```

### Terminal 3 (PowerShell): Start Celery
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

### Terminal 4 (PowerShell): Run Smoke Test
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
python tests\smoke_test_production.py
```

---

## Troubleshooting

### Redis Connection Failed
```bash
# In WSL, check if Redis is running
ps aux | grep redis

# Restart Redis
redis-cli -h 172.26.79.185 -p 6380 shutdown
bash start_redis.sh
```

### Flask/Celery Connection Error
Make sure both use the same Redis URL:
```powershell
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
```

### Port Already in Use
```powershell
# Kill Flask on port 5000
Get-NetTCPConnection -LocalPort 5000 | Select-Object -ExpandProperty OwningProcess | Stop-Process

# Kill Celery
Get-Process python | Where-Object {$_.CommandLine -like "*celery*"} | Stop-Process
```

---

## Expected Smoke Test Output

```
=== Production Smoke Test: Universal Question Engine ===

[Step 1] Creating approved admin user: smoke_test_admin_abc123
User smoke_test_admin_abc123 created (ID: 57)

[Step 2] Logging in...
Logged in. Token received.

[Step 3] Initiating Batch Generation (20 questions)...
Job started: abc123-def456-ghi789

[Step 4] Polling status...
[1/30] Status: queued | Progress: 0/20
[2/30] Status: processing | Progress: 5/20
[3/30] Status: processing | Progress: 10/20
[4/30] Status: completed | Progress: 20/20

Terminated with status: completed
✅ SMOKE TEST PASSED: Full Success
```
