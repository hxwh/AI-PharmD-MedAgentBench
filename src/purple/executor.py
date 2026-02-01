"""A2A executor for Purple Agent."""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Task,
    TaskState,
    Part,
    TextPart,
    DataPart,
    UnsupportedOperationError,
    InvalidRequestError,
)
from a2a.utils.errors import ServerError
from a2a.utils import (
    get_message_text,
    new_agent_text_message,
    new_task,
)

from .agent import Agent


TERMINAL_STATES = {
    TaskState.completed,
    TaskState.canceled,
    TaskState.failed,
    TaskState.rejected
}


class Executor(AgentExecutor):
    """Executor for Purple Agent tasks."""
    
    def __init__(self):
        """Initialize executor with agent instances per context."""
        self.agents: dict[str, Agent] = {}  # context_id -> agent instance
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute a Purple Agent task.
        
        Args:
            context: The request context
            event_queue: Event queue for task updates
            
        Raises:
            ServerError: If request is invalid or task is already processed
        """
        msg = context.message
        if not msg:
            raise ServerError(
                error=InvalidRequestError(message="Missing message in request")
            )
        
        task = context.current_task
        if task and task.status.state in TERMINAL_STATES:
            raise ServerError(
                error=InvalidRequestError(
                    message=f"Task {task.id} already processed (state: {task.status.state})"
                )
            )
        
        # Create new task if needed
        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)
        
        # Get or create agent for this context
        context_id = task.context_id
        agent = self.agents.get(context_id)
        if not agent:
            agent = Agent()
            self.agents[context_id] = agent
        
        # Create task updater
        updater = TaskUpdater(event_queue, task.id, context_id)
        
        # Start work
        await updater.update_status(
            TaskState.working,
            new_agent_text_message("Connecting to MCP server...")
        )
        
        try:
            # Extract task prompt from message
            task_prompt = get_message_text(msg)
            
            # Run agent
            result, trajectory = await agent.run(task_prompt)
            
            # Add result as artifact
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=result)),
                    Part(root=DataPart(data={"trajectory": trajectory})),
                ],
                name="Response",
            )
            
            # Complete if not already in terminal state
            if not updater._terminal_state_reached:
                await updater.complete()
                
        except Exception as e:
            print(f"Task failed with agent error: {e}")
            await updater.failed(
                new_agent_text_message(
                    f"Agent error: {e}",
                    context_id=context_id,
                    task_id=task.id
                )
            )
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel a task (not supported).
        
        Args:
            context: The request context
            event_queue: Event queue
            
        Raises:
            ServerError: Always raises UnsupportedOperationError
        """
        raise ServerError(error=UnsupportedOperationError())
