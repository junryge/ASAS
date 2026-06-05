# 🔮 헤르메스 스킬 문서 (Hermes Skills)

헤르메스의 **스킬**은 2종류입니다.
1. **빌트인 스킬** — 공통·자동. 질문 키워드에 맞으면 시스템 프롬프트에 자동 주입. (`hermes/builtin.py`)
2. **자기학습 스킬** — 사용자별·동적. 에이전트가 작업하며 스스로 만들고(확인형) 재사용. (`hermes/skills.py`)

> 데모스 공용 388개 스킬(`scientific-skills/`)은 헤르메스가 아니라 데모스 자산이라 제외.

---

## 1. 빌트인 스킬 (4종) — 전문 포함

질문에 해당 키워드가 있으면 점수 상위 2개가 자동 주입됩니다.

### 🧭 task-planning
- **설명**: 복잡한 작업은 먼저 단계 계획을 세우고 실행
- **발동 키워드**: 만들 · 구현 · 설계 · 프로그램 · 코드 · 연구 · 분석 · 계획 · 파이프라인 · 단계 · 아키텍처 · build · design · research
- **주입 본문**:
  ```
  복잡·다단계 요청이면 바로 답하지 말고:
  1) 목표를 한 줄로 정의
  2) 3~6단계 실행 계획 제시(각 단계 산출물 명시)
  3) 계획대로 실행/작성
  4) 마지막에 빠진 단계가 없는지 자가점검
  ```

### 🐞 systematic-debugging
- **설명**: 오류는 재현→가설→최소수정→검증 순서로
- **발동 키워드**: 오류 · 에러 · 버그 · 디버 · 안돼 · 안 돼 · 실패 · exception · traceback · 고장 · error · bug · fix
- **주입 본문**:
  ```
  오류 해결 순서:
  1) 증상/재현 조건 명확화
  2) 원인 가설 2~3개
  3) 가능성 높은 것부터 최소 변경으로 검증
  4) 환경 의존(패키지/권한) vs 코드 문제 구분
  5) 수정 후 재현 절차로 검증
  ```

### 📊 structured-data-analysis
- **설명**: 데이터는 컬럼/단위 확인 후 가설→통계→시각화
- **발동 키워드**: 데이터 · 분석 · 통계 · 반송 · FAB · 로그 · 수율 · OHT · OHS · CSV · 엑셀 · 컬럼 · 추세 · 이상 · data · analysis
- **주입 본문**:
  ```
  데이터 분석 절차:
  1) 컬럼명·단위·기간을 먼저 확인(추측 금지)
  2) 분석 질문을 가설로 정의
  3) 기술통계 → 이상치 → 상관/추세 순
  4) 실제 값/컬럼만 인용(없는 값 만들지 말 것)
  5) 결론 + 표/차트 시각화 권고
  ```

### ✅ answer-verification
- **설명**: 최종 답 전 자가검증(근거·누락 확인)
- **발동 키워드**: 보고서 · 결론 · 정확 · 검증 · 요약 · report · verify
- **주입 본문**:
  ```
  최종 답 직전 자가검증:
  1) 인용한 수치·컬럼·함수가 실제 컨텍스트에 있는가?
  2) 단정 대신 근거를 붙였는가?
  3) 요청을 빠짐없이 다뤘는가?
  불확실하면 추측임을 명시한다.
  ```

### 동작 방식
- `engine.build_system_prompt(user_id, query)` 가 `builtin.recall_builtin(query, top_k=2)` 호출 → 매칭 스킬 본문을
  `=== 권장 작업 방식 (헤르메스 빌트인 스킬) ===` 섹션으로 프롬프트에 추가.
- 키워드 매칭(점수=일치 키워드 수), 상위 2개만. 순수 프롬프트라 외부망/실행 불필요.

### 새 빌트인 스킬 추가법
`hermes/builtin.py` 의 `BUILTIN_SKILLS` 딕셔너리에 항목 추가:
```python
"skill-name": {
    "desc": "한 줄 설명",
    "keywords": ["발동", "키워드", "들"],
    "body": ("1) ...\n2) ..."),
},
```
→ demos(`demos_v1/hermes/builtin.py`) + 납품본(`agent-kits/hermes-engine/hermes/builtin.py`) **둘 다** 동일하게 추가.

---

## 2. 자기학습 스킬 (사용자별·동적)

에이전트가 **스스로 만드는** 개인 스킬. 처음 0개 → 작업하며 누적.

- **저장**: `demos_data/agents/<user_id>/skills/<이름>/SKILL.md` (공용 스킬과 동일한 frontmatter 형식)
- **생성**: 재사용 가치 있는 절차 발견 → 모델이 ` ```hermes:skill ` 블록 출력 → **사용자 승인(확인형)** 후 저장
- **회상**: 질문과 관련되면 BM25로 상위 2개 본문 자동 주입 (인덱스는 이름+설명만 주입, 본문은 매칭 시)
- **관리(UI)**: 상단바 🔮 헤르메스 → 📚 배운 스킬 탭 — 보기 / 📌pin / 삭제
- **이름 규칙**: 소문자-하이픈 클래스명만(2~40자). 일회성/날짜/세션 산물 이름 거부.
- **상태 관리(큐레이터)**: 30일 미사용→stale, 90일→archived (pinned 면제, **자동 삭제 없음**)

### 스킬 액션 (skill_manage 상당)
| 액션 | 설명 |
|---|---|
| create | 새 스킬 생성 |
| patch | 기존 스킬 부분 수정(find→replace) |
| edit | 전체 본문 교체 |
| delete | 삭제 |

---

## 3. 데모스 연계 — 🧭 헤르메스 작업스킬 조합

빌트인 4종에 대응하는 **실제 scientific-skills**를 묶은 조합을 데모스 스킬조합에 추가:

| 빌트인 | 매핑된 실제 스킬 |
|---|---|
| task-planning | `writing-plans` |
| systematic-debugging | `systematic-debugging` |
| structured-data-analysis | `exploratory-data-analysis` + `statistical-analysis` |
| answer-verification | `verification-before-completion` |

→ 스킬조합 드롭다운의 **🧭 헤르메스 작업스킬** 로 수동 선택 가능(헤르메스 안 켜도 사용).

---

## 한눈에
```
헤르메스 스킬
├─ ① 빌트인 4종 (공통·자동, builtin.py)
│    🧭 task-planning · 🐞 systematic-debugging · 📊 structured-data-analysis · ✅ answer-verification
├─ ② 자기학습 (사용자별·동적, skills.py)  0 → ∞
└─ ③ 데모스 연계 조합 🧭 헤르메스 작업스킬 (실제 SKILL.md 매핑)
```
