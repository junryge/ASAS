# Freedom 코딩 어시스턴트 사용 설명서

> 도메인 지식 + 코딩 스킬 + LLM 으로 **신규 프로그램을 완성**하는 사내 폐쇄망용 워크벤치.
> demos_v1 (PPT 플랫폼, 포트 10009) 와는 완전히 독립된 별도 플랫폼입니다.

---

## 목차

1. [개요](#1-개요)
2. [빠른 시작](#2-빠른-시작)
3. [화면 구성](#3-화면-구성)
4. [스킬 — 무엇이고 어떻게 쓰는가](#4-스킬--무엇이고-어떻게-쓰는가)
5. [도메인 지식 — 등록과 검색](#5-도메인-지식--등록과-검색)
6. [워크스페이스 — 파일 첨부](#6-워크스페이스--파일-첨부)
7. [시스템 프롬프트](#7-시스템-프롬프트)
8. [세션 관리](#8-세션-관리)
9. [컨텍스트 시스템 — LLM 입력이 어떻게 만들어지는가](#9-컨텍스트-시스템)
10. [하네스 — Tool 레지스트리·라우터·세션](#10-하네스)
11. [모델 — API · GGUF](#11-모델)
12. [표준 작업 흐름 (신규 프로그램 완성)](#12-표준-작업-흐름)
13. [API 레퍼런스](#13-api-레퍼런스)
14. [폴더 구조](#14-폴더-구조)
15. [트러블슈팅](#15-트러블슈팅)

---

## 1. 개요

**Freedom 코딩 어시스턴트** 는 다음 7가지 기능이 한 곳에 모인 사내 코딩 워크벤치입니다.

| # | 기능 | 위치 |
|---|------|------|
| 1 | 코딩 어시스턴트 페르소나 | `prompts.py` |
| 2 | API 토큰 인증 | `TOKEN.TXT` |
| 3 | GGUF 자동 로딩 | `MODEL_GGUF/` 폴더 |
| 4 | SSE 토큰 스트리밍 | `/api/code/chat/stream` |
| 5 | 도메인 지식 등록·BM25 검색 | `knowledge/` 폴더 |
| 6 | Capacity 스타일 스킬 작성 | `skills/<id>/SKILL.md` |
| 7 | 컨텍스트 + 하네스 통합 | `engine.py` + `harness_setup.py` |

핵심 철학:
- **자동 추론 비용 없음** — knowledge-search · 스킬 자동 선택 · 멀티에이전트 합성을 모두 끔. 사용자가 명시적으로 토글한 것만 동작.
- **빠른 응답** — LLM 토큰이 SSE 로 즉시 화면에 떨어짐.
- **독립** — `code_assist_v1/` 한 폴더 안에 TOKEN, API 설정, GGUF, 스킬, 지식 모두 자체 보관.

---

## 2. 빠른 시작

### 2.1. TOKEN 입력 (선택, GGUF 만 쓰면 불필요)

```
code_assist_v1/TOKEN.TXT
```
파일 안에 사내 HCP API 토큰 한 줄.

### 2.2. (선택) GGUF 모델 추가

```
code_assist_v1/MODEL_GGUF/
└── 원하는모델.gguf
```
폴더에 `.gguf` 파일을 넣으면 기동 시 자동 인식, VRAM 예산 안에서 가장 큰 모델이 자동 로드됩니다.

### 2.3. 실행

```powershell
cd F:\M14_Q\scientific-assistant
python -m code_assist_v1.app_code
```

### 2.4. 접속

```
http://localhost:10010
```

기본 모델 우선순위 (`api_config.json` `default_model_priority`):
1. qwen3-coder-480b
2. qwen3-coder-next
3. qwen3-coder-30b
4. glm-5
5. qwen3-next-80b
6. gpt-oss-20b

---

## 3. 화면 구성

```
┌──── 좌 사이드바 ────┬──── 메인 채팅 ────┬── 우 워크스페이스 ──┐
│ [스킬][지식][세션]  │ 어시스턴트 응답   │ 📁 첨부 파일 트리   │
│                     │ 사용자 질문       │                     │
│                     │ 입력박스 📎📚▶  │ 클릭 → 미리보기     │
└─────────────────────┴───────────────────┴─────────────────────┘
```

### 상단바 버튼
- **모델 드롭다운**: API 모델 + GGUF 통합 목록
- **effort**: 0(정확)~3(창의), LLM temperature 매핑
- **🌙 / ☀️**: 다크/라이트 테마 토글 (브라우저에 저장)
- **⚙️ 프롬프트**: 시스템 프롬프트 보기·편집
- **＋ 세션**: 새 세션 시작 (메시지 비움)
- **📖 문서**: 이 문서

### 입력박스 도구
- **📎** 워크스페이스에 파일 업로드 + 자동 첨부
- **📚** 도메인 지식 검색 ON/OFF (수동 토글)
- **전송 / 중단**: Enter 전송, Esc 또는 버튼으로 스트림 중단

### 사이드바 탭
- **스킬**: 등록된 코딩 스킬 목록 (체크 → 활성화)
- **지식**: 도메인 지식 문서 목록 (CRUD)
- **세션**: 과거 대화 기록 (날짜·시간 표시, 복원·삭제)

---

## 4. 스킬 — 무엇이고 어떻게 쓰는가

### 4.1. 스킬이란?

**스킬 = LLM 의 "작업 매뉴얼" 한 장**.

`SKILL.md` 라는 마크다운 파일 한 장에 frontmatter(메타) + 본문(절차) 형식으로 적힌 문서. 스킬을 활성화하면 그 본문이 시스템 프롬프트에 합쳐져 LLM 이 그 절차대로 행동합니다.

이 형식은 Anthropic 의 Claude Skills(Capacity 스타일) 와 동일합니다.

### 4.2. 시드된 69개 스킬 카테고리

`skills/` 폴더에는 첫 기동 시 `scientific-skills` 에서 가져온 코딩 관련 스킬 69개가 자동 복사됩니다.

| 카테고리 | 예시 | 용도 |
|---------|------|------|
| 언어·런타임 에이전트 | `agent-python-pro`, `agent-typescript-architect`, `agent-rust-engineer` | 해당 언어 베스트 프랙티스 |
| 프레임워크 에이전트 | `agent-fastapi-architect`, `agent-react-pro`, `agent-django-pro` | 프레임워크 절차 |
| 백엔드/프론트/풀스택 | `agent-backend-developer`, `agent-frontend-developer`, `agent-fullstack-developer` | 도메인 전반 |
| DevOps·인프라 | `agent-devops-engineer`, `agent-sre-engineer`, `agent-platform-engineer`, `agent-cloud-architect` | 배포·관측·인프라 |
| 데이터·ML | `agent-data-engineer`, `agent-ml-engineer`, `agent-ai-engineer` | 파이프라인·모델 |
| 보안·QA | `agent-security-engineer`, `agent-qa-engineer` | 보안 검토·테스트 |
| 코드 리뷰·아키텍처 | `agent-code-reviewer`, `agent-architect-reviewer`, `agent-api-designer` | 검토·설계 |
| 메타 (워크플로우) | `writing-skills`, `writing-plans`, `brainstorming`, `systematic-debugging`, `test-driven-development`, `verification-before-completion`, `requesting-code-review`, `using-superpowers`, `skill-creator` | Claude Code 워크플로우 |
| 개발 도구 | `chrome-devtools`, `git`, `github-cli` 등 | 도구 활용 |
| 도메인 검색 | `knowledge-search` | 도메인 지식 BM25 |

전체 목록은 좌사이드 [스킬] 탭이나 `GET /api/code/skills/list` 로 확인.

### 4.3. 스킬 활성화

1. 좌사이드 **[스킬]** 탭 클릭
2. 항목을 **클릭** → 활성화 (좌측 액센트바). 입력박스 위에 🛠 칩으로 표시됨
3. 다시 클릭 → 비활성. 칩의 ✕ 클릭도 동일
4. 항목 **우클릭** → SKILL.md 본문 열람·편집·삭제

활성 스킬은 채팅 요청 시 시스템 프롬프트에 **본문 그대로** 합쳐집니다.

### 4.4. 새 스킬 만들기

좌사이드 [스킬] 탭 하단 **＋** 버튼 → 모달:

```yaml
---
name: my-fastapi-skill
description: FastAPI 라우트와 미들웨어를 작성한다 (라우터 매칭 키워드)
license: MIT
metadata:
  author: ggg3g
  created: 2026-05-06
  tags: [python, fastapi, backend]
---

# 절차

1. ...
2. ...
```

저장하면 `skills/my-fastapi-skill/SKILL.md` 자동 생성, ToolRegistry 즉시 동기화 → 사이드바에 곧바로 등장.

### 4.5. 스킬 작성 팁

- **description 에 라우터 매칭 키워드를 넣으세요**. 하네스 라우터는 description 의 토큰을 매칭에 사용합니다.
- **본문은 절차형**으로 ("1. 먼저… 2. 다음…"). LLM 이 단계로 따르기 좋습니다.
- **반-환각 가드** 를 본문에 한 줄 적어두면 좋습니다 (예: "데이터 컬럼명을 지어내지 말고 모르면 '확인 필요'로 표시").
- **너무 길게 쓰지 마세요**. 4000자 넘어가면 자동으로 잘립니다 (`engine.py`).

---

## 5. 도메인 지식 — 등록과 검색

### 5.1. 빈 상태로 시작

`code_assist_v1/knowledge/` 폴더는 빈 상태로 시작합니다. 사용자가 직접 등록합니다 (user_id 같은 서브폴더 없이 평면).

### 5.2. 등록 방법 3가지

| 방법 | 절차 |
|------|------|
| 인-앱 작성 | [지식] 탭 → ＋ → 파일명 + 마크다운 본문 작성 → 저장 |
| 파일 업로드 | [지식] 탭 → 업로드 → `.md` `.txt` `.pdf` `.docx` 선택 → 텍스트 자동 추출 → `.md` 로 저장 |
| 직접 복사 | 탐색기에서 `code_assist_v1/knowledge/` 에 `.md` 파일 직접 넣기 → 다음 검색 시 자동 reindex |

### 5.3. 권장 frontmatter

```yaml
---
title: M14 FAB 컬럼 정의서
tags: [m14, fab, column]
date: 2026-05-06
---

# 본문
| 컬럼 | 의미 |
|------|------|
| EQP_ID | 장비 ID |
| ...    | ...   |
```

### 5.4. 검색·답변에 사용하기

1. 입력박스의 **📚** 버튼 클릭 → 그린 칩 `📚 도메인 지식 ON` 표시
2. 질문 입력 → 전송
3. 서버가 마지막 사용자 메시지로 BM25 검색 → 상위 8개 문서를 시스템 프롬프트에 주입 → LLM 이 출처 명시하며 답변

**자동 트리거 없음** — 📚 버튼이 켜져 있을 때만 검색이 동작합니다.

### 5.5. BM25 검색 알고리즘

`knowledge_store.py`:
- 한국어 2글자+ / 영문·숫자 2글자+ 토큰화
- BM25 (k1=1.5, b=0.75) + 파일명 부분일치 보너스(+5) + 본문 부분일치 보너스(+0.5)
- 상위 점수의 30% 미만은 제외
- mtime 기반 인덱스 자동 갱신

---

## 6. 워크스페이스 — 파일 첨부

작업 중인 코드를 LLM에 함께 전달하려면 워크스페이스에 올립니다.

### 6.1. 업로드

- 입력박스의 **📎** → 다중 파일 선택 → 자동 업로드 + 자동 첨부 (보라색 칩 `📄 main.py ✕`)
- 또는 우측 패널의 **＋** → 파일 선택

### 6.2. 우측 패널

- 파일 클릭 → 미리보기 (하단 영역)
- 우클릭 → 첨부 토글
- 미리보기 헤더의 **📎첨부** 버튼으로도 토글
- **⟳** 새로고침, **＋** 업로드

### 6.3. 컨텍스트 주입 규칙

`engine.py:build_workspace_block`:
- 파일 1개당 최대 4000자
- 전체 첨부 파일 합쳐서 최대 16000자
- 확장자에 따라 코드블록 언어 자동 감지 (`.py` → python, `.tsx` → tsx 등)
- 초과 시 잘림 표시 (`... (파일 잘림)`)

### 6.4. 저장 위치

`code_assist_v1/workspace/` (사용자 ID 폴더 없음, 평면)

---

## 7. 시스템 프롬프트

상단바 **⚙️ 프롬프트** 클릭:

| 영역 | 설명 |
|------|------|
| **기본 시스템 프롬프트** (664자) | 코딩 어시스턴트 페르소나, 작업 원칙, 응답 형식. 읽기 전용 |
| **반-환각 가드** (176자) | 검증 게이트. 읽기 전용 |
| **사용자 추가 지시** | 자유 입력. 예: "답변은 항상 한국어로", "Python 3.11 문법으로" |

푸터 버튼:
- **초기화**: 사용자 추가 지시 비움 (모달 유지)
- **저장**: 명시적 저장 + `123자` 토스트 (모달 유지)
- **닫기**: 모달 닫기

자동 저장도 동작합니다 (입력 즉시 `localStorage`).

기본 프롬프트는 [`prompts.py`](../prompts.py) 에서 직접 편집할 수 있습니다 (서버 재시작 필요).

---

## 8. 세션 관리

채팅 응답이 끝날 때마다 자동으로 `/api/harness/session/save` 호출 → `sessions/<sid>.json` 에 저장.

좌사이드 [세션] 탭:
```
첫 사용자 메시지 미리보기...                      [12턴]  [✕]
2026-05-06 14:32  ·  34215181
```

- **클릭** → 메시지 복원 (현재 세션 표시는 액센트색)
- **✕ 버튼** → 확인 후 삭제
- **상단바 ＋ 세션** → 새 세션 시작 (`session_id` 리셋)

---

## 9. 컨텍스트 시스템

LLM 한 호출당 시스템 메시지가 어떻게 만들어지는지:

```
[1] 기본 시스템 프롬프트 (CODING_SYSTEM_PROMPT, 664자)
   ↓
[2] 반-환각 가드 (ANTI_HALLUCINATION, 176자)
   ↓
[3] 활성 스킬 본문 (각 SKILL.md, 컨텍스트 예산의 40% 까지)
   ↓
[4] 사용자 추가 지시 (⚙️ 프롬프트의 user_extra)
   ↓ → 여기까지가 system 메시지 #1

[5] 도메인 지식 검색 결과 (📚 ON 시, 최대 12000자) → system 메시지 #2
[6] 워크스페이스 첨부 파일 (최대 16000자, 파일당 4000자) → system 메시지 #3

[7] 대화 히스토리 (최근 12턴 트림)
   ↓
LLM 호출
```

구현: `engine.py`
- `build_coding_system_prompt(skill_ids, user_extra, n_ctx)` → 1+2+3+4
- `build_knowledge_block(query, results)` → 5
- `build_workspace_block(files)` → 6
- `trim_message_history(messages, max_turns=12)` → 7

호출 흐름:
```
chat.js → POST /api/code/chat/stream
       ↓
routes_chat_stream.py
  - 모델 해석
  - 시스템 프롬프트 빌드 (engine)
  - knowledge / workspace 블록 추가
  - 메시지 12턴 트림
  - API 또는 GGUF 로 SSE 스트림
       ↓
LLM 토큰 → 클라이언트
```

---

## 10. 하네스

**하네스 = LLM 호출 외부의 운영 레이어**. Tool 레지스트리, 라우터, 세션, 권한, 피드백을 담당합니다.

### 10.1. 구성요소 (`harness-mvp/harness/`)

| 모듈 | 역할 |
|------|------|
| `Tool`, `ToolRegistry` | 스킬 = Tool 로 등록·조회·실행 |
| `ToolRouter` | 사용자 질의 → 토큰 매칭 점수로 스킬 추천 |
| `HarnessEngine` | 단일 턴 실행 루프 (예산·스트림) |
| `ToolPermissionContext` | deny-list 권한 차단 |
| `StoredSession` / `save_session` / `load_session` | 세션 JSON 저장·복원 |
| `HistoryLog` | 이벤트 로그 |
| `FeedbackStore` | 스킬별 품질 피드백 누적 |
| `select_experts` | 멀티 에이전트 동적 선정 |

### 10.2. 통합 (`harness_setup.py`)

기동 시 `setup_harness(app)` 가:
1. `init_harness(SKILLS_DIR)` — 빈 레지스트리 생성
2. `sync_skills()` — `code_assist_v1/skills/` 의 모든 SKILL.md 를 ToolRegistry 에 Tool 로 등록 (description = frontmatter 의 description)
3. `register_harness_routes(app)` — `/api/harness/*` 16개 엔드포인트 등록

스킬 CRUD 시 자동 sync — `routes_skills.py` 의 create / update / delete 후 `_sync_harness()` 호출 → 추가·갱신·제거 모두 즉시 반영.

### 10.3. 노출되는 16개 엔드포인트

| 엔드포인트 | 용도 |
|----------|------|
| GET `/api/harness/status` | 도구 수·세션 수·이벤트 수 |
| GET `/api/harness/skills?q=...` | 스킬 검색 |
| POST `/api/harness/route` | 질의 → 추천 스킬 (라우터 매칭) |
| POST `/api/harness/reload` | ToolRegistry 강제 재초기화 |
| POST `/api/harness/session/save` | 세션 저장 (채팅 종료 시 자동 호출됨) |
| GET `/api/harness/session/load/<id>` | 세션 복원 |
| GET `/api/harness/session/list` | 세션 목록 |
| DELETE `/api/harness/session/delete/<id>` | 세션 삭제 |
| GET `/api/harness/history` | 이벤트 로그 |
| POST `/api/harness/suggest-combo` | 보조 스킬 추천 |
| POST `/api/harness/validate-combo` | 스킬 조합 유효성 |
| POST `/api/harness/optimize-groups` | 스킬 그룹 최적화 (병렬 실행용) |
| POST `/api/harness/expert-pool` | 동적 에이전트 선정 |
| POST `/api/harness/feedback` | 피드백 저장 |
| GET `/api/harness/feedback/<skill>` | 스킬별 피드백 요약 |
| POST `/api/harness/feedback/prompt-hint` | 피드백 기반 프롬프트 힌트 |

### 10.4. 사용자가 일상적으로 만나는 곳

- [세션] 탭의 모든 동작 (저장·로드·삭제)
- 사용자가 만든 스킬이 `agent-*` 옆에 함께 노출됨 (자동 sync)
- 향후 멀티에이전트·피드백 루프 확장의 기반

---

## 11. 모델

### 11.1. API 모델 10개 (`api_config.json`)

| ID | 용도 | 컨텍스트 |
|----|------|---------|
| qwen3-coder-480b | 코딩 (최강) | 128K |
| qwen3-coder-next | 코딩 (균형) | 128K |
| qwen3-coder-30b | 코딩 (빠름) | 128K |
| glm-5 | 분석·일반 | 128K |
| qwen3-next-80b | 분석·요약 | 128K |
| qwen35-397b / -fp8 | 초대형 | 128K |
| qwen25-vl-72b / qwen3-vl-30b | 비전 | 128K |
| gpt-oss-20b | 빠름 | 128K |

### 11.2. GGUF 자동 로딩

`MODEL_GGUF/` 의 `.gguf` 파일을 첫 기동 시 자동 스캔.

- VRAM 예산 (`api_config.json` 의 `gguf.vram_budget_gb`, 기본 14GB) 안에서 가장 큰 모델 자동 로드
- 환경변수 `GGUF_VRAM_BUDGET_GB` 로 덮어쓰기 가능
- `mmproj-*.gguf` 파일이 같이 있으면 비전 모드 자동 감지
- Qwen3 시리즈는 `flash_attn=True` 자동 적용
- 모델 드롭다운에 `gguf-0`, `gguf-1`… 으로 노출

---

## 12. 표준 작업 흐름

신규 프로그램 완성까지의 권장 흐름:

```
[1] 도메인 지식 등록
    [지식] 탭 → ＋ 또는 업로드
    예: "M14_컬럼정의서.md", "사내API_스펙.md"
    ↓
[2] 코딩 스킬 작성 (선택)
    [스킬] 탭 → ＋ 새 스킬
    예: "M14 데이터로 FastAPI 만들기" 절차
    ↓
[3] 모델 선택
    상단 모델 드롭다운 → qwen3-coder-480b
    ↓
[4] 활성화
    - [스킬] 탭에서 사용할 스킬 클릭 (🛠 칩 표시)
    - 입력박스의 📚 ON (도메인 지식 검색)
    - 📎 으로 기존 코드 첨부
    ↓
[5] 질문
    "이 스펙으로 신규 프로그램 만들어줘"
    ↓ SSE 스트리밍
[6] 응답 코드를 워크스페이스에 저장
    /api/code/workspace/save 또는 직접 다운로드
    ↓
[7] 다음 턴에 다시 첨부 → 반복
```

---

## 13. API 레퍼런스

### 13.1. 코드 어시스턴트 API (`/api/code/*`, 20개)

| 엔드포인트 | 메서드 | 용도 |
|----------|-------|------|
| `/api/code/models` | GET | API + GGUF 모델 통합 목록 |
| `/api/code/system_prompt` | GET | 기본 시스템 프롬프트 |
| `/api/code/chat/stream` | POST | SSE 채팅 (메인) |
| `/api/code/skills/list` | GET | 스킬 목록 |
| `/api/code/skills/<id>` | GET | 스킬 상세·본문 |
| `/api/code/skills/create` | POST | 스킬 생성 |
| `/api/code/skills/update` | POST | 스킬 수정 |
| `/api/code/skills/delete` | POST | 스킬 삭제 |
| `/api/code/skills/whitelist` | GET·POST | 화이트리스트 |
| `/api/code/knowledge/list` | GET | 지식 파일 목록 |
| `/api/code/knowledge/view/<file>` | GET | 본문 조회 |
| `/api/code/knowledge/create` | POST | 작성 |
| `/api/code/knowledge/upload` | POST | 업로드 (md/txt/pdf/docx) |
| `/api/code/knowledge/delete` | POST | 삭제 |
| `/api/code/knowledge/search` | POST | BM25 검색 |
| `/api/code/knowledge/reindex` | POST | 인덱스 재빌드 |
| `/api/code/workspace/tree` | GET | 파일 트리 |
| `/api/code/workspace/file?path=` | GET | 파일 본문 |
| `/api/code/workspace/upload` | POST | 업로드 |
| `/api/code/workspace/save` | POST | 인-앱 저장 |
| `/api/code/workspace/delete` | POST | 삭제 |

### 13.2. 하네스 API (`/api/harness/*`, 16개)

[10.3 노출되는 16개 엔드포인트](#103-노출되는-16개-엔드포인트) 참조.

### 13.3. SSE 채팅 페이로드

```json
POST /api/code/chat/stream
{
  "model": "qwen3-coder-480b",
  "messages": [{"role": "user", "content": "..."}],
  "skills": ["agent-python-pro", "writing-plans"],
  "effort": 2,
  "enable_knowledge": true,
  "workspace_files": [{"filename": "main.py", "content": "..."}],
  "system_prompt": "추가 지시",
  "disable_fallback": true
}
```

응답 (SSE):
```
data: {"delta": "토큰"}\n\n
data: {"delta": "토큰"}\n\n
...
data: {"done": true, "model_used": "...", "elapsed_ms": 1234, "loaded_skills": [...], "knowledge_files": [...]}\n\n
```

---

## 14. 폴더 구조

```
code_assist_v1/
├── TOKEN.TXT                ← API 토큰 (자체)
├── api_config.json          ← 모델 설정 10개 (자체)
├── MODEL_GGUF/              ← .gguf 파일 (자체)
│
├── skills/                  ← 코딩 스킬 69개 (시드됨, 평면)
│   ├── agent-python-pro/SKILL.md
│   ├── agent-fastapi-architect/SKILL.md
│   └── ...
├── knowledge/               ← 도메인 지식 (사용자가 등록, 평면)
│   └── *.md
├── workspace/               ← 작업 파일 (평면)
├── sessions/                ← 세션 JSON (보조, harness 가 .harness_sessions 사용)
│
├── static/                  ← 프론트엔드 SPA
│   ├── index.html
│   ├── app.css              ← 다크/라이트 변수
│   ├── app.js               ← 전역 상태·테마·모달
│   ├── chat.js              ← SSE 수신·렌더
│   ├── skills.js            ← 스킬 패널
│   ├── knowledge.js         ← 지식 패널
│   ├── workspace.js         ← 워크스페이스 패널
│   ├── sessions.js          ← 세션 패널 (삭제·시간)
│   └── docs.html            ← 이 문서의 HTML 버전
│
├── docs/USAGE.md            ← 이 문서
│
├── __init__.py              ← Flask 앱 + create_app()
├── app_code.py              ← 진입점 (포트 10010)
├── config.py                ← 경로·TOKEN·모델 import
├── models.py                ← MODEL_REGISTRY 자체 빌드
├── gguf_loader.py           ← MODEL_GGUF/ 스캔·로드
├── utils.py                 ← gguf_model 글로벌
│
├── prompts.py               ← CODING_SYSTEM_PROMPT 등
├── engine.py                ← 컨텍스트 빌더
│
├── routes_models.py         ← /api/code/models, /api/code/system_prompt
├── routes_chat_stream.py    ← /api/code/chat/stream (SSE)
├── routes_skills.py         ← /api/code/skills/*
├── routes_knowledge.py      ← /api/code/knowledge/*
├── routes_workspace.py      ← /api/code/workspace/*
│
├── skill_filter.py          ← skills/ 단일 폴더 스캔
├── skill_whitelist.py       ← 코딩 스킬 화이트리스트
├── knowledge_store.py       ← BM25 검색 자체 구현
├── seed.py                  ← 첫 기동 시 코딩 스킬 시드
└── harness_setup.py         ← harness-mvp 통합
```

`scientific-skills/`, `knowledge/ggg3g/` 등 외부 폴더는 **첫 시드 때만** 참조됩니다. 이후엔 `code_assist_v1/` 안만 봅니다.

---

## 15. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|------------|
| `OSError: Windows error 6` | GGUF 로드가 콘솔 핸들을 깨뜨림. `app_code.py` 가 stdout/stderr 복원 + click.echo 무력화로 처리. 그래도 보이면 `python -m code_assist_v1.app_code` 가 최신 코드인지 확인 |
| 시작 시 `TOKEN.TXT 비어있음` | 사내 API 키가 없어 API 모델 비활성. GGUF 가 있으면 그것만으로 정상 동작 |
| `모든 모델이 VRAM 예산 초과` | 가장 작은 모델 자동 로드. 환경변수 `GGUF_VRAM_BUDGET_GB=24` 로 덮어쓰기 |
| 📚 토글 켰는데 검색 결과 없음 | `knowledge/` 폴더에 `.md` 파일이 있는지 확인. 검색어가 너무 짧으면 BM25 매칭 안 됨 |
| 스킬 목록이 비어있음 | `skills/` 폴더가 비어있고 `scientific-skills/` 도 없으면 시드가 못 일어남. 직접 SKILL.md 폴더를 만들거나 ＋로 작성 |
| 한국어 라우터 매칭이 약함 | `harness-mvp` 라우터는 단순 토큰 매칭. 영어 키워드를 description 에 넣으면 매칭률 향상 |
| Marked.js / highlight.js CDN 차단 | 폐쇄망에서 CDN 차단되면 `chat.js` 의 `miniRenderMd` 폴백 동작. syntax highlighting 만 비활성. 필요 시 `static/vendor/` 에 로컬 복사 |

---

## 부록 A. 환경 변수

| 변수 | 기본 | 용도 |
|------|------|------|
| `CODE_ASSIST_PORT` | 10010 | 서버 포트 |
| `GGUF_VRAM_BUDGET_GB` | 14 | GGUF 자동 로드 예산 |
| `GGUF_MAX_POOL_SIZE` | 4 | 멀티 GGUF 풀 |
| `AGENT_MAX_TOKENS` | 8192 | 에이전트 응답 cap |
| `DEFAULT_N_CTX` | 32768 | LLM 컨텍스트 길이 |
| `PYTHONIOENCODING` / `PYTHONUTF8` | utf-8 / 1 | Windows 콘솔 보호 (config.py 가 자동 설정) |

## 부록 B. 키보드 단축

| 키 | 동작 |
|----|------|
| Enter | 메시지 전송 |
| Shift + Enter | 줄바꿈 |
| Esc | 스트리밍 중단 |
| Ctrl + F5 | 강제 새로고침 (테마·UI 즉시 반영) |
