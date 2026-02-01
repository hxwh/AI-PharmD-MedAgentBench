"""Tests for flow construction."""

import pytest
from flow import build_single_task_flow


def test_build_single_task_flow():
    """Test single task flow construction."""
    flow = build_single_task_flow()
    
    assert flow is not None
    assert flow.start is not None
    assert flow.start.__class__.__name__ == "LoadTaskNode"


def test_flow_has_transitions():
    """Test flow has proper transitions."""
    flow = build_single_task_flow()
    
    # Check that start node has next nodes
    start_node = flow.start
    assert hasattr(start_node, 'next_nodes')
    assert len(start_node.next_nodes) > 0
