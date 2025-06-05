/**
 * EndNode component
 * Custom node for the workflow end point
 */
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import './Nodes.css';

const EndNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className="end-node">
      <Handle
        type="target"
        position={Position.Top}
        className="handle"
      />
      
      <div className="node-label">End</div>
    </div>
  );
};

export default memo(EndNode);
