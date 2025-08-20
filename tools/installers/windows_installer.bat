@echo off
REM Minimal Windows installer helper for PyPLECS
REM This script runs the packaged Python entrypoint to create config and run checks.

npython -m pyplecs.cli.installer create-config
python -m pyplecs.cli.installer check-windows

echo Done. Please edit config/default.yml to add your PLECS executable path if needed.
pause
