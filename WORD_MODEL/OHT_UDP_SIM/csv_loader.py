# -*- coding: utf-8 -*-
"""
LOGPRESSO_OHT_DATA CSV 로더

파일 형식 (Logpresso 표준):
    "_id","_table","_time", ...   <- 따옴표 포함 헤더
    "1234","M16A_OHT_DATA","2026-04-29 11:00:01.123+0900",...

특징:
  • _time 컬럼을 epoch (sec) 으로 정렬 후 시간순 정렬
  • REPLAY_START ~ REPLAY_END 범위만 로드
  • 컬럼 이름 그대로 보존 (UDP 송신 시 dict 그대로 직렬화)
  • 1초 단위 그룹핑 (같은 _time → 한 batch)
"""

import csv
import io
import os
import re
from datetime import datetime, timedelta
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
    """LOGPRESSO_OHT_DATA CSV 로더"""

    def __init__(self, csv_path: str, replay_start: str = "", replay_end: str = ""):
        self.csv_path = csv_path
        self.replay_start, self.replay_end = _parse_window(replay_start, replay_end)
        self.rows: List[Dict[str, str]] = []
        self.fieldnames: List[str] = []
        self.time_col: Optional[str] = None
        self.loaded = False

    # ───────────────────────────────────────────────
    def exists(self) -> bool:
        return os.path.exists(self.csv_path)

    def load(self) -> int:
        """전체 CSV 파싱. _time 컬럼 자동 탐지 + 시간순 정렬."""
        if not self.exists():
            self.rows = []
            self.fieldnames = []
            self.loaded = False
            return 0

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.fieldnames = list(reader.fieldnames or [])
            self.time_col = self._detect_time_col(self.fieldnames)
            for row in reader:
                if not row:
                    continue
                t = self._row_time(row)
                if t is None:
                    continue
                if self.replay_start and t < self._tz_align(t, self.replay_start):
                    continue
                if self.replay_end and t > self._tz_align(t, self.replay_end):
                    continue
                self.rows.append(row)

        self.rows.sort(key=lambda r: self._row_time(r) or datetime.min)
        self.loaded = True
        return len(self.rows)

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

    def _row_time(self, row: Dict[str, str]) -> Optional[datetime]:
        if not self.time_col:
            return None
        return _parse_time(row.get(self.time_col, ""))

    @staticmethod
    def _tz_align(target: datetime, ref: datetime) -> datetime:
        """ref(naive/aware) 를 target 의 tz에 맞춰 비교 가능하게 만듦"""
        if target.tzinfo is None and ref.tzinfo is not None:
            return ref.replace(tzinfo=None)
        if target.tzinfo is not None and ref.tzinfo is None:
            return ref.replace(tzinfo=target.tzinfo)
        return ref

    # ───────────────────────────────────────────────
    def total_rows(self) -> int:
        return len(self.rows)

    def time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        if not self.rows:
            return None, None
        return self._row_time(self.rows[0]), self._row_time(self.rows[-1])

    def duration_sec(self) -> int:
        a, b = self.time_range()
        if not a or not b:
            return 0
        return int((b - a).total_seconds())

    # ───────────────────────────────────────────────
    def iter_groups(self, loop: bool = False) -> Iterator[Tuple[datetime, List[Dict[str, str]]]]:
        """
        같은 1초 안의 row 들을 묶어서 yield.
        loop=True 이면 끝에서 다시 처음으로 (사이 1초 휴식).
        """
        if not self.rows:
            return
        while True:
            cur_t = None
            buf: List[Dict[str, str]] = []
            for row in self.rows:
                t = self._row_time(row)
                if t is None:
                    continue
                tsec = t.replace(microsecond=0)
                if cur_t is None:
                    cur_t = tsec
                if tsec != cur_t:
                    yield cur_t, buf
                    cur_t = tsec
                    buf = []
                buf.append(row)
            if buf and cur_t is not None:
                yield cur_t, buf
            if not loop:
                break


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
