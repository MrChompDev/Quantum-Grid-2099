# Quantum Grid 2099 — SSH game server image.
# Build:  docker build -t quantum-grid-2099 .
# Run:    docker run -d -p 2222:2222 -v qgrid-data:/data quantum-grid-2099
# Play:   ssh -p 2222 <this-host>
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QG_SAVE_DIR=/data/saves

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY qgrid/ qgrid/

# Non-root runtime. /data holds the SSH host key and player saves so both
# survive container restarts and rebuilds (mount a volume or bind mount here).
RUN useradd --create-home --shell /usr/sbin/nologin qgrid \
    && mkdir -p /data/saves \
    && chown -R qgrid:qgrid /app /data
USER qgrid

EXPOSE 2222
VOLUME ["/data"]

# The host key is generated inside /data on first boot if missing.
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "2222", "--host-key", "/data/ssh_host_key"]
