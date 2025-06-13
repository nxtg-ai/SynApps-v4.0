"""
Autonomous Agent Behaviors

Enables agents to make decisions and dynamically determine the flow of execution
in a workflow based on their outputs and internal decision-making processes.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode, WorkflowEdge, Workflow

logger = logging.getLogger("autonomy.agent_behavior")

class BranchingStrategy(str, Enum):
    """
    Strategies for determining branching in a workflow.
    """
    CONDITIONAL = "conditional"  # Branch based on a condition
    PARALLEL = "parallel"        # Execute all branches in parallel
    PRIORITY = "priority"        # Try branches in order of priority
    RANDOM = "random"            # Choose a random branch
    WEIGHTED = "weighted"        # Choose a branch based on weights
    CUSTOM = "custom"            # Custom branching logic

class BranchingCondition:
    """
    Condition for branching in a workflow.
    """
    def __init__(
        self,
        condition_type: str,
        parameters: Dict[str, Any],
        target_node_id: str
    ):
        """
        Initialize a branching condition.
        
        Args:
            condition_type: Type of condition (e.g., 'equals', 'contains', 'greater_than')
            parameters: Parameters for the condition
            target_node_id: ID of the target node if condition is met
        """
        self.condition_type = condition_type
        self.parameters = parameters
        self.target_node_id = target_node_id
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate the condition against a context.
        
        Args:
            context: Context to evaluate against
            
        Returns:
            True if condition is met, False otherwise
        """
        if self.condition_type == "equals":
            field = self.parameters.get("field")
            value = self.parameters.get("value")
            return context.get(field) == value
            
        elif self.condition_type == "contains":
            field = self.parameters.get("field")
            value = self.parameters.get("value")
            field_value = context.get(field)
            
            if isinstance(field_value, str):
                return value in field_value
            elif isinstance(field_value, (list, tuple)):
                return value in field_value
            elif isinstance(field_value, dict):
                return value in field_value
            return False
            
        elif self.condition_type == "greater_than":
            field = self.parameters.get("field")
            value = self.parameters.get("value")
            return context.get(field, 0) > value
            
        elif self.condition_type == "less_than":
            field = self.parameters.get("field")
            value = self.parameters.get("value")
            return context.get(field, 0) < value
            
        elif self.condition_type == "regex_match":
            import re
            field = self.parameters.get("field")
            pattern = self.parameters.get("pattern")
            field_value = context.get(field, "")
            if isinstance(field_value, str):
                return bool(re.search(pattern, field_value))
            return False
            
        elif self.condition_type == "custom":
            # Custom condition using a lambda function
            # This is for advanced use cases and should be used with caution
            custom_function = self.parameters.get("function")
            if callable(custom_function):
                return custom_function(context)
            return False
            
        # Default case
        return False

class AutonomousBehaviorManager:
    """
    Manages autonomous behaviors for agents in a workflow.
    """
    def __init__(self):
        """Initialize the autonomous behavior manager"""
        # Dictionary of branching strategies by node ID
        # node_id -> BranchingStrategy
        self.branching_strategies: Dict[str, BranchingStrategy] = {}
        
        # Dictionary of branching conditions by node ID
        # node_id -> List[BranchingCondition]
        self.branching_conditions: Dict[str, List[BranchingCondition]] = {}
        
        # Dictionary of custom branching functions by node ID
        # node_id -> Callable
        self.custom_branching_functions: Dict[str, Callable] = {}
        
        logger.info("AutonomousBehaviorManager initialized")
    
    def register_branching_strategy(
        self,
        node_id: str,
        strategy: BranchingStrategy
    ) -> None:
        """
        Register a branching strategy for a node.
        
        Args:
            node_id: ID of the node
            strategy: Branching strategy to use
        """
        self.branching_strategies[node_id] = strategy
        logger.info(f"Registered {strategy} branching strategy for node {node_id}")
    
    def register_branching_condition(
        self,
        node_id: str,
        condition: BranchingCondition
    ) -> None:
        """
        Register a branching condition for a node.
        
        Args:
            node_id: ID of the node
            condition: Branching condition
        """
        if node_id not in self.branching_conditions:
            self.branching_conditions[node_id] = []
        
        self.branching_conditions[node_id].append(condition)
        logger.info(f"Registered branching condition for node {node_id}")
    
    def register_custom_branching_function(
        self,
        node_id: str,
        function: Callable[[AppletMessage, List[WorkflowEdge]], List[str]]
    ) -> None:
        """
        Register a custom branching function for a node.
        
        Args:
            node_id: ID of the node
            function: Function that takes a message and available edges and returns target node IDs
        """
        self.custom_branching_functions[node_id] = function
        logger.info(f"Registered custom branching function for node {node_id}")
    
    def determine_next_nodes(
        self,
        node: WorkflowNode,
        message: AppletMessage,
        available_edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        Determine the next nodes to execute based on the node's branching strategy.
        
        Args:
            node: Current node
            message: Output message from the node
            available_edges: Available edges from the node
            
        Returns:
            List of target node IDs to execute next
        """
        node_id = node.id
        
        # Get the branching strategy for this node
        strategy = self.branching_strategies.get(node_id, BranchingStrategy.CONDITIONAL)
        
        # Handle based on strategy
        if strategy == BranchingStrategy.CUSTOM and node_id in self.custom_branching_functions:
            # Use custom branching function
            return self.custom_branching_functions[node_id](message, available_edges)
            
        elif strategy == BranchingStrategy.PARALLEL:
            # Execute all branches
            return [edge.target for edge in available_edges]
            
        elif strategy == BranchingStrategy.CONDITIONAL:
            # Use conditions to determine branches
            return self._evaluate_conditional_branching(node_id, message, available_edges)
            
        elif strategy == BranchingStrategy.PRIORITY:
            # Try branches in order of priority
            return self._evaluate_priority_branching(node_id, message, available_edges)
            
        elif strategy == BranchingStrategy.RANDOM:
            # Choose a random branch
            import random
            if available_edges:
                return [random.choice(available_edges).target]
            return []
            
        elif strategy == BranchingStrategy.WEIGHTED:
            # Choose a branch based on weights
            return self._evaluate_weighted_branching(node_id, message, available_edges)
            
        # Default: follow all edges
        return [edge.target for edge in available_edges]
    
    def _evaluate_conditional_branching(
        self,
        node_id: str,
        message: AppletMessage,
        available_edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        Evaluate conditional branching for a node.
        
        Args:
            node_id: ID of the node
            message: Output message from the node
            available_edges: Available edges from the node
            
        Returns:
            List of target node IDs to execute next
        """
        # If no conditions are registered, follow all edges
        if node_id not in self.branching_conditions:
            return [edge.target for edge in available_edges]
        
        # Create context for condition evaluation
        context = self._create_evaluation_context(message)
        
        # Evaluate conditions
        target_nodes = []
        for condition in self.branching_conditions[node_id]:
            if condition.evaluate(context):
                target_nodes.append(condition.target_node_id)
        
        # If no conditions matched, follow default edge if available
        if not target_nodes:
            for edge in available_edges:
                if edge.metadata.get("is_default", False):
                    target_nodes.append(edge.target)
                    break
        
        return target_nodes
    
    def _evaluate_priority_branching(
        self,
        node_id: str,
        message: AppletMessage,
        available_edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        Evaluate priority-based branching for a node.
        
        Args:
            node_id: ID of the node
            message: Output message from the node
            available_edges: Available edges from the node
            
        Returns:
            List of target node IDs to execute next
        """
        # Create context for condition evaluation
        context = self._create_evaluation_context(message)
        
        # Sort edges by priority
        sorted_edges = sorted(
            available_edges,
            key=lambda edge: edge.metadata.get("priority", 0),
            reverse=True
        )
        
        # Try each edge in order of priority
        for edge in sorted_edges:
            edge_conditions = edge.metadata.get("conditions", [])
            
            # If no conditions, use this edge
            if not edge_conditions:
                return [edge.target]
            
            # Check if all conditions are met
            conditions_met = True
            for condition_data in edge_conditions:
                condition = BranchingCondition(
                    condition_type=condition_data.get("type"),
                    parameters=condition_data.get("parameters", {}),
                    target_node_id=edge.target
                )
                if not condition.evaluate(context):
                    conditions_met = False
                    break
            
            if conditions_met:
                return [edge.target]
        
        # If no edges matched, return empty list
        return []
    
    def _evaluate_weighted_branching(
        self,
        node_id: str,
        message: AppletMessage,
        available_edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        Evaluate weighted branching for a node.
        
        Args:
            node_id: ID of the node
            message: Output message from the node
            available_edges: Available edges from the node
            
        Returns:
            List of target node IDs to execute next
        """
        import random
        
        # Get weights for each edge
        weights = []
        for edge in available_edges:
            weight = edge.metadata.get("weight", 1.0)
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
            
            # Choose an edge based on weights
            chosen_index = random.choices(
                range(len(available_edges)),
                weights=normalized_weights,
                k=1
            )[0]
            
            return [available_edges[chosen_index].target]
        
        # If no weights or all weights are 0, choose randomly
        if available_edges:
            return [random.choice(available_edges).target]
        
        return []
    
    def _create_evaluation_context(self, message: AppletMessage) -> Dict[str, Any]:
        """
        Create a context for condition evaluation from a message.
        
        Args:
            message: Message to create context from
            
        Returns:
            Context dictionary
        """
        context = {}
        
        # Add message content
        if isinstance(message.content, str):
            try:
                # Try to parse as JSON
                content_dict = json.loads(message.content)
                context.update(content_dict)
            except json.JSONDecodeError:
                context["content"] = message.content
        elif isinstance(message.content, dict):
            context.update(message.content)
        else:
            context["content"] = message.content
        
        # Add message context
        if message.context:
            context["message_context"] = message.context
        
        # Add message metadata
        if message.metadata:
            context["metadata"] = message.metadata
        
        return context
