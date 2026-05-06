# -*- coding: utf-8 -*-
"""
server.py — UDP_SIM 서버

- UDP 3710/3750 수신 (OHT_UDP_SIM/sender.py 가 보낸 패킷)
- 차량별 마지막 상태 유지 (currentNode/nextNode/distance/state/_time)
- WebSocket 으로 브라우저에 4Hz 로 푸시
- HTTP / 대시보드 / API
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

import config
from layout import Layout


# ─────────────────────────────────────────────────────
# 차량 상태
# ─────────────────────────────────────────────────────
STATE_NAMES = {
    1: "RUN", 2: "WAIT", 3: "OBS_BZ_STOP", 4: "MAINT", 5: "STOP",
    6: "OBS_STOP", 7: "EMERG", 8: "STANDBY",
}


@dataclass
class Vehicle:
    vid: str
    fab: str
    state: int = 1
    is_full: int = 0
    current_node: int = 0
    next_node: int = 0
    distance: int = 0
    destination: int = 0
    speed: int = 0
    source_port: str = ""
    dest_port:   str = ""
    last_ts:     Optional[datetime] = None      # CSV `_time`
    last_rx:     Optional[datetime] = None      # 우리 수신 시각

    def to_dict(self, layout: Layout) -> dict:
        pos = layout.get_position(self.current_node, self.next_node, self.distance) \
              if layout.loaded else None
        return {
            "vid": self.vid,
            "fab": self.fab,
            "state": self.state,
            "stateName": STATE_NAMES.get(self.state, f"S{self.state}"),
            "isFull": self.is_full,
            "currentNode": self.current_node,
            "nextNode":    self.next_node,
            "distance":    self.distance,
            "destination": self.destination,
            "speed":       self.speed,
            "sourcePort":  self.source_port,
            "destPort":    self.dest_port,
            "x": round(pos[0], 1) if pos else None,
            "y": round(pos[1], 1) if pos else None,
            "ts":   self.last_ts.isoformat() if self.last_ts else None,
            "rxAt": self.last_rx.isoformat() if self.last_rx else None,
        }


# ─────────────────────────────────────────────────────
# 행 → vehicle 변환 (LOGPRESSO 표준 + OHT_DATA_M14A 양식 모두 대응)
# ─────────────────────────────────────────────────────
def _i(row: dict, *keys, default: int = 0) -> int:
    for k in keys:
        v = row.get(k)
        if v in (None, ""): continue
        try:
            return int(float(v))
        except (TypeError, ValueError):
            continue
    return default


def _s(row: dict, *keys, default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v)
    return default


def parse_row(row: dict, fab: str) -> Optional[dict]:
    vid = _s(row, "VHL_ID", "VEHICLE", "vid")
    if not vid:
        return None
    cur = _i(row, "ADDRESS", "CURRENT_ADDR", "FROM_HIDID")
    nxt = _i(row, "NEXT_ADDRESS", "NEXT_ADDR", "TO_HIDID")
    if cur == 0 and nxt == 0:
        return None
    return {
        "vid": vid,
        "fab": fab,
        "state":       _i(row, "STATUS", "STATE", default=1),
        "is_full":     _i(row, "STOCK_INFO", "IS_FULL"),
        "current_node": cur,
        "next_node":    nxt,
        "distance":    _i(row, "DISTANCE", "DISTANCE_MM", "TRANS_CNT"),
        "destination": _i(row, "DESTINATION"),
        "speed":       _i(row, "SPEED", "FREE_FLOW_SPEED"),
        "source_port": _s(row, "FROM_RETURN_PORT", "SOURCE_PORT"),
        "dest_port":   _s(row, "DEST_RETURN_PORT", "DEST_PORT"),
    }


# ─────────────────────────────────────────────────────
# UDP 수신기
# ─────────────────────────────────────────────────────
class FabReceiver(threading.Thread):
    def __init__(self, fab: str, port: int, store: "VehicleStore"):
        super().__init__(daemon=True, name=f"udp-{fab}")
        self.fab   = fab
        self.port  = port
        self.store = store
        self.sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)

        self.rx_packets = 0
        self.rx_rows    = 0
        self.rx_bytes   = 0
        self.first_at:  Optional[datetime] = None
        self.last_at:   Optional[datetime] = None
        self.last_ts:   Optional[str] = None
        self.last_addr: Optional[Tuple[str, int]] = None
        self.last_error: Optional[str] = None
        self._bound = False

    def bind(self) -> bool:
        try:
            self.sock.bind((config.UDP_HOST, self.port))
            self._bound = True
            return True
        except OSError as e:
            self.last_error = f"bind: {e}"
            return False

    def stats(self) -> dict:
        return {
            "fab": self.fab, "port": self.port, "bound": self._bound,
            "rx_packets": self.rx_packets, "rx_rows": self.rx_rows,
            "rx_bytes": self.rx_bytes,
            "first_at": self.first_at.isoformat() if self.first_at else None,
            "last_at":  self.last_at.isoformat()  if self.last_at  else None,
            "last_ts":  self.last_ts,
            "last_addr": list(self.last_addr) if self.last_addr else None,
            "last_error": self.last_error,
        }

    def run(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(config.UDP_BUFFER_SIZE)
            except OSError as e:
                self.last_error = f"recv: {e}"
                return

            self.rx_packets += 1
            self.rx_bytes   += len(data)
            now = datetime.now()
            if self.first_at is None:
                self.first_at = now
            self.last_at   = now
            self.last_addr = addr

            pkt = self._parse(data)
            if pkt is None:
                continue
            self.last_ts = pkt.get("ts")
            ts_dt = _parse_ts(pkt.get("ts") or "")
            for row in pkt.get("rows") or []:
                vd = parse_row(row, self.fab)
                if vd is None:
                    continue
                self.rx_rows += 1
                self.store.update(vd, ts_dt, now)

    @staticmethod
    def _parse(data: bytes) -> Optional[dict]:
        text = data.decode("utf-8", errors="ignore").lstrip()
        if not text:
            return None
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        if text.startswith("#FAB="):
            head, _, body = text.partition("\n")
            meta = {}
            for kv in head.lstrip("#").split(";"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    meta[k.strip()] = v.strip()
            import csv as csvmod, io
            rows = list(csvmod.DictReader(io.StringIO(body)))
            return {"fab": meta.get("FAB"), "ts": meta.get("TS"),
                    "count": int(meta.get("N", len(rows))), "rows": rows}
        return None


def _parse_ts(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    import re
    s = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", s)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ─────────────────────────────────────────────────────
# 차량 저장소
# ─────────────────────────────────────────────────────
class VehicleStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.vehicles: Dict[Tuple[str, str], Vehicle] = {}  # (fab, vid) -> Vehicle

    def update(self, vd: dict, ts: Optional[datetime], rx_at: datetime):
        key = (vd["fab"], vd["vid"])
        with self.lock:
            v = self.vehicles.get(key)
            if v is None:
                v = Vehicle(vid=vd["vid"], fab=vd["fab"])
                self.vehicles[key] = v
            v.state         = vd["state"]
            v.is_full       = vd["is_full"]
            v.current_node  = vd["current_node"]
            v.next_node     = vd["next_node"]
            v.distance      = vd["distance"]
            v.destination   = vd["destination"]
            v.speed         = vd["speed"]
            v.source_port   = vd["source_port"]
            v.dest_port     = vd["dest_port"]
            v.last_ts       = ts
            v.last_rx       = rx_at

    def snapshot(self, fabs: List[str], layouts: Dict[str, Layout]) -> List[dict]:
        cutoff = datetime.now() - timedelta(seconds=config.VEHICLE_STALE_SEC)
        out: List[dict] = []
        with self.lock:
            for (fab, _), v in self.vehicles.items():
                if fab not in fabs:
                    continue
                if v.last_rx and v.last_rx < cutoff:
                    continue
                out.append(v.to_dict(layouts.get(fab) or Layout(fab, Path("/dev/null"))))
        return out

    def stats(self) -> dict:
        cutoff = datetime.now() - timedelta(seconds=config.VEHICLE_STALE_SEC)
        per_fab: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "live": 0})
        with self.lock:
            for (fab, _), v in self.vehicles.items():
                per_fab[fab]["total"] += 1
                if v.last_rx and v.last_rx >= cutoff:
                    per_fab[fab]["live"] += 1
        return {f: dict(s) for f, s in per_fab.items()}


# ─────────────────────────────────────────────────────
# FastAPI + WebSocket
# ─────────────────────────────────────────────────────
app = FastAPI(title="UDP_SIM — 실시간 OHT 위치", version="1.0")

LAYOUTS: Dict[str, Layout] = {
    "M14A":    Layout("M14A",    config.LAYOUT_FILE_M14A).load(),
    "M16A_BR": Layout("M16A_BR", config.LAYOUT_FILE_M16A_BR).load(),
}
STORE = VehicleStore()
RECEIVERS: Dict[str, FabReceiver] = {
    "M14A":    FabReceiver("M14A",    config.UDP_PORT_M14A,    STORE),
    "M16A_BR": FabReceiver("M16A_BR", config.UDP_PORT_M16A_BR, STORE),
}
WS_CLIENTS: List[WebSocket] = []


@app.on_event("startup")
async def startup():
    for r in RECEIVERS.values():
        if r.bind():
            r.start()
    print(f"[UDP_SIM] HTTP {config.HTTP_HOST}:{config.HTTP_PORT}")
    for fab, lo in LAYOUTS.items():
        print(f"[layout] {fab}: nodes={len(lo.nodes)} edges={len(lo.edges)} bounds={lo.bounds}")
    asyncio.create_task(_ws_pusher())


@app.get("/", response_class=HTMLResponse)
async def index():
    p = Path(__file__).parent / "dashboard.html"
    return p.read_text(encoding="utf-8")


@app.get("/api/state")
async def api_state():
    return {
        "now": datetime.now().isoformat(),
        "udp": {fab: r.stats() for fab, r in RECEIVERS.items()},
        "layouts": {fab: lo.stats() for fab, lo in LAYOUTS.items()},
        "vehicles": STORE.stats(),
    }


@app.get("/api/layout")
async def api_layout(fab: str = "M14A"):
    """배경 지도용 노드/엣지 (FAB 1개만)."""
    fab = fab.upper()
    lo = LAYOUTS.get(fab)
    if lo is None or not lo.loaded:
        return JSONResponse({"error": f"layout not loaded: {fab}"}, status_code=404)
    nodes = {str(nid): [round(c[0], 1), round(c[1], 1)] for nid, c in lo.nodes.items()}
    edges = []
    for (a, b), _ in lo.edges.items():
        if a in lo.nodes and b in lo.nodes:
            edges.append([a, b])
    return {"fab": fab, "nodes": nodes, "edges": edges, "bounds": list(lo.bounds)}


@app.get("/api/vehicles")
async def api_vehicles(fab: str = ""):
    fabs = [fab.upper()] if fab else list(LAYOUTS.keys())
    return {"vehicles": STORE.snapshot(fabs, LAYOUTS)}


# ── WebSocket: 4Hz 로 차량 푸시 ──
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    WS_CLIENTS.append(websocket)
    try:
        while True:
            msg = await websocket.receive_text()      # keep-alive (ping 등)
            _ = msg
    except WebSocketDisconnect:
        if websocket in WS_CLIENTS:
            WS_CLIENTS.remove(websocket)
    except Exception:
        if websocket in WS_CLIENTS:
            WS_CLIENTS.remove(websocket)


async def _ws_pusher():
    fabs = list(LAYOUTS.keys())
    while True:
        try:
            payload = {
                "ts": datetime.now().isoformat(),
                "udp": {fab: r.stats() for fab, r in RECEIVERS.items()},
                "vehicles": STORE.snapshot(fabs, LAYOUTS),
            }
            text = json.dumps(payload, default=str)
            dead = []
            for ws in WS_CLIENTS:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in WS_CLIENTS:
                    WS_CLIENTS.remove(ws)
        except Exception as e:
            print(f"[WS] pusher 오류: {e}")
        await asyncio.sleep(config.WS_PUSH_INTERVAL_S)


# ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  UDP_SIM — 실시간 OHT 차량 위치 (UDP 수신)")
    print(f"  UDP    : M14A:{config.UDP_PORT_M14A}  M16A_BR:{config.UDP_PORT_M16A_BR}")
    print(f"  WEB    : http://localhost:{config.HTTP_PORT}")
    print("=" * 60)
    uvicorn.run(app, host=config.HTTP_HOST, port=config.HTTP_PORT, log_level="warning")


if __name__ == "__main__":
    main()
