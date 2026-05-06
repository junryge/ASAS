#!/bin/bash
# OHT_UDP_SIM 일괄 실행 스크립트
# main + sender(M14A) + sender(M16A_BR) 3개 프로세스 동시 시작

cd "$(dirname "$0")"

mkdir -p logs

echo "[1/3] main 수신 (UDP 3710 + 3750, HTTP 11000)"
python3 main.py > logs/main.log 2>&1 &
MAIN_PID=$!

sleep 1

echo "[2/3] sender M14A   (UDP→3710, HTTP 11010)"
python3 sender.py m14a > logs/sender_m14a.log 2>&1 &
S1_PID=$!

echo "[3/3] sender M16A_BR (UDP→3750, HTTP 11020)"
python3 sender.py m16a_br > logs/sender_m16a_br.log 2>&1 &
S2_PID=$!

cat <<EOF

================================================================
  OHT_UDP_SIM 실행 중
  --------------------------------------------------------------
  main 수신 UI       : http://127.0.0.1:11000
  M14A 송신 UI       : http://127.0.0.1:11010
  M16A_BR 송신 UI    : http://127.0.0.1:11020
  --------------------------------------------------------------
  로그              : logs/main.log, logs/sender_m14a.log, logs/sender_m16a_br.log
  종료              : ./stop_all.sh
================================================================

EOF

echo $MAIN_PID > logs/main.pid
echo $S1_PID > logs/sender_m14a.pid
echo $S2_PID > logs/sender_m16a_br.pid

wait
