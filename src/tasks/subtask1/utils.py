"""Utility functions for MedAgentBench task evaluation."""
import httpx
import os

# FHIR API base URL
FHIR_API_BASE = os.environ.get("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")


def send_get_request(url: str, timeout: float = 30.0) -> dict:
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
