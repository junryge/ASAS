# Hermes Web

Hermes Agent 전용 독립 웹 UI. demos_v1 와 분리되어 동작.

## 구조

```
hermes-web/
├── server.py            ← Flask 백엔드 (포트 8788)
├── static/index.html    ← 화이트/다크 UI
├── start.bat            ← 더블클릭 시작
├── requirements.txt
└── README.md
```

## 전제

- `hermes-agent` 가 설치되어 있어야 함 (`pip install "hermes-agent[all]"`)
- `~/.hermes/config.yaml` 이 설정되어 있어야 함 (base_url 이 프록시 가리키도록)
- `demos_v1/hermes_proxy.py` 가 떠있어야 hermes 가 응답함

## 실행

### 더블클릭 (간단)

`start.bat` 더블클릭. 프록시 안 떠있으면 자동 spawn 시도.

### 명시적

```cmd
:: 1. 프록시 (별도 cmd)
cd ..\demos_v1
python hermes_proxy.py

:: 2. Hermes Web (이 폴더)
python server.py
:: 또는 다른 포트
python server.py 9000
```

브라우저: <http://localhost:8788>

## 환경 자동 감지

| 환경 | 트리거 경로 | hermes 동작 |
|---|---|---|
| HOME | `F:\M14_Q\scientific-assistant` 존재 | GGUF (proxy → demos:10009) |
| OFFICE | `C:\연구과제\CODE\데모스_분석툴\scientific-assistant` 존재 | HCP API 직접 |

프록시가 자동 분기. 이 웹 UI 는 hermes 만 호출.

## API

- `GET /api/health` — 프록시 상태, 환경 모드, hermes 바이너리, winpty
- `GET /api/skills` — `scientific-skills/` 폴더의 SKILL.md 카탈로그
- `POST /api/chat` — SSE 스트리밍
  - body: `{"messages": [...], "skills": ["skill1", "skill2"]}`
  - SSE 이벤트: `meta`, `token`, `error`, `end`, `[DONE]`

## 포트 충돌 방지

| 서비스 | 포트 |
|---|---|
| demos_v1 (있을 때) | 10009 |
| hermes_proxy.py | 8765 |
| **hermes-web (이 앱)** | **8788** |

세 가지 동시 실행 가능.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `[hermes] (0자)` | 프록시 다운 또는 winpty 없음 | `/api/health` 확인 |
| `prompt_toolkit: No Windows console` | pywinpty 미설치 | `pip install pywinpty` |
| 스킬 0개 | `scientific-skills/` 경로 못 찾음 | 환경 자동감지 결과 확인 |
| 응답 깨짐 (` </think>` 등) | hermes 모델이 thinking 누출 | `~/.hermes/config.yaml` 의 모델을 Qwen 계열로 변경 |
