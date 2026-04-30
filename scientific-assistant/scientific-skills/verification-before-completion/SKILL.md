---
name: verification-before-completion
description: Use BEFORE declaring any task complete, before saying "done", "finished", "완료", "끝", before creating a PR, before merging. Forces concrete evidence of success by running actual verification commands and capturing output. Blocks false completion claims. Use when user says "끝났어?", "배포해도 돼?", "완료", or when Claude is about to declare work finished.
---

# Verification Before Completion (완료 전 검증)

## 핵심 원칙

**"완료"를 선언하기 전에 그게 정말 작동하는지 증거로 입증해야 한다. "코드 썼으니 됐겠지"는 증거가 아니다.**

테스트가 통과했다 ≠ 기능이 동작한다. 빌드가 됐다 ≠ 배포하면 돌아간다.

## 언제 발동

- 사용자가 "완료", "끝", "done" 같은 말 하기 전 Claude 자신
- PR 만들기 전
- 병합하기 전
- 배포 승인 요청 전
- 태스크 체크 박스 ☑ 치기 전

## 금지 문장 (검증 없이 이거 말하면 위반)

- "구현 완료"
- "테스트도 다 통과해요"
- "배포 준비 됐어요"
- "작동할 겁니다"
- "아마 될 거예요"
- "이제 돼요"

## Verification Checklist (모두 실제로 실행)

### 1. 코드 빌드/컴파일

```bash
# Python
python -m py_compile src/**/*.py
# 또는
python -c "import src.mymodule"

# Node/React
npm run build

# Java (AMHS)
mvn compile
```

**증거:** 빌드 출력 전체 복사. 경고도 기록.

### 2. 유닛 테스트

```bash
pytest -v tests/
```

**증거:** "N passed" 출력. 스킵된 거 있으면 이유 기록.

### 3. 통합 테스트 / 실제 실행

코드만 돌리는 게 아니라 **실제 엔드-투-엔드**:

- **Python 스크립트:** `python script.py --real-input` 실행 → 출력 파일 확인
- **Flask 앱:** 서버 띄우고 `curl` 로 엔드포인트 확인
- **React 컴포넌트:** 브라우저에서 실제 렌더링 확인 (스크린샷)
- **Logpresso 쿼리:** 실제 시간 범위로 실행 → 결과 수, 컬럼 수, 샘플 로우 기록
- **V7 모델:** 실제 평가 CSV 로드 → 예측 생성 → precision/recall 출력

### 4. 역기능 확인 (Negative Test)

"이건 실패해야 하는 케이스"도 테스트:
- 잘못된 입력 → 예상된 에러 나오나?
- 권한 없을 때 → 거부되나?
- 네트워크 끊겼을 때 → graceful fallback?

### 5. 기존 기능 영향도

"새 거만 되면 되는 게 아니다. 기존 거 안 깨졌는지 확인."

```bash
pytest -v  # 전체 다
# 또는
pytest --lf  # 마지막 실패만 재실행 후
pytest      # 전체
```

### 6. 로그/에러 확인

- 정상 실행 중 ERROR/WARNING 로그 없나?
- 있으면 무시해도 되는 이유 명시

## 증거 포맷

완료 선언 시 다음 구조로 보고:

```markdown
## Verification Report

### 환경
- Python 3.x, 브랜치 feature/abc, 커밋 def456

### 실행한 검증
| # | 커맨드 | 결과 | 증거 |
|---|--------|------|------|
| 1 | `pytest -v` | 47 passed, 0 failed | (출력 첨부) |
| 2 | `python train.py --sample` | 모델 파일 생성 확인 | `ls -la xgboost_*.pkl` |
| 3 | `curl -X POST /predict` | 200 OK, 예측값 275.4 | (로그 첨부) |

### 알려진 제한
- GPU 없는 환경에서는 hist fallback (의도된 동작)
- Logpresso fixture 데이터 1시간 범위만 검증

### 결론
✅ 완료 승인 가능
```

## 존님 환경 특화 검증

### V7 모델 배포 전

- [ ] `test_currentjob_predict` 샘플 데이터로 학습 완주 확인
- [ ] Feature 개수 11개인가?
- [ ] GPU 실패 시 CPU fallback 작동하나?
- [ ] 예측 threshold 280 일관되게 적용?
- [ ] seq_max < 300 & future ≥ 300 surge 정의 맞나?
- [ ] 인코딩 fallback (utf-8 → cp949 → euc-kr) 테스트?

### Logpresso 쿼리 배포 전

- [ ] 실제 FAB 시간 범위(최소 1일치)로 실행했나?
- [ ] 결과 컬럼 수가 의도한 대로 (예: 180)?
- [ ] CRT_TM 단조 증가?
- [ ] NULL 비율 이상치 없나?

### ASAS 스킬 배포 전

- [ ] Qwen3-235B가 실제 발동시키는가 (description 체크)?
- [ ] 한국어 프롬프트 정상 응답?
- [ ] 다른 스킬과 이름/트리거 충돌 없나?
- [ ] 폐쇄망에서 외부 의존성 없나?

### OHT 시뮬레이터 변경 후

- [ ] React 빌드 성공?
- [ ] STK 모드 동작 확인 (스크린샷)
- [ ] Zone heatmap 색 정상?
- [ ] OHT 애니메이션 lerp 부드러운가?
- [ ] JAM stats 폴링 정상?

### Java AMHS 코드 변경 후

- [ ] 단위 테스트 실행
- [ ] Integration 환경에서 UDP 패킷 받아 파싱 성공 확인
- [ ] HID IN/OUT 집계 1분 버퍼 flush 확인
- [ ] Logpresso로 flush된 데이터 조회 성공

## Rationalization Table (유혹 차단)

Claude가 검증 skip하려고 할 때 뜨는 생각과 반박:

| 유혹 | 반박 |
|------|------|
| "간단한 변경이니까" | 간단한 변경이 프로덕션 다 터뜨린다 |
| "시간 없어" | 검증 안 하고 버그 나면 더 걸린다 |
| "로컬에서 돌아갔어" | 로컬 ≠ 프로덕션. 증거 아님 |
| "테스트 통과했어" | 테스트는 의도 검증. 실제 동작 검증 아님 |
| "이미 비슷한 패턴 써봤어" | 비슷 ≠ 동일 |
| "전에 해본 거야" | 전과 환경/데이터 다름 |

## 출력 템플릿

"완료" 선언 시 Claude가 응답할 포맷:

```
검증 완료했어요. 결과:

- 테스트: 47/47 통과
- 빌드: 성공
- 엔드-투-엔드: curl /predict → 200 OK, 예측값 275.4
- 기존 테스트: 모두 통과 (회귀 없음)

(상세 출력은 docs/verify/YYYY-MM-DD.md)

배포 진행해도 됩니다. 혹시 추가로 확인하고 싶은 케이스 있으세요?
```

증거 없이 "완료" 단독으로 말하면 **이 스킬 위반**.
