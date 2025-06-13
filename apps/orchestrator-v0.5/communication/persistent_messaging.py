"""
Persistent messaging system for the Meta-Agent Orchestrator
Extends the priority messaging system with database persistence
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.priority_messaging import PriorityMessageBus
from db.repository.message_repository import MessageRepository

logger = logging.getLogger("communication.persistent_messaging")

class PersistentMessageBus(PriorityMessageBus):
    """
    Enhanced message bus with database persistence support.
    Extends the PriorityMessageBus with database-backed message storage.
    """
    
    def __init__(self, repository: MessageRepository):
        """
        Initialize the persistent message bus.
        
        Args:
            repository: Message repository for database operations
        """
        super().__init__()
        self.repository = repository
        logger.info("Persistent message bus initialized")
    
    async def publish(self, topic: str, message: AppletMessage) -> None:
        """
        Publish a message to a topic with persistence.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        # First, persist the message to the database
        try:
            message_id = await self.repository.save_message(topic, message)
            # Add the database ID to the message metadata
            message.metadata["id"] = message_id
            logger.info(f"Message persisted to database with ID: {message_id}")
        except Exception as e:
            logger.error(f"Failed to persist message: {str(e)}")
            # Continue with in-memory processing even if persistence fails
        
        # Then, proceed with in-memory processing via the parent class
        await super().publish(topic, message)
    
    async def get_message_history_from_db(self, topic: str, limit: int = 100, 
                                        min_priority: int = 0) -> List[AppletMessage]:
        """
        Get message history for a topic from the database.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        try:
            return await self.repository.get_messages(topic, limit, min_priority)
        except Exception as e:
            logger.error(f"Failed to retrieve messages from database: {str(e)}")
            return []
    
    def get_message_history(self, topic: str, limit: int = 100, 
                          min_priority: int = 0) -> List[AppletMessage]:
        """
        Get message history for a topic from in-memory cache.
        For database history, use get_message_history_from_db.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        # Use the parent class implementation for in-memory history
        return super().get_message_history(topic, limit, min_priority)
    
    async def clear_message_history(self, topic: Optional[str] = None) -> int:
        """
        Clear message history for a topic or all topics from both memory and database.
        
        Args:
            topic: Topic to clear history for, or None for all topics
            
        Returns:
            Number of messages deleted from database
        """
        # Clear from memory
        if topic:
            if topic in self.message_history:
                del self.message_history[topic]
                logger.info(f"Cleared in-memory message history for topic: {topic}")
        else:
            self.message_history.clear()
            logger.info("Cleared all in-memory message history")
        
        # Clear from database
        try:
            deleted_count = await self.repository.delete_messages(topic)
            logger.info(f"Deleted {deleted_count} messages from database")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete messages from database: {str(e)}")
            return 0
