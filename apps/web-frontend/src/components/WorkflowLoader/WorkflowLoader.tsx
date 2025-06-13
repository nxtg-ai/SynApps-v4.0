/**
 * WorkflowLoader component
 * Allows users to select and load previously saved workflows
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Flow } from '../../types';
import apiService from '../../services/ApiService';
import './WorkflowLoader.css';

interface WorkflowLoaderProps {
  isOpen: boolean;
  onClose: () => void;
  currentFlowId?: string;
}

const WorkflowLoader: React.FC<WorkflowLoaderProps> = ({ 
  isOpen, 
  onClose,
  currentFlowId 
}) => {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      loadFlows();
    }
  }, [isOpen]);

  const loadFlows = async () => {
    setIsLoading(true);
    try {
      const flowsData = await apiService.getFlows();
      setFlows(flowsData);
    } catch (error) {
      console.error('Error loading workflows:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFlowSelect = (flowId: string) => {
    // Force a full page reload to ensure all node configurations are properly loaded
    window.location.href = `/editor/${flowId}`;
    onClose();
  };

  const filteredFlows = flows.filter(flow => 
    flow.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="workflow-loader-overlay">
      <div className="workflow-loader-modal">
        <div className="workflow-loader-header">
          <h2>Load Workflow</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="workflow-loader-search">
          <input
            type="text"
            placeholder="Search workflows..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="workflow-loader-content">
          {isLoading ? (
            <div className="loading-state">Loading workflows...</div>
          ) : filteredFlows.length > 0 ? (
            <ul className="workflow-list">
              {filteredFlows.map(flow => (
                <li 
                  key={flow.id} 
                  className={`workflow-item ${flow.id === currentFlowId ? 'current' : ''}`}
                  onClick={() => flow.id !== currentFlowId && handleFlowSelect(flow.id)}
                >
                  <div className="workflow-name">{flow.name}</div>
                  <div className="workflow-id">ID: {flow.id}</div>
                  {flow.id === currentFlowId && <span className="current-badge">Current</span>}
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              {searchTerm ? 'No workflows match your search' : 'No saved workflows found'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowLoader;
