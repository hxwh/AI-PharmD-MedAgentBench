"""FHIR API client for making requests to FHIR server."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from ..fastmcp.app import FHIR_API_BASE


def build_fhir_url(base: str, path: str) -> str:
    """Build FHIR URL safely, avoiding double slashes."""
    if not base.endswith('/'):
        base = base + '/'
    path = path.lstrip('/')
    return urljoin(base, path)


def _extract_resource_type(path: str) -> str:
    """Extract FHIR resource type from path."""
    clean = path.strip('/').split('/')[0].split('?')[0]
    return clean if clean else "Unknown"


def _extract_post_fields(body: Optional[Dict]) -> Dict[str, Any]:
    """Extract key fields from POST body for structured logging."""
    if not body:
        return {}
    
    extracted = {}
    resource_type = body.get("resourceType", "Unknown")
    extracted["resourceType"] = resource_type
    
    if "subject" in body:
        extracted["subject"] = body["subject"].get("reference", "")
    
    if resource_type == "Observation":
        extracted["status"] = body.get("status")
        if "code" in body:
            extracted["code"] = body["code"].get("text", "")
        extracted["valueString"] = body.get("valueString")
        extracted["effectiveDateTime"] = body.get("effectiveDateTime")
    
    elif resource_type == "MedicationRequest":
        extracted["status"] = body.get("status")
        extracted["intent"] = body.get("intent")
        extracted["authoredOn"] = body.get("authoredOn")
        
        if "medicationCodeableConcept" in body:
            med = body["medicationCodeableConcept"]
            if "coding" in med and med["coding"]:
                extracted["medication_system"] = med["coding"][0].get("system")
                extracted["medication_code"] = med["coding"][0].get("code")
            extracted["medication_text"] = med.get("text")
        
        if "dosageInstruction" in body and body["dosageInstruction"]:
            di = body["dosageInstruction"][0]
            extracted["route"] = di.get("route")
            if "doseAndRate" in di and di["doseAndRate"]:
                dar = di["doseAndRate"][0]
                if "doseQuantity" in dar:
                    extracted["dose_value"] = dar["doseQuantity"].get("value")
                    extracted["dose_unit"] = dar["doseQuantity"].get("unit")
                if "rateQuantity" in dar:
                    extracted["rate_value"] = dar["rateQuantity"].get("value")
                    extracted["rate_unit"] = dar["rateQuantity"].get("unit")
    
    elif resource_type == "ServiceRequest":
        extracted["status"] = body.get("status")
        extracted["intent"] = body.get("intent")
        extracted["priority"] = body.get("priority")
        extracted["authoredOn"] = body.get("authoredOn")
        extracted["occurrenceDateTime"] = body.get("occurrenceDateTime")
        
        if "code" in body and "coding" in body["code"] and body["code"]["coding"]:
            extracted["code_system"] = body["code"]["coding"][0].get("system")
            extracted["code_value"] = body["code"]["coding"][0].get("code")
        
        if "note" in body:
            extracted["note"] = body["note"].get("text", "")[:100]
    
    return extracted


def call_fhir(method: str, path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a request to the FHIR server.
    
    For POST requests in benchmarking mode, logs the request but doesn't modify data.
    """
    url = build_fhir_url(FHIR_API_BASE, path)
    
    if method == "GET":
        params = params or {}
        if "_format" not in params:
            params["_format"] = "json"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            result: Dict[str, Any] = {"url": url, "method": method}
            
            if method == "GET":
                response = client.get(url, params=params)
                response.raise_for_status()
                result["status_code"] = response.status_code
                result["response"] = response.json()
            else:
                resource_type = _extract_resource_type(path)
                
                result["status_code"] = 200
                result["response"] = "POST request accepted"
                result["fhir_post"] = {
                    "fhir_url": url,
                    "operation": f"{resource_type}.Create",
                    "resource_type": resource_type,
                    "parameters": body,
                    "extracted_fields": _extract_post_fields(body),
                    "accepted": True
                }
            return result
    except httpx.HTTPError as e:
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail += f" - Response: {e.response.text}"
            except Exception:
                pass
        return {"error": f"FHIR server error: {error_detail}"}


def validate_post_request(
    extracted: Dict[str, Any],
    expected: Dict[str, Any],
    resource_type: str
) -> Dict[str, Any]:
    """Validate extracted POST fields against expected values."""
    issues: List[Dict[str, Any]] = []
    
    for field, expected_value in expected.items():
        actual_value = extracted.get(field)
        
        if actual_value is None and expected_value is not None:
            issues.append({
                "severity": "error",
                "code": "missing",
                "field": field,
                "expected": expected_value,
                "actual": None,
                "diagnostics": f"Missing required field: {field}"
            })
        elif actual_value != expected_value:
            if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                if abs(actual_value - expected_value) > 0.1:
                    issues.append({
                        "severity": "error",
                        "code": "value",
                        "field": field,
                        "expected": expected_value,
                        "actual": actual_value,
                        "diagnostics": f"Field {field}: expected {expected_value}, got {actual_value}"
                    })
            else:
                issues.append({
                    "severity": "error",
                    "code": "value",
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                    "diagnostics": f"Field {field}: expected '{expected_value}', got '{actual_value}'"
                })
    
    return {
        "resourceType": "OperationOutcome",
        "operation": f"{resource_type}.Create",
        "valid": len(issues) == 0,
        "issue_count": len(issues),
        "issue": issues
    }
