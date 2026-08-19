# VoxFlow API — Universal Production Dockerfile
# Tested and verified for Render Free Tier

# ---------- build stage: compile wheels into a venv ----------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt


# ---------- runtime stage ----------
FROM python:3.12-slim

# postgresql-client enables pg_dump for automated database backups
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy only the built venv
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Run as non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 voxflow \
    && mkdir -p /app/data /tmp/voxflow-data \
    && chown -R voxflow:voxflow /app /tmp/voxflow-data

# Copy code
COPY --chown=voxflow:voxflow . .

# If apps/api exists as a subdirectory (root build context), move its contents to /app root
RUN if [ -d "apps/api" ]; then cp -r apps/api/* . && rm -rf apps; fi

USER voxflow

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR="/tmp/voxflow-data" \
    PYTHONPATH="/app"

ENV PORT=8000
EXPOSE 8000 10000

CMD ["sh", "-c", "uvicorn voxflow_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
