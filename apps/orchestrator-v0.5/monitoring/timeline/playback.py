"""
Timeline Playback for the Meta-Agent Orchestrator

Provides functionality for playing back workflow execution timelines,
allowing users to visualize and analyze workflow executions step by step.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from datetime import datetime, timedelta
import json
import uuid
import bisect

from monitoring.timeline.models import (
    TimelineEventType, TimelineEvent, ExecutionTimeline,
    TimelinePlaybackState, TimelinePlaybackControl, TimelinePlaybackUpdate
)
from monitoring.timeline.service import TimelineService
from communication.websocket import WebSocketManager

logger = logging.getLogger("monitoring.timeline.playback")

class TimelinePlaybackManager:
    """
    Manager for timeline playback functionality.
    """
    def __init__(
        self,
        timeline_service: TimelineService,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize the timeline playback manager.
        
        Args:
            timeline_service: Timeline service for accessing timelines
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        self.timeline_service = timeline_service
        self.websocket_manager = websocket_manager
        
        # Active playback sessions by workflow ID
        self.active_playbacks: Dict[str, TimelinePlaybackControl] = {}
        
        # Background tasks for playback
        self.playback_tasks: Dict[str, asyncio.Task] = {}
        
        # Update listeners
        self.update_listeners: List[Callable[[TimelinePlaybackUpdate], Awaitable[None]]] = []
        
        logger.info("TimelinePlaybackManager initialized")
    
    async def register_update_listener(
        self,
        listener: Callable[[TimelinePlaybackUpdate], Awaitable[None]]
    ) -> None:
        """
        Register a listener for playback updates.
        
        Args:
            listener: Async function to call with updates
        """
        self.update_listeners.append(listener)
        logger.info("Registered playback update listener")
    
    async def _notify_update_listeners(self, update: TimelinePlaybackUpdate) -> None:
        """
        Notify all update listeners of a playback update.
        
        Args:
            update: Update to notify about
        """
        for listener in self.update_listeners:
            try:
                await listener(update)
            except Exception as e:
                logger.error(f"Error in playback update listener: {str(e)}")
    
    async def start_playback(
        self,
        workflow_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        playback_speed: float = 1.0,
        loop: bool = False
    ) -> Optional[TimelinePlaybackControl]:
        """
        Start playback of a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            start_time: Optional start time for playback range
            end_time: Optional end time for playback range
            playback_speed: Playback speed multiplier
            loop: Whether to loop playback
            
        Returns:
            Playback control, or None if timeline not found
        """
        # Get timeline
        timeline = self.timeline_service.get_timeline(workflow_id)
        if not timeline:
            logger.warning(f"Cannot start playback for unknown workflow: {workflow_id}")
            return None
        
        # Determine start and end times
        if not start_time:
            start_time = timeline.start_time
        
        if not end_time:
            end_time = timeline.end_time or datetime.now()
        
        # Create playback control
        control = TimelinePlaybackControl(
            workflow_id=workflow_id,
            state=TimelinePlaybackState.PLAYING,
            current_time=start_time,
            playback_speed=playback_speed,
            loop=loop,
            start_time=start_time,
            end_time=end_time
        )
        
        # Store in active playbacks
        self.active_playbacks[workflow_id] = control
        
        # Start playback task
        if workflow_id in self.playback_tasks and not self.playback_tasks[workflow_id].done():
            self.playback_tasks[workflow_id].cancel()
        
        self.playback_tasks[workflow_id] = asyncio.create_task(
            self._run_playback(workflow_id)
        )
        
        logger.info(f"Started playback for workflow {workflow_id}")
        return control
    
    async def pause_playback(self, workflow_id: str) -> Optional[TimelinePlaybackControl]:
        """
        Pause playback of a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Updated playback control, or None if not found
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot pause playback for unknown workflow: {workflow_id}")
            return None
        
        # Update control
        control = self.active_playbacks[workflow_id]
        control.state = TimelinePlaybackState.PAUSED
        
        # Cancel playback task
        if workflow_id in self.playback_tasks and not self.playback_tasks[workflow_id].done():
            self.playback_tasks[workflow_id].cancel()
        
        # Send update
        await self._send_playback_update(workflow_id)
        
        logger.info(f"Paused playback for workflow {workflow_id}")
        return control
    
    async def resume_playback(self, workflow_id: str) -> Optional[TimelinePlaybackControl]:
        """
        Resume playback of a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Updated playback control, or None if not found
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot resume playback for unknown workflow: {workflow_id}")
            return None
        
        # Update control
        control = self.active_playbacks[workflow_id]
        control.state = TimelinePlaybackState.PLAYING
        
        # Start playback task
        if workflow_id in self.playback_tasks and not self.playback_tasks[workflow_id].done():
            self.playback_tasks[workflow_id].cancel()
        
        self.playback_tasks[workflow_id] = asyncio.create_task(
            self._run_playback(workflow_id)
        )
        
        logger.info(f"Resumed playback for workflow {workflow_id}")
        return control
    
    async def stop_playback(self, workflow_id: str) -> None:
        """
        Stop playback of a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot stop playback for unknown workflow: {workflow_id}")
            return
        
        # Cancel playback task
        if workflow_id in self.playback_tasks and not self.playback_tasks[workflow_id].done():
            self.playback_tasks[workflow_id].cancel()
        
        # Remove from active playbacks
        if workflow_id in self.active_playbacks:
            del self.active_playbacks[workflow_id]
        
        logger.info(f"Stopped playback for workflow {workflow_id}")
    
    async def seek_playback(
        self,
        workflow_id: str,
        seek_time: datetime
    ) -> Optional[TimelinePlaybackControl]:
        """
        Seek playback of a workflow execution timeline to a specific time.
        
        Args:
            workflow_id: ID of the workflow
            seek_time: Time to seek to
            
        Returns:
            Updated playback control, or None if not found
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot seek playback for unknown workflow: {workflow_id}")
            return None
        
        # Get control
        control = self.active_playbacks[workflow_id]
        
        # Validate seek time
        if seek_time < control.start_time:
            seek_time = control.start_time
        
        if control.end_time and seek_time > control.end_time:
            seek_time = control.end_time
        
        # Update control
        was_playing = control.state == TimelinePlaybackState.PLAYING
        control.state = TimelinePlaybackState.SEEKING
        control.current_time = seek_time
        
        # Send update
        await self._send_playback_update(workflow_id)
        
        # Resume playing if it was playing before
        if was_playing:
            control.state = TimelinePlaybackState.PLAYING
            
            # Restart playback task
            if workflow_id in self.playback_tasks and not self.playback_tasks[workflow_id].done():
                self.playback_tasks[workflow_id].cancel()
            
            self.playback_tasks[workflow_id] = asyncio.create_task(
                self._run_playback(workflow_id)
            )
        else:
            control.state = TimelinePlaybackState.PAUSED
        
        logger.info(f"Seeked playback for workflow {workflow_id} to {seek_time}")
        return control
    
    async def set_playback_speed(
        self,
        workflow_id: str,
        speed: float
    ) -> Optional[TimelinePlaybackControl]:
        """
        Set the playback speed for a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            speed: Playback speed multiplier
            
        Returns:
            Updated playback control, or None if not found
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot set playback speed for unknown workflow: {workflow_id}")
            return None
        
        # Update control
        control = self.active_playbacks[workflow_id]
        control.playback_speed = max(0.1, min(10.0, speed))  # Clamp between 0.1x and 10x
        
        logger.info(f"Set playback speed for workflow {workflow_id} to {control.playback_speed}x")
        return control
    
    async def set_playback_loop(
        self,
        workflow_id: str,
        loop: bool
    ) -> Optional[TimelinePlaybackControl]:
        """
        Set whether playback should loop for a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
            loop: Whether to loop playback
            
        Returns:
            Updated playback control, or None if not found
        """
        if workflow_id not in self.active_playbacks:
            logger.warning(f"Cannot set playback loop for unknown workflow: {workflow_id}")
            return None
        
        # Update control
        control = self.active_playbacks[workflow_id]
        control.loop = loop
        
        logger.info(f"Set playback loop for workflow {workflow_id} to {loop}")
        return control
    
    async def _run_playback(self, workflow_id: str) -> None:
        """
        Run playback for a workflow execution timeline.
        
        Args:
            workflow_id: ID of the workflow
        """
        if workflow_id not in self.active_playbacks:
            return
        
        # Get control and timeline
        control = self.active_playbacks[workflow_id]
        timeline = self.timeline_service.get_timeline(workflow_id)
        
        if not timeline:
            logger.warning(f"Cannot run playback for unknown workflow: {workflow_id}")
            return
        
        # Sort events by timestamp
        sorted_events = sorted(timeline.events, key=lambda e: e.timestamp)
        
        # Find index of first event after current time
        current_index = bisect.bisect_left(
            sorted_events,
            control.current_time,
            key=lambda e: e.timestamp
        )
        
        # Main playback loop
        try:
            while control.state == TimelinePlaybackState.PLAYING:
                # Check if we've reached the end
                if current_index >= len(sorted_events):
                    if control.loop:
                        # Loop back to start
                        control.current_time = control.start_time
                        current_index = 0
                        await self._send_playback_update(workflow_id)
                    else:
                        # Stop at end
                        control.state = TimelinePlaybackState.STOPPED
                        await self._send_playback_update(workflow_id)
                        break
                
                # Get current event
                event = sorted_events[current_index]
                
                # Update current time
                control.current_time = event.timestamp
                
                # Send update
                await self._send_playback_update(workflow_id)
                
                # Move to next event
                current_index += 1
                
                # If there's another event, wait until its time
                if current_index < len(sorted_events):
                    next_event = sorted_events[current_index]
                    wait_time = (next_event.timestamp - event.timestamp).total_seconds()
                    
                    # Adjust for playback speed
                    if control.playback_speed > 0:
                        wait_time /= control.playback_speed
                    
                    # Wait for next event
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                else:
                    # No more events, check if we should loop
                    if control.loop:
                        # Loop back to start
                        control.current_time = control.start_time
                        current_index = 0
                        await self._send_playback_update(workflow_id)
                    else:
                        # Stop at end
                        control.state = TimelinePlaybackState.STOPPED
                        await self._send_playback_update(workflow_id)
                        break
        
        except asyncio.CancelledError:
            # Playback was cancelled
            pass
        
        except Exception as e:
            logger.error(f"Error in playback task for workflow {workflow_id}: {str(e)}")
            control.state = TimelinePlaybackState.STOPPED
            await self._send_playback_update(workflow_id)
    
    async def _send_playback_update(self, workflow_id: str) -> None:
        """
        Send a playback update for a workflow.
        
        Args:
            workflow_id: ID of the workflow
        """
        if workflow_id not in self.active_playbacks:
            return
        
        # Get control and timeline
        control = self.active_playbacks[workflow_id]
        timeline = self.timeline_service.get_timeline(workflow_id)
        
        if not timeline:
            return
        
        # Find events at the current time
        current_events = []
        active_nodes = set()
        active_messages = set()
        
        for event in timeline.events:
            # Include events within a small window of the current time
            time_diff = abs((event.timestamp - control.current_time).total_seconds())
            if time_diff <= 0.5:  # Within half a second
                current_events.append(event)
                
                # Track active nodes and messages
                if event.node_id:
                    active_nodes.add(event.node_id)
                
                if event.message_id:
                    active_messages.add(event.message_id)
        
        # Calculate progress percentage
        progress = 0.0
        if control.start_time and control.end_time:
            total_duration = (control.end_time - control.start_time).total_seconds()
            if total_duration > 0:
                elapsed = (control.current_time - control.start_time).total_seconds()
                progress = min(100.0, max(0.0, (elapsed / total_duration) * 100.0))
        
        # Create update
        update = TimelinePlaybackUpdate(
            workflow_id=workflow_id,
            current_time=control.current_time,
            current_events=current_events,
            active_nodes=list(active_nodes),
            active_messages=list(active_messages),
            progress_percentage=progress
        )
        
        # Notify listeners
        await self._notify_update_listeners(update)
        
        # Send to WebSocket clients
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(
                    "playback_update",
                    update.dict()
                )
            except Exception as e:
                logger.error(f"Error broadcasting playback update: {str(e)}")
    
    def get_playback_control(self, workflow_id: str) -> Optional[TimelinePlaybackControl]:
        """
        Get the playback control for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Playback control, or None if not found
        """
        return self.active_playbacks.get(workflow_id)
