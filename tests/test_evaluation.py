"""Example script to test MedAgentBench evaluation locally."""

import asyncio
import json
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from a2a.types import Message, Part, TextPart
from agent import Agent


async def mock_updater():
    """Create a mock task updater for testing."""
    # Create a simple updater that prints updates
    class MockUpdater:
        def __init__(self):
            self.updates = []
            self._terminal_state_reached = False
        
        async def update_status(self, state, message):
            print(f"📊 Status Update: {state}")
            self.updates.append(("status", state, message))
        
        async def add_artifact(self, parts, name):
            print(f"📄 Artifact: {name}")
            for part in parts:
                if isinstance(part.root, TextPart):
                    print(f"   {part.root.text}")
            self.updates.append(("artifact", parts, name))
        
        async def start_work(self):
            print("🚀 Starting work...")
        
        async def complete(self):
            print("✅ Task completed")
            self._terminal_state_reached = True
        
        async def failed(self, message):
            print(f"❌ Task failed: {message}")
            self._terminal_state_reached = True
        
        async def reject(self, message):
            print(f"🚫 Task rejected: {message}")
            self._terminal_state_reached = True
    
    return MockUpdater()


async def test_evaluation(task_id="task_001", purple_agent_url="http://localhost:9019", 
                          mcp_server_url="http://localhost:8002", max_rounds=10, timeout=300):
    """Test the evaluation flow with a mock purple agent.
    
    Args:
        task_id: Task ID to evaluate (e.g., "task_001", "task_002", or direct "task1"-"task10")
        purple_agent_url: URL of the purple agent
        mcp_server_url: URL of the MCP server
        max_rounds: Maximum number of rounds for the agent
        timeout: Timeout in seconds
    """
    print("=" * 60)
    print("MedAgentBench Green Agent - Test Evaluation")
    print("=" * 60)
    print()
    
    # Create agent
    agent = Agent()
    
    # Create evaluation request
    eval_request = {
        "participants": {
            "agent": purple_agent_url
        },
        "config": {
            "task_id": task_id,
            "mcp_server_url": mcp_server_url,
            "max_rounds": max_rounds,
            "timeout": timeout
        }
    }
    
    # Create A2A message
    message = Message(
        kind="message",
        role="user",
        parts=[Part(TextPart(kind="text", text=json.dumps(eval_request)))],
        message_id="test_msg_001",
        context_id="test_ctx_001"
    )
    
    # Create mock updater
    updater = await mock_updater()
    
    print("📝 Evaluation Request:")
    print(json.dumps(eval_request, indent=2))
    print()
    
    try:
        await agent.run(message, updater)
    except Exception as e:
        print(f"Expected error (no purple agent running): {e}")
    
    print()
    print("=" * 60)
    print("Test completed. Check output above for flow execution.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test MedAgentBench evaluation locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run task_001 (maps to task7 - glucose level)
  python examples/test_evaluation.py
  
  # Run task_002 (maps to task1 - problem list)
  python examples/test_evaluation.py --task task_002
  
  # Run task directly by ID (task1-task10)
  python examples/test_evaluation.py --task task1
  python examples/test_evaluation.py --task task7
  
  # Use custom purple agent URL
  python examples/test_evaluation.py --purple http://localhost:9019
  
  # Custom timeout and rounds
  python examples/test_evaluation.py --max-rounds 15 --timeout 600

Available tasks:
  task_001 → task7: Get latest glucose level
  task_002 → task1: Get problem list
  task1: Find patient's current problem list
  task2: Calculate patient's age
  task3: Record blood pressure vital sign
  task4: Get latest magnesium level (24h)
  task5: Check and order magnesium if low
  task6: Calculate average glucose (24h)
  task7: Get latest glucose level
  task8: Order orthopedic consult
  task9: Check and order potassium if low
  task10: Check and order HbA1c if old
        """
    )
    
    parser.add_argument(
        "--task",
        type=str,
        default="task_001",
        help="Task ID to evaluate (default: task_001). Use task_001/task_002 or task1-task10"
    )
    
    parser.add_argument(
        "--purple",
        type=str,
        default="http://localhost:9019",
        help="Purple agent URL (default: http://localhost:9019)"
    )
    
    parser.add_argument(
        "--mcp-server",
        type=str,
        default="http://localhost:8002",
        help="MCP server URL (default: http://localhost:8002)"
    )
    
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=10,
        help="Maximum rounds for agent (default: 10)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(test_evaluation(
        task_id=args.task,
        purple_agent_url=args.purple,
        mcp_server_url=args.mcp_server,
        max_rounds=args.max_rounds,
        timeout=args.timeout
    ))
