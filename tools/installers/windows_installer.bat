echo Done. Please edit config/default.yml to add your PLECS executable path if needed.
@echo off
REM PyPLECS Windows installer helper (double-clickable)
REM Steps performed (interactive):
REM  1) Check for Python, offer to download installer if missing
REM  2) Create virtualenv `.venv` in project root
REM  3) Activate venv and install core Python requirements
REM  4) Detect common PLECS installation paths or ask the user, then update config/default.yml
REM  5) Offer to run `pytest tests/test_basic.py` to validate pywinauto / PLECS integration

SETLOCAL ENABLEDELAYEDEXPANSION
cd /d %~dp0\..\
+SET PROJ_ROOT=%CD%
+echo Project root: %PROJ_ROOT%
+
+:: 1) Check Python
+python --version >nul 2>&1
+IF %ERRORLEVEL% NEQ 0 (
+    echo Python non trovato nel PATH.
+    set /p DOWNLOAD_PY=Vuoi scaricare l'installer ufficiale di Python e avviare il setup? [y/N]: 
+    if /I "%DOWNLOAD_PY%"=="y" (
+        echo Scarico Python installer (semplice downloader, richiede PowerShell)...
+        powershell -Command "$url='https://www.python.org/ftp/python/3.10.12/python-3.10.12-amd64.exe'; $out='python-installer.exe'; (New-Object System.Net.WebClient).DownloadFile($url,$out)"
+        if exist python-installer.exe (
+            echo Avvio installer Python. Segui la procedura GUI (consigliato: tick 'Add Python to PATH').
+            start /wait python-installer.exe
+            del /f python-installer.exe >nul 2>&1
+        ) else (
+            echo Errore: download fallito. Apri manualmente https://www.python.org/downloads/ e installa Python 3.10+ e assicurati che 'Add to PATH' sia abilitato.
+            pause
+            goto :end
+        )
+    ) else (
+        echo Skip Python install. Assicurati di avere Python 3.8+ nel PATH e riavvia questo script.
+        pause
+        goto :end
+    )
+) ELSE (
+    python --version
+)
+
+:: 2) Create virtualenv
+echo Creazione virtual environment in %PROJ_ROOT%\.venv
+python -m venv .venv
+IF %ERRORLEVEL% NEQ 0 (
+    echo Fallita creazione venv. Assicurati che Python sia correttamente installato.
+    pause
+    goto :end
+)
+
+:: 3) Activate venv and install requirements
+echo Attivo venv e installo dipendenze minime (fastapi, uvicorn, jinja2, pandas, pyyaml)
+call .venv\Scripts\activate.bat
+IF %ERRORLEVEL% NEQ 0 (
+    echo Impossibile attivare la virtualenv. Controlla .venv\Scripts\activate.bat
+    pause
+    goto :end
+)
+
+:: Install core packages
+python -m pip install --upgrade pip
+python -m pip install fastapi uvicorn[standard] jinja2 pandas pyyaml pywin32 pywinauto --quiet
+IF %ERRORLEVEL% NEQ 0 (
+    echo Alcune installazioni pip potrebbero aver fallito; controlla l'output.
+)
+
+:: 4) Detect PLECS paths
+set FOUND_PLECS=
+set PLECS_CAND1="C:\\Program Files\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe"
+set PLECS_CAND2="C:\\Program Files\\Plexim\\PLECS 4.6 (64 bit)\\plecs.exe"
+set PLECS_CAND3="D:\\OneDrive\\Documenti\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe"
+for %%P in (%PLECS_CAND1% %PLECS_CAND2% %PLECS_CAND3%) do (
+    if exist %%~P (
+        set FOUND_PLECS=%%~P
+        goto :foundplecs
+    )
+)
+
+:askplecs
+echo Non ho trovato PLECS nelle posizioni comuni.
+set /p USER_PLECS=Inserisci il percorso completo verso plecs.exe (o premi ENTER per saltare): 
+if "%USER_PLECS%"=="" (
+    echo Hai scelto di non specificare il percorso ora. Ricorda di aggiornare config/default.yml con il path del tuo plecs.exe.
+    goto :afterplecs
+) else (
+    if exist "%USER_PLECS%" (
+        set FOUND_PLECS=%USER_PLECS%
+        goto :foundplecs
+    ) else (
+        echo Percorso non valido: %USER_PLECS%
@echo off
REM PyPLECS Windows installer helper (double-clickable or scriptable)
REM Usage: windows_installer.bat [--yes] [--plecs-path "C:\path\to\plecs.exe"] [--ps]

SETLOCAL ENABLEDELAYEDEXPANSION
set YES_FLAG=0
set PLECS_PATH_ARG=
set USE_PS=0
set EXIT_CODE=0
set FINAL_MSG=OK

:parse_args
if "%~1"=="" goto args_parsed
if /I "%~1"=="--yes" set YES_FLAG=1 & shift & goto parse_args
if /I "%~1"=="--plecs-path" set PLECS_PATH_ARG=%~2 & shift & shift & goto parse_args
if /I "%~1"=="--ps" set USE_PS=1 & shift & goto parse_args
shift & goto parse_args

:args_parsed
cd /d %~dp0\..\
SET PROJ_ROOT=%CD%
SET LOGFILE=%PROJ_ROOT%\installer_windows.log
SET STATUSFILE=%PROJ_ROOT%\installer_windows_status.json
echo [%DATE% %TIME%] Installer started > "%LOGFILE%"
echo Project root: %PROJ_ROOT% >> "%LOGFILE%"
echo Parsing flags: YES=%YES_FLAG% PLECS_PATH=%PLECS_PATH_ARG% USE_PS=%USE_PS% >> "%LOGFILE%"

:: 1) Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
	echo [%DATE% %TIME%] Python not found in PATH >> "%LOGFILE%"
	if "%YES_FLAG%"=="1" (
		set DOWNLOAD_PY=y
	) else (
		set /p DOWNLOAD_PY=Vuoi scaricare l'installer ufficiale di Python e avviare il setup? [y/N]: 
	)
	if /I "%DOWNLOAD_PY%"=="y" (
		echo [%DATE% %TIME%] Downloading Python installer... >> "%LOGFILE%"
		powershell -Command "$url='https://www.python.org/ftp/python/3.10.12/python-3.10.12-amd64.exe'; $out='python-installer.exe'; (New-Object System.Net.WebClient).DownloadFile($url,$out)"
		if exist python-installer.exe (
			echo [%DATE% %TIME%] Running Python installer... >> "%LOGFILE%"
			start /wait python-installer.exe
			del /f python-installer.exe >nul 2>&1
		) else (
			echo [%DATE% %TIME%] Error: download failed >> "%LOGFILE%"
			set EXIT_CODE=11
			set FINAL_MSG=python_download_failed
			goto end
		)
	) else (
		echo [%DATE% %TIME%] User skipped Python install >> "%LOGFILE%"
		set EXIT_CODE=10
		set FINAL_MSG=python_missing
		goto end
	)
) ELSE (
	for /f "delims=" %%I in ('python --version 2^>^&1') do set PYVER=%%I
	echo [%DATE% %TIME%] Python found: %PYVER% >> "%LOGFILE%"
)

:: 2) Create virtualenv
echo [%DATE% %TIME%] Creating virtualenv at %PROJ_ROOT%\.venv >> "%LOGFILE%"
python -m venv .venv
IF %ERRORLEVEL% NEQ 0 (
	echo [%DATE% %TIME%] Failed to create venv >> "%LOGFILE%"
	set EXIT_CODE=20
	set FINAL_MSG=venv_creation_failed
	goto end
)

:: 3) Activate venv and install requirements
echo [%DATE% %TIME%] Activating venv and installing core packages >> "%LOGFILE%"
call .venv\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
	echo [%DATE% %TIME%] Failed to activate venv >> "%LOGFILE%"
	set EXIT_CODE=21
	set FINAL_MSG=venv_activation_failed
	goto end
)

:: Install core packages
python -m pip install --upgrade pip >> "%LOGFILE%" 2>&1
python -m pip install fastapi uvicorn[standard] jinja2 pandas pyyaml pywin32 pywinauto --quiet >> "%LOGFILE%" 2>&1
IF %ERRORLEVEL% NEQ 0 (
	echo [%DATE% %TIME%] Some pip installs failed (see log) >> "%LOGFILE%"
	set EXIT_CODE=22
	set FINAL_MSG=pip_install_failed
	:: continue but mark failure
)

:: 4) Detect PLECS paths (allow override via --plecs-path)
set FOUND_PLECS=
if "%PLECS_PATH_ARG%" NEQ "" (
	if exist "%PLECS_PATH_ARG%" (
		set FOUND_PLECS=%PLECS_PATH_ARG%
		goto foundplecs
	) else (
		echo [%DATE% %TIME%] Provided plecs-path does not exist: %PLECS_PATH_ARG% >> "%LOGFILE%"
	)
)

set PLECS_CAND1="C:\\Program Files\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe"
set PLECS_CAND2="C:\\Program Files\\Plexim\\PLECS 4.6 (64 bit)\\plecs.exe"
set PLECS_CAND3="D:\\OneDrive\\Documenti\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe"
for %%P in (%PLECS_CAND1% %PLECS_CAND2% %PLECS_CAND3%) do (
	if exist %%~P (
		set FOUND_PLECS=%%~P
		goto foundplecs
	)
)

:askplecs
if "%YES_FLAG%"=="1" (
	echo [%DATE% %TIME%] Non-interactive mode and no plecs path found; skipping plecs detection. >> "%LOGFILE%"
	set EXIT_CODE=30
	set FINAL_MSG=plecs_not_found
	goto afterplecs
) else (
	echo Non ho trovato PLECS nelle posizioni comuni.
	set /p USER_PLECS=Inserisci il percorso completo verso plecs.exe (o premi ENTER per saltare): 
	if "%USER_PLECS%"=="" (
		echo Hai scelto di non specificare il percorso ora. Ricorda di aggiornare config/default.yml con il path del tuo plecs.exe.
		goto afterplecs
	) else (
		if exist "%USER_PLECS%" (
			set FOUND_PLECS=%USER_PLECS%
			goto foundplecs
		) else (
			echo Percorso non valido: %USER_PLECS%
			set /p TRY_AGAIN=Vuoi riprovare? [y/N]: 
			if /I "%TRY_AGAIN%"=="y" goto askplecs
			goto afterplecs
		)
	)
)

:foundplecs
echo [%DATE% %TIME%] Found PLECS at: %FOUND_PLECS% >> "%LOGFILE%"

:: Update config/default.yml using embedded Python to edit YAML reliably
if defined FOUND_PLECS (
	echo [%DATE% %TIME%] Aggiorno config/default.yml con il percorso rilevato... >> "%LOGFILE%"
	python - <<PY >> "%LOGFILE%" 2>&1
import sys, yaml, pathlib
cfg_path=pathlib.Path('config/default.yml')
if not cfg_path.exists():
	print('config/default.yml non trovato, ne creo uno minimale...')
	cfg_path.parent.mkdir(parents=True, exist_ok=True)
	cfg_path.write_text('plecs:\n  executable_paths: []\n')
text = cfg_path.read_text()
try:
	cfg = yaml.safe_load(text) or {}
except Exception as e:
	print('Errore parsing YAML:', e)
	cfg = {}
cfg.setdefault('plecs', {})
# set executable_paths to single entry list
cfg['plecs']['executable_paths'] = [r'%FOUND_PLECS%']
with open(cfg_path, 'w', encoding='utf-8') as f:
	yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('config/default.yml aggiornato con PLECS path')
PY
)

:afterplecs

if "%USE_PS%"=="1" (
	echo [%DATE% %TIME%] Calling PowerShell installer with provided args... >> "%LOGFILE%"
	set PS_ARGS=
	if "%YES_FLAG%"=="1" set PS_ARGS=%PS_ARGS% -Yes
	if defined FOUND_PLECS set PS_ARGS=%PS_ARGS% -PlecsPath "%FOUND_PLECS%"
	powershell -ExecutionPolicy Bypass -File "%~dp0\windows_installer.ps1" %PS_ARGS%
	if %ERRORLEVEL% NEQ 0 (
		echo [%DATE% %TIME%] PowerShell installer returned error code %ERRORLEVEL% >> "%LOGFILE%"
		set EXIT_CODE=40
		set FINAL_MSG=powershell_installer_failed
		goto end
	) else (
		echo [%DATE% %TIME%] PowerShell installer finished successfully >> "%LOGFILE%"
	)
) else (
	:: 5) Offer to run tests
	if "%YES_FLAG%"=="1" (
		echo [%DATE% %TIME%] Non-interactive mode: skipping tests. >> "%LOGFILE%"
	) else (
		set /p RUNTEST=Vuoi eseguire ora `pytest tests/test_basic.py` per verificare pywinauto/PLECS? [y/N]: 
		if /I "%RUNTEST%"=="y" (
			echo [%DATE% %TIME%] Running tests... >> "%LOGFILE%"
			python -m pytest tests/test_basic.py -q >> "%LOGFILE%" 2>&1
			if %ERRORLEVEL% NEQ 0 (
				echo [%DATE% %TIME%] Tests failed (see log) >> "%LOGFILE%"
				set EXIT_CODE=50
				set FINAL_MSG=tests_failed
			) else (
				echo [%DATE% %TIME%] Tests passed >> "%LOGFILE%"
			)
		) else (
			echo [%DATE% %TIME%] User skipped tests >> "%LOGFILE%"
		)
	)
)

:end
if "%EXIT_CODE%"=="0" (
	echo [%DATE% %TIME%] Installer finished successfully >> "%LOGFILE%"
	set FINAL_MSG=ok
) else (
	echo [%DATE% %TIME%] Installer finished with exit code %EXIT_CODE% (%FINAL_MSG%) >> "%LOGFILE%"
)

:: write a small JSON status file (best-effort)
powershell -NoProfile -Command "Try { $s = @{ timestamp = (Get-Date).ToString('o'); exit_code = %EXIT_CODE%; message = '%FINAL_MSG%'}; $s | ConvertTo-Json | Out-File -FilePath '%STATUSFILE%' -Encoding utf8 } Catch { Out-File -FilePath '%STATUSFILE%' -InputObject ('{"exit_code":-1,"message":"status_write_failed"}') -Encoding utf8 }"

echo Press any key to close...
pause >nul
ENDLOCAL
exit /b %EXIT_CODE%
