# 🔮 헤르메스 (데모스 재해석) — 설계

> 기존 hermes-agent 패키지는 **사용 안 함**. Hermes의 능력을 데모스 위에 **재구현**한다.
> 폐쇄망 + GGUF/API + 프록시(tools 제거) 환경 → **네이티브 툴콜 미사용, 텍스트 프로토콜**로 동작.

## 확정 결정
- **opt-in**: 스킬 조합에 `🔮 헤르메스` **통짜 1개** 추가 → 고른 에이전트만 4기능 전부 ON.
- **스킬 자동생성 = 확인형**: 저장 전 "이거 스킬로 저장할까요?" 물어보고 승인 시 저장.
- **세션 중 메모리 = 즉시 반영**: 새 메모리 저장 시 시스템 프롬프트 스냅샷 갱신.

## 기능
| | 기능 | 설명 |
|---|---|---|
| ① | 🧠 장기 메모리 | 선언적 사실(MEMORY) + 사용자 선호(USER). 새 세션·기기 넘어 유지 |
| ② | 📚 자기학습 스킬 | 재사용 가치 있는 절차를 SKILL.md로 생성/patch (확인형) |
| ③ | ❓ 되묻기 | 모호하면 추측 말고 먼저 질문 |
| ④ | 👍 피드백/자기반성 | 잘한 답 재사용, 실수 회피 |
| + | ♻️ 백그라운드 리뷰 | 응답 종료 시 카운터 점검 → 임계면 API 모델로 저장 판단 |
| + | 🗂 큐레이터 | **앱 시작 시** 마지막 실행일 확인 후 밀린 정리 1회 (stale/archive, 삭제 X) |
| + | 🔎 세션 회상 | sessions jsonl을 BM25로 검색 (LLM 없이) |

## 텍스트 프로토콜 (툴콜 대체)
모델이 답변 안에 펜스 블록을 출력하면 백엔드가 파싱·실행한다.

기억 저장:
~~~
```hermes:memory
store: memory            # memory | user
action: add              # add | replace | remove
target: <짧은 고유 부분문자열>   # replace/remove 시
text: 사용자는 응답을 표로 정리하는 걸 선호한다
```
~~~

스킬 저장(확인형 — 먼저 제안):
~~~
```hermes:skill
action: create           # create | patch | edit | delete
name: lpql-join-pattern
when: 로그프레소 조인 쿼리 작성 시
body: |
  1. ...
  2. ...
```
~~~
→ 백엔드는 즉시 저장하지 않고 **사용자에게 승인 카드**를 띄움 → 승인 시 저장.

되묻기:
~~~
```hermes:ask
- 대상 테이블이 M14인가요 M16인가요?
- 기간은?
```
~~~

## 저장 구조 (파일 기반, DB 없음)
```
demos_data/agents/{userID}/
├── MEMORY.md            # 항목 구분자 "§"
├── USER.md
├── skills/{스킬명}/SKILL.md
├── usage.json           # {스킬명: {use_count, last_used, state, pinned}}
├── counters.json        # {turns_since_memory, iters_since_skill}
├── curator.json         # {last_run: "YYYY-MM-DD"}
└── sessions/YYYY-MM-DD.jsonl   # 1줄=1메시지, 30일 로테이션
```
- 모든 쓰기: `tempfile` → `os.replace` 원자 교체.
- 저장소당 6,000자 상한, 인젝션 패턴 차단.

## 시스템 프롬프트 조립 (헤르메스 ON일 때)
```
[기존 DEMOS 시스템 프롬프트]
+ [MEMORY.md / USER.md 스냅샷]
+ [개인 스킬 인덱스 (이름 + 한 줄)]      ← 본문은 BM25 매칭 시만 로드
+ [텍스트 프로토콜 사용 지침 + 메모리/스킬 작성 규칙 + 되묻기 규칙]
```
세션 중 메모리 저장되면 스냅샷 재생성(즉시 반영).

## 백그라운드 리뷰
- counters: `turns_since_memory`(유저 턴+1, 임계 10), `iters_since_skill`(스킬 호출 시 0 리셋).
- SSE 종료 시 점검 → 임계 도달 시 **데몬 스레드**가 대화 스냅샷+리뷰 프롬프트를 **API 모델**(가벼운 것)에 전달.
- 리뷰는 memory/skill 텍스트 프로토콜만 출력. 본 대화 절대 차단 안 함. 실패는 로그만.
- ⚠️ API 불가(GGUF only) 환경이면 리뷰 생략(메인 채팅과 충돌 방지).

## 큐레이터 (앱 시작 시 따라잡기)
- `curator.json.last_run` 확인 → 오늘과 다르면 1회 실행 후 갱신.
- 30일 미사용→stale, 90일→archived(파일 보존, **삭제 금지**), pinned 면제.

## 만들 파일
- 스크립트: `hermes/store.py` `hermes/memory.py` `hermes/sessions.py` `hermes/skills.py` `hermes/review.py` `hermes/curator.py` `hermes/protocol.py` `hermes/routes.py`
- 스킬 MD: `hermes/prompts/*.md` (memory-rules, skill-authoring, clarify-gate, self-reflection)
- UI: 조합에 `🔮 헤르메스`, 개인 에이전트 "배운 스킬 목록"(pin/삭제/보기) + MEMORY/USER 편집

## 제외 (폐쇄망)
MCP · 게이트웨이 · 웹검색 · 자율 명령실행 · 파인튜닝

## 빌드 순서
1. 설계 MD ← (지금)
2. 저장계층: store/memory/sessions (+ 테스트)
3. protocol 파싱 + routes 채팅 훅 (메모리 주입·블록 처리)
4. 자기학습 skills (생성/patch + BM25 회상, 확인형)
5. 리뷰(카운터) + 큐레이터
6. UI (조합 항목 + 배운 스킬 목록 + 메모리 편집)
