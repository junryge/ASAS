# OpenHarness Installer v0.1.0 (PowerShell)
# Usage: Right-click -> Run with PowerShell
#   or: powershell -ExecutionPolicy Bypass -File install.ps1

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  OpenHarness Installer v0.1.0            ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OhHome = Join-Path $env:USERPROFILE ".openharness"

# 1. Create user config directory
Write-Host "→ Creating config directory: $OhHome"
foreach ($dir in @("skills", "plugins", "sessions")) {
    $path = Join-Path $OhHome $dir
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# 2. Create TOKEN.TXT if not exists
$tokenPath = Join-Path $OhHome "TOKEN.TXT"
if (!(Test-Path $tokenPath)) {
    New-Item -ItemType File -Path $tokenPath -Force | Out-Null
    Write-Host "→ Created TOKEN.TXT (empty)" -ForegroundColor Yellow
    Write-Host "  ⚠  Place your API key in: $tokenPath" -ForegroundColor Yellow
} else {
    Write-Host "→ TOKEN.TXT already exists" -ForegroundColor Green
}

# 3. Install package
Write-Host "→ Installing OpenHarness..."
try {
    & pip install -e $ScriptDir 2>&1 | Out-Null
    Write-Host "  ✅ pip install succeeded" -ForegroundColor Green
} catch {
    Write-Host "  Trying pip install --user..." -ForegroundColor Yellow
    try {
        & pip install -e $ScriptDir --user 2>&1 | Out-Null
        Write-Host "  ✅ pip install --user succeeded" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠  pip install failed. Use PYTHONPATH method:" -ForegroundColor Red
        Write-Host "     `$env:PYTHONPATH = `"$ScriptDir\src;`$env:PYTHONPATH`"" -ForegroundColor Gray
        Write-Host "     python -m openharness" -ForegroundColor Gray
    }
}

# 4. Verify
Write-Host ""
Write-Host "→ Verifying installation..."
$ohCmd = Get-Command oh -ErrorAction SilentlyContinue
if ($ohCmd) {
    Write-Host "  ✅ 'oh' command installed successfully" -ForegroundColor Green
} else {
    Write-Host "  ⚠  'oh' command not found in PATH" -ForegroundColor Yellow
    Write-Host "     Try: python -m openharness" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  Installation Complete!                  ║" -ForegroundColor Cyan
Write-Host "  ║                                          ║" -ForegroundColor Cyan
Write-Host "  ║  1. Add API key:                         ║" -ForegroundColor Cyan
Write-Host "  ║     $tokenPath" -ForegroundColor White
Write-Host "  ║  2. Run: oh                              ║" -ForegroundColor Cyan
Write-Host "  ║  3. Help: oh --help                      ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
