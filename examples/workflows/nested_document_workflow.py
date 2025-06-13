"""
Nested Document Processing Workflow Example

This example demonstrates the use of nested workflows for document processing.
A main workflow handles the overall document processing, while specialized
sub-workflows handle specific tasks like text extraction, analysis, and summarization.
"""

import asyncio
from typing import Dict, Any, Optional
import json
import logging

from models.agent_message import AppletMessage
from models.workflow_models import WorkflowDefinition, WorkflowStep
from workflow.workflow_engine_extensions import EnhancedWorkflowEngine
from workflow.nested_workflows import NestedWorkflowStep

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nested_document_workflow")

# Initialize the workflow engine
engine = EnhancedWorkflowEngine(message_bus=None, metrics_collector=None)

###################
# Text Extraction Sub-Workflow
###################

async def extract_text(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Extract text from a document"""
    logger.info("Extracting text from document")
    
    # In a real implementation, this would extract text from various document formats
    document_type = message.metadata.get("document_type", "text")
    document_content = message.content
    
    # Simulate text extraction based on document type
    if document_type == "pdf":
        extracted_text = f"Extracted text from PDF: {document_content}"
    elif document_type == "image":
        extracted_text = f"OCR extracted text from image: {document_content}"
    else:
        extracted_text = f"Plain text: {document_content}"
    
    # Update message
    message.content = extracted_text
    message.metadata["extraction_successful"] = True
    
    return message

async def clean_text(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Clean and normalize the extracted text"""
    logger.info("Cleaning extracted text")
    
    text = message.content
    
    # Simulate text cleaning
    cleaned_text = text.replace("  ", " ").strip()
    
    # Update message
    message.content = cleaned_text
    message.metadata["cleaning_applied"] = True
    
    return message

def create_extraction_workflow() -> WorkflowDefinition:
    """Create a text extraction workflow"""
    
    workflow = WorkflowDefinition(workflow_id="text-extraction-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="extract_text",
        handler=extract_text,
        next_step_id="clean_text"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="clean_text",
        handler=clean_text,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Analysis Sub-Workflow
###################

async def analyze_sentiment(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Analyze sentiment of the text"""
    logger.info("Analyzing sentiment")
    
    text = message.content
    
    # Simulate sentiment analysis
    # In a real implementation, this would use an NLP model
    if "great" in text.lower() or "good" in text.lower() or "excellent" in text.lower():
        sentiment = "positive"
    elif "bad" in text.lower() or "poor" in text.lower() or "terrible" in text.lower():
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Update context and message
    context["sentiment"] = sentiment
    message.metadata["sentiment"] = sentiment
    
    return message

async def extract_keywords(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Extract keywords from the text"""
    logger.info("Extracting keywords")
    
    text = message.content
    
    # Simulate keyword extraction
    # In a real implementation, this would use NLP techniques
    words = text.split()
    keywords = list(set([word for word in words if len(word) > 5]))[:5]  # Simple heuristic
    
    # Update context and message
    context["keywords"] = keywords
    message.metadata["keywords"] = keywords
    
    return message

async def categorize_content(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Categorize the content"""
    logger.info("Categorizing content")
    
    text = message.content
    keywords = context.get("keywords", [])
    
    # Simulate content categorization
    # In a real implementation, this would use classification models
    categories = []
    if any(kw in ["finance", "money", "economic", "market"] for kw in keywords):
        categories.append("Finance")
    if any(kw in ["health", "medical", "wellness", "fitness"] for kw in keywords):
        categories.append("Health")
    if any(kw in ["technology", "software", "digital", "computer"] for kw in keywords):
        categories.append("Technology")
    
    if not categories:
        categories = ["General"]
    
    # Update context and message
    context["categories"] = categories
    message.metadata["categories"] = categories
    
    # Combine analysis results into the message content
    analysis_result = {
        "sentiment": context.get("sentiment", "unknown"),
        "keywords": keywords,
        "categories": categories
    }
    message.content = json.dumps(analysis_result)
    
    return message

def create_analysis_workflow() -> WorkflowDefinition:
    """Create a text analysis workflow"""
    
    workflow = WorkflowDefinition(workflow_id="text-analysis-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="analyze_sentiment",
        handler=analyze_sentiment,
        next_step_id="extract_keywords"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="extract_keywords",
        handler=extract_keywords,
        next_step_id="categorize_content"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="categorize_content",
        handler=categorize_content,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Summarization Sub-Workflow
###################

async def generate_summary(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Generate a summary of the document"""
    logger.info("Generating document summary")
    
    # Get the original text from the parent context
    original_text = context.get("cleaned_text", "")
    
    # Get analysis results from the message
    try:
        analysis_results = json.loads(message.content)
    except:
        analysis_results = {}
    
    # Simulate summary generation
    # In a real implementation, this would use summarization models
    summary = f"This document is about {', '.join(analysis_results.get('categories', ['general topics']))}. "
    summary += f"The overall sentiment is {analysis_results.get('sentiment', 'neutral')}. "
    summary += f"Key topics include: {', '.join(analysis_results.get('keywords', ['none identified']))}."
    
    # Update message
    message.content = summary
    
    return message

def create_summarization_workflow() -> WorkflowDefinition:
    """Create a summarization workflow"""
    
    workflow = WorkflowDefinition(workflow_id="summarization-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="generate_summary",
        handler=generate_summary,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Main Document Processing Workflow
###################

async def receive_document(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Receive and validate the document"""
    logger.info("Receiving document")
    
    # Store the original document in context
    context["original_document"] = message.content
    
    # Validate document (simple check for demonstration)
    if not message.content:
        message.metadata["error"] = "Empty document"
        message.metadata["valid"] = False
    else:
        message.metadata["valid"] = True
    
    return message

async def process_extraction_results(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Process the results from the text extraction workflow"""
    logger.info("Processing extraction results")
    
    # Store the cleaned text in context for later use
    context["cleaned_text"] = message.content
    
    return message

async def process_analysis_results(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Process the results from the text analysis workflow"""
    logger.info("Processing analysis results")
    
    # The analysis results are already in the message content as JSON
    # We'll pass them through to the summarization workflow
    
    return message

async def finalize_document(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Finalize the document processing"""
    logger.info("Finalizing document processing")
    
    # Get the original document and the summary
    original_document = context.get("original_document", "")
    summary = message.content
    
    # Create the final result
    final_result = {
        "original_length": len(original_document),
        "summary": summary,
        "metadata": message.metadata
    }
    
    # Update message
    message.content = json.dumps(final_result, indent=2)
    message.metadata["processing_complete"] = True
    
    return message

def create_main_workflow() -> WorkflowDefinition:
    """Create the main document processing workflow with nested workflows"""
    
    workflow = WorkflowDefinition(workflow_id="document-processing-workflow")
    
    # Add regular steps
    workflow.add_step(WorkflowStep(
        step_id="receive_document",
        handler=receive_document,
        next_step_id="extraction_workflow"  # Next is the nested extraction workflow
    ))
    
    # Add nested workflow step for text extraction
    workflow.add_step(NestedWorkflowStep(
        step_id="extraction_workflow",
        child_workflow_id="text-extraction-workflow",
        context_mapping={
            "original_document": "content"  # Map parent context to child input
        },
        result_mapping={},  # No special mapping needed for results
        next_step_id="process_extraction_results"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="process_extraction_results",
        handler=process_extraction_results,
        next_step_id="analysis_workflow"  # Next is the nested analysis workflow
    ))
    
    # Add nested workflow step for text analysis
    workflow.add_step(NestedWorkflowStep(
        step_id="analysis_workflow",
        child_workflow_id="text-analysis-workflow",
        context_mapping={},  # No special mapping needed
        result_mapping={},  # No special mapping needed
        next_step_id="process_analysis_results"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="process_analysis_results",
        handler=process_analysis_results,
        next_step_id="summarization_workflow"  # Next is the nested summarization workflow
    ))
    
    # Add nested workflow step for summarization
    workflow.add_step(NestedWorkflowStep(
        step_id="summarization_workflow",
        child_workflow_id="summarization-workflow",
        context_mapping={
            "cleaned_text": "original_text"  # Map parent context to child context
        },
        result_mapping={},  # No special mapping needed
        next_step_id="finalize_document"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="finalize_document",
        handler=finalize_document,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

# Register all workflows with the engine
async def setup_workflows():
    """Set up all workflows and register them with the engine"""
    
    # Create and register the sub-workflows
    extraction_workflow = create_extraction_workflow()
    analysis_workflow = create_analysis_workflow()
    summarization_workflow = create_summarization_workflow()
    
    engine.register_workflow(extraction_workflow)
    engine.register_workflow(analysis_workflow)
    engine.register_workflow(summarization_workflow)
    
    # Create and register the main workflow
    main_workflow = create_main_workflow()
    engine.register_workflow(main_workflow)
    
    # Register the nested workflow relationships
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="document-processing-workflow",
        parent_step_id="extraction_workflow",
        child_workflow_id="text-extraction-workflow"
    )
    
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="document-processing-workflow",
        parent_step_id="analysis_workflow",
        child_workflow_id="text-analysis-workflow"
    )
    
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="document-processing-workflow",
        parent_step_id="summarization_workflow",
        child_workflow_id="summarization-workflow"
    )
    
    logger.info("All workflows registered")
    return main_workflow.workflow_id

# Example usage
async def run_example():
    """Run the example workflow with test documents"""
    
    workflow_id = await setup_workflows()
    
    # Test cases
    test_cases = [
        {
            "content": "This is a great document about financial markets and economic trends. The stock market has been performing well recently.",
            "metadata": {"document_type": "text", "source": "financial_report"}
        },
        {
            "content": "The patient's health has improved significantly after the new treatment. Medical tests show positive results.",
            "metadata": {"document_type": "pdf", "source": "medical_record"}
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"\n\n--- Processing Document {i+1} ---")
        
        # Create a message
        message = AppletMessage(
            content=test_case["content"],
            metadata=test_case["metadata"]
        )
        
        # Execute the workflow
        result = await engine.execute_workflow(workflow_id, message)
        
        # Display the result
        try:
            result_json = json.loads(result.content)
            logger.info(f"Document processing complete:")
            logger.info(f"Original length: {result_json.get('original_length')}")
            logger.info(f"Summary: {result_json.get('summary')}")
            logger.info(f"Metadata: {json.dumps(result.metadata, indent=2)}")
        except:
            logger.info(f"Result: {result.content}")
            logger.info(f"Metadata: {json.dumps(result.metadata, indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_example())
