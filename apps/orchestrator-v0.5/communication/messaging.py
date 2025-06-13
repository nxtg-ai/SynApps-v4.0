"""
Messaging system for the Meta-Agent Orchestrator
Handles agent-to-agent communication
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
import json

from models.agent_message import AppletMessage

logger = logging.getLogger("communication.messaging")

class MessageBus:
    """
    Message bus for agent-to-agent communication.
    Implements a publish-subscribe pattern for asynchronous messaging.
    """
    
    def __init__(self):
        """Initialize the message bus"""
        self.subscribers: Dict[str, List[Callable[[AppletMessage], Awaitable[None]]]] = {}
        self.message_history: Dict[str, List[AppletMessage]] = {}
        logger.info("Message bus initialized")
    
    async def publish(self, topic: str, message: AppletMessage) -> None:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        logger.info(f"Publishing message to topic: {topic}")
        
        # Store message in history
        if topic not in self.message_history:
            self.message_history[topic] = []
        self.message_history[topic].append(message)
        
        # Deliver to subscribers
        if topic in self.subscribers:
            delivery_tasks = []
            for callback in self.subscribers[topic]:
                delivery_tasks.append(asyncio.create_task(callback(message)))
            
            # Wait for all deliveries to complete
            if delivery_tasks:
                await asyncio.gather(*delivery_tasks)
    
    def subscribe(self, topic: str, callback: Callable[[AppletMessage], Awaitable[None]]) -> None:
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Async callback function to invoke when a message is published
        """
        logger.info(f"Subscribing to topic: {topic}")
        
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[AppletMessage], Awaitable[None]]) -> None:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            callback: Callback function to remove
        """
        logger.info(f"Unsubscribing from topic: {topic}")
        
        if topic in self.subscribers:
            self.subscribers[topic] = [cb for cb in self.subscribers[topic] if cb != callback]
            
            # Clean up empty subscriber lists
            if not self.subscribers[topic]:
                del self.subscribers[topic]
    
    def get_message_history(self, topic: str, limit: int = 100) -> List[AppletMessage]:
        """
        Get message history for a topic.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            
        Returns:
            List of messages, most recent first
        """
        if topic not in self.message_history:
            return []
        
        # Return most recent messages first
        return list(reversed(self.message_history[topic][-limit:]))
    
    def clear_history(self, topic: Optional[str] = None) -> None:
        """
        Clear message history.
        
        Args:
            topic: Topic to clear history for. If None, clear all history.
        """
        if topic:
            logger.info(f"Clearing message history for topic: {topic}")
            if topic in self.message_history:
                self.message_history[topic] = []
        else:
            logger.info("Clearing all message history")
            self.message_history = {}

class AgentCommunicator:
    """
    Handles communication between agents and the orchestrator.
    """
    
    def __init__(self, message_bus: MessageBus):
        """
        Initialize the agent communicator.
        
        Args:
            message_bus: Message bus to use for communication
        """
        self.message_bus = message_bus
        logger.info("Agent communicator initialized")
    
    async def send_to_agent(self, agent_id: str, message: AppletMessage) -> None:
        """
        Send a message to an agent.
        
        Args:
            agent_id: ID of the agent to send to
            message: Message to send
        """
        topic = f"agent.{agent_id}"
        await self.message_bus.publish(topic, message)
    
    async def send_to_workflow(self, workflow_id: str, message: AppletMessage) -> None:
        """
        Send a message to all agents in a workflow.
        
        Args:
            workflow_id: ID of the workflow
            message: Message to send
        """
        topic = f"workflow.{workflow_id}"
        await self.message_bus.publish(topic, message)
    
    async def broadcast(self, message: AppletMessage) -> None:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
        """
        topic = "broadcast"
        await self.message_bus.publish(topic, message)
    
    def register_agent_handler(
        self, 
        agent_id: str, 
        handler: Callable[[AppletMessage], Awaitable[None]]
    ) -> None:
        """
        Register a handler for messages sent to an agent.
        
        Args:
            agent_id: ID of the agent
            handler: Async handler function to invoke when a message is received
        """
        topic = f"agent.{agent_id}"
        self.message_bus.subscribe(topic, handler)
    
    def register_workflow_handler(
        self, 
        workflow_id: str, 
        handler: Callable[[AppletMessage], Awaitable[None]]
    ) -> None:
        """
        Register a handler for messages sent to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            handler: Async handler function to invoke when a message is received
        """
        topic = f"workflow.{workflow_id}"
        self.message_bus.subscribe(topic, handler)
    
    def register_broadcast_handler(
        self, 
        handler: Callable[[AppletMessage], Awaitable[None]]
    ) -> None:
        """
        Register a handler for broadcast messages.
        
        Args:
            handler: Async handler function to invoke when a message is received
        """
        topic = "broadcast"
        self.message_bus.subscribe(topic, handler)
    
    def get_agent_messages(self, agent_id: str, limit: int = 100) -> List[AppletMessage]:
        """
        Get message history for an agent.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            
        Returns:
            List of messages, most recent first
        """
        topic = f"agent.{agent_id}"
        return self.message_bus.get_message_history(topic, limit)
    
    def get_workflow_messages(self, workflow_id: str, limit: int = 100) -> List[AppletMessage]:
        """
        Get message history for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of messages to return
            
        Returns:
            List of messages, most recent first
        """
        topic = f"workflow.{workflow_id}"
        return self.message_bus.get_message_history(topic, limit)
