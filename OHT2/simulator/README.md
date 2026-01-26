# OHT2 Simulator

SK하이닉스 M14 반도체 공장 OHT (Overhead Hoist Transport) 시스템 시뮬레이터

## 개요

| 항목 | 값 |
|------|-----|
| 프로젝트 | M14-Pro Ver.1.22.2 |
| 클라이언트 | SK Hynix |
| 최대 OHT 차량 | 2,000대 |
| 최대 스테이션 | 22,972개 |
| 스케줄러 모드 | 동적 최적화 (Mode 3) |

## 설치

```bash
# 기본 실행 (의존성 없음)
python main.py

# 웹 서버 모드 (websockets 필요)
pip install websockets
python server.py
```

## 실행 방법

### 데모 모드
```bash
python main.py --mode demo
```

### 콘솔 모드
```bash
python main.py --mode console --duration 120
```

### 웹 서버 모드
```bash
python server.py
# 브라우저에서 http://localhost:8080 접속
```

## 구조

```
simulator/
├── core/
│   ├── __init__.py     # 모듈 exports
│   ├── models.py       # 데이터 모델 (Vehicle, Station, Job 등)
│   ├── scheduler.py    # 스케줄러 (경로 탐색, 작업 배정)
│   └── engine.py       # 시뮬레이션 엔진
├── web/
│   └── index.html      # 웹 기반 시각화 UI
├── config/
│   └── settings.json   # 설정 파일
├── main.py             # CLI 실행 스크립트
├── server.py           # 웹소켓 서버
└── README.md
```

## 핵심 기능

### 1. 데이터 모델
- **Vehicle**: OHT 차량 (상태, 위치, 속도, FOUP 보유 여부)
- **Station**: 로딩/언로딩 스테이션 (22,972개 타입별 분류)
- **Lane**: 레일 구간 (연결 정보, 활성화 상태)
- **TransportJob**: 이송 작업 (출발지, 목적지, 우선순위)

### 2. 스케줄러
- **동적 라우팅**: Dijkstra 알고리즘 기반 최단 경로 탐색
- **HotLot 우선순위**: Priority 99, 120초 타임아웃
- **작업 배정**: 가장 가까운 대기 차량 자동 배정

### 3. 충돌 방지
- **BUMP_DISTANCE**: 19,932mm 충돌 방지 거리
- **안전 속도 계산**: 전방 차량 거리 기반 속도 조절
- **비상 정지**: 근접 시 즉시 정지

### 4. 시각화 UI
- **실시간 맵 표시**: 차량, 스테이션, 레일 시각화
- **드래그/줌**: 맵 탐색
- **작업 생성**: 이송 작업 수동 생성
- **통계 대시보드**: 실시간 KPI 표시

## 속도 설정

| 속도 인덱스 | 속도 (m/min) |
|-------------|--------------|
| 1-5 | 1.5 - 15 |
| 6-10 | 20 - 40 |
| 11-15 | 45 - 65 |
| 16-20 | 70 - 100 |
| 21-25 | 110 - 150 |
| 26-32 | 160 - 200 |

## 곡선 반경별 속도

| 반경 | 진입 | 곡선 | 출구 |
|------|------|------|------|
| R400 | 8 | 8 | 13 |
| R450 | 16 | 14 | 16 |
| R500 | 11 | 11 | 17 |
| R600 | 11 | 11 | 14 |

## API (웹소켓)

### 명령어
```json
// 시뮬레이션 시작
{"command": "start"}

// 시뮬레이션 중지
{"command": "stop"}

// 작업 생성
{"command": "create_job", "source": 1, "dest": 10, "priority": "HOTLOT"}

// 상태 조회
{"command": "get_state"}
```

### 응답 (상태)
```json
{
    "tick": 1234,
    "time": 123.4,
    "vehicles": [...],
    "stations": [...],
    "jobs": {"pending": 5, "active": 3, "completed": 42},
    "statistics": {...}
}
```

## 라이선스

Internal Use Only - SK Hynix M14 Project
