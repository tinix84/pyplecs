# PyPLECS Installation Guide

Complete installation instructions for all platforms and use cases.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: pip install (Recommended)](#method-1-pip-install-recommended)
  - [Method 2: Development Install](#method-2-development-install)
  - [Method 3: Windows Installer](#method-3-windows-installer)
  - [Method 4: Minimal Install](#method-4-minimal-install)
- [Configuration](#configuration)
- [Verifying Installation](#verifying-installation)
- [Optional Dependencies](#optional-dependencies)
- [Platform-Specific Notes](#platform-specific-notes)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.8 or higher**
  ```bash
  python --version  # Should show 3.8+
  ```

- **PLECS 4.2 or higher**
  - Download from: https://www.plexim.com/download
  - Supported versions: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7+
  - Note installation path (needed for configuration)

### Recommended

- **Virtual environment** (to isolate dependencies)
  ```bash
  python -m venv pyplecs-env
  source pyplecs-env/bin/activate  # Linux/macOS
  pyplecs-env\Scripts\activate     # Windows
  ```

---

## Installation Methods

### Method 1: pip install (Recommended)

**Coming soon** - PyPI package not yet published.

For now, use Method 2 (Development Install).

---

### Method 2: Development Install

Install from source for the latest features:

```bash
# Clone repository
git clone https://github.com/tinix84/pyplecs.git
cd pyplecs

# Install in editable mode
pip install -e .

# Or install with all features
pip install -e . -r requirements.txt
```

**Minimal install** (core functionality only):
```bash
pip install -e . -r requirements-core.txt
```

**Platform-specific installs**:
```bash
# Linux (no GUI automation)
pip install -e . -r requirements-core.txt -r requirements-web.txt

# Windows (full features)
pip install -e . -r requirements.txt
```

---

### Method 3: Windows Installer

PyPLECS provides an interactive Windows installer with automatic PLECS detection:

#### Basic Installation

```batch
:: Double-click or run from command prompt
tools\installers\windows_installer.bat
```

The installer will:
1. Check for Python 3.8+
2. Auto-detect PLECS installation
3. Install PyPLECS with dependencies
4. Create configuration file
5. Verify installation

#### Non-Interactive Installation (PowerShell)

For automated deployments:

```powershell
# Basic install with auto-detected PLECS
.\tools\installers\windows_installer.ps1 -NonInteractive

# Advanced: specify PLECS path and options
.\tools\installers\windows_installer.ps1 `
  -NonInteractive `
  -PlecsPath "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe" `
  -VenvPath "D:\venvs\pyplecs" `
  -InstallWeb `
  -LogPath "install.log" `
  -JsonStatus "status.json"
```

**PowerShell Installer Options**:
- `-NonInteractive`: No prompts (for CI/CD)
- `-PlecsPath`: Specify PLECS executable path
- `-VenvPath`: Custom virtual environment location
- `-InstallWeb`: Include web UI dependencies
- `-InstallCache`: Include advanced caching dependencies
- `-LogPath`: Save installation log to file
- `-JsonStatus`: Output JSON status for automation

**Installer Features**:
- ✅ Automatic PLECS path detection (registry + common paths)
- ✅ Virtual environment creation
- ✅ Dependency installation with progress tracking
- ✅ Configuration file generation
- ✅ Installation verification
- ✅ Detailed logging (console + file)
- ✅ JSON status output for automation
- ✅ Exit codes for error handling

**Exit Codes**:
- `0`: Success
- `1`: Python version check failed
- `2`: Git clone failed
- `3`: Pip install failed
- `4`: Configuration creation failed
- `5`: Verification failed
- `10`: User cancelled (interactive mode)

**Example CI/CD Usage**:
```yaml
# GitHub Actions
- name: Install PyPLECS
  run: |
    .\tools\installers\windows_installer.ps1 `
      -NonInteractive `
      -JsonStatus status.json

    # Check exit code
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Parse JSON status
    $status = Get-Content status.json | ConvertFrom-Json
    Write-Host "Installed version: $($status.version)"
```

---

### Method 4: Minimal Install

For embedded systems, CI environments, or when disk space is limited:

```bash
# Core functionality only (~50 MB)
pip install -r requirements-core.txt

# Add what you need
pip install -r requirements-web.txt    # REST API + Web GUI
pip install -r requirements-cache.txt  # Advanced caching
pip install -r requirements-gui.txt    # Windows GUI automation
```

---

## Configuration

### Option 1: Setup Wizard (Recommended)

Run the interactive setup wizard:

```bash
pyplecs-setup
```

The wizard will:
1. Auto-detect PLECS installation
2. Test XML-RPC connection
3. Create `config/default.yml`
4. Verify configuration

### Option 2: Manual Configuration

Create `config/default.yml` in your project directory:

```yaml
plecs:
  # PLECS executable path (auto-detected by setup wizard)
  executable: "C:/Program Files/Plexim/PLECS 4.7 (64 bit)/plecs.exe"

  # XML-RPC server settings
  xmlrpc:
    host: "localhost"
    port: 1080
    timeout: 300

  # GUI automation (Windows only)
  gui:
    enabled: true
    process_priority: "high"  # high, normal, low

orchestration:
  # Match your CPU cores for optimal performance
  max_concurrent_simulations: 4
  batch_size: 4

  # Retry logic
  retry_attempts: 3
  retry_delay: 5  # seconds

  # Queue settings
  queue_size: 1000
  task_timeout: 3600  # 1 hour

cache:
  enabled: true
  directory: "./cache"

  # Storage format: parquet (fast), hdf5 (large data), csv (compatibility)
  storage_format: "parquet"

  # Compression: snappy (fast), gzip (small), lz4 (balanced), none
  compression: "snappy"

  # Time to live (seconds, 0 = infinite)
  ttl_seconds: 86400  # 24 hours

  # What to include in cache hash
  include_files: true        # Hash model file content
  include_parameters: true   # Hash simulation parameters
  exclude_fields:            # Don't hash these fields
    - "timestamp"
    - "run_id"
    - "user"

api:
  host: "0.0.0.0"
  port: 8000
  reload: false  # Set true for development
  log_level: "info"

webgui:
  host: "0.0.0.0"
  port: 5000
  debug: false

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "structured"  # structured, json, text

  # File logging
  file:
    enabled: true
    path: "logs/pyplecs.log"
    max_bytes: 10485760  # 10 MB
    backup_count: 5

  # Console logging
  console:
    enabled: true
    colored: true
```

### Configuration File Locations

PyPLECS searches for `config/default.yml` in this order:

1. Current working directory: `./config/default.yml`
2. Parent directories (up to 3 levels): `../config/default.yml`
3. Package directory: `<pyplecs-install>/config/default.yml`
4. User home: `~/.pyplecs/config.yml`

**Create in custom location**:
```bash
mkdir -p ~/.pyplecs
cp config/default.yml ~/.pyplecs/config.yml
# Edit ~/.pyplecs/config.yml
```

---

## Verifying Installation

### Quick Check

```bash
# Verify Python package installed
python -c "import pyplecs; print(pyplecs.__version__)"
# Expected output: 1.0.0

# Check entry points
pyplecs-setup --help
pyplecs-gui --help
pyplecs-api --help
```

### Full Verification

```bash
# Run test suite
pytest tests/

# Run specific verification tests
pytest tests/test_basic.py::BasicTestSuite::test04_pyplecs_xrpc_server -v

# Test batch API (requires PLECS running)
pytest tests/test_plecs_server_refactored.py -v

# Benchmark performance
pytest tests/benchmark_batch_speedup.py -v -s
```

### Manual Verification

```python
from pyplecs import PlecsServer
from pathlib import Path

# Test XML-RPC connection
try:
    with PlecsServer("test.plecs") as server:
        print("✅ PLECS XML-RPC connection successful")
except Exception as e:
    print(f"❌ Connection failed: {e}")

# Test cache
from pyplecs.cache import SimulationCache
cache = SimulationCache()
print(f"✅ Cache initialized: {cache.backend}")

# Test orchestrator
from pyplecs.orchestration import SimulationOrchestrator
orchestrator = SimulationOrchestrator()
print(f"✅ Orchestrator ready: {orchestrator.stats}")
```

---

## Optional Dependencies

### Web UI & REST API

```bash
pip install -r requirements-web.txt
```

Includes:
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `jinja2` - Web templates
- `plotly` - Interactive plots
- `websockets` - Real-time updates

**Verify**:
```bash
pyplecs-api &
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Advanced Caching

```bash
pip install -r requirements-cache.txt
```

Includes:
- `pyarrow` - Parquet storage (10x faster than CSV)
- `h5py` - HDF5 storage (for large datasets)
- `redis` - Distributed cache backend
- `diskcache` - Enhanced file caching

**Verify**:
```python
from pyplecs.cache import SimulationCache
cache = SimulationCache(storage_format="parquet")
print(cache.backend)  # Should show parquet support
```

### GUI Automation (Windows Only)

```bash
pip install -r requirements-gui.txt
```

Includes:
- `pywinauto` - GUI automation
- `psutil` - Process management

**Verify**:
```python
from pyplecs import PlecsApp
app = PlecsApp()
print("✅ GUI automation available")
```

### Development Tools

```bash
pip install -r requirements-dev.txt
```

Includes:
- `pytest` - Testing framework
- `black` - Code formatter
- `flake8` - Linter
- `mypy` - Type checker
- `sphinx` - Documentation generator

### Optimization (Future Feature)

```bash
pip install -r requirements-opt.txt
```

Includes:
- `optuna` - Bayesian optimization
- `scikit-optimize` - Sequential model-based optimization
- `deap` - Genetic algorithms

---

## Platform-Specific Notes

### Windows

**Full support** for all features including GUI automation.

**PLECS detection paths** (automatic):
1. Registry: `HKLM\SOFTWARE\Plexim\PLECS`
2. Common paths:
   - `C:\Program Files\Plexim\PLECS *\plecs.exe`
   - `C:\Program Files (x86)\Plexim\PLECS *\plecs.exe`
3. User-specified path in config

**Firewall**: Allow Python/PLECS on port 1080 (XML-RPC)

**Installer**: Use `tools\installers\windows_installer.bat` for guided setup

### macOS

**XML-RPC support only** (no GUI automation).

**PLECS paths**:
- `/Applications/PLECS.app/Contents/MacOS/plecs`
- Custom install location

**Installation**:
```bash
# Install core + web
pip install -r requirements-core.txt -r requirements-web.txt

# Configure PLECS path
pyplecs-setup
```

**Note**: `pywinauto` is Windows-only and not needed on macOS.

### Linux / WSL

**XML-RPC support only** (no GUI automation).

**PLECS paths**:
- `/opt/plecs/plecs`
- `/usr/local/bin/plecs`
- Custom build location

**WSL Notes**:
- PLECS must run in Windows host or via Wine
- Use Windows PLECS path in config
- XML-RPC works cross-boundary

**Installation**:
```bash
# Install core + web
pip install -r requirements-core.txt -r requirements-web.txt

# Configure PLECS path (Windows path if using WSL)
pyplecs-setup
```

**Wine** (if running PLECS natively on Linux):
```bash
# Install Wine
sudo apt install wine64

# Run PLECS via Wine
wine /path/to/plecs.exe &

# Configure PyPLECS to use Wine path
```

---

## Troubleshooting

### Issue: "PLECS executable not found"

**Solution**:
```bash
# Run setup wizard
pyplecs-setup

# Or manually edit config/default.yml
plecs:
  executable: "/full/path/to/plecs.exe"
```

**Find PLECS**:
```bash
# Windows
where plecs

# macOS
which plecs
mdfind -name plecs.app

# Linux
find / -name plecs 2>/dev/null
```

### Issue: "XML-RPC connection timeout"

**Causes**:
1. PLECS not running
2. XML-RPC server disabled in PLECS
3. Firewall blocking port 1080
4. Wrong host/port in config

**Solution**:
```bash
# 1. Start PLECS manually
# 2. Enable XML-RPC: PLECS > Preferences > Remote Control
# 3. Check firewall allows port 1080
# 4. Verify config/default.yml:
plecs:
  xmlrpc:
    host: "localhost"
    port: 1080
```

**Test connection**:
```python
import xmlrpc.client
server = xmlrpc.client.Server("http://localhost:1080/RPC2")
print(server.system.listMethods())
```

### Issue: "Module not found: pywinauto"

**Cause**: Optional dependency not installed (Windows-only feature)

**Solution**:
```bash
# On Windows
pip install -r requirements-gui.txt

# On macOS/Linux (not needed)
# GUI automation is Windows-only
```

### Issue: "Permission denied: ./cache"

**Cause**: No write access to cache directory

**Solution**:
```bash
# Check permissions
ls -la cache/

# Fix permissions
chmod 755 cache/

# Or use different cache directory in config:
cache:
  directory: "/tmp/pyplecs-cache"
```

### Issue: "Import error: fastapi"

**Cause**: Web dependencies not installed

**Solution**:
```bash
pip install -r requirements-web.txt
```

### Issue: "Slow simulations (no speedup)"

**Cause**: Batch API not enabled or batch_size=1

**Solution**:
```yaml
# Edit config/default.yml
orchestration:
  batch_size: 4  # Match CPU cores
  max_concurrent_simulations: 4
```

**Verify**:
```python
from pyplecs import PlecsServer
with PlecsServer("model.plecs") as server:
    # This should be 3-5x faster than sequential
    results = server.simulate_batch([
        {"Vi": 12}, {"Vi": 24}, {"Vi": 48}
    ])
```

### Issue: "Cache not working"

**Check**:
```python
from pyplecs.cache import SimulationCache
cache = SimulationCache()
stats = cache.get_stats()
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
```

**Enable debug logging**:
```yaml
# config/default.yml
logging:
  level: "DEBUG"
```

**Clear cache**:
```bash
# Via API
curl -X POST http://localhost:8000/cache/clear

# Or manually
rm -rf cache/*
```

### Issue: "Tests fail with 'No PLECS running'"

**Solution**:
```bash
# Start PLECS before running tests
# Enable XML-RPC in PLECS preferences

# Run tests with PLECS running
pytest tests/ -v
```

---

## Next Steps

After successful installation:

1. **Read the Quick Start**: [README.md](README.md#quick-start)
2. **Explore the Web GUI**: `pyplecs-gui` → http://localhost:5000
3. **Try the REST API**: [API.md](API.md)
4. **Run examples**: Check `tests/` for usage patterns
5. **Optimize performance**: [CLAUDE.md](CLAUDE.md) for architecture details

---

## Getting Help

- **Documentation**: See [README.md](README.md#documentation)
- **GitHub Issues**: https://github.com/tinix84/pyplecs/issues
- **Email**: tinix84@gmail.com

---

## Upgrading from v0.x

If upgrading from PyPLECS v0.x, see [MIGRATION.md](MIGRATION.md) for:
- Breaking changes
- Deprecated methods
- Migration checklist
- Performance improvements

---

**Installation complete!** 🎉 Ready to simulate faster with PyPLECS v1.0.0.
