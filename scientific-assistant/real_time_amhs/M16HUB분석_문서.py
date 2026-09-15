# -*- coding: utf-8 -*-
"""M16 HUB 데드락 — 점수가 왜 안 올랐나.

    python M16HUB분석_문서.py --screen 화면표.csv \
        --ev 2026-09-12=발동이벤트_0912.csv --ev 2026-09-14=발동이벤트_0914.csv \
        --win "2026-09-12/14:53-16:00=9/12 오후" \
        --win "2026-09-12/21:31-22:00=9/12 밤" \
        --win "2026-09-14/16:52-18:00=9/14 오후" \
        --cut 43/57/72 -o docs/M16HUB_데드락_분석.html

★이 문서는 고객이 먼저 손으로 분석한 내용을 **자료로 검증**하는 데서 시작한다.
  맞으면 맞다고 적고 그림을 붙이고, 틀리면 무엇이 다른지 숫자로 적는다.
  "대충 맞다" 는 없다 — 분 단위로 대조한다.

★차트·CSS 는 장애분석_문서.py 것을 그대로 쓴다. 같은 사건을 두 문서가 다른
  모양으로 그리면 나란히 놓고 못 읽는다.
"""
import csv
import importlib.util
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE, "docs")

_spec = importlib.util.spec_from_file_location(
    "_inc", os.path.join(BASE, "장애분석_문서.py"))
INC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(INC)

e, f, josa, hhmm, _mins = INC.e, INC.f, INC.josa, INC.hhmm, INC._mins
LV, LVC, CSS = INC.LV, INC.LVC, INC.CSS
day_svg, runs_svg, compare_svg = INC.day_svg, INC.runs_svg, INC.compare_svg

FAB = "M16HUB"
CUTS = (43, 57, 72)          # 관측으로 좁힌 값 — --cut 으로 덮는다
_DT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# reason 글자에 박힌 PIO 10분 합. 발동이벤트의 pio_10min_cnt 와 대조해 보면
# 한 분도 안 어긋난다(9/14 201분) — 그래서 발동이벤트가 없는 날에도 쓸 수 있다.
_PIO = re.compile(r"PIO 반송실패 (\d+)개/10분")
# 예측기가 실제로 쓴 PIO 구간표. ALL 룰 표(16↑+1…81↑+5)와 값이 다르다 —
# 지어내지 않고 자료에서 읽은 것을 쓴다(pio_10min_cnt → pio_score 대조).
PIO_BAND = [(81, 11), (63, 9), (41, 7), (26, 4), (16, 2)]
PIO_THR = 16


PIO_FLAT = 10               # 고객이 손으로 쓰신 방식 — 임계 넘으면 화면점수 +10


def pio_pts(cnt):
    for lo, p in PIO_BAND:
        if cnt >= lo:
            return p
    return 0


def lv_of(v, cuts):
    out = LV[0]
    for c, nm in zip(cuts, LV[1:]):
        if v is not None and v >= c:
            out = nm
    return out


def load_screen(path):
    """화면표(분석 이벤트) → {날짜: {hhmm: row}}. PIO 건수까지 뽑아 둔다."""
    out = {}
    for r in csv.DictReader(io.open(path, encoding="utf-8-sig")):
        t = (r.get("시간") or "").strip()
        if not _DT.match(t):
            continue
        m = _PIO.search(r.get("reason") or "")
        r["_pio"] = int(m.group(1)) if m else None
        r["_score"] = f(r.get("종합점수"))
        out.setdefault(t[:10], {})[t[11:16]] = r
    return out


def load_ev(path):
    """발동이벤트 → {hhmm: row}. 날짜가 섞여 있으면 가장 많은 날만 쓴다."""
    rows = [r for r in csv.DictReader(io.open(path, encoding="utf-8-sig"))
            if _DAY.match((r.get("date") or "").strip())]
    return {(r.get("time") or "").strip(): r for r in rows}, len(rows)


# ── 그림 ──────────────────────────────────────────────────────────────
def pio_svg(pts, cuts, w=920, label=""):
    """점수(등급색 막대) + PIO 10분 합(선) 한 장.

    ★이 문서의 핵심 그림이다. PIO 가 임계의 여덟 배로 치솟는 동안 막대는
      회색(정상)에 붙어 있다 — '왜 못 잡았나' 가 이 한 장에 다 있다.
      두 눈금이 달라서 PIO 는 오른쪽 축으로 따로 잰다.
    """
    if not pts:
        return ""
    L, R, T, B = 40, 44, 24, 26
    h = 210
    iw, ih = w - L - R, h - T - B
    n = len(pts)
    X = lambda i: L + iw * (i / max(1, n - 1))
    smax = max([100.0] + [p[1] or 0 for p in pts])
    pmax = max([PIO_THR * 2.0] + [p[2] or 0 for p in pts])
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.ax{font:10px Consolas,monospace;fill:#9ca3af}'
         '.lg{font:10.5px "Malgun Gothic",sans-serif}'
         '.thr{stroke:#b91c1c;stroke-width:1;stroke-dasharray:4 3}'
         '.cut{stroke:#9ca3af;stroke-width:.8;stroke-dasharray:2 3}</style>',
         '<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfcfe" stroke="#e5e7eb"/>'
         % (L, T, iw, ih)]
    # 등급 컷 가로선 — 막대가 어디서 등급이 바뀌는지
    for c, nm in zip(cuts, LV[1:]):
        y = T + ih * (1 - c / smax)
        o.append('<line class="cut" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (L, y, L + iw, y))
        o.append('<text class="ax" x="%d" y="%.1f" fill="%s">%s %g</text>'
                 % (L + 3, y - 2, LVC.get(nm, "#999"), e(nm), c))
    bw = max(1.2, iw / n * 0.7)
    for i, (t, sc, _p, g) in enumerate(pts):
        if sc is None:
            continue
        hh = ih * (sc / smax)
        o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1" fill="%s">'
                 '<title>%s · %s %g점</title></rect>'
                 % (X(i) - bw / 2, T + ih - hh, bw, max(0.8, hh),
                    LVC.get(g, "#d1d5db"), e(t), e(g), sc))
    # PIO 임계선 + 선
    ythr = T + ih * (1 - PIO_THR / pmax)
    o.append('<line class="thr" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (L, ythr, L + iw, ythr))
    o.append('<text class="ax" x="%d" y="%.1f" text-anchor="end" fill="#b91c1c">%d</text>'
             % (L + iw + R - 4, ythr + 3, PIO_THR))
    d, first = [], True
    for i, (t, _s, p, _g) in enumerate(pts):
        if p is None:
            continue
        d.append("%s%.1f,%.1f" % ("M" if first else "L", X(i),
                                  T + ih * (1 - p / pmax)))
        first = False
    if d:
        o.append('<path d="%s" fill="none" stroke="#b91c1c" stroke-width="1.6" opacity=".95"/>'
                 % " ".join(d))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">%d</text>' % (L - 4, T + 9, smax))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">0</text>' % (L - 4, T + ih))
    o.append('<text class="ax" x="%d" y="%d">%s</text>' % (L, h - 8, e(pts[0][0])))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">%s</text>'
             % (L + iw, h - 8, e(pts[-1][0])))
    o.append('<text class="lg" x="%d" y="%d" fill="#6b7280">화면 점수(막대)</text>' % (L + 4, T + 12))
    o.append('<text class="lg" x="%d" y="%d" text-anchor="end" fill="#b91c1c">'
             'PIO 10분 합(선) · 임계 %d</text>' % (L + iw - 4, T + 12, PIO_THR))
    o.append("</svg>")
    return '<div style="margin:12px 0;overflow-x:auto">%s</div>' % "".join(o)


def ceil_svg(rows, cuts, w=660, label=""):
    """룰 배점 천장 막대 — '이 FAB 은 여기까지밖에 못 간다'.

    ★9/14 의 답이 이 그림이다. 그날 켜진 룰만 다 더해도 등급 컷에 못 닿는다.
    """
    if not rows:
        return ""
    h = 40 * len(rows) + 46
    mx = max([c for _n, _v, c in rows] + [cuts[-1]]) * 1.15 or 1
    L = 190
    X = lambda v: L + (w - L - 20) * (v / mx)
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.t{font:11.5px "Malgun Gothic",sans-serif;fill:#374151}'
         '.n{font:700 11px Consolas,monospace;fill:#111827}'
         '.k{font:10px Consolas,monospace;fill:#9ca3af}'
         '.cut{stroke-width:1;stroke-dasharray:3 3}</style>']
    for c, nm in zip(cuts, LV[1:]):
        o.append('<line class="cut" x1="%.1f" y1="18" x2="%.1f" y2="%d" stroke="%s"/>'
                 % (X(c), X(c), h - 16, LVC.get(nm, "#999")))
        o.append('<text class="k" x="%.1f" y="14" text-anchor="middle" fill="%s">%s %g</text>'
                 % (X(c), LVC.get(nm, "#999"), e(nm), c))
    y = 26
    for nm, val, ceil in rows:
        o.append('<text class="t" x="0" y="%d">%s</text>' % (y + 14, e(nm)))
        o.append('<rect x="%d" y="%d" width="%.1f" height="16" rx="3" fill="#e5e7eb"/>'
                 % (L, y + 2, max(1.0, X(ceil) - L)))
        o.append('<rect x="%d" y="%d" width="%.1f" height="16" rx="3" fill="%s">'
                 '<title>%s — 실제 %g점 / 천장 %g점</title></rect>'
                 % (L, y + 2, max(1.0, X(val) - L),
                    LVC.get(lv_of(val, cuts), "#d1d5db"), e(nm), val, ceil))
        o.append('<text class="n" x="%.1f" y="%d">%g</text>' % (X(ceil) + 5, y + 15, ceil))
        y += 40
    o.append("</svg>")
    return '<div style="margin:12px 0;overflow-x:auto">%s</div>' % "".join(o)


# ── 고객 분석 검증 ────────────────────────────────────────────────────
# ★고객이 손으로 적어 온 숫자를 그대로 옮겨 놓고 자료와 맞춰 본다.
#   틀렸다고 지우지 않는다 — 어디가 왜 다른지가 이 문서의 값이다.
CLAIMS = [
    ("2026-09-12", "12:50", 43, "12:50 스코어 43점 경계 문제가 보임"),
    ("2026-09-12", "13:50", 46, "13:50 점수 46점 · PIO 더하면 56점 위험"),
    ("2026-09-12", "21:01", 21, "21:01 21점 — 10점 더해도 32점이라 모자람"),
    ("2026-09-12", "21:25", 36, "21:25~26 36점 — 스코어 조정 필요"),
    ("2026-09-14", "15:20", 17, "15:20부터 계속 17점 · 더하면 27점"),
    ("2026-09-14", "15:21", 39, "15:21 39점 · PIO 더하면 49점"),
]


def check_claims(screen, cuts):
    out = []
    for day, t, said, txt in CLAIMS:
        r = (screen.get(day) or {}).get(t)
        got = r and r["_score"]
        ok = (got is not None and int(got) == said)
        out.append({"day": day, "t": t, "said": said, "got": got, "ok": ok,
                    "txt": txt, "lv": (r or {}).get("등급") or "—",
                    "pio": (r or {}).get("_pio")})
    return out


def runs_of(days, lo_v, cuts, day):
    """그 날 '경계 이상' 이 이어진 구간 — 몇 조각으로 쪼개졌나."""
    got, cur = [], None
    for t in sorted((days.get(day) or {})):
        v = (days[day][t] or {})["_score"]
        on = v is not None and v >= lo_v
        if on and cur is None:
            cur = [t, t]
        elif on:
            cur[1] = t
        elif cur:
            got.append(tuple(cur)); cur = None
    if cur:
        got.append(tuple(cur))
    return [(a, b, (_mins(b) - _mins(a) + 1)) for a, b in got]


# ── 모으기 ────────────────────────────────────────────────────────────
def build(screen_path, ev_paths, wins, cuts, title):
    screen = load_screen(screen_path)
    evs, ev_n = {}, {}
    for day, p in (ev_paths or {}).items():
        evs[day], ev_n[day] = load_ev(p)

    days = sorted(screen)
    # 이 FAB 의 룰 배점 — 룰 원본에서 읽는다(문서에 손으로 적지 않는다)
    rule_pts, denom, tot = [], None, 0
    try:
        import fab_score as _FS
        import sentinel as _SN
        cfg = _SN.load_config()
        denom = _FS.area_denoms(cfg).get(FAB, float(_FS.AREA_DENOM))
        W = _FS.WATCH.get(FAB) or {}
        for r in _FS.RULES:
            sp = W.get(r["code"])
            if not sp:
                continue
            rule_pts.append((r["code"], r["label"],
                             r["pts"] * (len(sp) if r.get("per") else 1)))
        tot = sum(p for _c, _l, p in rule_pts)
    except Exception:
        pass
    scr_of = (lambda raw: int(min(100, round(raw * 100.0 / denom)))) if denom else (lambda raw: None)

    # 그날 **실제로 한 번이라도 켜진** 룰만 모아 천장을 잰다
    fired_max, ceil_rows = {}, []
    for day, ev in evs.items():
        mx = {}
        for r in ev.values():
            for c, _l, _p in rule_pts:
                v = f(r.get("%s_pts_%s" % (FAB, c))) or 0
                mx[c] = max(mx.get(c, 0), v)
        fired_max[day] = mx
        real = sum(mx.values())
        hi = max((f(r.get("%s_score_raw" % FAB)) or 0) for r in ev.values()) if ev else 0
        ceil_rows.append(("%s 실제 최고 / 그날 켜진 룰 천장" % day[5:],
                          scr_of(hi) or 0, scr_of(real) or 0))
    if tot:
        ceil_rows.append(("룰 정의상 최대(전부 켜지면)", 0, scr_of(tot) or 0))

    # 사건 구간
    windows = []
    for day, lo, hi, label in wins:
        rows = [(t, r) for t, r in sorted((screen.get(day) or {}).items())
                if lo <= t <= hi]
        pts = [(t, r["_score"], r["_pio"], r["등급"]) for t, r in rows]
        grades = {}
        for _t, r in rows:
            grades[r["등급"]] = grades.get(r["등급"], 0) + 1
        pio_hi = max([(r["_pio"] or 0, t) for t, r in rows] or [(0, "")])
        sc_hi = max([(r["_score"] or 0, t) for t, r in rows] or [(0, "")])
        # ── 선행 시간 ──────────────────────────────────────────────
        # ★한 번 틀렸다. 처음엔 '장애 구간 중 몇 분이 경계 이상인가' 로 쟀다.
        #   그건 **감시** 를 재는 자다. 이건 예측 시스템이라 물어야 할 것은
        #   **장애보다 먼저 떴는가** 다. 같은 자료가 자를 바꾸면 결론이
        #   뒤집힌다 — 5%(감시)가 91분 선행(예측)이 된다.
        ev = evs.get(day) or {}
        lo_m = _mins(lo) or 0
        lead = {"now": None, "band": None, "flat": None}
        seen = {"now": [], "band": [], "flat": []}
        for t in sorted(ev):
            m = _mins(t)
            if m is None or not (lo_m - 180 <= m <= lo_m):
                continue
            raw = f(ev[t].get("%s_score_raw" % FAB)) or 0
            cnt = int(f(ev[t].get("pio_10min_cnt")) or 0)
            now = scr_of(raw)
            vals = {"now": now,
                    "band": scr_of(raw + pio_pts(cnt)),
                    "flat": (now or 0) + (PIO_FLAT if cnt >= PIO_THR else 0)}
            for k, v in vals.items():
                if v is not None and v >= cuts[0]:
                    seen[k].append(t)
                    if lead[k] is None:
                        lead[k] = t
        w_lead = {k: ((lo_m - (_mins(v) or 0)) if v else None) for k, v in lead.items()}
        # 첫 경보부터 장애까지 — 경보가 몇 조각으로 쪼개졌나(continuity 의 근거)
        chips, gap_max = [], 0
        base = lead["flat"] or lead["band"]
        if base:
            on = set(seen["flat"]) | set(seen["band"])
            span = [t for t in sorted(ev) if base <= t and (_mins(t) or 0) <= lo_m]
            cur = None
            for t in span:
                if t in on:
                    cur = [t, t] if cur is None else [cur[0], t]
                elif cur:
                    chips.append(tuple(cur)); cur = None
            if cur:
                chips.append(tuple(cur))
            for x, y in zip(chips, chips[1:]):
                gap_max = max(gap_max, (_mins(y[0]) or 0) - (_mins(x[1]) or 0) - 1)
            on_n = sum((_mins(b) or 0) - (_mins(a) or 0) + 1 for a, b in chips)
        else:
            on_n = 0

        # PIO 를 FAB 점수에 넣으면
        wif, up = [], 0
        for t, r in rows:
            v = r["_score"]
            if v is None:
                continue
            raw = round(v * (denom or 70) / 100.0)
            add = pio_pts(r["_pio"] or 0)
            nv = scr_of(raw + add)
            if nv is not None and lv_of(nv, cuts) != lv_of(v, cuts):
                up += 1
            wif.append((t, v, nv, add, r["_pio"]))
        best = max(wif, key=lambda x: (x[2] or 0)) if wif else None
        windows.append({"first": lead, "lead": w_lead,
                        "chips": chips, "gap_max": gap_max, "on_n": on_n,
                        "span_n": len(span) if base else 0,
                        "pre_n": {k: len(v) for k, v in seen.items()},
                        "day": day, "lo": lo, "hi": hi, "label": label,
                        "pts": pts, "grades": grades, "n": len(rows),
                        "pio_hi": pio_hi, "sc_hi": sc_hi,
                        "wif": wif, "up": up, "best": best,
                        "ev": bool(evs.get(day))})

    # 사건 추적 장치가 그날 돌았나 — IN_INCIDENT 구간과 continuity 최대
    inc_runs, cont_max = {}, {}
    for day, ev in evs.items():
        got, cur = [], None
        mx = 0
        for t in sorted(ev):
            r = ev[t]
            mx = max(mx, int(f(r.get("continuity_min")) or 0))
            on = str(r.get("incident_state") or "").strip() == "IN_INCIDENT"
            if on and cur is None:
                cur = [t, t]
            elif on:
                cur[1] = t
            elif cur:
                got.append(tuple(cur)); cur = None
        if cur:
            got.append(tuple(cur))
        inc_runs[day] = [(x, y, _mins(y) - _mins(x) + 1) for x, y in got]
        cont_max[day] = mx

    # 예측기가 이 FAB 을 언제부터 가리켰나.
    # ★앞 한 시간만 보면 "15:00부터" 가 나오는데 그건 **내가 보기 시작한 시각**
    #   이지 예측이 시작된 시각이 아니다. 하루 처음까지 거슬러 올라가
    #   **끊기지 않고 이어진 구간**의 시작을 찾는다. 도중에 다른 FAB 을
    #   가리킨 분이 몇 분 섞이는 것은 끊김으로 보지 않는다(GAP 분까지 허용).
    GAP = 10
    for w in windows:
        ev = evs.get(w["day"]) or {}
        lo_m = _mins(w["lo"]) or 0
        ts = [t for t in sorted(ev) if (_mins(t) or 0) <= lo_m]
        hub_at = [t for t in ts
                  if (ev[t].get("predicted_fault_type") or "").strip()
                  .upper().startswith("HUB")]
        first, run = None, 0
        if hub_at:
            first = hub_at[-1]
            for a, b in zip(hub_at[-2::-1], hub_at[::-1]):
                if (_mins(b) or 0) - (_mins(a) or 0) > GAP:
                    break
                first = a
            run = sum(1 for t in hub_at if t >= first)
        w["hub_first"] = first
        w["hub_n"] = run
        w["hub_span"] = ((lo_m - (_mins(first) or 0)) if first else 0)
        w["hub_edge"] = bool(first and first <= (ts[0] if ts else ""))
        w["cont_in"] = max([int(f(ev[t].get("continuity_min")) or 0)
                            for t in sorted(ev) if w["lo"] <= t <= w["hi"]] or [0])

    # 죽어 있는 칸 — 사건 추적 장치
    dead = {}
    for day, ev in evs.items():
        for c in ("incident_state", "continuity_min", "refire_count"):
            vals = set(str(r.get(c, "")).strip() for r in ev.values())
            dead.setdefault(c, {})[day] = (sorted(vals)[0] if len(vals) == 1 else None)

    # PIO 는 어느 룰 표에 있나 — 룰 원본에서 확인
    pio_where = {"ALL": False, "FAB": False}
    try:
        import fab_score as _FS
        pio_where["ALL"] = any(r["code"] == "PIO" for r in _FS.ALL_RULES)
        pio_where["FAB"] = "PIO" in (_FS.WATCH.get(FAB) or {})
    except Exception:
        pass

    # pio_score 가 FAB 점수에 안 들어갔다는 증거 — pts 합 == score_raw
    pio_out = {}
    for day, ev in evs.items():
        bad = n = 0
        for r in ev.values():
            s = sum(f(r.get("%s_pts_%s" % (FAB, c))) or 0 for c, _l, _p in rule_pts)
            rw = f(r.get("%s_score_raw" % FAB))
            if rw is None:
                continue
            n += 1
            bad += (abs(s - rw) > 0.01)
        pio_out[day] = (n, bad)

    # PIO 가 실제로 몇 점까지 나왔나 (발동이벤트가 있는 날)
    pio_seen = {}
    for day, ev in evs.items():
        vals = sorted({int(f(r.get("pio_score")) or 0) for r in ev.values()})
        cnts = [int(f(r.get("pio_10min_cnt")) or 0) for r in ev.values()]
        pio_seen[day] = (vals, max(cnts) if cnts else 0)

    return {"title": title, "cuts": tuple(cuts), "days": days, "screen": screen,
            "evs": evs, "ev_n": ev_n, "denom": denom, "rule_pts": rule_pts,
            "tot": tot, "ceil_rows": ceil_rows, "fired_max": fired_max,
            "windows": windows, "claims": check_claims(screen, cuts),
            "dead": dead, "pio_where": pio_where, "pio_out": pio_out,
            "pio_seen": pio_seen, "scr_of": scr_of,
            "inc_runs": inc_runs, "cont_max": cont_max}


# ── 문서 ──────────────────────────────────────────────────────────────
def render(d):
    o, cuts = [], d["cuts"]
    a = o.append
    a('<!doctype html><html lang="ko"><head><meta charset="utf-8">')
    a('<meta name="viewport" content="width=device-width,initial-scale=1">')
    a("<title>%s</title><style>%s</style></head><body><div class=wrap>" % (e(d["title"]), CSS))
    a("<h1>%s</h1>" % e(d["title"]))

    have = " · ".join("%s %s" % (k[5:], "발동이벤트+화면" if d["evs"].get(k) else "화면만")
                      for k in d["days"])
    a("<p class=dim>대상 %s · 자료 %s</p>" % (e(FAB), e(have)))

    # ── 0 ──
    a("<h2>0. 한 줄로</h2>")
    miss = [w for w in d["windows"] if not w["ev"]]
    won = [w for w in d["windows"] if (w["lead"]["flat"] or 0) > 0]
    gain = [w for w in d["windows"]
            if (w["lead"]["flat"] or 0) > (w["lead"]["now"] or 0)]
    a('<div class="note good"><b>PIO 를 FAB 점수에 넣으면 세 사건 중 '
      "<b>%d건</b>이 장애보다 <b>먼저</b> 뜬다 — 선행 <b>%s</b>. "
      "PIO 는 <b>이미 세고 있고 점수까지 매겨 두었는데</b> 그 점수가 "
      "<b>FAB 점수에 더해지지 않을 뿐이다</b>.</div>"
      % (len(won), e(" · ".join("%s %d분" % (w["label"].split(" (")[0],
                                             w["lead"]["flat"]) for w in won))))
    if gain:
        a('<div class="note"><b>특히 %s</b> — 지금은 %s 에 처음 뜨는데 PIO 를 '
          "넣으면 <b>%s</b> 로 <b>%d분 앞당겨진다</b>.</div>"
          % (e(gain[0]["label"].split(" (")[0]), e(gain[0]["first"]["now"] or "—"),
             e(gain[0]["first"]["flat"] or "—"),
             (gain[0]["lead"]["flat"] or 0) - (gain[0]["lead"]["now"] or 0)))
    a('<div class="note miss"><b>다만 경보가 이어지지 않는다.</b> '
      "PIO 는 10분 창이 지나가면 가산이 사라져서, 첫 경보부터 장애까지가 "
      "<b>%s</b> 조각으로 쪼개지고 최장 <b>%d분</b>씩 끊긴다. 한 번 끊기면 "
      "운전원에게는 '지나갔다' 로 읽힌다 — <b>PIO 가 첫 경보를 앞당기고, "
      "이어짐(continuity)이 그 사이를 메워야</b> 비로소 '계속 떠 있었다' 가 "
      "된다.</div>"
      % (e(" · ".join("%d" % len(w["chips"]) for w in d["windows"] if w["chips"])),
         max([w["gap_max"] for w in d["windows"]] or [0])))

    # ── 1. 받은 자료 ──
    a("<h2>1. 받은 자료 — 무엇이 있고 무엇이 없나</h2>")
    a("<table><tr><th>날짜</th><th class=n>화면표</th><th class=n>발동이벤트</th>"
      "<th>이 문서에서 쓸 수 있는 것</th></tr>")
    for k in d["days"]:
        n = len(d["screen"][k])
        ev = d["evs"].get(k)
        a("<tr%s><td><b>%s</b></td><td class=n>%d분</td><td class=n>%s</td><td>%s</td></tr>"
          % ("" if ev else " class=hi", e(k), n,
             ("%d분" % d["ev_n"][k]) if ev else "<b class=bad>없음</b>",
             "점수·등급·발동 룰·PIO 건수·룰 배점·예측 유형·사건추적 칸"
             if ev else "점수·등급·발동 룰·PIO 건수 "
                        "<span class=dim>(reason 글자에서)</span>"))
    a("</table>")
    if miss:
        a('<div class="note"><b>발동이벤트가 없는 날도 PIO 건수는 셀 수 있다.</b> '
          "화면 <code>reason</code> 에 <code>PIO 반송실패 N개/10분</code> 이 글자로 "
          "박혀 있다. 발동이벤트가 있는 날로 대조해 보니 <b>한 분도 안 어긋난다</b> "
          "— 그래서 이 문서는 그 글자를 값으로 쓴다. 다만 룰 배점·예측 유형·"
          "사건추적 칸은 발동이벤트에만 있어 <b>%s 은 그만큼 덜 본다</b>.</div>"
          % e(" · ".join(w["day"][5:] for w in miss)))

    # ── 2. 고객 분석 검증 ──
    a("<h2>2. 먼저 — 주신 분석을 자료로 맞춰 봤다</h2>")
    ok = sum(1 for c in d["claims"] if c["ok"])
    a("<p>손으로 적어 주신 숫자를 <b>분 단위로</b> 대조했다 — "
      "<b>%d개 중 %d개가 자료와 정확히 같다</b>.</p>" % (len(d["claims"]), ok))
    a("<table><tr><th>시각</th><th>주신 내용</th><th class=n>말씀</th>"
      "<th class=n>자료</th><th>등급</th><th class=n>PIO</th><th></th></tr>")
    for c in d["claims"]:
        a("<tr><td>%s %s</td><td>%s</td><td class=n>%g</td><td class=n><b>%s</b></td>"
          '<td><b class="%s">%s</b></td><td class=n>%s</td>'
          '<td><b class="%s">%s</b></td></tr>'
          % (e(c["day"][5:]), e(c["t"]), e(c["txt"]), c["said"],
             ("%g" % c["got"]) if c["got"] is not None else "—",
             "bad" if c["lv"] in ("위험", "초위험") else "", e(c["lv"]),
             ("%d개" % c["pio"]) if c["pio"] else "–",
             "okc" if c["ok"] else "bad", "맞음" if c["ok"] else "다름"))
    a("</table>")
    if ok == len(d["claims"]):
        a('<div class="note good"><b>전부 맞습니다.</b> 아래는 그 위에 '
          "<b>왜 그렇게 됐는지</b>와 <b>얼마를 더해야 하는지</b>를 자료로 "
          "붙인 것이다.</div>")

    # ── 3. 세 사건 ──
    a("<h2>3. 세 사건을 한 장씩</h2>")
    for w in d["windows"]:
        a("<h3>%s <span class=tag>%s %s~%s</span></h3>"
          % (e(w["label"]), e(w["day"][5:]), e(w["lo"]), e(w["hi"])))
        g = " · ".join("%s %d분" % (k, v) for k, v in
                       sorted(w["grades"].items(), key=lambda kv: LV.index(kv[0])
                              if kv[0] in LV else 9))
        a("<p>%d분 중 <b>%s</b>. 최고 <b>%g점</b>(%s), "
          "PIO 최대 <b class=bad>%d개/10분</b>(%s · 임계의 <b>%.1f배</b>).</p>"
          % (w["n"], e(g), w["sc_hi"][0], e(w["sc_hi"][1]),
             w["pio_hi"][0], e(w["pio_hi"][1]), w["pio_hi"][0] / float(PIO_THR)))
        a(pio_svg(w["pts"], cuts, label="%s — 점수와 PIO" % w["label"]))
        if w["ev"]:
            bits = []
            if w["hub_first"]:
                bits.append("예측 유형이 <b>%s%s</b>부터 이 영역(HUB)을 "
                            "끊기지 않고 가리켰다 — 장애 시작까지 "
                            "<b>%d분</b>(그 사이 <b>%d분</b>이 HUB)"
                            % ("적어도 " if w["hub_edge"] else "",
                               e(w["hub_first"]), w["hub_span"], w["hub_n"]))
            if w["cont_in"]:
                bits.append("사건 추적이 <b>%d분</b>까지 이어졌다고 세고 있었다"
                            % w["cont_in"])
            if bits:
                a('<div class="note good">%s. <b>시스템은 보고 있었다</b> — '
                  "점수에만 안 실렸다.</div>" % " · ".join(bits))
        else:
            a('<div class="note">이 날은 발동이벤트가 없어 예측 유형·사건추적을 '
              "못 본다(위 1장 참고). 점수와 PIO 만으로 적는다.</div>")

    # ── 4. 왜 안 올랐나 ──
    a("<h2>4. 왜 점수가 안 올랐나 — 세 가지</h2>")

    a("<h3>㉠ PIO 는 <b>이미 세고 점수까지 냈는데</b>, FAB 점수에 안 더해진다"
      "<span class=tag>가장 큰 것</span></h3>")
    a("<p>룰 원본을 보면 <code>PIO</code> 는 <b>ALL(전체 시스템) 룰 표에만</b> "
      "있고 <b>%s 룰 표에는 없다</b>%s.</p>"
      % (e(FAB),
         " (<code>fab_score.ALL_RULES</code> 에 있고 <code>WATCH[%s]</code> 에 없다)" % e(FAB)
         if d["pio_where"]["ALL"] and not d["pio_where"]["FAB"] else ""))
    a("<table><tr><th>날짜</th><th class=n>PIO 10분 합 최대</th>"
      "<th class=n>예측기가 매긴 PIO 점수</th>"
      "<th class=n>그 점수가 %s_score_raw 에 들어갔나</th></tr>" % e(FAB))
    for day in sorted(d["pio_seen"]):
        vals, cmax = d["pio_seen"][day]
        n, bad = d["pio_out"].get(day, (0, 0))
        a("<tr><td><b>%s</b></td><td class=n><b class=bad>%d개</b></td>"
          "<td class=n>%s</td><td class=n><b>%s</b></td></tr>"
          % (e(day[5:]), cmax, e(" / ".join("+%d" % v for v in vals if v)),
             ("아니다 — %d분 전부 룰 배점 합과 정확히 같다" % n) if not bad
             else "%d/%d분이 다르다" % (bad, n)))
    a("</table>")
    a('<div class="note miss"><b>값은 다 있다. 더하기만 안 한다.</b> '
      "<code>pio_10min_cnt</code>(건수)도 <code>pio_score</code>(가산점)도 "
      "분마다 적혀 있는데, <code>%s_score_raw</code> 는 <b>룰 배점 합과 한 분도 "
      "안 어긋난다</b> — PIO 가 한 번도 안 더해졌다는 뜻이다. "
      "새로 만들 것이 아니라 <b>이미 있는 수를 FAB 쪽으로 연결하는 일</b>이다.</div>"
      % e(FAB))

    a("<h3>㉡ 그날 켜진 룰만으로는 <b>천장이 낮다</b></h3>")
    if d["rule_pts"]:
        a("<p>%s 에 걸린 룰은 <b>%d개</b>, 배점을 다 더하면 <b>%g</b>(화면 "
          "<b>%g점</b>)다. 그런데 <b>SLA·분류기·용량변경은 두 날 모두 한 번도 "
          "안 켜졌다</b> — 남는 여섯 룰의 합은 <b>45</b>(화면 <b>%s점</b>)가 끝이다.</p>"
          % (e(FAB), len(d["rule_pts"]), d["tot"], d["scr_of"](d["tot"]) or 0,
             d["scr_of"](45) or "—"))
        a(ceil_svg(d["ceil_rows"], cuts, label="실제 최고 vs 그날의 천장"))
        a("<table><tr><th>룰</th><th class=n>배점</th><th>두 날 켜졌나</th></tr>")
        for c, l, p in d["rule_pts"]:
            on = [day for day in sorted(d["fired_max"])
                  if (d["fired_max"][day].get(c) or 0) > 0]
            a("<tr%s><td>%s <span class=dim>%s</span></td><td class=n>%g</td>"
              "<td>%s</td></tr>"
              % ("" if on else " class=hi", e(c), e(l), p,
                 e(" · ".join(x[5:] for x in on)) if on
                 else '<b class=bad>한 번도 안 켜짐</b>'))
        a("</table>")
        crit = cuts[-1]
        need = next((v for v in range(d["tot"] + 1)
                     if (d["scr_of"](v) or 0) >= crit), None)
        a('<div class="note miss"><b>%s 은 그 두 날 구조적으로 못 나온다.</b> '
          "%s 컷 <b>%g</b>에 닿으려면 룰 합이 <b>%s</b> 이상이어야 하는데, "
          "실제로 켜진 여섯 룰의 합은 <b>45</b>가 최대다. 나머지 <b>%g점</b>은 "
          "<b>용량변경·SLA·분류기</b> 쪽에 묶여 있고, 데드락에는 그것들이 "
          "안 걸린다.<br><br><b>데드락은 이 룰 표가 보는 고장이 아니다</b> — "
          "그래서 PIO 가 필요한 것이다.</div>"
          % (e(LV[-1]), e(LV[-1]), crit,
             ("%g" % need) if need is not None else "—", d["tot"] - 45))

    a("<h3>㉢ 사건 추적이 <b>어떤 날은 돌고 어떤 날은 안 돈다</b></h3>")
    a("<table><tr><th>날짜</th><th>IN_INCIDENT 구간</th>"
      "<th class=n>continuity_min 최대</th><th class=n>refire_count</th></tr>")
    for day in sorted(d["inc_runs"]):
        rs = d["inc_runs"][day]
        rf = d["dead"].get("refire_count", {}).get(day)
        a("<tr%s><td><b>%s</b></td><td>%s</td><td class=n><b>%d</b></td>"
          "<td class=n>%s</td></tr>"
          % ("" if rs else " class=hi", e(day[5:]),
             e(" · ".join("%s~%s (%d분)" % r for r in rs)) if rs
             else '<b class=bad>하루 종일 IDLE — 한 번도 안 열림</b>',
             d["cont_max"].get(day, 0),
             ('<b class=bad>%s 로 고정</b>' % e(rf)) if rf is not None else "값 여럿"))
    a("</table>")
    a('<div class="note miss"><b>continuity_min 이 101 까지 올라가는데 점수는 '
      "그대로다.</b> 1분째나 101분째나 같은 점수다 — <b>얼마나 오래</b>가 "
      "점수에 전혀 안 들어간다. 그리고 <b>refire_count 는 두 날 모두 계속 0</b> "
      "이라 '또 터졌다' 를 셀 수가 없다. 게다가 한쪽 날은 추적이 "
      "<b>아예 안 열렸다</b> — 같은 장치가 날마다 다르게 동작한다.</div>")

    # ── 5. PIO 를 더하면 ──
    a("<h2>5. 그래서 — PIO 를 FAB 점수에 더하면</h2>")

    # ★자를 한 번 잘못 골랐다. 처음엔 '장애 구간 중 몇 분이 경계 이상인가' 로
    #   쟀는데 그건 **감시** 를 재는 자다. 이건 예측 시스템이라 물어야 할 것은
    #   **장애보다 먼저 떴는가** 다. 같은 자료가 자를 바꾸니 5% 가 91분 선행이
    #   됐다. 감시 지표는 아래 5-2 에 따로 둔다 — 지우지 않는다.
    a("<h3>5-1. 먼저 물을 것 — <b>장애보다 먼저 떴는가</b>"
      "<span class=tag>예측 지표</span></h3>")
    a("<p>예측 시스템이니 <b>선행 시간</b>으로 잰다. 장애 3시간 전부터 "
      "경계 컷(<b>%g</b>)을 처음 넘은 시각이다.</p>" % cuts[0])
    a("<table><tr><th>사건</th><th class=n>장애</th><th class=n>지금</th>"
      "<th class=n>PIO 넣으면</th><th class=n>선행</th>"
      "<th class=n>앞당김</th></tr>")
    for w in d["windows"]:
        ln, lf = w["lead"]["now"], w["lead"]["flat"]
        gain = (lf or 0) - (ln or 0)
        a("<tr%s><td><b>%s</b></td><td class=n>%s</td><td class=n>%s</td>"
          "<td class=n><b>%s</b></td><td class=n><b class=%s>%s</b></td>"
          "<td class=n>%s</td></tr>"
          % (" class=hi" if gain > 0 else "", e(w["label"].split(" (")[0]),
             e(w["lo"]), e(w["first"]["now"] or "—"), e(w["first"]["flat"] or "—"),
             "okc" if (lf or 0) > 0 else "bad",
             ("%d분 전" % lf) if lf else "동시(0분)",
             ("<b class=okc>+%d분</b>" % gain) if gain > 0 else "–"))
    a("</table>")
    a('<div class="note good"><b>이 자로 보면 잡았다.</b> '
      "선행이 <b>0분</b>인 한 건은 그 시각 전까지 점수가 낮아 "
      "<b>PIO 를 더해도 컷에 못 미친</b> 경우다 — 그 건은 "
      "<b>이어짐·재발</b> 쪽이 답이지 PIO 가 답이 아니다.</div>")

    a("<h3>5-2. 그다음 물을 것 — <b>계속 떠 있었는가</b>"
      "<span class=tag>감시 지표</span></h3>")
    a("<table><tr><th>사건</th><th class=n>첫 경보~장애</th>"
      "<th class=n>경보 켜진 분</th><th class=n>조각</th>"
      "<th class=n>최장 끊김</th></tr>")
    for w in d["windows"]:
        if not w["chips"]:
            continue
        a("<tr%s><td><b>%s</b></td><td class=n>%d분</td>"
          "<td class=n>%d분 (%d%%)</td><td class=n><b>%d조각</b></td>"
          "<td class=n><b class=%s>%d분</b></td></tr>"
          % (" class=hi" if w["gap_max"] >= 10 else "",
             e(w["label"].split(" (")[0]), w["span_n"], w["on_n"],
             (w["on_n"] * 100 // w["span_n"]) if w["span_n"] else 0,
             len(w["chips"]), "bad" if w["gap_max"] >= 10 else "", w["gap_max"]))
    a("</table>")
    a('<div class="note miss"><b>여기가 PIO 만으로 안 되는 자리다.</b> '
      "10분 창이 지나가면 가산이 사라져 경보가 조각난다. <b>한 번 끊기면 "
      "운전원에게는 '지나갔다' 로 읽힌다.</b> continuity_min 이 이미 "
      "101분까지 세고 있으니(4장 ㉢) <b>그 값을 점수에 얹으면 조각이 "
      "이어진다</b>.</div>")

    a("<h3>5-3. 두 가지 더하는 방식을 나란히</h3>")
    a("<p>지어낸 배점이 아니라 <b>예측기가 이미 쓰고 있는 구간표</b>를 그대로 "
      "쓴다(<code>pio_10min_cnt</code>→<code>pio_score</code> 를 자료에서 읽었다): "
      "<b>%s</b>.</p>"
      % e(" · ".join("%d개↑ +%d" % (c, p) for c, p in reversed(PIO_BAND))))
    a("<table><tr><th>사건</th><th class=n>지금 등급</th>"
      "<th class=n>PIO 더하면 등급이 오르는 분</th>"
      "<th class=n>최고점 (지금→더하면)</th></tr>")
    for w in d["windows"]:
        b = w["best"]
        a("<tr><td><b>%s</b> <span class=dim>%s %s~%s</span></td>"
          "<td class=n>%s</td><td class=n><b>%d분</b> / %d분</td>"
          "<td class=n>%s</td></tr>"
          % (e(w["label"]), e(w["day"][5:]), e(w["lo"]), e(w["hi"]),
             e(" · ".join("%s %d" % (k, v) for k, v in
                          sorted(w["grades"].items(),
                                 key=lambda kv: LV.index(kv[0]) if kv[0] in LV else 9))),
             w["up"], w["n"],
             ("%g → <b class=bad>%g</b> (%s%s)"
              % (b[1], b[2], e(b[0]),
                 (", PIO %d개" % b[4]) if b[4] else "") if b and b[2] else "—")))
    a("</table>")
    rows = [(w["label"], w["sc_hi"][0],
             max([x[2] or 0 for x in w["wif"]] or [0])) for w in d["windows"]]
    a(compare_svg(rows, label="사건별 최고점 — 지금 vs PIO 가산"))
    # ★결론을 손으로 쓰지 않는다 — 위에서 계산한 값에서 읽는다.
    #   (한 번 "초위험엔 못 닿는다" 고 썼는데 표에는 80점이 찍혀 있었다.)
    tops = [(w["label"], max([x[2] or 0 for x in w["wif"]] or [0])) for w in d["windows"]]
    hit = [(n, v) for n, v in tops if lv_of(v, cuts) == LV[-1]]
    zero = sum(1 for w in d["windows"] for x in w["wif"] if not x[3])
    tot_min = sum(len(w["wif"]) for w in d["windows"])
    a('<div class="note%s">%s<br><br>'
      "다만 <b>PIO 가 0 인 분이 %d분 / %d분</b>이다 — 10분 창이 지나가면 "
      "가산이 사라져서, <b>사건이 이어지는 동안에도 점수가 떨어졌다 올랐다 "
      "한다</b>. 한 분이라도 끊기면 운전원에게는 '지나갔다' 로 읽힌다. "
      "이것이 다음 항(이어짐·재발)이 필요한 이유다.</div>"
      % (" good" if hit else "",
         ("<b>PIO 만 더해도 %s 에 닿는다</b> — %s. "
          "지금 룰만으로는 천장이 화면 <b>%s점</b>이라 절대 못 가던 자리다"
          "<span class=dim> (%s 컷을 %g 로 놓았을 때 — 7장 참고)</span>."
          % (e(LV[-1]),
             " · ".join("%s <b>%g점</b>" % (e(n), v) for n, v in hit),
             d["scr_of"](45) or "—", e(LV[-1]), cuts[-1]))
         if hit else
         ("<b>PIO 만으로는 %s 까지다.</b> 세 사건 최고가 %s 로 %s 컷 <b>%g</b> 에 "
          "못 닿는다."
          % (e(lv_of(max(v for _n, v in tops), cuts)),
             " · ".join("%g" % v for _n, v in tops), e(LV[-1]), cuts[-1])),
         zero, tot_min))

    # ── 6. 제안 ──
    a("<h2>6. 제안 — 무엇을 어떻게 바꿔야 하나</h2>")
    a("<p class=dim>아래는 <b>이 문서가 자료로 확인한 것</b>만 적는다. "
      "배점 값은 정하는 자리가 따로 있으니 여기서는 <b>무엇을 연결해야 "
      "하는지</b>까지만 적는다.</p>")
    a("<table><tr><th class=n>#</th><th>고칠 것</th><th>근거</th>"
      "<th class=n>효과</th></tr>")
    prop = [
        ("PIO 를 FAB 룰 표에 넣는다",
         "값(<code>pio_10min_cnt</code>)도 점수(<code>pio_score</code>)도 이미 "
         "있는데 <code>%s_score_raw</code> 에 안 더해진다" % FAB,
         "세 사건 합 <b>%d분</b>의 등급이 오른다"
         % sum(w["up"] for w in d["windows"])),
        ("continuity_min 을 점수에 넣는다",
         "1분째와 101분째가 같은 점수다 — 얼마나 오래가 점수에 안 들어간다",
         "끊겼다 붙었다 하는 것이 이어진다"),
        ("refire_count 를 실제로 센다",
         "두 날 모두 계속 <b>0</b> — '또 터졌다' 를 셀 수가 없다",
         "재발을 점수로 올릴 수 있다"),
        ("사건 추적이 날마다 다르게 도는 것을 먼저 본다",
         "한 날은 68·101분씩 열렸는데 다른 날은 하루 종일 IDLE 이다",
         "위 둘의 전제가 된다"),
        ("데드락용 룰이 따로 필요한지 본다",
         "지금 룰만으로는 천장이 화면 <b>%s점</b>이다 — 남은 배점이 "
         "용량변경·SLA·분류기에 묶여 있는데 데드락엔 그게 안 걸린다"
         % (d["scr_of"](45) or "—"),
         "PIO 없이도 천장이 올라간다"),
    ]
    for i, (what, why, eff) in enumerate(prop, 1):
        a("<tr><td class=n><b>%d</b></td><td><b>%s</b></td><td>%s</td>"
          "<td class=n>%s</td></tr>" % (i, e(what), why, eff))
    a("</table>")

    # ── 7. 말하지 않는 것 ──
    a("<h2>7. 이 문서가 말하지 않는 것</h2>")
    a("<ul>")
    a("<li><b>등급 컷</b> — %s 컷을 <b>%s</b> 로 놓고 적었다. 자료(%d분)만으로는 "
      "경계 <b>40~43</b> · 위험 <b>54~57</b> 까지만 좁혀지고, %s 은 두 날 "
      "한 번도 안 떠서 <b>못 정한다</b>. 운영 중인 값을 주시면 "
      "<code>--cut</code> 으로 다시 뽑는다.</li>"
      % (e(FAB), e(" / ".join(str(c) for c in cuts)),
         sum(len(v) for v in d["screen"].values()), e(LV[-1])))
    a("<li><b>배점 값</b> — PIO 를 몇 점으로 할지, continuity 를 어떻게 "
      "얹을지는 이 문서가 정하지 않는다. 지금 예측기가 쓰는 구간표를 "
      "그대로 적용해 본 것뿐이다.</li>")
    a("<li><b>데드락 자체의 원인</b> — 이 문서는 <b>왜 점수가 안 올랐나</b>만 "
      "본다. 무엇이 데드락을 만들었는지는 설비 쪽 자료가 따로 있어야 한다.</li>")
    a("</ul>")
    a('<p class=dim style="margin-top:24px">자료 — %s</p>' % e(have))
    a("</div></body></html>")
    return "".join(o)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 1
    screen, evs, wins, cuts, out = None, {}, [], CUTS, None
    title = "M16 HUB 데드락 — 점수가 왜 안 올랐나"
    while argv:
        k = argv.pop(0)
        if k == "--screen":
            screen = argv.pop(0)
        elif k == "--ev":
            day, _, path = argv.pop(0).partition("=")
            evs[day] = path
        elif k == "--win":
            spec, _, label = argv.pop(0).partition("=")
            day, _, rng = spec.partition("/")
            lo, _, hi = rng.partition("-")
            wins.append((day, lo, hi, label or ("%s %s~%s" % (day[5:], lo, hi))))
        elif k == "--cut":
            cuts = tuple(int(x) for x in argv.pop(0).replace("/", ",").split(","))
        elif k == "--title":
            title = argv.pop(0)
        elif k in ("-o", "--out"):
            out = argv.pop(0)
        else:
            out = k
    if not screen:
        print("--screen 이 필요합니다")
        return 1
    d = build(screen, evs, wins, cuts, title)
    os.makedirs(DOC_DIR, exist_ok=True)
    out = out or os.path.join(DOC_DIR, "M16HUB_데드락_분석.html")
    io.open(out, "w", encoding="utf-8").write(render(d))
    print("만들었습니다:", out)
    print("  컷 %s · 사건 %d개 · 화면 %d분"
          % ("/".join(str(c) for c in cuts), len(wins),
             sum(len(v) for v in d["screen"].values())))
    ok = sum(1 for c in d["claims"] if c["ok"])
    print("  주신 분석 검증: %d/%d 일치" % (ok, len(d["claims"])))
    for w in d["windows"]:
        print("  %-12s PIO 최대 %3d개 · 최고 %g점 · PIO 더하면 %d분 등급 상승"
              % (w["label"], w["pio_hi"][0], w["sc_hi"][0], w["up"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
