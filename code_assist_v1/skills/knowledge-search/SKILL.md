---
name: knowledge-search
description: "도메인 지식 검색. code_assist_v1/knowledge/ 폴더의 등록된 문서에서 BM25 로 검색."
metadata:
  author: code_assist_v1
  version: "1.0.0"
---

# 도메인 지식 검색

`code_assist_v1/knowledge/` 폴더의 마크다운 문서에서 BM25 로 관련 문서를 찾아 답변한다.

## 응답 규칙

1. 검색 결과가 있으면 → 문서 내용 기반으로 답변. 출처 파일명 명시.
2. 검색 결과가 없으면 → "등록된 지식이 없습니다." 한 줄로 답변. 길게 설명하지 마라.
3. 없는 내용을 지어내지 마라.
4. 컬럼/스펙 질문 시 표 형태로 답변.
