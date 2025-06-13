"""
Persistent agent communication for the Meta-Agent Orchestrator
Extends the priority agent communicator with database persistence
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.priority_agent_messaging import PriorityAgentCommunicator
from communication.persistent_messaging import PersistentMessageBus
from db.repository.message_repository import MessageRepository

logger = logging.getLogger("communication.persistent_agent_messaging")

class PersistentAgentCommunicator(PriorityAgentCommunicator):
    """
    Enhanced agent communicator with database persistence support.
    Extends the PriorityAgentCommunicator with database-backed message storage.
    """
    
    def __init__(self, message_bus: PersistentMessageBus):
        """
        Initialize the persistent agent communicator.
        
        Args:
            message_bus: Persistent message bus to use for communication
        """
        super().__init__(message_bus)
        self.persistent_message_bus = message_bus  # Typed reference for persistence-specific methods
        logger.info("Persistent agent communicator initialized")
    
    async def get_agent_message_history_from_db(
        self, 
        agent_id: str, 
        limit: int = 100,
        min_priority: int = 0
    ) -> List[AppletMessage]:
        """
        Get message history for an agent from the database.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        topic = f"agent.{agent_id}"
        return await self.persistent_message_bus.get_message_history_from_db(topic, limit, min_priority)
    
    async def get_workflow_message_history_from_db(
        self, 
        workflow_id: str, 
        limit: int = 100,
        min_priority: int = 0
    ) -> List[AppletMessage]:
        """
        Get message history for a workflow from the database.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        topic = f"workflow.{workflow_id}"
        return await self.persistent_message_bus.get_message_history_from_db(topic, limit, min_priority)
    
    async def get_broadcast_message_history_from_db(
        self, 
        limit: int = 100,
        min_priority: int = 0
    ) -> List[AppletMessage]:
        """
        Get broadcast message history from the database.
        
        Args:
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        return await self.persistent_message_bus.get_message_history_from_db("broadcast", limit, min_priority)
    
    async def clear_agent_message_history(self, agent_id: str) -> int:
        """
        Clear message history for an agent from both memory and database.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Number of messages deleted from database
        """
        topic = f"agent.{agent_id}"
        return await self.persistent_message_bus.clear_message_history(topic)
    
    async def clear_workflow_message_history(self, workflow_id: str) -> int:
        """
        Clear message history for a workflow from both memory and database.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Number of messages deleted from database
        """
        topic = f"workflow.{workflow_id}"
        return await self.persistent_message_bus.clear_message_history(topic)
    
    async def clear_all_message_history(self) -> int:
        """
        Clear all message history from both memory and database.
        
        Returns:
            Number of messages deleted from database
        """
        return await self.persistent_message_bus.clear_message_history(None)
    
    async def get_agent_conversation_history(
        self, 
        agent_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get a formatted conversation history for an agent from the database.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation entries with role and content
        """
        messages = await self.get_agent_message_history_from_db(agent_id, limit)
        
        # Format as conversation history
        conversation = []
        for message in messages:
            # Determine role based on metadata or context
            role = "assistant"
            if message.metadata.get("from_user", False):
                role = "user"
            elif message.metadata.get("from_system", False):
                role = "system"
            
            conversation.append({
                "role": role,
                "content": message.content
            })
        
        # Reverse to get chronological order (oldest first)
        return list(reversed(conversation))
