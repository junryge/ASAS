@echo off
chcp 65001 >nul
title FlowBot RPA - 자동 실행 (웹 없이 동작)
cd /d "%~dp0"
echo ============================================================
echo   FlowBot RPA 자동 실행기
echo   - 이 창을 켜두면 config.json 의 run_times 에 자동 실행됩니다.
echo   - 지금 바로 1회 테스트하려면:  RPA지금실행.bat
echo   - 종료하려면 이 창에서 Ctrl+C
echo ============================================================
python run_flow.py
pause
