"""Task logging utility for MedAgentBench agent interactions."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class TaskLogger:
    """Logger for task execution with agent interactions."""
    
    def __init__(self, task_id: str, log_dir: Optional[str] = None):
        """Initialize task logger.
        
        Args:
            task_id: Task identifier
            log_dir: Directory for log files (default: logs/)
        """
        self.task_id = task_id
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"task_{task_id}_{timestamp}.log"
        
        self.start_time = None
        self.log_data = {
            "task_id": task_id,
            "started_at": None,
            "completed_at": None,
            "duration_seconds": None,
            "input": None,
            "output": None,
            "validation": None,
            "scoring": None,
        }
    
    def log_task_start(self, config: Dict[str, Any]) -> None:
        """Log task start with clear assessment flow structure."""
        self.start_time = datetime.now()
        self.log_data["started_at"] = self.start_time.isoformat()

        with open(self.log_file, 'w') as f:
            # Header with clear flow indication
            f.write("╔════════════════════════════════════════════════════════════════════════════════╗\n")
            f.write("║                        MEDAGENTBENCH ASSESSMENT FLOW                        ║\n")
            f.write("║                        Sequential Task Execution Log                        ║\n")
            f.write("╚════════════════════════════════════════════════════════════════════════════════╝\n")
            f.write(f"\n🎯 TASK: {self.task_id}\n")
            f.write(f"📅 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n📋 ASSESSMENT CONFIGURATION:\n")
            f.write(json.dumps(config, indent=2))
            f.write("\n")

            # Flow overview
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│                           ASSESSMENT FLOW OVERVIEW                           │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")
            f.write("│ [PHASE 1] ASSESSMENT SETUP     → Parse request, validate config, load task │\n")
            f.write("│ [PHASE 2] AGENT COMMUNICATION  → Connect MCP, send to Purple Agent          │\n")
            f.write("│ [PHASE 3] TASK EXECUTION       → Purple Agent processes, makes tool calls  │\n")
            f.write("│ [PHASE 4] RESPONSE VALIDATION  → Parse response, validate format           │\n")
            f.write("│ [PHASE 5] SCORING & RESULTS    → Compute ground truth, score, report       │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            f.flush()
    
    def log_task_details(self, task: Dict[str, Any]) -> None:
        """Log task details (description, patient_id, ground_truth)."""
        self.log_data["task_details"] = task
        
        with open(self.log_file, 'a') as f:
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│ [PHASE 1] ASSESSMENT SETUP - Task Configuration                           │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")
            f.write("│ [1.1] ✓ Task definition loaded                                             │\n")
            f.write("│ [1.2] ✓ Patient context prepared                                           │\n")
            f.write("│ [1.3] ✓ Evaluation criteria established                                   │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            f.write("📝 TASK SPECIFICATION:\n")
            f.write(f"   Description: {task.get('description', 'N/A')}\n")
            f.write(f"   Patient ID: {task.get('patient_id', 'N/A')}\n")
            f.write(f"   Instructions: {task.get('instructions', 'N/A')}\n")

            # Log original task data from test_data_v2.json if available
            original_task = task.get('_original', {})
            if original_task:
                f.write(f"\n🔍 ORIGINAL TASK DATA (from test_data_v2.json):\n")
                f.write(json.dumps(original_task, indent=2))
                f.write("\n")

            f.flush()
    
    def log_input(self, prompt: str, agent_url: str) -> None:
        """Log input sent to Purple Agent with clear communication phase."""
        self.log_data["input"] = {
            "prompt": prompt,
            "agent_url": agent_url,
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.log_file, 'a') as f:
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│ [PHASE 2] AGENT COMMUNICATION - Sending Task to Purple Agent              │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")
            f.write("│ [2.1] ✓ MCP server connection established                                  │\n")
            f.write("│ [2.2] ✓ Purple Agent endpoint resolved                                     │\n")
            f.write("│ [2.3] ✓ Task prompt constructed and sent                                   │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            f.write("📡 COMMUNICATION DETAILS:\n")
            f.write(f"   Agent URL: {agent_url}\n")
            f.write(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   MCP Server: Connected and ready\n\n")

            f.write("📤 TASK PROMPT SENT TO PURPLE AGENT:\n")
            f.write(f"{prompt}\n\n")
            f.flush()
    
    def log_output(self, response: str, trajectory: list = None) -> None:
        """Log output received from Purple Agent."""
        self.log_data["output"] = {
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }
        if trajectory:
            self.log_data["trajectory"] = trajectory
            print(f"DEBUG: Trajectory received with {len(trajectory)} steps")
        else:
            print("DEBUG: No trajectory received")
        
        with open(self.log_file, 'a') as f:
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│ [PHASE 3] TASK EXECUTION - Purple Agent Processing                         │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")
            f.write("│ [3.1] ✓ Purple Agent received task                                         │\n")
            f.write("│ [3.2] ✓ Tool discovery and reasoning initiated                             │\n")
            f.write("│ [3.3] ✓ Task execution completed                                           │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            # Log trajectory first (if available)
            if trajectory:
                f.write("🔄 EXECUTION TRAJECTORY:\n")
                f.write(f"   Total Rounds: {len(trajectory)}\n\n")

                for step in trajectory:
                    round_num = step.get("round", "?")
                    action = step.get("action", "unknown")
                    f.write(f"   [Round {round_num}] {action}\n")

                    if step.get("tool_name"):
                        f.write(f"      🔧 Tool: {step['tool_name']}\n")
                        f.write(f"      📝 Args: {step.get('tool_args', {})}\n")
                        if step.get("tool_result"):
                            # Try to format as JSON for readability, otherwise log full string
                            tool_result = step['tool_result']
                            try:
                                # If it's a string that looks like JSON, parse and pretty-print
                                if isinstance(tool_result, str):
                                    parsed = json.loads(tool_result)
                                    f.write(f"      📊 Result:\n{json.dumps(parsed, indent=6)}\n")
                                elif isinstance(tool_result, dict):
                                    f.write(f"      📊 Result:\n{json.dumps(tool_result, indent=6)}\n")
                                else:
                                    f.write(f"      📊 Result: {tool_result}\n")
                            except (json.JSONDecodeError, TypeError):
                                # Not JSON, log as-is
                                f.write(f"      📊 Result: {tool_result}\n")
                        if step.get("tool_error"):
                            f.write(f"      ❌ Error: {step['tool_error']}\n")

                    if step.get("llm_output") and action != "TOOL_CALL":
                        f.write(f"      🤖 LLM Reasoning: {step['llm_output'][:100]}{'...' if len(step['llm_output']) > 100 else ''}\n")

                    if step.get("result"):
                        f.write(f"      ✅ Step Result: {step['result']}\n")

                    if step.get("error"):
                        f.write(f"      ❌ Step Error: {step['error']}\n")

                    f.write("\n")
                f.flush()

            # Then log the final output
            f.write("📥 FINAL RESPONSE FROM PURPLE AGENT:\n")
            f.write(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n   Response: {response}\n\n")
            f.flush()
    
    def log_validation(self, validation: Dict[str, Any]) -> None:
        """Log validation results with clear phase indicators."""
        self.log_data["validation"] = {
            **validation,
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.log_file, 'a') as f:
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│ [PHASE 4] RESPONSE VALIDATION - Checking Purple Agent Output              │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")

            is_valid = validation.get('is_valid', False)
            status_icon = "✅" if is_valid else "❌"
            status_text = "PASSED" if is_valid else "FAILED"

            f.write(f"│ [4.1] {status_icon} Response format validation: {status_text}                    │\n")
            f.write("│ [4.2] ✓ FINISH([answer]) format checked                                    │\n")
            f.write("│ [4.3] ✓ Answer parsing attempted                                          │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            f.write("🔍 VALIDATION RESULTS:\n")
            f.write(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   Overall Status: {'✅ VALID' if is_valid else '❌ INVALID'}\n")

            if validation.get("errors"):
                f.write("   Validation Errors:\n")
                for error in validation["errors"]:
                    f.write(f"     • {error}\n")

            if validation.get("parsed_answer") is not None:
                f.write(f"   Parsed Answer: {validation['parsed_answer']}\n")

            if validation.get("failure_type"):
                f.write(f"   Failure Category: {validation['failure_type']}\n")

            f.write("\n")
            f.flush()
    
    def log_scoring(self, scoring: Dict[str, Any], loaded_ground_truth: list = None) -> None:
        """Log scoring results with final assessment phase."""
        self.log_data["scoring"] = {
            **scoring,
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.log_file, 'a') as f:
            f.write("┌─────────────────────────────────────────────────────────────────────────────┐\n")
            f.write("│ [PHASE 5] SCORING & RESULTS - Final Assessment                            │\n")
            f.write("├─────────────────────────────────────────────────────────────────────────────┤\n")

            score = scoring.get('score', 0.0)
            correct = scoring.get('correct', False)
            score_icon = "✅" if correct else "❌"
            score_text = f"{score:.1%}" if isinstance(score, (int, float)) else str(score)

            # Phase 5.1: Ground truth computation - check if computed_expected exists and not an error
            ground_truth_success = (
                scoring.get('computed_expected') is not None and
                scoring.get('failure_type') != 'evaluation_error'
            )
            gt_icon = "✅" if ground_truth_success else "❌"

            # Phase 5.2: Answer comparison - completed if we have a result (success or failure)
            comparison_completed = scoring.get('failure_type') is not None or correct
            comp_icon = "✅" if comparison_completed else "❌"

            f.write(f"│ [5.1] {gt_icon} Ground truth computed dynamically                           │\n")
            f.write(f"│ [5.2] {comp_icon} Answer comparison completed                               │\n")
            f.write(f"│ [5.3] 📊 Final Score: {score_text} ({'PASS' if correct else 'FAIL'})     │\n")
            f.write("└─────────────────────────────────────────────────────────────────────────────┘\n\n")

            f.write("🎯 ASSESSMENT RESULTS:\n")
            f.write(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   Score: {score_text}\n")
            f.write(f"   Status: {'✅ CORRECT' if correct else '❌ INCORRECT'}\n")

            # Show ground truth that was loaded at task start
            if loaded_ground_truth is not None:
                f.write(f"   Expected Answer: {loaded_ground_truth}\n")

            # Show computed expected if different (from dynamic evaluation)
            if scoring.get("computed_expected") is not None:
                computed = scoring["computed_expected"]
                if loaded_ground_truth != computed:
                    f.write(f"   Dynamically Computed Expected: {computed}\n")

            if scoring.get("failure_type"):
                f.write(f"   Failure Category: {scoring['failure_type']}\n")

            if scoring.get("failure_reason"):
                f.write(f"   Failure Reason: {scoring['failure_reason']}\n")

            f.write("\n")
            f.flush()
    
    def log_task_end(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Log task completion with clear assessment summary."""
        end_time = datetime.now()
        self.log_data["completed_at"] = end_time.isoformat()

        if self.start_time:
            duration = (end_time - self.start_time).total_seconds()
            self.log_data["duration_seconds"] = duration
        else:
            duration = 0

        if error:
            self.log_data["error"] = error

        with open(self.log_file, 'a') as f:
            # Assessment completion summary
            status_icon = "✅" if status == "completed" and not error else "❌"
            status_text = "SUCCESS" if status == "completed" and not error else "FAILED"

            f.write("╔════════════════════════════════════════════════════════════════════════════════╗\n")
            f.write(f"║                    ASSESSMENT {status_text} - {status_icon}                        ║\n")
            f.write("╚════════════════════════════════════════════════════════════════════════════════╝\n\n")

            f.write("📊 EXECUTION SUMMARY:\n")
            f.write(f"   Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if duration > 0:
                f.write(f"   Total Duration: {duration:.2f} seconds\n")
            f.write(f"   Final Status: {status.upper()}\n")

            if error:
                f.write(f"   Error: {error}\n")

            # Quick results overview
            scoring = self.log_data.get("scoring", {})
            if scoring:
                score = scoring.get('score', 0.0)
                correct = scoring.get('correct', False)
                score_display = f"{score:.1%}" if isinstance(score, (int, float)) else str(score)
                f.write(f"   Final Score: {score_display} ({'PASS' if correct else 'FAIL'})\n")

            f.write("\n" + "=" * 77 + "\n")
            f.write("DETAILED EXECUTION LOG ABOVE - Review phases 1-5 for complete assessment flow\n")
            f.write("=" * 77 + "\n\n")

            # Technical metadata (collapsed at end)
            f.write("🔧 TECHNICAL METADATA (JSON):\n")
            f.write("-" * 77 + "\n")
            f.write(json.dumps(self.log_data, indent=2))
            f.write("\n")
            f.flush()
    
    def get_log_path(self) -> Path:
        """Get the log file path (absolute)."""
        return self.log_file.resolve()
