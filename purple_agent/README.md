# PharmD Purple Agent

A pharmacist AI agent that uses FHIR tools to answer clinical questions and perform medical record operations. Built using the [A2A (Agent-to-Agent)](https://a2a-protocol.org/latest/) protocol and MCP (Model Context Protocol).

## Features

- **FHIR Integration**: Access patient data, lab values, medications, and conditions via MCP
- **LLM-Powered**: Uses Google Gemini for intelligent medical reasoning
- **A2A Protocol**: Standard agent-to-agent communication
- **Tool Discovery**: Automatically discovers available FHIR tools from MCP server

## Project Structure

```
purple_agent/
├── src/
│   ├── server.py      # A2A server setup and agent card configuration
│   ├── executor.py    # A2A request handling
│   ├── agent.py       # Agent implementation with MCP integration
│   └── messenger.py   # A2A messaging utilities
├── tests/
│   ├── conftest.py    # Test configuration
│   └── test_agent.py  # Agent tests
├── Dockerfile         # Docker configuration
├── pyproject.toml     # Python dependencies
└── .env.example       # Environment variables template
```

## Requirements

- Python 3.10+
- Google API Key (for Gemini LLM)
- MCP Server running (mcp_skills)
- FHIR Server (optional, for real data)

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GOOGLE_API_KEY=your_google_api_key

# Optional
PURPLE_AGENT_HOST=0.0.0.0
PURPLE_AGENT_PORT=9019
PURPLE_AGENT_CARD_URL=http://localhost:9019/
MCP_FHIR_API_BASE=http://localhost:8080/fhir/
MCP_SERVER_CWD=/path/to/pharmd
MAX_ROUNDS=10
```

## Running Locally

```bash
# Install dependencies
pip install -e .

# Run the server
python src/server.py

# Or with custom port
python src/server.py --port 9020
```

## Running with Docker

```bash
# Build the image
docker build -t pharmai-purple-agent .

# Run the container
docker run -p 9019:9019 \
  -e GOOGLE_API_KEY=your_key \
  pharmai-purple-agent
```

## Testing

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest --agent-url http://localhost:9019
```

## API

### Agent Card

```
GET /.well-known/agent-card.json
```

Returns the agent's capabilities and metadata.

### Send Message

```
POST /
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [{"kind": "text", "text": "What is the patient's latest blood glucose?"}]
    }
  }
}
```

## Agent Skills

- **FHIR Tools**: Access patient information, lab values, medications, conditions
- **Medical Reasoning**: Clinical decision support using Gemini LLM
- **Tool Calling**: Automatic tool discovery and execution via MCP

## License

MIT
