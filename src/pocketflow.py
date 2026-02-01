"""Minimal PocketFlow implementation for MedAgentBench."""

import asyncio
import time
from typing import Any, Optional


class Node:
    """Base node with prep -> exec -> post pattern."""
    
    def __init__(self, max_retries: int = 0, wait: int = 0):
        self.max_retries = max_retries
        self.wait = wait
        self.cur_retry = 0
        self.params = {}
        self.next_nodes = {}
    
    def set_params(self, params: dict):
        """Set node parameters."""
        self.params = params
        return self
    
    def prep(self, shared: dict) -> Any:
        """Prepare data from shared store."""
        return None
    
    def exec(self, prep_res: Any) -> Any:
        """Execute main logic (no shared access)."""
        return prep_res
    
    def post(self, shared: dict, prep_res: Any, exec_res: Any) -> Optional[str]:
        """Write results to shared store, return action."""
        return "default"
    
    def exec_fallback(self, prep_res: Any, exc: Exception) -> Any:
        """Fallback when exec fails after retries."""
        raise exc
    
    def run(self, shared: dict) -> Optional[str]:
        """Run the node with retry logic."""
        prep_res = self.prep(shared)
        
        for attempt in range(self.max_retries + 1):
            self.cur_retry = attempt
            try:
                exec_res = self.exec(prep_res)
                return self.post(shared, prep_res, exec_res)
            except Exception as e:
                if attempt < self.max_retries:
                    if self.wait > 0:
                        time.sleep(self.wait * (2 ** attempt))
                    continue
                else:
                    exec_res = self.exec_fallback(prep_res, e)
                    return self.post(shared, prep_res, exec_res)
    
    def __rshift__(self, other: "Node") -> "Node":
        """Default transition: self >> other."""
        self.next_nodes["default"] = other
        return other
    
    def __sub__(self, action: str):
        """Named action: self - "action" >> other."""
        class ActionBinder:
            def __init__(self, node, action):
                self.node = node
                self.action = action
            
            def __rshift__(self, other):
                self.node.next_nodes[self.action] = other
                return other
        
        return ActionBinder(self, action)


class AsyncNode(Node):
    """Async node for I/O operations."""
    
    async def prep_async(self, shared: dict) -> Any:
        """Async prep."""
        return self.prep(shared)
    
    async def exec_async(self, prep_res: Any) -> Any:
        """Async exec."""
        return self.exec(prep_res)
    
    async def post_async(self, shared: dict, prep_res: Any, exec_res: Any) -> Optional[str]:
        """Async post."""
        return self.post(shared, prep_res, exec_res)
    
    async def run_async(self, shared: dict) -> Optional[str]:
        """Run async node with retry logic."""
        prep_res = await self.prep_async(shared)
        
        for attempt in range(self.max_retries + 1):
            self.cur_retry = attempt
            try:
                exec_res = await self.exec_async(prep_res)
                return await self.post_async(shared, prep_res, exec_res)
            except Exception as e:
                if attempt < self.max_retries:
                    if self.wait > 0:
                        await asyncio.sleep(self.wait * (2 ** attempt))
                    continue
                else:
                    exec_res = self.exec_fallback(prep_res, e)
                    return await self.post_async(shared, prep_res, exec_res)


class Flow:
    """Flow orchestrator."""
    
    def __init__(self, start: Node):
        self.start = start
    
    def run(self, shared: dict):
        """Run the flow."""
        current = self.start
        
        while current:
            action = current.run(shared)
            if action is None or action not in current.next_nodes:
                break
            current = current.next_nodes[action]


class AsyncFlow:
    """Async flow orchestrator."""
    
    def __init__(self, start: Node):
        self.start = start
    
    async def run_async(self, shared: dict):
        """Run the async flow, handling both sync and async nodes."""
        current = self.start
        
        while current:
            # Check if node has run_async method (duck typing for robustness)
            if hasattr(current, 'run_async') and asyncio.iscoroutinefunction(current.run_async):
                action = await current.run_async(shared)
            else:
                # Sync node - run in thread pool to avoid blocking
                try:
                    action = await asyncio.to_thread(current.run, shared)
                except AttributeError:
                    # Fallback for Python < 3.9
                    loop = asyncio.get_event_loop()
                    action = await loop.run_in_executor(None, current.run, shared)
            
            if action is None or action not in current.next_nodes:
                break
            current = current.next_nodes[action]


class BatchNode(Node):
    """Node that processes multiple items."""
    
    def prep(self, shared: dict) -> list:
        """Return iterable of items."""
        return []
    
    def exec(self, item: Any) -> Any:
        """Process single item."""
        return item
    
    def post(self, shared: dict, prep_res: list, exec_res_list: list) -> Optional[str]:
        """Post-process all results."""
        return "default"
    
    def run(self, shared: dict) -> Optional[str]:
        """Run batch processing."""
        items = self.prep(shared)
        results = []
        
        for item in items:
            for attempt in range(self.max_retries + 1):
                self.cur_retry = attempt
                try:
                    result = self.exec(item)
                    results.append(result)
                    break
                except Exception as e:
                    if attempt < self.max_retries:
                        if self.wait > 0:
                            time.sleep(self.wait * (2 ** attempt))
                        continue
                    else:
                        result = self.exec_fallback(item, e)
                        results.append(result)
                        break
        
        return self.post(shared, items, results)
