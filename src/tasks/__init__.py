"""MedAgentBench tasks module.

This module is organized into subtasks:
- subtask1: Original MedAgentBench evaluation tasks
- subtask2: Reserved for future tasks
"""

# Re-export main functions from subtask1 for backward compatibility
from .subtask1 import compute_ground_truth, load_tasks, get_task

__all__ = ["compute_ground_truth", "load_tasks", "get_task"]
