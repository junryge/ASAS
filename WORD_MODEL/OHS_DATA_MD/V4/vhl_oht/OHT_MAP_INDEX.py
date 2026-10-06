# -*- coding: utf-8 -*-
"""
OHT_MAP_INDEX.py — 문제맵(HTML) 목록을 날짜별 CSV 로 남긴다 (다운로드 화면용)

    python OHT_MAP_INDEX.py            지금까지 만들어진 문제맵 전부 → CSV (빠진 것만 추가)
    python OHT_MAP_INDEX.py 20261003   그 날짜만

  읽는 곳  HID_BOTTLENECK/PROBLEM_MAP/{FAB}_{YYYYMMDD}/…/PROBLEM_MAP_{FAB}_{YYYYMMDD}_{HHMM}_{ALARM_EN}.html
  쓰는 곳  ../m16a_hubroom_event_prediction/oht_map/OHT_MAP_{YYYYMMDD}.csv   (vhl_ohl 폴더 기준)
           — config.json 의 "oht_map_dir" 로 바꿀 수 있다 (상대경로면 이 파일 폴더 기준)

  CSV 한 줄 = 문제맵 한 장
      날짜, 시간, FAB, ALARM_KR, ALARM_EN, HID_ZONE, HID_section,
      OHT_report, OHT_missing, OHT_JAM, ZONE_STOP, FILE_NAME, FILE_PATH
    · ALARM · 숫자 칸은 그 분의 HID_BOTTLENECK CSV 줄에서 가져온다 (없으면 파일 이름의 ALARM 만)
    · 같은 파일은 한 번만 들어간다 — 여러 번 돌려도 중복 없음
    · run_oht.py 가 문제맵을 만들 때마다 바로 부른다 (HID_VHL_OHT.py 는 그대로)
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "HID_BOTTLENECK"                      # HID_VHL_OHT.py 와 같은 위치
MAP_OUT = OUT_DIR / "PROBLEM_MAP"
CONFIG_FILE = HERE / "config.json"
DEFAULT_INDEX_DIR = "../m16a_hubroom_event_prediction/oht_map"

COLS = ["날짜", "시간", "FAB", "ALARM_KR", "ALARM_EN", "HID_ZONE", "HID_section",
        "OHT_report", "OHT_missing", "OHT_JAM", "ZONE_STOP", "FILE_NAME", "FILE_PATH"]
NAME_RE = re.compile(r"^PROBLEM_MAP_(.+)_(\d{8})_(\d{4})_([A-Z]+)\.html$")
ALARM_KR_OF = {"NORMAL": "정상", "WARNING": "경계", "DANGER": "위험", "CRITICAL": "초위험"}


def _config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_cfg = _config()
ENABLED = bool(_cfg.get("oht_map_enabled", True))
INDEX_DIR = Path(_cfg.get("oht_map_dir") or DEFAULT_INDEX_DIR)
if not INDEX_DIR.is_absolute():
    INDEX_DIR = (HERE / INDEX_DIR).resolve()


def _warn(msg):
    print(f"[OHT_MAP_INDEX] {msg}")


# ---------- 그 분의 판정 줄 (HID_BOTTLENECK CSV) ----------
_row_cache = {}                                        # 경로 → (mtime, {(날짜, 시간): 줄})


def _minute_rows(fab, ymd):
    out = {}
    for p in (OUT_DIR / fab / f"HID_BOTTLENECK_{fab}_{ymd}.csv",
              OUT_DIR / "PAST" / fab / f"HID_BOTTLENECK_{fab}_{ymd}.csv"):
        try:
            mt = p.stat().st_mtime_ns
        except OSError:
            continue
        hit = _row_cache.get(p)
        if not hit or hit[0] != mt:
            rows = {}
            try:
                with open(p, encoding="utf-8-sig", newline="") as f:
                    for r in csv.DictReader(f):
                        rows[(r.get("날짜", ""), r.get("시간", ""))] = r
            except Exception as e:
                _warn(f"{p.name} 읽기 실패 — 파일 이름 정보만 씀: {e}")
            hit = _row_cache[p] = (mt, rows)
        for k, v in hit[1].items():
            out.setdefault(k, v)                       # 실시간 CSV 우선, 없으면 PAST
    return out


def _line(path):
    m = NAME_RE.match(path.name)
    if not m:
        return None
    fab, ymd, hm, en = m.groups()
    day, tm = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}", f"{hm[:2]}:{hm[2:]}"
    r = _minute_rows(fab, ymd).get((day, tm), {})
    g = lambda k: r.get(k, "")
    return {
        "날짜": day, "시간": tm, "FAB": fab,
        "ALARM_KR": g("ALARM_KR") or g("ALARM") or ALARM_KR_OF.get(en, ""),
        "ALARM_EN": g("ALARM_EN") or en,
        "HID_ZONE": g("HID_ZONE"), "HID_section": g("HID_section"),
        "OHT_report": g(f"{fab}_OHT_report"), "OHT_missing": g(f"{fab}_OHT_missing"),
        "OHT_JAM": g(f"{fab}_OHT_JAM"), "ZONE_STOP": g("ZONE_STOP"),
        "FILE_NAME": path.name, "FILE_PATH": str(path.resolve()),
    }


# ---------- 목록 CSV ----------
def _index_path(ymd):
    return INDEX_DIR / f"OHT_MAP_{ymd}.csv"


def _have(p):
    try:
        with open(p, encoding="utf-8-sig", newline="") as f:
            return {r.get("FILE_NAME", "") for r in csv.DictReader(f)}
    except OSError:
        return set()


def _map_files(dates=None):
    """PROBLEM_MAP 아래 문제맵 HTML → {YYYYMMDD: [경로]} (dates 를 주면 그 날짜 폴더만)"""
    out = {}
    if not MAP_OUT.exists():
        return out
    for d in MAP_OUT.iterdir():
        if not d.is_dir():
            continue
        ymd = d.name.rsplit("_", 1)[-1]
        if dates and ymd not in dates:
            continue
        for p in d.rglob("PROBLEM_MAP_*.html"):
            m = NAME_RE.match(p.name)
            if m:
                out.setdefault(m.group(2), []).append(p)
    return out


def sync(dates=None):
    """문제맵 → 날짜별 CSV. 아직 없는 파일만 시간순으로 추가한다. 추가한 줄 수를 돌려준다."""
    if not ENABLED:
        return 0
    added = 0
    for ymd, files in sorted(_map_files(dates).items()):
        p = _index_path(ymd)
        have = _have(p)
        new = [x for x in (_line(f) for f in files if f.name not in have) if x]
        if not new:
            continue
        new.sort(key=lambda x: (x["시간"], x["FAB"], x["FILE_NAME"]))
        try:
            INDEX_DIR.mkdir(parents=True, exist_ok=True)
            first = not p.exists() or p.stat().st_size == 0
            with open(p, "a", encoding="utf-8-sig" if first else "utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                if first:
                    w.writeheader()
                w.writerows(new)
            added += len(new)
        except Exception as e:
            _warn(f"{p} 쓰기 실패 — 다음에 다시 넣는다: {e}")
    return added


def sync_recent():
    """실시간용 — 오늘 · 어제 폴더만 본다."""
    now = datetime.now()
    return sync({f"{now:%Y%m%d}", f"{now - timedelta(days=1):%Y%m%d}"})


if __name__ == "__main__":
    ds = {a for a in sys.argv[1:] if re.fullmatch(r"\d{8}", a)} or None
    n = sync(ds)
    print(f"문제맵 {n}개 추가 → {INDEX_DIR}" + ("" if ENABLED else "  (config.json oht_map_enabled false — 안 함)"))
