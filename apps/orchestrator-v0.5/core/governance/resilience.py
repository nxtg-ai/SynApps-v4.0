"""
Resilience Module for the Meta-Agent Orchestrator

Provides error handling, retry mechanisms, fallback strategies, and circuit breakers
to ensure robust workflow execution even in the presence of failures.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from enum import Enum
from datetime import datetime, timedelta

from models.agent_message import AppletMessage
from models.workflow import WorkflowNode, WorkflowEdge, Workflow
from core.governance.rule_engine import RuleEngine, RuleResult

logger = logging.getLogger("governance.resilience")

class ErrorSeverity(str, Enum):
    """
    Severity levels for errors encountered during workflow execution.
    """
    INFO = "info"           # Informational, not an error
    WARNING = "warning"     # Warning, execution can continue
    ERROR = "error"         # Error, execution may need to be retried or rerouted
    CRITICAL = "critical"   # Critical error, execution should be aborted

class ErrorType(str, Enum):
    """
    Types of errors that can occur during workflow execution.
    """
    VALIDATION = "validation"           # Data validation error
    EXECUTION = "execution"             # Error during node execution
    TIMEOUT = "timeout"                 # Execution timeout
    RATE_LIMIT = "rate_limit"           # Rate limit exceeded
    CONNECTIVITY = "connectivity"       # Network connectivity issue
    AUTHORIZATION = "authorization"     # Authorization error
    RESOURCE = "resource"               # Resource not found or unavailable
    SYSTEM = "system"                   # System error
    CUSTOM = "custom"                   # Custom error type

class RetryStrategy(str, Enum):
    """
    Strategies for retrying failed operations.
    """
    IMMEDIATE = "immediate"             # Retry immediately
    FIXED_DELAY = "fixed_delay"         # Retry after a fixed delay
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Retry with exponential backoff
    LINEAR_BACKOFF = "linear_backoff"   # Retry with linear backoff
    RANDOM_DELAY = "random_delay"       # Retry with random delay

class FallbackStrategy(str, Enum):
    """
    Strategies for handling failures when retries are exhausted.
    """
    DEFAULT_RESPONSE = "default_response"  # Return a default response
    ALTERNATE_NODE = "alternate_node"      # Route to an alternate node
    ERROR_NODE = "error_node"              # Route to a dedicated error handling node
    SKIP_NODE = "skip_node"                # Skip the failed node
    ABORT_WORKFLOW = "abort_workflow"      # Abort the entire workflow

class ResilienceConfig:
    """
    Configuration for resilience mechanisms.
    """
    def __init__(
        self,
        max_retries: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        jitter_ms: int = 500,
        fallback_strategy: FallbackStrategy = FallbackStrategy.ERROR_NODE,
        fallback_node_id: Optional[str] = None,
        default_response: Optional[Any] = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_ms: int = 60000
    ):
        """
        Initialize resilience configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_strategy: Strategy for retrying failed operations
            initial_delay_ms: Initial delay between retries in milliseconds
            max_delay_ms: Maximum delay between retries in milliseconds
            jitter_ms: Random jitter to add to delays in milliseconds
            fallback_strategy: Strategy for handling failures when retries are exhausted
            fallback_node_id: ID of the fallback node (for ALTERNATE_NODE and ERROR_NODE strategies)
            default_response: Default response to return (for DEFAULT_RESPONSE strategy)
            circuit_breaker_threshold: Number of failures before opening the circuit breaker
            circuit_breaker_timeout_ms: Time to keep the circuit breaker open in milliseconds
        """
        self.max_retries = max_retries
        self.retry_strategy = retry_strategy
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter_ms = jitter_ms
        self.fallback_strategy = fallback_strategy
        self.fallback_node_id = fallback_node_id
        self.default_response = default_response
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout_ms = circuit_breaker_timeout_ms

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout_ms: int = 60000
    ):
        """
        Initialize a circuit breaker.
        
        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening the circuit
            reset_timeout_ms: Time to keep the circuit open in milliseconds
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_ms = reset_timeout_ms
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self) -> None:
        """Record a successful operation"""
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
    
    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.
        
        Returns:
            True if the request should be allowed, False otherwise
        """
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if reset timeout has elapsed
            if self.last_failure_time:
                elapsed_ms = (datetime.now() - self.last_failure_time).total_seconds() * 1000
                if elapsed_ms >= self.reset_timeout_ms:
                    logger.info(f"Circuit breaker {self.name} transitioning to half-open after {elapsed_ms}ms")
                    self.state = "half-open"
                    return True
            return False
        
        # Half-open state: allow one request to test the service
        return True
    
    def reset(self) -> None:
        """Reset the circuit breaker to closed state"""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None

class ResilienceManager:
    """
    Manager for resilience mechanisms in the orchestrator.
    """
    def __init__(self, rule_engine: RuleEngine):
        """
        Initialize the resilience manager.
        
        Args:
            rule_engine: Rule engine for validating outputs
        """
        self.rule_engine = rule_engine
        self.node_configs: Dict[str, ResilienceConfig] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[str, Callable] = {}
        
        logger.info("ResilienceManager initialized")
    
    def configure_node_resilience(
        self,
        node_id: str,
        config: ResilienceConfig
    ) -> None:
        """
        Configure resilience for a node.
        
        Args:
            node_id: ID of the node
            config: Resilience configuration
        """
        self.node_configs[node_id] = config
        
        # Create circuit breaker if it doesn't exist
        if node_id not in self.circuit_breakers:
            self.circuit_breakers[node_id] = CircuitBreaker(
                name=f"node-{node_id}",
                failure_threshold=config.circuit_breaker_threshold,
                reset_timeout_ms=config.circuit_breaker_timeout_ms
            )
        
        logger.info(f"Configured resilience for node {node_id}")
    
    def register_error_handler(
        self,
        error_type: ErrorType,
        handler: Callable[[str, WorkflowNode, AppletMessage, Dict[str, Any]], Tuple[bool, Optional[AppletMessage]]]
    ) -> None:
        """
        Register a handler for a specific error type.
        
        Args:
            error_type: Type of error to handle
            handler: Function to handle the error
                The function should take (workflow_id, node, message, error_context) and return
                (handled, new_message)
        """
        self.error_handlers[error_type] = handler
        logger.info(f"Registered handler for error type {error_type}")
    
    def get_node_config(self, node_id: str) -> ResilienceConfig:
        """
        Get resilience configuration for a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Resilience configuration for the node
        """
        # Return node-specific config if available, otherwise return default
        return self.node_configs.get(node_id, ResilienceConfig())
    
    def should_allow_execution(self, node_id: str) -> bool:
        """
        Check if execution should be allowed for a node based on circuit breaker status.
        
        Args:
            node_id: ID of the node
            
        Returns:
            True if execution should be allowed, False otherwise
        """
        circuit_breaker = self.circuit_breakers.get(node_id)
        if circuit_breaker:
            return circuit_breaker.allow_request()
        return True
    
    def calculate_retry_delay_ms(
        self,
        retry_count: int,
        config: ResilienceConfig
    ) -> int:
        """
        Calculate delay before next retry based on retry strategy.
        
        Args:
            retry_count: Current retry attempt (0-based)
            config: Resilience configuration
            
        Returns:
            Delay in milliseconds before next retry
        """
        import random
        
        if config.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
            
        elif config.retry_strategy == RetryStrategy.FIXED_DELAY:
            delay = config.initial_delay_ms
            
        elif config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # 2^retry_count * initial_delay
            delay = config.initial_delay_ms * (2 ** retry_count)
            
        elif config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            # initial_delay * (retry_count + 1)
            delay = config.initial_delay_ms * (retry_count + 1)
            
        elif config.retry_strategy == RetryStrategy.RANDOM_DELAY:
            # Random delay between initial_delay and max_delay
            delay = random.randint(config.initial_delay_ms, config.max_delay_ms)
            
        else:
            # Default to fixed delay
            delay = config.initial_delay_ms
        
        # Add jitter
        if config.jitter_ms > 0:
            jitter = random.randint(-config.jitter_ms, config.jitter_ms)
            delay += jitter
        
        # Cap at max delay
        return min(delay, config.max_delay_ms)
    
    async def handle_error(
        self,
        workflow_id: str,
        node: WorkflowNode,
        message: AppletMessage,
        error_type: ErrorType,
        error_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[AppletMessage], Optional[str]]:
        """
        Handle an error during workflow execution.
        
        Args:
            workflow_id: ID of the workflow
            node: Node where the error occurred
            message: Message being processed
            error_type: Type of error
            error_context: Additional context about the error
            
        Returns:
            Tuple of (handled, new_message, next_node_id)
                handled: True if the error was handled, False otherwise
                new_message: New message to use (if handled)
                next_node_id: ID of the next node to execute (if handled and routing to another node)
        """
        node_id = node.id
        config = self.get_node_config(node_id)
        
        # Record failure in circuit breaker
        circuit_breaker = self.circuit_breakers.get(node_id)
        if circuit_breaker:
            circuit_breaker.record_failure()
        
        # Check if there's a specific handler for this error type
        if error_type in self.error_handlers:
            try:
                handled, new_message = await self.error_handlers[error_type](
                    workflow_id, node, message, error_context
                )
                if handled:
                    logger.info(f"Error {error_type} handled by custom handler for node {node_id}")
                    return True, new_message, None
            except Exception as e:
                logger.error(f"Error in custom handler for {error_type}: {str(e)}")
        
        # Get retry count from context or initialize
        retry_count = error_context.get("retry_count", 0)
        
        # Check if we should retry
        if retry_count < config.max_retries:
            # Calculate delay before retry
            delay_ms = self.calculate_retry_delay_ms(retry_count, config)
            
            # Update retry count in context
            error_context["retry_count"] = retry_count + 1
            
            logger.info(
                f"Retrying node {node_id} (attempt {retry_count + 1}/{config.max_retries}) "
                f"after {delay_ms}ms delay"
            )
            
            # Wait before retry
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            
            # Return same message for retry
            return True, message, None
        
        # Retries exhausted, apply fallback strategy
        logger.warning(
            f"Retries exhausted for node {node_id} ({config.max_retries} attempts). "
            f"Applying fallback strategy: {config.fallback_strategy}"
        )
        
        if config.fallback_strategy == FallbackStrategy.DEFAULT_RESPONSE:
            # Return default response
            if config.default_response is not None:
                new_message = AppletMessage(
                    content=config.default_response,
                    metadata={
                        "fallback": True,
                        "original_error": error_context
                    }
                )
                return True, new_message, None
        
        elif config.fallback_strategy == FallbackStrategy.ALTERNATE_NODE:
            # Route to alternate node
            if config.fallback_node_id:
                return True, message, config.fallback_node_id
        
        elif config.fallback_strategy == FallbackStrategy.ERROR_NODE:
            # Route to error handling node
            if config.fallback_node_id:
                # Add error context to message metadata
                message.metadata = message.metadata or {}
                message.metadata["error"] = error_context
                return True, message, config.fallback_node_id
        
        elif config.fallback_strategy == FallbackStrategy.SKIP_NODE:
            # Skip the failed node
            return True, message, None
        
        # Default: abort workflow (or let caller decide)
        return False, None, None
    
    async def validate_output(
        self,
        workflow_id: str,
        node: WorkflowNode,
        message: AppletMessage
    ) -> Tuple[bool, Dict[str, RuleResult], Dict[str, Any]]:
        """
        Validate node output against governance rules.
        
        Args:
            workflow_id: ID of the workflow
            node: Node that produced the output
            message: Output message to validate
            
        Returns:
            Tuple of (valid, rule_results, error_context)
                valid: True if output is valid, False otherwise
                rule_results: Results of rule application
                error_context: Error context if validation failed
        """
        # Apply governance rules
        rule_results = await self.rule_engine.apply_rules(workflow_id, node, message)
        
        # Check for errors
        errors = []
        for rule_id, result in rule_results.items():
            if not result.passed:
                errors.append({
                    "rule_id": rule_id,
                    "message": result.message,
                    "metadata": result.metadata
                })
        
        if errors:
            error_context = {
                "error_type": ErrorType.VALIDATION,
                "errors": errors,
                "retry_count": 0
            }
            return False, rule_results, error_context
        
        return True, rule_results, {}
    
    def record_success(self, node_id: str) -> None:
        """
        Record a successful node execution.
        
        Args:
            node_id: ID of the node
        """
        circuit_breaker = self.circuit_breakers.get(node_id)
        if circuit_breaker:
            circuit_breaker.record_success()
    
    def get_circuit_breaker_status(self, node_id: str) -> Dict[str, Any]:
        """
        Get status of circuit breaker for a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Status information for the circuit breaker
        """
        circuit_breaker = self.circuit_breakers.get(node_id)
        if not circuit_breaker:
            return {"exists": False}
        
        return {
            "exists": True,
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
            "last_failure_time": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
            "failure_threshold": circuit_breaker.failure_threshold,
            "reset_timeout_ms": circuit_breaker.reset_timeout_ms
        }
