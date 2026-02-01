#!/usr/bin/env python3
"""
AgentBeats Assessment Runner for PharmAgent Leaderboard
Communicates with Docker containers running the agents
"""

import os
import json
import httpx
import time
from datetime import datetime
import uuid

def load_config():
    """Load scenario configuration"""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open('scenario.toml', 'rb') as f:
        return tomllib.load(f)

def wait_for_service(url, timeout=60):
    """Wait for a service to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)
    return False

def run_assessment():
    """Run the assessment by communicating with Docker containers"""
    config = load_config()
    subtask = config['config'].get('subtask', 'subtask1')

    # Wait for agents to be ready
    green_url = "http://localhost:9009"
    purple_url = "http://localhost:9019"

    print("Waiting for green agent...")
    if not wait_for_service(f"{green_url}/.well-known/agent-card.json"):
        print("ERROR: Green agent not ready")
        return None

    print("Waiting for purple agent...")
    if not wait_for_service(f"{purple_url}/.well-known/agent-card.json"):
        print("ERROR: Purple agent not ready")
        return None

    print("Both agents are ready. Starting assessment...")

    # For now, return mock results - in a real implementation,
    # you would send A2A protocol messages to the green agent
    # to trigger the assessment with the purple agent
    if subtask == 'subtask1':
        return {
            'score': 0.85,
            'success_rate': 0.85,
            'details': 'Mock subtask1 results - replace with actual A2A communication'
        }
    else:
        return {
            'accuracy': 0.75,
            'hallucination_rate': 0.25,
            'details': 'Mock subtask2 results - replace with actual A2A communication'
        }

def main():
    results = run_assessment()
    if not results:
        return 1

    # Save results
    os.makedirs('results', exist_ok=True)

    assessment = {
        'submission_id': str(uuid.uuid4()),
        'participant_id': load_config()['participants'][0]['agentbeats_id'],
        'config': load_config()['config'],
        'result': results,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }

    with open(f'results/assessment_{assessment["submission_id"]}.json', 'w') as f:
        json.dump(assessment, f, indent=2)

    print(f"Assessment completed: {results}")
    return 0

if __name__ == '__main__':
    exit(main())