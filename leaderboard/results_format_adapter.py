#!/usr/bin/env python3
"""
Results Format Adapter for AgentBeats Leaderboard Compatibility

Transforms PharmAgent's detailed evaluation results into AgentBeats-compatible format.
Based on leaderboard-config.json scoring requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def extract_leaderboard_metrics(result_data: Dict[str, Any], subtask: str) -> Dict[str, Any]:
    """
    Extract metrics that match leaderboard-config.json scoring requirements.

    Args:
        result_data: The detailed result data from PharmAgent evaluation
        subtask: Either "subtask1" or "subtask2"

    Returns:
        Simplified metrics dict compatible with AgentBeats leaderboard
    """
    if subtask == "subtask1":
        # Subtask 1: Medical Record Tasks
        # Expected metrics: score, success_rate
        score = result_data.get("score", 0.0)
        success_rate = result_data.get("report", {}).get("success_rate", 0.0)

        return {
            "score": float(score),
            "success_rate": float(success_rate)
        }

    elif subtask == "subtask2":
        # Subtask 2: Confabulation Detection
        # Expected metrics: accuracy, hallucination_rate
        accuracy = result_data.get("accuracy", 0.0)
        hallucination_rate = result_data.get("hallucination_rate", 0.0)

        return {
            "accuracy": float(accuracy),
            "hallucination_rate": float(hallucination_rate)
        }

    else:
        raise ValueError(f"Unknown subtask: {subtask}")


def transform_pharmagent_results(pharmagent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform PharmAgent evaluation results into AgentBeats leaderboard format.

    Args:
        pharmagent_results: Raw results from PharmAgent evaluation

    Returns:
        AgentBeats-compatible results format
    """
    # Extract subtask from config or result data
    config = pharmagent_results.get("config", {})
    subtask = config.get("subtask", "subtask1")

    # Get the detailed result data
    result_data = pharmagent_results.get("result_data", {})

    # Extract leaderboard-compatible metrics
    metrics = extract_leaderboard_metrics(result_data, subtask)

    # Build AgentBeats-compatible results
    agentbeats_results = {
        "subtask": subtask,
        "participant_id": pharmagent_results.get("participant_id", "unknown"),
        "timestamp": pharmagent_results.get("timestamp", ""),
        "config": config,
        **metrics  # Add the scoring metrics at top level
    }

    return agentbeats_results


def main():
    """Convert PharmAgent results to AgentBeats format."""
    if len(sys.argv) != 3:
        print("Usage: python results_format_adapter.py <input_file> <output_file>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist")
        sys.exit(1)

    # Load PharmAgent results
    with open(input_file, 'r') as f:
        pharmagent_results = json.load(f)

    # Transform to AgentBeats format
    agentbeats_results = transform_pharmagent_results(pharmagent_results)

    # Save transformed results
    with open(output_file, 'w') as f:
        json.dump(agentbeats_results, f, indent=2)

    print(f"Transformed results saved to {output_file}")
    print(f"Metrics: {agentbeats_results}")


if __name__ == "__main__":
    main()