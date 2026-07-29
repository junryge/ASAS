#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 날짜별 CSV 누적 저장 (독립)

실시간 수집이 1분마다 가져온 데이터를 날짜 파일에 한 줄씩 붙인다.

    data/20260727_TOTAL.CSV

  · 기본 데이터 + AMOS 4개 컬럼이 합쳐진 상태 그대로 저장
  · 같은 시각(datetime)은 다시 안 쓴다 (재폴링 중복 방지)
  · 평가·리포트는 이 파일을 읽어서 한다 (로그프레소 재조회 불필요)
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime

from lp_client import load_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_lock = threading.Lock()
_keys_cache: dict[str, set] = {}      # {날짜: {이미 쓴 키}}


def data_dir(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    d = os.path.join(BASE_DIR, cfg.get("storage", {}).get("daily_csv_dir", "data"))
    os.makedirs(d, exist_ok=True)
    return d


def day_path(day: str, cfg: dict | None = None) -> str:
    """'20260727' → data/20260727_TOTAL.CSV"""
    return os.path.join(data_dir(cfg), f"{day}_TOTAL.CSV")


def _day_of(row: dict, time_col: str) -> str:
    """행의 날짜(yyyyMMdd) 추출."""
    d = "".join(ch for ch in str(row.get(time_col) or "") if ch.isdigit())
    return d[:8] if len(d) >= 8 else datetime.now().strftime("%Y%m%d")


def _key_of(row: dict, time_col: str, key_cols: list[str]) -> str:
    return "|".join(str(row.get(c) or "") for c in ([time_col] + key_cols))


def _load_keys(day: str, path: str, time_col: str, key_cols: list[str]) -> set:
    """파일에 이미 있는 키를 읽어둔다 (재시작 후에도 중복 방지)."""
    if day in _keys_cache:
        return _keys_cache[day]
    keys = set()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    keys.add(_key_of(r, time_col, key_cols))
        except Exception as e:
            print(f"[CSV] ⚠️ 기존 파일 읽기 실패({path}): {e}")
    _keys_cache[day] = keys
    return keys


def append_rows(rows: list[dict], cfg: dict | None = None) -> dict:
    """수집한 행을 날짜별 CSV 에 한 줄씩 추가. 이미 있는 시각은 건너뛴다.

    반환 {"written": n, "skipped": n, "files": [...]}
    """
    cfg = cfg or load_config()
    if not rows:
        return {"written": 0, "skipped": 0, "files": []}

    sc = cfg.get("storage", {})
    time_col = cfg.get("amos", {}).get("base_time_col", "datetime")
    key_cols = sc.get("dedupe_cols", ["hot_area"])

    written = skipped = failed = 0
    files: set[str] = set()

    with _lock:
        for row in rows:
            day = _day_of(row, time_col)
            path = day_path(day, cfg)
            keys = _load_keys(day, path, time_col, key_cols)
            k = _key_of(row, time_col, key_cols)
            if k in keys:
                skipped += 1
                continue

            # 헤더는 파일당 한 번만 정하고 이후 그 순서를 그대로 따른다.
            # (행마다 키 순서가 달라도 컬럼이 밀리지 않게)
            fields = _fields(path, row)
            new_file = not os.path.isfile(path) or os.path.getsize(path) == 0
            try:
                with open(path, "a", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                    if new_file:
                        w.writeheader()
                    w.writerow(row)
            except Exception as e:
                print(f"[CSV] ❌ 쓰기 실패({path}): {e}")
                failed += 1
                continue

            keys.add(k)
            written += 1
            files.add(path)

    out = {"written": written, "skipped": skipped,
           "files": sorted(os.path.basename(p) for p in files)}
    if failed:
        out["failed"] = failed
    return out


_fields_cache: dict[str, list] = {}


def _fields(path: str, row: dict) -> list:
    """그 파일의 컬럼 순서. 기존 파일이 있으면 그 헤더를 그대로 쓴다."""
    if path in _fields_cache:
        return _fields_cache[path]
    fields = None
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                fields = next(csv.reader(f), None)
        except Exception:
            fields = None
    if not fields:
        fields = list(row.keys())
    _fields_cache[path] = fields
    return fields


def read_day(day: str, cfg: dict | None = None) -> list[dict]:
    """날짜 CSV 전체 읽기. '2026-07-27' / '20260727' 모두 허용."""
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    path = day_path(day, cfg)
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def read_range(from_dt: str, to_dt: str, cfg: dict | None = None) -> list[dict]:
    """구간(yyyyMMddHHmmss) 에 걸친 날짜 파일들을 읽어 합친다."""
    cfg = cfg or load_config()
    time_col = cfg.get("amos", {}).get("base_time_col", "datetime")
    f8, t8 = from_dt[:8], to_dt[:8]

    out: list[dict] = []
    for day in sorted({p[:8] for p in _days_between(f8, t8)}):
        out.extend(read_day(day, cfg))

    def stamp(r):
        return "".join(ch for ch in str(r.get(time_col) or "") if ch.isdigit())[:14]

    out = [r for r in out if from_dt[:14] <= stamp(r) <= to_dt[:14]]
    out.sort(key=stamp)
    return out


def _days_between(f8: str, t8: str) -> list[str]:
    from datetime import timedelta
    try:
        a, b = datetime.strptime(f8, "%Y%m%d"), datetime.strptime(t8, "%Y%m%d")
    except ValueError:
        return [f8]
    days, cur = [], a
    while cur <= b:
        days.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return days


def last_time(day: str, cfg: dict | None = None) -> datetime | None:
    """그 날 파일에 저장된 가장 늦은 시각. 없으면 None."""
    cfg = cfg or load_config()
    time_col = cfg.get("amos", {}).get("base_time_col", "datetime")
    newest = None
    for r in read_day(day, cfg):
        d = "".join(ch for ch in str(r.get(time_col) or "") if ch.isdigit())[:14]
        if len(d) < 12:
            continue
        try:
            t = datetime.strptime(d.ljust(14, "0"), "%Y%m%d%H%M%S")
        except ValueError:
            continue
        if newest is None or t > newest:
            newest = t
    return newest


# ─────────────────── LLM 판단 CSV (1분 1행, 판정은 나중에 채워짐) ───────────────────
# data/20260729_LLM.CSV — 열어보면 바로 읽히도록 컬럼명을 한글로 둔다.
# 'datetime' 만 영문인데, TOTAL.CSV 와 이 열로 조인하기 때문이다.
#
#   datetime   그 분 (TOTAL.CSV 와 같은 키)
#   스코어/등급/구역   그 분 상태
#   실제이상   LLM 판단 — 지금 대응이 필요한 진짜 이상인가 (예/아니오)  ★채점 대상
#   확신도     LLM 확신도 0~100
#   판단/근거/조치     LLM 이 쓴 문장 (정상 구간은 '판단' 한 줄만)
#   판정       사후검증 결과 — 적중/과다탐지/누락/조치효과, 사람이 누르면 정탐/오탐
#   판정시각/판정근거  왜 그렇게 판정했는지
#   추론깊이   간단(정상 구간) / 상세(경계 이상)
LLM_FIELDS = [
    "datetime", "스코어", "등급", "구역",
    "실제이상", "확신도", "판단", "근거", "조치",
    "판정", "판정시각", "판정근거",
    "모델", "추론깊이", "소요ms", "오류",
]
_llm_lock = threading.Lock()


def llm_suffix(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    return (cfg.get("llm", {}).get("per_minute", {}) or {}).get("csv_suffix", "_LLM")


def llm_path(day: str, cfg: dict | None = None) -> str:
    """'20260729' → data/20260729_LLM.CSV"""
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    return os.path.join(data_dir(cfg), f"{day}{llm_suffix(cfg)}.CSV")


def read_llm_day(day: str, cfg: dict | None = None) -> list[dict]:
    p = llm_path(day, cfg)
    if not os.path.isfile(p):
        return []
    try:
        with open(p, "r", encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception as e:
        print(f"[LLM CSV] ⚠️ 읽기 실패({p}): {e}")
        return []


def llm_minutes(day: str, cfg: dict | None = None) -> set:
    """그 날 이미 추론을 남긴 분(datetime) 집합 — 중복 호출 방지."""
    return {(r.get("datetime") or "").strip() for r in read_llm_day(day, cfg)}


def upsert_llm_rows(rows: list[dict], cfg: dict | None = None) -> dict:
    """LLM 판단 행을 datetime 기준으로 추가하거나 갱신한다.

    판정(적중/과다탐지…)은 검증 창이 찬 뒤에 같은 행에 채워 넣어야 하므로
    append 가 아니라 upsert 다. 하루 1440행이라 통째로 다시 써도 부담 없다.
    """
    if not rows:
        return {"written": 0, "updated": 0, "files": []}
    cfg = cfg or load_config()
    written = updated = 0
    files: set[str] = set()

    with _llm_lock:
        by_day: dict[str, list[dict]] = {}
        for r in rows:
            by_day.setdefault(_day_of(r, "datetime"), []).append(r)

        for day, new_rows in by_day.items():
            cur = {(r.get("datetime") or "").strip(): r for r in read_llm_day(day, cfg)}
            for r in new_rows:
                k = (r.get("datetime") or "").strip()
                if not k:
                    continue
                if k in cur:
                    cur[k].update({f: v for f, v in r.items() if v not in (None, "")})
                    updated += 1
                else:
                    cur[k] = {f: r.get(f, "") for f in LLM_FIELDS}
                    written += 1
            p = llm_path(day, cfg)
            tmp = p + f".tmp{os.getpid()}"
            try:
                with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=LLM_FIELDS, extrasaction="ignore")
                    w.writeheader()
                    for k in sorted(cur):
                        w.writerow({f: cur[k].get(f, "") for f in LLM_FIELDS})
                os.replace(tmp, p)
                files.add(os.path.basename(p))
            except Exception as e:
                print(f"[LLM CSV] ❌ 쓰기 실패({p}): {e}")
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return {"written": written, "updated": updated, "files": sorted(files)}


def list_days(cfg: dict | None = None) -> list[dict]:
    """저장된 날짜 파일 목록 (최신순)."""
    d = data_dir(cfg)
    out = []
    for fn in sorted(os.listdir(d), reverse=True):
        if fn.upper().endswith("_TOTAL.CSV"):
            p = os.path.join(d, fn)
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    n = max(0, sum(1 for _ in f) - 1)
            except Exception:
                n = 0
            out.append({"day": fn[:8], "file": fn, "rows": n,
                        "bytes": os.path.getsize(p)})
    return out


if __name__ == "__main__":
    cfg = load_config()
    print(f"저장 위치: {data_dir(cfg)}")
    for d in list_days(cfg):
        print(f"  {d['file']}  {d['rows']:>6}행  {d['bytes']/1024:.1f}KB")
