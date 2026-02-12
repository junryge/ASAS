# HTML-JSON Parser Tool 사용 설명서

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [폴더 구조](#2-폴더-구조)
3. [데이터 흐름도](#3-데이터-흐름도)
4. [JSON 스키마](#4-json-스키마)
5. [각 파일별 상세 설명](#5-각-파일별-상세-설명)
6. [실행 방법](#6-실행-방법)
7. [사용 시나리오](#7-사용-시나리오)
8. [3D 캠퍼스 맵 도구](#8-3d-캠퍼스-맵-도구)
9. [커스터마이징 가이드](#9-커스터마이징-가이드)

---

## 1. 프로젝트 개요

SK Hynix 스타일의 인터랙티브 HTML 레이아웃을 **파싱(HTML→JSON)** 하고, **편집** 한 후, **재생성(JSON→HTML)** 할 수 있는 양방향 변환 도구입니다.

| 기능 | 설명 |
|------|------|
| HTML → JSON 파싱 | HTML 파일에서 메타데이터, CSS 변수, 컴포넌트, 플로우 다이어그램, JS 데이터 추출 |
| JSON 편집 | 브라우저 UI에서 섹션/컴포넌트/플로우 노드를 시각적으로 편집 |
| JSON → HTML 생성 | JSON 데이터에서 완전한 독립형 HTML 페이지 재생성 |
| 3D 캠퍼스 맵 | Three.js 기반 3D 빌딩 배치 및 시각화 도구 |

---

## 2. 폴더 구조

```
html_json_parser/
│
├── parse_layout.py        # [핵심] HTML → JSON 파서 엔진 (Python)
├── run_parser.py           # CLI 실행 도구
├── json_to_html.py         # JSON → HTML 생성 모듈 (Python)
├── tool_ui.html            # 브라우저 올인원 UI (4탭)
├── 3d_campus_map.html      # Three.js 3D 캠퍼스 맵 도구
│
└── output/                 # 출력 폴더 (자동 생성)
    ├── *.json              # 파싱된 JSON 결과
    └── *.html              # 재생성된 HTML
```

### 파일별 역할 요약

| 파일 | 라인 수 | 역할 | 실행 환경 |
|------|--------|------|----------|
| `parse_layout.py` | 593줄 | HTML 파싱 핵심 엔진 | Python 3.x |
| `run_parser.py` | 196줄 | CLI 명령어 도구 | Python 3.x (터미널) |
| `json_to_html.py` | 415줄 | HTML 재생성 모듈 | Python 3.x |
| `tool_ui.html` | 1,113줄 | 웹 기반 올인원 도구 | 브라우저 (서버 불필요) |
| `3d_campus_map.html` | 817줄 | 3D 맵 에디터 | 브라우저 (Three.js CDN) |

---

## 3. 데이터 흐름도

```
  ┌──────────────────┐
  │  원본 HTML 파일    │   예: SK_Hynix_3D_Campus_0.4V.HTML
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │  parse_layout.py             │   Python 파서
  │  (HTMLLayoutParser 클래스)    │
  │                              │
  │  추출 항목:                   │
  │  • metadata (제목, 언어)      │
  │  • css_variables (색상 등)    │
  │  • css_classes               │
  │  • components (카드, 섹션)    │
  │  • flow_diagram (노드, 화살표)│
  │  • js_data_objects (details)  │
  │  • text_content              │
  │  • statistics (통계)          │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────┐
  │  JSON 데이터       │   구조화된 중간 포맷
  └──┬─────┬─────┬───┘
     │     │     │
     │     │     ▼
     │     │   tool_ui.html (탭2)
     │     │   브라우저에서 시각적 편집
     │     │     │
     │     │     ▼
     │     │   편집된 JSON
     │     │     │
     ▼     ▼     ▼
  ┌──────────────────────────────┐
  │  json_to_html.py             │   Python 생성기
  │  (HTMLGenerator 클래스)       │
  │  또는                         │
  │  tool_ui.html (탭3)           │   브라우저 생성기
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────┐
  │  생성된 HTML 파일  │   독립형 인터랙티브 HTML
  └──────────────────┘
```

---

## 4. JSON 스키마

`parse_layout.py`가 생성하는 JSON의 전체 구조입니다.

```json
{
  "source_file": "SK_Hynix_3D_Campus_0.4V.HTML",
  "file_size_bytes": 12345,

  "metadata": {
    "lang": "ko",
    "title": "SK Hynix 3D Campus 0.4V",
    "meta_tags": [
      { "charset": "UTF-8" },
      { "name": "viewport", "content": "width=device-width, initial-scale=1.0" }
    ],
    "external_links": [
      "https://fonts.googleapis.com/css2?family=Noto+Sans+KR..."
    ],
    "external_scripts": []
  },

  "css_variables": {
    "bg": "#0a0e1a",
    "card": "#111827",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "blue": "#3b82f6",
    "cyan": "#06b6d4",
    "purple": "#8b5cf6",
    "amber": "#f59e0b",
    "emerald": "#10b981",
    "rose": "#f43f5e",
    "orange": "#f97316"
  },

  "css_classes": [
    "comp-card", "comp-emoji", "comp-name", "comp-full",
    "fab-section", "fab-header", "fab-name", "fab-badge",
    "flow-node", "flow-arrow", "flow-diagram",
    "detail-panel", "detail-header", "detail-body"
  ],

  "components": {
    "cards": [
      {
        "category": "oht",
        "name": "OHT",
        "full_name": "Overhead Hoist Transport",
        "emoji": "🚟"
      },
      {
        "category": "mcs",
        "name": "MCS",
        "full_name": "Material Control System",
        "emoji": "🖥️"
      }
    ],
    "sections": [
      {
        "name": "3D NAND FAB",
        "badge": "128 Layer",
        "components": ["oht", "mcs", "stk", "lft"]
      },
      {
        "name": "DRAM FAB",
        "badge": "1α nm",
        "components": ["cnv", "inv", "que", "rtc"]
      }
    ]
  },

  "flow_diagram": {
    "title": "FOUP 반송 흐름",
    "nodes": [
      { "type": "foup", "main_text": "FOUP",      "sub_label": "25 wafers" },
      { "type": "stk",  "main_text": "STK",       "sub_label": "Storage" },
      { "type": "oht",  "main_text": "OHT",       "sub_label": "Transport" },
      { "type": "fio",  "main_text": "Load Port", "sub_label": "EQ I/F" }
    ],
    "arrow_count": 3
  },

  "js_data_objects": {
    "details": {
      "oht": {
        "emoji": "🚟",
        "name": "OHT",
        "full": "Overhead Hoist Transport",
        "color": "#3b82f6",
        "items": [
          { "label": "설명",     "value": "천장 레일 위를 주행하는 반송 장치" },
          { "label": "주요 역할", "value": "장비 간 FOUP 운반" },
          { "label": "핵심 사양", "value": "최대 속도 6m/s, 하중 12kg" }
        ]
      },
      "mcs": {
        "emoji": "🖥️",
        "name": "MCS",
        "full": "Material Control System",
        "color": "#8b5cf6",
        "items": [
          { "label": "설명",     "value": "중앙 물류 제어 서버" },
          { "label": "주요 역할", "value": "반송 스케줄링 및 최적화" }
        ]
      }
    },
    "_functions": [
      { "name": "showDetail", "params": "cat" }
    ]
  },

  "text_content": [
    { "type": "h1", "text": "SK Hynix 3D Campus 0.4V" },
    { "type": "p",  "text": "AMHS 시스템 아키텍처" }
  ],

  "statistics": {
    "total_css_variables": 11,
    "total_css_classes": 14,
    "total_components": 8,
    "total_sections": 2,
    "total_flow_nodes": 4,
    "total_js_objects": 2,
    "total_text_items": 2,
    "html_size_bytes": 12345
  }
}
```

### 카테고리 → 색상 매핑

| 카테고리 ID | 이름 | 색상 |
|------------|------|------|
| `oht` | Overhead Hoist Transport | `blue` (#3b82f6) |
| `mcs` | Material Control System | `purple` (#8b5cf6) |
| `stk` | Stocker | `emerald` (#10b981) |
| `cnv` | Conveyor | `sky` (#0ea5e9) |
| `lft` | Lifter | `orange` (#f97316) |
| `inv` | Inventory Manager | `rose` (#f43f5e) |
| `que` | Queue Manager | `amber` (#f59e0b) |
| `rtc` | Route Controller | `purple` (#a78bfa) |
| `foup` | Front Opening Unified Pod | `emerald` (#34d399) |
| `pdt` | PDT | `orange` (#fb923c) |
| `fio` | Load Port I/F | `gray` (#94a3b8) |

---

## 5. 각 파일별 상세 설명

### 5.1 parse_layout.py (HTML → JSON 파서)

핵심 파서 엔진입니다. `HTMLLayoutParser` 클래스가 HTML 파일을 읽어 구조화된 JSON으로 변환합니다.

#### 클래스 구조

```python
class HTMLLayoutParser:
    def __init__(self, html_path: str)    # HTML 파일 경로로 초기화
    def parse(self) -> dict               # 전체 파싱 실행, 결과 딕셔너리 반환
    def save_json(self, output_path: str)  # JSON 파일로 저장
    def to_json_string(self) -> str        # JSON 문자열 반환
```

#### 내부 추출 메서드

| 메서드 | 추출 대상 | 파싱 방법 |
|--------|----------|----------|
| `_extract_metadata()` | title, lang, meta 태그, 외부 링크 | 정규표현식 + HTMLParser |
| `_extract_css_variables()` | `:root { --변수: 값 }` | 정규표현식 |
| `_extract_css_classes()` | `<style>` 내 CSS 클래스명 | 정규표현식 |
| `_extract_layout_structure()` | DOM 계층 구조 트리 | `_StructureParser` (HTMLParser 서브클래스) |
| `_extract_components()` | `.comp-card[data-cat]`, `.fab-section` | HTMLParser + data 속성 |
| `_extract_flow_diagram()` | `.flow-node`, `.flow-arrow` | HTMLParser |
| `_extract_js_data()` | `<script>` 내 JS 객체/함수 | 정규표현식 + 중괄호 매칭 |
| `_extract_text_content()` | h1~h6, p 태그 텍스트 | HTMLParser |

#### 사용 예시

```python
from parse_layout import HTMLLayoutParser

parser = HTMLLayoutParser("SK_Hynix_3D_Campus_0.4V.HTML")
result = parser.parse()

# 개별 데이터 접근
print(result["metadata"]["title"])           # 페이지 제목
print(result["components"]["cards"])          # 컴포넌트 카드 목록
print(result["flow_diagram"]["nodes"])        # 플로우 노드
print(result["css_variables"]["blue"])        # CSS 변수값
print(result["js_data_objects"]["details"])   # JS 상세 데이터

# JSON 저장
parser.save_json("output/result.json")
```

---

### 5.2 run_parser.py (CLI 도구)

터미널에서 실행하는 명령어 도구입니다.

```bash
# 기본 사용법 - 파일 하나 파싱
python3 run_parser.py SK_Hynix_3D_Campus_0.4V.HTML

# 출력 경로 지정
python3 run_parser.py input.html -o output/my_result.json

# 특정 섹션만 추출
python3 run_parser.py input.html --sections components,flow_diagram

# 폴더 내 HTML 일괄 파싱
python3 run_parser.py --dir ./html_files/

# 통계만 출력 (파일 저장 안 함)
python3 run_parser.py input.html --summary
```

#### CLI 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `<파일경로>` | 파싱할 HTML 파일 | `input.html` |
| `-o`, `--output` | JSON 출력 경로 | `-o result.json` |
| `--dir` | 폴더 일괄 처리 | `--dir ./htmls/` |
| `--sections` | 추출할 섹션 필터 | `--sections components,css_variables` |
| `--summary` | 통계만 출력 | `--summary` |

---

### 5.3 json_to_html.py (JSON → HTML 생성기)

JSON 데이터에서 SK Hynix 스타일의 인터랙티브 HTML 페이지를 생성합니다.

#### 클래스 구조

```python
class HTMLGenerator:
    def __init__(self, data: dict = None)                     # JSON 딕셔너리로 초기화
    def load_json(self, json_path: str)                       # JSON 파일 로드
    def generate(self, title="", theme=None) -> str           # HTML 문자열 생성
    def save(self, output_path: str, title="", theme=None)    # HTML 파일 저장
```

#### 생성되는 HTML 구조

```
<!DOCTYPE html>
<html>
  <head>
    ├── CSS (변수, 리셋, 그리드, 애니메이션)
    └── Google Fonts (Noto Sans KR, JetBrains Mono)
  </head>
  <body>
    <div class="container">
      ├── header (배지 + 그라데이션 제목 + 부제목)
      ├── amos-wrapper
      │   └── fab-grid
      │       ├── fab-section (섹션 1)
      │       │   └── comp-grid (컴포넌트 카드들)
      │       └── fab-section (섹션 2)
      │           └── comp-grid
      ├── detail-panel (클릭 시 펼쳐지는 상세 패널)
      ├── flow-section (플로우 다이어그램)
      └── footer
    </div>
    <script> (showDetail 함수 + details 데이터) </script>
  </body>
</html>
```

#### 사용 예시

```python
from json_to_html import HTMLGenerator

# JSON 파일에서 로드 → HTML 생성
gen = HTMLGenerator()
gen.load_json("output/SK_Hynix_3D_Campus_0.4V.json")
gen.save("output/regenerated.html")

# 딕셔너리에서 직접 생성
data = {
    "metadata": { "title": "My Layout", "lang": "ko" },
    "css_variables": { "bg": "#0a0e1a", "blue": "#3b82f6" },
    "components": {
        "cards": [
            { "category": "oht", "name": "OHT", "full_name": "Overhead Hoist", "emoji": "🚟" }
        ],
        "sections": []
    }
}
gen = HTMLGenerator(data)
html = gen.generate(title="My Layout")

# 테마 변경
gen.save("output/light_theme.html", theme={
    "bg": "#ffffff",
    "card": "#f8fafc",
    "text": "#1e293b",
    "border": "#e2e8f0"
})
```

#### 지원 테마

| 테마 | 배경색 | 카드색 | 텍스트색 |
|------|--------|--------|---------|
| 다크 (기본) | `#0a0e1a` | `#111827` | `#e2e8f0` |
| 라이트 | `#f8fafc` | `#ffffff` | `#1e293b` |
| SK Hynix 블루 | `#0c1222` | `#0f1a2e` | `#e2e8f0` |
| SK Hynix 그린 | `#0a1a0e` | `#0f2816` | `#e2e8f0` |

---

### 5.4 tool_ui.html (브라우저 올인원 도구)

서버 없이 브라우저에서 바로 사용하는 4탭 UI 도구입니다.

#### 탭 구성

```
┌─────────────────────────────────────────────────────────────┐
│  [HTML→JSON 파싱]  [JSON 편집기]  [JSON→HTML 생성]  [미리보기] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                      (현재 탭 내용)                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 탭 1: HTML → JSON 파싱

| 기능 | 설명 |
|------|------|
| 파일 업로드 | 드래그&드롭 또는 클릭으로 HTML 파일 업로드 |
| 직접 입력 | textarea에 HTML 코드 붙여넣기 |
| 샘플 로드 | SK Hynix FOUP 예제 HTML 자동 입력 |
| 파싱 실행 | DOMParser로 클라이언트 측 파싱 (서버 불필요) |
| 통계 표시 | CSS 변수, 클래스, 컴포넌트, 섹션, 플로우 노드 수 |
| JSON 트리 | 구문 강조된 JSON 트리 뷰 |
| 복사/다운로드 | JSON 클립보드 복사 또는 .json 파일 다운로드 |

#### 탭 2: JSON 편집기

| 영역 | 편집 가능 항목 |
|------|---------------|
| 메타데이터 | 페이지 제목, 언어(ko/en), 상단 배지 텍스트, 부제목 |
| 섹션 | 섹션 추가/삭제, 섹션명, 배지 텍스트 |
| 컴포넌트 | 이모지, 카테고리 ID, 이름, 전체 이름 추가/삭제 |
| 플로우 | 플로우 제목, 노드(main_text, sub_label) 추가/삭제 |
| 상세 데이터 | JS details 객체 JSON 직접 편집 |

#### 탭 3: JSON → HTML 생성

| 기능 | 설명 |
|------|------|
| 테마 선택 | 다크 / 라이트 / SK Hynix 블루 / SK Hynix 그린 |
| 파일명 설정 | 다운로드 시 파일명 지정 |
| JSON 입력 | 자동 채워지거나 수동 입력/수정 |
| HTML 생성 | JSON → 완전한 독립형 HTML 코드 생성 |
| 복사/다운로드/미리보기 | 생성된 HTML 활용 |

#### 탭 4: 미리보기

생성된 HTML을 iframe에서 실시간 미리보기합니다.

---

## 6. 실행 방법

### 방법 A: 브라우저에서 바로 열기 (가장 간단)

```
파일 탐색기에서 더블클릭:

  html_json_parser/tool_ui.html          ← HTML↔JSON 파서 UI
  html_json_parser/3d_campus_map.html    ← 3D 캠퍼스 맵 도구
```

### 방법 B: 로컬 서버 실행 (추천 - 3D 맵에 안정적)

```bash
cd html_json_parser

# Python 내장 서버
python3 -m http.server 8501
```

브라우저에서 접속:
- `http://localhost:8501/tool_ui.html` → HTML↔JSON 파서
- `http://localhost:8501/3d_campus_map.html` → 3D 맵

### 방법 C: Python CLI

```bash
cd html_json_parser

# HTML → JSON 파싱
python3 run_parser.py ../SK_Hynix_3D_Campus_0.4V.HTML

# JSON → HTML 생성
python3 -c "
from json_to_html import HTMLGenerator
gen = HTMLGenerator()
gen.load_json('output/SK_Hynix_3D_Campus_0.4V.json')
gen.save('output/regenerated.html')
"
```

---

## 7. 사용 시나리오

### 시나리오 1: 기존 HTML 분석 및 수정

```
1. tool_ui.html 열기
2. [탭1] HTML 파일 드래그&드롭
3. [탭1] 파싱 실행 → JSON 결과 확인
4. [탭2] 컴포넌트 이름/이모지 수정, 섹션 추가
5. [탭2] "편집 내용 적용" 클릭
6. [탭3] "HTML 생성" 클릭
7. [탭4] 미리보기 확인
8. [탭3] "HTML 다운로드" 클릭
```

### 시나리오 2: 새 레이아웃 처음부터 만들기

```
1. tool_ui.html 열기
2. [탭2] 메타데이터 입력 (제목, 배지 등)
3. [탭2] 섹션 추가 (예: "3D NAND FAB")
4. [탭2] 컴포넌트 추가 (OHT, MCS, STK 등)
5. [탭2] 플로우 노드 추가
6. [탭2] 상세 데이터 JSON 입력
7. [탭2] "편집 내용 적용" 클릭
8. [탭3] 테마 선택 → "HTML 생성"
9. [탭3] 다운로드
```

### 시나리오 3: Python 스크립트로 일괄 처리

```python
import os
from parse_layout import HTMLLayoutParser
from json_to_html import HTMLGenerator

# 여러 HTML 일괄 파싱
for fname in os.listdir("./html_files"):
    if fname.endswith(".html"):
        parser = HTMLLayoutParser(f"./html_files/{fname}")
        result = parser.parse()
        parser.save_json(f"./output/{fname.replace('.html', '.json')}")

# JSON 수정 후 재생성
import json
with open("output/result.json") as f:
    data = json.load(f)

data["metadata"]["title"] = "수정된 제목"
data["components"]["cards"].append({
    "category": "new",
    "name": "NEW",
    "full_name": "새 컴포넌트",
    "emoji": "🆕"
})

gen = HTMLGenerator(data)
gen.save("output/modified.html")
```

---

## 8. 3D 캠퍼스 맵 도구

### 화면 구성

```
┌──────────┬──────────────────────────────┬──────────┐
│          │                              │          │
│  좌측     │        3D 뷰포트              │  우측     │
│  빌딩목록  │        (Three.js)             │  속성편집  │
│          │                              │          │
│  M10     │    ┌────┐    ┌─────────┐     │  이름     │
│  M11     │    │M10 │    │  M14    │     │  유형     │
│  M14 ◀   │    └────┘    └─────────┘     │  색상     │
│  M15     │         ┌───────┐            │  위치 XYZ │
│  M16 HUB │         │ HUB   │            │  크기 WHD │
│          │         └───────┘            │  층수     │
│ ──────── │                              │  설명     │
│ 프리셋    │  [퍼스] [탑] [정면] [측면]     │          │
│ • 이천    │  [그리드] [라벨] [리셋]        │  [복제]   │
│ • 청주    │                              │  [삭제]   │
│ ──────── │                              │          │
│ [HTML]   │                              │          │
│ [JSON]   │                              │          │
└──────────┴──────────────────────────────┴──────────┘
```

### 마우스 조작

| 조작 | 기능 |
|------|------|
| 마우스 드래그 | 카메라 회전 |
| 스크롤 | 줌 인/아웃 (범위: 10~200) |
| Shift + 드래그 | 카메라 이동 (패닝) |
| 클릭 | 빌딩 선택 |

### 뷰 모드

| 모드 | 설명 |
|------|------|
| 퍼스펙티브 | 기본 3D 시점 (45° 각도) |
| 탑뷰 | 위에서 내려다보는 평면도 |
| 정면 | 정면에서 보는 입면도 |
| 측면 | 측면에서 보는 입면도 |

### 빌딩 유형

| 유형 | 설명 |
|------|------|
| `fab` | 제조동 (FAB) |
| `office` | 사무동 |
| `hub` | HUB (물류/AMHS) |
| `cleanroom` | 클린룸 |
| `utility` | 유틸리티 동 |
| `parking` | 주차장 |
| `other` | 기타 |

### 내장 프리셋

#### SK Hynix 이천 캠퍼스 (9동)

| 빌딩 | 유형 | 크기 (W×D×H) | 층수 | 색상 |
|------|------|-------------|------|------|
| M10 | FAB | 25×18×10 | 4F | 블루 |
| M11 | FAB | 25×18×10 | 4F | 시안 |
| M14 | FAB | 30×20×12 | 5F | 퍼플 |
| M15 | FAB | 28×18×11 | 4F | 앰버 |
| M16 HUB | HUB | 18×12×8 | 3F | 오렌지 |
| M16A | FAB | 22×16×10 | 4F | 에메랄드 |
| M16E | FAB | 22×16×10 | 4F | 틸 |
| R&D Center | 사무동 | 20×14×6 | 3F | 그레이 |
| Utility | 유틸리티 | 12×10×5 | 2F | 슬레이트 |

#### SK Hynix 청주 캠퍼스 (5동)

| 빌딩 | 유형 | 크기 (W×D×H) | 층수 | 색상 |
|------|------|-------------|------|------|
| C2 | FAB | 28×20×12 | 5F | 블루 |
| C2F | FAB | 28×20×12 | 5F | 시안 |
| C3 | FAB | 30×22×14 | 5F | 퍼플 |
| CJ PKG | FAB | 24×18×10 | 4F | 앰버 |
| CJ PRB | FAB | 20×16×9 | 3F | 에메랄드 |

### 내보내기 형식

#### JSON 내보내기

```json
{
  "version": "1.0",
  "name": "SK Hynix 3D Campus",
  "buildings": [
    {
      "name": "M14",
      "type": "fab",
      "x": 20, "y": 0, "z": -20,
      "width": 30, "height": 12, "depth": 20,
      "color": "#8b5cf6",
      "floors": 5,
      "description": "M14 FAB - 510 컬럼"
    }
  ],
  "camera": {
    "theta": 0.785,
    "phi": 1.047,
    "distance": 80,
    "target": { "x": 0, "y": 0, "z": 0 }
  }
}
```

#### HTML 내보내기

독립형 Three.js HTML 파일로 내보내집니다. 별도 파일 의존성 없이 브라우저에서 바로 실행됩니다.

---

## 9. 커스터마이징 가이드

### CSS 변수 커스텀

`json_to_html.py`의 `DEFAULT_COLORS`를 수정하거나, JSON의 `css_variables`를 변경:

```python
# json_to_html.py 수정
DEFAULT_COLORS = {
    "bg": "#ffffff",        # 배경색 변경
    "card": "#f8fafc",      # 카드 배경
    "text": "#1e293b",      # 텍스트 색
    "blue": "#0078d4",      # 포인트 색 (SK Hynix 브랜드)
}
```

### 새 카테고리 추가

```python
# json_to_html.py 수정
CATEGORY_COLORS = {
    "oht": "blue",
    "mcs": "purple",
    # ... 기존 항목
    "agv": "#e11d48",       # 새 카테고리 추가
    "amr": "#7c3aed",
}
```

### 3D 맵 빌딩 프리셋 추가

`3d_campus_map.html`의 `loadPreset()` 함수 내 `presets` 객체에 추가:

```javascript
const presets = {
    // ... 기존 프리셋
    my_campus: [
        { name: 'Building A', type: 'fab', x: 0, z: 0,
          width: 30, depth: 20, height: 12, floors: 4,
          color: '#3b82f6', description: 'Main FAB' },
        // ... 추가 빌딩
    ],
};
```

---

## 의존성

| 항목 | 버전 | 용도 |
|------|------|------|
| Python | 3.x | parse_layout.py, json_to_html.py, run_parser.py |
| 브라우저 | Chrome/Edge/Firefox | tool_ui.html, 3d_campus_map.html |
| Three.js | r128 (CDN) | 3D 캠퍼스 맵 렌더링 |
| Google Fonts | - | Noto Sans KR, JetBrains Mono |

> Python 외부 라이브러리 설치 불필요 (표준 라이브러리만 사용)
> 브라우저 도구는 인터넷 연결 필요 (CDN 폰트/Three.js)
