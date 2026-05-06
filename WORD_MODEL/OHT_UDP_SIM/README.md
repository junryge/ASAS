# OHT_UDP_SIM

LOGPRESSO_OHT_DATA CSV 를 읽어 **UDP 로 리플레이 송신** 하고, **메인 수신기 UI** 에서
실시간 표시하는 시뮬레이터.

> WORLD_SIM 과 폴더는 분리. 동작 방식 (UDP push, 단순 패스스루) 이 다르므로 **신규 폴더**.

---

## 구성

```
OHT_UDP_SIM/
├── config.py           포트/경로/속도 설정
├── csv_loader.py       LOGPRESSO_OHT_DATA CSV 파서 (시간순 정렬, 1초 그룹핑)
├── sender.py           UDP 송신기 (m14a / m16a_br 모드)
├── main.py             UDP 수신 메인 (3710 + 3750 동시 listen)
├── templates/
│   ├── sender.html     송신 제어 UI
│   └── main.html       수신 라이브 UI
├── start_all.sh        3개 프로세스 일괄 실행
├── stop_all.sh         일괄 정지
├── M14A_DATA/          ← LOGPRESSO_OHT_DATA_20260429.CSV 배치
└── M16A_BR_DATA/       ← LOGPRESSO_OHT_DATA_20260429.CSV 배치
```

---

## 동작

```
┌──────────────┐   UDP 3710  ┌──────────────┐
│ sender M14A  │ ──────────→ │              │       ┌────────────┐
│ HTTP 11010   │             │  main.py     │ ─SSE→ │ 브라우저    │
└──────────────┘             │  HTTP 11000  │       │ (main UI)  │
┌──────────────┐   UDP 3750  │              │       └────────────┘
│ sender M16BR │ ──────────→ │ 두 포트 listen │
│ HTTP 11020   │             └──────────────┘
└──────────────┘
```

- 송신측: 1초 묶음으로 row 들을 `JSON UDP 패킷` (기본) 으로 보냄
- 패킷 = `{fab, ts, count, rows[]}`  → 패킷당 최대 200 row, 초과 시 분할
- CSV 끝나면 자동으로 처음부터 (loop 토글로 끔/켬)
- 송신 속도 기본 60× (1분당 1시간 압축), UI 에서 0.1~3600× 조정

---

## 데이터 배치

```
WORD_MODEL/OHT_UDP_SIM/
  M14A_DATA/LOGPRESSO_OHT_DATA_20260429.CSV
  M16A_BR_DATA/LOGPRESSO_OHT_DATA_20260429.CSV
```

CSV 가 없으면 `config.py` 가 상위 폴더 (WORD_MODEL/, ASAS/) 까지 자동 탐색.

CSV 헤더는 Logpresso 표준 — `_id`, `_table`, `_time`, `EVENT_DT`, `VHL_ID` 등.
`_time` 컬럼을 자동 탐지해 시간순 정렬 + REPLAY_START~END 범위 필터.

기간: **2026-04-29 11:00 ~ 2026-04-30 23:46** (config.py 의 `REPLAY_START/END` 변경 가능)

---

## 실행

### 일괄

```bash
./start_all.sh
```

→ 3 프로세스 (main + 2 sender) 백그라운드 실행. 로그는 `logs/`.

브라우저:

- 메인 (수신 라이브)  : <http://127.0.0.1:11000>
- M14A 송신 제어     : <http://127.0.0.1:11010>
- M16A_BR 송신 제어  : <http://127.0.0.1:11020>

세 화면을 모두 띄운 뒤 **각 송신 UI 에서 ▶ 시작 버튼**.

### 개별

```bash
python3 main.py                 # 수신 메인 (먼저 실행)
python3 sender.py m14a          # M14A 송신
python3 sender.py m16a_br       # M16A_BR 송신
```

### 정지

```bash
./stop_all.sh
```

---

## 송신 UI

| 컨트롤 | 동작 |
|---|---|
| ▶ 시작 | 처음부터 재생 시작 |
| ⏸ 일시정지 / ▶ 재개 | 현재 위치 유지 |
| ■ 정지 | 송신 종료 |
| 속도 (×) | 0.1 = 1/10 속도, 1 = 실시간, 60 = 1분→1시간 |
| 루프 | CSV 끝나면 처음부터 (cycle++) |
| 위치 점프 | 0~100% 슬라이더 |

상태 표시: 전송 패킷/row/byte, 현재 ts, cycle, 진행률 바.

## 메인 UI

- 두 FAB (M14A, M16A_BR) 수신 통계 카드
- 실시간 피드 (SSE) — 패킷 단위 라이브 로그, 샘플 row 미리보기
- 필터 (M14A/M16A_BR 표시 토글), 자동 스크롤, 라인 수 제한
- 통계 초기화 버튼

---

## API

### Sender (`http://localhost:11010` 또는 `:11020`)

```
GET  /api/status                           # 현재 상태
POST /api/start  | /pause | /resume | /stop
POST /api/speed  body: {"speed": 60}
POST /api/loop   body: {"loop": true}
POST /api/seek   body: {"ratio": 0.5}      # 0~1
```

### Main (`http://localhost:11000`)

```
GET  /api/state                            # 두 FAB 통합 상태
GET  /api/recent?fab=M14A&n=50             # 최근 50건
GET  /api/stream                           # SSE 라이브 푸시
POST /api/clear                            # 통계 초기화
```

---

## UDP 패킷 포맷 (JSON 기본)

```json
{
  "fab":   "M14A",
  "ts":    "2026-04-29T11:00:01+09:00",
  "count": 38,
  "rows": [
    { "_id": "1234", "_time": "...", "VHL_ID": "BV0103", ... },
    ...
  ]
}
```

`config.PACKET_FORMAT = "csv"` 로 하면 CSV 형식으로 송신.
한 패킷이 64KB 를 넘지 않게 `MAX_ROWS_PER_PACKET=200` 으로 분할 송신.

---

## 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| 송신 UI 에서 `CSV 없음 ⚠️` | `M14A_DATA/` 또는 `M16A_BR_DATA/` 에 CSV 가 없음 |
| 메인 화면이 0 | 송신측 ▶ 시작 안 누름 / 방화벽 |
| 포트 충돌 | `config.py` 또는 환경변수 `UDP_PORT_M14A`, `UDP_PORT_M16A_BR` 로 변경 |
| 속도가 너무 느림 | 송신 UI 속도 ↑ (60 → 600) |

---

## 한계

- LAN 전제 (UDP 손실 보정 없음). 운영 배포 시 TCP/MQ 검토 권장
- 패킷이 64KB 넘는 row 로는 분할되지만, **단일 row 가 이미 64KB 이상** 이면 실패
- main 수신측이 죽어도 sender 는 계속 송신 (UDP 특성)
- 시간순 정렬을 위해 CSV 전체를 메모리에 적재 — 수GB 급은 부적합
