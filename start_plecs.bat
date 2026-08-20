@echo off
REM ──────────────────────────────────────────────────────────
REM  Start PLECS, then the pyplecs REST API.
REM
REM  Reads the PLECS path from config\default.yml. Run
REM  setup_env.bat first if that file does not exist yet.
REM
REM  `uv run` resolves the environment itself, so no activation
REM  or conda discovery is needed here.
REM ──────────────────────────────────────────────────────────

setlocal
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed. Run setup_env.bat.
    pause
    exit /b 1
)

REM ── Read the configured PLECS executable ─────────────────
for /f "usebackq delims=" %%P in (`uv run python -c "from pyplecs.cli.installer import read_plecs_path; p=read_plecs_path(); print(p) if p else exit(1)" 2^>nul`) do set "PLECS_EXE=%%P"

if not defined PLECS_EXE (
    echo [ERROR] No valid PLECS path in config\default.yml.
    echo         Run setup_env.bat to configure it.
    pause
    exit /b 1
)

echo [1/2] Starting PLECS: %PLECS_EXE%
start "" "%PLECS_EXE%"

echo       Waiting 10 seconds for PLECS to initialize...
timeout /t 10 /nobreak >nul

echo [2/2] Starting pyplecs REST API...
echo       (host and port come from config\default.yml; Ctrl+C to stop)
echo.
uv run pyplecs-api

echo.
echo pyplecs API stopped. Press any key to exit.
pause
