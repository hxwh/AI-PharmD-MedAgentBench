"""Purple Agent - LLM-based medical agent using FHIR tools via MCP.

Implements the Agent interface for A2A integration.
Uses MCP (Model Context Protocol) to discover and call FHIR tools.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

# Load environment variables
try:
    from dotenv import load_dotenv, find_dotenv
    # Try to find .env file by searching upward from current directory
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)
except ImportError:
    pass

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from messenger import Messenger


# Configuration
MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "10"))
MCP_SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "python")
MCP_SERVER_ARGS = os.getenv("MCP_SERVER_ARGS", "-m mcp_skills.fastmcp.server --stdio")
MCP_SERVER_CWD = os.getenv("MCP_SERVER_CWD", str(Path(__file__).parent.parent.parent))


class Agent:
    """Purple Agent - Pharmacist AI agent using FHIR tools via MCP."""
    
    def __init__(self):
        self.messenger = Messenger()
        self.max_rounds = MAX_ROUNDS

        # Store API key for later use
        self.api_key = os.getenv("GOOGLE_API_KEY")
    
    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Run the agent on an incoming message.

        Args:
            message: The incoming A2A message
            updater: Task updater for reporting progress
        """
        input_text = get_message_text(message)
        
        await updater.update_status(
            TaskState.working, 
            new_agent_text_message("Connecting to MCP server...")
        )
        
        try:
            result, trajectory = await self._run_with_mcp(input_text)

            # Include both text result and trajectory data
            parts = [Part(root=TextPart(kind="text", text=result))]
            if trajectory:
                parts.append(Part(root=DataPart(kind="data", data={"trajectory": trajectory})))

            await updater.add_artifact(
                parts=parts,
                name="Response",
            )
        except BaseException as e:
            # Extract actual exception from ExceptionGroup/BaseExceptionGroup
            error_msg = self._extract_exception_message(e)
            await updater.add_artifact(
                parts=[Part(root=TextPart(text=f"Error: {error_msg}"))],
                name="Error",
            )
    
    def _extract_exception_message(self, exc: BaseException) -> str:
        """Extract detailed error message from exception, including ExceptionGroup sub-exceptions."""
        # Handle ExceptionGroup/BaseExceptionGroup (Python 3.11+ or exceptiongroup backport)
        if hasattr(exc, 'exceptions'):
            # It's an ExceptionGroup - extract sub-exceptions
            messages = []
            for sub_exc in exc.exceptions:
                sub_msg = self._extract_exception_message(sub_exc)
                messages.append(sub_msg)
            return f"{type(exc).__name__}: {'; '.join(messages)}"
        
        # Regular exception - include type and message
        exc_type = type(exc).__name__
        exc_msg = str(exc)
        if exc_msg:
            return f"{exc_type}: {exc_msg}"
        return exc_type

    async def run_task(self, task_prompt: str) -> tuple:
        """Run agent on a task prompt directly (for testing).
        
        Args:
            task_prompt: The task to execute
            
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        return await self._run_with_mcp(task_prompt)
    
    async def _run_with_mcp(self, task_prompt: str) -> tuple:
        """Execute MCP connection and LLM loop.
        
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        # Prepare environment for MCP server
        env = os.environ.copy()
        if "MCP_FHIR_API_BASE" not in env:
            env["MCP_FHIR_API_BASE"] = os.getenv("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")
        
        # Parse MCP server command
        args = MCP_SERVER_ARGS.split()
        
        server_params = StdioServerParameters(
            command=MCP_SERVER_COMMAND,
            args=args,
            cwd=MCP_SERVER_CWD,
            env=env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tools = tools_result.tools
                
                tool_desc = self._build_tool_descriptions(tools)
                
                return await self._run_llm_loop(session, task_prompt, tool_desc)
    
    def _build_tool_descriptions(self, tools) -> str:
        """Build tool descriptions for LLM prompt."""
        lines = ["Available FHIR Tools:"]
        for tool in tools:
            lines.append(f"\n- {tool.name}: {tool.description or 'No description'}")
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                for param_name, param_info in props.items():
                    param_type = param_info.get('type', 'any')
                    param_desc = param_info.get('description', '')

                    # Handle complex object types with better descriptions
                    if param_type == 'object' and '$ref' in param_info:
                        ref = param_info['$ref']
                        if ref.endswith('NoteObject'):
                            lines.append(f"    - {param_name} (object): {param_desc} - Format: {{\"text\": \"your comment here\"}}")
                        elif ref.endswith('SubjectReference'):
                            lines.append(f"    - {param_name} (object): {param_desc} - Format: {{\"reference\": \"Patient/ID\"}}")
                        elif ref.endswith('ServiceRequestCode'):
                            lines.append(f"    - {param_name} (object): {param_desc} - Format: {{\"coding\": [{{\"system\": \"url\", \"code\": \"value\", \"display\": \"name\"}}]}}")
                        else:
                            lines.append(f"    - {param_name} ({param_type}): {param_desc}")
                    elif param_type == 'array' and 'items' in param_info and '$ref' in param_info['items']:
                        ref = param_info['items']['$ref']
                        if ref.endswith('DosageInstruction'):
                            lines.append(f"    - {param_name} (array): {param_desc} - Array of dosage instruction objects")
                        elif ref.endswith('VitalsCategoryElement'):
                            lines.append(f"    - {param_name} (array): {param_desc} - Array of category objects")
                        else:
                            lines.append(f"    - {param_name} (array): {param_desc}")
                    else:
                        if param_desc:
                            lines.append(f"    - {param_name} ({param_type}): {param_desc}")
                        else:
                            lines.append(f"    - {param_name} ({param_type})")
        return "\n".join(lines)
    
    async def _run_llm_loop(
        self, 
        session: ClientSession, 
        task_prompt: str, 
        tool_desc: str
    ) -> tuple:
        """Run LLM tool-calling loop until FINISH or max rounds.
        
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        import asyncio
        
        # Create client for API calls
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        client = genai.Client(api_key=self.api_key)
        
        context = []
        trajectory = []
        
        try:
            return await self._run_llm_loop_inner(client, session, task_prompt, tool_desc, context, trajectory)
        finally:
            # Always close client to prevent resource leaks
            client.close()
    
    async def _run_llm_loop_inner(
        self,
        client,
        session: ClientSession,
        task_prompt: str,
        tool_desc: str,
        context: list,
        trajectory: list
    ) -> tuple:
        """Inner LLM loop - separated to ensure client.close() in finally block."""
        import asyncio
        
        system_prompt = f"""You are a medical AI agent with access to FHIR tools via MCP.

{tool_desc}

To call a tool, respond with:
TOOL_CALL: tool_name(param1="value1", param2="value2")

When you have the final answer, respond with:
FINISH([answer1, answer2, ...])

Rules:
- Call tools to gather information before answering
- Use exact parameter names from tool descriptions
- FINISH must contain a JSON-parseable list
- For numeric answers: FINISH([118]) - just the number
- For text answers: FINISH(["Metformin", "Insulin"])
- For actions completed: FINISH(["recorded"]) or FINISH(["ordered"])

IMPORTANT FORMATTING RULES:
- Object parameters: Use curly braces WITHOUT outer quotes, e.g., note={{"text": "comment"}}
- Array parameters: Use square brackets WITHOUT outer quotes, e.g., category=[{{"coding": [...]}}]
- String parameters: Use double quotes, e.g., patient="Patient/123"
- For note parameter in create_service_request: Always use {{"text": "comment"}} format (single object, not array)
- Complex objects like code={{"coding": [{{"system": "url", "code": "value", "display": "name"}}]}}

TOOL SPECIFIC GUIDANCE:
- create_service_request note parameter: Must be a single object {{"text": "comment"}}, NOT an array
- For lab values, use get_latest_lab_value(patient="Patient/ID", code="CODE")
- For condition/problem lists, use get_patient_conditions(patient="Patient/ID")
- Do NOT pass large JSON between tools - use combined tools instead
- If task context says "It's YYYY-MM-DDTHH:MM:SS now", use THAT date as reference_date
- If task asks for a value "within last 24 hours" and no measurement available, return FINISH([-1])
"""
        
        for round_num in range(self.max_rounds):
            step = {"round": round_num + 1}
            
            # Build prompt
            if round_num == 0:
                prompt = f"{system_prompt}\n\nTask: {task_prompt}"
            else:
                prompt = f"{system_prompt}\n\nTask: {task_prompt}\n\nPrevious actions:\n" + "\n".join(context)
            
            # Call LLM with retry for rate limiting
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-lite",
                        contents=prompt
                    )
                    llm_output = response.text.strip()
                    step["llm_output"] = llm_output
                    break
                except Exception as e:
                    error_str = str(e)
                    # Check for rate limiting (429) or quota errors
                    if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                            await asyncio.sleep(wait_time)
                            continue
                    step["error"] = f"LLM call failed: {e}"
                    trajectory.append(step)
                    return (f"FINISH([\"error: LLM call failed - {e}\"])", trajectory)
            
            # Check for FINISH
            finish_match = re.search(r'FINISH\s*\(\s*(\[.*?\])\s*\)', llm_output, re.DOTALL)
            if finish_match:
                step["action"] = "FINISH"
                step["result"] = finish_match.group(1)
                trajectory.append(step)
                return (f"FINISH({finish_match.group(1)})", trajectory)
            
            # Check for tool call
            tool_name, args_str = self._extract_tool_call(llm_output)
            if tool_name:
                args = self._parse_tool_args(args_str)
                step["action"] = "TOOL_CALL"
                step["tool_name"] = tool_name
                step["tool_args"] = args
                
                try:
                    result = await session.call_tool(tool_name, args)
                    tool_output = result.content[0].text if result.content else "No result"
                    if len(tool_output) > 8000:
                        tool_output = tool_output[:8000] + "... (truncated)"
                    context.append(f"Called {tool_name}({args}) -> {tool_output}")
                    step["tool_result"] = tool_output
                except Exception as e:
                    context.append(f"Called {tool_name}({args}) -> Error: {e}")
                    step["tool_error"] = str(e)
            else:
                step["action"] = "REASONING"
                context.append(f"LLM said: {llm_output[:200]}")
            
            trajectory.append(step)
            
            # Small delay between rounds to avoid rate limiting
            await asyncio.sleep(0.5)
        
        trajectory.append({"round": self.max_rounds + 1, "action": "MAX_ROUNDS_REACHED"})
        return ("FINISH([\"max_rounds_reached\"])", trajectory)
    
    def _extract_tool_call(self, text: str) -> tuple:
        """Extract tool call with balanced parenthesis matching."""
        match = re.search(r'TOOL_CALL:\s*(\w+)\s*\(', text)
        if not match:
            return None, None
        
        tool_name = match.group(1)
        start_idx = match.end() - 1
        
        depth = 0
        in_string = False
        string_char = None
        i = start_idx
        
        while i < len(text):
            c = text[i]
            
            if c in ('"', "'") and (i == 0 or text[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = c
                elif c == string_char:
                    in_string = False
                    string_char = None
            elif not in_string:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        args_str = text[start_idx + 1:i]
                        return tool_name, args_str
            i += 1
        
        # Fallback to simple extraction
        simple_match = re.search(r'TOOL_CALL:\s*(\w+)\s*\(([^)]*)\)', text)
        if simple_match:
            return simple_match.group(1), simple_match.group(2)
        
        return None, None
    
    def _python_to_json(self, value: str) -> str:
        """Convert Python dict/list syntax to JSON format.
        
        Handles:
        - Single quotes → double quotes
        - Python True/False/None → JSON true/false/null
        """
        result = []
        i = 0
        in_string = False
        string_char = None
        
        while i < len(value):
            c = value[i]
            
            # Handle string boundaries
            if c in ('"', "'") and (i == 0 or value[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = c
                    # Always output double quote for JSON
                    result.append('"')
                    i += 1
                    continue
                elif c == string_char:
                    in_string = False
                    string_char = None
                    result.append('"')
                    i += 1
                    continue
            
            # Inside string - escape double quotes if using single quote syntax
            if in_string:
                if c == '"' and string_char == "'":
                    result.append('\\"')
                else:
                    result.append(c)
                i += 1
                continue
            
            # Outside string - handle Python keywords
            if c.isalpha():
                # Check for Python True/False/None
                if value[i:i+4] == 'True' and (i+4 >= len(value) or not value[i+4].isalnum()):
                    result.append('true')
                    i += 4
                    continue
                elif value[i:i+5] == 'False' and (i+5 >= len(value) or not value[i+5].isalnum()):
                    result.append('false')
                    i += 5
                    continue
                elif value[i:i+4] == 'None' and (i+4 >= len(value) or not value[i+4].isalnum()):
                    result.append('null')
                    i += 4
                    continue
            
            result.append(c)
            i += 1
        
        return ''.join(result)

    def _parse_json_value(self, value: str) -> any:
        """Try to parse a value as JSON, with Python syntax fallback."""
        # First try standard JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Try converting Python syntax to JSON
        try:
            json_value = self._python_to_json(value)
            return json.loads(json_value)
        except json.JSONDecodeError:
            pass
        
        # Return as string if all parsing fails
        return value

    def _parse_tool_args(self, args_str: str) -> dict:
        """Parse tool arguments from string."""
        if not args_str:
            return {}

        args = {}
        i = 0

        while i < len(args_str):
            # Skip whitespace and commas
            while i < len(args_str) and args_str[i] in ' \t\n,':
                i += 1
            if i >= len(args_str):
                break

            # Look for key=
            key_match = re.match(r'(\w+)\s*=\s*', args_str[i:])
            if not key_match:
                i += 1
                continue

            key = key_match.group(1)
            i += key_match.end()

            if i >= len(args_str):
                break

            # Parse value
            if args_str[i] in ('"', "'"):
                quote_char = args_str[i]
                i += 1

                if i >= len(args_str):
                    break

                # Check for JSON/dict object
                if args_str[i] in ('{', '['):
                    value, end_idx = self._parse_balanced_json(args_str[i:], quote_char)
                    if value is not None:
                        args[key] = self._parse_json_value(value)
                        i += end_idx
                        continue

                # Simple string value
                value_start = i
                while i < len(args_str):
                    if args_str[i] == quote_char and (i == value_start or args_str[i-1] != '\\'):
                        args[key] = args_str[value_start:i]
                        i += 1
                        break
                    i += 1

            elif args_str[i] in ('{', '['):
                value, end_idx = self._parse_balanced_json(args_str[i:], None)
                if value is not None:
                    args[key] = self._parse_json_value(value)
                    i += end_idx
                    continue

            elif args_str[i].isdigit() or (args_str[i] == '-' and i + 1 < len(args_str) and args_str[i+1].isdigit()):
                num_match = re.match(r'-?\d+\.?\d*', args_str[i:])
                if num_match:
                    num_str = num_match.group(0)
                    args[key] = float(num_str) if '.' in num_str else int(num_str)
                    i += num_match.end()
            else:
                # Unquoted string values
                value_start = i
                while i < len(args_str) and args_str[i] not in ',)':
                    i += 1
                args[key] = args_str[value_start:i].strip()

        return args
    
    def _parse_balanced_json(self, s: str, quote_char: str) -> tuple:
        """Parse JSON with balanced braces."""
        if not s or s[0] not in ('{', '['):
            return None, 0

        open_char = s[0]
        close_char = '}' if open_char == '{' else ']'

        depth = 0
        in_string = False
        inner_quote = None
        i = 0

        while i < len(s):
            c = s[i]

            if c in ('"', "'") and (i == 0 or s[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    inner_quote = c
                elif c == inner_quote:
                    in_string = False
                    inner_quote = None
            elif not in_string:
                if c == open_char:
                    depth += 1
                elif c == close_char:
                    depth -= 1
                    if depth == 0:
                        json_str = s[:i + 1]
                        end_idx = i + 1
                        if quote_char and end_idx < len(s) and s[end_idx] == quote_char:
                            end_idx += 1
                        return json_str, end_idx
            i += 1

        return None, 0
