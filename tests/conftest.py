"""Pytest configuration for MedAgentBench tests."""

import pytest


@pytest.fixture
def sample_eval_request():
    """Sample evaluation request for testing."""
    return {
        "participants": {
            "agent": "http://localhost:9019"
        },
        "config": {
            "task_id": "task_001",
            "mcp_server_url": "http://localhost:8002",
            "max_rounds": 10,
            "timeout": 300
        }
    }


@pytest.fixture
def sample_task():
    """Sample medical task for testing."""
    return {
        "id": "task_001",
        "description": "What is the patient's latest blood glucose level?",
        "patient_id": "Patient/example",
        "ground_truth": {
            "answer": ["191"],
            "readonly": True,
            "post_count": 0
        },
        "instructions": "Use the FHIR tools to find the patient's latest blood glucose observation."
    }


@pytest.fixture
def sample_agent_response():
    """Sample agent response for testing."""
    return "Based on the FHIR query, the patient's latest blood glucose level is FINISH([191])"
