# Hermes Web

Hermes Agent 전용 독립 웹 UI. **`demos_v1` 와 완전 분리** — demos 가 떠있지 않아도 동작함.

## 구조

```
hermes-web/
├── server.py            ← Flask 백엔드 (포트 8788) — UI 서빙 + hermes subprocess
├── hermes_proxy.py      ← LLM 게이트웨이 프록시 (포트 8765)
├── hermes_config.yaml   ← hermes-agent 설정 템플릿 (~/.hermes/config.yaml 로 복사)
├── static/index.html    ← 화이트/다크 UI
├── skills_kr.json       ← 스킬 한글 요약 캐시
├── start.bat            ← 더블클릭 시작
├── requirements.txt
└── README.md
```

## 전제

- `hermes-agent` 가 설치되어 있어야 함 (`pip install "hermes-agent[all]"`)
- `~/.hermes/config.yaml` 세팅 (아래 배포 절차 참고)
- `hermes-web/hermes_proxy.py` 가 떠있어야 hermes 가 응답함

## 배포 (최초 1회)

PowerShell:

```powershell
# 1. hermes-agent 설치
pip install "hermes-agent[all]"

# 2. config 복사 (이 폴더의 템플릿 → 사용자 홈)
mkdir $env:USERPROFILE\.hermes -ErrorAction SilentlyContinue
copy "scientific-assistant\hermes-web\hermes_config.yaml" "$env:USERPROFILE\.hermes\config.yaml"

# 3. 토큰 (OFFICE 환경에서 TOKEN.TXT 가 있으면 proxy 가 자동 주입)
$env:OPENAI_API_KEY = "<TOKEN.TXT 의 값>"
```

## 실행

### 더블클릭 (간단)

`start.bat` 더블클릭. 프록시 안 떠있으면 자동 spawn 시도.

### 명시적 (cmd 2개)

```cmd
:: 1. 프록시 (별도 창)
python scientific-assistant\hermes-web\hermes_proxy.py

:: 2. Hermes Web (별도 창)
python scientific-assistant\hermes-web\server.py
:: 다른 포트 쓰려면: python server.py 9000
```

브라우저: <http://localhost:8788>

## 환경 자동 감지

| 환경 | 트리거 경로 | hermes 동작 |
|---|---|---|
| HOME | `F:\M14_Q\scientific-assistant` 존재 | GGUF 자체 추론 (proxy 가 로컬 처리) |
| OFFICE | `C:\연구과제\CODE\데모스_분석툴\scientific-assistant` 존재 | HCP/Common vLLM API 포워딩 |

프록시가 자동 분기. 이 웹 UI 는 hermes 만 호출.

## 모델 / Tool-call

config 디폴트는 **`common.llm.skhynix.com` + `Kimi-K2.5`** — agentic / tool-call 검증된 조합.
파일 생성/수정 같은 도구 사용이 필요하면 `capabilities: [..., tools, function_calling]` 가
선언된 모델만 골라 써:

| 모델 | 추천 용도 |
|---|---|
| **Kimi-K2.5** ★ | 에이전트 / 도구 사용 / 자동 스킬 선택 |
| **GLM-5.1** ★ | 에이전트, reasoning, 빠름 |
| Qwen3.6-35B-A3B | 에이전트, 가벼움 |
| Gemma-4-31B | 에이전트, 가벼움 |
| (그 외) | 채팅 전용 — tool-call 미검증 |

> 옛 `dev.hcp.llm.skhynix.com` 엔드포인트 폴백이 필요하면 proxy 띄울 때
> `$env:HERMES_STRIP_TOOLS=1` 로 tools 필드 제거 모드 활성화.

## API

- `GET /api/health` — 프록시 상태, 환경 모드, hermes 바이너리, winpty
- `GET /api/skills` — `scientific-skills/` 폴더의 SKILL.md 카탈로그
- `GET /api/skill/<id>` — 개별 SKILL.md 본문 (progressive disclosure)
- `POST /api/chat` — SSE 스트리밍
  - body: `{"messages": [...], "skills": ["skill1", ...], "session_id": "...", "raw": false}`
  - SSE 이벤트: `meta`, `token`, `error`, `end`, `[DONE]`
- `POST /api/translate-skills` — 영문 description → 한글 요약 배치

## 포트

| 서비스 | 포트 |
|---|---|
| demos_v1 (있을 때) | 10009 |
| **hermes_proxy.py** | **8765** |
| **hermes-web (server.py)** | **8788** |

세 가지 동시 실행 가능.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 파일이 안 만들어진다 (글자만 나옴) | proxy 가 `tools` 필드 제거 / config 가 tool-call 모델 안 가리킴 | `Kimi-K2.5` 등 ★ 모델 선택, `HERMES_STRIP_TOOLS` 환경변수 해제 |
| 답변에 사용자 질문이 메아리 | hermes TUI 입력 에코 | 최신 server.py 가 자동 제거 — 갱신 필요 |
| `PROXY OFFLINE` | 8765 안 떠있음 | `python hermes_proxy.py` 실행 |
| `prompt_toolkit: No Windows console` | pywinpty 미설치 | `pip install pywinpty` |
| 스킬 0개 | `scientific-skills/` 경로 못 찾음 | `/api/health` 의 `skills_dir` 확인 |
| 응답이 빈 버블 | CoT 필터가 다 제거 | 상단 RAW 토글 켜고 재시도 |
| 새 메시지가 새 세션으로 시작 | localStorage 의 sid 안 들어감 | 브라우저 하드 리로드 (Ctrl+Shift+R), 상단 SESSION 뱃지 확인 |
