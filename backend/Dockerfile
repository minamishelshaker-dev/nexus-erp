# ========================================
# Nexus ERP - Backend Dockerfile
# ========================================
# Multi-stage production-ready Dockerfile
# Base: Python 3.11-slim
# ========================================

# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Production
# ========================================
FROM python:3.11-slim as production

# Labels
LABEL maintainer="Nexus ERP Team"
LABEL version="1.0.0"
LABEL description="Nexus ERP Backend API"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=nexus:nexus . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs && \
    chown -R nexus:nexus /app/uploads /app/logs

# Switch to non-root user
USER nexus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with gunicorn for production
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]

# ========================================
# Stage 3: Development
# ========================================
FROM production as development

# Switch back to root for development setup
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    debugpy \
    pytest-watch

# Set development environment
ENV ENVIRONMENT=development \
    DEBUG=true

# Switch back to nexus user
USER nexus

# Run with hot reload
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]
