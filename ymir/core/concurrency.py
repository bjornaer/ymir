"""
Concurrency runtime for Ymir programming language.

Provides Go-style concurrency primitives:
- spawn: Launch concurrent tasks
- channels: Type-safe communication between tasks
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("ymir.concurrency")


class Channel:
    """
    Thread-safe channel for communication between concurrent tasks.

    Channels are typed and use asyncio.Queue under the hood.
    """

    def __init__(self, element_type: type, buffer_size: int = 0):
        """
        Initialize a channel.

        Args:
            element_type: The type of elements that can be sent through the channel
            buffer_size: Size of the channel buffer (0 = unbuffered, blocking)
        """
        self.element_type = element_type
        self.buffer_size = buffer_size
        self.queue = asyncio.Queue(maxsize=buffer_size)
        self.closed = False

    async def send(self, value: Any) -> None:
        """
        Send a value to the channel.

        Args:
            value: The value to send

        Raises:
            ValueError: If channel is closed or value type doesn't match
        """
        if self.closed:
            raise ValueError("Cannot send on closed channel")

        # Type checking (simplified - in production would be more sophisticated)
        if self.element_type != Any and not isinstance(value, self.element_type):
            logger.warning(f"Type mismatch: expected {self.element_type}, got {type(value)}")

        await self.queue.put(value)
        logger.debug(f"Sent {value} to channel")

    async def receive(self) -> Any:
        """
        Receive a value from the channel.

        Returns:
            The value received from the channel

        Raises:
            ValueError: If channel is closed and empty
        """
        if self.closed and self.queue.empty():
            raise ValueError("Cannot receive from closed empty channel")

        value = await self.queue.get()
        logger.debug(f"Received {value} from channel")
        return value

    def close(self) -> None:
        """Close the channel. No more sends allowed."""
        self.closed = True

    def __repr__(self) -> str:
        return f"Channel[{self.element_type.__name__}](buffer={self.buffer_size})"


class ConcurrencyRuntime:
    """
    Runtime manager for concurrent tasks in Ymir.

    Manages spawned tasks, channels, and the event loop.
    """

    def __init__(self):
        """Initialize the concurrency runtime."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.tasks: Dict[str, asyncio.Task] = {}
        self.channels: Dict[str, Channel] = {}
        self._task_counter = 0

    def initialize(self) -> None:
        """Initialize or get the event loop."""
        try:
            self.loop = asyncio.get_running_loop()
            logger.info("Using existing event loop")
        except RuntimeError:
            # No running loop, create a new one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            logger.info("Created new event loop")

    def spawn(self, func: Callable, *args, **kwargs) -> str:
        """
        Spawn a new concurrent task.

        Args:
            func: The function to run concurrently
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Task identifier
        """
        if self.loop is None:
            self.initialize()

        task_id = f"task_{self._task_counter}"
        self._task_counter += 1

        # Wrap the function in a coroutine if it's not already one
        if asyncio.iscoroutinefunction(func):
            coro = func(*args, **kwargs)
        else:
            # Run in thread pool for CPU-bound tasks
            async def wrapped():
                return await self.loop.run_in_executor(self.thread_pool, func, *args, **kwargs)

            coro = wrapped()

        # Create and store the task
        task = self.loop.create_task(coro)
        self.tasks[task_id] = task

        logger.info(f"Spawned task {task_id}")
        return task_id

    def create_channel(self, element_type: type = Any, buffer_size: int = 0) -> Channel:
        """
        Create a new channel.

        Args:
            element_type: Type of elements in the channel
            buffer_size: Buffer size (0 = unbuffered)

        Returns:
            A new Channel instance
        """
        channel = Channel(element_type, buffer_size)
        logger.info(f"Created channel: {channel}")
        return channel

    async def wait_for_task(self, task_id: str) -> Any:
        """
        Wait for a specific task to complete.

        Args:
            task_id: The task identifier

        Returns:
            The result of the task
        """
        if task_id not in self.tasks:
            raise ValueError(f"Unknown task: {task_id}")

        result = await self.tasks[task_id]
        logger.info(f"Task {task_id} completed")
        return result

    async def wait_all(self) -> None:
        """Wait for all spawned tasks to complete."""
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
            logger.info("All tasks completed")

    def run_until_complete(self, coro) -> Any:
        """
        Run a coroutine until it completes.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        if self.loop is None:
            self.initialize()

        return self.loop.run_until_complete(coro)

    def shutdown(self) -> None:
        """Shutdown the runtime, cleaning up resources."""
        logger.info("Shutting down concurrency runtime")

        # Cancel all pending tasks
        for task_id, task in self.tasks.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled task {task_id}")

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        # Close the loop if we created it
        if self.loop and not self.loop.is_running():
            self.loop.close()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore errors during cleanup


# Global runtime instance
_runtime: Optional[ConcurrencyRuntime] = None


def get_runtime() -> ConcurrencyRuntime:
    """Get or create the global concurrency runtime."""
    global _runtime
    if _runtime is None:
        _runtime = ConcurrencyRuntime()
    return _runtime


def reset_runtime() -> None:
    """Reset the global runtime (useful for testing)."""
    global _runtime
    if _runtime is not None:
        _runtime.shutdown()
    _runtime = None
