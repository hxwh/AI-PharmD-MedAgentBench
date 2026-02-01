#!/usr/bin/env python3
"""
Record provenance information for AgentBeats assessment
"""

import json
import os
from datetime import datetime

def record_provenance():
    """Record assessment provenance information"""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    # Load scenario config
    with open('scenario.toml', 'rb') as f:
        config = tomllib.load(f)

    # Create provenance record
    provenance = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'scenario_config': config,
        'environment': {
            'github_run_id': os.getenv('GITHUB_RUN_ID'),
            'github_sha': os.getenv('GITHUB_SHA'),
            'github_ref': os.getenv('GITHUB_REF'),
        },
        'docker_images': {
            'green_agent': 'ghcr.io/hxwh/pharmagent-green:latest',
            'purple_agent': 'ghcr.io/hxwh/pharmagent-purple:latest'
        }
    }

    # Save provenance
    os.makedirs('results', exist_ok=True)
    with open('results/provenance.json', 'w') as f:
        json.dump(provenance, f, indent=2)

    print("Provenance recorded")

if __name__ == '__main__':
    record_provenance()