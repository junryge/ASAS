@echo off
REM ============================================================
REM  OHT 월드모델파생 — 단일 EXE 빌드 (Windows)
REM ============================================================
REM 사용법:   build.bat
REM 결과:     dist\oht_world.exe
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo [1/3] 의존성 설치 (없으면 자동)
python -m pip install --upgrade pip
python -m pip install pyinstaller fastapi uvicorn[standard] requests pandas
if errorlevel 1 (
  echo 의존성 설치 실패
  exit /b 1
)

echo.
echo [2/3] 이전 빌드 정리
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo [3/3] PyInstaller 빌드 시작
pyinstaller --clean --noconfirm oht_world.spec
if errorlevel 1 (
  echo 빌드 실패
  exit /b 1
)

echo.
echo ============================================================
echo  빌드 완료: dist\oht_world.exe
echo ============================================================
echo.
echo  사용 방법:
echo    1. dist\oht_world.exe 를 원하는 폴더로 이동
echo    2. 같은 폴더에 OHT_MAP\ 폴더 두기 (맵 데이터)
echo    3. oht_world.exe 더블클릭 → http://localhost:10005
echo.
endlocal
