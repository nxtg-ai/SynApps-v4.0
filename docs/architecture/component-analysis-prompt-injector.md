# Component Analysis: System Prompt Injector

## Current Implementation

The `SystemPromptInjector` is responsible for enhancing agent capabilities by injecting meta-prompts into the `system_prompt` field of `AppletMessage` objects before they are processed by agents. The current implementation:

1. Loads meta-prompt templates for different agent types
2. Injects system prompts based on node type and governance rules
3. Formats and includes output schemas for validation
4. Adds governance rules to system prompts

### Strengths

- **Template-based approach**: Uses predefined templates for different agent types
- **Schema integration**: Includes output schemas in prompts for structured responses
- **Governance integration**: Incorporates governance rules from the rule engine
- **Metadata tracking**: Records information about the prompt injection process

### Limitations

1. **Static templates**: Templates are hardcoded rather than being configurable
2. **Limited context awareness**: Doesn't consider the full workflow context
3. **No dynamic adaptation**: Doesn't adapt prompts based on previous interactions
4. **Limited agent specialization**: Basic agent type differentiation
5. **No versioning**: No support for prompt template versioning
6. **No A/B testing**: No capability to test different prompt variations

## Enhancement Opportunities

### 1. Dynamic Template Loading

Implement a configurable template system with database backing:

```python
class TemplateManager:
    def __init__(self, repository):
        self.repository = repository
        self.cache = {}
        self.cache_expiry = 300  # 5 minutes
        self.last_refresh = 0
        
    async def get_template(self, agent_type: str, version: str = "latest") -> str:
        # Check cache expiry
        if time.time() - self.last_refresh > self.cache_expiry:
            await self.refresh_cache()
            
        # Get from cache or fallback to default
        key = f"{agent_type}:{version}"
        return self.cache.get(key, self.cache.get("default:latest", ""))
        
    async def refresh_cache(self):
        templates = await self.repository.get_all_templates()
        self.cache = {f"{t.agent_type}:{t.version}": t.content for t in templates}
        self.last_refresh = time.time()
```

### 2. Context-Aware Prompting

Enhance the injector to consider workflow context:

```python
async def inject_system_prompt(self, 
                              node: WorkflowNode, 
                              message: AppletMessage,
                              workflow_id: str = None,
                              workflow_context: Dict[str, Any] = None) -> AppletMessage:
    # Get workflow context if not provided
    if workflow_id and not workflow_context:
        workflow_context = await self.context_provider.get_workflow_context(workflow_id)
        
    # Include relevant context in the prompt
    context_additions = self._format_workflow_context(workflow_context, node)
    
    # Rest of the injection logic
    # ...
    
    # Add context to the final prompt
    full_system_prompt = f"{base_prompt}\n\n{context_additions}\n\n{governance_additions}\n\n{schema_prompt}".strip()
    # ...
```

### 3. Adaptive Prompting

Implement adaptive prompting based on previous interactions:

```python
async def adapt_prompt_based_on_history(self, 
                                       node: WorkflowNode, 
                                       base_prompt: str,
                                       message_history: List[AppletMessage]) -> str:
    if not message_history:
        return base_prompt
        
    # Analyze previous interactions
    error_count = sum(1 for msg in message_history if msg.has_error())
    output_quality = self._assess_output_quality(message_history)
    
    # Adapt the prompt based on analysis
    adaptations = []
    
    if error_count > 2:
        adaptations.append("Please be especially careful with your response format. "
                          "Previous responses have had formatting errors.")
                          
    if output_quality < 0.7:  # Below threshold
        adaptations.append("Please provide more detailed and comprehensive responses. "
                          "Previous responses have been too brief or lacking detail.")
    
    # Add adaptations to the prompt
    if adaptations:
        return f"{base_prompt}\n\nADDITIONAL GUIDANCE:\n" + "\n".join(adaptations)
    
    return base_prompt
```

### 4. Enhanced Agent Specialization

Develop more specialized agent roles with tailored prompts:

```python
def get_specialized_prompt(self, node: WorkflowNode) -> str:
    # Extract specialization details
    agent_type = node.metadata.get("agent_type", "default")
    domain = node.metadata.get("domain", "general")
    expertise_level = node.metadata.get("expertise_level", "standard")
    tone = node.metadata.get("tone", "neutral")
    
    # Get specialized template
    template_key = f"{agent_type}:{domain}:{expertise_level}:{tone}"
    
    # Try to get specialized template, falling back to less specific ones
    template = (self.templates.get(template_key) or
                self.templates.get(f"{agent_type}:{domain}:{expertise_level}") or
                self.templates.get(f"{agent_type}:{domain}") or
                self.templates.get(agent_type) or
                self.templates.get("default"))
    
    return template
```

### 5. Prompt Template Versioning

Implement versioning for prompt templates:

```python
class VersionedTemplate:
    def __init__(self, agent_type: str, version: str, content: str, 
                 created_at: datetime, is_active: bool = True):
        self.agent_type = agent_type
        self.version = version
        self.content = content
        self.created_at = created_at
        self.is_active = is_active
        
class TemplateRepository:
    async def get_template(self, agent_type: str, version: str = None) -> VersionedTemplate:
        """Get a specific template version or the latest active one"""
        if version:
            return await self._get_specific_version(agent_type, version)
        else:
            return await self._get_latest_active(agent_type)
```

### 6. A/B Testing Support

Add support for A/B testing different prompt variations:

```python
class ABTestManager:
    def __init__(self, repository):
        self.repository = repository
        
    async def get_test_variant(self, test_id: str, entity_id: str) -> str:
        """Get a test variant based on test ID and entity ID"""
        # Deterministic assignment to ensure consistency
        test = await self.repository.get_test(test_id)
        if not test or not test.is_active:
            return None
            
        # Assign variant based on hash of entity_id
        variant_index = hash(entity_id) % len(test.variants)
        return test.variants[variant_index]
        
    async def record_result(self, test_id: str, entity_id: str, 
                           variant: str, metrics: Dict[str, Any]):
        """Record the result of a test variant"""
        await self.repository.save_test_result(test_id, entity_id, variant, metrics)
```

## Implementation Recommendations

1. **Modular Design**: Implement each enhancement as a separate module
2. **Configuration-Driven**: Make the system configurable via settings
3. **Metrics Collection**: Add metrics to track prompt effectiveness
4. **Gradual Rollout**: Implement features incrementally, starting with template loading
5. **Comprehensive Testing**: Add unit tests for each new feature

## Next Steps

1. Implement the `TemplateManager` for dynamic template loading
2. Add context awareness to the prompt injection process
3. Develop adaptive prompting based on interaction history
4. Enhance agent specialization with more detailed roles
5. Add versioning support for prompt templates
6. Implement A/B testing for prompt optimization
