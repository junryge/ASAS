#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
proxy.py — 헤르메스 DEMO.html 용 CORS 우회 프록시 (표준 라이브러리만, 설치 불필요)

브라우저(file://)는 보안정책(CORS) 때문에 사내 LLM API에 직접 fetch 하지 못합니다.
이 작은 프록시를 띄우면, DEMO.html → http://localhost:8000 → 사내 API 로 중계하며
CORS 헤더와 토큰을 자동으로 붙여줍니다. (당신의 Python 이 되면 이 프록시도 100% 됩니다)

사용법:
  1) token.txt 를 이 파일과 같은 폴더에 둔다 (Bearer 토큰 한 줄)
  2) python proxy.py            (기본 BASE=http://common.llm.skhynix.com, 포트 8000)
     - 다른 게이트웨이:  python proxy.py --base http://dev.hcp.llm.skhynix.com --port 8000
  3) DEMO.html 의 'API 주소' 를  http://localhost:8000/v1  로 바꾸고 저장
     - API 키 칸은 비워둬도 됨 (프록시가 token.txt 로 자동 인증)

지원 경로:  GET /v1/models,  POST /v1/chat/completions  (그 외 /v1/* 도 그대로 중계)
"""
import argparse, json, os, sys, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = "http://common.llm.skhynix.com"
TOKEN = ""


def _token():
    global TOKEN
    if TOKEN:
        return TOKEN
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "token.txt"), "token.txt"):
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                TOKEN = f.read().strip()
                return TOKEN
    return ""


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def _forward(self, method):
        # /v1/... 경로를 사내 BASE 로 그대로 중계
        url = BASE.rstrip("/") + self.path
        body = None
        if method == "POST":
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(n) if n else b""
        headers = {"Content-Type": "application/json"}
        tok = _token()
        if tok:
            headers["Authorization"] = "Bearer " + tok
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read(); code = r.status
        except urllib.error.HTTPError as e:
            data = e.read(); code = e.code
        except Exception as e:  # noqa
            data = json.dumps({"error": str(e)}).encode(); code = 502
        self.send_response(code); self._cors()
        self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  self._forward("GET")
    def do_POST(self): self._forward("POST")

    def log_message(self, fmt, *a):
        sys.stderr.write("  %s %s\n" % (self.command, self.path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE, help="사내 LLM API 베이스 (예: http://common.llm.skhynix.com)")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    BASE = a.base.rstrip("/")
    if not _token():
        print("⚠️  token.txt 를 못 찾았습니다 — 같은 폴더에 토큰 한 줄로 저장하세요.")
    print(f"🔮 헤르메스 프록시  http://localhost:{a.port}/v1  →  {BASE}/v1")
    print(f"   DEMO.html 의 API 주소를 http://localhost:{a.port}/v1 로 설정하세요. (Ctrl+C 종료)")
    ThreadingHTTPServer(("0.0.0.0", a.port), H).serve_forever()
