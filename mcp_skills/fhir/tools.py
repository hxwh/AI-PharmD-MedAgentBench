"""FHIR tools for PharmAgent MCP server.

These tools are available to both Green and Purple agents for clinical workflows.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional, Literal

from pydantic import Field

from ..fastmcp.app import mcp
from .client import call_fhir
from .models import (
    SubjectReference,
    VitalsCategoryElement,
    VitalsCodeObject,
    MedicationCodeableConcept,
    DosageInstruction,
    ServiceRequestCode,
    NoteObject,
)


# =============================================================================
# Patient Search
# =============================================================================

@mcp.tool()
def search_patients(
    identifier: Annotated[Optional[str], Field(description="The patient's identifier.")] = None,
    name: Annotated[Optional[str], Field(description="Any part of the patient's name.")] = None,
    family: Annotated[Optional[str], Field(description="The patient's family (last) name.")] = None,
    given: Annotated[Optional[str], Field(description="The patient's given name.")] = None,
    birthdate: Annotated[Optional[str], Field(description="Birth date in YYYY-MM-DD format.")] = None,
    gender: Annotated[Optional[str], Field(description="The patient's legal sex.")] = None,
) -> Dict[str, Any]:
    """Patient.Search - Filter or search for patients based on demographics."""
    params = {}
    if identifier: params["identifier"] = identifier

    # Intelligent name handling: if full name provided in 'name' but not specific parts
    # This fixes issues where FHIR server doesn't handle "First Last" in name param well
    if name and not family and not given and " " in name:
        parts = name.split()
        if len(parts) == 2:
            params["given"] = parts[0]
            params["family"] = parts[1]
        else:
            params["name"] = name
    elif name:
        params["name"] = name

    if family: params["family"] = family
    if given: params["given"] = given
    if birthdate: params["birthdate"] = birthdate
    if gender: params["gender"] = gender
    return call_fhir("GET", "/Patient", params=params)


# =============================================================================
# Clinical Data (Read)
# =============================================================================

@mcp.tool()
def list_patient_problems(
    patient: Annotated[str, Field(description="Reference to a patient resource.")],
    category: Annotated[Optional[str], Field(description="Always 'problem-list-item'.")] = None,
    count: Annotated[int, Field(description="Maximum number of conditions to return.")] = 1000,
) -> Dict[str, Any]:
    """Condition.Search (Problems) - Retrieve problems from a patient's chart."""
    params = {"patient": patient, "_count": count}
    if category: params["category"] = category
    return call_fhir("GET", "/Condition", params=params)


@mcp.tool()
def list_lab_observations(
    patient: Annotated[str, Field(description="Reference to a patient resource.")],
    code: Annotated[str, Field(description="The observation identifier (GLU, K, MG, HBA1C, A1C).")],
    date: Annotated[Optional[str], Field(description="Date when specimen was obtained.")] = None,
) -> Dict[str, Any]:
    """Observation.Search (Labs) - Return component level data for lab results."""
    params = {"patient": patient, "code": code}
    if date: params["date"] = date
    return call_fhir("GET", "/Observation", params=params)


@mcp.tool()
def get_latest_lab_value(
    patient: Annotated[str, Field(description="Patient reference (e.g., 'Patient/S2874099').")],
    code: Annotated[str, Field(description="Lab code: 'GLU', 'K', 'MG', 'HBA1C', 'A1C'.")],
) -> Dict[str, Any]:
    """Get the latest lab value for a patient in ONE call.
    
    This is the PREFERRED tool for getting the most recent lab result.
    """
    result = call_fhir("GET", "/Observation", params={"patient": patient, "code": code})
    
    if result.get("status_code") != 200:
        return {"error": f"FHIR request failed: {result.get('error', 'unknown')}", "found": False}
    
    response = result.get("response", {})
    entries = response.get("entry", [])
    
    if not entries:
        return {"latest_value": None, "latest_datetime": None, "found": False, "message": "No observations found"}
    
    latest_dt = None
    latest_value = None
    
    for entry in entries:
        resource = entry.get("resource", {})
        effective_str = resource.get("effectiveDateTime")
        if not effective_str:
            continue
        
        try:
            effective_dt = datetime.fromisoformat(effective_str.replace('Z', '+00:00'))
        except ValueError:
            continue
        
        if latest_dt is None or effective_dt > latest_dt:
            latest_dt = effective_dt
            if "valueQuantity" in resource:
                latest_value = resource["valueQuantity"].get("value")
            elif "valueString" in resource:
                latest_value = resource["valueString"]
    
    if latest_value is not None:
        return {
            "latest_value": latest_value,
            "latest_datetime": latest_dt.isoformat() if latest_dt else None,
            "found": True
        }
    else:
        return {"latest_value": None, "latest_datetime": None, "found": False, "message": "No valid observations found"}


@mcp.tool()
def list_vital_signs(
    patient: Annotated[str, Field(description="Reference to a patient resource.")],
    category: Annotated[str, Field(description="Use 'vital-signs'.")] = "vital-signs",
    date: Annotated[Optional[str], Field(description="The date range.")] = None,
) -> Dict[str, Any]:
    """Observation.Search (Vitals) - Retrieve vital sign data from a patient's chart."""
    params = {"patient": patient, "category": category}
    if date: params["date"] = date
    return call_fhir("GET", "/Observation", params=params)


@mcp.tool()
def list_medication_requests(
    patient: Annotated[str, Field(description="The FHIR patient ID.")],
    category: Annotated[Optional[str], Field(description="Category: 'Inpatient', 'Outpatient', 'Community', 'Discharge'.")] = None,
    date: Annotated[Optional[str], Field(description="The medication administration date.")] = None,
) -> Dict[str, Any]:
    """MedicationRequest.Search - Query for medication orders based on a patient."""
    params = {"patient": patient}
    if category: params["category"] = category
    if date: params["date"] = date
    return call_fhir("GET", "/MedicationRequest", params=params)


@mcp.tool()
def list_patient_procedures(
    patient: Annotated[str, Field(description="Reference to a patient resource.")],
    date: Annotated[str, Field(description="Date or period that the procedure was performed.")],
    code: Annotated[Optional[str], Field(description="External CPT codes.")] = None,
) -> Dict[str, Any]:
    """Procedure.Search - Retrieve completed procedures for a patient."""
    params = {"patient": patient, "date": date}
    if code: params["code"] = code
    return call_fhir("GET", "/Procedure", params=params)


# =============================================================================
# Clinical Data (Write)
# =============================================================================

@mcp.tool()
def record_vital_observation(
    resourceType: Annotated[str, Field(description="Use 'Observation'.")],
    category: Annotated[List[VitalsCategoryElement], Field(description="Array of category objects.")],
    code: Annotated[VitalsCodeObject, Field(description="Code object specifying what is measured.")],
    effectiveDateTime: Annotated[str, Field(description="The date and time in ISO format.")],
    status: Annotated[str, Field(description="The status. Only 'final' is supported.")],
    valueString: Annotated[str, Field(description="Measurement value as a string.")],
    subject: Annotated[SubjectReference, Field(description="The patient.")],
) -> Dict[str, Any]:
    """Observation.Create (Vitals) - File vital signs."""
    body = {
        "resourceType": resourceType,
        "category": [cat.model_dump() for cat in category],
        "code": code.model_dump(),
        "effectiveDateTime": effectiveDateTime,
        "status": status,
        "valueString": valueString,
        "subject": subject.model_dump(),
    }
    return call_fhir("POST", "/Observation", body=body)


@mcp.tool()
def create_medication_request(
    resourceType: Annotated[str, Field(description="Use 'MedicationRequest'.")],
    medicationCodeableConcept: Annotated[MedicationCodeableConcept, Field(description="Medication codeable concept.")],
    authoredOn: Annotated[str, Field(description="The date the prescription was written.")],
    dosageInstruction: Annotated[List[DosageInstruction], Field(description="Array of dosage instructions.")],
    status: Annotated[str, Field(description="Use 'active'.")],
    intent: Annotated[str, Field(description="Use 'order'.")],
    subject: Annotated[SubjectReference, Field(description="The patient.")],
) -> Dict[str, Any]:
    """MedicationRequest.Create - Create a medication order for a patient."""
    body = {
        "resourceType": resourceType,
        "medicationCodeableConcept": medicationCodeableConcept.model_dump(exclude_none=True),
        "authoredOn": authoredOn,
        "dosageInstruction": [di.model_dump(exclude_none=True) for di in dosageInstruction],
        "status": status,
        "intent": intent,
        "subject": subject.model_dump(),
    }
    return call_fhir("POST", "/MedicationRequest", body=body)


@mcp.tool()
def create_service_request(
    resourceType: Annotated[str, Field(description="Use 'ServiceRequest'.")],
    code: Annotated[ServiceRequestCode, Field(description="The standard terminology codes.")],
    authoredOn: Annotated[str, Field(description="The order instant in ISO format.")],
    status: Annotated[str, Field(description="Use 'active'.")],
    intent: Annotated[str, Field(description="Use 'order'.")],
    priority: Annotated[Literal["stat"], Field(description="Priority. Must be 'stat'.")],
    subject: Annotated[SubjectReference, Field(description="The patient.")],
    occurrenceDateTime: Annotated[Optional[str], Field(description="When to conduct.")] = None,
    note: Annotated[Optional[NoteObject], Field(description="Free text comment.")] = None,
) -> Dict[str, Any]:
    """ServiceRequest.Create - Create an order for labs, imaging, or consults."""
    body = {
        "resourceType": resourceType,
        "code": code.model_dump(),
        "authoredOn": authoredOn,
        "status": status,
        "intent": intent,
        "priority": priority,
        "subject": subject.model_dump(),
    }
    if occurrenceDateTime: body["occurrenceDateTime"] = occurrenceDateTime
    if note: body["note"] = note.model_dump()
    return call_fhir("POST", "/ServiceRequest", body=body)


# =============================================================================
# Utility Tools
# =============================================================================

@mcp.tool()
def check_date_within_period(
    date_to_check: Annotated[str, Field(description="The date to check, in ISO format.")],
    reference_date: Annotated[str, Field(description="The reference date to compare against.")],
    period_days: Annotated[int, Field(description="The number of days for the period.")],
) -> Dict[str, Any]:
    """Check if a date is within a specified period from a reference date."""
    try:
        def parse_date(s: str) -> datetime:
            s = s.replace('Z', '+00:00')
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return datetime.fromisoformat(s.split('+')[0])
        
        check_date = parse_date(date_to_check)
        ref_date = parse_date(reference_date)
        cutoff = ref_date - timedelta(days=period_days)
        is_within = check_date >= cutoff
        days_diff = (ref_date - check_date).days
        
        return {
            "date_to_check": date_to_check,
            "reference_date": reference_date,
            "period_days": period_days,
            "cutoff_date": cutoff.isoformat(),
            "is_within_period": is_within,
            "days_since_date": days_diff,
            "action": "DO_NOT_ORDER" if is_within else "ORDER_NEW_TEST"
        }
    except Exception as e:
        return {"error": f"Date parsing failed: {e}"}


@mcp.tool()
def calculate_age(
    birth_date: Annotated[str, Field(description="The patient's birth date.")],
    reference_date: Annotated[str, Field(description="The reference date.")],
) -> Dict[str, Any]:
    """Calculate a patient's age in years from their birth date."""
    try:
        birth_str = birth_date.replace('Z', '+00:00')
        if 'T' not in birth_str:
            birth_str += 'T00:00:00+00:00'
        birth = datetime.fromisoformat(birth_str)
        
        ref_str = reference_date.replace('Z', '+00:00')
        ref = datetime.fromisoformat(ref_str)
        
        age = ref.year - birth.year
        if (ref.month, ref.day) < (birth.month, birth.day):
            age -= 1
        
        return {
            "birth_date": birth_date,
            "reference_date": reference_date,
            "age_years": age,
        }
    except Exception as e:
        return {"error": f"Age calculation failed: {e}"}


@mcp.tool()
def evaluate_potassium_level(
    potassium_value: Annotated[float, Field(description="Potassium level (mmol/L)")],
    threshold: Annotated[float, Field(description="Threshold (mmol/L)")],
) -> Dict[str, Any]:
    """Evaluate if potassium is low or normal."""
    is_low = potassium_value < threshold
    return {
        "potassium_value": potassium_value,
        "threshold": threshold,
        "is_low": is_low,
        "status": "LOW" if is_low else "NORMAL",
    }


@mcp.tool()
def evaluate_magnesium_level(
    magnesium_value: Annotated[float, Field(description="The magnesium level in mg/dL.")],
) -> Dict[str, Any]:
    """Evaluate magnesium level and determine if IV replacement is needed."""
    if magnesium_value >= 1.9:
        return {"magnesium_value": magnesium_value, "status": "NORMAL", "needs_replacement": False, "action": "DO_NOT_ORDER"}
    elif magnesium_value >= 1.5:
        return {"magnesium_value": magnesium_value, "status": "MILD_DEFICIENCY", "needs_replacement": True, "dose_grams": 1, "infusion_hours": 1, "action": "ORDER_1G_OVER_1H"}
    elif magnesium_value >= 1.0:
        return {"magnesium_value": magnesium_value, "status": "MODERATE_DEFICIENCY", "needs_replacement": True, "dose_grams": 2, "infusion_hours": 2, "action": "ORDER_2G_OVER_2H"}
    else:
        return {"magnesium_value": magnesium_value, "status": "SEVERE_DEFICIENCY", "needs_replacement": True, "dose_grams": 4, "infusion_hours": 4, "action": "ORDER_4G_OVER_4H"}


@mcp.tool()
def calculate_potassium_dose(
    potassium_value: Annotated[float, Field(description="The potassium level in mmol/L.")],
    threshold: Annotated[float, Field(description="The threshold for hypokalemia.")] = 3.5,
) -> Dict[str, Any]:
    """Calculate oral potassium replacement dose for hypokalemia."""
    if potassium_value >= threshold:
        return {
            "potassium_value": potassium_value,
            "threshold": threshold,
            "status": "NORMAL",
            "needs_replacement": False,
            "action": "DO_NOT_ORDER"
        }
    
    deficit = threshold - potassium_value
    dose_mEq = (deficit / 0.1) * 10
    
    return {
        "potassium_value": potassium_value,
        "threshold": threshold,
        "deficit_mmol_L": deficit,
        "status": "LOW",
        "needs_replacement": True,
        "dose_mEq": round(dose_mEq, 1),
        "route": "oral",
        "medication_ndc": "40032-917-01",
        "action": "ORDER_ORAL_KCL"
    }


@mcp.tool()
def get_latest_observation_value(
    observations_json: Annotated[str, Field(description="JSON string of FHIR Bundle.")],
    cutoff_hours: Annotated[Optional[int], Field(description="Only consider observations within this many hours.")] = None,
    reference_datetime: Annotated[str, Field(description="Reference datetime in ISO format.")] = "2023-11-13T10:15:00+00:00",
) -> Dict[str, Any]:
    """Extract the latest observation value from a FHIR Observation bundle."""
    import json
    
    try:
        data = json.loads(observations_json) if isinstance(observations_json, str) else observations_json
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "found": False}
    
    entries = data.get("entry", []) if isinstance(data, dict) else []
    if not entries:
        return {"latest_value": None, "latest_datetime": None, "found": False, "message": "No observations found"}
    
    ref_dt = datetime.fromisoformat(reference_datetime.replace('Z', '+00:00'))
    cutoff_dt = ref_dt - timedelta(hours=cutoff_hours) if cutoff_hours else None
    
    latest_dt = None
    latest_value = None
    
    for entry in entries:
        resource = entry.get("resource", {})
        effective_str = resource.get("effectiveDateTime")
        if not effective_str:
            continue
        
        try:
            effective_dt = datetime.fromisoformat(effective_str.replace('Z', '+00:00'))
        except ValueError:
            continue
        
        if cutoff_dt and effective_dt < cutoff_dt:
            continue
        
        if latest_dt is None or effective_dt > latest_dt:
            latest_dt = effective_dt
            if "valueQuantity" in resource:
                latest_value = resource["valueQuantity"].get("value")
            elif "valueString" in resource:
                latest_value = resource["valueString"]
    
    if latest_value is not None:
        return {
            "latest_value": latest_value,
            "latest_datetime": latest_dt.isoformat() if latest_dt else None,
            "found": True
        }
    else:
        return {"latest_value": None, "latest_datetime": None, "found": False, "message": "No valid observations in range"}


@mcp.tool()
def get_patient_conditions(
    patient: Annotated[str, Field(description="Patient reference (e.g., 'Patient/S2874099').")],
) -> Dict[str, Any]:
    """Get simplified condition names for a patient in ONE call."""
    result = call_fhir("GET", "/Condition", params={"patient": patient, "_count": 1000})
    
    if result.get("status_code") != 200:
        return {"error": f"FHIR request failed: {result.get('error', 'unknown')}", "found": False}
    
    response = result.get("response", {})
    entries = response.get("entry", [])
    
    if not entries:
        return {"conditions": [], "found": False, "message": "No conditions found"}
    
    icd_mapping = {
        "E10": "Diabetes", "E11": "Diabetes",
        "I10": "Hypertension", "I11": "Hypertension", "I12": "Hypertension",
        "I13": "Hypertension", "I15": "Hypertension", "I16": "Hypertension",
        "I25": "Coronary Artery Disease",
        "I48": "Atrial Fibrillation",
        "I63": "Stroke",
        "I71": "Aortic Aneurysm",
    }
    
    simplified_conditions = []
    seen_categories = set()
    
    for entry in entries:
        resource = entry.get("resource", {})
        coding = resource.get("code", {}).get("coding", [])
        
        for code_obj in coding:
            icd_code = code_obj.get("code", "")
            if not icd_code:
                continue
            
            category = icd_code[:3]
            if category in seen_categories:
                continue
            
            if category in icd_mapping:
                condition_name = icd_mapping[category]
                if condition_name not in simplified_conditions:
                    simplified_conditions.append(condition_name)
                seen_categories.add(category)
    
    return {
        "conditions": simplified_conditions,
        "found": len(simplified_conditions) > 0,
        "count": len(simplified_conditions)
    }


@mcp.tool()
def extract_simplified_conditions(
    conditions_json: Annotated[str, Field(description="JSON string of FHIR Bundle containing Condition entries.")],
) -> Dict[str, Any]:
    """Extract simplified condition names from FHIR Condition bundle."""
    import json
    
    try:
        data = json.loads(conditions_json) if isinstance(conditions_json, str) else conditions_json
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "found": False}
    
    entries = data.get("entry", []) if isinstance(data, dict) else []
    if not entries:
        return {"conditions": [], "found": False, "message": "No conditions found"}
    
    icd_mapping = {
        "E10": "Diabetes", "E11": "Diabetes",
        "I10": "Hypertension", "I11": "Hypertension", "I12": "Hypertension",
        "I13": "Hypertension", "I15": "Hypertension", "I16": "Hypertension",
        "I25": "Coronary Artery Disease",
        "I48": "Atrial Fibrillation",
        "I63": "Stroke",
        "I71": "Aortic Aneurysm",
    }
    
    simplified_conditions = []
    seen_codes = set()
    
    for entry in entries:
        resource = entry.get("resource", {})
        coding = resource.get("code", {}).get("coding", [])
        
        for code_obj in coding:
            icd_code = code_obj.get("code", "")
            if not icd_code:
                continue
            
            category = icd_code[:3]
            
            if category in seen_codes:
                continue
            
            if category in icd_mapping:
                simplified_conditions.append(icd_mapping[category])
                seen_codes.add(category)
            else:
                display = code_obj.get("display", "")
                if display:
                    words = display.split()
                    skip_words = {"of", "the", "a", "an", "without", "with", "unspecified", "other"}
                    meaningful = [w.capitalize() for w in words[:3] if w.lower() not in skip_words]
                    if meaningful:
                        simplified_name = " ".join(meaningful)
                        if simplified_name not in simplified_conditions:
                            simplified_conditions.append(simplified_name)
    
    return {
        "conditions": simplified_conditions,
        "found": len(simplified_conditions) > 0,
        "count": len(simplified_conditions)
    }


@mcp.tool()
def calculate_average_observation(
    observations_json: Annotated[str, Field(description="JSON string of FHIR Bundle.")],
    cutoff_hours: Annotated[int, Field(description="Only consider observations within this many hours.")],
    reference_datetime: Annotated[str, Field(description="Reference datetime.")] = "2023-11-13T10:15:00+00:00",
) -> Dict[str, Any]:
    """Calculate the average of observation values within a time window."""
    import json
    
    try:
        data = json.loads(observations_json) if isinstance(observations_json, str) else observations_json
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "found": False}
    
    entries = data.get("entry", []) if isinstance(data, dict) else []
    if not entries:
        return {"average": -1, "count": 0, "found": False, "message": "No observations found"}
    
    ref_dt = datetime.fromisoformat(reference_datetime.replace('Z', '+00:00'))
    cutoff_dt = ref_dt - timedelta(hours=cutoff_hours)
    
    values = []
    
    for entry in entries:
        resource = entry.get("resource", {})
        effective_str = resource.get("effectiveDateTime")
        if not effective_str:
            continue
        
        try:
            effective_dt = datetime.fromisoformat(effective_str.replace('Z', '+00:00'))
        except ValueError:
            continue
        
        if effective_dt < cutoff_dt:
            continue
        
        if "valueQuantity" in resource:
            val = resource["valueQuantity"].get("value")
            if val is not None:
                values.append(float(val))
    
    if not values:
        return {"average": -1, "count": 0, "found": False, "message": "No observations in time range"}
    
    avg = sum(values) / len(values)
    return {
        "average": avg,
        "count": len(values),
        "found": True
    }
