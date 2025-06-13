"""
Validation module for the SynApps Orchestrator v0.5.0
"""

from core.validation.schema_validator import (
    validate_message,
    ValidationResult,
    SchemaRegistry,
    register_default_schemas
)

__all__ = [
    "validate_message",
    "ValidationResult",
    "SchemaRegistry",
    "register_default_schemas"
]
