"""Mock Purple Agent for testing Green Agent locally."""

import asyncio
import json
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    import pathlib
    # Load .env from project root (two levels up from examples/)
    env_path = pathlib.Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip
except Exception:
    pass  # .env file not found, skip

app = FastAPI()

# Simple mock that returns correct answers
MOCK_RESPONSES = {
    "task_001": "Based on the FHIR query, the patient's latest blood glucose level is FINISH([191])",
    "task_002": "After checking the medication records, the patient is taking FINISH([\"Metformin\", \"Insulin\"])",
}


class Message(BaseModel):
    kind: str = "message"
    role: str = "user"
    parts: list
    message_id: str
    context_id: Optional[str] = None


@app.get("/.well-known/agent-card.json")
async def agent_card():
    """Return agent card."""
    import os
    # Use environment variable if set, otherwise localhost
    card_url = os.getenv("PURPLE_AGENT_CARD_URL", "http://localhost:9019/")

    return {
        "name": "Mock Purple Agent",
        "description": "Mock agent for testing",
        "url": card_url,
        "version": "0.1.0",
        "default_input_modes": ["text"],
        "default_output_modes": ["text"],
        "capabilities": {"streaming": False},
        "skills": []
    }


@app.get("/")
async def root():
    """Return info about the agent."""
    card_url = os.getenv("PURPLE_AGENT_CARD_URL", "http://localhost:9019/")
    return {
        "name": "Mock Purple Agent",
        "description": "Mock agent for testing MedAgentBench",
        "agent_card": f"{card_url}.well-known/agent-card.json",
        "endpoints": {
            "GET /.well-known/agent-card.json": "Get agent card",
            "POST /": "Send A2A protocol message"
        }
    }


@app.post("/")
async def handle_message(request: dict):
    """Handle A2A message."""
    print(f"📨 Received request: {json.dumps(request, indent=2)[:200]}...")
    
    # Extract message
    params = request.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])
    
    if not parts:
        return {"error": "No message parts"}
    
    # Get text content
    text = parts[0].get("text", "") if parts else ""
    print(f"📝 Message text: {text[:200]}...")
    
    # Determine which task based on content
    response_text = "FINISH([\"unknown\"])"
    if "blood glucose" in text.lower():
        response_text = MOCK_RESPONSES["task_001"]
    elif "medication" in text.lower():
        response_text = MOCK_RESPONSES["task_002"]
    
    print(f"✅ Responding with: {response_text}")
    
    # Get context_id, ensuring it's a string or None
    context_id = message.get("context_id")
    if context_id is None:
        # Generate a new context_id if none provided
        from uuid import uuid4
        context_id = str(uuid4())
    
    # Return A2A response
    return {
        "jsonrpc": "2.0",
        "result": {
            "kind": "message",
            "role": "agent",
            "parts": [
                {
                    "kind": "text",
                    "text": response_text
                }
            ],
            "message_id": "mock_response_001",
            "context_id": context_id
        },
        "id": request.get("id")
    }


if __name__ == "__main__":
    import uvicorn
    import os

    # Get configuration from environment
    host = os.getenv("PURPLE_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("PURPLE_AGENT_PORT", "9019"))

    print(f"🟣 Starting Mock Purple Agent on http://{host}:{port}")
    print("This agent will return correct answers for testing")
    print(f"Accessible from: http://localhost:{port} or remote IP:{port}")
    uvicorn.run(app, host=host, port=port)
