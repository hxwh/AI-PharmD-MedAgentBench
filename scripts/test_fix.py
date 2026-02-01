#!/usr/bin/env python3
"""Simple test to verify the note parameter fix."""

import asyncio
import os
import sys
sys.path.insert(0, '/root/UTSA-SOYOUDU/PharmAgent/purple_agent/src')
from agent import Agent

async def test_note_fix():
    """Test that the agent now formats note parameter correctly."""

    # Create agent
    agent = Agent()

    # Test task that requires create_service_request with note
    task_prompt = """Order orthopedic surgery referral for patient S6550627. Specify within the free text of the referral, "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations." """

    try:
        result, trajectory = await agent.run_task(task_prompt)
        print("Test completed successfully!")
        print(f"Result: {result}")

        # Check trajectory for note parameter usage
        for step in trajectory:
            if step.get('tool_name') == 'create_service_request':
                args = step.get('tool_args', {})
                note_value = args.get('note')
                print(f"Note parameter: {note_value}")
                if isinstance(note_value, dict) and 'text' in note_value:
                    print("✅ SUCCESS: Note parameter is correctly formatted as single object")
                    return True
                elif isinstance(note_value, list):
                    print("❌ FAILED: Note parameter is still formatted as array")
                    return False
                else:
                    print(f"⚠️  UNKNOWN: Note parameter format: {type(note_value)}")
                    return False

        print("⚠️  No create_service_request call found in trajectory")
        return False

    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    # Set minimal environment
    os.environ.setdefault("GOOGLE_API_KEY", "test_key")
    os.environ.setdefault("MAX_ROUNDS", "3")  # Limit rounds for testing

    success = asyncio.run(test_note_fix())
    exit(0 if success else 1)