# Multi-stage build for optimized image size
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash apiuser

FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /tmp/

# Install all dependencies properly
# First install numpy < 2.0 to ensure compatibility
RUN pip3 install --no-cache-dir --user "numpy<2.0,>=1.21.0"

# Install all requirements including dev diffusers
RUN pip3 install --no-cache-dir --user -r /tmp/requirements.txt

# Install additional packages that might be missing
RUN pip3 install --no-cache-dir --user starlette

FROM base AS runtime

# Copy installed packages from builder
COPY --from=builder /root/.local /home/apiuser/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=apiuser:apiuser app/ /app/
COPY --chown=apiuser:apiuser config/ /app/config/
COPY --chown=apiuser:apiuser scripts/ /app/scripts/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py || true

# Create necessary directories
RUN mkdir -p /app/outputs /app/logs /app/models && \
    chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Add local bin to PATH
ENV PATH="/home/apiuser/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Environment variables
ENV HF_HOME=/app/models \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Start with gunicorn
CMD ["gunicorn", "api_server:app", "--config", "/app/config/gunicorn_config.py", "--bind", "0.0.0.0:8000"]
