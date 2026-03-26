---
name: knowledge-search
description: >
  도메인 지식 검색 스킬. knowledge 폴더의 FAB 컬럼 정보, 아키텍처 문서,
  도메인 지식을 검색하여 답변한다.
  "컬럼 정보", "FAB", "아키텍처", "도메인", "지식 검색" 등을 요청할 때 활성화.
metadata:
  author: Demos
  version: "1.0.0"
  tags:
    - knowledge
    - domain
    - fab
    - column
    - architecture
---

# 도메인 지식 검색 스킬

이 스킬은 `knowledge/` 폴더에 저장된 도메인 지식 문서를 검색하여 답변한다.

## 검색 가능한 문서

### FAB 컬럼 정보 (30개)
- FAB_M14_컬럼.md, FAB_M14B_컬럼.md
- FAB_M16_컬럼.md, FAB_M16A_컬럼.md, FAB_M16B_컬럼.md, FAB_M16E_컬럼.md, FAB_M16HUB_컬럼.md
- FAB_M10_컬럼.md, FAB_M10A_컬럼.md, FAB_M10B_컬럼.md, FAB_M10C_컬럼.md, FAB_M10F_컬럼.md
- FAB_M11_컬럼.md, FAB_M11A_컬럼.md, FAB_M11B_컬럼.md
- FAB_M15_컬럼.md, FAB_M15A_컬럼.md, FAB_M15B_컬럼.md, FAB_M15B_WLP3_컬럼.md, FAB_M15C_컬럼.md
- FAB_C2_컬럼.md, FAB_C2F_컬럼.md
- FAB_CJPKG_FRONT_컬럼.md, FAB_CJPKG_MBS_컬럼.md, FAB_CJPRB_컬럼.md, FAB_CJPRB_WLP3_컬럼.md
- FAB_ICPKG_PNT4_1F_컬럼.md, FAB_ICPKG_PNT4_5F_컬럼.md, FAB_ICPRB_컬럼.md
- FAB_R3_컬럼.md, FAB_M16_PKT_컬럼.md, FAB_M16_WT_컬럼.md

### 아키텍처/시스템 문서
- SK_Hynix_Domain_Knowledge.md — SK하이닉스 도메인 지식
- M14_v10.4_프로젝트_아키텍처.md — M14 프로젝트 아키텍처
- Hubroom_v8.3_아키텍처.md — 허브룸 아키텍처
- HID_INOUT_JAVA_변경상황.md — HID 변경 이력
- 내부시스템_접속정보.md — 내부 시스템 접속 정보
- 예측모델_개발히스토리.md — 예측 모델 개발 이력
- 프로젝트별_통신_방식.md — 프로젝트 통신 방식

## 동작 방식

1. 사용자 질문에서 키워드 추출
2. knowledge/ 폴더의 파일명과 내용을 검색
3. 매칭된 문서 내용을 LLM에 전달하여 답변 생성

## 응답 규칙

1. 검색된 문서의 내용을 기반으로 **정확하게** 답변하라
2. 문서에 없는 내용을 **지어내지 마라**
3. 어떤 문서에서 정보를 찾았는지 **출처를 명시**하라
4. 여러 문서가 매칭되면 관련도 높은 것 위주로 답변하라
