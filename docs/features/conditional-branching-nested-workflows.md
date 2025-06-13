# Conditional Branching and Nested Workflows

This document provides an overview of the conditional branching and nested workflow features implemented in the SynApps Meta-Agent Orchestrator v0.5.0.

## Table of Contents

- [Overview](#overview)
- [Conditional Branching](#conditional-branching)
  - [Branch Conditions](#branch-conditions)
  - [Creating Branches](#creating-branches)
  - [API Usage](#conditional-branching-api)
- [Nested Workflows](#nested-workflows)
  - [Context Mapping](#context-mapping)
  - [Creating Nested Workflows](#creating-nested-workflows)
  - [API Usage](#nested-workflows-api)
- [Integration with Workflow Engine](#integration-with-workflow-engine)
- [Examples](#examples)

## Overview

The SynApps Meta-Agent Orchestrator now supports two powerful features that enhance workflow flexibility and composability:

1. **Conditional Branching**: Allows workflows to dynamically choose different execution paths based on message content, metadata, or context.
2. **Nested Workflows**: Enables hierarchical composition of workflows, where a step in one workflow can trigger the execution of another workflow.

These features are implemented in the `EnhancedWorkflowEngine` which extends the base `MetaAgentOrchestrator` with additional capabilities.

## Conditional Branching

Conditional branching enables dynamic routing of messages within a workflow based on conditions evaluated against the message content, metadata, or context.

### Branch Conditions

The system supports several types of conditions:

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

### Creating Branches

Branches are created by specifying:

1. A source step ID (where the branch originates)
2. One or more conditions with target step IDs
3. An optional default target step ID

When a message is processed at the source step, each condition is evaluated in order. The first matching condition determines the next step to execute.

### Conditional Branching API

The API provides endpoints for creating and managing branches:

```
POST /api/workflows/enhanced/{workflow_id}/branches
```

Example request body:
```json
{
  "source_step_id": "step1",
  "conditions": [
    {
      "condition_type": "CONTENT_MATCH",
      "target_step_id": "step2",
      "content_pattern": "success",
      "pattern_is_regex": false,
      "case_sensitive": false
    },
    {
      "condition_type": "METADATA_CHECK",
      "target_step_id": "step3",
      "metadata_key": "status",
      "metadata_value": "error",
      "metadata_comparison": "equals"
    }
  ],
  "default_target_step_id": "step4"
}
```

To retrieve all branches for a workflow:

```
GET /api/workflows/enhanced/{workflow_id}/branches
```

## Nested Workflows

Nested workflows allow for hierarchical composition of workflows, where a step in one workflow can trigger the execution of another workflow.

### Context Mapping

When a nested workflow is executed, data can be passed between the parent and child workflows through context mapping:

1. **Context Mapping**: Maps keys from the parent workflow's context to keys in the child workflow's context
2. **Result Mapping**: Maps keys from the child workflow's result back to the parent workflow's context

This enables workflows to be modular and reusable while still sharing necessary data.

### Creating Nested Workflows

A nested workflow is created by:

1. Creating a `NestedWorkflowStep` in the parent workflow
2. Specifying the child workflow ID
3. Defining context and result mappings
4. Registering the relationship with the `NestedWorkflowEngine`

When the parent workflow reaches the nested workflow step, the child workflow is executed. The parent workflow is paused until the child workflow completes.

### Nested Workflows API

The API provides endpoints for creating and managing nested workflows:

```
POST /api/workflows/enhanced/{workflow_id}/nested
```

Example request body:
```json
{
  "parent_step_id": "step2",
  "child_workflow_id": "child-workflow-1",
  "context_mapping": {
    "parent_key1": "child_key1",
    "parent_key2": "child_key2"
  },
  "result_mapping": {
    "child_result": "parent_result"
  }
}
```

To check the status of a nested workflow:

```
GET /api/workflows/enhanced/{workflow_id}/nested/{step_id}/status
```

To cancel a running nested workflow:

```
POST /api/workflows/enhanced/{workflow_id}/nested/{step_id}/cancel
```

## Integration with Workflow Engine

The `EnhancedWorkflowEngine` integrates these features with the existing workflow engine:

1. It extends `MetaAgentOrchestrator` to maintain compatibility with existing code
2. It overrides key methods like `_get_next_step` and `execute_step` to support branching and nested workflows
3. It provides additional methods for creating and managing branches and nested workflows

## Examples

### Conditional Branching Example

```python
# Create a workflow with conditional branching
workflow = WorkflowDefinition(workflow_id="workflow-with-branching")

# Add steps
workflow.add_step(WorkflowStep(step_id="start"))
workflow.add_step(WorkflowStep(step_id="process_success"))
workflow.add_step(WorkflowStep(step_id="process_error"))
workflow.add_step(WorkflowStep(step_id="default_process"))

# Register the workflow
engine.register_workflow(workflow)

# Create a branch from the "start" step
branch = engine.create_content_branch(
    workflow_id="workflow-with-branching",
    source_step_id="start",
    conditions=[
        engine.branching_engine.create_content_condition(
            target_step_id="process_success",
            content_pattern="success"
        ),
        engine.branching_engine.create_metadata_condition(
            target_step_id="process_error",
            metadata_key="status",
            metadata_value="error"
        )
    ],
    default_target_step_id="default_process"
)
```

### Nested Workflow Example

```python
# Create parent workflow
parent_workflow = WorkflowDefinition(workflow_id="parent-workflow")
parent_workflow.add_step(WorkflowStep(step_id="parent_start"))
parent_workflow.add_step(NestedWorkflowStep(
    step_id="nested_step",
    child_workflow_id="child-workflow",
    context_mapping={"parent_input": "child_input"},
    result_mapping={"child_output": "parent_result"}
))
parent_workflow.add_step(WorkflowStep(step_id="parent_end"))

# Create child workflow
child_workflow = WorkflowDefinition(workflow_id="child-workflow")
child_workflow.add_step(WorkflowStep(step_id="child_start"))
child_workflow.add_step(WorkflowStep(step_id="child_process"))
child_workflow.add_step(WorkflowStep(step_id="child_end"))

# Register workflows
engine.register_workflow(parent_workflow)
engine.register_workflow(child_workflow)

# Register nested workflow relationship
engine.register_nested_workflow(
    parent_workflow_id="parent-workflow",
    parent_step_id="nested_step",
    child_workflow_id="child-workflow"
)
```
