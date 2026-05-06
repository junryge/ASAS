# -*- coding: utf-8 -*-
"""
LOGPRESSO_OHT_DATA CSV 스트리밍 로더 — 메모리 O(1)

전략:
  1) load()           : 빠른 메타 스캔만 (행 수, 시작/끝 ts).  row 보관 안 함.
  2) iter_groups()    : 호출 시점마다 CSV 를 처음부터 스트리밍.
                        REPLAY 윈도우 안에서 1초 단위로 묶어 yield.
  3) loop / seek 는 sender 측에서 iter_groups 를 다시 호출하는 방식.

전제: LOGPRESSO CSV 는 _time 오름차순으로 이미 정렬되어 있음 (표준).
      정렬이 흐트러져도 1초 그룹 단위라 큰 문제는 없음.
"""

import csv
import io
import os
import re
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Tuple


_TIME_PATTERNS = [
    "%Y-%m-%d %H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
]


def _parse_time(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip().strip('"')
    s = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", s)  # +09:00 → +0900
    for fmt in _TIME_PATTERNS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_window(start: str, end: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    return _parse_time(start), _parse_time(end)


class OhtCsvLoader:
    """LOGPRESSO_OHT_DATA CSV 스트리밍 로더 (전체 적재 X)"""

    def __init__(self, csv_path: str, replay_start: str = "", replay_end: str = ""):
        self.csv_path = csv_path
        self.replay_start, self.replay_end = _parse_window(replay_start, replay_end)
        self.fieldnames: List[str] = []
        self.time_col:   Optional[str] = None
        # 메타
        self.row_count = 0
        self.first_ts: Optional[datetime] = None
        self.last_ts:  Optional[datetime] = None
        self.file_bytes = 0
        self.loaded = False

    # ───────────────────────────────────────────────
    def exists(self) -> bool:
        return os.path.exists(self.csv_path)

    def load(self) -> int:
        """빠른 메타 스캔 — row 는 보관 안 함, 카운트와 시작/끝 ts 만 저장."""
        if not self.exists():
            self.fieldnames = []
            self.time_col = None
            self.row_count = 0
            self.first_ts = self.last_ts = None
            self.loaded = False
            return 0

        try:
            self.file_bytes = os.path.getsize(self.csv_path)
        except OSError:
            self.file_bytes = 0

        cnt = 0
        first = None
        last  = None
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.fieldnames = list(reader.fieldnames or [])
            self.time_col   = self._detect_time_col(self.fieldnames)
            if not self.time_col:
                self.loaded = False
                return 0
            for row in reader:
                if not row:
                    continue
                t = _parse_time(row.get(self.time_col, ""))
                if t is None:
                    continue
                if self.replay_start and t < self._tz_align(t, self.replay_start):
                    continue
                if self.replay_end and t > self._tz_align(t, self.replay_end):
                    continue
                cnt += 1
                if first is None or t < first: first = t
                if last  is None or t > last:  last  = t

        self.row_count = cnt
        self.first_ts  = first
        self.last_ts   = last
        self.loaded    = True
        return cnt

    # ───────────────────────────────────────────────
    @staticmethod
    def _detect_time_col(fieldnames: List[str]) -> Optional[str]:
        for c in fieldnames:
            if c.strip().lower() in ("_time", "time", "event_dt", "timestamp"):
                return c
        for c in fieldnames:
            if "time" in c.lower() or "_dt" in c.lower():
                return c
        return None

    @staticmethod
    def _tz_align(target: datetime, ref: datetime) -> datetime:
        if target.tzinfo is None and ref.tzinfo is not None:
            return ref.replace(tzinfo=None)
        if target.tzinfo is not None and ref.tzinfo is None:
            return ref.replace(tzinfo=target.tzinfo)
        return ref

    # ───────────────────────────────────────────────
    def total_rows(self) -> int:
        return self.row_count

    def time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        return self.first_ts, self.last_ts

    def duration_sec(self) -> int:
        if not self.first_ts or not self.last_ts:
            return 0
        return int((self.last_ts - self.first_ts).total_seconds())

    # ───────────────────────────────────────────────
    def iter_groups(
        self, start_at_idx: int = 0
    ) -> Iterator[Tuple[datetime, List[Dict[str, str]], int]]:
        """
        CSV 를 처음부터 스트리밍해서 1초 단위 그룹 yield.

        yields: (group_ts, batch_rows, last_row_idx_after_emit)

        start_at_idx > 0 이면 윈도우 안에서 그 만큼의 row 를 skip 후 시작.
        호출 한 번 = 한 cycle. loop 처리는 caller 에서 다시 호출.
        """
        if not self.exists() or not self.time_col:
            return

        idx     = 0
        cur_t:  Optional[datetime] = None
        buf:    List[Dict[str, str]] = []

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                t = _parse_time(row.get(self.time_col, ""))
                if t is None:
                    continue
                if self.replay_start and t < self._tz_align(t, self.replay_start):
                    continue
                if self.replay_end and t > self._tz_align(t, self.replay_end):
                    continue

                idx += 1
                if idx <= start_at_idx:
                    continue

                tsec = t.replace(microsecond=0)
                if cur_t is None:
                    cur_t = tsec
                if tsec != cur_t:
                    yield cur_t, buf, idx - 1
                    cur_t = tsec
                    buf = []
                buf.append(row)

        if buf and cur_t is not None:
            yield cur_t, buf, idx


# ───────────────────────────────────────────────
# 패킷 직렬화
# ───────────────────────────────────────────────
def serialize_json(fab: str, ts: datetime, rows: List[Dict[str, str]]) -> bytes:
    import json
    pkt = {
        "fab": fab,
        "ts": ts.isoformat(),
        "count": len(rows),
        "rows": rows,
    }
    return json.dumps(pkt, ensure_ascii=False).encode("utf-8")


def serialize_csv(fab: str, ts: datetime, rows: List[Dict[str, str]],
                  fieldnames: List[str]) -> bytes:
    buf = io.StringIO()
    buf.write(f"#FAB={fab};TS={ts.isoformat()};N={len(rows)}\n")
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")
