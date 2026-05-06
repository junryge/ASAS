---
name: test-driven-development
description: Use during any implementation work - writing new functions, classes, modules, or fixing bugs. Enforces strict RED-GREEN-REFACTOR cycle where failing test must exist and be verified failing BEFORE any production code is written. Code written before its test is deleted, not adapted. Use when user says "구현해줘", "함수 만들자", "기능 추가", "버그 수정", or whenever production code is about to be written.
---

# Test-Driven Development (RED-GREEN-REFACTOR)

## 아이언 룰

**테스트 없는 프로덕션 코드는 존재할 수 없다. 테스트 먼저 쓰기 전에 쓴 코드는 삭제하고 다시 시작한다. 적응시키지 않는다.**

이 룰 위반하면 TDD 하는 게 아니다. 그냥 "테스트도 같이 쓰는 사람"일 뿐.

## 사이클

```
┌────────────┐   실패 확인   ┌────────────┐   통과 확인   ┌──────────┐
│ RED (test) │ ─────────→   │ GREEN      │ ─────────→   │ REFACTOR │
│ 실패 테스트 │              │ 최소 구현   │              │ 정리     │
└────────────┘              └────────────┘              └──────────┘
     ↑                                                       │
     └───────────────────── 다음 케이스 ──────────────────────┘
```

### RED (빨강)
1. 구현할 동작을 **1개** 명확히 정함 (여러 개 X)
2. 그 동작을 검증하는 테스트 작성
3. **테스트 실행 → FAIL 확인** (이거 안 하면 TDD 아님)
4. FAIL 메시지가 "함수/클래스 없음" 같은 기본 에러면 OK

### GREEN (초록)
1. 테스트를 통과시키는 **최소한의 코드**만 작성
2. 하드코딩해도 OK (첫 케이스는 `return expected_value` 가능)
3. 실행 → PASS 확인
4. 다른 테스트들도 아직 통과하는지 전체 실행

### REFACTOR
1. 중복 제거, 이름 개선, 구조 정리
2. 각 변경 후 테스트 재실행 → 여전히 PASS 확인
3. 끝나면 커밋

## 절대 금지

**❌ "구현 먼저 하고 테스트 나중에"**
→ TDD가 아니다. 구현 지웠다가 다시 시작.

**❌ "이건 간단하니까 테스트 생략"**
→ 간단해도 규칙 동일. 간단한 테스트 5분이면 쓴다.

**❌ "테스트 실행 안 해보고 구현 작성"**
→ 테스트가 진짜 실패하는지 확인 안 하면, 이미 passing인 죽은 테스트일 수 있음.

**❌ "한 번에 테스트 5개 쓰고 구현"**
→ 1 test → 1 implementation → 확인. 배치 금지.

## 존님 환경 TDD 패턴

### Python (pytest)

```python
# tests/test_v7_feature.py
import pandas as pd
from features import compute_target_acceleration

def test_target_acceleration_last_10_mean_uses_exactly_10_rows():
    # Given 30 rows of data
    df = pd.DataFrame({"TARGET": list(range(30))})
    # When computing acceleration
    acc = compute_target_acceleration(df)
    # Then it uses last 10 rows mean
    expected = (sum(range(20, 30)) / 10) - (sum(range(10, 20)) / 10)
    assert abs(acc - expected) < 1e-6
```

실행: `pytest tests/test_v7_feature.py -v`

### Java (AMHS - JUnit)

OhtMsgWorkerRunnable 같은 클래스:

```java
@Test
void hidInOutAggregator_flushesEvery1MinuteBuffer() {
    HidAggregator agg = new HidAggregator();
    agg.record("HID001", "IN", ts("10:00:15"));
    agg.record("HID001", "IN", ts("10:00:45"));
    agg.record("HID001", "IN", ts("10:01:05"));

    List<BufferFlush> flushed = agg.flushIfDue(ts("10:01:10"));

    assertEquals(1, flushed.size());
    assertEquals(2, flushed.get(0).count);  // 10:00 버킷의 IN 2건만
}
```

### Logpresso 쿼리 (스냅샷 테스트)

쿼리 결과를 test fixture로 고정:

```python
def test_sorter_abn_query_returns_180_columns():
    result = run_logpresso(QUERY_SORTER_ABN)
    assert len(result.columns) == 180
    assert "CRT_TM" in result.columns
    assert result["CRT_TM"].is_monotonic_increasing
```

## Test Anti-patterns (존님 업무 특화)

### ❌ sleep 기반 비동기 테스트
```python
# BAD
task.start()
time.sleep(2)
assert task.done()
```
고침: **condition-based waiting**
```python
# GOOD
task.start()
wait_until(lambda: task.done(), timeout=5)
```

### ❌ 하드 경로 (폐쇄망 환경에서 안 돌아감)
```python
# BAD
df = pd.read_csv("C:/Users/Jon/Desktop/data.csv")
```
고침: fixture에 소량 넣거나 환경변수.

### ❌ LLM 응답을 정확 매칭
```python
# BAD
assert response == "정확히 이 문장"
```
고침: 구조 검증.
```python
# GOOD
assert "요약" in response or "summary" in response.lower()
assert len(response) > 50
```

### ❌ 실시간 타임스탬프로 검증
```python
# BAD
assert row["CRT_TM"] == datetime.now()
```
고침: 고정 시간 주입.

## 체크리스트 (매 사이클)

- [ ] 테스트 하나만 쓰고 있나? (여러 개 배치 X)
- [ ] 테스트 실행해서 FAIL 확인했나?
- [ ] 구현이 테스트 통과시키는 **최소한**인가?
- [ ] 전체 테스트 스위트 여전히 통과하나?
- [ ] 리팩터 후에도 테스트 통과하나?
- [ ] 커밋 메시지에 "feat", "fix", "test", "refactor" 구분 명시?

## 존님 환경 TDD 예외 허용

다음은 TDD strict 적용 어려움 - judgment call:

1. **EDA(탐색적 분석)** - 데이터 처음 보는 단계는 notebook에서 자유롭게, 패턴 확정되면 그때부터 TDD
2. **3D 시각화 UI** - 시각적 결과는 visual regression test 아니면 manual QA
3. **Blender addon 같은 플러그인** - 테스트 환경 구축 비용 큼. Integration test 1-2개만
4. **Logpresso 쿼리 실시간 데이터 의존** - Fixture 만들기 어려우면 smoke test만

이런 경우도 "테스트 없어도 됨"이 아니라 "다른 형태 검증(manual QA, fixture snapshot 등)"으로 대체. `verification-before-completion` 스킬이 책임진다.
