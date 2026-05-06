# -*- coding: utf-8 -*-
"""
main.py — UDP 수신 메인 (M14A:3710, M16A_BR:3750 두 포트 동시 수신)

사용법
    python3 main.py
        UDP listen :3710 (M14A) + :3750 (M16A_BR)
        HTTP UI    :11000

API
    GET /api/state          전체 상태
    GET /api/recent?fab=M14A&n=50    최근 N건
    GET /api/stream         SSE (Server-Sent Events) — 신규 패킷 실시간 푸시
    POST /api/clear         통계/버퍼 초기화
"""

import json
import socket
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import config


HTML_PATH = Path(__file__).parent / "templates" / "main.html"
RECENT_BUF = 500       # FAB 별 최근 패킷 버퍼
SSE_QUEUE  = 200       # SSE 클라이언트별 펜딩 큐


# ─────────────────────────────────────────────────────
# 수신 워커
# ─────────────────────────────────────────────────────
class FabReceiver:
    def __init__(self, fab: str, port: int):
        self.fab = fab
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        try:
            self.sock.bind(("0.0.0.0", port))
        except OSError as e:
            print(f"[ERR] bind {fab}:{port} failed — {e}")
            raise

        self.recent: Deque[Dict] = deque(maxlen=RECENT_BUF)
        self.lock = threading.Lock()

        # 통계
        self.rx_packets = 0
        self.rx_rows    = 0
        self.rx_bytes   = 0
        self.first_at: Optional[datetime] = None
        self.last_at: Optional[datetime]  = None
        self.last_ts:  Optional[str] = None
        self.last_addr: Optional[Tuple[str, int]] = None
        self.last_error: Optional[str] = None

        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def stats(self) -> Dict:
        return {
            "fab": self.fab,
            "port": self.port,
            "rx_packets": self.rx_packets,
            "rx_rows": self.rx_rows,
            "rx_bytes": self.rx_bytes,
            "first_at": self.first_at.isoformat() if self.first_at else None,
            "last_at":  self.last_at.isoformat() if self.last_at else None,
            "last_ts":  self.last_ts,
            "last_addr": list(self.last_addr) if self.last_addr else None,
            "buffer": len(self.recent),
            "last_error": self.last_error,
        }

    def recent_list(self, n: int = 50) -> List[Dict]:
        with self.lock:
            return list(self.recent)[-max(1, min(n, RECENT_BUF)):]

    def clear(self):
        with self.lock:
            self.recent.clear()
        self.rx_packets = 0
        self.rx_rows = 0
        self.rx_bytes = 0
        self.first_at = None
        self.last_at = None
        self.last_ts = None
        self.last_addr = None
        self.last_error = None

    def _loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(config.UDP_BUFFER_SIZE)
            except OSError as e:
                self.last_error = f"recv: {e}"
                time.sleep(0.1)
                continue

            self.rx_packets += 1
            self.rx_bytes += len(data)
            self.last_at = datetime.now()
            if self.first_at is None:
                self.first_at = self.last_at
            self.last_addr = addr

            pkt = self._parse(data)
            if pkt is None:
                continue

            self.rx_rows += pkt.get("count", len(pkt.get("rows", [])))
            self.last_ts = pkt.get("ts")

            entry = {
                "rx_at": self.last_at.isoformat(),
                "from":  f"{addr[0]}:{addr[1]}",
                "size":  len(data),
                "fab":   pkt.get("fab", self.fab),
                "ts":    pkt.get("ts"),
                "count": pkt.get("count", len(pkt.get("rows", []))),
                "rows":  pkt.get("rows", []),
            }
            with self.lock:
                self.recent.append(entry)
            HUB.broadcast(self.fab, entry)

    @staticmethod
    def _parse(data: bytes) -> Optional[Dict]:
        text = data.decode("utf-8", errors="ignore").lstrip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        if text.startswith("#FAB="):  # csv 모드
            head, _, body = text.partition("\n")
            meta = {}
            for kv in head.lstrip("#").split(";"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    meta[k.strip()] = v.strip()
            import csv as csvmod
            import io
            rows = list(csvmod.DictReader(io.StringIO(body)))
            return {
                "fab":   meta.get("FAB"),
                "ts":    meta.get("TS"),
                "count": int(meta.get("N", len(rows))),
                "rows":  rows,
            }
        return None


# ─────────────────────────────────────────────────────
# SSE 허브 (수신 → 브라우저)
# ─────────────────────────────────────────────────────
class SseHub:
    def __init__(self):
        self.clients: List["queue.Queue"] = []   # type: ignore
        self.lock = threading.Lock()

    def subscribe(self):
        import queue
        q: queue.Queue = queue.Queue(maxsize=SSE_QUEUE)
        with self.lock:
            self.clients.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def broadcast(self, fab: str, entry: Dict):
        slim = {
            "fab":   entry["fab"],
            "ts":    entry["ts"],
            "rx_at": entry["rx_at"],
            "from":  entry["from"],
            "count": entry["count"],
            "size":  entry["size"],
            "sample": entry["rows"][:3],
        }
        msg = json.dumps(slim, ensure_ascii=False)
        with self.lock:
            dead = []
            for q in self.clients:
                try:
                    q.put_nowait(msg)
                except Exception:
                    dead.append(q)
            for q in dead:
                self.clients.remove(q)


HUB = SseHub()


# ─────────────────────────────────────────────────────
# HTTP UI / API
# ─────────────────────────────────────────────────────
RECEIVERS: Dict[str, FabReceiver] = {}


class MainHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, code: int, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str, ctype="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ── routes ─────────────────────────────────────
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path

        if path in ("/", "/index.html"):
            html = HTML_PATH.read_text(encoding="utf-8")
            html = html.replace("{{UDP_PORT_M14A}}",    str(config.UDP_PORT_M14A))
            html = html.replace("{{UDP_PORT_M16A_BR}}", str(config.UDP_PORT_M16A_BR))
            self._send_text(200, html, "text/html; charset=utf-8")
            return

        if path == "/api/state":
            out = {
                "now":     datetime.now().isoformat(),
                "udp": {
                    "M14A":    {"port": config.UDP_PORT_M14A},
                    "M16A_BR": {"port": config.UDP_PORT_M16A_BR},
                },
                "fabs": {k: v.stats() for k, v in RECEIVERS.items()},
            }
            self._send_json(200, out)
            return

        if path == "/api/recent":
            qs = parse_qs(u.query)
            fab = (qs.get("fab", ["M14A"])[0] or "").upper()
            n   = int(qs.get("n", ["50"])[0])
            r = RECEIVERS.get(fab)
            if not r:
                self._send_json(404, {"error": "unknown fab", "fab": fab})
                return
            self._send_json(200, {"fab": fab, "rows": r.recent_list(n)})
            return

        if path == "/api/stream":
            self._stream()
            return

        self._send_json(404, {"error": "not_found", "path": path})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/clear":
            for r in RECEIVERS.values():
                r.clear()
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "not_found", "path": path})

    # ── SSE stream ─────────────────────────────────
    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        q = HUB.subscribe()
        try:
            self.wfile.write(b"retry: 2000\n\n")
            self.wfile.flush()
            last_ping = time.time()
            while True:
                try:
                    msg = q.get(timeout=1.0)
                    self.wfile.write(b"data: " + msg.encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                except Exception:
                    if time.time() - last_ping > 15:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        last_ping = time.time()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            HUB.unsubscribe(q)


# ─────────────────────────────────────────────────────
def main():
    try:
        m14 = FabReceiver("M14A",    config.UDP_PORT_M14A)
        m16 = FabReceiver("M16A_BR", config.UDP_PORT_M16A_BR)
    except OSError:
        return 2

    RECEIVERS["M14A"]    = m14
    RECEIVERS["M16A_BR"] = m16
    m14.start()
    m16.start()

    print("=" * 60)
    print("OHT UDP MAIN RECEIVER")
    print(f"  UDP listen : M14A→{config.UDP_PORT_M14A}  M16A_BR→{config.UDP_PORT_M16A_BR}")
    print(f"  HTTP UI    : http://127.0.0.1:{config.HTTP_PORT_MAIN}")
    print("=" * 60)

    httpd = ThreadingHTTPServer(("0.0.0.0", config.HTTP_PORT_MAIN), MainHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
