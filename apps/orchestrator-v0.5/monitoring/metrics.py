"""
Metrics collection and monitoring for the Meta-Agent Orchestrator
"""

import time
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

logger = logging.getLogger("monitoring.metrics")

class MetricsCollector:
    """
    Collects and records metrics for the Meta-Agent Orchestrator.
    """
    
    def __init__(self):
        """Initialize the metrics collector"""
        self.workflow_metrics: Dict[str, Dict[str, Any]] = {}
        self.node_metrics: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.global_metrics: Dict[str, Any] = {
            "total_workflows_executed": 0,
            "total_nodes_executed": 0,
            "total_validation_failures": 0,
            "total_rule_violations": 0,
            "total_execution_time": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        logger.info("Metrics collector initialized")
    
    def record_workflow_start(self, workflow_id: str) -> None:
        """
        Record the start of a workflow execution.
        
        Args:
            workflow_id: ID of the workflow
        """
        self.workflow_metrics[workflow_id] = {
            "start_time": time.time(),
            "status": "running",
            "nodes_executed": 0,
            "validation_failures": 0,
            "rule_violations": 0,
            "execution_time": 0
        }
        logger.info(f"Workflow {workflow_id} execution started")
    
    def record_workflow_end(self, workflow_id: str, status: str) -> Dict[str, Any]:
        """
        Record the end of a workflow execution.
        
        Args:
            workflow_id: ID of the workflow
            status: Final status of the workflow
            
        Returns:
            Metrics for the workflow execution
        """
        if workflow_id not in self.workflow_metrics:
            logger.warning(f"No start record found for workflow {workflow_id}")
            return {}
        
        metrics = self.workflow_metrics[workflow_id]
        metrics["status"] = status
        metrics["end_time"] = time.time()
        metrics["execution_time"] = metrics["end_time"] - metrics["start_time"]
        
        # Update global metrics
        self.global_metrics["total_workflows_executed"] += 1
        self.global_metrics["total_execution_time"] += metrics["execution_time"]
        
        logger.info(f"Workflow {workflow_id} execution ended with status {status}")
        return metrics
    
    def record_node_start(self, workflow_id: str, node_id: str) -> None:
        """
        Record the start of a node execution.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
        """
        if workflow_id not in self.node_metrics:
            self.node_metrics[workflow_id] = {}
        
        self.node_metrics[workflow_id][node_id] = {
            "start_time": time.time(),
            "status": "running",
            "validation_failures": 0,
            "rule_violations": 0,
            "execution_time": 0
        }
        
        # Update workflow metrics
        if workflow_id in self.workflow_metrics:
            self.workflow_metrics[workflow_id]["nodes_executed"] += 1
        
        logger.info(f"Node {node_id} execution started in workflow {workflow_id}")
    
    def record_node_end(self, workflow_id: str, node_id: str, status: str) -> Dict[str, Any]:
        """
        Record the end of a node execution.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            status: Final status of the node
            
        Returns:
            Metrics for the node execution
        """
        if workflow_id not in self.node_metrics or node_id not in self.node_metrics[workflow_id]:
            logger.warning(f"No start record found for node {node_id} in workflow {workflow_id}")
            return {}
        
        metrics = self.node_metrics[workflow_id][node_id]
        metrics["status"] = status
        metrics["end_time"] = time.time()
        metrics["execution_time"] = metrics["end_time"] - metrics["start_time"]
        
        # Update global metrics
        self.global_metrics["total_nodes_executed"] += 1
        
        logger.info(f"Node {node_id} execution ended with status {status} in workflow {workflow_id}")
        return metrics
    
    def record_validation_failure(self, workflow_id: str, node_id: str, details: Dict[str, Any]) -> None:
        """
        Record a validation failure.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            details: Details of the validation failure
        """
        # Update node metrics
        if workflow_id in self.node_metrics and node_id in self.node_metrics[workflow_id]:
            self.node_metrics[workflow_id][node_id]["validation_failures"] += 1
            if "validation_details" not in self.node_metrics[workflow_id][node_id]:
                self.node_metrics[workflow_id][node_id]["validation_details"] = []
            self.node_metrics[workflow_id][node_id]["validation_details"].append(details)
        
        # Update workflow metrics
        if workflow_id in self.workflow_metrics:
            self.workflow_metrics[workflow_id]["validation_failures"] += 1
        
        # Update global metrics
        self.global_metrics["total_validation_failures"] += 1
        
        logger.warning(f"Validation failure in node {node_id} of workflow {workflow_id}: {json.dumps(details)}")
    
    def record_rule_violation(self, workflow_id: str, node_id: str, rule_id: str, details: Dict[str, Any]) -> None:
        """
        Record a rule violation.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            rule_id: ID of the rule that was violated
            details: Details of the rule violation
        """
        # Update node metrics
        if workflow_id in self.node_metrics and node_id in self.node_metrics[workflow_id]:
            self.node_metrics[workflow_id][node_id]["rule_violations"] += 1
            if "rule_violations_details" not in self.node_metrics[workflow_id][node_id]:
                self.node_metrics[workflow_id][node_id]["rule_violations_details"] = []
            self.node_metrics[workflow_id][node_id]["rule_violations_details"].append({
                "rule_id": rule_id,
                **details
            })
        
        # Update workflow metrics
        if workflow_id in self.workflow_metrics:
            self.workflow_metrics[workflow_id]["rule_violations"] += 1
        
        # Update global metrics
        self.global_metrics["total_rule_violations"] += 1
        
        logger.warning(f"Rule violation ({rule_id}) in node {node_id} of workflow {workflow_id}: {json.dumps(details)}")
    
    def get_workflow_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get metrics for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Metrics for the workflow
        """
        return self.workflow_metrics.get(workflow_id, {})
    
    def get_node_metrics(self, workflow_id: str, node_id: str) -> Dict[str, Any]:
        """
        Get metrics for a node.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            
        Returns:
            Metrics for the node
        """
        if workflow_id not in self.node_metrics:
            return {}
        return self.node_metrics[workflow_id].get(node_id, {})
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """
        Get global metrics.
        
        Returns:
            Global metrics
        """
        # Update uptime
        self.global_metrics["uptime_seconds"] = (
            datetime.utcnow() - 
            datetime.fromisoformat(self.global_metrics["start_time"])
        ).total_seconds()
        
        return self.global_metrics
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self.workflow_metrics = {}
        self.node_metrics = {}
        self.global_metrics = {
            "total_workflows_executed": 0,
            "total_nodes_executed": 0,
            "total_validation_failures": 0,
            "total_rule_violations": 0,
            "total_execution_time": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        logger.info("Metrics reset")
