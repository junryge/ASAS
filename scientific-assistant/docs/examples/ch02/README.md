# Chapter 2 — 예제 코드

본 폴더의 코드는 **학습 전용**이다. `scientific-assistant/app.py` 운영 서버와는 별도로 동작한다.

## 파일

| 파일 | 설명 | 포트 |
|------|------|------|
| `hello_llm.py` | 사내 LLM(Qwen3-Coder-30B-A3B-Instruct) 호출 미니 채팅 서버 | 10010 |
| `smoke_test.py` | 로컬 서버 / 사내 엔드포인트 헬스체크 | - |

## 환경

- **엔드포인트**: `http://common.llm.skhynix.com` (OpenAI 호환)
- **기본 모델**: `Qwen3-Coder-30B-A3B-Instruct`
- **인증**: `Authorization: Bearer <token.txt 내용>`
- **토큰 파일**: `token.txt` (또는 `TOKEN.TXT`) — 같은 폴더 또는 프로젝트 루트

## 사용

```bash
# 1) 미니 서버 띄우기
python hello_llm.py
# → http://localhost:10010

# 2) 로컬 서버 헬스체크
python smoke_test.py --port 10010

# 3) 사내 LLM 엔드포인트 직접 점검 (token.txt 필요)
python smoke_test.py --remote --list                       # 모델 목록
python smoke_test.py --remote                              # ping 테스트
python smoke_test.py --remote --model Qwen3-Coder-30B-A3B-Instruct
```

## 환경변수로 모델/엔드포인트 바꾸기

```bash
# Linux/macOS
export LLM_BASE_URL=http://common.llm.skhynix.com
export LLM_MODEL=Qwen3-Coder-30B-A3B-Instruct
python hello_llm.py

# Windows (PowerShell)
$env:LLM_BASE_URL="http://common.llm.skhynix.com"
$env:LLM_MODEL="Qwen3-Coder-30B-A3B-Instruct"
python hello_llm.py
```

## 동작 모드

- **token.txt 있음** → 사내 LLM (Qwen3-Coder-30B-A3B-Instruct) 호출
- **token.txt 없음** → 에코(echo) 응답 (학습용 폴백)

## 의존성

```bash
pip install flask requests
```
