"""
Chapter 2 학습용 미니 LLM 서버 (SKHynix 사내 LLM 엔드포인트 사용).

scientific-assistant/app.py 의 동작 원리를 최소 코드로 재현한 학습 전용 데모.
- /         : 간단한 채팅 HTML
- /api/chat : 메시지를 받아 사내 LLM(OpenAI 호환) 호출

기본 엔드포인트 : http://common.llm.skhynix.com
기본 모델       : Qwen3-Coder-30B-A3B-Instruct
인증            : Authorization: Bearer <token.txt 내용>

실행:
    python hello_llm.py
    → http://localhost:10010
"""
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_URL = os.environ.get("LLM_BASE_URL", "http://common.llm.skhynix.com")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "Qwen3-Coder-30B-A3B-Instruct")


def load_token():
    """token.txt 를 같은 폴더 또는 프로젝트 루트에서 찾는다."""
    candidates = (
        "token.txt",
        "TOKEN.TXT",
        os.path.join("..", "..", "..", "token.txt"),
        os.path.join("..", "..", "..", "TOKEN.TXT"),
    )
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    return ""


API_TOKEN = load_token()

INDEX_HTML = """<!doctype html>
<meta charset="utf-8"><title>Hello LLM</title>
<h2>Hello LLM (mini) - Chapter 2 demo</h2>
<p>모델: <b id=m>(loading...)</b></p>
<textarea id=q rows=3 cols=60 placeholder="질문을 입력"></textarea><br>
<button onclick="ask()">전송</button>
<button onclick="resetChat()">대화 초기화</button>
<pre id=a style="white-space:pre-wrap;background:#f4f4f4;padding:8px"></pre>
<script>
fetch('/api/info').then(r=>r.json()).then(j=>{document.getElementById('m').innerText = j.model});
async function ask(){
  const q = document.getElementById('q').value;
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: q})
  });
  const j = await r.json();
  document.getElementById('a').innerText = j.reply || j.error;
}
async function resetChat(){
  await fetch('/api/reset', {method: 'POST'});
  document.getElementById('a').innerText = '(대화 초기화됨)';
}
</script>
"""

# 단순 인메모리 대화 히스토리 (학습용)
HISTORY = []


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/info")
def info():
    return jsonify({"base_url": BASE_URL, "model": DEFAULT_MODEL,
                    "token_loaded": bool(API_TOKEN)})


@app.route("/api/reset", methods=["POST"])
def reset():
    HISTORY.clear()
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"error": "message is empty"}), 400

    if not API_TOKEN:
        return jsonify({
            "reply": f"[ECHO] {msg}\n(token.txt 가 없어 에코 모드로 동작합니다)"
        })

    HISTORY.append({"role": "user", "content": msg})

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": HISTORY,
        "max_tokens": 1024,
    }

    try:
        resp = requests.post(f"{BASE_URL}/v1/chat/completions",
                             headers=headers, json=payload, timeout=120)
    except requests.RequestException as e:
        HISTORY.pop()
        return jsonify({"error": f"네트워크 오류: {e}"}), 500

    if resp.status_code != 200:
        HISTORY.pop()
        return jsonify({"error": f"API {resp.status_code}: {resp.text[:300]}"}), 500

    answer = resp.json()["choices"][0]["message"]["content"]
    HISTORY.append({"role": "assistant", "content": answer})
    return jsonify({"reply": answer})


if __name__ == "__main__":
    mode = "있음" if API_TOKEN else "없음 → 에코 모드"
    print(f"🪄 Hello LLM 시작 → http://localhost:10010")
    print(f"   엔드포인트: {BASE_URL}")
    print(f"   모델     : {DEFAULT_MODEL}")
    print(f"   토큰     : {mode}")
    app.run(host="0.0.0.0", port=10010, debug=False)
