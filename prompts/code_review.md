You are a bullet-sharp AI Copilot tasked with rewriting a project improvement plan into a format that’s LLM-friendly. Provide:

1. A concise transformation of the plan into a clear, structured prompt for ChatGPT-5 Mini.
2. Organized sections: Role, Objective, Instructions, Structure, Tone, Format.
3. Optional: A short “chain-of-thought” sketch explaining your choices.
4. A final succinct prompt ready to paste.

Original content:
"""
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


Task received — I will produce an executable Phase 1 → Task 1.1 plan: short summary, prioritized checklist, 4–6 concrete subtasks (with steps, files, commands, docstring template, acceptance checks and time estimates), docs/examples layout, a GitHub Actions job to auto-build & deploy docs, and quick local verification commands.

High-level plan

Use Sphinx (good Python + autodoc integration) to generate API docs, add consistent Google-style docstrings across core modules, create 5+ runnable examples in examples/, improve FastAPI endpoint docs, and wire a CI job to auto-build and publish to GitHub Pages.
Prioritized checklist (deliverables)

 Choose & configure Sphinx in docs
 Add Google-style docstrings to all public functions/classes in pyplecs/*
 Create examples/ with 5+ practical scripts + README
 Enhance FastAPI route docstrings/response_model/examples
 CI job to build and deploy docs to GitHub Pages
 Docstring/lint checks (pydocstyle / sphinx-build) in CI
Subtasks (S1..S5)

S1 — Initialize Sphinx docs and basic toolchain

Purpose: Bootstraps documentation site, autodoc & napoleon for Google/NumPy style.
Steps:
Add docs dependencies: Sphinx, sphinx-autobuild (optional), sphinx-rtd-theme (or pydata-sphinx-theme), sphinx.ext.napoleon, sphinx.ext.autodoc, sphinx_autodoc_typehints.
Run sphinx-quickstart in docs and enable extensions in docs/conf.py.
Generate autodoc stubs with sphinx-apidoc for pyplecs package.
Add docs/index.rst linking API docs and examples.
Files to create/edit:
docs (folder)
docs/conf.py (configure extensions, path)
docs/index.rst (home)
docs/api/pyplecs.rst (via sphinx-apidoc)
Commands (run in repo root; use PowerShell or bash)
Acceptance criteria:
 docs/_build/html/index.html builds without errors.
 autodoc pages for pyplecs appear under docs/_build/html.
Time estimate: 1.5–3 hours

S2 — Add consistent Google-style docstrings to public APIs

Purpose: Make API discoverable via autodoc and improve developer UX.
Steps:
Adopt Google-style docstring template (see template below).
Audit public symbols in pyplecs.py, config.py, exceptions.py.
Add docstrings for public classes, functions, and methods. Mark private/internal with leading underscore and exclude them from docs or hide with :noindex: when needed.
Add pydocstyle config and run checks locally.
Files to edit:
pyplecs.py
config.py
exceptions.py
Add pyproject.toml or .pydocstyle config if missing
Docstring template (Google style)
Commands
Acceptance criteria:
 All public classes/functions have non-empty docstrings.
 pydocstyle reports zero violations for configured rules.
Time estimate: 4–12 hours (depends on codebase size; estimate ~1 dev-day)

S3 — Create examples/ with 5+ practical scripts and docs

Purpose: Provide copy/paste examples that demonstrate common workflows and make docs actionable.
Steps:
Create examples/ top-level folder.
Add at least five example scripts (see suggestions below) with if __name__ == "__main__" and small README.md per example.
Link examples from docs (docs/examples.rst).
Files to create:
examples/README.md
examples/simple_simulation.py
examples/parameter_sweep.py
examples/load_model_and_set_vars.py
examples/run_headless_sim.py
examples/integrate_with_fastapi.py
Example examples/simple_simulation.py stub
Acceptance criteria:
 5 scripts present and runnable
 Each script documented in examples/README.md
 Links to examples from docs (examples page)
Time estimate: 4–8 hours

S4 — Improve FastAPI endpoint docs and OpenAPI wiring

Purpose: Ensure the web GUI API shows helpful descriptions/examples in FastAPI auto-docs.
Steps:
Add summary, description, response_model, and examples to route decorators in webgui.py (or proper path).
Add Pydantic models for request/response with field docstrings and example values.
Re-generate OpenAPI schema (FastAPI exposes /openapi.json) and ensure description fields show up.
Link FastAPI docs into Sphinx (either embed or link to hosted OpenAPI).
Files to edit:
webgui.py
pyplecs/api/models.py (new file if models don't exist)
Minimal change example (FastAPI)
Acceptance criteria:
 Swagger UI (docs) shows summary/description/examples for key endpoints
 /openapi.json includes descriptions
Time estimate: 2–6 hours

S5 — CI: Build, test doc generation, and deploy to GitHub Pages

Purpose: Auto-build docs and publish to gh-pages on merge to main (or dev branch chosen).
Steps:
Add GitHub Actions workflow .github/workflows/docs.yml that:
Installs dependencies
Builds docs with sphinx-build
Uses peaceiris/actions-gh-pages (or crazy-max/ghaction alternative) to publish docs/_build/html to gh-pages
Add badge to README.
Files to create:
.github/workflows/docs.yml
CI job (paste-ready YAML)
Acceptance criteria:
 Workflow runs on push and deploys HTML to gh-pages.
 README contains docs badge with link.
Time estimate: 1–2 hours
Repository layout (recommended)

Quick verification commands (run locally)

Machine-friendly acceptance checklist (YAML-ish)

Short justification for choosing Sphinx

Sphinx is the defacto Python documentation system with mature autodoc, napoleon (Google/NumPy style), type-hint integration, and many themes. It integrates easily into CI pipelines and supports fine-grained control over API pages (recommended for library-style docs).
Minimal follow-ups / next steps for maintainers

Pick final theme (sphinx-rtd-theme or pydata-sphinx-theme).
Decide branch for publishing (main vs dev).
Run S1 locally and commit docs config and examples/.
Start S2 docstring updates in priority order (core helpers → public API → webgui).
Concise time budget estimate

S1: 1.5–3 hrs
S2: 4–12 hrs (approx 1 dev-day)
S3: 4–8 hrs
S4: 2–6 hrs
S5: 1–2 hrs Total Phase 1 estimate: ~2–4 working days (1–2 devs, part-time)
If you want, I can now:

Generate the exact docs/conf.py snippet configured for this repo,
Draft the 5 example scripts,
Create the initial docs/index.rst and examples/README.md,
Or create the .github/workflows/docs.yml file in the repo.
Which of those follow-ups should I do next?