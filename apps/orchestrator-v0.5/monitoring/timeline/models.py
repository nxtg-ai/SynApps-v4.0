"""
Models for workflow execution timeline visualization and playback.

Defines data structures for tracking and visualizing the execution timeline
of workflows, including events, agent interactions, and message flows.
"""

from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class TimelineEventType(str, Enum):
    """
    Types of events that can occur in a workflow execution timeline.
    """
    WORKFLOW_START = "workflow_start"       # Workflow execution started
    WORKFLOW_COMPLETE = "workflow_complete"  # Workflow execution completed
    WORKFLOW_FAILED = "workflow_failed"      # Workflow execution failed
    NODE_START = "node_start"               # Node execution started
    NODE_COMPLETE = "node_complete"         # Node execution completed
    NODE_FAILED = "node_failed"             # Node execution failed
    MESSAGE_SENT = "message_sent"           # Message sent between nodes
    MESSAGE_RECEIVED = "message_received"   # Message received by a node
    AGENT_STATE_CHANGE = "agent_state_change"  # Agent state changed
    RULE_APPLIED = "rule_applied"           # Governance rule applied
    ERROR_OCCURRED = "error_occurred"       # Error occurred
    RETRY_ATTEMPT = "retry_attempt"         # Retry attempted
    FALLBACK_TRIGGERED = "fallback_triggered"  # Fallback strategy triggered
    CIRCUIT_BREAKER_CHANGE = "circuit_breaker_change"  # Circuit breaker state changed
    CUSTOM_EVENT = "custom_event"           # Custom event

class TimelineEvent(BaseModel):
    """
    Represents an event in a workflow execution timeline.
    """
    event_id: str = Field(description="Unique identifier for the event")
    workflow_id: str = Field(description="ID of the workflow")
    event_type: TimelineEventType = Field(description="Type of event")
    timestamp: datetime = Field(description="When the event occurred")
    node_id: Optional[str] = Field(None, description="ID of the node involved (if applicable)")
    message_id: Optional[str] = Field(None, description="ID of the message involved (if applicable)")
    agent_id: Optional[str] = Field(None, description="ID of the agent involved (if applicable)")
    duration_ms: Optional[float] = Field(None, description="Duration of the event in milliseconds (if applicable)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details about the event")
    related_event_ids: List[str] = Field(default_factory=list, description="IDs of related events")

class TimelineSegment(BaseModel):
    """
    A segment of a workflow execution timeline.
    """
    workflow_id: str = Field(description="ID of the workflow")
    start_time: datetime = Field(description="Start time of the segment")
    end_time: datetime = Field(description="End time of the segment")
    events: List[TimelineEvent] = Field(description="Events in the segment")
    
    class Config:
        arbitrary_types_allowed = True

class ExecutionTimeline(BaseModel):
    """
    Complete execution timeline for a workflow.
    """
    workflow_id: str = Field(description="ID of the workflow")
    workflow_name: str = Field(description="Name of the workflow")
    start_time: datetime = Field(description="Start time of the workflow execution")
    end_time: Optional[datetime] = Field(None, description="End time of the workflow execution")
    duration_ms: Optional[float] = Field(None, description="Duration of the workflow execution in milliseconds")
    status: str = Field(description="Current status of the workflow execution")
    events: List[TimelineEvent] = Field(default_factory=list, description="Events in the timeline")
    node_durations: Dict[str, float] = Field(default_factory=dict, description="Duration of each node execution in milliseconds")
    node_start_times: Dict[str, datetime] = Field(default_factory=dict, description="Start time of each node execution")
    message_flows: List[Dict[str, Any]] = Field(default_factory=list, description="Message flows between nodes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True

class TimelinePlaybackState(str, Enum):
    """
    States for timeline playback.
    """
    STOPPED = "stopped"     # Playback is stopped
    PLAYING = "playing"     # Playback is playing
    PAUSED = "paused"       # Playback is paused
    SEEKING = "seeking"     # Playback is seeking to a specific time

class TimelinePlaybackControl(BaseModel):
    """
    Control for timeline playback.
    """
    workflow_id: str = Field(description="ID of the workflow")
    state: TimelinePlaybackState = Field(description="Current playback state")
    current_time: datetime = Field(description="Current playback time")
    playback_speed: float = Field(1.0, description="Playback speed multiplier")
    loop: bool = Field(False, description="Whether to loop playback")
    start_time: Optional[datetime] = Field(None, description="Start time for playback range")
    end_time: Optional[datetime] = Field(None, description="End time for playback range")
    
    class Config:
        arbitrary_types_allowed = True

class TimelinePlaybackUpdate(BaseModel):
    """
    Update for timeline playback.
    """
    workflow_id: str = Field(description="ID of the workflow")
    current_time: datetime = Field(description="Current playback time")
    current_events: List[TimelineEvent] = Field(default_factory=list, description="Events at the current time")
    active_nodes: List[str] = Field(default_factory=list, description="Currently active nodes")
    active_messages: List[str] = Field(default_factory=list, description="Currently active messages")
    progress_percentage: float = Field(0.0, description="Playback progress percentage (0-100)")
    
    class Config:
        arbitrary_types_allowed = True
