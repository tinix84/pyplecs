@echo off
REM ──────────────────────────────────────────────────────────
REM  PyPLECS Setup — One-time environment configuration
REM
REM  Self-bootstrapping: all discovery in pure batch (no Python
REM  needed until the environment is ready).
REM
REM  Steps:
REM    1. Scan for Python + conda (PATH + common install dirs)
REM    2. Choose Python environment (existing conda env or new venv)
REM    3. Activate env + install dependencies
REM    4. Configure PLECS path (Python script, needs yaml)
REM
REM  All settings saved to config/default.yml.
REM  Run this ONCE before using start_plecs.bat.
REM ──────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   PyPLECS Environment Setup
echo ============================================================

REM ══════════════════════════════════════════════════════════
REM  Step 1: Scan for Python and conda installations
REM ══════════════════════════════════════════════════════════
echo.
echo [1/4] Scanning for Python and conda installations...

set "HAS_PYTHON=0"
set "HAS_CONDA=0"
set "CONDA_BAT="
set "PYTHON_EXE="

REM ── Try conda on PATH first ──────────────────────────────
set "CONDA_ROOT="
call conda --version >nul 2>&1
if not errorlevel 1 (
    set "HAS_CONDA=1"
    for /f "delims=" %%V in ('call conda --version 2^>^&1') do echo       [OK] %%V ^(on PATH^)
    REM Resolve conda root from PATH
    for /f "delims=" %%P in ('where conda.bat 2^>nul') do (
        for %%Q in ("%%~dpP..") do set "CONDA_ROOT=%%~fQ"
    )
    goto :conda_found
)

REM ── Scan common conda install locations ──────────────────
echo       conda not on PATH, scanning common locations...
for %%D in (
    "%USERPROFILE%\miniconda3"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\Miniconda3"
    "%USERPROFILE%\Anaconda3"
    "%LOCALAPPDATA%\miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%PROGRAMDATA%\miniconda3"
    "%PROGRAMDATA%\Anaconda3"
    "C:\miniconda3"
    "C:\anaconda3"
    "C:\tools\miniconda3"
    "C:\tools\Anaconda3"
) do (
    if exist "%%~D\condabin\conda.bat" (
        set "HAS_CONDA=1"
        set "CONDA_BAT=%%~D\condabin\conda.bat"
        set "CONDA_ROOT=%%~D"
        echo       [OK] conda found: %%~D
        goto :conda_found
    )
    if exist "%%~D\Scripts\conda.exe" (
        set "HAS_CONDA=1"
        set "CONDA_BAT=%%~D\Scripts\conda.exe"
        set "CONDA_ROOT=%%~D"
        echo       [OK] conda found: %%~D
        goto :conda_found
    )
)
echo       conda not found.

:conda_found

REM ── Initialize conda if found via scan (not on PATH) ─────
if defined CONDA_BAT (
    REM Run conda init hook so 'conda activate' works in this session
    for %%D in ("!CONDA_BAT!") do set "CONDA_ROOT=%%~dpD.."
    if exist "!CONDA_ROOT!\condabin\conda_hook.bat" (
        call "!CONDA_ROOT!\condabin\conda_hook.bat"
    ) else if exist "!CONDA_ROOT!\Scripts\activate.bat" (
        call "!CONDA_ROOT!\Scripts\activate.bat"
    )
)

REM ── Try python on PATH ───────────────────────────────────
python --version >nul 2>&1
if not errorlevel 1 (
    set "HAS_PYTHON=1"
    for /f "delims=" %%V in ('python --version 2^>^&1') do echo       [OK] %%V
    goto :python_found
)

REM ── Scan common Python install locations ─────────────────
echo       python not on PATH, scanning...
for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%LOCALAPPDATA%\Programs\Python\Python310"
    "C:\Python313"
    "C:\Python312"
    "C:\Python311"
    "C:\Python310"
) do (
    if exist "%%~D\python.exe" (
        set "HAS_PYTHON=1"
        set "PYTHON_EXE=%%~D\python.exe"
        echo       [OK] Python found: %%~D
        set "PATH=%%~D;%%~D\Scripts;!PATH!"
        goto :python_found
    )
)

REM If conda found, python is available through conda
if "%HAS_CONDA%"=="1" (
    set "HAS_PYTHON=1"
    echo       [OK] Python available via conda.
)

:python_found

if "%HAS_PYTHON%"=="0" if "%HAS_CONDA%"=="0" (
    echo.
    echo [ERROR] No Python or conda installation found.
    echo.
    echo   Install one of these:
    echo     - Python: https://www.python.org/downloads/
    echo     - Miniconda: https://docs.conda.io/en/latest/miniconda.html
    echo     - Anaconda: https://www.anaconda.com/download
    echo.
    echo   Tip: Check "Add to PATH" during installation, or install
    echo   to a standard location so this script can find it.
    echo.
    pause
    exit /b 1
)

echo.

REM ══════════════════════════════════════════════════════════
REM  Step 2: Choose Python environment
REM ══════════════════════════════════════════════════════════
echo [2/4] Python environment selection...
echo.

set "ENV_TYPE="
set "ENV_NAME="

REM Check for existing .venv
set "HAS_VENV=0"
if exist ".venv\Scripts\activate.bat" set "HAS_VENV=1"

REM List conda envs if available
set "CONDA_COUNT=0"
if "%HAS_CONDA%"=="1" (
    echo   Available conda environments:
    for /f "tokens=1,*" %%A in ('call conda env list 2^>nul ^| findstr /v /c:"#" ^| findstr /r /v "^$"') do (
        set /a CONDA_COUNT+=1
        echo     !CONDA_COUNT!. %%A
        set "CONDA_ENV_!CONDA_COUNT!=%%A"
    )
    if "!CONDA_COUNT!"=="0" (
        echo     ^(none found^)
    )
    echo.
)

if "%HAS_VENV%"=="1" (
    echo   Existing .venv found.
    echo.
)

echo   Options:
if "%HAS_CONDA%"=="1" if not "!CONDA_COUNT!"=="0" (
    echo     [C] Use existing conda environment
)
if "%HAS_VENV%"=="1" (
    echo     [V] Use existing .venv
) else (
    echo     [V] Create new .venv
)
echo.

REM Default: conda if available with envs, otherwise venv
if "%HAS_CONDA%"=="1" if not "!CONDA_COUNT!"=="0" (
    set "DEFAULT_CHOICE=C"
) else (
    set "DEFAULT_CHOICE=V"
)

set /p "ENV_CHOICE=  Choose [C=conda, V=venv] [%DEFAULT_CHOICE%]: "
if not defined ENV_CHOICE set "ENV_CHOICE=%DEFAULT_CHOICE%"

REM Normalize to uppercase
if /i "%ENV_CHOICE%"=="c" set "ENV_CHOICE=C"
if /i "%ENV_CHOICE%"=="v" set "ENV_CHOICE=V"

if "%ENV_CHOICE%"=="C" (
    set "ENV_TYPE=conda"
    echo.
    set "CONDA_SEL=1"
    set /p "CONDA_SEL=  Conda env name or number [1]: "

    REM Resolve numeric selection to env name
    REM Use 'call' to force double expansion: CONDA_SEL -> index -> CONDA_ENV_N -> name
    call set "ENV_NAME=%%CONDA_ENV_!CONDA_SEL!%%"
    if "!ENV_NAME!"=="" set "ENV_NAME=!CONDA_SEL!"
    echo       Selected: conda ^(!ENV_NAME!^)
) else (
    set "ENV_TYPE=venv"
    set "ENV_NAME="
    echo       Selected: venv
)

REM ══════════════════════════════════════════════════════════
REM  Step 3: Activate environment + install dependencies
REM ══════════════════════════════════════════════════════════
echo.
echo [3/4] Setting up environment...

if "%ENV_TYPE%"=="conda" (
    echo       Activating conda env: %ENV_NAME%
    call conda activate %ENV_NAME%
    if errorlevel 1 (
        echo [ERROR] Failed to activate conda env '%ENV_NAME%'.
        pause
        exit /b 1
    )
) else (
    if not exist ".venv\Scripts\activate.bat" (
        echo       Creating .venv...
        python -m venv .venv
        if errorlevel 1 (
            echo [ERROR] Failed to create .venv.
            pause
            exit /b 1
        )
    )
    call .venv\Scripts\activate.bat
)

echo       Installing dependencies...
python -m pip install --quiet --upgrade pip 2>nul

if exist "requirements-core.txt" (
    python -m pip install --quiet -r requirements-core.txt
    echo       requirements-core.txt installed.
)
if exist "requirements-web.txt" (
    python -m pip install --quiet -r requirements-web.txt
    echo       requirements-web.txt installed.
)
if exist "requirements-cache.txt" (
    python -m pip install --quiet -r requirements-cache.txt
    echo       requirements-cache.txt installed.
)

REM ══════════════════════════════════════════════════════════
REM  Step 4: Configure PLECS path (now Python + yaml available)
REM ══════════════════════════════════════════════════════════
echo.
echo [4/4] Configuring PLECS path...
echo.

REM Save python env config to default.yml (env_type, env_name, conda_root)
python -c "import yaml; from pathlib import Path; p=Path('config/default.yml'); cfg=yaml.safe_load(p.read_text()); cfg.setdefault('python',{}); cfg['python']['env_type']='%ENV_TYPE%'; cfg['python']['env_name']='%ENV_NAME%'; cfg['python']['conda_root']=r'%CONDA_ROOT%'; p.write_text(yaml.dump(cfg,default_flow_style=False,sort_keys=False))"

REM Interactive PLECS path config
python tools\configure_plecs.py
if errorlevel 1 (
    echo [ERROR] PLECS configuration failed.
    pause
    exit /b 1
)

echo ============================================================
echo   Setup complete! Run start_plecs.bat to launch.
echo ============================================================
echo.
pause
