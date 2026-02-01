"""Evaluation tools for Green Agent - provides groundtruth access.

These tools are ONLY available to the Green Agent and provide access to
evaluation functions from refsol_eval.py for validating clinical decisions.

Purple Agent does NOT have access to these tools and must rely entirely
on clinical reasoning.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

import httpx
from pydantic import Field

from ..fastmcp.app import mcp, FHIR_API_BASE


# =============================================================================
# Helper Functions (adapted from refsol_eval.py)
# =============================================================================

def _send_get_request(url: str, timeout: float = 30.0) -> dict:
    """Send GET request to FHIR server and return response."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return {
                "status_code": response.status_code,
                "data": response.text
            }
    except httpx.HTTPError as e:
        return {
            "status_code": getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
            "error": str(e),
            "data": "{}"
        }


def _calculate_age(dob: datetime) -> int:
    """Calculate age from date of birth."""
    today = datetime(2023, 11, 13)
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


# =============================================================================
# Evaluation Tools (Green Agent Only)
# =============================================================================

@mcp.tool()
def get_task1_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier (e.g., 'S2874099').")],
    expected_conditions: Annotated[str, Field(description="JSON list of expected conditions from case data.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 1 - Problem list retrieval.
    
    Returns whether the expected conditions match the reference solution.
    Task 1 expects NO POST requests and the result should match the expected conditions.
    """
    try:
        expected = json.loads(expected_conditions)
        return {
            "task": "task1",
            "patient_mrn": patient_mrn,
            "groundtruth": expected,
            "evaluation_criteria": "Result must match expected conditions exactly, no POST requests allowed"
        }
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON for expected_conditions: {e}"}


@mcp.tool()
def get_task2_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 2 - Patient age calculation.
    
    Queries FHIR to get patient DOB and calculates the expected age.
    """
    url = f"{FHIR_API_BASE}Patient?identifier={patient_mrn}&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch patient: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        dob_str = data['entry'][0]['resource']['birthDate']
        parsed_date = datetime.strptime(dob_str, "%Y-%m-%d")
        expected_age = _calculate_age(parsed_date)
        
        return {
            "task": "task2",
            "patient_mrn": patient_mrn,
            "birth_date": dob_str,
            "groundtruth": [expected_age],
            "evaluation_criteria": "Result must be a list with single age value, no POST requests allowed"
        }
    except (KeyError, IndexError, ValueError) as e:
        return {"error": f"Failed to parse patient data: {e}"}


@mcp.tool()
def get_task4_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 4 - Latest magnesium in 24h.
    
    Returns the latest MG value within 24 hours of reference time.
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=MG&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        cutoff = datetime.fromisoformat("2023-11-13T10:15:00+00:00")
        last_meas, last_value = None, None
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if effective_time >= (cutoff - timedelta(hours=24)):
                if (last_meas is None) or (effective_time > last_meas):
                    last_meas = effective_time
                    last_value = value
        
        groundtruth = [last_value if last_value is not None else -1]
        
        return {
            "task": "task4",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "latest_datetime": last_meas.isoformat() if last_meas else None,
            "evaluation_criteria": "Result must match groundtruth, no POST requests allowed"
        }
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def get_task5_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 5 - MG check and replacement.
    
    Returns expected MG value and dosing if replacement needed.
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=MG&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        cutoff = datetime.fromisoformat("2023-11-13T10:15:00+00:00")
        last_meas, last_value = None, None
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if effective_time >= (cutoff - timedelta(hours=24)):
                if (last_meas is None) or (effective_time > last_meas):
                    last_meas = effective_time
                    last_value = value
        
        groundtruth = [last_value if last_value is not None else -1]
        
        result: Dict[str, Any] = {
            "task": "task5",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "mg_value": last_value,
        }
        
        if last_value is None:
            result["action"] = "NO_ORDER_NEEDED"
            result["reason"] = "No MG value available"
        elif last_value > 1.9:
            result["action"] = "NO_ORDER_NEEDED"
            result["reason"] = "MG level normal (>= 1.9)"
        else:
            # Determine dose based on MG level
            if last_value < 1:
                dose, rate = 4, 4
            elif last_value < 1.5:
                dose, rate = 2, 2
            else:
                dose, rate = 1, 1
            
            result["action"] = "ORDER_IV_MAGNESIUM"
            result["expected_order"] = {
                "medication_ndc": "0338-1715-40",
                "route": "IV",
                "dose_grams": dose,
                "infusion_hours": rate,
                "authoredOn": "2023-11-13T10:15:00+00:00"
            }
        
        return result
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def get_task6_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 6 - Average glucose in 24h.
    
    Returns the average GLU value within 24 hours of reference time.
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=GLU&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        cutoff = datetime.fromisoformat("2023-11-13T10:15:00+00:00")
        glu_sum, glu_count = 0.0, 0.0
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if effective_time >= (cutoff - timedelta(hours=24)):
                glu_sum += value
                glu_count += 1
        
        groundtruth = [glu_sum / glu_count if glu_count != 0 else -1]
        
        return {
            "task": "task6",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "sample_count": int(glu_count),
            "evaluation_criteria": "Result must be within 0.1 of groundtruth, no POST requests allowed"
        }
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def get_task7_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 7 - Latest glucose (all time).
    
    Returns the most recent GLU value regardless of time cutoff.
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=GLU&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        last_meas, last_value = None, None
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if (last_meas is None) or (effective_time > last_meas):
                last_meas = effective_time
                last_value = value
        
        groundtruth = [last_value if last_value is not None else -1]
        
        return {
            "task": "task7",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "latest_datetime": last_meas.isoformat() if last_meas else None,
            "evaluation_criteria": "Result must match groundtruth, no POST requests allowed"
        }
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def get_task9_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 9 - Potassium check and replacement.
    
    Returns expected K value and dosing if replacement needed.
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=K&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        last_meas, last_value = None, None
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if (last_meas is None) or (effective_time > last_meas):
                last_meas = effective_time
                last_value = value
        
        groundtruth = [last_value if last_value is not None else -1]
        
        result: Dict[str, Any] = {
            "task": "task9",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "k_value": last_value,
        }
        
        if last_value is None or last_value >= 3.5:
            result["action"] = "NO_ORDER_NEEDED"
            result["reason"] = "K level normal (>= 3.5) or unavailable"
        else:
            # Calculate dose: (3.5 - K) / 0.1 * 10 mEq
            dose = (3.5 - last_value) / 0.1 * 10
            
            result["action"] = "ORDER_ORAL_KCL_AND_RECHECK"
            result["expected_medication_order"] = {
                "medication_ndc": "40032-917-01",
                "route": "oral",
                "dose_mEq": dose,
                "authoredOn": "2023-11-13T10:15:00+00:00"
            }
            result["expected_service_request"] = {
                "code_system": "http://loinc.org",
                "code_value": "2823-3",  # Potassium serum/plasma
                "priority": "stat",
                "occurrenceDateTime_contains": "2023-11-14T08:"
            }
        
        return result
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def get_task10_groundtruth(
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Get groundtruth for Task 10 - A1C check and order if needed.
    
    Returns expected A1C value and whether a new order is needed (if >1 year old).
    """
    url = f"{FHIR_API_BASE}Observation?patient={patient_mrn}&code=A1C&_count=5000&_format=json"
    get_res = _send_get_request(url)
    
    if get_res.get("status_code") != 200:
        return {"error": f"Failed to fetch observations: {get_res.get('error', 'unknown')}"}
    
    try:
        data = json.loads(get_res['data'])
        cutoff = datetime.fromisoformat("2023-11-13T10:15:00+00:00")
        one_year_ago = datetime.fromisoformat("2022-11-13T10:15:00+00:00")
        
        last_meas, last_value, last_time = None, None, None
        
        for entry in data.get('entry', []):
            effective_time = datetime.fromisoformat(entry['resource']['effectiveDateTime'])
            value = entry['resource']['valueQuantity']['value']
            if (last_meas is None) or (effective_time > last_meas):
                last_meas = effective_time
                last_time = entry['resource']['effectiveDateTime']
                last_value = value
        
        if last_value is None:
            groundtruth = [-1]
        else:
            groundtruth = [last_value, last_time]
        
        result: Dict[str, Any] = {
            "task": "task10",
            "patient_mrn": patient_mrn,
            "groundtruth": groundtruth,
            "a1c_value": last_value,
            "a1c_datetime": last_time,
        }
        
        if last_value is None or last_meas < one_year_ago:
            result["action"] = "ORDER_NEW_A1C"
            result["reason"] = "A1C unavailable or older than 1 year"
            result["expected_service_request"] = {
                "code_system": "http://loinc.org",
                "code_value": "4548-4",  # HbA1c
                "priority": "stat",
                "authoredOn": "2023-11-13T10:15:00+00:00"
            }
        else:
            result["action"] = "NO_ORDER_NEEDED"
            result["reason"] = "A1C is within 1 year"
        
        return result
    except (KeyError, ValueError) as e:
        return {"error": f"Failed to parse observation data: {e}"}


@mcp.tool()
def validate_task_result(
    task_id: Annotated[str, Field(description="Task ID (task1 through task10).")],
    agent_result: Annotated[str, Field(description="Agent's result as JSON string.")],
    patient_mrn: Annotated[str, Field(description="Patient MRN/identifier.")],
) -> Dict[str, Any]:
    """[GREEN AGENT ONLY] Validate agent's result against groundtruth.
    
    Compares the agent's answer to the expected answer for the given task.
    Returns validation result with detailed feedback.
    """
    # Get groundtruth based on task
    groundtruth_funcs = {
        "task2": get_task2_groundtruth,
        "task4": get_task4_groundtruth,
        "task5": get_task5_groundtruth,
        "task6": get_task6_groundtruth,
        "task7": get_task7_groundtruth,
        "task9": get_task9_groundtruth,
        "task10": get_task10_groundtruth,
    }
    
    if task_id not in groundtruth_funcs:
        return {
            "valid": False,
            "error": f"Task {task_id} validation not supported. Supported: {list(groundtruth_funcs.keys())}"
        }
    
    # Get groundtruth
    gt_result = groundtruth_funcs[task_id](patient_mrn)
    
    if "error" in gt_result:
        return {"valid": False, "error": gt_result["error"]}
    
    groundtruth = gt_result.get("groundtruth")
    
    # Parse agent result
    try:
        agent_answer = json.loads(agent_result)
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"Invalid JSON in agent_result: {e}"}
    
    # Compare results
    if task_id == "task6":
        # Task 6 allows tolerance of 0.1
        if isinstance(agent_answer, list) and len(agent_answer) == 1:
            if isinstance(agent_answer[0], (int, float)) and isinstance(groundtruth[0], (int, float)):
                if abs(agent_answer[0] - groundtruth[0]) < 0.1:
                    return {"valid": True, "agent_result": agent_answer, "groundtruth": groundtruth}
    
    if agent_answer == groundtruth:
        return {"valid": True, "agent_result": agent_answer, "groundtruth": groundtruth}
    
    # For tasks that allow empty result
    if task_id in ["task5", "task9", "task10"] and agent_answer == []:
        return {
            "valid": True,
            "agent_result": agent_answer,
            "groundtruth": groundtruth,
            "note": "Empty result accepted for this task"
        }
    
    return {
        "valid": False,
        "agent_result": agent_answer,
        "groundtruth": groundtruth,
        "mismatch": True
    }
