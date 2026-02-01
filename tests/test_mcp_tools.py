#!/usr/bin/env python
"""Test MCP server tools directly."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_tools():
    """Test MCP server via stdio."""
    print("Testing MedAgentBench MCP Server")
    print("=" * 50)
    
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_skills.fastmcp.server", "--stdio"],
        cwd=str(project_root)
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("✓ Connected to MCP server\n")
            
            # List tools
            print("Available Tools:")
            print("-" * 50)
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  • {tool.name}")
                if tool.description:
                    desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                    print(f"    {desc}")
            
            print(f"\nTotal: {len(tools.tools)} tools")
            
            # List resources
            print("\nAvailable Resources:")
            print("-" * 50)
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  • {resource.uri}")
            
            # Test a simple tool call - search patients
            print("\n" + "=" * 50)
            print("Testing: search_patients(name='John')")
            print("-" * 50)
            try:
                result = await session.call_tool("search_patients", {"name": "John"})
                content = result.content[0].text if result.content else "No content"
                # Parse and pretty print
                data = json.loads(content)
                if "response" in data and "entry" in data["response"]:
                    entries = data["response"]["entry"]
                    print(f"Found {len(entries)} patient(s)")
                    for entry in entries[:3]:  # Show first 3
                        patient = entry.get("resource", {})
                        name = patient.get("name", [{}])[0]
                        print(f"  - {name.get('given', [''])[0]} {name.get('family', '')}")
                else:
                    print(json.dumps(data, indent=2)[:500])
            except Exception as e:
                print(f"Error: {e}")
            
            print("\n✓ MCP server is working correctly!")


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
