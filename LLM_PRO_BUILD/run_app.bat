@echo off
chcp 65001 >nul
echo ========================================
echo   Nomos LLM Desktop v1.0
echo ========================================
echo.

cd /d "%~dp0"

REM Python 3.11 경로 설정
set "PYTHON=C:\Python\Python3119\python.exe"

REM Python 확인
"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11이 설치되어 있지 않습니다.
    echo 경로를 확인하세요: %PYTHON%
    pause
    exit /b 1
)

REM 앱 실행
echo [INFO] 앱을 시작합니다...
"%PYTHON%" -m app.main

if errorlevel 1 (
    echo.
    echo [ERROR] 앱 실행 중 오류가 발생했습니다.
    echo 의존성을 확인하세요: %PYTHON% -m pip install -r requirements.txt
    pause
)
