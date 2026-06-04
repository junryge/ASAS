"""
최소 통합 예제 — 헤르메스를 아무 Flask 앱에 붙이는 법.

실행:
    cd hermes-engine
    pip install flask
    python examples/app_min.py
    → http://localhost:8900

핵심은 단 한 줄:  register_hermes_routes(app)
나머지(/api/chat)는 당신의 기존 LLM 챗을 그대로 쓰면 된다.
이 예제의 /api/chat 은 에코(데모용)다.
"""
import os
import sys
import json

# hermes 패키지 경로 (예제가 hermes-engine/examples 안에 있으므로 상위 추가)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, Response, send_from_directory
from hermes import register_hermes_routes   # ← 이 한 줄이 핵심

app = Flask(__name__)

# 1) 헤르메스 라우트 등록 (/api/hermes/*)
register_hermes_routes(app)


# 2) 당신의 기존 채팅 엔드포인트 (여기선 데모용 에코)
@app.route("/api/chat", methods=["POST"])
def chat():
    d = request.get_json(force=True, silent=True) or {}
    sysp = d.get("system_prompt", "")
    last = ""
    for m in reversed(d.get("messages", [])):
        if m.get("role") == "user":
            last = m.get("content", "")
            break
    # 데모: system_prompt 에 헤르메스 기억이 들어왔는지 보여주고,
    # 모델이 기억 블록을 내는 것처럼 흉내 (실서비스는 진짜 LLM 응답)
    reply = f"(echo) 받은 질문: {last}\n\n[system_prompt 길이: {len(sysp)}자]"
    if "기억" in last or "remember" in last.lower():
        reply += "\n\n```hermes:memory\nstore: user\naction: add\ntext: " + last + "\n```"
    return jsonify({"reply": reply})


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "demo.html")


@app.route("/static/<path:p>")
def static_files(p):
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"), p)


if __name__ == "__main__":
    print("HERMES_DATA_DIR =", os.environ.get("HERMES_DATA_DIR", "(기본: ./hermes_data)"))
    app.run(host="0.0.0.0", port=8900, debug=True)
