<#
Advanced PyPLECS Windows installer (PowerShell)
Features:
- Accepts switches for non-interactive use: -Yes (assume yes), -PlecsPath
- Download with retries and logging
- SHA256 checksum verification of downloaded installer (user-supplied or fetched)
- Optional Authenticode signature check
- Creates virtualenv, installs packages, updates config/default.yml
- Run tests optionally

Usage examples:
.	./windows_installer.ps1 -Yes -PlecsPath "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe" -PythonUrl https://www.python.org/ftp/python/3.10.12/python-3.10.12-amd64.exe -Checksum <sha256>
.	./windows_installer.ps1   # interactive
#>
param(
    [switch]$Yes,
    [string]$PlecsPath,
    [string]$PythonUrl = 'https://www.python.org/ftp/python/3.10.12/python-3.10.12-amd64.exe',
    [string]$Checksum = '',
    [switch]$SkipAuthSignatureCheck,
    [switch]$RunTests,
    [switch]$ForceVenv
)

# Logging
function Log { param($msg) Write-Output $msg; Try { Add-Content -Path $logFile -Value ("$(Get-Date -Format o) - $msg") } Catch { Write-Output "Failed to write to log: $msg" } }

# Utilities
function Download-FileWithRetry {
    param(
        [string]$Url,
        [string]$Destination,
        [int]$Retries = 3,
        [int]$DelaySeconds = 3
    )
    for ($i=1; $i -le $Retries; $i++) {
        try {
            Log "Downloading $Url (attempt $i) -> $Destination"
            Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -ErrorAction Stop
            return $true
        } catch {
            Log "Download attempt $i failed: $_"
            if ($i -lt $Retries) { Start-Sleep -Seconds $DelaySeconds }
        }
    }
    return $false
}

function Get-FileSHA256 {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return '' }
    try {
        $hash = Get-FileHash -Path $Path -Algorithm SHA256
        return $hash.Hash.ToLower()
    } catch {
        Log "Error computing SHA256: $_"
        return ''
    }
}

function Verify-AuthenticodeSignature {
    param([string]$Path)
    try {
        $sig = Get-AuthenticodeSignature -FilePath $Path
        return $sig.Status -eq 'Valid'
    } catch {
        Log "Authenticode check error: $_"
        return $false
    }
}

# Elevation helper
function Ensure-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Log "Not running as admin. Relaunching elevated..."
        Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" @PSBoundParameters" -Verb RunAs
        exit 0
    }
}

# Begin

# Compute project root (installers -> tools -> project root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$scriptDirResolved = (Resolve-Path -Path $scriptDir).Path
$toolsDir = Split-Path -Parent $scriptDirResolved
$projRoot = Split-Path -Parent $toolsDir
Set-Location -Path $projRoot

# Initialize log and status files inside project tools folder
$logFile = Join-Path -Path $projRoot -ChildPath 'tools\installer_windows.log'
$statusFile = Join-Path -Path $projRoot -ChildPath 'tools\installer_windows_status.json'
function Log { param($msg) Write-Output $msg; Try { Add-Content -Path $logFile -Value ("$(Get-Date -Format o) - $msg") } Catch { Write-Output "Failed to write to log: $msg" } }
Log "Starting advanced Windows installer"
Log "Project root: $projRoot"

# initialize status
$global:ExitCode = 0
$global:StatusMessage = 'ok'

function Write-StatusJson {
    param([int]$code, [string]$message)
    $obj = @{ timestamp = (Get-Date).ToString('o'); exit_code = $code; message = $message }
    Try {
        $obj | ConvertTo-Json | Out-File -FilePath $statusFile -Encoding utf8 -Force
    } Catch {
        Log "Failed to write status JSON: $_"
    }
}

# 1) Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    if ($Yes) {
        Log "Python not found, non-interactive mode: proceeding to download."
    } else {
        $r = Read-Host "Python non trovato. Vuoi scaricarlo dal sito ufficiale e avviare l'installer? (y/N)"
        if ($r -notin @('y','Y','yes','Yes')) { Log "User declined Python download. Exiting."; exit 1 }
    }
    $installer = Join-Path -Path $env:TEMP -ChildPath (Split-Path -Path $PythonUrl -Leaf)
    $ok = Download-FileWithRetry -Url $PythonUrl -Destination $installer -Retries 4 -DelaySeconds 5
    if (-not $ok) { Log "Download failed"; $global:ExitCode = 2; $global:StatusMessage = 'python_download_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }

    if ($Checksum) {
        $actual = Get-FileSHA256 -Path $installer
    if ($actual -ne $Checksum.ToLower()) { Log "Checksum mismatch: expected $Checksum got $actual"; $global:ExitCode = 3; $global:StatusMessage = 'checksum_mismatch'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
    Log "Checksum verified"
    }

    if (-not $SkipAuthSignatureCheck) {
        $sigOk = Verify-AuthenticodeSignature -Path $installer
    if ($sigOk) { Log "Authenticode signature valid" } else { Log "Authenticode signature invalid or not present"; if (-not $SkipAuthSignatureCheck) { $global:ExitCode = 4; $global:StatusMessage = 'auth_signature_invalid'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode } }
    }

    # Run installer elevated
    Log "Running Python installer (elevated). This may prompt UAC."
    Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Verb RunAs -Wait
    Remove-Item -Path $installer -ErrorAction SilentlyContinue
} else {
    Log "Python found: $($python.Path)"
}

# 2) Create venv
$venvPath = Join-Path -Path $projRoot -ChildPath '.venv'
if ((Test-Path $venvPath) -and $ForceVenv) {
    Log "Force flag set: removing existing venv at $venvPath"
    try { Remove-Item -Recurse -Force -Path $venvPath -ErrorAction Stop; Log "Removed existing venv." } catch { Log "Failed to remove existing venv: $_" }
}
if (-not (Test-Path $venvPath)) {
    Log "Creating venv at $venvPath"
    try {
        $venvResult = & python -m venv $venvPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log "[ERROR] venv creation failed with exit code $LASTEXITCODE. Output: $venvResult"
            $global:ExitCode = 9; $global:StatusMessage = 'venv_creation_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
        } else {
            Log "venv created successfully at $venvPath"
        }
    } catch {
        Log "[EXCEPTION] Exception during venv creation: $_"
        $global:ExitCode = 9; $global:StatusMessage = 'venv_creation_exception'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
    }
} else {
    Log "venv already exists at $venvPath"
}

# 3) Activate and install requirements
$activate = Join-Path -Path $venvPath -ChildPath 'Scripts\Activate.ps1'
if (Test-Path $activate) {
    Log "Activating venv and installing dependencies"
    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    try {
        & $venvPython -m pip install --upgrade pip
        & $venvPython -m pip install fastapi uvicorn[standard] jinja2 pandas pyyaml pywin32 pywinauto --progress-bar off
        if ($LASTEXITCODE -ne 0) { Log "pip install inside venv failed with exit code $LASTEXITCODE"; $global:ExitCode = 5; $global:StatusMessage = 'pip_install_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
    } catch {
        Log "Exception during pip install in venv: $_"
        $global:ExitCode = 5; $global:StatusMessage = 'pip_install_exception'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
    }
} else {
    Log "Activate script not found in venv: $activate"
    $global:ExitCode = 6; $global:StatusMessage = 'activate_missing'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
}

# 4) Handle PLECS path
if ($PlecsPath) {
    if (-not (Test-Path $PlecsPath)) { Log "Provided PLECS path not found: $PlecsPath"; $global:ExitCode = 7; $global:StatusMessage = 'plecs_path_invalid'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
    $found = $PlecsPath
} else {
    # search common paths
    $commonPaths = @(
        'C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe',
        'C:\Program Files\Plexim\PLECS 4.6 (64 bit)\plecs.exe',
        'C:\Program Files\Plexim\PLECS 4.5 (64 bit)\plecs.exe',
        'D:\OneDrive\Documenti\Plexim\PLECS 4.7 (64 bit)\plecs.exe',
        'D:\Plexim\PLECS 4.7 (64 bit)\PLECS.exe',
        'D:\Plexim\PLECS 4.7 (64 bit)\plecs.exe',
        'D:\Plexim\PLECS 4.6 (64 bit)\PLECS.exe',
        'D:\Plexim\PLECS 4.6 (64 bit)\plecs.exe'
    )
    $found = $null
    foreach ($p in $commonPaths) { 
        if (Test-Path $p) { 
            $found = $p
            Log "Found PLECS at: $found"
            break 
        } 
    }
    if (-not $found) {
        if (-not $Yes) {
            $u = Read-Host "Non ho trovato PLECS. Inserisci il percorso completo a plecs.exe (o premi ENTER per saltare)"
            if ($u) { $found = $u }
        }
    }
}

if ($found) {
    Log "Updating config/default.yml with PLECS path: $found"
    $pyCode = @"
import yaml, pathlib
cfg_path=pathlib.Path('config/default.yml')
if not cfg_path.exists():
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text('plecs:\n  executable_paths: []\n')
text = cfg_path.read_text()
try:
    cfg = yaml.safe_load(text) or {}
except Exception:
    cfg = {}
cfg.setdefault('plecs', {})
cfg['plecs']['executable_paths'] = [r'$found']
with open(cfg_path,'w',encoding='utf-8') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('updated')
"@
    $tempPy = Join-Path $env:TEMP 'update_config.py'
    Set-Content -Path $tempPy -Value $pyCode -Encoding UTF8
    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    & $venvPython $tempPy
    Remove-Item $tempPy -ErrorAction SilentlyContinue
}

# 5) Run tests if requested
if ($RunTests) {
    Log "Running smoke tests"
    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    try {
        & $venvPython -m pytest tests/test_smoke.py -v
        if ($LASTEXITCODE -ne 0) { Log "Smoke tests failed with exit code $LASTEXITCODE"; $global:ExitCode = 8; $global:StatusMessage = 'tests_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
        Log "Smoke tests passed successfully"
    } catch {
        Log "Exception during smoke tests: $_"
        $global:ExitCode = 8; $global:StatusMessage = 'tests_exception'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
    }
}

Log "Installer finished"
Write-StatusJson $global:ExitCode $global:StatusMessage
exit $global:ExitCode
