"""A2A server for MedAgentBench Green Agent."""

import argparse
import os
import sys
import uvicorn

# Add src directory to Python path for imports
src_dir = os.path.dirname(os.path.dirname(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    import pathlib
    # Load .env from project root (one level up from src/)
    env_path = pathlib.Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip
except Exception:
    pass  # .env file not found, skip

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
    """Run the MedAgentBench Green Agent server."""
    parser = argparse.ArgumentParser(
        description="MedAgentBench Green Agent - Medical reasoning task evaluator"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("GREEN_AGENT_HOST", "127.0.0.1"),
        help="Host to bind the server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("GREEN_AGENT_PORT", "9009")),
        help="Port to bind the server (default: 9009)"
    )
    parser.add_argument(
        "--card-url",
        type=str,
        help="URL to advertise in the agent card"
    )
    args = parser.parse_args()

    # Define agent skill
    skill = AgentSkill(
        id="medagentbench-evaluation",
        name="Medical Reasoning Task Evaluation",
        description=(
            "Evaluates medical AI agents on clinical reasoning tasks using FHIR data. "
            "Provides comprehensive assessment with failure taxonomy and detailed metrics."
        ),
        tags=["medical", "evaluation", "fhir", "clinical-reasoning", "benchmark"],
        examples=[
            "Evaluate an agent's ability to retrieve patient blood glucose levels",
            "Assess medication list retrieval accuracy",
            "Test clinical reasoning with FHIR resources"
        ]
    )

    # Determine agent card URL (prioritize: arg > env var > default)
    card_url = (
        args.card_url or
        os.getenv("GREEN_AGENT_CARD_URL") or
        f"http://localhost:{args.port}/"
    )

    # Create agent card
    agent_card = AgentCard(
        name="MedAgentBench Green Agent",
        description=(
            "Green agent (evaluator) for MedAgentBench - a benchmark for evaluating "
            "medical LLM agents on clinical reasoning tasks. Orchestrates task execution, "
            "communicates with agents under test via A2A protocol, provides FHIR tools via MCP, "
            "and returns comprehensive evaluation results with failure taxonomy."
        ),
        url=card_url,
        version='0.1.0',
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
    
    print(f"Starting MedAgentBench Green Agent on {args.host}:{args.port}")
    print(f"Agent card URL: {agent_card.url}")
    
    # Build the app
    app = server.build()
    
    # Add GET handler for root path
    async def root_handler(request):
        return JSONResponse({
            "name": "MedAgentBench Green Agent",
            "description": "Green agent (evaluator) for MedAgentBench - a benchmark for evaluating medical LLM agents",
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
