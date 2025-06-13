"""
Output Enforcer for the Meta-Agent Orchestrator
Ensures agent outputs conform to the expected structure
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Union

from models.agent_message import AppletMessage
from core.validation.schema_validator import SchemaRegistry, ValidationResult, validate_message

logger = logging.getLogger("validation.output_enforcer")

class OutputEnforcer:
    """
    Enforces structured output for agent responses by:
    1. Detecting unstructured outputs
    2. Attempting to convert them to the expected structure
    3. Validating the converted output
    """
    
    def __init__(self):
        """Initialize the OutputEnforcer"""
        logger.info("OutputEnforcer initialized")
    
    async def enforce_structure(self, 
                               message: AppletMessage, 
                               agent_type: str) -> tuple[AppletMessage, bool]:
        """
        Enforce structured output for an agent message.
        
        Args:
            message: The agent message to enforce structure on
            agent_type: The type of agent that produced the message
            
        Returns:
            Tuple of (enforced message, was_modified)
        """
        # Check if we have a schema for this agent type
        if not SchemaRegistry.has_schema(agent_type):
            logger.warning(f"No schema found for agent type: {agent_type}, skipping enforcement")
            return message, False
            
        # Get the schema
        schema = SchemaRegistry.get_schema(agent_type)
        
        # Check if the message content is already structured
        content = message.content
        is_structured = self._is_structured_output(content)
        
        if is_structured:
            # Validate the structured output
            validation_result = validate_message(message)
            if validation_result.is_valid:
                logger.debug(f"Message from agent type {agent_type} already has valid structured output")
                return message, False
                
            # If not valid, try to fix it
            logger.info(f"Message from agent type {agent_type} has structured but invalid output, attempting to fix")
            fixed_message = self._fix_structured_output(message, schema)
            return fixed_message, True
        else:
            # Try to convert unstructured output to structured
            logger.info(f"Message from agent type {agent_type} has unstructured output, attempting to convert")
            structured_message = self._convert_to_structured(message, schema)
            return structured_message, True
    
    def _is_structured_output(self, content: Union[str, Dict[str, Any]]) -> bool:
        """
        Check if the content is already structured (valid JSON).
        
        Args:
            content: The content to check
            
        Returns:
            True if structured, False otherwise
        """
        if isinstance(content, dict):
            return True
            
        if isinstance(content, str):
            # Try to parse as JSON
            try:
                json.loads(content)
                return True
            except json.JSONDecodeError:
                # Check if it's a JSON-like string with code blocks
                json_pattern = r"```json\s*([\s\S]*?)\s*```"
                match = re.search(json_pattern, content)
                if match:
                    try:
                        json.loads(match.group(1))
                        return True
                    except json.JSONDecodeError:
                        pass
                        
        return False
    
    def _convert_to_structured(self, 
                              message: AppletMessage, 
                              schema: Dict[str, Any]) -> AppletMessage:
        """
        Convert unstructured output to structured format based on schema.
        
        Args:
            message: The message to convert
            schema: The schema to conform to
            
        Returns:
            Converted message
        """
        content = message.content
        
        # Create a new message with the same context and metadata
        converted_message = AppletMessage(
            content=content,
            context=dict(message.context) if message.context else {},
            metadata=dict(message.metadata) if message.metadata else {}
        )
        
        # Extract JSON if it's in a code block
        if isinstance(content, str):
            json_pattern = r"```json\s*([\s\S]*?)\s*```"
            match = re.search(json_pattern, content)
            if match:
                try:
                    extracted_json = json.loads(match.group(1))
                    converted_message.content = extracted_json
                    converted_message.metadata["structured_output_extracted"] = True
                    return converted_message
                except json.JSONDecodeError:
                    pass
        
        # If we can't extract JSON, try to create a structured output based on schema
        if "type" in schema and schema["type"] == "object" and "properties" in schema:
            structured_output = {}
            
            # For each property in the schema, try to extract a value from the content
            for prop_name, prop_schema in schema["properties"].items():
                prop_desc = prop_schema.get("description", prop_name)
                
                # Simple heuristic: look for sections that might contain the property
                if isinstance(content, str):
                    # Look for sections like "Analysis:" or "## Analysis"
                    patterns = [
                        rf"{prop_name}:\s*(.*?)(?:\n\n|\n[A-Z]|\Z)",
                        rf"{prop_desc}:\s*(.*?)(?:\n\n|\n[A-Z]|\Z)",
                        rf"#{{{1,3}}}\s*{prop_name}\s*\n(.*?)(?:\n#{{{1,3}}}|\Z)",
                        rf"#{{{1,3}}}\s*{prop_desc}\s*\n(.*?)(?:\n#{{{1,3}}}|\Z)"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                        if match:
                            value = match.group(1).strip()
                            
                            # Convert to appropriate type based on schema
                            if "type" in prop_schema:
                                if prop_schema["type"] == "array" and not value.startswith("["):
                                    # Convert bullet points or numbered lists to array
                                    items = re.findall(r"(?:^|\n)(?:[-*•]|\d+\.)\s*(.*?)(?=(?:\n[-*•]|\n\d+\.|\Z))", value, re.DOTALL)
                                    value = [item.strip() for item in items if item.strip()]
                                elif prop_schema["type"] == "number":
                                    try:
                                        value = float(value)
                                    except ValueError:
                                        # Try to extract a number from the text
                                        number_match = re.search(r"(\d+(?:\.\d+)?)", value)
                                        if number_match:
                                            value = float(number_match.group(1))
                                elif prop_schema["type"] == "boolean":
                                    value = value.lower() in ["true", "yes", "1"]
                            
                            structured_output[prop_name] = value
                            break
            
            # If we managed to extract at least some properties, use the structured output
            if structured_output:
                converted_message.content = structured_output
                converted_message.metadata["structured_output_created"] = True
                logger.info(f"Created structured output with {len(structured_output)} properties")
        
        return converted_message
    
    def _fix_structured_output(self, 
                              message: AppletMessage, 
                              schema: Dict[str, Any]) -> AppletMessage:
        """
        Fix structured but invalid output to conform to schema.
        
        Args:
            message: The message to fix
            schema: The schema to conform to
            
        Returns:
            Fixed message
        """
        content = message.content
        
        # Create a new message with the same context and metadata
        fixed_message = AppletMessage(
            content=content if not isinstance(content, str) else json.loads(content),
            context=dict(message.context) if message.context else {},
            metadata=dict(message.metadata) if message.metadata else {}
        )
        
        # Ensure content is a dictionary
        if isinstance(fixed_message.content, str):
            try:
                fixed_message.content = json.loads(fixed_message.content)
            except json.JSONDecodeError:
                # If we can't parse it as JSON, return the original message
                return message
        
        # If content is not a dict, we can't fix it
        if not isinstance(fixed_message.content, dict):
            return message
            
        # Get the content as a dict for easier manipulation
        content_dict = fixed_message.content
        
        # Check for required properties and add defaults if missing
        if "required" in schema and "properties" in schema:
            for prop_name in schema["required"]:
                if prop_name not in content_dict:
                    # Add a default value based on the property type
                    prop_schema = schema["properties"].get(prop_name, {})
                    prop_type = prop_schema.get("type", "string")
                    
                    if prop_type == "string":
                        content_dict[prop_name] = "No information provided"
                    elif prop_type == "array":
                        content_dict[prop_name] = []
                    elif prop_type == "object":
                        content_dict[prop_name] = {}
                    elif prop_type == "number":
                        content_dict[prop_name] = 0
                    elif prop_type == "boolean":
                        content_dict[prop_name] = False
                    
                    logger.info(f"Added default value for missing required property: {prop_name}")
        
        # Fix property types
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                if prop_name in content_dict and "type" in prop_schema:
                    expected_type = prop_schema["type"]
                    value = content_dict[prop_name]
                    
                    # Convert to the expected type
                    if expected_type == "string" and not isinstance(value, str):
                        content_dict[prop_name] = str(value)
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        try:
                            content_dict[prop_name] = float(value)
                        except (ValueError, TypeError):
                            content_dict[prop_name] = 0
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        content_dict[prop_name] = bool(value)
                    elif expected_type == "array" and not isinstance(value, list):
                        if isinstance(value, str):
                            # Try to convert string to array
                            items = re.findall(r"(?:^|\n)(?:[-*•]|\d+\.)\s*(.*?)(?=(?:\n[-*•]|\n\d+\.|\Z))", value, re.DOTALL)
                            content_dict[prop_name] = [item.strip() for item in items if item.strip()]
                        else:
                            content_dict[prop_name] = [value] if value else []
                    elif expected_type == "object" and not isinstance(value, dict):
                        content_dict[prop_name] = {}
        
        fixed_message.metadata["structured_output_fixed"] = True
        return fixed_message
