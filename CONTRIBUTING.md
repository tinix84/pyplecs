# Contributing to PyPLECS

Thank you for considering contributing to PyPLECS! 🎉

This guide will help you get started with development, understand the codebase architecture, and contribute effectively.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes**:
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Violations of the code of conduct may be reported to tinix84@gmail.com. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Development Setup

#### 1. Fork and Clone

```bash
# Fork on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/pyplecs.git
cd pyplecs

# Add upstream remote
git remote add upstream https://github.com/tinix84/pyplecs.git
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

#### 3. Install Dependencies

```bash
# Install package in editable mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Install optional dependencies for full features
pip install -r requirements.txt
```

#### 4. Verify Installation

```bash
# Run tests to verify setup
pytest

# Check code formatting
black --check pyplecs/
flake8 pyplecs/

# Verify import works
python -c "import pyplecs; print(pyplecs.__version__)"
```

#### 5. Configure PLECS

```bash
# Run setup wizard
pyplecs-setup

# Or manually create config/default.yml
```

---

## Architecture Overview

PyPLECS is structured in two layers:

### Core Layer

**`pyplecs/pyplecs.py`** (~150 lines):
- Thin wrapper around PLECS XML-RPC and GUI automation
- `PlecsServer` class: XML-RPC client for remote simulations
- `PlecsApp` class: Windows GUI automation via pywinauto
- Batch parallel API: `simulate_batch()` leverages PLECS native parallelization

**Design principle**: Minimal abstraction over PLECS. Let PLECS do what PLECS does best.

### Value-Add Layer

Modern features that make PLECS scalable:

**`orchestration/`** (~280 lines):
- `SimulationOrchestrator`: Task queue with priority levels
- `TaskPriority`: CRITICAL/HIGH/NORMAL/LOW enum
- `SimulationTask`: Task representation with status tracking
- Batch execution grouping for optimal performance
- Retry logic with exponential backoff

**`cache/`**:
- `SimulationCache`: Hash-based result caching
- `CacheBackend`: Storage abstraction (File/Redis/Memory)
- SHA256 hashing of model + parameters
- Parquet/HDF5/CSV storage formats

**`api/`**:
- FastAPI REST endpoints
- OpenAPI automatic documentation
- WebSocket for real-time updates

**`webgui/`**:
- Web monitoring interface
- Jinja2 templates
- Real-time dashboard

**`core/models.py`**:
- Pydantic data models
- `SimulationRequest`, `SimulationResult`, `CacheEntry`

### Key Design Decisions

1. **Thin core, rich value-add**: Don't duplicate PLECS functionality
2. **Leverage native capabilities**: Use PLECS batch API instead of Python threading
3. **Explicit is better than implicit**: No magic, clear data flow
4. **Optional dependencies**: Core works without web/cache/GUI features

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

---

## Development Workflow

### 1. Create Feature Branch

```bash
# Update your fork
git fetch upstream
git checkout dev
git merge upstream/dev

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Make Changes

Follow these guidelines:

#### Code Organization
- Keep functions small and focused (single responsibility)
- Use type hints for all function signatures
- Add docstrings to public functions and classes
- Extract magic numbers to named constants
- Prefer composition over inheritance

#### Error Handling
- Use specific exception types (not bare `except:`)
- Provide actionable error messages
- Log errors with context (structured logging)
- Fail fast, fail explicitly

#### Performance
- Profile before optimizing
- Use built-in functions when possible
- Avoid premature optimization
- Document performance trade-offs

### 3. Write Tests

**All new features must have tests**. PyPLECS uses pytest.

#### Test Structure

```python
# tests/test_feature.py
import pytest
from pyplecs import PlecsServer

class TestFeature:
    """Test suite for new feature."""

    def test_basic_functionality(self):
        """Test basic use case."""
        # Arrange
        server = PlecsServer("model.plecs")

        # Act
        result = server.new_feature()

        # Assert
        assert result is not None

    def test_edge_case_handling(self):
        """Test edge cases."""
        # Test boundary conditions, error cases
        pass

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_parameterized(self, input, expected):
        """Test with multiple inputs."""
        assert input * 2 == expected
```

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_feature.py -v

# Run specific test
pytest tests/test_feature.py::TestFeature::test_basic_functionality -v

# Run with coverage
pytest --cov=pyplecs tests/

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

#### Test Categories

Mark tests appropriately:

```python
@pytest.mark.slow  # Long-running tests
@pytest.mark.integration  # Requires PLECS running
@pytest.mark.unit  # Fast, isolated tests
```

### 4. Update Documentation

Update relevant documentation:

- **Docstrings**: All public functions/classes
- **README.md**: New features, usage examples
- **MIGRATION.md**: Breaking changes
- **CHANGELOG.md**: Version history
- **CLAUDE.md**: Architecture changes

### 5. Format and Lint

```bash
# Format code with black
black pyplecs/

# Sort imports with isort
isort pyplecs/

# Lint with flake8
flake8 pyplecs/

# Type check with mypy
mypy pyplecs/

# Or run all checks
./scripts/check_code.sh  # If available
```

---

## Testing

### Test Organization

```
tests/
├── test_basic.py              # Legacy tests (GUI automation, XML-RPC)
├── test_refactored.py         # Modern architecture tests
├── test_plecs_server_refactored.py  # Core batch API tests
├── test_orchestrator_batch.py  # Batch orchestration tests
├── benchmark_batch_speedup.py  # Performance benchmarks
└── fixtures/                  # Test data and fixtures
```

### Test Requirements

**Unit Tests**:
- Fast (<100ms per test)
- No external dependencies (PLECS, network)
- Use mocks/stubs for isolation
- High code coverage (>80%)

**Integration Tests**:
- Require PLECS running with XML-RPC enabled
- Test real simulation workflows
- Mark with `@pytest.mark.integration`
- Run in CI with PLECS mock/stub

**Benchmark Tests**:
- Validate performance claims (5x speedup, etc.)
- Run manually before releases
- Document results in CHANGELOG.md

### Writing Good Tests

#### Do
- ✅ Test behavior, not implementation
- ✅ Use descriptive test names
- ✅ Follow Arrange-Act-Assert pattern
- ✅ Test edge cases and error conditions
- ✅ Keep tests independent (no shared state)
- ✅ Use fixtures for common setup

#### Don't
- ❌ Test private methods directly
- ❌ Use time.sleep() (use proper async testing)
- ❌ Hardcode paths or values
- ❌ Ignore flaky tests (fix or mark as known issue)
- ❌ Skip writing tests (required for PR approval)

### Code Coverage

Maintain >80% test coverage:

```bash
# Generate coverage report
pytest --cov=pyplecs --cov-report=html tests/

# View in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## Code Style

PyPLECS follows **PEP 8** with some customizations.

### Style Guidelines

#### Line Length
- **100 characters** maximum (vs PEP 8's 79)
- Break long lines logically

#### Formatting
```python
# Use black for auto-formatting
black pyplecs/

# Configuration in pyproject.toml
[tool.black]
line-length = 100
target-version = ['py38']
```

#### Imports
```python
# Order: stdlib → third-party → local
import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI

from pyplecs import PlecsServer
from pyplecs.cache import SimulationCache

# Sort with isort
isort pyplecs/
```

#### Type Hints
```python
from typing import List, Dict, Optional, Union
from pathlib import Path

def simulate_batch(
    self,
    params_list: List[Dict[str, float]],
    timeout: Optional[int] = None
) -> List[Dict[str, np.ndarray]]:
    """
    Run batch simulations with PLECS native parallelization.

    Args:
        params_list: List of parameter dictionaries
        timeout: Optional timeout in seconds

    Returns:
        List of result dictionaries

    Raises:
        TimeoutError: If simulation exceeds timeout
        ValueError: If params_list is empty
    """
    if not params_list:
        raise ValueError("params_list cannot be empty")
    # ...
```

#### Docstrings
Use Google-style docstrings:

```python
def function(arg1: str, arg2: int = 0) -> bool:
    """
    Short one-line summary.

    Longer description if needed. Explain purpose, behavior,
    and important details.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (default: 0)

    Returns:
        Description of return value

    Raises:
        ValueError: When arg2 is negative
        TypeError: When arg1 is not a string

    Example:
        >>> function("test", 42)
        True
    """
    pass
```

#### Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- `_leading_underscore` for private methods
- Descriptive names (avoid abbreviations unless common)

```python
# Good
def calculate_simulation_hash(model_file: Path, parameters: dict) -> str:
    MAX_RETRIES = 3
    cache_key = f"{model_file.stem}_{hash(parameters)}"
    return cache_key

# Bad
def calc_sim_h(m: str, p: dict) -> str:
    r = 3
    k = f"{m}_{p}"
    return k
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring (no feature/fix)
- `perf`: Performance improvement
- `test`: Add or update tests
- `chore`: Maintenance (deps, build, etc.)
- `ci`: CI/CD changes

### Examples

```bash
# Feature
git commit -m "feat(api): add batch simulation endpoint

Implement POST /simulations/batch for submitting multiple
simulations in one API call. Orchestrator batches them for
parallel execution via PLECS batch API.

Closes #123"

# Bug fix
git commit -m "fix(cache): resolve hash collision on similar parameters

Use JSON canonical serialization instead of str() for hashing
simulation parameters to avoid hash collisions.

Fixes #456"

# Breaking change
git commit -m "feat: remove file-based variant generation

BREAKING CHANGE: generate_variant_plecs_mdl() and
GenericConverterPlecsMdl removed. Use PLECS native ModelVars
instead.

See MIGRATION.md for upgrade instructions."

# Documentation
git commit -m "docs: add installation guide for macOS

Add macOS-specific installation instructions including
PLECS path detection and configuration."

# Chore
git commit -m "chore: bump version to 1.0.0 and modularize requirements

- Update version in setup.py, pyproject.toml
- Split requirements.txt into modular files
- Keep monolithic requirements.txt for backwards compatibility"
```

### Claude Attribution

When AI tools assist with commits, include attribution:

```bash
git commit -m "feat: add batch parallel simulation API

Implement simulate_batch() method leveraging PLECS native
parallelization for 3-5x speedup on multi-core machines.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Pull Request Process

### Before Submitting PR

#### Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Code follows style guidelines (`black`, `flake8`, `mypy`)
- [ ] Documentation updated (README, MIGRATION, CHANGELOG)
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with `dev` branch
- [ ] Branch is up to date with `dev`
- [ ] CHANGELOG.md updated (if user-facing change)

#### Update from Upstream

```bash
git fetch upstream
git rebase upstream/dev
# Resolve conflicts if any
git push origin feature/your-feature --force-with-lease
```

### PR Template

Use this template when creating pull request:

```markdown
## Description

Brief description of what this PR does.

## Motivation

Why is this change needed? What problem does it solve?

## Changes

- [ ] Feature A: Description
- [ ] Fix B: Description
- [ ] Docs C: Description

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement

## Testing

How was this tested? Include:
- Test cases added
- Manual testing performed
- Platforms tested (Windows/macOS/Linux)
- PLECS versions tested

## Breaking Changes

List any breaking changes and migration path.

## Screenshots (if applicable)

Add screenshots for UI changes.

## Related Issues

Closes #123
Relates to #456

## Checklist

- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have made corresponding documentation changes
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated checks**: CI runs tests, linting, type checking
2. **Maintainer review**: Code review by project maintainer
3. **Discussion**: Address feedback, make changes
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to `dev` branch

### After PR Merged

```bash
# Update your fork
git checkout dev
git pull upstream dev

# Delete feature branch
git branch -d feature/your-feature
git push origin --delete feature/your-feature
```

---

## Release Process

For maintainers releasing new versions.

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (v1.0.0 → v2.0.0): Breaking changes
- **MINOR** (v1.0.0 → v1.1.0): New features, backward compatible
- **PATCH** (v1.0.0 → v1.0.1): Bug fixes, backward compatible

### Release Checklist

1. **Update version numbers**:
   ```python
   # pyplecs/__init__.py
   __version__ = "1.1.0"
   ```
   ```python
   # setup.py
   version='1.1.0'
   ```
   ```toml
   # pyproject.toml
   version = "1.1.0"
   ```

2. **Update CHANGELOG.md**:
   - Move changes from `[Unreleased]` to `[1.1.0] - YYYY-MM-DD`
   - Add summary of changes
   - Note breaking changes prominently

3. **Run full test suite**:
   ```bash
   pytest --cov=pyplecs tests/
   pytest tests/benchmark_batch_speedup.py -v -s  # Benchmarks
   ```

4. **Create release branch**:
   ```bash
   git checkout -b release/v1.1.0
   ```

5. **Commit version bump**:
   ```bash
   git commit -am "chore: bump version to 1.1.0"
   ```

6. **Tag release**:
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0: <brief summary>"
   ```

7. **Push to GitHub**:
   ```bash
   git push origin release/v1.1.0
   git push origin v1.1.0
   ```

8. **Merge to main**:
   ```bash
   git checkout main
   git merge release/v1.1.0
   git push origin main
   ```

9. **Create GitHub Release**:
   - Go to https://github.com/tinix84/pyplecs/releases/new
   - Select tag `v1.1.0`
   - Title: `PyPLECS v1.1.0`
   - Description: Copy from CHANGELOG.md
   - Attach any binaries/installers
   - Publish release

10. **Publish to PyPI** (when available):
    ```bash
    python setup.py sdist bdist_wheel
    twine upload dist/*
    ```

11. **Announce release**:
    - GitHub Discussions
    - Update README.md badges if needed
    - Social media (LinkedIn, Twitter)

---

## Questions?

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Email**: tinix84@gmail.com for private inquiries

---

## License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

**Thank you for contributing to PyPLECS!** 🚀
