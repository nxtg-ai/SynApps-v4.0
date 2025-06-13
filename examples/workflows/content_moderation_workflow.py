"""
Content Moderation Workflow Example

This example demonstrates the use of conditional branching in a content moderation workflow.
The workflow processes user-submitted content and routes it to different handling paths
based on moderation results.
"""

import asyncio
from typing import Dict, Any
import json
import logging

from models.agent_message import AppletMessage
from models.workflow_models import WorkflowDefinition, WorkflowStep
from workflow.workflow_engine_extensions import EnhancedWorkflowEngine
from workflow.conditional_branching import ConditionalBranch, BranchCondition, ConditionType

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("content_moderation_workflow")

# Initialize the workflow engine
engine = EnhancedWorkflowEngine(message_bus=None, metrics_collector=None)

# Define the workflow steps
async def receive_content(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Receive user-submitted content"""
    logger.info("Receiving user content")
    return message

async def moderate_content(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Check content against moderation rules"""
    logger.info("Moderating content")
    
    # Simulate content moderation
    content = message.content.lower()
    
    # Check for prohibited content
    prohibited_terms = ["offensive", "inappropriate", "harmful"]
    flagged = any(term in content for term in prohibited_terms)
    
    # Check for content requiring review
    review_terms = ["review", "check", "verify"]
    needs_review = any(term in content for term in review_terms)
    
    # Update message metadata with moderation results
    message.metadata["moderation_flagged"] = flagged
    message.metadata["moderation_needs_review"] = needs_review
    message.metadata["moderation_status"] = "flagged" if flagged else "needs_review" if needs_review else "approved"
    
    return message

async def process_approved_content(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Process content that passed moderation"""
    logger.info("Processing approved content")
    message.content = f"APPROVED: {message.content}"
    return message

async def queue_for_review(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Queue content for human review"""
    logger.info("Queuing content for human review")
    message.content = f"REVIEW NEEDED: {message.content}"
    message.metadata["review_priority"] = "medium"
    return message

async def reject_content(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Reject prohibited content"""
    logger.info("Rejecting prohibited content")
    message.content = f"REJECTED: {message.content}"
    message.metadata["rejection_reason"] = "Content violates community guidelines"
    return message

async def notify_user(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Send notification to the user about content status"""
    logger.info(f"Notifying user: {message.metadata.get('moderation_status', 'unknown')}")
    
    status = message.metadata.get("moderation_status", "unknown")
    if status == "approved":
        message.content = f"Your content has been approved and published."
    elif status == "needs_review":
        message.content = f"Your content has been queued for review. We'll notify you once the review is complete."
    else:  # flagged/rejected
        message.content = f"Your content has been rejected as it appears to violate our community guidelines."
    
    return message

# Create the workflow definition
def create_content_moderation_workflow() -> WorkflowDefinition:
    """Create a content moderation workflow with conditional branching"""
    
    # Create the workflow
    workflow = WorkflowDefinition(workflow_id="content-moderation")
    
    # Add steps
    workflow.add_step(WorkflowStep(
        step_id="receive_content",
        handler=receive_content,
        next_step_id="moderate_content"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="moderate_content",
        handler=moderate_content,
        # We'll override this with conditional branching
        next_step_id=None
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="process_approved",
        handler=process_approved_content,
        next_step_id="notify_user"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="queue_for_review",
        handler=queue_for_review,
        next_step_id="notify_user"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="reject_content",
        handler=reject_content,
        next_step_id="notify_user"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="notify_user",
        handler=notify_user,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

# Register workflow with the engine
async def setup_workflow():
    """Set up the workflow with conditional branching"""
    
    # Create and register the workflow
    workflow = create_content_moderation_workflow()
    engine.register_workflow(workflow)
    
    # Create conditional branching from the moderate_content step
    branch = ConditionalBranch(
        source_step_id="moderate_content",
        conditions=[
            BranchCondition(
                condition_type=ConditionType.METADATA_CHECK,
                target_step_id="reject_content",
                metadata_key="moderation_status",
                metadata_value="flagged",
                metadata_comparison="equals"
            ),
            BranchCondition(
                condition_type=ConditionType.METADATA_CHECK,
                target_step_id="queue_for_review",
                metadata_key="moderation_status",
                metadata_value="needs_review",
                metadata_comparison="equals"
            )
        ],
        default_target_step_id="process_approved"
    )
    
    # Register the branch with the engine
    engine.branching_engine.register_branch(workflow.workflow_id, branch)
    
    logger.info(f"Content moderation workflow registered with ID: {workflow.workflow_id}")
    return workflow.workflow_id

# Example usage
async def run_example():
    """Run the example workflow with different inputs"""
    
    workflow_id = await setup_workflow()
    
    # Test cases
    test_cases = [
        "This is normal content that should be approved.",
        "This content contains offensive language and should be rejected.",
        "Please review this content before publishing."
    ]
    
    for content in test_cases:
        logger.info(f"\n\n--- Testing with content: {content} ---")
        
        # Create a message
        message = AppletMessage(
            content=content,
            metadata={"source": "user_submission", "timestamp": "2025-06-13T10:48:35-07:00"}
        )
        
        # Execute the workflow
        result = await engine.execute_workflow(workflow_id, message)
        
        # Display the result
        logger.info(f"Final status: {result.metadata.get('moderation_status', 'unknown')}")
        logger.info(f"Final message: {result.content}")
        logger.info(f"Final metadata: {json.dumps(result.metadata, indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_example())
