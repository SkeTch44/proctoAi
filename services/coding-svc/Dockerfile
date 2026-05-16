FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

COPY app/ app/

RUN useradd -m svc && chown -R svc:svc /app
USER svc

EXPOSE 8005

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8005/health'); assert r.status_code==200"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "2"]
