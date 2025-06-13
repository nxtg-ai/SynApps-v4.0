"""
Dynamic routing system for the Meta-Agent Orchestrator
Provides intelligent message routing based on content, metadata, and system state
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Set, Tuple, Union, TypeVar
from enum import Enum
import re
import json
from dataclasses import dataclass, field

from models.agent_message import AppletMessage
from communication.persistent_messaging import PersistentMessageBus
from communication.message_batching import BatchingMessageBus
from communication.message_replay import ReplayableMessageBus

logger = logging.getLogger("communication.dynamic_routing")

# Type definitions
T = TypeVar('T', bound=AppletMessage)
RouteHandler = Callable[[T], Awaitable[None]]
RoutePredicate = Callable[[T], Awaitable[bool]]
MessageTransformer = Callable[[T], Awaitable[T]]

class RouteType(Enum):
    """Types of message routes"""
    CONTENT = "content"      # Route based on message content
    METADATA = "metadata"    # Route based on message metadata
    PATTERN = "pattern"      # Route based on regex pattern matching
    AGENT = "agent"          # Route based on source/target agent
    CUSTOM = "custom"        # Route based on custom predicate function
    DEFAULT = "default"      # Default route when no others match


@dataclass
class Route:
    """
    Represents a message route with its routing criteria and handler
    """
    name: str
    route_type: RouteType
    target_topic: str
    handler: RouteHandler
    priority: int = 0
    
    # Content-based routing
    content_keywords: List[str] = field(default_factory=list)
    
    # Metadata-based routing
    metadata_keys: Dict[str, Any] = field(default_factory=dict)
    
    # Pattern-based routing
    pattern: Optional[str] = None
    pattern_flags: int = 0
    compiled_pattern: Optional[re.Pattern] = None
    
    # Agent-based routing
    source_agent: Optional[str] = None
    target_agent: Optional[str] = None
    
    # Custom predicate
    predicate: Optional[RoutePredicate] = None
    
    # Transformations to apply before routing
    transformers: List[MessageTransformer] = field(default_factory=list)
    
    def __post_init__(self):
        """Compile regex pattern if provided"""
        if self.pattern:
            self.compiled_pattern = re.compile(self.pattern, self.pattern_flags)

    async def matches(self, message: T) -> bool:
        """
        Check if a message matches this route's criteria
        
        Args:
            message: Message to check
            
        Returns:
            True if the message matches, False otherwise
        """
        if self.route_type == RouteType.DEFAULT:
            return True
        
        elif self.route_type == RouteType.CONTENT:
            if not self.content_keywords:
                return False
            
            # Check if message content contains any of the keywords
            if hasattr(message, 'content') and isinstance(message.content, str):
                content = message.content.lower()
                return any(keyword.lower() in content for keyword in self.content_keywords)
            return False
        
        elif self.route_type == RouteType.METADATA:
            if not self.metadata_keys:
                return False
            
            # Check if message metadata matches all required keys
            if hasattr(message, 'metadata') and isinstance(message.metadata, dict):
                for key, value in self.metadata_keys.items():
                    if key not in message.metadata:
                        return False
                    
                    # If value is None, just check for key existence
                    if value is not None and message.metadata[key] != value:
                        return False
                
                return True
            return False
        
        elif self.route_type == RouteType.PATTERN:
            if not self.compiled_pattern:
                return False
            
            # Check if message content matches the pattern
            if hasattr(message, 'content') and isinstance(message.content, str):
                return bool(self.compiled_pattern.search(message.content))
            return False
        
        elif self.route_type == RouteType.AGENT:
            # Check source agent
            if self.source_agent and hasattr(message, 'source'):
                if message.source != self.source_agent:
                    return False
            
            # Check target agent
            if self.target_agent and hasattr(message, 'target'):
                if message.target != self.target_agent:
                    return False
            
            return True
        
        elif self.route_type == RouteType.CUSTOM:
            if not self.predicate:
                return False
            
            # Use custom predicate function
            return await self.predicate(message)
        
        return False


class DynamicRouter:
    """
    Router that dynamically routes messages based on content, metadata, and system state
    """
    
    def __init__(self):
        """Initialize the dynamic router"""
        # Dictionary of source topic -> list of routes
        self.routes: Dict[str, List[Route]] = {}
        
        # Dictionary of route name -> route
        self.route_by_name: Dict[str, Route] = {}
        
        # Default routes for each topic
        self.default_routes: Dict[str, Route] = {}
        
        logger.info("Dynamic router initialized")
    
    def add_route(self, source_topic: str, route: Route) -> None:
        """
        Add a route for a source topic
        
        Args:
            source_topic: Topic to route from
            route: Route to add
        """
        # Initialize routes list if needed
        if source_topic not in self.routes:
            self.routes[source_topic] = []
        
        # Add route to list
        self.routes[source_topic].append(route)
        
        # Add route to name lookup
        self.route_by_name[route.name] = route
        
        # If this is a default route, store it separately
        if route.route_type == RouteType.DEFAULT:
            self.default_routes[source_topic] = route
        
        # Sort routes by priority (highest first)
        self.routes[source_topic].sort(key=lambda r: -r.priority)
        
        logger.info(f"Added route '{route.name}' from topic '{source_topic}' to '{route.target_topic}'")
    
    def remove_route(self, route_name: str) -> bool:
        """
        Remove a route by name
        
        Args:
            route_name: Name of the route to remove
            
        Returns:
            True if the route was removed, False if it wasn't found
        """
        if route_name not in self.route_by_name:
            return False
        
        # Get the route
        route = self.route_by_name[route_name]
        
        # Remove from all topic lists
        for topic, routes in self.routes.items():
            if route in routes:
                routes.remove(route)
        
        # Remove from name lookup
        del self.route_by_name[route_name]
        
        # Remove from default routes if applicable
        for topic, default_route in list(self.default_routes.items()):
            if default_route.name == route_name:
                del self.default_routes[topic]
        
        logger.info(f"Removed route '{route_name}'")
        return True
    
    def get_route(self, route_name: str) -> Optional[Route]:
        """
        Get a route by name
        
        Args:
            route_name: Name of the route to get
            
        Returns:
            The route, or None if not found
        """
        return self.route_by_name.get(route_name)
    
    def get_routes_for_topic(self, topic: str) -> List[Route]:
        """
        Get all routes for a topic
        
        Args:
            topic: Topic to get routes for
            
        Returns:
            List of routes for the topic
        """
        return self.routes.get(topic, [])
    
    async def find_matching_route(self, topic: str, message: T) -> Optional[Route]:
        """
        Find the first matching route for a message
        
        Args:
            topic: Source topic
            message: Message to route
            
        Returns:
            Matching route, or None if no match found
        """
        # Check if we have routes for this topic
        if topic not in self.routes:
            return None
        
        # Check each route in priority order
        for route in self.routes[topic]:
            if await route.matches(message):
                return route
        
        # Return default route if available
        return self.default_routes.get(topic)
    
    async def apply_transformers(self, route: Route, message: T) -> T:
        """
        Apply all transformers for a route to a message
        
        Args:
            route: Route with transformers
            message: Message to transform
            
        Returns:
            Transformed message
        """
        result = message
        
        # Apply each transformer in sequence
        for transformer in route.transformers:
            try:
                result = await transformer(result)
            except Exception as e:
                logger.error(f"Error applying transformer for route '{route.name}': {str(e)}")
        
        return result


class RoutingMessageBus:
    """
    Message bus with dynamic routing capabilities
    """
    
    def __init__(self, message_bus: Union[PersistentMessageBus, BatchingMessageBus, ReplayableMessageBus]):
        """
        Initialize the routing message bus
        
        Args:
            message_bus: Underlying message bus to wrap
        """
        self.message_bus = message_bus
        self.router = DynamicRouter()
        
        # Dictionary of topic -> callback
        self.callbacks: Dict[str, Set[Callable[[T], Awaitable[None]]]] = {}
        
        logger.info("Routing message bus initialized")
    
    async def start(self) -> None:
        """Start the routing message bus"""
        # Start the underlying message bus if it has a start method
        if hasattr(self.message_bus, 'start'):
            await self.message_bus.start()
        
        logger.info("Routing message bus started")
    
    async def stop(self) -> None:
        """Stop the routing message bus"""
        # Stop the underlying message bus if it has a stop method
        if hasattr(self.message_bus, 'stop'):
            await self.message_bus.stop()
        
        logger.info("Routing message bus stopped")
    
    def add_route(self, source_topic: str, route: Route) -> None:
        """
        Add a route
        
        Args:
            source_topic: Topic to route from
            route: Route to add
        """
        self.router.add_route(source_topic, route)
        
        # Make sure we're subscribed to the source topic
        self._ensure_source_subscription(source_topic)
    
    def remove_route(self, route_name: str) -> bool:
        """
        Remove a route
        
        Args:
            route_name: Name of the route to remove
            
        Returns:
            True if the route was removed, False if it wasn't found
        """
        return self.router.remove_route(route_name)
    
    def get_route(self, route_name: str) -> Optional[Route]:
        """
        Get a route by name
        
        Args:
            route_name: Name of the route to get
            
        Returns:
            The route, or None if not found
        """
        return self.router.get_route(route_name)
    
    def _ensure_source_subscription(self, topic: str) -> None:
        """
        Ensure we're subscribed to a source topic
        
        Args:
            topic: Topic to subscribe to
        """
        # Check if we're already subscribed
        if topic in self.callbacks:
            return
        
        # Subscribe to the topic
        self.message_bus.subscribe(topic, self._route_message)
        
        # Initialize callback set
        self.callbacks[topic] = set()
        
        logger.info(f"Subscribed to source topic: {topic}")
    
    async def _route_message(self, message: T) -> None:
        """
        Route a message according to routing rules
        
        Args:
            message: Message to route
        """
        # Determine the source topic
        source_topic = message.topic if hasattr(message, 'topic') else None
        
        if not source_topic:
            logger.warning(f"Message has no topic, cannot route: {message}")
            return
        
        # Find a matching route
        route = await self.router.find_matching_route(source_topic, message)
        
        if not route:
            logger.debug(f"No matching route for message on topic '{source_topic}'")
            return
        
        # Apply transformers
        transformed_message = await self.router.apply_transformers(route, message)
        
        # Route the message
        try:
            # If the route has a handler, use it
            if route.handler:
                await route.handler(transformed_message)
            
            # Otherwise, publish to the target topic
            else:
                await self.message_bus.publish(route.target_topic, transformed_message)
            
            logger.debug(f"Routed message from '{source_topic}' to '{route.target_topic}' via route '{route.name}'")
        
        except Exception as e:
            logger.error(f"Error routing message via route '{route.name}': {str(e)}")
    
    async def publish(self, topic: str, message: T) -> None:
        """
        Publish a message to a topic
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        # Set the topic on the message if it has a topic attribute
        if hasattr(message, 'topic'):
            message.topic = topic
        
        await self.message_bus.publish(topic, message)
    
    def subscribe(self, topic: str, callback: Callable[[T], Awaitable[None]]) -> None:
        """
        Subscribe to a topic
        
        Args:
            topic: Topic to subscribe to
            callback: Function to call when a message is received
        """
        # Subscribe to the underlying message bus
        self.message_bus.subscribe(topic, callback)
        
        # Add to our callback set
        if topic not in self.callbacks:
            self.callbacks[topic] = set()
        
        self.callbacks[topic].add(callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[T], Awaitable[None]]) -> bool:
        """
        Unsubscribe from a topic
        
        Args:
            topic: Topic to unsubscribe from
            callback: Function to unsubscribe
            
        Returns:
            True if the callback was unsubscribed, False otherwise
        """
        # Unsubscribe from the underlying message bus
        result = self.message_bus.unsubscribe(topic, callback)
        
        # Remove from our callback set
        if topic in self.callbacks and callback in self.callbacks[topic]:
            self.callbacks[topic].remove(callback)
        
        return result
    
    def create_content_route(self, name: str, source_topic: str, target_topic: str,
                           keywords: List[str], priority: int = 0) -> Route:
        """
        Create a content-based route
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            keywords: Keywords to match in content
            priority: Route priority
            
        Returns:
            Created route
        """
        route = Route(
            name=name,
            route_type=RouteType.CONTENT,
            target_topic=target_topic,
            handler=None,
            priority=priority,
            content_keywords=keywords
        )
        
        self.add_route(source_topic, route)
        return route
    
    def create_metadata_route(self, name: str, source_topic: str, target_topic: str,
                            metadata: Dict[str, Any], priority: int = 0) -> Route:
        """
        Create a metadata-based route
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            metadata: Metadata keys and values to match
            priority: Route priority
            
        Returns:
            Created route
        """
        route = Route(
            name=name,
            route_type=RouteType.METADATA,
            target_topic=target_topic,
            handler=None,
            priority=priority,
            metadata_keys=metadata
        )
        
        self.add_route(source_topic, route)
        return route
    
    def create_pattern_route(self, name: str, source_topic: str, target_topic: str,
                           pattern: str, case_sensitive: bool = True, priority: int = 0) -> Route:
        """
        Create a pattern-based route
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            pattern: Regex pattern to match
            case_sensitive: Whether the pattern is case-sensitive
            priority: Route priority
            
        Returns:
            Created route
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        
        route = Route(
            name=name,
            route_type=RouteType.PATTERN,
            target_topic=target_topic,
            handler=None,
            priority=priority,
            pattern=pattern,
            pattern_flags=flags
        )
        
        self.add_route(source_topic, route)
        return route
    
    def create_agent_route(self, name: str, source_topic: str, target_topic: str,
                         source_agent: Optional[str] = None, target_agent: Optional[str] = None,
                         priority: int = 0) -> Route:
        """
        Create an agent-based route
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            source_agent: Source agent to match
            target_agent: Target agent to match
            priority: Route priority
            
        Returns:
            Created route
        """
        route = Route(
            name=name,
            route_type=RouteType.AGENT,
            target_topic=target_topic,
            handler=None,
            priority=priority,
            source_agent=source_agent,
            target_agent=target_agent
        )
        
        self.add_route(source_topic, route)
        return route
    
    def create_custom_route(self, name: str, source_topic: str, target_topic: str,
                          predicate: RoutePredicate, priority: int = 0) -> Route:
        """
        Create a custom route with a predicate function
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            predicate: Function that determines if a message matches
            priority: Route priority
            
        Returns:
            Created route
        """
        route = Route(
            name=name,
            route_type=RouteType.CUSTOM,
            target_topic=target_topic,
            handler=None,
            priority=priority,
            predicate=predicate
        )
        
        self.add_route(source_topic, route)
        return route
    
    def create_default_route(self, name: str, source_topic: str, target_topic: str) -> Route:
        """
        Create a default route for when no other routes match
        
        Args:
            name: Route name
            source_topic: Topic to route from
            target_topic: Topic to route to
            
        Returns:
            Created route
        """
        route = Route(
            name=name,
            route_type=RouteType.DEFAULT,
            target_topic=target_topic,
            handler=None,
            priority=-1000  # Lowest priority
        )
        
        self.add_route(source_topic, route)
        return route
    
    def add_transformer_to_route(self, route_name: str, transformer: MessageTransformer) -> bool:
        """
        Add a transformer to a route
        
        Args:
            route_name: Name of the route to add the transformer to
            transformer: Transformer function
            
        Returns:
            True if the transformer was added, False if the route wasn't found
        """
        route = self.get_route(route_name)
        
        if not route:
            return False
        
        route.transformers.append(transformer)
        return True
