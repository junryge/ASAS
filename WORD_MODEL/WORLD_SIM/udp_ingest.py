# -*- coding: utf-8 -*-
"""
udp_ingest.py — OHT_UDP_SIM 송신기로부터 UDP 패킷 수신해서 월드모델에 주입

WORLD_SIM/main.py 가 부팅 시 UdpIngest 인스턴스를 생성하고 start() 한다.
콜백 on_packet(fab, ts, vehicles) 으로 engine.world.load_vehicles_from_frame(...) 호출.

송신기 패킷 (JSON):
    {"fab": "M14A"|"M16A_BR", "ts": "2026-04-29T11:00:01+09:00",
     "count": N, "rows": [ {... LOGPRESSO 행 ...}, ... ]}
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections import deque
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from data_loader import parse_oht_data_m14a_row


PacketCallback = Callable[[str, datetime, List[dict]], None]


def _parse_ts(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    # "+09:00" → "+0900" 보정 (3.6 호환)
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


def _row_to_vehicle(row: dict, ts: datetime) -> Optional[dict]:
    """LOGPRESSO 한 행 → world_model 이 받는 vehicle dict.
    1) parse_oht_data_m14a_row 시도 (VEHICLE/ADDRESS/... 컬럼)
    2) 실패 시 LOGPRESSO 표준 (VHL_ID/HID_VALUE/...) 폴백
    """
    v = parse_oht_data_m14a_row(row, t=ts)
    if v and v.get('vid'):
        return v

    vid = (row.get('VHL_ID') or row.get('VEHICLE') or row.get('vid') or '').strip()
    if not vid:
        return None

    def _i(key, d=0):
        try: return int(float(row.get(key, d) or d))
        except (TypeError, ValueError): return d

    cur = _i('CURRENT_ADDR') or _i('ADDRESS') or _i('FROM_HIDID')
    nxt = _i('NEXT_ADDR')   or _i('NEXT_ADDRESS') or _i('TO_HIDID')
    dist = _i('DISTANCE')   or _i('DISTANCE_MM') or _i('TRANS_CNT')
    state = _i('STATUS', 1) or _i('STATE', 1) or 1

    if cur == 0 or nxt == 0:
        return None
    return {
        'vid': vid,
        'state': state,
        'stateName': '',
        'isFull': _i('STOCK_INFO') or _i('IS_FULL'),
        'currentNode': cur,
        'distance': dist,
        'nextNode': nxt,
        'destination': _i('DESTINATION'),
        'sourcePort': str(row.get('SOURCE_PORT') or row.get('FROM_RETURN_PORT') or ''),
        'destPort':   str(row.get('DEST_PORT')   or row.get('DEST_RETURN_PORT') or ''),
        'speed': _i('SPEED') or _i('FREE_FLOW_SPEED'),
        '_time': ts,
    }


class FabStream:
    """FAB 별 수신 통계 + 마지막 vehicle 스냅샷"""
    def __init__(self, fab: str, port: int):
        self.fab  = fab
        self.port = port
        self.rx_packets = 0
        self.rx_rows    = 0
        self.rx_bytes   = 0
        self.first_at: Optional[datetime] = None
        self.last_at:  Optional[datetime] = None
        self.last_ts:  Optional[str] = None
        self.last_addr: Optional[Tuple[str, int]] = None
        self.last_error: Optional[str] = None
        # 1초 내 같은 ts 끼리 묶음 (송신측 분할 패킷 합치기용)
        self._cur_ts: Optional[str] = None
        self._cur_buf: List[dict] = []
        self.recent: deque = deque(maxlen=200)

    def stats(self) -> dict:
        return {
            "fab": self.fab,
            "port": self.port,
            "rx_packets": self.rx_packets,
            "rx_rows":    self.rx_rows,
            "rx_bytes":   self.rx_bytes,
            "first_at":   self.first_at.isoformat() if self.first_at else None,
            "last_at":    self.last_at.isoformat()  if self.last_at  else None,
            "last_ts":    self.last_ts,
            "last_addr":  list(self.last_addr) if self.last_addr else None,
            "last_error": self.last_error,
        }


class UdpIngest:
    """두 포트 동시 listen + 콜백"""
    def __init__(
        self,
        port_m14a: int = 3710,
        port_m16a_br: int = 3750,
        host: str = "0.0.0.0",
        on_packet: Optional[PacketCallback] = None,
        buffer_size: int = 65535,
    ):
        self.host = host
        self.buffer_size = buffer_size
        self.on_packet = on_packet
        self.streams: Dict[str, FabStream] = {
            "M14A":    FabStream("M14A",    port_m14a),
            "M16A_BR": FabStream("M16A_BR", port_m16a_br),
        }
        self._sockets: Dict[str, socket.socket] = {}
        self._threads: List[threading.Thread] = []
        self._running = False
        self.last_error: Optional[str] = None

    # ── lifecycle ─────────────────────────────────
    def start(self) -> bool:
        if self._running:
            return True
        for fab, st in self.streams.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
                s.bind((self.host, st.port))
                self._sockets[fab] = s
                t = threading.Thread(
                    target=self._loop, args=(fab, s), daemon=True, name=f"udp-{fab}"
                )
                t.start()
                self._threads.append(t)
            except OSError as e:
                self.last_error = f"bind {fab}:{st.port} → {e}"
                print(f"[UDP] {self.last_error}")
                self.stop()
                return False
        self._running = True
        print(f"[UDP] listen M14A:{self.streams['M14A'].port}  "
              f"M16A_BR:{self.streams['M16A_BR'].port}")
        return True

    def stop(self):
        self._running = False
        for s in self._sockets.values():
            try: s.close()
            except OSError: pass
        self._sockets.clear()
        self._threads.clear()

    # ── recv loop ─────────────────────────────────
    def _loop(self, fab: str, sock: socket.socket):
        st = self.streams[fab]
        while True:
            try:
                data, addr = sock.recvfrom(self.buffer_size)
            except OSError:
                return  # socket closed

            st.rx_packets += 1
            st.rx_bytes   += len(data)
            now = datetime.now()
            if st.first_at is None:
                st.first_at = now
            st.last_at   = now
            st.last_addr = addr

            pkt = self._parse(data)
            if pkt is None:
                continue

            ts_str = pkt.get("ts") or ""
            ts_dt = _parse_ts(ts_str)
            rows  = pkt.get("rows") or []
            st.rx_rows += len(rows)
            st.last_ts = ts_str

            # 같은 ts 분할 패킷이면 누적, ts 바뀌면 직전 묶음을 콜백 처리
            if st._cur_ts is None or ts_str == st._cur_ts:
                st._cur_ts = ts_str
                st._cur_buf.extend(rows)
            else:
                self._flush(fab, st)
                st._cur_ts = ts_str
                st._cur_buf = list(rows)

            # 휴리스틱: 같은 ts 라도 일정량 모이면 즉시 flush
            if len(st._cur_buf) >= 200:
                self._flush(fab, st)
                st._cur_ts = ts_str
                st._cur_buf = []

    def _flush(self, fab: str, st: FabStream):
        if not st._cur_buf:
            return
        ts_dt = _parse_ts(st._cur_ts or "") or datetime.now()
        vehicles: List[dict] = []
        for row in st._cur_buf:
            v = _row_to_vehicle(row, ts_dt)
            if v is not None:
                vehicles.append(v)
        st.recent.append({
            "ts": st._cur_ts, "n_rows": len(st._cur_buf), "n_vehicles": len(vehicles),
        })
        if self.on_packet and vehicles:
            try:
                self.on_packet(fab, ts_dt, vehicles)
            except Exception as e:
                st.last_error = f"callback: {e!r}"

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
            return {
                "fab":   meta.get("FAB"),
                "ts":    meta.get("TS"),
                "count": int(meta.get("N", len(rows))),
                "rows":  rows,
            }
        return None

    # ── inspection ───────────────────────────────
    def state(self) -> dict:
        return {
            "running": self._running,
            "host":    self.host,
            "fabs":    {k: v.stats() for k, v in self.streams.items()},
            "last_error": self.last_error,
        }
