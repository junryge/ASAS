# Nomos LLM - 코딩 어시스턴트

SK Hynix 폐쇄망 환경에서 동작하는 PySide6 기반 데스크탑 LLM 코딩 어시스턴트.
API 우선, GGUF 로컬 모델 폴백. Aider + 마기(MAGI) + Ralph 에이전트 통합.

---

## 주요 기능

- **일반 대화 / 코드 생성** — LLM과 자유롭게 대화하거나 새 코드를 생성
- **코드 수정 (Aider)** — 프로젝트 파일을 선택하고, LLM이 코드를 직접 수정. Git 기반 Diff 미리보기 → 승인/거절 워크플로우
- **코드 분석** — 선택한 파일의 구조, 버그, 개선점 분석
- **마기(MAGI) 에이전트** — nanobot 기반 자율 코딩 에이전트 (선택적)
- **Ralph 자율 루프** — 작업 분해 → 반복 실행 → 검증 자동화 루프
- **자기교정(SC)** — 생성된 코드를 자동 검증 후 재시도
- **모던 다크 UI** — Pygments 구문 강조, 줄번호, 한국어 우클릭 메뉴

---

## 설치 방법

### 1. 사전 요구사항

- Python 3.10 이상
- Git (코드 수정 모드에서 필요)
- (선택) CUDA 지원 GPU (로컬 GGUF 모델 사용 시)

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. API 토큰 설정

`token.txt` 파일에 API 토큰을 입력합니다:

```bash
echo "YOUR_API_TOKEN_HERE" > token.txt
```

토큰 탐색 경로 (우선순위):
1. 프로젝트 루트의 `token.txt`
2. 상위 디렉토리의 `token.txt`
3. 홈 디렉토리의 `~/token.txt`

### 4. (선택) 로컬 GGUF 모델 배치

로컬 모드를 사용하려면 GGUF 모델 파일을 프로젝트 루트 또는 `models/` 폴더에 배치합니다:

```
LLM_PRO/
├── models/
│   ├── Qwen3-14B-Q4_K_M.gguf
│   ├── Qwen3-8B-Q6_K.gguf
│   └── qwen3-1.7b-q8_0.gguf
```

### 5. (선택) 환경 변수로 API URL 설정

기본 API URL을 변경하려면 `.env` 파일이나 환경변수를 사용합니다:

```bash
export LLM_DEV_URL="http://your-dev-server/v1/chat/completions"
export LLM_PROD_URL="http://your-prod-server/v1/chat/completions"
export LLM_COMMON_URL="http://your-common-server/v1/chat/completions"
```

---

## 실행 방법

```bash
python run_app.py
```

또는:

```bash
python -m app.main
```

### PyInstaller EXE 빌드 (선택)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name NomosLLM run_app.py
```

---

## 사용법

### 모드 전환 (좌측 사이드바)

| 모드 | 설명 |
|------|------|
| 💬 대화 | 일반 질문, 코드 설명 |
| ⚡ 코드 생성 | 새 코드 작성 요청 |
| 🔧 코드 수정 | 프로젝트 파일 직접 수정 (Aider) |
| 📊 분석 | 코드 분석, 데이터 분석 |
| 🤖 에이전트 | 마기/Ralph 자율 코딩 |

### 환경 전환 (상단 헤더)

- **DEV(30B)** — 개발 서버 (Qwen3-Coder-30B)
- **PROD(80B)** — 운영 서버 (Qwen3-Next-80B)
- **COMMON(20B)** — 공통 서버 (gpt-oss-20b)
- **LOCAL** — 로컬 GGUF 모델

### 코드 수정 워크플로우

1. **코드 수정** 모드 선택
2. 프로젝트를 선택하거나 새로 생성
3. 파일 트리에서 수정할 파일을 **체크**
4. 수정 요청 입력 후 전송
5. Diff 뷰어에서 변경사항 확인 → **적용** 또는 **거절**

### Ralph 자율 루프

에이전트 모드에서 "자율", "자동으로", "루프" 등의 키워드를 포함하면 Ralph 모드 활성화:
- 작업을 자동으로 분해
- 최대 N회 반복 실행 (헤더에서 설정 가능)
- 각 스텝마다 검증 수행

---

## 프로젝트 구조

```
LLM_PRO/
├── run_app.py              # 진입점
├── token.txt               # API 토큰
├── requirements.txt        # 의존성
├── app/
│   ├── main.py             # 앱 초기화 (메인 함수)
│   ├── main_window.py      # 메인 윈도우 + 시그널 연결
│   ├── core/
│   │   ├── config.py       # 설정 관리 (ENV_CONFIG, GGUF 모델)
│   │   ├── llm_provider.py # API + GGUF 통합 LLM 호출
│   │   ├── prompt_builder.py # 모드별 시스템 프롬프트
│   │   ├── self_correction.py # 자기교정 루프
│   │   └── gguf_server.py  # OpenAI 호환 로컬 서버
│   ├── agent/
│   │   ├── nanobot_manager.py # 마기(MAGI) 에이전트
│   │   ├── ralph_loop.py   # Ralph 자율 실행 루프
│   │   ├── tools.py        # 코드 검증 도구
│   │   └── sk_provider.py  # nanobot LLM 프로바이더
│   ├── aider/
│   │   ├── bridge.py       # Aider 통합 (코드 수정/분석)
│   │   ├── project_manager.py # 프로젝트 CRUD
│   │   └── git_ops.py      # Git 작업 (diff, undo, history)
│   └── ui/
│       ├── theme.py        # 다크 테마 스타일시트
│       ├── sidebar.py      # 좌측 모드 사이드바
│       ├── header.py       # 상단 헤더 (환경/모델 전환)
│       ├── chat_panel.py   # 채팅 패널
│       ├── code_editor.py  # Pygments 구문 강조 에디터
│       ├── project_panel.py # 프로젝트/파일 트리 패널
│       ├── diff_viewer.py  # Diff 뷰어 (승인/거절)
│       ├── dialogs.py      # 다이얼로그 (프로젝트 생성 등)
│       └── workers.py      # QThread 백그라운드 워커
└── aider_projects/         # 프로젝트 저장소 (자동 생성)
```

---

## 라이선스

내부 사용 전용.
