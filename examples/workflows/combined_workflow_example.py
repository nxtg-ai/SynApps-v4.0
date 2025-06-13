"""
Combined Workflow Example

This example demonstrates the integration of both conditional branching and nested workflows
in a single workflow. It shows how to use these features together to create complex,
dynamic orchestration patterns.

The workflow processes customer support tickets, using conditional branching to route
tickets based on their category, and nested workflows to handle specialized processing
for each category.
"""

import asyncio
from typing import Dict, Any, Optional
import json
import logging
import uuid

from models.agent_message import AppletMessage
from models.workflow_models import WorkflowDefinition, WorkflowStep
from workflow.workflow_engine_extensions import EnhancedWorkflowEngine
from workflow.nested_workflows import NestedWorkflowStep
from workflow.conditional_branching import ConditionalBranch, BranchCondition, ConditionType

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("combined_workflow_example")

# Initialize the workflow engine
engine = EnhancedWorkflowEngine(message_bus=None, metrics_collector=None)

###################
# Technical Support Sub-Workflow
###################

async def diagnose_technical_issue(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Diagnose the technical issue"""
    logger.info("Diagnosing technical issue")
    
    issue_description = message.content
    
    # Simulate issue diagnosis
    if "login" in issue_description.lower():
        diagnosis = "Authentication issue"
        severity = "medium"
    elif "crash" in issue_description.lower() or "error" in issue_description.lower():
        diagnosis = "Application error"
        severity = "high"
    else:
        diagnosis = "General technical issue"
        severity = "low"
    
    # Update context and message
    context["diagnosis"] = diagnosis
    context["severity"] = severity
    message.metadata["diagnosis"] = diagnosis
    message.metadata["severity"] = severity
    
    return message

async def provide_technical_solution(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Provide a solution for the technical issue"""
    logger.info("Providing technical solution")
    
    diagnosis = context.get("diagnosis", "Unknown issue")
    severity = context.get("severity", "low")
    
    # Simulate solution generation
    if "Authentication issue" in diagnosis:
        solution = "Please try resetting your password and clearing browser cookies."
    elif "Application error" in diagnosis:
        solution = "Please update to the latest version and restart the application."
    else:
        solution = "Please try restarting the application and contact support if the issue persists."
    
    # Update message
    message.content = solution
    message.metadata["solution_provided"] = True
    message.metadata["resolution_type"] = "technical"
    
    return message

def create_technical_support_workflow() -> WorkflowDefinition:
    """Create a technical support workflow"""
    
    workflow = WorkflowDefinition(workflow_id="technical-support-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="diagnose_issue",
        handler=diagnose_technical_issue,
        next_step_id="provide_solution"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="provide_solution",
        handler=provide_technical_solution,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Billing Support Sub-Workflow
###################

async def analyze_billing_issue(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Analyze the billing issue"""
    logger.info("Analyzing billing issue")
    
    issue_description = message.content
    
    # Simulate billing analysis
    if "refund" in issue_description.lower():
        issue_type = "refund_request"
        urgency = "high"
    elif "charge" in issue_description.lower() and "wrong" in issue_description.lower():
        issue_type = "incorrect_charge"
        urgency = "high"
    elif "subscription" in issue_description.lower():
        issue_type = "subscription_issue"
        urgency = "medium"
    else:
        issue_type = "general_billing"
        urgency = "low"
    
    # Update context and message
    context["issue_type"] = issue_type
    context["urgency"] = urgency
    message.metadata["issue_type"] = issue_type
    message.metadata["urgency"] = urgency
    
    return message

async def resolve_billing_issue(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Resolve the billing issue"""
    logger.info("Resolving billing issue")
    
    issue_type = context.get("issue_type", "unknown")
    
    # Simulate resolution generation
    if issue_type == "refund_request":
        resolution = "We've processed your refund request. Please allow 3-5 business days for the amount to appear in your account."
    elif issue_type == "incorrect_charge":
        resolution = "We've investigated the incorrect charge and have issued a credit to your account."
    elif issue_type == "subscription_issue":
        resolution = "We've updated your subscription settings as requested. The changes will take effect in your next billing cycle."
    else:
        resolution = "We've noted your billing concern and our team will review your account within 24 hours."
    
    # Update message
    message.content = resolution
    message.metadata["solution_provided"] = True
    message.metadata["resolution_type"] = "billing"
    
    return message

def create_billing_support_workflow() -> WorkflowDefinition:
    """Create a billing support workflow"""
    
    workflow = WorkflowDefinition(workflow_id="billing-support-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="analyze_issue",
        handler=analyze_billing_issue,
        next_step_id="resolve_issue"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="resolve_issue",
        handler=resolve_billing_issue,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Account Support Sub-Workflow
###################

async def verify_account_issue(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Verify the account issue"""
    logger.info("Verifying account issue")
    
    issue_description = message.content
    
    # Simulate account verification
    if "password" in issue_description.lower() or "reset" in issue_description.lower():
        issue_type = "password_reset"
        security_check = "required"
    elif "email" in issue_description.lower() and "change" in issue_description.lower():
        issue_type = "email_change"
        security_check = "required"
    elif "delete" in issue_description.lower() or "close" in issue_description.lower():
        issue_type = "account_closure"
        security_check = "required"
    else:
        issue_type = "general_account"
        security_check = "optional"
    
    # Update context and message
    context["issue_type"] = issue_type
    context["security_check"] = security_check
    message.metadata["issue_type"] = issue_type
    message.metadata["security_check"] = security_check
    
    return message

async def process_account_change(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Process the account change"""
    logger.info("Processing account change")
    
    issue_type = context.get("issue_type", "unknown")
    security_check = context.get("security_check", "optional")
    
    # Simulate processing
    if security_check == "required":
        instructions = f"For security purposes, we need to verify your identity before processing your {issue_type}. "
        instructions += "Please check your email for a verification link."
        
        # In a real implementation, this would trigger an email
        message.metadata["verification_sent"] = True
    else:
        instructions = "We've processed your account change request."
        message.metadata["verification_sent"] = False
    
    # Update message
    message.content = instructions
    message.metadata["solution_provided"] = True
    message.metadata["resolution_type"] = "account"
    
    return message

def create_account_support_workflow() -> WorkflowDefinition:
    """Create an account support workflow"""
    
    workflow = WorkflowDefinition(workflow_id="account-support-workflow")
    
    workflow.add_step(WorkflowStep(
        step_id="verify_issue",
        handler=verify_account_issue,
        next_step_id="process_change"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="process_change",
        handler=process_account_change,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

###################
# Main Customer Support Workflow
###################

async def receive_ticket(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Receive and validate the support ticket"""
    logger.info("Receiving support ticket")
    
    # Store the original ticket in context
    context["original_ticket"] = message.content
    
    # Extract ticket category if provided in metadata
    category = message.metadata.get("category", None)
    
    # If no category is provided, attempt to categorize based on content
    if not category:
        content = message.content.lower()
        if any(word in content for word in ["error", "bug", "crash", "doesn't work", "broken"]):
            category = "technical"
        elif any(word in content for word in ["bill", "charge", "payment", "refund", "subscription"]):
            category = "billing"
        elif any(word in content for word in ["account", "password", "login", "email", "profile"]):
            category = "account"
        else:
            category = "general"
        
        # Update metadata with detected category
        message.metadata["category"] = category
        message.metadata["auto_categorized"] = True
    
    logger.info(f"Ticket categorized as: {category}")
    
    return message

async def process_general_inquiry(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Process a general inquiry that doesn't fit other categories"""
    logger.info("Processing general inquiry")
    
    inquiry = context.get("original_ticket", message.content)
    
    # Simulate general response
    response = "Thank you for contacting customer support. "
    response += "We've received your inquiry and will get back to you within 24 hours. "
    response += "For faster assistance, please consider providing more details about your issue."
    
    # Update message
    message.content = response
    message.metadata["resolution_type"] = "general"
    message.metadata["solution_provided"] = True
    
    return message

async def finalize_ticket(message: AppletMessage, context: Dict[str, Any]) -> AppletMessage:
    """Finalize the support ticket with appropriate metadata"""
    logger.info("Finalizing support ticket")
    
    # Get the original ticket and the resolution
    original_ticket = context.get("original_ticket", "")
    resolution = message.content
    category = message.metadata.get("category", "general")
    
    # Add ticket closing information
    closing_message = "\n\nThank you for contacting our support team. "
    closing_message += "If you have any further questions, please reply to this ticket. "
    closing_message += f"Your ticket reference is: TICKET-{uuid.uuid4().hex[:8].upper()}"
    
    # Update message
    message.content = resolution + closing_message
    message.metadata["ticket_status"] = "resolved"
    message.metadata["resolution_category"] = category
    message.metadata["resolution_time"] = "2025-06-13T11:15:36-07:00"  # Using the current time
    
    return message

def create_main_workflow() -> WorkflowDefinition:
    """Create the main customer support workflow with conditional branching and nested workflows"""
    
    workflow = WorkflowDefinition(workflow_id="customer-support-workflow")
    
    # Add regular steps
    workflow.add_step(WorkflowStep(
        step_id="receive_ticket",
        handler=receive_ticket,
        next_step_id=None  # Will be determined by conditional branching
    ))
    
    # Add nested workflow steps for each category
    workflow.add_step(NestedWorkflowStep(
        step_id="technical_support",
        child_workflow_id="technical-support-workflow",
        context_mapping={},  # No special mapping needed
        result_mapping={},  # No special mapping needed
        next_step_id="finalize_ticket"
    ))
    
    workflow.add_step(NestedWorkflowStep(
        step_id="billing_support",
        child_workflow_id="billing-support-workflow",
        context_mapping={},  # No special mapping needed
        result_mapping={},  # No special mapping needed
        next_step_id="finalize_ticket"
    ))
    
    workflow.add_step(NestedWorkflowStep(
        step_id="account_support",
        child_workflow_id="account-support-workflow",
        context_mapping={},  # No special mapping needed
        result_mapping={},  # No special mapping needed
        next_step_id="finalize_ticket"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="general_inquiry",
        handler=process_general_inquiry,
        next_step_id="finalize_ticket"
    ))
    
    workflow.add_step(WorkflowStep(
        step_id="finalize_ticket",
        handler=finalize_ticket,
        next_step_id=None  # End of workflow
    ))
    
    return workflow

# Register all workflows and set up branching
async def setup_workflows():
    """Set up all workflows, register them with the engine, and configure branching"""
    
    # Create and register the sub-workflows
    technical_workflow = create_technical_support_workflow()
    billing_workflow = create_billing_support_workflow()
    account_workflow = create_account_support_workflow()
    
    engine.register_workflow(technical_workflow)
    engine.register_workflow(billing_workflow)
    engine.register_workflow(account_workflow)
    
    # Create and register the main workflow
    main_workflow = create_main_workflow()
    engine.register_workflow(main_workflow)
    
    # Register the nested workflow relationships
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="customer-support-workflow",
        parent_step_id="technical_support",
        child_workflow_id="technical-support-workflow"
    )
    
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="customer-support-workflow",
        parent_step_id="billing_support",
        child_workflow_id="billing-support-workflow"
    )
    
    engine.nested_workflow_engine.register_nested_workflow(
        parent_workflow_id="customer-support-workflow",
        parent_step_id="account_support",
        child_workflow_id="account-support-workflow"
    )
    
    # Create conditional branching from the receive_ticket step
    branch = ConditionalBranch(
        source_step_id="receive_ticket",
        conditions=[
            BranchCondition(
                condition_type=ConditionType.METADATA_CHECK,
                target_step_id="technical_support",
                metadata_key="category",
                metadata_value="technical",
                metadata_comparison="equals"
            ),
            BranchCondition(
                condition_type=ConditionType.METADATA_CHECK,
                target_step_id="billing_support",
                metadata_key="category",
                metadata_value="billing",
                metadata_comparison="equals"
            ),
            BranchCondition(
                condition_type=ConditionType.METADATA_CHECK,
                target_step_id="account_support",
                metadata_key="category",
                metadata_value="account",
                metadata_comparison="equals"
            )
        ],
        default_target_step_id="general_inquiry"
    )
    
    # Register the branch with the engine
    engine.branching_engine.register_branch(main_workflow.workflow_id, branch)
    
    logger.info("All workflows and branches registered")
    return main_workflow.workflow_id

# Example usage
async def run_example():
    """Run the example workflow with test tickets"""
    
    workflow_id = await setup_workflows()
    
    # Test cases
    test_cases = [
        {
            "content": "The application keeps crashing when I try to save my work.",
            "metadata": {"ticket_id": "T-001", "priority": "high"}
        },
        {
            "content": "I was charged twice for my monthly subscription. Please refund one of the charges.",
            "metadata": {"ticket_id": "T-002", "priority": "medium"}
        },
        {
            "content": "I need to change my account email address.",
            "metadata": {"ticket_id": "T-003", "priority": "low"}
        },
        {
            "content": "I have a question about your company's services.",
            "metadata": {"ticket_id": "T-004", "priority": "low"}
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"\n\n--- Processing Support Ticket {i+1} ---")
        
        # Create a message
        message = AppletMessage(
            content=test_case["content"],
            metadata=test_case["metadata"]
        )
        
        # Execute the workflow
        result = await engine.execute_workflow(workflow_id, message)
        
        # Display the result
        logger.info(f"Ticket Resolution:")
        logger.info(f"Content: {result.content}")
        logger.info(f"Category: {result.metadata.get('category', 'unknown')}")
        logger.info(f"Resolution Type: {result.metadata.get('resolution_type', 'unknown')}")
        logger.info(f"Ticket Status: {result.metadata.get('ticket_status', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(run_example())
