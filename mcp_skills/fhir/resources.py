"""MCP resources for PharmAgent tasks and prompts."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ..fastmcp.app import mcp


# Evaluator to required tools mapping
EVALUATOR_TOOLS_MAP: Dict[str, List[str]] = {
    "task1": ["search_patients", "list_patient_problems"],
    "task2": ["search_patients", "calculate_age"],
    "task3": ["search_patients", "record_vital_observation"],
    "task4": ["search_patients", "list_lab_observations", "get_latest_observation_value"],
    "task5": ["search_patients", "list_lab_observations", "get_latest_observation_value", "evaluate_magnesium_level", "create_medication_request"],
    "task6": ["search_patients", "list_lab_observations", "calculate_average_observation"],
    "task7": ["search_patients", "list_lab_observations", "get_latest_observation_value"],
    "task8": ["search_patients", "create_service_request"],
    "task9": ["search_patients", "list_lab_observations", "get_latest_observation_value", "evaluate_potassium_level", "calculate_potassium_dose", "create_medication_request", "create_service_request"],
    "task10": ["search_patients", "list_lab_observations", "get_latest_observation_value", "check_date_within_period", "create_service_request"],
}


@mcp.resource("pharmd://prompts/agent")
def get_agent_prompt() -> str:
    """Agent prompt template for PharmAgent evaluation."""
    return """You are a medical AI agent with access to FHIR tools via MCP.

Available Tool Categories:
1. Patient Search - Find patients by demographics
2. Clinical Read - Get lab values, conditions, medications, vitals
3. Clinical Write - Create observations, medication requests, service requests
4. Utilities - Date calculations, lab value evaluations

Lab Codes:
- GLU: Blood glucose
- K: Potassium
- MG: Magnesium
- HBA1C/A1C: Glycated hemoglobin

For best results:
- Use get_latest_lab_value() for recent lab values
- Use get_patient_conditions() for problem lists
- Use combined tools instead of passing large JSON between calls
"""


@mcp.resource("pharmd://tools/catalog")
def get_tools_catalog() -> str:
    """Catalog of available FHIR tools and their purposes."""
    catalog = {
        "name": "PharmAgent FHIR Tools Catalog",
        "categories": {
            "patient": {
                "description": "Patient search and demographics",
                "tools": ["search_patients"]
            },
            "clinical_read": {
                "description": "Read clinical data (labs, vitals, conditions, medications, procedures)",
                "tools": [
                    "list_patient_problems",
                    "list_lab_observations",
                    "list_vital_signs",
                    "list_medication_requests",
                    "list_patient_procedures"
                ]
            },
            "clinical_write": {
                "description": "Create clinical orders and observations",
                "tools": [
                    "record_vital_observation",
                    "create_medication_request",
                    "create_service_request"
                ]
            },
            "utilities": {
                "description": "Calculation and evaluation utilities",
                "tools": [
                    "calculate_age",
                    "check_date_within_period",
                    "evaluate_potassium_level",
                    "evaluate_magnesium_level",
                    "calculate_potassium_dose",
                    "get_latest_observation_value",
                    "calculate_average_observation"
                ]
            }
        },
        "lab_codes": {
            "GLU": "Blood glucose",
            "K": "Potassium",
            "MG": "Magnesium",
            "A1C": "HbA1c (glycated hemoglobin)",
            "HBA1C": "HbA1c (alternative code)"
        },
        "medication_ndc_codes": {
            "0338-1715-40": "Magnesium sulfate (IV)",
            "40032-917-01": "Potassium chloride (oral)"
        },
        "service_request_codes": {
            "loinc": {
                "2823-3": "Potassium serum/plasma",
                "4548-4": "HbA1c"
            },
            "snomed": {
                "306181000000106": "Referral to orthopedic service"
            }
        }
    }
    return json.dumps(catalog, indent=2)
