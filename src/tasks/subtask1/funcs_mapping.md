# FHIR API to MCP Tools Mapping

This document maps the original `funcs_v1.json` FHIR API endpoints to the MCP tools in `tools.py`.

## Dynamic Tool Discovery

The agent can discover tools at runtime instead of using hardcoded definitions:

```python
# Enable dynamic discovery in config
config = {
    "mcp_server_url": "http://localhost:8002",
    "dynamic_tools": True  # NEW: Enable runtime tool discovery
}

# How it works internally:
from utils.mcp_discovery import discover_tools_sync
result = discover_tools_sync("http://localhost:8002")
print(result["formatted"])  # Tool descriptions for prompt
print(result["count"])      # Number of tools discovered
```

Benefits:
- Tools are discovered from MCP server at runtime
- No need to update prompts when tools change
- Automatic categorization (Search, Read, Write, Utilities)
- Falls back to static template if discovery fails

## Direct Mappings (1:1)

| Original API (`funcs_v1.json`) | MCP Tool (`funcs_mcp.json`) |
|-------------------------------|----------------------------|
| `GET {api_base}/Patient` | `search_patients` |
| `GET {api_base}/Condition` | `list_patient_problems` |
| `GET {api_base}/Observation` (Labs) | `list_lab_observations` |
| `GET {api_base}/Observation` (Vitals) | `list_vital_signs` |
| `POST {api_base}/Observation` | `record_vital_observation` |
| `GET {api_base}/MedicationRequest` | `list_medication_requests` |
| `POST {api_base}/MedicationRequest` | `create_medication_request` |
| `GET {api_base}/Procedure` | `list_patient_procedures` |
| `POST {api_base}/ServiceRequest` | `create_service_request` |

## Convenience Tools (New in MCP)

These tools combine multiple operations or add processing logic:

| MCP Tool | Purpose | Replaces |
|----------|---------|----------|
| `get_latest_lab_value` | Get most recent lab in ONE call | `list_lab_observations` + `get_latest_observation_value` |
| `get_patient_conditions` | Get simplified condition names | `list_patient_problems` + `extract_simplified_conditions` |

## Utility Tools (New in MCP)

These provide clinical decision support:

| MCP Tool | Purpose |
|----------|---------|
| `check_date_within_period` | Check if date is recent enough |
| `calculate_age` | Calculate patient age in years |
| `evaluate_potassium_level` | Evaluate if K+ is low |
| `evaluate_magnesium_level` | Evaluate Mg level + dosing |
| `calculate_potassium_dose` | Calculate KCl replacement dose |
| `get_latest_observation_value` | Extract latest value from FHIR bundle |
| `extract_simplified_conditions` | Map ICD-10 to readable names |
| `calculate_average_observation` | Calculate average within time window |

## Key Parameter Differences

### Patient Reference
- **funcs_v1.json**: `"patient": "S2874099"` (just ID)
- **funcs_mcp.json**: `"patient": "Patient/S2874099"` (FHIR reference format)

### Complex Objects
POST requests use Pydantic models in `tools.py`. The `funcs_mcp.json` flattens these into JSON schema:

```python
# tools.py uses Pydantic models:
subject: SubjectReference  # -> {"reference": "Patient/12345"}
dosageInstruction: List[DosageInstruction]  # -> Nested JSON

# funcs_mcp.json uses inline JSON schema
```

## Structured POST Response Format

POST requests return structured metadata for validation and debugging:

```json
{
  "fhir_post": {
    "fhir_url": "http://localhost:8080/fhir/MedicationRequest",
    "operation": "MedicationRequest.Create",
    "resource_type": "MedicationRequest",
    "parameters": { /* full request body */ },
    "extracted_fields": {
      "resourceType": "MedicationRequest",
      "subject": "Patient/S2874099",
      "status": "active",
      "route": "IV",
      "dose_value": 2,
      "dose_unit": "g",
      "medication_code": "0338-1715-40"
    },
    "accepted": true
  }
}
```

### Multi-Error Validation

The `validate_post_request()` function reports ALL errors at once:

```json
{
  "resourceType": "OperationOutcome",
  "operation": "MedicationRequest.Create",
  "valid": false,
  "issue_count": 3,
  "issue": [
    {"severity": "error", "field": "route", "expected": "IV", "actual": "oral"},
    {"severity": "error", "field": "dose_value", "expected": 2, "actual": 4},
    {"severity": "error", "field": "rate_value", "expected": 2, "actual": 4}
  ]
}
```

This is useful for debugging agents - if a MedicationRequest has both wrong dose AND wrong route, both failures are reported.

## Usage Recommendations

1. **Prefer convenience tools** (`get_latest_lab_value`, `get_patient_conditions`) over raw FHIR queries
2. **Use utility tools** for clinical logic instead of implementing in agent code
3. **Follow FHIR reference format** for patient IDs: `"Patient/{id}"`
