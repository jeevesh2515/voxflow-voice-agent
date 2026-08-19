# VoxFlow API — production image (Root Build Context)
# Compatible with 1-click Render / Railway / Fly.io root deployments

# ---------- build stage: compile wheels into a venv ----------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY apps/api/requirements.txt requirements.txt
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

COPY --chown=voxflow:voxflow apps/api/ .
USER voxflow

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR="/tmp/voxflow-data" \
    PYTHONPATH="/app"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "voxflow_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
