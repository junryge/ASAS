#!/bin/bash
echo "============================================"
echo "  Nomos LLM PRO - 설치 스크립트 (Linux/Mac)"
echo "============================================"
echo

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되어 있지 않습니다."
    echo "Python 3.10 이상을 설치해주세요."
    exit 1
fi

echo "[1/4] Python 확인 완료"
python3 --version

# pip 업그레이드
echo
echo "[2/4] pip 업그레이드 중..."
python3 -m pip install --upgrade pip

# 필수 패키지 설치
echo
echo "[3/4] 필수 패키지 설치 중..."
pip3 install PySide6>=6.5.0
pip3 install requests>=2.28.0
pip3 install Pygments>=2.15.0

# llama-cpp-python GPU 버전 설치
echo
echo "[4/4] llama-cpp-python (CUDA GPU 지원) 설치 중..."
CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 pip3 install llama-cpp-python>=0.2.50 --force-reinstall --no-cache-dir

# 선택 패키지
echo
echo "============================================"
echo "  선택 패키지 설치"
echo "============================================"
echo
read -p "마기(MAGI) 에이전트 설치? (y/n): " INSTALL_NANOBOT
if [ "$INSTALL_NANOBOT" = "y" ]; then
    echo "nanobot-ai 설치 중..."
    pip3 install nanobot-ai>=0.1.0
fi

# 모델 폴더 확인
echo
mkdir -p ../models
echo "[확인] models 폴더 생성됨"

# 완료
echo
echo "============================================"
echo "  설치 완료!"
echo "============================================"
echo
echo "다음 단계:"
echo "  1. models 폴더에 GGUF 모델 파일 배치"
echo "     (예: Qwen3-8B-Q6_K.gguf)"
echo "  2. API 사용 시 token.txt 파일 배치"
echo "  3. ./run.sh 실행"
echo
