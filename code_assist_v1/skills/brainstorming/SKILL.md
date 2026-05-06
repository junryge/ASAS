---
name: brainstorming
description: Use when the user asks to build, design, or plan something new - before writing ANY code. Socratic design refinement that forces spec clarification through questions, explores alternatives, and presents design in digestible sections for approval. Produces a saved design document. Use when user says "만들자", "설계해줘", "어떻게 구현하면 좋을까", "새 기능 추가", or describes a rough idea that needs tightening before implementation.
---

# Brainstorming (설계 세션)

## 핵심 원칙

**사용자가 "X 만들어줘"라고 해도 바로 코드 쓰면 안 된다.** 무엇을 진짜 원하는지, 제약 조건이 뭔지, 대안은 뭐가 있는지 먼저 파악. Socratic 방식으로 질문해서 스펙 뽑아낸다.

## 언제 발동

- "새 기능 만들자"
- "X를 구현하고 싶은데"
- "어떻게 설계해야 할까"
- 막연한 아이디어 ("AMHS 통합 대시보드 만들자" 같은)

## 언제 skip

- 버그 수정 (→ systematic-debugging)
- 이미 스펙 명확한 단순 태스크 ("이 함수 하나 추가해줘")
- 사용자가 "시간 없으니까 그냥 짜" 명시

## 프로세스

### Phase 1: 현재 상황 파악

다음 질문을 **실제로 던져서** 답 받아야 한다. 혼자 추측해서 넘어가지 말 것.

1. **목표:** "이게 해결하려는 진짜 문제가 뭔가요?"
2. **사용자:** "누가, 언제, 어떤 상황에서 이걸 쓰나요?"
3. **기존 자산:** "지금 있는 코드/데이터/시스템 중 뭘 재사용할 수 있나요?" (ASAS, V7, OHT 시뮬레이터 등)
4. **제약:** "폐쇄망, 성능, 용량, 마감일, 승인 프로세스 중 걸리는 게 있나요?"
5. **성공 기준:** "어떤 상태가 되면 '끝났다'고 할 수 있나요?"

### Phase 2: 대안 제시 (최소 2개)

하나의 안만 내지 마라. 적어도 2개 제시하고 트레이드오프 명시.

```
안 A: [접근법 요약]
  장점: ...
  단점: ...
  공수: ...

안 B: [다른 접근법]
  장점: ...
  단점: ...
  공수: ...

추천: A (이유: ...)
```

### Phase 3: 섹션 단위 합의

설계 문서를 한 번에 쏟아내지 말고 섹션별로 확인 받는다:

1. 아키텍처 개요 → 확인
2. 데이터 모델/스키마 → 확인
3. 주요 컴포넌트/API → 확인
4. 테스트 전략 → 확인
5. 배포/운영 → 확인

각 섹션마다 "이 부분 이대로 가도 되나요?" 물어본다.

### Phase 4: 설계 문서 저장

합의된 내용을 `docs/plans/YYYY-MM-DD-<feature>.md`에 저장. 이 문서가 다음 `writing-plans` 스킬의 입력이 됨.

## ASAS/AMHS 맥락 질문 템플릿

AMHS 관련이면 추가로:
- "M14A/M14B/M16A/M16B/M16HUB 중 어느 FAB 대상?"
- "실시간(<1분) 필요? 배치(시간/일)로 충분?"
- "Oracle AWS_IDC_DATA_HIS? Logpresso ts_data_view_*? 둘 다?"
- "현장 OP한테 노출? SM만? 개발용?"

ML 관련이면:
- "V7 (XGBoost) 재활용 가능? 아니면 다른 모델?"
- "학습 데이터 어디서 뽑을지 (CRT_TM 범위)?"
- "예측 대상(TARGET)과 lead time 몇 분?"
- "허용 가능한 오탐률은?"

LLM 관련이면:
- "Qwen3-235B로 충분? 다른 모델 필요?"
- "스트리밍? 동기?"
- "한국어 시스템 프롬프트 있나?"

## Common Mistakes

**A. 혼자 스펙 추측해서 코드부터**
- 증상: 사용자가 한 줄 요청 → 바로 100줄 코드
- 고침: Phase 1 질문 3개 이상 먼저 던져라

**B. 대안 없이 최적해 제시**
- 증상: "A로 하세요" 단일안
- 고침: 항상 최소 2개 비교

**C. 대형 설계 문서 한방 투척**
- 증상: 10섹션을 한 번에 내고 "어때요?" 묻기
- 고침: 섹션별로 쪼개서 하나씩 확인

**D. 기존 자산 무시**
- 증상: ASAS 355 스킬 있는데 비슷한 거 새로 만들자고 제안
- 고침: Phase 1에서 재사용 가능 자산 반드시 확인

## 출력 포맷

설계 문서 파일은 다음 구조:

```markdown
# [Feature Name] 설계 문서

**목표:** (한 문장)
**배경:** (왜 필요한가)

## 요구사항
- 기능 요구: ...
- 비기능 요구 (성능/보안/운영): ...

## 아키텍처
[다이어그램 or 설명]

## 주요 결정 (Decision Log)
| # | 결정 | 이유 | 대안 |
|---|------|------|------|
| 1 | XGBoost 재사용 | V7 검증됨, 공수↓ | LightGBM |

## 컴포넌트
1. [컴포넌트 A] - 책임: ...
2. [컴포넌트 B] - 책임: ...

## 테스트 전략

## 마일스톤
```

이 문서가 `writing-plans`의 입력이다.
