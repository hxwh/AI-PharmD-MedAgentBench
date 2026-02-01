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


def transform_agentbeats_results(agentbeats_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform AgentBeats client results into leaderboard-compatible format.

    Args:
        agentbeats_results: Results from AgentBeats client (may be A2A artifacts or direct results)

    Returns:
        Leaderboard-compatible results format
    """
    # Handle different possible input formats from AgentBeats client

    # Case 1: Direct results format (if client outputs structured JSON)
    if "subtask" in agentbeats_results and "participant_id" in agentbeats_results:
        return agentbeats_results  # Already in correct format

    # Case 2: A2A artifacts format (extract from artifacts)
    if "artifacts" in agentbeats_results:
        for artifact in agentbeats_results["artifacts"]:
            if artifact.get("name") == "Evaluation Result":
                parts = artifact.get("parts", [])
                for part in parts:
                    if part.get("kind") == "data":
                        data = part.get("data", {})
                        if data:
                            # This should contain the detailed PharmAgent results
                            return transform_pharmagent_results(data)

    # Case 3: Raw PharmAgent format (fallback for testing)
    if "result_data" in agentbeats_results:
        return transform_pharmagent_results(agentbeats_results)

    # Default: assume it's already in the right format
    return agentbeats_results


def get_participant_id_from_scenario() -> str:
    """
    Extract participant ID from scenario.toml for leaderboard results.
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    scenario_file = Path("scenario.toml")
    if scenario_file.exists():
        with open(scenario_file, 'rb') as f:
            scenario = tomllib.load(f)

        participants = scenario.get("participants", [])
        if participants:
            # Use the first participant's agentbeats_id, or name if no ID
            participant = participants[0]
            return participant.get("agentbeats_id") or participant.get("name", "unknown")

    return "unknown"


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

    # Get participant ID from scenario or results
    participant_id = pharmagent_results.get("participant_id")
    if not participant_id or participant_id == "unknown":
        participant_id = get_participant_id_from_scenario()

    # Build AgentBeats-compatible results
    leaderboard_results = {
        "subtask": subtask,
        "participant_id": participant_id,
        "timestamp": pharmagent_results.get("timestamp", ""),
        "config": config,
        **metrics  # Add the scoring metrics at top level
    }

    return leaderboard_results


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

    # Load AgentBeats client results
    with open(input_file, 'r') as f:
        client_results = json.load(f)

    # Transform to leaderboard format
    leaderboard_results = transform_agentbeats_results(client_results)

    # Save transformed results
    with open(output_file, 'w') as f:
        json.dump(leaderboard_results, f, indent=2)

    print(f"Transformed results saved to {output_file}")
    print(f"Metrics: {leaderboard_results}")


if __name__ == "__main__":
    main()