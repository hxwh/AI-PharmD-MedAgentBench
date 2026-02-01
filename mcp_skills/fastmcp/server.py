"""FastMCP server for PharmAgent.

MCP (Model Context Protocol) server providing FHIR tools for clinical workflows.
Supports two agent types via --agent-type flag:

- green: FHIR tools + evaluation tools (groundtruth access for validation)
- purple: FHIR tools only (clinical reasoning without groundtruth)

Usage:
    # Purple agent (default) - clinical reasoning only
    python -m mcp_skills.fastmcp.server
    
    # Green agent - with evaluation/groundtruth tools
    python -m mcp_skills.fastmcp.server --agent-type green
    
    # stdio transport for MCP Inspector
    python -m mcp_skills.fastmcp.server --stdio

Environment Variables:
    MCP_FHIR_API_BASE: FHIR server base URL (default: http://localhost:8080/fhir/)
    AGENT_TYPE: Default agent type if --agent-type not specified
"""
from __future__ import annotations

import argparse
import os

from .app import mcp, FHIR_API_BASE, AgentType, create_mcp_server


def main() -> None:
    """Run the PharmAgent MCP Server."""
    parser = argparse.ArgumentParser(
        description="PharmAgent MCP Server - FHIR tools for clinical workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Agent Types:
    green   - FHIR tools + evaluation tools (groundtruth access)
    purple  - FHIR tools only (clinical reasoning mode)

Examples:
    # Purple agent (default)
    python -m mcp_skills.fastmcp.server
    
    # Green agent with evaluation tools
    python -m mcp_skills.fastmcp.server --agent-type green

    # stdio transport for MCP Inspector
    python -m mcp_skills.fastmcp.server --stdio
    npx @modelcontextprotocol/inspector python -m mcp_skills.fastmcp.server --stdio
        """
    )
    parser.add_argument(
        "--agent-type",
        choices=["green", "purple"],
        default=os.environ.get("AGENT_TYPE", "purple").lower(),
        help="Agent type: 'green' (with eval tools) or 'purple' (clinical only)"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Use stdio transport (for MCP Inspector)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to listen on (default: 8002)"
    )
    args = parser.parse_args()
    
    # Set agent type in environment for tool registration
    agent_type = AgentType(args.agent_type)
    os.environ["AGENT_TYPE"] = agent_type.value
    
    # Import tools AFTER setting agent type - they register via decorators
    # This ensures only appropriate tools are registered
    from ..fhir import tools  # noqa: F401
    from ..fhir import resources  # noqa: F401
    from ..pokemon import tools as pokemon_tools  # noqa: F401

    # Import eval tools only for green agent
    if agent_type == AgentType.GREEN:
        from ..fhir import eval_tools  # noqa: F401
    
    if args.stdio:
        mcp.run(transport="stdio")
    else:
        # Add health endpoint for monitoring using FastMCP custom_route
        from starlette.responses import JSONResponse

        async def health_check(request):
            """Health check endpoint for monitoring."""
            return JSONResponse({
                "status": "healthy",
                "agent_type": agent_type.value,
                "fhir_api_base": FHIR_API_BASE,
                "timestamp": "2026-02-01T00:22:56Z"  # Would be dynamic in production
            })

        async def root(request):
            """Root endpoint with basic info."""
            return JSONResponse({
                "name": f"PharmAgent MCP Server ({agent_type.value.upper()} Agent)",
                "agent_type": agent_type.value,
                "fhir_api_base": FHIR_API_BASE,
                "description": "FHIR tools for clinical workflows",
                "health": "/health",
                "mcp_endpoint": "/mcp"
            })

        # Add custom routes
        mcp.custom_route("/health", methods=["GET"])(health_check)
        mcp.custom_route("/", methods=["GET"])(root)

        print("=" * 60)
        print(f"PharmAgent MCP Server ({agent_type.value.upper()} Agent)")
        print("=" * 60)
        print(f"Agent Type: {agent_type.value}")
        print(f"Transport: http")
        print(f"FHIR API base: {FHIR_API_BASE}")
        print(f"Listening on: http://{args.host}:{args.port}")
        print(f"Health check: http://{args.host}:{args.port}/health")
        print()
        if agent_type == AgentType.GREEN:
            print("Tools: FHIR + Evaluation (groundtruth access)")
        else:
            print("Tools: FHIR only (clinical reasoning mode)")
        print()
        print("Use --stdio flag for MCP Inspector")
        print("=" * 60)
        mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
