"""
Database models for the Meta-Agent Orchestrator
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class WorkflowModel(Base):
    """
    Database model for a workflow.
    """
    __tablename__ = "workflows"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    
    # Relationships
    nodes = relationship("WorkflowNodeModel", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdgeModel", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship("WorkflowRunModel", back_populates="workflow")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges]
        }

class WorkflowNodeModel(Base):
    """
    Database model for a workflow node.
    """
    __tablename__ = "workflow_nodes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    applet_id = Column(String(36), nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    config = Column(JSON, default=dict)
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="nodes")
    source_edges = relationship("WorkflowEdgeModel", foreign_keys="WorkflowEdgeModel.source_id", back_populates="source_node")
    target_edges = relationship("WorkflowEdgeModel", foreign_keys="WorkflowEdgeModel.target_id", back_populates="target_node")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "name": self.name,
            "type": self.type,
            "applet_id": self.applet_id,
            "position": {
                "x": self.position_x,
                "y": self.position_y
            },
            "config": self.config
        }

class WorkflowEdgeModel(Base):
    """
    Database model for a workflow edge.
    """
    __tablename__ = "workflow_edges"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    source_id = Column(String(36), ForeignKey("workflow_nodes.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("workflow_nodes.id"), nullable=False)
    condition = Column(JSON, nullable=True)
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="edges")
    source_node = relationship("WorkflowNodeModel", foreign_keys=[source_id], back_populates="source_edges")
    target_node = relationship("WorkflowNodeModel", foreign_keys=[target_id], back_populates="target_edges")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "source": self.source_id,
            "target": self.target_id,
            "condition": self.condition
        }

class WorkflowRunModel(Base):
    """
    Database model for a workflow run.
    """
    __tablename__ = "workflow_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    metrics = Column(JSON, default=dict)
    completed_applets = Column(JSON, default=list)  # List of completed applet IDs for visual feedback
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="runs")
    node_runs = relationship("NodeRunModel", back_populates="workflow_run", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metrics": self.metrics,
            "completed_applets": self.completed_applets
        }

class NodeRunModel(Base):
    """
    Database model for a node run.
    """
    __tablename__ = "node_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False)
    node_id = Column(String(36), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    metrics = Column(JSON, default=dict)
    
    # Relationships
    workflow_run = relationship("WorkflowRunModel", back_populates="node_runs")
    messages = relationship("MessageModel", back_populates="node_run", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "workflow_run_id": self.workflow_run_id,
            "node_id": self.node_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metrics": self.metrics
        }

class MessageModel(Base):
    """
    Database model for agent messages.
    """
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_run_id = Column(String(36), ForeignKey("node_runs.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # "input" or "output"
    content = Column(Text, nullable=False)
    context = Column(JSON, default=dict)
    meta_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy reserved name conflict
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    node_run = relationship("NodeRunModel", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "node_run_id": self.node_run_id,
            "direction": self.direction,
            "content": self.content,
            "context": self.context,
            "metadata": self.meta_data,  # Return as metadata in the dict for API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ValidationResultModel(Base):
    """
    Database model for validation results.
    """
    __tablename__ = "validation_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False)
    is_valid = Column(Boolean, nullable=False)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("MessageModel")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class RuleResultModel(Base):
    """
    Database model for rule application results.
    """
    __tablename__ = "rule_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False)
    rule_id = Column(String(50), nullable=False)
    passed = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSON, default=dict)  # Renamed from metadata to avoid SQLAlchemy reserved name conflict
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("MessageModel")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "rule_id": self.rule_id,
            "passed": self.passed,
            "message": self.message,
            "metadata": self.meta_data,  # Return as metadata in the dict for API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
