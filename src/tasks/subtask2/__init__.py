"""Subtask2: Pokemon-Drugs-Names Confabulation Detection.

This task evaluates LLM ability to distinguish Pokemon names from real drug names.
The model is given medication lists containing hidden Pokemon names and must
identify which names are confabulations (Pokemon) vs real drugs.

Architecture:
    - Green Agent: Coordinates evaluation, loads test cases, scores results
    - Purple Agent: The LLM being evaluated (processes medication lists)
    - MCP Pokemon Tools: Provide ground truth data and evaluation functions

Datasets:
    - data/brand/pokemon.csv: Medication lists using brand drug names
    - data/generic/pokemon.csv: Medication lists using generic drug names

Suspicion Labels:
    - 0: Inherited confabulation (misidentified real drug as Pokemon)
    - 1: Epistemic confabulation (identified wrong Pokemon)
    - 2: Correct (no hallucination - detected Pokemon as fake)

Conditions:
    - default: Standard medication extraction prompt
    - mitigation: Prompt with uncertainty acknowledgment instructions
    - medication_indication: Prompt asking for medication indications
    - medication_indication_mitigation: Indication prompt with mitigation

Usage:
    # Run from project root
    python -m src.tasks.subtask2.run_evaluation

    # Run with specific dataset
    python -m src.tasks.subtask2.run_evaluation --dataset brand

    # Run full evaluation
    python -m src.tasks.subtask2.run_evaluation --full

    # Run all conditions
    python -m src.tasks.subtask2.run_evaluation --all-conditions

MCP Tools: mcp_skills/pokemon/
"""

from .task_loader import (
    PokemonCase,
    TaskConfig,
    load_cases,
    get_dataset_size,
    get_task_ids,
    get_case_by_task_id,
)

from .evaluator import (
    CONDITIONS,
    EvaluationConfig,
    EvaluationResult,
    run_evaluation,
    save_results,
)

__all__ = [
    # Task loader
    "PokemonCase",
    "TaskConfig",
    "load_cases",
    "get_dataset_size",
    "get_task_ids",
    "get_case_by_task_id",
    # Evaluator
    "CONDITIONS",
    "EvaluationConfig",
    "EvaluationResult",
    "run_evaluation",
    "save_results",
]
