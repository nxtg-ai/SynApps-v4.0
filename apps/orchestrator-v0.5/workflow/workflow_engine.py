"""
Workflow Engine for the Meta-Agent Orchestrator
Core workflow execution and management functionality
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

logger = logging.getLogger("workflow.workflow_engine")

# Type definitions
T = TypeVar('T', bound=AppletMessage)

@dataclass
class WorkflowExecutionContext:
    """
    Context for workflow execution
    Maintains state during workflow execution
    """
    workflow_id: str
    current_node_id: Optional[str] = None
    visited_nodes: Set[str] = field(default_factory=set)
    execution_data: Dict[str, Any] = field(default_factory=dict)
    current_message: Optional[AppletMessage] = None
    
    def add_data(self, key: str, value: Any) -> None:
        """Add data to the execution context"""
        self.execution_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from the execution context"""
        return self.execution_data.get(key, default)


class WorkflowEngine:
    """
    Core workflow engine
    Handles workflow execution and management
    """
    
    def __init__(self):
        """Initialize the workflow engine"""
        self.workflows: Dict[str, Workflow] = {}
        self.execution_contexts: Dict[str, WorkflowExecutionContext] = {}
        self.update_callbacks: List[Callable[[str, Dict[str, Any]], Awaitable[None]]] = []
    
    def register_workflow(self, workflow: Workflow) -> None:
        """
        Register a workflow with the engine
        
        Args:
            workflow: The workflow to register
        """
        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.id}")
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Get a workflow by ID
        
        Args:
            workflow_id: The ID of the workflow to get
            
        Returns:
            The workflow, or None if not found
        """
        return self.workflows.get(workflow_id)
    
    def register_workflow_update_callback(
        self, callback: Callable[[str, Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Register a callback for workflow updates
        
        Args:
            callback: The callback function to register
        """
        self.update_callbacks.append(callback)
    
    async def notify_workflow_update(self, workflow_id: str, update_data: Dict[str, Any]) -> None:
        """
        Notify all registered callbacks of a workflow update
        
        Args:
            workflow_id: The ID of the workflow that was updated
            update_data: Data about the update
        """
        for callback in self.update_callbacks:
            try:
                await callback(workflow_id, update_data)
            except Exception as e:
                logger.error(f"Error in workflow update callback: {e}")
    
    async def execute_workflow(self, workflow_id: str, initial_message: Optional[T] = None) -> Optional[T]:
        """
        Execute a workflow
        
        Args:
            workflow_id: The ID of the workflow to execute
            initial_message: The initial message to start the workflow with
            
        Returns:
            The final result of the workflow execution
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None
        
        # Create execution context
        context = WorkflowExecutionContext(
            workflow_id=workflow_id,
            current_message=initial_message
        )
        self.execution_contexts[workflow_id] = context
        
        # Find start node
        start_node = None
        for node in workflow.nodes:
            if not any(edge.target_id == node.id for edge in workflow.edges):
                start_node = node
                break
        
        if not start_node:
            logger.error(f"No start node found for workflow: {workflow_id}")
            return None
        
        # Start execution from the start node
        context.current_node_id = start_node.id
        return await self._continue_workflow_execution(workflow_id, context)
    
    async def _continue_workflow_execution(self, workflow_id: str, context: WorkflowExecutionContext) -> Optional[T]:
        """
        Continue executing a workflow from its current state
        
        Args:
            workflow_id: The ID of the workflow to execute
            context: The current execution context
            
        Returns:
            The final result of the workflow execution
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None
        
        while context.current_node_id:
            # Get current node
            current_node = next((n for n in workflow.nodes if n.id == context.current_node_id), None)
            if not current_node:
                logger.error(f"Node not found: {context.current_node_id}")
                return None
            
            # Mark node as visited
            context.visited_nodes.add(current_node.id)
            
            # Execute node
            try:
                # In a real implementation, this would execute the node's function
                # For now, we'll just log it
                logger.info(f"Executing node: {current_node.id}")
                
                # Notify of node execution
                await self.notify_workflow_update(workflow_id, {
                    "type": "node_execution",
                    "node_id": current_node.id,
                    "status": "executing"
                })
                
                # Find next node
                next_node_id = None
                for edge in workflow.edges:
                    if edge.source_id == current_node.id:
                        next_node_id = edge.target_id
                        break
                
                # Update context
                context.current_node_id = next_node_id
                
                # Notify of node completion
                await self.notify_workflow_update(workflow_id, {
                    "type": "node_execution",
                    "node_id": current_node.id,
                    "status": "completed"
                })
                
                # If no next node, we're done
                if not next_node_id:
                    logger.info(f"Workflow completed: {workflow_id}")
                    await self.notify_workflow_update(workflow_id, {
                        "type": "workflow_execution",
                        "status": "completed"
                    })
                    return context.current_message
                
            except Exception as e:
                logger.error(f"Error executing node {current_node.id}: {e}")
                await self.notify_workflow_update(workflow_id, {
                    "type": "node_execution",
                    "node_id": current_node.id,
                    "status": "error",
                    "error": str(e)
                })
                return None
        
        return context.current_message
