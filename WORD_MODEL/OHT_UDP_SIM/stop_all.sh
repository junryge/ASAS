#!/bin/bash
cd "$(dirname "$0")"

for f in logs/main.pid logs/sender_m14a.pid logs/sender_m16a_br.pid; do
  if [ -f "$f" ]; then
    pid=$(cat "$f")
    if kill -0 "$pid" 2>/dev/null; then
      echo "kill $pid ($f)"
      kill "$pid"
    fi
    rm -f "$f"
  fi
done

# 남은 프로세스 정리
pkill -f "python3 main.py"   2>/dev/null
pkill -f "python3 sender.py" 2>/dev/null

echo "정지 완료"
