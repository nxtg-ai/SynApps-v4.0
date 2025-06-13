# AI Agent Orchestration

This document provides an architectural overview of the AI agent orchestration system in SynApps v4.0, focusing on the enhanced workflow capabilities.

## Table of Contents

- [Overview](#overview)
- [Core Components](#core-components)
- [Workflow Engine](#workflow-engine)
- [Enhanced Workflow Features](#enhanced-workflow-features)
  - [Conditional Branching](#conditional-branching)
  - [Nested Workflows](#nested-workflows)
- [API Integration](#api-integration)
- [Implementation Details](#implementation-details)

## Overview

The SynApps Meta-Agent Orchestrator is responsible for coordinating the execution of AI agent workflows. It routes messages between agents, manages workflow state, and ensures proper execution of workflow steps.

With the v0.5.0 release, the orchestrator has been enhanced with conditional branching and nested workflow capabilities, enabling more complex and dynamic workflow patterns.

## Core Components

The orchestration system consists of several key components:

1. **MetaAgentOrchestrator**: The core orchestration engine that manages workflow execution
2. **EnhancedWorkflowEngine**: Extends the base orchestrator with advanced workflow capabilities
3. **ConditionalBranchingEngine**: Handles dynamic routing based on message conditions
4. **NestedWorkflowEngine**: Manages hierarchical workflow execution
5. **WorkflowDefinition**: Represents a workflow with steps and transitions
6. **WorkflowStep**: Represents an individual step in a workflow
7. **WorkflowExecutionContext**: Maintains the state of a workflow execution

## Workflow Engine

The workflow engine is responsible for:

1. **Workflow Registration**: Registering workflow definitions with steps and transitions
2. **Workflow Execution**: Executing workflows step by step
3. **Message Routing**: Routing messages between workflow steps
4. **State Management**: Maintaining workflow execution state

The base `MetaAgentOrchestrator` provides these core capabilities, while the `EnhancedWorkflowEngine` extends them with conditional branching and nested workflow support.

## Enhanced Workflow Features

### Conditional Branching

Conditional branching enables dynamic routing of messages within a workflow based on conditions evaluated against the message content, metadata, or context.

#### Key Components

- **ConditionalBranchingEngine**: Core engine for evaluating conditions and determining next steps
- **ConditionalBranch**: Represents a branch with conditions and target steps
- **BranchCondition**: Represents a condition to be evaluated
- **ConditionType**: Enum defining different types of conditions (content match, metadata check, etc.)

#### Condition Types

1. **Content Match**: Evaluates patterns against message content
   - Supports exact matches or regex patterns
   - Can be case-sensitive or case-insensitive

2. **Metadata Check**: Evaluates conditions against message metadata
   - Supports various comparison operators (equals, not equals, contains, etc.)
   - Can check for the presence or absence of metadata keys

3. **Context Check**: Evaluates conditions against workflow context
   - Similar to metadata checks but operates on the context dictionary
   - Useful for making decisions based on workflow state

4. **Default**: Always matches, used as a fallback option

#### Workflow Integration

The `EnhancedWorkflowEngine` overrides the `_get_next_step` method to check for conditional branches before falling back to the default next step logic. This allows seamless integration of conditional branching with the existing workflow execution flow.

### Nested Workflows

Nested workflows allow for hierarchical composition of workflows, where a step in one workflow can trigger the execution of another workflow.

#### Key Components

- **NestedWorkflowEngine**: Core engine for managing nested workflow execution
- **NestedWorkflowStep**: Special workflow step that triggers execution of a child workflow
- **NestedWorkflowContext**: Maintains the state of a nested workflow execution
- **NestedWorkflowStatus**: Enum defining the status of a nested workflow execution

#### Context Mapping

When a nested workflow is executed, data can be passed between the parent and child workflows through context mapping:

1. **Context Mapping**: Maps keys from the parent workflow's context to keys in the child workflow's context
2. **Result Mapping**: Maps keys from the child workflow's result back to the parent workflow's context

#### Workflow Integration

The `EnhancedWorkflowEngine` overrides the `execute_step` method to handle nested workflow steps. When a nested workflow step is encountered, the parent workflow is paused until the child workflow completes.

## API Integration

The enhanced workflow features are exposed through a set of API endpoints:

1. **Conditional Branching API**:
   - `POST /api/workflows/enhanced/{workflow_id}/branches`: Create a conditional branch
   - `GET /api/workflows/enhanced/{workflow_id}/branches`: Get all branches for a workflow

2. **Nested Workflow API**:
   - `POST /api/workflows/enhanced/{workflow_id}/nested`: Create a nested workflow step
   - `GET /api/workflows/enhanced/{workflow_id}/nested/{step_id}/status`: Get nested workflow status
   - `POST /api/workflows/enhanced/{workflow_id}/nested/{step_id}/cancel`: Cancel a nested workflow

3. **Workflow Execution API**:
   - `POST /api/workflows/enhanced/{workflow_id}/execute-with-branching`: Execute a workflow with branching support

## Implementation Details

### Conditional Branching Implementation

The conditional branching engine evaluates conditions in order and returns the first matching target step. If no conditions match and a default target step is specified, it returns the default target step.

```python
async def evaluate_branch(self, branch: ConditionalBranch, message: T) -> Optional[str]:
    """Evaluate a branch against a message"""
    for condition in branch.conditions:
        if await self._evaluate_condition(condition, message):
            return condition.target_step_id
    
    return branch.default_target_step_id
```

### Nested Workflow Implementation

The nested workflow engine manages the execution of child workflows and handles the mapping of context data between parent and child workflows.

```python
async def execute_nested_workflow(self, context: NestedWorkflowContext, message: T) -> Optional[T]:
    """Execute a nested workflow"""
    # Map context from parent to child
    child_message = self._map_context(context, message)
    
    # Execute the child workflow
    result = await self.parent_engine.execute_workflow(
        context.child_workflow_id, child_message
    )
    
    if result:
        # Map results back to parent
        return self._map_results(context, result, message)
    
    return None
```

For more detailed information, see the [Conditional Branching and Nested Workflows](../features/conditional-branching-nested-workflows.md) feature documentation.
