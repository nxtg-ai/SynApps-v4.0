"""
Database models for message persistence
"""

from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.base import Base

class MessageModel(Base):
    """
    Database model for persisting agent messages.
    """
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, index=True)
    topic = Column(String(255), index=True, nullable=False)
    content = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    priority = Column(Integer, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), index=True, nullable=True)
    workflow = relationship("WorkflowModel", back_populates="messages")
    
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=True)
    agent = relationship("AgentModel", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, topic={self.topic}, priority={self.priority})>"
