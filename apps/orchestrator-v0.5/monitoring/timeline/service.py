"""
Timeline Service for the Meta-Agent Orchestrator

Manages the execution timeline visualization and playback functionality.
Tracks and records events during workflow execution for later analysis and replay.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from datetime import datetime, timedelta
import json
from collections import deque

from monitoring.timeline.models import (
    TimelineEventType, TimelineEvent, TimelineSegment, ExecutionTimeline,
    TimelinePlaybackState, TimelinePlaybackControl, TimelinePlaybackUpdate
)
from models.workflow import WorkflowNode, Workflow
from models.agent_message import AppletMessage
from communication.websocket import WebSocketManager

logger = logging.getLogger("monitoring.timeline.service")

class TimelineService:
    """
    Service for managing workflow execution timelines.
    """
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        """
        Initialize the timeline service.
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        # WebSocket manager for pushing updates
        self.websocket_manager = websocket_manager
        
        # Active timelines by workflow ID
        self.active_timelines: Dict[str, ExecutionTimeline] = {}
        
        # Completed timelines by workflow ID
        self.completed_timelines: Dict[str, ExecutionTimeline] = {}
        
        # Active playback controls by workflow ID
        self.playback_controls: Dict[str, TimelinePlaybackControl] = {}
        
        # Event listeners
        self.event_listeners: List[Callable[[TimelineEvent], Awaitable[None]]] = []
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        
        logger.info("TimelineService initialized")
    
    async def start(self) -> None:
        """Start the timeline service"""
        # No background tasks to start yet
        logger.info("TimelineService started")
    
    async def register_event_listener(
        self,
        listener: Callable[[TimelineEvent], Awaitable[None]]
    ) -> None:
        """
        Register a listener for timeline events.
        
        Args:
            listener: Async function to call with events
        """
        self.event_listeners.append(listener)
        logger.info("Registered timeline event listener")
    
    async def _notify_event_listeners(self, event: TimelineEvent) -> None:
        """
        Notify all event listeners of a new event.
        
        Args:
            event: Event to notify about
        """
        for listener in self.event_listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Error in timeline event listener: {str(e)}")
    
    async def create_timeline(
        self,
        workflow_id: str,
        workflow_name: str
    ) -> ExecutionTimeline:
        """
        Create a new execution timeline for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            workflow_name: Name of the workflow
            
        Returns:
            New execution timeline
        """
        now = datetime.now()
        
        # Create timeline
        timeline = ExecutionTimeline(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            start_time=now,
            status="running"
        )
        
        # Add to active timelines
        self.active_timelines[workflow_id] = timeline
        
        # Create and record workflow start event
        await self.record_event(
            workflow_id=workflow_id,
            event_type=TimelineEventType.WORKFLOW_START,
            details={
                "workflow_name": workflow_name
            }
        )
        
        logger.info(f"Created timeline for workflow {workflow_id}")
        return timeline
    
    async def complete_timeline(
        self,
        workflow_id: str,
        status: str = "completed"
    ) -> Optional[ExecutionTimeline]:
        """
        Complete an execution timeline for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            status: Final status of the workflow
            
        Returns:
            Completed execution timeline, or None if not found
        """
        if workflow_id not in self.active_timelines:
            logger.warning(f"Cannot complete timeline for unknown workflow: {workflow_id}")
            return None
        
        # Get timeline
        timeline = self.active_timelines[workflow_id]
        
        # Update timeline
        now = datetime.now()
        timeline.end_time = now
        timeline.status = status
        
        if timeline.start_time:
            timeline.duration_ms = (now - timeline.start_time).total_seconds() * 1000
        
        # Record workflow completion event
        event_type = (
            TimelineEventType.WORKFLOW_COMPLETE
            if status == "completed"
            else TimelineEventType.WORKFLOW_FAILED
        )
        
        await self.record_event(
            workflow_id=workflow_id,
            event_type=event_type,
            details={
                "duration_ms": timeline.duration_ms,
                "status": status
            }
        )
        
        # Move to completed timelines
        self.completed_timelines[workflow_id] = timeline
        del self.active_timelines[workflow_id]
        
        logger.info(f"Completed timeline for workflow {workflow_id} with status {status}")
        return timeline
    
    async def record_event(
        self,
        workflow_id: str,
        event_type: TimelineEventType,
        node_id: Optional[str] = None,
        message_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        related_event_ids: Optional[List[str]] = None
    ) -> Optional[TimelineEvent]:
        """
        Record an event in a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            event_type: Type of event
            node_id: ID of the node involved (if applicable)
            message_id: ID of the message involved (if applicable)
            agent_id: ID of the agent involved (if applicable)
            duration_ms: Duration of the event in milliseconds (if applicable)
            details: Additional details about the event
            related_event_ids: IDs of related events
            
        Returns:
            Recorded event, or None if timeline not found
        """
        if workflow_id not in self.active_timelines:
            logger.warning(f"Cannot record event for unknown workflow: {workflow_id}")
            return None
        
        # Get timeline
        timeline = self.active_timelines[workflow_id]
        
        # Create event
        event = TimelineEvent(
            event_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            event_type=event_type,
            timestamp=datetime.now(),
            node_id=node_id,
            message_id=message_id,
            agent_id=agent_id,
            duration_ms=duration_ms,
            details=details or {},
            related_event_ids=related_event_ids or []
        )
        
        # Add to timeline
        timeline.events.append(event)
        
        # Update node durations and start times
        if event_type == TimelineEventType.NODE_START and node_id:
            timeline.node_start_times[node_id] = event.timestamp
            
        elif event_type == TimelineEventType.NODE_COMPLETE and node_id:
            if node_id in timeline.node_start_times:
                start_time = timeline.node_start_times[node_id]
                duration = (event.timestamp - start_time).total_seconds() * 1000
                timeline.node_durations[node_id] = duration
        
        # Update message flows
        if event_type == TimelineEventType.MESSAGE_SENT and node_id and message_id:
            timeline.message_flows.append({
                "message_id": message_id,
                "source_node_id": node_id,
                "timestamp": event.timestamp.isoformat(),
                "details": details or {}
            })
            
        elif event_type == TimelineEventType.MESSAGE_RECEIVED and node_id and message_id:
            # Find the corresponding sent message
            for flow in timeline.message_flows:
                if flow.get("message_id") == message_id and "target_node_id" not in flow:
                    flow["target_node_id"] = node_id
                    flow["delivery_timestamp"] = event.timestamp.isoformat()
                    
                    if "timestamp" in flow:
                        sent_time = datetime.fromisoformat(flow["timestamp"])
                        delivery_time = event.timestamp
                        flow["delivery_duration_ms"] = (delivery_time - sent_time).total_seconds() * 1000
                    
                    break
        
        # Notify listeners
        await self._notify_event_listeners(event)
        
        # Send WebSocket update if available
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(
                    "timeline_event",
                    {
                        "workflow_id": workflow_id,
                        "event": event.dict()
                    }
                )
            except Exception as e:
                logger.error(f"Error broadcasting timeline event: {str(e)}")
        
        logger.debug(f"Recorded {event_type} event for workflow {workflow_id}")
        return event
    
    def get_timeline(self, workflow_id: str) -> Optional[ExecutionTimeline]:
        """
        Get the execution timeline for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Execution timeline, or None if not found
        """
        # Check active timelines first
        if workflow_id in self.active_timelines:
            return self.active_timelines[workflow_id]
        
        # Then check completed timelines
        if workflow_id in self.completed_timelines:
            return self.completed_timelines[workflow_id]
        
        return None
    
    def get_timeline_segment(
        self,
        workflow_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[TimelineSegment]:
        """
        Get a segment of a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            start_time: Start time of the segment
            end_time: End time of the segment
            
        Returns:
            Timeline segment, or None if timeline not found
        """
        timeline = self.get_timeline(workflow_id)
        if not timeline:
            return None
        
        # Filter events in the time range
        events = [
            event for event in timeline.events
            if start_time <= event.timestamp <= end_time
        ]
        
        return TimelineSegment(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time,
            events=events
        )
    
    def get_all_timelines(self) -> Dict[str, ExecutionTimeline]:
        """
        Get all execution timelines (active and completed).
        
        Returns:
            Dictionary mapping workflow IDs to timelines
        """
        all_timelines = {}
        all_timelines.update(self.active_timelines)
        all_timelines.update(self.completed_timelines)
        return all_timelines
