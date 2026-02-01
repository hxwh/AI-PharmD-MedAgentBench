# PharmAgent MCP Server Docker Image
# Supports both Green (with eval tools) and Purple (clinical only) agent types

FROM python:3.11-slim

# Build args for agent type
ARG AGENT_TYPE=purple

# Create non-root user
RUN adduser --disabled-password --gecos '' agent
USER agent
WORKDIR /home/agent

# Copy project structure
COPY --chown=agent:agent mcp_skills/ ./mcp_skills/

# Install dependencies
RUN pip install --no-cache-dir --user \
    fastmcp>=2.0.0 \
    httpx>=0.28.1 \
    pydantic>=2.11.9 \
    uvicorn>=0.38.0

# Set Python path
ENV PATH="/home/agent/.local/bin:${PATH}"
ENV PYTHONPATH="/home/agent:${PYTHONPATH}"

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV MCP_FHIR_API_BASE=http://host.docker.internal:8080/fhir/
ENV AGENT_TYPE=${AGENT_TYPE}

EXPOSE 8002

# Entry point - uses AGENT_TYPE from environment
CMD ["python", "-m", "mcp_skills.fastmcp.server", "--host", "0.0.0.0", "--port", "8002"]
