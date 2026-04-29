# 제2장. 첫 실행 — `python app.py` 한 줄로 내 LLM 띄우기

> **이 장의 목표**
> - `scientific-assistant/app.py`를 실행해 **로컬 웹 채팅 UI를 띄운다.**
> - 부팅 로그를 읽고 **각 컴포넌트가 정상인지 판별**할 수 있게 된다.
> - 본격 진입 전 동작 원리를 이해하기 위해 **미니 데모(`hello_llm.py`)** 를 직접 만들어본다.
> - 사내 LLM 엔드포인트(`http://common.llm.skhynix.com`)와 모델 `Qwen3-Coder-30B-A3B-Instruct`를 직접 호출해 본다.
> - 자주 발생하는 **5가지 오류와 해결법**을 익힌다.

---

## 2.1 한눈에 보는 부팅 흐름

```
python app.py
   │
   ├─ ① demos_v1 패키지 import → Flask app 객체 생성
   ├─ ② create_app() → 라우트(URL) 등록
   ├─ ③ scan_skills()  → scientific-skills 폴더 스캔
   ├─ ④ token.txt 로드 → 사내 LLM API 키 메모리 적재
   ├─ ⑤ 하니스 브릿지 초기화 (옵션)
   ├─ ⑥ Logpresso 테이블 갱신 (옵션)
   ├─ ⑦ GGUF 파일 자동 감지 → 가장 큰 모델 로드
   └─ ⑧ Flask 서버 기동 (0.0.0.0:10009)
```

이 흐름은 `app.py` 36~167줄에 그대로 코드로 표현되어 있다. 이번 장에서는 이 흐름을 **눈으로 확인**하고, 다음 장부터 각 단계를 깊이 파헤친다.

---

## 2.2 실행 전 최종 체크

1장에서 준비한 항목을 다시 확인한다.

```bash
# 가상환경 활성화 (Windows)
.venv\Scripts\activate
# (Linux/macOS)
source .venv/bin/activate

# 필수 패키지
pip install flask requests urllib3
```

폴더 안에 다음 파일이 있어야 한다.

| 파일/폴더 | 필수 | 비고 |
|-----------|------|------|
| `app.py` | ✅ | 진입점 |
| `demos_v1/` | ✅ | 핵심 모듈 |
| `scientific-skills/` | ⚠️ 권장 | 없으면 스킬 0개로 시작 |
| `token.txt` | ⚠️ 권장 | 사내 LLM 사용 시 (한 줄, Bearer 토큰) |
| `*.gguf` | ⛔ 선택 | 5장에서 다룸 |

### `token.txt` 형식

```
sk-skh-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **주의** — `token.txt`는 절대 git에 커밋하지 않는다. `.gitignore`에 반드시 포함할 것.

---

## 2.3 사내 LLM 엔드포인트 개요

본 가이드는 SK하이닉스 공통 LLM 게이트웨이를 기본 백엔드로 사용한다.

| 항목 | 값 |
|------|---|
| Base URL | `http://common.llm.skhynix.com` |
| 인증 헤더 | `Authorization: Bearer <token.txt 내용>` |
| 모델 목록 조회 | `GET /v1/models` |
| 채팅 호출 | `POST /v1/chat/completions` (OpenAI 호환) |
| 본 가이드 기본 모델 | **`Qwen3-Coder-30B-A3B-Instruct`** |

### `curl` 한 줄로 토큰·연결 확인

```bash
TOKEN=$(cat token.txt)

# 모델 목록
curl -s http://common.llm.skhynix.com/v1/models \
  -H "Authorization: Bearer $TOKEN" | head

# 한 번 대화
curl -s http://common.llm.skhynix.com/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen3-Coder-30B-A3B-Instruct",
       "messages":[{"role":"user","content":"안녕"}],
       "max_tokens":128}'
```

응답이 200으로 떨어지면 토큰·네트워크 OK다.

---

## 2.4 첫 실행

```bash
cd scientific-assistant
python app.py
```

### 정상 부팅 시 콘솔 출력 (예시)

```
==================================================
  Demos V1.0
==================================================
  📂 스킬 폴더: /home/user/.../scientific-skills
  ✅ 발견된 스킬: 355개
     - adaptyv
     - aeon
     - aesthetic
     ...
     ... 외 345개
  🔑 token.txt: 로드됨 (108자)
  🔧 하네스: 355개 스킬 레지스트리 등록 완료
     → /api/harness/skills, /api/harness/session/*, /api/harness/status
  ℹ️  GGUF 파일 없음 → LOCAL GGUF 비활성

  🖥️  사용 가능한 LLM 환경:
     [skhynix] SKHynix Common LLM → http://common.llm.skhynix.com

  🌐 http://localhost:10009 에서 접속하세요
==================================================
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:10009
```

### 부팅 로그 읽는 법

| 로그 라인 | 의미 | 문제 시 |
|-----------|------|---------|
| `📂 스킬 폴더` | 스킬 디렉터리 위치 | 경로 틀림 → 4장에서 수정 |
| `✅ 발견된 스킬: N개` | 스킬 자동 스캔 결과 | 0개면 폴더 비어있음 |
| `🔑 token.txt: 로드됨` | 사내 LLM 토큰 OK | 없으면 LLM 호출 불가 |
| `🔧 하네스: N개 ... 등록` | 도구 연동 OK | 7장에서 다룸 |
| `💻 GGUF 자동 감지!` | 로컬 모델 발견 | 5장에서 다룸 |
| `🌐 http://localhost:10009` | 접속 주소 | 이 주소를 브라우저에서 열기 |

---

## 2.5 브라우저 접속

<http://localhost:10009> 를 연다. Flask가 띄운 채팅 UI가 보이면 성공이다.

> **TIP** — 같은 LAN의 다른 기기에서 접속하려면 PC IP(예: `http://192.168.0.10:10009`)로 접속한다. 단, **방화벽**과 **보안 정책**을 반드시 확인할 것.

### 첫 메시지 보내기

1. 화면 상단의 **모델 선택** 드롭다운에서 `Qwen3-Coder-30B-A3B-Instruct` 선택
2. 입력창에 다음을 입력
   ```
   안녕? 너는 누구야? 어떤 스킬들을 가지고 있어?
   ```
3. 응답이 돌아오면 **연결 OK**

---

## 2.6 미니 데모 — `hello_llm.py` 직접 만들어보기

`app.py`는 기능이 많아서 처음에는 어렵다. 같은 패턴을 **100줄 남짓의 최소 코드**로 재현해 본다.

> 아래 두 파일은 이미 `docs/examples/ch02/` 에 만들어 두었다. 바로 실행해 봐도 된다.

### 2.6.1 핵심 호출 패턴 (참고용 30줄)

사내 LLM은 OpenAI 호환이므로 `requests` 한 번이면 끝난다.

```python
import requests

with open("token.txt", "r") as f:
    token = f.read().strip()

BASE = "http://common.llm.skhynix.com"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# 1) 모델 목록
models = requests.get(f"{BASE}/v1/models", headers=headers).json()
models = models.get("data", models) if isinstance(models, dict) else models
for i, m in enumerate(models):
    name = m.get("id", m) if isinstance(m, dict) else m
    print(f"  [{i}] {name}")

# 2) 한 번 호출
resp = requests.post(f"{BASE}/v1/chat/completions", headers=headers, json={
    "model": "Qwen3-Coder-30B-A3B-Instruct",
    "messages": [{"role": "user", "content": "안녕?"}],
    "max_tokens": 1024,
})
print(resp.json()["choices"][0]["message"]["content"])
```

### 2.6.2 `hello_llm.py` — 미니 채팅 서버

`docs/examples/ch02/hello_llm.py` 핵심 부분:

```python
BASE_URL = os.environ.get("LLM_BASE_URL", "http://common.llm.skhynix.com")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "Qwen3-Coder-30B-A3B-Instruct")

@app.route("/api/chat", methods=["POST"])
def chat():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "message is empty"}), 400

    if not API_TOKEN:
        return jsonify({"reply": f"[ECHO] {msg}\n(token.txt 가 없어 에코 모드)"})

    HISTORY.append({"role": "user", "content": msg})

    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_TOKEN}",
                 "Content-Type": "application/json"},
        json={"model": DEFAULT_MODEL, "messages": HISTORY, "max_tokens": 1024},
        timeout=120,
    )
    if resp.status_code != 200:
        HISTORY.pop()
        return jsonify({"error": f"API {resp.status_code}: {resp.text[:300]}"}), 500

    answer = resp.json()["choices"][0]["message"]["content"]
    HISTORY.append({"role": "assistant", "content": answer})
    return jsonify({"reply": answer})
```

특징:
- **`token.txt`를 자동 탐색** (현재 폴더 → 프로젝트 루트)
- **인메모리 대화 히스토리** 유지 (`/api/reset` 으로 초기화)
- **환경변수**(`LLM_BASE_URL`, `LLM_MODEL`)로 모델·엔드포인트 변경 가능
- 토큰이 없으면 **에코 모드**로 폴백 → 학습용

### 2.6.3 `smoke_test.py` — 헬스체크

`docs/examples/ch02/smoke_test.py` 는 **두 가지 모드**를 지원한다.

```bash
# A. 로컬 서버 점검
python smoke_test.py --port 10010      # hello_llm.py
python smoke_test.py --port 10009      # 본 운영 app.py

# B. 사내 LLM 엔드포인트 직접 점검 (token.txt 필요)
python smoke_test.py --remote --list                          # 모델 목록만
python smoke_test.py --remote                                 # 기본 모델로 ping
python smoke_test.py --remote --model Qwen3-Coder-30B-A3B-Instruct
```

### 2.6.4 실행 순서

```bash
# 터미널 1
cd scientific-assistant/docs/examples/ch02
python hello_llm.py
# → http://localhost:10010

# 터미널 2
python smoke_test.py --port 10010
# → ✅ 헬스체크 통과

# (옵션) 사내 엔드포인트가 직접 살아있는지
python smoke_test.py --remote --list
```

> 이 미니 데모는 **본 프로젝트의 어떤 파일도 수정하지 않는다.** 학습 전용이며, 본 운영 서버는 `scientific-assistant/app.py`다.

---

## 2.7 자주 발생하는 오류 5가지

### 오류 1: `ModuleNotFoundError: No module named 'flask'`
**원인** 가상환경 비활성 또는 패키지 미설치
**해결**
```bash
source .venv/bin/activate    # 또는 .venv\Scripts\activate
pip install flask requests
```

### 오류 2: `OSError: [Errno 98] Address already in use` / `WinError 10048`
**원인** 포트 10009를 다른 프로세스가 점유
**해결**
```bash
# Linux/macOS
lsof -i :10009
kill <PID>

# Windows
netstat -ano | findstr 10009
taskkill /PID <PID> /F
```
또는 `app.py` 167줄의 `port=10009`를 `10019` 등으로 변경.

### 오류 3: `API 401 Unauthorized` 또는 `⚠️ token.txt 비어있음`
**원인** 토큰 누락/만료
**해결**
- `token.txt` 가 같은 폴더에 있는지 확인
- 파일 안에 **공백·개행 없이** 토큰만 있는지 확인 (`hello_llm.py`는 `strip()` 한다)
- `curl ... /v1/models` 로 토큰이 살아있는지 직접 검증

### 오류 4: `API 404 Not Found: model ... is not available`
**원인** 모델명이 사내 게이트웨이에 없음
**해결**
```bash
python smoke_test.py --remote --list
```
로 사용 가능한 모델 ID를 확인 후 환경변수로 지정:
```bash
export LLM_MODEL=Qwen3-Coder-30B-A3B-Instruct
python hello_llm.py
```

### 오류 5: 브라우저에서 `이 사이트에 연결할 수 없음`
**원인** 콘솔에 `Running on ...` 이 안 떴거나, 방화벽/프록시 차단
**해결**
- 콘솔 로그를 끝까지 확인 (다른 줄에서 멈췄다면 거기가 진짜 원인)
- `127.0.0.1:10010` 와 `localhost:10010` 둘 다 시도
- 사내망에서 외부로 나가는 프록시 환경변수가 사내 LLM 호출까지 막을 수 있다 → `NO_PROXY=common.llm.skhynix.com` 설정

---

## 2.8 종료 방법

- 콘솔에서 `Ctrl + C` 한 번 → Flask 정상 종료
- GGUF 모델이 로드된 상태라면 메모리 해제까지 1~3초 대기

---

## 2.9 2장 체크리스트

- [ ] `token.txt` 가 프로젝트 루트(또는 예제 폴더)에 존재
- [ ] `curl ... /v1/models` 가 모델 목록을 200으로 반환
- [ ] `python hello_llm.py` 실행 → <http://localhost:10010> 응답 확인
- [ ] `python smoke_test.py --port 10010` → ✅ 통과
- [ ] `python smoke_test.py --remote --list` → 모델 목록에 `Qwen3-Coder-30B-A3B-Instruct` 보임
- [ ] `python app.py` 실행 → <http://localhost:10009> 에서 첫 응답 받음

---

## 2.10 다음 장 예고

**제3장 — 모델·엔드포인트 자유롭게 갈아끼우기**
- `api_config.json` 의 의미와 구조
- 사내 LLM 외 모델(다른 Qwen, Llama 등) 추가하기
- 모델별 토큰 한도·온도(temperature) 튜닝
- API 호출 디버깅 — `curl` 한 줄로 진단

---

*문서 버전: v1.1 (2026-04-29) — 사내 LLM(Qwen3-Coder-30B-A3B-Instruct) 기준으로 갱신*
*브랜치: `claude/create-llm-guide-chapter-one-RDZ12`*
