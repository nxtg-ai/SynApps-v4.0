"""
Configuration models for the Meta-Agent Orchestrator
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import os

class LLMConfig(BaseModel):
    """
    Configuration for LLM providers and models.
    """
    provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, etc.)"
    )
    model: str = Field(
        default="gpt-4",
        description="Model to use for LLM operations"
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for LLM sampling"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum number of tokens for LLM responses"
    )
    additional_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific parameters"
    )
    
    @validator('provider')
    def validate_provider(cls, v):
        """Validate that the provider is supported"""
        supported_providers = ['openai', 'anthropic', 'cohere', 'huggingface']
        if v not in supported_providers:
            raise ValueError(f"Provider must be one of: {', '.join(supported_providers)}")
        return v

class DatabaseConfig(BaseModel):
    """
    Configuration for database connections.
    """
    url: str = Field(
        description="Database connection URL"
    )
    pool_size: int = Field(
        default=5,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections to overflow"
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL statements to stdout"
    )

class MetaAgentConfig(BaseModel):
    """
    Configuration for the Meta-Agent Orchestrator.
    """
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed operations"
    )
    validation_strictness: float = Field(
        default=0.8,
        description="Strictness level for output validation (0.0-1.0)"
    )
    governance_rules: List[str] = Field(
        default_factory=list,
        description="List of governance rule IDs to apply"
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable monitoring and metrics collection"
    )
    prompt_templates: Dict[str, str] = Field(
        default_factory=dict,
        description="Templates for system prompts by agent type"
    )

class Settings(BaseSettings):
    """
    Global settings for the Meta-Agent Orchestrator.
    """
    app_name: str = Field(
        default="SynApps Meta-Agent Orchestrator",
        description="Name of the application"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration"
    )
    database: DatabaseConfig = Field(
        description="Database configuration"
    )
    meta_agent: MetaAgentConfig = Field(
        default_factory=MetaAgentConfig,
        description="Meta-Agent configuration"
    )
    api_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="API keys for external services"
    )
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        
    @classmethod
    def from_environment(cls) -> "Settings":
        """
        Create settings from environment variables.
        
        Environment variables should be prefixed with ORCHESTRATOR_,
        e.g., ORCHESTRATOR_DEBUG=true.
        """
        # Load settings from environment variables
        database_url = os.getenv("ORCHESTRATOR_DATABASE_URL", "sqlite:///orchestrator.db")
        
        return cls(
            debug=os.getenv("ORCHESTRATOR_DEBUG", "false").lower() == "true",
            environment=os.getenv("ORCHESTRATOR_ENVIRONMENT", "development"),
            database=DatabaseConfig(url=database_url),
            api_keys={
                "openai": os.getenv("ORCHESTRATOR_OPENAI_API_KEY", ""),
                "anthropic": os.getenv("ORCHESTRATOR_ANTHROPIC_API_KEY", ""),
            }
        )
