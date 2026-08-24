"""
real_time_amhs/fab_score_doc.py — 'FAB 별로는 어떻게 다른가' 문서를 만든다

    python fab_score_doc.py            → docs/FAB별_위험도_스코어.html
    python fab_score_doc.py 파일.html   → 그 경로로

왜 생성하나 — 손으로 쓰면 어긋난다
    기존 '스코어 산출' 문서는 손으로 쓴 것이라, thresholds.json 이 바뀌면
    문서만 옛날 값으로 남는다. 이 문서의 숫자는 전부 fab_score.py 의
    WATCH / RULES / solo_ceiling() 에서 뽑는다. config.fab_score 로 임계를
    덮으면 문서도 같이 따라간다. 등급 컷도 config.grade 에서 읽는다
    (경계 60 · 위험 71 · 초위험 85 — 50 이 아니다).

스타일
    docs/style.css 는 기존 문서에서 그대로 가져온 것이다. 같은 집안 문서로
    보여야 현장에서 두 개를 나란히 놓고 읽는다. 파일 하나로 끝나야 해서
    (사내망엔 CDN 이 없다) 생성할 때 통째로 넣는다.
"""
from __future__ import annotations

import html
import os

import fab_score as F

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE_DIR, "docs")
OUT = os.path.join(DOC_DIR, "FAB별_위험도_스코어.html")

# RA_sus·RB_fast 는 독립 임계가 아니라 상위 룰의 배수다 — 문서에 그대로 밝힌다
DERIVED = {"RA_sus": ("RA", 0.7), "RB_fast": ("RB", 0.3)}


def e(s) -> str:
    return html.escape("" if s is None else str(s))


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def _thr_cell(fab: str, rule: str, cfg) -> str:
    """임계값 칸. 여러 조건이면 줄바꿈해서 전부, 없으면 '—', 미정의면 표시."""
    items = F.watch(fab, cfg).get(rule) or []
    if not items:
        return '<span class="none">—</span>'
    out = []
    for it in items:
        thr, op = it.get("thr"), it.get("op") or ">="
        if thr is None:
            out.append('<span class="undef">임계 미정의</span>')
            continue
        sign = {"<=": "≤", "diff10": "10분 +", ">=": "≥"}.get(op, "≥")
        unit = it.get("unit") or ""
        cell = f'{sign} {fmt(thr)}{e(unit)}'
        if it.get("normal") is not None:
            cell += f' <span class="th">(평상 {fmt(it["normal"])})</span>'
        out.append(cell)
    return "<br>".join(out)


def _col_cell(fab: str, rule: str, cfg) -> str:
    items = F.watch(fab, cfg).get(rule) or []
    if not items:
        return '<span class="none">—</span>'
    out = []
    for it in items:
        csv = it.get("csv") or ""
        tail = (f'<span class="th">CSV {e(csv)}</span>' if csv
                else '<span class="nocsv">CSV 에 값 없음</span>')
        out.append(f'<span class="amos">{e(it["amos"])}</span><br>{tail}')
    return '<div class="colstack">' + "</div><div class='colstack'>".join(out) + "</div>"


# ────────────────────────────── 조각들 ──────────────────────────────
def grid_thresholds(fabs, cfg) -> str:
    """룰 × FAB 임계값 격자 — 이 문서의 본론."""
    head = "".join(f'<th class="n">{e(f)}</th>' for f in fabs)
    rows = []
    for r in F.RULES:
        code = r["code"]
        pts = f'{r["pts"]}×n' if r.get("per") else r["pts"]
        note = ""
        if code in DERIVED:
            src, mul = DERIVED[code]
            note = f'<span class="rdesc">임계 = R-{src} × {mul:g}</span>'
        cells = "".join(f'<td class="n">{_thr_cell(f, code, cfg)}</td>' for f in fabs)
        rows.append(
            f'<tr><td class="rule">{e(_rname(code))}'
            f'<span class="rdesc">{e(r["label"])}</span>{note}</td>'
            f'<td class="n"><span class="pts">{pts}</span></td>{cells}</tr>')
    return (f'<div class="tw"><table class="grid"><thead><tr>'
            f'<th>룰</th><th class="n">배점</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def _rname(code: str) -> str:
    return {"RA": "R-A", "RA_sus": "R-A′", "RB": "R-B", "RB_fast": "R-B fast",
            "RC": "R-C", "RD": "R-D"}.get(code, code)


def _all_cell(code: str, cfg) -> str:
    """ALL 칸 — 영역 룰(R-A…R-D)은 ALL 이 직접 안 본다. 그렇다고 '없음' 이
    아니라 '영역별로만 본다' 가 맞는 말이다. SLA·소터·MAXCAPA 는 ALL 에
    **집계 컬럼**이 따로 있다."""
    items = F.watch("ALL", cfg).get(code) or []
    if not items:
        return '<span class="none">영역별로만</span>'
    out = []
    for it in items:
        out.append(f'<span class="amos">{e(it["amos"])}</span><br>'
                   f'<span class="th">CSV {e(it["csv"])}</span>')
    return '<div class="colstack">' + "</div><div class='colstack'>".join(out) + "</div>"


def grid_columns(fabs, cfg) -> str:
    """룰 × (ALL + FAB) 컬럼 격자 — '실제로 보고 있는 컬럼' 정의."""
    head = '<th>ALL</th>' + "".join(f'<th>{e(f)}</th>' for f in fabs)
    rows = []
    for r in F.RULES:
        code = r["code"]
        cells = (f'<td class="col allcol">{_all_cell(code, cfg)}</td>'
                 + "".join(f'<td class="col">{_col_cell(f, code, cfg)}</td>'
                           for f in fabs))
        rows.append(f'<tr><td class="rule">{e(_rname(code))}'
                    f'<span class="rdesc">{e(r["label"])}</span></td>{cells}</tr>')
    # ALL 만 갖는 항 — 흐름과 융합 집계. FAB 칸은 비운다.
    for code in ("FLOW", "FUSE", "SCORE"):
        r = next(x for x in F.ALL_RULES if x["code"] == code)
        rows.append(
            f'<tr class="allonly"><td class="rule">{e(code)}'
            f'<span class="rdesc">{e(r["label"])}</span></td>'
            f'<td class="col allcol">{_all_cell(code, cfg)}</td>'
            f'<td class="col th" colspan="{len(fabs)}">ALL 에만 있는 항입니다 '
            f'— 영역 점수에는 안 들어갑니다</td></tr>')
    return (f'<div class="tw"><table class="grid cols"><thead><tr>'
            f'<th>룰</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def join_table(sys: str, cfg) -> str:
    """화면이 이미 그리는 지표 ⇄ 룰/임계."""
    j = F.join_columns(sys, cfg)
    rows = ""
    for m in j["metrics"]:
        if m["used"]:
            tag = " · ".join(_rname(c) for c in m["rules"])
            # 임계로 판정하지 않는 항(집계·판정결과·배수)에 '임계 미정의' 라고
            # 쓰면 빠뜨린 것처럼 읽힌다. 무엇으로 판정하는지 그대로 적는다.
            how = {"sum": "집계값", "score": "판정 결과", "text": "판정 결과",
                   "ratio30": "30분 평균 대비 배수"}
            thr = " / ".join(
                (how.get(op) or "임계 미정의") if t is None else fmt(t)
                for t, op in zip(m["thr"], m["op"]))
            cls = ""
        else:
            tag = '<span class="none">쓰지 않음</span>'
            thr = '<span class="th">참고 표시용</span>'
            cls = ' class="off"'
        rows += (f'<tr{cls}><td class="mono" style="font-size:11.5px">{e(m["key"])}</td>'
                 f'<td>{e(m["label"])}</td>'
                 f'<td class="col"><span class="amos">{e(m["raw"])}</span></td>'
                 f'<td>{tag}</td><td class="n">{thr}</td></tr>')
    for x in j["only_rule"]:
        rows += (f'<tr class="miss"><td class="mono" style="font-size:11.5px">'
                 f'{e(x["key"])}</td><td>{e(x["label"])}</td>'
                 f'<td class="col"><span class="amos">{e(x["raw"])}</span></td>'
                 f'<td>{" · ".join(_rname(c) for c in x["rules"])}</td>'
                 f'<td class="n"><span class="undef">화면에 없음</span></td></tr>')
    return (f'<div class="tw"><table><thead><tr><th>CSV 컬럼</th><th>이름</th>'
            f'<th>AMOS 컬럼</th><th>쓰는 룰</th><th class="n">임계</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="pipe-note" style="margin-top:8px">화면 지표 '
            f'<b>{j["n_screen"]}개</b> 중 룰이 실제로 쓰는 것 '
            f'<b>{j["n_used"]}개</b>'
            + (f' · 룰은 보는데 화면 목록에 없는 컬럼 '
               f'<b style="color:var(--g2)">{len(j["only_rule"])}개</b>'
               if j["only_rule"] else "")
            + (f' · CSV 에 값이 안 실려 오는 컬럼 {len(j["no_csv"])}개'
               if j["no_csv"] else "") + '</p>')


def six_rows(fabs, cfg, warn, danger, crit) -> str:
    """관제 화면의 여섯 시스템(ALL + FAB 5)이 각각 무엇을 잰 값인가.

    ★이 표가 없으면 ALL 60점과 FAB 60점을 같은 뜻으로 읽는다.
      둘 다 0~100 이고 등급 컷도 같지만, 잰 대상이 다르다.
    """
    body = (
        '<tr><td class="area">ALL</td>'
        '<td>8개 영역 융합 <span class="th">(영역합 + 흐름 + SLA + Sorter '
        '+ MAXCAPA)</span></td>'
        f'<td class="n">raw &divide; {F.RAW_FULL} &times; 100</td>'
        '<td class="n">0~100</td>'
        f'<td><b>실제로 경보가 나는 값</b> — {warn}점부터 사건이 열립니다</td>'
        '<td class="n"><span class="none">없음</span></td></tr>')
    for f in fabs:
        mx = F.max_area(f, cfg)
        so = F.solo_ceiling(f, cfg, "typical")
        body += (
            f'<tr><td class="area">{e(f)}</td>'
            f'<td>그 영역의 9개 룰 <span class="th">(임계와 대조해 켜짐/꺼짐)'
            f'</span></td>'
            f'<td class="n">영역점수 &times; 2</td>'
            f'<td class="n">0~{mx["risk_max"]}</td>'
            f'<td>그 FAB <b>자체</b> 등급 — 전체 경보와는 별개</td>'
            f'<td class="n">{so["score"]}점</td></tr>')
    return (f'<div class="tw"><table><thead><tr>'
            f'<th>시스템</th><th>무엇을 보나</th><th class="n">어떻게 점수가 되나</th>'
            f'<th class="n">나올 수 있는 범위</th><th>이 점수의 뜻</th>'
            f'<th class="n">단독 상한</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def all_block(cfg) -> str:
    """ALL 만 가진 것 — 융합 5개 항, 룰별 걸린 영역 수. 실측 한 줄로 보여준다."""
    import csv as _csv
    path = os.path.join(BASE_DIR, "fixtures", "발동이벤트_샘플.csv")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8-sig") as fh:
        rs = list(_csv.DictReader(fh))
    r = rs[0]
    a = F.all_row(r, cfg)
    fu = a["fuse"]

    parts = [("영역점수합", fu["areas"], "8개 영역 점수 × 가중치"),
             ("흐름", fu["flow"], "10개 흐름 노드가 30분 평균의 몇 배인가"),
             ("SLA", fu["sla"], "SLA 가 걸린 영역 수 × 5"),
             ("Sorter", fu["sorter"], "소터가 걸린 영역 수 × 3"),
             ("MAXCAPA", fu["maxcapa"], "상한이 내려간 컬럼 수 × 10 × 영역수")]
    prow = "".join(f'<div class="calc-row"><div class="lbl">{e(n)}</div>'
                   f'<div class="exp th">{e(d)}</div>'
                   f'<div class="val">{v:g}</div></div>' for n, v, d in parts)

    rr = "".join(
        f'<tr><td class="rule">{e(_rname(c))}<span class="rdesc">'
        f'{e(F.RULE_BY_CODE[c]["label"])}</span></td>'
        f'<td class="n">{F.RULE_BY_CODE[c]["pts"]}</td>'
        f'<td class="n"><b>{a["per_rule"][c]}</b> / {len(F.fabs(cfg))}</td>'
        f'<td class="th">{"·".join(f for f in F.fabs(cfg) if (F._num(r.get(f"{f}_pts_{c}")) or 0) > 0) or "—"}</td>'
        f'</tr>' for c in F.RULE_ORDER)

    return (
        f'<div class="calc"><div style="font-size:12.5px;color:var(--muted);'
        f'margin-bottom:10px">실측 한 줄 — <span class="mono">'
        f'{e(r.get("datetime"))}</span></div>{prow}'
        f'<div class="calc-total"><div class="lbl">raw 합계</div>'
        f'<div class="exp mono">min(100, round({fu["raw"]:g} &times; 100 '
        f'&divide; {F.RAW_FULL}))</div>'
        f'<div class="val">{fu["calc"]}</div></div></div>'
        f'<h3 class="sub-h">룰마다 몇 개 영역에서 켜졌나</h3>'
        f'<p class="subtitle">ALL 점수가 왜 그 숫자인지는 여기서 읽힙니다. '
        f'한 영역에서 아홉 룰이 다 켜지는 것보다, 여러 영역에서 한두 룰씩 '
        f'켜지는 쪽이 점수를 더 올립니다.</p>'
        f'<div class="tw"><table class="grid"><thead><tr><th>룰</th>'
        f'<th class="n">배점</th><th class="n">걸린 영역</th>'
        f'<th>어디에서</th></tr></thead><tbody>{rr}</tbody></table></div>'
        f'<p class="pipe-note" style="margin-top:10px">이 한 줄에서 '
        f'영역 {a["areas_hit"]}/{a["areas_total"]} 곳이 걸렸고, 최고구역은 '
        f'<span class="mono">{e(a["hot_area"])}</span>, '
        f'단계는 {e(a["stage_name"]) or "—"} 입니다.</p>')


def solo_table(fabs, cfg, warn: int) -> str:
    """단독 상한 — 이 문서에서 가장 중요한 표. 두 시나리오를 같이 보여 준다."""
    rows = []
    for f in fabs:
        t = F.solo_ceiling(f, cfg, "typical")
        m = F.solo_ceiling(f, cfg, "max")
        if m["score"] < warn:
            pill = '<span class="pill p3">최대로도 못 감</span>'
        elif t["score"] < warn:
            pill = '<span class="pill p1">최대 조건에서만</span>'
        else:
            pill = '<span class="pill p0">도달</span>'
        p = t["parts"]
        rows.append(
            f'<tr><td class="area">{e(f)}</td>'
            f'<td class="n">{t["weight"]:g}</td>'
            f'<td class="n">{t["flow_nodes"]}</td>'
            f'<td class="n">{t["maxcapa_cols"]}</td>'
            f'<td class="n th">{p["영역점수"]:g} + {p["흐름"]:g} + {p["SLA"]:g}'
            f' + {p["Sorter"]:g} + {p["MAXCAPA"]:g} = {t["raw"]:g}</td>'
            f'<td class="n"><b>{t["score"]}</b></td>'
            f'<td class="n">{m["score"]}</td>'
            f'<td>{pill}</td></tr>')
    return (f'<div class="tw"><table><thead><tr>'
            f'<th>FAB</th><th class="n">가중치</th><th class="n">흐름 노드</th>'
            f'<th class="n">MAXCAPA 컬럼</th><th class="n">통상 raw 내역</th>'
            f'<th class="n">통상 상한</th><th class="n">최대 상한</th>'
            f'<th>경계 {warn}점</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def scale_table(cfg, warn, danger, crit) -> str:
    """영역점수 → 위험도 → 등급 환산표."""
    from sentinel import grade
    rows = []
    prev = None
    for a in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50):
        r = F.risk(a)
        g = grade(r, cfg)
        cls = {"경계": "p1", "위험": "p2", "초위험": "p3"}.get(g["level"], "p0")
        # 등급이 바뀌는 줄에 선을 긋는다 — 컷이 어디인지 눈으로 찾게
        edge = (' style="border-top:2px solid var(--g1)"'
                if prev is not None and g["level"] != prev else "")
        mark = (f' <span class="th">← 컷 {r}</span>'
                if prev is not None and g["level"] != prev else "")
        prev = g["level"]
        rows.append(f'<tr{edge}><td class="n">{a}</td><td class="n"><b>{r}</b>{mark}</td>'
                    f'<td><span class="pill {cls}">{e(g["emoji"])} {e(g["level"])}</span></td>'
                    f'<td class="th">{e(_what(a))}</td></tr>')
    return (f'<div class="tw"><table><thead><tr>'
            f'<th class="n">영역점수 (0~{F.AREA_CAP} · 상한)</th>'
            f'<th class="n">위험도 (0~100)</th><th>FAB 자체 등급</th>'
            f'<th>대략 이런 상태</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def _what(a: int) -> str:
    return {0: "켜진 룰 없음", 5: "R-A′ 하나", 10: "R-A 하나 또는 R-A′+SORT",
            15: "R-A + R-A′", 20: "R-A + R-A′ + 소터·SLA",
            25: "R-A + R-C + R-D", 30: "R-A + R-A′ + R-C + R-D",
            35: "여기에 SLA 까지", 40: "R-B 계열까지 합류",
            45: "여덟 룰 언저리", 50: "상한 — 더 나빠져도 50"}.get(a, "")


def fab_cards(fabs, cfg) -> str:
    """FAB 하나씩 — 자기가 보는 컬럼 전부."""
    out = []
    for f in fabs:
        w = F.watch(f, cfg)
        c = F.solo_ceiling(f, cfg, "typical")
        n_cols = sum(len(v) for v in w.values())
        n_csv = sum(1 for v in w.values() for it in v if it.get("csv"))
        rows = []
        for r in F.RULES:
            items = w.get(r["code"]) or []
            if not items:
                rows.append(f'<tr class="off"><td class="rule">{e(_rname(r["code"]))}</td>'
                            f'<td colspan="3" class="th">이 FAB 에는 이 룰이 없습니다 '
                            f'— 배점 {r["pts"]}점을 받을 길이 없다는 뜻입니다</td></tr>')
                continue
            for i, it in enumerate(items):
                rule_td = (f'<td class="rule" rowspan="{len(items)}">{e(_rname(r["code"]))}'
                           f'<span class="rdesc">{r["pts"]}점</span></td>' if i == 0 else "")
                thr = it.get("thr")
                op = it.get("op") or ">="
                sign = {"<=": "≤", "diff10": "10분 +", ">=": "≥"}.get(op, "≥")
                thr_s = ('<span class="undef">임계 미정의</span>' if thr is None
                         else f'{sign} {fmt(thr)}{e(it.get("unit") or "")}')
                csv = it.get("csv") or ""
                csv_s = (f'<span class="mono">{e(csv)}</span>' if csv
                         else '<span class="nocsv">CSV 에 값 없음</span>')
                rows.append(f'<tr>{rule_td}<td class="col"><span class="amos">'
                            f'{e(it["amos"])}</span><br><span class="th">'
                            f'{e(it["label"])}</span></td>'
                            f'<td class="n">{thr_s}</td><td class="n">{csv_s}</td></tr>')
        out.append(
            f'<section class="card"><div class="cardhead">'
            f'<h3 class="mono">{e(f)}</h3>'
            f'<p class="cardmeta">감시 컬럼 {n_cols}개 (CSV 에 값이 실려오는 것 {n_csv}개) · '
            f'가중치 {c["weight"]:g} · 흐름 노드 {c["flow_nodes"]}개 · '
            f'단독 전체점수 상한 <b>{c["score"]}점</b> (통상)</p></div>'
            f'<div class="tw"><table class="fabtbl"><thead><tr><th>룰</th>'
            f'<th>실제 지표 컬럼</th><th class="n">임계값</th>'
            f'<th class="n">CSV 컬럼</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    return "".join(out)


def verify_block(cfg) -> str:
    """fixture 실물 형식 한 줄을 그대로 재계산해 보여 준다.

    맞는 줄만 골라 싣지 않는다 — 안 맞는 줄이 있으면 그것도 적는다.
    """
    import csv as _csv
    path = os.path.join(BASE_DIR, "fixtures", "발동이벤트_샘플.csv")
    if not os.path.isfile(path):
        return '<p class="subtitle">검증용 샘플 파일이 없습니다.</p>'
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(_csv.DictReader(fh))
    fabs = F.fabs(cfg)
    out, mism = [], []
    ok = 0
    for r in rows:
        fc = F.fuse_check(r, cfg)
        ok += bool(fc["match"])
        for f in fabs:
            a = F.area_score(r, f, cfg)
            if a["mismatch"]:
                mism.append((str(r.get("datetime") or ""), a["mismatch"]))
        per = " · ".join(f'{f} {F.area_score(r, f, cfg)["area"]:g}' for f in fabs)
        tag = ('<span class="pill p0" style="color:var(--ok);border-color:var(--ok);'
               'background:var(--okbg)">일치</span>' if fc["match"]
               else '<span class="pill p2">불일치</span>')
        out.append(f'<tr><td class="mono">{e(r.get("datetime"))}</td>'
                   f'<td class="th">{e(per)}</td>'
                   f'<td class="n">{fc["areas"]:g}</td><td class="n">{fc["flow"]:g}</td>'
                   f'<td class="n">{fc["sla"]:g}</td><td class="n">{fc["sorter"]:g}</td>'
                   f'<td class="n">{fc["maxcapa"]:g}</td><td class="n">{fc["raw"]:g}</td>'
                   f'<td class="n"><b>{fc["calc"]}</b></td>'
                   f'<td class="n">{fmt(fc["stored"])}</td><td>{tag}</td></tr>')
    return (f'<div class="tw"><table><thead><tr><th>시각</th><th>영역점수</th>'
            f'<th class="n">영역합</th><th class="n">흐름</th><th class="n">SLA</th>'
            f'<th class="n">소터</th><th class="n">MC</th><th class="n">raw</th>'
            f'<th class="n">재현</th><th class="n">저장값</th><th>판정</th>'
            f'</tr></thead><tbody>{"".join(out)}</tbody></table></div>'
            f'<p class="pipe-note" style="margin-top:10px">{len(rows)}행 중 {ok}행이 '
            f'정확히 재현됐습니다. 나머지는 시험용으로 손댄 행이라 내부 값끼리 '
            f'맞지 않습니다 — 재현이 안 되는 것이 아니라 그 행이 실제 관측이 '
            f'아니라는 뜻입니다.</p>'
            + (('<div class="note warn"><h4>영역점수가 상한을 넘긴 행이 있습니다 — '
                '현장 확인이 필요합니다</h4><p>'
                + "<br>".join(f'<span class="mono">{e(t)}</span> · {e(m)}'
                              for t, m in mism)
                + f'</p><p>저장된 <span class="mono">{{FAB}}_score</span> 가 '
                  f'상한 {F.AREA_CAP} 보다 큽니다. 샘플을 손으로 만들면서 생긴 값일 '
                  f'수도 있고, 예측기가 <b>{{FAB}}_score 에는 상한을 적용하지 않는</b> '
                  f'것일 수도 있습니다. 둘은 전혀 다른 이야기라 추측으로 넘기지 '
                  f'않았습니다. 실데이터에서 <span class="mono">{{FAB}}_score &gt; '
                  f'{F.AREA_CAP}</span> 인 행이 나오는지 확인해 주십시오 — 나온다면 '
                  f'상한은 융합 단계에서만 걸리는 것이고, '
                  f'<code class="mono">fab_score.AREA_CAP</code> 적용 위치를 '
                  f'고쳐야 합니다.</p></div>') if mism else ""))


# ────────────────────────────── 문서 ──────────────────────────────
EXTRA_CSS = """
/* FAB 비교 문서에서 추가로 쓰는 것만 */
.grid th,.grid td{vertical-align:top}
.grid td.rule{background:var(--surface2);border-right:1px solid var(--line2);white-space:nowrap}
.grid tbody td.n{font-family:ui-monospace,"SF Mono",Consolas,monospace;font-size:12.5px;line-height:1.5}
.grid.cols td{font-size:11.5px}
.rdesc{display:block;margin-top:4px;font-size:11.5px;font-weight:400;color:var(--muted);line-height:1.45}
.none{color:var(--faint)}
.undef{color:var(--g2);font-weight:700}
.nocsv{color:var(--faint);font-style:italic;font-size:11.5px}
.amos{font-family:ui-monospace,"SF Mono",Consolas,monospace;font-size:11.5px;
      color:var(--ink);word-break:break-all}
.th{color:var(--faint);font-weight:400;font-size:11.5px}
.colstack+.colstack{margin-top:7px;padding-top:7px;border-top:1px dashed var(--line)}
.card{margin:0 0 28px}
.cardhead{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin:0 0 10px}
.cardhead h3{margin:0;font-size:19px;color:var(--accent);letter-spacing:-.01em}
.cardmeta{margin:0;font-size:12.5px;color:var(--muted)}
.fabtbl td.rule{background:var(--surface2);border-right:1px solid var(--line2);white-space:nowrap}
.fabtbl tr.off td{color:var(--faint);background:var(--surface2)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:860px){.two{grid-template-columns:1fr}}
/* ALL 칸은 배경을 달리 둔다 — 영역이 아니라는 걸 표에서 바로 보이게 */
.grid td.allcol{background:var(--accent-soft);border-right:1px solid var(--accent-line)}
.grid tr.allonly td{background:var(--surface2)}
.grid tr.allonly td.allcol{background:var(--accent-soft)}
tr.off td{color:var(--faint)}
tr.miss td{background:var(--g2bg)}
"""


def build(cfg=None) -> str:
    from lp_client import load_config
    from sentinel import grade_cuts
    cfg = cfg or load_config()
    fabs = F.fabs(cfg)
    warn, danger, crit = grade_cuts(cfg)

    with open(os.path.join(DOC_DIR, "style.css"), encoding="utf-8") as fh:
        css = fh.read()

    # '통상' 시나리오에서 경계에 못 가는 FAB / '최대' 로도 못 가는 FAB
    blind = [f for f in fabs if F.solo_ceiling(f, cfg, "typical")["score"] < warn]
    hard_blind = [f for f in fabs if F.solo_ceiling(f, cfg, "max")["score"] < warn]
    worst = max(fabs, key=lambda f: F.solo_ceiling(f, cfg, "typical")["score"])
    best_hidden = min(fabs, key=lambda f: F.solo_ceiling(f, cfg, "typical")["score"])
    bh = F.solo_ceiling(best_hidden, cfg, "typical")
    wc = F.solo_ceiling(worst, cfg, "typical")
    hub = F.solo_ceiling("M16HUB", cfg, "typical")

    # 룰이 아예 없는 칸 — 다섯 FAB 을 **전부** 싣는다. 빠진 곳만 실으면
    # 표가 목록이 되고, 비교가 안 된다. 온전한 FAB 도 '—' 로 보여야 한다.
    miss_rows = ""
    for f in fabs:
        w = F.watch(f, cfg)
        gone = [c for c in F.RULE_ORDER if not (w.get(c) or [])]
        undef = sorted({c for c in F.RULE_ORDER
                        for it in (w.get(c) or []) if it.get("thr") is None})
        mx = F.max_area(f, cfg)
        lost = sum(p for _why, p in mx["lost"].values())
        top = ('<span class="pill p0">상한 도달</span>' if mx["capped"]
               else f'<span class="pill p2">{mx["area_max"]}점이 천장</span>')
        miss_rows += (
            f'<tr><td class="area">{e(f)}</td>'
            f'<td>{", ".join(_rname(c) for c in gone) if gone else "<span class=none>—</span>"}</td>'
            f'<td>{", ".join(_rname(c) for c in undef) if undef else "<span class=none>—</span>"}</td>'
            f'<td class="n">{lost if lost else "<span class=none>0</span>"}</td>'
            f'<td class="n">{mx["possible"]}</td>'
            f'<td class="n"><b>{mx["area_max"]}</b> / {F.AREA_CAP}</td>'
            f'<td class="n">{mx["risk_max"]}</td><td>{top}</td></tr>')

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FAB별 위험도 스코어 — 나란히 놓고 보기</title>
<style>
{css}
{EXTRA_CSS}
</style>
</head>
<body>

<header>
  <div class="hin">
    <p class="eyebrow">M16 ↔ M14 Bridge · FAB 비교</p>
    <h1>FAB 별로는 어떻게 다른가</h1>
    <p class="lede">
      기존 <b>스코어 산출</b> 문서는 전체 점수 하나가 만들어지는 과정을 폈습니다.
      이 문서는 같은 재료를 <b>FAB 다섯 개로 갈라 나란히</b> 놓습니다 —
      어느 FAB 이 어떤 컬럼을 보고, 임계가 얼마나 다르고,
      그래서 <b>혼자서는 몇 점까지밖에 못 가는지</b>.
      숫자는 전부 <code class="mono">fab_score.py</code> 에서 뽑아 생성했습니다.
    </p>
    <div class="formula-strip mono">
      <b>ALL</b> = min(100, round(raw &times; 100 &divide; {F.RAW_FULL})) &nbsp;·&nbsp;
      <b>FAB 위험도</b> = 영역점수 &times; 2 &nbsp;·&nbsp;
      <b>영역점수</b> = min({F.AREA_CAP}, &Sigma; 켜진 룰 배점)
    </div>
    <div class="formula-strip mono" style="margin-top:10px;
         background:var(--g1bg);border-color:var(--g1)">
      <b style="color:var(--g1)">등급 컷</b> &nbsp; 경계 <b>{warn}</b> &nbsp;·&nbsp;
      위험 <b>{danger}</b> &nbsp;·&nbsp; 초위험 <b>{crit}</b>
      &nbsp;&nbsp;&nbsp;<span style="color:var(--muted)">
      ★위 식의 {F.AREA_CAP} 은 <b>영역점수 상한</b>이지 등급 컷이 아닙니다.</span>
    </div>
  </div>
</header>

<div class="wrap">

  <div class="note key">
    <h4>이 문서를 만든 이유 한 줄</h4>
    <p>한 FAB 에서 9개 룰이 <b>전부</b> 켜지고 흐름까지 심각해도, 전체 점수는
      <b>{e(best_hidden)} {bh["score"]}점 ~ {e(worst)} {wc["score"]}점</b>에 그칩니다.
      경계 컷 <b>{warn}점</b>에 다섯 FAB 중 <b>하나도 닿지 못합니다.</b>
      즉 <b>전체 점수 화면만 보면 한 FAB 에 국한된 정체는 보이지 않습니다.</b>
      FAB 을 따로 세워 비교해야 하는 이유가 이것입니다.</p>
    <p>이 계산은 남의 말이 아닙니다. 스코어 산출 문서가 <b>예측기를 직접 호출해</b>
      낸 검증표에 "허브 한 곳에 룰 전부 + 흐름 심각 = <b>44점</b>" 이라는 줄이 있고,
      같은 조건을 이 문서의 계산으로 넣으면 <b>{hub["score"]}점</b>이 나옵니다
      (문서는 영역합 48, 여기는 상한 {F.AREA_CAP} — 그 차이만큼입니다).
      서로 다른 경로로 같은 답이 나왔습니다.</p>
    <p>경계 하한은 2026-08 에 50 → <b>{warn}</b> 으로 올라갔습니다.
      경계가 올라간 만큼 <b>단독 FAB 사각지대는 더 넓어졌습니다.</b>
      (컷과 상한을 구분하는 이야기는 바로 아래 절에 따로 적었습니다.)</p>
  </div>

  <!-- 0. ALL 포함 여섯 시스템 -->
  <section>
    <div class="sechead"><span class="step">먼저</span><h2>관제 화면의 여섯 시스템 — 같은 자, 다른 대상</h2></div>
    <p class="subtitle">
      관제 화면은 <b>ALL + FAB 다섯</b> 을 고르게 되어 있습니다. 여섯 줄 모두
      0~100 점이고 등급 컷도 같은 {warn} / {danger} / {crit} 입니다.
      <b>그런데 잰 대상이 다릅니다.</b> 이걸 모르고 나란히 읽으면
      "M16HUB 는 24점인데 왜 ALL 은 19점이냐" 같은 질문에서 막힙니다.
    </p>
    {six_rows(fabs, cfg, warn, danger, crit)}
    <div class="note key">
      <h4>{F.AREA_CAP} 은 등급 컷이 아닙니다 — 영역점수 상한입니다</h4>
      <p>숫자 두 개가 붙어 다녀서 헷갈리기 쉽습니다. 갈라 두겠습니다.</p>
      <p><b>{F.AREA_CAP}</b> — 한 영역에서 아홉 룰이 다 켜지면 합이 63 인데,
        거기서 자르는 <b>상한</b>입니다. 한 곳이 전체를 밀어올리지 못하게
        막는 장치입니다. 등급과 아무 상관이 없습니다.</p>
      <p><b>{warn} / {danger} / {crit}</b> — 경계 · 위험 · 초위험이 시작되는
        <b>등급 컷</b>입니다. 2026-08 에 경계가 50 → <b>{warn}</b> 으로
        올라갔습니다. 기존 스코어 산출 문서의 <span class="mono">50/71/85</span>
        표기는 <b>옛 값</b>이고, 이 문서는 <code class="mono">config.grade</code>
        의 현재 값을 읽어 씁니다.</p>
    </div>
  </section>

  <!-- 0-2. ALL 은 어떻게 만들어지나 -->
  <section>
    <div class="sechead"><span class="step">ALL</span><h2>ALL 은 영역이 아니다 — 그래서 임계도 단독 상한도 없다</h2></div>
    <p class="subtitle">
      뒤이어 나오는 임계값 격자·컬럼 격자에 <b>ALL 칸이 없는 이유</b>입니다.
      ALL 은 자기 컬럼을 보고 룰을 켜는 영역이 아니라, 여덟 영역의 점수에
      네 개 항을 더해 만든 <b>합</b>입니다. 그래서 자기 임계값이 없고,
      '이 시스템만 걸리면 몇 점' 이라는 단독 상한도 없습니다 —
      자기가 전체이기 때문입니다.
    </p>
    <p class="subtitle">대신 ALL 만 가진 것이 있습니다. 융합 다섯 항과,
      <b>룰마다 몇 개 영역에서 켜졌는가</b> 입니다.</p>
    {all_block(cfg)}
  </section>

  <!-- 1. 임계값 격자 -->
  <section>
    <div class="sechead"><span class="step">비교 1</span><h2>같은 룰, 다른 임계값</h2></div>
    <p class="subtitle">
      배점은 다섯 FAB 이 <b>완전히 같습니다</b>(10·5·10·5·8·7·5·3·10×n, 상한 {F.AREA_CAP}).
      다른 것은 임계값뿐입니다 — FAB 마다 평소 수준이 다르니 당연히 달라야 합니다.
      배점이 같기 때문에 <b>영역점수는 그대로 FAB 간 비교가 됩니다.</b>
    </p>
    {grid_thresholds(fabs, cfg)}
    <div class="note">
      <h4>여기서 바로 읽히는 것</h4>
      <p>반송시간 임계가 M16HUB 9.0분 · M16A 3.2분으로 <b>세 배 가까이</b> 벌어집니다.
        허브룸은 원래 오래 걸리는 구간이라 그렇습니다. 그래서 M16A 3.4분과
        M16HUB 3.4분은 전혀 다른 상태이고, <b>원본 값을 나란히 놓고 비교하면 안 됩니다.</b>
        비교해야 하는 것은 값이 아니라 <b>임계를 넘었느냐(=점수)</b> 입니다.</p>
    </div>
  </section>

  <!-- 2. 컬럼 격자 -->
  <section>
    <div class="sechead"><span class="step">비교 2</span><h2>ALL · FAB 별로 실제 보고 있는 컬럼</h2></div>
    <p class="subtitle">
      같은 룰이라도 FAB 마다 다른 컬럼을 봅니다. <b>ALL 칸</b>은 따로 읽으십시오 —
      ALL 은 영역 룰(R-A…R-D)을 직접 보지 않고 <b>영역별로만</b> 봅니다.
      대신 표 아래쪽에 ALL 만 갖는 항(흐름·융합 집계·판정)이 따로 있습니다.
      위가 AMOS 실제 컬럼명,
      아래가 그 값이 실려 오는 발동이벤트 CSV 컬럼입니다.
      <b>CSV 에 값이 없는 컬럼</b>은 관제 화면에 숫자가 안 뜬다는 뜻입니다 —
      룰은 켜지는데 근거 값을 볼 수 없는 구간입니다.
    </p>
    {grid_columns(fabs, cfg)}
    <div class="note warn">
      <h4>반송시간만 QUE.TIME 과 QUE.LOAD 로 갈립니다</h4>
      <p>M16HUB · M14B 는 <span class="mono">QUE.TIME.AVGTOTALTIME1MIN</span>(총 반송시간),
        M14 · M16A · M16B 는 <span class="mono">QUE.LOAD.AVGLOADTIME1MIN</span>(적재시간)입니다.
        같은 'R-A' 이지만 재는 것이 다릅니다. 임계가 다른 이유의 절반이 여기 있습니다.</p>
    </div>
  </section>

  <!-- 2-2. 화면 지표 ⇄ 룰 -->
  <section>
    <div class="sechead"><span class="step">비교 2-2</span><h2>화면이 그리는 지표와, 룰이 실제로 쓰는 컬럼</h2></div>
    <p class="subtitle">
      관제 화면의 추이 그래프 목록은 이미 정해져 있습니다 —
      ALL 은 <code class="mono">config.ui.metric_groups</code>,
      FAB 은 <code class="mono">lp_client._fab_strip()</code> 입니다.
      이 문서는 그 목록을 <b>새로 만들지 않고 그대로 가져와서</b>, 각 지표가
      어느 룰의 어느 임계에 걸리는지를 붙였습니다. 두 곳에 적으면 반드시
      갈라지기 때문입니다.
    </p>
    <p class="subtitle">그러자 <b>화면에 있는데 점수에는 안 쓰이는 지표</b>와,
      반대로 <b>점수는 쓰는데 화면에 없는 컬럼</b>이 드러났습니다.</p>

    <div class="note key">
      <h4>ALL 화면은 점수를 만드는 값을 거의 안 보여 줍니다</h4>
      <p>ALL 화면이 그리는 지표 <b>{F.join_columns("ALL", cfg)["n_screen"]}개</b>
        중, ALL 점수 계산에 실제로 들어가는 것은
        <b>{F.join_columns("ALL", cfg)["n_used"]}개</b>(스코어 자신)뿐입니다.
        나머지는 FAB 별 지표를 참고로 늘어놓은 것입니다.</p>
      <p>정작 ALL 점수를 만드는 네 항 —
        <span class="mono">flow_score</span> ·
        <span class="mono">sla_score_total</span> ·
        <span class="mono">sorter_score_total</span> ·
        <span class="mono">mc_score_total</span> — 은
        <b>ALL 화면 지표 목록에 없습니다.</b> CSV 에는 실려 옵니다.
        "왜 60점인가" 를 화면에서 짚으려면 이 넷이 있어야 합니다.
        <code class="mono">config.ui.metric_groups</code> 에 추가하면 바로 그려집니다.</p>
    </div>

    <h3 class="sub-h">ALL</h3>
    {join_table("ALL", cfg)}
    {"".join(f'<h3 class="sub-h">{e(f)}</h3>' + join_table(f, cfg) for f in fabs)}
  </section>

  <!-- 2-3. 점수 컬럼 이름 -->
  <section>
    <div class="sechead"><span class="step">이름</span><h2>그 FAB 의 점수는 어느 컬럼인가 — area_score</h2></div>
    <p class="subtitle">
      같은 값이 파일에 따라 다른 이름으로 실려 옵니다. 이 시스템은 이미
      <span class="mono">area_score</span> 라는 이름을 쓰고 있고,
      이 문서와 계산도 <b>그 이름을 그대로 따라갑니다.</b>
    </p>
    <div class="tw"><table><thead><tr>
      <th>어디서 온 행</th><th>그 FAB 점수 컬럼</th><th>전체 점수 컬럼</th>
      <th>비고</th></tr></thead><tbody>
      <tr><td>통합 파일 <span class="mono">{{day}}_발동이벤트.csv</span></td>
        <td class="mono">{{FAB}}_score</td>
        <td class="mono">unified_risk_score</td>
        <td class="th">둘 다 그대로 들어 있습니다</td></tr>
      <tr><td>FAB 분리 파일 <span class="mono">fab분리/…_{{FAB}}.csv</span></td>
        <td class="mono"><b>area_score</b></td>
        <td class="mono">unified_risk_score</td>
        <td class="th">전체 점수도 같이 들어 있습니다 — 그 FAB 점수가 아닙니다</td></tr>
      <tr><td>정규화된 행 <span class="th">(jupyter_csv._fab_rows)</span></td>
        <td class="mono">unified_risk_score <span class="th">(= area_score)</span></td>
        <td class="mono">all_score</td>
        <td class="th">받는 즉시 자리를 바꿉니다. 원본은 all_score 로 밀려납니다</td></tr>
    </tbody></table></div>
    <div class="note warn">
      <h4>정규화된 행을 전체 점수로 읽으면 한 FAB 점수를 전체라고 띄우게 됩니다</h4>
      <p>FAB 분리 파일을 받는 순간 <span class="mono">area_score</span> 가
        <span class="mono">unified_risk_score</span> 자리로 옮겨 갑니다
        (안 그러면 M14 화면이 전체 점수로 등급을 매깁니다).
        그래서 그 행에서 전체 점수를 보려면
        <span class="mono">all_score</span> 를 봐야 합니다.
        <code class="mono">fab_score</code> 는
        <span class="mono">all_score</span> 가 있으면 정규화된 행으로 알아보고
        스스로 자리를 바로잡습니다 — 조용히 틀린 숫자를 내지 않습니다.</p>
    </div>
  </section>

  <!-- 3. 비는 칸 -->
  <section>
    <div class="sechead"><span class="step">비교 3</span><h2>어떤 FAB 은 아예 받을 수 없는 점수가 있다</h2></div>
    <p class="subtitle">
      룰 자체가 없는 칸입니다. 그 FAB 은 그 배점을 받을 <b>길이 없습니다</b> —
      상태가 나빠서 0점인 것과 다릅니다.
    </p>
    <div class="tw"><table><thead><tr>
      <th>FAB</th><th>룰이 없는 항목</th><th>임계가 안 적힌 항목</th>
      <th class="n">못 받는 배점</th><th class="n">받을 수 있는 합</th>
      <th class="n">영역점수 천장</th><th class="n">위험도 천장</th>
      <th>상한 {F.AREA_CAP}점</th></tr></thead>
      <tbody>{miss_rows}</tbody></table></div>
    <div class="note key">
      <h4>천장이 낮은 FAB 은 등급도 못 올라갑니다</h4>
      <p>상한 {F.AREA_CAP}점은 다섯 FAB 이 같지만, 룰이 없는 FAB 은 <b>거기까지 갈
        수가 없습니다.</b> M14B 는 R-C·MAXCAPA 가 없고 SLA 임계도 안 적혀 있어
        받을 수 있는 합이 {F.max_area("M14B", cfg)["possible"]}점입니다 —
        위험도로 {F.max_area("M14B", cfg)["risk_max"]}점, 즉
        <b>초위험({crit}점) 등급에 영원히 못 갑니다.</b>
        FAB 을 나란히 놓고 등급을 비교할 때 반드시 같이 봐야 하는 숫자입니다.</p>
    </div>
    <div class="note warn">
      <h4>M14B 의 SLA 는 컬럼은 있는데 임계가 없습니다</h4>
      <p><span class="mono">sla_M14B</span> 는 CSV 에 실려 옵니다. 그런데 스코어 산출
        문서의 SLA 표에는 M14B 행이 없습니다. 값을 지어내지 않고 <b>임계 미정의</b>로
        두었습니다. <code class="mono">thresholds.json</code> 을 확인해
        <code class="mono">config.json</code> 의
        <span class="mono">fab_score.thresholds.M14B.SLA</span> 에 넣으면
        이 문서와 관제 화면이 함께 갱신됩니다.</p>
    </div>
  </section>

  <!-- 4. 단독 상한 -->
  <section>
    <div class="sechead"><span class="step">비교 4</span><h2>이 FAB 하나만 걸리면 전체 몇 점까지 가나</h2></div>
    <p class="subtitle">
      영역점수는 {F.AREA_CAP}에서 잘리고, 융합에서 raw {F.RAW_FULL} 을 100점으로 놓습니다.
      그래서 한 FAB 이 최대로 나빠져도 전체 점수는 아래 값을 넘지 못합니다.
    </p>
    {solo_table(fabs, cfg, warn)}
    <p class="pipe-note" style="margin-top:10px">
      두 시나리오를 같이 놓았습니다. <b>통상</b> — 영역점수 상한 {F.AREA_CAP} 도달 ·
      흐름 노드 1개 심각(30점) · MAXCAPA 1컬럼 하락.
      <b>최대</b> — 그 FAB 의 흐름 노드가 전부 심각하고 MAXCAPA 컬럼도 전부 내려간,
      현실에서 거의 안 나오는 상한. 둘 다 SLA·Sorter·MAXCAPA 융합 재가산을 포함하고
      나머지 일곱 영역은 0 으로 두었습니다.
    </p>
    <div class="note key">
      <h4>통상 조건에서 경계에 못 가는 FAB — <b>{", ".join(blind) if blind else "없음"}</b></h4>
      <p>다섯 FAB <b>전부</b>입니다. 한 곳이 크게 망가지는 흔한 모습으로는
        전체 점수 화면에 등급조차 뜨지 않습니다.</p>
      <p>최대 조건까지 끌어올려도 못 가는 곳은
        <b>{", ".join(hard_blind) if hard_blind else "없음"}</b> 입니다.
        {"M16B 는 가중치가 0.5 라 영역점수 " + str(F.AREA_CAP) + " 이 합산에 " + str(F.AREA_CAP // 2) + " 로만 들어갑니다 — 흐름 노드도 1개뿐이라 어떤 조건에서도 " + str(F.solo_ceiling("M16B", cfg, "max")["score"]) + "점이 천장입니다." if "M16B" in hard_blind else ""}</p>
      <p><b>이들의 정체는 FAB 화면에서만 보입니다.</b> 그래서 관제 화면은
        전체 점수와 FAB 위험도를 <b>같이</b> 띄워야 합니다.</p>
    </div>
  </section>

  <!-- 5. 눈금 -->
  <section>
    <div class="sechead"><span class="step">비교 5</span><h2>눈금 맞추기 — 영역점수 0~50 을 100점으로</h2></div>
    <p class="subtitle">
      영역점수는 0~{F.AREA_CAP} 이고 전체 점수는 0~100 입니다. 눈금이 달라 나란히 못 놓습니다.
      그래서 영역점수에 2를 곱해 <b>위험도</b>로 폈습니다. 값을 바꾸는 게 아니라
      자를 바꾸는 것이라, FAB 간 순위는 그대로입니다.
    </p>
    {scale_table(cfg, warn, danger, crit)}
    <div class="note key">
      <h4>이 등급은 그 FAB 자체 등급입니다 — 전체 등급과 같은 뜻이 아닙니다</h4>
      <p>FAB 위험도가 <b>초위험</b>인데 전체 점수는 <b>등급 없음</b>일 수 있습니다.
        모순이 아니라 위 '비교 4' 에서 본 구조 그대로입니다.
        화면에서도 두 숫자를 반드시 같이 띄우고, 어느 쪽 자로 잰 값인지 적어야 합니다.</p>
    </div>
  </section>

  <!-- 6. 왜 평소 대비로는 비교가 안 되나 -->
  <section>
    <div class="sechead"><span class="step">비교 6</span><h2>왜 '평소 대비 얼마나 튀었나' 로는 비교가 안 되나</h2></div>
    <p class="subtitle">
      관제 화면의 <b>기여도 추정</b>(<code class="mono">contrib.py</code>)은 그 FAB 의
      조용한 구간을 기준선으로 잡고 거기서 몇 배 벗어났는지를 잽니다.
      한 FAB 안에서 '무엇이 이 점수를 올렸나' 를 볼 때는 맞는 방법입니다.
      그런데 FAB 끼리 비교할 때 쓰면 정반대로 갑니다.
    </p>
    <div class="two">
      <div class="prop"><div class="tag">상대 편차 (쓰면 안 됨)</div>
        <h4>늘 나쁜 FAB 이 '정상'으로 보인다</h4>
        <p>아침부터 저녁까지 반송시간이 높은 FAB 은 <b>기준선도 같이 높습니다.</b>
          그래서 '평소와 같음' 이 되어 편차가 0 에 가깝습니다.
          반대로 평소가 아주 조용한 FAB 은 조금만 올라도 크게 튀어 보입니다.
          <b>순위가 뒤집힙니다.</b></p></div>
      <div class="prop"><div class="tag">절대 임계 (이 문서가 쓰는 것)</div>
        <h4>임계를 넘었느냐만 본다</h4>
        <p>배점이 다섯 FAB 에서 같으므로, 영역점수 25점은 어느 FAB 에서든
          <b>같은 무게의 25점</b>입니다. 기준선을 안 쓰니 늘 나쁜 FAB 도
          늘 나쁘게 나옵니다. 그래서 <code class="mono">fab_score.py</code> 는
          통계적 편차를 한 번도 쓰지 않습니다.</p></div>
    </div>
  </section>

  <!-- 7. FAB 카드 -->
  <section>
    <div class="sechead"><span class="step">FAB 별</span><h2>FAB 하나씩 — 보고 있는 컬럼 전부</h2></div>
    <p class="subtitle">
      위 격자를 FAB 기준으로 다시 편 것입니다. 관제 담당이 자기 FAB 한 장만
      떼어 볼 수 있게 나눴습니다.
    </p>
    {fab_cards(fabs, cfg)}
  </section>

  <!-- 8. 검증 -->
  <section>
    <div class="sechead"><span class="step">검증</span><h2>문서의 숫자가 실제 데이터와 맞는가</h2></div>
    <p class="subtitle">
      143컬럼 실물 형식 샘플의 각 행에서, <span class="mono">{{FAB}}_pts_*</span> 를
      더해 영역점수를 만들고 융합 공식으로 전체 점수를 다시 계산했습니다.
      저장된 <span class="mono">unified_risk_score</span> 와 비교합니다.
    </p>
    {verify_block(cfg)}
    <div class="note">
      <h4>이 숫자들은 추정이 아니라 재현입니다</h4>
      <p>기여도 추정(<code class="mono">contrib.py</code>)은 점수식을 모른 채 낸 값이라
        화면에도 '추정'이라고 씁니다. 여기는 다릅니다 — 예측기가 룰별 배점을
        <span class="mono">{{FAB}}_pts_*</span> 컬럼으로 그대로 떨궈 주기 때문에,
        더하기만 하면 영역점수가 나옵니다. 저장값과 어긋나면
        <code class="mono">fab_score.area_score()</code> 가
        <span class="mono">mismatch</span> 로 알립니다 — 조용히 한쪽을 고르지 않습니다.</p>
    </div>
  </section>

  <footer>
    <p>출처 — 임계값·배점·컬럼명은 <b>스코어 산출</b> 문서
      (<code class="mono">hubroom_predictor.py</code> 의
      <code class="mono">eval_area_rules</code> ·
      <code class="mono">evaluate_unified</code>,
      <code class="mono">thresholds.json</code>) 에서 옮겼습니다.
      등급 컷은 <code class="mono">config.grade</code> 의 현재 값
      ({warn} / {danger} / {crit}) 입니다.</p>
    <p>이 문서는 <code class="mono">python fab_score_doc.py</code> 로 다시 만듭니다.
      임계가 바뀌면 <code class="mono">config.json</code> 의
      <span class="mono">fab_score.thresholds</span> 만 고치고 다시 생성하십시오 —
      문서와 관제 화면이 같이 갱신됩니다.</p>
  </footer>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    import sys
    os.makedirs(DOC_DIR, exist_ok=True)
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    html_text = build()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    print(f"✅ {out}  ({len(html_text):,} bytes)")
