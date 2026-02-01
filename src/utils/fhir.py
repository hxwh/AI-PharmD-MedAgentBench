"""FHIR API utilities for MedAgentBench evaluation."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

from tasks.subtask1.utils import send_get_request

logger = logging.getLogger("medagentbench")

FHIR_API_BASE = os.environ.get("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")


def fetch_latest_observation(mrn: str, lab_code: str) -> tuple[Optional[float], Optional[datetime]]:
    """Fetch the latest observation value for a patient and lab code.
    
    Args:
        mrn: Patient MRN (without 'Patient/' prefix)
        lab_code: FHIR observation code (e.g., 'GLU', 'MG')
    
    Returns:
        Tuple of (value, effective_datetime) or (None, None) if not found
    """
    url = f"{FHIR_API_BASE}Observation?patient={mrn}&code={lab_code}&_count=5000&_format=json"
    logger.debug(f"Fetching observation: {url}")
    
    response = send_get_request(url)
    if response.get("status_code") != 200:
        logger.warning(f"FHIR request failed: {response.get('error', 'Unknown error')}")
        return None, None
    
    data = json.loads(response.get("data", "{}"))
    latest_time, latest_value = None, None
    
    for entry in data.get("entry", []):
        resource = entry.get("resource", {})
        try:
            effective_time = datetime.fromisoformat(resource["effectiveDateTime"])
            value = resource["valueQuantity"]["value"]
            if latest_time is None or effective_time > latest_time:
                latest_time = effective_time
                latest_value = value
        except (KeyError, ValueError) as e:
            logger.debug(f"Skipping malformed entry: {e}")
            continue
    
    return latest_value, latest_time


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
        numeric_match = re.search(r'\d+\.?\d*', val)
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


if __name__ == "__main__":
    # Test FHIR utilities
    print("Testing fetch_latest_observation...")
    value, ts = fetch_latest_observation("S2874099", "GLU")
    print(f"Glucose: {value} at {ts}")
    
    print("\nTesting normalize_answer...")
    test_cases = [
        ("108.0 mg/dL", "108"),
        ("108", "108"),
        (108.0, "108"),
        (108, "108"),
        ("ORDERED", "ordered"),
        ("No action needed", "noactionneeded"),
    ]
    for inp, expected in test_cases:
        result = normalize_answer(inp)
        status = "✓" if result == expected else "✗"
        print(f"  {status} normalize_answer({inp!r}) = {result!r} (expected {expected!r})")
