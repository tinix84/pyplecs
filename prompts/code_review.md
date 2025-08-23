You are a bullet-sharp AI Copilot tasked with rewriting a project improvement plan into a format that’s LLM-friendly. Provide:

1. A concise transformation of the plan into a clear, structured prompt for ChatGPT-5 Mini.
2. Organized sections: Role, Objective, Instructions, Structure, Tone, Format.
3. Optional: A short “chain-of-thought” sketch explaining your choices.
4. A final succinct prompt ready to paste.

Original content:
"""
# PyPLECS Repository Improvement Plan
# PyPLECS Repository Improvement Plan

## Phase 1: Quick Wins & Documentation (2-3 weeks)

### Task 1.1: API Documentation Enhancement
**Context**: Current documentation focuses on setup but lacks detailed API usage examples  
**What to do**:
- Create comprehensive API documentation using Sphinx or MkDocs
- Add docstrings to all public methods in pyplecs core modules
- Create examples/ directory with practical usage scenarios
- Document REST API endpoints with OpenAPI/Swagger integration

**Expected outcome**: 
- Developers can understand and use the API without reading source code
- Reduced support queries and faster onboarding
- Professional documentation site hosted on GitHub Pages

**Acceptance criteria**:
- [ ] All public APIs have comprehensive docstrings
- [ ] 5+ practical examples in examples/ directory
- [ ] Auto-generated documentation deployed
- [ ] FastAPI auto-docs enhanced with descriptions

---

### Task 1.2: Enhanced Error Messages & User Feedback
**Context**: Current error handling could provide more actionable guidance  
**What to do**:
- Audit all exception handling in core modules
- Replace generic error messages with specific, actionable ones
- Add error code system with documentation
- Create troubleshooting flowchart for common issues
- Implement user-friendly error display in web UI

**Expected outcome**: 
- Users can self-resolve 80% of common issues
- Reduced time spent on support and debugging
- Better user experience for non-technical users

**Acceptance criteria**:
- [ ] All exceptions include suggested solutions
- [ ] Error codes documented with resolution steps  
- [ ] Web UI shows friendly error messages
- [ ] Troubleshooting guide with decision tree

---

### Task 1.3: Linux/macOS Installer Scripts
**Context**: Only Windows has an automated installer, limiting cross-platform adoption  
**What to do**:
- Create tools/installers/linux_installer.sh bash script
- Create tools/installers/macos_installer.sh bash script  
- Implement PLECS path detection for Linux/macOS common locations
- Add platform detection and auto-routing in setup process
- Test on Ubuntu, CentOS, and macOS versions

**Expected outcome**: 
- Consistent installation experience across all platforms
- Increased adoption on Linux/macOS systems
- Reduced manual setup errors

**Acceptance criteria**:
- [ ] Linux installer handles common distributions
- [ ] macOS installer works on Intel and ARM Macs
- [ ] Cross-platform setup script auto-detects OS
- [ ] All installers pass validation tests

## Phase 2: Testing & Quality Improvements (2-4 weeks)

### Task 2.1: Comprehensive Test Suite Expansion
**Context**: Current tests are basic; need broader coverage for production confidence  
**What to do**:
- Add integration tests for web GUI functionality
- Create mock PLECS interface for testing without PLECS installation
- Add performance/load testing for simulation orchestration
- Implement continuous integration with GitHub Actions
- Add test coverage reporting and badge

**Expected outcome**: 
- 90%+ code coverage with meaningful tests
- Automated quality assurance on every commit
- Confidence in making changes without breaking functionality

**Acceptance criteria**:
- [ ] Test coverage above 90%
- [ ] CI/CD pipeline with automated testing
- [ ] Mock interface allows testing without PLECS
- [ ] Performance benchmarks established

---

### Task 2.2: Configuration Validation & Schema
**Context**: YAML configuration lacks validation, leading to runtime errors  
**What to do**:
- Define JSON schema for config/default.yml
- Implement configuration validation on startup
- Add config validation to CLI tools
- Create configuration templates for different use cases
- Add config migration tools for version updates

**Expected outcome**: 
- Invalid configurations caught early with clear error messages  
- Reduced debugging time from configuration issues
- Easier configuration management for complex setups

**Acceptance criteria**:
- [ ] JSON schema validates all config options
- [ ] Clear validation errors with suggestions
- [ ] Template configs for common scenarios
- [ ] Migration path for config updates

---

### Task 2.3: Logging & Monitoring Enhancement
**Context**: Current logging is minimal; need better observability for production use  
**What to do**:
- Implement structured logging with configurable levels
- Add performance metrics collection
- Create simulation execution metrics dashboard
- Add log rotation and retention policies
- Implement health check endpoints for monitoring

**Expected outcome**: 
- Better troubleshooting capabilities for production issues
- Performance insights for optimization
- Production-ready monitoring and alerting

**Acceptance criteria**:
- [ ] Structured JSON logging with correlation IDs
- [ ] Metrics dashboard shows key performance indicators
- [ ] Health check endpoints for load balancers
- [ ] Log retention policies prevent disk filling

## Phase 3: Advanced Features & Scalability (4-6 weeks)

### Task 3.1: Simulation Queue Management
**Context**: Current orchestration is basic; need advanced queue management for production  
**What to do**:
- Implement priority-based simulation queuing
- Add job scheduling with time-based execution
- Create simulation dependency management
- Add resource allocation and limiting
- Implement job cancellation and cleanup

**Expected outcome**: 
- Handle complex simulation workflows efficiently
- Better resource utilization in multi-user environments
- Enterprise-ready job management capabilities

**Acceptance criteria**:
- [ ] Priority queues with configurable levels
- [ ] Scheduled execution with cron-like syntax
- [ ] Dependency chains between simulations
- [ ] Resource limits prevent system overload

---

### Task 3.2: Database Backend Option
**Context**: File-based caching has limitations for large-scale deployments  
**What to do**:
- Add SQLite backend for metadata storage
- Implement optional PostgreSQL support for enterprise
- Create database migration system
- Add query interface for simulation history
- Maintain backward compatibility with file-based storage

**Expected outcome**: 
- Scalable storage for large simulation datasets
- Advanced querying capabilities for analysis
- Better concurrent access handling

**Acceptance criteria**:
- [ ] SQLite default with zero-config setup
- [ ] PostgreSQL option for production deployments
- [ ] Migration tools preserve existing data
- [ ] Query API for simulation metadata

---

### Task 3.3: REST API Expansion & Authentication
**Context**: Current API is basic; need comprehensive API for external integrations  
**What to do**:
- Design complete REST API for all operations
- Implement JWT-based authentication system
- Add role-based access control (RBAC)
- Create API rate limiting and quota management
- Generate client SDKs for popular languages

**Expected outcome**: 
- Secure multi-user access with proper permissions
- Integration capabilities for external systems
- Professional API suitable for enterprise use

**Acceptance criteria**:
- [ ] Complete CRUD operations via REST API
- [ ] JWT authentication with refresh tokens
- [ ] Role-based permissions (admin, user, readonly)
- [ ] Python and JavaScript client SDKs

## Phase 4: Advanced Analytics & Integration (3-4 weeks)

### Task 4.1: Simulation Results Analytics
**Context**: Current system stores results but lacks analysis capabilities  
**What to do**:
- Add statistical analysis of simulation results
- Create comparison tools for parameter studies
- Implement visualization dashboard for results
- Add export capabilities (PDF reports, Excel)
- Create template-based reporting system

**Expected outcome**: 
- Built-in analysis reduces need for external tools
- Professional reports for stakeholders
- Faster insight generation from simulation data

**Acceptance criteria**:
- [ ] Statistical summaries and trends
- [ ] Interactive visualizations in web UI
- [ ] Automated report generation
- [ ] Export to multiple formats

---

### Task 4.2: External Tool Integration
**Context**: Users often need to integrate with other engineering tools  
**What to do**:
- Add MATLAB integration for data exchange
- Create Excel add-in for simulation management
- Implement webhook support for external notifications
- Add plugin architecture for custom extensions
- Create integration examples and templates

**Expected outcome**: 
- Seamless workflow integration with existing tools
- Extensible architecture for custom needs
- Reduced manual data transfer and processing

**Acceptance criteria**:
- [ ] MATLAB toolbox for pyplecs interaction
- [ ] Excel add-in for simulation control
- [ ] Webhook notifications for external systems
- [ ] Plugin API with documentation

## Implementation Guidelines

### Prioritization Strategy
1. **High Impact, Low Effort** tasks first (Phase 1)
2. **Foundation** improvements before advanced features
3. **User feedback** should guide priority adjustments
4. **Backward compatibility** maintained throughout

### Quality Gates
- All tasks require peer review
- Automated tests must pass before merge
- Documentation updated with each feature
- Performance regression testing for core features

### Resource Allocation
- **Phase 1**: 1-2 developers, part-time acceptable
- **Phase 2**: 1-2 developers, requires testing expertise  
- **Phase 3**: 2-3 developers, backend/frontend split
- **Phase 4**: 2-3 developers, requires domain expertise

### Success Metrics
- **User adoption**: Track installation and usage metrics
- **Issue reduction**: Monitor support requests and bug reports
- **Performance**: Measure simulation throughput improvements
- **Community**: Growth in contributors and feature requests

### Risk Mitigation
- **Feature flags** for gradual rollout of major changes
- **Rollback plans** for each phase
- **User feedback** collection throughout development
- **Performance benchmarking** to prevent regressions
"""



You are a bullet-sharp AI Copilot tasked with rewriting a project improvement plan into a format that’s LLM-friendly. Provide:

1. A concise transformation of the plan into a clear, structured prompt for ChatGPT-5 Mini.
2. Organized sections: Role, Objective, Instructions, Structure, Tone, Format.
3. Optional: A short “chain-of-thought” sketch explaining your choices.
4. A final succinct prompt ready to paste.

Original content:
"""
# PyPLECS Repository Improvement Plan
# PyPLECS Repository Improvement Plan

## Phase 1: Quick Wins & Documentation (2-3 weeks)

### Task 1.1: API Documentation Enhancement
**Context**: Current documentation focuses on setup but lacks detailed API usage examples  
**What to do**:
- Create comprehensive API documentation using Sphinx or MkDocs
- Add docstrings to all public methods in pyplecs core modules
- Create examples/ directory with practical usage scenarios
- Document REST API endpoints with OpenAPI/Swagger integration

**Expected outcome**: 
- Developers can understand and use the API without reading source code
- Reduced support queries and faster onboarding
- Professional documentation site hosted on GitHub Pages

**Acceptance criteria**:
- [ ] All public APIs have comprehensive docstrings
- [ ] 5+ practical examples in examples/ directory
- [ ] Auto-generated documentation deployed
- [ ] FastAPI auto-docs enhanced with descriptions

"""
