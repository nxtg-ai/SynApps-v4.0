"""
Unit tests for the content-based routing system
"""

import pytest
import asyncio
import re
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.persistent_messaging import PersistentMessageBus
from communication.content_routing import ContentRouter

class TestContentRouting:
    """Test suite for content-based routing components"""
    
    @pytest.fixture
    def mock_message_bus(self):
        """Create a mock message bus for testing"""
        message_bus = MagicMock(spec=PersistentMessageBus)
        message_bus.subscribe = MagicMock()
        message_bus.unsubscribe = MagicMock()
        return message_bus
    
    @pytest.fixture
    def content_router(self, mock_message_bus):
        """Create a content router for testing"""
        return ContentRouter(mock_message_bus)
    
    @pytest.mark.asyncio
    async def test_add_route(self, content_router, mock_message_bus):
        """Test adding a route"""
        # Create a mock condition and handler
        condition = MagicMock(return_value=True)
        handler = AsyncMock()
        
        # Add a route
        content_router.add_route("test_route", condition, handler, ["test_topic"])
        
        # Verify message bus was subscribed to
        mock_message_bus.subscribe.assert_called_once()
        assert "test_topic" in content_router.active_subscriptions
        assert "test_route" in content_router.routes
    
    @pytest.mark.asyncio
    async def test_remove_route(self, content_router, mock_message_bus):
        """Test removing a route"""
        # Create a mock condition and handler
        condition = MagicMock(return_value=True)
        handler = AsyncMock()
        
        # Add a route
        content_router.add_route("test_route", condition, handler, ["test_topic"])
        
        # Remove the route
        result = content_router.remove_route("test_route")
        
        # Verify route was removed
        assert result is True
        assert "test_route" not in content_router.routes
        mock_message_bus.unsubscribe.assert_called_once()
        assert "test_topic" not in content_router.active_subscriptions
    
    @pytest.mark.asyncio
    async def test_route_handler(self, content_router):
        """Test the route handler"""
        # Create a mock condition and handler
        condition = MagicMock(return_value=True)
        handler = AsyncMock()
        
        # Add a route
        content_router.add_route("test_route", condition, handler, ["test_topic"])
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Call the route handler
        await content_router._route_handler(message)
        
        # Verify condition and handler were called
        condition.assert_called_once_with(message)
        handler.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_keyword_route(self, content_router):
        """Test keyword-based routing"""
        # Create a mock handler
        handler = AsyncMock()
        
        # Add a keyword route
        content_router.add_keyword_route(
            "keyword_route", 
            ["important", "urgent"], 
            handler, 
            ["test_topic"]
        )
        
        # Create test messages
        matching_message = AppletMessage(content="This is an important message")
        non_matching_message = AppletMessage(content="This is a regular message")
        
        # Call the route handler with both messages
        await content_router._route_handler(matching_message)
        await content_router._route_handler(non_matching_message)
        
        # Verify handler was called only for the matching message
        handler.assert_called_once_with(matching_message)
    
    @pytest.mark.asyncio
    async def test_regex_route(self, content_router):
        """Test regex-based routing"""
        # Create a mock handler
        handler = AsyncMock()
        
        # Add a regex route
        content_router.add_regex_route(
            "regex_route", 
            r"error.*code:\s*(\d+)", 
            handler, 
            ["test_topic"],
            re.IGNORECASE
        )
        
        # Create test messages
        matching_message = AppletMessage(content="An Error occurred with code: 404")
        non_matching_message = AppletMessage(content="Operation completed successfully")
        
        # Call the route handler with both messages
        await content_router._route_handler(matching_message)
        await content_router._route_handler(non_matching_message)
        
        # Verify handler was called only for the matching message
        handler.assert_called_once_with(matching_message)
    
    @pytest.mark.asyncio
    async def test_metadata_route(self, content_router):
        """Test metadata-based routing"""
        # Create a mock handler
        handler = AsyncMock()
        
        # Add a metadata route
        content_router.add_metadata_route(
            "metadata_route", 
            "source", 
            "user_input", 
            handler, 
            ["test_topic"]
        )
        
        # Create test messages
        matching_message = AppletMessage(
            content="User message", 
            metadata={"source": "user_input"}
        )
        non_matching_message = AppletMessage(
            content="System message", 
            metadata={"source": "system"}
        )
        
        # Call the route handler with both messages
        await content_router._route_handler(matching_message)
        await content_router._route_handler(non_matching_message)
        
        # Verify handler was called only for the matching message
        handler.assert_called_once_with(matching_message)
    
    @pytest.mark.asyncio
    async def test_priority_route(self, content_router):
        """Test priority-based routing"""
        # Create a mock handler
        handler = AsyncMock()
        
        # Add a priority route
        content_router.add_priority_route(
            "priority_route", 
            8,  # Min priority
            handler, 
            ["test_topic"]
        )
        
        # Create test messages
        high_priority = PriorityMessage(content="Critical alert", priority=9)
        medium_priority = PriorityMessage(content="Important notice", priority=6)
        low_priority = PriorityMessage(content="Information", priority=3)
        
        # Call the route handler with all messages
        await content_router._route_handler(high_priority)
        await content_router._route_handler(medium_priority)
        await content_router._route_handler(low_priority)
        
        # Verify handler was called only for the high priority message
        handler.assert_called_once_with(high_priority)
    
    @pytest.mark.asyncio
    async def test_multiple_routes(self, content_router):
        """Test multiple routes with the same message"""
        # Create mock handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Add routes
        content_router.add_keyword_route(
            "keyword_route", 
            ["alert"], 
            handler1, 
            ["test_topic"]
        )
        content_router.add_priority_route(
            "priority_route", 
            8,
            handler2, 
            ["test_topic"]
        )
        
        # Create a message that matches both routes
        message = PriorityMessage(content="Critical alert", priority=9)
        
        # Call the route handler
        await content_router._route_handler(message)
        
        # Verify both handlers were called
        handler1.assert_called_once_with(message)
        handler2.assert_called_once_with(message)
    
    def test_get_active_routes(self, content_router):
        """Test getting active routes"""
        # Add some routes
        handler = AsyncMock()
        content_router.add_keyword_route("route1", ["keyword1"], handler, ["topic1"])
        content_router.add_regex_route("route2", r"pattern", handler, ["topic2"])
        
        # Get active routes
        routes = content_router.get_active_routes()
        
        # Verify routes were returned
        assert len(routes) == 2
        route_ids = [r["id"] for r in routes]
        assert "route1" in route_ids
        assert "route2" in route_ids
