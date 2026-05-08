---
name: knowledge-search
description: "사용자별 개인 지식 도메인 검색. knowledge/{user_id}/ 폴더에서 검색."
metadata:
  author: Demos
  version: "3.0.0"
---

# 도메인 지식 검색

사용자별 `knowledge/{user_id}/` 폴더에서 등록된 문서를 검색하여 답변한다.

## 응답 규칙

1. 검색 결과가 있으면 → 문서 내용 기반으로 답변. 출처 파일명 명시.
2. 검색 결과가 없으면 → "등록된 지식이 없습니다." 한 줄로 답변. 길게 설명하지 마라.
3. 없는 내용을 지어내지 마라.
4. 컬럼 질문 시 테이블 형태로 답변.
