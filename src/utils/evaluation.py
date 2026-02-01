"""Evaluation utilities for MedAgentBench scoring.

This module provides answer comparison for MedAgentBench tasks. 

IMPORTANT ARCHITECTURE NOTE:
- READ-ONLY tasks (task1, task2, task4, task6, task7): Use this module for evaluation
- POST tasks (task3, task5, task8, task9, task10): Full evaluation with POST payload 
  validation is done by Agentify-MedAgentBench evaluator (scenarios/medagentbench/evaluator)
  which has access to fhir_ops tracking from MCP tool calls.

Ground truth is computed dynamically by querying the FHIR server using compute_ground_truth()
from refsol.py, which contains the reference implementation from Stanford MedAgentBench.
"""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("medagentbench")

# Import ground truth computation from refsol
from tasks.subtask1.refsol import compute_ground_truth

# FHIR API base for dynamic ground truth computation
FHIR_API_BASE = os.environ.get("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")


def normalize_answer(val) -> str:
    """Normalize an answer value for comparison.
    
    Handles:
    - Numeric strings: extracts number, converts whole floats to int
    - Text strings: lowercase, remove punctuation/whitespace
    - Numbers: convert to int if whole number
    
    Args:
        val: Value to normalize (str, int, float)
    
    Returns:
        Normalized string representation
    """
    if isinstance(val, str):
        # Try to extract a number (including decimals)
        numeric_match = re.search(r'-?\d+\.?\d*', val)
        if numeric_match:
            num_str = numeric_match.group()
            try:
                num = float(num_str)
                # Convert 108.0 -> "108"
                if num == int(num):
                    return str(int(num))
                return num_str
            except ValueError:
                return num_str
        # For text: remove non-alphanumeric and normalize
        clean = re.sub(r'[^\w\s]', '', val).lower()
        return re.sub(r'\s+', '', clean)
    
    # For numeric values
    if isinstance(val, (int, float)):
        if float(val) == int(val):
            return str(int(val))
        return str(val)
    
    return str(val).lower()


def evaluate_task(
    parsed_answer: Optional[list],
    ground_truth: list,
    task_data: dict,
    agent_response_raw: str,
    trajectory: list = None
) -> dict:
    """Evaluate agent answer against ground truth.
    
    For READ-ONLY tasks, computes ground truth dynamically if not provided
    and compares with agent answer.
    
    For POST tasks, validates that POST operations were performed successfully
    using the trajectory data.
    
    Args:
        parsed_answer: Agent's parsed answer (list of values)
        ground_truth: Expected answer from task definition (may be empty)
        task_data: Original task data with id, eval_MRN, etc.
        agent_response_raw: Raw agent response (for violation checks)
        trajectory: List of agent action steps with tool calls and results
    
    Returns:
        dict with: score, correct, failure_type, failure_reason, computed_expected
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": None
    }
    
    if trajectory is None:
        trajectory = []
    
    if parsed_answer is None:
        result["failure_type"] = "invalid_finish_format"
        result["failure_reason"] = "No valid answer parsed"
        return result
    
    task_id = task_data.get("id", "")
    task_prefix = task_id.split("_")[0] if "_" in task_id else task_id
    post_tasks = ("task3", "task5", "task8", "task9", "task10")

    # Special handling for hybrid tasks that require both data retrieval AND conditional action
    if task_id.startswith("task10"):
        return _evaluate_task10(parsed_answer, task_data, trajectory)
    elif task_id.startswith("task9"):
        return _evaluate_task9(parsed_answer, task_data, trajectory)
    elif task_id.startswith("task5"):
        return _evaluate_task5(parsed_answer, task_data, trajectory)

    # For POST tasks, validate via trajectory
    if task_prefix in post_tasks:
        return _evaluate_post_task(parsed_answer, task_data, trajectory)
    
    # Check readonly violations for read-only tasks
    readonly = task_data.get("readonly", True)
    if readonly and "fhir_post" in agent_response_raw.lower():
        result["failure_type"] = "readonly_violation"
        result["failure_reason"] = "Agent made POST request on readonly task"
        return result
    
    # Compute ground truth dynamically if not provided
    if not ground_truth or ground_truth == []:
        try:
            ground_truth = compute_ground_truth(task_id, task_data, FHIR_API_BASE)
            result["computed_expected"] = ground_truth
            logger.info(f"Computed ground truth for {task_id}: {ground_truth}")
        except ValueError as e:
            logger.debug(f"Cannot compute ground truth for {task_id}: {e}")
            ground_truth = []
        except Exception as e:
            logger.error(f"Failed to compute ground truth for {task_id}: {e}")
            result["failure_type"] = "evaluation_error"
            result["failure_reason"] = f"Could not compute ground truth: {e}"
            return result
    else:
        result["computed_expected"] = ground_truth
    
    # No ground truth available
    if not ground_truth:
        result["failure_type"] = "no_ground_truth"
        result["failure_reason"] = "No ground truth available for comparison"
        return result
    
    # Compare answers using task-specific rules
    return _compare_answers(parsed_answer, ground_truth, task_data)


def _evaluate_task10(parsed_answer: list, task_data: dict, trajectory: list) -> dict:
    """Evaluate task10 variants: A1C conditional ordering based on measurement availability/age.

    All task10 variants evaluate whether the agent correctly:
    1. Orders a new A1C test if no measurements exist or measurements are > 1 year old
    2. Does not order if recent measurements exist

    The returned answer format is not checked - only the actions matter.
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": ["action_completed"]  # For compatibility with existing logs
    }

    # Compute ground truth to determine what actions should have been taken
    try:
        from tasks.subtask1.refsol import compute_ground_truth
        expected_measurement = compute_ground_truth(task_data.get('id', ''), task_data, FHIR_API_BASE)

        # Determine if ordering was required
        if expected_measurement == [-1]:
            # No measurements exist - ordering is required
            should_order_test = True
        else:
            # Check if measurement is > 1 year old
            from datetime import datetime
            cutoff = datetime.fromisoformat("2022-11-13T10:15:00+00:00")  # 1 year ago
            measurement_time = datetime.fromisoformat(expected_measurement[1])
            should_order_test = measurement_time < cutoff

    except Exception as e:
        logger.error(f"Failed to compute ground truth for {task_data.get('id', 'task10')}: {e}")
        result["failure_type"] = "evaluation_error"
        result["failure_reason"] = f"Could not compute ground truth: {e}"
        return result

    # Check agent's action decision
    agent_made_post = any(
        step.get("tool_result", "").lower().find("fhir_post") >= 0 or
        '"accepted":true' in step.get("tool_result", "").lower() or
        '"accepted": true' in step.get("tool_result", "").lower()
        for step in trajectory
    )

    if should_order_test and not agent_made_post:
        result["failure_type"] = "missing_required_action"
        result["failure_reason"] = "Agent should have ordered a new A1C test (no measurements or measurements > 1 year old)"
        return result
    elif not should_order_test and agent_made_post:
        result["failure_type"] = "incorrect_action"
        result["failure_reason"] = "Agent should NOT have ordered a test (recent measurements exist)"
        return result

    # All checks passed
    result["score"] = 1.0
    result["correct"] = True
    return result


def _evaluate_task9(parsed_answer: list, task_data: dict, trajectory: list) -> dict:
    """Evaluate task9 variants: Potassium conditional ordering based on measurement levels.

    All task9 variants evaluate whether the agent correctly:
    1. Orders BOTH medication AND lab test if K < 3.5
    2. Does not order if K >= 3.5

    The returned answer format is not checked - only the actions matter.
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": ["action_completed"]  # For compatibility with existing logs
    }

    # Compute ground truth to determine what actions should have been taken
    try:
        from tasks.subtask1.refsol import compute_ground_truth
        expected_measurement = compute_ground_truth(task_data.get('id', ''), task_data, FHIR_API_BASE)

        # Determine if ordering was required based on potassium level
        # Order needed if K < 3.5
        should_order = expected_measurement[0] < 3.5 if expected_measurement != [-1] else False

    except Exception as e:
        logger.error(f"Failed to compute ground truth for {task_data.get('id', 'task9')}: {e}")
        result["failure_type"] = "evaluation_error"
        result["failure_reason"] = f"Could not compute ground truth: {e}"
        return result

    # Check agent's action decision - should have exactly 2 POSTs if ordering needed
    posts = []
    for step in trajectory:
        tool_result = step.get("tool_result", "")
        if isinstance(tool_result, str):
            # Extract accepted POSTs
            if '"accepted":true' in tool_result.lower() or '"accepted": true' in tool_result.lower():
                posts.append(tool_result)

    agent_made_correct_posts = len(posts) == 2 if should_order else len(posts) == 0

    if should_order and not agent_made_correct_posts:
        result["failure_type"] = "missing_required_actions"
        result["failure_reason"] = f"Should have ordered 2 items (medication + lab), got {len(posts)}"
        return result
    elif not should_order and not agent_made_correct_posts:
        result["failure_type"] = "incorrect_actions"
        result["failure_reason"] = f"Should have ordered 0 items (potassium normal), got {len(posts)}"
        return result

    # All checks passed
    result["score"] = 1.0
    result["correct"] = True
    return result


def _evaluate_task5(parsed_answer: list, task_data: dict, trajectory: list) -> dict:
    """Evaluate task5 variants: Magnesium conditional ordering based on measurement levels.

    All task5 variants evaluate whether the agent correctly:
    1. Orders magnesium replacement medication if MG < 1.9
    2. Does not order if MG >= 1.9 or no recent measurement

    The returned answer format is not checked - only the actions matter.
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": ["action_completed"]  # For compatibility with existing logs
    }

    # Compute ground truth to determine what actions should have been taken
    try:
        from tasks.subtask1.refsol import compute_ground_truth
        expected_measurement = compute_ground_truth(task_data.get('id', ''), task_data, FHIR_API_BASE)

        # Determine if ordering was required based on magnesium level
        # Order needed if MG < 1.9
        should_order = expected_measurement[0] < 1.9 if expected_measurement != [-1] else False

    except Exception as e:
        logger.error(f"Failed to compute ground truth for {task_data.get('id', 'task5')}: {e}")
        result["failure_type"] = "evaluation_error"
        result["failure_reason"] = f"Could not compute ground truth: {e}"
        return result

    # Check agent's action decision
    agent_made_post = any(
        step.get("tool_result", "").lower().find("fhir_post") >= 0 or
        '"accepted":true' in step.get("tool_result", "").lower()
        for step in trajectory
    )

    if should_order and not agent_made_post:
        result["failure_type"] = "missing_required_action"
        result["failure_reason"] = "Agent should have ordered magnesium replacement (MG < 1.9)"
        return result
    elif not should_order and agent_made_post:
        result["failure_type"] = "incorrect_action"
        result["failure_reason"] = "Agent should NOT have ordered magnesium (MG >= 1.9 or no recent measurement)"
        return result

    # All checks passed
    result["score"] = 1.0
    result["correct"] = True
    return result


def _evaluate_post_task(parsed_answer: list, task_data: dict, trajectory: list) -> dict:
    """Evaluate POST validation tasks using trajectory data.
    
    Checks that agent:
    1. Made at least one successful POST/create operation
    2. Returned an appropriate completion response (e.g., "ordered", "recorded")
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": ["action_completed"]
    }
    
    # Check if any POST was made in trajectory
    post_found = False
    post_accepted = False
    
    for step in trajectory:
        tool_result = step.get("tool_result", "")
        if isinstance(tool_result, str):
            # Check for fhir_post in result
            if "fhir_post" in tool_result.lower() or '"accepted":true' in tool_result.lower() or '"accepted": true' in tool_result.lower():
                post_found = True
                if ('"accepted":true' in tool_result.lower() or '"accepted": true' in tool_result.lower() or
                    '"status_code":200' in tool_result or '"status_code": 200' in tool_result):
                    post_accepted = True
                    break
    
    if not post_found:
        result["failure_type"] = "no_post_operation"
        result["failure_reason"] = "Agent did not perform any POST operation"
        return result
    
    if not post_accepted:
        result["failure_type"] = "post_rejected"
        result["failure_reason"] = "POST operation was not accepted by server"
        return result
    
    # Check agent's answer indicates completion
    valid_responses = ["ordered", "recorded", "created", "submitted", "completed", "done"]
    answer_valid = False
    
    if parsed_answer:
        for ans in parsed_answer:
            if isinstance(ans, str) and ans.lower() in valid_responses:
                answer_valid = True
                break
    
    if not answer_valid:
        # Still accept if POST was successful, just note the answer format
        logger.debug(f"POST task completed but answer {parsed_answer} not in expected format")
    
    # POST was successful
    result["score"] = 1.0
    result["correct"] = True
    return result


def _compare_answers(parsed_answer: list, ground_truth: list, task_data: dict = None) -> dict:
    """Compare parsed answer with ground truth using task-specific rules.
    
    Rules (from refsol.py):
    - task5, task9, task10: Accept [] as valid answer (agent may return empty for check tasks)
    - task6: Use 0.1 tolerance for floating point comparison (average glucose)
    - Others: Exact match after normalization
    """
    result = {
        "score": 0.0,
        "correct": False,
        "failure_type": None,
        "failure_reason": None,
        "computed_expected": ground_truth
    }
    
    task_id = task_data.get("id", "") if task_data else ""
    task_prefix = task_id.split("_")[0] if "_" in task_id else task_id
    
    # Task5, Task9, Task10: Accept empty list as valid answer
    # These are "check and act" tasks where agent may return [] after taking action
    if task_prefix in ("task5", "task9", "task10"):
        if parsed_answer == []:
            result["score"] = 1.0
            result["correct"] = True
            return result
    
    # Task6: Floating point comparison with 0.1 tolerance (average glucose)
    if task_prefix == "task6":
        if len(parsed_answer) == 1 and len(ground_truth) == 1:
            try:
                agent_value = float(parsed_answer[0])
                expected_value = float(ground_truth[0])
                if abs(agent_value - expected_value) < 0.1:
                    result["score"] = 1.0
                    result["correct"] = True
                    return result
            except (ValueError, TypeError):
                pass
        result["failure_type"] = "answer_mismatch"
        result["failure_reason"] = f"Expected {ground_truth}, got {parsed_answer}"
        return result
    
    # Default: Exact match after normalization
    normalized_answer = [normalize_answer(a) for a in parsed_answer]
    normalized_truth = [normalize_answer(t) for t in ground_truth]
    
    if normalized_answer == normalized_truth:
        result["score"] = 1.0
        result["correct"] = True
    else:
        result["failure_type"] = "answer_mismatch"
        result["failure_reason"] = f"Expected {ground_truth}, got {parsed_answer}"
    
    return result


if __name__ == "__main__":
    # Test evaluation
    print("Testing evaluate_task...")

    # Test static comparison
    result = evaluate_task(
        parsed_answer=["108"],
        ground_truth=["108"],
        task_data={"id": "task1_1", "readonly": True},
        agent_response_raw="FINISH([108])"
    )
    print(f"Static match: {result}")

    # Test mismatch
    result = evaluate_task(
        parsed_answer=["100"],
        ground_truth=["108"],
        task_data={"id": "task1_1", "readonly": True},
        agent_response_raw="FINISH([100])"
    )
    print(f"Mismatch: {result}")

    # Test task6 float comparison
    result = evaluate_task(
        parsed_answer=["123.45"],
        ground_truth=["123.5"],
        task_data={"id": "task6_1", "readonly": True},
        agent_response_raw="FINISH([123.45])"
    )
    print(f"Task6 float (within tolerance): {result}")

    # Test task5/9/10 empty list acceptance
    result = evaluate_task(
        parsed_answer=[],
        ground_truth=["1.5"],
        task_data={"id": "task5_1", "readonly": False},
        agent_response_raw="FINISH([])"
    )
    print(f"Task5 empty list: {result}")
