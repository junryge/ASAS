---
name: weekly-report
tags: 주간보고, weekly, report, PPT, 금주실적, 차주계획
category: document
description: "주간보고 PPT 생성. 금주 실적과 차주 계획을 python-pptx로 PPT 변환"
date: 2026-04-13
---

# 주간보고 PPT 생성

## 실행 방법 (반드시 이 순서대로)

### Step 1: JSON 데이터 파일 생성
개인 지식의 주간보고 데이터를 아래 형식의 JSON 파일로 저장한다.

```json
[
    {
        "name": "smartATLAS",
        "current": [
            {"content": "▶ 업무1\n   1) 상세\n     ▶세부", "date": "4/22", "progress": "97%"},
            {"content": "▶ 업무2\n   1) 상세\n     ▶세부", "date": "4/08", "progress": "100%"}
        ],
        "next": [
            {"content": "▶ 계획1\n   1) 상세\n     ▶세부", "date": "4/22", "progress": "98%"}
        ],
        "issues": ""
    }
]
```

### Step 2: 스크립트 실행
```bash
python scientific-skills/weekly-report/scripts/gen_pptx.py data.json smartATLAS_주간보고_20260408.pptx
```

## 중요 규칙
1. **gen_pptx.py 스크립트를 절대 수정하지 말 것**
2. **Python 코드를 새로 작성하지 말 것** - 기존 스크립트를 실행만 할 것
3. JSON 데이터 파일만 생성하면 됨
4. 프로젝트가 여러 개면 JSON 배열에 추가
5. 상태 기호: ▶ 진행중 (고정)
6. 파일명: {프로젝트명}_주간보고_{YYYYMMDD}.pptx

## JSON 데이터 필드 설명
- `name`: 프로젝트명
- `current`: 금주 실적 배열
  - `content`: 추진 내용 (줄바꿈은 \n)
  - `date`: 납기 (예: "4/22")
  - `progress`: 진척율 (예: "97%")
- `next`: 차주 계획 배열 (current와 동일 구조)
- `issues`: Issue 및 협의사항 (문자열, 없으면 "")
