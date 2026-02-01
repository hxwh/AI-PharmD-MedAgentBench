"""Utility functions for MedAgentBench Green Agent.

Provides:
- call_gemini: LLM wrapper for Gemini API
- fetch_latest_observation: FHIR query utility
- normalize_answer: Answer normalization for comparison
- evaluate_task: Task evaluation (answer comparison only, see evaluation.py for details)
"""

from .call_gemini import call_gemini
from .fhir import fetch_latest_observation
from .evaluation import evaluate_task, normalize_answer

__all__ = [
    "call_gemini",
    "fetch_latest_observation",
    "normalize_answer",
    "evaluate_task",
]
