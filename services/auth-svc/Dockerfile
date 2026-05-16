FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

# App code
COPY app/ app/

# Non-root user
RUN useradd -m svc && chown -R svc:svc /app
USER svc

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8001/health'); assert r.status_code==200"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
