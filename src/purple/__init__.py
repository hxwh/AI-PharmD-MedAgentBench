"""Purple Agent - LLM-based medical agent using FHIR tools via MCP.

This module provides the Purple Agent implementation that:
1. Connects to MCP server to discover FHIR tools
2. Uses LLM (Gemini) to call tools and answer medical queries
3. Communicates via A2A protocol
"""

from .agent import MCPAgentNode, Agent
from .executor import Executor

__all__ = ["MCPAgentNode", "Agent", "Executor"]
