# Changelog

All notable changes to the SynApps MVP project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-31

### Fixed

- **Workflow Editor Infinite Update Loop**
  - Modified the `handleNodeClick` function in `EditorPage.tsx` to check if the node already exists in the workflow
  - Used `useRef` to track previous flow values in `WorkflowCanvas.tsx` to prevent unnecessary re-renders
  - Implemented proper state comparison using JSON stringification in the `handleFlowChange` function

- **Node Panel Not Displaying**
  - Restructured the editor sidebar layout in `EditorPage.tsx` to properly display all panels
  - Added scrolling to the sidebar in `EditorPage.css` to ensure all content is accessible
  - Removed duplicate node panel code from the bottom of the component

- **Drag and Drop Not Working**
  - Implemented proper `onDrop` and `onDragOver` handlers in the `WorkflowCanvas` component
  - Fixed the `handleNodeClick` function to properly add new nodes when clicked
  - Added proper TypeScript type checking to prevent null reference errors

### Added

- **Enhanced Sidebar Layout**
  - Improved organization of the sidebar with Input Panel, Available Nodes, and Results Panel
  - Added overflow scrolling to ensure all panels are accessible

### Changed

- **Node Addition Logic**
  - Modified how nodes are added to the workflow when clicked vs. dragged
  - Ensured proper flow state updates when adding new nodes

## [0.1.0] - 2025-05-22

### Added

- **Initial MVP Release**
  - Basic workflow editor with React Flow
  - Support for Writer, Artist, and Memory applets
  - Real-time workflow execution via WebSockets
  - Results panel with text and image output support

### Fixed

- **Image Results Rendering**
  - Implemented a recursive scanning algorithm to detect image data in various formats
  - Added support for multiple image formats (URLs, base64, nested objects)

- **WebSocket Connection Issues**
  - Updated WebSocket URL to explicitly use `localhost:8000`
  - Added better connection management and logging
  - Implemented proper subscription in the EditorPage component
