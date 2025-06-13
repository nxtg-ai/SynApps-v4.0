"""
Dashboard Service for the Meta-Agent Orchestrator

Collects, processes, and manages monitoring data for the real-time dashboard UI.
Provides APIs for retrieving current state and historical data.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from datetime import datetime, timedelta
import json
import uuid
from collections import deque

from monitoring.dashboard.models import (
    AgentState, MessageDirection, MessageStatus,
    AgentStatusModel, MessageFlowModel, WorkflowStatusModel, 
    WorkflowMetrics, AgentMetrics, DashboardUpdateModel
)
from models.agent_message import AppletMessage
from models.workflow import WorkflowNode, Workflow
from communication.websocket import WebSocketManager

logger = logging.getLogger("monitoring.dashboard.service")

class DashboardService:
    """
    Service for managing the real-time monitoring dashboard.
    """
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        """
        Initialize the dashboard service.
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        # WebSocket manager for pushing updates
        self.websocket_manager = websocket_manager
        
        # Current state
        self.agent_states: Dict[str, AgentStatusModel] = {}
        self.workflow_states: Dict[str, WorkflowStatusModel] = {}
        
        # Historical data (limited size)
        self.message_history: deque = deque(maxlen=1000)  # Last 1000 messages
        self.agent_history: Dict[str, deque] = {}  # History by agent
        self.workflow_history: Dict[str, deque] = {}  # History by workflow
        
        # Update listeners
        self.update_listeners: List[Callable[[DashboardUpdateModel], Awaitable[None]]] = []
        
        # System metrics
        self.system_metrics: Dict[str, Any] = {
            "start_time": datetime.now(),
            "total_workflows": 0,
            "active_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_messages": 0,
            "messages_per_minute": 0,
            "error_rate": 0.0
        }
        
        # Message rate tracking
        self.message_timestamps: deque = deque(maxlen=1000)  # Last 1000 message timestamps
        
        logger.info("DashboardService initialized")
    
    async def start(self) -> None:
        """Start the dashboard service"""
        # Start background tasks
        asyncio.create_task(self._update_metrics_loop())
        logger.info("DashboardService started")
    
    async def _update_metrics_loop(self) -> None:
        """Background task to update metrics periodically"""
        while True:
            try:
                # Update messages per minute
                self._update_message_rate()
                
                # Update system-wide metrics
                self._update_system_metrics()
                
                # Send periodic updates to clients
                await self._send_dashboard_update()
                
            except Exception as e:
                logger.error(f"Error in metrics update loop: {str(e)}")
            
            # Update every 5 seconds
            await asyncio.sleep(5)
    
    def _update_message_rate(self) -> None:
        """Update the messages per minute metric"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Count messages in the last minute
        recent_messages = [ts for ts in self.message_timestamps if ts > one_minute_ago]
        
        # Update metric
        self.system_metrics["messages_per_minute"] = len(recent_messages)
    
    def _update_system_metrics(self) -> None:
        """Update system-wide metrics"""
        # Count active workflows
        active_workflows = 0
        completed_workflows = 0
        failed_workflows = 0
        
        for workflow_id, status in self.workflow_states.items():
            if status.status == "running":
                active_workflows += 1
            elif status.status == "completed":
                completed_workflows += 1
            elif status.status == "failed":
                failed_workflows += 1
        
        self.system_metrics["active_workflows"] = active_workflows
        self.system_metrics["completed_workflows"] = completed_workflows
        self.system_metrics["failed_workflows"] = failed_workflows
        
        # Calculate overall error rate
        total_nodes = sum(ws.metrics.total_nodes for ws in self.workflow_states.values())
        failed_nodes = sum(ws.metrics.failed_nodes for ws in self.workflow_states.values())
        
        if total_nodes > 0:
            self.system_metrics["error_rate"] = failed_nodes / total_nodes
        else:
            self.system_metrics["error_rate"] = 0.0
        
        # Calculate uptime
        uptime = datetime.now() - self.system_metrics["start_time"]
        self.system_metrics["uptime_seconds"] = uptime.total_seconds()
    
    async def register_update_listener(
        self,
        listener: Callable[[DashboardUpdateModel], Awaitable[None]]
    ) -> None:
        """
        Register a listener for dashboard updates.
        
        Args:
            listener: Async function to call with updates
        """
        self.update_listeners.append(listener)
        logger.info("Registered dashboard update listener")
    
    async def _send_dashboard_update(
        self,
        agent_updates: List[AgentStatusModel] = None,
        message_flows: List[MessageFlowModel] = None,
        workflow_updates: List[WorkflowStatusModel] = None
    ) -> None:
        """
        Send a dashboard update to all listeners and WebSocket clients.
        
        Args:
            agent_updates: Agent status updates
            message_flows: Message flow updates
            workflow_updates: Workflow status updates
        """
        # Create update model
        update = DashboardUpdateModel(
            timestamp=datetime.now(),
            agent_updates=agent_updates or [],
            message_flows=message_flows or [],
            workflow_updates=workflow_updates or [],
            system_metrics=self.system_metrics
        )
        
        # Notify listeners
        for listener in self.update_listeners:
            try:
                await listener(update)
            except Exception as e:
                logger.error(f"Error in dashboard update listener: {str(e)}")
        
        # Send to WebSocket clients
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(
                    "dashboard_update",
                    update.dict()
                )
            except Exception as e:
                logger.error(f"Error broadcasting dashboard update: {str(e)}")
    
    async def update_agent_status(
        self,
        agent_id: str,
        node_id: str,
        workflow_id: str,
        state: AgentState,
        current_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the status of an agent.
        
        Args:
            agent_id: ID of the agent
            node_id: ID of the node in the workflow
            workflow_id: ID of the workflow
            state: Current state of the agent
            current_message_id: ID of the message being processed
            metadata: Additional metadata
        """
        now = datetime.now()
        
        # Create or update agent status
        if agent_id in self.agent_states:
            agent_status = self.agent_states[agent_id]
            agent_status.state = state
            agent_status.current_message_id = current_message_id
            agent_status.last_update = now
            if metadata:
                agent_status.metadata.update(metadata)
        else:
            agent_status = AgentStatusModel(
                agent_id=agent_id,
                node_id=node_id,
                workflow_id=workflow_id,
                state=state,
                current_message_id=current_message_id,
                last_update=now,
                metadata=metadata or {}
            )
            self.agent_states[agent_id] = agent_status
        
        # Add to history
        if agent_id not in self.agent_history:
            self.agent_history[agent_id] = deque(maxlen=100)
        self.agent_history[agent_id].append((now, agent_status.copy()))
        
        # Send update
        await self._send_dashboard_update(agent_updates=[agent_status])
        
        logger.debug(f"Updated agent status: {agent_id} -> {state}")
    
    async def update_agent_metrics(
        self,
        agent_id: str,
        metrics_update: Dict[str, Any]
    ) -> None:
        """
        Update metrics for an agent.
        
        Args:
            agent_id: ID of the agent
            metrics_update: Metrics to update
        """
        if agent_id not in self.agent_states:
            logger.warning(f"Cannot update metrics for unknown agent: {agent_id}")
            return
        
        # Update metrics
        agent_status = self.agent_states[agent_id]
        
        for key, value in metrics_update.items():
            if hasattr(agent_status.metrics, key):
                setattr(agent_status.metrics, key, value)
        
        # Calculate error rate
        if agent_status.metrics.total_messages > 0:
            agent_status.metrics.error_rate = (
                agent_status.metrics.failed_messages / agent_status.metrics.total_messages
            )
        
        # Send update
        await self._send_dashboard_update(agent_updates=[agent_status])
        
        logger.debug(f"Updated agent metrics: {agent_id}")
    
    async def record_message_flow(
        self,
        message_id: str,
        workflow_id: str,
        source_id: str,
        target_id: str,
        direction: MessageDirection,
        status: MessageStatus,
        content_type: str,
        content_size: int,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a message flow between agents or components.
        
        Args:
            message_id: ID of the message
            workflow_id: ID of the workflow
            source_id: ID of the source (agent or component)
            target_id: ID of the target (agent or component)
            direction: Direction of the message flow
            status: Status of the message
            content_type: Type of content in the message
            content_size: Size of the message content in bytes
            duration_ms: Duration of the message processing in ms
            metadata: Additional metadata
        """
        now = datetime.now()
        
        # Create message flow model
        message_flow = MessageFlowModel(
            message_id=message_id,
            workflow_id=workflow_id,
            source_id=source_id,
            target_id=target_id,
            direction=direction,
            status=status,
            timestamp=now,
            content_type=content_type,
            content_size=content_size,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Add to history
        self.message_history.append(message_flow)
        
        # Track message timestamp for rate calculation
        self.message_timestamps.append(now)
        
        # Update system metrics
        self.system_metrics["total_messages"] += 1
        
        # Send update
        await self._send_dashboard_update(message_flows=[message_flow])
        
        logger.debug(f"Recorded message flow: {source_id} -> {target_id}")
    
    async def update_workflow_status(
        self,
        workflow_id: str,
        workflow_name: str,
        status: str,
        current_node_ids: Optional[List[str]] = None,
        completed_node_ids: Optional[List[str]] = None,
        failed_node_ids: Optional[List[str]] = None,
        metrics_update: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            workflow_name: Name of the workflow
            status: Current status of the workflow
            current_node_ids: IDs of currently active nodes
            completed_node_ids: IDs of completed nodes
            failed_node_ids: IDs of failed nodes
            metrics_update: Metrics to update
            metadata: Additional metadata
        """
        now = datetime.now()
        
        # Create or update workflow status
        if workflow_id in self.workflow_states:
            workflow_status = self.workflow_states[workflow_id]
            workflow_status.status = status
            workflow_status.last_update = now
            
            if current_node_ids is not None:
                workflow_status.current_node_ids = current_node_ids
            
            if completed_node_ids is not None:
                workflow_status.completed_node_ids = completed_node_ids
            
            if failed_node_ids is not None:
                workflow_status.failed_node_ids = failed_node_ids
            
            if metadata:
                workflow_status.metadata.update(metadata)
        else:
            workflow_status = WorkflowStatusModel(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                status=status,
                current_node_ids=current_node_ids or [],
                completed_node_ids=completed_node_ids or [],
                failed_node_ids=failed_node_ids or [],
                last_update=now,
                metadata=metadata or {}
            )
            self.workflow_states[workflow_id] = workflow_status
            
            # Update system metrics for new workflow
            self.system_metrics["total_workflows"] += 1
        
        # Update metrics if provided
        if metrics_update:
            for key, value in metrics_update.items():
                if hasattr(workflow_status.metrics, key):
                    setattr(workflow_status.metrics, key, value)
        
        # Update metrics based on node counts
        if completed_node_ids is not None and workflow_status.metrics.total_nodes > 0:
            workflow_status.metrics.completed_nodes = len(completed_node_ids)
        
        if failed_node_ids is not None and workflow_status.metrics.total_nodes > 0:
            workflow_status.metrics.failed_nodes = len(failed_node_ids)
            workflow_status.metrics.error_rate = (
                workflow_status.metrics.failed_nodes / workflow_status.metrics.total_nodes
            )
        
        # Add to history
        if workflow_id not in self.workflow_history:
            self.workflow_history[workflow_id] = deque(maxlen=100)
        self.workflow_history[workflow_id].append((now, workflow_status.copy()))
        
        # Send update
        await self._send_dashboard_update(workflow_updates=[workflow_status])
        
        logger.debug(f"Updated workflow status: {workflow_id} -> {status}")
    
    def get_agent_status(self, agent_id: str) -> Optional[AgentStatusModel]:
        """
        Get the current status of an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Current status of the agent, or None if not found
        """
        return self.agent_states.get(agent_id)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatusModel]:
        """
        Get the current status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Current status of the workflow, or None if not found
        """
        return self.workflow_states.get(workflow_id)
    
    def get_agent_history(
        self,
        agent_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical status updates for an agent.
        
        Args:
            agent_id: ID of the agent
            limit: Maximum number of history items to return
            
        Returns:
            List of historical status updates
        """
        if agent_id not in self.agent_history:
            return []
        
        history = list(self.agent_history[agent_id])[-limit:]
        return [{"timestamp": ts, "status": status.dict()} for ts, status in history]
    
    def get_workflow_history(
        self,
        workflow_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical status updates for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of history items to return
            
        Returns:
            List of historical status updates
        """
        if workflow_id not in self.workflow_history:
            return []
        
        history = list(self.workflow_history[workflow_id])[-limit:]
        return [{"timestamp": ts, "status": status.dict()} for ts, status in history]
    
    def get_message_history(
        self,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical message flows.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            agent_id: Optional agent ID to filter by
            limit: Maximum number of history items to return
            
        Returns:
            List of historical message flows
        """
        # Filter message history
        filtered_history = []
        for message in self.message_history:
            if workflow_id and message.workflow_id != workflow_id:
                continue
            
            if agent_id and agent_id not in (message.source_id, message.target_id):
                continue
            
            filtered_history.append(message)
        
        # Return most recent messages first
        return [msg.dict() for msg in filtered_history[-limit:]]
    
    def get_dashboard_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of the current dashboard state.
        
        Returns:
            Dictionary with current dashboard state
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                agent_id: status.dict()
                for agent_id, status in self.agent_states.items()
            },
            "workflows": {
                workflow_id: status.dict()
                for workflow_id, status in self.workflow_states.items()
            },
            "system_metrics": self.system_metrics,
            "recent_messages": [
                msg.dict() for msg in list(self.message_history)[-10:]
            ]
        }
