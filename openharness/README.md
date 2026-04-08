# OpenHarness - Open Agent Harness

팀원 개인별 CLI AI 에이전트 하네스

---

## 설치 방법

### 방법 1: 설치 스크립트 (권장)

```bash
# 1. 압축파일 해제
unzip openharness.zip
cd openharness

# 2. 설치 실행
bash install.sh
```

### 방법 2: 수동 설치

```bash
# 1. 압축파일 해제
unzip openharness.zip
cd openharness

# 2. pip 설치
pip install -e .

# 3. 설정 디렉토리 생성
mkdir -p ~/.openharness/{skills,plugins,sessions}

# 4. API 키 설정
nano ~/.openharness/TOKEN.TXT
# → API 키를 입력하고 저장
```

### 방법 3: PYTHONPATH 직접 사용 (pip 없이)

```bash
unzip openharness.zip
cd openharness

# PYTHONPATH에 src 추가 후 실행
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python -m openharness
```

---

## API 키 설정

**필수**: LLM 서버에 연결하려면 TOKEN.TXT에 API 키를 넣어야 합니다.

```bash
# 키 파일 위치 (아래 중 하나)
~/.openharness/TOKEN.TXT    # 개인 홈 (우선순위 1)
./TOKEN.TXT                  # 현재 작업 디렉토리 (우선순위 2)
```

```bash
# 키 입력 예시
echo "sk-your-api-key-here" > ~/.openharness/TOKEN.TXT
```

> TOKEN.TXT가 없거나 비어있으면 시작 시 경고가 표시되고 API 호출이 불가합니다.

---

## 사용법

### 인터랙티브 모드 (기본)

```bash
oh
```

실행하면 다음과 같이 표시됩니다:

```
  ╔══════════════════════════════════════════╗
  ║     OpenHarness  v0.1.0                  ║
  ║     Open Agent Harness for Teams         ║
  ╚══════════════════════════════════════════╝

  🔑 TOKEN.TXT: loaded (32 chars)
  🤖 Default model: PROD (397B)
  🔧 Tools: 8 (0 skills, 0 plugins)
  💬 Type /help for commands, /exit to quit

you> 안녕하세요, 코드 리뷰 해주세요
```

### 모델 지정

```bash
oh --model qwen3-coder-480b     # 코더 전용 모델
oh --model glm-5                # 빠른 범용 모델
oh --model qwen3-vl-235b        # 비전 모델 (이미지 지원)
oh --model gpt-oss-120b         # 경량 모델
```

### 헤드리스 (단일 명령) 모드

```bash
# 간단한 질문
oh run "Python으로 퀵소트 구현해줘"

# JSON 출력
oh run "이 코드의 버그를 찾아줘" --json

# 여러 턴 실행
oh run "테스트를 작성하고 실행해줘" --max-turns 5
```

### 상태 확인

```bash
oh status     # 시스템 상태
oh models     # 사용 가능한 모델 목록
oh skills     # 로드된 스킬 목록
oh plugins    # 로드된 플러그인 목록
```

---

## 슬래시 커맨드

인터랙티브 모드에서 `/`로 시작하는 커맨드를 사용할 수 있습니다:

| 커맨드 | 설명 |
|--------|------|
| `/help` | 사용 가능한 커맨드 목록 |
| `/models` | 사용 가능한 LLM 모델 목록 |
| `/model [name]` | 현재 모델 확인/변경 |
| `/skills` | 로드된 스킬 목록 |
| `/plugins` | 로드된 플러그인 목록 |
| `/status` | 시스템 상태 |
| `/clear` | 화면 지우기 |
| `/exit` | 종료 |

### 예시

```
you> /models
# Available Models

  → qwen3.5-397b              PROD (397B)          [high]
    qwen3-coder-480b           Coder-480B           [high]
    glm-5                      GLM-5                [medium]
    gpt-oss-120b               COMMON (120B)        [medium]
    glm-4.7                    GLM-4.7              [low]
    ...

you> /model qwen3-coder-480b
Model set to: qwen3-coder-480b

you> /status
# Status
  Token: loaded
  Model: qwen3-coder-480b
  Tools: 8
  Skills: 0
  Plugins: 0
```

---

## 모델 목록

### 텍스트/코드 모델

| 키 | 모델명 | 성능 | 용도 |
|----|--------|------|------|
| `qwen3.5-397b` | Qwen3.5-397B-A17B | ★★★ | 복잡한 분석, 대규모 코드 |
| `qwen3-coder-480b` | Qwen3-Coder-480B | ★★★ | 코딩 전문 |
| `qwen3-235b-2507` | Qwen3-235B | ★★★ | 범용 대형 |
| `glm-5` | GLM-5 | ★★☆ | 빠른 범용 |
| `gpt-oss-120b` | gpt-oss-120b | ★★☆ | 경량 범용 |
| `qwen3-coder-next` | Qwen3-Coder-Next | ★★☆ | 차세대 코더 |
| `glm-4.7` | GLM-4.7 | ★☆☆ | 초고속 |
| `qwen3.5-35b` | Qwen3.5-35B | ★☆☆ | 초경량 |

### 비전 모델 (이미지 지원)

| 키 | 모델명 | 성능 | 용도 |
|----|--------|------|------|
| `qwen3-vl-235b` | VL-235B | ★★★ | 복잡한 이미지 분석 |
| `qwen2.5-vl-72b` | VL-72B | ★★☆ | 일반 이미지 분석 |
| `qwen3-vl-30b` | VL-30B | ★☆☆ | 빠른 이미지 분석 |

### 자동 라우팅

모델을 지정하지 않으면 쿼리 특성에 따라 자동 선택됩니다:
- 코딩 키워드 → Coder-480B
- 복잡한 분석 → PROD (397B)
- 이미지 포함 → Vision 모델
- 단순 질문 → COMMON (120B)

### 폴백 체인

선택된 모델이 실패하면 자동으로 대체 모델을 순차 시도합니다 (최대 6회).

---

## 스킬 추가

Anthropic의 SKILL.md 형식과 호환됩니다.

### 커스텀 스킬 만들기

```bash
mkdir -p ~/.openharness/skills/my-skill
cat > ~/.openharness/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: 나만의 커스텀 스킬
---
# My Custom Skill

이 스킬은 특정 작업을 수행합니다.
다음 지침을 따라주세요:
1. 입력을 분석합니다
2. 결과를 생성합니다
3. 피드백을 제공합니다
EOF
```

### Anthropic 공식 스킬 사용

`anthropics/skills` 리포지토리의 스킬을 `~/.openharness/skills/`에 복사하면 자동 인식됩니다:

```bash
git clone https://github.com/anthropics/skills /tmp/skills
cp -r /tmp/skills/skills/* ~/.openharness/skills/
```

---

## 플러그인 추가

Anthropic의 Claude Code 플러그인 형식과 호환됩니다.

### 플러그인 구조

```
~/.openharness/plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 필수: 메타데이터
├── commands/
│   └── my-command.md      # 슬래시 커맨드
├── agents/
│   └── my-agent.md        # 에이전트 정의
└── skills/
    └── my-skill/SKILL.md  # 번들 스킬
```

### plugin.json 예시

```json
{
  "name": "my-plugin",
  "description": "나만의 플러그인",
  "version": "1.0.0"
}
```

### Claude Code 공식 플러그인 사용

```bash
# anthropics/claude-code 플러그인 복사
git clone https://github.com/anthropics/claude-code /tmp/claude-code
cp -r /tmp/claude-code/plugins/* ~/.openharness/plugins/
```

---

## 디렉토리 구조

```
~/.openharness/              # 개인 설정 (홈 디렉토리)
├── TOKEN.TXT                # API 키
├── skills/                  # 커스텀 스킬
│   ├── my-skill/SKILL.md
│   └── ...
├── plugins/                 # 커스텀 플러그인
│   ├── my-plugin/
│   └── ...
└── .harness_sessions/       # 세션 히스토리
    ├── {session-id}.json
    └── ...
```

---

## 프로젝트 소스 구조

```
openharness/
├── src/openharness/         # 코어 소스 (~3000줄)
│   ├── api/                 # API 연결 (TOKEN.TXT, 모델 레지스트리, Provider)
│   ├── engine/              # Agent Loop (registry, router, engine)
│   ├── tools/               # 8개 빌트인 도구
│   ├── skills/              # SKILL.md 로더
│   ├── plugins/             # Plugin 로더
│   ├── permissions/         # 권한 관리
│   ├── hooks/               # 라이프사이클 훅
│   ├── commands/            # 슬래시 커맨드
│   ├── memory/              # 세션/히스토리/트랜스크립트
│   ├── coordinator/         # 멀티에이전트 (확장용)
│   └── cli.py               # CLI 엔트리포인트
├── tests/                   # 테스트 (60개 통과)
├── skills/anthropic/        # Anthropic 공식 스킬 (별도 설치)
├── plugins/anthropic/       # Anthropic 공식 플러그인 (별도 설치)
├── pyproject.toml           # Python 패키지 설정
├── install.sh               # 설치 스크립트
└── TOKEN.TXT.template       # 토큰 템플릿
```

---

## 트러블슈팅

### TOKEN.TXT 관련

```
⚠️ TOKEN.TXT: missing or empty
→ ~/.openharness/TOKEN.TXT 에 API 키를 넣어주세요
```

**해결**: `echo "your-api-key" > ~/.openharness/TOKEN.TXT`

### 모델 연결 실패

```
All 6 models failed. Last error: Connection error
```

**해결**: 내부 LLM 서버 (`dev.hcp.llm.skhynix.com`) 접근 가능한지 확인

### pip 설치 실패 (프록시)

프록시 환경에서는 PYTHONPATH 방식 사용:

```bash
export PYTHONPATH="/path/to/openharness/src:$PYTHONPATH"
python -m openharness
```

---

## 라이선스

Apache-2.0
