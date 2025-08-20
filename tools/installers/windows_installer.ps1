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
    [switch]$RunTests
)

# Logging
$logFile = Join-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) -ChildPath '..\installer_windows.log'
$logFile = (Resolve-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition)).Path + '\installer_windows.log'
$statusFile = (Resolve-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition)).Path + '\installer_windows_status.json'
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
Log "Starting advanced Windows installer"
$projRoot = (Resolve-Path -Path (Join-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) -ChildPath '..')).Path
Log "Project root: $projRoot"
Set-Location -Path $projRoot

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
if (-not (Test-Path $venvPath)) {
    Log "Creating venv at $venvPath"
    & python -m venv $venvPath
}

# 3) Activate and install requirements
$activate = Join-Path -Path $venvPath -ChildPath 'Scripts\Activate.ps1'
if (Test-Path $activate) {
    Log "Activating venv"
    & powershell -NoProfile -ExecutionPolicy Bypass -Command "& '$activate'; python -m pip install --upgrade pip; python -m pip install fastapi uvicorn[standard] jinja2 pandas pyyaml pywin32 pywinauto --quiet"
    if ($LASTEXITCODE -ne 0) { Log "pip install inside venv failed"; $global:ExitCode = 5; $global:StatusMessage = 'pip_install_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
} else {
    Log "Activate script not found in venv"
    $global:ExitCode = 6; $global:StatusMessage = 'activate_missing'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode
}

# 4) Handle PLECS path
if ($PlecsPath) {
    if (-not (Test-Path $PlecsPath)) { Log "Provided PLECS path not found: $PlecsPath"; $global:ExitCode = 7; $global:StatusMessage = 'plecs_path_invalid'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
    $found = $PlecsPath
} else {
    # search common paths
    $c1 = 'C:\\Program Files\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe'
    $c2 = 'C:\\Program Files\\Plexim\\PLECS 4.6 (64 bit)\\plecs.exe'
    $c3 = 'D:\\OneDrive\\Documenti\\Plexim\\PLECS 4.7 (64 bit)\\plecs.exe'
    $found = $null
    foreach ($p in @($c1,$c2,$c3)) { if (Test-Path $p) { $found = $p; break } }
    if (-not $found) {
        if (-not $Yes) {
            $u = Read-Host "Non ho trovato PLECS. Inserisci il percorso completo a plecs.exe (o premi ENTER per saltare)"
            if ($u) { $found = $u }
        }
    }
}

if ($found) {
    Log "Updating config/default.yml with PLECS path: $found"
    python - <<PY
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
cfg['plecs']['executable_paths'] = [r'%found%']
with open(cfg_path,'w',encoding='utf-8') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('updated')
PY
}

# 5) Run tests if requested
if ($RunTests) {
    Log "Running pytest tests/test_basic.py"
    & powershell -NoProfile -ExecutionPolicy Bypass -Command "& '$activate'; python -m pytest tests/test_basic.py -q"
    if ($LASTEXITCODE -ne 0) { Log "Tests failed"; $global:ExitCode = 8; $global:StatusMessage = 'tests_failed'; Write-StatusJson $global:ExitCode $global:StatusMessage; exit $global:ExitCode }
}

Log "Installer finished"
Write-StatusJson $global:ExitCode $global:StatusMessage
exit $global:ExitCode
