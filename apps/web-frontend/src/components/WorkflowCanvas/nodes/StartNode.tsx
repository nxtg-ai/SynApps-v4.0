/**
 * StartNode component
 * Custom node for the workflow start point
 */
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { NodeConfig } from './NodeConfig';
import './Nodes.css';
import './NodeConfig.css';

const StartNode: React.FC<NodeProps> = ({ data, id }) => {
  const { setNodes } = useReactFlow();
  const status = data.status || 'idle';
  
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

  return (
    <div className={`start-node ${status}`}>
      <NodeConfig 
        nodeId={id}
        nodeType="start"
        data={data}
        onConfigChange={handleConfigChange}
      />
      <div className="node-label">Start</div>
      
      <div className={`node-status-indicator ${status}`} />
      
      <Handle
        type="source"
        position={Position.Bottom}
        className="handle"
      />
    </div>
  );
};

export default memo(StartNode);
