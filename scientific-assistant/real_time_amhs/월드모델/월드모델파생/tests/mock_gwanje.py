#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가짜 관제(real_time_amhs) — 실시간 모드의 스코어 중계(/api/score/*) 시험용. 진짜 데이터 없음.

    python tests/mock_gwanje.py 18989

관제와 같은 주소로 받는다: /api/feed · /api/graph · /api/contrib · /api/oht_map/report.
/mock/last 는 마지막으로 받은 주소와 인자(sys 등), 받은 수(n)를 돌려준다.
"""
import json
import sys
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LAST = {"path": "", "q": {}, "n": 0}
CUTS = {"warn": 60, "danger": 71, "critical": 85}


def rows(sysname, n):
    now = datetime.now().replace(second=0, microsecond=0)
    out = []
    for i in range(n):
        t = now - timedelta(minutes=i)
        sc = [34, 62, 75, 88][i % 4]
        lv = "정상" if sc < 60 else "경계" if sc < 71 else "위험" if sc < 85 else "초위험"
        r = {"at": t.isoformat(), "datetime": t.strftime("%Y-%m-%d %H:%M"), "time": t.strftime("%H:%M"),
             "score": float(sc), "level": lv, "emoji": "", "area": sysname,
             "reason": f"{sysname} 반송지연 지속 · PIO_ERROR {i % 3 + 1}개/1분",
             "reason_raw": "RA_sus|PIO", "metrics": [{"raw": f"{sysname}.QUE.TIME.AVGTOTALTIME1MIN", "label": "반송시간"}],
             "m": {"big": list(range(50))},              # 화면이 안 쓰는 무거운 칸 — 중계가 빼야 한다
             "zones": ["Z1"], "hi_fab": sysname, "fab": {sysname: sc}}
        if lv != "정상":
            r["alm"] = {"lv": lv + "중", "w": 3, "d": 1, "c": 1, "why": f"최근 10분에 {lv} 이상"}
        if i == 1:
            fn = f"PROBLEM_MAP_{sysname}_{t:%Y%m%d}_{t:%H%M}_WARNING.html"
            r["hid"] = [{"d": t.strftime("%Y%m%d"), "t": t.strftime("%H:%M"), "f": sysname, "z": "2", "file": fn}]
        out.append(r)
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/mock/last":
            return self._send(200, json.dumps(LAST, ensure_ascii=False), "application/json")
        LAST.update(path=u.path, q=q, n=LAST["n"] + 1)
        s = q.get("sys", "ALL")
        if u.path == "/api/feed":
            n = int(q.get("limit", 90))
            d = {"rows": rows(s, n), "day": datetime.now().strftime("%Y%m%d"), "fallback": False,
                 "latest": rows(s, 1)[0]["datetime"], "alarm_now": None, "fab_cuts": {s: CUTS},
                 "groups": [{"big": "x" * 1000}]}
            return self._send(200, json.dumps(d, ensure_ascii=False), "application/json")
        if u.path == "/api/graph":
            at = q.get("at", "")
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200" data-sys="{s}" '
                   f'data-theme="{q.get("theme", "")}" data-min="{q.get("minutes", "")}">'
                   f'<rect class="ghit" data-at="{at}" x="0" y="0" width="10" height="10"/></svg>')
            return self._send(200, svg, "image/svg+xml; charset=utf-8")
        if u.path == "/api/contrib":
            return self._send(200, '<div class="note">기여도 추정 (가짜)</div>', "text/html; charset=utf-8")
        if u.path == "/api/oht_map/report":
            name = q.get("name", "")
            return self._send(200, f"<html><body>{name}</body></html>", "text/html",
                              {"Content-Disposition": f'attachment; filename="{name}"'})
        return self._send(404, "{}", "application/json")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18989
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
