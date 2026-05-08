---
name: systematic-debugging
description: Use when any bug, test failure, error, or unexpected behavior appears. Enforces 4-phase root cause investigation BEFORE any fix is attempted. Symptom patches are forbidden. Covers evidence gathering, data flow tracing, hypothesis testing, and architecture review after 3 failed fixes. Use when user says "왜 안 되지", "에러 나", "디버깅", "이상해", "테스트 실패", or when code misbehaves in any way.
---

# Systematic Debugging (4단계 루트코즈)

## 핵심 원칙

**루트코즈 조사 전에는 그 어떤 수정도 시도하지 않는다. 증상만 고치는 패치는 실패다.**

무작위 수정은 시간 낭비 + 새 버그 양산. 95%의 "루트코즈를 못 찾겠다"는 케이스는 조사 부족.

## 4단계 (순서대로, 건너뛰기 금지)

### Phase 1: Root Cause Investigation (루트코즈 조사)

이 단계 끝나기 전엔 **수정 제안 금지**.

1. **에러 메시지 완독**
   - 스택 트레이스 맨 위 뿐만 아니라 **맨 아래 "Caused by"**까지
   - 에러 코드/메시지 그대로 복사

2. **재현**
   - 같은 조건에서 100% 재현되나?
   - 재현 안 되면 조건 좁히기 전 수정 절대 금지
   - Logpresso 쿼리면 동일 시간 범위로 재실행

3. **최근 변경 확인**
   ```bash
   git log --oneline -20
   git diff HEAD~5 -- <suspect_file>
   ```

4. **데이터 흐름 추적 (multi-component system)**
   각 컴포넌트 경계마다 로그 삽입:
   ```python
   # Layer 1: 입력
   logger.info(f"[L1] input={input[:100]}")
   # Layer 2: 처리 전
   logger.info(f"[L2] after_parse={parsed}")
   # Layer 3: DB 콜 전후
   logger.info(f"[L3] query={query}, result_len={len(rows)}")
   # Layer 4: 출력
   logger.info(f"[L4] output={output}")
   ```
   한 번 실행 → 어느 레이어에서 깨지는지 증거 확보.

### Phase 2: Pattern Analysis (패턴 분석)

1. **같은 버그 다른 데서도 나나?**
   ```bash
   grep -r "similar_pattern" src/
   ```
2. **비슷한 버그 히스토리 있나?** (커밋 로그, 이슈 트래커)
3. **리그레션인가, 처음부터 버그였나?**

이 단계에서 "이 클래스의 구조적 문제"인지, "한 줄짜리 실수"인지 판정.

### Phase 3: Hypothesis Testing (가설 검증)

1. **가설 1개 세움:** "X가 null이어서 Y에서 NPE 발생"
2. **검증 방법 설계:** "X 로그 찍어서 null 확인"
3. **증거 수집**
4. **가설 맞으면 → Phase 4**
5. **가설 틀리면 → Phase 1로 복귀** (다른 데이터 더 확보)

금지: "이거겠지" 추측으로 바로 수정.

### Phase 4: Implementation (수정)

1. **실패 테스트 먼저 작성** (TDD)
   - 버그 재현 테스트 → FAIL 확인
2. **최소 수정**
3. **테스트 통과 확인**
4. **Defense-in-depth 고려** (다른 레이어에도 validation 추가할 만한가)
5. **커밋**

### Phase 4.5: Architecture Review (3번 실패 시)

같은 버그를 수정 시도 **3번** 실패하면:

**STOP.** 더 이상 수정하지 말고 사람과 대화:

> "이거 3번 고쳐봤는데 다 실패. 가설이 잘못된 게 아니라 아키텍처가 잘못된 걸 수도 있어요. 이 부분 구조를 다시 봐야 할 것 같은데 어떻게 생각하세요?"

이건 가설 실패가 아니다. **잘못된 설계의 신호**.

## 금지 패턴 (보이는 즉시 Phase 1로 복귀)

| 패턴 | 왜 나쁜가 |
|------|----------|
| "일단 try/except로 감싸자" | 증상만 숨김 |
| "재시도 로직 추가" | 근본 원인 안 고침 |
| "일단 None 체크 추가" | 왜 None이 들어오는지 모름 |
| "타임아웃 늘리자" | 왜 느린지 모름 |
| "restart하면 되던데" | 재현 안 된 게 아니라 못 한 것 |
| "캐시 지우면 됨" | 캐시 왜 꼬였는지 모름 |

## 존님 환경 특화 체크포인트

### Logpresso 쿼리 실패

1. **문법 에러 먼저 확인**
   - `datestr()`, `dateformat()`, `dateparse()` 썼나? → 지원 안 됨. `from=/to=` 사용
   - `join` 키를 command 뒤에 바로 썼나?
   - `timechart`로 non-aggregated field 유지하려고 했나? → `stats` 사용

2. **테이블 선택**
   - 인덱스 필드 (CARRIER 등) 필터링이면 `table`+`search` NO → `fulltext` + `ts_data_view_*` YES
   
3. **시간 범위**
   - from/to 포맷: `yyyyMMddHHmmss` 14자리

### Oracle IDC 데이터

1. CRT_TM vs CHG_TM 테이블 잘 선택했나? (HIS vs PDT_HIS)
2. 타임존 KST/UTC 혼재?
3. 인코딩: `utf-8` → `cp949` → `euc-kr` 순서 fallback 있나?

### V7 모델 예측 이상

1. GPU/CPU fallback 로그 확인 (`gpu_hist` 실패 후 `hist`로 갔나)
2. Feature 개수 11개 그대로? (7 base + 4 momentum)
3. `seq_data = df[i-30:i]` 인덱스 경계 확인
4. prediction threshold 280 변경된 적 있나?

### Qwen3-235B 연동 실패

1. `http.client` 사용 중인가? (`requests`는 한글 body 인코딩 이슈 있음)
2. Content-Type charset=utf-8 명시?
3. 시스템 프롬프트 한국어 맞나?

### OHT 시뮬레이터

1. UDP 패킷 형식 변경된 적 있나?
2. layout.xml 버전 일치?
3. HID 존 경계 좌표 최신인가?

## 디버깅 로그 템플릿

문제 해결 과정 기록 (`docs/debug/YYYY-MM-DD-<bug>.md`):

```markdown
# 버그: [한 줄 요약]

## 증상
- 에러 메시지: ...
- 재현 조건: ...
- 발생 시점: ...

## Phase 1: Investigation
- 에러 위치: file.py:123
- 데이터 흐름 로그:
  - L1 OK
  - L2 OK
  - L3 에서 빈 list 반환 ← 여기

## Phase 2: Pattern
- 같은 패턴: grep 결과 ...
- 최근 변경: commit abc123

## Phase 3: Hypothesis
- 가설: L3의 쿼리가 잘못된 테이블 참조
- 검증: 쿼리 로그 → 확인
- 결과: 맞음

## Phase 4: Fix
- 실패 테스트: test_query_uses_correct_table
- 수정: file.py:123 FROM wrong_table → ts_data_view_m14a
- 커밋: def456

## Defense-in-depth
- 추가: 테이블명 검증 assert 추가 (file.py:100)
```

## 체크리스트

- [ ] 증상이 아니라 원인을 찾았는가?
- [ ] 재현 100% 되는가?
- [ ] 증거(로그) 있는가, 추측인가?
- [ ] 수정 전 실패 테스트 있는가?
- [ ] 수정 후 다른 테스트도 여전히 통과하는가?
- [ ] 3번 실패했으면 아키텍처 대화 했는가?
