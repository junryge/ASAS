# -*- coding: utf-8 -*-
"""
sender.py — LOGPRESSO_OHT_DATA CSV → UDP 송신기

사용법
    python3 sender.py m14a       # M14A → UDP 3710 + 송신 UI :11010
    python3 sender.py m16a_br    # M16A_BR → UDP 3750 + 송신 UI :11020

웹 UI
    http://localhost:11010 (M14A)
    http://localhost:11020 (M16A_BR)

API
    GET  /api/status     송신 상태/통계
    POST /api/start      송신 시작
    POST /api/pause      일시정지
    POST /api/resume     재개
    POST /api/stop       정지 + 처음으로
    POST /api/speed      속도 변경  (body: {"speed": 60})
    POST /api/loop       루프 토글  (body: {"loop": true})
    POST /api/seek       위치 이동  (body: {"ratio": 0.0~1.0})
"""

import json
import socket
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import config
from csv_loader import OhtCsvLoader, serialize_json, serialize_csv


# ─────────────────────────────────────────────────────
# FAB 프로필
# ─────────────────────────────────────────────────────
FAB_PROFILES: Dict[str, Dict] = {
    "m14a": {
        "fab": "M14A",
        "csv": config.CSV_FILE_M14A,
        "udp_port": config.UDP_PORT_M14A,
        "http_port": config.HTTP_PORT_SENDER_M14A,
        "color": "#22c55e",
    },
    "m16a_br": {
        "fab": "M16A_BR",
        "csv": config.CSV_FILE_M16A_BR,
        "udp_port": config.UDP_PORT_M16A_BR,
        "http_port": config.HTTP_PORT_SENDER_M16A_BR,
        "color": "#3b82f6",
    },
}


# ─────────────────────────────────────────────────────
# 송신 워커
# ─────────────────────────────────────────────────────
class SenderWorker:
    def __init__(self, fab: str, csv_path: str, udp_host: str, udp_port: int):
        self.fab = fab
        self.csv_path = csv_path
        self.udp_host = udp_host
        self.udp_port = udp_port

        self.loader = OhtCsvLoader(
            csv_path,
            replay_start=config.REPLAY_START,
            replay_end=config.REPLAY_END,
        )

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)

        # 상태
        self.lock     = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.running  = False
        self.paused   = False
        self.stop_flag= False

        self.speed    = float(config.DEFAULT_SPEED)
        self.loop     = True
        self.seek_ratio: Optional[float] = None

        # 통계
        self.tx_packets = 0
        self.tx_rows    = 0
        self.tx_bytes   = 0
        self.cur_idx    = 0
        self.cur_ts: Optional[datetime] = None
        self.last_tx: Optional[datetime] = None
        self.cycle    = 0
        self.last_error: Optional[str] = None
        self.start_real: Optional[float] = None

    # ── load ────────────────────────────────────────
    def load(self) -> int:
        n = self.loader.load()
        return n

    # ── start / pause / resume / stop ───────────────
    def start(self):
        with self.lock:
            if self.running:
                return False
            if not self.loader.loaded:
                self.loader.load()
            if self.loader.total_rows() == 0:
                self.last_error = f"CSV not found or empty: {self.csv_path}"
                return False
            self.running = True
            self.paused = False
            self.stop_flag = False
            self.cur_idx = 0
            self.tx_packets = 0
            self.tx_rows = 0
            self.tx_bytes = 0
            self.cycle = 0
            self.start_real = time.time()
            self.last_error = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def pause(self):  self.paused = True
    def resume(self): self.paused = False
    def stop(self):
        self.stop_flag = True
        self.running = False

    def set_speed(self, s: float):
        self.speed = max(0.1, min(s, 3600.0))

    def set_loop(self, b: bool):
        self.loop = bool(b)

    def seek(self, ratio: float):
        self.seek_ratio = max(0.0, min(1.0, ratio))

    # ── status ──────────────────────────────────────
    def status(self) -> Dict:
        rng = self.loader.time_range()
        first = rng[0].isoformat() if rng[0] else None
        last  = rng[1].isoformat() if rng[1] else None
        return {
            "fab": self.fab,
            "csv": self.csv_path,
            "csv_exists": self.loader.exists(),
            "rows_total": self.loader.total_rows(),
            "rows_first_ts": first,
            "rows_last_ts": last,
            "udp_host": self.udp_host,
            "udp_port": self.udp_port,
            "running": self.running,
            "paused": self.paused,
            "speed": self.speed,
            "loop": self.loop,
            "cycle": self.cycle,
            "tx_packets": self.tx_packets,
            "tx_rows": self.tx_rows,
            "tx_bytes": self.tx_bytes,
            "cur_idx": self.cur_idx,
            "cur_ts": self.cur_ts.isoformat() if self.cur_ts else None,
            "last_tx": self.last_tx.isoformat() if self.last_tx else None,
            "elapsed_real_sec": (time.time() - self.start_real) if self.start_real else 0,
            "last_error": self.last_error,
        }

    # ── 송신 루프 (스트리밍) ────────────────────────
    def _run(self):
        if not self.loader.time_col:
            self.last_error = "time column not detected"
            self.running = False
            return

        total = self.loader.total_rows()
        try:
            while not self.stop_flag:
                # 이번 cycle 의 시작 위치 (seek 적용)
                seek = self.seek_ratio
                self.seek_ratio = None
                start_idx = int(seek * total) if seek is not None and total > 0 else 0
                self.cur_idx = start_idx

                last_sent_ts: Optional[datetime] = None
                consumed_any = False

                # CSV 처음부터 스트리밍 (start_idx 만큼 건너뛰고 시작)
                for ts0, batch, new_idx in self.loader.iter_groups(start_at_idx=start_idx):
                    if self.stop_flag:
                        return
                    if self.seek_ratio is not None:
                        # 새 seek → 안쪽 for 탈출 → 바깥 while 에서 재시작
                        break

                    # 다음 group 까지 대기 (현재 ts - 직전 ts)
                    if last_sent_ts is not None:
                        wait_sec = self._sleep_for(last_sent_ts, ts0)
                        # pause/stop 처리
                        while wait_sec > 0 and not self.stop_flag:
                            if self.seek_ratio is not None:
                                break
                            if self.paused:
                                time.sleep(0.1)
                                continue
                            chunk = min(0.1, wait_sec)
                            time.sleep(chunk)
                            wait_sec -= chunk
                        if self.seek_ratio is not None:
                            break

                    if self.stop_flag:
                        return
                    if self.paused:
                        # paused 인 동안 송신 안 하고 대기
                        while self.paused and not self.stop_flag and self.seek_ratio is None:
                            time.sleep(0.1)
                        if self.stop_flag:
                            return
                        if self.seek_ratio is not None:
                            break

                    self._send_batch(ts0, batch)
                    self.cur_idx = new_idx
                    last_sent_ts = ts0
                    consumed_any = True

                if self.stop_flag:
                    return
                if self.seek_ratio is not None:
                    continue   # 새 seek 로 재시작
                if not self.loop:
                    break
                # cycle 끝 → 처음부터
                if consumed_any:
                    self.cycle += 1

        except Exception as e:
            self.last_error = f"runtime: {e!r}"
        finally:
            self.running = False

    def _send_batch(self, ts: datetime, rows: List[Dict[str, str]]):
        if not rows:
            return
        max_n = max(1, config.MAX_ROWS_PER_PACKET)
        for i in range(0, len(rows), max_n):
            chunk = rows[i:i + max_n]
            if config.PACKET_FORMAT == "csv":
                pkt = serialize_csv(self.fab, ts, chunk, self.loader.fieldnames)
            else:
                pkt = serialize_json(self.fab, ts, chunk)
            try:
                self.sock.sendto(pkt, (self.udp_host, self.udp_port))
            except OSError as e:
                self.last_error = f"sendto: {e}"
                continue
            self.tx_packets += 1
            self.tx_rows += len(chunk)
            self.tx_bytes += len(pkt)
            self.last_tx = datetime.now()
        self.cur_ts = ts

    def _sleep_for(self, cur_ts: datetime, next_ts: Optional[datetime]) -> float:
        if next_ts is None:
            return 0.0
        delta = (next_ts - cur_ts).total_seconds()
        if delta < 0:
            delta = 0.0
        return max(0.0, delta / max(self.speed, 0.001))


# ─────────────────────────────────────────────────────
# HTTP UI / API
# ─────────────────────────────────────────────────────
HTML_PATH = Path(__file__).parent / "templates" / "sender.html"


class SenderHandler(BaseHTTPRequestHandler):
    worker: SenderWorker = None       # 클래스 변수 (서버 시작 시 할당)
    profile: Dict = None

    # 로그 줄임
    def log_message(self, format, *args):
        pass

    # ── helpers ─────────────────────────────────────
    def _send_json(self, code: int, obj: Dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str, ctype: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict:
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return {}

    # ── routes ──────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html"):
            html = HTML_PATH.read_text(encoding="utf-8")
            html = html.replace("{{FAB}}", self.profile["fab"])
            html = html.replace("{{COLOR}}", self.profile["color"])
            html = html.replace("{{UDP_PORT}}", str(self.profile["udp_port"]))
            self._send_text(200, html, "text/html; charset=utf-8")
            return

        if path == "/api/status":
            self._send_json(200, self.worker.status())
            return

        self._send_json(404, {"error": "not_found", "path": path})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        body = self._read_json()

        if path == "/api/start":
            ok = self.worker.start()
            self._send_json(200, {"ok": ok, "status": self.worker.status()})
            return
        if path == "/api/pause":
            self.worker.pause()
            self._send_json(200, {"ok": True})
            return
        if path == "/api/resume":
            self.worker.resume()
            self._send_json(200, {"ok": True})
            return
        if path == "/api/stop":
            self.worker.stop()
            self._send_json(200, {"ok": True})
            return
        if path == "/api/speed":
            self.worker.set_speed(float(body.get("speed", config.DEFAULT_SPEED)))
            self._send_json(200, {"ok": True, "speed": self.worker.speed})
            return
        if path == "/api/loop":
            self.worker.set_loop(bool(body.get("loop", True)))
            self._send_json(200, {"ok": True, "loop": self.worker.loop})
            return
        if path == "/api/seek":
            self.worker.seek(float(body.get("ratio", 0.0)))
            self._send_json(200, {"ok": True})
            return

        self._send_json(404, {"error": "not_found", "path": path})


# ─────────────────────────────────────────────────────
def run(profile_key: str):
    if profile_key not in FAB_PROFILES:
        print(f"[ERR] unknown profile: {profile_key}  (m14a / m16a_br)")
        sys.exit(2)

    p = FAB_PROFILES[profile_key]
    worker = SenderWorker(p["fab"], p["csv"], config.UDP_HOST, p["udp_port"])
    n = worker.load()

    print("=" * 60)
    print(f"OHT UDP SENDER — {p['fab']}")
    print(f"  CSV       : {p['csv']}  ({'EXISTS' if worker.loader.exists() else 'NOT FOUND'})")
    print(f"  rows      : {n}")
    rng = worker.loader.time_range()
    print(f"  time range: {rng[0]} ~ {rng[1]}")
    print(f"  UDP       : {config.UDP_HOST}:{p['udp_port']}")
    print(f"  HTTP UI   : http://127.0.0.1:{p['http_port']}")
    print("=" * 60)

    SenderHandler.worker  = worker
    SenderHandler.profile = p

    httpd = ThreadingHTTPServer(("0.0.0.0", p["http_port"]), SenderHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        worker.stop()
        httpd.shutdown()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    run(arg.lower())
