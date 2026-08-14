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

# FAB 별 파일(fab분리 폴더) — 실물과 같은 특징만 축약:
#   · unified_risk_score(전체 점수)와 hot_area(전체 기준 M16HUB)가 그대로 있고
#   · 그 FAB 자신의 점수는 area_score / area_level 이다
#   · {FAB}_pts_* 룰 점수 컬럼이 있다 (기여도 분해가 이걸 쓴다)
# 정규화(area_score→unified, hot_area→FAB)가 안 되면 화면이 전체 점수를
# 보게 되므로, 두 점수를 일부러 다르게 둔다.
FABS = ("M14", "M14B", "M16A", "M16B", "M16HUB")


def fab_csv(day: str, fab: str) -> bytes:
    d = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    head = ("file,datetime,date,time,unified_risk_score,unified_risk_level,"
            f"hot_area,reason,{fab}_score,{fab}_pts_RA_sus,{fab}_pts_SLA,"
            f"{fab}_ra,sla_{fab},area_score,area_level,area_saturated")
    scores = [(5, ""), (55, "경계"), (72, "위험"), (88, "초위험")]
    rows = [
        f"HUB_PR.csv,{d} 00:0{i},{d},00:0{i},44,경계,M16HUB,"
        f"\"hot_area=M16HUB; 발동: M16HUB[R-A_sus]; {fab}[R-A_sus,SLA(9.9%4분초과)]\","
        f"{sc},5,5,3.1{i},9.9,{sc},{lv},"
        for i, (sc, lv) in enumerate(scores)
    ]
    return ("\n".join([head] + rows) + "\n").encode("utf-8")


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
            if not name[:8].isdigit() or name[:4] != "2026":
                return self._send(404, "<html>Not Found</html>")
            # FAB 별 파일 — …/fab분리/20260814_발동이벤트_M14.csv
            for fab in FABS:
                if name.endswith(f"발동이벤트_{fab}.csv"):
                    if "fab분리" not in urllib.parse.unquote(path):
                        return self._send(404, "<html>Not Found</html>")
                    return self._send(200, fab_csv(name[:8], fab), "text/csv")
            if not name.endswith("발동이벤트.csv"):
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
