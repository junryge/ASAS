# Agent Kits — 에이전트 소스 키트 모음

개발자가 자기 프로젝트에 가져다 통합할 수 있는 **독립 소스 패키지** 모음입니다.
두 키트는 **서로 독립적**이며, 각각 단독으로도 쓸 수 있습니다.
(합치는 건 가져가는 개발자가 필요에 맞게 — 여기선 소스만 제공합니다.)

```
agent-kits/
├── hermes-engine/   🔮 기억하고 스스로 배우는 레이어 (메모리·자기학습·되묻기·세션회상)
└── harness-mvp/     🛠 도구 실행 하네스 (도구 등록·프롬프트 라우팅·멀티턴·세션·권한)
```

---

## 🔮 hermes-engine
"쓸수록 잘 맞춰주는" 기억/자기학습 레이어. 어떤 Flask + LLM 챗 앱에도 드롭인.
- 네이티브 함수콜 불필요(**텍스트 프로토콜**), 폐쇄망/GGUF/API 무관, 파일 저장(DB 없음)
- 핵심: `register_hermes_routes(app)` 한 줄 + 프론트 `Hermes.prep/post`
- 자세히 → `hermes-engine/README.md`

빠른 실행:
```bash
cd hermes-engine && pip install -r requirements.txt && python examples/app_min.py
```

## 🛠 harness-mvp
Python 도구 실행 하네스. 도구를 등록하고, 프롬프트로 라우팅해서, 멀티턴으로 실행/세션 저장.
- 도구 레지스트리 · 권한(deny-list) · 라우터 · 엔진(턴 루프/예산/스트림) · 세션/히스토리/트랜스크립트
- 자세히 → `harness-mvp/README.md`, `harness-mvp/ARCHITECTURE.md`

빠른 실행:
```bash
cd harness-mvp
python -m harness list           # 등록된 도구
python -m harness route "echo hello"
python -m unittest discover -s tests   # 테스트 (80개)
```

---

## 둘의 관계
| | hermes-engine | harness-mvp |
|---|---|---|
| 역할 | **기억·학습**(무엇을 아는가) | **도구 실행**(무엇을 하는가) |
| 의존 | Flask (웹 라우트용) | 표준 라이브러리만 |
| 통합 | 챗 앱의 send 흐름을 감쌈 | 도구 실행 파이프라인 |
| 결합 | 선택 — 하네스가 hermes-engine을 호출해 "기억하는 도구 에이전트"로 만들 수 있음(개발자 몫) |

> 이 폴더는 **소스 제공용**입니다. 각 키트의 README를 보고 자기 앱에 맞게 통합하세요.
