/**
 * Type definitions for SynApps MVP
 */

export interface FlowNode {
  id: string;
  type: string;
  position: {
    x: number;
    y: number;
  };
  data: Record<string, any>;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  animated?: boolean;
}

export interface Flow {
  id: string;
  name: string;
  description?: string;
  version?: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  metadata?: Record<string, any>;
}

export interface WorkflowRunStatus {
  run_id: string;
  flow_id: string;
  status: 'running' | 'success' | 'error';
  current_applet?: string;
  completed_applets?: string[]; // Array of completed node IDs
  progress: number;
  total_steps: number;
  start_time: number;
  end_time?: number;
  results: Record<string, any>;
  error?: string;
  input_data?: Record<string, any>; // Optional field for initial input data
}

export interface AppletMetadata {
  type: string;
  name: string;
  description: string;
  version: string;
  capabilities: string[];
}

export interface FlowTemplate {
  id: string;
  name: string;
  description: string;
  tags: string[];
  flow: Flow;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
  timestamp: number;
  read: boolean;
}

export interface CodeSuggestionRequest {
  code: string;
  hint: string;
}

export interface CodeSuggestionResponse {
  original: string;
  suggestion: string;
  diff: string;
}
