"""
SynApps Orchestrator v0.5.0
Main entry point for the Meta-Agent Orchestrator
"""

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import json
from uuid import uuid4

from core.meta_agent.orchestrator import MetaAgentOrchestrator
from workflow.workflow_engine_extensions import EnhancedWorkflowEngine
from api.routes import router as api_router
from api.workflow_enhanced_routes import router as enhanced_workflow_router
from api.websocket import manager as ws_manager, handle_websocket_message, broadcast_workflow_update
from models.config import Settings
from db.session import init_db
from db.repository import WorkflowRepository, WorkflowRunRepository, MessageRepository
from monitoring.metrics import MetricsCollector
from monitoring.analytics import AnalyticsEngine
from communication.messaging import MessageBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("orchestrator")

# Load settings
settings = Settings()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Meta-Agent Orchestrator v0.5.0")
    
    # Initialize database
    logger.info("Initializing database")
    init_db()
    
    # Initialize message bus
    logger.info("Initializing message bus")
    message_bus = MessageBus()
    app.state.message_bus = message_bus
    
    # Initialize metrics collector
    logger.info("Initializing metrics collector")
    metrics_collector = MetricsCollector()
    app.state.metrics_collector = metrics_collector
    
    # Initialize analytics engine
    logger.info("Initializing analytics engine")
    analytics_engine = AnalyticsEngine(metrics_collector)
    app.state.analytics_engine = analytics_engine
    
    # Initialize orchestrator with dependencies
    logger.info("Initializing orchestrator")
    orchestrator = EnhancedWorkflowEngine(
        message_bus=message_bus,
        metrics_collector=metrics_collector
    )
    app.state.orchestrator = orchestrator
    
    # Register workflow update callback for WebSocket broadcasting
    orchestrator.register_workflow_update_callback(broadcast_workflow_update)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Meta-Agent Orchestrator")
    
    # Perform any cleanup tasks here
    await message_bus.shutdown()

# Create FastAPI app
app = FastAPI(
    title="SynApps Meta-Agent Orchestrator",
    description="Next-generation AI agent orchestration system",
    version="0.5.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Include enhanced workflow API routes
app.include_router(enhanced_workflow_router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid4())
    await ws_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle the message
            await handle_websocket_message(
                websocket=websocket,
                client_id=client_id,
                message=message,
                orchestrator=app.state.orchestrator
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(client_id)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "status": "ok",
        "version": "0.5.0",
        "name": "SynApps Meta-Agent Orchestrator"
    }
