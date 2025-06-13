"""
System Prompt Injector

This module is responsible for injecting agent-specific meta-prompts into
AppletMessage.context["system_prompt"] prior to execution.
"""

import logging
from typing import Dict, Any, Optional, List
import json

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode
from core.governance.rule_engine import RuleEngine

logger = logging.getLogger("meta_agent.system_prompt_injector")

class SystemPromptInjector:
    """
    Injects meta-prompts into agent messages to enhance their capabilities,
    enforce output structure, and ensure compliance with governance rules.
    """
    
    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        """
        Initialize the SystemPromptInjector.
        
        Args:
            rule_engine: Optional rule engine for governance rules
        """
        self.rule_engine = rule_engine or RuleEngine()
        self.meta_prompt_templates = self._load_meta_prompt_templates()
        logger.info("SystemPromptInjector initialized")
        
    def _load_meta_prompt_templates(self) -> Dict[str, str]:
        """
        Load meta-prompt templates from configuration.
        
        Returns:
            Dictionary of meta-prompt templates by agent type
        """
        # In a production system, these would be loaded from a database or config file
        return {
            "default": """
                You are an AI assistant in a multi-agent workflow system.
                Please ensure your responses follow the required output format.
                Your output will be validated against a schema.
            """,
            "code_generator": """
                You are a code generation assistant. 
                Please ensure your code is well-documented, follows best practices, and is secure.
                Format your response as valid JSON with the following structure:
                {
                    "code": "your generated code here",
                    "language": "programming language",
                    "explanation": "explanation of the code"
                }
            """,
            "data_analyst": """
                You are a data analysis assistant.
                Please ensure your analysis is thorough and your insights are actionable.
                Format your response as valid JSON with the following structure:
                {
                    "analysis": "your analysis here",
                    "insights": ["insight 1", "insight 2", ...],
                    "recommendations": ["recommendation 1", "recommendation 2", ...]
                }
            """,
            "content_creator": """
                You are a content creation assistant.
                Please ensure your content is engaging, accurate, and appropriate.
                Format your response as valid JSON with the following structure:
                {
                    "title": "content title",
                    "content": "your generated content here",
                    "target_audience": "description of target audience",
                    "tone": "tone of the content"
                }
            """
        }
    
    async def inject_system_prompt(self, 
                                  node: WorkflowNode, 
                                  message: AppletMessage,
                                  workflow_id: str = None) -> AppletMessage:
        """
        Inject a system prompt into an agent message based on the node type and governance rules.
        
        Args:
            node: The workflow node containing the agent
            message: The message to inject the system prompt into
            workflow_id: Optional workflow ID for governance rules
            
        Returns:
            The message with the injected system prompt
        """
        # Create a copy of the message to avoid modifying the original
        injected_message = AppletMessage(
            content=message.content,
            context=dict(message.context) if message.context else {},
            metadata=dict(message.metadata) if message.metadata else {}
        )
        
        # Get the base meta-prompt template based on agent type
        agent_type = node.metadata.get("agent_type", "default")
        base_prompt = self.meta_prompt_templates.get(agent_type, self.meta_prompt_templates["default"])
        
        # Apply governance rules if available
        governance_additions = ""
        if workflow_id and self.rule_engine:
            governance_rules = await self.rule_engine.get_rules_for_node(workflow_id, node.id)
            if governance_rules:
                governance_additions = self._format_governance_rules(governance_rules)
        
        # Get output schema if available
        output_schema = self._get_output_schema(node)
        schema_prompt = self._format_output_schema(output_schema) if output_schema else ""
        
        # Combine all prompt components
        full_system_prompt = f"{base_prompt}\n\n{governance_additions}\n\n{schema_prompt}".strip()
        
        # Inject the system prompt into the message context
        if "context" not in injected_message.context:
            injected_message.context["context"] = {}
            
        injected_message.context["system_prompt"] = full_system_prompt
        
        # Add metadata about the injection
        injected_message.metadata["system_prompt_injected"] = True
        injected_message.metadata["system_prompt_agent_type"] = agent_type
        
        logger.debug(f"Injected system prompt for agent type {agent_type}")
        return injected_message
    
    def _format_governance_rules(self, rules: List[Dict[str, Any]]) -> str:
        """
        Format governance rules as a string for inclusion in the system prompt.
        
        Args:
            rules: List of governance rule dictionaries
            
        Returns:
            Formatted governance rules as a string
        """
        if not rules:
            return ""
            
        rules_text = "GOVERNANCE RULES:\n"
        for i, rule in enumerate(rules, 1):
            rules_text += f"{i}. {rule.get('description', 'Unknown rule')}\n"
            
        return rules_text
    
    def _get_output_schema(self, node: WorkflowNode) -> Optional[Dict[str, Any]]:
        """
        Get the output schema for a node if available.
        
        Args:
            node: The workflow node
            
        Returns:
            Output schema as a dictionary or None if not available
        """
        # In a real implementation, this would be retrieved from the node metadata
        # or from a schema registry
        if "output_schema" in node.metadata:
            return node.metadata["output_schema"]
        
        # For now, return a default schema based on agent type
        agent_type = node.metadata.get("agent_type", "default")
        default_schemas = {
            "code_generator": {
                "type": "object",
                "required": ["code", "language", "explanation"],
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"},
                    "explanation": {"type": "string"}
                }
            },
            "data_analyst": {
                "type": "object",
                "required": ["analysis", "insights", "recommendations"],
                "properties": {
                    "analysis": {"type": "string"},
                    "insights": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}}
                }
            },
            "content_creator": {
                "type": "object",
                "required": ["title", "content", "target_audience", "tone"],
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "target_audience": {"type": "string"},
                    "tone": {"type": "string"}
                }
            }
        }
        
        return default_schemas.get(agent_type)
    
    def _format_output_schema(self, schema: Dict[str, Any]) -> str:
        """
        Format an output schema as a string for inclusion in the system prompt.
        
        Args:
            schema: The output schema as a dictionary
            
        Returns:
            Formatted output schema as a string
        """
        if not schema:
            return ""
            
        schema_text = "OUTPUT SCHEMA:\n"
        schema_text += "Your response must conform to the following JSON schema:\n"
        schema_text += json.dumps(schema, indent=2)
        
        return schema_text
