"""MedAgentBench evaluation tasks and reference solutions.

This module contains:
- test_data_v2.json: Benchmark tasks for agent evaluation (from Stanford MedAgentBench)
- refsol.py: Reference solution evaluators from Stanford MedAgentBench
  - task1() to task10(): Full evaluation functions (POST validation + answer check)
  - compute_ground_truth(): Simplified entry point for computing expected answers only

Architecture:
- For ANSWER-ONLY evaluation: Use compute_ground_truth() via utils/evaluation.py
- For FULL evaluation (including POST validation): Use the Agentify-MedAgentBench
  evaluator (scenarios/medagentbench/evaluator) which has access to fhir_ops tracking
"""
import json
from pathlib import Path

from .refsol import compute_ground_truth

TASKS_DIR = Path(__file__).parent
TASKS_FILE = TASKS_DIR / "test_data_v2.json"

__all__ = ["compute_ground_truth", "load_tasks", "get_task"]


def load_tasks() -> list:
    """Load benchmark tasks from tasks.json."""
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)


def get_task(task_id: str) -> dict:
    """Get a specific task by ID."""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise ValueError(f"Task not found: {task_id}")
