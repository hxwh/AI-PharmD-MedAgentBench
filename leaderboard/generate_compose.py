#!/usr/bin/env python3
"""
Generate Docker Compose configuration for AgentBeats assessment
"""

import yaml
import os
import sys

def load_scenario_config():
    """Load scenario configuration from scenario.toml"""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open('scenario.toml', 'rb') as f:
        return tomllib.load(f)

def generate_docker_compose():
    """Generate docker-compose.yml based on scenario configuration"""
    config = load_scenario_config()

    green_agent_id = config['green_agent']['agentbeats_id']
    if not green_agent_id or green_agent_id == "your-pharmagent-green-agent-id":
        print("ERROR: Green agent ID not set in scenario.toml")
        sys.exit(1)

    # For now, we'll use placeholder logic since we don't have the actual AgentBeats API
    # In a real implementation, this would fetch agent details from AgentBeats API
    green_image = f"ghcr.io/hxwh/pharmagent-green:latest"  # Update with your actual image

    # Check if participant agent is specified
    participant_agent_id = config['participants'][0]['agentbeats_id'] if config['participants'] else ""
    if not participant_agent_id:
        print("ERROR: Participant agent ID not set in scenario.toml")
        sys.exit(1)

    # For now, use a placeholder purple agent image
    # In production, this would be fetched from AgentBeats API based on participant_agent_id
    purple_image = f"ghcr.io/hxwh/pharmagent-purple:latest"  # This would be dynamic

    # Read template and substitute variables
    with open('docker-compose.yml.template', 'r') as f:
        template = f.read()

    compose_content = template.replace('${GREEN_AGENT_IMAGE}', green_image)
    compose_content = compose_content.replace('${PURPLE_AGENT_IMAGE}', purple_image)

    # Write docker-compose.yml
    with open('docker-compose.yml', 'w') as f:
        f.write(compose_content)

    print(f"Generated docker-compose.yml with green: {green_image}, purple: {purple_image}")

if __name__ == '__main__':
    generate_docker_compose()