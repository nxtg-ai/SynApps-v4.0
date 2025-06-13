/**
 * EndNode component
 * Custom node for the workflow end point
 */
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import './Nodes.css';

const EndNode: React.FC<NodeProps> = ({ data }) => {
  const status = data.status || 'idle';
  
  return (
    <div className={`end-node ${status}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      
      <div className="node-label">End</div>
      
      <div className={`node-status-indicator ${status}`} />
    </div>
  );
};

export default memo(EndNode);
