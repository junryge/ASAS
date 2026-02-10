# OHT 3D Layout Visualization System - 개발 문서

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | AMOS MAP SYSTEM PRO - OHT FAB Simulator |
| **목적** | 반도체 FAB OHT(Overhead Hoist Transport) 레일 시스템 3D 시각화 |
| **개발 방식** | **3D LLM (3D Large Language Model)** - LLM이 3D 엔진 역할 |
| **버전** | 2.0.0 |
| **포트** | 10003 |
| **개발자** | John Prestige |

---

## 3D LLM (3D Large Language Model) 개발 기법

### 핵심 개념: 3D LLM이란?

**3D LLM = Large Language Model이 3D 엔진 역할을 수행하는 개발 패러다임**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   기존 3D 개발:  사람 → 3D 엔진 (Unity/Unreal) → 결과물     │
│                                                             │
│   3D LLM 개발:   사람 → LLM (= 3D 엔진) → 결과물            │
│                                                             │
│   LLM 자체가 3D 씬 구성, 모델링, 애니메이션, 물리,           │
│   최적화를 모두 수행하는 "지능형 3D 엔진"                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

본 프로젝트는 **3D LLM 기법**을 적용하여 개발되었습니다.
LLM이 단순 코드 보조가 아니라, **3D 씬 설계 → 모델링 → 렌더링 → 애니메이션 → 최적화**의
전 과정을 직접 수행하는 **3D 생성 엔진** 역할을 합니다.

기존 3D 개발은 Unity, Unreal Engine, Blender 등 전문 도구와
3D 그래픽스 프로그래머가 필수였지만, 3D LLM 방식에서는
**자연어 프롬프트만으로 완전한 3D 시스템을 생성**합니다.

### 3D LLM vs 기존 3D 엔진 비교

| 구분 | 기존 3D 엔진 | **3D LLM** (본 프로젝트) |
|------|-------------|-------------------------|
| **엔진** | Unity, Unreal, Godot | **LLM 자체가 엔진** |
| **입력** | C#/C++ 코드, 에디터 GUI | **자연어 프롬프트** |
| **3D 모델** | Maya/Blender → FBX/OBJ 임포트 | **LLM이 코드로 직접 생성** |
| **애니메이션** | 키프레임, 본 리깅 | **LLM이 상태 머신 + 물리 생성** |
| **최적화** | 개발자가 수동 프로파일링 | **LLM이 InstancedMesh 등 자동 적용** |
| **렌더링** | 엔진 내장 렌더러 | **Three.js WebGL (LLM이 구성)** |
| **배포** | 빌드 → 설치 파일 | **HTML 1개 (브라우저)** |
| **수정** | 소스 분석 → 수정 → 빌드 | **"이거 바꿔줘" → 즉시 반영** |
| **개발 기간** | 수주 ~ 수개월 | **수시간 ~ 수일** |
| **전문성** | 3D 그래픽스 전문 지식 필요 | **도메인 지식만 있으면 가능** |

### 3D LLM이 수행하는 역할

```
┌─────────────────────────────────────────────────────────────┐
│              3D LLM = 통합 3D 엔진                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 씬 설계     │  │ 3D 모델링   │  │ 렌더링 구성  │        │
│  │             │  │             │  │             │        │
│  │ Scene       │  │ Procedural  │  │ WebGL       │        │
│  │ Camera      │  │ Geometry    │  │ Shader      │        │
│  │ Lighting    │  │ Material    │  │ Post-FX     │        │
│  │ Fog         │  │ Texture     │  │ Anti-alias  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 애니메이션   │  │ 물리/시뮬   │  │ 성능 최적화  │        │
│  │             │  │             │  │             │        │
│  │ State Machine│  │ Path Follow │  │ InstancedMesh│       │
│  │ Curve Interp│  │ Collision   │  │ Spatial Index│       │
│  │ Tween       │  │ Zone Logic  │  │ LOD/Culling  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │ UI 생성     │  │ 데이터 연동  │                          │
│  │             │  │             │                          │
│  │ CSS Layout  │  │ REST API    │                          │
│  │ DOM Control │  │ JSON Parse  │                          │
│  │ Event Mgmt  │  │ WebSocket   │                          │
│  └─────────────┘  └─────────────┘                          │
│                                                             │
│  입력: 자연어 "OHT 레일 시스템을 3D로 보여줘"                  │
│  출력: 완전한 3D 애플리케이션 (2,500줄 HTML)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3D LLM 개발 워크플로우

```
┌─────────────────────────────────────────────────────────────┐
│                   3D LLM 워크플로우                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [STEP 1] 도메인 전문가가 자연어로 요구사항 전달               │
│  ┌─────────────────────────────────────────┐                │
│  │ "반도체 FAB의 OHT 레일 시스템이야.       │                │
│  │  layout.xml에 노드 4만개, 레일 5만개야.  │                │
│  │  이걸 3D로 볼 수 있게 해줘.              │                │
│  │  차량도 레일 위에 달리게 하고."           │                │
│  └───────────────┬─────────────────────────┘                │
│                  ▼                                          │
│  [STEP 2] 3D LLM이 전체 3D 시스템 생성                       │
│  ┌─────────────────────────────────────────┐                │
│  │ LLM 내부 처리:                          │                │
│  │  ① 3D 씬 아키텍처 설계                  │                │
│  │  ② Three.js 코드 생성                   │                │
│  │  ③ 대규모 데이터용 InstancedMesh 적용    │                │
│  │  ④ 차량 프로시저럴 모델링                │                │
│  │  ⑤ 경로 추적 애니메이션 시스템           │                │
│  │  ⑥ UI 패널 + 인터랙션 구현              │                │
│  └───────────────┬─────────────────────────┘                │
│                  ▼                                          │
│  [STEP 3] 반복 프롬프트로 기능 확장/수정                      │
│  ┌─────────────────────────────────────────┐                │
│  │ "Zone 혼잡도 보여줘"     → Zone 시스템   │                │
│  │ "미니맵 넣어줘"          → Canvas 미니맵 │                │
│  │ "FAB 여러개 전환해줘"    → Multi-FAB API │                │
│  │ "OHT 대수 저장해줘"     → 설정 영구저장  │                │
│  └───────────────┬─────────────────────────┘                │
│                  ▼                                          │
│  [STEP 4] 완성 → 브라우저에서 바로 실행                       │
│  ┌─────────────────────────────────────────┐                │
│  │ ✅ HTML 1개 파일 = 완전한 3D 애플리케이션│                │
│  │ ✅ 빌드/컴파일 없음                     │                │
│  │ ✅ 45,000 노드 + 1,500 차량 @ 60 FPS   │                │
│  └─────────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3D LLM이 생성한 결과물 상세

#### 1) 프로시저럴 3D 모델링

3D LLM은 외부 모델 파일(FBX, OBJ) 없이 **코드만으로 모든 3D 형상을 생성**합니다.

```
OHT 차량 = 3D LLM이 자연어에서 생성한 프로시저럴 모델

  프롬프트: "OHT 차량 만들어줘. 주황색 캐리지, 바퀴 2개,
           케이블로 FOUP 내리는 구조, 비콘등 포함"

  3D LLM 출력:
        ◆ Beacon (CylinderGeometry)          ← LLM이 생성
        │
    ════╧════  Carriage (BoxGeometry 24×6×10)  ← LLM이 생성
    ●       ●  Wheels (CylinderGeometry) × 2   ← LLM이 생성
    ┃ Motor ┃  Motor (BoxGeometry 12×3×8)      ← LLM이 생성
    ┃       ┃  Cables (CylinderGeometry) × 2   ← LLM이 생성 + 동적 스케일
    ┗━━━━━━━┛  Gripper (BoxGeometry)           ← LLM이 생성
    ┌───────┐
    │ FOUP  │  FOUP Body + Lid                 ← LLM이 생성 + 상태별 표시
    └───────┘
    ○ Ring (TorusGeometry)                     ← LLM이 생성 + 회전 애니메이션
    ◉ Lights × 2                               ← LLM이 생성 (전방 노랑/후방 빨강)
```

> 기존: 3D 아티스트가 Maya/Blender에서 모델링 → FBX 내보내기 → 로더 코드 작성 → 임포트
> 3D LLM: "OHT 차량 만들어줘" → **LLM이 지오메트리 조합으로 즉시 생성**

#### 2) 대규모 렌더링 최적화

3D LLM이 데이터 규모를 인지하고 **자동으로 최적화 패턴을 적용**:

```javascript
// 3D LLM이 45,000개 노드를 인지하고 자동으로 InstancedMesh 적용
// 사람이 "InstancedMesh 써줘"라고 말하지 않아도 LLM이 판단

const nodeMesh = new THREE.InstancedMesh(geometry, material, 45000);
// → 45,000개 오브젝트를 1번의 GPU 드로우 콜로 렌더링
```

| 데이터 규모 | 일반 Mesh | 3D LLM (InstancedMesh) |
|------------|----------|----------------------|
| 45,000 노드 | 45,000 드로우 콜 → **5 FPS** | 1 드로우 콜 → **60 FPS** |
| 52,000 엣지 | 메모리 초과 | InstancedMesh로 처리 |
| 1,500 차량 | 프레임 드랍 | Material 공유로 최적화 |

#### 3) 실시간 시뮬레이션

3D LLM이 생성한 차량 상태 머신 + 물리 애니메이션:

```
3D LLM이 자연어에서 생성한 시뮬레이션 로직:

프레임 루프 (requestAnimationFrame, 60 FPS)
    │
    ├── 차량 이동: CatmullRomCurve3 경로 추적
    │     └── Zone 혼잡도에 따른 자동 속도 감소
    │
    ├── 케이블 물리: scale.y 동적 변경
    │     └── 스테이션 도착 → 하강 → 대기 → 상승
    │
    ├── FOUP 적재: visible 토글
    │     └── 적재/비적재 상태 시각적 반영
    │
    ├── JAM 시뮬: 혼잡 Zone에서 정체 발생
    │     └── 3초 후 0.3%/프레임 확률로 자동 해제
    │
    └── Zone 통계: 1초마다 차량 위치 집계 → UI 반영
```

#### 4) 반응형 UI 자동 생성

| UI 요소 | 3D LLM 생성 방식 |
|---------|-----------------|
| 좌측 통계 패널 | CSS Grid + 실시간 DOM 업데이트 |
| 플로팅 컨트롤 | 드래그 가능 패널 (mousedown/mousemove) |
| 미니맵 | Canvas 2D 별도 렌더링 |
| OHT 리스트 | innerHTML 동적 생성 + 이벤트 위임 |
| 색상 피커 | CSS 그라데이션 버튼 + Material 교체 |
| 뷰 프리셋 | 카메라 position/target 프리셋 전환 |

### 3D LLM 개발의 핵심 장점

```
┌────────────────────────────────────────────────────────────┐
│               3D LLM 핵심 장점 5가지                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. LLM = 3D 엔진                                         │
│     별도 엔진(Unity/Unreal) 설치 불필요                     │
│     LLM 자체가 씬 설계 → 모델링 → 렌더링 → 최적화 수행     │
│                                                            │
│  2. 자연어 → 3D 직접 변환                                   │
│     "OHT가 레일 위를 달려" → 3D 차량 경로 추적 코드 생성    │
│     3D 프로그래밍 지식 없이 도메인 전문가가 직접 개발        │
│                                                            │
│  3. 실시간 반복 수정                                        │
│     "차량 색상 바꿔줘" → 즉시 Material 수정                 │
│     "Zone 표시 추가해줘" → 즉시 시각화 로직 추가            │
│     빌드/컴파일 과정 없이 브라우저 새로고침만으로 확인       │
│                                                            │
│  4. 자동 성능 최적화                                        │
│     LLM이 데이터 규모를 인지하고 InstancedMesh,             │
│     공간 인덱싱, Material 공유 등을 자동으로 적용           │
│     개발자가 프로파일링하지 않아도 60 FPS 달성              │
│                                                            │
│  5. 제로 빌드 배포                                          │
│     HTML 1개 파일 = 완전한 3D 애플리케이션                  │
│     서버 1개 실행 → 브라우저 접속 → 끝                     │
│     CDN import로 의존성 자동 해결                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3D LLM 프롬프트 히스토리

본 프로젝트에서 실제 사용된 3D LLM 프롬프트:

| 단계 | 프롬프트 (자연어 입력) | 3D LLM 출력 |
|------|----------------------|------------|
| 3D 씬 생성 | "layout.xml을 파싱해서 3D로 보여줘" | Three.js Scene + Camera + Renderer + 데이터 로더 |
| 모델링 | "OHT 차량을 레일 위에 달리게 해줘" | 프로시저럴 차량 모델 + 경로 추적 애니메이션 |
| 시뮬레이션 | "JAM, 정지, 적재 상태 넣어줘" | 상태 머신 + 시나리오 생성 + 시각적 피드백 |
| Zone 물리 | "Zone별 혼잡도 표시해줘" | Zone 집계 + 속도 감소 물리 + UI 표시 |
| UI | "좌측에 통계, 우측에 차량 리스트" | CSS Grid 레이아웃 + 탭 UI + 이벤트 위임 |
| 미니맵 | "우하단에 미니맵 추가해줘" | Canvas 2D 미니맵 + 뷰포트 인디케이터 |
| Multi-FAB | "여러 FAB 전환 가능하게 해줘" | FAB 드롭다운 + REST API + 캐시 무효화 |
| 설정 저장 | "OHT 대수 FAB별로 저장되게 해줘" | JSON 파일 영구 저장 + 자동 복원 |

### 3D LLM 기술적 한계 및 해결

| 한계 | 3D LLM 해결 방법 |
|------|-----------------|
| 3D 모델 파일 생성 불가 | 프로시저럴 지오메트리 (Box/Cylinder/Sphere 조합) |
| 컨텍스트 윈도우 한계 | 단일 HTML 파일 구조 (빌드 없이 전체 코드 관리) |
| 텍스처/PBR 한계 | MeshPhongMaterial + 색상 기반 시각 구분 |
| 복잡한 물리 엔진 없음 | 경로 추적 + 상태 머신으로 시뮬레이션 근사 |
| GPU 셰이더 직접 작성 한계 | Three.js 내장 렌더러 + InstancedMesh 최적화 활용 |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    시스템 전체 구조 (3-Tier)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1단계] XML 파싱         [2단계] 서버           [3단계] 3D UI    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │parse_layout.py│───▶│  server.py   │───▶│oht_3d_layout │  │
│  │              │    │  (FastAPI)   │    │   .html      │  │
│  │ layout.xml   │    │  Port:10003  │    │  (Three.js)  │  │
│  │    ▼         │    │              │    │              │  │
│  │ JSON + CSV   │    │  REST API    │    │  WebGL 3D    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
MAP 디렉토리                    fab_data/                     브라우저
┌──────────┐                 ┌──────────┐                ┌──────────┐
│ M14A/    │  parse_layout   │ M14A/    │   FastAPI      │ Three.js │
│  *.zip   │ ──────────────▶ │  .json   │ ──────────▶    │ 3D 렌더링│
│ M14B/    │   XML → JSON    │  .csv    │  /layout_data  │          │
│  *.zip   │                 │ M14B/    │  .json         │ 60 FPS   │
│ M16A/    │                 │  .json   │                │ WebGL    │
│  *.zip×3 │                 │  .csv    │                │          │
│ M16B/    │                 │ M16B/    │                │          │
│  *.zip   │                 │  .json   │                │          │
└──────────┘                 └──────────┘                └──────────┘
```

---

## 파일 구성

```
OHT_3D/
├── parse_layout.py        # XML 파서 (853줄)
├── server.py              # FastAPI 웹 서버 (892줄)
├── oht_3d_layout.html     # Three.js 3D UI (2,582줄)
├── AAAA.TXT               # 사용법 문서
├── LAYOUT_3D_V0.2.zip     # 샘플 layout.xml + 코드 원본
├── DEV_DOCUMENT.md        # 본 개발 문서
└── fab_data/              # [자동 생성] FAB별 파싱 결과
    ├── _fab_settings.json  # FAB별 설정 (OHT 대수 등)
    ├── _fab_registry.json  # FAB 메타데이터
    ├── M14A/
    │   ├── M14A.json       # 3D 시각화 데이터
    │   └── master_csv/
    │       └── M14A_HID_Zone_Master.csv
    ├── M14B/
    │   └── ...
    └── M16A-A/
        └── ...
```

---

## 1. parse_layout.py - XML 파서

### 핵심 기능
대용량 layout.xml (200MB+)을 메모리 효율적으로 파싱하여 JSON + CSV 생성.

### 함수 목록

| 함수 | 목적 | 입력 | 출력 |
|------|------|------|------|
| `parse_layout_xml()` | 핵심 파서: XML → JSON + CSV | xml_path, output_dir, fab_name | {fab_name}.json, CSV |
| `parse_from_zip()` | ZIP에서 layout.xml 추출 후 파싱 | zip_path, output_dir, fab_name | JSON + CSV |
| `scan_and_parse_map()` | MAP 디렉토리 전체 스캔 | map_dir, output_base_dir | 전체 FAB 파싱 |
| `auto_detect_and_parse()` | 자동 감지 모드 (인자 없이 실행) | base_dir (선택) | 자동 탐지 후 파싱 |
| `_find_layout_zips()` | 디렉토리에서 layout ZIP 탐색 | dir_path | ZIP 파일 목록 |

### XML 파싱 대상 데이터

```
layout.xml
├── AddressInfo (노드)
│   ├── id, x, y 좌표
│   ├── symbol (직진/곡선/분기/합류)
│   ├── is_station, branch, junction 플래그
│   └── 연결 정보 (다음 노드, 거리, 속도)
├── StationInfo (스테이션)
│   ├── port_id, category, type
│   └── 연결 노드 위치
├── McpZoneInfo (MCP Zone)
│   ├── vehicle_max, vehicle_precaution
│   └── IN/OUT lane 정보
└── HidZoneInfo (HID Zone)
    ├── HID Zone ID, 이름
    └── 소속 MCP Zone 매핑
```

### 출력 JSON 구조

```json
{
  "fab_name": "M14A",
  "project": "FAB Layout",
  "total_nodes": 45000,
  "total_edges": 52000,
  "total_stations": 3200,
  "total_mcp_zones": 85,
  "bounds": { "min_x": 0, "max_x": 80000, "min_y": 0, "max_y": 40000 },
  "nodes": [
    { "id": 1, "x": 1234.5, "y": 5678.9, "symbol": "straight",
      "is_station": true, "stations": [...], "connections": [...] }
  ],
  "edges": [
    { "from": 1, "to": 2, "distance": 150, "speed": 2000 }
  ],
  "stations": [...],
  "mcp_zones": [...],
  "hid_zones": [...]
}
```

### 사용법

```bash
# 자동 감지 (권장)
python parse_layout.py

# MAP 디렉토리 지정
python parse_layout.py --scan /path/to/MAP

# 단일 ZIP
python parse_layout.py layout.zip

# 단일 XML (레거시)
python parse_layout.py layout.xml . M14A
```

### 자동 감지 탐색 순서

```
1순위: 하위 폴더에 layout.xml 포함 ZIP → MAP 구조로 스캔
2순위: 현재 폴더에 layout.xml 포함 ZIP → 각각 파싱
3순위: 현재 폴더에 layout.xml → 직접 파싱
4순위: 형제 폴더에서 MAP 구조 탐색
```

### ZIP 파일 탐색 우선순위 (`_find_layout_zips`)

```
1순위: *.layout.zip 패턴
2순위: 모든 *.zip 열어서 layout.xml 포함 여부 확인
       (LAYOUT/LAYOUT.XML 같은 하위 폴더 구조도 지원)
```

---

## 2. server.py - FastAPI 웹 서버

### 서버 설정

| 항목 | 값 |
|------|------|
| 프레임워크 | FastAPI + uvicorn |
| 포트 | 10003 |
| CORS | 전체 허용 (`*`) |
| CSV 저장 간격 | 10초 |
| OUTPUT 정리 간격 | 600초 (10분) |

### API 엔드포인트 전체 목록

#### 페이지 서빙

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 메인 3D 시각화 페이지 |
| GET | `/oht_3d_layout.html` | 3D 페이지 직접 접근 |

#### 레이아웃 데이터

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/layout_data.json` | 현재 FAB JSON 데이터 (캐시 비활성화) |
| GET | `/api/layout` | 레이아웃 요약 정보 |
| GET | `/api/layout/nodes?limit=&offset=` | 노드 목록 (페이지네이션) |
| GET | `/api/layout/edges?limit=&offset=` | 엣지 목록 |
| GET | `/api/layout/stations` | 스테이션 목록 |
| GET | `/api/layout/mcp_zones` | MCP Zone 목록 |
| GET | `/api/layout/search?q=` | 노드/스테이션 검색 |

#### Multi-FAB 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/fabs` | 등록된 FAB 목록 + 현재 FAB |
| POST | `/api/fab/switch` | FAB 전환 `{fab_name: "M14B"}` |
| GET | `/api/fab/settings` | 현재 FAB 설정 조회 (OHT 대수) |
| POST | `/api/fab/settings` | FAB 설정 저장 `{oht_count: 200}` |

#### XML 파싱

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/parse` | XML 파일 경로 지정 파싱 |
| POST | `/api/parse/upload` | XML 파일 업로드 파싱 |
| POST | `/api/parse/scan` | MAP 디렉토리 스캔 파싱 |

#### CSV 마스터 데이터

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/master` | FAB 마스터 데이터 목록 |
| GET | `/api/master/{fab}/csv/{file}` | CSV 파일 다운로드 |
| GET | `/api/master/{fab}/download_all` | FAB 전체 CSV 목록 |

#### 시뮬레이션

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/simulation/status` | 시뮬레이션 상태 |
| POST | `/api/simulation/start` | 시뮬레이션 시작 |
| POST | `/api/simulation/scenario` | 시나리오 생성 (JAM/정지/적재) |
| POST | `/api/simulation/reset` | 시뮬레이션 초기화 |
| GET | `/api/simulation/vehicles` | 차량 목록 |
| GET | `/api/simulation/vehicle/{id}` | 차량 상세 |

#### 시스템

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/status` | 서버 상태 |
| GET | `/api/output/status` | OUTPUT 디렉토리 상태 |

### Multi-FAB 동작 구조

```
서버 시작
    │
    ▼
load_fab_registry()
    │  fab_data/ 스캔
    │  - 하위 디렉토리별 JSON 탐색
    │  - _fab_registry.json 메타데이터 보강
    ▼
switch_fab_internal(첫 번째 FAB)
    │  - layout_data 메모리 로드
    │  - current_fab_name 설정
    │  - current_fab_json 경로 설정
    ▼
서버 대기 (Port 10003)
    │
    ▼  [사용자 FAB 전환 요청]
POST /api/fab/switch {fab_name: "M14B"}
    │  - switch_fab_internal("M14B")
    │  - layout_data 교체
    ▼
GET /layout_data.json
    │  - current_fab_json 경로의 파일 반환
    │  - Cache-Control: no-cache
    ▼
브라우저 3D 렌더링
```

### FAB 설정 영구 저장

```json
// fab_data/_fab_settings.json
{
  "M14A": { "oht_count": 200 },
  "M14B": { "oht_count": 500 },
  "M16A-A": { "oht_count": 150 }
}
```

- OHT 대수 변경 시 자동 저장 (`POST /api/fab/settings`)
- FAB 전환 시 저장된 값 자동 복원
- 서버 재시작해도 유지

---

## 3. oht_3d_layout.html - Three.js 3D 시각화

### LLM 기반 3D 개발

본 시스템의 3D 시각화는 **LLM(대규모 언어 모델)**을 활용하여 개발되었습니다.

- **Three.js** 기반 WebGL 3D 렌더링
- **ES Module** 방식 (`<script type="module">`)
- **Import Map** 으로 Three.js CDN 로딩
- **단일 HTML 파일**에 CSS + JS + 3D 로직 통합 (2,582줄)

### UI 레이아웃

```
┌──────────────────────────────────────────────────────────────┐
│ [AMOS MAP SYSTEM PRO] [LIVE] [M14A] [▼ FAB선택] [이동]  FPS │
├──────┬─────────────────────────────────────┬─────────────────┤
│      │                                     │                 │
│ 좌측 │         3D 뷰포트 (Three.js)         │    우측 패널    │
│ 패널 │                                     │                 │
│      │  ┌─────────────┐                   │  [OHT차량|Zone] │
│ 통계 │  │ 플로팅 컨트롤 │                   │                 │
│ OHT  │  │ 높이/두께/뷰 │                   │  차량 리스트    │
│ 설정 │  │ 레이어/색상  │    ┌────┐         │  또는           │
│ 시뮬 │  └─────────────┘    │미니맵│         │  Zone 리스트    │
│      │                     └────┘         │                 │
├──────┴─────────────────────────────────────┴─────────────────┤
│ (사이드바 토글 버튼)                                          │
└──────────────────────────────────────────────────────────────┘
```

### 3D 오브젝트 구조

#### Scene 구성

| 그룹 | 오브젝트 | 렌더링 방식 |
|------|---------|------------|
| `floorGroup` | 바닥면 + 그리드 | PlaneGeometry |
| `supportGroup` | 지지 기둥 + 빔 | InstancedMesh |
| `railGroup` | 레일 트랙 (좌/우 레일 + 크로스 타이 + 베이스) | InstancedMesh |
| `nodeGroup` | 주소 노드 (구체) | InstancedMesh |
| `stationGroup` | 스테이션 마커 (팔면체) | InstancedMesh |
| `labelGroup` | 스테이션 ID 라벨 | Sprite |
| `vehicleGroup` | OHT 차량 | Group (복합 지오메트리) |
| `zoneLaneGroup` | HID Zone IN/OUT 레인 | Line |

#### OHT 차량 상세 모델

```
        ◆ 비콘 (Beacon) - 주황색 원통
        │
    ════╧════  캐리지 (Carriage) - 주황색 박스
    ●       ●  바퀴 (Wheels) × 2 - 회색 원통
    ┃  모터  ┃  모터 (Motor) - 진한 주황
    ┃       ┃  케이블 (Cables) × 2 - 회색 (하강/상승 시 길이 변화)
    ┗━━━━━━━┛  그리퍼 (Gripper) - 은색
    ┌───────┐
    │ FOUP  │  FOUP (반도체 웨이퍼 캐리어) - 흰색 (적재 시만 표시)
    └───────┘
    ○ 링 (Ring) - 노란색 토러스 (회전 애니메이션)
    ◉ 전방등 (노란색) + 후방등 (빨간색)
```

### 차량 상태 머신 (State Machine)

```
                    ┌──────────┐
          ┌────────▶│  moving   │◀────────┐
          │         └────┬─────┘         │
          │              │ 스테이션 도착   │
          │              ▼               │
          │         ┌──────────┐         │
          │         │ lowering │         │
          │         │ (케이블↓) │         │
          │         └────┬─────┘         │
          │              ▼               │
          │         ┌──────────┐         │
          │         │ waiting  │         │
          │         │ (2.5초)  │         │
          │         └────┬─────┘         │
          │              ▼               │
          │         ┌──────────┐         │
          └─────────│ raising  │         │
                    │ (케이블↑) │         │
                    └──────────┘         │
                                         │
                    ┌──────────┐         │
                    │   jam    │─────────┘
                    │(3초+자동 │  0.3%/프레임 확률로
                    │  복구)   │  자동 해제
                    └──────────┘
```

### Zone 혼잡도 시스템

```
OHT 수 vs Zone 임계값:

  정상 (Normal)     주의 (Warning)      포화 (Saturated)
├─────────────────┼──────────────────┼──────────────────▶
0            precaution(35)     vehicle_max(37)

속도 감소 공식:
  occupancy < 70%  → speedFactor = 1.0 (정상 속도)
  occupancy ≥ 70%  → speedFactor = max(0.3, 1.0 - (occupancy-70)/100)
```

### 성능 최적화

| 기법 | 설명 | 효과 |
|------|------|------|
| **InstancedMesh** | 레일/노드/기둥을 단일 드로우 콜로 렌더링 | 45,000+ 노드 처리 |
| **공간 인덱싱** | 그리드 기반 노드 탐색 (`_nodeGrid`) | O(1) 최근접 노드 검색 |
| **Zone 캐시** | 차량-Zone 매핑 1초/회 갱신 | CPU 부하 감소 |
| **Material 공유** | 차량 간 재질 공유 (복제 안 함) | 메모리 절약 |
| **이벤트 위임** | 리스트 클릭을 부모에서 처리 | DOM 이벤트 최소화 |
| **디바운싱** | 컨트롤 변경 지연 처리 | 불필요한 리빌드 방지 |

### 주요 JS 함수

| 함수 | 기능 |
|------|------|
| `boot()` | FAB 목록 조회 → 드롭다운 세팅 → init() 호출 |
| `init()` | Scene/Camera/Renderer 초기화, 데이터 로드, 3D 빌드 |
| `buildRails()` | 레일 트랙 InstancedMesh 생성 |
| `buildNodes()` | 노드 구체 InstancedMesh 생성 |
| `buildStationMarkers()` | 스테이션 마커 생성 |
| `buildPaths()` | 노드 그래프에서 차량 경로 추출 |
| `spawnVehicles(count)` | OHT 차량 생성 (상세 지오메트리) |
| `updateVehicles(dt)` | 매 프레임 차량 이동/상태 업데이트 |
| `updateZoneCheck()` | Zone별 차량 수 집계 + 혼잡도 계산 |
| `fullRebuild()` | 전체 3D 씬 재구성 |
| `drawMinimap()` | 우하단 미니맵 렌더링 |
| `focusVehicle(idx)` | 차량 선택 + 경로 시각화 + 카메라 이동 |
| `focusZone(zoneId)` | Zone 카메라 포커스 |
| `saveOhtSettings(count)` | OHT 대수 서버에 저장 |

---

## 4. MAP 디렉토리 구조

### 실제 FAB 구조

```
MAP/
├── M14A/           ← FAB M14A
│   └── A.layout.zip
│       └── LAYOUT/LAYOUT.XML      (200MB+)
├── M14B/           ← FAB M14B
│   └── A.layout.zip
│       └── LAYOUT/LAYOUT.XML
├── M16A/           ← FAB M16A (3개 서브시스템)
│   ├── A.layout.zip    → M16A-A
│   ├── BR.layout.zip   → M16A-BR
│   └── E.layout.zip    → M16A-E
└── M16B/           ← FAB M16B
    └── B.layout.zip
        └── LAYOUT/LAYOUT.XML
```

### 파싱 결과 (fab_data/)

```
fab_data/
├── _fab_registry.json      ← 전체 FAB 메타 정보
├── _fab_settings.json      ← FAB별 설정 (OHT 대수)
├── M14A/
│   ├── M14A.json           ← 3D 시각화 데이터
│   └── master_csv/
│       └── M14A_HID_Zone_Master.csv
├── M14B/
│   ├── M14B.json
│   └── master_csv/
│       └── M14B_HID_Zone_Master.csv
├── M16A-A/
│   ├── M16A-A.json
│   └── master_csv/
├── M16A-BR/
│   ├── M16A-BR.json
│   └── master_csv/
├── M16A-E/
│   ├── M16A-E.json
│   └── master_csv/
└── M16B/
    ├── M16B.json
    └── master_csv/
```

---

## 5. 실행 가이드

### 1단계: XML 파싱

```bash
cd OHT_3D

# 방법 A: 자동 감지 (MAP 폴더가 근처에 있을 때)
python parse_layout.py

# 방법 B: MAP 디렉토리 직접 지정
python parse_layout.py --scan /path/to/MAP

# 방법 C: 단일 ZIP 파일
python parse_layout.py /path/to/A.layout.zip
```

### 2단계: 서버 실행

```bash
python server.py
# 또는
uvicorn server:app --host 0.0.0.0 --port 10003 --reload
```

### 3단계: 브라우저 접속

```
http://localhost:10003
```

### FAB 전환

1. 헤더 드롭다운에서 FAB 선택
2. **[이동]** 버튼 클릭
3. 페이지 리로드 → 새 FAB 로딩 (로딩 화면에 FAB 이름 표시)

---

## 6. 기술 스택

| 구분 | 기술 | 버전/설명 |
|------|------|----------|
| **백엔드** | Python 3 | |
| | FastAPI | 비동기 웹 프레임워크 |
| | uvicorn | ASGI 서버 |
| | Pydantic | 데이터 검증 |
| **프론트엔드** | Three.js | r160+ (ES Module CDN) |
| | OrbitControls | 카메라 조작 |
| | HTML5 / CSS3 | 단일 파일 SPA |
| **데이터** | XML | layout.xml (iterparse) |
| | JSON | 3D 시각화 데이터 |
| | CSV | 마스터 데이터 |
| **개발 도구** | LLM | 3D 코드 생성 |
| | Git | 버전 관리 |

---

## 7. 주요 설계 결정

### 단일 HTML 파일 구조
- 배포 간소화: 서버가 HTML 1개만 서빙
- 의존성 최소화: Three.js CDN import map 사용
- LLM 생성에 적합: 단일 컨텍스트로 전체 UI 생성 가능

### InstancedMesh 렌더링
- 45,000+ 노드, 52,000+ 엣지를 개별 Mesh로 생성하면 성능 불가
- InstancedMesh로 단일 드로우 콜 → 60 FPS 유지

### FAB별 독립 디렉토리
- JSON과 CSV를 FAB별로 분리
- 서버 재시작 없이 FAB 전환
- 설정(OHT 대수) FAB별 영구 저장

### 브라우저 캐시 무효화
- `layout_data.json?t=timestamp` 매 요청마다 캐시 무시
- `Cache-Control: no-cache` 서버 응답 헤더
- FAB 전환 시 구 데이터 로딩 방지

---

## 8. 커밋 히스토리

| 커밋 | 내용 |
|------|------|
| `88cdcf5` | 초기 파일 업로드 |
| `3bf4342` | 다중 FAB 지원: ZIP 파싱, FAB 전환 API, FAB 선택 UI |
| `718da09` | parse_layout.py 자동 감지 모드 |
| `acd342e` | FAB별 독립 디렉토리 구조 + CSV/JSON 분리 |
| `3bbd598` | FAB별 OHT 대수 설정 영구 저장 |
| `99eaea1` | ZIP 탐색 로직 강화 (일반 *.zip 지원) |
| `b9632a7` | FAB 선택 오버레이 제거, 기본 FAB 바로 로딩 |
| `d831999` | FAB 드롭다운 [이동] 버튼 추가 |
| `e269e4b` | onFabGo window 바인딩 (module scope 수정) |
| `476fac4` | 이동 버튼 가드 제거 |
| `97414d4` | 브라우저 캐시 문제 해결 |
| `1fc67f6` | 로딩 화면 FAB 이름 표시 |
