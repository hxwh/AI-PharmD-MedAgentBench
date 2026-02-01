"""Full integration test with Green Agent and Mock Purple Agent.

Usage:
    python tests/full_test.py                    # Run default task (task_001)
    python tests/full_test.py task1_1           # Run specific task
    python tests/full_test.py --task task1_5    # Run with --task flag
"""

import asyncio
import json
import httpx
import os
import sys
import time
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass


async def test_agent_card(green_url: str = "http://localhost:9009"):
    """Test 1: Check agent card is accessible."""
    print("\n" + "="*60)
    print("TEST 1: Agent Card")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{green_url}/.well-known/agent-card.json")
            if response.status_code == 200:
                card = response.json()
                print("✅ Agent card accessible")
                print(f"   Name: {card.get('name')}")
                print(f"   Version: {card.get('version')}")
                print(f"   Skills: {len(card.get('skills', []))}")
                return True
            else:
                print(f"❌ Agent card failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("   Make sure green agent is running: python src/server.py")
            return False


async def test_evaluation(
    task_id: str = "task_001",
    green_url: str = "http://localhost:9009",
    purple_url: str = "http://localhost:9019",
    mcp_url: str = "http://localhost:8002",
    timeout: int = 300
):
    """Test 2: Send evaluation request."""
    print("\n" + "="*60)
    print("TEST 2: Evaluation Request")
    print("="*60)
    
    eval_request = {
        "participants": {
            "agent": purple_url
        },
        "config": {
            "task_id": task_id,
            "mcp_server_url": mcp_url,
            "max_rounds": 10,
            "timeout": timeout
        }
    }
    
    message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": json.dumps(eval_request)
                    }
                ],
                "message_id": f"test_{int(time.time())}"
            }
        },
        "id": 1
    }
    
    print("📤 Sending evaluation request...")
    print(f"   Task: {task_id}")
    print(f"   Green Agent: {green_url}")
    print(f"   Purple Agent: {purple_url}")
    
    async with httpx.AsyncClient(timeout=timeout + 30) as client:
        try:
            response = await client.post(
                f"{green_url}/",
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Request accepted")
                
                # Parse response
                if "result" in result:
                    msg = result["result"]
                    parts = msg.get("parts", [])
                    
                    for part in parts:
                        if part.get("kind") == "text":
                            text = part.get("text", "")
                            print("\n📊 Result Summary:")
                            print(text[:500])
                        elif part.get("kind") == "data":
                            data = part.get("data", {})
                            print("\n📈 Evaluation Data:")
                            print(f"   Score: {data.get('score')}")
                            print(f"   Correct: {data.get('correct')}")
                            print(f"   Failure Type: {data.get('failure_type')}")
                
                return True
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except httpx.TimeoutException:
            print("❌ Request timed out")
            print("   This might be expected if purple agent isn't running")
            return False
        except Exception as e:
            print(f"❌ Request error: {e}")
            return False


async def test_purple_agent(purple_url: str = "http://localhost:9019"):
    """Test 3: Check if purple agent is running."""
    print("\n" + "="*60)
    print("TEST 3: Purple Agent Check")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(f"{purple_url}/.well-known/agent-card.json")
            if response.status_code == 200:
                card = response.json()
                print("✅ Purple agent is running")
                print(f"   Name: {card.get('name')}")
                return True
            else:
                print("⚠️  Purple agent returned error")
                return False
        except Exception as e:
            print("⚠️  Purple agent not running")
            print("   Start with: python examples/mock_purple_agent.py")
            return False


async def run_all_tests(
    use_docker_network: bool = False,
    task_id: str = "task_001"
):
    """Run all tests in sequence.
    
    Args:
        use_docker_network: If True, use Docker network hostnames
        task_id: Task ID to evaluate (e.g., task_001, task1_1, task1)
    """
    # Configure URLs based on network mode
    if use_docker_network:
        green_url = "http://aipharmd-green:9009"
        purple_url = "http://aipharmd-purple:9019"
        mcp_url = "http://aipharmd-mcp:8002"
    else:
        green_url = os.getenv("GREEN_AGENT_CARD_URL", "http://localhost:9009").rstrip('/')
        purple_url = os.getenv("PURPLE_AGENT_CARD_URL", "http://localhost:9019").rstrip('/')
        mcp_url = os.getenv("FHIR_MCP_SERVER_URL", "http://localhost:8002")
    
    timeout = int(os.getenv("TASK_TIMEOUT", "300"))
    
    print("\n" + "="*60)
    print("PharmD - Full Test Suite")
    print("="*60)
    print(f"Task ID: {task_id}")
    print(f"Green Agent: {green_url}")
    print(f"Purple Agent: {purple_url}")
    print("="*60)
    
    results = {
        "agent_card": await test_agent_card(green_url),
        "purple_agent": await test_purple_agent(purple_url),
    }
    
    # Only run evaluation if both agents are up
    if results["agent_card"] and results["purple_agent"]:
        results["evaluation"] = await test_evaluation(
            task_id=task_id,
            green_url=green_url,
            purple_url=purple_url,
            mcp_url=mcp_url,
            timeout=timeout
        )
    else:
        print("\n⚠️  Skipping evaluation test (agents not ready)")
        results["evaluation"] = False
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Agent Card:     {'✅ PASS' if results['agent_card'] else '❌ FAIL'}")
    print(f"Purple Agent:   {'✅ PASS' if results['purple_agent'] else '⚠️  NOT RUNNING'}")
    print(f"Evaluation:     {'✅ PASS' if results['evaluation'] else '❌ FAIL or SKIPPED'}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    elif results["agent_card"]:
        print("✅ Green agent is working (missing purple agent for full test)")
    else:
        print("❌ Some tests failed")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    if not results["agent_card"]:
        print("1. Start green agent: python src/server.py")
    if not results["purple_agent"]:
        print("2. Start purple agent: cd purple_agent/src && python server.py")
    if results["agent_card"] and results["purple_agent"] and not results["evaluation"]:
        print("3. Check logs for errors")
    if passed == total:
        print("✅ System is ready for evaluation!")
    print()
    
    return passed == total


def main():
    """Main entry point with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run PharmD full integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/full_test.py                    # Run default task
  python tests/full_test.py task1_1            # Run specific task
  python tests/full_test.py --task task1_5     # Run with --task flag
  python tests/full_test.py --docker           # Use Docker network
        """
    )
    
    parser.add_argument(
        "task_id",
        nargs="?",
        default="task_001",
        help="Task ID to evaluate (default: task_001)"
    )
    
    parser.add_argument(
        "--task",
        type=str,
        help="Task ID (alternative to positional argument)"
    )
    
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Use Docker network hostnames"
    )
    
    args = parser.parse_args()
    
    # --task flag takes precedence
    task_id = args.task or args.task_id
    
    success = asyncio.run(run_all_tests(
        use_docker_network=args.docker,
        task_id=task_id
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
