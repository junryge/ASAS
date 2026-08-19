"""ml_feed.py — ML 조기예측(chronos-2) 결과를 받아 두고 읽는다.

무엇인가
    반송시간 10분 평균이 임계(14.765분)를 넘을 확률을 1분마다 내는 별도
    시스템이다. 우리 룰베이스와 **완전히 독립**이다 — 서로의 판정을 입력으로
    쓰지 않는다. 그래서 같은 사건을 각각 언제 알렸는지 비교할 수 있다.

        ml_score_10m/30m  임계 넘을 확률 0.0000~1.0000
        ml_level_10m/30m  0.60↑ 위험 / 0.30↑ 경계 (우리 등급 어휘와 같다)
        stage             0 정상 / 1 관찰 / 2 선제경보 / 3 진행중
        raw_value         그 순간 반송시간(분) — 튐이 섞여 있다
        smoothed          10분 평균 — 실제 판단 기준
        threshold         임계(분)

★왜 TOTAL.CSV 에 합치지 않는가
    ① 눈금이 다르다. 우리는 unified_risk_score 0~100(컷 60/71/85), ML 은
       분(分) 단위 반송시간이다. 한 그래프에 겹쳐 그리면 거짓말이 된다.
    ② 행 구조가 다르다. ML 행에는 prediction_for_10m 이라는 **미래 시각**
       축이 있다.
    ③ 출처가 다르다. 한쪽이 죽어도 다른 쪽은 그대로 돌아야 한다.
    그래서 {day}_LLM.CSV 가 사는 방식 그대로 {day}_ML.CSV 로 따로 둔다.
    조인은 datetime 으로만 한다.

★ALL 전용이다
    파일이 m16a_hubroom_event_prediction 잡에서 나오고, ALL 화면이 보는
    발동이벤트.csv 와 같은 잡이다. FAB 별 예측은 아직 없다.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime

from lp_client import load_config
from store_csv import data_dir

# CSV 가 주는 칸 (순서 유지 — 원본 그대로 남긴다)
COLS = [
    "datetime", "prediction_for_10m", "prediction_for_30m",
    "ml_score_10m", "ml_score_30m", "ml_level_10m", "ml_level_30m",
    "raw_value", "smoothed", "threshold",
    "stage", "stage_name", "lead_min", "reason", "backend",
]

# stage 코드 → 화면 문구. 숫자만 보여주면 아무도 못 읽는다.
STAGES = {
    "0": ("정상", "임계를 넘을 조짐이 없다"),
    "1": ("관찰", "올라가는 기미 — 아직 알리지 않는다"),
    "2": ("선제경보", "곧 임계를 넘을 것으로 본다"),
    "3": ("진행중", "이미 임계를 넘었다 (예측이 아니라 현재 상태)"),
}


def cfg_of(cfg: dict) -> dict:
    """ML 설정 — source.jupyter 를 그대로 쓰되 path 만 갈아 끼운다.

    ★같은 서버·같은 비밀번호다. 로그인·인코딩·타임아웃을 다시 만들 이유가
      없어서 주피터 클라이언트를 통째로 재사용한다.
    """
    j = dict((cfg.get("source", {}) or {}).get("jupyter", {}) or {})
    ml = (cfg.get("ml", {}) or {})
    j["path"] = ml.get("path") or j.get("ml_path") or ""
    return j


def enabled(cfg: dict) -> bool:
    ml = (cfg.get("ml", {}) or {})
    return bool(ml.get("enabled", True)) and bool(cfg_of(cfg).get("path"))


def ml_path(day: str, cfg: dict | None = None) -> str:
    """'20260819' → data/20260819_ML.CSV"""
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    return os.path.join(data_dir(cfg), f"{day}_ML.CSV")


def read_day(day: str, cfg: dict | None = None) -> list[dict]:
    p = ml_path(day, cfg)
    if not os.path.isfile(p):
        return []
    try:
        with open(p, "r", encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception as e:
        print(f"[ML CSV] ⚠️ 읽기 실패({p}): {e}")
        return []


def _write(day: str, rows: list[dict], cfg: dict | None = None) -> None:
    p = ml_path(day, cfg)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def fetch_day(day: str = "", cfg: dict | None = None) -> dict:
    """그 날짜 예측 CSV 를 받아 저장 → {rows, added, error}.

    ★이미 있는 datetime 은 건너뛴다. 그래서 매 분 통째로 받아도 중복이
      안 쌓이고, 빠진 분은 다음 주기에 저절로 메워진다 (발동이벤트와 같은 방식).
    """
    cfg = cfg or load_config()
    day = day or datetime.now().strftime("%Y%m%d")
    if not enabled(cfg):
        return {"rows": 0, "added": 0, "error": "ml.path 가 비어 있습니다"}

    import jupyter_csv as jc
    c = cfg_of(cfg)
    raw, err = jc.download(day, {"source": {"jupyter": c}})
    if err:
        return {"rows": 0, "added": 0, "error": err}
    try:
        new = jc.parse_csv(raw, c)
    except Exception as e:
        return {"rows": 0, "added": 0, "error": f"파싱 실패: {type(e).__name__}: {e}"}

    have = read_day(day, cfg)
    seen = {(r.get("datetime") or "").strip() for r in have}
    add = [r for r in new if (r.get("datetime") or "").strip()
           and (r.get("datetime") or "").strip() not in seen]
    if add:
        merged = have + add
        merged.sort(key=lambda r: (r.get("datetime") or ""))
        _write(day, merged, cfg)
    return {"rows": len(have) + len(add), "added": len(add), "error": ""}


def _f(v, default=None):
    try:
        s = str(v).strip()
        return float(s) if s else default
    except (TypeError, ValueError):
        return default


def latest(day: str = "", cfg: dict | None = None) -> dict | None:
    """가장 최근 한 줄 — 화면 상단에 그대로 보여줄 모양으로."""
    cfg = cfg or load_config()
    day = day or datetime.now().strftime("%Y%m%d")
    rows = read_day(day, cfg)
    if not rows:
        return None
    r = max(rows, key=lambda x: (x.get("datetime") or ""))
    st = str(r.get("stage") or "0").strip()
    name, desc = STAGES.get(st, (r.get("stage_name") or "?", ""))
    return {
        "datetime": r.get("datetime"),
        "p10": _f(r.get("ml_score_10m"), 0.0),
        "p30": _f(r.get("ml_score_30m"), 0.0),
        "level10": (r.get("ml_level_10m") or "").strip() or "정상",
        "level30": (r.get("ml_level_30m") or "").strip() or "정상",
        "raw": _f(r.get("raw_value")),
        "smoothed": _f(r.get("smoothed")),
        "threshold": _f(r.get("threshold")),
        "stage": st, "stage_name": name, "stage_desc": desc,
        "lead_min": (r.get("lead_min") or "").strip(),
        "reason": (r.get("reason") or "").strip(),
        "backend": (r.get("backend") or "").strip(),
        "for10": r.get("prediction_for_10m"),
        "for30": r.get("prediction_for_30m"),
    }


def summary(day: str = "", cfg: dict | None = None) -> dict:
    """그 날 집계 — 단계별 분 수, 선제경보 구간, 최근 상태."""
    cfg = cfg or load_config()
    day = day or datetime.now().strftime("%Y%m%d")
    rows = read_day(day, cfg)
    by_stage = {k: 0 for k in STAGES}
    pmax10 = pmax30 = 0.0
    for r in rows:
        st = str(r.get("stage") or "0").strip()
        if st in by_stage:
            by_stage[st] += 1
        pmax10 = max(pmax10, _f(r.get("ml_score_10m"), 0.0) or 0.0)
        pmax30 = max(pmax30, _f(r.get("ml_score_30m"), 0.0) or 0.0)

    # 선제경보(2)·진행중(3) 이 이어진 구간을 사건으로 묶는다
    spans, cur = [], None
    for r in sorted(rows, key=lambda x: (x.get("datetime") or "")):
        st = str(r.get("stage") or "0").strip()
        if st in ("2", "3"):
            if cur is None:
                cur = {"from": r.get("datetime"), "to": r.get("datetime"),
                       "stage": st, "lead": (r.get("lead_min") or "").strip()}
            else:
                cur["to"] = r.get("datetime")
                if st == "3":
                    cur["stage"] = "3"        # 예보였다가 실제로 넘어갔다
        elif cur is not None:
            spans.append(cur)
            cur = None
    if cur is not None:
        spans.append(cur)

    return {
        "day": day, "rows": len(rows),
        "by_stage": by_stage,
        "stage_labels": {k: v[0] for k, v in STAGES.items()},
        "max_p10": round(pmax10, 4), "max_p30": round(pmax30, 4),
        "spans": spans[-20:],
        "latest": latest(day, cfg),
        "enabled": enabled(cfg),
    }


def day_range(d_from: str, d_to: str) -> list[str]:
    """'20260801','20260819' → 그 사이 날짜 목록 (양끝 포함).

    거꾸로 넣어도 알아서 바로잡는다 — 화면에서 실수하기 쉬운 자리다.
    """
    from datetime import timedelta
    a = "".join(ch for ch in str(d_from) if ch.isdigit())[:8]
    b = "".join(ch for ch in str(d_to) if ch.isdigit())[:8]
    if len(a) != 8 or len(b) != 8:
        return []
    if a > b:
        a, b = b, a
    try:
        cur = datetime.strptime(a, "%Y%m%d")
        end = datetime.strptime(b, "%Y%m%d")
    except ValueError:
        return []
    out = []
    while cur <= end and len(out) < 400:          # 400일이면 충분하고, 사고도 막는다
        out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


def read_range(d_from: str, d_to: str, cfg: dict | None = None) -> list[dict]:
    """여러 날을 한 목록으로 — 시각순. 없는 날은 그냥 건너뛴다."""
    cfg = cfg or load_config()
    rows: list[dict] = []
    for d in day_range(d_from, d_to):
        rows.extend(read_day(d, cfg))
    rows.sort(key=lambda r: (r.get("datetime") or ""))
    return rows


def export_csv(d_from: str, d_to: str, cfg: dict | None = None) -> str:
    """그 기간을 CSV 한 덩어리로. 원본 칸 그대로 — 분석에 바로 쓰라고."""
    import io
    rows = read_range(d_from, d_to, cfg)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def fetch_range(d_from: str, d_to: str, cfg: dict | None = None,
                skip_existing: bool = True) -> dict:
    """기간을 통째로 받아온다 (빠진 날 메우기).

    skip_existing 이면 이미 받아 둔 날은 건너뛴다 — 한 달치를 다시 받느라
    파일서버를 몇 십 번 두드릴 이유가 없다. 오늘은 아직 쌓이는 중이라 늘 받는다.
    """
    cfg = cfg or load_config()
    today = datetime.now().strftime("%Y%m%d")
    days = day_range(d_from, d_to)
    got = skipped = failed = added = 0
    errors: list[str] = []
    for d in days:
        if skip_existing and d != today and read_day(d, cfg):
            skipped += 1
            continue
        r = fetch_day(d, cfg)
        if r["error"]:
            failed += 1
            if len(errors) < 5:
                errors.append(f"{d}: {r['error'][:80]}")
        else:
            got += 1
            added += r["added"]
    return {"days": len(days), "fetched": got, "skipped": skipped,
            "failed": failed, "added": added, "errors": errors}


if __name__ == "__main__":                       # 손으로 한 번 받아 보기
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else ""
    res = fetch_day(d)
    print(f"받음: {res['rows']}행 (신규 {res['added']})"
          + (f" · 오류 {res['error']}" if res["error"] else ""))
    s = summary(d)
    print(f"단계별(분): " + " · ".join(
        f"{s['stage_labels'][k]} {v}" for k, v in s["by_stage"].items()))
    if s["latest"]:
        L = s["latest"]
        print(f"최근 {L['datetime']} · 10분 {L['p10']:.2f} / 30분 {L['p30']:.2f}"
              f" · {L['stage_name']} · 10분평균 {L['smoothed']} / 임계 {L['threshold']}")
