@echo off
title OpenHarness Installer v0.1.0

echo.
echo  ==========================================
echo   OpenHarness Installer v0.1.0
echo  ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "OH_HOME=%USERPROFILE%\.openharness"

rem 1. Create user config directory
echo [1/5] Creating config directory: %OH_HOME%
if not exist "%OH_HOME%" mkdir "%OH_HOME%"
if not exist "%OH_HOME%\skills" mkdir "%OH_HOME%\skills"
if not exist "%OH_HOME%\plugins" mkdir "%OH_HOME%\plugins"
if not exist "%OH_HOME%\sessions" mkdir "%OH_HOME%\sessions"
echo       OK

rem 2. Create TOKEN.TXT if not exists
echo [2/5] Checking TOKEN.TXT...
if not exist "%OH_HOME%\TOKEN.TXT" (
    type nul > "%OH_HOME%\TOKEN.TXT"
    echo       Created: %OH_HOME%\TOKEN.TXT
    echo       ** API key required! Run: notepad %OH_HOME%\TOKEN.TXT
) else (
    echo       Already exists: %OH_HOME%\TOKEN.TXT
)

rem 3. Try pip install
echo [3/5] Trying pip install...
pip install -e "%SCRIPT_DIR%" >nul 2>&1
if %errorlevel%==0 (
    echo       OK - pip install succeeded
    goto :verify
)
pip install -e "%SCRIPT_DIR%" --user >nul 2>&1
if %errorlevel%==0 (
    echo       OK - pip install --user succeeded
    goto :verify
)
echo       pip failed (proxy/network) - using local mode instead

rem 4. Create oh.bat launcher (pip failed, use PYTHONPATH instead)
:create_launcher
echo [4/5] Creating oh.bat launcher...

set "OH_BAT=%OH_HOME%\oh.bat"

echo @echo off> "%OH_BAT%"
echo set "PYTHONPATH=%SCRIPT_DIR%src;%%PYTHONPATH%%">> "%OH_BAT%"
echo python -m openharness %%*>> "%OH_BAT%"

echo       Created: %OH_BAT%

rem 5. Add to PATH (current session + permanently via registry)
echo [5/5] Adding to PATH...

rem Add to current session
set "PATH=%OH_HOME%;%PATH%"

rem Check if already in user PATH
echo %PATH% | findstr /i /c:"%OH_HOME%" >nul 2>&1
if %errorlevel%==0 (
    echo       Already in PATH
) else (
    rem Add to user PATH permanently
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%B"
    if defined CURRENT_PATH (
        setx PATH "%CURRENT_PATH%;%OH_HOME%" >nul 2>&1
    ) else (
        setx PATH "%OH_HOME%" >nul 2>&1
    )
    echo       Added %OH_HOME% to user PATH
    echo       ** New CMD windows will have 'oh' available
)
goto :done

:verify
echo [4/5] Skipping launcher (pip installed)
echo [5/5] Verifying...
where oh >nul 2>&1
if %errorlevel%==0 (
    echo       [OK] 'oh' command ready
) else (
    echo       'oh' not in PATH yet - creating launcher...
    goto :create_launcher
)

:done
echo.
echo  ==========================================
echo   Installation Complete!
echo  ==========================================
echo.
echo   Installed to: %SCRIPT_DIR%
echo   Config dir:   %OH_HOME%
echo   Launcher:     %OH_HOME%\oh.bat
echo.
echo   NEXT STEPS:
echo.
echo   1. Set API key (required):
echo      notepad %OH_HOME%\TOKEN.TXT
echo      (paste your API key and save)
echo.
echo   2. CLOSE this CMD and open a NEW one
echo.
echo   3. Run:
echo      oh
echo.
echo  ==========================================
echo.
pause
