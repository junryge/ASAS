@echo off
chcp 65001 >nul 2>&1
title OpenHarness Installer v0.1.0

echo ╔══════════════════════════════════════════╗
echo ║  OpenHarness Installer v0.1.0            ║
echo ╚══════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
set "OH_HOME=%USERPROFILE%\.openharness"

:: 1. Create user config directory
echo → Creating config directory: %OH_HOME%
if not exist "%OH_HOME%" mkdir "%OH_HOME%"
if not exist "%OH_HOME%\skills" mkdir "%OH_HOME%\skills"
if not exist "%OH_HOME%\plugins" mkdir "%OH_HOME%\plugins"
if not exist "%OH_HOME%\sessions" mkdir "%OH_HOME%\sessions"

:: 2. Create TOKEN.TXT if not exists
if not exist "%OH_HOME%\TOKEN.TXT" (
    type nul > "%OH_HOME%\TOKEN.TXT"
    echo → Created TOKEN.TXT (empty)
    echo   ⚠  Place your API key in: %OH_HOME%\TOKEN.TXT
) else (
    echo → TOKEN.TXT already exists
)

:: 3. Install package
echo → Installing OpenHarness...
pip install -e "%SCRIPT_DIR%" 2>nul
if errorlevel 1 (
    echo   pip install failed. Trying with --user flag...
    pip install -e "%SCRIPT_DIR%" --user 2>nul
)
if errorlevel 1 (
    echo   ⚠  pip install failed. Use PYTHONPATH method instead:
    echo      set PYTHONPATH=%SCRIPT_DIR%src;%%PYTHONPATH%%
    echo      python -m openharness
)

:: 4. Verify
echo.
echo → Verifying installation...
where oh >nul 2>&1
if %errorlevel%==0 (
    echo   ✅ 'oh' command installed successfully
) else (
    echo   ⚠  'oh' command not found in PATH
    echo      Try: python -m openharness
    echo      Or add Python Scripts to PATH
)

echo.
echo ╔══════════════════════════════════════════╗
echo ║  Installation Complete!                  ║
echo ║                                          ║
echo ║  1. Add API key:                         ║
echo ║     %OH_HOME%\TOKEN.TXT                  ║
echo ║  2. Run: oh                              ║
echo ║  3. Help: oh --help                      ║
echo ╚══════════════════════════════════════════╝
echo.
pause
