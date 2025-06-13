"""
Content-based routing for the Meta-Agent Orchestrator messaging system
Provides advanced message routing based on content patterns and conditions
"""

import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable, Pattern, Set, Tuple

from models.agent_message import AppletMessage
from communication.persistent_messaging import PersistentMessageBus

logger = logging.getLogger("communication.content_routing")

# Type definitions
RouteCondition = Callable[[AppletMessage], bool]
RouteHandler = Callable[[AppletMessage], Awaitable[None]]
RouteId = str

class ContentRouter:
    """
    Content-based router for intelligent message routing.
    Routes messages based on content patterns and conditions.
    """
    
    def __init__(self, message_bus: PersistentMessageBus):
        """
        Initialize the content router.
        
        Args:
            message_bus: Message bus to use for routing
        """
        self.message_bus = message_bus
        
        # Dictionary of route conditions and handlers
        # {route_id: (condition, handler, topics)}
        self.routes: Dict[RouteId, Tuple[RouteCondition, RouteHandler, Set[str]]] = {}
        
        # Track active subscriptions to avoid duplicates
        self.active_subscriptions: Set[str] = set()
        
        logger.info("Content router initialized")
    
    async def _route_handler(self, message: AppletMessage) -> None:
        """
        Handle incoming messages and route them based on conditions.
        
        Args:
            message: Message to route
        """
        for route_id, (condition, handler, _) in self.routes.items():
            try:
                if condition(message):
                    logger.info(f"Message matched route condition: {route_id}")
                    await handler(message)
            except Exception as e:
                logger.error(f"Error in route handler {route_id}: {str(e)}")
    
    def add_route(self, route_id: str, condition: RouteCondition, 
                handler: RouteHandler, topics: List[str]) -> None:
        """
        Add a new content-based route.
        
        Args:
            route_id: Unique identifier for the route
            condition: Function that determines if a message matches the route
            handler: Function to handle matched messages
            topics: List of topics to listen on for this route
        """
        if route_id in self.routes:
            logger.warning(f"Overwriting existing route: {route_id}")
        
        # Store the route
        self.routes[route_id] = (condition, handler, set(topics))
        
        # Subscribe to topics if not already subscribed
        for topic in topics:
            if topic not in self.active_subscriptions:
                self.message_bus.subscribe(topic, self._route_handler)
                self.active_subscriptions.add(topic)
                logger.info(f"Subscribed to topic for content routing: {topic}")
    
    def remove_route(self, route_id: str) -> bool:
        """
        Remove a content-based route.
        
        Args:
            route_id: ID of the route to remove
            
        Returns:
            True if the route was removed, False if it didn't exist
        """
        if route_id not in self.routes:
            logger.warning(f"Route not found: {route_id}")
            return False
        
        # Remove the route
        _, _, topics = self.routes.pop(route_id)
        
        # Check if we can unsubscribe from any topics
        for topic in topics:
            # Check if any other routes are using this topic
            topic_still_needed = any(topic in route_topics for _, _, route_topics in self.routes.values())
            
            if not topic_still_needed and topic in self.active_subscriptions:
                # No other routes need this topic, unsubscribe
                self.message_bus.unsubscribe(topic, self._route_handler)
                self.active_subscriptions.remove(topic)
                logger.info(f"Unsubscribed from topic: {topic}")
        
        logger.info(f"Removed route: {route_id}")
        return True
    
    def add_keyword_route(self, route_id: str, keywords: List[str], 
                        handler: RouteHandler, topics: List[str],
                        case_sensitive: bool = False) -> None:
        """
        Add a route that matches messages containing specific keywords.
        
        Args:
            route_id: Unique identifier for the route
            keywords: List of keywords to match
            handler: Function to handle matched messages
            topics: List of topics to listen on for this route
            case_sensitive: Whether keyword matching should be case sensitive
        """
        def keyword_condition(message: AppletMessage) -> bool:
            content = message.content
            if not case_sensitive:
                content = content.lower()
                keywords_to_match = [k.lower() for k in keywords]
            else:
                keywords_to_match = keywords
            
            return any(keyword in content for keyword in keywords_to_match)
        
        self.add_route(route_id, keyword_condition, handler, topics)
        logger.info(f"Added keyword route {route_id} with {len(keywords)} keywords")
    
    def add_regex_route(self, route_id: str, pattern: str, 
                      handler: RouteHandler, topics: List[str],
                      flags: int = 0) -> None:
        """
        Add a route that matches messages using a regex pattern.
        
        Args:
            route_id: Unique identifier for the route
            pattern: Regex pattern to match
            handler: Function to handle matched messages
            topics: List of topics to listen on for this route
            flags: Regex flags (e.g., re.IGNORECASE)
        """
        compiled_pattern = re.compile(pattern, flags)
        
        def regex_condition(message: AppletMessage) -> bool:
            return bool(compiled_pattern.search(message.content))
        
        self.add_route(route_id, regex_condition, handler, topics)
        logger.info(f"Added regex route {route_id} with pattern: {pattern}")
    
    def add_metadata_route(self, route_id: str, metadata_key: str, metadata_value: Any,
                         handler: RouteHandler, topics: List[str]) -> None:
        """
        Add a route that matches messages with specific metadata.
        
        Args:
            route_id: Unique identifier for the route
            metadata_key: Metadata key to match
            metadata_value: Metadata value to match
            handler: Function to handle matched messages
            topics: List of topics to listen on for this route
        """
        def metadata_condition(message: AppletMessage) -> bool:
            return message.metadata.get(metadata_key) == metadata_value
        
        self.add_route(route_id, metadata_condition, handler, topics)
        logger.info(f"Added metadata route {route_id} for {metadata_key}={metadata_value}")
    
    def add_priority_route(self, route_id: str, min_priority: int,
                         handler: RouteHandler, topics: List[str]) -> None:
        """
        Add a route that matches messages with a minimum priority level.
        
        Args:
            route_id: Unique identifier for the route
            min_priority: Minimum priority level to match
            handler: Function to handle matched messages
            topics: List of topics to listen on for this route
        """
        def priority_condition(message: AppletMessage) -> bool:
            if hasattr(message, 'priority'):
                return message.priority >= min_priority
            return False
        
        self.add_route(route_id, priority_condition, handler, topics)
        logger.info(f"Added priority route {route_id} for priority >= {min_priority}")
    
    def get_active_routes(self) -> List[Dict[str, Any]]:
        """
        Get a list of active routes.
        
        Returns:
            List of route information dictionaries
        """
        routes_info = []
        for route_id, (_, _, topics) in self.routes.items():
            routes_info.append({
                "id": route_id,
                "topics": list(topics)
            })
        return routes_info
