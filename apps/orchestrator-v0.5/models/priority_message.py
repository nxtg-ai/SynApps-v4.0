"""
Priority Message model for agent communication with priority support
"""

from typing import Dict, Any, Optional
from pydantic import Field, validator

from models.agent_message import AppletMessage

class PriorityMessage(AppletMessage):
    """
    Enhanced message format with priority support for agent communication.
    Extends the standard AppletMessage with priority information.
    
    Priority levels:
    - 0: Lowest priority (background tasks)
    - 1-3: Low priority (non-critical operations)
    - 4-6: Normal priority (default operations)
    - 7-9: High priority (important operations)
    - 10: Highest priority (critical operations)
    """
    
    priority: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Message priority level (0-10, where 10 is highest priority)"
    )
    
    @validator('priority')
    def validate_priority(cls, value):
        """Ensure priority is within valid range"""
        if not (0 <= value <= 10):
            raise ValueError(f"Priority must be between 0 and 10, got {value}")
        return value
    
    def is_critical(self) -> bool:
        """Check if the message is critical (priority >= 8)"""
        return self.priority >= 8
    
    def is_background(self) -> bool:
        """Check if the message is a background task (priority <= 2)"""
        return self.priority <= 2
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "content": "Critical system alert: Database connection lost",
                "context": {
                    "system_prompt": "You are a System Monitor agent. Report critical issues.",
                    "workflow_id": "wf-123",
                    "node_id": "node-456"
                },
                "metadata": {
                    "execution_time": 0.12,
                    "token_count": 42,
                    "model": "gpt-4.1"
                },
                "priority": 10
            }
        }
