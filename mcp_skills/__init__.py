"""PharmAgent Skill MCP Agent.

MCP Server providing FHIR tools for clinical workflows with support for
two agent types:

- Green Agent: FHIR tools + evaluation tools (groundtruth access)
- Purple Agent: FHIR tools only (clinical reasoning mode)

Usage:
    # Purple agent (default)
    python -m mcp_skills.fastmcp.server
    
    # Green agent with evaluation tools
    python -m mcp_skills.fastmcp.server --agent-type green

    # With custom FHIR server
    MCP_FHIR_API_BASE=http://fhir.example.com/fhir/ python -m mcp_skills.fastmcp.server
"""
from .fastmcp.app import mcp, FHIR_API_BASE, AgentType

__version__ = "1.0.0"
__all__ = ["mcp", "FHIR_API_BASE", "AgentType"]
