"""Tests for PocketFlow nodes."""

import pytest
from nodes import (
    LoadTaskNode,
    PrepareContextNode,
    ValidateResponseNode,
    ScoreResultNode,
)


def test_load_task_node(sample_task):
    """Test LoadTaskNode."""
    node = LoadTaskNode()
    shared = {
        "request": {
            "config": {"task_id": "task_001"}
        }
    }
    
    action = node.run(shared)
    
    assert action == "default"
    assert "current_task" in shared
    assert shared["current_task"]["id"] == "task_001"


def test_prepare_context_node(sample_task):
    """Test PrepareContextNode."""
    node = PrepareContextNode()
    shared = {
        "request": {
            "config": {
                "mcp_server_url": "http://localhost:8002",
                "max_rounds": 10
            }
        },
        "current_task": sample_task
    }
    
    action = node.run(shared)
    
    assert action == "default"
    assert "task_prompt" in shared
    assert "MCP Server URL" in shared["task_prompt"]
    assert sample_task["description"] in shared["task_prompt"]


def test_validate_response_valid(sample_agent_response):
    """Test ValidateResponseNode with valid response."""
    node = ValidateResponseNode()
    shared = {
        "agent_response": {
            "raw": sample_agent_response,
            "parsed": None
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"],
                "readonly": True,
                "post_count": 0
            }
        }
    }
    
    action = node.run(shared)
    
    assert action == "valid"
    assert shared["validation"]["is_valid"] is True
    assert shared["validation"]["parsed_answer"] == ["191"]


def test_validate_response_invalid_format():
    """Test ValidateResponseNode with invalid format."""
    node = ValidateResponseNode()
    shared = {
        "agent_response": {
            "raw": "The answer is 191 but no FINISH format",
            "parsed": None
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"],
                "readonly": True,
                "post_count": 0
            }
        }
    }
    
    action = node.run(shared)
    
    assert action == "invalid"
    assert shared["validation"]["is_valid"] is False
    assert shared["validation"]["failure_type"] == "invalid_finish_format"


def test_validate_response_readonly_violation():
    """Test ValidateResponseNode detects readonly violation."""
    node = ValidateResponseNode()
    shared = {
        "agent_response": {
            "raw": "I will POST this data. FINISH([191])",
            "parsed": None
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"],
                "readonly": True,
                "post_count": 0
            }
        }
    }
    
    action = node.run(shared)
    
    assert action == "invalid"
    assert shared["validation"]["is_valid"] is False
    assert shared["validation"]["failure_type"] == "readonly_violation"


def test_score_result_correct():
    """Test ScoreResultNode with correct answer."""
    node = ScoreResultNode()
    shared = {
        "agent_response": {
            "parsed": ["191"]
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"]
            }
        }
    }
    
    action = node.run(shared)
    
    assert action == "success"
    assert shared["results"]["score"] == 1.0
    assert shared["results"]["correct"] is True


def test_score_result_incorrect():
    """Test ScoreResultNode with incorrect answer."""
    node = ScoreResultNode()
    shared = {
        "agent_response": {
            "parsed": ["180"]
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"]
            }
        }
    }
    
    action = node.run(shared)
    
    assert action == "failure"
    assert shared["results"]["score"] == 0.0
    assert shared["results"]["correct"] is False
    assert shared["results"]["failure_type"] == "answer_mismatch"


def test_score_result_normalized_comparison():
    """Test ScoreResultNode normalizes answers for comparison."""
    node = ScoreResultNode()
    shared = {
        "agent_response": {
            "parsed": ["191 mg/dL"]
        },
        "current_task": {
            "ground_truth": {
                "answer": ["191"]
            }
        }
    }
    
    action = node.run(shared)
    
    # Should match after normalization
    assert action == "success"
    assert shared["results"]["score"] == 1.0
    assert shared["results"]["correct"] is True
