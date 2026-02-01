# MedAgentBench Green Agent (Evaluator) Docker Image
# Following AgentBeats standard Dockerfile pattern
# See: https://github.com/RDI-Foundation/agentbeats-tutorial

FROM ghcr.io/astral-sh/uv:python3.11-bookworm

ENV UV_HTTP_TIMEOUT=300

# Create non-root user
RUN adduser --disabled-password --gecos '' agentbeats

# Copy project files (as root first)
COPY pyproject.toml uv.lock README.md ./
COPY src src
COPY config config
COPY mcp_skills mcp_skills
COPY purple_agent purple_agent

# Install dependencies as root, then clean up
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e mcp_skills && \
    uv pip install --system -e purple_agent && \
    uv pip install --system \
        "a2a-sdk[http-server]>=0.3.20" \
        "httpx>=0.28.1" \
        "pocketflow>=0.0.1" \
        "pydantic>=2.11.9" \
        "python-dotenv>=1.1.1" \
        "uvicorn>=0.38.0" \
        "google-genai>=1.36.0" \
        "fastmcp>=2.0.0" \
        "pyyaml>=6.0"

# Change ownership to agentbeats user
RUN chown -R agentbeats:agentbeats /home/agentbeats

# Switch to non-root user
USER agentbeats
WORKDIR /home/agentbeats/medagentbench

# ENTRYPOINT accepts --host, --port, --card-url as per AgentBeats standard
ENTRYPOINT ["uv", "run", "src/server.py"]
CMD ["--host", "0.0.0.0"]
EXPOSE 9009
