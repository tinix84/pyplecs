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
+        set /p TRY_AGAIN=Vuoi riprovare? [y/N]: 
+        if /I "%TRY_AGAIN%"=="y" goto askplecs
+        goto :afterplecs
+    )
+)
+
+:foundplecs
+echo Found PLECS at: %FOUND_PLECS%
+
+:: Update config/default.yml using embedded Python to edit YAML reliably
+if defined FOUND_PLECS (
+    echo Aggiorno config/default.yml con il percorso rilevato...
+    python - <<PY
+import sys, yaml, pathlib
+cfg_path=pathlib.Path('config/default.yml')
+if not cfg_path.exists():
+    print('config/default.yml non trovato, ne creo uno minimale...')
+    cfg_path.parent.mkdir(parents=True, exist_ok=True)
+    cfg_path.write_text('plecs:\n  executable_paths: []\n')
+text = cfg_path.read_text()
+try:
+    cfg = yaml.safe_load(text) or {}
+except Exception as e:
+    print('Errore parsing YAML:', e)
+    cfg = {}
+cfg.setdefault('plecs', {})
+# set executable_paths to single entry list
+cfg['plecs']['executable_paths'] = [r'%FOUND_PLECS%']
+with open(cfg_path, 'w', encoding='utf-8') as f:
+    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
+print('config/default.yml aggiornato con PLECS path')
+PY
+)
+
+:afterplecs
+
+:: 5) Offer to run tests
+set /p RUNTEST=Vuoi eseguire ora `pytest tests/test_basic.py` per verificare pywinauto/PLECS? [y/N]: 
+if /I "%RUNTEST%"=="y" (
+    echo Eseguo pytest... (potrebbe aprire finestre GUI e richiedere input)
+    python -m pytest tests/test_basic.py -q
+) else (
+    echo Skip dei test richiesti.
+)
+
+:end
+echo Fatto. Premi un tasto per chiudere...
+pause >nul
+ENDLOCAL
