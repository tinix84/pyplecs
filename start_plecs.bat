@echo off
REM ──────────────────────────────────────────────────────────
REM  Start PLECS GUI + pyplecs REST API
REM
REM  Reads PLECS path and Python env from config/default.yml
REM  (set by setup_env.bat). Run setup_env.bat first.
REM ──────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ── Read Python environment config ───────────────────────
set "ENV_TYPE=venv"
set "ENV_NAME="
set "CONDA_ROOT="
if exist "config\default.yml" (
    for /f "usebackq tokens=2 delims=: " %%V in (`findstr "env_type:" "config\default.yml"`) do set "ENV_TYPE=%%V"
    for /f "usebackq tokens=2 delims=: " %%V in (`findstr "env_name:" "config\default.yml"`) do set "ENV_NAME=%%V"
    for /f "usebackq tokens=1,* delims=: " %%A in (`findstr "conda_root:" "config\default.yml"`) do set "CONDA_ROOT=%%B"
    REM Trim leading space from CONDA_ROOT
    if defined CONDA_ROOT for /f "tokens=*" %%T in ("!CONDA_ROOT!") do set "CONDA_ROOT=%%T"
)

REM ── Bootstrap: ensure conda is available if not on PATH ──
call conda --version >nul 2>&1
if errorlevel 1 (
    REM Try saved conda_root from config first
    if defined CONDA_ROOT (
        if exist "!CONDA_ROOT!\condabin\conda_hook.bat" (
            call "!CONDA_ROOT!\condabin\conda_hook.bat"
            goto :conda_ready
        )
    )
    REM Fallback: scan common locations
    for %%D in (
        "%USERPROFILE%\miniconda3"
        "%USERPROFILE%\anaconda3"
        "%USERPROFILE%\Miniconda3"
        "%USERPROFILE%\Anaconda3"
        "%LOCALAPPDATA%\miniconda3"
        "%LOCALAPPDATA%\anaconda3"
        "%PROGRAMDATA%\miniconda3"
        "%PROGRAMDATA%\anaconda3"
        "%PROGRAMDATA%\Miniconda3"
        "%PROGRAMDATA%\Anaconda3"
        "C:\miniconda3"
        "C:\anaconda3"
        "C:\tools\miniconda3"
        "C:\tools\Anaconda3"
    ) do (
        if exist "%%~D\condabin\conda_hook.bat" (
            call "%%~D\condabin\conda_hook.bat"
            goto :conda_ready
        )
    )
)
:conda_ready

if "%ENV_TYPE%"=="conda" (
    echo Activating conda env: !ENV_NAME!
    call conda activate !ENV_NAME!
    if errorlevel 1 (
        echo [ERROR] Failed to activate conda env '!ENV_NAME!'. Run setup_env.bat.
        pause
        exit /b 1
    )
) else (
    if not exist ".venv\Scripts\activate.bat" (
        echo [ERROR] .venv not found. Run setup_env.bat first.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
)

REM ── Read PLECS path from config ──────────────────────────
for /f "usebackq delims=" %%P in (`python tools\read_plecs_path.py plecs 2^>nul`) do set "PLECS_EXE=%%P"

if not defined PLECS_EXE (
    echo [ERROR] Could not read PLECS path from config/default.yml.
    echo         Run setup_env.bat to configure.
    pause
    exit /b 1
)

REM ── Launch PLECS ─────────────────────────────────────────
echo [1/2] Starting PLECS: %PLECS_EXE%
start "" "%PLECS_EXE%"

echo       Waiting 10 seconds for PLECS to initialize...
timeout /t 10 /nobreak > nul

REM ── Launch pyplecs REST API ──────────────────────────────
echo [2/2] Starting pyplecs REST API on 0.0.0.0:8081...
echo       (Press Ctrl+C to stop)
echo.
python _start_api.py

echo.
echo pyplecs API stopped. Press any key to exit.
pause
