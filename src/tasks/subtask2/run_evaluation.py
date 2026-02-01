#!/usr/bin/env python3
"""Run Pokemon-Drugs confabulation detection evaluation.

This script runs the subtask2 evaluation using green and purple agents.
No OpenAI/VLLM dependencies - uses the agent system.

Usage:
    # Run default evaluation (subset test)
    python -m src.tasks.subtask2.run_evaluation

    # Run on brand dataset only
    python -m src.tasks.subtask2.run_evaluation --dataset brand

    # Run full evaluation (all cases)
    python -m src.tasks.subtask2.run_evaluation --full

    # Run with specific condition
    python -m src.tasks.subtask2.run_evaluation --condition mitigation

    # Run all conditions
    python -m src.tasks.subtask2.run_evaluation --all-conditions
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src directory to path for imports
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Add project root to path
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.tasks.subtask2.evaluator import (
    CONDITIONS,
    EvaluationConfig,
    run_evaluation,
    save_results,
)
from src.tasks.subtask2.task_loader import get_dataset_size


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger("subtask2")


@dataclass
class ScriptArguments:
    """Command-line arguments for subtask2 evaluation."""
    # Agent configuration
    purple_agent_url: Optional[str] = field(
        default="http://localhost:9019",
        metadata={"help": "URL of purple agent (LLM to test)"}
    )
    mcp_server_url: Optional[str] = field(
        default="http://localhost:8002",
        metadata={"help": "URL of MCP server"}
    )
    
    # Dataset configuration
    dataset: Optional[str] = field(
        default=None,
        metadata={"help": "Dataset: 'brand', 'generic', or None for both"}
    )
    subset_test: Optional[bool] = field(
        default=True,
        metadata={"help": "Use subset for testing (default: True)"}
    )
    subset_size: Optional[int] = field(
        default=10,
        metadata={"help": "Subset size if subset_test=True"}
    )
    full: Optional[bool] = field(
        default=False,
        metadata={"help": "Run full evaluation (all cases)"}
    )
    
    # Evaluation configuration
    num_runs: Optional[int] = field(
        default=1,
        metadata={"help": "Number of runs per case"}
    )
    condition: Optional[str] = field(
        default="default",
        metadata={"help": "Prompt condition to use"}
    )
    all_conditions: Optional[bool] = field(
        default=False,
        metadata={"help": "Run all conditions"}
    )
    
    # Output configuration
    output_dir: Optional[str] = field(
        default="./experiments/subtask2",
        metadata={"help": "Output directory for results"}
    )
    timeout: Optional[int] = field(
        default=120,
        metadata={"help": "Request timeout in seconds"}
    )


def parse_args() -> ScriptArguments:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Pokemon-Drugs confabulation detection evaluation"
    )
    
    # Agent configuration
    parser.add_argument(
        "--purple-agent-url",
        default="http://localhost:9019",
        help="URL of purple agent (LLM to test)"
    )
    parser.add_argument(
        "--mcp-server-url",
        default="http://localhost:8002",
        help="URL of MCP server"
    )
    
    # Dataset configuration
    parser.add_argument(
        "--dataset",
        choices=["brand", "generic"],
        default=None,
        help="Dataset: 'brand', 'generic', or None for both"
    )
    parser.add_argument(
        "--subset-test",
        action="store_true",
        default=True,
        help="Use subset for testing (default: True)"
    )
    parser.add_argument(
        "--no-subset-test",
        action="store_true",
        help="Disable subset test (use all data)"
    )
    parser.add_argument(
        "--subset-size",
        type=int,
        default=10,
        help="Subset size if subset_test=True"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full evaluation (all cases)"
    )
    
    # Evaluation configuration
    parser.add_argument(
        "--num-runs",
        type=int,
        default=1,
        help="Number of runs per case"
    )
    parser.add_argument(
        "--condition",
        choices=CONDITIONS,
        default="default",
        help="Prompt condition to use"
    )
    parser.add_argument(
        "--all-conditions",
        action="store_true",
        help="Run all conditions"
    )
    
    # Output configuration
    parser.add_argument(
        "--output-dir",
        default="./experiments/subtask2",
        help="Output directory for results"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds"
    )
    
    args = parser.parse_args()
    
    # Handle --full and --no-subset-test flags
    subset_test = True
    if args.full or args.no_subset_test:
        subset_test = False
    
    return ScriptArguments(
        purple_agent_url=args.purple_agent_url,
        mcp_server_url=args.mcp_server_url,
        dataset=args.dataset,
        subset_test=subset_test,
        subset_size=args.subset_size,
        full=args.full,
        num_runs=args.num_runs,
        condition=args.condition,
        all_conditions=args.all_conditions,
        output_dir=args.output_dir,
        timeout=args.timeout,
    )


async def main_async(args: ScriptArguments) -> int:
    """Main async function."""
    print("\n" + "=" * 60)
    print("SUBTASK2: POKEMON-DRUGS CONFABULATION DETECTION")
    print("=" * 60)
    print(f"Purple Agent: {args.purple_agent_url}")
    print(f"MCP Server: {args.mcp_server_url}")
    print(f"Dataset: {args.dataset or 'both (brand + generic)'}")
    print(f"Subset Test: {args.subset_test}")
    if args.subset_test:
        print(f"Subset Size: {args.subset_size}")
    else:
        brand_size = get_dataset_size("brand")
        generic_size = get_dataset_size("generic")
        print(f"Full Evaluation: {brand_size} brand + {generic_size} generic cases")
    print(f"Number of Runs: {args.num_runs}")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 60 + "\n")

    # Determine conditions to run
    conditions_to_run = CONDITIONS if args.all_conditions else [args.condition]

    all_results = []

    for condition in conditions_to_run:
        print(f"\n--- Running condition: {condition} ---\n")

        config = EvaluationConfig(
            purple_agent_url=args.purple_agent_url,
            mcp_server_url=args.mcp_server_url,
            dataset=args.dataset,
            subset_test=args.subset_test,
            subset_size=args.subset_size,
            num_runs=args.num_runs,
            condition=condition,
            output_dir=args.output_dir,
            timeout=args.timeout,
        )

        try:
            results = await run_evaluation(config)
            save_results(results, args.output_dir)
            all_results.append(results)
            
            # Print summary
            metrics = results["metrics"]
            print(f"\n--- Results for condition: {condition} ---")
            print(f"Total Cases: {metrics['total_cases']}")
            print(f"Correct: {metrics['correct']} ({metrics['accuracy']*100:.1f}%)")
            print(f"Inherited Hallucinations: {metrics['inherited_hallucinations']}")
            print(f"Epistemic Hallucinations: {metrics['epistemic_hallucinations']}")
            print(f"Hallucination Rate: {metrics['hallucination_rate']*100:.1f}%")
            print("-" * 40)
            
        except Exception as e:
            logger.error(f"Evaluation failed for condition {condition}: {e}")
            return 1
    
    # Save combined results if running all conditions
    if args.all_conditions and len(all_results) > 1:
        combined = {
            "conditions": {r["config"]["condition"]: r["metrics"] for r in all_results},
            "timestamp": datetime.now().isoformat(),
        }
        combined_path = Path(args.output_dir) / f"subtask2_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(combined_path, "w") as f:
            json.dump(combined, f, indent=2)
        print(f"\nCombined results saved to: {combined_path}")
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60 + "\n")
    
    return 0


def main() -> int:
    """Main entry point."""
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
