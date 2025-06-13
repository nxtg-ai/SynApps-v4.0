"""
Enhanced workflow API routes for the Meta-Agent Orchestrator
Exposes conditional branching and nested workflow capabilities to the frontend
"""

import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, status
from pydantic import BaseModel, Field
import uuid
import json
import asyncio

from models.workflow_models import (
    WorkflowDefinition, 
    WorkflowStep, 
    WorkflowExecutionContext
)
from models.agent_message import AppletMessage
from workflow.conditional_branching import (
    ConditionalBranchingEngine, 
    ConditionalBranch, 
    BranchCondition,
    ConditionType
)
from workflow.nested_workflows import (
    NestedWorkflowEngine, 
    NestedWorkflowStep,
    NestedWorkflowStatus
)
from workflow.workflow_engine_extensions import EnhancedWorkflowEngine

logger = logging.getLogger("api.workflow_enhanced_routes")

# API Models for request/response
class ConditionRequest(BaseModel):
    """Request model for creating a condition"""
    condition_type: str
    target_step_id: str
    content_pattern: Optional[str] = None
    pattern_is_regex: bool = False
    case_sensitive: bool = True
    metadata_key: Optional[str] = None
    metadata_value: Optional[Any] = None
    metadata_comparison: Optional[str] = None
    context_key: Optional[str] = None
    context_value: Optional[Any] = None
    context_comparison: Optional[str] = None


class BranchRequest(BaseModel):
    """Request model for creating a branch"""
    source_step_id: str
    conditions: List[ConditionRequest]
    default_target_step_id: Optional[str] = None


class NestedWorkflowRequest(BaseModel):
    """Request model for creating a nested workflow step"""
    parent_step_id: str
    child_workflow_id: str
    context_mapping: Dict[str, str] = Field(default_factory=dict)
    result_mapping: Dict[str, str] = Field(default_factory=dict)


class BranchResponse(BaseModel):
    """Response model for a branch"""
    branch_id: str
    source_step_id: str
    conditions: List[Dict[str, Any]]
    default_target_step_id: Optional[str] = None


class NestedWorkflowResponse(BaseModel):
    """Response model for a nested workflow"""
    parent_step_id: str
    child_workflow_id: str
    context_mapping: Dict[str, str]
    result_mapping: Dict[str, str]


class NestedWorkflowStatusResponse(BaseModel):
    """Response model for nested workflow status"""
    execution_id: str
    parent_workflow_id: str
    parent_step_id: str
    child_workflow_id: str
    status: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None


# Create router
router = APIRouter(prefix="/api/workflows/enhanced", tags=["enhanced-workflows"])


# Helper function to get the orchestrator from the request
def get_orchestrator(request: Request) -> EnhancedWorkflowEngine:
    """Get the orchestrator from the request"""
    orchestrator = request.app.state.orchestrator
    
    if not isinstance(orchestrator, EnhancedWorkflowEngine):
        raise HTTPException(
            status_code=500,
            detail="Orchestrator does not support enhanced workflow features"
        )
    
    return orchestrator


@router.post("/{workflow_id}/branches", response_model=BranchResponse)
async def create_branch(
    workflow_id: str,
    branch_request: BranchRequest,
    request: Request
):
    """
    Create a conditional branch in a workflow
    """
    orchestrator = get_orchestrator(request)
    
    # Convert condition requests to BranchCondition objects
    conditions = []
    for condition_req in branch_request.conditions:
        condition_type = getattr(ConditionType, condition_req.condition_type.upper())
        
        if condition_type == ConditionType.CONTENT_MATCH:
            condition = orchestrator.branching_engine.create_content_condition(
                target_step_id=condition_req.target_step_id,
                content_pattern=condition_req.content_pattern,
                pattern_is_regex=condition_req.pattern_is_regex,
                case_sensitive=condition_req.case_sensitive
            )
        
        elif condition_type == ConditionType.METADATA_CHECK:
            condition = orchestrator.branching_engine.create_metadata_condition(
                target_step_id=condition_req.target_step_id,
                metadata_key=condition_req.metadata_key,
                metadata_value=condition_req.metadata_value,
                comparison=condition_req.metadata_comparison
            )
        
        elif condition_type == ConditionType.CONTEXT_CHECK:
            condition = orchestrator.branching_engine.create_context_condition(
                target_step_id=condition_req.target_step_id,
                context_key=condition_req.context_key,
                context_value=condition_req.context_value,
                comparison=condition_req.context_comparison
            )
        
        elif condition_type == ConditionType.ALWAYS:
            condition = orchestrator.branching_engine.create_default_condition(
                target_step_id=condition_req.target_step_id
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported condition type: {condition_req.condition_type}"
            )
        
        conditions.append(condition)
    
    # Create the branch
    branch = orchestrator.create_content_branch(
        workflow_id=workflow_id,
        source_step_id=branch_request.source_step_id,
        conditions=conditions,
        default_target_step_id=branch_request.default_target_step_id
    )
    
    # Convert branch to response model
    response = {
        "branch_id": branch.branch_id,
        "source_step_id": branch.source_step_id,
        "conditions": [
            {
                "condition_type": condition.condition_type.value,
                "target_step_id": condition.target_step_id,
                "content_pattern": condition.content_pattern,
                "pattern_is_regex": condition.pattern_is_regex,
                "case_sensitive": condition.case_sensitive,
                "metadata_key": condition.metadata_key,
                "metadata_value": condition.metadata_value,
                "metadata_comparison": condition.metadata_comparison,
                "context_key": condition.context_key,
                "context_value": condition.context_value,
                "context_comparison": condition.context_comparison
            }
            for condition in branch.conditions
        ],
        "default_target_step_id": branch.default_target_step_id
    }
    
    return response


@router.get("/{workflow_id}/branches", response_model=List[BranchResponse])
async def get_branches(workflow_id: str, request: Request):
    """
    Get all branches for a workflow
    """
    orchestrator = get_orchestrator(request)
    
    # Get branches for the workflow
    branches = orchestrator.branching_engine.get_branches_for_workflow(workflow_id)
    
    # Convert branches to response models
    responses = []
    for branch in branches:
        response = {
            "branch_id": branch.branch_id,
            "source_step_id": branch.source_step_id,
            "conditions": [
                {
                    "condition_type": condition.condition_type.value,
                    "target_step_id": condition.target_step_id,
                    "content_pattern": condition.content_pattern,
                    "pattern_is_regex": condition.pattern_is_regex,
                    "case_sensitive": condition.case_sensitive,
                    "metadata_key": condition.metadata_key,
                    "metadata_value": condition.metadata_value,
                    "metadata_comparison": condition.metadata_comparison,
                    "context_key": condition.context_key,
                    "context_value": condition.context_value,
                    "context_comparison": condition.context_comparison
                }
                for condition in branch.conditions
            ],
            "default_target_step_id": branch.default_target_step_id
        }
        
        responses.append(response)
    
    return responses


@router.post("/{workflow_id}/nested", response_model=NestedWorkflowResponse)
async def create_nested_workflow(
    workflow_id: str,
    nested_request: NestedWorkflowRequest,
    request: Request
):
    """
    Create a nested workflow step
    """
    orchestrator = get_orchestrator(request)
    
    # Register the nested workflow relationship
    orchestrator.register_nested_workflow(
        parent_workflow_id=workflow_id,
        parent_step_id=nested_request.parent_step_id,
        child_workflow_id=nested_request.child_workflow_id
    )
    
    # Create the nested workflow step
    step = orchestrator.create_nested_workflow_step(
        step_id=nested_request.parent_step_id,
        child_workflow_id=nested_request.child_workflow_id,
        context_mapping=nested_request.context_mapping,
        result_mapping=nested_request.result_mapping
    )
    
    # Convert to response model
    response = {
        "parent_step_id": nested_request.parent_step_id,
        "child_workflow_id": nested_request.child_workflow_id,
        "context_mapping": nested_request.context_mapping,
        "result_mapping": nested_request.result_mapping
    }
    
    return response


@router.get("/{workflow_id}/nested/{step_id}/status", response_model=NestedWorkflowStatusResponse)
async def get_nested_workflow_status(
    workflow_id: str,
    step_id: str,
    request: Request
):
    """
    Get the status of a nested workflow execution
    """
    orchestrator = get_orchestrator(request)
    
    # Get the execution context for the step
    context = orchestrator.nested_workflow_engine.get_step_execution(workflow_id, step_id)
    
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"No nested workflow execution found for step {step_id} in workflow {workflow_id}"
        )
    
    # Convert to response model
    response = {
        "execution_id": context.execution_id,
        "parent_workflow_id": context.parent_workflow_id,
        "parent_step_id": context.parent_step_id,
        "child_workflow_id": context.child_workflow_id,
        "status": context.status.value,
        "start_time": context.start_time,
        "end_time": context.end_time,
        "error_message": context.error_message
    }
    
    return response


@router.post("/{workflow_id}/nested/{step_id}/cancel")
async def cancel_nested_workflow(
    workflow_id: str,
    step_id: str,
    request: Request
):
    """
    Cancel a nested workflow execution
    """
    orchestrator = get_orchestrator(request)
    
    # Get the execution context for the step
    context = orchestrator.nested_workflow_engine.get_step_execution(workflow_id, step_id)
    
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"No nested workflow execution found for step {step_id} in workflow {workflow_id}"
        )
    
    # Cancel the execution
    cancelled = await orchestrator.nested_workflow_engine.cancel_nested_workflow(context.execution_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to cancel nested workflow execution {context.execution_id}"
        )
    
    return {"status": "cancelled"}


@router.post("/{workflow_id}/execute-with-branching")
async def execute_workflow_with_branching(
    workflow_id: str,
    request: Request,
    input_message: Dict[str, Any]
):
    """
    Execute a workflow with conditional branching support
    """
    orchestrator = get_orchestrator(request)
    
    # Create an AppletMessage from the input
    message = AppletMessage(
        content=input_message.get("content", ""),
        metadata=input_message.get("metadata", {}),
        context=input_message.get("context", {})
    )
    
    # Execute the workflow
    try:
        result = await orchestrator.execute_workflow(workflow_id, message)
        
        if not result:
            return {"status": "running"}
        
        return {
            "status": "completed",
            "result": {
                "content": result.content,
                "metadata": result.metadata,
                "context": result.context
            }
        }
    
    except Exception as e:
        logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing workflow: {str(e)}"
        )
