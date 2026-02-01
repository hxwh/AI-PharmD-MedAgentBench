#!/usr/bin/env python3
"""Simple script to run MedAgentBench evaluation."""

import asyncio
import json
import httpx
import os
import sys
from pathlib import Path
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    # Go up one level from scripts/ to project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass


async def run_evaluation(task_id="task_001", purple_agent_url=None, green_agent_url=None, output_dir=None):
    """Run a single evaluation task."""
    
    # Get URLs from environment or use defaults
    if purple_agent_url is None:
        purple_agent_url = os.getenv("PURPLE_AGENT_CARD_URL", "http://localhost:9019/").rstrip('/')
    
    if green_agent_url is None:
        green_agent_url = os.getenv("GREEN_AGENT_CARD_URL", "http://localhost:9009/").rstrip('/')
    
    mcp_server_url = os.getenv("FHIR_MCP_SERVER_URL", "http://localhost:8002")
    max_rounds = int(os.getenv("MAX_ROUNDS", "10"))
    timeout = int(os.getenv("TASK_TIMEOUT", "300"))
    
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
    
    message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "parts": [{
                    "kind": "text",
                    "text": json.dumps(eval_request)
                }],
                "message_id": f"eval_{task_id}_{int(asyncio.get_event_loop().time())}"
            }
        },
        "id": 1
    }
    
    print("=" * 60)
    print("MedAgentBench Evaluation")
    print("=" * 60)
    print(f"Task ID:        {task_id}")
    print(f"Green Agent:    {green_agent_url}")
    print(f"Purple Agent:   {purple_agent_url}")
    print(f"MCP Server:     {mcp_server_url}")
    print(f"Max Rounds:     {max_rounds}")
    print(f"Timeout:        {timeout}s")
    print("=" * 60)
    print()
    
    # Check if agents are running
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(f"{green_agent_url}/.well-known/agent-card.json")
            if response.status_code != 200:
                print(f"❌ Green agent not accessible at {green_agent_url}")
                return False
            print("✅ Green agent is running")
        except Exception as e:
            print(f"❌ Cannot connect to green agent: {e}")
            print(f"   Make sure it's running: python src/server.py")
            return False
        
        try:
            response = await client.get(f"{purple_agent_url}/.well-known/agent-card.json")
            if response.status_code != 200:
                print(f"⚠️  Purple agent not accessible at {purple_agent_url}")
                print("   Evaluation may fail")
            else:
                print("✅ Purple agent is running")
        except Exception as e:
            print(f"⚠️  Cannot connect to purple agent: {e}")
            print("   Start it with: python examples/mock_purple_agent.py")
    
    print()
    print("📤 Sending evaluation request...")
    
    # Send evaluation request
    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        try:
            response = await client.post(
                f"{green_agent_url}/",
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Evaluation completed")
                print()
                
                # Parse and display results
                result_data = {}
                result_text = ""
                log_path = None
                
                if "result" in result:
                    msg = result["result"]
                    
                    # Check artifacts first (newer format)
                    artifacts = msg.get("artifacts", [])
                    for artifact in artifacts:
                        artifact_parts = artifact.get("parts", [])
                        for part in artifact_parts:
                            if part.get("kind") == "text":
                                text = part.get("text", "")
                                if text:
                                    result_text = text
                                    print("📊 Result:")
                                    print("-" * 60)
                                    print(text)
                                    print("-" * 60)
                            elif part.get("kind") == "data":
                                data = part.get("data", {})
                                if data:
                                    result_data = data
                                    log_path = data.get("log_path") or log_path  # Extract log path if available
                    
                    # Fallback: check parts directly (older format)
                    if not result_data and not result_text:
                        parts = msg.get("parts", [])
                        for part in parts:
                            if part.get("kind") == "text":
                                text = part.get("text", "")
                                result_text = text
                                print("📊 Result:")
                                print("-" * 60)
                                print(text)
                                print("-" * 60)
                            elif part.get("kind") == "data":
                                data = part.get("data", {})
                                if data:
                                    result_data = data
                                    log_path = data.get("log_path") or log_path  # Extract log path if available
                    
                    # Display metrics
                    if result_data:
                        print("\n📈 Evaluation Metrics:")
                        print(f"   Score:        {result_data.get('score', 'N/A')}")
                        print(f"   Correct:      {result_data.get('correct', 'N/A')}")
                        print(f"   Failure Type: {result_data.get('failure_type', 'none')}")
                        # if log_path:
                        #     print(f"   Log File:     {log_path}")
                
                # Save results to file
                if output_dir is None:
                    # Go up one level from scripts/ to project root
                    base_dir = Path(__file__).parent.parent / "experiments"

                    # Organize results by subtask
                    if task_id.startswith("task"):
                        # Subtask1: FHIR-based medical reasoning tasks
                        results_dir = base_dir / "subtask1"
                    else:
                        # Fallback: other tasks
                        results_dir = base_dir
                else:
                    results_dir = Path(output_dir)
                results_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = results_dir / f"evaluation_{task_id}_{timestamp}.json"
                
                saved_data = {
                    "timestamp": datetime.now().isoformat(),
                    "task_id": task_id,
                    "green_agent_url": green_agent_url,
                    "purple_agent_url": purple_agent_url,
                    "mcp_server_url": mcp_server_url,
                    "config": {
                        "max_rounds": max_rounds,
                        "timeout": timeout
                    },
                    "result_text": result_text,
                    "result_data": result_data,
                    "log_path": log_path,  # Include log path in saved results
                    "full_response": result
                }
                
                with open(result_file, "w") as f:
                    json.dump(saved_data, f, indent=2)
                
                # Print log path first, then results file
                # Try multiple sources for log_path
                final_log_path = None
                if log_path:
                    final_log_path = log_path
                elif result_data.get("log_path"):
                    final_log_path = result_data.get("log_path")
                elif saved_data.get("log_path"):
                    final_log_path = saved_data.get("log_path")
                else:
                    # Fallback: construct log path from task_id and timestamp
                    # Log files are named: task_{task_id}_{timestamp}.log
                    # Determine log directory based on task type
                    if task_id.startswith("task"):
                        # Subtask1 tasks save logs to src/logs
                        logs_dir = Path(__file__).parent.parent / "src" / "logs"
                    else:
                        # Other tasks save logs to main logs directory
                        logs_dir = Path(__file__).parent.parent / "logs"

                    # Try to find the most recent log file for this task
                    if logs_dir.exists():
                        log_files = sorted(logs_dir.glob(f"task_{task_id}_*.log"), reverse=True)
                        if log_files:
                            final_log_path = str(log_files[0].resolve())
                
                if final_log_path:
                    print(f"\n📋 Log file:        {final_log_path}")
                else:
                    print(f"\n📋 Log file:        (not found - check src/logs/ or logs/ directory)")

                print(f"💾 Results saved to: {result_file}")
                
                return True
            else:
                print(f"❌ Evaluation failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False
                
        except httpx.TimeoutException:
            print(f"❌ Evaluation timed out after {timeout}s")
            print("   This might indicate the purple agent is not responding")
            return False
        except Exception as e:
            print(f"❌ Evaluation error: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run MedAgentBench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run task_001 (legacy - maps to task7: latest glucose)
  python scripts/run_evaluation.py
  
  # Run task_002 (legacy - maps to task1: problem list)
  python scripts/run_evaluation.py --task task_002
  
  # Run any task directly (task1-task10)
  python scripts/run_evaluation.py --task task1   # Problem list
  python scripts/run_evaluation.py --task task2   # Calculate age
  python scripts/run_evaluation.py --task task3   # Record BP
  python scripts/run_evaluation.py --task task4   # Latest magnesium (24h)
  python scripts/run_evaluation.py --task task5   # Check/order magnesium
  python scripts/run_evaluation.py --task task6   # Average glucose (24h)
  python scripts/run_evaluation.py --task task7   # Latest glucose
  python scripts/run_evaluation.py --task task8   # Order consult
  python scripts/run_evaluation.py --task task9   # Check/order potassium
  python scripts/run_evaluation.py --task task10  # Check/order A1C
  
  # Run specific task variants (task1_1, task1_2, etc. from test_data_v2.json)
  python scripts/run_evaluation.py --task task1_1  # Specific task variant
  python scripts/run_evaluation.py --task task2_1  # Another variant
  
  # Run all tasks sequentially
  python scripts/run_all_tasks.py
  
  # Use custom URLs
  python scripts/run_evaluation.py --green http://66.179.241.197:9009 --purple http://66.179.241.197:9019
  
  # Save to custom directory
  python scripts/run_evaluation.py --output-dir ./my_results
        """
    )
    
    parser.add_argument(
        "--task",
        type=str,
        default="task_001",
        help="Task ID to evaluate (default: task_001). Supports: task_001, task_002, task1-task10, or task variants like task1_1, task2_1, etc."
    )
    
    parser.add_argument(
        "--green",
        type=str,
        help="Green agent URL (default: from .env or localhost:9009)"
    )
    
    parser.add_argument(
        "--purple",
        type=str,
        help="Purple agent URL (default: from .env or localhost:9019)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to save results (default: ./experiments)"
    )
    
    args = parser.parse_args()
    
    success = asyncio.run(run_evaluation(
        task_id=args.task,
        purple_agent_url=args.purple,
        green_agent_url=args.green,
        output_dir=args.output_dir
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
