"""FHIR module for PharmAgent MCP Server.

Provides FHIR tools, resources, models, and evaluation tools for clinical workflows.
"""
from .models import (
    SubjectReference,
    VitalsCategoryElement,
    VitalsCodeObject,
    MedicationCodeableConcept,
    DosageInstruction,
    ServiceRequestCode,
    NoteObject,
)
from .client import call_fhir, build_fhir_url

__all__ = [
    "SubjectReference",
    "VitalsCategoryElement",
    "VitalsCodeObject",
    "MedicationCodeableConcept",
    "DosageInstruction",
    "ServiceRequestCode",
    "NoteObject",
    "call_fhir",
    "build_fhir_url",
]
