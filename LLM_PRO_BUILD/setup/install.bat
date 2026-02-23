@echo off
chcp 65001 >nul
echo ============================================
echo   Nomos LLM PRO - 설치 스크립트 (Windows)
echo ============================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 설치해주세요.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Python 확인 완료
python --version

:: pip 업그레이드
echo.
echo [2/4] pip 업그레이드 중...
python -m pip install --upgrade pip

:: 필수 패키지 설치
echo.
echo [3/4] 필수 패키지 설치 중...
pip install PySide6>=6.5.0
pip install requests>=2.28.0
pip install Pygments>=2.15.0

:: llama-cpp-python GPU 버전 설치
echo.
echo [4/4] llama-cpp-python (CUDA GPU 지원) 설치 중...
echo NVIDIA GPU가 있으면 CUDA 버전으로 설치됩니다.
set CMAKE_ARGS=-DGGML_CUDA=on
set FORCE_CMAKE=1
pip install llama-cpp-python>=0.2.50 --force-reinstall --no-cache-dir

:: 선택 패키지
echo.
echo ============================================
echo   선택 패키지 설치
echo ============================================
echo.

set /p INSTALL_NANOBOT="마기(MAGI) 에이전트 설치? (y/n): "
if /i "%INSTALL_NANOBOT%"=="y" (
    echo nanobot-ai 설치 중...
    pip install nanobot-ai>=0.1.0
)

:: 모델 폴더 확인
echo.
if not exist "..\models" mkdir "..\models"
echo [확인] models 폴더 생성됨

:: 완료
echo.
echo ============================================
echo   설치 완료!
echo ============================================
echo.
echo 다음 단계:
echo   1. models 폴더에 GGUF 모델 파일 배치
echo      (예: Qwen3-8B-Q6_K.gguf)
echo   2. API 사용 시 token.txt 파일 배치
echo   3. run.bat 실행
echo.
pause
