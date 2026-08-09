# ============================================================
# Dockerfile for Fake News Detector — Production API
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies only (not spacy/streamlit/training deps)
COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-deploy.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim as runtime

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs models data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check (P4-4 FIX: use stdlib — requests is not in requirements-deploy.txt)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"


EXPOSE 8000

# Run the FastAPI production server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
