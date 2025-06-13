/**
 * WorkflowCanvas component
 * Visual editor for creating and visualizing AI workflows
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  Connection,
  Edge,
  Node,
  applyNodeChanges,
  applyEdgeChanges,
  OnConnect,
  OnEdgesChange,
  OnNodesChange,
  ConnectionLineType
} from 'reactflow';
import 'reactflow/dist/style.css';
import anime from 'animejs';
import { Flow, WorkflowRunStatus } from '../../types';
import { generateId } from '../../utils/flowUtils';
import './WorkflowCanvas.css';

// Custom node types
import AppletNode from './nodes/AppletNode';
import StartNode from './nodes/StartNode';
import EndNode from './nodes/EndNode';

// Handlers for workflow execution
import webSocketService from '../../services/WebSocketService';

interface WorkflowCanvasProps {
  flow: Flow;
  onFlowChange: (flow: Flow) => void;
  readonly?: boolean;
}

const nodeTypes = {
  applet: AppletNode,
  start: StartNode,
  end: EndNode,
  writer: AppletNode,
  memory: AppletNode,
  artist: AppletNode,
};

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({ flow, onFlowChange, readonly = false }) => {
  // Convert Flow to ReactFlow nodes and edges
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [runStatus, setRunStatus] = useState<WorkflowRunStatus | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  
  // Reference to the anime.js timeline
  const animationRef = useRef<anime.AnimeTimelineInstance | null>(null);
  
  // Reference to the ReactFlow wrapper div
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  
  // Use ref to track previous flow value to prevent unnecessary updates
  const prevFlowRef = useRef<string>('');
  
  // Convert our Flow format to ReactFlow format
  useEffect(() => {
    if (!flow) return; // Guard against null flow
    
    // Convert current flow to string for comparison
    const currentFlowStr = JSON.stringify(flow);
    
    // Skip update if flow hasn't changed
    if (prevFlowRef.current === currentFlowStr) {
      return;
    }
    
    // Update ref with current flow
    prevFlowRef.current = currentFlowStr;
    
    // Map nodes - only if we have nodes to map
    if (!Array.isArray(flow.nodes)) {
      console.warn('Flow nodes is not an array:', flow.nodes);
      return; // Prevent processing invalid data
    }
    
    try {
      // Map nodes with proper type checking
      const mappedNodes = flow.nodes.map(node => {
        if (!node || typeof node !== 'object') {
          console.warn('Invalid node in flow:', node);
          return null; // Skip invalid nodes
        }
        
        // Create a properly typed node
        const typedNode: Node = {
          id: node.id,
          type: node.type === 'writer' || node.type === 'memory' || node.type === 'artist' 
            ? node.type 
            : node.type === 'start' || node.type === 'end' 
              ? node.type 
              : 'applet',
          position: node.position || { x: 0, y: 0 }, // Default position if missing
          data: {
            ...(node.data || {}), // Guard against missing data
            label: (node.data && node.data.label) || node.type || 'Unknown',
            // Initialize node-specific configuration data if not present
            ...(node.type === 'start' && (!node.data || !node.data.inputData) && { inputData: '', parsedInputData: {} }),
            ...(node.type === 'writer' && (!node.data || !node.data.systemPrompt) && { systemPrompt: '' }),
            ...(node.type === 'artist' && (!node.data || !node.data.systemPrompt) && { systemPrompt: '', generator: 'dall-e' }),
            status: (node.data && node.data.status) || 'idle' // Ensure status is always defined
          }
        };
        
        return typedNode;
      }).filter((node): node is Node => node !== null);
      
      // Map edges - only if we have edges to map
      if (!Array.isArray(flow.edges)) {
        console.warn('Flow edges is not an array:', flow.edges);
        return; // Prevent processing invalid data
      }
      
      const mappedEdges = flow.edges.map(edge => {
        if (!edge || typeof edge !== 'object') {
          console.warn('Invalid edge in flow:', edge);
          return null; // Skip invalid edges
        }
        
        // Create a properly typed edge
        const typedEdge: Edge = {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          animated: edge.animated || false,
        };
        
        return typedEdge;
      }).filter((edge): edge is Edge => edge !== null);
      
      // Update state with properly typed arrays
      setNodes(mappedNodes);
      setEdges(mappedEdges);
    } catch (error) {
      console.error('Error processing flow data:', error);
    }
  }, [flow]);
  
  // Node changes handler
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      if (readonly) return;
      
      setNodes((nds) => {
        const newNodes = applyNodeChanges(changes, nds);
        
        // Update the flow with the new node positions and data
        const updatedFlow = {
          ...flow,
          nodes: flow.nodes.map(node => {
            const updatedNode = newNodes.find(n => n.id === node.id);
            if (updatedNode) {
              return {
                ...node,
                position: updatedNode.position,
                data: {
                  ...node.data,
                  ...updatedNode.data
                }
              };
            }
            return node;
          })
        };
        
        onFlowChange(updatedFlow);
        return newNodes;
      });
    },
    [flow, onFlowChange, readonly]
  );
  
  // Edge changes handler
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      if (readonly) return;
      
      setEdges((eds) => {
        const newEdges = applyEdgeChanges(changes, eds);
        
        // Update the flow with the new edges
        const updatedFlow = {
          ...flow,
          edges: flow.edges.map(edge => {
            const updatedEdge = newEdges.find(e => e.id === edge.id);
            if (updatedEdge) {
              return {
                ...edge,
                animated: updatedEdge.animated || false
              };
            }
            return edge;
          })
        };
        
        onFlowChange(updatedFlow);
        return newEdges;
      });
    },
    [flow, onFlowChange, readonly]
  );
  
  // Connection handler
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (readonly) return;
      
      const newEdge = {
        id: generateId(),
        source: connection.source || '',
        target: connection.target || '',
        animated: false
      };
      
      setEdges((eds) => {
        const newEdges = addEdge(connection, eds);
        
        // Update the flow with the new edge
        const updatedFlow = {
          ...flow,
          edges: [...flow.edges, newEdge]
        };
        
        onFlowChange(updatedFlow);
        return newEdges;
      });
    },
    [flow, onFlowChange, readonly]
  );

  // Subscribe to workflow status updates
  useEffect(() => {
    const unsubscribe = webSocketService.subscribe('workflow.status', (status: WorkflowRunStatus) => {
      // Only update if it's our flow
      if (status.flow_id === flow.id) {
        setRunStatus(status);
        
        // Keep track of completed nodes
        if (status.completed_applets && Array.isArray(status.completed_applets)) {
          setCompletedNodes(status.completed_applets);
        } else if (status.current_applet && status.status !== 'error') {
          // If completed_applets is not provided, infer from current_applet
          // Find the index of current node in the workflow
          const nodeIndex = flow.nodes.findIndex(node => node.id === status.current_applet);
          
          if (nodeIndex > 0) {
            // Mark all nodes before the current one as completed
            const previousNodeIds = flow.nodes
              .slice(0, nodeIndex)
              .map(node => node.id);
            setCompletedNodes(previousNodeIds);
          }
        }
        
        // Update node statuses
        setNodes(prevNodes => {
          return prevNodes.map(node => {
            // Current node is running
            if (node.id === status.current_applet) {
              return {
                ...node,
                data: { ...node.data, status: 'running' }
              };
            }
            
            // Node is already completed
            if (status.completed_applets && status.completed_applets.includes(node.id)) {
              return {
                ...node,
                data: { ...node.data, status: 'success' }
              };
            }
            
            // Error state
            if (status.status === 'error' && node.id === status.current_applet) {
              return {
                ...node,
                data: { ...node.data, status: 'error' }
              };
            }
            
            // Default state
            return {
              ...node,
              data: { ...node.data, status: node.data.status || 'idle' }
            };
          });
        });
        
        // Update edge animations
        const updatedEdges = edges.map(edge => {
          // Find which node is the target of this edge
          const targetNode = nodes.find(node => node.id === edge.target);
          
          // If target node is the current one or completed, animate the edge
          if (targetNode && (targetNode.id === status.current_applet || targetNode.data.status === 'success')) {
            return {
              ...edge,
              animated: true
            };
          }
          
          return edge;
        });
        
        setEdges(updatedEdges);
        
        // Create animations
        animateWorkflow(status);
      }
    });
    
    return () => {
      unsubscribe();
    };
  }, [flow.id, nodes, edges, completedNodes, flow.nodes]);
  
  // Animation function
  const animateWorkflow = (status: WorkflowRunStatus) => {
    // Stop any existing animation
    if (animationRef.current) {
      animationRef.current.pause();
    }
    
    // Create a new animation timeline
    const timeline = anime.timeline({
      easing: 'easeOutSine',
      duration: 500
    });
    
    // Find the current node element
    const currentNodeElement = document.querySelector(`[data-id="${status.current_applet}"]`);
    
    if (currentNodeElement) {
      // Add pulse animation to current node
      timeline.add({
        targets: currentNodeElement,
        scale: [1, 1.05, 1],
        opacity: [1, 0.8, 1],
        duration: 1000,
        easing: 'easeInOutQuad'
      });
    }
    
    // Store the timeline reference
    animationRef.current = timeline;
  };
  
  // Handle drop event for new nodes
  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      
      if (readonly) return;
      
      if (reactFlowWrapper.current && reactFlowInstance) {
        const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
        const nodeData = event.dataTransfer.getData('application/reactflow');
        
        if (!nodeData) return;
        
        const data = JSON.parse(nodeData);
        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });
        
        const newNodeId = generateId();
        
        // Update the flow with the new node
        const updatedFlow = {
          ...flow,
          nodes: [...flow.nodes, {
            id: newNodeId,
            type: data.type,
            position,
            data: { 
              label: data.data.label,
              status: 'idle'
            }
          }]
        };
        
        onFlowChange(updatedFlow);
      }
    },
    [flow, onFlowChange, reactFlowInstance, readonly]
  );
  
  // Handle drag over event
  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);
  
  return (
    <div className="workflow-canvas" ref={reactFlowWrapper}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
          attributionPosition="bottom-right"
          connectionLineStyle={{ stroke: '#ddd', strokeWidth: 2 }}
          connectionLineType={ConnectionLineType.Bezier}
          snapToGrid={true}
          snapGrid={[15, 15]}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
          minZoom={0.2}
          maxZoom={4}
          onNodeDragStop={(e, node) => {
            // Update node position in our Flow format when drag stops
            if (!readonly) {
              const updatedFlow = {
                ...flow,
                nodes: flow.nodes.map(n => {
                  if (n.id === node.id) {
                    return {
                      ...n,
                      position: node.position
                    };
                  }
                  return n;
                })
              };
              onFlowChange(updatedFlow);
            }
          }}
        >
          <Background color="#f8f8f8" gap={16} />
          <Controls />
          <MiniMap
            nodeStrokeColor={(n) => {
              if (n.data?.status === 'running') return '#1a90ff';
              if (n.data?.status === 'success') return '#52c41a';
              if (n.data?.status === 'error') return '#ff4d4f';
              return '#eee';
            }}
            nodeColor={(n) => {
              if (n.type === 'start') return '#d9f7be';
              if (n.type === 'end') return '#fff1f0';
              if (n.type === 'writer') return '#e6f7ff';
              if (n.type === 'memory') return '#f9f0ff';
              if (n.type === 'artist') return '#fff7e6';
              return '#fff';
            }}
            nodeBorderRadius={2}
          />
        </ReactFlow>
      </ReactFlowProvider>
      
      {runStatus && (
        <div className={`workflow-status ${runStatus.status}`}>
          <div className="workflow-status-header">
            <span className="status-label">Status: {runStatus.status}</span>
            <span className="progress-label">
              {runStatus.progress} / {runStatus.total_steps} steps
            </span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ 
                width: `${(runStatus.progress / runStatus.total_steps) * 100}%` 
              }}
            />
          </div>
          {runStatus.error && (
            <div className="error-message">
              Error: {runStatus.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Wrap the component with ReactFlowProvider to provide the Zustand store
const WorkflowCanvasWithProvider: React.FC<WorkflowCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <WorkflowCanvas {...props} />
    </ReactFlowProvider>
  );
};

export default WorkflowCanvasWithProvider;
