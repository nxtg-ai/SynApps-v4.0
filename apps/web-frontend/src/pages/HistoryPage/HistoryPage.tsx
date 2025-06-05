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
  
  // Load workflow runs
  useEffect(() => {
    const loadRuns = async () => {
      setIsLoading(true);
      try {
        const runsData = await apiService.getRuns();
        setRuns(runsData);
        
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
        } else if (runsData.length > 0) {
          // Select the most recent run
          setSelectedRun(runsData[0]);
        }
      } catch (error) {
        console.error('Error loading runs:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadRuns();
  }, [runIdParam]);
  
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
              <h3>Recent Runs</h3>
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
                      <span className="flow-name">{run.flow_id}</span>
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
                      <span className="detail-label">Flow</span>
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
                    {Object.keys(selectedRun.results).length > 0 ? (
                      <div className="results-tree">
                        {Object.entries(selectedRun.results).map(([nodeId, result]) => {
                          const nodeResult = result as { type: string; output: any };
                          return (
                            <div key={nodeId} className="result-node">
                              <div className="result-header">
                                <span className="node-type">{nodeResult.type}</span>
                                <span className="node-id">{nodeId}</span>
                              </div>
                              <div className="result-output">
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
                            </div>
                          );
                        })}
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
