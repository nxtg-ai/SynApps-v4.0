"""
Nested workflow support for the Meta-Agent Orchestrator
Enables hierarchical workflow composition and execution
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
from models.workflow import WorkflowNode, Workflow
from workflow.workflow_engine import WorkflowEngine, WorkflowExecutionContext

logger = logging.getLogger("workflow.nested_workflows")

# Type definitions
T = TypeVar('T', bound=AppletMessage)


class NestedWorkflowStatus(Enum):
    """Status of a nested workflow execution"""
    PENDING = "pending"       # Not yet started
    RUNNING = "running"       # Currently executing
    COMPLETED = "completed"   # Successfully completed
    FAILED = "failed"         # Failed to complete
    CANCELLED = "cancelled"   # Cancelled by parent workflow


@dataclass
class NestedWorkflowContext:
    """
    Context for a nested workflow execution
    """
    parent_workflow_id: str
    parent_step_id: str
    child_workflow_id: str
    execution_id: str
    status: NestedWorkflowStatus = NestedWorkflowStatus.PENDING
    result_message: Optional[T] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    # Mapping of parent context keys to child context keys
    context_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Mapping of child result keys to parent context keys
    result_mapping: Dict[str, str] = field(default_factory=dict)


class NestedWorkflowEngine:
    """
    Engine for managing nested workflows
    """
    
    def __init__(self, workflow_engine: WorkflowEngine):
        """
        Initialize the nested workflow engine
        
        Args:
            workflow_engine: Main workflow engine to use for executing workflows
        """
        self.workflow_engine = workflow_engine
        
        # Dictionary of parent workflow ID -> set of child workflow IDs
        self.parent_to_children: Dict[str, Set[str]] = {}
        
        # Dictionary of child workflow ID -> parent workflow ID
        self.child_to_parent: Dict[str, str] = {}
        
        # Dictionary of execution ID -> nested workflow context
        self.execution_contexts: Dict[str, NestedWorkflowContext] = {}
        
        # Dictionary of parent step ID -> nested workflow context
        self.step_contexts: Dict[str, NestedWorkflowContext] = {}
        
        logger.info("Nested workflow engine initialized")
    
    def register_nested_workflow(self, parent_workflow_id: str, parent_step_id: str,
                               child_workflow_id: str) -> None:
        """
        Register a nested workflow relationship
        
        Args:
            parent_workflow_id: ID of the parent workflow
            parent_step_id: ID of the step in the parent workflow
            child_workflow_id: ID of the child workflow
        """
        # Initialize parent-to-children mapping if needed
        if parent_workflow_id not in self.parent_to_children:
            self.parent_to_children[parent_workflow_id] = set()
        
        # Add child to parent's set
        self.parent_to_children[parent_workflow_id].add(child_workflow_id)
        
        # Add child-to-parent mapping
        self.child_to_parent[child_workflow_id] = parent_workflow_id
        
        logger.info(f"Registered nested workflow relationship: {parent_workflow_id} -> {child_workflow_id}")
    
    def get_child_workflows(self, parent_workflow_id: str) -> Set[str]:
        """
        Get all child workflows for a parent workflow
        
        Args:
            parent_workflow_id: ID of the parent workflow
            
        Returns:
            Set of child workflow IDs
        """
        return self.parent_to_children.get(parent_workflow_id, set())
    
    def get_parent_workflow(self, child_workflow_id: str) -> Optional[str]:
        """
        Get the parent workflow for a child workflow
        
        Args:
            child_workflow_id: ID of the child workflow
            
        Returns:
            Parent workflow ID, or None if the workflow is not a child
        """
        return self.child_to_parent.get(child_workflow_id)
    
    def is_nested_workflow(self, workflow_id: str) -> bool:
        """
        Check if a workflow is a nested workflow
        
        Args:
            workflow_id: ID of the workflow to check
            
        Returns:
            True if the workflow is a nested workflow, False otherwise
        """
        return workflow_id in self.child_to_parent
    
    async def execute_nested_workflow(self, parent_workflow_id: str, parent_step_id: str,
                                   child_workflow_id: str, input_message: T,
                                   context_mapping: Optional[Dict[str, str]] = None,
                                   result_mapping: Optional[Dict[str, str]] = None) -> str:
        """
        Execute a nested workflow
        
        Args:
            parent_workflow_id: ID of the parent workflow
            parent_step_id: ID of the step in the parent workflow
            child_workflow_id: ID of the child workflow
            input_message: Input message for the child workflow
            context_mapping: Mapping of parent context keys to child context keys
            result_mapping: Mapping of child result keys to parent context keys
            
        Returns:
            Execution ID for the nested workflow
        """
        # Register the nested workflow relationship if not already registered
        if child_workflow_id not in self.get_child_workflows(parent_workflow_id):
            self.register_nested_workflow(parent_workflow_id, parent_step_id, child_workflow_id)
        
        # Create a new execution ID
        execution_id = str(uuid.uuid4())
        
        # Create context for the nested workflow
        context = NestedWorkflowContext(
            parent_workflow_id=parent_workflow_id,
            parent_step_id=parent_step_id,
            child_workflow_id=child_workflow_id,
            execution_id=execution_id,
            context_mapping=context_mapping or {},
            result_mapping=result_mapping or {}
        )
        
        # Store the context
        self.execution_contexts[execution_id] = context
        self.step_contexts[parent_step_id] = context
        
        # Prepare input message with mapped context
        child_message = self._prepare_child_input(input_message, context)
        
        # Start the nested workflow execution asynchronously
        asyncio.create_task(self._execute_workflow(execution_id, child_message))
        
        logger.info(f"Started nested workflow execution: {execution_id} for workflow {child_workflow_id}")
        return execution_id
    
    def _prepare_child_input(self, message: T, context: NestedWorkflowContext) -> T:
        """
        Prepare input message for a child workflow by mapping context from parent
        
        Args:
            message: Input message
            context: Nested workflow context
            
        Returns:
            Prepared message with mapped context
        """
        # Create a copy of the message to avoid modifying the original
        child_message = copy.deepcopy(message)
        
        # Ensure the message has a context dictionary
        if not hasattr(child_message, 'context') or child_message.context is None:
            child_message.context = {}
        
        # Get the parent workflow execution context
        parent_context = self.workflow_engine.get_execution_context(context.parent_workflow_id)
        
        if parent_context and parent_context.current_message:
            parent_message = parent_context.current_message
            
            # Map context from parent to child
            if hasattr(parent_message, 'context') and isinstance(parent_message.context, dict):
                for parent_key, child_key in context.context_mapping.items():
                    if parent_key in parent_message.context:
                        child_message.context[child_key] = parent_message.context[parent_key]
        
        return child_message
    
    def _prepare_parent_result(self, parent_message: T, child_message: T, 
                             context: NestedWorkflowContext) -> T:
        """
        Prepare result message for a parent workflow by mapping results from child
        
        Args:
            parent_message: Parent message to update
            child_message: Child result message
            context: Nested workflow context
            
        Returns:
            Updated parent message with mapped results
        """
        # Create a copy of the parent message to avoid modifying the original
        result_message = copy.deepcopy(parent_message)
        
        # Ensure the message has a context dictionary
        if not hasattr(result_message, 'context') or result_message.context is None:
            result_message.context = {}
        
        # Map results from child to parent
        if hasattr(child_message, 'context') and isinstance(child_message.context, dict):
            for child_key, parent_key in context.result_mapping.items():
                if child_key in child_message.context:
                    result_message.context[parent_key] = child_message.context[child_key]
        
        return result_message
    
    async def _execute_workflow(self, execution_id: str, input_message: T) -> None:
        """
        Execute a nested workflow
        
        Args:
            execution_id: Execution ID
            input_message: Input message for the workflow
        """
        context = self.execution_contexts.get(execution_id)
        
        if not context:
            logger.error(f"No context found for execution ID: {execution_id}")
            return
        
        try:
            # Update status
            context.status = NestedWorkflowStatus.RUNNING
            context.start_time = asyncio.get_event_loop().time()
            
            # Execute the workflow
            result = await self.workflow_engine.execute_workflow(
                context.child_workflow_id, input_message
            )
            
            # Update context with result
            context.result_message = result
            context.status = NestedWorkflowStatus.COMPLETED
            context.end_time = asyncio.get_event_loop().time()
            
            # Process the result
            await self._process_nested_result(execution_id)
            
            logger.info(f"Completed nested workflow execution: {execution_id}")
        
        except Exception as e:
            # Update context with error
            context.status = NestedWorkflowStatus.FAILED
            context.error_message = str(e)
            context.end_time = asyncio.get_event_loop().time()
            
            logger.error(f"Error executing nested workflow {execution_id}: {str(e)}")
    
    async def _process_nested_result(self, execution_id: str) -> None:
        """
        Process the result of a nested workflow execution
        
        Args:
            execution_id: Execution ID
        """
        context = self.execution_contexts.get(execution_id)
        
        if not context or context.status != NestedWorkflowStatus.COMPLETED:
            return
        
        # Get the parent workflow execution context
        parent_context = self.workflow_engine.get_execution_context(context.parent_workflow_id)
        
        if not parent_context or not parent_context.current_message:
            logger.warning(f"Parent context not found for nested workflow {execution_id}")
            return
        
        # Map results from child to parent
        if context.result_message:
            updated_message = self._prepare_parent_result(
                parent_context.current_message, context.result_message, context
            )
            
            # Update the parent workflow's current message
            parent_context.current_message = updated_message
        
        # Resume the parent workflow
        await self.workflow_engine.resume_workflow_from_step(
            context.parent_workflow_id, context.parent_step_id, parent_context.current_message
        )
    
    async def cancel_nested_workflow(self, execution_id: str) -> bool:
        """
        Cancel a nested workflow execution
        
        Args:
            execution_id: Execution ID
            
        Returns:
            True if the workflow was cancelled, False otherwise
        """
        context = self.execution_contexts.get(execution_id)
        
        if not context or context.status not in [NestedWorkflowStatus.PENDING, NestedWorkflowStatus.RUNNING]:
            return False
        
        # Update status
        context.status = NestedWorkflowStatus.CANCELLED
        context.end_time = asyncio.get_event_loop().time()
        
        # Cancel the workflow execution
        await self.workflow_engine.cancel_workflow(context.child_workflow_id)
        
        logger.info(f"Cancelled nested workflow execution: {execution_id}")
        return True
    
    def get_execution_status(self, execution_id: str) -> Optional[NestedWorkflowStatus]:
        """
        Get the status of a nested workflow execution
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Status of the execution, or None if not found
        """
        context = self.execution_contexts.get(execution_id)
        return context.status if context else None
    
    def get_execution_context(self, execution_id: str) -> Optional[NestedWorkflowContext]:
        """
        Get the context of a nested workflow execution
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution context, or None if not found
        """
        return self.execution_contexts.get(execution_id)
    
    def get_step_execution(self, parent_workflow_id: str, 
                         parent_step_id: str) -> Optional[NestedWorkflowContext]:
        """
        Get the nested workflow execution for a parent step
        
        Args:
            parent_workflow_id: ID of the parent workflow
            parent_step_id: ID of the step in the parent workflow
            
        Returns:
            Execution context, or None if not found
        """
        context = self.step_contexts.get(parent_step_id)
        
        # Verify that the context belongs to the specified parent workflow
        if context and context.parent_workflow_id == parent_workflow_id:
            return context
        
        return None


class NestedWorkflowStep:
    """
    Workflow step that executes a nested workflow
    """
    
    def __init__(self, step_id: str, child_workflow_id: str,
               context_mapping: Optional[Dict[str, str]] = None,
               result_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize a nested workflow step
        
        Args:
            step_id: ID of the step
            child_workflow_id: ID of the child workflow
            context_mapping: Mapping of parent context keys to child context keys
            result_mapping: Mapping of child result keys to parent context keys
        """
        super().__init__(step_id)
        self.child_workflow_id = child_workflow_id
        self.context_mapping = context_mapping or {}
        self.result_mapping = result_mapping or {}
        self.nested_engine: Optional[NestedWorkflowEngine] = None
    
    def set_nested_engine(self, engine: NestedWorkflowEngine) -> None:
        """
        Set the nested workflow engine
        
        Args:
            engine: Nested workflow engine
        """
        self.nested_engine = engine
    
    async def execute(self, workflow_id: str, message: T) -> Optional[T]:
        """
        Execute the step by starting a nested workflow
        
        Args:
            workflow_id: ID of the parent workflow
            message: Input message
            
        Returns:
            None, as the result will be processed asynchronously
        """
        if not self.nested_engine:
            raise ValueError("Nested workflow engine not set")
        
        # Execute the nested workflow
        await self.nested_engine.execute_nested_workflow(
            parent_workflow_id=workflow_id,
            parent_step_id=self.step_id,
            child_workflow_id=self.child_workflow_id,
            input_message=message,
            context_mapping=self.context_mapping,
            result_mapping=self.result_mapping
        )
        
        # Return None to indicate that the step is not yet complete
        # The parent workflow will be resumed when the nested workflow completes
        return None
