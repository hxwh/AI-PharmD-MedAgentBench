"""PocketFlow nodes for MedAgentBench evaluation.

Each node follows the pattern:
- prep(): Read from shared store
- exec(): Pure computation (no shared access)
- post(): Write to shared, return action string
"""

import ast
import json
import re
from typing import Any

from pocketflow import Node, AsyncNode
from a2a.types import TaskState
from a2a.utils import new_agent_text_message
from messenger import A2AMessenger
from utils.evaluation import evaluate_task


# =============================================================================
# Task Loading
# =============================================================================

class LoadTaskNode(Node):
    """Load and normalize a medical task from tasks.json."""
    
    def prep(self, shared: dict) -> str:
        """Get task ID from config."""
        task_id = shared["request"]["config"].get("task_id", "task1")
        # Map legacy task IDs to new format
        legacy_mapping = {"task_001": "task7", "task_002": "task1"}
        return legacy_mapping.get(task_id, task_id)
    
    def exec(self, task_id: str) -> dict:
        """Load task and normalize to standard format."""
        import os
        from tasks.subtask1 import get_task, compute_ground_truth
        
        task = get_task(task_id)
        mrn = task.get("eval_MRN", "S2874099")
        patient_id = f"Patient/{mrn}" if not mrn.startswith("Patient/") else mrn
        
        # Handle test_data_v2.json format: "instruction" maps to "question"/"description"
        description = task.get("question", task.get("description", task.get("instruction", "")))
        sol = task.get("sol", [])
        if not isinstance(sol, list):
            sol = [sol]
        
        # Compute ground truth dynamically if not provided in task data
        if not sol:
            fhir_api_base = os.environ.get("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")
            try:
                sol = compute_ground_truth(task_id, task, fhir_api_base)
            except (ValueError, Exception):
                # POST validation tasks or FHIR unavailable - use empty
                sol = []
        
        # Use "instruction" field if "instructions" is not present (test_data_v2.json format)
        instructions = task.get("instructions", task.get("instruction", ""))
        if not instructions:
            instructions = f"Use the FHIR tools to {description.lower()}"
        
        # Infer readonly and post_count from task prefix if not provided
        # POST tasks: task3, task5, task8, task9, task10
        task_prefix = task_id.split("_")[0] if "_" in task_id else task_id
        post_tasks = ("task3", "task5", "task8", "task9", "task10")
        
        if "readonly" in task:
            readonly = task["readonly"]
        else:
            readonly = task_prefix not in post_tasks
        
        if "post_count" in task:
            post_count = task["post_count"]
        else:
            post_count = 1 if task_prefix in post_tasks else 0
        
        return {
            "id": task["id"],
            "description": description,
            "patient_id": patient_id,
            "ground_truth": {
                "answer": sol,
                "readonly": readonly,
                "post_count": post_count
            },
            "instructions": instructions,
            "_original": task  # Preserve for dynamic evaluation
        }
    
    def post(self, shared: dict, prep_res: str, exec_res: dict) -> str:
        """Store task in shared."""
        shared["current_task"] = exec_res
        logger = shared.get("task_logger")
        if logger:
            logger.log_task_details(exec_res)
        return "default"


# =============================================================================
# Context Preparation
# =============================================================================

class PrepareContextNode(Node):
    """Prepare task prompt for the Purple Agent.
    
    Uses dynamic template with tool discovery from MCP server at runtime.
    """
    
    def prep(self, shared: dict) -> tuple:
        """Get task and config."""
        task = shared["current_task"]
        mcp_url = shared["request"]["config"].get("mcp_server_url", "http://localhost:8002")
        max_rounds = shared["request"]["config"].get("max_rounds", 10)
        dynamic_tools = shared["request"]["config"].get("dynamic_tools", False)
        return task, mcp_url, max_rounds, dynamic_tools
    
    def exec(self, inputs: tuple) -> str:
        """Format task prompt using dynamic template with tool discovery."""
        task, mcp_url, max_rounds, dynamic_tools = inputs
        
        import prompts
        
        context = f"""Patient ID: {task['patient_id']}
Instructions: {task['instructions']}
Maximum rounds: {max_rounds}"""
        
        # Always use dynamic template with tool discovery
        tools_text = self._discover_tools(mcp_url)
        template = prompts.agent_dynamic()
        return template.format(
            mcp_server_url=mcp_url,
            tools=tools_text,
            context=context,
            question=task['description']
        )
    
    def _discover_tools(self, mcp_url: str) -> str:
        """Discover tools from MCP server.
        
        Returns formatted tool text or empty string on failure.
        """
        try:
            from ..utils.mcp_discovery import discover_tools_sync
            result = discover_tools_sync(mcp_url, timeout=5.0)
            if result.get("count", 0) > 0:
                return result["formatted"]
        except Exception:
            pass
        return ""
    
    def post(self, shared: dict, prep_res: tuple, exec_res: str) -> str:
        """Store formatted prompt."""
        shared["task_prompt"] = exec_res
        return "default"


# =============================================================================
# Agent Communication
# =============================================================================

class SendToAgentNode(AsyncNode):
    """Send task to Purple Agent via A2A protocol."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messenger = A2AMessenger()
    
    async def prep_async(self, shared: dict) -> tuple:
        """Get prompt and agent config."""
        if "task_prompt" not in shared:
            raise ValueError("task_prompt not found - PrepareContextNode may have failed")
        
        prompt = shared["task_prompt"]
        agent_url = str(shared["request"]["participants"]["agent"])
        timeout = shared["request"]["config"].get("timeout", 300)
        updater = shared.get("updater")  # Get updater for forwarding status updates
        
        logger = shared.get("task_logger")
        if logger:
            logger.log_input(prompt, agent_url)
        
        return prompt, agent_url, timeout, updater
    
    async def exec_async(self, inputs: tuple) -> tuple:
        """Send message and get response."""
        prompt, agent_url, timeout, updater = inputs
        
        # Create callback to forward purple agent status updates through green agent
        async def forward_status_update(state: str, message_text: str) -> None:
            """Forward purple agent status updates to green agent's updater."""
            if updater:
                # Map state string to TaskState enum
                state_map = {
                    "submitted": TaskState.submitted,
                    "working": TaskState.working,
                    "completed": TaskState.completed,
                    "failed": TaskState.failed,
                }
                task_state = state_map.get(state, TaskState.working)
                
                # Forward the update with a prefix to indicate it's from purple agent
                await updater.update_status(
                    task_state,
                    new_agent_text_message(f"Agent: {message_text}")
                )
        
        return await self.messenger.talk_to_agent(
            message=prompt,
            url=agent_url,
            new_conversation=True,
            timeout=timeout,
            streaming=True,  # Enable streaming to receive intermediate updates
            status_callback=forward_status_update if updater else None,
        )
    
    async def post_async(self, shared: dict, prep_res: tuple, exec_res: tuple) -> str:
        """Store agent response."""
        response, trajectory = exec_res
        shared["agent_response"] = {
            "raw": response,
            "parsed": None,
            "trajectory": trajectory
        }
        
        logger = shared.get("task_logger")
        if logger:
            logger.log_output(response, trajectory=trajectory)
        
        return "default"


# =============================================================================
# Response Validation
# =============================================================================

class ValidateResponseNode(Node):
    """Validate agent response format and extract answer."""
    
    def prep(self, shared: dict) -> tuple:
        """Get response and ground truth."""
        response = shared["agent_response"]["raw"]
        ground_truth = shared["current_task"]["ground_truth"]
        return response, ground_truth
    
    def exec(self, inputs: tuple) -> dict:
        """Parse FINISH format and check for violations."""
        response, ground_truth = inputs
        
        validation = {
            "is_valid": True,
            "errors": [],
            "parsed_answer": None,
            "failure_type": None
        }
        
        # Extract FINISH(...)
        match = re.search(r"FINISH\((.*?)\)", response, re.DOTALL)
        if not match:
            validation["is_valid"] = False
            validation["errors"].append("Response does not contain FINISH(...) format")
            validation["failure_type"] = "invalid_finish_format"
            return validation
        
        # Parse answer
        answer_str = match.group(1).strip()
        parsed = self._parse_answer(answer_str)
        
        if parsed is None:
            validation["is_valid"] = False
            validation["errors"].append(f"Could not parse answer: {answer_str}")
            validation["failure_type"] = "invalid_finish_format"
            return validation
        
        validation["parsed_answer"] = parsed
        
        # Note: POST validation (readonly checks, POST count) is deferred to scoring phase
        # which has access to trajectory data with actual fhir_post operations
        
        return validation
    
    def _parse_answer(self, answer_str: str) -> list | None:
        """Parse answer string to list of strings."""
        # Try JSON first
        try:
            parsed = json.loads(answer_str)
            if not isinstance(parsed, list):
                parsed = [parsed]
            return [str(v) for v in parsed]
        except json.JSONDecodeError:
            pass
        
        # Try Python literal
        try:
            parsed = ast.literal_eval(answer_str)
            if not isinstance(parsed, list):
                parsed = [parsed]
            return [str(v) for v in parsed]
        except (ValueError, SyntaxError):
            pass
        
        return None
    
    def post(self, shared: dict, prep_res: tuple, exec_res: dict) -> str:
        """Store validation results."""
        shared["validation"] = exec_res
        shared["agent_response"]["parsed"] = exec_res.get("parsed_answer")
        
        logger = shared.get("task_logger")
        if logger:
            logger.log_validation(exec_res)
        
        return "valid" if exec_res["is_valid"] else "invalid"


# =============================================================================
# Scoring
# =============================================================================

class ScoreResultNode(Node):
    """Score agent answer against ground truth."""

    def prep(self, shared: dict) -> tuple:
        """Get answer and task data for evaluation."""
        parsed_answer = shared["agent_response"]["parsed"]
        ground_truth = shared["current_task"]["ground_truth"]["answer"]
        task_data = shared["current_task"].get("_original", {})
        response_raw = shared["agent_response"]["raw"]
        trajectory = shared["agent_response"].get("trajectory", [])
        return parsed_answer, ground_truth, task_data, response_raw, trajectory

    def exec(self, inputs: tuple) -> dict:
        """Evaluate answer using utility function."""
        parsed_answer, ground_truth, task_data, response_raw, trajectory = inputs
        return evaluate_task(parsed_answer, ground_truth, task_data, response_raw, trajectory)

    def post(self, shared: dict, prep_res: tuple, exec_res: dict) -> str:
        """Store score and update metrics."""
        shared["results"] = exec_res

        # Update metrics
        task_id = shared["current_task"]["id"]
        if "metrics" not in shared:
            shared["metrics"] = {"tasks": {}}
        shared["metrics"]["tasks"][task_id] = exec_res

        logger = shared.get("task_logger")
        if logger:
            # Get the loaded ground truth from prep results
            _, loaded_ground_truth, _, _, _ = prep_res
            logger.log_scoring(exec_res, loaded_ground_truth)

        return "success" if exec_res["correct"] else "failure"


# =============================================================================
# Failure Recording
# =============================================================================

class RecordFailureNode(Node):
    """Record and classify failure details."""
    
    def prep(self, shared: dict) -> dict:
        """Get validation and results."""
        return {
            "validation": shared.get("validation", {}),
            "results": shared.get("results", {})
        }
    
    def exec(self, inputs: dict) -> dict:
        """Classify failure type."""
        validation = inputs["validation"]
        results = inputs["results"]
        
        failure_info = {
            "failure_type": None,
            "failure_reason": None,
            "details": []
        }
        
        if validation.get("failure_type"):
            failure_info["failure_type"] = validation["failure_type"]
            failure_info["details"].extend(validation.get("errors", []))
        elif results.get("failure_type"):
            failure_info["failure_type"] = results["failure_type"]
            failure_info["failure_reason"] = results.get("failure_reason")
        else:
            failure_info["failure_type"] = "unknown"
            failure_info["failure_reason"] = "Unclassified failure"
        
        return failure_info
    
    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        """Update results with failure info."""
        if "results" not in shared or shared["results"] is None:
            shared["results"] = {}
        shared["results"].update(exec_res)
        
        # Update metrics
        task_id = shared["current_task"]["id"]
        if "metrics" not in shared:
            shared["metrics"] = {"tasks": {}}
        if task_id not in shared["metrics"]["tasks"]:
            shared["metrics"]["tasks"][task_id] = shared["results"].copy()
        
        return "default"


# =============================================================================
# Report Generation
# =============================================================================

class GenerateReportNode(Node):
    """Generate evaluation report with statistics."""
    
    def prep(self, shared: dict) -> dict:
        """Get all metrics."""
        return shared.get("metrics", {"tasks": {}})
    
    def exec(self, metrics: dict) -> dict:
        """Generate report summary."""
        tasks = metrics.get("tasks", {})
        
        if not tasks:
            return {
                "summary": "No tasks completed",
                "total_tasks": 0,
                "pass_rate": 0.0,
                "total_score": 0.0
            }
        
        total_score = sum(t.get("score", 0.0) for t in tasks.values())
        total_tasks = len(tasks)
        pass_rate = (total_score / total_tasks * 100) if total_tasks > 0 else 0.0
        
        # Count failures by type
        failure_counts = {}
        for task_result in tasks.values():
            failure_type = task_result.get("failure_type")
            if failure_type:
                failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1
        
        # Format results
        task_lines = []
        for task_id, t in tasks.items():
            status = "✓" if t.get("correct", False) else "✗"
            task_lines.append(
                f"  {task_id}: {status} (score: {t.get('score', 0.0)}, "
                f"failure: {t.get('failure_type', 'none')})"
            )
        
        summary = f"""MedAgentBench Evaluation Results
================================
Total Tasks: {total_tasks}
Pass Rate: {pass_rate:.1f}% ({int(total_score)}/{total_tasks})
Total Score: {total_score:.1f}/{total_tasks}

Failure Breakdown:
{json.dumps(failure_counts, indent=2) if failure_counts else "No failures"}

Task Results:
{chr(10).join(task_lines)}"""
        
        return {
            "summary": summary,
            "total_tasks": total_tasks,
            "pass_rate": pass_rate,
            "total_score": total_score,
            "failure_breakdown": failure_counts,
            "task_details": tasks
        }
    
    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        """Store final report."""
        shared["report"] = exec_res
        return "default"
