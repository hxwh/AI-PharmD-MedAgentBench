#!/usr/bin/env python3
"""
Test script to send assessment request to Green Agent
"""

import asyncio
import json
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart


async def send_assessment_request():
    """Send assessment request to Green Agent and observe orchestration."""

    green_endpoint = "http://localhost:9009"
    participants = {"agent": "http://localhost:9019"}
    config = {
        "task_id": "task1_1",
        "mcp_server_url": "http://localhost:8002",
        "max_rounds": 10,
        "timeout": 60
    }

    request_data = {"participants": participants, "config": config}
    print("=" * 60)
    print("Assessment Request Test")
    print("=" * 60)
    print(f"📤 Sending assessment request to Green Agent at {green_endpoint}")
    print(f"   Participants: {participants}")
    print(f"   Config: {config}")
    print(f"\n📋 Full request data:\n{json.dumps(request_data, indent=2)}\n")

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            # Get agent card
            resolver = A2ACardResolver(httpx_client=client, base_url=green_endpoint)
            agent_card = await resolver.get_agent_card()
            print("✅ Successfully connected to Green Agent")
            print(f"   Agent: {agent_card.name}")
            print(f"   URL: {agent_card.url}")

            # Create A2A client
            factory = ClientFactory(ClientConfig(httpx_client=client, streaming=True))
            a2a_client = factory.create(agent_card)

            # Create assessment message
            message = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(kind="text", text=json.dumps(request_data)))],
                message_id="assessment-request",
            )

            print("\n🔄 Starting assessment orchestration...")
            print("   Green Agent should now:")
            print("   1. Parse the assessment request")
            print("   2. Validate participants and config")
            print("   3. Load task definition")
            print("   4. Prepare MCP tools")
            print("   5. Send task to Purple Agent via A2A")
            print("   6. Orchestrate the evaluation flow")
            print("   7. Return results")
            print("\n" + "=" * 60)
            print("ORCHESTRATION OUTPUT:")
            print("=" * 60)

            # Send message and observe orchestration
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

            print("\n" + "=" * 60)
            print("ASSESSMENT COMPLETE")
            print("=" * 60)

            if result:
                print("📊 Final Results:")
                print(json.dumps(result, indent=2))
            else:
                print("ℹ️  No structured results returned")

            return result

        except Exception as e:
            print(f"❌ Error during assessment: {e}")
            return None


if __name__ == "__main__":
    asyncio.run(send_assessment_request())