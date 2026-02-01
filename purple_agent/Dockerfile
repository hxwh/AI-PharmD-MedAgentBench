# MedAgentBench Purple Agent (Agent Under Test) Docker Image
# Following AgentBeats standard Dockerfile pattern
# See: https://github.com/RDI-Foundation/agentbeats-tutorial

FROM ghcr.io/astral-sh/uv:python3.11-bookworm

ENV UV_HTTP_TIMEOUT=300

# Create non-root user
RUN adduser --disabled-password --gecos '' agentbeats
USER agentbeats
WORKDIR /home/agentbeats/medagentbench

# Copy project files
COPY --chown=agentbeats:agentbeats pyproject.toml uv.lock README.md ./

# Copy source code
COPY --chown=agentbeats:agentbeats src src

# Install dependencies with uv (locked)
RUN --mount=type=cache,target=/home/agentbeats/.cache/uv,uid=1000 \
    uv sync --locked --no-dev --no-install-project

# ENTRYPOINT accepts --host, --port, --card-url as per AgentBeats standard
ENTRYPOINT ["uv", "run", "src/server.py"]
CMD ["--host", "0.0.0.0", "--port", "9019"]
EXPOSE 9019
