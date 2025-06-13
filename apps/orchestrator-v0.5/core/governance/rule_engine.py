"""
Rule Engine for the Meta-Agent Orchestrator
Enforces governance rules for deterministic execution
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel, Field

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode

logger = logging.getLogger("governance.rule_engine")

class RuleResult(BaseModel):
    """
    Result of applying a governance rule.
    """
    rule_id: str = Field(description="ID of the rule that was applied")
    passed: bool = Field(description="Whether the rule passed")
    message: str = Field(description="Message explaining the result")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the rule application"
    )

class Rule(BaseModel):
    """
    A governance rule that can be applied to agent outputs.
    """
    id: str = Field(description="Unique identifier for the rule")
    name: str = Field(description="Human-readable name for the rule")
    description: str = Field(description="Description of what the rule enforces")
    severity: str = Field(description="Severity level (info, warning, error)")
    
    # This will be set programmatically
    check_function: Optional[Callable] = None
    
    def apply(self, workflow_id: str, node: WorkflowNode, message: AppletMessage) -> RuleResult:
        """
        Apply the rule to a message.
        
        Args:
            workflow_id: ID of the workflow
            node: Node that produced the message
            message: Message to check
            
        Returns:
            RuleResult with the outcome
        """
        if not self.check_function:
            logger.warning(f"Rule {self.id} has no check function")
            return RuleResult(
                rule_id=self.id,
                passed=True,
                message=f"Rule {self.id} skipped: no check function"
            )
        
        try:
            passed, message_text, metadata = self.check_function(workflow_id, node, message)
            return RuleResult(
                rule_id=self.id,
                passed=passed,
                message=message_text,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Error applying rule {self.id}: {str(e)}")
            return RuleResult(
                rule_id=self.id,
                passed=False,
                message=f"Error applying rule: {str(e)}",
                metadata={"error": str(e)}
            )

class RuleEngine:
    """
    Engine for applying governance rules to agent outputs.
    """
    
    def __init__(self):
        """Initialize the Rule Engine"""
        self.rules: Dict[str, Rule] = {}
        self._register_default_rules()
        logger.info("Rule Engine initialized")
    
    def register_rule(self, rule: Rule, check_function: Callable) -> None:
        """
        Register a rule with the engine.
        
        Args:
            rule: Rule to register
            check_function: Function to check if the rule passes
                The function should take (workflow_id, node, message) and return
                (passed, message, metadata)
        """
        rule.check_function = check_function
        self.rules[rule.id] = rule
        logger.info(f"Registered rule: {rule.id} - {rule.name}")
    
    async def apply_rules(
        self, 
        workflow_id: str, 
        node: WorkflowNode, 
        message: AppletMessage,
        rule_ids: List[str] = None
    ) -> Dict[str, RuleResult]:
        """
        Apply rules to a message.
        
        Args:
            workflow_id: ID of the workflow
            node: Node that produced the message
            message: Message to check
            rule_ids: Optional list of rule IDs to apply. If None, all rules are applied.
            
        Returns:
            Dictionary mapping rule IDs to RuleResults
        """
        results = {}
        
        # Determine which rules to apply
        rules_to_apply = []
        if rule_ids:
            # Apply only specified rules
            for rule_id in rule_ids:
                if rule_id in self.rules:
                    rules_to_apply.append(self.rules[rule_id])
                else:
                    logger.warning(f"Rule {rule_id} not found")
        else:
            # Apply all rules
            rules_to_apply = list(self.rules.values())
        
        # Apply rules
        for rule in rules_to_apply:
            logger.info(f"Applying rule {rule.id} to message from node {node.id}")
            result = rule.apply(workflow_id, node, message)
            results[rule.id] = result
            
            if not result.passed and rule.severity == "error":
                logger.error(f"Rule {rule.id} failed: {result.message}")
                # In a real implementation, you might want to handle this differently
                # For example, by retrying the agent execution or falling back to a default
        
        return results
    
    def _register_default_rules(self) -> None:
        """Register default governance rules"""
        
        # Content safety rule
        def check_content_safety(workflow_id: str, node: WorkflowNode, message: AppletMessage):
            # In a real implementation, this would use a content safety API
            # For now, we'll just check for some basic keywords
            unsafe_keywords = ["harmful", "illegal", "offensive"]
            content = message.content.lower()
            
            for keyword in unsafe_keywords:
                if keyword in content:
                    return False, f"Content contains unsafe keyword: {keyword}", {"keyword": keyword}
            
            return True, "Content passed safety check", {}
        
        content_safety_rule = Rule(
            id="content_safety",
            name="Content Safety",
            description="Ensures that agent outputs do not contain harmful content",
            severity="error"
        )
        self.register_rule(content_safety_rule, check_content_safety)
        
        # Response length rule
        def check_response_length(workflow_id: str, node: WorkflowNode, message: AppletMessage):
            # Check if the response is too short or too long
            content = message.content
            length = len(content)
            
            if length < 10:
                return False, "Response is too short", {"length": length}
            
            if length > 10000:
                return False, "Response is too long", {"length": length}
            
            return True, "Response length is acceptable", {"length": length}
        
        response_length_rule = Rule(
            id="response_length",
            name="Response Length",
            description="Ensures that agent outputs are of an appropriate length",
            severity="warning"
        )
        self.register_rule(response_length_rule, check_response_length)
        
        # JSON structure rule
        def check_json_structure(workflow_id: str, node: WorkflowNode, message: AppletMessage):
            # Check if the response is valid JSON if it's supposed to be
            if node.config.get("output_format") == "json":
                content = message.content
                
                import json
                try:
                    json.loads(content)
                    return True, "JSON structure is valid", {}
                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON structure: {str(e)}", {"error": str(e)}
            
            return True, "JSON structure check not applicable", {}
        
        json_structure_rule = Rule(
            id="json_structure",
            name="JSON Structure",
            description="Ensures that JSON outputs have a valid structure",
            severity="error"
        )
        self.register_rule(json_structure_rule, check_json_structure)
