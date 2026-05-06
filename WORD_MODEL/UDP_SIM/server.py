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
    raw_x:       Optional[float] = None        # CSV 직접 좌표 (있으면 우선)
    raw_y:       Optional[float] = None
    last_ts:     Optional[datetime] = None      # CSV `_time`
    last_rx:     Optional[datetime] = None      # 우리 수신 시각

    def to_dict(self, layout: Layout) -> dict:
        # CSV 의 진짜 좌표가 있으면 그걸 그대로 사용 (가장 정확)
        if self.raw_x is not None and self.raw_y is not None:
            pos = (self.raw_x, self.raw_y)
        else:
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
# 컬럼 이름은 대소문자/언더바 무시 매칭 (LOGPRESSO 다양한 스키마 대응)
# ─────────────────────────────────────────────────────
def _norm(k: str) -> str:
    return "".join(c.lower() for c in str(k) if c.isalnum())


def _build_lookup(row: dict) -> Dict[str, str]:
    """row 의 키를 정규화된 alias 로 매핑. {정규화된키: 원본키}"""
    return {_norm(k): k for k in row.keys()}


def _get(row: dict, lookup: Dict[str, str], *aliases: str):
    for a in aliases:
        ak = _norm(a)
        if ak in lookup:
            v = row.get(lookup[ak])
            if v not in (None, ""):
                return v
    return None


def _i(row: dict, lookup: Dict[str, str], *aliases: str, default: int = 0) -> int:
    v = _get(row, lookup, *aliases)
    if v is None:
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _s(row: dict, lookup: Dict[str, str], *aliases: str, default: str = "") -> str:
    v = _get(row, lookup, *aliases)
    return str(v) if v is not None else default


def _to_float(s: str) -> Optional[float]:
    try:
        return float(s.strip())
    except (ValueError, AttributeError, TypeError):
        return None


def parse_oht_line(line: str, fab: str) -> Optional[dict]:
    """LOGPRESSO 의 line 컬럼 내부 raw OHT 메시지 파싱.

    포맷 자동 감지:
      A) VHL_STATE_REPORT (21필드): 2,OHT,VID,STATE,FULL,err,onl,CUR,DIST,NEXT,...
      B) WIDE format with X,Y: timestamp,VID,X,Y,coord,state,name,full,cur,next,dist,...
      C) 기타 — VID 만 추출 + 가능한 필드 시도

    좌표는 라인 안에 있으면 그대로 사용 (가장 확실).
    """
    if not line:
        return None
    s = line.strip().strip('"').strip("'")

    # "2,OHT," 패턴 있으면 그 위치부터
    if "2,OHT," in s:
        s = s[s.index("2,OHT,"):]
    f = s.split(",")
    if len(f) < 4:
        return None

    # ── 포맷 추정 ──────────────────────────────
    is_state_report = (f[0] == "2" and f[1] == "OHT")  # VHL_STATE_REPORT

    if is_state_report:
        # 2,OHT,VID,STATE,FULL,err,onl,CUR,DIST,NEXT,...
        vid = f[2].strip()
        if not vid:
            return None
        result = {
            "vid": vid, "fab": fab,
            "state":       int(f[3])  if len(f) > 3  and f[3].strip().lstrip('-').isdigit() else 1,
            "is_full":     int(f[4])  if len(f) > 4  and f[4].strip().isdigit() else 0,
            "current_node": int(f[7]) if len(f) > 7  and f[7].strip().isdigit() else 0,
            "distance":    int(f[8])  if len(f) > 8  and f[8].strip().isdigit() else 0,
            "next_node":   int(f[9])  if len(f) > 9  and f[9].strip().isdigit() else 0,
            "destination": int(f[13]) if len(f) > 13 and f[13].strip().lstrip('-').isdigit() else 0,
            "source_port": f[16].strip() if len(f) > 16 else "",
            "dest_port":   f[17].strip() if len(f) > 17 else "",
            "speed":       int(f[18])  if len(f) > 18 and f[18].strip().lstrip('-').isdigit() else 0,
            "_x": None, "_y": None,
        }
        # 21필드 너머 추가 필드에 x,y 가 있을 수 있음 — 큰 부동소수점 2개 연속이면 좌표 가정
        for i in range(21, min(len(f), 30) - 1):
            x = _to_float(f[i]); y = _to_float(f[i+1])
            if x is not None and y is not None and abs(x) > 100 and abs(y) > 100:
                result["_x"] = x
                result["_y"] = y
                break
        return result

    # ── B) WIDE format: timestamp,VID,X,Y,... ──
    # 첫 필드가 시간형 문자열이면 wide 포맷일 가능성
    vid = f[1].strip() if len(f) > 1 else ""
    x = _to_float(f[2]) if len(f) > 2 else None
    y = _to_float(f[3]) if len(f) > 3 else None
    if vid and x is not None and y is not None and abs(x) > 100 and abs(y) > 100:
        # state, name, full, cur, next, dist 추출 시도
        state = int(f[5]) if len(f) > 5 and f[5].strip().lstrip('-').isdigit() else 1
        is_full = int(f[7]) if len(f) > 7 and f[7].strip().isdigit() else 0
        cur = int(f[8]) if len(f) > 8 and f[8].strip().isdigit() else 0
        nxt = int(f[9]) if len(f) > 9 and f[9].strip().isdigit() else 0
        dist = int(f[10]) if len(f) > 10 and f[10].strip().isdigit() else 0
        return {
            "vid": vid, "fab": fab,
            "state": state, "is_full": is_full,
            "current_node": cur, "next_node": nxt, "distance": dist,
            "destination": 0, "source_port": "", "dest_port": "", "speed": 0,
            "_x": x, "_y": y,
        }

    return None


def parse_row(row: dict, fab: str) -> Optional[dict]:
    L = _build_lookup(row)

    # 직접 X / Y 컬럼이 있으면 그 값 그대로 — 가장 정확
    x_raw = _get(row, L, "x", "X", "POS_X", "POSX", "x_mm", "X_MM")
    y_raw = _get(row, L, "y", "Y", "POS_Y", "POSY", "y_mm", "Y_MM")
    rx = _to_float(str(x_raw)) if x_raw is not None else None
    ry = _to_float(str(y_raw)) if y_raw is not None else None

    # ① LOGPRESSO 'line' 컬럼 안에 raw OHT 메시지
    line = _s(row, L, "line", "LINE", "MESSAGE", "MSG", "RAW")
    if line and ",OHT," in line:
        v = parse_oht_line(line, fab)
        if v:
            # 컬럼에 따로 x/y 가 있으면 line 추정값보다 우선
            if rx is not None and ry is not None:
                v["_x"] = rx; v["_y"] = ry
            return v

    # ② 평탄 컬럼 폴백
    vid = _s(row, L,
             "VHL_ID", "VEHICLE", "VEHICLE_ID", "VEHICLEID",
             "vid", "OHT_ID", "OHTID", "CARRIER_ID", "CARRIERID")
    if not vid:
        return None

    cur = _i(row, L,
             "ADDRESS", "CURRENT_ADDRESS", "CURRENTADDRESS",
             "CURRENT_ADDR", "CURRENT_NODE", "CURRENTNODE",
             "FROM_HIDID", "FROM_NODE", "FROMNODE", "NODE_ID", "NODEID")
    nxt = _i(row, L,
             "NEXT_ADDRESS", "NEXTADDRESS",
             "NEXT_ADDR", "NEXT_NODE", "NEXTNODE",
             "TO_HIDID", "TO_NODE", "TONODE")

    return {
        "vid": vid,
        "fab": fab,
        "state":       _i(row, L, "STATUS", "STATE", default=1),
        "is_full":     _i(row, L, "STOCK_INFO", "IS_FULL", "ISFULL"),
        "current_node": cur,
        "next_node":    nxt,
        "distance":    _i(row, L, "DISTANCE", "DISTANCE_MM", "DISTANCEMM", "TRANS_CNT"),
        "destination": _i(row, L, "DESTINATION", "DEST"),
        "speed":       _i(row, L, "SPEED", "FREE_FLOW_SPEED"),
        "source_port": _s(row, L, "FROM_RETURN_PORT", "SOURCE_PORT", "SRC_PORT"),
        "dest_port":   _s(row, L, "DEST_RETURN_PORT", "DEST_PORT"),
        "_x": rx, "_y": ry,
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
        # 진단용: 마지막 패킷 raw 정보
        self.last_columns: List[str] = []
        self.last_raw_row: Optional[dict] = None
        self.parsed_ok = 0
        self.parsed_fail = 0

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
            "columns": self.last_columns,
            "last_raw_row": self.last_raw_row,
            "parsed_ok":   self.parsed_ok,
            "parsed_fail": self.parsed_fail,
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
            rows = pkt.get("rows") or []
            if rows:
                self.last_raw_row = rows[0]
                self.last_columns = list(rows[0].keys())
            for row in rows:
                self.rx_rows += 1
                vd = parse_row(row, self.fab)
                if vd is None:
                    self.parsed_fail += 1
                    continue
                self.parsed_ok += 1
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
            # CSV 직접 좌표 (있으면 layout lookup 안 거치고 바로 사용)
            v.raw_x         = vd.get("_x")
            v.raw_y         = vd.get("_y")
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

# FAB 별 자기 캐시 1개씩만 — 맵 깨끗하게 (3개 fab 겹치지 않게)
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
