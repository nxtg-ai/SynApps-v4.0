/**
 * StartNode component
 * Custom node for the workflow start point
 */
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import './Nodes.css';

const StartNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className="start-node">
      <div className="node-label">Start</div>
      
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
      />
    </div>
  );
};

export default memo(StartNode);
