# UDP_SIM — 실시간 OHT 차량 위치 (UDP 수신 전용 시뮬)

`OHT_UDP_SIM/sender.py` 가 송신한 UDP 패킷 (LOGPRESSO_OHT_DATA) 을 받아
**차량 위치를 지도에 표시**하는 신규 시뮬.

기존 `WORLD_SIM` 은 손대지 않고 별도 폴더로 동작. 레이아웃 캐시(`OHT_MAP/cache/`) 만
**읽기전용** 으로 공유.

```
[CSV] ─→ OHT_UDP_SIM/sender.py ─UDP 3710/3750─→ UDP_SIM/server.py ─WebSocket→ 브라우저
                                                  │
                                                  └─ OHT_MAP/cache/*.json (read only)
```

---

## 구성

```
UDP_SIM/
├── config.py        포트 / 캐시 경로 / 푸시 주기
├── layout.py        OHT_MAP 캐시 → 노드/엣지 + (x,y) 보간
├── server.py        FastAPI: UDP 수신 + WebSocket + HTTP
├── dashboard.html   차량 지도 UI (SVG 줌/팬, 잔상, 상태 분포, 수신 통계)
└── README.md
```

---

## 실행

### 0) 의존성 (한 번만)

```bash
pip install fastapi uvicorn
```

### 1) 수신측 (UDP_SIM)

```bash
cd WORD_MODEL/UDP_SIM
python3 server.py
```

→ 출력
```
[UDP_SIM] HTTP 0.0.0.0:12000
[layout] M14A:    nodes=9402  edges=10422
[layout] M16A_BR: nodes=1945  edges=...
```

브라우저: <http://localhost:12000>

### 2) 송신측 (OHT_UDP_SIM)

```bash
cd WORD_MODEL/OHT_UDP_SIM

python3 sender.py m14a       # UDP 3710 + 제어 UI :11010
python3 sender.py m16a_br    # UDP 3750 + 제어 UI :11020
```

각 송신기 UI 에서 **▶ 시작** 클릭 → CSV `_time` 순서대로 UDP 송신 시작.

---

## UI 기능

### 토픽바
- **FAB 선택** — M14A / M16A_BR
- **엣지/노드/잔상/차량ID** 토글
- **전체보기** — bounds 기준 fit
- **UDP 표시기** — 두 FAB 의 ●live / stale / off 상태 + 패킷 수
- **WS** 상태 (연결됨/끊김)

### 좌측 패널
- 현재 FAB 정보 (노드/엣지/활성 차량/전체 차량)
- M14A / M16A_BR 각 UDP 수신 통계 (패킷/row/byte/CSV ts/최근 수신/송신 from)
- 차량 상태 분포 막대 (RUN/WAIT/STOP/...)

### 지도
- 마우스 휠 = 줌
- 드래그 = 이동
- 더블클릭 = 전체보기
- 차량 = 색 = 상태, 외곽선 = FAB (M14A 녹색 / M16A_BR 파랑)
- 잔상 = 최근 8 프레임 경로

---

## API

```
GET  /                       대시보드 HTML
GET  /api/state              UDP 통계 + 차량 카운트
GET  /api/layout?fab=M14A    배경 지도 (노드 + 엣지)
GET  /api/vehicles?fab=M14A  현재 차량 스냅샷
WS   /ws                     4Hz 차량 푸시
```

---

## 데이터 흐름

```
sender.py (CSV `_time` 순)
  ─UDP JSON─→  FabReceiver(M14A:3710 / M16A_BR:3750)
                 │  parse_row(row) → {vid, currentNode, nextNode, distance, state, ...}
                 ▼
              VehicleStore.update()              # (fab, vid) -> Vehicle
                 │
                 ▼  매 0.25초
            ws_pusher() → WebSocket
                 │
                 ▼
            dashboard.html                        # SVG 지도 + 잔상
              layout.get_position(curr, next, dist) → (x,y)
```

`Vehicle.last_rx` 가 10초 이상 갱신 안 되면 stale → 화면에서 사라짐
(`config.VEHICLE_STALE_SEC` 조정).

---

## 한계

- **레이아웃 캐시**: `WORD_MODEL/OHT_MAP/cache/M14A_A_layout_cache.json`,
  `M16A_BR_layout_cache.json` 가 있어야 함 (이미 존재).
  파일이 없으면 차량 위치는 계산 안 됨 (수신 통계는 정상).
- LAN 전제 (UDP 손실 보정 없음)
- Tens of thousands 차량은 SVG 부하 — 1k 이내가 적정
- 데드락 예측, TAT 등 분석은 포함 안 함 (WORLD_SIM 영역)
