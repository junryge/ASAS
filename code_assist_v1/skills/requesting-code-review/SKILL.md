---
name: requesting-code-review
description: Use before creating a PR, before requesting human review, or when user says "리뷰해줘", "코드 검토", "PR 올리기 전에", "체크 좀". Covers pre-review self-checklist (correctness, security, performance, readability), how to structure review request (scope, context, specific questions), and how to receive/respond to feedback constructively. Use whenever code is about to be reviewed by another person or by Claude acting as reviewer.
---

# Requesting Code Review (코드 리뷰 요청 및 수용)

## 핵심 원칙

**리뷰어가 짐작하게 만들지 마라.** 뭘 리뷰해달라는지, 왜 그렇게 짰는지, 뭐가 걱정인지 명시. 리뷰어가 코드 읽느라 10분 쓰는 거랑 존님이 5분 써서 맥락 주는 거랑 비교하면 후자가 훨씬 이득.

## 두 가지 모드

### 모드 A: 리뷰 요청 (존님이 리뷰 받을 때)
### 모드 B: 리뷰 수용 (피드백 받고 반영할 때)

---

## 모드 A: 리뷰 요청

### Pre-Review Self-Checklist

리뷰 요청 전에 **혼자** 다음 통과. 여기서 잡히는 거 리뷰어한테 가져가면 시간 낭비.

#### 1. 정확성 (Correctness)
- [ ] 유닛 테스트 모두 통과?
- [ ] 통합 테스트 또는 실제 실행해봤나?
- [ ] 에지 케이스 3개 이상 검증? (빈 입력, null, 큰 데이터, 잘못된 타입)
- [ ] 기존 테스트 회귀 없음?

#### 2. 보안 (Security)
- [ ] 하드코딩된 비밀 없음? (API key, 패스워드, 엔드포인트)
- [ ] SQL 인젝션 (f-string으로 쿼리 조립 X, parameter binding)
- [ ] 사용자 입력 검증?
- [ ] 로그에 민감 데이터 안 찍나? (CARRIER ID 같은 건 OK지만 개인정보 X)

#### 3. 비즈니스 룰 (AMHS 특화)
- [ ] OHT 경로 계산 로직 변경했다면 → 회전 비용, 엣지 가중치 일관성?
- [ ] HID 존 구분 변경했다면 → 기존 할당 규칙과 충돌 없나?
- [ ] V7 threshold 변경했다면 → 실제 false positive/negative 영향?

#### 4. 입력 검증 (Input Validation)
- [ ] CSV 로딩: 인코딩 auto (utf-8 → cp949 → euc-kr)?
- [ ] 시간 포맷: CRT_TM 파싱 실패 처리?
- [ ] 빈 DataFrame 처리?

#### 5. 성능 (Performance)
- [ ] N+1 쿼리 없음?
- [ ] 큰 loop 안에서 DB/네트워크 콜 없음?
- [ ] 메모리 copy 과도한 데가 없나? (큰 DataFrame)
- [ ] Logpresso 쿼리 시간 범위 적절한가?

### 리뷰 요청 포맷

리뷰 요청할 때 다음 구조로 메시지 작성:

```markdown
## 리뷰 요청: [제목]

### 배경
- 해결하려는 문제: ...
- 관련 이슈/티켓: #123

### 변경 범위
- 파일: 5개
- LOC: +230 -45
- 핵심 파일:
  - `train.py` (모델 학습 로직)
  - `features.py` (V7 feature 1개 추가)
  - `tests/test_features.py` (신규)

### 핵심 결정 (리뷰어가 확인해 주면 좋을 것)
1. **momentum feature 4번째 추가 결정**
   - 왜: 기존 3개로 기울기 약한 상승 놓쳤음
   - 대안 검토: 윈도우 사이즈 20 → 버려짐 (reason)

2. **GPU fallback 로직 위치**
   - train 함수 내부 vs 별도 util
   - 선택: 내부 (호출하는 곳 1군데라서)

### 걱정되는 부분
- [ ] feature 추가로 학습 시간 15% 증가 — 허용 범위인지?
- [ ] CSV 인코딩 fallback 순서 변경 이력 있나?

### 검증
- [x] pytest 47/47 통과
- [x] 샘플 데이터 학습 완주
- [ ] 실제 FAB 데이터 평가 (리뷰 후 진행 예정)

### Self-Review 결과
위 체크리스트 모두 통과.
```

## 모드 B: 리뷰 수용

### 피드백 받을 때 반응

#### 방어적 반응 금지
```
❌ "그건 의도한 겁니다"
❌ "이미 그렇게 하고 있어요"
❌ "다른 곳도 그래요"
```

#### 건설적 반응
```
✅ "그 부분 놓쳤네요. 고칠게요."
✅ "의도는 X였는데 혹시 그게 의도대로 읽히지 않으면 이렇게 바꿀까요?"
✅ "이 부분 저도 애매했어요. 대안 A/B 중 어느 게 좋을지 같이 봐주세요."
```

### 피드백 분류

받은 코멘트를 3개 버킷으로:

| 버킷 | 정의 | 대응 |
|------|------|------|
| **Must Fix** | 버그, 보안, 회귀 | 즉시 수정 후 재요청 |
| **Should Fix** | 가독성, 네이밍, 구조 | 수정. 시간 없으면 이슈로 기록 |
| **Discussion** | 디자인 의견 차이 | 리뷰어와 대화 후 결정 |

각 코멘트에 어느 버킷인지 명시:

```markdown
> 리뷰어: 이 함수 이름이 목적을 잘 표현 못 하는 것 같아요.

[Should Fix] 동의합니다. `compute_target_acceleration_last_10` 으로 변경.

> 리뷰어: 여기 try-except 너무 광범위한 것 같은데.

[Discussion] 의도는 외부 콜 어떤 에러든 잡아서 fallback 데이터로 가는 건데요, 혹시 specific exception들로 나눠 받는 게 나을까요?
```

### 반영 후 커뮤니케이션

모든 피드백에 **명시적으로** 답:

```markdown
## 리뷰 반영 결과

- [x] 함수명 변경 (compute_target_acceleration → compute_target_acceleration_last_10_mean) — commit abc123
- [x] except 세분화 (UnicodeDecodeError, FileNotFoundError 분리) — commit def456
- [x] 테스트 추가 (빈 DataFrame 케이스) — commit ghi789
- [ ] [Discussion 계속] momentum feature 4번째의 윈도우 크기 → 다음 미팅에서

재리뷰 부탁드립니다.
```

## 존님 환경 특화 리뷰 항목

### AMHS Java (ATLAS)
- [ ] TibRV subject 이름 규칙 지켰나?
- [ ] RailEdge/BranchJoinEdge 수정 시 `DijkstraVhlRouteFind` 영향?
- [ ] UDP 패킷 파싱 offset 정확?
- [ ] 1분 버퍼 flush timing 레이스 없나?

### Logpresso 쿼리
- [ ] `fulltext` 사용?
- [ ] `ts_data_view_*` 테이블?
- [ ] 시간 범위 14자리 포맷?
- [ ] `stats` vs `timechart` 선택 이유?
- [ ] `eval No = seq() + 0` 있나?

### V7 모델 코드
- [ ] Feature 개수 정확 (11)?
- [ ] Surge 정의 (seq_max<300 & future≥300) 지켰나?
- [ ] GPU/CPU fallback 로깅?
- [ ] seed 고정?

### React/JSX (OHT simulator)
- [ ] STK 모드 케이스 분기 빠짐 없음?
- [ ] Zone heatmap 색 변환 정확?
- [ ] useEffect cleanup 있나?
- [ ] WebSocket 재연결 로직?

### Qwen3 연동
- [ ] `http.client` 사용?
- [ ] 한국어 시스템 프롬프트?
- [ ] Timeout 설정?
- [ ] 에러 시 fallback?

## Rationalization Table

존님이 리뷰 요청 skip 하려고 할 때:

| 유혹 | 반박 |
|------|------|
| "작은 변경이라 괜찮아" | 작은 변경이 프로덕션 터뜨리는 역사 많음 |
| "시간 없어 그냥 머지" | 사후 핫픽스가 시간 더 걸림 |
| "나밖에 아는 사람 없어" | 그게 리뷰가 더 필요한 이유 (지식 전파) |
| "내가 전문가야" | 전문가도 실수함. 리뷰는 실력 문제 아님 |

## Quick Reference

Self-review 5분:
```
□ 테스트 통과
□ 하드코딩 비밀 없음
□ 인코딩 fallback (해당 시)
□ 에지 케이스 3개
□ 기존 테스트 회귀 없음
```

리뷰 요청 메시지 필수 4가지:
1. 배경 (왜)
2. 변경 범위 (뭘)
3. 핵심 결정 (어떻게)
4. 걱정되는 부분 (뭐가 불안)
