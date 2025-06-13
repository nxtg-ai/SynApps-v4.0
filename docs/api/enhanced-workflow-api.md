# Enhanced Workflow API Documentation

This document provides detailed information about the API endpoints available for working with enhanced workflow features in the SynApps Meta-Agent Orchestrator v0.5.0.

## Base URL

All API endpoints are relative to the base URL:

```
http://localhost:8000
```

## Authentication

Authentication is required for all API endpoints. Use the following header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### Conditional Branching

#### Create a Branch

Creates a conditional branch in a workflow.

**Endpoint:** `POST /api/workflows/enhanced/{workflow_id}/branches`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the workflow

**Request Body:**
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

**Condition Types:**
- `CONTENT_MATCH`: Matches against message content
  - Required fields: `target_step_id`, `content_pattern`
  - Optional fields: `pattern_is_regex`, `case_sensitive`
- `METADATA_CHECK`: Checks message metadata
  - Required fields: `target_step_id`, `metadata_key`
  - Optional fields: `metadata_value`, `metadata_comparison`
- `CONTEXT_CHECK`: Checks workflow context
  - Required fields: `target_step_id`, `context_key`
  - Optional fields: `context_value`, `context_comparison`
- `ALWAYS`: Always matches
  - Required fields: `target_step_id`

**Response:**
```json
{
  "branch_id": "branch-123",
  "source_step_id": "step1",
  "conditions": [
    {
      "condition_type": "CONTENT_MATCH",
      "target_step_id": "step2",
      "content_pattern": "success",
      "pattern_is_regex": false,
      "case_sensitive": false,
      "metadata_key": null,
      "metadata_value": null,
      "metadata_comparison": null,
      "context_key": null,
      "context_value": null,
      "context_comparison": null
    },
    {
      "condition_type": "METADATA_CHECK",
      "target_step_id": "step3",
      "content_pattern": null,
      "pattern_is_regex": null,
      "case_sensitive": null,
      "metadata_key": "status",
      "metadata_value": "error",
      "metadata_comparison": "equals",
      "context_key": null,
      "context_value": null,
      "context_comparison": null
    }
  ],
  "default_target_step_id": "step4"
}
```

**Status Codes:**
- `201 Created`: Branch created successfully
- `400 Bad Request`: Invalid request body
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

#### Get Branches for a Workflow

Retrieves all branches for a workflow.

**Endpoint:** `GET /api/workflows/enhanced/{workflow_id}/branches`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the workflow

**Response:**
```json
[
  {
    "branch_id": "branch-123",
    "source_step_id": "step1",
    "conditions": [
      {
        "condition_type": "CONTENT_MATCH",
        "target_step_id": "step2",
        "content_pattern": "success",
        "pattern_is_regex": false,
        "case_sensitive": false,
        "metadata_key": null,
        "metadata_value": null,
        "metadata_comparison": null,
        "context_key": null,
        "context_value": null,
        "context_comparison": null
      }
    ],
    "default_target_step_id": "step4"
  }
]
```

**Status Codes:**
- `200 OK`: Branches retrieved successfully
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

### Nested Workflows

#### Create a Nested Workflow Step

Creates a nested workflow step in a workflow.

**Endpoint:** `POST /api/workflows/enhanced/{workflow_id}/nested`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the parent workflow

**Request Body:**
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

**Response:**
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

**Status Codes:**
- `201 Created`: Nested workflow step created successfully
- `400 Bad Request`: Invalid request body
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

#### Get Nested Workflow Status

Retrieves the status of a nested workflow execution.

**Endpoint:** `GET /api/workflows/enhanced/{workflow_id}/nested/{step_id}/status`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the parent workflow
- `step_id` (string, required): The ID of the nested workflow step

**Response:**
```json
{
  "execution_id": "exec-123",
  "parent_workflow_id": "parent-workflow",
  "parent_step_id": "step2",
  "child_workflow_id": "child-workflow-1",
  "status": "RUNNING",
  "start_time": 1623456789.123,
  "end_time": null,
  "error_message": null
}
```

**Status Values:**
- `PENDING`: Nested workflow execution is pending
- `RUNNING`: Nested workflow is currently running
- `COMPLETED`: Nested workflow has completed successfully
- `FAILED`: Nested workflow execution failed
- `CANCELLED`: Nested workflow execution was cancelled

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `404 Not Found`: Nested workflow execution not found
- `500 Internal Server Error`: Server error

#### Cancel a Nested Workflow

Cancels a running nested workflow execution.

**Endpoint:** `POST /api/workflows/enhanced/{workflow_id}/nested/{step_id}/cancel`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the parent workflow
- `step_id` (string, required): The ID of the nested workflow step

**Response:**
```json
{
  "status": "cancelled"
}
```

**Status Codes:**
- `200 OK`: Nested workflow cancelled successfully
- `400 Bad Request`: Failed to cancel nested workflow
- `404 Not Found`: Nested workflow execution not found
- `500 Internal Server Error`: Server error

### Workflow Execution

#### Execute Workflow with Branching

Executes a workflow with conditional branching support.

**Endpoint:** `POST /api/workflows/enhanced/{workflow_id}/execute-with-branching`

**Path Parameters:**
- `workflow_id` (string, required): The ID of the workflow to execute

**Request Body:**
```json
{
  "content": "Hello, world!",
  "metadata": {
    "key1": "value1",
    "key2": "value2"
  },
  "context": {
    "contextKey1": "contextValue1",
    "contextKey2": "contextValue2"
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "result": {
    "content": "Processed result",
    "metadata": {
      "key1": "value1",
      "key2": "value2"
    },
    "context": {
      "contextKey1": "contextValue1",
      "contextKey2": "contextValue2"
    }
  }
}
```

**Status Values:**
- `running`: Workflow execution is in progress
- `completed`: Workflow execution has completed

**Status Codes:**
- `200 OK`: Workflow executed successfully
- `400 Bad Request`: Invalid request body
- `404 Not Found`: Workflow not found
- `500 Internal Server Error`: Server error

## Error Responses

All API endpoints return standard error responses in the following format:

```json
{
  "detail": "Error message describing the issue"
}
```

## Examples

### Creating a Conditional Branch

```bash
curl -X POST "http://localhost:8000/api/workflows/enhanced/workflow-123/branches" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_step_id": "step1",
    "conditions": [
      {
        "condition_type": "CONTENT_MATCH",
        "target_step_id": "step2",
        "content_pattern": "success",
        "pattern_is_regex": false,
        "case_sensitive": false
      }
    ],
    "default_target_step_id": "step3"
  }'
```

### Creating a Nested Workflow Step

```bash
curl -X POST "http://localhost:8000/api/workflows/enhanced/parent-workflow/nested" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "parent_step_id": "step2",
    "child_workflow_id": "child-workflow-1",
    "context_mapping": {
      "parent_input": "child_input"
    },
    "result_mapping": {
      "child_output": "parent_result"
    }
  }'
```

### Executing a Workflow with Branching

```bash
curl -X POST "http://localhost:8000/api/workflows/enhanced/workflow-123/execute-with-branching" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Process this message",
    "metadata": {
      "priority": "high"
    },
    "context": {
      "user_id": "user-123"
    }
  }'
```
