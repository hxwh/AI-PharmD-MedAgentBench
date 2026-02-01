"""MedAgentBench Green Agent implementation."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from flow import build_single_task_flow
from utils.task_logger import TaskLogger


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medagentbench")


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: dict[str, HttpUrl]  # role -> agent URL
    config: dict[str, Any]


class Agent:
    """MedAgentBench Green Agent for evaluating medical reasoning tasks."""
    
    # Required participant roles
    required_roles: list[str] = ["agent"]
    
    # Required config keys (either task_id or task_ids must be present)
    required_config_keys: list[str] = []
    
    def __init__(self):
        """Initialize the agent."""
        logger.info("MedAgentBench Green Agent initialized")
    
    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        """Validate the evaluation request.
        
        Args:
            request: The evaluation request to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check required roles
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing required roles: {missing_roles}"
        
        # Check that we have either task_id or task_ids
        task_id = request.config.get("task_id")
        task_ids = request.config.get("task_ids")

        if not task_id and not task_ids:
            return False, "Either 'task_id' (single task) or 'task_ids' (multiple tasks) must be specified"

        if task_id and task_ids:
            return False, "Cannot specify both 'task_id' and 'task_ids' - use one or the other"

        # Validate single task_id
        if task_id and not isinstance(task_id, str):
            return False, "task_id must be a string"
        
        # Optional: validate task_ids for batch processing
        task_ids = request.config.get("task_ids")
        if task_ids is not None:
            if not isinstance(task_ids, list):
                return False, "task_ids must be a list"
            if not all(isinstance(tid, str) for tid in task_ids):
                return False, "All task_ids must be strings"
        
        return True, "ok"
    
    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Run the evaluation.
        
        Args:
            message: The incoming A2A message
            updater: Task updater for reporting progress
        """
        input_text = get_message_text(message)
        
        # Parse and validate request
        try:
            request = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                logger.error(f"Request validation failed: {msg}")
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            logger.error(f"Request parsing failed: {e}")
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return
        
        # Check if we have multiple tasks or single task
        task_ids = request.config.get("task_ids")
        task_id = request.config.get("task_id")

        # Determine log directory based on task type
        log_dir = None
        if task_ids:
            # Check if any task is subtask1 (starts with "task")
            is_subtask1_batch = any(tid.startswith("task") for tid in task_ids)
            if is_subtask1_batch:
                log_dir = str(Path(__file__).parent / "logs")
        else:
            # Single task - check if it's subtask1
            is_subtask1 = task_id.startswith("task")
            if is_subtask1:
                log_dir = str(Path(__file__).parent / "logs")

        if task_ids:
            # Multiple tasks - create a batch identifier
            batch_id = f"batch_{len(task_ids)}_tasks"
            logger.info(f"Starting evaluation for {len(task_ids)} tasks: {task_ids}")
            task_logger = TaskLogger(task_id=batch_id, log_dir=log_dir)
        else:
            # Single task
            logger.info(f"Starting evaluation for task: {task_id}")
            task_logger = TaskLogger(task_id=task_id, log_dir=log_dir)
        task_logger.log_task_start({
            "participants": {k: str(v) for k, v in request.participants.items()},
            "config": request.config
        })
        
        # Update status - Phase 1: Setup
        await updater.update_status(
            TaskState.working,
            new_agent_text_message("[PHASE 1] ASSESSMENT SETUP - Parsing request and loading configuration...")
        )
        
        # Determine tasks to run
        if task_ids:
            tasks_to_run = []
            for task_id in task_ids:
                # For task types like "task1", expand to all instances
                if task_id.isdigit() or (task_id.startswith("task") and "_" not in task_id):
                    task_num = task_id.replace("task", "") if task_id.startswith("task") else task_id
                    # Run all 30 instances of this task type
                    for i in range(1, 31):
                        tasks_to_run.append(f"task{task_num}_{i}")
                else:
                    tasks_to_run.append(task_id)
        else:
            tasks_to_run = [task_id]

        logger.info(f"Will evaluate {len(tasks_to_run)} tasks: {tasks_to_run[:5]}{'...' if len(tasks_to_run) > 5 else ''}")

        # Update status - Task preparation complete
        await updater.update_status(
            TaskState.working,
            new_agent_text_message(f"[PHASE 1] ✓ Configuration loaded - Ready to evaluate {len(tasks_to_run)} tasks")
        )

        # Initialize aggregated results
        aggregated_results = {
            "total_tasks": len(tasks_to_run),
            "completed_tasks": 0,
            "failed_tasks": 0,
            "task_results": {},
            "summary": {
                "correct": 0,
                "incorrect": 0,
                "average_score": 0.0
            }
        }

        try:
            # Run evaluation for each task
            for i, current_task_id in enumerate(tasks_to_run, 1):
                logger.info(f"Evaluating task {i}/{len(tasks_to_run)}: {current_task_id}")

                # Update progress - Phase 2-5: Task execution
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(f"[PHASE 2-5] Executing task {i}/{len(tasks_to_run)}: {current_task_id} - Communicating with Purple Agent...")
                )

                # Create task-specific shared store
                task_config = request.config.copy()
                task_config["task_id"] = current_task_id

                shared = {
                    "request": {
                        "participants": {k: str(v) for k, v in request.participants.items()},
                        "config": task_config
                    },
                    "current_task": None,
                    "task_prompt": None,
                    "agent_response": None,
                    "validation": None,
                    "results": None,
                    "metrics": {"tasks": {}},
                    "report": None,
                    "task_logger": task_logger,
                    "updater": updater  # Add updater for forwarding purple agent updates
                }

                try:
                    # Build and run evaluation flow for this task
                    flow = build_single_task_flow()
                    await flow.run_async(shared)

                    # Store task result
                    task_result = shared.get("results", {})
                    aggregated_results["task_results"][current_task_id] = task_result

                    if task_result.get("correct", False):
                        aggregated_results["summary"]["correct"] += 1
                    else:
                        aggregated_results["summary"]["incorrect"] += 1

                    aggregated_results["completed_tasks"] += 1

                except Exception as task_error:
                    logger.error(f"Task {current_task_id} failed: {task_error}")
                    aggregated_results["task_results"][current_task_id] = {
                        "error": str(task_error),
                        "correct": False,
                        "score": 0.0
                    }
                    aggregated_results["failed_tasks"] += 1
                    aggregated_results["summary"]["incorrect"] += 1

            # Calculate final statistics
            total_correct = aggregated_results["summary"]["correct"]
            total_tasks = aggregated_results["total_tasks"]
            aggregated_results["summary"]["average_score"] = total_correct / total_tasks if total_tasks > 0 else 0.0

            # Create final report
            report = {
                "summary": f"Evaluated {total_tasks} tasks. Correct: {total_correct}/{total_tasks} ({total_correct/total_tasks*100:.1f}%)",
                "total_tasks": total_tasks,
                "correct_tasks": total_correct,
                "failed_tasks": aggregated_results["failed_tasks"],
                "success_rate": total_correct/total_tasks if total_tasks > 0 else 0.0
            }

            # Log completion
            task_logger.log_task_end("completed")
            log_path = str(task_logger.get_log_path())
            logger.info(f"Batch evaluation completed. Log saved to: {log_path}")
            print(f"📋 Batch evaluation log saved to: {log_path}")

            results = aggregated_results

            # For batch results, use aggregate statistics
            score = results["summary"]["average_score"]
            correct = results["summary"]["correct"] == results["total_tasks"]  # All tasks correct
            failure_type = "batch_evaluation"

            task_identifier = f"batch_{len(tasks_to_run)}_tasks" if task_ids else task_id

            summary = f"""Batch Evaluation: {results['total_tasks']} tasks
Result: {'✓ PASS' if correct else '✗ PARTIAL'}
Score: {score:.3f} ({results['summary']['correct']}/{results['total_tasks']} correct)
Success Rate: {results['summary']['correct']/results['total_tasks']*100:.1f}%

{report.get('summary', 'No detailed report available')}"""

            # Create result data for batch
            result_data = {
                "task_id": task_identifier,
                "batch_info": {
                    "total_tasks": results["total_tasks"],
                    "correct_tasks": results["summary"]["correct"],
                    "failed_tasks": results["failed_tasks"],
                    "task_results": results["task_results"]
                },
                "score": score,
                "correct": correct,
                "failure_type": failure_type,
                "report": report,
                "log_path": log_path
            }
            logger.debug(f"Result data includes log_path: {log_path in result_data}")
            
            logger.info(f"Evaluation completed: score={score}, correct={correct}")
            
            # Save results to experiments directory
            results_dir = Path(__file__).parent.parent / "experiments"

            # Determine subfolder based on task type
            if task_id and task_id.startswith("task"):
                # Subtask1 tasks (task1_1, task2_5, etc.)
                results_dir = results_dir / "subtask1"
            elif task_id and task_id.startswith("subtask2"):
                # Subtask2 tasks
                results_dir = results_dir / "subtask2"
            # For other tasks, use experiments/ root

            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Save complete result data as JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_identifier = task_identifier if 'task_identifier' in locals() else (task_ids[0] if task_ids else task_id)
            result_file = results_dir / f"batch_{len(tasks_to_run)}_tasks_{timestamp}.json"

            complete_result = {
                "batch_id": task_identifier,
                "timestamp": datetime.now().isoformat(),
                "total_tasks": len(tasks_to_run),
                "tasks_evaluated": tasks_to_run,
                "score": score,
                "correct": correct,
                "failure_type": failure_type,
                "batch_results": results,
                "report": report,
                "summary": summary,
                "log_path": log_path
            }
            
            with open(result_file, 'w') as f:
                json.dump(complete_result, f, indent=2)
            
            logger.info(f"Result saved to: {result_file}")
            
            # Add artifact with results
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=summary)),
                    Part(root=DataPart(data=result_data)),
                ],
                name="Evaluation Result",
            )
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            
            # Log task failure (use task_logger variable, not shared, in case shared wasn't created)
            try:
                if "task_logger" in shared:
                    shared["task_logger"].log_task_end("failed", error=error_msg)
                else:
                    task_logger.log_task_end("failed", error=error_msg)
            except Exception as log_error:
                logger.error(f"Failed to log task end: {log_error}")
            
            await updater.failed(
                new_agent_text_message(f"[ERROR] Assessment execution failed: {str(e)} - Check logs for detailed error information")
            )
            return


if __name__ == "__main__":
    # Test agent initialization
    agent = Agent()
    print(f"Agent initialized with required roles: {agent.required_roles}")
    print(f"Required config keys: {agent.required_config_keys}")
    
    # Test request validation
    test_request = EvalRequest(
        participants={"agent": "http://localhost:9019"},
        config={
            "task_id": "task_001",
            "mcp_server_url": "http://localhost:8002",
            "max_rounds": 10
        }
    )
    
    is_valid, msg = agent.validate_request(test_request)
    print(f"Validation result: {is_valid}, {msg}")
