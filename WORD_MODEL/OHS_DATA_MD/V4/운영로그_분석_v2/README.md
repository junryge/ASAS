# 운영로그 분석 v2 — Episode 단위 장애 라벨링

> v1 (`../운영로그_파서.py`, 메시지 단위) 의 한계를 보완.
> 6/12 검토결과 (`../장애라벨링_검토결과_20260612.md`) 의 제안 4개 전부 반영.

---

## 폴더 구조

```
운영로그_분석_v2/
 ├─ README.md                    ← 본 파일
 ├─ 운영로그_파서_v2.py          ★ 메인 코드
 └─ output/                      ← 실행 결과
     ├─ YYYYMMDD_HHMMSS_message.csv   (메시지 단위, v1 호환)
     ├─ YYYYMMDD_HHMMSS_episode.csv   (Episode 단위, v2 핵심)
     └─ YYYYMMDD_HHMMSS_summary.json  (통계 요약)
```

---

## 사용법

```bash
python3 운영로그_파서_v2.py <운영로그.txt>
python3 운영로그_파서_v2.py ../AP/MA202605.txt --out ./output
```

---

## v1 vs v2 핵심 차이

| 항목 | v1 (`운영로그_파서.py`) | v2 (`운영로그_파서_v2.py`) |
|---|---|---|
| 처리 단위 | 메시지 (1메시지 = 1장애) | **Episode (1장애 = 여러 메시지 묶음)** |
| 카테고리 | event_type 17종 (혼재) | **6종** (fault/action/recovery/rollback/cancel/normal) |
| 장애 유형 | 없음 | **7종** (정체/브릿지/리프터/CNV/MLUD/통신/기타) |
| 키워드 우선순위 | 단순 매칭 | **복구 > 장애** (Case 4) |
| Episode 묶기 | 없음 | **장비 + 30분 window** |
| orphan 처리 | 없음 | **선행 fault 없는 recovery 제외** (Case 1) |
| 거품 제거 | — | **86.8%** (실측: 152건 → 20건) |

---

## 알고리즘 8단계

1. **헤더 기준 메시지 분리** — `작성자,조직,YYYY-MM-DD HH:MM:SS`
2. **전처리** — 멘션(`{{@이름}}`)/URL/이미지 제거
3. **카테고리 분류 6종** — 복구 키워드 우선
4. **장애유형 7종 분류** — fault 메시지만
5. **장비명/라인 추출** — 정규식
6. **Episode 클러스터링** — find_open_episode (score-based)
7. **Episode 라벨링** — start/end/장비/유형/지속/severity/상태
8. **Output 생성** — message.csv + episode.csv + summary.json

---

## 설정값 (6/12 검토 기반)

| 변수 | 값 | 설명 |
|---|---|---|
| `SESSION_WINDOW_MIN` | 30 | Episode 묶기 시간 윈도우 (분) |
| `REOPEN_WINDOW_MIN` | 15 | 복구 후 재발생 분리 |
| `SCORE_THRESHOLD` | 6 | find_open_episode 매칭 임계 |

### find_open_episode 점수

| 조건 | 점수 |
|---|---|
| 같은 장비 | +6 |
| 같은 라인 | +3 |
| 역할 흐름 자연스러움 (fault→action→recovery 등) | +3 |
| **threshold** | **≥ 6** (장비 일치만 해도 매칭) |

---

## 예외 처리 5 Case (실데이터 검증)

| Case | 설명 | v2 처리 |
|---|---|---|
| 1 | 복구 단독 등장 (선행 fault 없음) | `orphan` 라벨, 장애 카운트 제외 |
| 2 | 요청→완료→원복요청→원복완료 | 1 Episode 로 묶음 |
| 3 | 복구 후 재발생 (gap > window) | 새 Episode |
| 4 | "Error 조치되어" — 장애+복구 공존 | recovery 우선 매칭 |
| 5 | "Error 발생으로 Close 하겠" — fault+action 공존 | **fault 우선** (FAULT_PRIORITY_KEYWORDS) |

---

## 실측 결과 (MA202605.txt 529건)

```
[1/4] 메시지 파싱: 476건 (이미지/멘션 전용 제거 후)
[2/4] 카테고리:    fault 71 / recovery 28 / rollback 45 / action 3 / cancel 5 / normal 324
[3/4] Episode:    20건 (closed 5 / open 15) + orphan 9건 별도
[4/4] 출력:        message.csv, episode.csv, summary.json

📊 v1 (메시지 단위) 장애 카운트 : 152건
📊 v2 (Episode 단위) 장애 카운트: 20건
📉 거품 제거: 86.8%
```

### Episode 분포 (장애 유형별)

| 유형 | Episode 수 |
|---|---|
| 리프터 (4ABLD/6ABL) | 6 |
| 정체/병목 | 5 |
| 브릿지 (ZT) | 4 |
| CNV (4AFC) | 2 |
| 기타 | 1 |

### Severity 분포

| 등급 | 기준 | 개수 |
|---|---|---|
| HIGH | > 60분 | 0 |
| MED | 15~60분 | 3 |
| LOW | < 15분 | 17 |

---

## 알려진 실제 사례 (5월)

| Episode | 일시 | 장비 | 유형 | 지속 | 상태 |
|---|---|---|---|---|---|
| E1 | 05-06 11:49~12:05 | 4ABLD131 | 리프터 | 16분 | closed |
| E17 | 05-14 11:57~12:21 | 4ABLD131 | 리프터 | 25분 | closed (재발생) |
| E19 | 05-16 03:49~04:09 | 4ABLD121 | 리프터 | 20분 | closed |

→ 같은 4ABLD131 이 5/6과 5/14 에 발생하지만 8일 간격이라 자동으로 **별도 Episode 2건** 으로 분리됨 (Case 3).

---

## Output CSV 컬럼

### `episode.csv` (v2 핵심)

| 컬럼 | 설명 |
|---|---|
| `episode_id` | Episode 일련번호 |
| `start_time` | 장애 시작 |
| `end_time` | 종료 (open 이면 last_time) |
| `duration_min` | 지속 시간 |
| `equipment` | 장비명 (4ABLD131 등) |
| `line` | 라인 (M14B 등) |
| `fault_type` | 7종 유형 |
| `severity` | LOW/MED/HIGH |
| `status` | open/closed/orphan |
| `is_orphan` | Y/N |
| `message_count` | 묶인 메시지 수 |
| `message_ids` | 메시지 ID 리스트 (`|` 구분) |

### `message.csv` (v1 호환)

| 컬럼 | 설명 |
|---|---|
| `msg_id` | 메시지 ID |
| `datetime` | 시각 |
| `sender`, `org` | 작성자/조직 |
| `category` | 6종 카테고리 |
| `fault_type` | fault 일 때 유형 |
| `equipment`, `line` | 추출된 장비/라인 |
| `text` | 메시지 본문 |

---

## 다음 단계 (검토결과 §6 인용)

| 단계 | 작업 | 룰베이스 수정 |
|---|---|---|
| 1 | ✅ **본 작업 (v2 파서)** | ❌ |
| 2 | ML 라벨 B 연결 (`messenger_to_incidents.py`) | ❌ (재학습만) |
| 3 | 사건단위↔Episode 자동 매칭 | ⚠️ `INCIDENT_FIELDS` 확장 |
| 4 | 임계값 피드백 자동화 | ⚠️ 신규 모듈 |
| 5 | 신규 룰 추가 (예: 통신/에러) | ✅ hubroom_predictor.py |

---

## 관련 문서

- `../장애라벨링_검토결과_20260612.md` — 본 작업의 근거 (제안 4개 검증)
- `../운영로그_파서_v2_명세서.md` — 명세서 (이후 갱신 예정)
- `../운영로그_파서.py` — v1 (메시지 단위)
- `../AP/MA202605.txt` — 검증 데이터 (5월 메신저 529건)
