"""
Tests for Ymir concurrency features (spawn, channels).
"""

import pytest

from ymir.core.concurrency import Channel, ConcurrencyRuntime


class TestChannel:
    """Test Channel functionality."""

    def test_channel_creation(self):
        """Test creating a channel."""
        ch = Channel(int, buffer_size=5)
        assert ch.buffer_size == 5
        assert ch.element_type == int
        assert not ch.closed

    def test_unbuffered_channel(self):
        """Test unbuffered channel."""
        ch = Channel(int, buffer_size=0)
        assert ch.buffer_size == 0

    def test_channel_repr(self):
        """Test channel string representation."""
        ch = Channel(str, buffer_size=10)
        assert "Channel[str]" in repr(ch)


class TestConcurrencyRuntime:
    """Test ConcurrencyRuntime functionality."""

    def test_runtime_creation(self):
        """Test creating a runtime."""
        runtime = ConcurrencyRuntime()
        assert runtime.loop is None
        assert len(runtime.tasks) == 0

    def test_runtime_initialization(self):
        """Test runtime initialization."""
        runtime = ConcurrencyRuntime()
        runtime.initialize()
        assert runtime.loop is not None

    def test_create_channel(self):
        """Test creating a channel through runtime."""
        runtime = ConcurrencyRuntime()
        ch = runtime.create_channel(int, buffer_size=5)
        assert isinstance(ch, Channel)
        assert ch.element_type == int
        assert ch.buffer_size == 5

    def test_spawn_function(self):
        """Test spawning a function."""
        runtime = ConcurrencyRuntime()
        runtime.initialize()

        def test_func():
            return 42

        task_id = runtime.spawn(test_func)
        assert task_id.startswith("task_")
        assert task_id in runtime.tasks


class TestChannelOperations:
    """Test channel send/receive operations."""

    @pytest.mark.asyncio
    async def test_send_receive(self):
        """Test basic send and receive."""
        ch = Channel(int, buffer_size=1)

        await ch.send(42)
        value = await ch.receive()

        assert value == 42

    @pytest.mark.asyncio
    async def test_buffered_channel(self):
        """Test buffered channel operations."""
        ch = Channel(str, buffer_size=3)

        # Send multiple values
        await ch.send("hello")
        await ch.send("world")
        await ch.send("!")

        # Receive them
        assert await ch.receive() == "hello"
        assert await ch.receive() == "world"
        assert await ch.receive() == "!"

    @pytest.mark.asyncio
    async def test_channel_close(self):
        """Test closing a channel."""
        ch = Channel(int, buffer_size=1)

        await ch.send(100)
        ch.close()

        # Should still be able to receive buffered value
        value = await ch.receive()
        assert value == 100

        # Should raise error on send after close
        with pytest.raises(ValueError, match="Cannot send on closed channel"):
            await ch.send(200)
