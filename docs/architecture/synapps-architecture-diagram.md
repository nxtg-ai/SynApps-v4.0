# SynApps Architecture Diagram

## Current Architecture

```mermaid
graph TD
    %% Frontend Components
    subgraph "Frontend (React)"
        UI[Web UI]
        ApiService[API Service]
        WebSocketService[WebSocket Service]
        FlowEditor[Flow Editor]
        FlowRunner[Flow Runner]
    end
    
    %% Backend Components
    subgraph "Backend (FastAPI)"
        API[API Routes]
        WS[WebSocket Handler]
        Orchestrator[Meta-Agent Orchestrator]
        Validator[Schema Validator]
        Repository[DB Repository]
    end
    
    %% Applets
    subgraph "Applets"
        Writer[Writer Applet]
        Researcher[Researcher Applet]
        Analyzer[Analyzer Applet]
        OtherApplets[Other Applets...]
    end
    
    %% Database
    DB[(Database)]
    
    %% Connections
    UI --> ApiService
    UI --> WebSocketService
    ApiService --> API
    WebSocketService --> WS
    API --> Orchestrator
    WS --> Orchestrator
    Orchestrator --> Repository
    Repository --> DB
    Orchestrator --> Validator
    Orchestrator --> Writer
    Orchestrator --> Researcher
    Orchestrator --> Analyzer
    Orchestrator --> OtherApplets
```

## Enhanced Architecture

```mermaid
graph TD
    %% Frontend Components
    subgraph "Frontend (React)"
        UI[Web UI]
        ApiService[API Service]
        WebSocketService[WebSocket Service]
        FlowEditor[Enhanced Flow Editor]
        FlowRunner[Flow Runner]
        Timeline[Execution Timeline]
        Metrics[Metrics Dashboard]
    end
    
    %% Backend Components
    subgraph "Backend (FastAPI)"
        API[API Routes]
        WS[WebSocket Handler]
        
        subgraph "Microkernel Orchestrator"
            Core[Orchestrator Core]
            PromptInjector[System Prompt Injector]
            OutputEnforcer[Output Enforcer]
            RuleEngine[Governance Rule Engine]
            MessageBus[Message Bus]
        end
        
        Repository[DB Repository]
        MetricsCollector[Metrics Collector]
        Analytics[Analytics Engine]
        TimelineService[Timeline Service]
    end
    
    %% Applets (Snaplets)
    subgraph "Snaplets"
        Writer[Writer Snaplet]
        Researcher[Researcher Snaplet]
        Analyzer[Analyzer Snaplet]
        OtherSnaplets[Other Snaplets...]
    end
    
    %% Database
    DB[(Database)]
    
    %% External Services
    ExternalAPIs[External APIs]
    
    %% Connections - Frontend
    UI --> ApiService
    UI --> WebSocketService
    UI --> FlowEditor
    UI --> FlowRunner
    UI --> Timeline
    UI --> Metrics
    
    %% Connections - API
    ApiService --> API
    WebSocketService --> WS
    
    %% Connections - Backend Core
    API --> Core
    WS --> Core
    Core --> PromptInjector
    Core --> OutputEnforcer
    Core --> RuleEngine
    Core --> MessageBus
    Core --> Repository
    Core --> MetricsCollector
    
    %% Connections - Analytics & Timeline
    MetricsCollector --> Analytics
    Core --> TimelineService
    TimelineService --> Repository
    Analytics --> Repository
    
    %% Connections - Database
    Repository --> DB
    
    %% Connections - Snaplets
    MessageBus --> Writer
    MessageBus --> Researcher
    MessageBus --> Analyzer
    MessageBus --> OtherSnaplets
    
    %% External Connections
    Writer --> ExternalAPIs
    Researcher --> ExternalAPIs
    Analyzer --> ExternalAPIs
```

## Key Enhancements

1. **Microkernel Orchestrator**:
   - Lightweight core with modular components
   - System Prompt Injector for standardized agent instructions
   - Output Enforcer for structured response validation
   - Governance Rule Engine for compliance and safety

2. **Message Bus**:
   - Direct agent-to-agent communication
   - Event-driven architecture
   - Asynchronous message passing

3. **Enhanced Monitoring**:
   - Metrics Collector for performance tracking
   - Analytics Engine for insights
   - Timeline Service for execution history and playback

4. **Improved Frontend**:
   - Enhanced Flow Editor with advanced node types
   - Execution Timeline visualization
   - Metrics Dashboard for monitoring

5. **Standardized Snaplet Interface**:
   - Consistent API for all AI agents
   - Pluggable architecture
   - Support for parallel execution and conditional branching
