"""
Unit tests for the message replay mechanism
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.persistent_messaging import PersistentMessageBus
from communication.message_replay import (
    MessageReplayManager,
    ReplayableMessageBus
)
from database.models.message_models import MessageStatus

class TestMessageReplay:
    """Test suite for message replay components"""
    
    @pytest.fixture
    def mock_message_bus(self):
        """Create a mock message bus for testing"""
        message_bus = MagicMock(spec=PersistentMessageBus)
        message_bus.publish = AsyncMock()
        message_bus.subscribe = MagicMock()
        message_bus.unsubscribe = MagicMock()
        message_bus.get_failed_messages = AsyncMock()
        message_bus.update_message_status = AsyncMock()
        return message_bus
    
    @pytest.mark.asyncio
    async def test_replay_manager_start_stop(self, mock_message_bus):
        """Test starting and stopping the replay manager"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Start the manager
        await manager.start()
        
        # Verify manager is running
        assert manager.running is True
        
        # Stop the manager
        await manager.stop()
        
        # Verify manager is stopped
        assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_register_processor_and_filter(self, mock_message_bus):
        """Test registering processors and filters"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor and filter
        processor = AsyncMock(return_value=True)
        filter_func = MagicMock(return_value=True)
        
        # Register processor and filter
        manager.register_processor("test_topic", processor)
        manager.register_filter("test_topic", filter_func)
        
        # Verify registration
        assert manager.processors["test_topic"] is processor
        assert manager.filters["test_topic"] is filter_func
    
    @pytest.mark.asyncio
    async def test_replay_failed_messages(self, mock_message_bus):
        """Test replaying failed messages"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor
        processor = AsyncMock(return_value=True)
        manager.register_processor("test_topic", processor)
        
        # Create mock failed messages
        message1 = AppletMessage(content="Failed message 1")
        message1.id = "msg1"
        message2 = AppletMessage(content="Failed message 2")
        message2.id = "msg2"
        failed_messages = [message1, message2]
        
        # Configure mock message bus
        mock_message_bus.get_failed_messages.return_value = failed_messages
        
        # Start the manager
        await manager.start()
        
        try:
            # Replay failed messages
            replay_id, count = await manager.replay_failed_messages("test_topic")
            
            # Verify count
            assert count == 2
            
            # Verify get_failed_messages was called
            mock_message_bus.get_failed_messages.assert_called_once()
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify processor was called for each message
            assert processor.call_count == 2
            assert processor.call_args_list[0][0][0] is message1
            assert processor.call_args_list[1][0][0] is message2
            
            # Verify update_message_status was called for each message
            assert mock_message_bus.update_message_status.call_count == 2
            mock_message_bus.update_message_status.assert_any_call("msg1", MessageStatus.PROCESSED)
            mock_message_bus.update_message_status.assert_any_call("msg2", MessageStatus.PROCESSED)
            
            # Verify replay status
            status = manager.get_replay_status(replay_id)
            assert status is not None
            assert status["topic"] == "test_topic"
            assert status["total_messages"] == 2
            assert status["processed_messages"] == 2
            assert status["successful_messages"] == 2
            assert status["failed_messages"] == 0
            assert status["status"] == "completed"
        finally:
            # Stop the manager
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_replay_with_filter(self, mock_message_bus):
        """Test replaying messages with a filter"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor
        processor = AsyncMock(return_value=True)
        manager.register_processor("test_topic", processor)
        
        # Create a filter that only accepts messages with "accept" in the content
        def filter_func(message):
            return "accept" in message.content.lower()
        
        manager.register_filter("test_topic", filter_func)
        
        # Create mock failed messages
        message1 = AppletMessage(content="Accept this message")
        message1.id = "msg1"
        message2 = AppletMessage(content="Reject this message")
        message2.id = "msg2"
        failed_messages = [message1, message2]
        
        # Configure mock message bus
        mock_message_bus.get_failed_messages.return_value = failed_messages
        
        # Start the manager
        await manager.start()
        
        try:
            # Replay failed messages
            replay_id, count = await manager.replay_failed_messages("test_topic")
            
            # Verify count (only one message should pass the filter)
            assert count == 1
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify processor was called only for the accepted message
            assert processor.call_count == 1
            assert processor.call_args_list[0][0][0] is message1
            
            # Verify update_message_status was called only for the accepted message
            assert mock_message_bus.update_message_status.call_count == 1
            mock_message_bus.update_message_status.assert_called_once_with("msg1", MessageStatus.PROCESSED)
        finally:
            # Stop the manager
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_processor_failure(self, mock_message_bus):
        """Test handling processor failures"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor that fails for the second message
        async def failing_processor(message):
            if message.id == "msg2":
                return False
            return True
        
        manager.register_processor("test_topic", failing_processor)
        
        # Create mock failed messages
        message1 = AppletMessage(content="Message 1")
        message1.id = "msg1"
        message2 = AppletMessage(content="Message 2")
        message2.id = "msg2"
        failed_messages = [message1, message2]
        
        # Configure mock message bus
        mock_message_bus.get_failed_messages.return_value = failed_messages
        
        # Start the manager
        await manager.start()
        
        try:
            # Replay failed messages
            replay_id, count = await manager.replay_failed_messages("test_topic")
            
            # Verify count
            assert count == 2
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify update_message_status was called for each message with appropriate status
            assert mock_message_bus.update_message_status.call_count == 2
            mock_message_bus.update_message_status.assert_any_call("msg1", MessageStatus.PROCESSED)
            mock_message_bus.update_message_status.assert_any_call("msg2", MessageStatus.FAILED)
            
            # Verify replay status
            status = manager.get_replay_status(replay_id)
            assert status is not None
            assert status["topic"] == "test_topic"
            assert status["total_messages"] == 2
            assert status["processed_messages"] == 2
            assert status["successful_messages"] == 1
            assert status["failed_messages"] == 1
            assert status["status"] == "completed"
        finally:
            # Stop the manager
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_processor_exception(self, mock_message_bus):
        """Test handling processor exceptions"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor that raises an exception
        async def exception_processor(message):
            if message.id == "msg2":
                raise ValueError("Test exception")
            return True
        
        manager.register_processor("test_topic", exception_processor)
        
        # Create mock failed messages
        message1 = AppletMessage(content="Message 1")
        message1.id = "msg1"
        message2 = AppletMessage(content="Message 2")
        message2.id = "msg2"
        failed_messages = [message1, message2]
        
        # Configure mock message bus
        mock_message_bus.get_failed_messages.return_value = failed_messages
        
        # Start the manager
        await manager.start()
        
        try:
            # Replay failed messages
            replay_id, count = await manager.replay_failed_messages("test_topic")
            
            # Verify count
            assert count == 2
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify update_message_status was called for each message with appropriate status
            assert mock_message_bus.update_message_status.call_count == 2
            mock_message_bus.update_message_status.assert_any_call("msg1", MessageStatus.PROCESSED)
            mock_message_bus.update_message_status.assert_any_call("msg2", MessageStatus.FAILED)
            
            # Verify replay status
            status = manager.get_replay_status(replay_id)
            assert status is not None
            assert status["topic"] == "test_topic"
            assert status["processed_messages"] == 2
            assert status["successful_messages"] == 1
            assert status["failed_messages"] == 1
            assert status["status"] == "completed"
        finally:
            # Stop the manager
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_no_processor_registered(self, mock_message_bus):
        """Test replaying messages with no processor registered"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Start the manager
        await manager.start()
        
        try:
            # Replay failed messages for a topic with no processor
            replay_id, count = await manager.replay_failed_messages("test_topic")
            
            # Verify empty result
            assert replay_id == ""
            assert count == 0
            
            # Verify get_failed_messages was not called
            mock_message_bus.get_failed_messages.assert_not_called()
        finally:
            # Stop the manager
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_replayable_message_bus(self, mock_message_bus):
        """Test replayable message bus"""
        # Create a replayable message bus
        bus = ReplayableMessageBus(mock_message_bus)
        
        # Start the bus
        await bus.start()
        
        try:
            # Create a mock callback
            callback = AsyncMock()
            
            # Subscribe to a topic
            bus.subscribe("test_topic", callback)
            
            # Verify subscription was passed to underlying bus
            mock_message_bus.subscribe.assert_called_once_with("test_topic", callback)
            
            # Verify processor was registered
            assert "test_topic" in bus.replay_manager.processors
            
            # Create mock failed messages
            message1 = AppletMessage(content="Failed message")
            message1.id = "msg1"
            failed_messages = [message1]
            
            # Configure mock message bus
            mock_message_bus.get_failed_messages.return_value = failed_messages
            
            # Replay failed messages
            replay_id, count = await bus.replay_failed_messages("test_topic")
            
            # Verify count
            assert count == 1
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify callback was called
            callback.assert_called_once_with(message1)
            
            # Verify update_message_status was called
            mock_message_bus.update_message_status.assert_called_once_with("msg1", MessageStatus.PROCESSED)
            
            # Test publishing a message
            message2 = AppletMessage(content="New message")
            await bus.publish("test_topic", message2)
            
            # Verify publish was passed to underlying bus
            mock_message_bus.publish.assert_called_once_with("test_topic", message2)
            
            # Test unsubscribing
            result = bus.unsubscribe("test_topic", callback)
            
            # Verify unsubscribe was passed to underlying bus
            mock_message_bus.unsubscribe.assert_called_once_with("test_topic", callback)
            
            # Test registering a replay filter
            filter_func = MagicMock(return_value=True)
            bus.register_replay_filter("test_topic", filter_func)
            
            # Verify filter was registered
            assert bus.replay_manager.filters["test_topic"] is filter_func
            
            # Test getting message history
            bus.get_message_history("test_topic", 10, 5)
            mock_message_bus.get_message_history.assert_called_once_with("test_topic", 10, 5)
            
            # Test getting message history from database
            await bus.get_message_history_from_db("test_topic", 20, 8)
            mock_message_bus.get_message_history_from_db.assert_called_once_with("test_topic", 20, 8)
        finally:
            # Stop the bus
            await bus.stop()
    
    @pytest.mark.asyncio
    async def test_schedule_periodic_replay(self, mock_message_bus):
        """Test scheduling periodic replay"""
        # Create a replay manager
        manager = MessageReplayManager(mock_message_bus)
        
        # Create mock processor
        processor = AsyncMock(return_value=True)
        manager.register_processor("test_topic", processor)
        
        # Create mock failed messages
        message = AppletMessage(content="Failed message")
        message.id = "msg1"
        failed_messages = [message]
        
        # Configure mock message bus
        mock_message_bus.get_failed_messages.return_value = failed_messages
        
        # Start the manager
        await manager.start()
        
        try:
            # Schedule periodic replay with a short interval
            task_id = await manager.schedule_periodic_replay(
                "test_topic", timedelta(milliseconds=100)
            )
            
            # Verify task ID is not empty
            assert task_id != ""
            
            # Allow time for at least one replay
            await asyncio.sleep(0.2)
            
            # Verify get_failed_messages was called at least once
            assert mock_message_bus.get_failed_messages.call_count >= 1
            
            # Verify processor was called at least once
            assert processor.call_count >= 1
        finally:
            # Stop the manager
            await manager.stop()
