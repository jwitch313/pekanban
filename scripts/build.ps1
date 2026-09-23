# build.ps1 - Build the PeKanBan Windows executable with PyInstaller.
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1
#
# Output: dist\PeKanBan\PeKanBan.exe  (one-directory layout)
#
# Prerequisites:
#   - uv installed and on PATH
#   - `uv sync` has been run (installs PySide6, SQLAlchemy, PyInstaller)

$ErrorActionPreference = "Stop"

Write-Host "==> Syncing dependencies (uv sync)..." -ForegroundColor Cyan
uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

Write-Host "==> Building executable (pyinstaller kanban.spec)..." -ForegroundColor Cyan
uv run pyinstaller kanban.spec --noconfirm
if ($LASTEXITCODE -ne 0) { throw "pyinstaller build failed" }

$exe = Join-Path $PSScriptRoot "..\dist\PeKanBan\PeKanBan.exe"
$exe = (Resolve-Path $exe).Path

if (Test-Path $exe) {
    Write-Host "==> Build complete." -ForegroundColor Green
    Write-Host "    Executable: $exe"
    Write-Host "    Folder:     dist\PeKanBan - copy the whole folder to deploy."
} else {
    throw "Expected output not found: $exe"
}
