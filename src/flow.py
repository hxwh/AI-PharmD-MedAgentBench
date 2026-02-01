"""Flow construction for MedAgentBench evaluation."""

from pocketflow import Flow, AsyncFlow
from nodes import (
    LoadTaskNode,
    PrepareContextNode,
    SendToAgentNode,
    ValidateResponseNode,
    ScoreResultNode,
    RecordFailureNode,
    GenerateReportNode,
)


def build_single_task_flow() -> AsyncFlow:
    """Build flow for evaluating a single task.
    
    Flow:
    1. LoadTask -> PrepareContext -> SendToAgent
    2. ValidateResponse -> (valid) -> ScoreResult
    3. ValidateResponse -> (invalid) -> RecordFailure
    4. ScoreResult -> (success) -> GenerateReport
    5. ScoreResult -> (failure) -> RecordFailure -> GenerateReport
    """
    # Create nodes
    load_task = LoadTaskNode(max_retries=2, wait=1)
    prepare_context = PrepareContextNode()
    send_to_agent = SendToAgentNode(max_retries=1, wait=5)
    validate_response = ValidateResponseNode()
    score_result = ScoreResultNode()
    record_failure = RecordFailureNode()
    generate_report = GenerateReportNode()
    
    # Build flow
    # Main path: load -> prepare -> send -> validate
    load_task >> prepare_context >> send_to_agent >> validate_response
    
    # Validation branches
    validate_response - "valid" >> score_result
    validate_response - "invalid" >> record_failure
    
    # Scoring branches
    score_result - "success" >> generate_report
    score_result - "failure" >> record_failure
    
    # Failure path to report
    record_failure >> generate_report
    
    return AsyncFlow(start=load_task)


def build_multi_task_flow() -> AsyncFlow:
    """Build flow for evaluating multiple tasks.
    
    NOTE: This is a placeholder implementation. Currently returns
    the single task flow. Future implementation would process
    multiple tasks in batch or sequence.
    """
    return build_single_task_flow()


if __name__ == "__main__":
    import asyncio
    
    # Test flow construction
    flow = build_single_task_flow()
    
    # Sample shared store
    shared = {
        "request": {
            "participants": {
                "agent": "http://localhost:9019"
            },
            "config": {
                "task_id": "task_001",
                "mcp_server_url": "http://localhost:8002",
                "max_rounds": 10,
                "timeout": 300
            }
        },
        "metrics": {"tasks": {}}
    }
    
    print("Flow constructed successfully")
    print(f"Starting node: {flow.start.__class__.__name__}")
