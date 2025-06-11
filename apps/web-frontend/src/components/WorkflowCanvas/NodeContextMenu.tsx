import React, { useEffect, useRef } from 'react';
import './NodeContextMenu.css';

interface NodeContextMenuProps {
  nodeRect: DOMRect;
  nodeId: string;
  nodeType: string;
  onDelete: (nodeId: string) => void;
  onOpenConfig: (nodeId: string) => void;
  onClose: () => void;
}

const NodeContextMenu: React.FC<NodeContextMenuProps> = ({ nodeRect, nodeId, nodeType, onDelete, onOpenConfig, onClose }) => {
  // Create a ref for the menu element
  const menuRef = React.useRef<HTMLDivElement>(null);
  
  // Handle click outside to close the menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Only close if clicking outside the menu
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    
    // Add event listener
    document.addEventListener('mousedown', handleClickOutside);
    
    // Clean up
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  // Calculate position to place menu right next to the node
  const menuStyle = {
    position: 'absolute' as const,
    top: `${nodeRect.top}px`,
    left: `${nodeRect.right + 5}px`, // 5px offset from the right edge of the node
    pointerEvents: 'auto' as const
  };
  
  return (
    <div 
      className="node-context-menu"
      ref={menuRef}
      style={menuStyle}
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <ul>
        {/* Only show edit option for applet nodes, not start/end nodes */}
        {nodeType === 'applet' && (
          <li onClick={() => { onOpenConfig(nodeId); onClose(); }}>
            <span className="menu-icon">⚙️</span> Edit Configuration
          </li>
        )}
        <li onClick={() => { onDelete(nodeId); onClose(); }}>
          <span className="menu-icon">🗑️</span> Delete Node
        </li>
        <li className="menu-divider"></li>
        <li onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onClose();
        }}>
          <span className="menu-icon">❌</span> Cancel
        </li>
      </ul>
    </div>
  );
};

export default NodeContextMenu;
