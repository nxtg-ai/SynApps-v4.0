"""
Agent-to-Agent Messaging System

Enables direct communication between agents in a workflow, allowing them to
exchange information without going through the central orchestrator.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
import uuid

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode

logger = logging.getLogger("communication.agent_messaging")

class AgentMessage:
    """
    Message exchanged directly between agents.
    """
    def __init__(
        self,
        message_id: str,
        source_id: str,
        target_id: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an agent message.
        
        Args:
            message_id: Unique identifier for the message
            source_id: ID of the source agent/node
            target_id: ID of the target agent/node
            content: Message content
            metadata: Additional metadata
        """
        self.message_id = message_id
        self.source_id = source_id
        self.target_id = target_id
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = asyncio.get_event_loop().time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "message_id": self.message_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create from dictionary representation"""
        message = cls(
            message_id=data["message_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            content=data["content"],
            metadata=data["metadata"]
        )
        message.timestamp = data.get("timestamp", asyncio.get_event_loop().time())
        return message
    
    @classmethod
    def from_applet_message(
        cls,
        source_id: str,
        target_id: str,
        applet_message: AppletMessage,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'AgentMessage':
        """Create from an AppletMessage"""
        combined_metadata = dict(applet_message.metadata) if applet_message.metadata else {}
        if metadata:
            combined_metadata.update(metadata)
        
        return cls(
            message_id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            content=applet_message.content,
            metadata=combined_metadata
        )

class AgentMessagingSystem:
    """
    System for direct agent-to-agent messaging.
    """
    def __init__(self):
        """Initialize the agent messaging system"""
        # Dictionary of message queues for each agent
        # agent_id -> List[AgentMessage]
        self.message_queues: Dict[str, List[AgentMessage]] = {}
        
        # Dictionary of message handlers for each agent
        # agent_id -> Callable
        self.message_handlers: Dict[str, Callable[[AgentMessage], Awaitable[None]]] = {}
        
        # Dictionary of subscriptions
        # topic -> List[agent_id]
        self.subscriptions: Dict[str, List[str]] = {}
        
        logger.info("AgentMessagingSystem initialized")
    
    def register_agent(self, agent_id: str) -> None:
        """
        Register an agent with the messaging system.
        
        Args:
            agent_id: ID of the agent to register
        """
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = []
            logger.info(f"Registered agent {agent_id} with messaging system")
    
    def register_message_handler(
        self,
        agent_id: str,
        handler: Callable[[AgentMessage], Awaitable[None]]
    ) -> None:
        """
        Register a message handler for an agent.
        
        Args:
            agent_id: ID of the agent
            handler: Async function to handle incoming messages
        """
        self.message_handlers[agent_id] = handler
        logger.info(f"Registered message handler for agent {agent_id}")
    
    def subscribe_to_topic(self, agent_id: str, topic: str) -> None:
        """
        Subscribe an agent to a topic.
        
        Args:
            agent_id: ID of the agent
            topic: Topic to subscribe to
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        
        if agent_id not in self.subscriptions[topic]:
            self.subscriptions[topic].append(agent_id)
            logger.info(f"Agent {agent_id} subscribed to topic {topic}")
    
    def unsubscribe_from_topic(self, agent_id: str, topic: str) -> None:
        """
        Unsubscribe an agent from a topic.
        
        Args:
            agent_id: ID of the agent
            topic: Topic to unsubscribe from
        """
        if topic in self.subscriptions and agent_id in self.subscriptions[topic]:
            self.subscriptions[topic].remove(agent_id)
            logger.info(f"Agent {agent_id} unsubscribed from topic {topic}")
    
    async def send_message(
        self,
        source_id: str,
        target_id: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send a message from one agent to another.
        
        Args:
            source_id: ID of the source agent
            target_id: ID of the target agent
            content: Message content
            metadata: Additional metadata
            
        Returns:
            ID of the sent message
        """
        # Create the message
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            content=content,
            metadata=metadata
        )
        
        # Add to target agent's queue
        if target_id not in self.message_queues:
            self.register_agent(target_id)
        
        self.message_queues[target_id].append(message)
        
        # Notify handler if registered
        if target_id in self.message_handlers:
            try:
                await self.message_handlers[target_id](message)
            except Exception as e:
                logger.error(f"Error in message handler for agent {target_id}: {e}")
        
        logger.info(f"Message {message.message_id} sent from {source_id} to {target_id}")
        return message.message_id
    
    async def publish_to_topic(
        self,
        source_id: str,
        topic: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Publish a message to a topic.
        
        Args:
            source_id: ID of the source agent
            topic: Topic to publish to
            content: Message content
            metadata: Additional metadata
            
        Returns:
            List of message IDs sent
        """
        message_ids = []
        
        # Add topic to metadata
        combined_metadata = metadata or {}
        combined_metadata["topic"] = topic
        
        # Send to all subscribers
        if topic in self.subscriptions:
            for target_id in self.subscriptions[topic]:
                if target_id != source_id:  # Don't send to self
                    message_id = await self.send_message(
                        source_id=source_id,
                        target_id=target_id,
                        content=content,
                        metadata=combined_metadata
                    )
                    message_ids.append(message_id)
        
        return message_ids
    
    def get_messages(self, agent_id: str) -> List[AgentMessage]:
        """
        Get all messages for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of messages
        """
        return self.message_queues.get(agent_id, [])
    
    def get_and_clear_messages(self, agent_id: str) -> List[AgentMessage]:
        """
        Get and clear all messages for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of messages
        """
        messages = self.get_messages(agent_id)
        self.message_queues[agent_id] = []
        return messages
    
    def clear_messages(self, agent_id: str) -> None:
        """
        Clear all messages for an agent.
        
        Args:
            agent_id: ID of the agent
        """
        self.message_queues[agent_id] = []
        logger.info(f"Cleared messages for agent {agent_id}")
    
    def get_message_count(self, agent_id: str) -> int:
        """
        Get the number of messages for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Number of messages
        """
        return len(self.message_queues.get(agent_id, []))
    
    def get_all_agents(self) -> List[str]:
        """
        Get all registered agents.
        
        Returns:
            List of agent IDs
        """
        return list(self.message_queues.keys())
