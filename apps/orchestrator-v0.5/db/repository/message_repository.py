"""
Repository for message persistence
"""

import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from db.models.message import MessageModel

logger = logging.getLogger("db.repository.message_repository")

class MessageRepository:
    """
    Repository for persisting and retrieving messages.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the message repository.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.info("Message repository initialized")
    
    async def save_message(self, topic: str, message: AppletMessage) -> str:
        """
        Save a message to the database.
        
        Args:
            topic: Message topic
            message: Message to save
            
        Returns:
            ID of the saved message
        """
        # Generate a unique ID if not present
        message_id = message.metadata.get("id", str(uuid.uuid4()))
        
        # Extract workflow_id and agent_id from context if available
        workflow_id = message.context.get("workflow_id")
        agent_id = message.context.get("agent_id") or message.context.get("node_id")
        
        # Determine priority
        priority = 5  # Default priority
        if isinstance(message, PriorityMessage):
            priority = message.priority
        
        # Create database model
        db_message = MessageModel(
            id=message_id,
            topic=topic,
            content=message.content,
            context=message.context,
            metadata=message.metadata,
            priority=priority,
            workflow_id=workflow_id,
            agent_id=agent_id,
            created_at=datetime.now()
        )
        
        # Save to database
        self.session.add(db_message)
        await self.session.commit()
        
        logger.info(f"Saved message {message_id} to topic {topic}")
        return message_id
    
    async def get_messages(self, topic: str, limit: int = 100, 
                          min_priority: int = 0) -> List[AppletMessage]:
        """
        Get messages for a topic.
        
        Args:
            topic: Topic to get messages for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        # Query database
        query = (
            select(MessageModel)
            .where(MessageModel.topic == topic)
            .where(MessageModel.priority >= min_priority)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        db_messages = result.scalars().all()
        
        # Convert to AppletMessage objects
        messages = []
        for db_message in db_messages:
            if db_message.priority > 0:  # Has explicit priority
                message = PriorityMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {},
                    priority=db_message.priority
                )
            else:
                message = AppletMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {}
                )
            
            # Add database ID to metadata
            message.metadata["id"] = db_message.id
            messages.append(message)
        
        logger.info(f"Retrieved {len(messages)} messages for topic {topic}")
        return messages
    
    async def get_agent_messages(self, agent_id: str, limit: int = 100,
                               min_priority: int = 0) -> List[AppletMessage]:
        """
        Get messages for an agent.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        # Query database
        query = (
            select(MessageModel)
            .where(MessageModel.agent_id == agent_id)
            .where(MessageModel.priority >= min_priority)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        db_messages = result.scalars().all()
        
        # Convert to AppletMessage objects
        messages = []
        for db_message in db_messages:
            if db_message.priority > 0:  # Has explicit priority
                message = PriorityMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {},
                    priority=db_message.priority
                )
            else:
                message = AppletMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {}
                )
            
            # Add database ID to metadata
            message.metadata["id"] = db_message.id
            messages.append(message)
        
        logger.info(f"Retrieved {len(messages)} messages for agent {agent_id}")
        return messages
    
    async def get_workflow_messages(self, workflow_id: str, limit: int = 100,
                                  min_priority: int = 0) -> List[AppletMessage]:
        """
        Get messages for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        # Query database
        query = (
            select(MessageModel)
            .where(MessageModel.workflow_id == workflow_id)
            .where(MessageModel.priority >= min_priority)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        db_messages = result.scalars().all()
        
        # Convert to AppletMessage objects
        messages = []
        for db_message in db_messages:
            if db_message.priority > 0:  # Has explicit priority
                message = PriorityMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {},
                    priority=db_message.priority
                )
            else:
                message = AppletMessage(
                    content=db_message.content,
                    context=db_message.context or {},
                    metadata=db_message.metadata or {}
                )
            
            # Add database ID to metadata
            message.metadata["id"] = db_message.id
            messages.append(message)
        
        logger.info(f"Retrieved {len(messages)} messages for workflow {workflow_id}")
        return messages
    
    async def delete_messages(self, topic: Optional[str] = None) -> int:
        """
        Delete messages for a topic or all messages if topic is None.
        
        Args:
            topic: Topic to delete messages for, or None for all
            
        Returns:
            Number of messages deleted
        """
        if topic:
            # Delete messages for a specific topic
            query = select(MessageModel).where(MessageModel.topic == topic)
            result = await self.session.execute(query)
            db_messages = result.scalars().all()
            
            for db_message in db_messages:
                await self.session.delete(db_message)
            
            count = len(db_messages)
        else:
            # Delete all messages
            query = select(MessageModel)
            result = await self.session.execute(query)
            db_messages = result.scalars().all()
            
            for db_message in db_messages:
                await self.session.delete(db_message)
            
            count = len(db_messages)
        
        await self.session.commit()
        logger.info(f"Deleted {count} messages")
        return count
