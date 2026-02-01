"""A2A Protocol messenger utility for agent communication."""

import json
from uuid import uuid4
from typing import Optional, Callable, Awaitable

import httpx
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
)
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    DataPart,
    TaskState,
)
from a2a.utils import new_agent_text_message


DEFAULT_TIMEOUT = 300


def create_message(
    *, role: Role = Role.user, text: str, context_id: str | None = None
) -> Message:
    """Create an A2A message."""
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
        context_id=context_id,
    )


def merge_parts(parts: list[Part]) -> tuple:
    """Merge message parts into a single string and extract trajectory.
    
    Returns:
        Tuple of (text_response, trajectory_list or None)
    """
    chunks = []
    trajectory = None
    for part in parts:
        if isinstance(part.root, TextPart):
            chunks.append(part.root.text)
        elif isinstance(part.root, DataPart):
            # Extract trajectory if present
            data = part.root.data
            if isinstance(data, dict) and "trajectory" in data:
                trajectory = data["trajectory"]
            else:
                chunks.append(json.dumps(data, indent=2))
    return "\n".join(chunks), trajectory


class A2AMessenger:
    """Messenger for A2A protocol communication."""
    
    def __init__(self):
        self._context_ids = {}

    async def talk_to_agent(
        self,
        message: str,
        url: str,
        new_conversation: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        streaming: bool = False,
        status_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> tuple:
        """
        Communicate with another agent via A2A protocol.

        Args:
            message: The message to send to the agent
            url: The agent's URL endpoint
            new_conversation: If True, start fresh conversation
            timeout: Timeout in seconds for the request
            streaming: If True, enable streaming to receive intermediate updates
            status_callback: Optional async callback(status, message_text) for status updates

        Returns:
            Tuple of (response_str, trajectory_list or None)
            
        Raises:
            RuntimeError: If agent responds with non-completed status
        """
        outputs = await self._send_message(
            message=message,
            base_url=url,
            context_id=None if new_conversation else self._context_ids.get(url, None),
            timeout=timeout,
            streaming=streaming,
            status_callback=status_callback,
        )
        if outputs.get("status", "completed") != "completed":
            raise RuntimeError(f"{url} responded with: {outputs}")
        self._context_ids[url] = outputs.get("context_id", None)
        return outputs["response"], outputs.get("trajectory")

    async def _send_message(
        self,
        message: str,
        base_url: str,
        context_id: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        streaming: bool = False,
        status_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> dict:
        """Send A2A message and return response."""
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
            agent_card = await resolver.get_agent_card()
            config = ClientConfig(
                httpx_client=httpx_client,
                streaming=streaming,
            )
            factory = ClientFactory(config)
            client = factory.create(agent_card)

            outbound_msg = create_message(text=message, context_id=context_id)
            last_event = None
            outputs = {"response": "", "context_id": None, "trajectory": None}

            async for event in client.send_message(outbound_msg):
                last_event = event
                
                # Forward intermediate status updates if streaming and callback provided
                if streaming and status_callback:
                    match event:
                        case (task, update):
                            state = task.status.state.value
                            if task.status.message:
                                for part in task.status.message.parts:
                                    if hasattr(part.root, "text") and part.root.text:
                                        await status_callback(state, part.root.text)

            match last_event:
                case Message() as msg:
                    outputs["context_id"] = msg.context_id
                    text, trajectory = merge_parts(msg.parts)
                    outputs["response"] += text
                    if trajectory:
                        outputs["trajectory"] = trajectory

                case (task, update):
                    outputs["context_id"] = task.context_id
                    outputs["status"] = task.status.state.value
                    msg = task.status.message
                    if msg:
                        text, trajectory = merge_parts(msg.parts)
                        outputs["response"] += text
                        if trajectory:
                            outputs["trajectory"] = trajectory
                    if task.artifacts:
                        for artifact in task.artifacts:
                            text, trajectory = merge_parts(artifact.parts)
                            outputs["response"] += text
                            if trajectory and not outputs["trajectory"]:
                                outputs["trajectory"] = trajectory

            return outputs

    def reset(self):
        """Reset conversation contexts."""
        self._context_ids = {}


if __name__ == "__main__":
    import asyncio
    
    async def test():
        messenger = A2AMessenger()
        # Test with a local agent (update URL as needed)
        response = await messenger.talk_to_agent(
            "Hello, how are you?",
            "http://localhost:9009",
            new_conversation=True
        )
        print(f"Response: {response}")
    
    asyncio.run(test())
