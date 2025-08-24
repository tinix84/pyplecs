# PyPLECS Object-Oriented Migration Plan

## Overview
This plan will help you systematically migrate PyPLECS from its current structure to a clean object-oriented architecture with proper separation of concerns for FastAPI and MCP integration.

## Prerequisites
1. **Backup your current code**: `git commit -am "Backup before OOP refactoring"`
2. **Create feature branch**: `git checkout -b feature/oop-refactoring`
3. **Document current API endpoints**: List all existing FastAPI routes and their functionality

---

## Phase 1: Analysis and Core Structure Setup

### Step 1.1: Current Code Analysis

**LLM Command:**
```
Analyze the current PyPLECS codebase structure. I need you to:

1. **Examine the main files and identify:**
   - All classes currently defined
   - All functions that could become methods
   - Dependencies between different parts
   - FastAPI route definitions and their logic

2. **Create a current architecture map:**
   - List all Python files and their main responsibilities  
   - Identify which code handles: PLECS interface, web API, simulation logic, configuration
   - Note any code duplication or tightly coupled components

3. **Generate a compatibility matrix:**
   - Which existing functions can be preserved as-is
   - Which functions need refactoring to fit the new object model
   - Which FastAPI routes need updating

Please provide this analysis in a structured format with specific file names and line numbers where possible.
```

### Step 1.2: Create New Directory Structure

**LLM Command:**
```
Based on the current PyPLECS structure, help me create a new directory organization. Generate the complete folder structure and explain what goes where:

```
pyplecs/
├── pyplecs/
│   ├── __init__.py
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── models.py           # PLECSModel, SimulationResult classes
│   │   ├── applications.py     # PLECSApp hierarchy
│   │   ├── simulations.py      # PLECSSimulation, SimulationPlan
│   │   └── server.py           # PLECSServer orchestration
│   ├── web/                     # FastAPI integration
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app setup
│   │   ├── routes/             # API route modules
│   │   │   ├── __init__.py
│   │   │   ├── simulations.py
│   │   │   ├── models.py
│   │   │   └── dashboard.py
│   │   ├── schemas.py          # Pydantic models
│   │   └── websockets.py       # WebSocket handlers
│   ├── mcp/                     # MCP integration
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── handlers.py
│   ├── cli/                     # CLI tools (keep existing)
│   ├── config/                  # Configuration management
│   └── utils/                   # Utilities and helpers
├── tests/                       # Test files
├── config/                      # Configuration files
└── tools/                       # Build and deployment tools
```

For each directory, specify:
1. What files to create initially
2. What existing code should move there
3. Import statements needed
4. Dependencies between modules
```

---

## Phase 2: Core Classes Implementation

### Step 2.1: Create Base Models and Enums

**LLM Command:**
```
Create the foundational classes for PyPLECS. I need you to implement:

**File: `pyplecs/core/models.py`**

1. **Implement these enums and dataclasses:**
   ```python
   # Copy the SimulationStatus, SimulationType enums from my architecture proposal
   # Copy the SimulationResult dataclass
   ```

2. **Implement PLECSModel class:**
   - Analyze my current model-related code in [provide your current file path]
   - Extract the existing property methods and functionality
   - Add the new methods: set_variables(), get_model_vars_opts()
   - Ensure backward compatibility with existing code
   - Add proper type hints and docstrings

3. **Add validation and error handling:**
   - File existence checking
   - Path validation
   - Variable type conversion with error handling

The class should be a drop-in replacement for existing model functionality while adding the new object-oriented interface.
```

### Step 2.2: Create Application Interface Classes

**LLM Command:**
```
Create the PLECS application interface classes in `pyplecs/core/applications.py`.

**Requirements:**
1. **Analyze existing PLECS interaction code** in my current codebase to understand:
   - How PLECS GUI is currently launched
   - How XRPC server communication works
   - What process management is currently implemented
   - Error handling patterns

2. **Implement the PLECSApp hierarchy:**
   ```python
   # Implement PLECSApp abstract base class
   # Implement PLECSGUIApp with current GUI launch logic
   # Implement PLECSXRPCApp with current XRPC communication
   ```

3. **Migration strategy:**
   - Each concrete class should wrap existing functions initially
   - Preserve all current functionality
   - Add async support where beneficial
   - Include proper resource cleanup

4. **Testing hooks:**
   - Add methods that can be easily mocked for testing
   - Include connection validation
   - Add health check methods

Please analyze my current PLECS interaction code and show me exactly how to migrate it to these new classes.
```

### Step 2.3: Create Simulation Management Classes

**LLM Command:**
```
Implement the simulation orchestration layer in `pyplecs/core/simulations.py`.

**Tasks:**
1. **Analyze current simulation logic:**
   - Look at my existing test files (test_basic.py, etc.)
   - Identify patterns in sequential vs parallel execution
   - Extract parameter sweep logic
   - Find callback/progress reporting mechanisms

2. **Implement PLECSSimulation class:**
   - Wrap individual simulation execution
   - Add status tracking with callbacks
   - Include timeout and cancellation support
   - Maintain compatibility with existing simulation functions

3. **Implement SimulationPlan class:**
   - Handle batch operations
   - Parameter sweep generation
   - Resource allocation planning
   - Execution scheduling

4. **Create migration helpers:**
   - Functions to convert existing simulation calls to new objects
   - Backward compatibility wrappers
   - Progress reporting integration

Show me specific code examples of how to migrate my current simulation functions to use these new classes.
```

### Step 2.4: Create Server Orchestration

**LLM Command:**
```
Implement the main server orchestration in `pyplecs/core/server.py`.

**Requirements:**
1. **Analyze current application lifecycle:**
   - How is PLECS currently started/stopped?
   - What configuration loading exists?
   - How are multiple PLECS instances managed?

2. **Implement PLECSServer class:**
   - Application registry and lifecycle management
   - Configuration integration with existing config/default.yml
   - Simulation queue and execution management
   - Cache system integration (preserve existing cache logic)

3. **Preserve existing functionality:**
   - All current PLECS executable detection
   - Configuration validation
   - Logging integration
   - Error handling patterns

4. **Add new capabilities:**
   - Health monitoring
   - Resource management
   - Graceful shutdown
   - Multi-instance coordination

Please show me how to integrate this with my existing configuration system and startup logic.
```

---

## Phase 3: FastAPI Integration Refactoring

### Step 3.1: Create Pydantic Schemas

**LLM Command:**
```
Create modern Pydantic schemas for the FastAPI integration in `pyplecs/web/schemas.py`.

**Tasks:**
1. **Analyze current API:**
   - List all existing FastAPI endpoints and their input/output
   - Identify request/response patterns
   - Document current validation logic

2. **Create comprehensive schemas:**
   ```python
   # Request schemas for all current endpoints
   # Response schemas with proper typing
   # Error response schemas
   # WebSocket message schemas
   ```

3. **Migration compatibility:**
   - Ensure new schemas accept all current request formats
   - Add proper validation with helpful error messages
   - Include backward compatibility for any API changes

4. **Advanced features:**
   - Add OpenAPI documentation strings
   - Include example values
   - Add custom validators where needed

Please analyze my current FastAPI routes and create schemas that match the existing API while preparing for the new object structure.
```

### Step 3.2: Refactor FastAPI Routes

**LLM Command:**
```
Refactor the FastAPI routes to use the new object-oriented structure.

**Process:**
1. **Analyze current routes:**
   - [Provide your current FastAPI route file]
   - Document all endpoints, their logic, and dependencies
   - Identify shared code that can be moved to the core classes

2. **Create route modules:**
   - `pyplecs/web/routes/simulations.py` - All simulation-related endpoints
   - `pyplecs/web/routes/models.py` - Model management endpoints  
   - `pyplecs/web/routes/dashboard.py` - Dashboard and monitoring

3. **Refactoring strategy:**
   - Each route should be a thin wrapper around core business logic
   - Move complex logic to the appropriate core classes
   - Preserve all existing endpoint URLs and behavior
   - Add proper dependency injection for PLECSServer instance

4. **Example transformation:**
   ```python
   # Show me how to transform this existing route:
   @app.post("/simulate")
   async def simulate(request_data):
       # [my current simulation logic]
   
   # Into this new structure:
   @router.post("/simulate") 
   async def simulate(request: SimulationRequest, server: PLECSServer = Depends()):
       # Clean, object-oriented implementation
   ```

Please provide specific code showing the before/after transformation for each of my current routes.
```

### Step 3.3: WebSocket Integration

**LLM Command:**
```
Upgrade the WebSocket functionality to use the new callback system.

**Requirements:**
1. **Analyze current WebSocket implementation:**
   - [Provide current WebSocket code if any]
   - Identify real-time update requirements
   - Document current client-server communication patterns

2. **Implement enhanced WebSocket handler:**
   - Integration with PLECSSimulation callback system
   - Real-time status updates
   - Error handling and reconnection logic
   - Multiple client support

3. **Create WebSocket message protocol:**
   - Standardized message formats
   - Client command handling (cancel, pause, resume)
   - Batch operation progress updates
   - Connection management

4. **Migration plan:**
   - Preserve existing WebSocket endpoints
   - Add new real-time features
   - Maintain backward compatibility

Show me how to integrate WebSocket updates with the new PLECSSimulation callback system.
```

---

## Phase 4: MCP Integration

### Step 4.1: MCP Server Implementation

**LLM Command:**
```
Implement MCP (Model Context Protocol) integration for PyPLECS.

**Tasks:**
1. **Research current MCP standards:**
   - What MCP protocols should we support?
   - What are the standard tool and resource patterns?
   - How should PLECS simulations be exposed via MCP?

2. **Implement MCP server classes:**
   - `pyplecs/mcp/server.py` - Main MCP server
   - `pyplecs/mcp/handlers.py` - Tool and resource handlers
   - Integration with existing PLECSServer

3. **Define MCP tools:**
   - Simulation execution tools
   - Model management tools  
   - Result retrieval tools
   - Parameter sweep tools

4. **Define MCP resources:**
   - Model file access
   - Simulation results
   - Execution logs
   - Configuration data

5. **Integration strategy:**
   - How to expose MCP alongside FastAPI
   - Configuration for enabling/disabling MCP
   - Authentication and security considerations

Please implement a complete MCP integration that exposes PLECS functionality to MCP clients.
```

---

## Phase 5: Migration and Testing

### Step 5.1: Create Migration Scripts

**LLM Command:**
```
Create migration utilities to help transition from old to new structure.

**Requirements:**
1. **Backward compatibility layer:**
   ```python
   # File: pyplecs/compatibility.py
   # Create wrapper functions that maintain old API while using new classes
   # Ensure existing code continues to work without changes
   ```

2. **Migration helpers:**
   - Functions to convert old configuration formats
   - Scripts to update existing model references
   - Database migration if any persistent data exists

3. **Gradual migration support:**
   - Allow old and new code to coexist during transition
   - Provide deprecation warnings for old patterns
   - Clear upgrade path documentation

4. **Validation tools:**
   - Scripts to verify migration correctness
   - Automated testing of backward compatibility
   - Performance comparison tools

Show me specific migration scripts and compatibility layers for my codebase.
```

### Step 5.2: Comprehensive Testing Strategy

**LLM Command:**
```
Create a comprehensive testing strategy for the refactored codebase.

**Testing Requirements:**
1. **Unit tests for core classes:**
   - PLECSModel functionality
   - PLECSApp implementations  
   - Simulation orchestration
   - Server lifecycle management

2. **Integration tests:**
   - FastAPI endpoint testing
   - WebSocket communication testing
   - MCP protocol testing
   - End-to-end simulation workflows

3. **Compatibility tests:**
   - Verify all existing functionality still works
   - Test migration scripts
   - Validate configuration compatibility
   - Check performance characteristics

4. **Mock strategies:**
   - Mock PLECS executable for CI/CD
   - Mock file system interactions
   - Mock network communication
   - Database mocking if applicable

5. **Test structure:**
   ```
   tests/
   ├── unit/
   │   ├── test_models.py
   │   ├── test_applications.py
   │   ├── test_simulations.py
   │   └── test_server.py
   ├── integration/
   │   ├── test_fastapi_routes.py
   │   ├── test_websockets.py
   │   └── test_mcp.py
   ├── compatibility/
   │   └── test_backward_compatibility.py
   └── fixtures/
       ├── mock_models/
       └── test_configs/
   ```

Please analyze my current test_basic.py and other test files, then create a comprehensive test suite that covers both new functionality and ensures backward compatibility.
```

### Step 5.3: Documentation and Deployment

**LLM Command:**
```
Create updated documentation and deployment procedures.

**Documentation Tasks:**
1. **API documentation:**
   - Update FastAPI OpenAPI schemas
   - Document new object-oriented interfaces
   - Provide migration guides for existing users

2. **Architecture documentation:**
   - System design overview
   - Class relationship diagrams
   - Interaction patterns
   - Extension points for future development

3. **Deployment guides:**
   - Updated installation procedures
   - Configuration migration steps
   - Troubleshooting guides
   - Performance tuning recommendations

4. **Developer documentation:**
   - Contributing guidelines for new structure
   - Code style and patterns
   - Testing procedures
   - Release process updates

Please create comprehensive documentation that helps both users and developers understand the new architecture and migration process.
```

---

## Execution Timeline

### Week 1: Foundation
- Execute Phase 1 & 2 LLM commands
- Set up new directory structure
- Implement core classes
- Create basic tests

### Week 2: Web Integration  
- Execute Phase 3 LLM commands
- Refactor FastAPI routes
- Update WebSocket functionality
- Comprehensive testing

### Week 3: MCP and Polish
- Execute Phase 4 & 5 LLM commands  
- Implement MCP integration
- Create migration tools
- Documentation updates

### Week 4: Validation and Release
- End-to-end testing
- Performance validation
- Migration testing
- Release preparation

---

## LLM Command Template

When working with an LLM, use this template for each command:

```
**Context:** I'm refactoring PyPLECS to use object-oriented architecture for better FastAPI and MCP integration.

**Current State:** [Describe what you've completed so far]

**Task:** [Specific LLM command from above]

**Constraints:**
- Maintain backward compatibility with existing API
- Preserve all current functionality  
- Follow Python best practices and type hints
- Include comprehensive error handling
- Add proper logging integration

**Expected Output:**
- Complete, working code files
- Explanation of changes made
- Migration notes for existing code
- Test cases for new functionality

**Files to Consider:** [List relevant current files]
```

---

## Success Criteria

✅ **All existing functionality preserved**  
✅ **FastAPI routes are clean and maintainable**  
✅ **MCP integration works seamlessly**  
✅ **Comprehensive test coverage**  
✅ **Clear upgrade path for users**  
✅ **Performance maintained or improved**  
✅ **Code is more maintainable and extensible**

This plan gives you a systematic approach to migrate PyPLECS while leveraging LLM assistance for each phase. Each command is specific enough to get actionable code while maintaining the overall architecture vision.