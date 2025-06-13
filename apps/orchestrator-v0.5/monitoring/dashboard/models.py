"""
Models for the real-time monitoring dashboard.

Defines data structures for tracking agent states, message flows,
and other metrics for visualization in the dashboard UI.
"""

from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class AgentState(str, Enum):
    """
    Possible states of an agent in a workflow.
    """
    IDLE = "idle"               # Agent is idle
    INITIALIZING = "initializing"  # Agent is initializing
    PROCESSING = "processing"    # Agent is processing a request
    WAITING = "waiting"         # Agent is waiting for input
    COMPLETED = "completed"     # Agent has completed its task
    FAILED = "failed"           # Agent has failed
    RETRYING = "retrying"       # Agent is retrying after failure
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker is open for this agent

class MessageDirection(str, Enum):
    """
    Direction of a message flow.
    """
    INCOMING = "incoming"       # Message coming into an agent
    OUTGOING = "outgoing"       # Message going out from an agent
    INTERNAL = "internal"       # Message internal to the orchestrator

class MessageStatus(str, Enum):
    """
    Status of a message in the system.
    """
    CREATED = "created"         # Message has been created
    QUEUED = "queued"           # Message is queued for delivery
    DELIVERED = "delivered"     # Message has been delivered
    PROCESSED = "processed"     # Message has been processed
    FAILED = "failed"           # Message processing failed
    RETRYING = "retrying"       # Message is being retried

class AgentMetrics(BaseModel):
    """
    Metrics for an agent in a workflow.
    """
    total_messages: int = Field(default=0, description="Total messages processed")
    successful_messages: int = Field(default=0, description="Successfully processed messages")
    failed_messages: int = Field(default=0, description="Failed messages")
    retry_count: int = Field(default=0, description="Number of retries")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time in ms")
    last_processing_time_ms: float = Field(default=0.0, description="Last processing time in ms")
    error_rate: float = Field(default=0.0, description="Error rate (0.0-1.0)")

class AgentStatusModel(BaseModel):
    """
    Status of an agent in a workflow.
    """
    agent_id: str = Field(description="ID of the agent")
    node_id: str = Field(description="ID of the node in the workflow")
    workflow_id: str = Field(description="ID of the workflow")
    state: AgentState = Field(description="Current state of the agent")
    current_message_id: Optional[str] = Field(None, description="ID of the message being processed")
    last_update: datetime = Field(description="Timestamp of the last status update")
    metrics: AgentMetrics = Field(default_factory=AgentMetrics, description="Agent metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class MessageFlowModel(BaseModel):
    """
    Represents a message flow between agents or components.
    """
    message_id: str = Field(description="ID of the message")
    workflow_id: str = Field(description="ID of the workflow")
    source_id: str = Field(description="ID of the source (agent or component)")
    target_id: str = Field(description="ID of the target (agent or component)")
    direction: MessageDirection = Field(description="Direction of the message flow")
    status: MessageStatus = Field(description="Status of the message")
    timestamp: datetime = Field(description="Timestamp when the flow was recorded")
    content_type: str = Field(description="Type of content in the message")
    content_size: int = Field(description="Size of the message content in bytes")
    duration_ms: Optional[float] = Field(None, description="Duration of the message processing in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class WorkflowMetrics(BaseModel):
    """
    Metrics for a workflow execution.
    """
    total_nodes: int = Field(default=0, description="Total number of nodes in the workflow")
    completed_nodes: int = Field(default=0, description="Number of completed nodes")
    failed_nodes: int = Field(default=0, description="Number of failed nodes")
    total_messages: int = Field(default=0, description="Total number of messages")
    total_retries: int = Field(default=0, description="Total number of retries")
    start_time: Optional[datetime] = Field(None, description="Start time of the workflow execution")
    end_time: Optional[datetime] = Field(None, description="End time of the workflow execution")
    duration_ms: Optional[float] = Field(None, description="Duration of the workflow execution in ms")
    error_rate: float = Field(default=0.0, description="Error rate (0.0-1.0)")

class WorkflowStatusModel(BaseModel):
    """
    Status of a workflow execution.
    """
    workflow_id: str = Field(description="ID of the workflow")
    workflow_name: str = Field(description="Name of the workflow")
    status: str = Field(description="Current status of the workflow")
    current_node_ids: List[str] = Field(default_factory=list, description="IDs of currently active nodes")
    completed_node_ids: List[str] = Field(default_factory=list, description="IDs of completed nodes")
    failed_node_ids: List[str] = Field(default_factory=list, description="IDs of failed nodes")
    metrics: WorkflowMetrics = Field(default_factory=WorkflowMetrics, description="Workflow metrics")
    last_update: datetime = Field(description="Timestamp of the last status update")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class DashboardUpdateModel(BaseModel):
    """
    Update for the real-time dashboard.
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the update")
    agent_updates: List[AgentStatusModel] = Field(default_factory=list, description="Agent status updates")
    message_flows: List[MessageFlowModel] = Field(default_factory=list, description="Message flow updates")
    workflow_updates: List[WorkflowStatusModel] = Field(default_factory=list, description="Workflow status updates")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System-wide metrics")
