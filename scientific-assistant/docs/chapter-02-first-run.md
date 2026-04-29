# 제2장. 첫 실행 — `python app.py` 한 줄로 내 LLM 띄우기

> **이 장의 목표**
> - `scientific-assistant/app.py`를 실행해 **로컬 웹 채팅 UI를 띄운다.**
> - 부팅 로그를 읽고 **각 컴포넌트가 정상인지 판별**할 수 있게 된다.
> - 본격 진입 전 동작 원리를 이해하기 위해 **미니 데모(`hello_llm.py`)** 를 직접 만들어본다.
> - 자주 발생하는 **5가지 오류와 해결법**을 익힌다.

---

## 2.1 한눈에 보는 부팅 흐름

```
python app.py
   │
   ├─ ① demos_v1 패키지 import → Flask app 객체 생성
   ├─ ② create_app() → 라우트(URL) 등록
   ├─ ③ scan_skills()  → scientific-skills 폴더 스캔
   ├─ ④ TOKEN.TXT 로드 → Claude API 키 메모리 적재
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
| `TOKEN.TXT` | ⚠️ 권장 | Claude API 사용 시 |
| `*.gguf` | ⛔ 선택 | 5장에서 다룸 |

---

## 2.3 첫 실행

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
  🔑 TOKEN.TXT: 로드됨 (108자)
  🔧 하네스: 355개 스킬 레지스트리 등록 완료
     → /api/harness/skills, /api/harness/session/*, /api/harness/status
  ℹ️  GGUF 파일 없음 → LOCAL GGUF 비활성

  🖥️  사용 가능한 LLM 환경:
     [claude] Claude (Anthropic) → https://api.anthropic.com/v1/messages

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
| `🔑 TOKEN.TXT: 로드됨` | API 키 OK | 없으면 Claude 호출 불가 |
| `🔧 하네스: N개 ... 등록` | 도구 연동 OK | 7장에서 다룸 |
| `💻 GGUF 자동 감지!` | 로컬 모델 발견 | 5장에서 다룸 |
| `🌐 http://localhost:10009` | 접속 주소 | 이 주소를 브라우저에서 열기 |

---

## 2.4 브라우저 접속

<http://localhost:10009> 를 연다. Flask가 띄운 채팅 UI가 보이면 성공이다.

> **TIP** — 같은 LAN의 다른 기기에서 접속하려면 PC IP(예: `http://192.168.0.10:10009`)로 접속한다. 단, **방화벽**과 **보안 정책**을 반드시 확인할 것.

### 첫 메시지 보내기

1. 화면 상단의 **환경 선택** 드롭다운에서 `claude` 선택 (또는 GGUF 모델)
2. 입력창에 다음을 입력
   ```
   안녕? 너는 누구야? 어떤 스킬들을 가지고 있어?
   ```
3. 응답이 돌아오면 **연결 OK**

---

## 2.5 미니 데모 — `hello_llm.py` 직접 만들어보기

`app.py`는 기능이 많아서 처음에는 어렵다. 같은 패턴을 **70줄짜리 최소 코드**로 재현해 본다. 이 데모를 이해하면 `demos_v1/` 의 분리 구조도 자연스럽게 보인다.

> 아래 두 파일은 이미 `docs/examples/ch02/` 에 만들어 두었다. 바로 실행해 봐도 된다.

### 2.5.1 `hello_llm.py` — 최소 채팅 서버

```python
# docs/examples/ch02/hello_llm.py
"""
70줄짜리 미니 LLM 서버.
- /         : 간단한 채팅 HTML
- /api/chat : 메시지를 받아 Claude 또는 에코 응답
실행:  python hello_llm.py  →  http://localhost:10010
"""
import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

# 1) 같은 폴더의 TOKEN.TXT 또는 상위 프로젝트의 키 사용
def load_token():
    for p in ("TOKEN.TXT", "../../../TOKEN.TXT"):
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    return ""

API_TOKEN = load_token()

INDEX_HTML = """<!doctype html>
<meta charset="utf-8"><title>Hello LLM</title>
<h2>Hello LLM (mini)</h2>
<textarea id=q rows=3 cols=60 placeholder="질문을 입력"></textarea><br>
<button onclick="ask()">전송</button>
<pre id=a style="white-space:pre-wrap;background:#f4f4f4;padding:8px"></pre>
<script>
async function ask(){
  const q = document.getElementById('q').value;
  const r = await fetch('/api/chat',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:q})});
  const j = await r.json();
  document.getElementById('a').innerText = j.reply || j.error;
}
</script>
"""

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/api/chat", methods=["POST"])
def chat():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "message is empty"}), 400

    # 토큰 없으면 에코로 폴백 → 학습용
    if not API_TOKEN:
        return jsonify({"reply": f"[ECHO] {msg}\n(TOKEN.TXT가 없어 에코 모드입니다)"})

    # Claude API 호출 (Messages API)
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": msg}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_TOKEN,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = "".join(b.get("text", "") for b in data.get("content", []))
        return jsonify({"reply": text})
    except Exception as e:
        return jsonify({"error": f"API error: {e}"}), 500


if __name__ == "__main__":
    print(f"🪄 Hello LLM 시작 → http://localhost:10010  (토큰: {'있음' if API_TOKEN else '없음 → 에코 모드'})")
    app.run(host="0.0.0.0", port=10010, debug=False)
```

### 2.5.2 `smoke_test.py` — 서버 헬스체크

`app.py` 또는 `hello_llm.py`가 정상인지 확인하는 30초짜리 스크립트.

```python
# docs/examples/ch02/smoke_test.py
"""
사용:
  python smoke_test.py                # 기본: localhost:10009 (app.py)
  python smoke_test.py 10010          # 포트 변경 (hello_llm.py)
"""
import sys
import json
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10009
BASE = f"http://localhost:{PORT}"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return r.status, r.read()[:200]

def post_chat(msg):
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps({"message": msg}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

print(f"[1/2] GET {BASE}/ ... ", end="")
try:
    status, body = get("/")
    print(f"OK ({status}, {len(body)} bytes)")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

print(f"[2/2] POST /api/chat ... ", end="")
try:
    status, j = post_chat("ping?")
    print(f"OK ({status})")
    print("   응답:", (j.get("reply") or j.get("error") or "")[:120])
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

print("✅ 헬스체크 통과")
```

### 2.5.3 실행 순서

```bash
# 터미널 1
cd scientific-assistant/docs/examples/ch02
python hello_llm.py
# → http://localhost:10010

# 터미널 2
python smoke_test.py 10010
# → ✅ 헬스체크 통과
```

> 이 미니 데모는 **본 프로젝트의 어떤 파일도 수정하지 않는다.** 학습 전용이며, 본 운영 서버는 `scientific-assistant/app.py`다.

---

## 2.6 자주 발생하는 오류 5가지

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

### 오류 3: `⚠️ TOKEN.TXT: 없음 또는 비어있음`
**원인** API 키 파일 누락
**해결** 1장 1.6.4 참고. 단, 5장의 GGUF 모델만 쓸 거라면 무시해도 된다.

### 오류 4: `⚠️ 스킬 폴더 없음`
**원인** `scientific-skills/`가 `app.py`와 같은 위치에 없음
**해결** 스킬 ZIP을 풀어 `scientific-assistant/scientific-skills/`로 이동.

### 오류 5: 브라우저에서 `이 사이트에 연결할 수 없음`
**원인** 콘솔에 `Running on ...` 이 안 떴거나, 방화벽/프록시 차단
**해결**
- 콘솔 로그를 끝까지 확인 (다른 줄에서 멈췄다면 거기가 진짜 원인)
- `127.0.0.1:10009` 와 `localhost:10009` 둘 다 시도
- 사내망이면 회사 프록시 환경변수(`HTTP_PROXY`) 해제

---

## 2.7 종료 방법

- 콘솔에서 `Ctrl + C` 한 번 → Flask 정상 종료
- GGUF 모델이 로드된 상태라면 메모리 해제까지 1~3초 대기

---

## 2.8 2장 체크리스트

- [ ] `python app.py` 실행 후 부팅 로그 확인
- [ ] 콘솔의 8단계 로그 의미를 이해함
- [ ] <http://localhost:10009> 에서 첫 응답 받음
- [ ] `hello_llm.py` 를 직접 실행해 봄
- [ ] `smoke_test.py` 가 ✅ 로 끝남
- [ ] 5가지 오류 중 본인이 겪은 것을 해결함

---

## 2.9 다음 장 예고

**제3장 — API 키와 모델 연결: Claude·GGUF·외부 모델 자유롭게 갈아끼우기**
- `api_config.json` 의 의미와 구조
- 환경(`ENV_CONFIG`) 추가/제거하기
- 모델별 토큰 한도·온도(temperature) 튜닝
- API 호출 디버깅 — `curl` 한 줄로 진단

---

*문서 버전: v1.0 (2026-04-29)*
*브랜치: `claude/create-llm-guide-chapter-one-RDZ12`*
