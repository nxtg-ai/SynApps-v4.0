"""
Compliance Service for the Meta-Agent Orchestrator

Manages compliance rules, checks, metrics collection, and report generation.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from datetime import datetime, timedelta
import json

from monitoring.compliance.models import (
    ComplianceRuleType, ComplianceRuleSeverity, ComplianceRuleStatus,
    ComplianceRule, ComplianceCheck, ComplianceMetric, ComplianceReport,
    ComplianceReportFormat, ComplianceReportRequest, ComplianceDashboardMetrics
)

logger = logging.getLogger("monitoring.compliance.service")

class ComplianceService:
    """
    Service for managing compliance rules, checks, and reporting.
    """
    def __init__(self):
        """Initialize the compliance service."""
        # Rules by rule_id
        self.rules: Dict[str, ComplianceRule] = {}
        
        # Checks by check_id
        self.checks: Dict[str, ComplianceCheck] = {}
        
        # Metrics by metric_id
        self.metrics: Dict[str, ComplianceMetric] = {}
        
        # Reports by report_id
        self.reports: Dict[str, ComplianceReport] = {}
        
        # Rule check listeners
        self.check_listeners: List[Callable[[ComplianceCheck], Awaitable[None]]] = []
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        
        logger.info("ComplianceService initialized")
    
    async def start(self) -> None:
        """Start the compliance service"""
        # Load default rules
        await self._load_default_rules()
        
        logger.info("ComplianceService started")
    
    async def _load_default_rules(self) -> None:
        """Load default compliance rules"""
        default_rules = [
            ComplianceRule(
                rule_id=str(uuid.uuid4()),
                name="Content Policy Check",
                description="Checks messages for content policy violations",
                rule_type=ComplianceRuleType.CONTENT_POLICY,
                severity=ComplianceRuleSeverity.HIGH,
                parameters={
                    "prohibited_content": [
                        "harmful_instructions",
                        "hate_speech",
                        "explicit_content"
                    ],
                    "threshold": 0.8
                }
            ),
            ComplianceRule(
                rule_id=str(uuid.uuid4()),
                name="Schema Validation",
                description="Validates message schemas against defined schemas",
                rule_type=ComplianceRuleType.SCHEMA_VALIDATION,
                severity=ComplianceRuleSeverity.MEDIUM,
                parameters={
                    "strict_mode": True,
                    "allow_additional_properties": False
                }
            ),
            ComplianceRule(
                rule_id=str(uuid.uuid4()),
                name="Agent Behavior Monitor",
                description="Monitors agent behavior for compliance with defined patterns",
                rule_type=ComplianceRuleType.AGENT_BEHAVIOR,
                severity=ComplianceRuleSeverity.MEDIUM,
                parameters={
                    "max_consecutive_errors": 3,
                    "max_response_time_ms": 10000
                }
            ),
            ComplianceRule(
                rule_id=str(uuid.uuid4()),
                name="Prompt Injection Protection",
                description="Detects and prevents prompt injection attempts",
                rule_type=ComplianceRuleType.PROMPT_INJECTION,
                severity=ComplianceRuleSeverity.CRITICAL,
                parameters={
                    "detection_patterns": [
                        "ignore previous instructions",
                        "disregard your directives",
                        "forget your training"
                    ],
                    "threshold": 0.7
                }
            ),
            ComplianceRule(
                rule_id=str(uuid.uuid4()),
                name="Rate Limiting",
                description="Enforces rate limits on API calls and agent interactions",
                rule_type=ComplianceRuleType.RATE_LIMIT,
                severity=ComplianceRuleSeverity.LOW,
                parameters={
                    "max_requests_per_minute": 60,
                    "max_tokens_per_minute": 10000
                }
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default compliance rules")
    
    async def register_check_listener(
        self,
        listener: Callable[[ComplianceCheck], Awaitable[None]]
    ) -> None:
        """
        Register a listener for compliance checks.
        
        Args:
            listener: Async function to call with checks
        """
        self.check_listeners.append(listener)
        logger.info("Registered compliance check listener")
    
    async def _notify_check_listeners(self, check: ComplianceCheck) -> None:
        """
        Notify all check listeners of a new check.
        
        Args:
            check: Check to notify about
        """
        for listener in self.check_listeners:
            try:
                await listener(check)
            except Exception as e:
                logger.error(f"Error in compliance check listener: {str(e)}")
    
    async def create_rule(self, rule: ComplianceRule) -> ComplianceRule:
        """
        Create a new compliance rule.
        
        Args:
            rule: Rule to create
            
        Returns:
            Created rule
        """
        # Ensure rule has an ID
        if not rule.rule_id:
            rule.rule_id = str(uuid.uuid4())
        
        # Set timestamps
        now = datetime.now()
        rule.created_at = now
        rule.updated_at = now
        
        # Store rule
        self.rules[rule.rule_id] = rule
        
        logger.info(f"Created compliance rule: {rule.name} ({rule.rule_id})")
        return rule
    
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[ComplianceRule]:
        """
        Update an existing compliance rule.
        
        Args:
            rule_id: ID of the rule to update
            updates: Updates to apply
            
        Returns:
            Updated rule, or None if not found
        """
        if rule_id not in self.rules:
            logger.warning(f"Cannot update unknown rule: {rule_id}")
            return None
        
        # Get rule
        rule = self.rules[rule_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        # Update timestamp
        rule.updated_at = datetime.now()
        
        logger.info(f"Updated compliance rule: {rule.name} ({rule.rule_id})")
        return rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a compliance rule.
        
        Args:
            rule_id: ID of the rule to delete
            
        Returns:
            True if deleted, False if not found
        """
        if rule_id not in self.rules:
            logger.warning(f"Cannot delete unknown rule: {rule_id}")
            return False
        
        # Delete rule
        del self.rules[rule_id]
        
        logger.info(f"Deleted compliance rule: {rule_id}")
        return True
    
    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """
        Get a compliance rule by ID.
        
        Args:
            rule_id: ID of the rule
            
        Returns:
            Rule, or None if not found
        """
        return self.rules.get(rule_id)
    
    def get_rules(
        self,
        rule_type: Optional[ComplianceRuleType] = None,
        enabled_only: bool = True
    ) -> List[ComplianceRule]:
        """
        Get compliance rules, optionally filtered.
        
        Args:
            rule_type: Optional rule type to filter by
            enabled_only: Whether to only include enabled rules
            
        Returns:
            List of rules
        """
        rules = list(self.rules.values())
        
        # Filter by type
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        # Filter by enabled
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
