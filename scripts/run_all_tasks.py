#!/usr/bin/env python3
"""Run all MedAgentBench tasks sequentially."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import run_evaluation
sys.path.insert(0, str(Path(__file__).parent))

from run_evaluation import run_evaluation


async def run_all_tasks(purple_agent_url=None, green_agent_url=None, output_dir=None):
    """Run all tasks (task1-task10) sequentially."""
    
    # All available tasks
    tasks = [
        "task1",   # Find patient's current problem list
        "task2",   # Calculate patient's age
        "task3",   # Record blood pressure vital sign
        "task4",   # Get latest magnesium level (24h)
        "task5",   # Check and order magnesium if low
        "task6",   # Calculate average glucose (24h)
        "task7",   # Get latest glucose level
        "task8",   # Order orthopedic consult
        "task9",   # Check and order potassium if low
        "task10",  # Check and order HbA1c if old
    ]
    
    print("=" * 60)
    print("MedAgentBench - Running All Tasks")
    print("=" * 60)
    print(f"Total tasks: {len(tasks)}")
    print("=" * 60)
    print()
    
    results = []
    
    for i, task_id in enumerate(tasks, 1):
        print(f"\n{'='*60}")
        print(f"Task {i}/{len(tasks)}: {task_id}")
        print(f"{'='*60}\n")
        
        success = await run_evaluation(
            task_id=task_id,
            purple_agent_url=purple_agent_url,
            green_agent_url=green_agent_url,
            output_dir=output_dir
        )
        
        results.append({
            "task_id": task_id,
            "success": success
        })
        
        if not success:
            print(f"\n⚠️  Task {task_id} failed. Continuing with next task...")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    print(f"Total tasks:  {len(results)}")
    print(f"Successful:   {successful}")
    print(f"Failed:       {failed}")
    print()
    
    if failed > 0:
        print("Failed tasks:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['task_id']}")
    
    return successful == len(results)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run all MedAgentBench tasks sequentially",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tasks with default settings
  python scripts/run_all_tasks.py
  
  # Use custom URLs
  python scripts/run_all_tasks.py --green http://66.179.241.197:9009 --purple http://66.179.241.197:9019
  
  # Save to custom directory
  python scripts/run_all_tasks.py --output-dir ./my_results
        """
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
    
    success = asyncio.run(run_all_tasks(
        purple_agent_url=args.purple,
        green_agent_url=args.green,
        output_dir=args.output_dir
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
