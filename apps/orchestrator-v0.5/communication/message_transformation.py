"""
Message transformation pipeline for the Meta-Agent Orchestrator
Provides a framework for applying transformations to messages
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union, TypeVar

from models.agent_message import AppletMessage

logger = logging.getLogger("communication.message_transformation")

# Type definitions
T = TypeVar('T', bound=AppletMessage)
MessageTransformer = Callable[[T], Awaitable[Optional[T]]]
SyncMessageTransformer = Callable[[T], Optional[T]]

class MessageTransformationPipeline:
    """
    Pipeline for applying transformations to messages.
    Transformations are applied in the order they are added.
    """
    
    def __init__(self, name: str = "default"):
        """
        Initialize the message transformation pipeline.
        
        Args:
            name: Name of the pipeline for logging purposes
        """
        self.name = name
        self.transformers: List[MessageTransformer] = []
        logger.info(f"Message transformation pipeline '{name}' initialized")
    
    def add_transformer(self, transformer: Union[MessageTransformer, SyncMessageTransformer]) -> None:
        """
        Add a transformer to the pipeline.
        
        Args:
            transformer: Function that transforms a message
        """
        # If the transformer is synchronous, wrap it in an async function
        if not asyncio.iscoroutinefunction(transformer):
            async def async_wrapper(message: T) -> Optional[T]:
                return transformer(message)
            self.transformers.append(async_wrapper)
        else:
            self.transformers.append(transformer)
        
        logger.info(f"Added transformer to pipeline '{self.name}' (total: {len(self.transformers)})")
    
    async def transform(self, message: T) -> Optional[T]:
        """
        Apply all transformations to a message.
        
        Args:
            message: Message to transform
            
        Returns:
            Transformed message, or None if the message was filtered out
        """
        current_message = message
        
        for i, transformer in enumerate(self.transformers):
            if current_message is None:
                # Message was filtered out by a previous transformer
                logger.info(f"Message filtered out at step {i} in pipeline '{self.name}'")
                return None
            
            try:
                current_message = await transformer(current_message)
            except Exception as e:
                logger.error(f"Error in transformer {i} in pipeline '{self.name}': {str(e)}")
                # Continue with the original message if a transformer fails
        
        return current_message


class ContentFilterTransformer:
    """
    Transformer that filters messages based on content patterns.
    """
    
    def __init__(self, patterns: List[str], is_blacklist: bool = True):
        """
        Initialize the content filter transformer.
        
        Args:
            patterns: List of patterns to match
            is_blacklist: If True, messages matching patterns are filtered out
                          If False, only messages matching patterns are kept
        """
        self.patterns = patterns
        self.is_blacklist = is_blacklist
        logger.info(f"Content filter transformer initialized with {len(patterns)} patterns")
    
    def __call__(self, message: T) -> Optional[T]:
        """
        Filter a message based on content patterns.
        
        Args:
            message: Message to filter
            
        Returns:
            Message if it passes the filter, None otherwise
        """
        content = message.content.lower()
        matches_pattern = any(pattern.lower() in content for pattern in self.patterns)
        
        if self.is_blacklist and matches_pattern:
            # Blacklist mode: filter out messages that match patterns
            logger.info("Message filtered out by blacklist")
            return None
        elif not self.is_blacklist and not matches_pattern:
            # Whitelist mode: filter out messages that don't match patterns
            logger.info("Message filtered out by whitelist")
            return None
        
        return message


class MetadataEnrichmentTransformer:
    """
    Transformer that enriches messages with additional metadata.
    """
    
    def __init__(self, metadata_provider: Callable[[], Dict[str, Any]]):
        """
        Initialize the metadata enrichment transformer.
        
        Args:
            metadata_provider: Function that returns metadata to add
        """
        self.metadata_provider = metadata_provider
        logger.info("Metadata enrichment transformer initialized")
    
    def __call__(self, message: T) -> T:
        """
        Enrich a message with additional metadata.
        
        Args:
            message: Message to enrich
            
        Returns:
            Enriched message
        """
        # Get metadata from provider
        metadata = self.metadata_provider()
        
        # Add metadata to message
        for key, value in metadata.items():
            if key not in message.metadata:
                message.metadata[key] = value
        
        logger.info(f"Message enriched with {len(metadata)} metadata fields")
        return message


class ContentFormattingTransformer:
    """
    Transformer that formats message content.
    """
    
    def __init__(self, formatter: Callable[[str], str]):
        """
        Initialize the content formatting transformer.
        
        Args:
            formatter: Function that formats message content
        """
        self.formatter = formatter
        logger.info("Content formatting transformer initialized")
    
    def __call__(self, message: T) -> T:
        """
        Format a message's content.
        
        Args:
            message: Message to format
            
        Returns:
            Formatted message
        """
        # Format message content
        message.content = self.formatter(message.content)
        
        logger.info("Message content formatted")
        return message


class PriorityAdjustmentTransformer:
    """
    Transformer that adjusts message priority based on content or metadata.
    """
    
    def __init__(self, priority_calculator: Callable[[AppletMessage], int]):
        """
        Initialize the priority adjustment transformer.
        
        Args:
            priority_calculator: Function that calculates priority for a message
        """
        self.priority_calculator = priority_calculator
        logger.info("Priority adjustment transformer initialized")
    
    def __call__(self, message: T) -> T:
        """
        Adjust a message's priority.
        
        Args:
            message: Message to adjust
            
        Returns:
            Message with adjusted priority
        """
        # Only adjust priority if the message has a priority attribute
        if hasattr(message, 'priority'):
            # Calculate new priority
            new_priority = self.priority_calculator(message)
            
            # Set new priority
            message.priority = new_priority
            logger.info(f"Message priority adjusted to {new_priority}")
        
        return message


class MessageTransformationManager:
    """
    Manager for message transformation pipelines.
    """
    
    def __init__(self):
        """
        Initialize the message transformation manager.
        """
        self.pipelines: Dict[str, MessageTransformationPipeline] = {}
        logger.info("Message transformation manager initialized")
    
    def create_pipeline(self, name: str) -> MessageTransformationPipeline:
        """
        Create a new transformation pipeline.
        
        Args:
            name: Name of the pipeline
            
        Returns:
            New transformation pipeline
        """
        if name in self.pipelines:
            logger.warning(f"Overwriting existing pipeline: {name}")
        
        pipeline = MessageTransformationPipeline(name)
        self.pipelines[name] = pipeline
        
        logger.info(f"Created transformation pipeline: {name}")
        return pipeline
    
    def get_pipeline(self, name: str) -> Optional[MessageTransformationPipeline]:
        """
        Get a transformation pipeline by name.
        
        Args:
            name: Name of the pipeline
            
        Returns:
            Transformation pipeline, or None if not found
        """
        return self.pipelines.get(name)
    
    def remove_pipeline(self, name: str) -> bool:
        """
        Remove a transformation pipeline.
        
        Args:
            name: Name of the pipeline
            
        Returns:
            True if the pipeline was removed, False if it didn't exist
        """
        if name not in self.pipelines:
            logger.warning(f"Pipeline not found: {name}")
            return False
        
        del self.pipelines[name]
        logger.info(f"Removed pipeline: {name}")
        return True
    
    def get_pipeline_names(self) -> List[str]:
        """
        Get the names of all transformation pipelines.
        
        Returns:
            List of pipeline names
        """
        return list(self.pipelines.keys())
