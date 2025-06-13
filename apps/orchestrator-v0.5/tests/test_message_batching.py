"""
Unit tests for the message batching and throttling system
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.persistent_messaging import PersistentMessageBus
from communication.message_batching import (
    MessageBatcher,
    MessageThrottler,
    BatchingMessageBus
)

class TestMessageBatching:
    """Test suite for message batching components"""
    
    @pytest.fixture
    def mock_message_bus(self):
        """Create a mock message bus for testing"""
        message_bus = MagicMock(spec=PersistentMessageBus)
        message_bus.publish = AsyncMock()
        message_bus.subscribe = MagicMock()
        message_bus.unsubscribe = MagicMock()
        return message_bus
    
    @pytest.mark.asyncio
    async def test_message_batcher_add_message(self):
        """Test adding messages to a batcher"""
        # Create a batcher with small batch size
        batcher = MessageBatcher(batch_size=2, timeout_seconds=10.0)
        
        # Create a mock batch handler
        handler = AsyncMock()
        batcher.register_batch_handler("test_topic", handler)
        
        # Start the batcher
        await batcher.start()
        
        try:
            # Add messages
            message1 = AppletMessage(content="Message 1")
            message2 = AppletMessage(content="Message 2")
            
            await batcher.add_message("test_topic", message1)
            
            # First message shouldn't trigger batch processing yet
            handler.assert_not_called()
            
            await batcher.add_message("test_topic", message2)
            
            # Second message should trigger batch processing
            await asyncio.sleep(0.1)  # Allow time for processing
            handler.assert_called_once()
            
            # Verify batch contents
            batch = handler.call_args[0][0]
            assert len(batch) == 2
            assert batch[0].content == "Message 1"
            assert batch[1].content == "Message 2"
        finally:
            # Stop the batcher
            await batcher.stop()
    
    @pytest.mark.asyncio
    async def test_message_batcher_timeout(self):
        """Test batch timeout processing"""
        # Create a batcher with short timeout
        batcher = MessageBatcher(batch_size=5, timeout_seconds=0.2)
        
        # Create a mock batch handler
        handler = AsyncMock()
        batcher.register_batch_handler("test_topic", handler)
        
        # Start the batcher
        await batcher.start()
        
        try:
            # Add a message
            message = AppletMessage(content="Test message")
            await batcher.add_message("test_topic", message)
            
            # Message shouldn't trigger batch processing yet
            handler.assert_not_called()
            
            # Wait for timeout
            await asyncio.sleep(0.3)
            
            # Timeout should trigger batch processing
            handler.assert_called_once()
            
            # Verify batch contents
            batch = handler.call_args[0][0]
            assert len(batch) == 1
            assert batch[0].content == "Test message"
        finally:
            # Stop the batcher
            await batcher.stop()
    
    @pytest.mark.asyncio
    async def test_message_batcher_unregister_handler(self):
        """Test unregistering a batch handler"""
        # Create a batcher
        batcher = MessageBatcher()
        
        # Create a mock batch handler
        handler = AsyncMock()
        batcher.register_batch_handler("test_topic", handler)
        
        # Unregister the handler
        result = batcher.unregister_batch_handler("test_topic")
        
        # Verify handler was unregistered
        assert result is True
        assert "test_topic" not in batcher.batch_handlers
        
        # Try to unregister a non-existent handler
        result = batcher.unregister_batch_handler("non_existent")
        
        # Verify operation failed
        assert result is False
    
    @pytest.mark.asyncio
    async def test_message_throttler_acquire(self):
        """Test acquiring tokens from a throttler"""
        # Create a throttler with 5 tokens
        throttler = MessageThrottler(rate_limit=5, time_window_seconds=1.0)
        
        # Acquire tokens
        result1 = await throttler.acquire(2)
        result2 = await throttler.acquire(2)
        result3 = await throttler.acquire(2)
        
        # Verify results
        assert result1 is True   # 5 - 2 = 3 tokens left
        assert result2 is True   # 3 - 2 = 1 token left
        assert result3 is False  # Not enough tokens (need 2, have 1)
        
        # Verify token count
        assert throttler.tokens == 1
    
    @pytest.mark.asyncio
    async def test_message_throttler_refill(self):
        """Test token refill in a throttler"""
        # Create a throttler with 5 tokens and fast refill
        throttler = MessageThrottler(rate_limit=5, time_window_seconds=0.1)
        
        # Use all tokens
        result1 = await throttler.acquire(5)
        assert result1 is True
        assert throttler.tokens == 0
        
        # Wait for refill
        await asyncio.sleep(0.2)  # Should refill all tokens
        
        # Try to acquire tokens again
        result2 = await throttler.acquire(5)
        
        # Verify tokens were refilled
        assert result2 is True
        assert throttler.tokens == 0
    
    @pytest.mark.asyncio
    async def test_message_throttler_wait_for_tokens(self):
        """Test waiting for tokens"""
        # Create a throttler with 2 tokens and fast refill
        throttler = MessageThrottler(rate_limit=10, time_window_seconds=0.1)
        
        # Use all tokens
        await throttler.acquire(10)
        assert throttler.tokens == 0
        
        # Start waiting for tokens
        start_time = time.time()
        await throttler.wait_for_tokens(5)
        elapsed = time.time() - start_time
        
        # Verify we waited for tokens
        assert elapsed >= 0.05  # Should wait at least half the time window
        assert throttler.tokens >= 0  # Should have used the tokens
    
    @pytest.mark.asyncio
    async def test_batching_message_bus(self, mock_message_bus):
        """Test batching message bus"""
        # Create a batching message bus
        bus = BatchingMessageBus(
            mock_message_bus,
            batch_size=2,
            batch_timeout_seconds=1.0,
            rate_limit=10,
            time_window_seconds=1.0
        )
        
        # Create a mock batch handler
        batch_handler = AsyncMock()
        
        # Register the batch handler
        bus.register_batch_handler("test_topic", batch_handler)
        
        # Start the bus
        await bus.start()
        
        try:
            # Publish messages
            message1 = AppletMessage(content="Message 1")
            message2 = AppletMessage(content="Message 2")
            
            await bus.publish("test_topic", message1)
            await bus.publish("test_topic", message2)
            
            # Allow time for batch processing
            await asyncio.sleep(0.1)
            
            # Verify batch was processed
            batch_handler.assert_called_once()
            batch = batch_handler.call_args[0][0]
            assert len(batch) == 2
            assert batch[0].content == "Message 1"
            assert batch[1].content == "Message 2"
            
            # Test immediate publishing
            message3 = AppletMessage(content="Message 3")
            await bus.publish_immediate("test_topic", message3)
            
            # Verify message was published directly
            mock_message_bus.publish.assert_called_once_with("test_topic", message3)
        finally:
            # Stop the bus
            await bus.stop()
    
    @pytest.mark.asyncio
    async def test_batching_message_bus_subscribe(self, mock_message_bus):
        """Test subscribing to a batching message bus"""
        # Create a batching message bus
        bus = BatchingMessageBus(mock_message_bus)
        
        # Create a mock callback
        callback = AsyncMock()
        
        # Subscribe to a topic
        bus.subscribe("test_topic", callback)
        
        # Verify subscription was passed to underlying bus
        mock_message_bus.subscribe.assert_called_once_with("test_topic", callback)
        
        # Unsubscribe from the topic
        result = bus.unsubscribe("test_topic", callback)
        
        # Verify unsubscription was passed to underlying bus
        mock_message_bus.unsubscribe.assert_called_once_with("test_topic", callback)
    
    @pytest.mark.asyncio
    async def test_batching_message_bus_history(self, mock_message_bus):
        """Test getting message history from a batching message bus"""
        # Create a batching message bus
        bus = BatchingMessageBus(mock_message_bus)
        
        # Mock history methods
        mock_message_bus.get_message_history = MagicMock(return_value=["message1", "message2"])
        mock_message_bus.get_message_history_from_db = AsyncMock(return_value=["message3", "message4"])
        
        # Get in-memory history
        history1 = bus.get_message_history("test_topic", 10, 5)
        
        # Verify method was called on underlying bus
        mock_message_bus.get_message_history.assert_called_once_with("test_topic", 10, 5)
        assert history1 == ["message1", "message2"]
        
        # Get database history
        history2 = await bus.get_message_history_from_db("test_topic", 20, 8)
        
        # Verify method was called on underlying bus
        mock_message_bus.get_message_history_from_db.assert_called_once_with("test_topic", 20, 8)
        assert history2 == ["message3", "message4"]
