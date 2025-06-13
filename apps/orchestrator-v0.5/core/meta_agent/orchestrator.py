"""
Meta-Agent Orchestrator
Core implementation of the LLM-powered Meta-Agent that orchestrates AI agents.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable

from models.agent_message import AppletMessage
from models.workflow import Workflow, WorkflowNode
from core.validation.schema_validator import validate_message
from core.validation.output_enforcer import OutputEnforcer
from core.meta_agent.system_prompt_injector import SystemPromptInjector
from core.governance.rule_engine import RuleEngine

logger = logging.getLogger("meta_agent.orchestrator")

class MetaAgentOrchestrator:
    """
    The Meta-Agent Orchestrator is the core component that coordinates
    AI agents, injects system prompts, validates outputs, and ensures
    deterministic execution.
    """
    
    def __init__(self, message_bus=None, metrics_collector=None):
        """Initialize the Meta-Agent Orchestrator
        
        Args:
            message_bus: The message bus for agent communication
            metrics_collector: The metrics collector for monitoring
        """
        self.rule_engine = RuleEngine()
        self.active_workflows: Dict[str, Workflow] = {}
        self.message_history: Dict[str, List[AppletMessage]] = {}
        self.message_bus = message_bus
        self.metrics_collector = metrics_collector
        self.workflow_update_callbacks: List[Callable[[str, Dict[str, Any]], Awaitable[None]]] = []
        self.system_prompt_injector = SystemPromptInjector(self.rule_engine)
        self.output_enforcer = OutputEnforcer()
        logger.info("Meta-Agent Orchestrator initialized")
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow by orchestrating its agents with meta-prompts
        and structured output validation.
        
        Args:
            workflow_id: The ID of the workflow to execute
            
        Returns:
            Execution results and metrics
        """
        try:
            logger.info(f"Starting execution of workflow {workflow_id}")
            
            # Load the workflow from the database
            workflow = await self._load_workflow(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found in database")
                raise ValueError(f"Workflow {workflow_id} not found")
            
            logger.info(f"Loaded workflow {workflow_id} with {len(workflow.nodes)} nodes and {len(workflow.edges)} edges")
            
            # Store workflow in active workflows
            self.active_workflows[workflow_id] = workflow
            self.message_history[workflow_id] = []
            
            # Find the start node
            start_node = self._find_start_node(workflow)
            if not start_node:
                logger.error(f"No start node found in workflow {workflow_id}")
                logger.error(f"Available node types: {[node.type for node in workflow.nodes]}")
                raise ValueError(f"No start node found in workflow {workflow_id}")
            
            logger.info(f"Starting execution from node {start_node.id} ({start_node.name})")
            
            # Execute the workflow starting from the start node
            results = await self._execute_node(workflow_id, start_node.id)
            
            # Create status object
            status = {
                "workflow_id": workflow_id,
                "status": "completed",
                "results": results,
                "metrics": self._calculate_metrics(workflow_id)
            }
            
            logger.info(f"Workflow {workflow_id} execution completed successfully")
            
            # Notify callbacks about workflow completion
            await self._notify_workflow_update(workflow_id, status)
            
            return status
            
        except ValueError as e:
            # Handle expected errors
            logger.error(f"Workflow execution error: {str(e)}")
            
            # Create error status
            error_status = {
                "workflow_id": workflow_id,
                "status": "error",
                "error": str(e),
                "results": None,
                "metrics": None
            }
            
            # Notify callbacks about the error
            await self._notify_workflow_update(workflow_id, error_status)
            
            # Re-raise the exception
            raise
            
        except Exception as e:
            # Handle unexpected errors
            logger.exception(f"Unexpected error during workflow execution: {str(e)}")
            
            # Create error status
            error_status = {
                "workflow_id": workflow_id,
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "results": None,
                "metrics": None
            }
            
            # Notify callbacks about the error
            await self._notify_workflow_update(workflow_id, error_status)
            
            # Re-raise the exception
            raise
    
    async def _execute_node(self, workflow_id: str, node_id: str) -> Dict[str, Any]:
        """
        Execute a single node in the workflow with meta-prompt injection
        and output validation.
        
        Args:
            workflow_id: The ID of the workflow
            node_id: The ID of the node to execute
            
        Returns:
            Node execution results
        """
        workflow = self.active_workflows[workflow_id]
        node = self._find_node_by_id(workflow, node_id)
        
        if not node:
            raise ValueError(f"Node {node_id} not found in workflow {workflow_id}")
        
        # Prepare input message with meta-prompt injection
        input_message = await self._prepare_input_message(workflow_id, node)
        
        # Execute the applet with the prepared message
        output_message = await self._execute_applet(node, input_message)
        
        # Get the agent type from the node metadata
        agent_type = node.metadata.get("agent_type", "default")
        
        # Enforce structured output
        output_message, was_modified = await self.output_enforcer.enforce_structure(
            message=output_message,
            agent_type=agent_type
        )
        
        if was_modified:
            logger.info(f"Output structure was enforced for node {node.id} in workflow {workflow_id}")
            output_message.metadata["output_structure_enforced"] = True
        
        # Validate the output message
        validation_result = validate_message(output_message)
        
        if not validation_result.is_valid:
            # Handle validation failure based on rules
            output_message = await self._handle_validation_failure(
                workflow_id, node, input_message, output_message, validation_result
            )
        
        # Store the message in history
        self.message_history[workflow_id].append(output_message)
        
        # Apply governance rules
        rule_result = await self.rule_engine.apply_rules(workflow_id, node, output_message)
        
        # Find next nodes to execute
        next_nodes = self._find_next_nodes(workflow, node)
        
        # Create node status update
        node_status = {
            "workflow_id": workflow_id,
            "node_id": node.id,
            "status": "completed",
            "has_errors": output_message.metadata.get("error", False)
        }
        
        # Notify callbacks about node completion
        await self._notify_workflow_update(workflow_id, node_status)
        
        # Execute next nodes if any
        next_results = {}
        for next_node in next_nodes:
            next_results[next_node.id] = await self._execute_node(workflow_id, next_node.id)
        
        return {
            "node_id": node_id,
            "output": output_message.content,
            "metadata": output_message.metadata,
            "validation": validation_result.to_dict(),
            "rule_result": rule_result,
            "next_results": next_results
        }
    
    async def _prepare_input_message(self, workflow_id: str, node: WorkflowNode) -> AppletMessage:
        """
        Prepare an input message for a node with meta-prompt injection.
        
        Args:
            workflow_id: The ID of the workflow
            node: The node to prepare input for
            
        Returns:
            Prepared AppletMessage with injected meta-prompt
        """
        # Create a base message
        base_message = AppletMessage(
            content="Please process this request",
            context={
                "workflow_id": workflow_id, 
                "node_id": node.id,
                "agent_type": node.metadata.get("agent_type", "default")
            },
            metadata={}
        )
        
        # Inject system prompt
        injected_message = await self.system_prompt_injector.inject_system_prompt(
            node=node,
            message=base_message,
            workflow_id=workflow_id
        )
        
        return injected_message
    
    async def _execute_applet(self, node: WorkflowNode, input_message: AppletMessage) -> AppletMessage:
        """
        Execute an applet with the given input message.
        
        Args:
            node: The node containing the applet to execute
            input_message: The input message for the applet
            
        Returns:
            Output message from the applet
        """
        # TODO: Implement actual applet execution
        return AppletMessage(
            content="Sample output from applet",
            context=input_message.context,
            metadata={"execution_time": 0.5}
        )
    
    async def _handle_validation_failure(
        self, 
        workflow_id: str,
        node: WorkflowNode,
        input_message: AppletMessage,
        output_message: AppletMessage,
        validation_result: Any
    ) -> AppletMessage:
        """
        Handle validation failure based on rules.
        
        Args:
            workflow_id: The ID of the workflow
            node: The node that failed validation
            input_message: The original input message
            output_message: The invalid output message
            validation_result: The validation result
            
        Returns:
            Corrected or fallback AppletMessage
        """
        # TODO: Implement retry logic, repair attempts, or fallback mechanisms
        return AppletMessage(
            content="Fallback output due to validation failure",
            context=output_message.context,
            metadata={
                "error": True,
                "error_type": "validation_failure",
                "validation_errors": validation_result.errors
            }
        )
    
    def _calculate_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """
        Calculate execution metrics for a workflow.
        
        Args:
            workflow_id: The ID of the workflow
            
        Returns:
            Execution metrics
        """
        # TODO: Implement metrics calculation
        return {
            "execution_time": 0,
            "validation_success_rate": 0,
            "retry_count": 0
        }
    
    async def _load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Load a workflow from the database.
        
        Args:
            workflow_id: The ID of the workflow to load
            
        Returns:
            The loaded workflow or None if not found
        """
        from db.repository import WorkflowRepository
        from db.session import get_db
        
        # Get database session
        db = next(get_db())
        
        # Create repository
        repository = WorkflowRepository(db)
        
        # Get workflow from database
        db_workflow = repository.get_workflow(workflow_id)
        if not db_workflow:
            logger.error(f"Workflow {workflow_id} not found in database")
            return None
        
        # Convert to domain model
        workflow = repository.to_domain_workflow(db_workflow)
        logger.info(f"Loaded workflow {workflow_id} with {len(workflow.nodes)} nodes and {len(workflow.edges)} edges")
        
        return workflow
    
    def _find_node_by_id(self, workflow: Workflow, node_id: str) -> Optional[WorkflowNode]:
        """
        Find a node by its ID in a workflow.
        
        Args:
            workflow: The workflow to search in
            node_id: The ID of the node to find
            
        Returns:
            The node or None if not found
        """
        for node in workflow.nodes:
            if node.id == node_id:
                return node
        return None
    
    def _find_next_nodes(self, workflow: Workflow, node: WorkflowNode) -> List[WorkflowNode]:
        """
        Find the next nodes to execute after a given node.
        
        Args:
            workflow: The workflow to search in
            node: The current node
            
        Returns:
            List of next nodes to execute
        """
        next_nodes = []
        for edge in workflow.edges:
            if edge.source == node.id:
                next_node = self._find_node_by_id(workflow, edge.target)
                if next_node:
                    next_nodes.append(next_node)
        return next_nodes
        
    def _find_start_node(self, workflow: Workflow) -> Optional[WorkflowNode]:
        """
        Find the start node in a workflow.
        
        Args:
            workflow: The workflow to search in
            
        Returns:
            The start node or None if not found
        """
        logger.info(f"Looking for start node in workflow with {len(workflow.nodes)} nodes")
        
        # First try to find a node with type 'start'
        for node in workflow.nodes:
            if node.type and node.type.lower() == 'start':
                logger.info(f"Found start node by type: {node.id}")
                return node
                
        # If no node with type 'start' is found, try to find a node with name containing 'start'
        for node in workflow.nodes:
            if node.name and 'start' in node.name.lower():
                logger.info(f"Found start node by name: {node.id}")
                return node
                
        # If still not found, check if there's only one node without incoming edges
        nodes_with_incoming_edges = set(edge.target for edge in workflow.edges)
        start_candidates = [node for node in workflow.nodes if node.id not in nodes_with_incoming_edges]
        
        if len(start_candidates) == 1:
            logger.info(f"Found start node by topology: {start_candidates[0].id}")
            return start_candidates[0]
            
        # If multiple candidates, log warning and return None
        if len(start_candidates) > 1:
            logger.warning(f"Multiple potential start nodes found: {[node.id for node in start_candidates]}")
            
        logger.error("No start node found in workflow")
        return None
    
    def register_workflow_update_callback(self, callback: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        Register a callback to be notified of workflow updates.
        
        Args:
            callback: An async function that takes workflow_id and status dict
        """
        self.workflow_update_callbacks.append(callback)
        logger.info(f"Registered workflow update callback: {callback.__name__}")
    
    async def _notify_workflow_update(self, workflow_id: str, status: Dict[str, Any]):
        """
        Notify all registered callbacks about a workflow update.
        
        Args:
            workflow_id: The ID of the workflow that was updated
            status: The new status information
        """
        for callback in self.workflow_update_callbacks:
            try:
                await callback(workflow_id, status)
            except Exception as e:
                logger.error(f"Error in workflow update callback: {e}")

