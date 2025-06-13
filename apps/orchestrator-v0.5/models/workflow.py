"""
Workflow models for the Meta-Agent Orchestrator
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4
from datetime import datetime

class WorkflowEdge(BaseModel):
    """
    Represents a connection between two nodes in a workflow.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str = Field(description="ID of the source node")
    target: str = Field(description="ID of the target node")
    condition: Optional[str] = Field(
        default=None, 
        description="Optional condition for edge traversal"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowNode(BaseModel):
    """
    Represents a node in a workflow, which can be an agent, a start node,
    an end node, or a decision node.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(description="Display name of the node")
    type: str = Field(description="Type of node (agent, start, end, decision)")
    applet_id: Optional[str] = Field(
        default=None,
        description="ID of the associated applet, if this is an agent node"
    )
    position: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0, "y": 0},
        description="Position of the node in the workflow canvas"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-specific configuration"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('type')
    def validate_node_type(cls, v):
        """Validate that the node type is one of the allowed values"""
        allowed_types = ['start', 'end', 'agent', 'decision', 'fork', 'join']
        if v not in allowed_types:
            raise ValueError(f"Node type must be one of: {', '.join(allowed_types)}")
        return v

class Workflow(BaseModel):
    """
    Represents a complete workflow with nodes and edges.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(description="Name of the workflow")
    description: Optional[str] = Field(default=None)
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_node(self, node: WorkflowNode) -> WorkflowNode:
        """Add a node to the workflow"""
        self.nodes.append(node)
        self.updated_at = datetime.utcnow()
        return node
    
    def add_edge(self, edge: WorkflowEdge) -> WorkflowEdge:
        """Add an edge to the workflow"""
        self.edges.append(edge)
        self.updated_at = datetime.utcnow()
        return edge
    
    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by its ID"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges that originate from the specified node"""
        return [edge for edge in self.edges if edge.source == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges that target the specified node"""
        return [edge for edge in self.edges if edge.target == node_id]

class WorkflowRunStatus(BaseModel):
    """
    Represents the status of a workflow run.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str = Field(description="ID of the workflow being run")
    status: Literal["pending", "running", "completed", "failed", "canceled"] = Field(
        default="pending"
    )
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    completed_nodes: List[str] = Field(
        default_factory=list,
        description="IDs of nodes that have completed execution"
    )
    current_nodes: List[str] = Field(
        default_factory=list,
        description="IDs of nodes currently executing"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Errors encountered during workflow execution"
    )
    results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results of workflow execution"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics collected during workflow execution"
    )
    
    def mark_node_completed(self, node_id: str) -> None:
        """Mark a node as completed"""
        if node_id in self.current_nodes:
            self.current_nodes.remove(node_id)
        if node_id not in self.completed_nodes:
            self.completed_nodes.append(node_id)
    
    def mark_node_started(self, node_id: str) -> None:
        """Mark a node as currently executing"""
        if node_id not in self.current_nodes:
            self.current_nodes.append(node_id)
    
    def add_error(self, node_id: str, error_type: str, error_message: str, details: Dict[str, Any] = None) -> None:
        """Add an error to the workflow run"""
        self.errors.append({
            "node_id": node_id,
            "error_type": error_type,
            "error_message": error_message,
            "details": details or {},
            "timestamp": datetime.utcnow()
        })
        
    def is_complete(self) -> bool:
        """Check if the workflow run is complete"""
        return self.status in ["completed", "failed", "canceled"]
