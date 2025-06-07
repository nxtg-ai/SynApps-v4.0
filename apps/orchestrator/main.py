"""
SynApps Orchestrator - Core Module

This is the lightweight microkernel that routes messages between applets in a
defined sequence. The orchestrator's job is purely to pass messages and data
between applets.
"""
import asyncio
import importlib
import json
import logging
import os
import sys
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Type

# Add the parent directory to the Python path so we can import the apps package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import database modules
from contextlib import asynccontextmanager
from db import init_db, close_db_connections
from repositories import FlowRepository, WorkflowRunRepository
from models import FlowModel, FlowNodeModel, FlowEdgeModel, WorkflowRunStatusModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("orchestrator")

# Define lifespan context manager for database initialization and cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and cleanup."""
    # Startup: Initialize the database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialization complete")
    
    yield
    
    # Shutdown: Close database connections
    logger.info("Closing database connections...")
    await close_db_connections()
    logger.info("Database connections closed")

# Initialize FastAPI app with lifespan
app = FastAPI(title="SynApps Orchestrator", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class AppletStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class FlowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, int]
    data: Dict[str, Any] = {}

class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False

class Flow(BaseModel):
    id: str
    name: str
    nodes: List[FlowNode]
    edges: List[FlowEdge]

class AppletMessage(BaseModel):
    content: Any
    context: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class WorkflowRunStatus(BaseModel):
    run_id: str
    flow_id: str
    status: str
    current_applet: Optional[str] = None
    progress: int = 0
    total_steps: int = 0
    start_time: float = 0
    end_time: Optional[float] = None
    results: Dict[str, Any] = {}
    error: Optional[str] = None

# Global state - connection management
connected_clients: List[WebSocket] = []
applet_registry: Dict[str, Type['BaseApplet']] = {}

# Database initialization is now handled by the lifespan context manager

# WebSocket connection manager
async def broadcast_status(status: Dict[str, Any]):
    """Broadcast workflow status to all connected clients."""
    if not connected_clients:
        logger.warning("No connected clients to broadcast to")
        return
    
    message = {
        "type": "workflow.status",
        "data": status
    }
    
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            # We'll handle disconnected clients in the WebSocket endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")
    
    try:
        while True:
            # Just keep the connection open, we'll push updates as they happen
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining clients: {len(connected_clients)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected due to error. Remaining clients: {len(connected_clients)}")

# Base Applet class
class BaseApplet:
    """Base class that all applets must implement."""
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return applet metadata."""
        return {
            "name": cls.__name__,
            "description": cls.__doc__ or "No description provided",
            "version": getattr(cls, "VERSION", "0.1.0"),
            "capabilities": getattr(cls, "CAPABILITIES", []),
        }
    
    async def on_message(self, message: AppletMessage) -> AppletMessage:
        """Process an incoming message and return a response."""
        raise NotImplementedError("Applets must implement on_message")

def model_to_dict(model):
    """Convert a Pydantic model to a dictionary, handling both v1 and v2 Pydantic."""
    if isinstance(model, dict):
        return model
    # Handle both Pydantic v1 (dict) and v2 (model_dump)
    return model.model_dump() if hasattr(model, 'model_dump') else model.dict()

# Orchestrator Core
class Orchestrator:
    """Core orchestration engine that executes applet flows."""
    
    @staticmethod
    async def load_applet(applet_type: str) -> BaseApplet:
        """Dynamically load an applet by type."""
        if applet_type in applet_registry:
            return applet_registry[applet_type]()
        
        # Attempt to load from the applets directory
        try:
            # Convert type to module path (e.g., 'writer' -> 'apps.applets.writer.applet')
            module_path = f"apps.applets.{applet_type}.applet"
            module = importlib.import_module(module_path)
            applet_class = getattr(module, f"{applet_type.capitalize()}Applet")
            
            # Register applet
            applet_registry[applet_type] = applet_class
            
            return applet_class()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load applet '{applet_type}': {e}")
            raise ValueError(f"Applet type '{applet_type}' not found")
    @staticmethod
    def create_run_id() -> str:
        """Generate a unique run ID."""
        return str(uuid.uuid4())
        
    @staticmethod
    async def execute_flow(flow: Flow, input_data: Dict[str, Any]) -> str:
        """Execute a flow and return the run ID."""
        run_id = Orchestrator.create_run_id()
        
        # Create workflow run status
        status = WorkflowRunStatus(
            run_id=run_id,
            flow_id=flow["id"],
            status="running",
            start_time=time.time(),
            total_steps=len(flow["nodes"])
        )
        
        # Convert status to dictionary
        status_dict = model_to_dict(status)
        
        # Initialize repository and save initial status
        workflow_run_repo = WorkflowRunRepository()
        logger.info(f"Starting workflow execution with run ID: {run_id}")
        await workflow_run_repo.save(status_dict)
        
        # Broadcast initial status
        await broadcast_status(status_dict)
        
        # Start execution in background task
        asyncio.create_task(Orchestrator._execute_flow_async(run_id, flow, input_data, workflow_run_repo))
        
        return run_id
    @staticmethod
    async def _execute_flow_async(run_id: str, flow: dict, input_data: Dict[str, Any], workflow_run_repo: WorkflowRunRepository):
        status = await workflow_run_repo.get_by_run_id(run_id)
        
        # Create a mapping of node IDs to node data
        nodes_by_id = {node["id"]: node for node in flow["nodes"]}
        
        # Create an adjacency list for the graph
        graph = {}
        for edge in flow["edges"]:
            if edge["source"] not in graph:
                graph[edge["source"]] = []
            graph[edge["source"]].append(edge["target"])
        
        # Find start nodes (nodes with no incoming edges)
        target_nodes = set(edge["target"] for edge in flow["edges"])
        start_nodes = [node["id"] for node in flow["nodes"] if node["id"] not in target_nodes]
        
        if not start_nodes:
            status["status"] = "error"
            status["error"] = "No start node found in flow"
            status["end_time"] = time.time()
            await workflow_run_repo.save(status)
            await broadcast_status(status)
            return
        
        # Initialize context with input data
        context = {
            "input": input_data,
            "results": {},
            "run_id": run_id
        }
        
        # Process the graph starting from start nodes
        current_nodes = start_nodes
        visited = set()
        
        try:
            while current_nodes:
                next_nodes = []
                
                for node_id in current_nodes:
                    if node_id in visited:
                        continue
                    
                    visited.add(node_id)
                    node = nodes_by_id[node_id]
                    
                    # Update status
                    status["current_applet"] = node["type"]
                    status["progress"] += 1
                    await workflow_run_repo.save(status)
                    await broadcast_status(status)
                    
                    # Skip if not an applet node
                    if node["type"].lower() in ["start", "end"]:
                        if node_id in graph:
                            next_nodes.extend(graph[node_id])
                        continue
                    
                    # Load and execute applet
                    try:
                        applet = await Orchestrator.load_applet(node["type"].lower())
                        
                        # Create message
                        message = AppletMessage(
                            content=input_data,
                            context=context,
                            metadata={"node_id": node_id, "run_id": run_id}
                        )
                        
                        # Process message
                        response = await applet.on_message(message)
                        
                        # Store result in context
                        context["results"][node_id] = {
                            "type": node["type"],
                            "output": response.content
                        }
                        
                        # Update context with any changes from applet
                        context.update(response.context)
                        
                        # Add next nodes
                        if node_id in graph:
                            next_nodes.extend(graph[node_id])
                            
                            # Animate edges
                            for edge in flow["edges"]:
                                if edge["source"] == node_id:
                                    edge["animated"] = True
                    
                    except Exception as e:
                        logger.error(f"Error executing applet '{node['type']}': {e}")
                        status["status"] = "error"
                        status["error"] = f"Error in applet '{node['type']}': {str(e)}"
                        status["end_time"] = time.time()
                        await workflow_run_repo.save(status)
                        await broadcast_status(status)
                        return
                
                current_nodes = next_nodes
            
            # Workflow completed successfully
            status["status"] = "success"
            status["end_time"] = time.time()
            status["results"] = context["results"]
            await workflow_run_repo.save(status)
            await broadcast_status(status)
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            status["status"] = "error"
            status["error"] = f"Workflow execution error: {str(e)}"
            status["end_time"] = time.time()
            await workflow_run_repo.save(status)
            await broadcast_status(status)

# API Routes
@app.get("/")
async def read_root():
    return {"message": "SynApps Orchestrator API", "version": "0.1.0"}

@app.get("/applets")
async def list_applets():
    """List all registered applets with their metadata."""
    result = []
    
    # First include registered applets
    for applet_type, applet_class in applet_registry.items():
        result.append({
            "type": applet_type,
            **applet_class.get_metadata()
        })
    
    # Then try to discover applets from the applets directory
    applets_dir = os.path.join(os.path.dirname(__file__), "..", "applets")
    if os.path.exists(applets_dir):
        for applet_dir in os.listdir(applets_dir):
            if applet_dir not in [a["type"] for a in result]:
                try:
                    applet = await Orchestrator.load_applet(applet_dir)
                    result.append({
                        "type": applet_dir,
                        **applet.get_metadata()
                    })
                except Exception as e:
                    logger.warning(f"Failed to load applet '{applet_dir}': {e}")
    
    return result

@app.post("/flows")
async def create_flow(flow: Flow):
    """Create or update a flow."""
    await FlowRepository.save(model_to_dict(flow))
    return {"message": "Flow created", "id": flow.id}

@app.get("/flows")
async def list_flows():
    """List all flows."""
    return await FlowRepository.get_all()

@app.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    """Get a flow by ID."""
    flow = await FlowRepository.get_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow

@app.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str):
    """Delete a flow."""
    flow = await FlowRepository.get_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await FlowRepository.delete(flow_id)
    return {"message": "Flow deleted"}

@app.post("/flows/{flow_id}/run")
async def run_flow(flow_id: str, input_data: Dict[str, Any]):
    """Run a flow with the given input data."""
    flow = await FlowRepository.get_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    run_id = await Orchestrator.execute_flow(flow, input_data)
    return {"run_id": run_id}

@app.get("/runs")
async def list_runs():
    """List all workflow runs."""
    return await WorkflowRunRepository.get_all()

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a workflow run by ID."""
    run = await WorkflowRunRepository.get_by_run_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.post("/ai/suggest")
async def ai_suggest(data: Dict[str, str]):
    """Generate code suggestions using AI."""
    # This will be implemented with OpenAI or similar
    # For MVP, we'll mock this
    code = data.get("code", "")
    hint = data.get("hint", "")
    
    # In a real implementation, we would call OpenAI Codex here
    # For now, just echo back with a comment
    suggested_code = f"{code}\n\n# AI Suggestion based on hint: {hint}\n# TODO: Implement AI code suggestions"
    
    return {
        "original": code,
        "suggestion": suggested_code,
        "diff": "# TODO: Generate actual diff"
    }

# For direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
