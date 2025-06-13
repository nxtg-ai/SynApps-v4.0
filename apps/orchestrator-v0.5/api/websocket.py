"""
WebSocket support for the Meta-Agent Orchestrator
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any
import logging
import json
import asyncio
from uuid import UUID

from core.meta_agent.orchestrator import MetaAgentOrchestrator
from api.routes import get_orchestrator

logger = logging.getLogger("api.websocket")

# Store active connections
class ConnectionManager:
    def __init__(self):
        # client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # workflow_id -> List[client_id]
        self.workflow_subscriptions: Dict[str, List[str]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            self.active_connections.pop(client_id)
            logger.info(f"Client {client_id} disconnected")
            
            # Remove client from all subscriptions
            for workflow_id in self.workflow_subscriptions:
                if client_id in self.workflow_subscriptions[workflow_id]:
                    self.workflow_subscriptions[workflow_id].remove(client_id)
    
    def subscribe_to_workflow(self, client_id: str, workflow_id: str):
        if workflow_id not in self.workflow_subscriptions:
            self.workflow_subscriptions[workflow_id] = []
        
        if client_id not in self.workflow_subscriptions[workflow_id]:
            self.workflow_subscriptions[workflow_id].append(client_id)
            logger.info(f"Client {client_id} subscribed to workflow {workflow_id}")
    
    def unsubscribe_from_workflow(self, client_id: str, workflow_id: str):
        if workflow_id in self.workflow_subscriptions and client_id in self.workflow_subscriptions[workflow_id]:
            self.workflow_subscriptions[workflow_id].remove(client_id)
            logger.info(f"Client {client_id} unsubscribed from workflow {workflow_id}")
    
    async def broadcast_to_workflow(self, workflow_id: str, message: Dict[str, Any]):
        """Send message to all clients subscribed to a workflow"""
        if workflow_id not in self.workflow_subscriptions:
            return
            
        disconnected_clients = []
        for client_id in self.workflow_subscriptions[workflow_id]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
            else:
                disconnected_clients.append(client_id)
                
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending personal message to client {client_id}: {e}")
                self.disconnect(client_id)


# Create a connection manager instance
manager = ConnectionManager()


async def handle_websocket_message(
    websocket: WebSocket, 
    client_id: str,
    message: Dict[str, Any],
    orchestrator: MetaAgentOrchestrator
):
    """Handle incoming WebSocket messages"""
    try:
        message_type = message.get("type")
        
        if message_type == "subscribe":
            workflow_id = message.get("workflow_id")
            if workflow_id:
                manager.subscribe_to_workflow(client_id, workflow_id)
                await manager.send_personal_message(
                    client_id, 
                    {
                        "type": "subscription_confirmed",
                        "workflow_id": workflow_id
                    }
                )
                
        elif message_type == "unsubscribe":
            workflow_id = message.get("workflow_id")
            if workflow_id:
                manager.unsubscribe_from_workflow(client_id, workflow_id)
                
        elif message_type == "ping":
            await manager.send_personal_message(
                client_id,
                {
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                }
            )
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await manager.send_personal_message(
                client_id,
                {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                }
            )
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message(
            client_id,
            {
                "type": "error",
                "error": str(e)
            }
        )


# Register this function to broadcast workflow execution updates
async def broadcast_workflow_update(workflow_id: str, status: Dict[str, Any]):
    """Broadcast workflow execution updates to subscribed clients"""
    await manager.broadcast_to_workflow(
        workflow_id,
        {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "status": status
        }
    )
