# Quick Start Guide

## One-Click Startup (Recommended)

Simply run this command in PowerShell:

```powershell
cd c:\Users\Sketch\Desktop\proctoAi
.\start_all.ps1
```

This will automatically:
1. ✅ Start Redis in WSL (port 6380)
2. ✅ Check/Start Ollama (port 11434)
3. ✅ Start Flask Backend (port 5000)
4. ✅ Start Celery Worker
5. ✅ Start React Frontend (port 3000)
6. 🌐 Open browser to http://localhost:3000

**To stop all services:** Press any key in the script window.

---

## Manual Startup (For Debugging)

### Terminal 1: Redis (WSL)
```bash
bash start_redis.sh
```

### Terminal 2: Flask Backend
```powershell
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
$env:FLASK_APP='backend.app'
python -m flask run --host=127.0.0.1 --port=5000
```

### Terminal 3: Celery Worker
```powershell
$env:CELERY_BROKER_URL='redis://172.26.79.185:6380/0'
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

### Terminal 4: Frontend
```powershell
cd frontend
npm start
```

---

## Access Points

- **Frontend (Student/Admin):** http://localhost:3000
- **Backend API:** http://127.0.0.1:5000
- **API Docs (Swagger):** http://127.0.0.1:5000/apidocs
- **Ollama:** http://localhost:11434

---

## Default Credentials

Create admin user:
```powershell
python backend/create_super_admin.py
```

---

## Troubleshooting

### Port Already in Use
```powershell
# Kill Flask (port 5000)
Get-NetTCPConnection -LocalPort 5000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force

# Kill Frontend (port 3000)
Get-NetTCPConnection -LocalPort 3000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force
```

### Redis Not Connecting
```bash
# In WSL
redis-cli -h 172.26.79.185 -p 6380 ping
# Should return: PONG
```

### Ollama GPU Issues
```powershell
# Restart Ollama
Get-Process | Where-Object {$_.ProcessName -like "*ollama*"} | Stop-Process -Force
ollama serve
```

---

## Running Tests

### Smoke Test (Full System)
```powershell
python tests\smoke_test_production.py
```

### Health Check
```powershell
python check_services.py
```
