# SynApps Orchestrator v0.5.0

This is the next-generation orchestrator for SynApps, featuring a complete rewrite with enhanced AI agent orchestration capabilities.

## Overview

The v0.5.0 orchestrator introduces a groundbreaking evolution in agent orchestration: the Orchestrator is now elevated to an **LLM-powered Meta-Agent**. Rather than simply routing messages, the Orchestrator becomes the execution brain of the system—rewriting prompts, enforcing structured outputs, and ensuring each agent behaves deterministically within complex workflows.

## Key Features

- **Meta-Agent Execution Core**: Intelligent orchestration of AI agents with dynamic prompt engineering
- **System Prompt Injection**: Automatic injection of system prompts to guide agent behavior
- **Structured Output Enforcement**: Schema validation to ensure consistent agent outputs
- **Deterministic Execution Governance**: Rule-based governance to ensure predictable execution
- **Enhanced Agent Communication**: Publish-subscribe messaging system for agent-to-agent communication
- **Monitoring and Analytics**: Comprehensive metrics collection and performance analysis

## Project Structure

```
/apps/orchestrator-v0.5/
├── core/                  # Core orchestrator components
│   ├── meta_agent/        # Meta-agent implementation
│   ├── validation/        # Schema validation
│   └── governance/        # Execution governance
├── communication/         # Agent communication protocols
├── monitoring/            # Monitoring and analytics
├── models/                # Data models and schemas
├── api/                   # API endpoints
├── tests/                 # Test suite
└── migrations/            # Database migrations
```

## Module Descriptions

### Core Modules

- **meta_agent**: The central orchestrator that coordinates agent execution, validation, and governance
- **validation**: Schema-based validation for agent outputs using JSON schemas
- **governance**: Rule engine for enforcing deterministic execution and content safety

### Communication Module

- **messaging**: Implements a publish-subscribe pattern for asynchronous agent-to-agent communication

### Monitoring Module

- **metrics**: Collects execution metrics for workflows and nodes
- **analytics**: Provides insights and visualizations for workflow performance

### Models

- **agent_message**: Defines the AppletMessage model for agent communication
- **workflow**: Defines workflow-related models (Workflow, WorkflowNode, WorkflowEdge)
- **config**: Configuration models for LLM settings, database connections, etc.

## API Endpoints

### Workflow Management

- `POST /api/workflows`: Create a new workflow
- `GET /api/workflows`: List all workflows
- `GET /api/workflows/{workflow_id}`: Get a specific workflow
- `PUT /api/workflows/{workflow_id}`: Update a workflow
- `DELETE /api/workflows/{workflow_id}`: Delete a workflow

### Workflow Execution

- `POST /api/workflows/{workflow_id}/execute`: Execute a workflow
- `GET /api/workflows/{workflow_id}/status`: Get workflow execution status

### Node Management

- `POST /api/workflows/{workflow_id}/nodes`: Add a node to a workflow
- `PUT /api/workflows/{workflow_id}/nodes/{node_id}`: Update a node
- `DELETE /api/workflows/{workflow_id}/nodes/{node_id}`: Delete a node

### Edge Management

- `POST /api/workflows/{workflow_id}/edges`: Add an edge to a workflow
- `DELETE /api/workflows/{workflow_id}/edges/{edge_id}`: Delete an edge

### Meta-Agent Operations

- `POST /api/meta-agent/validate`: Validate a message against an agent schema
- `POST /api/meta-agent/apply-rules`: Apply governance rules to a message

## Development

### Prerequisites

- Python 3.9+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0+

### Getting Started

1. Create a virtual environment
2. Install dependencies
3. Run the development server

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Integration with SynApps

To integrate the orchestrator with the main SynApps application:

1. Update the frontend to use the new orchestrator API endpoints
2. Modify the workflow editor to support the new workflow model
3. Update the database schema to match the new models

## Testing

Run the test suite with:

```bash
pytest
```

## Versioning

This is part of the v0.5.0 release of SynApps, representing a significant architectural change from v0.4.0.
