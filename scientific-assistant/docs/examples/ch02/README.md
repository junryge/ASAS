# Chapter 2 — 예제 코드

본 폴더의 코드는 **학습 전용**이다. `scientific-assistant/app.py` 운영 서버와는 별도로 동작한다.

## 파일

| 파일 | 설명 | 포트 |
|------|------|------|
| `hello_llm.py` | 70줄짜리 미니 채팅 서버 | 10010 |
| `smoke_test.py` | HTTP 헬스체크 스크립트 | - |

## 사용

```bash
# 1) 미니 서버 띄우기
python hello_llm.py
# → http://localhost:10010

# 2) 다른 터미널에서 헬스체크
python smoke_test.py 10010

# 3) 본 운영 서버(app.py)도 같은 방식으로 점검 가능
python smoke_test.py 10009
```

## 동작 모드

- **TOKEN.TXT 있음** → Claude API(`claude-sonnet-4-6`) 호출
- **TOKEN.TXT 없음** → 에코(echo) 응답 (학습용 폴백)

`TOKEN.TXT` 위치 탐색 순서:
1. 현재 폴더 (`docs/examples/ch02/TOKEN.TXT`)
2. 프로젝트 루트 (`scientific-assistant/TOKEN.TXT`)
