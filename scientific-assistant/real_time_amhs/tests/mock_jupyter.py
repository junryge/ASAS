"""가짜 주피터 파일서버 — 진짜와 같은 로그인 흐름으로 CSV 를 내준다.

  GET  /login   → _xsrf 쿠키 + 로그인 폼
  POST /login   → 비밀번호 맞으면 세션 쿠키, 틀리면 폼 재출력(200, 'Invalid password')
  GET  /files/… → 세션 쿠키 없으면 403, 있으면 CSV
"""
import json, os, sys, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# 테스트 전용 더미. 진짜 비밀번호를 여기에 두면 저장소에 커밋된다.
PW = os.environ.get("MOCK_PW", "테스트용-더미-비번")
with open(os.environ.get("MOCK_CSV") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "fixtures", "발동이벤트_샘플.csv"), "rb") as _f:
    CSV = _f.read()
SESS = set()


class Srv(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8", cookies=()):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for c in cookies:
            self.send_header("Set-Cookie", c)
        self.end_headers()
        self.wfile.write(body)

    def _cookies(self):
        raw = self.headers.get("Cookie", "")
        return dict(p.strip().split("=", 1) for p in raw.split(";") if "=" in p)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/login":
            return self._send(200, "<html><body><form><input name='password'>"
                                   "</form></body></html>",
                              cookies=["_xsrf=abc123; Path=/"])
        if path.startswith("/api/contents"):
            if self._cookies().get("session_id") not in SESS:
                return self._send(403, "<html>Forbidden</html>")
            days = ["20260809", "20260810", "20260811"]
            return self._send(200, json.dumps({"content": [
                {"name": f"{d}_발동이벤트.csv", "size": 5243, "type": "file",
                 "last_modified": f"2026-08-{d[6:]}T23:59:00Z"} for d in days
            ] + [{"name": "메모.md", "size": 10, "type": "file"}]},
                ensure_ascii=False), "application/json")
        if path.startswith("/files/"):
            if self._cookies().get("session_id") not in SESS:
                return self._send(403, "<html>Forbidden</html>")
            name = urllib.parse.unquote(path.rsplit("/", 1)[-1])
            if not name.endswith("발동이벤트.csv"):
                return self._send(404, "<html>Not Found</html>")
            if not name[:8].isdigit() or name[:4] != "2026":
                return self._send(404, "<html>Not Found</html>")
            return self._send(200, CSV, "text/csv")
        return self._send(404, "<html>Not Found</html>")

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/login":
            return self._send(404, "nope")
        n = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(n).decode())
        if self._cookies().get("_xsrf") != form.get("_xsrf", [""])[0]:
            return self._send(403, "<html>XSRF cookie does not match</html>")
        if form.get("password", [""])[0] != PW:
            return self._send(200, "<html><body>Invalid password or token"
                                   "<form><input name='password'></form></body></html>")
        sid = "s%d" % time.time_ns()
        SESS.add(sid)
        return self._send(200, "<html>ok</html>",
                          cookies=[f"session_id={sid}; Path=/"])

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9911
    Srv(("127.0.0.1", port), H).serve_forever()
