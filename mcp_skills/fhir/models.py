"""Pydantic models for FHIR resources."""
from typing import List, Optional

from pydantic import BaseModel, Field


class SubjectReference(BaseModel):
    """Subject reference object pointing to a patient."""
    reference: str = Field(description="The patient FHIR ID (e.g., 'Patient/12345')")


class VitalsCategoryCoding(BaseModel):
    """Coding element for vital signs category."""
    system: str = Field(
        default="http://hl7.org/fhir/observation-category",
        description="Use 'http://hl7.org/fhir/observation-category'"
    )
    code: str = Field(
        default="vital-signs",
        description="Use 'vital-signs'"
    )
    display: str = Field(
        default="Vital Signs",
        description="Use 'Vital Signs'"
    )


class VitalsCategoryElement(BaseModel):
    """Category element for vital signs observation."""
    coding: List[VitalsCategoryCoding] = Field(
        description="Array of coding objects for the category"
    )


class VitalsCodeObject(BaseModel):
    """Code object for vital signs - specifies what is being measured."""
    text: str = Field(
        description="What is being measured (e.g., 'BP', 'Temp', 'HR', 'SpO2')"
    )


class MedicationCoding(BaseModel):
    """Coding for medication."""
    system: str = Field(
        default="http://hl7.org/fhir/sid/ndc",
        description="Coding system such as 'http://hl7.org/fhir/sid/ndc'"
    )
    code: str = Field(description="The actual medication code")
    display: str = Field(description="Display name of the medication")


class MedicationCodeableConcept(BaseModel):
    """Medication codeable concept with coding and text."""
    coding: List[MedicationCoding] = Field(description="Array of medication coding objects")
    text: str = Field(description="The order display name of the medication")


class DoseQuantity(BaseModel):
    """Dose quantity with value and unit."""
    value: float = Field(description="Numeric dose value")
    unit: str = Field(description="Unit for the dose such as 'g', 'mg', 'mL'")


class RateQuantity(BaseModel):
    """Rate quantity with value and unit (for IV medications)."""
    value: float = Field(description="Numeric rate value")
    unit: str = Field(description="Unit for the rate such as 'h' (per hour)")


class DoseAndRate(BaseModel):
    """Dose and rate specification."""
    doseQuantity: Optional[DoseQuantity] = None
    rateQuantity: Optional[RateQuantity] = None


class DosageInstruction(BaseModel):
    """Dosage instruction with route and dose/rate."""
    route: str = Field(description="The medication route (e.g., 'IV', 'oral')")
    doseAndRate: List[DoseAndRate] = Field(description="Array of dose and rate specs")


class ServiceRequestCoding(BaseModel):
    """Coding for service request."""
    system: str = Field(description="Coding system (LOINC, SNOMED, CPT)")
    code: str = Field(description="The actual code")
    display: str = Field(description="Display name")


class ServiceRequestCode(BaseModel):
    """Code object for service request."""
    coding: List[ServiceRequestCoding] = Field(
        description="Array of coding objects"
    )


class NoteObject(BaseModel):
    """Note object with text field for comments."""
    text: str = Field(description="Free text comment")
