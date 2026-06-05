# 🔮 Hermes Engine (포터블)

기존 `hermes-agent` 패키지 **없이**, 어떤 Flask + LLM 챗 앱에도 떨어뜨려 쓰는
**"기억하고 스스로 배우는" 에이전트 레이어**입니다.

- ✅ 폐쇄망 / GGUF / API 어디서나 동작 (외부망·MCP·게이트웨이 불필요)
- ✅ 네이티브 함수콜(tool calling) 불필요 — **텍스트 프로토콜**로 동작
- ✅ 파일 기반 저장 (DB 없음), 사용자별 분리
- ✅ 메인 채팅(`/api/chat`)을 **건드리지 않고** 감싸는 방식

## 무엇을 하나
| 능력 | 설명 |
|---|---|
| 🧠 장기 메모리 | 선언적 사실(MEMORY)/선호(USER)를 기억 → **새 세션·재접속에도 유지** |
| 📚 자기학습 스킬 | 재사용 가치 있는 절차를 `SKILL.md`로 저장(확인형) → 다음에 BM25 회상 |
| 🧭 **빌트인 스킬 팩** | 질문 키워드에 맞으면 자동 주입: task-planning · systematic-debugging · structured-data-analysis · answer-verification (`builtin.py`) |
| ❓ 되묻기 | 요청이 모호하면 추측 말고 먼저 질문 |
| 🔎 세션 회상 | 과거 대화 BM25 검색 (LLM 없이) |
| ♻️ 백그라운드 리뷰 | 카운터 임계 시 백그라운드로 놓친 기억 자동 보충 (`review.py`, 호스트가 LLM 주입) |
| 🗂 큐레이터 | 앱 시작 시 1회 — 30일 미사용 스킬→stale, 90일→archived (pinned 면제, `curator.py`) |

> 모델 자체가 똑똑해지는 게 아니라, **좋은 기억·절차를 컨텍스트로 떠먹여** 쓸수록 잘 맞춰줍니다.
> 자세한 스킬/기능: [HERMES_FEATURES.md](HERMES_FEATURES.md) · [HERMES_SKILLS.md](HERMES_SKILLS.md)

---

## 설치 / 배치
폴더째 복사해서 `import hermes` 가능한 위치에 두면 끝.
```
hermes-engine/
├── hermes/            ← 이 패키지를 PYTHONPATH 에 (또는 프로젝트에 복사)
│   ├── store · memory · sessions · protocol · skills · counters
│   ├── engine · routes · curator · review · builtin
│   └── config        (HERMES_DATA_DIR 설정)
├── examples/app_min.py
├── static/hermes-client.js
├── requirements.txt   (flask)
├── HERMES_FEATURES.md / .html   ← 전체 기능
└── HERMES_SKILLS.md / .html      ← 스킬 상세
```

저장 위치는 환경변수로 지정(없으면 `./hermes_data`):
```bash
export HERMES_DATA_DIR=/path/to/data     # 구조: <DATA>/agents/<user_id>/
```

---

## 백엔드 연동 (한 줄)
```python
from flask import Flask
from hermes import register_hermes_routes

app = Flask(__name__)
register_hermes_routes(app)     # /api/hermes/* 등록 (메인 /api/chat 무수정)
```

### 동작 흐름 (당신의 채팅 send 를 감싼다)
```
[전송 전]  POST /api/hermes/prep  {user_id, query}
            → {system_addon}  ← 기억+개인스킬+지침. system_prompt 에 합쳐 /api/chat 호출
[응답 후]  POST /api/hermes/post  {user_id, answer, user_message, session_id}
            → {clean, memory_results, pending_skills, questions, review_due}
              · clean         : 블록 제거된 표시용 본문
              · memory_results: 자동 저장된 기억
              · pending_skills: 승인 대기 스킬(확인형) → 사용자 OK 시 confirm
              · questions     : 되묻기 질문
[스킬 승인] POST /api/hermes/skill/confirm  {user_id, spec}
```

### 프로그래밍 API (라우트 없이 직접)
```python
from hermes import engine
addon = engine.build_system_prompt(user_id, query)   # 프롬프트에 추가할 문자열
res   = engine.apply_response(user_id, llm_answer)    # 블록 처리 결과(dict)
ok, msg = engine.confirm_skill(user_id, res["pending_skills"][0])
```

---

## 빌트인 스킬 · 백그라운드 리뷰 · 큐레이터

### 🧭 빌트인 스킬 팩 (`builtin.py`)
질문 키워드에 맞으면 `build_system_prompt` 가 상위 2개를 자동 주입(순수 프롬프트):
task-planning · systematic-debugging · structured-data-analysis · answer-verification.
새 스킬은 `BUILTIN_SKILLS` 딕셔너리에 `{desc, keywords, body}` 추가.

### ♻️ 백그라운드 리뷰 (`review.py`)
대화가 임계(메모리 카운터)에 도달하면, 백그라운드 스레드가 놓친 기억을 보충 저장.
LLM 호출은 **호스트가 주입**(미주입 시 no-op):
```python
from hermes import review
review.set_completion(lambda messages: my_llm(messages))   # str 반환
```
- 메모리만 자동 저장(스킬은 확인형이라 제외). 본 대화 절대 차단 안 함, 실패는 로그만.

### 🗂 큐레이터 (`curator.py`)
`register_hermes_routes(app)` 호출 시 1회 자동 실행(앱 시작 시 밀린 정리 따라잡기):
30일 미사용→stale, 90일→archived (pinned 면제, **자동 삭제 없음**).

---

## 프론트 연동
`static/hermes-client.js` 를 페이지에 포함하면 `window.Hermes` 사용 가능.
```html
<script src="/static/hermes-client.js"></script>
```
```js
const uid = currentUser.id;

// 1) 전송 전: 기억/스킬/지침을 system_prompt 에 합치기
const addon = await Hermes.prep(uid, text);
const system_prompt = (addon + "\n\n" + baseSystemPrompt).trim();

// 2) 기존 /api/chat 로 평소처럼 스트리밍 … 답변 누적 = answer

// 3) 응답 후: 블록 처리
const r = await Hermes.post(uid, answer, text, sessionId);
showAnswer(r.clean);                       // 블록 제거된 본문
if (r.questions.length) showQuestions(r.questions);
for (const spec of r.pending_skills) {     // 확인형 스킬 저장
  if (confirm(`스킬 '${spec.name}' 저장?`)) await Hermes.confirmSkill(uid, spec);
}
```

뷰어용 API: `Hermes.getMemory(uid)`, `Hermes.listSkills(uid)`,
`Hermes.memoryOp(uid, store, action, {text/target})`, `Hermes.searchSessions(uid, q)`.

---

## 텍스트 프로토콜 (모델이 출력하는 블록)
모델이 답변 끝에 아래 펜스 블록을 내면 엔진이 파싱해 처리합니다.
(`build_system_prompt` 가 이 사용법을 시스템 프롬프트에 자동 주입)

````
```hermes:memory
store: user            # user | memory
action: add            # add | replace | remove
text: 사용자는 응답을 표로 정리하는 걸 선호한다
```

```hermes:skill
action: create         # create | patch
name: lpql-join-pattern
when: 로그프레소 조인 쿼리 작성 시
body: |
  1. ...
  2. ...
```

```hermes:ask
- 대상 FAB은 M14인가요?
- 기간은?
```
````

---

## 엔드포인트 요약
| 메서드 | 경로 | 용도 |
|---|---|---|
| POST | `/api/hermes/prep` | 시스템 프롬프트 추가분 |
| POST | `/api/hermes/post` | 응답 블록 처리 + 세션 로그 |
| POST | `/api/hermes/skill/confirm` | 승인된 스킬 저장 |
| GET  | `/api/hermes/skills` | 배운 스킬 목록 |
| GET  | `/api/hermes/skill/view` | 스킬 본문 |
| POST | `/api/hermes/skill/pin` · `/skill/delete` | 고정/삭제 |
| GET  | `/api/hermes/memory` | 기억 조회 |
| POST | `/api/hermes/memory/op` | 기억 추가/교체/삭제 |
| GET  | `/api/hermes/sessions/search` | 세션 회상 |

## 저장 구조
```
<HERMES_DATA_DIR>/agents/<user_id>/
├── MEMORY.md / USER.md          # 항목 구분자 §
├── skills/<name>/SKILL.md       # 배운 개인 스킬
├── usage.json / counters.json
└── sessions/YYYY-MM-DD.jsonl    # 30일 로테이션
```
모든 쓰기는 `tempfile → os.replace` 원자 교체. 저장 전 인젝션 패턴 차단.

---

## 빠른 실행 (예제)
```bash
cd hermes-engine
pip install -r requirements.txt
python examples/app_min.py      # http://localhost:8900
```

## 주의 / 한계
- 품질은 **연결한 LLM 성능**에 좌우 (기억 추출·스킬 작성도 그 모델이 함).
- 기억이 너무 쌓이면 컨텍스트가 커지니, 큰 컨텍스트 모델(API)에서 효과가 큼.
- 자율 명령실행/웹검색/파인튜닝은 범위 밖.

## 라이선스
프로젝트 정책에 따름.
