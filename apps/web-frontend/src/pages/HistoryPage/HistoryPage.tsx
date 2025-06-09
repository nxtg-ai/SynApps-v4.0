/**
 * HistoryPage component
 * Displays workflow run history and details
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import MainLayout from '../../components/Layout/MainLayout';
import { WorkflowRunStatus } from '../../types';
import apiService from '../../services/ApiService';
import './HistoryPage.css';

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const runIdParam = queryParams.get('run');
  
  const [runs, setRuns] = useState<WorkflowRunStatus[]>([]);
  const [selectedRun, setSelectedRun] = useState<WorkflowRunStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [flowNames, setFlowNames] = useState<Record<string, string>>({});
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc'); // Default to newest first
  const [flowDetails, setFlowDetails] = useState<Record<string, any>>({});
  
  // Load workflow runs and flow details
  useEffect(() => {
    const loadRuns = async () => {
      setIsLoading(true);
      try {
        const runsData = await apiService.getRuns();
        
        // Sort runs by start_time based on current sort order
        const sortedRuns = [...runsData].sort((a, b) => 
          sortOrder === 'desc' ? b.start_time - a.start_time : a.start_time - b.start_time
        );
        setRuns(sortedRuns);
        
        // Fetch flow details to get names
        const flowIdsMap: Record<string, boolean> = {};
        const uniqueFlowIds: string[] = [];
        
        // Get unique flow IDs without using Set spread operator
        runsData.forEach(run => {
          if (!flowIdsMap[run.flow_id]) {
            flowIdsMap[run.flow_id] = true;
            uniqueFlowIds.push(run.flow_id);
          }
        });
        
        const flowNamesMap: Record<string, string> = {};
        const flowDetailsMap: Record<string, any> = {};
        
        // Fetch flow details in parallel
        await Promise.all(uniqueFlowIds.map(async (flowId) => {
          try {
            const flowData = await apiService.getFlow(flowId);
            flowNamesMap[flowId] = flowData.name || `Flow ${flowId}`;
            flowDetailsMap[flowId] = flowData;
          } catch (error) {
            console.error(`Error loading flow ${flowId}:`, error);
            flowNamesMap[flowId] = `Flow ${flowId}`;
          }
        }));
        
        setFlowNames(flowNamesMap);
        setFlowDetails(flowDetailsMap);
        
        // If run ID is provided in URL, select that run
        if (runIdParam) {
          const run = runsData.find(r => r.run_id === runIdParam);
          if (run) {
            setSelectedRun(run);
          } else {
            // Try to load the specific run
            try {
              const runData = await apiService.getRun(runIdParam);
              setSelectedRun(runData);
            } catch (error) {
              console.error('Error loading specific run:', error);
            }
          }
        } else if (sortedRuns.length > 0) {
          // Select the most recent run (first item in the sorted runs when sorting by desc)
          setSelectedRun(sortedRuns[0]);
        }
      } catch (error) {
        console.error('Error loading runs:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadRuns();
  }, [runIdParam, sortOrder]);
  
  // Format date for display
  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };
  
  // Format duration
  const formatDuration = (startTime: number, endTime?: number) => {
    if (!endTime) return 'In progress';
    
    const durationSeconds = endTime - startTime;
    
    if (durationSeconds < 60) {
      return `${durationSeconds.toFixed(2)} seconds`;
    } else {
      const minutes = Math.floor(durationSeconds / 60);
      const seconds = durationSeconds % 60;
      return `${minutes}m ${seconds.toFixed(0)}s`;
    }
  };
  
  return (
    <MainLayout title="Workflow History">
      <div className="history-page">
        {isLoading ? (
          <div className="loading-state">Loading workflow runs...</div>
        ) : runs.length === 0 ? (
          <div className="empty-state">
            <p>No workflow runs found.</p>
            <button 
              className="create-button"
              onClick={() => navigate('/editor')}
            >
              Create a Workflow
            </button>
          </div>
        ) : (
          <div className="history-container">
            <div className="runs-sidebar">
              <div className="runs-header">
                <h3>Recent Runs</h3>
                <button 
                  className="sort-toggle" 
                  onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                  title={sortOrder === 'desc' ? 'Currently: Newest first' : 'Currently: Oldest first'}
                >
                  {sortOrder === 'desc' ? '↓ Newest first' : '↑ Oldest first'}
                </button>
              </div>
              <div className="runs-list">
                {runs.map(run => (
                  <div 
                    key={run.run_id}
                    className={`run-item ${run.status} ${selectedRun?.run_id === run.run_id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedRun(run);
                      // Update URL without navigating
                      navigate(`/history?run=${run.run_id}`, { replace: true });
                    }}
                  >
                    <div className="run-header">
                      <span className="flow-name">{flowNames[run.flow_id] || 'Loading...'}</span>
                      <span className="flow-id">ID: {run.flow_id}</span>
                      <span className={`status-badge ${run.status}`}>
                        {run.status}
                      </span>
                    </div>
                    <div className="run-time">
                      {formatDate(run.start_time)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="run-details">
              {selectedRun ? (
                <>
                  <div className="details-header">
                    <h2>Run Details</h2>
                    <span className={`status-badge large ${selectedRun.status}`}>
                      {selectedRun.status}
                    </span>
                  </div>
                  
                  <div className="details-grid">
                    <div className="detail-item">
                      <span className="detail-label">Run ID</span>
                      <span className="detail-value">{selectedRun.run_id}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Flow Name</span>
                      <span className="detail-value">{flowNames[selectedRun.flow_id] || 'Unknown'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Flow ID</span>
                      <span className="detail-value">{selectedRun.flow_id}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Start Time</span>
                      <span className="detail-value">{formatDate(selectedRun.start_time)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">End Time</span>
                      <span className="detail-value">
                        {selectedRun.end_time ? formatDate(selectedRun.end_time) : 'In progress'}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Duration</span>
                      <span className="detail-value">
                        {formatDuration(selectedRun.start_time, selectedRun.end_time)}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Steps</span>
                      <span className="detail-value">
                        {selectedRun.progress} / {selectedRun.total_steps}
                      </span>
                    </div>
                  </div>
                  
                  {selectedRun.error && (
                    <div className="error-panel">
                      <h3>Error</h3>
                      <div className="error-message">{selectedRun.error}</div>
                    </div>
                  )}
                  
                  <h3>Results</h3>
                  <div className="results-panel">
                    {selectedRun && flowDetails[selectedRun.flow_id] ? (
                      <div className="results-tree">
                        {(() => {
                          const flow = flowDetails[selectedRun.flow_id];
                          const allNodes = flow.nodes || [];
                          const results = selectedRun.results || {};
                          
                          // Create a map of node IDs to their positions in the flow
                          const nodePositions: Record<string, number> = {};
                          allNodes.forEach((node: any, index: number) => {
                            nodePositions[node.id] = index;
                          });
                          
                          // Define interfaces for our node data
                          interface FlowNode {
                            id: string;
                            type: string;
                            [key: string]: any;
                          }
                          
                          interface DisplayNode {
                            nodeId: string;
                            nodeType: string;
                            position: number;
                            result: { type: string; output: any } | null;
                          }
                          
                          // Create a complete list of nodes to display, including Start and End
                          const displayNodes = allNodes.map((node: FlowNode) => {
                            const nodeId = node.id;
                            const nodeType = node.type;
                            const isStartOrEnd = nodeType.toLowerCase() === 'start' || nodeType.toLowerCase() === 'end';
                            const resultData = results[nodeId];
                            
                            return {
                              nodeId,
                              nodeType,
                              position: nodePositions[nodeId],
                              // If it's a Start or End node without result data, create a placeholder
                              result: resultData || (isStartOrEnd ? { type: nodeType, output: isStartOrEnd ? {} : null } : null)
                            } as DisplayNode;
                          }).filter((item: DisplayNode) => item.result !== null);
                          
                          // Sort by position in the flow
                          return displayNodes
                            .sort((a: DisplayNode, b: DisplayNode) => a.position - b.position)
                            .map((item: DisplayNode, index: number) => {
                              const { nodeId, nodeType, result } = item;
                              const stepNumber = index + 1;
                              const nodeResult = result as { type: string; output: any };
                              
                              // Extract input prompt if available in the output
                              let inputPrompt = '';
                              if (nodeResult.output && typeof nodeResult.output === 'object') {
                                if (nodeResult.output.prompt) {
                                  inputPrompt = nodeResult.output.prompt;
                                } else if (nodeResult.output.input) {
                                  inputPrompt = typeof nodeResult.output.input === 'string' 
                                    ? nodeResult.output.input 
                                    : JSON.stringify(nodeResult.output.input);
                                }
                              }
                              
                              const isStartOrEnd = nodeType.toLowerCase() === 'start' || nodeType.toLowerCase() === 'end';
                              
                              return (
                                <div key={nodeId} className={`result-node ${isStartOrEnd ? 'system-node' : ''}`}>
                                  <div className="result-header">
                                    <span className="step-number">Step {stepNumber}</span>
                                    <span className={`node-type ${isStartOrEnd ? 'system-node-type' : ''}`}>{nodeType}</span>
                                    <span className="node-id">{nodeId}</span>
                                  </div>
                                  
                                  {inputPrompt && (
                                    <div className="prompt-section">
                                      <div className="prompt-header">Input Prompt:</div>
                                      <div className="prompt-content">{inputPrompt}</div>
                                    </div>
                                  )}
                                  
                                  {isStartOrEnd ? (
                                    <div className="result-output system-node-output">
                                      <div className="output-header">{nodeType.toLowerCase() === 'start' ? 'Workflow Input Data' : 'Final Workflow Context'}</div>
                                      {nodeType.toLowerCase() === 'start' ? (
                                        <div>
                                          <div className="text-output">Initial workflow input data:</div>
                                          <div className="json-output">
                                            <pre>
                                              {(() => {
                                                // For Start node, show the initial input data from the workflow run
                                                console.log('Selected run data:', selectedRun);
                                                
                                                // Try multiple sources for input data
                                                let inputData = {};
                                                
                                                // Source 1: input_data field directly on the run
                                                if (selectedRun.input_data && typeof selectedRun.input_data === 'object') {
                                                  console.log('Found input_data in selectedRun:', selectedRun.input_data);
                                                  inputData = selectedRun.input_data;
                                                } 
                                                // Source 2: Look for Start node in results that might have the input
                                                else if (selectedRun.results) {
                                                  // Find the Start node in the results
                                                  const startNode = Object.entries(selectedRun.results)
                                                    .find(([nodeId, result]: [string, any]) => {
                                                      const node = flowDetails[selectedRun.flow_id]?.nodes?.find((n: any) => n.id === nodeId);
                                                      return node && node.type.toLowerCase() === 'start';
                                                    });
                                                    
                                                  if (startNode && startNode[1] && startNode[1].output) {
                                                    console.log('Found Start node with output:', startNode[1].output);
                                                    // Try to get input from the Start node output
                                                    if (typeof startNode[1].output === 'object') {
                                                      if (startNode[1].output.input) {
                                                        inputData = startNode[1].output.input;
                                                      } else if (startNode[1].output.context && startNode[1].output.context.input) {
                                                        inputData = startNode[1].output.context.input;
                                                      }
                                                    }
                                                  }
                                                }
                                                
                                                // Source 3: Find any node with context information as a last resort
                                                if (Object.keys(inputData).length === 0) {
                                                  const firstNodeWithContext = Object.values(selectedRun.results || {})
                                                    .find((result: any) => 
                                                      result && 
                                                      result.output && 
                                                      typeof result.output === 'object' && 
                                                      result.output.context && 
                                                      result.output.context.input
                                                    );
                                                  
                                                  if (firstNodeWithContext && firstNodeWithContext.output.context.input) {
                                                    console.log('Found input in node context:', firstNodeWithContext.output.context.input);
                                                    inputData = firstNodeWithContext.output.context.input;
                                                  }
                                                }
                                                
                                                // If we have a non-empty object, stringify it
                                                if (Object.keys(inputData).length > 0) {
                                                  return JSON.stringify(inputData, null, 2);
                                                }
                                                
                                                // Default empty object
                                                return JSON.stringify({}, null, 2);
                                              })()}
                                            </pre>
                                          </div>
                                        </div>
                                      ) : (
                                        <div>
                                          <div className="text-output">Final workflow context:</div>
                                          <div className="json-output">
                                            <pre>
                                              {(() => {
                                                // For End node, show the final workflow context with all results
                                                // First get all nodes with context
                                                const allNodesWithContext = Object.entries(selectedRun.results || {})
                                                  .filter(([_, result]: [string, any]) => 
                                                    result && 
                                                    result.output && 
                                                    typeof result.output === 'object' && 
                                                    result.output.context
                                                  );
                                                  
                                                // If there are no nodes with context, show the entire results object
                                                if (allNodesWithContext.length === 0) {
                                                  return JSON.stringify(selectedRun.results || {}, null, 2);
                                                }
                                                
                                                // Sort by node position to get the last node
                                                const sortedNodes = [...allNodesWithContext].sort((a: [string, any], b: [string, any]) => {
                                                  const nodeA = flowDetails[selectedRun.flow_id]?.nodes?.find((n: any) => n.id === a[0]);
                                                  const nodeB = flowDetails[selectedRun.flow_id]?.nodes?.find((n: any) => n.id === b[0]);
                                                  if (nodeA && nodeB) {
                                                    // Sort by y position (higher y is later in the flow)
                                                    if (nodeA.position.y !== nodeB.position.y) {
                                                      return nodeB.position.y - nodeA.position.y; // Last node first
                                                    }
                                                    // If same y position, sort by x position
                                                    return nodeB.position.x - nodeA.position.x;
                                                  }
                                                  return 0;
                                                });

                                                const lastNodeWithContext = sortedNodes.length > 0 ? sortedNodes[0] : null;

                                                // Extract the final context if available
                                                const finalContext = lastNodeWithContext ? 
                                                  lastNodeWithContext[1].output.context : 
                                                  { results: {} };

                                                return JSON.stringify(finalContext, null, 2);
                                              })()}
                                            </pre>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <div className="result-output">
                                      <div className="output-header">Output:</div>
                                      {typeof nodeResult.output === 'string' ? (
                                        <div className="text-output">{nodeResult.output}</div>
                                      ) : nodeResult.output && nodeResult.output.image ? (
                                        <div className="image-output">
                                          <img 
                                            src={`data:image/png;base64,${nodeResult.output.image}`} 
                                            alt="Generated output" 
                                          />
                                        </div>
                                      ) : (
                                        <div className="json-output">
                                          <pre>
                                            {JSON.stringify(nodeResult.output, null, 2)}
                                          </pre>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            });
                        })()}
                      </div>
                    ) : (
                      <div className="no-results">
                        {selectedRun.status === 'running' ? 
                          'Workflow is still running...' : 
                          'No results available.'}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="no-run-selected">
                  <p>Select a run from the sidebar to view details.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default HistoryPage;
