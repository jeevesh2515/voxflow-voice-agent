# VoxFlow API — lean production image.
#
# Builds on both x86_64 and ARM64 (Oracle Cloud's Always Free tier is Ampere
# A1, which is ARM). All wheels used here publish aarch64 manylinux builds.
#
# No build-essential, no ffmpeg, no git: speech-to-text runs on Groq's hosted
# Whisper rather than a local model, and PyAV bundles its own FFmpeg libraries
# in the wheel. That takes the image from ~2.5GB to roughly 250MB.

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

# Copy only the built venv — none of the build tooling comes with it.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Run as a non-root user. This process is reachable from the public internet
# via the Twilio webhook, so it should not be root.
RUN useradd --create-home --shell /bin/bash --uid 1000 voxflow
COPY --chown=voxflow:voxflow . .
USER voxflow

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# One worker on purpose: call state (_call_meta, per-stream buffers, the STT
# singleton) lives in process memory, so a second worker would drop calls whose
# webhook and WebSocket landed on different processes. Scale by adding
# instances behind a sticky load balancer, not by adding workers here.
CMD ["uvicorn", "voxflow_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
