"""
Database and API models for the SynApps orchestrator.

This module defines SQLAlchemy ORM models for database persistence
and Pydantic models for API validation.
"""
from typing import Dict, List, Any, Optional
import time
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

# SQLAlchemy Base
Base = declarative_base()

# SQLAlchemy ORM Models
class Flow(Base):
    """ORM model for workflow flows."""
    __tablename__ = "flows"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    
    # Relationships
    nodes = relationship("FlowNode", back_populates="flow", cascade="all, delete-orphan")
    edges = relationship("FlowEdge", back_populates="flow", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges]
        }


class FlowNode(Base):
    """ORM model for workflow nodes."""
    __tablename__ = "flow_nodes"
    
    id = Column(String, primary_key=True)
    flow_id = Column(String, ForeignKey("flows.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    data = Column(JSON, nullable=True)
    
    # Relationships
    flow = relationship("Flow", back_populates="nodes")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "position": {
                "x": self.position_x,
                "y": self.position_y
            },
            "data": self.data or {}
        }


class FlowEdge(Base):
    """ORM model for workflow edges."""
    __tablename__ = "flow_edges"
    
    id = Column(String, primary_key=True)
    flow_id = Column(String, ForeignKey("flows.id", ondelete="CASCADE"), nullable=False)
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)
    animated = Column(Boolean, default=False)
    
    # Relationships
    flow = relationship("Flow", back_populates="edges")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "animated": self.animated
        }


class WorkflowRun(Base):
    """ORM model for workflow runs."""
    __tablename__ = "workflow_runs"
    
    id = Column(String, primary_key=True)
    flow_id = Column(String, ForeignKey("flows.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="idle")
    current_applet = Column(String, nullable=True)
    completed_applets = Column(JSON, nullable=True)  # Store list of completed node IDs
    progress = Column(Integer, nullable=False, default=0)
    total_steps = Column(Integer, nullable=False, default=0)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=True)
    results = Column(JSON, nullable=True)
    input_data = Column(JSON, nullable=True)  # Store the initial input data
    error = Column(String, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "run_id": self.id,
            "flow_id": self.flow_id,
            "status": self.status,
            "current_applet": self.current_applet,
            "completed_applets": self.completed_applets or [],
            "progress": self.progress,
            "total_steps": self.total_steps,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": self.results or {},
            "input_data": self.input_data or {},
            "error": self.error
        }


# Pydantic API Models
class FlowNodeModel(BaseModel):
    """API model for flow nodes."""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any] = Field(default_factory=dict)


class FlowEdgeModel(BaseModel):
    """API model for flow edges."""
    id: str
    source: str
    target: str
    animated: bool = False


class FlowModel(BaseModel):
    """API model for flows."""
    id: str
    name: str
    nodes: List[FlowNodeModel] = Field(default_factory=list)
    edges: List[FlowEdgeModel] = Field(default_factory=list)


class WorkflowRunStatusModel(BaseModel):
    """API model for workflow run status."""
    run_id: str
    flow_id: str
    status: str = "idle"
    current_applet: Optional[str] = None
    completed_applets: List[str] = Field(default_factory=list)  # List of completed node IDs
    progress: int = 0
    total_steps: int = 0
    start_time: float = Field(default_factory=lambda: time.time())
    end_time: Optional[float] = None
    results: Dict[str, Any] = Field(default_factory=dict)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Override dict method to provide a consistent output."""
        result = super().dict(*args, **kwargs)
        # Ensure results and input_data are never None
        if result.get("results") is None:
            result["results"] = {}
        if result.get("input_data") is None:
            result["input_data"] = {}
        return result
