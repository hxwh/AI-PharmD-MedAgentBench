"""Purple Agent - LLM-based medical agent using FHIR tools via MCP.

Implements PocketFlow AsyncNode pattern:
- prep_async: Read task from shared store
- exec_async: Connect to MCP, run LLM tool-calling loop
- post_async: Write result and trajectory to shared store
"""

import json
import os
import re
from typing import Optional

from pocketflow import AsyncNode, AsyncFlow

try:
    from dotenv import load_dotenv
    import pathlib
    env_path = pathlib.Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except Exception:
    pass

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "10"))
MCP_SERVER_CWD = os.getenv("MCP_SERVER_CWD", str(pathlib.Path(__file__).parent.parent.parent))


class MCPAgentNode(AsyncNode):
    """Connect to MCP server, discover tools, run LLM tool-calling loop.
    
    This node implements the core Purple Agent logic:
    1. Connect to MCP server via stdio
    2. Discover available FHIR tools
    3. Run LLM loop: prompt → tool call → result → repeat until FINISH
    """
    
    def __init__(self, max_retries: int = 3, wait: int = 10):
        super().__init__(max_retries=max_retries, wait=wait)
        self.max_rounds = MAX_ROUNDS
    
    async def prep_async(self, shared: dict) -> dict:
        """Read task prompt and API key."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        return {
            "task_prompt": shared.get("task_prompt", ""),
            "api_key": api_key
        }
    
    async def exec_async(self, prep_res: dict) -> tuple:
        """Execute MCP connection and LLM loop.
        
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        # Pass environment variables to MCP server subprocess
        # Inherit current environment and ensure MCP_FHIR_API_BASE is set
        env = os.environ.copy()
        if "MCP_FHIR_API_BASE" not in env:
            env["MCP_FHIR_API_BASE"] = os.getenv("MCP_FHIR_API_BASE", "http://localhost:8080/fhir/")
        
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_skills.fastmcp.server", "--stdio"],
            cwd=MCP_SERVER_CWD,
            env=env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tools = tools_result.tools
                
                tool_desc = self._build_tool_descriptions(tools)
                
                return await self._run_llm_loop(
                    session, 
                    prep_res["task_prompt"], 
                    tool_desc,
                    prep_res["api_key"]
                )
    
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
                    if param_desc:
                        lines.append(f"    - {param_name} ({param_type}): {param_desc}")
                    else:
                        lines.append(f"    - {param_name} ({param_type})")
        return "\n".join(lines)
    
    async def _run_llm_loop(
        self, 
        session: ClientSession, 
        task_prompt: str, 
        tool_desc: str, 
        api_key: str
    ) -> tuple:
        """Run LLM tool-calling loop until FINISH or max rounds.
        
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        import asyncio
        
        client = genai.Client(api_key=api_key)
        
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

IMPORTANT: 
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

                # Check for JSON - handle both quoted JSON and direct JSON after quote
                if args_str[i] in ('{', '['):
                    value, end_idx = self._parse_balanced_json(args_str[i:], quote_char)
                    if value is not None:
                        # Parse the JSON string to Python object
                        try:
                            args[key] = json.loads(value)
                        except json.JSONDecodeError:
                            args[key] = value  # Keep as string if parsing fails
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

            # Handle unquoted JSON objects/arrays (fallback for LLM that doesn't quote JSON)
            elif args_str[i] in ('{', '['):
                value, end_idx = self._parse_balanced_json(args_str[i:], None)
                if value is not None:
                    # Parse the JSON string to Python object
                    try:
                        args[key] = json.loads(value)
                    except json.JSONDecodeError:
                        args[key] = value  # Keep as string if parsing fails
                    i += end_idx
                    continue

            elif args_str[i].isdigit() or (args_str[i] == '-' and i + 1 < len(args_str) and args_str[i+1].isdigit()):
                num_match = re.match(r'-?\d+\.?\d*', args_str[i:])
                if num_match:
                    num_str = num_match.group(0)
                    args[key] = float(num_str) if '.' in num_str else int(num_str)
                    i += num_match.end()
            else:
                # Handle unquoted string values
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
                        # Skip trailing quote if specified
                        if quote_char and end_idx < len(s) and s[end_idx] == quote_char:
                            end_idx += 1
                        return json_str, end_idx
            i += 1

        return None, 0
    
    async def post_async(self, shared: dict, prep_res: dict, exec_res: tuple) -> str:
        """Store result and trajectory in shared store."""
        result, trajectory = exec_res
        shared["result"] = result
        shared["trajectory"] = trajectory
        return "default"


class Agent:
    """Purple Agent wrapper for A2A integration."""
    
    def __init__(self):
        self.flow = self._build_flow()
    
    def _build_flow(self) -> AsyncFlow:
        """Build PocketFlow for agent execution."""
        agent_node = MCPAgentNode()
        return AsyncFlow(start=agent_node)
    
    async def run(self, task_prompt: str) -> tuple:
        """Run agent on a task.
        
        Args:
            task_prompt: The task to execute
            
        Returns:
            Tuple of (result_string, trajectory_list)
        """
        shared = {"task_prompt": task_prompt}
        await self.flow.run_async(shared)
        return shared.get("result", "FINISH([\"error\"])"), shared.get("trajectory", [])
