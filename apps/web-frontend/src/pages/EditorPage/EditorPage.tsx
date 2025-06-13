/**
 * EditorPage component
 * Page for creating and editing workflows
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MainLayout from '../../components/Layout/MainLayout';
import WorkflowCanvas from '../../components/WorkflowCanvas/WorkflowCanvas';
import CodeEditor from '../../components/CodeEditor/CodeEditor';
import TemplateLoader from '../../components/TemplateLoader/TemplateLoader';
import WorkflowLoader from '../../components/WorkflowLoader/WorkflowLoader';
import { Flow } from '../../types';
import { generateId } from '../../utils/flowUtils';
import apiService from '../../services/ApiService';
import './EditorPage.css';

const EditorPage: React.FC<{}> = () => {
  const { flowId } = useParams<{ flowId: string }>();
  const navigate = useNavigate();
  
  const [flow, setFlow] = useState<Flow | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [showTemplates, setShowTemplates] = useState<boolean>(false);
  const [showWorkflowLoader, setShowWorkflowLoader] = useState<boolean>(false);
  const [showCodeEditor, setShowCodeEditor] = useState<boolean>(false);
  const [selectedApplet, setSelectedApplet] = useState<string>('');
  const [appletCode, setAppletCode] = useState<string>('');
  
  // State for workflow results
  const [workflowResults, setWorkflowResults] = useState<any>(null);

  // Load flow data if flowId is provided
  useEffect(() => {
    const loadFlow = async () => {
      setIsLoading(true);
      
      if (flowId) {
        try {
          const flowData = await apiService.getFlow(flowId);
          setFlow(flowData);
        } catch (error) {
          console.error('Error loading flow:', error);
          // Create an empty flow if not found
          createEmptyFlow();
        }
      } else {
        // Create an empty flow for new workflows
        createEmptyFlow();
      }
      
      setIsLoading(false);
    };
    
    loadFlow();
  }, [flowId]);

  // Subscribe to WebSocket updates for workflow results
  useEffect(() => {
    // Make sure WebSocket is connected
    import('../../services/WebSocketService').then(({ default: webSocketService }) => {
      console.log('Setting up WebSocket connection for workflow:', flowId);
      // Ensure WebSocket is connected
      webSocketService.connect();

      // Subscribe to workflow status updates
      const unsubscribe = webSocketService.subscribe('workflow.status', (status) => {
        console.log('Received workflow status update:', status);
        
        // Enhanced debug logging
        console.log('Current flowId:', flowId);
        console.log('Status flowId:', status.flow_id);
        console.log('Status:', status.status);
        console.log('Results:', status.results);
        
        // Guard against null or undefined flowId
        if (!flowId || !status.flow_id) return;
        
        // Only process updates for our current flow and avoid unnecessary updates
        if (status.flow_id === flowId) {
          if (status.status === 'success' && status.results) {
            console.log('Setting workflow results:', status.results);
            // Use a functional update to prevent unnecessary state updates
            setWorkflowResults((prevResults: any) => {
              // Skip update if results are the same (prevent infinite loop)
              if (prevResults && JSON.stringify(prevResults) === JSON.stringify(status.results)) {
                return prevResults;
              }
              return status.results;
            });
            
            // Only update running state if it's currently true
            setIsRunning(prev => prev ? false : prev);
          }
        }
      });

      return () => {
        unsubscribe();
      };
    });
  }, [flowId]);
  
  
  // Create an empty flow
  const createEmptyFlow = () => {
    const newFlow: Flow = {
      id: generateId(),
      name: 'New Workflow',
      nodes: [
        {
          id: generateId(),
          type: 'start',
          position: { x: 250, y: 25 },
          data: { 
            label: 'Start',
            inputData: '',
            parsedInputData: {} 
          }
        },
        {
          id: generateId(),
          type: 'end',
          position: { x: 250, y: 500 },
          data: { label: 'End' }
        }
      ],
      edges: []
    };
    
    setFlow(newFlow);
  };
  
    // Save the flow
    const saveFlow = async () => {
      if (!flow) return;
      
      setIsSaving(true);
      
      try {
        const response = await apiService.saveFlow(flow);
        console.log('Flow saved:', response);
        
        // Always update the flow ID in state to ensure it matches what's in the database
        setFlow(prevFlow => {
          if (!prevFlow) return null;
          return {
            ...prevFlow,
            id: response.id
          };
        });
        
        // Update URL if this is a new flow
        if (!flowId) {
          navigate(`/editor/${response.id}`);
        }
      } catch (error) {
        console.error('Error saving flow:', error);
      } finally {
      setIsSaving(false);
    }
  };
  
  // Run the flow
  const runFlow = async () => {
    if (!flow) return;
    
    // Validate that the workflow has a start node before execution
    const hasStartNode = flow.nodes.some(node => 
      node.type === 'start' || node.type === 'startNode'
    );
    
    if (!hasStartNode) {
      alert('This workflow does not have a Start node. Please add a Start node before running the workflow.');
      return;
    }
    
    setIsRunning(true);
    setWorkflowResults(null);
    
    try {
      // Use an empty object as input - the actual input will come from the Start node's configuration
      const emptyInput = {};
      
      console.log('Running flow with ID:', flow.id);
      console.log('Flow nodes:', flow.nodes.map(n => ({ id: n.id, type: n.type })));
      
      const response = await apiService.runFlow(flow.id, emptyInput);
      console.log('Flow execution started:', response);
      
      // Results will come through WebSocket
    } catch (error) {
      console.error('Error running flow:', error);
      setIsRunning(false);
      
      // Show error message to user
      alert('Error running workflow. Please check the console for details.');
    }
  };
  
  // Handle flow changes
  const handleFlowChange = useCallback((updatedFlow: Flow) => {
    // Only update if there's an actual change to prevent infinite loops
    if (JSON.stringify(flow) !== JSON.stringify(updatedFlow)) {
      setFlow(updatedFlow);
    }
  }, [flow]);
  
  // Handle template selection
  const handleSelectTemplate = (templateFlow: Flow) => {
    setFlow(templateFlow);
    setShowTemplates(false);
  };
  
  // Handle node click to edit applet code
  const handleNodeClick = async (nodeId: string, nodeType: string) => {
    // Check if this is an existing node in the workflow
    if (flow && flow.nodes.some(node => node.id === nodeId)) {
      // Only handle existing nodes for editing, not for adding
      if (nodeType === 'start' || nodeType === 'end') return;
      
      setSelectedApplet(nodeType);
      setAppletCode(`// Loading ${nodeType} applet code...`);
      setShowCodeEditor(true);
      
      // In a real implementation, we would fetch the actual applet code
      // For MVP, we'll simulate this with a timeout
      setTimeout(() => {
      setAppletCode(`
"""
${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)}Applet - ${nodeType === 'writer' ? 'Text generation' : nodeType === 'artist' ? 'Image generation' : 'Memory storage'} applet for SynApps

This applet is a placeholder for demonstration purposes.
"""
import os
import json
import logging
from typing import Dict, Any

from main import BaseApplet, AppletMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("${nodeType}-applet")

class ${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)}Applet(BaseApplet):
    """
    ${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)} Applet implementation.
    
    Replace this with your custom logic.
    """
    
    VERSION = "0.1.0"
    
    def __init__(self):
        """Initialize the ${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)} Applet."""
        # Your initialization code here
        pass
    
    async def on_message(self, message: AppletMessage) -> AppletMessage:
        """Process an incoming message."""
        logger.info("${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)} Applet received message")
        
        # Extract content and context
        content = message.content
        context = message.context
        
        # Your applet logic here
        result = self.process_content(content)
        
        # Return the response
        return AppletMessage(
            content=result,
            context=context,
            metadata={"applet": "${nodeType}"}
        )
    
    def process_content(self, content: Any) -> Any:
        """Process the content and return a result."""
        # Your processing logic here
        return f"Processed by ${nodeType} applet: {content}"
`);
    }, 500);
    } else if (flow) {
      // This is a new node being added from the node panel by clicking
      // Create a new node and add it to the flow
      const newNode = {
        id: nodeId,
        type: nodeType,
        position: { x: 100, y: 100 }, // Default position in the center of the canvas
        data: { label: nodeType.charAt(0).toUpperCase() + nodeType.slice(1) }
      };
      
      // Update the flow with the new node
      const updatedFlow = {
        ...flow,
        id: flow.id, // Ensure ID is preserved
        name: flow.name || 'Untitled Workflow', // Ensure name is preserved
        nodes: [...flow.nodes, newNode],
        edges: flow.edges || [] // Ensure edges are preserved
      };
      
      // Update the flow state
      setFlow(updatedFlow);
      console.log(`New node of type ${nodeType} with ID ${nodeId} added to the workflow`);
    }
  };
  
  // Handle applet code save
  const handleCodeSave = (code: string) => {
    // In a real implementation, we would send the code to the backend
    console.log(`Saving ${selectedApplet} applet code:`, code);
    
    // Close the editor
    setShowCodeEditor(false);
  };
  
  // Create header actions
  const headerActions = (
    <div className="editor-actions">
      <button 
        className="template-button"
        onClick={() => setShowTemplates(true)}
      >
        Templates
      </button>
      <button 
        className="load-button"
        onClick={() => setShowWorkflowLoader(true)}
      >
        Load Workflow
      </button>
      <input
        type="text"
        className="workflow-name-input"
        value={flow?.name || ''}
        onChange={(e) => setFlow(prev => prev ? { ...prev, name: e.target.value } : null)}
        placeholder="Workflow Name"
      />
      <button 
        className="save-button"
        onClick={saveFlow}
        disabled={isSaving || !flow}
      >
        {isSaving ? 'Saving...' : 'Save'}
      </button>
      <button 
        className="run-button"
        onClick={runFlow}
        disabled={isRunning || !flow}
      >
        {isRunning ? 'Running...' : 'Run Workflow'}
      </button>
    </div>
  );
  
  return (
    <MainLayout title="Workflow Editor" actions={headerActions}>
      <div className="editor-page">
        {/* Workflow Loader Modal */}
        <WorkflowLoader 
          isOpen={showWorkflowLoader}
          onClose={() => setShowWorkflowLoader(false)}
          currentFlowId={flowId}
        />
        
        {isLoading ? (
          <div className="loading-state">Loading workflow...</div>
        ) : flow ? (
          <div className="editor-container">
            <div className="canvas-container">
              <WorkflowCanvas 
                flow={flow} 
                onFlowChange={handleFlowChange} 
              />
            </div>
            <div className="editor-sidebar">
              {/* Node-specific configuration is now handled by each node component */}
              
              {/* Output Data Panel */}
              {/* Node Panel - Moved above results panel for better visibility */}
              <div className="node-panel">
                <h3>Available Nodes</h3>
                <div className="node-list">
                  <div 
                    className="node-item writer"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/reactflow', JSON.stringify({
                        type: 'writer',
                        data: { label: 'Writer' }
                      }));
                    }}
                    onClick={() => handleNodeClick(generateId(), 'writer')}
                  >
                    <span className="node-icon">✍️</span>
                    <span className="node-label">Writer</span>
                  </div>
                  <div 
                    className="node-item artist"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/reactflow', JSON.stringify({
                        type: 'artist',
                        data: { label: 'Artist' }
                      }));
                    }}
                    onClick={() => handleNodeClick(generateId(), 'artist')}
                  >
                    <span className="node-icon">🎨</span>
                    <span className="node-label">Artist</span>
                  </div>
                  <div 
                    className="node-item memory"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/reactflow', JSON.stringify({
                        type: 'memory',
                        data: { label: 'Memory' }
                      }));
                    }}
                    onClick={() => handleNodeClick(generateId(), 'memory')}
                  >
                    <span className="node-icon">🧠</span>
                    <span className="node-label">Memory</span>
                  </div>
                </div>
              </div>
              
              {/* Output Data Panel */}
              <div className="results-panel">
                <h3>Output Data {isRunning && '(Processing...)'}</h3>
                
                {/* Workflow metadata */}
                <div className="debug-info" style={{ fontSize: '12px', marginBottom: '10px', color: '#666' }}>
                  <div>Flow ID: {flowId}</div>
                  <div>Results available: {workflowResults ? 'Yes' : 'No'}</div>
                </div>
                
                {workflowResults ? (
                  <>
                    {/* Text Results Section */}
                    <div className="result-section">
                      <h4 className="section-title">Text Output</h4>
                      {workflowResults.writer ? (
                        <div className="text-result">
                          {workflowResults.writer.content || JSON.stringify(workflowResults.writer)}
                        </div>
                      ) : (
                        <div className="no-data">No text output available</div>
                      )}
                    </div>
                    
                    {/* Raw Results Section */}
                    <div className="result-section">
                      <h4 className="section-title">Raw Results</h4>
                      <pre className="text-result" style={{ whiteSpace: 'pre-wrap', maxHeight: '200px', overflow: 'auto' }}>
                        {JSON.stringify(workflowResults, null, 2)}
                      </pre>
                    </div>
                    
                    {/* Image Results Section */}
                    <div className="result-section">
                      <h4 className="section-title">Image Results</h4>
                      
                      {/* Direct access to the complete workflow results for image detection */}
                      {(() => {
                        console.log('Complete workflow results:', workflowResults);
                        
                        // CASE 1: Check if artist data exists directly in workflowResults
                        if (workflowResults.artist) {
                          console.log('Artist data found:', workflowResults.artist);
                          
                          // Case 1.1: Direct image URL
                          if (workflowResults.artist.image_url) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={workflowResults.artist.image_url} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: image_url</div>
                              </div>
                            );
                          }
                          
                          // Case 1.2: Base64 image property
                          if (workflowResults.artist.image) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={`data:image/png;base64,${workflowResults.artist.image}`} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: artist.image</div>
                              </div>
                            );
                          }
                          
                          // Case 1.3: Content is base64 string
                          if (typeof workflowResults.artist.content === 'string' && 
                              workflowResults.artist.content.match(/^[A-Za-z0-9+/=]+$/)) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={`data:image/png;base64,${workflowResults.artist.content}`} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: artist.content (base64)</div>
                              </div>
                            );
                          }
                          
                          // Case 1.4: Nested content object
                          if (workflowResults.artist.content && typeof workflowResults.artist.content === 'object') {
                            if (workflowResults.artist.content.image) {
                              return (
                                <div className="image-container">
                                  <img 
                                    src={`data:image/png;base64,${workflowResults.artist.content.image}`} 
                                    alt="Generated artwork" 
                                    className="result-image"
                                  />
                                  <div className="image-property">Source: artist.content.image</div>
                                </div>
                              );
                            }
                          }
                          
                          // Case 1.5: Property contains base64 PNG signature
                          for (const key in workflowResults.artist) {
                            const value = workflowResults.artist[key];
                            if (typeof value === 'string' && value.startsWith('iVBORw0KGgo')) {
                              return (
                                <div className="image-container">
                                  <img 
                                    src={`data:image/png;base64,${value}`} 
                                    alt="Generated artwork" 
                                    className="result-image"
                                  />
                                  <div className="image-property">Source: artist.{key}</div>
                                </div>
                              );
                            }
                          }
                        }
                        
                        // CASE 2: Check artist node in the top-level nodes collection
                        if (workflowResults.nodes && workflowResults.nodes.artist) {
                          console.log('Artist data found in nodes:', workflowResults.nodes.artist);
                          const artistNode = workflowResults.nodes.artist;
                          
                          // Similar checks for the artist node
                          if (artistNode.image_url) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={artistNode.image_url} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: nodes.artist.image_url</div>
                              </div>
                            );
                          }
                          
                          if (artistNode.image) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={`data:image/png;base64,${artistNode.image}`} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: nodes.artist.image</div>
                              </div>
                            );
                          }
                          
                          // Check for content
                          if (typeof artistNode.content === 'string' && 
                              artistNode.content.match(/^[A-Za-z0-9+/=]+$/)) {
                            return (
                              <div className="image-container">
                                <img 
                                  src={`data:image/png;base64,${artistNode.content}`} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: nodes.artist.content</div>
                              </div>
                            );
                          }
                          
                          // Check for base64 signatures in any property
                          for (const key in artistNode) {
                            const value = artistNode[key];
                            if (typeof value === 'string' && value.startsWith('iVBORw0KGgo')) {
                              return (
                                <div className="image-container">
                                  <img 
                                    src={`data:image/png;base64,${value}`} 
                                    alt="Generated artwork" 
                                    className="result-image"
                                  />
                                  <div className="image-property">Source: nodes.artist.{key}</div>
                                </div>
                              );
                            }
                          }
                        }
                        
                        // CASE 3: Look for any property that could be an image in the entire result
                        console.log('Scanning entire result for potential image data');
                        const scanForImageData = (obj: any, path = ''): any => {
                          if (!obj || typeof obj !== 'object') return null;
                          
                          // Check direct properties
                          for (const key in obj) {
                            const currentPath = path ? `${path}.${key}` : key;
                            const value = obj[key];
                            
                            // Look for common image property names
                            if ((key === 'image' || key === 'image_url' || key === 'image_data' || 
                                key === 'base64' || key === 'url') && typeof value === 'string') {
                              console.log(`Found potential image at ${currentPath}:`, value.substring(0, 30));
                              
                              // For URLs
                              if (value.startsWith('http')) {
                                return { path: currentPath, value, type: 'url' };
                              }
                              
                              // For base64 data
                              if (value.startsWith('data:image') || value.startsWith('iVBORw0KGgo')) {
                                return { path: currentPath, value, type: 'base64' };
                              }
                              
                              // For potential base64 without header
                              if (value.match(/^[A-Za-z0-9+/=]+$/) && value.length > 100) {
                                return { path: currentPath, value, type: 'base64' };
                              }
                            }
                            
                            // Recurse into nested objects
                            if (typeof value === 'object' && value !== null) {
                              const result = scanForImageData(value, currentPath);
                              if (result) return result;
                            }
                          }
                          
                          return null;
                        };
                        
                        const imageData = scanForImageData(workflowResults);
                        if (imageData) {
                          console.log('Found image data through deep scan:', imageData);
                          if (imageData.type === 'url') {
                            return (
                              <div className="image-container">
                                <img 
                                  src={imageData.value} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: {imageData.path}</div>
                              </div>
                            );
                          } else { // base64
                            const dataUrl = imageData.value.startsWith('data:image') 
                              ? imageData.value 
                              : `data:image/png;base64,${imageData.value}`;
                            
                            return (
                              <div className="image-container">
                                <img 
                                  src={dataUrl} 
                                  alt="Generated artwork" 
                                  className="result-image"
                                />
                                <div className="image-property">Source: {imageData.path}</div>
                              </div>
                            );
                          }
                        }
                        
                        // No image found after all attempts
                        return (
                          <div className="no-data">
                            <p>No image data found in results</p>
                            <p className="debug-note">Check browser console for details</p>
                          </div>
                        );
                      })()}
                    </div>
                  </>
                ) : (
                  <div className="no-results">
                    {isRunning ? 
                      'Workflow is running... results will appear here when complete.' : 
                      'No results yet. Run the workflow to see results here.'}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="error-state">
            <p>Could not load the workflow.</p>
            <button 
              className="create-button"
              onClick={createEmptyFlow}
            >
              Create New Workflow
            </button>
          </div>
        )}
      </div>
      
      {showTemplates && (
        <div className="modal-overlay">
          <TemplateLoader 
            onSelectTemplate={handleSelectTemplate}
            onClose={() => setShowTemplates(false)}
          />
        </div>
      )}
      
      {showCodeEditor && (
        <div className="modal-overlay">
          <div className="code-editor-modal">
            <CodeEditor 
              appletType={selectedApplet}
              initialCode={appletCode}
              onSave={handleCodeSave}
              onClose={() => setShowCodeEditor(false)}
            />
          </div>
        </div>
      )}
    </MainLayout>
  );
};

export default EditorPage;
