# -*- coding: utf-8 -*-
"""
LOGPRESSO_OHT_DATA CSV 스트리밍 로더 — O(1) 로드, byte-offset 기반

큰 파일 (수 GB ~ 수십 GB) 대응:
  • load() = 파일 크기 + 헤더 + 첫 row 만 읽음. 전체 스캔 안 함.
  • iter_groups(start_byte=0): byte 오프셋부터 스트리밍. 처음 row 찾으면 yield 시작.
  • seek = 파일 byte ratio 기준.

전제: LOGPRESSO CSV 가 _time 오름차순.
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
    s = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", s)
    for fmt in _TIME_PATTERNS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_window(start: str, end: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    return _parse_time(start), _parse_time(end)


def _parse_csv_line(line: str) -> List[str]:
    """한 줄을 csv 파서로 분해 (따옴표/콤마 안전)."""
    try:
        return next(csv.reader([line]))
    except StopIteration:
        return []


class OhtCsvLoader:
    """LOGPRESSO_OHT_DATA CSV — O(1) 메타 + byte 스트리밍"""

    def __init__(self, csv_path: str, replay_start: str = "", replay_end: str = ""):
        self.csv_path = csv_path
        self.replay_start, self.replay_end = _parse_window(replay_start, replay_end)
        self.fieldnames: List[str] = []
        self.time_col:   Optional[str] = None
        self.time_col_idx: Optional[int] = None
        self.file_bytes  = 0
        self.first_ts:   Optional[datetime] = None   # 첫 row 의 ts (메타용)
        self.last_ts:    Optional[datetime] = None   # 알 수 없음 (대용량 대응)
        self.row_count   = -1                        # 알 수 없음
        self.loaded      = False
        self._header_byte_end = 0                    # 헤더 끝 byte 위치

    # ───────────────────────────────────────────────
    def exists(self) -> bool:
        return os.path.exists(self.csv_path)

    def load(self) -> int:
        """O(1) 로드 — 파일 크기 + 헤더 + 첫 row 만 읽음. 14GB 도 즉시."""
        if not self.exists():
            self.fieldnames = []
            self.time_col = None
            self.file_bytes = 0
            self.first_ts = None
            self.loaded = False
            return 0

        try:
            self.file_bytes = os.path.getsize(self.csv_path)
        except OSError:
            self.file_bytes = 0

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            # 헤더 한 줄
            header_line = f.readline()
            if not header_line:
                self.loaded = False
                return 0
            self._header_byte_end = f.tell()

            # 헤더 파싱
            self.fieldnames = _parse_csv_line(header_line.rstrip("\r\n"))
            self.time_col = self._detect_time_col(self.fieldnames)
            if self.time_col and self.time_col in self.fieldnames:
                self.time_col_idx = self.fieldnames.index(self.time_col)

            # 첫 유효 row 의 ts 만 (윈도우 밖이면 그냥 그대로 — 시작 안내용)
            if self.time_col_idx is not None:
                for _ in range(50):
                    line = f.readline()
                    if not line:
                        break
                    fields = _parse_csv_line(line.rstrip("\r\n"))
                    if self.time_col_idx >= len(fields):
                        continue
                    t = _parse_time(fields[self.time_col_idx])
                    if t is not None:
                        self.first_ts = t
                        break

        self.loaded = True
        return self.file_bytes

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
        # 미상 — 파일 크기 반환 (UI 진행률용)
        return self.file_bytes if self.row_count < 0 else self.row_count

    def time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        return self.first_ts, self.last_ts

    def duration_sec(self) -> int:
        if not self.first_ts or not self.last_ts:
            return 0
        return int((self.last_ts - self.first_ts).total_seconds())

    # ───────────────────────────────────────────────
    def iter_groups(
        self, start_byte: int = 0
    ) -> Iterator[Tuple[datetime, List[Dict[str, str]], int]]:
        """
        CSV 를 byte 오프셋부터 스트리밍해서 1초 단위 그룹 yield.

        yields: (group_ts, batch_rows, byte_pos_after_emit)

        start_byte=0 이면 헤더 다음부터.
        start_byte>0 이면 그 위치로 seek 후 다음 줄 시작 (잘린 줄은 버림).
        """
        if not self.exists() or self.time_col_idx is None:
            return
        if not self.fieldnames:
            return

        cols = self.fieldnames
        tidx = self.time_col_idx

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            if start_byte and start_byte > self._header_byte_end:
                try:
                    f.seek(start_byte)
                except OSError:
                    f.seek(self._header_byte_end)
                f.readline()  # 잘린 줄 버림
            else:
                # 헤더 건너뛰기
                f.readline()

            cur_t: Optional[datetime] = None
            buf: List[Dict[str, str]] = []

            while True:
                line = f.readline()
                if not line:
                    break
                line = line.rstrip("\r\n")
                if not line:
                    continue
                fields = _parse_csv_line(line)
                if not fields or tidx >= len(fields):
                    continue
                t = _parse_time(fields[tidx])
                if t is None:
                    continue
                if self.replay_start and t < self._tz_align(t, self.replay_start):
                    continue
                if self.replay_end and t > self._tz_align(t, self.replay_end):
                    # 윈도우 끝 — 더 이상 처리 안 함
                    break

                # 패딩
                if len(fields) < len(cols):
                    fields = fields + [""] * (len(cols) - len(fields))
                row = dict(zip(cols, fields))

                tsec = t.replace(microsecond=0)
                if cur_t is None:
                    cur_t = tsec
                if tsec != cur_t:
                    yield cur_t, buf, f.tell()
                    cur_t = tsec
                    buf = []
                buf.append(row)

            if buf and cur_t is not None:
                yield cur_t, buf, f.tell()


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
