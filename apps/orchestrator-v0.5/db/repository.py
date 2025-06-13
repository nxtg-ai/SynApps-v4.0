"""
Repository layer for database operations in the Meta-Agent Orchestrator
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session

from models.workflow import Workflow, WorkflowNode, WorkflowEdge
from models.agent_message import AppletMessage
from db.models import (
    WorkflowModel, 
    WorkflowNodeModel, 
    WorkflowEdgeModel, 
    WorkflowRunModel,
    NodeRunModel,
    MessageModel,
    ValidationResultModel,
    RuleResultModel
)

logger = logging.getLogger("db.repository")

class WorkflowRepository:
    """
    Repository for workflow operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_workflow(self, workflow: Workflow) -> WorkflowModel:
        """
        Create a new workflow.
        
        Args:
            workflow: Workflow to create
            
        Returns:
            Created workflow model
        """
        db_workflow = WorkflowModel(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description
        )
        
        self.db.add(db_workflow)
        self.db.commit()
        self.db.refresh(db_workflow)
        
        # Add nodes and edges
        for node in workflow.nodes:
            self.add_node(workflow.id, node)
        
        for edge in workflow.edges:
            self.add_edge(workflow.id, edge)
        
        return db_workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowModel]:
        """
        Get a workflow by ID.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow model or None if not found
        """
        return self.db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    
    def get_all_workflows(self) -> List[WorkflowModel]:
        """
        Get all workflows.
        
        Returns:
            List of workflow models
        """
        return self.db.query(WorkflowModel).filter(WorkflowModel.is_active == True).all()
    
    def update_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Optional[WorkflowModel]:
        """
        Update a workflow.
        
        Args:
            workflow_id: ID of the workflow
            data: Data to update
            
        Returns:
            Updated workflow model or None if not found
        """
        db_workflow = self.get_workflow(workflow_id)
        if not db_workflow:
            return None
        
        for key, value in data.items():
            if hasattr(db_workflow, key):
                setattr(db_workflow, key, value)
        
        db_workflow.updated_at = datetime.utcnow()
        db_workflow.version += 1
        
        self.db.commit()
        self.db.refresh(db_workflow)
        
        return db_workflow
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            True if deleted, False if not found
        """
        db_workflow = self.get_workflow(workflow_id)
        if not db_workflow:
            return False
        
        # Soft delete
        db_workflow.is_active = False
        db_workflow.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def add_node(self, workflow_id: str, node: WorkflowNode) -> WorkflowNodeModel:
        """
        Add a node to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            node: Node to add
            
        Returns:
            Created node model
        """
        db_node = WorkflowNodeModel(
            id=node.id,
            workflow_id=workflow_id,
            name=node.name,
            type=node.type,
            applet_id=node.applet_id,
            position_x=node.position.get("x", 0) if node.position else 0,
            position_y=node.position.get("y", 0) if node.position else 0,
            config=node.config
        )
        
        self.db.add(db_node)
        self.db.commit()
        self.db.refresh(db_node)
        
        return db_node
    
    def update_node(self, workflow_id: str, node_id: str, data: Dict[str, Any]) -> Optional[WorkflowNodeModel]:
        """
        Update a node.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            data: Data to update
            
        Returns:
            Updated node model or None if not found
        """
        db_node = self.db.query(WorkflowNodeModel).filter(
            WorkflowNodeModel.workflow_id == workflow_id,
            WorkflowNodeModel.id == node_id
        ).first()
        
        if not db_node:
            return None
        
        for key, value in data.items():
            if key == "position" and isinstance(value, dict):
                db_node.position_x = value.get("x", db_node.position_x)
                db_node.position_y = value.get("y", db_node.position_y)
            elif hasattr(db_node, key):
                setattr(db_node, key, value)
        
        self.db.commit()
        self.db.refresh(db_node)
        
        return db_node
    
    def delete_node(self, workflow_id: str, node_id: str) -> bool:
        """
        Delete a node.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the node
            
        Returns:
            True if deleted, False if not found
        """
        db_node = self.db.query(WorkflowNodeModel).filter(
            WorkflowNodeModel.workflow_id == workflow_id,
            WorkflowNodeModel.id == node_id
        ).first()
        
        if not db_node:
            return False
        
        self.db.delete(db_node)
        self.db.commit()
        
        return True
    
    def add_edge(self, workflow_id: str, edge: WorkflowEdge) -> WorkflowEdgeModel:
        """
        Add an edge to a workflow.
        
        Args:
            workflow_id: ID of the workflow
            edge: Edge to add
            
        Returns:
            Created edge model
        """
        db_edge = WorkflowEdgeModel(
            id=edge.id,
            workflow_id=workflow_id,
            source_id=edge.source,
            target_id=edge.target,
            condition=edge.condition
        )
        
        self.db.add(db_edge)
        self.db.commit()
        self.db.refresh(db_edge)
        
        return db_edge
    
    def delete_edge(self, workflow_id: str, edge_id: str) -> bool:
        """
        Delete an edge.
        
        Args:
            workflow_id: ID of the workflow
            edge_id: ID of the edge
            
        Returns:
            True if deleted, False if not found
        """
        db_edge = self.db.query(WorkflowEdgeModel).filter(
            WorkflowEdgeModel.workflow_id == workflow_id,
            WorkflowEdgeModel.id == edge_id
        ).first()
        
        if not db_edge:
            return False
        
        self.db.delete(db_edge)
        self.db.commit()
        
        return True
    
    def to_domain_workflow(self, db_workflow: WorkflowModel) -> Workflow:
        """
        Convert a database workflow model to a domain workflow.
        
        Args:
            db_workflow: Database workflow model
            
        Returns:
            Domain workflow
        """
        nodes = []
        for db_node in db_workflow.nodes:
            nodes.append(WorkflowNode(
                id=db_node.id,
                name=db_node.name,
                type=db_node.type,
                applet_id=db_node.applet_id,
                position={"x": db_node.position_x, "y": db_node.position_y},
                config=db_node.config
            ))
        
        edges = []
        for db_edge in db_workflow.edges:
            edges.append(WorkflowEdge(
                id=db_edge.id,
                source=db_edge.source_id,
                target=db_edge.target_id,
                condition=db_edge.condition
            ))
        
        return Workflow(
            id=db_workflow.id,
            name=db_workflow.name,
            description=db_workflow.description,
            nodes=nodes,
            edges=edges
        )

class WorkflowRunRepository:
    """
    Repository for workflow run operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_run(self, workflow_id: str) -> WorkflowRunModel:
        """
        Create a new workflow run.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Created workflow run model
        """
        db_run = WorkflowRunModel(
            workflow_id=workflow_id,
            status="running",
            started_at=datetime.utcnow()
        )
        
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        
        return db_run
    
    def get_run(self, run_id: str) -> Optional[WorkflowRunModel]:
        """
        Get a workflow run by ID.
        
        Args:
            run_id: ID of the run
            
        Returns:
            Workflow run model or None if not found
        """
        return self.db.query(WorkflowRunModel).filter(WorkflowRunModel.id == run_id).first()
    
    def get_runs_for_workflow(self, workflow_id: str) -> List[WorkflowRunModel]:
        """
        Get all runs for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of workflow run models
        """
        return self.db.query(WorkflowRunModel).filter(WorkflowRunModel.workflow_id == workflow_id).all()
    
    def update_run_status(self, run_id: str, status: str, error: Optional[str] = None) -> Optional[WorkflowRunModel]:
        """
        Update the status of a workflow run.
        
        Args:
            run_id: ID of the run
            status: New status
            error: Error message if any
            
        Returns:
            Updated workflow run model or None if not found
        """
        db_run = self.get_run(run_id)
        if not db_run:
            return None
        
        db_run.status = status
        
        if status in ["completed", "failed"]:
            db_run.completed_at = datetime.utcnow()
        
        if error:
            db_run.error = error
        
        self.db.commit()
        self.db.refresh(db_run)
        
        return db_run
    
    def update_run_metrics(self, run_id: str, metrics: Dict[str, Any]) -> Optional[WorkflowRunModel]:
        """
        Update the metrics of a workflow run.
        
        Args:
            run_id: ID of the run
            metrics: Metrics to update
            
        Returns:
            Updated workflow run model or None if not found
        """
        db_run = self.get_run(run_id)
        if not db_run:
            return None
        
        db_run.metrics = metrics
        
        self.db.commit()
        self.db.refresh(db_run)
        
        return db_run
    
    def update_completed_applets(self, run_id: str, completed_applets: List[str]) -> Optional[WorkflowRunModel]:
        """
        Update the list of completed applets for a workflow run.
        
        Args:
            run_id: ID of the run
            completed_applets: List of completed applet IDs
            
        Returns:
            Updated workflow run model or None if not found
        """
        db_run = self.get_run(run_id)
        if not db_run:
            return None
        
        db_run.completed_applets = completed_applets
        
        self.db.commit()
        self.db.refresh(db_run)
        
        return db_run
    
    def create_node_run(self, workflow_run_id: str, node_id: str) -> NodeRunModel:
        """
        Create a new node run.
        
        Args:
            workflow_run_id: ID of the workflow run
            node_id: ID of the node
            
        Returns:
            Created node run model
        """
        db_node_run = NodeRunModel(
            workflow_run_id=workflow_run_id,
            node_id=node_id,
            status="running",
            started_at=datetime.utcnow()
        )
        
        self.db.add(db_node_run)
        self.db.commit()
        self.db.refresh(db_node_run)
        
        return db_node_run
    
    def update_node_run_status(
        self, 
        node_run_id: str, 
        status: str, 
        error: Optional[str] = None
    ) -> Optional[NodeRunModel]:
        """
        Update the status of a node run.
        
        Args:
            node_run_id: ID of the node run
            status: New status
            error: Error message if any
            
        Returns:
            Updated node run model or None if not found
        """
        db_node_run = self.db.query(NodeRunModel).filter(NodeRunModel.id == node_run_id).first()
        if not db_node_run:
            return None
        
        db_node_run.status = status
        
        if status in ["completed", "failed"]:
            db_node_run.completed_at = datetime.utcnow()
        
        if error:
            db_node_run.error = error
        
        self.db.commit()
        self.db.refresh(db_node_run)
        
        return db_node_run
    
    def update_node_run_metrics(self, node_run_id: str, metrics: Dict[str, Any]) -> Optional[NodeRunModel]:
        """
        Update the metrics of a node run.
        
        Args:
            node_run_id: ID of the node run
            metrics: Metrics to update
            
        Returns:
            Updated node run model or None if not found
        """
        db_node_run = self.db.query(NodeRunModel).filter(NodeRunModel.id == node_run_id).first()
        if not db_node_run:
            return None
        
        db_node_run.metrics = metrics
        
        self.db.commit()
        self.db.refresh(db_node_run)
        
        return db_node_run

class MessageRepository:
    """
    Repository for message operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_message(
        self, 
        node_run_id: str, 
        direction: str, 
        message: AppletMessage
    ) -> MessageModel:
        """
        Create a new message.
        
        Args:
            node_run_id: ID of the node run
            direction: Direction of the message ("input" or "output")
            message: Message to create
            
        Returns:
            Created message model
        """
        db_message = MessageModel(
            node_run_id=node_run_id,
            direction=direction,
            content=message.content,
            context=message.context,
            metadata=message.metadata
        )
        
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        
        return db_message
    
    def get_messages_for_node_run(self, node_run_id: str) -> List[MessageModel]:
        """
        Get all messages for a node run.
        
        Args:
            node_run_id: ID of the node run
            
        Returns:
            List of message models
        """
        return self.db.query(MessageModel).filter(MessageModel.node_run_id == node_run_id).all()
    
    def create_validation_result(
        self, 
        message_id: str, 
        is_valid: bool, 
        errors: List[Dict[str, Any]]
    ) -> ValidationResultModel:
        """
        Create a new validation result.
        
        Args:
            message_id: ID of the message
            is_valid: Whether the message is valid
            errors: Validation errors if any
            
        Returns:
            Created validation result model
        """
        db_validation = ValidationResultModel(
            message_id=message_id,
            is_valid=is_valid,
            errors=errors
        )
        
        self.db.add(db_validation)
        self.db.commit()
        self.db.refresh(db_validation)
        
        return db_validation
    
    def create_rule_result(
        self, 
        message_id: str, 
        rule_id: str, 
        passed: bool, 
        message: str, 
        metadata: Dict[str, Any]
    ) -> RuleResultModel:
        """
        Create a new rule result.
        
        Args:
            message_id: ID of the message
            rule_id: ID of the rule
            passed: Whether the rule passed
            message: Rule result message
            metadata: Additional metadata
            
        Returns:
            Created rule result model
        """
        db_rule_result = RuleResultModel(
            message_id=message_id,
            rule_id=rule_id,
            passed=passed,
            message=message,
            metadata=metadata
        )
        
        self.db.add(db_rule_result)
        self.db.commit()
        self.db.refresh(db_rule_result)
        
        return db_rule_result
