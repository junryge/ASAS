# WORLD_SIM 레일 차단 표시 패치

## 적용 방법

### 1. dashboard.html 교체
```
WORD_MODEL/WORLD_SIM/dashboard.html
```
위 경로에 포함된 `dashboard.html`로 덮어쓰기.

### 2. data_loader.py 수정
`data_loader.py`의 `DateDataLoader` 클래스 안에서:

**[A] 새 메서드 추가** (예: `get_hid_speed_summary` 뒤)
→ `data_loader_railcut_patch.py`의 `_get_active_rail_cuts` 메서드 복사해서 붙여넣기

**[B] `get_frame_at` 메서드 안의 RAIL_CUT 블록 교체**

기존:
```python
# RAIL_CUT: 현재까지 발생한 이벤트
rail_cuts = []
for t, ev in self.rail_cut_events:
    if t <= target_time:
        rail_cuts.append(ev)
```

교체:
```python
# RAIL_CUT: 페어 매칭으로 현재 활성 차단만 반환
rail_cuts = self._get_active_rail_cuts(target_time)
```

### 3. CSV 파일
기존 포맷 그대로 사용. 변경 없음.

```
OHS_DATA_MD/
  20260414/LOGPRESSO_OHT_RAIL_CUT_20260414.CSV
  20260415/LOGPRESSO_OHT_RAIL_CUT_20260415.CSV
  ...
```

### 4. 서버 재시작
```bash
cd WORD_MODEL/WORLD_SIM
python main.py
```

---

## 동작 로직

- **STATE=ABNORMAL** → 맵에 ⛔ 표시 (빨간 점선 + X 마커, 깜빡임)
- **STATE=NORMAL**   → 맵에서 자동 제거
- **NORMAL 없으면**   → 계속 표시 유지
- **ABNORMAL 없이 NORMAL만 오면** → 조용히 무시 (에러 없음)

데이터가 말하는 대로 그대로 믿고 처리.

---

## UI 추가 기능

- 상단 툴바: `차단 표시` 토글 버튼 (on/off)
- 상단 배너: 활성 차단 있을 때 빨간 배너 자동 표시
- 좌측 사이드바: `레일 차단 이벤트` 패널에 활성 개수 + 최근 5건 로그
- 맵 범례: 좌하단에 `⛔ 레일 차단 (N)` 자동 추가

---

## 남은 결정 사항

**날짜 처리 방식** — 현재 구조는 **선택한 날짜 하루치만 재생**.

만약 전날 차단이 다음 날로 이어지는 경우 반영하려면:
→ `_scan_data_dates` 수정해서 선택 날짜 + 이전 날짜들 연결 필요 (별도 요청 시 제공)
