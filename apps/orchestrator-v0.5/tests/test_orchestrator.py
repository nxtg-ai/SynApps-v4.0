"""
Tests for the Meta-Agent Orchestrator
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.meta_agent.orchestrator import MetaAgentOrchestrator
from models.agent_message import AppletMessage
from models.workflow import Workflow, WorkflowNode, WorkflowEdge
from core.validation.schema_validator import validate_message, ValidationResult
from core.governance.rule_engine import RuleEngine

@pytest.fixture
def orchestrator():
    """Create a MetaAgentOrchestrator instance for testing"""
    return MetaAgentOrchestrator()

@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing"""
    workflow = Workflow(
        id="wf-test-123",
        name="Test Workflow"
    )
    
    # Add nodes
    start_node = WorkflowNode(
        id="node-start",
        name="Start",
        type="start",
        position={"x": 100, "y": 100}
    )
    workflow.add_node(start_node)
    
    analyzer_node = WorkflowNode(
        id="node-analyzer",
        name="Analyzer",
        type="agent",
        applet_id="applet-analyzer",
        position={"x": 300, "y": 100},
        config={"output_format": "json"}
    )
    workflow.add_node(analyzer_node)
    
    end_node = WorkflowNode(
        id="node-end",
        name="End",
        type="end",
        position={"x": 500, "y": 100}
    )
    workflow.add_node(end_node)
    
    # Add edges
    workflow.add_edge(WorkflowEdge(
        id="edge-1",
        source="node-start",
        target="node-analyzer"
    ))
    
    workflow.add_edge(WorkflowEdge(
        id="edge-2",
        source="node-analyzer",
        target="node-end"
    ))
    
    return workflow

@pytest.mark.asyncio
async def test_find_start_node(orchestrator, sample_workflow):
    """Test finding the start node in a workflow"""
    start_node = orchestrator._find_start_node(sample_workflow)
    assert start_node is not None
    assert start_node.id == "node-start"
    assert start_node.type == "start"

@pytest.mark.asyncio
async def test_find_node_by_id(orchestrator, sample_workflow):
    """Test finding a node by ID in a workflow"""
    node = orchestrator._find_node_by_id(sample_workflow, "node-analyzer")
    assert node is not None
    assert node.id == "node-analyzer"
    assert node.type == "agent"
    assert node.applet_id == "applet-analyzer"

@pytest.mark.asyncio
async def test_find_next_nodes(orchestrator, sample_workflow):
    """Test finding next nodes in a workflow"""
    start_node = orchestrator._find_node_by_id(sample_workflow, "node-start")
    next_nodes = orchestrator._find_next_nodes(sample_workflow, start_node)
    assert len(next_nodes) == 1
    assert next_nodes[0].id == "node-analyzer"

@pytest.mark.asyncio
async def test_prepare_input_message(orchestrator):
    """Test preparing an input message with meta-prompt injection"""
    node = WorkflowNode(
        id="node-test",
        name="Test Node",
        type="analyzer",
        applet_id="applet-test"
    )
    
    message = await orchestrator._prepare_input_message("wf-test", node)
    assert isinstance(message, AppletMessage)
    assert "system_prompt" in message.context
    assert message.context["workflow_id"] == "wf-test"
    assert message.context["node_id"] == "node-test"

@pytest.mark.asyncio
async def test_execute_applet(orchestrator):
    """Test executing an applet"""
    node = WorkflowNode(
        id="node-test",
        name="Test Node",
        type="analyzer",
        applet_id="applet-test"
    )
    
    input_message = AppletMessage(
        content="Test input",
        context={"system_prompt": "You are a test agent"}
    )
    
    output_message = await orchestrator._execute_applet(node, input_message)
    assert isinstance(output_message, AppletMessage)
    assert output_message.content is not None
    assert "execution_time" in output_message.metadata

@pytest.mark.asyncio
async def test_handle_validation_failure(orchestrator):
    """Test handling validation failure"""
    node = WorkflowNode(
        id="node-test",
        name="Test Node",
        type="analyzer",
        applet_id="applet-test"
    )
    
    input_message = AppletMessage(
        content="Test input",
        context={"system_prompt": "You are a test agent"}
    )
    
    output_message = AppletMessage(
        content="Invalid output",
        context=input_message.context
    )
    
    validation_result = ValidationResult(
        is_valid=False,
        errors=[{"message": "Test validation error"}]
    )
    
    corrected_message = await orchestrator._handle_validation_failure(
        "wf-test", node, input_message, output_message, validation_result
    )
    
    assert isinstance(corrected_message, AppletMessage)
    assert corrected_message.has_error()
    assert "error_type" in corrected_message.metadata
    assert corrected_message.metadata["error_type"] == "validation_failure"

@pytest.mark.asyncio
async def test_execute_node(orchestrator, sample_workflow):
    """Test executing a node in a workflow"""
    # Mock the orchestrator's internal methods
    orchestrator._prepare_input_message = MagicMock(return_value=AppletMessage(
        content="Test input",
        context={"system_prompt": "You are a test agent"}
    ))
    
    orchestrator._execute_applet = MagicMock(return_value=AppletMessage(
        content="Test output",
        context={"system_prompt": "You are a test agent"},
        metadata={"execution_time": 0.1}
    ))
    
    # Mock the validation function
    with patch("core.meta_agent.orchestrator.validate_message") as mock_validate:
        mock_validate.return_value = ValidationResult(is_valid=True)
        
        # Set up the workflow in the orchestrator
        orchestrator.active_workflows = {"wf-test": sample_workflow}
        orchestrator.message_history = {"wf-test": []}
        
        # Mock the rule engine
        orchestrator.rule_engine.apply_rules = MagicMock(return_value={})
        
        # Execute the node
        result = await orchestrator._execute_node("wf-test", "node-analyzer")
        
        # Check the result
        assert result is not None
        assert result["node_id"] == "node-analyzer"
        assert "output" in result
        assert "validation" in result
        assert result["validation"]["is_valid"] is True

@pytest.mark.asyncio
async def test_execute_workflow(orchestrator, sample_workflow):
    """Test executing a workflow"""
    # Mock the orchestrator's methods
    orchestrator._load_workflow = MagicMock(return_value=sample_workflow)
    orchestrator._execute_node = MagicMock(return_value={"node_id": "node-start", "output": "Test output"})
    orchestrator._calculate_metrics = MagicMock(return_value={"execution_time": 0.5})
    
    # Execute the workflow
    result = await orchestrator.execute_workflow("wf-test")
    
    # Check the result
    assert result is not None
    assert result["workflow_id"] == "wf-test"
    assert result["status"] == "completed"
    assert "results" in result
    assert "metrics" in result
