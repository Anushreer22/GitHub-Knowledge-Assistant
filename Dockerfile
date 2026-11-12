# GitHub Knowledge Assistant - Backend Production Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and metadata
COPY dataset_pipeline/ ./dataset_pipeline/
COPY retrieval/ ./retrieval/
COPY backend/ ./backend/
COPY models/ ./models/
COPY data/metadata/ ./data/metadata/
COPY data/indexes/ ./data/indexes/
COPY data/processed/ ./data/processed/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
