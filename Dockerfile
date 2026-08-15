# ─────────────────────────────────────────────────────────────────────────────
# GitHub Analyzer MCP Server — Dockerfile
#
# Build:  docker build -t github-analyzer-mcp .
# Run:    docker run -p 8000:8000 --env-file .env github-analyzer-mcp
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Install dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System packages needed for some wheels
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Isolated venv so we can copy it cleanly into the runtime image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy the pre-built venv
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code only (no .env — secrets come from env vars at runtime)
COPY src/ ./src/
COPY server.py .

# HTTP transport port
EXPOSE 8000

USER appuser

# Healthcheck — calls the /mcp endpoint (MCP streamable HTTP)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/mcp')" \
        || exit 1

# Run in HTTP transport mode so Docker clients can connect over the network
# (stdio transport requires subprocess launch — only works locally)
CMD ["python", "server.py", "--http", "--host", "0.0.0.0", "--port", "8000"]
