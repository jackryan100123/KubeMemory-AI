# Stage 1: dependency resolver
FROM python:3.11-slim-bookworm AS deps
WORKDIR /deps
COPY requirements/base.txt requirements/prod.txt ./
RUN pip install --no-cache-dir -r prod.txt --target /install

# Stage 2: builder (compile any C extensions)
FROM python:3.11-slim-bookworm AS builder
COPY --from=deps /install /install

# Stage 3: runtime (minimal image)
FROM python:3.11-slim-bookworm AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && apt-get update -qq && apt-get install -y -qq --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
WORKDIR /app
COPY . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && chown -R appuser:appuser /app
ENTRYPOINT ["/docker-entrypoint.sh"]
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
