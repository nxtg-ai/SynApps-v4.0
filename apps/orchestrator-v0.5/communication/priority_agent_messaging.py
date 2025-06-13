"""
Priority-based agent communication for the Meta-Agent Orchestrator
Extends the base agent communicator with priority support
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.messaging import AgentCommunicator
from communication.priority_messaging import PriorityMessageBus

logger = logging.getLogger("communication.priority_agent_messaging")

class PriorityAgentCommunicator(AgentCommunicator):
    """
    Enhanced agent communicator with priority support.
    Extends the standard AgentCommunicator with priority-based message handling.
    """
    
    def __init__(self, message_bus: PriorityMessageBus):
        """
        Initialize the priority agent communicator.
        
        Args:
            message_bus: Priority message bus to use for communication
        """
        super().__init__(message_bus)
        self.priority_message_bus = message_bus  # Typed reference for priority-specific methods
        logger.info("Priority agent communicator initialized")
    
    async def send_to_agent_with_priority(
        self, 
        agent_id: str, 
        message: AppletMessage,
        priority: int = 5
    ) -> None:
        """
        Send a message to an agent with specified priority.
        
        Args:
            agent_id: ID of the agent to send to
            message: Message to send
            priority: Priority level (0-10, where 10 is highest)
        """
        topic = f"agent.{agent_id}"
        await self.priority_message_bus.publish_with_priority(topic, message, priority)
    
    async def send_to_workflow_with_priority(
        self, 
        workflow_id: str, 
        message: AppletMessage,
        priority: int = 5
    ) -> None:
        """
        Send a message to all agents in a workflow with specified priority.
        
        Args:
            workflow_id: ID of the workflow
            message: Message to send
            priority: Priority level (0-10, where 10 is highest)
        """
        topic = f"workflow.{workflow_id}"
        await self.priority_message_bus.publish_with_priority(topic, message, priority)
    
    async def broadcast_with_priority(
        self, 
        message: AppletMessage,
        priority: int = 5
    ) -> None:
        """
        Broadcast a message to all agents with specified priority.
        
        Args:
            message: Message to broadcast
            priority: Priority level (0-10, where 10 is highest)
        """
        topic = "broadcast"
        await self.priority_message_bus.publish_with_priority(topic, message, priority)
    
    async def send_critical_to_agent(self, agent_id: str, message: AppletMessage) -> None:
        """
        Send a critical message to an agent (priority 10).
        
        Args:
            agent_id: ID of the agent to send to
            message: Message to send
        """
        await self.send_to_agent_with_priority(agent_id, message, 10)
    
    async def send_critical_to_workflow(self, workflow_id: str, message: AppletMessage) -> None:
        """
        Send a critical message to all agents in a workflow (priority 10).
        
        Args:
            workflow_id: ID of the workflow
            message: Message to send
        """
        await self.send_to_workflow_with_priority(workflow_id, message, 10)
    
    async def broadcast_critical(self, message: AppletMessage) -> None:
        """
        Broadcast a critical message to all agents (priority 10).
        
        Args:
            message: Message to broadcast
        """
        await self.broadcast_with_priority(message, 10)
    
    def get_agent_messages_by_priority(
        self, 
        agent_id: str, 
        limit: int = 100,
        min_priority: int = 0
    ) -> List[AppletMessage]:
        """
        Get message history for an agent filtered by priority.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include (0-10)
            
        Returns:
            List of messages, most recent first
        """
        topic = f"agent.{agent_id}"
        return self.priority_message_bus.get_message_history(topic, limit, min_priority)
    
    def get_workflow_messages_by_priority(
        self, 
        workflow_id: str, 
        limit: int = 100,
        min_priority: int = 0
    ) -> List[AppletMessage]:
        """
        Get message history for a workflow filtered by priority.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include (0-10)
            
        Returns:
            List of messages, most recent first
        """
        topic = f"workflow.{workflow_id}"
        return self.priority_message_bus.get_message_history(topic, limit, min_priority)
    
    def get_critical_agent_messages(self, agent_id: str, limit: int = 100) -> List[AppletMessage]:
        """
        Get critical message history for an agent (priority >= 8).
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            
        Returns:
            List of critical messages, most recent first
        """
        return self.get_agent_messages_by_priority(agent_id, limit, 8)
    
    def get_critical_workflow_messages(self, workflow_id: str, limit: int = 100) -> List[AppletMessage]:
        """
        Get critical message history for a workflow (priority >= 8).
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of messages to return
            
        Returns:
            List of critical messages, most recent first
        """
        return self.get_workflow_messages_by_priority(workflow_id, limit, 8)
