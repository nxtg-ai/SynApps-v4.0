/**
 * AppletNode component
 * Custom node for applets in the workflow canvas
 */
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { NodeConfig } from './NodeConfig';
import './Nodes.css';
import './NodeConfig.css';

const AppletNode: React.FC<NodeProps> = ({ data, id, type }) => {
  const appletType = type || 'applet';
  const status = data.status || 'idle';
  const { setNodes } = useReactFlow();
  
  const handleConfigChange = useCallback((nodeId: string, updatedData: Record<string, any>) => {
    setNodes(nodes => 
      nodes.map(node => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              ...updatedData
            }
          };
        }
        return node;
      })
    );
  }, [setNodes]);
  
  // Get the icon based on applet type
  const getIcon = () => {
    switch (appletType) {
      case 'writer':
        return '✍️';
      case 'artist':
        return '🎨';
      case 'memory':
        return '🧠';
      default:
        return '🔌';
    }
  };
  
  // Get the color based on applet type
  const getColor = () => {
    switch (appletType) {
      case 'writer':
        return '#e6f7ff';
      case 'artist':
        return '#fff7e6';
      case 'memory':
        return '#f9f0ff';
      default:
        return '#f5f5f5';
    }
  };
  
  // Get the border color based on status
  const getBorderColor = () => {
    switch (status) {
      case 'running':
        return '#1a90ff';
      case 'success':
        return '#52c41a';
      case 'error':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };
  
  return (
    <div 
      className={`applet-node ${status}`} 
      style={{ 
        backgroundColor: getColor(),
        borderColor: getBorderColor()
      }}
      data-id={id}
    >
      {(appletType === 'writer' || appletType === 'artist') && (
        <NodeConfig 
          nodeId={id}
          nodeType={appletType}
          data={data}
          onConfigChange={handleConfigChange}
        />
      )}

      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      
      <div className="applet-icon">
        {getIcon()}
      </div>
      
      <div className="applet-content">
        <div className="applet-name">{data.label || type}</div>
        {data.description && (
          <div className="applet-description">{data.description}</div>
        )}
      </div>
      
      <div className={`applet-status-indicator ${status}`} />
      
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
      />
    </div>
  );
};

export default memo(AppletNode);
