# 제3장. 모델·엔드포인트 자유롭게 갈아끼우기

> **이 장의 목표**
> - `api_config.json` 의 **구조**와 각 필드의 의미를 이해한다.
> - 사내 LLM 7종(GLM-5, Qwen3-Coder-480B/Next/30B, Qwen3-VL-30B, Qwen3-Next-80B, GPT-OSS-20B)을 자유롭게 **갈아끼우는 법**을 익힌다.
> - 새 모델을 **추가/제거** 한다.
> - 토큰 한도·온도(temperature) 등 **세부 튜닝 파라미터**를 조정한다.
> - `curl` 한 줄과 파이썬 진단 도구로 **API 호출을 디버깅** 한다.

---

## 3.1 왜 모델을 바꿔쓸까?

| 상황 | 권장 모델 | 이유 |
|------|-----------|------|
| 짧은 질의응답·빠른 응답 | `gpt-oss-20b`, `qwen3-vl-30b` | 저비용·저지연 |
| 코드 작성·리팩터링 | `qwen3-coder-30b`, `qwen3-coder-next` | 코드 특화 |
| 대규모 코드베이스 분석 | `qwen3-coder-480b` | 480B 파라미터 |
| 문서 요약·심층 분석 | `qwen3-next-80b`, `glm-5` | 분석 능력 |
| 이미지/표 인식 | `qwen3-vl-30b` | 비전 지원 |

**핵심 원칙** — 한 모델에 묶이지 말고, 작업 유형에 맞는 모델을 선택해라. `api_config.json` 한 파일만 편집하면 된다.

---

## 3.2 `api_config.json` 한눈에 보기

`scientific-assistant/api_config.json` 파일은 5개의 큰 블록으로 구성된다.

```json
{
  "_doc": "...",
  "_updated": "...",
  "token_settings": { ... },   // ① 토큰·컨텍스트 한도
  "gguf": { ... },             // ② 로컬 GGUF 풀 설정 (5장)
  "logpresso": { ... },        // ③ Logpresso 연결 (10장)
  "models": { ... }            // ④ 사내 LLM 모델 7개
}
```

### 3.2.1 `token_settings` — 토큰/컨텍스트 한도

```json
"token_settings": {
  "agent_max_tokens": 8192,     // 일반 에이전트 1회 응답 상한
  "synth_max_tokens": 16384,    // 합성/요약 에이전트 상한 (더 길어야 함)
  "default_n_ctx": 4096,        // GGUF 기본 컨텍스트
  "gguf_reply_cap": 4096,       // GGUF 응답 토큰 상한
  "gguf_ctx_reserve": 1536      // GGUF 입력 여유분
}
```

> **TIP** — 답변이 자꾸 중간에서 끊긴다면 `agent_max_tokens` 부터 늘려본다(예: 8192 → 12288).

### 3.2.2 `models` — 모델 레지스트리

각 모델 한 개의 풀 스펙:

```json
"qwen3-coder-30b": {
  "env_id": "coder-common",
  "model": "Qwen3-Coder-30B-A3B-Instruct",
  "url": "http://common.llm.skhynix.com/v1/chat/completions",
  "name": "Coder-30B-A3B (Common)",
  "capabilities": ["text", "code", "medium"],
  "context_window": 128000,
  "priority": 3,
  "cost_tier": "low"
}
```

| 필드 | 의미 |
|------|------|
| `env_id` | 내부 환경 식별자 (UI 드롭다운·라우터 분기) |
| `model` | 실제 API에 보내는 모델명 |
| `url` | OpenAI 호환 엔드포인트 (`/v1/chat/completions`) |
| `name` | UI에 표시되는 라벨 |
| `capabilities` | 라우터가 자동 선택할 때 쓰는 태그 |
| `context_window` | 입력+출력 토큰 상한 |
| `priority` | 1=최우선, 숫자↑=후순위 (폴백 체인용) |
| `cost_tier` | `low`/`medium`/`high` — 비용 인지 라우팅 |

### 3.2.3 현재 등록된 모델 7종

| 키 | 엔드포인트 | 강점 |
|----|-----------|------|
| `glm-5` | dev.hcp | 일반·분석 (medium) |
| `qwen3-coder-480b` | dev.hcp | **대형 코드** (high) |
| `qwen3-coder-next` | dev.hcp | 코드 (medium) |
| `qwen3-vl-30b` | dev.hcp | **비전** (low) |
| `gpt-oss-20b` | common | 빠른 일반 (low) |
| `qwen3-next-80b` | common | 분석·요약 (medium) |
| `qwen3-coder-30b` | common | 코드 (low) — **2장 기본** |

---

## 3.3 로딩 순서 — 설정 → 코드까지

```
api_config.json
   │
   ▼
demos_v1/config.py        ← _EXT_CONFIG 로 메모리 적재
   │
   ▼
demos_v1/models.py        ← MODEL_REGISTRY 빌드 (capabilities: list→set)
   │
   ▼
demos_v1/router.py        ← 작업 유형에 맞는 모델 자동 선택
   │
   ▼
demos_v1/routes_chat.py   ← /api/chat 호출
```

`api_config.json` 만 수정하면 **`app.py` 재시작만으로** 새 모델이 메뉴에 뜬다. 코드 수정 불필요.

---

## 3.4 실습 1 — 새 모델 추가하기

예: 사내에 `Qwen3-Math-7B` 라는 수학 특화 모델이 새로 배포되었다고 가정.

### Step 1. `api_config.json` 편집

`models` 블록 안에 한 항목 추가:

```json
"qwen3-math-7b": {
  "env_id": "math",
  "model": "Qwen3-Math-7B-Instruct",
  "url": "http://common.llm.skhynix.com/v1/chat/completions",
  "name": "Math-7B (Common)",
  "capabilities": ["text", "math", "fast"],
  "context_window": 32000,
  "priority": 3,
  "cost_tier": "low"
}
```

### Step 2. 토큰 확인

`token.txt`가 해당 엔드포인트에 유효한지 확인.

```bash
curl -s http://common.llm.skhynix.com/v1/models \
  -H "Authorization: Bearer $(cat token.txt)" | grep -i math
```

목록에 `Qwen3-Math-7B-Instruct` 가 보이면 OK.

### Step 3. 재시작

```bash
python app.py
```

콘솔에 `[CONFIG] api_config.json 로드 완료 (8개 모델)` 가 뜨면 성공.

### Step 4. 코드 없이 호출 확인

```bash
python docs/examples/ch03/model_probe.py qwen3-math-7b "2+2=?"
```

---

## 3.5 실습 2 — 모델 제거/비활성화

가장 안전한 방법은 **삭제가 아닌 주석화**다. JSON은 주석을 지원하지 않으므로 **키 이름 앞에 `_` 를 붙여 비활성** 한다.

```json
"_qwen3-vl-30b": { ... }   // 이름 변경만 하면 레지스트리에서 빠진다
```

또는 더 명확하게 `priority`를 매우 큰 값(예: `99`)으로 둬서 폴백 체인 뒤로 보낸다.

---

## 3.6 실습 3 — 토큰 한도 늘리기

응답이 자꾸 잘리면 `token_settings` 를 조정한다.

```json
"token_settings": {
  "agent_max_tokens": 12288,    // 8192 → 12288
  "synth_max_tokens": 24000     // 16384 → 24000
}
```

환경변수로 임시 오버라이드도 가능:

```bash
# Linux/macOS
export AGENT_MAX_TOKENS=12288
python app.py

# Windows PowerShell
$env:AGENT_MAX_TOKENS="12288"; python app.py
```

(`demos_v1/config.py` 가 `os.getenv(...)` 로 환경변수 우선 적용)

---

## 3.7 실습 4 — temperature 등 sampling 파라미터

OpenAI 호환 엔드포인트는 다음 파라미터를 모두 받는다.

| 파라미터 | 의미 | 권장값 |
|---------|------|-------|
| `temperature` | 무작위성 (0=결정적, 2=과한 창의) | 코드: 0.0~0.3 · 글: 0.7 |
| `top_p` | 누적 확률 컷오프 | 0.9 (기본) |
| `top_k` | 후보 토큰 수 | 40 (Qwen 계열) |
| `presence_penalty` | 같은 단어 반복 억제 | 0.0~0.5 |
| `frequency_penalty` | 빈도 기반 페널티 | 0.0~0.5 |
| `stop` | 중단 시퀀스 배열 | `["```\n\n"]` 등 |

`api_config.json` 의 모델 블록에 다음 필드를 **추가**하면 호출 시 기본값으로 적용되도록 후속 장에서 확장할 수 있다. (현재 코드는 `temperature` 를 라우터에서 동적으로 결정)

```json
"qwen3-coder-30b": {
  ...
  "defaults": { "temperature": 0.1, "top_p": 0.9 }
}
```

---

## 3.8 디버깅 — `curl` 한 줄 진단법

문제 발생 시 항상 **가장 작은 단위**로 끊어서 확인한다.

### ① 토큰 살아있나?

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  http://common.llm.skhynix.com/v1/models \
  -H "Authorization: Bearer $(cat token.txt)"
# 200 → OK
```

### ② 특정 모델이 메뉴에 있나?

```bash
curl -s http://common.llm.skhynix.com/v1/models \
  -H "Authorization: Bearer $(cat token.txt)" \
  | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(m['id'] for m in d.get('data',d)))"
```

### ③ 한 번 호출이 정말 되나?

```bash
curl -s http://common.llm.skhynix.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat token.txt)" \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen3-Coder-30B-A3B-Instruct",
       "messages":[{"role":"user","content":"1+1?"}],
       "max_tokens":32, "temperature":0}' | python -m json.tool
```

응답에 `choices[0].message.content` 가 보이면 끝.

### ④ 흔한 HTTP 코드

| 코드 | 의미 | 조치 |
|------|------|------|
| 401 | 토큰 무효/만료 | `token.txt` 갱신 |
| 403 | 권한 없음 | 사내 LLM 게이트웨이 권한 확인 |
| 404 | 모델명 오타 | `/v1/models` 로 정확한 ID 확인 |
| 408 | 타임아웃 | `max_tokens` 줄이거나 모델 변경 |
| 429 | 레이트리밋 | 잠시 대기 또는 다른 모델 |
| 500 | 게이트웨이 오류 | 다른 엔드포인트(dev.hcp ↔ common) 시도 |

---

## 3.9 동봉 예제 코드

`docs/examples/ch03/` 에 다음 3개 파일을 두었다.

| 파일 | 용도 |
|------|------|
| `multi_model_chat.py` | `api_config.json` 의 모델 목록을 읽어 **CLI에서 선택해 채팅** |
| `model_probe.py` | 등록된 **모든 모델을 ping** 해서 살아있는지 표로 출력 |
| `api_config.sample.json` | 새 모델 추가 예시가 포함된 **샘플 설정** |

### 3.9.1 `multi_model_chat.py` 사용

```bash
cd scientific-assistant/docs/examples/ch03
python multi_model_chat.py
# === 사용 가능 모델 ===
#   [0] glm-5             → GLM-5 (HCP)
#   [1] qwen3-coder-480b  → Coder-480B (HCP)
#   ...
#   [6] qwen3-coder-30b   → Coder-30B-A3B (Common)
# 모델 번호 선택: 6
#
# 질문 (quit 입력시 종료): 안녕?
# 답변: ...
```

### 3.9.2 `model_probe.py` — 전체 헬스체크

```bash
python model_probe.py
# [ok ]  glm-5             dev.hcp        0.7s
# [ok ]  qwen3-coder-480b  dev.hcp        2.1s
# [ok ]  qwen3-coder-next  dev.hcp        0.9s
# [fail] qwen3-vl-30b      dev.hcp        404 model not found
# [ok ]  gpt-oss-20b       common         0.5s
# [ok ]  qwen3-next-80b    common         1.4s
# [ok ]  qwen3-coder-30b   common         0.6s   ← 본 가이드 기본
#
# 요약: 6/7 정상
```

특정 모델만 호출:
```bash
python model_probe.py qwen3-coder-30b "파이썬 fizzbuzz 한 줄로"
```

### 3.9.3 `api_config.sample.json`

운영용 `api_config.json` 을 망가뜨리지 않도록 **별도 샘플**을 두었다. `Qwen3-Math-7B` 같은 가상의 추가 모델 예시 포함.

---

## 3.10 모범 사례 (Best Practices)

1. **`api_config.json` 은 git에 커밋해도 안전**하다 (토큰 없음).
2. 그러나 `_doc`/`_updated` 필드를 **수정 이력 기록** 용도로 적극 활용한다.
3. 새 모델 추가 시 반드시 `model_probe.py` 로 **한 번 호출 확인** 후 배포한다.
4. `priority` 는 **운영 정책의 표현**이다. 단순 선호도가 아니라 **폴백 순서**를 정의함을 잊지 말 것.
5. `capabilities` 태그는 **라우터의 자동 선택 근거**이므로 정확히 부여한다 (예: 비전 모델에 `vision` 누락 금지).

---

## 3.11 3장 체크리스트

- [ ] `api_config.json` 의 5개 블록(`token_settings`/`gguf`/`logpresso`/`models`) 의미를 안다
- [ ] 모델 1개의 9개 필드(`env_id`~`cost_tier`)를 설명할 수 있다
- [ ] 새 모델 한 개를 **JSON 편집만으로** 추가해 봤다
- [ ] `python model_probe.py` 실행 → 7개 중 몇 개가 살아있는지 확인했다
- [ ] `multi_model_chat.py` 로 모델을 바꿔가며 같은 질문을 던져 응답 차이를 비교했다
- [ ] `curl` 진단 4단계(토큰→모델→호출→에러코드)를 외웠다

---

## 3.12 다음 장 예고

**제4장 — 스킬 시스템: 355개 도메인 지식을 LLM에 주입하기**
- `scientific-skills/` 폴더 구조 해부
- 스킬 1개가 LLM 응답에 어떻게 끼어드는가
- 첫 커스텀 스킬 만들기 — `my-skill/SKILL.md`
- 스킬 키워드 매칭 알고리즘
- "내 분야"에 맞는 스킬 패키지 설계

---

*문서 버전: v1.0 (2026-04-29)*
*브랜치: `claude/create-llm-guide-chapter-one-RDZ12`*
