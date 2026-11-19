$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

py -3.11 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --name WiredCam `
  --add-data "index.html;." `
  --add-data "assets;assets" `
  --collect-all av `
  launcher.py

Write-Host "Created dist\WiredCam\WiredCam.exe"
Write-Host "Copy Android platform-tools beside the EXE, or install it on PATH."
