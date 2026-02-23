@echo off
chcp 65001 >nul
echo Nomos LLM PRO 시작 중...
cd /d "%~dp0\.."
python -m app.main
if errorlevel 1 (
    echo.
    echo [오류] 실행에 실패했습니다.
    echo 설치가 완료되었는지 확인해주세요: setup\install.bat
    pause
)
