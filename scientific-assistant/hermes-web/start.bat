@echo off
chcp 65001 >nul 2>&1
title Hermes Web

set PORT=8788
if not "%~1"=="" set PORT=%~1

echo ======================================================================
echo   Hermes Web 시작 (port %PORT%)
echo ======================================================================
echo.

REM 1) 프록시(:8765) 살아있나 확인 — 없으면 같은 폴더의 hermes_proxy.py 실행
echo [1/2] 프록시(:8765) 확인...
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8765/ > "%TEMP%\hermes_proxy_check.tmp" 2>nul
set /p PROXY_CODE=<"%TEMP%\hermes_proxy_check.tmp"
del "%TEMP%\hermes_proxy_check.tmp" >nul 2>&1

if "%PROXY_CODE%"=="200" (
    echo       프록시 살아있음 ✓
) else (
    echo       프록시 없음 → 새 창에서 시작...
    start "Hermes Proxy" cmd /c "cd /d %~dp0 && python hermes_proxy.py"
    timeout /t 3 /nobreak >nul
)

REM 2) Hermes Web 서버 시작
echo [2/2] Hermes Web 서버 시작 (port %PORT%)...
echo.

python "%~dp0server.py" %PORT%
pause
