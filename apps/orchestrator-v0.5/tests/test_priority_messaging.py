"""
Unit tests for the priority messaging system
"""

import pytest
import asyncio
from typing import List

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.priority_messaging import PriorityMessageBus
from communication.priority_agent_messaging import PriorityAgentCommunicator

class TestPriorityMessaging:
    """Test suite for priority messaging components"""
    
    @pytest.fixture
    def message_bus(self):
        """Create a priority message bus for testing"""
        return PriorityMessageBus()
    
    @pytest.fixture
    def agent_communicator(self, message_bus):
        """Create a priority agent communicator for testing"""
        return PriorityAgentCommunicator(message_bus)
    
    @pytest.mark.asyncio
    async def test_priority_message_model(self):
        """Test the PriorityMessage model"""
        # Create a priority message
        message = PriorityMessage(
            content="Test message",
            priority=8
        )
        
        # Check properties
        assert message.content == "Test message"
        assert message.priority == 8
        assert message.is_critical() is True
        assert message.is_background() is False
        
        # Create a low priority message
        low_message = PriorityMessage(
            content="Background task",
            priority=1
        )
        
        # Check properties
        assert low_message.content == "Background task"
        assert low_message.priority == 1
        assert low_message.is_critical() is False
        assert low_message.is_background() is True
    
    @pytest.mark.asyncio
    async def test_priority_message_bus(self, message_bus):
        """Test the PriorityMessageBus"""
        # Create test messages with different priorities
        high_priority = PriorityMessage(content="High priority", priority=9)
        medium_priority = PriorityMessage(content="Medium priority", priority=5)
        low_priority = PriorityMessage(content="Low priority", priority=2)
        
        # Create a collector for received messages
        received_messages: List[AppletMessage] = []
        
        # Create a subscriber callback
        async def collect_message(message: AppletMessage):
            received_messages.append(message)
            await asyncio.sleep(0.1)  # Simulate processing time
        
        # Subscribe to test topic
        message_bus.subscribe("test_topic", collect_message)
        
        # Publish messages in reverse priority order
        await message_bus.publish("test_topic", low_priority)
        await message_bus.publish("test_topic", medium_priority)
        await message_bus.publish("test_topic", high_priority)
        
        # Allow time for processing
        await asyncio.sleep(0.5)
        
        # Check that messages were received in priority order (highest first)
        assert len(received_messages) == 3
        assert received_messages[0].content == "High priority"
        assert received_messages[1].content == "Medium priority"
        assert received_messages[2].content == "Low priority"
    
    @pytest.mark.asyncio
    async def test_priority_agent_communicator(self, agent_communicator):
        """Test the PriorityAgentCommunicator"""
        # Create test messages
        standard_message = AppletMessage(content="Standard message")
        
        # Create a collector for received messages
        received_messages: List[AppletMessage] = []
        
        # Create a subscriber callback
        async def collect_message(message: AppletMessage):
            received_messages.append(message)
            await asyncio.sleep(0.1)  # Simulate processing time
        
        # Register handler for test agent
        agent_communicator.register_agent_handler("test_agent", collect_message)
        
        # Send messages with different priorities
        await agent_communicator.send_to_agent_with_priority("test_agent", standard_message, 3)
        await agent_communicator.send_critical_to_agent("test_agent", standard_message)
        
        # Allow time for processing
        await asyncio.sleep(0.5)
        
        # Check that messages were received in priority order (critical first)
        assert len(received_messages) == 2
        assert isinstance(received_messages[0], PriorityMessage)
        assert received_messages[0].priority == 10  # Critical message
        assert isinstance(received_messages[1], PriorityMessage)
        assert received_messages[1].priority == 3   # Low priority message
    
    @pytest.mark.asyncio
    async def test_get_messages_by_priority(self, agent_communicator):
        """Test filtering messages by priority"""
        # Create and send test messages with different priorities
        await agent_communicator.send_to_agent_with_priority(
            "test_agent", AppletMessage(content="Low priority"), 2)
        await agent_communicator.send_to_agent_with_priority(
            "test_agent", AppletMessage(content="Medium priority"), 5)
        await agent_communicator.send_to_agent_with_priority(
            "test_agent", AppletMessage(content="High priority"), 8)
        
        # Get all messages
        all_messages = agent_communicator.get_agent_messages("test_agent")
        assert len(all_messages) == 3
        
        # Get messages with priority >= 5
        important_messages = agent_communicator.get_agent_messages_by_priority(
            "test_agent", min_priority=5)
        assert len(important_messages) == 2
        assert all(isinstance(msg, PriorityMessage) for msg in important_messages)
        assert all(msg.priority >= 5 for msg in important_messages)
        
        # Get critical messages
        critical_messages = agent_communicator.get_critical_agent_messages("test_agent")
        assert len(critical_messages) == 1
        assert critical_messages[0].content == "High priority"
