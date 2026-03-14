Windows installer quick usage

This directory contains helper installers for Windows:

- `windows_installer.bat` - double-clickable, interactive or scriptable batch wrapper. Supports flags:
  - `--yes` : assume yes for prompts (non-interactive)
  - `--plecs-path "C:\path\to\plecs.exe"` : predefine PLECS executable path
  - `--ps` : delegate to the PowerShell installer for advanced checks

- `windows_installer.ps1` - advanced PowerShell installer. Features:
  - download Python installer with retries
  - SHA256 checksum verification and optional Authenticode signature check
  - creates `.venv` and installs core Python packages
  - updates `config/default.yml` with detected/provided PLECS path
  - writes `installer_windows.log` and `installer_windows_status.json` in the project root

Examples

Interactive double-click:
- Double-click `windows_installer.bat` and follow prompts.

Non-interactive (assume yes):
```powershell
# from project root
tools\installers\windows_installer.bat --yes --plecs-path "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe"
```

Run the PowerShell installer directly and export status JSON:
```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\installers\windows_installer.ps1 -Yes -PlecsPath "C:\Program Files\Plexim\PLECS 4.7 (64 bit)\plecs.exe" -PythonUrl "https://www.python.org/ftp/python/3.10.12/python-3.10.12-amd64.exe" -Checksum <sha256>
```

CI integration

After execution the PowerShell installer writes `installer_windows_status.json` containing:
```json
{ "timestamp": "...", "exit_code": 0, "message": "ok" }
```

Check `installer_windows.log` for detailed logs and `installer_windows_status.json` for a CI-friendly status.
