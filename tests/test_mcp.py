#!/usr/bin/env python
"""Quick test to verify MCP server is working."""

import httpx
import sys


def test_mcp_server(url: str = "http://localhost:8002"):
    """Test MCP server connection."""
    print(f"Testing MCP server at {url}...")
    
    try:
        # Try the http endpoint
        response = httpx.get(f"{url}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"✓ MCP server healthy")
            return True
    except httpx.HTTPError as e:
        print(f"✗ MCP server not responding: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_fhir_server(url: str = "http://localhost:8080/fhir"):
    """Test FHIR server connection."""
    print(f"Testing FHIR server at {url}...")
    
    try:
        response = httpx.get(f"{url}/metadata", timeout=10.0)
        if response.status_code == 200:
            print(f"✓ FHIR server healthy")
            return True
    except httpx.HTTPError as e:
        print(f"✗ FHIR server not responding: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def main():
    """Run all tests."""
    print("MedAgentBench Service Test")
    print("=" * 40)
    print()
    
    fhir_ok = test_fhir_server()
    print()
    mcp_ok = test_mcp_server()
    print()
    
    if fhir_ok and mcp_ok:
        print("=" * 40)
        print("✓ All services running!")
        print()
        print("Next steps:")
        print("  - Use MCP Inspector: npx @modelcontextprotocol/inspector python -m mcp_skills.fastmcp.server --stdio")
        print("  - Run evaluation: python scripts/run_evaluation.py")
        return 0
    else:
        print("=" * 40)
        print("✗ Some services not available")
        print()
        if not fhir_ok:
            print("  Start FHIR: ./scripts/start_fhir.sh")
        if not mcp_ok:
            print("  Start MCP:  ./scripts/start_mcp.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
