@echo off
REM ──────────────────────────────────────────────────────────
REM  PyPLECS setup — run once before start_plecs.bat.
REM
REM  Two steps, because there are only two things to do:
REM    1. uv creates .venv and installs the pinned dependencies
REM    2. pyplecs-setup finds PLECS and writes config\default.yml
REM
REM  uv replaces the Python/conda discovery this script used to do:
REM  it downloads a matching interpreter itself if none is present.
REM ──────────────────────────────────────────────────────────

setlocal
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed.
    echo         Install it with:  winget install astral-sh.uv
    echo         or see https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo [1/2] Installing dependencies with uv...
uv sync --extra web --extra cache --extra gui
if errorlevel 1 (
    echo [ERROR] uv sync failed.
    pause
    exit /b 1
)
echo       done.
echo.

echo [2/2] Configuring PLECS path...
uv run pyplecs-setup configure-plecs
if errorlevel 1 (
    echo [ERROR] PLECS configuration failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup complete. Run start_plecs.bat to launch.
echo ============================================================
pause
