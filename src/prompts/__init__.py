"""Centralized prompt management for MedAgentBench."""
from pathlib import Path

_DIR = Path(__file__).parent


def load(name: str) -> str:
    """Load prompt by name (without extension)."""
    path = _DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text()


# Pre-load common prompts
def agent() -> str:
    """Agent prompt template (static tool list)."""
    return load("agent")


def agent_dynamic() -> str:
    """Agent prompt template with {tools} placeholder for dynamic discovery."""
    return load("agent_dynamic")


def mcp() -> str:
    """MCP server instructions."""
    return load("mcp")
