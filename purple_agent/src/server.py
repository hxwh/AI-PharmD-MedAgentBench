"""A2A server for Purple Agent - Pharmacist AI agent using FHIR tools."""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

# Add src directory to Python path for imports
src_dir = os.path.dirname(os.path.dirname(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv, find_dotenv
    # Try to find .env file by searching upward from current directory
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)
except ImportError:
    pass

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from starlette.routing import Route
from starlette.responses import JSONResponse

from executor import Executor


def main():
    """Run the Purple Agent server."""
    parser = argparse.ArgumentParser(
        description="Purple Agent - Pharmacist AI agent using FHIR tools via MCP"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("PURPLE_AGENT_HOST", "0.0.0.0"),
        help="Host to bind the server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PURPLE_AGENT_PORT", "9019")),
        help="Port to bind the server (default: 9019)"
    )
    parser.add_argument(
        "--card-url",
        type=str,
        help="URL to advertise in the agent card"
    )
    args = parser.parse_args()

    # Define agent skill
    skill = AgentSkill(
        id="fhir_tools",
        name="FHIR Tools",
        description=(
            "Access FHIR data via MCP (Model Context Protocol). "
            "Can retrieve patient information, lab values, medications, conditions, "
            "and perform medical record operations."
        ),
        tags=["medical", "fhir", "mcp", "pharmacist", "clinical"],
        examples=[
            "Retrieve patient's latest blood glucose level",
            "Get patient's current medication list",
            "Find patient's problem list",
            "Check lab values within a time period"
        ]
    )

    # Determine agent card URL (prioritize: arg > env var > default)
    card_url = (
        args.card_url or
        os.getenv("PURPLE_AGENT_CARD_URL") or
        f"http://localhost:{args.port}/"
    )

    # Create agent card
    agent_card = AgentCard(
        name="PharmD Purple Agent",
        description=(
            "A pharmacist AI agent that uses FHIR tools to answer clinical questions "
            "and perform medical record operations. Powered by Gemini LLM and MCP (Model Context Protocol) "
            "for secure FHIR data access."
        ),
        url=card_url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill]
    )
    
    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=Executor(),
        task_store=InMemoryTaskStore(),
    )
    
    # Create A2A server
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    print(f"🟣 Starting Purple Agent on {args.host}:{args.port}")
    print(f"   Agent card URL: {agent_card.url}")
    
    # Build the app
    app = server.build()
    
    # Add GET handler for root path
    async def root_handler(request):
        return JSONResponse({
            "name": "PharmD Purple Agent",
            "description": "A pharmacist AI agent that uses FHIR tools to answer clinical questions",
            "agent_card": f"{card_url}.well-known/agent-card.json",
            "endpoints": {
                "GET /.well-known/agent-card.json": "Get agent card",
                "POST /": "Send A2A protocol message"
            }
        })
    
    # Add GET route for root (only GET, POST is already handled by A2A)
    app.router.routes.insert(0, Route("/", root_handler, methods=["GET"]))
    
    # Run server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
