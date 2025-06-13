"""
Schema Validator for the Meta-Agent Orchestrator
Validates agent outputs against predefined schemas
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ValidationError, Field

from models.agent_message import AppletMessage

logger = logging.getLogger("validation.schema_validator")

class ValidationResult(BaseModel):
    """
    Result of a validation operation.
    """
    is_valid: bool = Field(description="Whether the validation passed")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Validation errors if any"
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Validation warnings if any"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }

class SchemaRegistry:
    """
    Registry of output schemas for different agent types.
    """
    _schemas: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register_schema(cls, agent_type: str, schema: Dict[str, Any]) -> None:
        """
        Register a schema for an agent type.
        
        Args:
            agent_type: Type of agent (e.g., 'analyzer', 'researcher')
            schema: JSON schema for the agent's output
        """
        cls._schemas[agent_type] = schema
        logger.info(f"Registered schema for agent type: {agent_type}")
    
    @classmethod
    def get_schema(cls, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for an agent type.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            JSON schema or None if not found
        """
        return cls._schemas.get(agent_type)
    
    @classmethod
    def has_schema(cls, agent_type: str) -> bool:
        """
        Check if a schema exists for an agent type.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            True if a schema exists, False otherwise
        """
        return agent_type in cls._schemas

def validate_message(message: AppletMessage) -> ValidationResult:
    """
    Validate an agent message against its schema.
    
    Args:
        message: The message to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    # Extract agent type from context
    agent_type = message.context.get("agent_type")
    if not agent_type:
        logger.warning("No agent_type found in message context, skipping validation")
        return ValidationResult(
            is_valid=True,
            warnings=[{"message": "No agent_type found in message context, skipping validation"}]
        )
    
    # Check if schema exists for this agent type
    if not SchemaRegistry.has_schema(agent_type):
        logger.warning(f"No schema found for agent type: {agent_type}, skipping validation")
        return ValidationResult(
            is_valid=True,
            warnings=[{"message": f"No schema found for agent type: {agent_type}, skipping validation"}]
        )
    
    # Get schema
    schema = SchemaRegistry.get_schema(agent_type)
    
    try:
        # Parse message content as JSON if it's a string
        content = message.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # If content is not valid JSON, we'll validate it as a string
                pass
        
        # Validate against schema
        # For simplicity, we're using a basic approach here
        # In a real implementation, you might use a library like jsonschema
        errors = _validate_against_schema(content, schema)
        
        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors
            )
        
        return ValidationResult(is_valid=True)
    
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return ValidationResult(
            is_valid=False,
            errors=[{"message": f"Validation error: {str(e)}"}]
        )

def _validate_against_schema(content: Any, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate content against a JSON schema.
    
    Args:
        content: Content to validate
        schema: JSON schema
        
    Returns:
        List of validation errors
    """
    # This is a simplified implementation
    # In a real application, use a proper JSON schema validator
    errors = []
    
    # Check type
    expected_type = schema.get("type")
    if expected_type:
        if expected_type == "object" and not isinstance(content, dict):
            errors.append({"message": f"Expected object, got {type(content).__name__}"})
        elif expected_type == "array" and not isinstance(content, list):
            errors.append({"message": f"Expected array, got {type(content).__name__}"})
        elif expected_type == "string" and not isinstance(content, str):
            errors.append({"message": f"Expected string, got {type(content).__name__}"})
        elif expected_type == "number" and not isinstance(content, (int, float)):
            errors.append({"message": f"Expected number, got {type(content).__name__}"})
        elif expected_type == "boolean" and not isinstance(content, bool):
            errors.append({"message": f"Expected boolean, got {type(content).__name__}"})
    
    # Check properties if object
    if isinstance(content, dict) and "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            # Check required properties
            if "required" in schema and prop_name in schema["required"] and prop_name not in content:
                errors.append({"message": f"Missing required property: {prop_name}"})
                continue
            
            # Validate property if present
            if prop_name in content:
                prop_errors = _validate_against_schema(content[prop_name], prop_schema)
                for error in prop_errors:
                    error["path"] = f"{prop_name}.{error.get('path', '')}" if "path" in error else prop_name
                errors.extend(prop_errors)
    
    # Check items if array
    if isinstance(content, list) and "items" in schema:
        for i, item in enumerate(content):
            item_errors = _validate_against_schema(item, schema["items"])
            for error in item_errors:
                error["path"] = f"[{i}].{error.get('path', '')}" if "path" in error else f"[{i}]"
            errors.extend(item_errors)
    
    return errors

# Register some example schemas
def register_default_schemas():
    """Register default schemas for common agent types"""
    
    # Analyzer agent schema
    analyzer_schema = {
        "type": "object",
        "required": ["analysis", "confidence", "recommendations"],
        "properties": {
            "analysis": {
                "type": "string",
                "description": "Detailed analysis of the data"
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0 and 1"
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of recommendations based on the analysis"
            }
        }
    }
    
    # Researcher agent schema
    researcher_schema = {
        "type": "object",
        "required": ["findings", "sources"],
        "properties": {
            "findings": {
                "type": "string",
                "description": "Research findings"
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "url"],
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Source title"
                        },
                        "url": {
                            "type": "string",
                            "description": "Source URL"
                        },
                        "relevance": {
                            "type": "number",
                            "description": "Relevance score between 0 and 1"
                        }
                    }
                },
                "description": "List of sources"
            }
        }
    }
    
    # Register schemas
    SchemaRegistry.register_schema("analyzer", analyzer_schema)
    SchemaRegistry.register_schema("researcher", researcher_schema)

# Register default schemas on module import
register_default_schemas()
