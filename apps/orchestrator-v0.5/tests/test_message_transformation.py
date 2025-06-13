"""
Unit tests for the message transformation pipeline
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from models.agent_message import AppletMessage
from models.priority_message import PriorityMessage
from communication.message_transformation import (
    MessageTransformationPipeline,
    MessageTransformationManager,
    ContentFilterTransformer,
    MetadataEnrichmentTransformer,
    ContentFormattingTransformer,
    PriorityAdjustmentTransformer
)

class TestMessageTransformation:
    """Test suite for message transformation components"""
    
    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        """Test an empty transformation pipeline"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Transform message
        result = await pipeline.transform(message)
        
        # Verify message was returned unchanged
        assert result is message
        assert result.content == "Test message"
    
    @pytest.mark.asyncio
    async def test_sync_transformer(self):
        """Test a synchronous transformer"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create a transformer
        def uppercase_transformer(message):
            message.content = message.content.upper()
            return message
        
        # Add transformer to pipeline
        pipeline.add_transformer(uppercase_transformer)
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Transform message
        result = await pipeline.transform(message)
        
        # Verify message was transformed
        assert result is message
        assert result.content == "TEST MESSAGE"
    
    @pytest.mark.asyncio
    async def test_async_transformer(self):
        """Test an asynchronous transformer"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create a transformer
        async def reverse_transformer(message):
            message.content = message.content[::-1]
            return message
        
        # Add transformer to pipeline
        pipeline.add_transformer(reverse_transformer)
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Transform message
        result = await pipeline.transform(message)
        
        # Verify message was transformed
        assert result is message
        assert result.content == "egassem tseT"
    
    @pytest.mark.asyncio
    async def test_multiple_transformers(self):
        """Test multiple transformers in a pipeline"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create transformers
        def uppercase_transformer(message):
            message.content = message.content.upper()
            return message
        
        async def add_prefix_transformer(message):
            message.content = "PREFIX: " + message.content
            return message
        
        # Add transformers to pipeline
        pipeline.add_transformer(uppercase_transformer)
        pipeline.add_transformer(add_prefix_transformer)
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Transform message
        result = await pipeline.transform(message)
        
        # Verify message was transformed by both transformers
        assert result is message
        assert result.content == "PREFIX: TEST MESSAGE"
    
    @pytest.mark.asyncio
    async def test_filtering_transformer(self):
        """Test a transformer that filters messages"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create a transformer that filters messages containing "filter"
        def filter_transformer(message):
            if "filter" in message.content.lower():
                return None
            return message
        
        # Add transformer to pipeline
        pipeline.add_transformer(filter_transformer)
        
        # Create test messages
        message1 = AppletMessage(content="This message should be filtered")
        message2 = AppletMessage(content="This message should pass")
        
        # Transform messages
        result1 = await pipeline.transform(message1)
        result2 = await pipeline.transform(message2)
        
        # Verify filtering
        assert result1 is None
        assert result2 is message2
        assert result2.content == "This message should pass"
    
    @pytest.mark.asyncio
    async def test_transformer_exception(self):
        """Test handling of transformer exceptions"""
        # Create pipeline
        pipeline = MessageTransformationPipeline("test")
        
        # Create a transformer that raises an exception
        def error_transformer(message):
            raise ValueError("Test error")
        
        # Add transformer to pipeline
        pipeline.add_transformer(error_transformer)
        
        # Create a test message
        message = AppletMessage(content="Test message")
        
        # Transform message (should not raise exception)
        result = await pipeline.transform(message)
        
        # Verify message was returned unchanged
        assert result is None
    
    @pytest.mark.asyncio
    async def test_content_filter_transformer_blacklist(self):
        """Test content filter transformer in blacklist mode"""
        # Create transformer
        transformer = ContentFilterTransformer(["secret", "confidential"], is_blacklist=True)
        
        # Create test messages
        message1 = AppletMessage(content="This contains secret information")
        message2 = AppletMessage(content="This is public information")
        
        # Apply transformer
        result1 = transformer(message1)
        result2 = transformer(message2)
        
        # Verify filtering
        assert result1 is None
        assert result2 is message2
    
    @pytest.mark.asyncio
    async def test_content_filter_transformer_whitelist(self):
        """Test content filter transformer in whitelist mode"""
        # Create transformer
        transformer = ContentFilterTransformer(["approved", "public"], is_blacklist=False)
        
        # Create test messages
        message1 = AppletMessage(content="This is approved content")
        message2 = AppletMessage(content="This is restricted content")
        
        # Apply transformer
        result1 = transformer(message1)
        result2 = transformer(message2)
        
        # Verify filtering
        assert result1 is message1
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_metadata_enrichment_transformer(self):
        """Test metadata enrichment transformer"""
        # Create metadata provider
        def metadata_provider():
            return {
                "timestamp": "2025-06-12T16:30:00Z",
                "source": "test_suite"
            }
        
        # Create transformer
        transformer = MetadataEnrichmentTransformer(metadata_provider)
        
        # Create test message
        message = AppletMessage(content="Test message", metadata={"existing": "value"})
        
        # Apply transformer
        result = transformer(message)
        
        # Verify metadata was added
        assert result is message
        assert result.metadata["existing"] == "value"
        assert result.metadata["timestamp"] == "2025-06-12T16:30:00Z"
        assert result.metadata["source"] == "test_suite"
    
    @pytest.mark.asyncio
    async def test_content_formatting_transformer(self):
        """Test content formatting transformer"""
        # Create formatter
        def formatter(content):
            return content.replace("ugly", "beautiful")
        
        # Create transformer
        transformer = ContentFormattingTransformer(formatter)
        
        # Create test message
        message = AppletMessage(content="This is an ugly message")
        
        # Apply transformer
        result = transformer(message)
        
        # Verify content was formatted
        assert result is message
        assert result.content == "This is an beautiful message"
    
    @pytest.mark.asyncio
    async def test_priority_adjustment_transformer(self):
        """Test priority adjustment transformer"""
        # Create priority calculator
        def priority_calculator(message):
            # Set priority based on content
            if "urgent" in message.content.lower():
                return 10
            elif "important" in message.content.lower():
                return 7
            else:
                return 3
        
        # Create transformer
        transformer = PriorityAdjustmentTransformer(priority_calculator)
        
        # Create test messages
        message1 = PriorityMessage(content="Urgent alert", priority=5)
        message2 = PriorityMessage(content="Important notice", priority=5)
        message3 = PriorityMessage(content="Regular update", priority=5)
        
        # Apply transformer
        result1 = transformer(message1)
        result2 = transformer(message2)
        result3 = transformer(message3)
        
        # Verify priorities were adjusted
        assert result1 is message1
        assert result1.priority == 10
        assert result2 is message2
        assert result2.priority == 7
        assert result3 is message3
        assert result3.priority == 3
    
    def test_message_transformation_manager(self):
        """Test message transformation manager"""
        # Create manager
        manager = MessageTransformationManager()
        
        # Create pipelines
        pipeline1 = manager.create_pipeline("pipeline1")
        pipeline2 = manager.create_pipeline("pipeline2")
        
        # Verify pipelines were created
        assert manager.get_pipeline("pipeline1") is pipeline1
        assert manager.get_pipeline("pipeline2") is pipeline2
        
        # Verify pipeline names
        pipeline_names = manager.get_pipeline_names()
        assert "pipeline1" in pipeline_names
        assert "pipeline2" in pipeline_names
        
        # Remove a pipeline
        result = manager.remove_pipeline("pipeline1")
        
        # Verify pipeline was removed
        assert result is True
        assert manager.get_pipeline("pipeline1") is None
        assert "pipeline1" not in manager.get_pipeline_names()
        
        # Try to remove a non-existent pipeline
        result = manager.remove_pipeline("non_existent")
        
        # Verify operation failed
        assert result is False
