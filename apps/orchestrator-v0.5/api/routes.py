"""
API Routes for the Meta-Agent Orchestrator
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, Request
from typing import Dict, Any, List, Optional
import logging
from uuid import UUID

from models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowRunStatus
from core.meta_agent.orchestrator import MetaAgentOrchestrator

logger = logging.getLogger("api.routes")

# Create router
router = APIRouter()

# Helper function to get orchestrator from app state
async def get_orchestrator(request: Request) -> MetaAgentOrchestrator:
    """Get the orchestrator instance from the app state"""
    return request.app.state.orchestrator

# Workflow endpoints
@router.post("/workflows", response_model=Workflow)
async def create_workflow(
    workflow: Workflow,
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Workflow:
    """
    Create a new workflow.
    """
    logger.info(f"Creating new workflow: {workflow.name}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Create workflow in database
    db_workflow = repository.create_workflow(workflow)
    
    # Convert to domain model and return
    return repository.to_domain_workflow(db_workflow)

@router.get("/workflows", response_model=List[Workflow])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> List[Workflow]:
    """
    List all workflows.
    """
    logger.info("Listing workflows")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Get all workflows from database
    db_workflows = repository.get_all_workflows()
    
    # Convert to domain models and return
    workflows = [repository.to_domain_workflow(db_workflow) for db_workflow in db_workflows]
    
    # Apply pagination
    return workflows[skip:skip+limit]

@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: str = Path(..., description="ID of the workflow to get"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Workflow:
    """
    Get a workflow by ID.
    """
    logger.info(f"Getting workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Get workflow from database
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Convert to domain model and return
    return repository.to_domain_workflow(db_workflow)

@router.put("/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(
    workflow: Workflow,
    workflow_id: str = Path(..., description="ID of the workflow to update"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Workflow:
    """
    Update a workflow.
    """
    logger.info(f"Updating workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Update workflow data
    data = workflow.dict(exclude_unset=True)
    data["id"] = workflow_id  # Ensure ID doesn't change
    
    # Update workflow in database
    db_workflow = repository.update_workflow(workflow_id, data)
    
    # Handle nodes and edges separately
    # Delete existing nodes and edges
    for node in db_workflow.nodes:
        repository.delete_node(workflow_id, node.id)
    
    for edge in db_workflow.edges:
        repository.delete_edge(workflow_id, edge.id)
    
    # Add new nodes and edges
    for node in workflow.nodes:
        repository.add_node(workflow_id, node)
    
    for edge in workflow.edges:
        repository.add_edge(workflow_id, edge)
    
    # Get updated workflow
    db_workflow = repository.get_workflow(workflow_id)
    
    # Convert to domain model and return
    return repository.to_domain_workflow(db_workflow)

@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str = Path(..., description="ID of the workflow to delete"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Delete a workflow.
    """
    logger.info(f"Deleting workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Delete workflow from database
    success = repository.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    return {"message": f"Workflow {workflow_id} deleted"}

# Workflow execution endpoints
@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    background_tasks: BackgroundTasks,
    workflow_id: str = Path(..., description="ID of the workflow to execute"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Execute a workflow.
    """
    logger.info(f"Executing workflow: {workflow_id}")
    
    # Start execution in the background
    background_tasks.add_task(orchestrator.execute_workflow, workflow_id)
    
    return {
        "message": f"Workflow {workflow_id} execution started",
        "workflow_id": workflow_id,
        "status": "pending"
    }

@router.get("/workflows/{workflow_id}/status", response_model=WorkflowRunStatus)
async def get_workflow_status(
    workflow_id: str = Path(..., description="ID of the workflow to get status for"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> WorkflowRunStatus:
    """
    Get the status of a workflow execution.
    """
    logger.info(f"Getting status for workflow: {workflow_id}")
    # In a real implementation, this would query a database
    # For now, we'll raise a 404
    raise HTTPException(status_code=404, detail=f"Workflow run for {workflow_id} not found")

# Node endpoints
@router.post("/workflows/{workflow_id}/nodes", response_model=WorkflowNode)
async def add_node(
    node: WorkflowNode,
    workflow_id: str = Path(..., description="ID of the workflow to add a node to"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> WorkflowNode:
    """
    Add a node to a workflow.
    """
    logger.info(f"Adding node to workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Add node to workflow
    db_node = repository.add_node(workflow_id, node)
    
    # Return node with ID
    return node

@router.put("/workflows/{workflow_id}/nodes/{node_id}", response_model=WorkflowNode)
async def update_node(
    node: WorkflowNode,
    workflow_id: str = Path(..., description="ID of the workflow"),
    node_id: str = Path(..., description="ID of the node to update"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> WorkflowNode:
    """
    Update a node in a workflow.
    """
    logger.info(f"Updating node {node_id} in workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Ensure node ID matches path parameter
    node.id = node_id
    
    # Update node data
    data = node.dict(exclude_unset=True)
    
    # Update node in database
    db_node = repository.update_node(workflow_id, node_id, data)
    if not db_node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in workflow {workflow_id}")
    
    # Return updated node
    return node

@router.delete("/workflows/{workflow_id}/nodes/{node_id}")
async def delete_node(
    workflow_id: str = Path(..., description="ID of the workflow"),
    node_id: str = Path(..., description="ID of the node to delete"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Delete a node from a workflow.
    """
    logger.info(f"Deleting node {node_id} from workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Delete node from workflow
    success = repository.delete_node(workflow_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in workflow {workflow_id}")
    
    return {"message": f"Node {node_id} deleted from workflow {workflow_id}"}

# Edge endpoints
@router.post("/workflows/{workflow_id}/edges", response_model=WorkflowEdge)
async def add_edge(
    edge: WorkflowEdge,
    workflow_id: str = Path(..., description="ID of the workflow to add an edge to"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> WorkflowEdge:
    """
    Add an edge to a workflow.
    """
    logger.info(f"Adding edge to workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Add edge to workflow
    db_edge = repository.add_edge(workflow_id, edge)
    
    # Return edge with ID
    return edge

@router.delete("/workflows/{workflow_id}/edges/{edge_id}")
async def delete_edge(
    workflow_id: str = Path(..., description="ID of the workflow"),
    edge_id: str = Path(..., description="ID of the edge to delete"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Delete an edge from a workflow.
    """
    logger.info(f"Deleting edge {edge_id} from workflow: {workflow_id}")
    
    from db.repository import WorkflowRepository
    from db.session import get_db
    
    # Get database session
    db = next(get_db())
    
    # Create repository
    repository = WorkflowRepository(db)
    
    # Check if workflow exists
    db_workflow = repository.get_workflow(workflow_id)
    if not db_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # Delete edge from workflow
    success = repository.delete_edge(workflow_id, edge_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found in workflow {workflow_id}")
    
    return {"message": f"Edge {edge_id} deleted from workflow {workflow_id}"}

# Meta-Agent specific endpoints
@router.post("/meta-agent/validate", response_model=Dict[str, Any])
async def validate_message(
    message: Dict[str, Any],
    agent_type: str = Query(..., description="Type of agent to validate against"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Validate a message against an agent schema.
    """
    logger.info(f"Validating message for agent type: {agent_type}")
    
    from models.agent_message import AppletMessage
    from core.validation.schema_validator import validate_message as validate
    
    # Create AppletMessage from request body
    applet_message = AppletMessage(
        content=message.get("content", ""),
        context={"agent_type": agent_type, **message.get("context", {})},
        metadata=message.get("metadata", {})
    )
    
    # Validate message
    result = validate(applet_message)
    
    return result.to_dict()

@router.post("/meta-agent/apply-rules", response_model=Dict[str, Any])
async def apply_rules(
    message: Dict[str, Any],
    workflow_id: str = Query(..., description="ID of the workflow"),
    node_id: str = Query(..., description="ID of the node"),
    rule_ids: List[str] = Query(None, description="IDs of rules to apply"),
    orchestrator: MetaAgentOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Apply governance rules to a message.
    """
    logger.info(f"Applying rules to message for node {node_id} in workflow {workflow_id}")
    
    from models.agent_message import AppletMessage
    from models.workflow import WorkflowNode
    
    # Create AppletMessage from request body
    applet_message = AppletMessage(
        content=message.get("content", ""),
        context=message.get("context", {}),
        metadata=message.get("metadata", {})
    )
    
    # Create dummy node
    node = WorkflowNode(
        id=node_id,
        name="Dummy Node",
        type="agent",
        config=message.get("node_config", {})
    )
    
    # Apply rules
    results = await orchestrator.rule_engine.apply_rules(
        workflow_id=workflow_id,
        node=node,
        message=applet_message,
        rule_ids=rule_ids
    )
    
    # Convert results to dict
    return {
        rule_id: result.dict() for rule_id, result in results.items()
    }
