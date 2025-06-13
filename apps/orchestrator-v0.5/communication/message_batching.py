"""
Message batching and throttling for the Meta-Agent Orchestrator
Provides mechanisms for efficient handling of high message volumes
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Set, Tuple, Generic, TypeVar
from collections import defaultdict, deque
from datetime import datetime, timedelta

from models.agent_message import AppletMessage
from communication.persistent_messaging import PersistentMessageBus

logger = logging.getLogger("communication.message_batching")

# Type definitions
T = TypeVar('T', bound=AppletMessage)
BatchHandler = Callable[[List[T]], Awaitable[None]]

class MessageBatcher:
    """
    Batches messages for efficient processing.
    Collects messages until a batch size or timeout is reached.
    """
    
    def __init__(self, 
                 batch_size: int = 10, 
                 timeout_seconds: float = 1.0,
                 max_batches: int = 100):
        """
        Initialize the message batcher.
        
        Args:
            batch_size: Number of messages to collect before processing
            timeout_seconds: Maximum time to wait before processing an incomplete batch
            max_batches: Maximum number of batches to queue before blocking
        """
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.max_batches = max_batches
        
        # Dictionary of topic -> list of messages
        self.message_batches: Dict[str, List[T]] = defaultdict(list)
        
        # Dictionary of topic -> last batch time
        self.last_batch_times: Dict[str, float] = {}
        
        # Dictionary of topic -> batch handlers
        self.batch_handlers: Dict[str, BatchHandler] = {}
        
        # Dictionary of topic -> batch processing tasks
        self.batch_tasks: Dict[str, asyncio.Task] = {}
        
        # Semaphore to limit concurrent batch processing
        self.batch_semaphore = asyncio.Semaphore(max_batches)
        
        # Flag to indicate if the batcher is running
        self.running = False
        
        # Main processing task
        self.processing_task: Optional[asyncio.Task] = None
        
        logger.info(f"Message batcher initialized (batch_size={batch_size}, timeout={timeout_seconds}s)")
    
    def register_batch_handler(self, topic: str, handler: BatchHandler) -> None:
        """
        Register a handler for a topic's batches.
        
        Args:
            topic: Topic to handle batches for
            handler: Function to handle batches
        """
        self.batch_handlers[topic] = handler
        logger.info(f"Registered batch handler for topic: {topic}")
    
    def unregister_batch_handler(self, topic: str) -> bool:
        """
        Unregister a batch handler.
        
        Args:
            topic: Topic to unregister handler for
            
        Returns:
            True if a handler was unregistered, False otherwise
        """
        if topic in self.batch_handlers:
            del self.batch_handlers[topic]
            logger.info(f"Unregistered batch handler for topic: {topic}")
            return True
        return False
    
    async def add_message(self, topic: str, message: T) -> None:
        """
        Add a message to a batch.
        
        Args:
            topic: Topic to add message to
            message: Message to add
        """
        # Ensure the batcher is running
        if not self.running:
            await self.start()
        
        # Add message to batch
        self.message_batches[topic].append(message)
        
        # Update last batch time
        self.last_batch_times[topic] = time.time()
        
        # Check if batch is ready for processing
        if len(self.message_batches[topic]) >= self.batch_size:
            await self._process_batch(topic)
    
    async def _process_batch(self, topic: str) -> None:
        """
        Process a batch of messages.
        
        Args:
            topic: Topic to process batch for
        """
        # Check if there are messages to process
        if not self.message_batches[topic]:
            return
        
        # Check if there's a handler for this topic
        if topic not in self.batch_handlers:
            logger.warning(f"No batch handler registered for topic: {topic}")
            # Clear the batch since it can't be processed
            self.message_batches[topic].clear()
            return
        
        # Get the batch handler
        handler = self.batch_handlers[topic]
        
        # Get the batch of messages
        batch = self.message_batches[topic]
        self.message_batches[topic] = []
        
        # Process the batch with concurrency control
        async with self.batch_semaphore:
            try:
                await handler(batch)
                logger.info(f"Processed batch of {len(batch)} messages for topic: {topic}")
            except Exception as e:
                logger.error(f"Error processing batch for topic {topic}: {str(e)}")
    
    async def _check_timeouts(self) -> None:
        """
        Check for batch timeouts and process any timed-out batches.
        """
        current_time = time.time()
        
        for topic, last_time in list(self.last_batch_times.items()):
            # Check if batch has timed out
            if (current_time - last_time) >= self.timeout_seconds:
                # Process the batch if it has any messages
                if self.message_batches[topic]:
                    await self._process_batch(topic)
    
    async def _processing_loop(self) -> None:
        """
        Main processing loop for checking timeouts.
        """
        while self.running:
            try:
                await self._check_timeouts()
                # Sleep for a short time to avoid busy waiting
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in batch processing loop: {str(e)}")
    
    async def start(self) -> None:
        """
        Start the message batcher.
        """
        if self.running:
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._processing_loop())
        logger.info("Message batcher started")
    
    async def stop(self) -> None:
        """
        Stop the message batcher and process any remaining batches.
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
        
        # Process any remaining batches
        for topic in list(self.message_batches.keys()):
            if self.message_batches[topic]:
                await self._process_batch(topic)
        
        logger.info("Message batcher stopped")


class MessageThrottler:
    """
    Throttles message processing to prevent system overload.
    Limits the rate at which messages are processed.
    """
    
    def __init__(self, 
                 rate_limit: int = 100, 
                 time_window_seconds: float = 1.0,
                 burst_limit: int = 200):
        """
        Initialize the message throttler.
        
        Args:
            rate_limit: Maximum number of messages to process per time window
            time_window_seconds: Time window for rate limiting in seconds
            burst_limit: Maximum number of messages to allow in a burst
        """
        self.rate_limit = rate_limit
        self.time_window_seconds = time_window_seconds
        self.burst_limit = burst_limit
        
        # Token bucket for rate limiting
        self.tokens = rate_limit
        self.last_refill_time = time.time()
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.info(f"Message throttler initialized (rate={rate_limit}/{time_window_seconds}s, burst={burst_limit})")
    
    async def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time.
        """
        current_time = time.time()
        elapsed = current_time - self.last_refill_time
        
        # Calculate tokens to add
        tokens_to_add = int(elapsed / self.time_window_seconds * self.rate_limit)
        
        if tokens_to_add > 0:
            self.tokens = min(self.tokens + tokens_to_add, self.burst_limit)
            self.last_refill_time = current_time
    
    async def acquire(self, count: int = 1) -> bool:
        """
        Acquire tokens for processing messages.
        
        Args:
            count: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self.lock:
            await self._refill_tokens()
            
            if self.tokens >= count:
                self.tokens -= count
                return True
            else:
                return False
    
    async def wait_for_tokens(self, count: int = 1) -> None:
        """
        Wait until tokens are available.
        
        Args:
            count: Number of tokens to wait for
        """
        while True:
            if await self.acquire(count):
                return
            
            # Calculate time to wait for at least one token
            time_for_one_token = self.time_window_seconds / self.rate_limit
            await asyncio.sleep(time_for_one_token)


class BatchingMessageBus:
    """
    Message bus with batching and throttling support.
    Wraps a PersistentMessageBus with batching and throttling capabilities.
    """
    
    def __init__(self, 
                 message_bus: PersistentMessageBus,
                 batch_size: int = 10,
                 batch_timeout_seconds: float = 1.0,
                 rate_limit: int = 100,
                 time_window_seconds: float = 1.0):
        """
        Initialize the batching message bus.
        
        Args:
            message_bus: Underlying message bus to wrap
            batch_size: Number of messages to collect before processing
            batch_timeout_seconds: Maximum time to wait before processing an incomplete batch
            rate_limit: Maximum number of messages to process per time window
            time_window_seconds: Time window for rate limiting in seconds
        """
        self.message_bus = message_bus
        self.batcher = MessageBatcher(batch_size, batch_timeout_seconds)
        self.throttler = MessageThrottler(rate_limit, time_window_seconds)
        
        logger.info("Batching message bus initialized")
    
    async def start(self) -> None:
        """
        Start the batching message bus.
        """
        await self.batcher.start()
        logger.info("Batching message bus started")
    
    async def stop(self) -> None:
        """
        Stop the batching message bus.
        """
        await self.batcher.stop()
        logger.info("Batching message bus stopped")
    
    def register_batch_handler(self, topic: str, handler: BatchHandler) -> None:
        """
        Register a handler for a topic's batches.
        
        Args:
            topic: Topic to handle batches for
            handler: Function to handle batches
        """
        self.batcher.register_batch_handler(topic, handler)
    
    async def publish(self, topic: str, message: T) -> None:
        """
        Publish a message to a topic with batching and throttling.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        # Wait for throttling tokens
        await self.throttler.wait_for_tokens()
        
        # Add message to batch
        await self.batcher.add_message(topic, message)
    
    async def publish_immediate(self, topic: str, message: T) -> None:
        """
        Publish a message immediately, bypassing batching but not throttling.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        # Wait for throttling tokens
        await self.throttler.wait_for_tokens()
        
        # Publish message directly
        await self.message_bus.publish(topic, message)
    
    def subscribe(self, topic: str, callback: Callable[[T], Awaitable[None]]) -> None:
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Function to call when a message is received
        """
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
