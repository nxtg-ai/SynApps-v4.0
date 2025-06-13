"""
Unit tests for the persistent messaging system
"""

import pytest
import asyncio
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.persistent_messaging import PersistentMessageBus
from communication.persistent_agent_messaging import PersistentAgentCommunicator
from db.repository.message_repository import MessageRepository

class TestPersistentMessaging:
    """Test suite for persistent messaging components"""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock message repository for testing"""
        repository = AsyncMock(spec=MessageRepository)
        repository.save_message = AsyncMock(return_value="test-message-id")
        repository.get_messages = AsyncMock(return_value=[
            PriorityMessage(content="Test message 1", priority=8),
            PriorityMessage(content="Test message 2", priority=5)
        ])
        repository.delete_messages = AsyncMock(return_value=2)
        return repository
    
    @pytest.fixture
    def message_bus(self, mock_repository):
        """Create a persistent message bus for testing"""
        return PersistentMessageBus(mock_repository)
    
    @pytest.fixture
    def agent_communicator(self, message_bus):
        """Create a persistent agent communicator for testing"""
        return PersistentAgentCommunicator(message_bus)
    
    @pytest.mark.asyncio
    async def test_persistent_message_bus_publish(self, message_bus, mock_repository):
        """Test message publishing with persistence"""
        # Create a test message
        message = PriorityMessage(content="Test message", priority=8)
        
        # Create a collector for received messages
        received_messages = []
        
        # Create a subscriber callback
        async def collect_message(message):
            received_messages.append(message)
        
        # Subscribe to test topic
        message_bus.subscribe("test_topic", collect_message)
        
        # Publish message
        await message_bus.publish("test_topic", message)
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        # Verify message was persisted
        mock_repository.save_message.assert_called_once_with("test_topic", message)
        
        # Verify message was delivered
        assert len(received_messages) == 1
        assert received_messages[0].content == "Test message"
        assert received_messages[0].metadata["id"] == "test-message-id"
    
    @pytest.mark.asyncio
    async def test_get_message_history_from_db(self, message_bus, mock_repository):
        """Test retrieving message history from database"""
        # Get message history
        messages = await message_bus.get_message_history_from_db("test_topic", 10, 5)
        
        # Verify repository was called
        mock_repository.get_messages.assert_called_once_with("test_topic", 10, 5)
        
        # Verify messages were returned
        assert len(messages) == 2
        assert messages[0].content == "Test message 1"
        assert messages[1].content == "Test message 2"
    
    @pytest.mark.asyncio
    async def test_clear_message_history(self, message_bus, mock_repository):
        """Test clearing message history"""
        # Add some messages to in-memory history
        message = AppletMessage(content="Test message")
        message_bus.message_history["test_topic"] = [message]
        
        # Clear message history
        deleted_count = await message_bus.clear_message_history("test_topic")
        
        # Verify repository was called
        mock_repository.delete_messages.assert_called_once_with("test_topic")
        
        # Verify in-memory history was cleared
        assert "test_topic" not in message_bus.message_history
        
        # Verify delete count was returned
        assert deleted_count == 2
    
    @pytest.mark.asyncio
    async def test_persistent_agent_communicator(self, agent_communicator, mock_repository):
        """Test persistent agent communicator"""
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Send message to agent
        await agent_communicator.send_to_agent("test_agent", message)
        
        # Verify message was persisted
        mock_repository.save_message.assert_called_once()
        assert mock_repository.save_message.call_args[0][0] == "agent.test_agent"
        
        # Get agent message history from database
        messages = await agent_communicator.get_agent_message_history_from_db("test_agent")
        
        # Verify repository was called
        mock_repository.get_messages.assert_called_once_with("agent.test_agent", 100, 0)
        
        # Verify messages were returned
        assert len(messages) == 2
    
    @pytest.mark.asyncio
    async def test_get_agent_conversation_history(self, agent_communicator):
        """Test getting formatted conversation history"""
        # Mock the get_agent_message_history_from_db method
        agent_communicator.get_agent_message_history_from_db = AsyncMock(return_value=[
            AppletMessage(
                content="Hello, how can I help?", 
                metadata={"from_system": False}
            ),
            AppletMessage(
                content="I need assistance", 
                metadata={"from_user": True}
            ),
            AppletMessage(
                content="System initialization", 
                metadata={"from_system": True}
            )
        ])
        
        # Get conversation history
        conversation = await agent_communicator.get_agent_conversation_history("test_agent")
        
        # Verify conversation format
        assert len(conversation) == 3
        assert conversation[0]["role"] == "system"
        assert conversation[0]["content"] == "System initialization"
        assert conversation[1]["role"] == "user"
        assert conversation[1]["content"] == "I need assistance"
        assert conversation[2]["role"] == "assistant"
        assert conversation[2]["content"] == "Hello, how can I help?"
