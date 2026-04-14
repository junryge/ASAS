---
name: logpresso-search
description: >
  로그프레소(Logpresso) 서버에 직접 연결하여 LPQL 쿼리를 실행하고 결과를 조회하는 스킬.
  사용자가 "로그프레소 조회", "로그프레소 검색", "로그프레소 데이터 보여줘" 등을 요청할 때 활성화.
  /api/logpresso/query API를 통해 서버에서 직접 데이터를 가져온다.
metadata:
  author: Demos
  version: "1.0.0"
  tags:
    - logpresso
    - search
    - query-execution
    - log-search
---

# 로그프레소 조회 스킬

이 스킬은 로그프레소 서버에 직접 연결하여 데이터를 조회한다.
쿼리 생성이 아니라 **실제 서버 실행**을 담당한다.

## 동작 방식

1. 사용자 요청에서 테이블명, 기간, 조건을 파악
2. LPQL 쿼리를 자동 생성
3. 로그프레소 서버(`/api/logpresso/query`)에 실행 요청
4. **결과(5건 미리보기) + 생성된 LPQL 쿼리**를 함께 표시
5. 서버 연결 실패 시 → 생성된 LPQL 쿼리만 표시

## 핵심 규칙

1. **절대 테이블명을 추측하지 마라.** 사용자가 말한 테이블명만 사용.
2. **절대 컬럼명을 추측하지 마라.** 모르면 fields 없이 전체 조회.
3. 기간 미지정 시 기본값: 오늘 하루 `from=YYYYMMDD000000 to=YYYYMMDD235959`
4. **limit은 무조건 5** (미리보기용)
5. 결과에 **항상 LPQL 쿼리를 함께 표시**

## 사용자에게 물어볼 정보

정보가 부족하면 아래를 물어라:
- 테이블명: __________
- 기간: __________ (예: duration=1h 또는 from=20260326000000 to=20260326235959)
- 필터 조건: __________ (예: LEVEL=="ERROR")

## 쿼리 생성 규칙 (컬럼 모를 때)

```lpql
table from=20260326000000 to=20260326235959 테이블명
| limit 5
```

컬럼을 알면:
```lpql
table from=20260326000000 to=20260326235959 테이블명
| search 조건
| fields 컬럼1, 컬럼2
| sort _time
| limit 5
```

## API 연동

이 스킬은 `/api/logpresso/query` 엔드포인트의 **execute 모드**를 사용한다.

```
POST /api/logpresso/query
{"query": "사용자 요청 텍스트"}
```

응답 (성공):
- mode: "execute"
- lpql: 생성된 LPQL 쿼리
- preview_data: 조회 결과 (5건)
- total_rows: 전체 건수

응답 (실패):
- error: 에러 메시지
- lpql: 생성된 LPQL 쿼리 (항상 포함)
- error_detail: 실패 상세 정보 (reason, response_preview, query_sent)

## 실패 시 표시 규칙

조회 실패 시 사용자에게 **반드시 아래 내용을 모두 표시**하라:
1. **에러 메시지** — 왜 실패했는지 (연결 타임아웃, HTTP 에러, 빈 응답 등)
2. **생성된 LPQL 쿼리** — 어떤 쿼리를 실행하려 했는지
3. **서버 응답 미리보기** — 서버가 반환한 에러 내용 (있으면)
4. **실패 원인 추정** — 테이블명 오류, 서버 연결 불가, 권한 문제 등