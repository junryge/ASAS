---
name: weekly-report
tags: 주간보고, weekly, report, PPT, 금주실적, 차주계획
category: document
description: "주간보고 PPT 생성. 금주 실적과 차주 계획을 PPT로 변환"
date: 2026-04-13
---

# 주간보고 PPT 생성

## 중요 규칙
1. **python-pptx 코드를 직접 작성하지 말 것**
2. 반드시 `/api/weekly-report/generate` API를 호출할 것
3. 개인 지식에서 주간보고 데이터를 읽어서 JSON으로 변환 후 API 호출

## 사용법

사용자가 "주간보고 PPT 만들어줘" 요청 시:

### Step 1: 개인 지식에서 데이터 추출
지식 검색 결과의 CSV 데이터를 아래 JSON 형식으로 변환

### Step 2: API 호출
```
POST /api/weekly-report/generate
Content-Type: application/json

{
    "filename": "smartATLAS_주간보고_20260408.pptx",
    "projects": [
        {
            "name": "smartATLAS",
            "current": [
                {"content": "▶ 업무제목\n   1) 상세내용\n     ▶세부사항", "date": "4/22", "progress": "97%"}
            ],
            "next": [
                {"content": "▶ 계획제목\n   1) 상세내용\n     ▶세부사항", "date": "4/22", "progress": "98%"}
            ],
            "issues": ""
        }
    ]
}
```

### Step 3: 다운로드 URL 제공
API 응답의 `download_url`을 사용자에게 제공

## JSON 필드 설명
- `name`: 프로젝트명
- `current`: 금주 실적 배열
  - `content`: 추진 내용 (줄바꿈은 \n, ▶ 접두사 사용)
  - `date`: 납기 (예: "4/22")
  - `progress`: 진척율 (예: "97%")
- `next`: 차주 계획 배열 (current와 동일 구조)
- `issues`: Issue 및 협의사항 (없으면 "")

## 상태 기호
- ▶ 진행중 (고정)

## 파일명 형식
{프로젝트명}_주간보고_{YYYYMMDD}.pptx
