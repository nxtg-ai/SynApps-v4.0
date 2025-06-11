import React from 'react';
import './NodeContextMenu.css';

interface NodeContextMenuProps {
  x: number;
  y: number;
  nodeType: string;
  onDelete: () => void;
  onEdit: () => void;
  onClose: () => void;
}

const NodeContextMenu: React.FC<NodeContextMenuProps> = ({ x, y, nodeType, onDelete, onEdit, onClose }) => {
  // Create a ref for the menu element
  const menuRef = React.useRef<HTMLDivElement>(null);
  
  // Handle click outside to close the menu
  React.useEffect(() => {
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

  return (
    <div 
      className="node-context-menu"
      ref={menuRef}
      style={{ 
        position: 'absolute',
        top: y,
        left: x,
        zIndex: 1000
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <ul>
        {/* Only show edit option for applet nodes, not start/end nodes */}
        {nodeType !== 'start' && nodeType !== 'end' && (
          <li onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setTimeout(() => {
              onEdit();
              onClose();
            }, 0);
          }}>
            <span className="menu-icon">✏️</span> Edit Configuration
          </li>
        )}
        <li onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          // Use setTimeout to ensure the event completes before we execute the delete
          setTimeout(() => {
            onDelete();
            onClose();
          }, 0);
        }}>
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
