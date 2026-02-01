#!/usr/bin/env python3
"""
MedAgentBench Scenario Runner - AgentBeats Compatible
"""
import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import httpx

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass


def parse_scenario(scenario_path: str) -> dict:
    path = Path(scenario_path)
    if not path.exists():
        print(f"Error: Scenario file not found: {path}")
        sys.exit(1)
    with open(path, "rb") as f:
        return tomllib.load(f)


def check_endpoint(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    import socket
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.error, OSError):
        return False


def wait_for_agent(endpoint: str, timeout: int = 60) -> bool:
    agent_card_url = f"{endpoint.rstrip('/')}/.well-known/agent-card.json"
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(agent_card_url, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_agent(cmd: str, show_logs: bool = False) -> subprocess.Popen:
    full_env = os.environ.copy()
    kwargs = {
        "shell": True,
        "env": full_env,
        "stdout": None if show_logs else subprocess.DEVNULL,
        "stderr": None if show_logs else subprocess.DEVNULL,
        "start_new_session": True,
    }
    return subprocess.Popen(cmd, **kwargs)


async def send_assessment_request(green_endpoint, participants, config, timeout=300):
    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.types import Message, Part, Role, TextPart

    request_data = {"participants": participants, "config": config}
    print(f"\n📤 Sending assessment request:\n   {json.dumps(request_data, indent=2)}\n")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        resolver = A2ACardResolver(httpx_client=client, base_url=green_endpoint)
        agent_card = await resolver.get_agent_card()
        factory = ClientFactory(ClientConfig(httpx_client=client, streaming=True))
        a2a_client = factory.create(agent_card)
        
        message = Message(
            kind="message",
            role=Role.user,
            parts=[Part(TextPart(kind="text", text=json.dumps(request_data)))],
            message_id="assessment-request",
        )
        
        result = {}
        async for event in a2a_client.send_message(message):
            match event:
                case Message() as msg:
                    for part in msg.parts:
                        if hasattr(part.root, "text"):
                            print(part.root.text)
                case (task, update):
                    state = task.status.state.value
                    if task.status.message:
                        for part in task.status.message.parts:
                            if hasattr(part.root, "text"):
                                print(f"[Status: {state}] {part.root.text}")
                    if state == "completed" and task.artifacts:
                        for artifact in task.artifacts:
                            for part in artifact.parts:
                                if hasattr(part.root, "data"):
                                    result = part.root.data
                                elif hasattr(part.root, "text"):
                                    print(part.root.text)
        return result


def main():
    parser = argparse.ArgumentParser(description="MedAgentBench Scenario Runner")
    parser.add_argument("scenario", help="Path to scenario TOML file")
    parser.add_argument("--show-logs", action="store_true")
    parser.add_argument("--serve-only", action="store_true")
    parser.add_argument("--skip-start", action="store_true")
    args = parser.parse_args()
    
    scenario = parse_scenario(args.scenario)
    green_agent = scenario["green_agent"]
    participants = {p["role"]: p["endpoint"] for p in scenario["participants"]}
    config = scenario.get("config", {})
    timeout = config.get("timeout", 300)
    
    print("=" * 60)
    print("MedAgentBench Scenario Runner (AgentBeats Compatible)")
    print("=" * 60)
    print(f"Green Agent: {green_agent['endpoint']}")
    print(f"Participants: {participants}")
    print(f"Config: {config}\n")
    
    started_agents = []
    
    def cleanup():
        if started_agents:
            print("\n🧹 Stopping agents...")
            for name, proc in started_agents:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                        print(f"  Stopped {name}")
                    except:
                        pass
    
    try:
        if not args.skip_start:
            if check_endpoint(green_agent["endpoint"]):
                print(f"✓ Green agent already running")
            elif green_agent.get("cmd"):
                print(f"Starting green agent: {green_agent['cmd']}")
                proc = start_agent(green_agent["cmd"], args.show_logs)
                started_agents.append(("green_agent", proc))
            
            for p in scenario["participants"]:
                if check_endpoint(p["endpoint"]):
                    print(f"✓ {p['role']} already running")
                elif p.get("cmd"):
                    print(f"Starting {p['role']}: {p['cmd']}")
                    proc = start_agent(p["cmd"], args.show_logs)
                    started_agents.append((p["role"], proc))
        
        print("\n⏳ Waiting for agents...")
        if not wait_for_agent(green_agent["endpoint"], timeout=30):
            print(f"❌ Green agent failed to start")
            sys.exit(1)
        print("  ✅ Green agent ready")
        
        for p in scenario["participants"]:
            if not wait_for_agent(p["endpoint"], timeout=30):
                print(f"❌ {p['role']} failed to start")
                sys.exit(1)
            print(f"  ✅ {p['role']} ready")
        
        print("\n🎉 All agents ready!")
        
        if args.serve_only:
            print("\n📡 Serve-only mode. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        
        print("\n" + "=" * 60)
        print("Running Assessment")
        print("=" * 60)
        
        result = asyncio.run(send_assessment_request(
            green_agent["endpoint"], participants, config, timeout
        ))
        
        print("\n" + "=" * 60)
        print("Assessment Complete")
        print("=" * 60)
        
        if result:
            print("\n📊 Results:")
            print(json.dumps(result, indent=2))
            
            results_dir = Path(__file__).parent.parent / "experiments"
            results_dir.mkdir(parents=True, exist_ok=True)
            task_id = config.get("task_id", "unknown")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            result_file = results_dir / f"scenario_{task_id}_{timestamp}.json"
            
            with open(result_file, "w") as f:
                json.dump({"config": config, "results": result}, f, indent=2)
            print(f"\n💾 Results saved to: {result_file}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
