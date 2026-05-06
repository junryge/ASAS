# OHT_UDP_SIM (송신 전용)

LOGPRESSO_OHT_DATA CSV → **UDP 송신** 시뮬레이터.

> 수신은 **`WORD_MODEL/WORLD_SIM`** (기존 시뮬) 에서 받음.
> 본 폴더는 **송신기만** 제공.

---

## 동작 흐름

```
LOGPRESSO_OHT_DATA_20260429.CSV (M14A)  ─┐
                                         ├─→ sender.py m14a    ─UDP 3710─┐
LOGPRESSO_OHT_DATA_20260429.CSV (M16BR) ─┘                                 │
                                                                           ▼
                                            ┌──────────────────────────────┐
                                            │  WORD_MODEL/WORLD_SIM        │
                                            │  main.py (FastAPI)            │
                                            │   - UDP listen 3710 / 3750   │
                                            │   - engine.world 에 차량 주입  │
                                            │   - dashboard 표시            │
                                            └──────────────────────────────┘
                                            ▲
LOGPRESSO_OHT_DATA_20260429.CSV (M16BR) ──→ sender.py m16a_br ─UDP 3750──┘
```

- 송신측이 row 의 **`_time`** 차이만큼 sleep 하여 시간순 송신 (속도 배율 적용)
- 같은 1초 안의 row 는 한 패킷 (200 row 초과 시 분할)
- CSV 끝나면 자동 loop (cycle++)
- WORLD_SIM 은 UDP 패킷이 들어올 때마다 `engine.world.load_vehicles_from_frame(...)` 호출

---

## 구성

```
OHT_UDP_SIM/
├── config.py           포트/경로/속도/기간
├── csv_loader.py       LOGPRESSO_OHT_DATA CSV 파서
├── sender.py           UDP 송신 (m14a / m16a_br 모드) + 송신 제어 UI
├── templates/sender.html   송신 제어 UI 템플릿
├── M14A_DATA/          ← LOGPRESSO_OHT_DATA_20260429.CSV 배치
└── M16A_BR_DATA/       ← LOGPRESSO_OHT_DATA_20260429.CSV 배치
```

---

## 데이터 배치

```
WORD_MODEL/OHT_UDP_SIM/
  M14A_DATA/LOGPRESSO_OHT_DATA_20260429.CSV
  M16A_BR_DATA/LOGPRESSO_OHT_DATA_20260429.CSV
```

CSV 가 없으면 `config.py` 가 상위 폴더 (WORD_MODEL/, ASAS/) 까지 자동 탐색.

기간: **2026-04-29 11:00 ~ 2026-04-30 23:46** (config.py 의 `REPLAY_START/END` 변경 가능)

---

## 실행

### ① 수신측 (WORLD_SIM) 먼저 띄움

```bash
cd ../WORLD_SIM
python3 main.py
```

→ `[UDP] listen M14A:3710  M16A_BR:3750` 출력 확인.
대시보드: <http://localhost:8000> (실제 SERVER_PORT 는 WORLD_SIM/config.py 참조)

### ② 송신측

```bash
cd OHT_UDP_SIM

# 두 FAB 동시
python3 sender.py m14a       &
python3 sender.py m16a_br    &
```

각 송신기는 자체 제어 UI 를 띄움 — **▶ 시작 버튼을 눌러야 송신**:

| 송신기 | UDP 포트 | 제어 UI |
|---|---|---|
| M14A    | 3710 | <http://127.0.0.1:11010> |
| M16A_BR | 3750 | <http://127.0.0.1:11020> |

---

## 송신 UI 기능

| 컨트롤 | 동작 |
|---|---|
| ▶ 시작 | 처음부터 재생 시작 |
| ⏸ 일시정지 / ▶ 재개 | 현재 위치 유지 |
| ■ 정지 | 송신 종료 |
| 속도 (×) | 0.1 = 1/10 속도, 1 = 실시간, 60 = 1분→1시간 |
| 루프 | CSV 끝나면 처음부터 (cycle++) |
| 위치 점프 | 0~100% 슬라이더 |

상태 표시: 전송 패킷/row/byte, 현재 ts, cycle, 진행률 바.

---

## 송신 API (제어용)

각 sender 별 `http://127.0.0.1:11010` 또는 `:11020`

```
GET  /api/status                           # 현재 상태
POST /api/start  | /pause | /resume | /stop
POST /api/speed  body: {"speed": 60}
POST /api/loop   body: {"loop": true}
POST /api/seek   body: {"ratio": 0.5}
```

---

## 수신측 (WORLD_SIM) UDP 통계 확인

```bash
curl http://localhost:8000/api/udp/state
```

```json
{
  "running": true,
  "host": "0.0.0.0",
  "fabs": {
    "M14A":    {"port": 3710, "rx_packets": ..., "rx_rows": ..., "last_ts": "..."},
    "M16A_BR": {"port": 3750, "rx_packets": ..., "rx_rows": ..., "last_ts": "..."}
  },
  "last_error": null
}
```

---

## UDP 패킷 포맷 (JSON 기본)

```json
{
  "fab":   "M14A",
  "ts":    "2026-04-29T11:00:01+09:00",
  "count": 38,
  "rows":  [ { "_id":"...", "_time":"...", "VHL_ID":"BV0103", ... }, ... ]
}
```

`config.PACKET_FORMAT = "csv"` 로 하면 CSV 형식 송신.
한 패킷이 64KB 를 넘지 않게 200 row 단위로 분할 송신.

---

## 한계

- LAN 전제 (UDP 손실 보정 없음)
- 단일 row 가 64KB 이상이면 송신 실패
- 수신측이 죽어도 송신은 계속 (UDP 특성)
- 시간순 정렬을 위해 CSV 전체를 메모리에 적재 — 수GB 급은 부적합
