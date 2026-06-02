# 제4장. 스킬 시스템 — 355개 도메인 지식을 LLM에 주입하기

> **이 장의 목표**
> - `scientific-skills/` 폴더가 어떻게 구성되는지, **스킬 1개의 해부도**를 이해한다.
> - 사용자 질문이 들어왔을 때 **어떤 스킬이 어떻게 자동 선택**되는지(스코어링 알고리즘)를 파악한다.
> - **첫 커스텀 스킬**(`my-skill-semicon-fab`)을 만들어 LLM 응답이 어떻게 달라지는지 확인한다.
> - 스킬 키워드/한글 설명/도메인 그룹 매핑의 **3대 레지스트리**를 직접 수정한다.

---

## 4.1 "스킬" 이란?

스킬(skill)은 한 도메인 지식을 **LLM이 그때그때 읽어들일 수 있는 마크다운 묶음** 으로 캡슐화한 것이다. 학습(fine-tuning) 없이, **시스템 프롬프트에 끼워넣어 즉시 적용** 한다.

```
사용자 질문 → 키워드 매칭 → 관련 스킬 N개 선택
            → SKILL.md 내용을 system prompt에 합성
            → LLM 호출 → 도메인 친화적 답변
```

| 항목 | 파인튜닝 | RAG | **스킬** |
|------|---------|-----|---------|
| 학습 필요 | ✅ | ❌ | ❌ |
| 비용 | 매우 높음 | 중간 | **거의 0** |
| 수정 속도 | 시간/일 단위 | 분 단위 | **초 단위** |
| 모델 종속 | 강함 | 약함 | **없음** |
| 추적성 | 낮음 | 높음 | **매우 높음**(MD 파일) |

> **핵심** — 스킬은 "모델을 가르치는" 게 아니라 **"매 호출마다 컨닝페이퍼를 끼워주는"** 방식이다.

---

## 4.2 폴더 구조 한눈에 보기

```
scientific-assistant/
├── scientific-skills/                ← 스킬 루트
│   ├── biopython/                    ← 스킬 1개 = 폴더 1개
│   │   ├── SKILL.md                  ← (필수) 프롬프트 본문
│   │   ├── scripts/                  ← (선택) 참조 코드
│   │   ├── references/               ← (선택) 추가 자료
│   │   └── assets/                   ← (선택) 그림/CSV 등
│   ├── agent-ai-engineer/
│   │   └── SKILL.md
│   ├── rdkit/
│   ├── ...                           ← 총 355+개
└── demos_v1/skills.py                ← 스킬 로더·매처
```

**규칙**
1. 폴더 이름 = 스킬 ID (소문자, kebab-case 권장)
2. `SKILL.md` 가 반드시 있어야 인식된다 (`scan_skills()` 기준)
3. 그 외 모든 파일은 선택사항이며, 카탈로그에 부가정보로만 노출된다

---

## 4.3 `SKILL.md` 의 해부

`scientific-skills/agent-ai-engineer/SKILL.md` 의 시작 부분.

```markdown
---
name: ai-engineer
description: >
  Expert AI engineer specializing in AI system design, model implementation,
  and production deployment. Use PROACTIVELY for AI architecture design,
  model selection, training pipeline development, and production AI deployment.
model: inherit
color: cyan
tools: Read, Write, Bash, Glob, Grep, python, jupyter, tensorflow, pytorch
---

## Opus 4.5 Capabilities
...
```

### YAML 프론트매터(상단 `---` 블록)

| 필드 | 의미 | 비고 |
|------|------|------|
| `name` | 스킬 이름(표시용) | 폴더명과 달라도 OK |
| `description` | 라우터·사용자에게 노출할 한 줄 설명 | "Use PROACTIVELY" 같은 표현으로 자동 발동 유도 |
| `model` | `inherit`(현 선택 모델) 또는 강제 지정 | 보통 inherit |
| `color` | UI 뱃지 색상 | cyan/magenta/yellow… |
| `tools` | 이 스킬이 가정하는 외부 툴 | 주로 문서화 용도 |

### 본문(프론트매터 이후)

본문은 **그대로 LLM의 system prompt 에 prepend** 된다. 따라서 다음 원칙을 지키면 좋다.

1. **역할**(누가/뭐 하는 사람)
2. **체크리스트**(절대 빠뜨리면 안 되는 항목)
3. **출력 양식**(JSON? 표? 마크다운?)
4. **실행 가능한 예시 1~2개**

> 분량은 **300~800줄** 사이가 가장 효율 좋다. 너무 짧으면 LLM이 무시하고, 너무 길면 컨텍스트 낭비.

---

## 4.4 스킬 자동 선택 — 안에서 무슨 일이 벌어지나

핵심 흐름은 `demos_v1/skills.py` 안에 있다.

```
사용자 질문 q
    │
    ▼
auto_select_skills(q)                          ← 단순 매칭
or context_aware_skill_select(q, history)      ← 멀티턴 라우터
    │
    ▼
_score_query(q.lower())  ──→ skill_id : score 딕셔너리
    │
    ▼
점수 내림차순 정렬 → 상위 3개 반환
```

### 4.4.1 스코어링 규칙

```python
SKILL_KEYWORDS = {
    "biopython": ["생물","서열","DNA","RNA","단백질","FASTA","BLAST", ...],
    "rdkit":     ["RDKit","SMILES","분자","molecule","화합물", ...],
    ...
}

# _score_query (요약)
for kw in keywords:
    if 짧은 ASCII 단어:   # ex: "RNA"
        whole-word 매칭 시 score += len(kw) * 2     # 가중치 2배
    else:                 # ex: "단백질구조"
        부분 문자열 매칭 시 score += len(kw)        # 가중치 1배
```

즉, **긴 키워드일수록 점수가 높고**, 짧은 영문 약어는 단어 경계까지 봐서 오탐을 줄인다.

### 4.4.2 컨텍스트 인식 (멀티턴)

`context_aware_skill_select()` 는 다음을 더 한다.

| 단계 | 가중치 | 설명 |
|------|--------|------|
| 현재 질문 | 1.0 | `_score_query(q)` |
| 직전 3턴 사용자 발화 | 0.3 | 이전 맥락 유지 |
| 키워드 트리거 부스트 | +3~+15 | "에러"→debugging, "PPT"→pptx, "drawio"→drawio-diagram 등 |
| 업로드 파일 확장자 | +3~+8 | `.csv`→exploratory-data-analysis 등 |
| 메타 스킬 | +6~+9 | "계획"→writing-plans, "검증"→verification-before-completion |

이 모든 합산 결과의 **상위 3개** 가 system prompt에 합성된다.

> **TIP** — UI에서 "📂 스킬 자동 선택" 토글을 끄면 사용자가 수동 선택한 스킬만 적용된다.

---

## 4.5 3대 레지스트리 — 어디에 무엇을 더할까

스킬 시스템은 `demos_v1/skills.py` 안에 **3개의 dict**를 갖는다. 새 스킬을 만들 때 **이 3곳에 반드시 등록**해야 자동 추천을 받는다.

| 레지스트리 | 위치 | 역할 |
|-----------|------|------|
| `SKILL_DESC_KO` | skills.py 상단 | 카탈로그 UI에 표시할 **한글 한 줄 설명** |
| `SKILL_KEYWORDS` | skills.py 중단 | **자동 매칭 키워드** 목록 |
| `DOMAIN_SKILLS` | skills.py 별도 블록 | UI **카테고리 그룹**(생물/화학/물리 등) |

빠뜨리면?
- `SKILL_DESC_KO` 누락 → 폴더는 잡히지만 설명 없음 (동작은 됨)
- `SKILL_KEYWORDS` 누락 → **자동 추천 안 됨** (수동 선택만 가능)
- `DOMAIN_SKILLS` 누락 → "기타 스킬" 카테고리로 분류

---

## 4.6 실습 — 첫 커스텀 스킬 `semicon-fab` 만들기

반도체 팹(Fab) 도메인 스킬을 한 개 만들어, LLM 응답이 어떻게 달라지는지 본다.

### Step 1. 폴더와 SKILL.md 생성

`scientific-skills/semicon-fab/SKILL.md` 에 다음 내용을 만든다. (본 가이드의 `docs/examples/ch04/my-skill-semicon-fab/` 에 완성본이 있다.)

```markdown
---
name: semicon-fab
description: >
  반도체 팹(Fab) 공정/장비/계측 도메인 보조 스킬.
  웨이퍼 흐름, 노광/식각/증착/CMP, FOUP/AMHS, OHT/AGV/CNV, MES/EAP, SECS/GEM,
  EES/FDC, 수율(yield)/결함(defect)/PM(예방정비)/RM(수리정비)/OEE 관련 질문에 우선 적용.
model: inherit
color: indigo
tools: Read, Grep, python
---

## 역할
당신은 반도체 팹 운영 데이터 분석을 보조하는 도메인 어시스턴트다.
사용자가 OHT/AGV/CNV 물류·MES 이벤트·SECS/GEM 메시지·수율 데이터에 대해 질문하면
다음 원칙으로 답한다.

## 답변 원칙
1. 약어를 처음 쓸 때 한국어 풀이 병기 (예: AMHS = Automated Material Handling System).
2. 시간 단위 표기는 **초 단위**까지 명확히 (예: 12.3 s, 4 m 20 s).
3. 코드 예시는 pandas/polars 기준. CSV/Parquet 컬럼 이름을 추정해 명시.
4. 수율 이슈는 **공정 → 장비 → 챔버 → 슬롯 → 웨이퍼** 순서로 단계별 드릴다운.
5. 답변 끝에 "검증을 위한 다음 질문 3개" 를 항상 제안.

## 자주 등장하는 도메인 용어
| 약어 | 풀이 | 비고 |
|------|------|------|
| AMHS | Automated Material Handling System | 자동 물류 |
| OHT  | Overhead Hoist Transport | 천장 이송차 |
| AGV  | Automated Guided Vehicle | 무인 운반차 |
| CNV  | Conveyor | 컨베이어 |
| FOUP | Front Opening Unified Pod | 웨이퍼 카세트 |
| MES  | Manufacturing Execution System | 제조 실행 시스템 |
| SECS/GEM | SEMI Equipment Communications Standard | 장비 표준 통신 |
| EES  | Equipment Engineering System | 장비 엔지니어링 |
| FDC  | Fault Detection & Classification | 이상 감지/분류 |
| OEE  | Overall Equipment Effectiveness | 종합설비효율 |

## 출력 양식 예시
질문: "OHT 가 자꾸 N7 베이에서 멈춘다"
→
```
## 진단 가설
1. ...
2. ...

## 점검 SQL/스크립트
...

## 검증을 위한 다음 질문 3개
- ...
```
```

### Step 2. `SKILL_DESC_KO` 추가

`demos_v1/skills.py` 의 `SKILL_DESC_KO` dict에 한 줄.

```python
SKILL_DESC_KO = {
    ...
    "semicon-fab": "반도체 팹 공정/물류/MES",   # ← 추가
}
```

### Step 3. `SKILL_KEYWORDS` 추가

```python
SKILL_KEYWORDS = {
    ...
    "semicon-fab": [
        "반도체","팹","fab","웨이퍼","wafer","FOUP","FOUP카세트",
        "OHT","AGV","CNV","컨베이어","AMHS","베이","bay",
        "MES","EAP","SECS","GEM","EES","FDC","수율","yield",
        "결함","defect","챔버","chamber","슬롯","slot","OEE","PM","RM",
    ],
}
```

### Step 4. (선택) `DOMAIN_SKILLS` 에 카테고리 등록

```python
DOMAIN_SKILLS = {
    ...
    "manufacturing": {
        "label": "제조/팹",
        "icon": "🏭",
        "color": "#4f46e5",
        "skills": ["semicon-fab"],
    },
}
```

### Step 5. 재시작 → 확인

```bash
python app.py
# 콘솔: ✅ 발견된 스킬: 356개  ← 1개 늘었는지 확인
```

브라우저에서 "OHT 가 N7 베이에서 자꾸 멈춰" 라고 물어보면, 응답 상단의 "사용된 스킬" 에 `semicon-fab` 가 떠야 한다.

---

## 4.7 동봉 예제 코드

`docs/examples/ch04/` 에 다음 4개를 두었다.

| 파일 | 용도 |
|------|------|
| `skill_selector_demo.py` | 키워드 dict 만으로 **스코어링 알고리즘 시뮬레이션** |
| `run_with_skill.py` | `SKILL.md` 한 개를 system prompt로 끼워 **사내 LLM 호출** |
| `my-skill-semicon-fab/SKILL.md` | 위 실습의 완성본 |
| `README.md` | 사용법 |

### 4.7.1 `skill_selector_demo.py`

```bash
python skill_selector_demo.py "OHT가 자꾸 N7 베이에서 멈춰요"
# === 상위 스킬 ===
#   [+ 44]  semicon-fab
#   [+ 12]  agent-debugger
#   [+  9]  systematic-debugging
```

키워드 dict와 스코어링 규칙은 본 프로젝트 `skills.py` 와 동일하게 단순화해 두었다. **사용자가 가상의 키워드를 직접 추가해보며 매칭 결과를 즉시 확인**할 수 있다.

### 4.7.2 `run_with_skill.py`

```bash
# 동봉 스킬을 끼워 호출
python run_with_skill.py my-skill-semicon-fab "OHT가 N7 베이에서 멈춰요"

# 다른 스킬도 가능 (절대/상대 경로 또는 scientific-skills/ 하위 ID)
python run_with_skill.py rdkit "벤젠의 SMILES 알려줘"
python run_with_skill.py ../../../scientific-skills/biopython "DNA 역상보 함수 짜줘"
```

내부적으로 `SKILL.md` 의 본문(프론트매터 제외)을 **system 메시지로 prepend** 한 뒤 `Qwen3-Coder-30B-A3B-Instruct` 를 호출한다.

---

## 4.8 잘 만든 스킬의 7가지 특징

1. **단일 책임** — 한 스킬은 한 가지 일만 한다. 여러 도메인을 묶으면 매칭이 흐려진다.
2. **자기 소개 1줄** — `description` 첫 문장만 봐도 무슨 스킬인지 안다.
3. **체크리스트가 있다** — 모델이 빠뜨리기 쉬운 항목을 명시.
4. **출력 양식 예시** — 마크다운/JSON 등 결과 포맷을 박아둔다.
5. **자기 한계 명시** — "이 스킬은 X 는 다루지 않는다" 한 줄.
6. **약어 사전** — 도메인 용어를 표로 정리.
7. **다음 단계 제안** — 답변 끝에 추가 질문 2~3개를 권유하도록 지시.

---

## 4.9 디버깅 팁

### "내 스킬이 자동 추천 안 돼요"
1. `SKILL_KEYWORDS` 에 등록했는가?
2. 키워드가 너무 일반적이지 않은가? (예: "데이터" 하나만으로는 100개 스킬과 충돌)
3. 다른 스킬 키워드와 **점수 경쟁**에서 졌을 수 있다 → `skill_selector_demo.py` 로 확인
4. `MANUAL_ONLY_SKILLS` 에 들어가 있지는 않은지

### "스킬이 너무 길어서 응답이 짧아져요"
- 한 스킬 본문은 가능하면 **800줄 이내**.
- 길어진다면 `references/` 폴더로 분리하고 본문에서 인용만.

### "스킬을 바꿨는데 반영이 안 돼요"
- 캐시(`_SKILLS_CACHE`)가 살아있을 수 있다 → `reload_skills()` 호출 또는 `app.py` 재시작.

---

## 4.10 4장 체크리스트

- [ ] `SKILL.md` 의 프론트매터 5개 필드를 설명할 수 있다
- [ ] `SKILL_KEYWORDS` 의 스코어링 규칙(긴 키워드 우선, ASCII 단어경계)을 안다
- [ ] `context_aware_skill_select()` 의 5단계 가산 흐름을 안다
- [ ] `semicon-fab` 스킬을 직접 만들어 자동 추천을 받아봤다
- [ ] `skill_selector_demo.py` 로 가상의 질문 점수를 본인 머리로 예측해봤다
- [ ] `run_with_skill.py` 로 스킬 적용/미적용 응답 차이를 비교해봤다

---

## 4.11 다음 장 예고

**제5장 — 로컬 GGUF 모델로 완전 오프라인 동작시키기**
- GGUF란? 양자화(Quantization) 한 줄 정리
- `llama-cpp-python` 설치와 첫 로드
- 다중 모델 풀(`MAX_POOL_SIZE`, `VRAM_BUDGET_GB`) 동작 원리
- CPU vs GPU 추론 속도 비교
- 사내 LLM 다운 시 자동 폴백 구성

---

*문서 버전: v1.0 (2026-04-29)*
*브랜치: `claude/create-llm-guide-chapter-one-RDZ12`*
