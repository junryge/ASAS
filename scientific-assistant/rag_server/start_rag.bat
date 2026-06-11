@echo off
chcp 65001 >/dev/null
cd /d %~dp0
echo ============================================
echo  RAG 서버 시작 (rag_server 전용 venv)
echo ============================================
if not exist "venv\Scripts\activate.bat" (
  echo [최초 1회] 가상환경 생성 + 공식 llama-cpp-python 설치 중...
  python -m venv venv
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install flask llama-cpp-python
) else (
  call venv\Scripts\activate.bat
)
echo.
echo [실행] python app.py
python app.py
pause
