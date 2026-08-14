FROM python:3.11-slim

# Install uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspace

# Copy dependency files first — Docker caches this layer
COPY pyproject.toml uv.lock ./

# Install production deps only (no dev extras)
RUN uv sync --frozen --no-dev

# Put the virtual environment on the PATH so `python` uses it by default
ENV PATH="/workspace/.venv/bin:$PATH"

# Copy full source
COPY . .

# Cloud Run sets PORT automatically
ENV PORT=8080
EXPOSE 8080

# adk web takes the parent dir of the agent module.
# Our layout: /workspace/app/agent.py  → pass /workspace as AGENTS_DIR
# CMD ["sh", "-c", "adk web --host 0.0.0.0 --port ${PORT} /workspace"]
CMD ["python", "-m", "app.mcp_servers.bigquery_mcp"]
