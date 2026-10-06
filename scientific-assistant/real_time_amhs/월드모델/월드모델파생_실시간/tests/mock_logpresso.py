#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가짜 로그프레소 — 시험 · 화면 확인용. 진짜 데이터는 하나도 없다 (차 번호 · 운반물 다 지어낸 것).

    python tests/mock_logpresso.py 18888          (키: 환경변수 MOCK_LP_KEY, 기본 'dummy-key')

진짜와 같은 주소로 받는다:
    /logpresso/httpexport/query.csv?_apikey=…&_q=table from=yyyyMMddHHmmss to=… <테이블> | …
키가 틀리면 401 (진짜처럼 로그인 화면 HTML). 테이블 이름으로 지도(OHT_MAP/cache)를 골라
그 지도의 레일 고리를 따라 차를 돌린다 — **벽시계 기준**이라 '지금' 을 물으면 지금 위치가 온다.
    · 운행 32대   — 고리를 따라 돈다 (차마다 700~1600 단위/초), 2초마다 보고 (상태 1/3/4/5 섞어서)
    · HT_STOP 1대 — 한 자리, 상태 8, 10초마다 보고
    · JAM 4대     — 한 주소에 몰려 상태 7, 5초마다 보고 (정체 묶음이 생긴다)
    · 미보고 3대  — 멈춘 채(상태 2) 3분에 한 번만 보고 → 50초 넘으면 미보고
적재는 MOCK_LAG_SEC(3초) 늦게 된다 — 그 뒤 줄은 아직 없다.
"""
import csv
import io
import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WM_DIR = os.path.abspath(os.environ.get("WM_DIR") or os.path.join(HERE, "..", "..", "월드모델파생"))
CACHE = os.path.join(WM_DIR, "OHT_MAP", "cache")
KEY = os.environ.get("MOCK_LP_KEY", "dummy-key")
LAG = float(os.environ.get("MOCK_LAG_SEC", "3"))
FMT = "%Y%m%d%H%M%S"
HITS = {"n": 0, "last_q": ""}
CUT = {"n": 0}          # 0 이 아니면 응답을 그 바이트에서 끊는다 (진짜에서 난 IncompleteRead 흉내)

TABLE_MAP = {"oht_data_m14a": "M14A_A", "oht_data_m14b": "M14B_A", "oht_data_m16a": "M16A_A",
             "oht_data_m16b": "M16B_B", "oht_data_m16br": "M16A_BR"}
COLS = ["_time", "VEHICLE", "MSG_ID", "STATUS", "STOCK_INFO", "ADDRESS", "DISTANCE", "NEXT_ADDRESS",
        "EDGE", "CARRIER", "DESTINATION", "VEHICLE_EXECUTE_CYCLE", "OPERATION_STATUS"]


class World:
    """지도 하나의 가짜 차들. 같은 시각이면 늘 같은 줄을 낸다 (결정적)."""

    def __init__(self, name):
        with open(os.path.join(CACHE, f"{name}_layout_cache.json"), encoding="utf-8") as f:
            c = json.load(f)
        adj = {int(k): [int(x) for x in v] for k, v in c["adj"].items()}
        dist = {tuple(int(x) for x in k.split(",")): float(v) for k, v in c["edges"].items()}
        self.cycle = self._longest_cycle(adj, dist)
        self.edges = [(self.cycle[i], self.cycle[(i + 1) % len(self.cycle)]) for i in range(len(self.cycle))]
        self.lens = [dist.get(e, 500.0) for e in self.edges]
        self.total = sum(self.lens)
        rng = random.Random(7)
        n = len(self.edges)
        # ★간격 · 속도를 들쭉날쭉하게 — 똑같이 두면 몇 초 뒤 그림이 앞차 자리와 겹쳐 '안 움직이는' 것처럼 보인다
        self.movers = [{"vid": f"V{9000 + i:05d}", "off": rng.uniform(0, self.total),
                        "v": rng.uniform(700, 1600),
                        "full": i % 3 == 0, "cyc": 4 if i % 3 == 0 else 2,
                        "car": f"TEST{i:04d}" if i % 3 == 0 else ""} for i in range(32)]
        # 멈춘 차들 — 고리의 엣지 위 고정 자리
        jam_e = self.edges[n // 3]
        self.jams = [{"vid": f"V{9100 + i:05d}", "edge": jam_e, "d": 0} for i in range(4)]
        self.ht = {"vid": "V09200", "edge": self.edges[(2 * n) // 3], "d": int(self.lens[(2 * n) // 3] / 2)}
        self.miss = [{"vid": f"V{9300 + i:05d}", "edge": self.edges[rng.randrange(n)], "d": 0,
                      "phase": i * 37} for i in range(3)]

    @staticmethod
    def _longest_cycle(adj, dist):
        best = []
        rng = random.Random(11)
        starts = sorted(adj)
        for _ in range(60):
            cur = rng.choice(starts)
            path, pos = [], {}
            while cur not in pos and len(path) < 4000:
                pos[cur] = len(path)
                path.append(cur)
                nbs = adj.get(cur) or []
                if not nbs:
                    break
                cur = rng.choice(nbs)
            if cur in pos:
                cyc = path[pos[cur]:]
                if len(cyc) > len(best):
                    best = cyc
        if len(best) < 3:
            raise SystemExit("레일 고리를 못 찾았습니다")
        return best

    def _at(self, s):
        s %= self.total
        for e, ln in zip(self.edges, self.lens):
            if s < ln:
                return e, int(s)
            s -= ln
        return self.edges[-1], 0

    def rows(self, t0: datetime, t1: datetime):
        """[t0, t1) 의 보고 줄 — 정수 초마다 훑는다."""
        out = []
        t = t0.replace(microsecond=0)
        if t < t0:
            t += timedelta(seconds=1)
        while t < t1:
            sec = int(t.timestamp())
            for i, m in enumerate(self.movers):
                if (sec + i) % 2:
                    continue                                  # 2초마다 (차마다 엇갈려)
                e, d = self._at(m["off"] + m["v"] * sec)       # 차마다 700~1600 단위/초
                st = (1, 3, 4, 5)[(sec // 7 + i) % 4]
                out.append(self._row(t, m["vid"], st, m["full"], e, d, m["car"], m["cyc"]))
            for i, j in enumerate(self.jams):
                if (sec + i) % 5 == 0:
                    out.append(self._row(t, j["vid"], 7, False, j["edge"], j["d"], "", 0))
            if sec % 10 == 0:
                h = self.ht
                out.append(self._row(t, h["vid"], 8, True, h["edge"], h["d"], "TEST-HT", 4))
            for m in self.miss:
                if (sec + m["phase"]) % 180 == 0:
                    out.append(self._row(t, m["vid"], 2, False, m["edge"], m["d"], "", 0))
            t += timedelta(seconds=1)
        out.sort(key=lambda r: r["_time"])
        return out

    @staticmethod
    def _row(t, vid, st, full, e, d, car, cyc):
        return {"_time": t.strftime("%Y-%m-%d %H:%M:%S"), "VEHICLE": vid, "MSG_ID": "2", "STATUS": str(st),
                "STOCK_INFO": "1" if full else "0", "ADDRESS": str(e[0]), "DISTANCE": str(d),
                "NEXT_ADDRESS": str(e[1]), "EDGE": f"{e[0]}-{e[1]}", "CARRIER": car,
                "DESTINATION": "0", "VEHICLE_EXECUTE_CYCLE": str(cyc), "OPERATION_STATUS": "1"}


_WORLDS = {}


def world(table):
    name = TABLE_MAP.get(table)
    if not name:
        return None
    if name not in _WORLDS:
        _WORLDS[name] = World(name)
    return _WORLDS[name]


_Q = re.compile(r"table\s+from=(\d{14})\s+to=(\d{14})\s+([A-Za-z0-9_]+)")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/mock/cut":
            CUT["n"] = int((q.get("bytes") or ["0"])[0])
            self.send_response(200)
            self.end_headers()
            return self.wfile.write(b"ok")
        if u.path == "/mock/hits":
            body = json.dumps(HITS).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return self.wfile.write(body)
        if u.path != "/logpresso/httpexport/query.csv":
            self.send_response(404)
            self.end_headers()
            return
        if (q.get("_apikey") or [""])[0] != KEY:
            body = b"<html><body>login</body></html>"
            self.send_response(401)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            return self.wfile.write(body)
        m = _Q.search((q.get("_q") or [""])[0])
        HITS["n"] += 1
        HITS["last_q"] = (q.get("_q") or [""])[0]
        w = world(m.group(3)) if m else None
        if not m or w is None:
            self.send_response(500)
            self.end_headers()
            return self.wfile.write(b"bad query or table")
        t0 = datetime.strptime(m.group(1), FMT)
        t1 = min(datetime.strptime(m.group(2), FMT), datetime.now() - timedelta(seconds=LAG))
        rows = w.rows(t0, t1) if t1 > t0 else []
        buf = io.StringIO()
        wr = csv.DictWriter(buf, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(rows)
        body = buf.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if CUT["n"] and len(body) > CUT["n"]:
            self.wfile.write(body[:CUT["n"]])          # 길이는 다 준다고 해 놓고 중간에 끊는다
            self.close_connection = True
            return
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18888
    print(f"[가짜 로그프레소] :{port} · 키 {KEY[:2]}… · 적재 지연 {LAG}초")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
