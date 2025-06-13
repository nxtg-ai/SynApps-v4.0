"""
Compliance Metrics and Reporting Models

Defines data structures for tracking compliance with governance rules,
monitoring agent behavior, and generating reports for audit and analysis.
"""

from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class ComplianceRuleType(str, Enum):
    """
    Types of compliance rules that can be enforced.
    """
    CONTENT_POLICY = "content_policy"        # Content policy rules
    RATE_LIMIT = "rate_limit"                # Rate limiting rules
    AUTHENTICATION = "authentication"        # Authentication rules
    AUTHORIZATION = "authorization"          # Authorization rules
    DATA_PRIVACY = "data_privacy"            # Data privacy rules
    SCHEMA_VALIDATION = "schema_validation"  # Schema validation rules
    PROMPT_INJECTION = "prompt_injection"    # Prompt injection protection
    OUTPUT_FILTERING = "output_filtering"    # Output filtering rules
    AGENT_BEHAVIOR = "agent_behavior"        # Agent behavior rules
    CUSTOM_RULE = "custom_rule"              # Custom compliance rules

class ComplianceRuleSeverity(str, Enum):
    """
    Severity levels for compliance rule violations.
    """
    INFO = "info"              # Informational only
    LOW = "low"                # Low severity
    MEDIUM = "medium"          # Medium severity
    HIGH = "high"              # High severity
    CRITICAL = "critical"      # Critical severity

class ComplianceRuleStatus(str, Enum):
    """
    Status of a compliance rule check.
    """
    PASSED = "passed"          # Rule check passed
    FAILED = "failed"          # Rule check failed
    WARNING = "warning"        # Rule check passed with warnings
    ERROR = "error"            # Error during rule check
    SKIPPED = "skipped"        # Rule check skipped

class ComplianceRule(BaseModel):
    """
    Definition of a compliance rule.
    """
    rule_id: str = Field(description="Unique identifier for the rule")
    name: str = Field(description="Name of the rule")
    description: str = Field(description="Description of the rule")
    rule_type: ComplianceRuleType = Field(description="Type of rule")
    severity: ComplianceRuleSeverity = Field(description="Severity of rule violations")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the rule")
    created_at: datetime = Field(default_factory=datetime.now, description="When the rule was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the rule was last updated")

class ComplianceCheck(BaseModel):
    """
    Result of a compliance rule check.
    """
    check_id: str = Field(description="Unique identifier for the check")
    rule_id: str = Field(description="ID of the rule that was checked")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow (if applicable)")
    node_id: Optional[str] = Field(None, description="ID of the node (if applicable)")
    agent_id: Optional[str] = Field(None, description="ID of the agent (if applicable)")
    message_id: Optional[str] = Field(None, description="ID of the message (if applicable)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the check was performed")
    status: ComplianceRuleStatus = Field(description="Status of the check")
    details: Dict[str, Any] = Field(default_factory=dict, description="Details of the check")
    remediation_taken: Optional[str] = Field(None, description="Remediation action taken (if any)")

class ComplianceMetric(BaseModel):
    """
    Metric for compliance reporting.
    """
    metric_id: str = Field(description="Unique identifier for the metric")
    name: str = Field(description="Name of the metric")
    description: str = Field(description="Description of the metric")
    rule_type: Optional[ComplianceRuleType] = Field(None, description="Type of rule (if applicable)")
    value: float = Field(description="Value of the metric")
    unit: str = Field(description="Unit of the metric")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the metric was recorded")
    dimensions: Dict[str, str] = Field(default_factory=dict, description="Dimensions for the metric")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ComplianceReport(BaseModel):
    """
    Compliance report for a workflow or time period.
    """
    report_id: str = Field(description="Unique identifier for the report")
    name: str = Field(description="Name of the report")
    description: str = Field(description="Description of the report")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow (if applicable)")
    start_time: datetime = Field(description="Start time of the report period")
    end_time: datetime = Field(description="End time of the report period")
    generated_at: datetime = Field(default_factory=datetime.now, description="When the report was generated")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of the report")
    metrics: List[ComplianceMetric] = Field(default_factory=list, description="Metrics in the report")
    checks: List[ComplianceCheck] = Field(default_factory=list, description="Checks in the report")
    violations: List[ComplianceCheck] = Field(default_factory=list, description="Rule violations in the report")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations based on the report")

class ComplianceReportFormat(str, Enum):
    """
    Format options for compliance reports.
    """
    JSON = "json"              # JSON format
    CSV = "csv"                # CSV format
    HTML = "html"              # HTML format
    PDF = "pdf"                # PDF format
    MARKDOWN = "markdown"      # Markdown format

class ComplianceReportRequest(BaseModel):
    """
    Request for generating a compliance report.
    """
    name: str = Field(description="Name of the report")
    description: Optional[str] = Field(None, description="Description of the report")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow (if applicable)")
    start_time: datetime = Field(description="Start time of the report period")
    end_time: datetime = Field(description="End time of the report period")
    rule_types: Optional[List[ComplianceRuleType]] = Field(None, description="Types of rules to include")
    severities: Optional[List[ComplianceRuleSeverity]] = Field(None, description="Severities to include")
    include_passed: bool = Field(True, description="Whether to include passed checks")
    format: ComplianceReportFormat = Field(ComplianceReportFormat.JSON, description="Format of the report")
    include_recommendations: bool = Field(True, description="Whether to include recommendations")

class ComplianceDashboardMetrics(BaseModel):
    """
    Metrics for the compliance dashboard.
    """
    total_workflows: int = Field(0, description="Total number of workflows")
    total_checks: int = Field(0, description="Total number of compliance checks")
    total_violations: int = Field(0, description="Total number of rule violations")
    compliance_rate: float = Field(0.0, description="Overall compliance rate (0-100)")
    violation_by_severity: Dict[str, int] = Field(default_factory=dict, description="Violations by severity")
    violation_by_rule_type: Dict[str, int] = Field(default_factory=dict, description="Violations by rule type")
    recent_violations: List[ComplianceCheck] = Field(default_factory=list, description="Recent violations")
    top_violated_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Most frequently violated rules")
    metrics_over_time: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Metrics over time")
