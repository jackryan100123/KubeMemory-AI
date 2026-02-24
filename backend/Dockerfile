# ============================================================
# Stage 1: Dependency installer
# Install Python packages in isolation — keeps build cache clean
# ============================================================
FROM python:3.11-slim-bookworm AS deps

WORKDIR /deps

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/prod.txt ./
RUN pip install --no-cache-dir --prefix=/install -r prod.txt

# ============================================================
# Stage 2: Builder — run tests, compile assets
# ============================================================
FROM python:3.11-slim-bookworm AS builder

COPY --from=deps /install /install
WORKDIR /app
COPY . .

# Run tests (comment out if you want faster builds during dev)
# RUN PYTHONPATH=/install/lib/python3.11/site-packages python -m pytest --tb=short

# ============================================================
# Stage 3: Runtime — minimal, non-root, no dev tools
# ============================================================
FROM python:3.11-slim-bookworm AS runtime

# Security: install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# Security: create non-root user
RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Copy installed packages from deps (builder does not add more packages)
COPY --from=deps /install /usr/local

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create required directories with correct ownership
RUN mkdir -p /app/static /app/media /app/chroma_data \
    && chown -R appuser:appuser /app

# Switch to non-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/agents/status/ || exit 1

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
