#!/bin/bash
echo "Nomos LLM PRO 시작 중..."
cd "$(dirname "$0")/.."
python3 -m app.main
if [ $? -ne 0 ]; then
    echo
    echo "[오류] 실행에 실패했습니다."
    echo "설치가 완료되었는지 확인해주세요: setup/install.sh"
fi
