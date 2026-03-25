# System Smoke Test Guide

## Prerequisites

Before running the smoke test, you need to start the following services:

### 1. Start Redis (if not already running)
Redis should be running on `172.26.79.185:6380`

### 2. Start Flask Backend
Open a terminal and run:
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
$env:FLASK_APP='backend.app'
$env:FLASK_ENV='development'
python -m flask run --host=127.0.0.1 --port=5000
```

**Expected Output:**
```
 * Serving Flask app 'backend.app'
 * Running on http://127.0.0.1:5000
```

### 3. Start Celery Worker
Open a **second terminal** and run:
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

**Expected Output:**
```
[tasks]
  . backend.generation_tasks.generate_batch_task
celery@HOSTNAME ready.
```

### 4. Run Smoke Test
Open a **third terminal** and run:
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
python tests\smoke_test_production.py
```

---

## What the Smoke Test Verifies

The smoke test performs the following checks:

1. ✅ **Database Access**: Creates a test admin user
2. ✅ **Authentication**: Logs in and receives JWT token
3. ✅ **API Endpoint**: Calls `/api/generate_questions_universal`
4. ✅ **Celery Dispatch**: Verifies job is queued
5. ✅ **Redis Status**: Polls `/api/generation_status/{job_id}`
6. ✅ **Worker Processing**: Confirms Celery worker picks up task
7. ✅ **Question Generation**: Generates 20 MCQ questions
8. ✅ **Terminal State**: Reaches 'completed', 'partial', or 'failed'

---

## Expected Results

### ✅ Success (Best Case)
```
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
[4/30] Status: processing | Progress: 15/20
[5/30] Status: completed | Progress: 20/20

Terminated with status: completed
✅ SMOKE TEST PASSED: Full Success
```

### ⚠️ Partial Success (Acceptable)
```
Terminated with status: partial
✅ SMOKE TEST PASSED: Partial Success (Safety check worked)
```
This means some questions were generated successfully, but not all. This is acceptable and shows the error handling is working.

### ❌ Failure Scenarios

**Backend Not Running:**
```
ConnectionRefusedError: [WinError 10061] No connection could be made
```
**Solution:** Start Flask backend (see step 2 above)

**Celery Not Running:**
```
[30/30] Status: queued | Progress: 0/20
❌ SMOKE TEST FAILED: Timeout waiting for terminal state
```
**Solution:** Start Celery worker (see step 3 above)

**Redis Not Running:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```
**Solution:** Start Redis on WSL or Windows

---

## Quick Start (All-in-One)

If you want to run everything at once, use PowerShell with multiple panes or run this batch script:

```powershell
# Terminal 1: Flask
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd c:\Users\Sketch\Desktop\proctoAi; `$env:FLASK_APP='backend.app'; python -m flask run --host=127.0.0.1 --port=5000"

# Terminal 2: Celery
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd c:\Users\Sketch\Desktop\proctoAi; `$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'; celery -A backend.celery_app worker --loglevel=info --pool=solo"

# Wait for services to start
Start-Sleep -Seconds 5

# Terminal 3: Smoke Test
python tests\smoke_test_production.py
```

---

## Troubleshooting

### Issue: "Module not found"
**Solution:** Make sure you're in the project root directory:
```powershell
cd c:\Users\Sketch\Desktop\proctoAi
```

### Issue: "Port 5000 already in use"
**Solution:** Kill the existing Flask process:
```powershell
Get-Process -Name python | Where-Object {$_.Path -like "*flask*"} | Stop-Process
```

### Issue: "Celery worker crashes immediately"
**Solution:** Check Redis connection:
```powershell
redis-cli -h 172.26.79.185 -p 6380 ping
```
Should return `PONG`

### Issue: "Questions not generating (stuck at 0/20)"
**Solution:** Check Ollama is running:
```powershell
curl http://localhost:11434/api/tags
```
Should return list of models including `llama3.1`
