# Deployment Blueprint: ProctoAi

**Target Architecture:** Dockerized Flask + React on scalable cloud infrastructure.

## 1. Containerization Strategy

### Backend (`Dockerfile`)
```dockerfile
# Use official lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for OpenCV/Audio)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 5000

# Run with Gunicorn for production suitability
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "app:app", "--bind", "0.0.0.0:5000"]
```

## 2. Environment Configuration (`.env.production`)

```ini
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY= <GENERATED_HIGH_ENTROPY_KEY>
JWT_SECRET_KEY= <GENERATED_HIGH_ENTROPY_KEY>
GEMINI_API_KEY= <YOUR_GOOGLE_AI_KEY>
CORS_ORIGINS=https://proctoai.yourdomain.com
DATABASE_URI=sqlite:///instance/exam_platform.db
```

## 3. Production Serving

### Gunicorn Configuration
- **Workers:** 1 eventlet worker (required for Socket.IO compatibility).
- **Timeout:** Increase to 120s for long AI generation tasks.

### Nginx Reverse Proxy
- Terminate SSL at Nginx.
- Forward `/socket.io` with sticky sessions or correct headers.

## 4. Scaling Plan
- **Horizontal Scaling:** requires Redis message queue for Socket.IO sync across nodes.
- **Database:** Migrate from SQLite to PostgreSQL for concurrent exam sessions > 50.

## 5. CI/CD Pipeline Recommendations
- **Linting:** `flake8`
- **Testing:** `python -m unittest discover test`
- **Build:** `docker build -t proctoai-backend:latest .`
