# Multi-Stage Production Dockerfile for WeatherGPT
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend /app/backend
COPY frontend /app/frontend
COPY run_app.py /app/run_app.py
COPY README.md /app/README.md

# Create non-root user for security hardening
RUN useradd -u 1001 -m weathergpt && \
    chown -R weathergpt:weathergpt /app

USER weathergpt

# Expose HTTP / WebSocket API port
EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Launch uvicorn production server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
