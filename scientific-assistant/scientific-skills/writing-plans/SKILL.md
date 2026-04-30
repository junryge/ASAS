---
name: writing-plans
description: Use after brainstorming produces an approved design document, before any implementation begins. Breaks the design into bite-sized tasks of 2-5 minutes each, with exact file paths, complete code blocks, and verification steps per task. Every task is concrete enough that an engineer with zero codebase context could execute it. Use when user says "계획 짜자", "구현 순서", "태스크로 쪼개줘", or after brainstorming completes.
---

# Writing Plans (구현 계획 작성)

## 핵심 원칙

**계획은 "새로 온 주니어 개발자가 우리 코드베이스 전혀 모르고, 센스 없고, 테스트 싫어함" 가정하고 써야 한다.** 구체적이지 않으면 실패한 계획.

## 전제

이 스킬은 `brainstorming`으로 승인된 설계 문서가 있는 상태에서 발동. 없으면 먼저 brainstorming.

## 아이언 룰

각 태스크는 다음을 모두 포함해야 한다. 하나라도 빠지면 태스크 실패:

1. **정확한 파일 경로** (기존 파일이면 라인 번호까지)
2. **완전한 코드 블록** (pseudo code 금지, TODO 금지)
3. **검증 방법** (어떤 커맨드로, 어떤 출력이 나와야)
4. **TDD 순서** (실패 테스트 먼저 → 구현)
5. **예상 소요 시간** 2-5분

## 계획 파일 위치

`docs/plans/YYYY-MM-DD-<feature>-plan.md`

## 계획 템플릿

```markdown
# [Feature] 구현 계획

> **필수 전제:** 이 계획은 태스크 단위로 순차 실행. 각 태스크 끝날 때마다 검증 → 커밋.

**목표:** (한 문장)
**아키텍처 요약:** (2-3 문장)
**기술 스택:** (언어/라이브러리)

---

## Task 1: [컴포넌트명]

**파일:**
- 생성: `exact/path/to/file.py`
- 수정: `exact/path/existing.py:123-145`
- 테스트: `tests/test_file.py`

**예상 시간:** 3분

- [ ] **Step 1: 실패 테스트 작성**
  ```python
  def test_cr_tm_filler_fills_missing_minutes():
      df = pd.DataFrame({
          "CRT_TM": ["2025-09-09 10:00", "2025-09-09 10:03"],
          "VAL": [1.0, 2.0]
      })
      result = fill_missing_minutes(df)
      assert len(result) == 4  # 10:00, 10:01, 10:02, 10:03
      assert result.loc[1, "VAL"] == 0  # 빠진 분은 0
  ```

- [ ] **Step 2: 테스트 실패 확인**
  실행: `pytest tests/test_file.py::test_cr_tm_filler_fills_missing_minutes -v`
  예상: FAIL with "fill_missing_minutes not defined"

- [ ] **Step 3: 최소 구현**
  ```python
  def fill_missing_minutes(df):
      df["CRT_TM"] = pd.to_datetime(df["CRT_TM"])
      full_range = pd.date_range(df["CRT_TM"].min(),
                                   df["CRT_TM"].max(),
                                   freq="1min")
      return df.set_index("CRT_TM").reindex(full_range, fill_value=0).reset_index()
  ```

- [ ] **Step 4: 테스트 통과 확인**
  실행: `pytest tests/test_file.py::test_cr_tm_filler_fills_missing_minutes -v`
  예상: PASS

- [ ] **Step 5: 커밋**
  `git commit -m "feat: add fill_missing_minutes for 1-min CRT_TM gaps"`

---

## Task 2: ...
```

## 절대 쓰면 안 되는 표현 (계획 실패)

| 금지 표현 | 왜 금지 | 대신 |
|----------|--------|------|
| "TBD", "추후 결정" | 결정 미룸 | 지금 결정하고 명시 |
| "적절한 에러 처리 추가" | 뭐가 적절한지 불명 | 구체 except 블록 코드 |
| "관련 테스트 작성" | 테스트 코드 없음 | 실제 테스트 코드 블록 |
| "Task N과 비슷하게" | 순서 뒤죽박죽 읽을 수 있음 | 코드 반복해서 적어라 |
| "에지 케이스 처리" | 어떤 엣지? | 케이스 나열 + 각각 처리 |
| "최적화" | 뭘? | 구체 지표 + 방법 |

## 계획 자체 검증 (완성 후)

자기 계획을 fresh eyes로 다시 본다:

1. **스펙 커버리지:** 설계 문서 요구사항 하나하나 → 어느 태스크가 구현하나? 빈 항목 있나?
2. **플레이스홀더 스캔:** "TBD", "TODO", "etc.", "적절히" 단어 검색. 하나라도 있으면 실패.
3. **태스크 독립성:** 각 태스크가 앞 태스크 맥락 없이 읽힐 수 있나? (주니어 가정)
4. **검증 단계 있나:** 각 태스크에 "어떻게 확인하나" 블록 있나?
5. **시간:** 각 태스크가 정말 2-5분 범위인가? 10분 넘으면 쪼개라.

## 존님 환경 체크리스트 추가

AMHS/ASAS 맥락이면:
- [ ] 폐쇄망 제약 반영? (외부 pip install 불가능한 거 가정)
- [ ] Qwen3-235B 엔드포인트 하드코딩? 환경변수?
- [ ] 인코딩 auto-detect (utf-8 → cp949 → euc-kr) 적용?
- [ ] Logpresso 쿼리 규칙 (fulltext + ts_data_view_*) 지켰나?
- [ ] CRT_TM/CHG_TM 같은 컬럼명 일관성?

ML 관련이면:
- [ ] GPU/CPU fallback (gpu_hist → hist) 있나?
- [ ] 데이터 로딩 인코딩 체인 있나?
- [ ] seed 고정?
- [ ] 모델 파일 네이밍 규칙 (xgboost_30min_10min_D3.pkl 같은)

## Common Mistakes

**A. 덩어리 계획**
- 증상: "1. 모델 학습 2. 배포" 같은 고수준 태스크
- 고침: 각 단계를 10-20개 2-5분 태스크로 쪼갬

**B. 코드 생략**
- 증상: "여기서 함수 구현" 이라고만 씀
- 고침: 실제 코드 블록 전체 복붙 가능하게

**C. TDD 역순**
- 증상: 구현 먼저 → 나중에 테스트
- 고침: 항상 실패 테스트 → 실행 → 구현 → 통과 → 커밋 순서

**D. 검증 생략**
- 증상: "커밋"만 쓰고 "어떻게 확인" 없음
- 고침: 각 태스크에 예상 출력까지 명시
