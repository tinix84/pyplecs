# Explanation of Each Directory
core
Purpose: Contains core business logic for simulations, models, and server orchestration.
Files to Create:
models.py: Define PLECSModel, SimulationResult, and related classes.
applications.py: Implement PLECSApp hierarchy for GUI and XRPC communication.
simulations.py: Manage simulation execution and plans.
server.py: Handle server orchestration and lifecycle management.
Existing Code to Move:
Classes from models.py and plecs_components.py.
Simulation logic from pyplecs/core/simulations.py.
Dependencies:
ConfigManager for configuration.
CacheBackend for caching simulation results.
pyplecs/web/
Purpose: FastAPI integration for REST API and WebSocket handlers.
Files to Create:
main.py: FastAPI app setup.
routes/: Modularized API route files.
simulations.py: Simulation-related endpoints.
models.py: Model management endpoints.
dashboard.py: Dashboard and monitoring endpoints.
schemas.py: Pydantic models for request/response validation.
websockets.py: WebSocket handlers for real-time updates.
Existing Code to Move:
FastAPI routes from integrate_with_fastapi.py.
Dependencies:
PLECSServer for simulation orchestration.
SimulationRequest and SimulationResult for API models.
pyplecs/mcp/
Purpose: MCP (Model Context Protocol) integration.
Files to Create:
server.py: MCP server implementation.
handlers.py: Tool and resource handlers.
Existing Code to Move:
MCP-related logic from models.py.
Dependencies:
PLECSServer for simulation orchestration.
cli
Purpose: CLI tools for managing PyPLECS.
Files to Keep:
Existing CLI scripts (e.g., installer.py).
pyplecs/config/
Purpose: Configuration management.
Files to Keep:
config.py: Centralized configuration manager.
Dependencies:
ConfigManager for loading and validating configurations.
pyplecs/utils/
Purpose: Utilities and helper functions.
Files to Keep:
General-purpose utility scripts.
tests
Purpose: Test files for unit, integration, and compatibility testing.
Files to Create:
unit/: Unit tests for core classes.
integration/: Integration tests for FastAPI and MCP.
compatibility/: Backward compatibility tests.
Existing Code to Move:
Test files from tests.
config
Purpose: Configuration files.
Files to Keep:
default.yml: Default configuration.
tools
Purpose: Build and deployment tools.
Files to Keep:
Installer scripts (e.g., windows_installer.ps1).