"""
Message replay mechanism for the Meta-Agent Orchestrator
Provides fault tolerance through message replay capabilities
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Set, Tuple, TypeVar
from datetime import datetime, timedelta
import json
import uuid

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.persistent_messaging import PersistentMessageBus
from database.models.message_models import MessageStatus

logger = logging.getLogger("communication.message_replay")

# Type definitions
T = TypeVar('T', bound=AppletMessage)
MessageProcessor = Callable[[T], Awaitable[bool]]
MessageFilter = Callable[[T], bool]

class MessageReplayManager:
    """
    Manager for replaying failed or unprocessed messages.
    Provides fault tolerance through message replay capabilities.
    """
    
    def __init__(self, message_bus: PersistentMessageBus):
        """
        Initialize the message replay manager.
        
        Args:
            message_bus: Message bus to use for replaying messages
        """
        self.message_bus = message_bus
        
        # Dictionary of topic -> processor function
        self.processors: Dict[str, MessageProcessor] = {}
        
        # Dictionary of topic -> filter function
        self.filters: Dict[str, MessageFilter] = {}
        
        # Dictionary of replay session ID -> status
        self.active_replays: Dict[str, Dict[str, Any]] = {}
        
        # Flag to indicate if the manager is running
        self.running = False
        
        # Main processing task
        self.processing_task: Optional[asyncio.Task] = None
        
        logger.info("Message replay manager initialized")
    
    def register_processor(self, topic: str, processor: MessageProcessor) -> None:
        """
        Register a processor function for a topic.
        
        Args:
            topic: Topic to register processor for
            processor: Function that processes messages and returns success status
        """
        self.processors[topic] = processor
        logger.info(f"Registered message processor for topic: {topic}")
    
    def register_filter(self, topic: str, filter_func: MessageFilter) -> None:
        """
        Register a filter function for a topic.
        
        Args:
            topic: Topic to register filter for
            filter_func: Function that determines if a message should be replayed
        """
        self.filters[topic] = filter_func
        logger.info(f"Registered message filter for topic: {topic}")
    
    async def start(self) -> None:
        """
        Start the message replay manager.
        """
        if self.running:
            return
        
        self.running = True
        logger.info("Message replay manager started")
    
    async def stop(self) -> None:
        """
        Stop the message replay manager.
        """
        if not self.running:
            return
        
        self.running = False
        
        # Cancel the processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Message replay manager stopped")
    
    async def replay_failed_messages(self, topic: str, 
                                  time_window: Optional[timedelta] = None,
                                  max_messages: int = 100) -> Tuple[str, int]:
        """
        Replay failed messages for a topic.
        
        Args:
            topic: Topic to replay messages for
            time_window: Time window to look back for failed messages
            max_messages: Maximum number of messages to replay
            
        Returns:
            Tuple of (replay session ID, number of messages replayed)
        """
        # Check if there's a processor for this topic
        if topic not in self.processors:
            logger.warning(f"No processor registered for topic: {topic}")
            return "", 0
        
        # Get the processor
        processor = self.processors[topic]
        
        # Get the filter if available
        message_filter = self.filters.get(topic, lambda _: True)
        
        # Get failed messages from the database
        failed_messages = await self.message_bus.get_failed_messages(
            topic, time_window, max_messages
        )
        
        # Filter messages
        filtered_messages = [msg for msg in failed_messages if message_filter(msg)]
        
        if not filtered_messages:
            logger.info(f"No failed messages to replay for topic: {topic}")
            return "", 0
        
        # Create a replay session ID
        replay_id = str(uuid.uuid4())
        
        # Initialize replay status
        self.active_replays[replay_id] = {
            "topic": topic,
            "total_messages": len(filtered_messages),
            "processed_messages": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "status": "running"
        }
        
        # Start replay task
        asyncio.create_task(self._replay_messages(replay_id, filtered_messages, processor))
        
        logger.info(f"Started replay session {replay_id} for topic {topic} with {len(filtered_messages)} messages")
        return replay_id, len(filtered_messages)
    
    async def _replay_messages(self, replay_id: str, 
                             messages: List[T], 
                             processor: MessageProcessor) -> None:
        """
        Replay a list of messages.
        
        Args:
            replay_id: ID of the replay session
            messages: List of messages to replay
            processor: Function to process each message
        """
        for message in messages:
            try:
                # Process the message
                success = await processor(message)
                
                # Update message status in the database
                if success:
                    await self.message_bus.update_message_status(
                        message.id, MessageStatus.PROCESSED
                    )
                    self.active_replays[replay_id]["successful_messages"] += 1
                else:
                    await self.message_bus.update_message_status(
                        message.id, MessageStatus.FAILED
                    )
                    self.active_replays[replay_id]["failed_messages"] += 1
                
                # Update processed count
                self.active_replays[replay_id]["processed_messages"] += 1
                
            except Exception as e:
                logger.error(f"Error replaying message {message.id}: {str(e)}")
                await self.message_bus.update_message_status(
                    message.id, MessageStatus.FAILED
                )
                self.active_replays[replay_id]["failed_messages"] += 1
                self.active_replays[replay_id]["processed_messages"] += 1
        
        # Update replay status
        self.active_replays[replay_id]["status"] = "completed"
        self.active_replays[replay_id]["end_time"] = datetime.now()
        
        logger.info(f"Completed replay session {replay_id} with "
                   f"{self.active_replays[replay_id]['successful_messages']} successful and "
                   f"{self.active_replays[replay_id]['failed_messages']} failed messages")
    
    def get_replay_status(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a replay session.
        
        Args:
            replay_id: ID of the replay session
            
        Returns:
            Status dictionary, or None if the session doesn't exist
        """
        return self.active_replays.get(replay_id)
    
    async def schedule_periodic_replay(self, topic: str, 
                                     interval: timedelta,
                                     time_window: Optional[timedelta] = None,
                                     max_messages: int = 100) -> str:
        """
        Schedule periodic replay of failed messages.
        
        Args:
            topic: Topic to replay messages for
            interval: Interval between replays
            time_window: Time window to look back for failed messages
            max_messages: Maximum number of messages to replay per run
            
        Returns:
            ID of the scheduled task
        """
        task_id = str(uuid.uuid4())
        
        async def periodic_replay():
            while self.running:
                try:
                    await self.replay_failed_messages(topic, time_window, max_messages)
                except Exception as e:
                    logger.error(f"Error in periodic replay for topic {topic}: {str(e)}")
                
                # Wait for the next interval
                await asyncio.sleep(interval.total_seconds())
        
        # Start the periodic replay task
        asyncio.create_task(periodic_replay())
        
        logger.info(f"Scheduled periodic replay for topic {topic} with interval {interval}")
        return task_id


class ReplayableMessageBus:
    """
    Message bus with replay capabilities.
    Wraps a PersistentMessageBus with replay functionality.
    """
    
    def __init__(self, message_bus: PersistentMessageBus):
        """
        Initialize the replayable message bus.
        
        Args:
            message_bus: Underlying message bus to wrap
        """
        self.message_bus = message_bus
        self.replay_manager = MessageReplayManager(message_bus)
        
        # Dictionary of topic -> processor function
        self.processors: Dict[str, MessageProcessor] = {}
        
        logger.info("Replayable message bus initialized")
    
    async def start(self) -> None:
        """
        Start the replayable message bus.
        """
        await self.replay_manager.start()
        logger.info("Replayable message bus started")
    
    async def stop(self) -> None:
        """
        Stop the replayable message bus.
        """
        await self.replay_manager.stop()
        logger.info("Replayable message bus stopped")
    
    async def publish(self, topic: str, message: T) -> None:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        await self.message_bus.publish(topic, message)
    
    def subscribe(self, topic: str, callback: Callable[[T], Awaitable[None]]) -> None:
        """
        Subscribe to a topic with automatic replay capability.
        
        Args:
            topic: Topic to subscribe to
            callback: Function to call when a message is received
        """
        # Create a processor that calls the callback and returns success status
        async def processor(message: T) -> bool:
            try:
                await callback(message)
                return True
            except Exception:
                return False
        
        # Register the processor with the replay manager
        self.replay_manager.register_processor(topic, processor)
        self.processors[topic] = processor
        
        # Subscribe to the topic
        self.message_bus.subscribe(topic, callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[T], Awaitable[None]]) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            callback: Function to unsubscribe
            
        Returns:
            True if the callback was unsubscribed, False otherwise
        """
        return self.message_bus.unsubscribe(topic, callback)
    
    async def replay_failed_messages(self, topic: str, 
                                  time_window: Optional[timedelta] = None,
                                  max_messages: int = 100) -> Tuple[str, int]:
        """
        Replay failed messages for a topic.
        
        Args:
            topic: Topic to replay messages for
            time_window: Time window to look back for failed messages
            max_messages: Maximum number of messages to replay
            
        Returns:
            Tuple of (replay session ID, number of messages replayed)
        """
        return await self.replay_manager.replay_failed_messages(
            topic, time_window, max_messages
        )
    
    def get_replay_status(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a replay session.
        
        Args:
            replay_id: ID of the replay session
            
        Returns:
            Status dictionary, or None if the session doesn't exist
        """
        return self.replay_manager.get_replay_status(replay_id)
    
    async def schedule_periodic_replay(self, topic: str, 
                                     interval: timedelta,
                                     time_window: Optional[timedelta] = None,
                                     max_messages: int = 100) -> str:
        """
        Schedule periodic replay of failed messages.
        
        Args:
            topic: Topic to replay messages for
            interval: Interval between replays
            time_window: Time window to look back for failed messages
            max_messages: Maximum number of messages to replay per run
            
        Returns:
            ID of the scheduled task
        """
        return await self.replay_manager.schedule_periodic_replay(
            topic, interval, time_window, max_messages
        )
    
    def register_replay_filter(self, topic: str, filter_func: MessageFilter) -> None:
        """
        Register a filter function for message replay.
        
        Args:
            topic: Topic to register filter for
            filter_func: Function that determines if a message should be replayed
        """
        self.replay_manager.register_filter(topic, filter_func)
    
    def get_message_history(self, topic: str, limit: int = 100, 
                          min_priority: int = 0) -> List[T]:
        """
        Get message history for a topic.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        return self.message_bus.get_message_history(topic, limit, min_priority)
    
    async def get_message_history_from_db(self, topic: str, limit: int = 100, 
                                        min_priority: int = 0) -> List[T]:
        """
        Get message history for a topic from the database.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include
            
        Returns:
            List of messages, most recent first
        """
        return await self.message_bus.get_message_history_from_db(topic, limit, min_priority)
