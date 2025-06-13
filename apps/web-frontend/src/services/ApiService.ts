/**
 * ApiService - Handles HTTP communication with the enhanced Meta-Agent Orchestrator backend
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { 
  Flow, 
  FlowTemplate, 
  AppletMetadata, 
  WorkflowRunStatus,
  CodeSuggestionRequest,
  CodeSuggestionResponse
} from '../types';

class ApiService {
  private api: AxiosInstance;
  
  constructor() {
    const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    
    this.api = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      response => response,
      error => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }
  
  /**
   * Get all available applets
   */
  public async getApplets(): Promise<AppletMetadata[]> {
    const response = await this.api.get('/api/applets');
    return response.data;
  }
  
  /**
   * Get all workflows
   */
  public async getFlows(): Promise<Flow[]> {
    const response = await this.api.get('/api/workflows');
    return response.data;
  }
  
  /**
   * Get a specific workflow
   */
  public async getFlow(flowId: string): Promise<Flow> {
    const response = await this.api.get(`/api/workflows/${flowId}`);
    return response.data;
  }
  
  /**
   * Save a workflow - creates new or updates existing
   */
  public async saveFlow(flow: Flow): Promise<{ id: string }> {
    // Transform frontend Flow to backend Workflow format
    const backendWorkflow = {
      id: flow.id || undefined, // Let backend generate ID if not provided
      name: flow.name || 'Untitled Workflow', // Ensure name is never empty
      description: flow.description || '', 
      version: flow.version || '1.0.0',
      nodes: flow.nodes.map(node => {
        // Ensure node has a valid type that matches backend expectations
        let nodeType = node.type;
        if (nodeType === 'appletNode') nodeType = 'agent';
        if (nodeType === 'startNode') nodeType = 'start';
        if (nodeType === 'endNode') nodeType = 'end';
        
        // Ensure position is properly formatted
        const position = {
          x: node.position?.x || 0,
          y: node.position?.y || 0
        };
        
        return {
          id: node.id,
          name: node.data?.label || nodeType || 'Unnamed Node',
          type: nodeType,
          position: position,
          applet_id: node.data?.appletId || null,
          config: node.data || {},
          metadata: {}
        };
      }),
      edges: flow.edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        condition: null,
        metadata: {}
      })),
      metadata: flow.metadata || {}
    };
    
    console.log('Sending workflow to backend:', backendWorkflow);
    
    try {
      // Check if the workflow has a valid ID and exists in the backend
      // Use PUT for updates to existing workflows, POST for new workflows
      let response;
      
      if (flow.id && flow.id.length > 0) {
        // This is an existing workflow with an ID - use PUT to update
        console.log(`Updating existing workflow with ID: ${flow.id}`);
        try {
          response = await this.api.put(`/api/workflows/${flow.id}`, backendWorkflow);
          console.log('Workflow updated successfully:', response.data);
        } catch (updateError: any) {
          // If we get a 404, the workflow doesn't exist despite having an ID
          // This can happen if the workflow was created client-side but never saved
          if (updateError.response?.status === 404) {
            console.log('Workflow not found, creating as new instead');
            response = await this.api.post('/api/workflows', backendWorkflow);
            console.log('New workflow created successfully:', response.data);
          } else {
            // Re-throw other errors
            throw updateError;
          }
        }
      } else {
        // This is a new workflow without an ID - use POST to create
        console.log('Creating new workflow');
        response = await this.api.post('/api/workflows', backendWorkflow);
        console.log('New workflow created successfully:', response.data);
      }
      
      return { id: response.data.id };
    } catch (error: any) {
      console.error('Error saving workflow:', error.response?.data || error);
      throw error;
    }
  }
  
  /**
   * Delete a workflow
   */
  public async deleteFlow(flowId: string): Promise<void> {
    await this.api.delete(`/api/workflows/${flowId}`);
  }
  
  /**
   * Execute a workflow with the given input data
   */
  public async runFlow(flowId: string, inputData: Record<string, any>): Promise<{ run_id: string }> {
    try {
      console.log(`Executing workflow with ID: ${flowId}`);
      const response = await this.api.post(`/api/workflows/${flowId}/execute`, inputData);
      console.log('Workflow execution response:', response.data);
      
      // Map the response to match what the frontend expects
      return { 
        run_id: response.data.workflow_id || response.data.id || flowId 
      };
    } catch (error: any) {
      console.error('Error executing workflow:', error);
      
      // Provide more detailed error information if available
      if (error.response) {
        console.error('Response status:', error.response.status);
        console.error('Response data:', error.response.data);
        
        // Check for specific error cases
        if (error.response.status === 404) {
          console.error(`Workflow with ID ${flowId} not found. Verify the workflow was saved correctly.`);
        } else if (error.response.status === 422) {
          console.error('Invalid request format. Check workflow structure and input data.');
        }
      }
      
      throw error;
    }
  }
  
  /**
   * Get all workflow runs
   */
  public async getRuns(): Promise<WorkflowRunStatus[]> {
    // In the enhanced orchestrator, we get runs by workflow status endpoint
    const response = await this.api.get('/api/workflows/status');
    return response.data;
  }
  
  /**
   * Get a specific workflow run status
   */
  public async getRun(runId: string): Promise<WorkflowRunStatus> {
    const response = await this.api.get(`/api/workflows/${runId}/status`);
    return response.data;
  }
  
  /**
   * Get AI code suggestions
   */
  public async getCodeSuggestion(request: CodeSuggestionRequest): Promise<CodeSuggestionResponse> {
    // In the enhanced orchestrator, we use the meta-agent validation endpoint
    const response = await this.api.post('/api/meta-agent/validate', {
      ...request,
      agent_type: 'code_suggestion'
    });
    return response.data;
  }
  
  /**
   * Apply governance rules to a message
   */
  public async applyRules(workflowId: string, nodeId: string, message: any, ruleIds?: string[]): Promise<any> {
    const params = new URLSearchParams();
    params.append('workflow_id', workflowId);
    params.append('node_id', nodeId);
    if (ruleIds && ruleIds.length > 0) {
      ruleIds.forEach(id => params.append('rule_ids', id));
    }
    
    const response = await this.api.post(`/api/meta-agent/apply-rules?${params.toString()}`, message);
    return response.data;
  }
}

// Create a singleton instance
export const apiService = new ApiService();
export default apiService;
