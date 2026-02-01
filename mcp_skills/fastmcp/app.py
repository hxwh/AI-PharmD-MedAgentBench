"""FastMCP application instance for PharmAgent.

Supports two agent types:
- Green Agent: FHIR tools + evaluation tools (groundtruth access)
- Purple Agent: FHIR tools only (clinical reasoning)

The agent type is set via environment variable AGENT_TYPE or --agent-type flag.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from fastmcp import FastMCP


class AgentType(Enum):
    """Agent type determines which tools are available."""
    GREEN = "green"   # FHIR + evaluation tools (groundtruth access)
    PURPLE = "purple"  # FHIR tools only (clinical reasoning)


# FHIR API base URL
FHIR_API_BASE = os.environ.get("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")

# Agent type from environment (can be overridden by CLI flag)
AGENT_TYPE = AgentType(os.environ.get("AGENT_TYPE", "purple").lower())


def _get_instructions(agent_type: AgentType) -> str:
    """Get MCP instructions based on agent type."""
    base_instructions = """
PharmAgent MCP Server - FHIR Tools for Clinical Workflows

Available Tool Categories:
1. Patient Search - Find patients by demographics
2. Clinical Read - Get lab values, conditions, medications, vitals
3. Clinical Write - Create observations, medication requests, service requests
4. Utilities - Date calculations, lab value evaluations

Lab Codes:
- GLU: Blood glucose
- K: Potassium
- MG: Magnesium
- HBA1C/A1C: Glycated hemoglobin

For best results:
- Use get_latest_lab_value() for recent lab values
- Use get_patient_conditions() for problem lists
- Use combined tools instead of passing large JSON between calls
"""
    
    if agent_type == AgentType.GREEN:
        return base_instructions + """

GREEN AGENT MODE:
You have access to evaluation tools that can verify your clinical decisions 
against groundtruth answers. Use these tools to validate your responses.

Additional Tools:
- evaluate_task_result: Validate task results against expected answers
- get_task_groundtruth: Get reference solution for a task (for self-evaluation)
"""
    else:
        return base_instructions + """

PURPLE AGENT MODE:
You are in clinical reasoning mode. You must rely entirely on your medical 
knowledge and the FHIR data to make clinical decisions. No groundtruth 
or evaluation tools are available.

Focus on:
- Careful clinical reasoning
- Evidence-based decision making
- Appropriate use of FHIR data
"""


def create_mcp_server(agent_type: Optional[AgentType] = None) -> FastMCP:
    """Create FastMCP server instance for the specified agent type.
    
    Args:
        agent_type: Agent type (defaults to AGENT_TYPE env var)
    
    Returns:
        Configured FastMCP server instance
    """
    if agent_type is None:
        agent_type = AGENT_TYPE
    
    name = f"PharmAgent MCP Server ({agent_type.value.upper()})"
    instructions = _get_instructions(agent_type)
    
    return FastMCP(name=name, instructions=instructions)


# Default server instance - tools register to this via decorators
mcp = create_mcp_server()
