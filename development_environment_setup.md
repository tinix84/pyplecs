# PyPLECS Development Environment Setup

## Prerequisites
- Python 3.8+ (3.10+ recommended)
- PLECS Standalone (for real simulation)
- Git
- Windows, Linux, or macOS (Windows best supported)

## Setup Steps

1. **Clone the repository:**
   ```sh
   git clone https://github.com/tinix84/pyplecs.git
   cd pyplecs
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   # For full features (parquet, yaml):
   pip install .[full]
   ```

4. **(Windows) Use the installer script for automated setup:**
   ```pwsh
   tools\installers\windows_installer.ps1
   ```

5. **Configure PLECS path and XML-RPC:**
   - Edit `config/default.yml` if needed to set PLECS executable path and XML-RPC port.
   - By default, XML-RPC is enabled on port 1080.

6. **Run tests to verify setup:**
   ```sh
   pytest tests/ -v
   ```

7. **Run the CLI demo:**
   ```sh
   python cli_demo_nomocks.py
   ```

## Notes
- Linux/macOS: Manual setup only (no installer script yet)
- PLECS must be installed and licensed for real simulation
- For development, see `DEV_PLAN.md` and `incomplete_methods_inventory.md`

---

This guide provides a quickstart for setting up a development environment for PyPLECS. For more details, see the README and documentation files.
