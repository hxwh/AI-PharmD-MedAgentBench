"""Tests for MedAgentBench Green Agent."""

import pytest
from pydantic import ValidationError

from agent import Agent, EvalRequest


def test_agent_initialization():
    """Test agent initialization."""
    agent = Agent()
    assert agent.required_roles == ["agent"]
    assert agent.required_config_keys == ["task_id"]


def test_valid_request_validation(sample_eval_request):
    """Test validation of valid request."""
    agent = Agent()
    request = EvalRequest(**sample_eval_request)
    is_valid, msg = agent.validate_request(request)
    
    assert is_valid is True
    assert msg == "ok"


def test_missing_role_validation():
    """Test validation fails with missing role."""
    agent = Agent()
    request = EvalRequest(
        participants={},  # Missing "agent" role
        config={"task_id": "task_001"}
    )
    is_valid, msg = agent.validate_request(request)
    
    assert is_valid is False
    assert "Missing required roles" in msg


def test_missing_config_key_validation():
    """Test validation fails with missing config key."""
    agent = Agent()
    request = EvalRequest(
        participants={"agent": "http://localhost:9019"},
        config={}  # Missing "task_id"
    )
    is_valid, msg = agent.validate_request(request)
    
    assert is_valid is False
    assert "Missing required config keys" in msg


def test_invalid_task_id_validation():
    """Test validation fails with invalid task_id."""
    agent = Agent()
    request = EvalRequest(
        participants={"agent": "http://localhost:9019"},
        config={"task_id": ""}  # Empty task_id
    )
    is_valid, msg = agent.validate_request(request)
    
    assert is_valid is False
    assert "task_id must be a non-empty string" in msg


def test_invalid_task_ids_validation():
    """Test validation fails with invalid task_ids list."""
    agent = Agent()
    request = EvalRequest(
        participants={"agent": "http://localhost:9019"},
        config={
            "task_id": "task_001",
            "task_ids": "not_a_list"  # Should be list
        }
    )
    is_valid, msg = agent.validate_request(request)
    
    assert is_valid is False
    assert "task_ids must be a list" in msg
