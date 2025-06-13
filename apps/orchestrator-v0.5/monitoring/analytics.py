"""
Analytics for the Meta-Agent Orchestrator
Provides insights and visualizations for workflow executions
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json

from monitoring.metrics import MetricsCollector

logger = logging.getLogger("monitoring.analytics")

class AnalyticsEngine:
    """
    Analytics engine for the Meta-Agent Orchestrator.
    Processes metrics data to provide insights and visualizations.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize the analytics engine.
        
        Args:
            metrics_collector: The metrics collector to use
        """
        self.metrics_collector = metrics_collector
        logger.info("Analytics engine initialized")
    
    def get_workflow_performance_summary(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get a performance summary for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Performance summary
        """
        workflow_metrics = self.metrics_collector.get_workflow_metrics(workflow_id)
        if not workflow_metrics:
            return {"error": f"No metrics found for workflow {workflow_id}"}
        
        # Get node metrics for this workflow
        node_metrics = {}
        if workflow_id in self.metrics_collector.node_metrics:
            node_metrics = self.metrics_collector.node_metrics[workflow_id]
        
        # Calculate average node execution time
        avg_node_execution_time = 0
        if node_metrics:
            execution_times = [
                metrics.get("execution_time", 0) 
                for metrics in node_metrics.values() 
                if metrics.get("execution_time", 0) > 0
            ]
            if execution_times:
                avg_node_execution_time = sum(execution_times) / len(execution_times)
        
        # Calculate success rate
        total_nodes = workflow_metrics.get("nodes_executed", 0)
        failed_nodes = sum(
            1 for metrics in node_metrics.values() 
            if metrics.get("status") == "failed"
        )
        success_rate = 1.0
        if total_nodes > 0:
            success_rate = (total_nodes - failed_nodes) / total_nodes
        
        return {
            "workflow_id": workflow_id,
            "execution_time": workflow_metrics.get("execution_time", 0),
            "status": workflow_metrics.get("status", "unknown"),
            "nodes_executed": total_nodes,
            "validation_failures": workflow_metrics.get("validation_failures", 0),
            "rule_violations": workflow_metrics.get("rule_violations", 0),
            "avg_node_execution_time": avg_node_execution_time,
            "success_rate": success_rate,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_node_performance_breakdown(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get a performance breakdown by node for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of node performance metrics
        """
        if workflow_id not in self.metrics_collector.node_metrics:
            return []
        
        node_metrics = self.metrics_collector.node_metrics[workflow_id]
        breakdown = []
        
        for node_id, metrics in node_metrics.items():
            breakdown.append({
                "node_id": node_id,
                "execution_time": metrics.get("execution_time", 0),
                "status": metrics.get("status", "unknown"),
                "validation_failures": metrics.get("validation_failures", 0),
                "rule_violations": metrics.get("rule_violations", 0)
            })
        
        # Sort by execution time (descending)
        breakdown.sort(key=lambda x: x["execution_time"], reverse=True)
        
        return breakdown
    
    def get_validation_failure_analysis(self, workflow_id: str) -> Dict[str, Any]:
        """
        Analyze validation failures for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Analysis of validation failures
        """
        if workflow_id not in self.metrics_collector.node_metrics:
            return {"total_failures": 0, "failures_by_node": {}, "common_errors": []}
        
        node_metrics = self.metrics_collector.node_metrics[workflow_id]
        failures_by_node = {}
        all_errors = []
        
        for node_id, metrics in node_metrics.items():
            failures = metrics.get("validation_failures", 0)
            if failures > 0:
                failures_by_node[node_id] = failures
                
                # Collect error details
                if "validation_details" in metrics:
                    all_errors.extend(metrics["validation_details"])
        
        # Count error types
        error_counts = {}
        for error in all_errors:
            error_type = error.get("error_type", "unknown")
            if error_type not in error_counts:
                error_counts[error_type] = 0
            error_counts[error_type] += 1
        
        # Get most common errors
        common_errors = [
            {"type": error_type, "count": count}
            for error_type, count in error_counts.items()
        ]
        common_errors.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_failures": sum(failures_by_node.values()),
            "failures_by_node": failures_by_node,
            "common_errors": common_errors
        }
    
    def get_rule_violation_analysis(self, workflow_id: str) -> Dict[str, Any]:
        """
        Analyze rule violations for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Analysis of rule violations
        """
        if workflow_id not in self.metrics_collector.node_metrics:
            return {"total_violations": 0, "violations_by_node": {}, "violations_by_rule": {}}
        
        node_metrics = self.metrics_collector.node_metrics[workflow_id]
        violations_by_node = {}
        violations_by_rule = {}
        
        for node_id, metrics in node_metrics.items():
            violations = metrics.get("rule_violations", 0)
            if violations > 0:
                violations_by_node[node_id] = violations
                
                # Count violations by rule
                if "rule_violations_details" in metrics:
                    for violation in metrics["rule_violations_details"]:
                        rule_id = violation.get("rule_id", "unknown")
                        if rule_id not in violations_by_rule:
                            violations_by_rule[rule_id] = 0
                        violations_by_rule[rule_id] += 1
        
        return {
            "total_violations": sum(violations_by_node.values()),
            "violations_by_node": violations_by_node,
            "violations_by_rule": violations_by_rule
        }
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get system health metrics.
        
        Returns:
            System health metrics
        """
        global_metrics = self.metrics_collector.get_global_metrics()
        
        # Calculate average workflow execution time
        avg_workflow_time = 0
        if global_metrics.get("total_workflows_executed", 0) > 0:
            avg_workflow_time = (
                global_metrics.get("total_execution_time", 0) / 
                global_metrics.get("total_workflows_executed", 1)
            )
        
        # Calculate error rates
        validation_failure_rate = 0
        if global_metrics.get("total_nodes_executed", 0) > 0:
            validation_failure_rate = (
                global_metrics.get("total_validation_failures", 0) / 
                global_metrics.get("total_nodes_executed", 1)
            )
        
        rule_violation_rate = 0
        if global_metrics.get("total_nodes_executed", 0) > 0:
            rule_violation_rate = (
                global_metrics.get("total_rule_violations", 0) / 
                global_metrics.get("total_nodes_executed", 1)
            )
        
        return {
            "uptime_seconds": global_metrics.get("uptime_seconds", 0),
            "total_workflows_executed": global_metrics.get("total_workflows_executed", 0),
            "total_nodes_executed": global_metrics.get("total_nodes_executed", 0),
            "avg_workflow_execution_time": avg_workflow_time,
            "validation_failure_rate": validation_failure_rate,
            "rule_violation_rate": rule_violation_rate,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_performance_report(self, workflow_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Performance report
        """
        return {
            "summary": self.get_workflow_performance_summary(workflow_id),
            "node_breakdown": self.get_node_performance_breakdown(workflow_id),
            "validation_analysis": self.get_validation_failure_analysis(workflow_id),
            "rule_violation_analysis": self.get_rule_violation_analysis(workflow_id),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def export_metrics_json(self, workflow_id: str) -> str:
        """
        Export metrics for a workflow as JSON.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            JSON string of metrics
        """
        workflow_metrics = self.metrics_collector.get_workflow_metrics(workflow_id)
        node_metrics = {}
        if workflow_id in self.metrics_collector.node_metrics:
            node_metrics = self.metrics_collector.node_metrics[workflow_id]
        
        export_data = {
            "workflow_id": workflow_id,
            "workflow_metrics": workflow_metrics,
            "node_metrics": node_metrics,
            "exported_at": datetime.utcnow().isoformat()
        }
        
        return json.dumps(export_data, indent=2)
