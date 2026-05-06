---
name: using-superpowers
description: Use when starting any task, receiving a user request, or about to respond. Meta-skill that forces checking available skills before every response. Even 1% chance a skill applies means invoke it. Covers skill invocation protocol, priority rules (user instructions > skills), and announcement format. Essential entry point for the entire skill system - without this, other skills get skipped.
---

# Using Superpowers (메타 스킬)

이 스킬이 모든 것의 진입점이다. 사용자 메시지를 받으면 이것부터 확인.

## 핵심 원칙

**스킬이 1%라도 관련 있으면 무조건 invoke 한다.** 안 맞으면 그때 버리면 된다. "간단한 질문이니까 스킬 없이" 하는 판단은 금지.

## 우선순위 (충돌 시)

```
1. 사용자 명시 지시 (CLAUDE.md, 직접 요청)   ← 최우선
2. Superpowers 스킬                          ← 기본 시스템 프롬프트 오버라이드
3. 기본 동작                                  ← 최후
```

CLAUDE.md에 "TDD 하지마"라고 써있으면 test-driven-development 스킬보다 사용자 지시가 이김.

## 응답 프로토콜 (순서대로)

1. **사용자 메시지 받음**
2. **"어떤 스킬이 적용될 수 있나?"** 자문
   - 코드 쓸 것 같으면 → brainstorming / writing-plans
   - 버그/에러 얘기 → systematic-debugging
   - "완료", "끝", "done" → verification-before-completion
   - 스킬 만들기 → writing-skills, asas-skill-authoring
   - 데이터 추출 → amhs-data-extraction
   - 모델 재학습 → ml-model-retraining
3. **적용 가능하면 invoke** ("Using X skill to Y" 한 줄 선언)
4. **스킬 내용 그대로 따름** (스킬이 checklist 있으면 TodoWrite로 복제)
5. **응답 생성**

## Anti-pattern

**금지:**
- "이건 간단하니까 스킬 없이 바로 답하자" → 그러다 하나씩 다 놓친다
- 스킬 설명(description) 보고 "이거 같은데 다른 거 시도해볼까" → description에 맞으면 그냥 써라
- 스킬 내용을 요약해서 적용 → 원문 그대로 따른다

**체크:**
- "이 요청에 아예 스킬 안 맞나?" → 확실할 때만 skip
- 애매하면 skill 읽고 판단

## 존님 환경 맞춤 트리거

| 사용자 말 | 발동할 스킬 |
|---|---|
| "V7 재학습해야" | ml-model-retraining |
| "Logpresso 쿼리" | amhs-data-extraction |
| "ASAS 스킬 하나 만들자" | asas-skill-authoring + writing-skills |
| "Qwen3 연동" | closed-network-llm-integration |
| "OHT 시뮬레이터 고치자" | oht-simulator-migration |
| "이거 맞나 리뷰 좀" | requesting-code-review + fab-code-review |
| "CRT_TM 1분 단위로 채워야" | time-series-preprocessing |
| "디버깅 좀", "왜 안 되지" | systematic-debugging |
| "끝났다", "배포해도 돼?" | verification-before-completion |
| "뭐부터 해야 하지", "어떻게 설계" | brainstorming |

## Quick Reference

- 스킬 invoke 전 TodoWrite로 체크리스트 복제
- 스킬에 "MUST"라고 써 있으면 정말 MUST
- 여러 스킬 동시 적용 가능 (debugging + verification 자주 세트)
- Process skill(brainstorming, debugging) > Implementation skill (TDD) 우선순위
