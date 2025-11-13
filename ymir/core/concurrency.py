"""
Concurrency runtime for Ymir programming language.

Provides Go-style concurrency primitives:
- spawn: Launch concurrent tasks
- channels: Type-safe communication between tasks
- async/await: Asynchronous function support
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
    Uses Go-style concurrency with spawn and channels.
    """

    def __init__(self):
        """Initialize the concurrency runtime."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.tasks: Dict[str, asyncio.Task] = {}
        self.channels: Dict[str, Channel] = {}
        self._task_counter = 0
        self._in_async_context = False
        self._in_spawned_task = False  # Separate flag for spawned tasks vs entry point

    def initialize(self) -> None:
        """Initialize or get the event loop."""
        try:
            self.loop = asyncio.get_running_loop()
            logger.info("Using existing event loop")
        except RuntimeError:
            # No running loop, create a new one
            # Clear any tasks from a previous loop to avoid cross-loop issues
            if self.tasks:
                logger.warning(f"Clearing {len(self.tasks)} tasks from previous event loop")
                self.tasks.clear()
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
            # Wrap sync function in async wrapper (cooperative, not parallel)
            # This avoids threading issues with asyncio
            async def wrapped():
                # Yield control to allow other tasks to run
                await asyncio.sleep(0)
                return func(*args, **kwargs)

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
            # Filter out tasks that don't belong to the current loop
            current_loop = asyncio.get_running_loop()
            valid_tasks = []
            invalid_task_ids = []

            for task_id, task in self.tasks.items():
                try:
                    # Check if the task belongs to the current loop
                    if task.get_loop() == current_loop:
                        valid_tasks.append(task)
                    else:
                        invalid_task_ids.append(task_id)
                        logger.warning(f"Task {task_id} belongs to a different event loop, skipping")
                except Exception as e:
                    logger.warning(f"Error checking task {task_id}: {e}")
                    invalid_task_ids.append(task_id)

            # Remove invalid tasks
            for task_id in invalid_task_ids:
                del self.tasks[task_id]

            # Gather only valid tasks
            if valid_tasks:
                await asyncio.gather(*valid_tasks, return_exceptions=True)
                logger.info(f"All {len(valid_tasks)} valid tasks completed")
            else:
                logger.info("No valid tasks to wait for")

    def run_until_complete(self, coro) -> Any:
        """
        Run a coroutine until it completes, ensuring spawned tasks can execute.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        if self.loop is None:
            self.initialize()

        # Check if the loop is already running
        try:
            running_loop = asyncio.get_running_loop()
            if running_loop is self.loop:
                # Loop is already running - we're inside an async context
                # This shouldn't happen with the new design where everything runs async
                logger.error("Attempted to call run_until_complete from within running loop!")
                raise RuntimeError("Cannot call run_until_complete from async context")
        except RuntimeError:
            # No running loop, we can safely use run_until_complete
            pass

        # Wrap the coroutine to ensure spawned tasks get a chance to run
        async def run_with_tasks():
            # Give spawned tasks a chance to start
            await asyncio.sleep(0)
            # Now await the main coroutine
            result = await coro
            # Give tasks another chance after the operation
            await asyncio.sleep(0)
            return result

        # Run the coroutine to completion
        # The event loop will also process any spawned tasks
        return self.loop.run_until_complete(run_with_tasks())

    def enter_async_context(self) -> None:
        """Mark that we're entering an async execution context."""
        self._in_async_context = True

    def exit_async_context(self) -> None:
        """Mark that we're exiting an async execution context."""
        self._in_async_context = False

    def is_in_async_context(self) -> bool:
        """Check if we're currently in an async execution context."""
        return self._in_async_context

    def enter_spawned_task_context(self) -> None:
        """Mark that we're in a spawned task (not entry point)."""
        self._in_spawned_task = True
        self.enter_async_context()

    def exit_spawned_task_context(self) -> None:
        """Mark that we're exiting a spawned task."""
        self._in_spawned_task = False
        self.exit_async_context()

    def is_in_spawned_task(self) -> bool:
        """Check if currently executing in a spawned task (not entry point)."""
        return self._in_spawned_task

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
