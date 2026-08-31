param([string]$Python = "$PSScriptRoot\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $Python -m PyInstaller --noconfirm --onefile --windowed `
        --name CFRP_Router_CAM --collect-all ezdxf --collect-all OCP cfrp_router_cam.py
    if ($LASTEXITCODE -ne 0) { throw "EXE build failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
