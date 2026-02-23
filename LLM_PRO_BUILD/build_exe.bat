@echo off
chcp 65001 >nul
echo ========================================
echo   Nomos LLM - Windows EXE 빌드
echo ========================================
echo.

cd /d "%~dp0"

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되어 있지 않습니다!
    echo         https://www.python.org/downloads/ 에서 Python 3.10+ 설치
    pause
    exit /b 1
)

REM 1단계: 의존성 설치
echo [1/4] 의존성 설치 중...
pip install PySide6>=6.6.0 markdown>=3.5 Pygments>=2.17 requests>=2.31 httpx>=0.25 "pyinstaller>=6.0" --quiet
if errorlevel 1 (
    echo [WARNING] 일부 의존성 설치 실패 - 계속 진행합니다...
)

REM 선택적 의존성 (실패해도 무시)
echo [1/4] 선택적 의존성 설치 중 (llama-cpp-python, aider-chat)...
pip install llama-cpp-python>=0.2.0 --quiet 2>nul
pip install aider-chat>=0.40.0 --quiet 2>nul

REM 2단계: 이전 빌드 정리
echo.
echo [2/4] 이전 빌드 정리...
if exist dist\NomosLLM rmdir /s /q dist\NomosLLM
if exist build\nomos rmdir /s /q build\nomos

REM 3단계: 빌드 실행
echo.
echo [3/4] PyInstaller 빌드 시작...
echo       (수 분 소요될 수 있습니다)
echo.
pyinstaller nomos.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] 빌드 실패!
    echo.
    echo 문제 해결:
    echo   1. pip install pyinstaller --upgrade
    echo   2. pip install PySide6 --upgrade
    echo   3. 관리자 권한으로 다시 실행
    pause
    exit /b 1
)

REM 4단계: 배포 폴더 구성
echo.
echo [4/4] 배포 폴더 구성...
if not exist dist\NomosLLM\models mkdir dist\NomosLLM\models
if not exist dist\NomosLLM\aider_projects mkdir dist\NomosLLM\aider_projects

REM config.ini 복사 (spec에서 datas로도 포함하지만, 사용자가 수정할 수 있게 별도 복사)
if exist config.ini copy /y config.ini dist\NomosLLM\config.ini >nul

REM token.txt 복사 (있으면)
if exist token.txt copy /y token.txt dist\NomosLLM\token.txt >nul

echo.
echo ========================================
echo   빌드 완료!
echo ========================================
echo.
echo   결과 폴더: dist\NomosLLM\
echo   실행 파일: dist\NomosLLM\NomosLLM.exe
echo.
echo   [배포 시 참고]
echo     - dist\NomosLLM\config.ini : API URL/모델 설정
echo     - dist\NomosLLM\token.txt  : API 토큰 (필요시)
echo     - dist\NomosLLM\models\    : GGUF 모델 파일 (로컬 모드용)
echo.
pause
