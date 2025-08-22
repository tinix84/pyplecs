# PyPLECS Test Suite

This directory contains the PyPLECS test suite, organized by test type and requirements.

## Test File Organization

### 🤖 `test_automated.py` - Automated Tests
**Purpose**: Tests that run without user interaction, perfect for CI/CD pipelines.

**Usage**:
```bash
# Run all automated tests
python -m pytest tests/test_automated.py -v

# Run specific test
python -m pytest tests/test_automated.py::AutomatedTestSuite::test01_absolute_truth_and_meaning -v
```

**Includes**:
- Basic functionality tests
- PLECS application initialization
- XML-RPC server setup
- Model variant generation
- Basic GUI command testing

### 👤 `test_interactive.py` - Interactive Tests
**Purpose**: Tests that require manual user input and supervision.

**Usage**:
```bash
# Run all interactive tests (will wait for user input)
python -m pytest tests/test_interactive.py -v -s

# Run specific interactive test
python -m pytest tests/test_interactive.py::InteractiveTestSuite::test01_sequential_simulation_server_same_file -v -s
```

**Includes**:
- Sequential simulation tests with manual progression
- Multi-variant simulation workflows
- User-supervised test scenarios

**Note**: Use the `-s` flag to see output and input prompts in real-time.

### 🖱️ `test_gui_automation.py` - GUI Automation Tests
**Purpose**: Tests that require external applications (removed - GUI automation no longer supported).

**Usage**:
```bash
# Run GUI automation tests (requires full GUI environment)
python -m pytest tests/test_gui_automation.py -v -s
```

**Includes**:
- External application automation (removed)
- PLECS GUI automation
- External application interaction

**Requirements**:
- Windows GUI environment (not headless)
- Required applications installed (Notepad, PLECS)

### 📜 `test_basic.py` - Legacy Compatibility
**Purpose**: Backward compatibility file that redirects to `test_automated.py`.

**Status**: DEPRECATED - Use the specific test files instead.

## Test Execution Strategies

### For Development
```bash
# Quick automated test run
python -m pytest tests/test_automated.py -v

# Full automated test with coverage
python -m pytest tests/test_automated.py --cov=pyplecs -v
```

### For Manual Testing
```bash
# Interactive simulation testing
python -m pytest tests/test_interactive.py -v -s

# GUI automation testing
python -m pytest tests/test_gui_automation.py -v -s
```

### For CI/CD Pipelines
```bash
# Only automated tests (no user interaction required)
python -m pytest tests/test_automated.py -v --tb=short
```

### For Comprehensive Testing
```bash
# Run all test types (requires manual interaction)
python -m pytest tests/test_automated.py tests/test_interactive.py tests/test_gui_automation.py -v -s
```

## Test Environment Requirements

### Minimal (Automated Tests)
- Python 3.10+
- PyPLECS package installed
- PLECS executable configured in `config/default.yml`
- Test data files in `data/` directory

### Interactive Testing
- All minimal requirements
- Terminal/console access for input prompts
- Manual supervision capability

### GUI Automation Testing
- All minimal requirements
- Windows GUI environment (not headless/SSH)
- External applications available (if required)

## Configuration

Tests use the PyPLECS configuration system:
- Configuration file: `config/default.yml`
- PLECS executable path must be properly configured
- Test data files expected in `data/` directory

## Troubleshooting

### Common Issues

**Import Errors**: Ensure you're running tests from the project root directory.
```bash
cd /path/to/pyplecs
python -m pytest tests/test_automated.py -v
```

**PLECS Path Issues**: Verify configuration in `config/default.yml`:
```yaml
plecs:
  executable_paths:
    - "C:\\Program Files\\Plecs 4.8\\bin\\plecs.exe"
```

**Interactive Test Hanging**: Use the `-s` flag to see input prompts:
```bash
python -m pytest tests/test_interactive.py -v -s
```

**GUI Automation Failures**: Ensure you're running in a full GUI environment, not headless/SSH.

### Test Data Dependencies

Tests expect these files to exist:
- `data/simple_buck.plecs` - Main simulation model
- `data/01/simple_buck01.plecs` - Variant 1 (generated)
- `data/02/simple_buck02.plecs` - Variant 2 (generated)

## Contributing

When adding new tests:

1. **Automated functionality** → Add to `test_automated.py`
2. **Interactive workflows** → Add to `test_interactive.py`  
3. **GUI automation** → Add to `test_gui_automation.py`

Follow the existing patterns and include proper documentation for each test method.
