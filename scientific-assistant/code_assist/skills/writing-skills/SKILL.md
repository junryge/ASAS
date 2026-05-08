---
name: writing-skills
description: Use when creating new Claude skills or improving existing ones. Applies TDD to documentation - write failing test scenarios first, then minimal skill content to address the specific failures, then refactor to close loopholes. Covers YAML frontmatter rules, description optimization for triggering, progressive disclosure, and context window economy. Use when user says "스킬 만들자", "skill 작성", "SKILL.md", or wants to author/modify any skill.
---

# Writing Skills (스킬 작성법)

## 핵심 원칙

**스킬 작성은 TDD다.** 테스트 없이 스킬 쓰면 삭제하고 다시 시작. 스킬도 코드와 동일한 품질 기준 적용.

사이클:
```
RED: 스킬 없이 시나리오 돌림 → 어떻게 실패하는지 관찰
GREEN: 그 실패를 막는 최소한의 스킬 내용 작성
REFACTOR: 에이전트가 찾는 loophole(합리화) 닫기
```

## 스킬 구조

```
skill-name/
├── SKILL.md            # 필수 (YAML frontmatter + 본문)
├── references/         # 선택 - 상세 참조 (필요 시 읽힘)
│   └── detailed.md
├── scripts/            # 선택 - 실행 가능 도구
└── assets/             # 선택 - 템플릿/아이콘/폰트
```

## YAML Frontmatter

```yaml
---
name: skill-identifier
description: 1024자 이하. "Use when..." 으로 시작. 트리거 조건 명시.
---
```

### name 규칙
- 64자 이하
- kebab-case
- 동명사 권장 (writing-plans, debugging, reviewing-code)

### description 규칙 (가장 중요!)

Description은 Claude가 스킬 invoke 여부 결정하는 유일한 근거. 여기 실패하면 스킬 자체가 무용지물.

**원칙:**
1. 반드시 3인칭 (description은 system prompt에 주입됨)
2. "Use when..." 으로 시작
3. 무엇을 하는지 + 언제 쓰는지 둘 다 포함
4. 핵심 키워드 앞쪽에 배치
5. 한국어 트리거 명시 (존님 환경!)

### description 예시

❌ **나쁨:**
```yaml
description: For async testing
```
너무 추상적. 언제 써야 하는지 없음.

❌ **나쁨:**
```yaml
description: I can help with V7 model
```
1인칭. 무슨 역할인지 불명.

✅ **좋음:**
```yaml
description: Use when working with V7 surge prediction model - retraining, threshold tuning (280 default), feature engineering (11 features: 7 base + 4 momentum), GPU/CPU fallback, or evaluation. Covers XGBoost 30min-to-10min prediction, surge definition (seq_max<300 & future≥300), encoding auto-detect (utf-8→cp949→euc-kr). Use when user says "V7 재학습", "surge 예측", "threshold 튜닝", or working with xgboost_30min_10min_*.pkl files.
```

## Progressive Disclosure (3단계 로딩)

| 레벨 | 언제 로드 | 크기 목표 |
|------|----------|----------|
| Metadata (name + description) | 항상 | ~100 단어 |
| SKILL.md 본문 | 스킬 트리거 시 | < 500 줄 이상적 |
| references/*.md | 필요 시 | 무제한 |

**SKILL.md가 500줄 넘으면 `references/` 로 쪼개라.**

## RED-GREEN-REFACTOR 적용

### RED: Baseline 관찰

스킬 쓰기 전에:
1. 테스트 시나리오 3-5개 작성
2. 스킬 없이 Claude에 돌림 (실제로 혹은 멘탈 시뮬레이션)
3. Claude가 어떻게 실패하는지 기록

예:
```
시나리오: "Logpresso 쿼리 만들어줘. CARRIER 필터링 포함."
Baseline 실패:
- table + search 조합 제안 → 실제로 동작 안 함
- datestr() 함수 사용 → 지원 안 됨
- timechart로 CARRIER 유지 시도 → field 드랍됨
```

### GREEN: 최소 스킬 작성

관찰된 실패를 **정확히** 막는 규칙만 적는다. 가설적 케이스 대응 금지.

```markdown
## Logpresso 아이언 룰

- 인덱스 필드 (CARRIER) 필터링 시 MUST `fulltext` + `ts_data_view_*`
- MUST NOT 사용: `datestr()`, `dateformat()`, `dateparse()`
- CARRIER 같은 non-aggregated field 유지 시 `stats` 사용 (`timechart` X)
```

### REFACTOR: Loophole 닫기

Claude에 다시 돌려서 합리화/우회 시도하는지 관찰:

```
우회 시도: "근데 이번 케이스는 small data라 table+search도 되겠죠?"
→ 스킬에 추가: "데이터 크기 무관 규칙이다. 예외 없다."
```

## 금지 패턴

### ❌ 스킬 본문에 트리거 조건
```markdown
# Use this skill when...
```
→ 트리거는 description에. 본문은 "어떻게 하는지".

### ❌ 워크플로우를 description에 요약
```yaml
description: First do A, then B, then C...
```
→ Claude가 description만 보고 본문 안 읽을 수 있음. description은 트리거만.

### ❌ 애매한 규칙
```markdown
Handle errors appropriately.
```
→ 구체적으로: `except UnicodeDecodeError: try cp949`

### ❌ 500줄 넘는 SKILL.md
→ references/로 쪼개고 본문엔 포인터만.

## 체크리스트 (스킬 완성 후)

- [ ] YAML frontmatter 유효 (파서 돌려봄)
- [ ] description "Use when..." 으로 시작
- [ ] description 3인칭
- [ ] description 한국어 트리거 단어 포함 (존님 환경)
- [ ] SKILL.md 500줄 이하 (이상이면 references/로)
- [ ] 테스트 시나리오 3개 이상 돌려봄
- [ ] Baseline (스킬 없이) 실패 확인
- [ ] 스킬 적용 후 통과 확인
- [ ] Loophole 시도 → 반박 추가
- [ ] 공통 실수 섹션 있음
- [ ] Quick Reference 있음

## 존님 환경용 스킬 작성 팁

### 1. 한국어 트리거 필수
description에 "만들자", "고쳐", "왜 안 되지" 같은 존님 실제 말투 포함.

### 2. ASAS 플랫폼 스킬은 별도로
ASAS용 스킬은 `asas-skill-authoring` 스킬이 따로 있음. Qwen3-235B 타겟과 Claude 타겟은 프롬프트 스타일 다름.

### 3. 폐쇄망 제약 명시
외부 pip install 못 하는 환경이면 스킬 본문에 "의존성: 표준 라이브러리만" 같은 제약 적기.

### 4. 구체적 예시 반드시
추상 규칙만 쓰지 말고 존님 실제 파일명, 컬럼명, 쿼리 예시 넣기:
- `xgboost_30min_10min_D3.pkl`
- `CRT_TM`, `CHG_TM`
- `M14A/M14B/M16/M16A/M16B/M16HUB`
- `ts_data_view_m14a`

## 스킬 템플릿

```markdown
---
name: your-skill-name
description: Use when [트리거 조건]. [스킬이 하는 것]. [한국어 트리거 단어].
---

# Skill Name (한국어 부제)

## 핵심 원칙
[한 단락, 아이언 룰]

## 언제 발동
- ...

## 프로세스
### Step 1: ...
### Step 2: ...

## 존님 환경 특화
[AMHS/ASAS/Qwen3 맥락]

## Common Mistakes
| 증상 | 고침 |
|------|------|

## 체크리스트
- [ ] ...

## Quick Reference
[키 커맨드, 파일명, 값 등]
```

이 템플릿 복사해서 채우는 걸로 시작.
