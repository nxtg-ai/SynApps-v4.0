"""
Priority-based messaging system for the Meta-Agent Orchestrator
Extends the base messaging system with priority queue support
"""

import logging
import asyncio
import heapq
from typing import Dict, Any, List, Optional, Callable, Awaitable, Tuple
from datetime import datetime

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.messaging import MessageBus

logger = logging.getLogger("communication.priority_messaging")

class PriorityMessageBus(MessageBus):
    """
    Enhanced message bus with priority queue support for agent-to-agent communication.
    Extends the standard MessageBus with priority-based message delivery.
    """
    
    def __init__(self):
        """Initialize the priority message bus"""
        super().__init__()
        # Priority queues for each topic (list of tuples: (-priority, timestamp, message))
        # Using negative priority so that higher priority messages come first in the heap
        self.priority_queues: Dict[str, List[Tuple[int, float, AppletMessage]]] = {}
        # Flag to indicate if the priority processor is running
        self.is_processing: Dict[str, bool] = {}
        logger.info("Priority message bus initialized")
    
    async def publish(self, topic: str, message: AppletMessage) -> None:
        """
        Publish a message to a topic with priority support.
        
        Args:
            topic: Topic to publish to
            message: Message to publish (can be AppletMessage or PriorityMessage)
        """
        logger.info(f"Publishing message to topic: {topic}")
        
        # Store message in history
        if topic not in self.message_history:
            self.message_history[topic] = []
        self.message_history[topic].append(message)
        
        # Initialize priority queue for topic if it doesn't exist
        if topic not in self.priority_queues:
            self.priority_queues[topic] = []
            self.is_processing[topic] = False
        
        # Determine message priority
        priority = 5  # Default priority (middle)
        if isinstance(message, PriorityMessage):
            priority = message.priority
        
        # Add to priority queue (use negative priority for max-heap behavior)
        timestamp = datetime.now().timestamp()
        heapq.heappush(self.priority_queues[topic], (-priority, timestamp, message))
        
        # Start processing the queue if not already running
        if not self.is_processing[topic]:
            asyncio.create_task(self._process_queue(topic))
    
    async def _process_queue(self, topic: str) -> None:
        """
        Process messages in the priority queue for a topic.
        
        Args:
            topic: Topic to process messages for
        """
        self.is_processing[topic] = True
        
        try:
            while self.priority_queues[topic]:
                # Get highest priority message
                _, _, message = heapq.heappop(self.priority_queues[topic])
                
                # Deliver to subscribers
                if topic in self.subscribers:
                    delivery_tasks = []
                    for callback in self.subscribers[topic]:
                        delivery_tasks.append(asyncio.create_task(callback(message)))
                    
                    # Wait for all deliveries to complete
                    if delivery_tasks:
                        await asyncio.gather(*delivery_tasks)
        finally:
            self.is_processing[topic] = False
    
    def get_message_history(self, topic: str, limit: int = 100, 
                          min_priority: int = 0) -> List[AppletMessage]:
        """
        Get message history for a topic with optional priority filtering.
        
        Args:
            topic: Topic to get history for
            limit: Maximum number of messages to return
            min_priority: Minimum priority level to include (0-10)
            
        Returns:
            List of messages, most recent first
        """
        if topic not in self.message_history:
            return []
        
        # Filter by priority if needed
        if min_priority > 0:
            filtered_messages = [
                msg for msg in self.message_history[topic]
                if not isinstance(msg, PriorityMessage) or msg.priority >= min_priority
            ]
        else:
            filtered_messages = self.message_history[topic]
        
        # Return most recent messages first
        return list(reversed(filtered_messages[-limit:]))
    
    async def publish_with_priority(self, topic: str, message: AppletMessage, 
                                  priority: int) -> None:
        """
        Publish a standard message with an explicit priority.
        
        Args:
            topic: Topic to publish to
            message: Standard AppletMessage to publish
            priority: Priority level (0-10)
        """
        # Convert to PriorityMessage if it's not already
        if not isinstance(message, PriorityMessage):
            priority_message = PriorityMessage(
                content=message.content,
                context=message.context,
                metadata=message.metadata,
                priority=priority
            )
        else:
            # Override priority if message is already a PriorityMessage
            message.priority = priority
            priority_message = message
            
        await self.publish(topic, priority_message)
