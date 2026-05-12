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
from csv_loader import OhtCsvLoader, serialize_json, serialize_csv, serialize_raw_line


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
        self.data_repeat = 1            # 같은 패킷을 N 번 반복 송신 (UDP 부하 ↑)

        # 통계
        self.tx_packets = 0
        self.tx_rows    = 0
        self.tx_bytes   = 0
        self.cur_byte   = 0     # 파일 byte 오프셋 (진행률용)
        # 초당 패킷 수 (pps) — 1초 윈도우 + 로그 기록
        from collections import deque
        self._pps_window: deque = deque(maxlen=10)   # (epoch_sec, packets, rows, bytes)
        self._pps_last_sec = 0
        self._pps_acc_pkt = 0
        self._pps_acc_row = 0
        self._pps_acc_byte = 0
        self.pps_packets = 0
        self.pps_rows    = 0
        self.pps_bytes   = 0
        self._log_path: Optional[Path] = None
        self._log_fp = None
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
            if not self.loader.exists() or self.loader.file_bytes == 0:
                self.last_error = f"CSV not found or empty: {self.csv_path}"
                return False
            if not self.loader.time_col:
                self.last_error = f"time column not detected. fieldnames={self.loader.fieldnames}"
                return False
            self.running = True
            self.paused = False
            self.stop_flag = False
            self.cur_byte = 0
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

    def set_host(self, host: str):
        h = (host or "").strip()
        if h:
            self.udp_host = h

    def set_data_repeat(self, n: int):
        self.data_repeat = max(1, min(int(n), 10000))

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
            "file_bytes": self.loader.file_bytes,
            "fieldnames": self.loader.fieldnames,
            "time_col":   self.loader.time_col,
            "rows_first_ts": first,
            "rows_last_ts": last,        # 대용량 모드는 None
            "udp_host": self.udp_host,
            "udp_port": self.udp_port,
            "running": self.running,
            "paused": self.paused,
            "speed": self.speed,
            "data_repeat": self.data_repeat,
            "loop": self.loop,
            "cycle": self.cycle,
            "tx_packets": self.tx_packets,
            "tx_rows": self.tx_rows,
            "tx_bytes": self.tx_bytes,
            "pps_packets": int(self.pps_packets),
            "pps_rows":    int(self.pps_rows),
            "pps_bytes":   int(self.pps_bytes),
            "log_path":    str(self._log_path) if self._log_path else None,
            "cur_byte": self.cur_byte,
            "cur_ts": self.cur_ts.isoformat() if self.cur_ts else None,
            "last_tx": self.last_tx.isoformat() if self.last_tx else None,
            "elapsed_real_sec": (time.time() - self.start_real) if self.start_real else 0,
            "last_error": self.last_error,
        }

    # ── 테스트 송신 (네트워크 검증용) ──────────────
    def send_test(self) -> Dict:
        """가짜 1 row 패킷을 즉시 송신 — 네트워크 연결 확인."""
        try:
            from datetime import datetime as _dt
            ts = _dt.now()
            row = {
                "_id":     "TEST",
                "_table":  f"{self.fab}_TEST",
                "_time":   ts.isoformat(),
                "line":    f"2,OHT,TEST{self.fab},1,1,0000,1,1,0,2,1,1,TESTCAR,999,SRC,DST,4,RUN,90,0,0",
            }
            fmt = config.PACKET_FORMAT
            if fmt == "csv":
                pkt = serialize_csv(self.fab, ts, [row], self.loader.fieldnames if self.loader.loaded else ["_id","_table","_time","line"])
            elif fmt == "json":
                pkt = serialize_json(self.fab, ts, [row])
            else:
                pkt = serialize_raw_line(self.fab, ts, [row])
            self.sock.sendto(pkt, (self.udp_host, self.udp_port))
            self.tx_packets += 1
            self.tx_rows += 1
            self.tx_bytes += len(pkt)
            self.last_tx = _dt.now()
            return {"ok": True, "bytes": len(pkt), "to": f"{self.udp_host}:{self.udp_port}"}
        except Exception as e:
            self.last_error = f"send_test: {e!r}"
            return {"ok": False, "error": str(e)}

    # ── 송신 루프 (byte 스트리밍) ───────────────────
    def _run(self):
        if not self.loader.time_col:
            self.last_error = "time column not detected"
            self.running = False
            return

        total_bytes = self.loader.file_bytes
        print(f"[{self.fab}] _run 시작 — file={total_bytes/1024/1024:.0f}MB time_col={self.loader.time_col}")
        try:
            while not self.stop_flag:
                # 이번 cycle 의 시작 위치 (seek 적용)
                seek = self.seek_ratio
                self.seek_ratio = None
                start_byte = int(seek * total_bytes) if seek is not None and total_bytes > 0 else 0
                self.cur_byte = start_byte

                last_sent_ts: Optional[datetime] = None
                consumed_any = False
                yielded = 0

                print(f"[{self.fab}] iter_groups(start_byte={start_byte})...")
                for ts0, batch, byte_pos in self.loader.iter_groups(start_byte=start_byte):
                    yielded += 1
                    if yielded == 1:
                        print(f"[{self.fab}] 첫 group: ts={ts0} rows={len(batch)} byte_pos={byte_pos}")
                    if self.stop_flag:
                        return
                    if self.seek_ratio is not None:
                        break

                    # 다음 group 까지 대기 (직전 ts → 현재 ts)
                    if last_sent_ts is not None:
                        wait_sec = self._sleep_for(last_sent_ts, ts0)
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
                        while self.paused and not self.stop_flag and self.seek_ratio is None:
                            time.sleep(0.1)
                        if self.stop_flag:
                            return
                        if self.seek_ratio is not None:
                            break

                    self._send_batch(ts0, batch)
                    self.cur_byte = byte_pos
                    last_sent_ts = ts0
                    consumed_any = True

                print(f"[{self.fab}] cycle 종료 — yielded={yielded} sent_packets={self.tx_packets} sent_rows={self.tx_rows}")
                if self.stop_flag:
                    return
                if self.seek_ratio is not None:
                    continue
                if not self.loop:
                    break
                if consumed_any:
                    self.cycle += 1
                else:
                    self.last_error = ("CSV 에서 유효한 row 가 한 개도 안 나옴. "
                                       "REPLAY 윈도우/시간컬럼/파싱 설정 확인.")
                    print(f"[{self.fab}] {self.last_error}")
                    break

        except Exception as e:
            self.last_error = f"runtime: {e!r}"
            print(f"[{self.fab}] 예외: {e!r}")
        finally:
            self.running = False

    def _send_batch(self, ts: datetime, rows: List[Dict[str, str]]):
        if not rows:
            return
        max_n = max(1, config.MAX_ROWS_PER_PACKET)
        for i in range(0, len(rows), max_n):
            chunk = rows[i:i + max_n]
            fmt = config.PACKET_FORMAT
            if fmt == "csv":
                pkt = serialize_csv(self.fab, ts, chunk, self.loader.fieldnames)
            elif fmt == "json":
                pkt = serialize_json(self.fab, ts, chunk)
            else:   # raw_line (기본)
                pkt = serialize_raw_line(self.fab, ts, chunk)
                if not pkt:
                    continue
            # 같은 패킷을 data_repeat 번 반복 송신.
            # 매 sendto 마다 self.data_repeat 를 다시 읽어 사용자 변경 즉각 반영.
            sent_n = 0
            while sent_n < max(1, int(self.data_repeat)):
                if self.stop_flag or self.paused:
                    break
                try:
                    self.sock.sendto(pkt, (self.udp_host, self.udp_port))
                except OSError as e:
                    self.last_error = f"sendto: {e}"
                    break
                self.tx_packets += 1
                self.tx_rows += len(chunk)
                self.tx_bytes += len(pkt)
                self._pps_acc_pkt  += 1
                self._pps_acc_row  += len(chunk)
                self._pps_acc_byte += len(pkt)
                sent_n += 1
            self.last_tx = datetime.now()
        self.cur_ts = ts
        self._tick_pps()

    def _tick_pps(self):
        """초가 바뀌면 직전 1초 pps 를 갱신 + 로그 한 줄."""
        now_sec = int(time.time())
        if self._pps_last_sec == 0:
            self._pps_last_sec = now_sec
            return
        if now_sec == self._pps_last_sec:
            return
        # 직전 초 마감
        elapsed = now_sec - self._pps_last_sec
        if elapsed <= 0: elapsed = 1
        pkt = self._pps_acc_pkt  / elapsed
        row = self._pps_acc_row  / elapsed
        byt = self._pps_acc_byte / elapsed
        self._pps_window.append((self._pps_last_sec, pkt, row, byt))
        self.pps_packets = pkt
        self.pps_rows    = row
        self.pps_bytes   = byt
        # 로그 파일 기록 (송신 측 — 부하 테스트 분석용)
        if self._log_fp is None:
            self._open_log()
        if self._log_fp is not None:
            try:
                ts = datetime.fromtimestamp(self._pps_last_sec).strftime("%Y-%m-%d %H:%M:%S")
                fb = self.loader.file_bytes or 1
                pct = (self.cur_byte / fb * 100) if fb else 0.0
                err = (self.last_error or "").replace(",", ";")
                self._log_fp.write(
                    f"{ts},{self.fab},{self.udp_host},{self.udp_port},"
                    f"{self.speed},{self.data_repeat},"
                    f"{int(pkt)},{int(row)},{int(byt)},"
                    f"{self.tx_packets},{self.tx_rows},{self.tx_bytes},"
                    f"{self.cur_byte},{self.loader.file_bytes},{pct:.2f},"
                    f"{self.cycle},{err}\n"
                )
                self._log_fp.flush()
            except Exception as e:
                self.last_error = f"log: {e}"
        # 초기화
        self._pps_acc_pkt = 0
        self._pps_acc_row = 0
        self._pps_acc_byte = 0
        self._pps_last_sec = now_sec

    def _open_log(self):
        try:
            log_dir = Path(__file__).parent / "logs"
            log_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_path = log_dir / f"sender_{self.fab}_{stamp}.csv"
            self._log_fp = open(self._log_path, "w", encoding="utf-8")
            self._log_fp.write(
                "time,fab,udp_host,udp_port,"
                "speed,data_repeat,"
                "tx_pps,tx_rps,tx_bps,"
                "tx_packets_total,tx_rows_total,tx_bytes_total,"
                "cur_byte,file_bytes,progress_pct,"
                "cycle,errors\n"
            )
        except Exception as e:
            self.last_error = f"log open: {e}"

    def _sleep_for(self, cur_ts: datetime, next_ts: Optional[datetime]) -> float:
        """ts 간격 만큼 sleep. CSV 가 descending 이어도 abs 로 동일 간격 유지."""
        if next_ts is None:
            return 0.0
        delta = abs((next_ts - cur_ts).total_seconds())
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
        if path == "/api/host":
            self.worker.set_host(str(body.get("host", "")))
            self._send_json(200, {"ok": True, "host": self.worker.udp_host})
            return
        if path == "/api/data_repeat":
            self.worker.set_data_repeat(int(body.get("repeat", 1)))
            self._send_json(200, {"ok": True, "data_repeat": self.worker.data_repeat})
            return
        if path == "/api/loop":
            self.worker.set_loop(bool(body.get("loop", True)))
            self._send_json(200, {"ok": True, "loop": self.worker.loop})
            return
        if path == "/api/seek":
            self.worker.seek(float(body.get("ratio", 0.0)))
            self._send_json(200, {"ok": True})
            return
        if path == "/api/test":
            res = self.worker.send_test()
            self._send_json(200, res)
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
