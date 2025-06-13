/**
 * NodeConfig component
 * Provides configuration UI for different node types
 */
import React, { useState, useEffect } from 'react';
import './NodeConfig.css';

interface NodeConfigProps {
  nodeId: string;
  nodeType: string;
  data: Record<string, any>;
  onConfigChange: (nodeId: string, updatedData: Record<string, any>) => void;
}

export const NodeConfig: React.FC<NodeConfigProps> = ({ 
  nodeId, 
  nodeType, 
  data, 
  onConfigChange 
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleConfig = () => {
    setIsOpen(!isOpen);
  };

  const handleConfigChange = (updatedData: Record<string, any>) => {
    onConfigChange(nodeId, {
      ...data,
      ...updatedData
    });
  };

  // Render different config panels based on node type
  const renderConfigPanel = () => {
    switch (nodeType.toLowerCase()) {
      case 'start':
        return (
          <StartNodeConfig 
            data={data} 
            onChange={handleConfigChange} 
          />
        );
      case 'writer':
        return (
          <WriterNodeConfig 
            data={data} 
            onChange={handleConfigChange} 
          />
        );
      case 'artist':
        return (
          <ArtistNodeConfig 
            data={data} 
            onChange={handleConfigChange} 
          />
        );
      default:
        return null;
    }
  };

  if (!['start', 'writer', 'artist'].includes(nodeType.toLowerCase())) {
    return null;
  }

  return (
    <div className="node-config">
      <button 
        className="config-toggle" 
        onClick={toggleConfig}
        title="Configure node"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </button>
      
      {isOpen && (
        <div className="config-panel">
          <div className="config-header">
            <h3>{nodeType} Configuration</h3>
            <button className="close-button" onClick={toggleConfig}>×</button>
          </div>
          <div className="config-content">
            {renderConfigPanel()}
          </div>
        </div>
      )}
    </div>
  );
};

// Start Node Configuration
interface StartNodeConfigProps {
  data: Record<string, any>;
  onChange: (updatedData: Record<string, any>) => void;
}

export const StartNodeConfig: React.FC<StartNodeConfigProps> = ({ data, onChange }) => {
  // Initialize inputData from node data, ensuring it's a string
  const [inputData, setInputData] = useState(() => {
    // Check if inputData exists in the node data
    if (data.inputData !== undefined) {
      return data.inputData;
    }
    // If not, initialize with empty string
    return '';
  });
  
  // Initialize parsedInputData when component mounts
  useEffect(() => {
    // Only initialize if inputData exists but parsedInputData doesn't
    if (data.inputData && data.parsedInputData === undefined) {
      try {
        // Try to parse as JSON if it looks like JSON
        const trimmed = data.inputData.trim();
        if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
            (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
          const parsedJson = JSON.parse(data.inputData);
          onChange({ parsedInputData: parsedJson });
        } else {
          onChange({ parsedInputData: { text: data.inputData } });
        }
      } catch (error) {
        // If not valid JSON, store as plain text
        onChange({ parsedInputData: { text: data.inputData } });
      }
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInputData(value);
    
    try {
      // Try to parse as JSON if it looks like JSON
      const trimmed = value.trim();
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
          (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        const parsedJson = JSON.parse(value);
        onChange({ inputData: value, parsedInputData: parsedJson });
      } else {
        onChange({ inputData: value, parsedInputData: { text: value } });
      }
    } catch (error) {
      // If not valid JSON, store as plain text
      onChange({ inputData: value, parsedInputData: { text: value } });
    }
  };

  return (
    <div className="start-node-config">
      <div className="form-group">
        <label htmlFor="input-data">Input Data:</label>
        <textarea
          id="input-data"
          value={inputData}
          onChange={handleInputChange}
          placeholder="Enter initial workflow data (plain text or JSON)"
          rows={5}
        />
        <small className="form-help">
          This data will be used as the initial input for the workflow.
          You can enter plain text or JSON.
        </small>
      </div>
    </div>
  );
};

// Writer Node Configuration
interface WriterNodeConfigProps {
  data: Record<string, any>;
  onChange: (updatedData: Record<string, any>) => void;
}

export const WriterNodeConfig: React.FC<WriterNodeConfigProps> = ({ data, onChange }) => {
  const [systemPrompt, setSystemPrompt] = useState(data.systemPrompt || '');

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setSystemPrompt(value);
    onChange({ systemPrompt: value });
  };

  return (
    <div className="writer-node-config">
      <div className="form-group">
        <label htmlFor="system-prompt">System Prompt:</label>
        <textarea
          id="system-prompt"
          value={systemPrompt}
          onChange={handlePromptChange}
          placeholder="Enter system prompt for the LLM"
          rows={5}
        />
        <small className="form-help">
          This prompt will guide the behavior of the language model.
        </small>
      </div>
    </div>
  );
};

// Artist Node Configuration
interface ArtistNodeConfigProps {
  data: Record<string, any>;
  onChange: (updatedData: Record<string, any>) => void;
}

export const ArtistNodeConfig: React.FC<ArtistNodeConfigProps> = ({ data, onChange }) => {
  const [systemPrompt, setSystemPrompt] = useState(data.systemPrompt || '');
  const [generator, setGenerator] = useState(data.generator || 'dall-e');

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setSystemPrompt(value);
    onChange({ systemPrompt: value, generator });
  };

  const handleGeneratorChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setGenerator(value);
    onChange({ systemPrompt, generator: value });
  };

  return (
    <div className="artist-node-config">
      <div className="form-group">
        <label htmlFor="generator">Image Generator:</label>
        <select
          id="generator"
          value={generator}
          onChange={handleGeneratorChange}
        >
          <option value="dall-e">DALL-E</option>
          <option value="stable-diffusion">Stable Diffusion</option>
          <option value="midjourney">Midjourney</option>
        </select>
      </div>
      
      <div className="form-group">
        <label htmlFor="artist-system-prompt">System Prompt:</label>
        <textarea
          id="artist-system-prompt"
          value={systemPrompt}
          onChange={handlePromptChange}
          placeholder="Enter system prompt for the image generator"
          rows={5}
        />
        <small className="form-help">
          This prompt will guide the behavior of the image generation model.
        </small>
      </div>
    </div>
  );
};

export default NodeConfig;
