
# PyPLECS: Python Automation for PLECS Simulations

# PyPLECS

Advanced automation for PLECS simulations with a web UI, REST API, and orchestration tools.

This repository contains the PyPLECS core library, a FastAPI-based web GUI for monitoring and controlling simulations, and helper installers/scripts to bootstrap a development or deployment environment.

## Key features

- Automated orchestration of PLECS simulations (sequential and parallel)
- FastAPI web GUI with WebSocket real-time updates
- Cache system for simulation results (file-based / parquet)
- CLI helper `pyplecs-setup` for configuration and environment checks
- Windows installer script to create a `.venv`, install deps and configure the PLECS executable path

## Requirements

- Python 3.8+ (3.10+ recommended)
- On Windows: PowerShell / pwsh available for installer scripts
- PLECS (external, optional) if you want to run GUI-driven simulations

Core Python dependencies are listed in `requirements.txt` and in `pyproject.toml`.

## Installation

Two main ways to prepare the project environment: automated (Windows) or manual (cross-platform).

### Automated (Windows) installer

The repository includes an advanced installer at `tools/installers/windows_installer.ps1` that will:

- Create a `.venv` in the project root
- Install required Python packages into the venv
- Probe common PLECS install locations and update `config/default.yml` with the found executable path
- Optionally run a basic test suite to validate the setup

Run non-interactively from the project root (PowerShell):

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\installers\windows_installer.ps1 -Yes
```

To force recreation of the `.venv`, add the `-ForceVenv` switch:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\installers\windows_installer.ps1 -Yes -ForceVenv
```

Installer logs are written to `tools/installer_windows.log` and status JSON to `tools/installer_windows_status.json`.

### Manual (cross-platform)

1. Create and activate a virtual environment in the project root:

```bash
python -m venv .venv
# On Linux/macOS
source .venv/bin/activate
# On Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. (Optional) Install the package in editable mode for development:

```bash
pip install -e .
```

## First steps and installation checks

- Verify the virtual environment exists and `python` resolves to `.venv`'s interpreter.
- Basic check: run the web GUI locally (see Usage below).
- Use `pyplecs-setup` CLI (installed via `pyproject.toml` entry points) for convenience commands:

```bash
python -m pyplecs.cli.installer create-config
python -m pyplecs.cli.installer check-windows
```

## Usage

### Start the Web GUI

The lightweight starter script is `start_webgui.py` at the project root. Run it from the project root (with the `.venv` active):

```bash
python start_webgui.py
```

Default server address: http://127.0.0.1:8001

Available pages:

- `/` - Dashboard
- `/simulations` - Simulation manager
- `/cache` - Cache monitor
- `/settings` - Configuration (PLECS paths, orchestration settings)

### CLI

- `pyplecs-setup` (entry point) provides helper tasks such as creating a minimal `config/default.yml` and running platform checks.

## Configuration

The primary configuration file is `config/default.yml`. The Windows installer can populate the `plecs.executable_paths` entry. Example minimal config written by the installer:

```yaml
plecs:
	executable_paths:
		- 'C:\\Program Files\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe'
```

Other application settings are stored centrally and loaded via `pyplecs.config`.

## Running tests

The project includes pytest tests under `tests/`. Run the full test suite with the venv Python:

```bash
.venv\Scripts\Activate.ps1  # Windows PowerShell
python -m pytest -q
```

For a quick installation validation without GUI dependencies, run the smoke test:

```bash
python -m pytest tests/test_smoke.py -v
```

The Windows installer offers an option to run `pytest tests/test_basic.py` to validate integration.

## Troubleshooting

### PLECS Path Configuration

If you get a **PLECS executable not found** error, update the path in `config/default.yml`:

```yaml
plecs:
  executable_paths:
    - "C:/Program Files/Plexim/PLECS 4.7 (64 bit)/plecs.exe"  # Update to your version
```

You can add multiple paths for different PLECS versions:
```yaml
plecs:
  executable_paths:
    - "D:/OneDrive/Documenti/Plexim/PLECS 4.7 (64 bit)/plecs.exe"
    - "C:/Program Files/Plexim/PLECS 4.7 (64 bit)/plecs.exe"
    - "C:/Program Files/Plexim/PLECS 4.6 (64 bit)/plecs.exe"
```

### Installation Issues

- `.venv` not present: ensure the installer was run from the project root. The installer will create `.venv` in the repository root. Use `-ForceVenv` to recreate.
- Missing Python packages (ImportError): activate the venv and run `pip install -r requirements.txt`.
- Installer logs: `tools/installer_windows.log` and `tools/installer_windows_status.json` contain detailed outcomes and error codes.

Common error codes (written in status JSON):

- `venv_creation_failed` / `venv_creation_exception` - venv creation failed
- `pip_install_failed` / `pip_install_exception` - dependency installation failed
- `plecs_path_invalid` - supplied PLECS path could not be found

If you need interactive help on Windows, run the PowerShell installer without `-Yes` to use prompts.

## Contributing

Contributions welcome. Please open issues or pull requests. Follow these guidelines:

- Run tests before pushing changes: `python -m pytest`
- Keep code style with `black` and `flake8` as configured in `requirements.txt`
- Update `docs/PROGRESS_MEMO.md` with high-level progress notes for large changes

## License

This project is licensed under the terms in the `LICENSE` file.

---

If you want, I can also generate a short Quick Start section with example commands tailored to Windows or Linux — tell me which platform you'd like prioritized.



