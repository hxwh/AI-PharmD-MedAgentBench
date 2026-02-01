"""MCP Tool Discovery - Discover tools from MCP server at runtime.

This module enables dynamic tool discovery instead of hardcoded tool lists.
The agent connects to the MCP server and queries available tools, making
the system more flexible and maintainable.

Usage:
    tools_text = await discover_tools_async("http://localhost:8002/mcp")
    # Returns formatted tool descriptions for prompt injection
"""

from typing import Any, Dict, List, Optional


async def discover_tools_async(mcp_server_url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Discover available tools from MCP server.
    
    Connects to the MCP server and retrieves the list of available tools
    with their descriptions and parameters.
    
    Args:
        mcp_server_url: MCP server URL (e.g., "http://localhost:8002/mcp")
        timeout: Request timeout in seconds
    
    Returns:
        Dict with:
        - tools: List of tool metadata
        - formatted: Pre-formatted string for prompt injection
        - count: Number of tools discovered
    
    Example:
        result = await discover_tools_async("http://localhost:8002/mcp")
        print(result["formatted"])  # Ready for prompt
    """
    # Import fastmcp Client - may fail due to circular import when src/mcp/ shadows mcp package
    try:
        from fastmcp import Client
    except ImportError as e:
        return {
            "tools": [],
            "formatted": "",
            "count": 0,
            "error": f"FastMCP Client not available: {e}"
        }
    
    try:
        # Ensure URL ends with /mcp for FastMCP Streamable-HTTP transport
        url = mcp_server_url.rstrip('/')
        if not url.endswith('/mcp'):
            url = f"{url}/mcp"
        
        # Use FastMCP Client for proper protocol handling
        client = Client(url, timeout=timeout)
        async with client:
            tools_result = await client.list_tools()
            # Convert Tool objects to dicts for compatibility
            tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, 'inputSchema') else {}
                }
                for t in tools_result
            ]
            return {
                "tools": tools,
                "formatted": format_tools_for_prompt(tools),
                "count": len(tools)
            }
    except Exception as e:
        # Return empty on failure - caller should fallback to static list
        return {
            "tools": [],
            "formatted": "",
            "count": 0,
            "error": str(e)
        }


def format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    """Format discovered tools for inclusion in agent prompt.
    
    Groups tools by category and formats them in a clear, readable way.
    
    Args:
        tools: List of tool metadata from MCP server
    
    Returns:
        Formatted string ready for prompt injection
    """
    if not tools:
        return "No tools available."
    
    # Categorize tools
    search_tools = []
    read_tools = []
    write_tools = []
    utility_tools = []
    quick_tools = []
    
    for tool in tools:
        name = tool.get("name", "")
        desc = tool.get("description", "")
        
        # Categorize by name pattern
        if name.startswith("search_"):
            search_tools.append(name)
        elif name.startswith("list_"):
            read_tools.append(name)
        elif name in ("record_vital_observation", "create_medication_request", "create_service_request"):
            write_tools.append(name)
        elif name.startswith("get_") and ("latest" in name or "conditions" in name):
            quick_tools.append((name, desc))
        else:
            utility_tools.append(name)
    
    # Format output
    lines = [f"## Tools ({len(tools)} total)\n"]
    
    if search_tools:
        lines.append(f"**Search:** {', '.join(search_tools)}\n")
    
    if read_tools:
        lines.append(f"**Read:** {', '.join(read_tools)}\n")
    
    if quick_tools:
        lines.append("**Quick Access (PREFERRED):**")
        for name, desc in quick_tools:
            # Extract key usage from description
            short_desc = desc.split('.')[0] if desc else ""
            lines.append(f"- `{name}()` → {short_desc}")
        lines.append("")
    
    if write_tools:
        lines.append(f"**Write:** {', '.join(write_tools)}\n")
    
    if utility_tools:
        lines.append(f"**Utilities:** {', '.join(utility_tools)}\n")
    
    return "\n".join(lines)


def format_tool_schema(tool: Dict[str, Any]) -> str:
    """Format a single tool's full schema for detailed documentation.
    
    Args:
        tool: Tool metadata from MCP server
    
    Returns:
        Formatted tool documentation
    """
    name = tool.get("name", "unknown")
    desc = tool.get("description", "No description")
    schema = tool.get("inputSchema", {})
    
    lines = [f"### {name}", f"{desc}", ""]
    
    props = schema.get("properties", {})
    required = schema.get("required", [])
    
    if props:
        lines.append("**Parameters:**")
        for param_name, param_info in props.items():
            req_mark = " (required)" if param_name in required else ""
            param_desc = param_info.get("description", "")
            param_type = param_info.get("type", "any")
            lines.append(f"- `{param_name}` ({param_type}){req_mark}: {param_desc}")
    
    return "\n".join(lines)


# Synchronous wrapper for non-async contexts
def discover_tools_sync(mcp_server_url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Synchronous version of discover_tools_async.
    
    Runs the async version in an event loop. Prefer async version when possible.
    """
    import asyncio
    try:
        return asyncio.run(discover_tools_async(mcp_server_url, timeout))
    except Exception as e:
        return {
            "tools": [],
            "formatted": "",
            "count": 0,
            "error": str(e)
        }


if __name__ == "__main__":
    # Test tool discovery
    import asyncio
    
    async def test():
        result = await discover_tools_async("http://localhost:8002/mcp")
        print(f"Discovered {result['count']} tools")
        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            print("\n" + result["formatted"])
    
    asyncio.run(test())
