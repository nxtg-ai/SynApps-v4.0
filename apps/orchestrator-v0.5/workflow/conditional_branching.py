"""
Conditional branching support for the Meta-Agent Orchestrator
Enables dynamic workflow paths based on message content and conditions
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union, TypeVar
from enum import Enum
import re
import json
from dataclasses import dataclass, field
import uuid

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode, Workflow

logger = logging.getLogger("workflow.conditional_branching")

# Type definitions
T = TypeVar('T', bound=AppletMessage)
ConditionEvaluator = Callable[[T], Awaitable[bool]]


class ConditionType(Enum):
    """Types of conditions for branching"""
    CONTENT_MATCH = "content_match"      # Match message content against a string or pattern
    METADATA_CHECK = "metadata_check"    # Check message metadata for specific values
    CONTEXT_CHECK = "context_check"      # Check message context for specific values
    CUSTOM = "custom"                    # Custom condition function
    ALWAYS = "always"                    # Always evaluate to true (default branch)


@dataclass
class BranchCondition:
    """
    Represents a condition for a workflow branch
    """
    condition_type: ConditionType
    target_step_id: str
    
    # Content match parameters
    content_pattern: Optional[str] = None
    pattern_is_regex: bool = False
    case_sensitive: bool = True
    compiled_pattern: Optional[re.Pattern] = None
    
    # Metadata check parameters
    metadata_key: Optional[str] = None
    metadata_value: Optional[Any] = None
    metadata_comparison: Optional[str] = None  # "eq", "neq", "gt", "lt", "contains", etc.
    
    # Context check parameters
    context_key: Optional[str] = None
    context_value: Optional[Any] = None
    context_comparison: Optional[str] = None  # "eq", "neq", "gt", "lt", "contains", etc.
    
    # Custom condition
    custom_condition: Optional[ConditionEvaluator] = None
    
    def __post_init__(self):
        """Compile regex pattern if needed"""
        if self.condition_type == ConditionType.CONTENT_MATCH and self.content_pattern and self.pattern_is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self.compiled_pattern = re.compile(self.content_pattern, flags)


@dataclass
class ConditionalBranch:
    """
    Represents a conditional branch in a workflow
    """
    branch_id: str
    source_step_id: str
    conditions: List[BranchCondition]
    default_target_step_id: Optional[str] = None


class ConditionalBranchingEngine:
    """
    Engine for evaluating conditional branches in workflows
    """
    
    def __init__(self):
        """Initialize the conditional branching engine"""
        # Dictionary of workflow ID -> list of conditional branches
        self.workflow_branches: Dict[str, List[ConditionalBranch]] = {}
        
        # Dictionary of branch ID -> conditional branch
        self.branches_by_id: Dict[str, ConditionalBranch] = {}
        
        logger.info("Conditional branching engine initialized")
    
    def register_branch(self, workflow_id: str, branch: ConditionalBranch) -> None:
        """
        Register a conditional branch for a workflow
        
        Args:
            workflow_id: ID of the workflow
            branch: Conditional branch to register
        """
        # Initialize branch list if needed
        if workflow_id not in self.workflow_branches:
            self.workflow_branches[workflow_id] = []
        
        # Add branch to list
        self.workflow_branches[workflow_id].append(branch)
        
        # Add branch to ID lookup
        self.branches_by_id[branch.branch_id] = branch
        
        logger.info(f"Registered conditional branch {branch.branch_id} for workflow {workflow_id}")
    
    def get_branch(self, branch_id: str) -> Optional[ConditionalBranch]:
        """
        Get a branch by ID
        
        Args:
            branch_id: ID of the branch to get
            
        Returns:
            The branch, or None if not found
        """
        return self.branches_by_id.get(branch_id)
    
    def get_branches_for_workflow(self, workflow_id: str) -> List[ConditionalBranch]:
        """
        Get all branches for a workflow
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of branches for the workflow
        """
        return self.workflow_branches.get(workflow_id, [])
    
    def get_branches_from_step(self, workflow_id: str, step_id: str) -> List[ConditionalBranch]:
        """
        Get all branches from a specific step in a workflow
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the source step
            
        Returns:
            List of branches from the step
        """
        branches = self.get_branches_for_workflow(workflow_id)
        return [branch for branch in branches if branch.source_step_id == step_id]
    
    async def evaluate_condition(self, condition: BranchCondition, message: T) -> bool:
        """
        Evaluate a branch condition against a message
        
        Args:
            condition: Condition to evaluate
            message: Message to evaluate against
            
        Returns:
            True if the condition matches, False otherwise
        """
        if condition.condition_type == ConditionType.ALWAYS:
            return True
        
        elif condition.condition_type == ConditionType.CONTENT_MATCH:
            if not hasattr(message, 'content') or not isinstance(message.content, str):
                return False
            
            content = message.content
            
            if condition.pattern_is_regex and condition.compiled_pattern:
                return bool(condition.compiled_pattern.search(content))
            else:
                if condition.case_sensitive:
                    return condition.content_pattern in content
                else:
                    return condition.content_pattern.lower() in content.lower()
        
        elif condition.condition_type == ConditionType.METADATA_CHECK:
            if not hasattr(message, 'metadata') or not isinstance(message.metadata, dict):
                return False
            
            if condition.metadata_key not in message.metadata:
                return False
            
            value = message.metadata[condition.metadata_key]
            
            return self._compare_values(value, condition.metadata_value, condition.metadata_comparison)
        
        elif condition.condition_type == ConditionType.CONTEXT_CHECK:
            if not hasattr(message, 'context') or not isinstance(message.context, dict):
                return False
            
            if condition.context_key not in message.context:
                return False
            
            value = message.context[condition.context_key]
            
            return self._compare_values(value, condition.context_value, condition.context_comparison)
        
        elif condition.condition_type == ConditionType.CUSTOM:
            if not condition.custom_condition:
                return False
            
            try:
                return await condition.custom_condition(message)
            except Exception as e:
                logger.error(f"Error evaluating custom condition: {str(e)}")
                return False
        
        return False
    
    def _compare_values(self, value: Any, target: Any, comparison: Optional[str]) -> bool:
        """
        Compare two values using the specified comparison operator
        
        Args:
            value: Value to compare
            target: Target value to compare against
            comparison: Comparison operator
            
        Returns:
            Result of the comparison
        """
        if comparison is None or comparison == "eq":
            return value == target
        
        elif comparison == "neq":
            return value != target
        
        elif comparison == "gt":
            return value > target
        
        elif comparison == "gte":
            return value >= target
        
        elif comparison == "lt":
            return value < target
        
        elif comparison == "lte":
            return value <= target
        
        elif comparison == "contains":
            if isinstance(value, str) and isinstance(target, str):
                return target in value
            elif isinstance(value, (list, tuple, set)):
                return target in value
            elif isinstance(value, dict):
                return target in value
            return False
        
        elif comparison == "startswith":
            if isinstance(value, str) and isinstance(target, str):
                return value.startswith(target)
            return False
        
        elif comparison == "endswith":
            if isinstance(value, str) and isinstance(target, str):
                return value.endswith(target)
            return False
        
        return False
    
    async def evaluate_branch(self, branch: ConditionalBranch, message: T) -> Optional[str]:
        """
        Evaluate a conditional branch against a message
        
        Args:
            branch: Branch to evaluate
            message: Message to evaluate against
            
        Returns:
            ID of the target step to route to, or None if no conditions match
        """
        # Check each condition in order
        for condition in branch.conditions:
            try:
                if await self.evaluate_condition(condition, message):
                    return condition.target_step_id
            except Exception as e:
                logger.error(f"Error evaluating condition: {str(e)}")
        
        # Return default target if no conditions match
        return branch.default_target_step_id
    
    async def get_next_step(self, workflow_id: str, current_step_id: str, message: T) -> Optional[str]:
        """
        Get the next step for a message in a workflow
        
        Args:
            workflow_id: ID of the workflow
            current_step_id: ID of the current step
            message: Message to evaluate
            
        Returns:
            ID of the next step, or None if no branches match
        """
        # Get branches from the current step
        branches = self.get_branches_from_step(workflow_id, current_step_id)
        
        if not branches:
            logger.debug(f"No branches found from step {current_step_id} in workflow {workflow_id}")
            return None
        
        # Evaluate each branch
        for branch in branches:
            next_step = await self.evaluate_branch(branch, message)
            if next_step:
                logger.debug(f"Branch {branch.branch_id} matched, routing to step {next_step}")
                return next_step
        
        logger.debug(f"No matching branches found from step {current_step_id} in workflow {workflow_id}")
        return None
    
    def create_content_condition(self, target_step_id: str, content_pattern: str, 
                               pattern_is_regex: bool = False, case_sensitive: bool = True) -> BranchCondition:
        """
        Create a content-based condition
        
        Args:
            target_step_id: ID of the target step
            content_pattern: Pattern to match in content
            pattern_is_regex: Whether the pattern is a regex
            case_sensitive: Whether the match is case-sensitive
            
        Returns:
            Created condition
        """
        return BranchCondition(
            condition_type=ConditionType.CONTENT_MATCH,
            target_step_id=target_step_id,
            content_pattern=content_pattern,
            pattern_is_regex=pattern_is_regex,
            case_sensitive=case_sensitive
        )
    
    def create_metadata_condition(self, target_step_id: str, metadata_key: str,
                                metadata_value: Any, comparison: str = "eq") -> BranchCondition:
        """
        Create a metadata-based condition
        
        Args:
            target_step_id: ID of the target step
            metadata_key: Key to check in metadata
            metadata_value: Value to compare against
            comparison: Comparison operator
            
        Returns:
            Created condition
        """
        return BranchCondition(
            condition_type=ConditionType.METADATA_CHECK,
            target_step_id=target_step_id,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
            metadata_comparison=comparison
        )
    
    def create_context_condition(self, target_step_id: str, context_key: str,
                               context_value: Any, comparison: str = "eq") -> BranchCondition:
        """
        Create a context-based condition
        
        Args:
            target_step_id: ID of the target step
            context_key: Key to check in context
            context_value: Value to compare against
            comparison: Comparison operator
            
        Returns:
            Created condition
        """
        return BranchCondition(
            condition_type=ConditionType.CONTEXT_CHECK,
            target_step_id=target_step_id,
            context_key=context_key,
            context_value=context_value,
            context_comparison=comparison
        )
    
    def create_custom_condition(self, target_step_id: str, 
                              condition_func: ConditionEvaluator) -> BranchCondition:
        """
        Create a custom condition
        
        Args:
            target_step_id: ID of the target step
            condition_func: Function that evaluates the condition
            
        Returns:
            Created condition
        """
        return BranchCondition(
            condition_type=ConditionType.CUSTOM,
            target_step_id=target_step_id,
            custom_condition=condition_func
        )
    
    def create_default_condition(self, target_step_id: str) -> BranchCondition:
        """
        Create a default condition that always matches
        
        Args:
            target_step_id: ID of the target step
            
        Returns:
            Created condition
        """
        return BranchCondition(
            condition_type=ConditionType.ALWAYS,
            target_step_id=target_step_id
        )
    
    def create_branch(self, workflow_id: str, source_step_id: str, 
                    conditions: List[BranchCondition],
                    default_target_step_id: Optional[str] = None) -> ConditionalBranch:
        """
        Create and register a conditional branch
        
        Args:
            workflow_id: ID of the workflow
            source_step_id: ID of the source step
            conditions: List of conditions
            default_target_step_id: Default target step ID
            
        Returns:
            Created branch
        """
        branch_id = str(uuid.uuid4())
        
        branch = ConditionalBranch(
            branch_id=branch_id,
            source_step_id=source_step_id,
            conditions=conditions,
            default_target_step_id=default_target_step_id
        )
        
        self.register_branch(workflow_id, branch)
        return branch
