# 메인 채팅 SSE 스트리밍 — 작업 계획서

작성일: **2026-04-30**
대상 파일: `demos_v1/routes_chat.py`, `demos_v1/routes_chat_stream.py`, `demos_v1/frontend.py`
현재 상태: **Code Assistant 만 SSE, 메인 채팅 비-스트리밍**
백업: `20260430_수정원본.zip`

---

## 1. 왜 이 작업이 필요한가

### 사용자 체감 문제
- 대형 모델 + 긴 응답 시 **30초 ~ 5분 동안 화면 빈 상태**
- 응답 도착하면 통째로 8KB+ 텍스트 폭탄
- 사용자: "멈췄나?", "느려", "다른 거 함" → 만족도 ↓

### 같은 모델인데 체감 차이
| 지표 | 비-스트리밍 (현재) | 스트리밍 (목표) |
|---|---|---|
| **첫 글자 (TTFT)** | 30~180초 | **2~5초** (30~60배 빠른 체감) |
| **읽기 시작** | 응답 끝난 후 | **즉시** (모델이 생성하는 동안 읽음) |
| **잘못된 답 발견** | 끝까지 기다려야 | 5~10초 만에 가능 → 토큰 절약 |
| **사용자 불안감** | 높음 | 낮음 |

→ 실제 응답 시간은 같지만 **체감 만족도 2~3배**.

---

## 2. 메인 채팅이 어려운 이유

`routes_chat.py` 의 `/api/chat` 핸들러는 1900+ 줄 단일 함수. 안에 들어있는 기능들:

### A. 모델 선택 분기
- **단일 API 모델 직접 선택** (예: `kimi-k25`) — 가장 단순
- **자동 모드** (`env: ['auto']`) — 서버가 쿼리 분석 후 모델 결정
- **GGUF 모델** (`gguf-0` 등) — llama.cpp 경유, 다른 호출 방식
- **다중 모델 병렬** (`env: ['kimi', '480b']`) — 동시 호출 후 합성

### B. 폴백 체인
- 첫 모델 HTTP 400/429/500 → 다음 모델로 자동 재시도
- `FALLBACK_CHAINS` dict 에 정의 (예: `qwen3-coder-480b → glm-5 → ...`)

### C. 컨텍스트 주입
- **knowledge-search 스킬** → BM25 검색 결과 12KB 까지 system 메시지로 주입
- **CSV 데이터** → 업로드된 표 데이터 system 에 포함
- **첨부 파일** → 텍스트 추출 후 user 메시지에 병합
- **이미지** → Vision 모델 사용 시 base64 inline

### D. 자동 형식·스타일 감지
- `format=auto` → 쿼리 분석으로 code/analysis/report 등 분류
- `writing_style=auto` → "전문가 분석" / "단계별" / "간결" 등 자동
- → system prompt 마지막에 형식 지시 자동 추가

### E. 특수 라우팅
- **drawio/PPT 키워드** 감지 → max_tokens 16K~32K 강제
- **think_mode** → `<think>` 토큰 영역 별도 처리
- **weekly-report** 스킬 → BM25 검색 + 특수 system prompt

### F. 응답 후처리
- `<think>` 태그 잘라내기
- truncated 감지 (`finish_reason=length`)
- think 만 있고 본문 비어있으면 `max_tokens` 2배로 재시도
- 마크다운/Mermaid 보강
- 에이전트 자동 저장 (피드백 루프)

→ 이 모든 걸 SSE 화 = 큰 작업.

---

## 3. 단계별 접근 (3 Phase)

### 🥇 Phase 2-A — 단일 API 모델 직접 선택만 (반일)
**대상**: 사용자가 모델 드롭다운에서 "✨ 자동" 끄고 명시적으로 1개 모델 고른 케이스.

**제외**: auto / 병렬 / GGUF / 파일 첨부 / 형식 자동 / drawio·PPT.

**구현**:
- 프론트 `send()` 함수: 진입 직후 `_isStreamable` 판별 후 분기
- 분기 조건:
  ```javascript
  selEnvs.length === 1
  && selEnvs[0] !== 'auto'
  && !selEnvs[0].startsWith('gguf-')
  && attachedNames.length === 0
  ```
- 백엔드: 기존 `/api/chat/stream` 그대로 사용 (Code Assistant 와 공유)
- 메타에 `[⚡ 스트리밍]` 라벨로 구분

**효과**: 사용자가 모델 직접 선택하는 경우만 (~20% 케이스) 즉시 스트리밍.

**리스크**:
- knowledge-search 스킬 사용 시 BM25 결과 미반영 → 보완: 백엔드에 추가 ✅ (이미 구현됨)
- 자동 형식/스타일 미반영 → 사용자가 의식하면 포맷 직접 지정 가능

**상태**: 한 번 시도했으나 사용자 요청으로 원복. **재진입 가능**.

---

### 🥈 Phase 2-B — 자동 모드 + 폴백 (1일)
**대상**: `env: ['auto']` 케이스. 서버가 모델 결정 후 SSE 시작.

**구현**:
1. 새 엔드포인트: `/api/chat/stream-auto` 또는 기존 `/api/chat/stream` 확장
2. 백엔드 흐름:
   ```
   요청 받음 → classify_and_route() 로 모델 결정 → SSE 헤더 응답 시작
   → 첫 이벤트: {"router": "kimi-k25", "reason": "..."}
   → 모델 stream=True 호출 → 토큰별 yield
   → HTTP 400 받으면 다음 모델로 → {"fallback": "kimi-k25 → glm-5"} 이벤트
   → 새 모델 stream 다시 시작
   ```
3. 프론트:
   - 첫 이벤트 받으면 라우팅 정보 표시 ("🤖 자동 선택: Kimi-K2.5")
   - 폴백 이벤트 받으면 스트리밍 박스 텍스트 비우고 다시 시작 (또는 이어서 — UX 결정 필요)

**리스크**:
- 폴백 발생 시 부분 텍스트 처리 — 버릴지 이어붙일지 결정
- `classify_and_route()` 비용 — 30초 텍스트 분석 후 SSE 시작이면 의미 없음 (다행히 빠름)

**효과**: 사용자 60~70% 케이스 (자동 모드) 도 스트리밍.

---

### 🥉 Phase 2-C — 병렬 + 합성 (1일)
**대상**: `env: ['kimi', '480b']` 같이 모델 2개 이상 동시 호출.

**구현**:
1. 백엔드:
   - 각 모델 동시 stream=True 호출 (ThreadPoolExecutor 안에서 비동기 처리)
   - 각자 끝까지 받기 (스트리밍 X)
   - 합성 모델 (예: GLM-5) 에 결과 던져서 합성 → **합성 단계만 SSE**
2. 프론트:
   - "🔀 병렬 분석 중... (Kimi + Coder-480B)" 표시
   - 각 모델 완료 시 카운터 증가
   - 합성 시작하면 SSE 박스 등장

**리스크**:
- 병렬 호출 자체는 시간 소요 → 사용자 입장에선 1단계 대기는 동일
- 합성 단계만 SSE → 부분 효과

**효과**: 병렬 모드 사용자 (~5%) 도 부분 스트리밍.

---

### 🏆 Phase 2-D — 파일 첨부 + 자동 형식 + drawio/PPT 등 (1일)
**대상**: 나머지 모든 케이스.

**구현**:
- `/api/chat/stream` 에 csv_data, uploaded_files_data 매개변수 전달
- 자동 형식/스타일 감지 결과를 SSE 첫 이벤트로 전송
- drawio/PPT 키워드 감지 시 max_tokens 부스트 그대로 적용

**리스크**:
- routes_chat.py 의 1900줄 거의 다 stream 버전으로 옮겨야 함
- 회귀 위험 ↑

**효과**: 100% 스트리밍.

---

## 4. 권장 진행 순서

```
Phase 2-A (반일) ──┐
                   │ 검증 후 진행
Phase 2-B (1일) ───┤
                   │
Phase 2-C (1일) ───┤
                   │
Phase 2-D (1일) ───┘
```

**총 공수**: 3.5일 ~ 1주 (디버깅·테스트 포함).

---

## 5. 각 Phase 의 구체적 작업

### Phase 2-A 구체 단계 (재진입 시)

#### Step 1: 프론트 `send()` 분기 추가 (`frontend.py`)
**위치**: line 2132 `chatAbort = new AbortController();` 직후

```javascript
const _isStreamable = selEnvs.length === 1
                   && selEnvs[0] !== 'auto'
                   && !selEnvs[0].startsWith('gguf-')
                   && attachedNames.length === 0;

if(_isStreamable){
  // SSE 경로 (Code Assistant 와 동일 패턴)
  typing.remove();
  const _ssBox = document.createElement('div');
  _ssBox.className = 'msg assistant streaming';
  _ssBox.innerHTML = '<div class="msg-label">Demos <span style="font-size:10px;color:#6366f1;">⏵ 스트리밍</span></div><div class="streaming-content" style="white-space:pre-wrap;"></div>';
  document.getElementById('msgs').appendChild(_ssBox);
  const _ssContent = _ssBox.querySelector('.streaming-content');
  const _ssTextNode = document.createTextNode('');
  _ssContent.appendChild(_ssTextNode);
  // ... fetch /api/chat/stream + getReader + parse SSE
  return;
}

// 아니면 기존 try { fetch('/api/chat', ...) } 그대로
```

#### Step 2: 백엔드 엔드포인트 (`routes_chat_stream.py`)
**이미 존재** — Code Assistant 가 사용 중.
변경 없음 (이미 knowledge-search 처리도 됨).

#### Step 3: 정상 동작 확인
1. 메인 채팅 모델 드롭다운에서 "✨ 자동" 해제
2. 단일 모델 선택 (예: 🔥 Kimi-K2.5)
3. 텍스트만 질문 ("V10_4 모델 설명해줘")
4. ▶ 클릭 → 2~5초 안에 첫 글자
5. 응답 끝에 `[⚡ 스트리밍]` 라벨 확인

#### Step 4: 회귀 테스트
- 자동 모드로 질문 → `/api/chat` 사용 (기존)
- 병렬 모델 선택 → `/api/chat` 사용 (기존)
- GGUF 선택 → `/api/chat` 사용 (기존)
- CSV 첨부 후 질문 → `/api/chat` 사용 (기존)

### Phase 2-A 의 제거된 코드 (참조)
이전 시도 (커밋 `2f2786b`) 에서 130줄 제거됨. git 에서 복원 가능:
```bash
git show 2f2786b -- scientific-assistant/demos_v1/frontend.py
```

---

## 6. 알려진 함정

### A. SSE 토큰별 textContent 재할당 → O(n²) 느려짐
- **이미 해결**: `_ssTextNode.appendData(ev.delta)` 사용
- 새 코드 작성 시 절대 `textContent = fullText` 패턴 쓰지 말 것

### B. nginx 버퍼링
- nginx 가 SSE 를 버퍼링하면 한 번에 떨어짐
- 백엔드 응답 헤더에 `X-Accel-Buffering: no` 이미 포함됨
- nginx conf 추가 권장:
  ```nginx
  proxy_buffering off;
  proxy_cache off;
  ```

### C. 마크다운 렌더링 시점
- 스트리밍 중엔 **plain text** (textContent), 완료 후 마크다운
- 토큰별 마크다운은 코드블록·표 깨짐 발생
- ChatGPT 도 같은 패턴

### D. Abort 시 부분 텍스트
- ESC / ⏹ 누르면 `chatAbort.abort()` → fetch reader 자동 cancel
- 백엔드는 connection close 감지 → 종료
- 프론트 catch 에서 `_ssFullText` 가 비어있지 않으면 메시지로 살림

### E. knowledge-search 비용
- BM25 자체는 빠름 (수백 ms)
- 12KB system prompt 주입 → 모델 첫 토큰 느려짐 (1~3초)
- inherent → 어쩔 수 없음

### F. SSE 응답 안 끝남 (좀비 연결)
- 백엔드 try/except 에서 `[DONE]` 못 받으면 영원히 대기 위험
- 현재 구현: timeout=600s 로 강제 끊김
- 추가 안전장치: heartbeat 이벤트 (선택)

---

## 7. 공수 + 일정 추정

| Phase | 공수 | 누적 효과 |
|---|---|---|
| **2-A** (단일 모델) | 반일 | 사용자 20% 케이스 SSE |
| **2-B** (자동 모드) | 1일 | 80% (자동+단일) |
| **2-C** (병렬 합성) | 1일 | 85% |
| **2-D** (파일+형식+drawio) | 1일 | **100%** |
| **합계** | **3.5일** | 전부 |

---

## 8. 의사결정 포인트

### Q1. Phase 2-A 만 할 것인가, 끝까지 갈 것인가?
- **2-A 만**: 빠른 효과, 안전. 사용자 "✨ 자동" 끄고 모델 직접 선택해야 함 (학습 비용)
- **끝까지**: 완전. 시간 ↑.

### Q2. 폴백 시 부분 텍스트 처리?
- 옵션 A: 첫 모델 응답 버리고 두 번째 모델 처음부터 다시 시작
- 옵션 B: 첫 모델 부분 응답 살린 채로 두 번째 모델 시작 (이어쓰기)
- **추천**: 옵션 A — 일관성. UI 에 "Kimi 실패, GLM-5 로 재시작" 알림.

### Q3. 자동 형식·스타일 감지 결과를 SSE 로 어떻게 알리나?
- 옵션 A: 첫 이벤트로 `{"meta": {format, style}}` 전송 후 텍스트 stream
- 옵션 B: done 이벤트에 포함만
- **추천**: 옵션 A — 라벨 즉시 표시 가능

### Q4. 마크다운 렌더링은 언제?
- 옵션 A: 완료 후 한 번 (현재)
- 옵션 B: 단락 단위 (`\n\n` 도착 시) 점진 렌더
- **추천**: 옵션 A — 안전. 옵션 B 는 코드블록 깨질 위험.

---

## 9. 진행 시 명령어 모음

### 작업 시작 (Phase 2-A 재진입)
```bash
cd /home/user/ASAS/scientific-assistant
# 백업
cp demos_v1/frontend.py 20260417_SKILL/backup/frontend_BEFORE_phase2a_retry.py
# 이전 시도 참조
git show 2f2786b -- demos_v1/frontend.py | less
# 수정 후 검증
python -c "import ast; ast.parse(open('demos_v1/frontend.py').read())"
```

### 빠른 원복 (문제 시)
```bash
unzip -o 20260417_SKILL/20260430_수정원본.zip
```

### Push
```bash
git add demos_v1/frontend.py
git commit -m "feat(streaming): Phase 2-A 재진입 — 단일 API 모델 메인 채팅 SSE"
git push origin claude/plan-skill-system-8c3Vx
```

---

## 10. 결론

메인 채팅 SSE 는 **단계적**으로 가는 게 맞음.

**가장 가성비**: Phase 2-A (반일) — 사용자가 "✨ 자동" 끄고 모델 직접 선택 시만 SSE.
**완전 효과**: Phase 2-A → 2-B → 2-C → 2-D (3.5일).

당장 시작할지, 기존 안정 상태 유지하면서 다른 작업 먼저 할지는 **운영 우선순위 판단**.

---

## 부록: 현재 SSE 인프라 (이미 동작 중)

### 백엔드: `demos_v1/routes_chat_stream.py`
- POST `/api/chat/stream` — Code Assistant 사용 중
- 단일 API 모델 + 폴백 비활성 + knowledge-search 지원
- timeout 600s
- SSE 형식: `data: {"delta": "..."}\n\n` / `data: {"done": true, ...}\n\n`

### 프론트: `demos_v1/frontend.py` `runCodeAssistant()`
- `getReader()` + `TextDecoder` + SSE 라인 파싱
- `_ssTextNode.appendData()` (O(n) 효율)
- scroll 100ms 쓰로틀
- abort 시 부분 텍스트 보존

→ Phase 2-A 는 이 패턴을 `send()` 에 복붙만 하면 됨.
