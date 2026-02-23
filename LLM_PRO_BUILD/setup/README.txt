============================================
  Nomos LLM PRO - 설치 가이드
============================================

■ 시스템 요구사항
  - Python 3.10 이상
  - NVIDIA GPU (GGUF 모드: RTX 3060 12GB 이상 권장)
  - CUDA Toolkit 11.7 이상 (GPU 사용 시)
  - Windows 10/11 또는 Linux

■ 폴더 구조
  LLM_PRO/
  ├── app/                  # 앱 소스코드
  ├── models/               # GGUF 모델 파일 (.gguf)
  ├── setup/                # 설치/실행 스크립트 (여기)
  │   ├── requirements.txt  # Python 패키지 목록
  │   ├── install.bat       # Windows 설치
  │   ├── install.sh        # Linux/Mac 설치
  │   ├── run.bat           # Windows 실행
  │   ├── run.sh            # Linux/Mac 실행
  │   └── README.txt        # 이 파일
  ├── token.txt             # API 토큰 (API 모드 사용 시)
  └── domain_knowledge.txt  # 도메인 지식 (선택)

■ 설치 방법
  1. setup 폴더에서 install.bat (Windows) 또는 install.sh (Linux) 실행
  2. 필수 패키지 자동 설치됨
  3. 마기(MAGI) 에이전트는 선택 설치

■ 실행 전 준비

  [GGUF 모드 - 로컬 추론 (폐쇄망)]
  - models/ 폴더에 GGUF 모델 파일 배치
  - 지원 모델:
    · Qwen3-8B-Q6_K.gguf   (6.7GB, RTX 3060 12GB 추천)
    · Qwen3-14B-Q4_K_M.gguf (8.7GB, RTX 4070 이상)
    · Qwen3-32B-Q4_K_M.gguf (19GB, RTX 4090 이상)

  [API 모드 - 회사 서버]
  - token.txt 파일에 API 토큰 입력
  - 환경별 서버: 개발(dev), 운영(prod), 공통(common)

■ 실행
  setup 폴더에서 run.bat (Windows) 또는 run.sh (Linux) 실행

■ 필수 패키지 (자동 설치됨)
  - PySide6        : GUI 프레임워크
  - llama-cpp-python: GGUF 모델 추론 (GPU 가속)
  - requests       : API HTTP 요청
  - Pygments       : 코드 구문 강조

■ 선택 패키지
  - nanobot-ai     : 마기(MAGI) 에이전트 도구 실행
                     (미설치 시 bridge 폴백으로 동작)

■ 앱 모드 설명
  - 일반    : 질문/대화 (LLM 직접)
  - 생성    : 코드 생성 (LLM 직접)
  - 분석    : 코드 분석, 읽기전용 (bridge)
  - 수정    : 코드 수정 + diff (bridge)
  - 에이전트: 마기 단독 or 마기+Ralph 협동
    · 일반 질문 → 마기 단독 실행
    · "자동으로", "전체 수정" 등 키워드 → 마기+Ralph 협동

■ GPU 참고 (RTX 3060 12GB 기준)
  - Qwen3-8B-Q6_K: VRAM ~8GB 사용, 56도, ctx=32768
  - n_gpu_layers=35 (전체 오프로드)
  - 공유 GPU 메모리는 느려서 의미 없음
