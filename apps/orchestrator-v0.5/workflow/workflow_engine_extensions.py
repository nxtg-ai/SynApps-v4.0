"""
Workflow engine extensions for the Meta-Agent Orchestrator
Integrates conditional branching and nested workflow support with the main workflow engine
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union, TypeVar, Set
from enum import Enum
import json
from dataclasses import dataclass, field
import uuid
import copy

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode, Workflow, WorkflowEdge
from core.meta_agent.orchestrator import MetaAgentOrchestrator
from workflow.conditional_branching import ConditionalBranchingEngine, ConditionalBranch, BranchCondition
from workflow.nested_workflows import NestedWorkflowEngine, NestedWorkflowStep

logger = logging.getLogger("workflow.workflow_engine_extensions")

# Type definitions
T = TypeVar('T', bound=AppletMessage)


class EnhancedWorkflowEngine(MetaAgentOrchestrator):
    """
    Enhanced workflow engine with support for conditional branching and nested workflows
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the enhanced workflow engine"""
        super().__init__(*args, **kwargs)
        
        # Initialize conditional branching engine
        self.branching_engine = ConditionalBranchingEngine()
        
        # Initialize nested workflow engine
        self.nested_workflow_engine = NestedWorkflowEngine(self)
        
        logger.info("Enhanced workflow engine initialized with conditional branching and nested workflow support")
    
    async def _get_next_step(self, workflow_id: str, current_step_id: str, message: T) -> Optional[str]:
        """
        Get the next step in a workflow, considering conditional branches
        
        Args:
            workflow_id: ID of the workflow
            current_step_id: ID of the current step
            message: Message being processed
            
        Returns:
            ID of the next step, or None if no next step
        """
        # Check for conditional branches first
        next_step = await self.branching_engine.get_next_step(workflow_id, current_step_id, message)
        
        # If a conditional branch matched, use that
        if next_step:
            logger.debug(f"Conditional branch matched, next step: {next_step}")
            return next_step
        
        # Otherwise, fall back to the default next step logic
        return await super()._get_next_step(workflow_id, current_step_id, message)
    
    async def execute_step(self, workflow_id: str, step_id: str, message: T) -> Optional[T]:
        """
        Execute a workflow step
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step to execute
            message: Input message for the step
            
        Returns:
            Output message from the step, or None if the step is asynchronous
        """
        # Get the workflow definition
        workflow = self._get_workflow(workflow_id)
        
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None
        
        # Get the step
        step = workflow.get_step(step_id)
        
        if not step:
            logger.error(f"Step not found in workflow {workflow_id}: {step_id}")
            return None
        
        # If this is a nested workflow step, set the nested engine
        if isinstance(step, NestedWorkflowStep):
            step.set_nested_engine(self.nested_workflow_engine)
        
        # Execute the step
        try:
            result = await step.execute(workflow_id, message)
            
            # If the step returned None (e.g., nested workflow step), 
            # the workflow will be resumed later when the nested workflow completes
            if result is None:
                logger.debug(f"Step {step_id} returned None, workflow will be resumed later")
                return None
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing step {step_id} in workflow {workflow_id}: {str(e)}")
            return None
    
    def register_conditional_branch(self, workflow_id: str, branch: ConditionalBranch) -> None:
        """
        Register a conditional branch for a workflow
        
        Args:
            workflow_id: ID of the workflow
            branch: Conditional branch to register
        """
        self.branching_engine.register_branch(workflow_id, branch)
    
    def create_content_branch(self, workflow_id: str, source_step_id: str, 
                            conditions: List[BranchCondition],
                            default_target_step_id: Optional[str] = None) -> ConditionalBranch:
        """
        Create and register a conditional branch based on content
        
        Args:
            workflow_id: ID of the workflow
            source_step_id: ID of the source step
            conditions: List of conditions
            default_target_step_id: Default target step ID
            
        Returns:
            Created branch
        """
        branch = self.branching_engine.create_branch(
            workflow_id, source_step_id, conditions, default_target_step_id
        )
        return branch
    
    def register_nested_workflow(self, parent_workflow_id: str, parent_step_id: str,
                               child_workflow_id: str) -> None:
        """
        Register a nested workflow relationship
        
        Args:
            parent_workflow_id: ID of the parent workflow
            parent_step_id: ID of the step in the parent workflow
            child_workflow_id: ID of the child workflow
        """
        self.nested_workflow_engine.register_nested_workflow(
            parent_workflow_id, parent_step_id, child_workflow_id
        )
    
    def create_nested_workflow_step(self, step_id: str, child_workflow_id: str,
                                  context_mapping: Optional[Dict[str, str]] = None,
                                  result_mapping: Optional[Dict[str, str]] = None) -> NestedWorkflowStep:
        """
        Create a nested workflow step
        
        Args:
            step_id: ID of the step
            child_workflow_id: ID of the child workflow
            context_mapping: Mapping of parent context keys to child context keys
            result_mapping: Mapping of child result keys to parent context keys
            
        Returns:
            Created step
        """
        step = NestedWorkflowStep(
            step_id=step_id,
            child_workflow_id=child_workflow_id,
            context_mapping=context_mapping,
            result_mapping=result_mapping
        )
        
        # Set the nested engine
        step.set_nested_engine(self.nested_workflow_engine)
        
        return step
    
    async def resume_workflow_from_step(self, workflow_id: str, step_id: str, message: T) -> Optional[T]:
        """
        Resume a workflow from a specific step
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step to resume from
            message: Input message
            
        Returns:
            Final result of the workflow, or None if the workflow is still running
        """
        # Get the workflow execution context
        context = self.get_execution_context(workflow_id)
        
        if not context:
            logger.error(f"No execution context found for workflow {workflow_id}")
            return None
        
        # Update the current step and message
        context.current_step_id = step_id
        context.current_message = message
        
        # Continue the workflow execution
        return await self._continue_workflow_execution(workflow_id, context)
    
    async def _continue_workflow_execution(self, workflow_id: str, context: Dict[str, Any]) -> Optional[T]:
        """
        Continue executing a workflow from its current state
        
        Args:
            workflow_id: ID of the workflow
            context: Workflow execution context
            
        Returns:
            Final result of the workflow, or None if the workflow is still running
        """
        # Get the workflow definition
        workflow = self._get_workflow(workflow_id)
        
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None
        
        # Continue executing steps until the workflow completes or pauses
        while context.current_step_id:
            # Get the next step
            next_step_id = await self._get_next_step(
                workflow_id, context.current_step_id, context.current_message
            )
            
            if not next_step_id:
                # No next step, workflow is complete
                logger.info(f"Workflow {workflow_id} completed")
                return context.current_message
            
            # Update the current step
            context.current_step_id = next_step_id
            
            # Execute the step
            result = await self.execute_step(
                workflow_id, context.current_step_id, context.current_message
            )
            
            if result is None:
                # Step is asynchronous (e.g., nested workflow), pause execution
                logger.debug(f"Workflow {workflow_id} paused at step {context.current_step_id}")
                return None
            
            # Update the current message with the step result
            context.current_message = result
        
        # Workflow is complete
        logger.info(f"Workflow {workflow_id} completed")
        return context.current_message


class BranchingWorkflowStep:
    """
    Workflow step that supports conditional branching
    """
    
    def __init__(self, step_id: str, branching_engine: Optional[ConditionalBranchingEngine] = None):
        """
        Initialize a branching workflow step
        
        Args:
            step_id: ID of the step
            branching_engine: Conditional branching engine
        """
        self.step_id = step_id
        self.branching_engine = branching_engine
        self.branches: List[ConditionalBranch] = []
    
    def set_branching_engine(self, engine: ConditionalBranchingEngine) -> None:
        """
        Set the conditional branching engine
        
        Args:
            engine: Conditional branching engine
        """
        self.branching_engine = engine
    
    def add_branch(self, workflow_id: str, branch: ConditionalBranch) -> None:
        """
        Add a conditional branch
        
        Args:
            workflow_id: ID of the workflow
            branch: Conditional branch to add
        """
        if self.branching_engine:
            self.branching_engine.register_branch(workflow_id, branch)
        
        self.branches.append(branch)
    
    async def execute(self, workflow_id: str, message: T) -> T:
        """
        Execute the step
        
        Args:
            workflow_id: ID of the workflow
            message: Input message
            
        Returns:
            Output message (same as input for this step type)
        """
        # This step doesn't modify the message, it just enables branching
        return message
