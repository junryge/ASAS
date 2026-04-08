@echo off
title OpenHarness Installer v0.1.0

echo.
echo  ==========================================
echo   OpenHarness Installer v0.1.0
echo  ==========================================
echo.

set "INSTALL_DIR=D:\openharness"
set "SCRIPT_DIR=%~dp0"
set "OH_HOME=%INSTALL_DIR%"

rem 1. Copy to D:\openharness
echo [1/4] Installing to %INSTALL_DIR% ...
if not "%SCRIPT_DIR%"=="%INSTALL_DIR%\" (
    if exist "%INSTALL_DIR%" (
        echo       %INSTALL_DIR% already exists, updating...
    )
    xcopy "%SCRIPT_DIR%*" "%INSTALL_DIR%\" /E /I /Y /Q >nul 2>&1
)
echo       OK

rem 2. Create config folders and TOKEN.TXT
echo [2/4] Creating config...
if not exist "%INSTALL_DIR%\sessions" mkdir "%INSTALL_DIR%\sessions"
if not exist "%INSTALL_DIR%\TOKEN.TXT" (
    type nul > "%INSTALL_DIR%\TOKEN.TXT"
    echo       Created: %INSTALL_DIR%\TOKEN.TXT
    echo       ** API key required!
) else (
    echo       TOKEN.TXT exists
)

rem 3. Create oh.bat launcher in D:\openharness
echo [3/4] Creating oh.bat ...
set "OH_BAT=%INSTALL_DIR%\oh.bat"

> "%OH_BAT%" (
    echo @echo off
    echo set "PYTHONPATH=%INSTALL_DIR%\src;%%PYTHONPATH%%"
    echo python -m openharness %%*
)
echo       Created: %OH_BAT%

rem 4. Add D:\openharness to PATH
echo [4/4] Adding to PATH...
set "PATH=%INSTALL_DIR%;%PATH%"

echo %PATH% | findstr /i /c:"%INSTALL_DIR%" >nul 2>&1
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%B"
echo %CURRENT_PATH% | findstr /i /c:"%INSTALL_DIR%" >nul 2>&1
if %errorlevel%==0 (
    echo       Already in PATH
) else (
    if defined CURRENT_PATH (
        setx PATH "%CURRENT_PATH%;%INSTALL_DIR%" >nul 2>&1
    ) else (
        setx PATH "%INSTALL_DIR%" >nul 2>&1
    )
    echo       Added %INSTALL_DIR% to user PATH
)

echo.
echo  ==========================================
echo   Installation Complete!
echo  ==========================================
echo.
echo   Installed:  %INSTALL_DIR%
echo   Launcher:   %INSTALL_DIR%\oh.bat
echo   Token file: %INSTALL_DIR%\TOKEN.TXT
echo.
echo   NEXT STEPS:
echo.
echo   1. API key setting:
echo      notepad %INSTALL_DIR%\TOKEN.TXT
echo.
echo   2. Close this CMD, open NEW CMD
echo.
echo   3. Type: oh
echo.
echo  ==========================================
echo.
pause
