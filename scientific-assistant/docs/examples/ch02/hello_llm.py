"""
Chapter 2 학습용 미니 LLM 서버 (70줄짜리 hello-world).

scientific-assistant/app.py 의 동작 원리를 최소 코드로 재현한 학습 전용 데모.
- /         : 간단한 채팅 HTML
- /api/chat : 메시지를 받아 Claude API 호출 또는 에코 응답

실행:
    python hello_llm.py
    → http://localhost:10010
"""
import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)


def load_token():
    """같은 폴더 또는 프로젝트 루트의 TOKEN.TXT 를 찾는다."""
    candidates = (
        "TOKEN.TXT",
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
<textarea id=q rows=3 cols=60 placeholder="질문을 입력"></textarea><br>
<button onclick="ask()">전송</button>
<pre id=a style="white-space:pre-wrap;background:#f4f4f4;padding:8px"></pre>
<script>
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

    if not API_TOKEN:
        return jsonify({
            "reply": f"[ECHO] {msg}\n(TOKEN.TXT 가 없어 에코 모드로 동작합니다)"
        })

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
    mode = "있음" if API_TOKEN else "없음 → 에코 모드"
    print(f"🪄 Hello LLM 시작 → http://localhost:10010  (토큰: {mode})")
    app.run(host="0.0.0.0", port=10010, debug=False)
