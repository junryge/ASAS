# -*- coding: utf-8 -*-
"""OHT_Bridge_Monitor.html — 판마다 그 FAB 의 실제 아이소메트리 + **✎ 수정 모드**.

    python MAP_아이소_얹기.py            ← 보통은 이것만
    python MAP_아이소_얹기.py --reset    ← 화면에서 저장한 설정을 버리고 아래 표대로 새로

  ★인자 없이 돌리면 **OHT_Bridge_Monitor.html 자체**를 만든다 (더블클릭으로 연다).
    고객 원본은 처음 한 번 OHT_Bridge_Monitor_원본.html 로 떠 두고, 늘 그 원본에서 만든다.
  ★있는 것만 얹는다 — 캐시(또는 layout.zip)가 없는 FAB 은 건너뛴다.

2026-09-21. 고객:
  "M14A 저 건축물 위에 M14A 아이소메트리 올려줘" · "사각형에 꽉차게 해야지" ·
  "M14LFT, M14CNV 표시하는 패널은 삭제해주고" · "M16LFT2F 패널삭제" · "M16LFT 패널삭제" ·
  "M16EUV → M16A 패널명 변경, 색상도 빨간색으로" · "M166F → M16B 로 변경" ·
  "M14B 패널 아래로 그리고 앞으로" · "동간 브릿지 통합 반송 현황 말고 FAB별 실시간 상황표" ·
  "ISOMETRIC VIEW 범례 삭제" · "오른쪽 열 삭제 — 나중에 따로 여기서 메세지 만들꺼야" ·
  "수정하기 버튼 만들어줘 — 패널, 맵 수정 가능하게, 맵 추가도 가능하게" ·
  "OHT_Bridge_Monitor.html 색상변경가능하게 해주라. 바탕화면" ·
  "현재 마우스로 움직이는 왼쪽으로 하는 부분은 ctrl 누르면 변경되게 해주라" ·
  "패널 M16HUBOHT 라고 있는데 M16HUBROOM 이라고 표기 변경해주라" ·
  "배경색상이 어두워서 기존에 다크,화이트,네이비,고대비 적용 가능하게 해주라".

어떻게 되어 있나
────────────────────────────────────────────────────────────────────
  이 스크립트는 **틀(고객 원본)을 거의 안 건드린다**. 하는 일은 셋뿐이다:

  ① 틀에 이름표를 단다 — data-bm-plate(판) · data-bm-card / data-bm-name(패널) ·
     data-bm-area(오른쪽 열·KPI·범례·안내·단추 줄) · data-bm-text(제목) ·
     data-bm-bg(바탕·무대·격자·빛 — 색을 바꿀 자리).
     패널 transform 에는 translate3d(var(--bmx),var(--bmy),var(--bmz)) 를 끼워
     둔다 — 틀이 드래그·줌마다 transform 을 다시 써도 위치가 안 풀린다.
  ② 설정 JSON(<script id="bm-config">)을 만든다 — 판마다 맵(레일·설비 좌표),
     패널 바꿈, 구역 숨김, 제목. 기본값은 아래 표들이다.
  ③ bridge_editor.js 를 <head> 에 넣는다 — 설정대로 화면을 꾸미고, '✎ 수정'
     창에서 고친 것을 **설정 JSON 한 장**(OHT_Bridge_Monitor_설정.json)으로 저장한다
     (고객: "HTML 을 그대로 저장하냐 — JSON 만들면 되지"). 그 브라우저에도 남아
     다음에 열면 이대로 뜨고, 다른 PC 에서는 '불러오기' 로 그 JSON 을 고른다.

  옆에 설정 JSON 이 있으면 그걸 HTML 기본값으로 굳힌다 — 어느 PC 에서 열어도 그대로.
  맵 좌표·패널·구역 모두 화면이 고친 대로다. 표대로 새로 하려면 --reset.

도면_얹기.py 에서 배운 것 — 그대로 지킨다
────────────────────────────────────────────────────────────────────
  ⓑ 템플릿 JSON 을 되돌릴 때 "</" 는 <\\u002F 로 적는다. 설정 JSON 도 "</" 는 <\\/ 로.
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import math
import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "OHT_MAP", "cache")
MONITOR = os.path.join(BASE, "OHT_Bridge_Monitor.html")         # 더블클릭해서 보는 것
ORIG = os.path.join(BASE, "OHT_Bridge_Monitor_원본.html")        # 고객이 만든 그대로
EDITOR_JS = os.path.join(BASE, "bridge_editor.js")

# ── 판 — ★층 ↔ FAB 짝이 다르면 **이 표만** 고치면 된다 (화면 '✎ 수정' 에서도 바꾼다) ──
#   find : 그 판을 찾을 표식 (고객 마크업의 left/top/width/height 그대로)
#   fab/prefix 가 없으면 맵 없이 둔다 (M16 HUB)
PLATES = [
    dict(key="m14b", tag="7F · M14B", fab="M14B", prefix="A", col="#3ad6c8",
         find="left:30px;top:20px;width:300px;height:210px"),
    dict(key="m14a", tag="3F · M14A", fab="M14A", prefix="A", col="#3ad6c8",
         find="left:30px;top:420px;width:300px;height:210px"),
    dict(key="m16hub", tag="M16 HUB", fab=None, prefix=None, col="#8fd3ff",
         find="left:360px;top:250px;width:340px;height:300px"),
    dict(key="m16a", tag="6F · M16", fab="M16A", prefix="A", col="#ffce7a",
         find="left:690px;top:20px;width:290px;height:220px"),
    dict(key="m16b", tag="2F · M16", fab="M16B", prefix="B", col="#ff8f8f",
         find="left:690px;top:530px;width:290px;height:210px"),
]

# ── 패널 — 기본값 (화면 '✎ 수정 → 패널' 에서 고친다) ────────────────────
#   hide · name · tone(teal/blue/amber/red) · dx/dy/dz(px: 판 위 좌우·앞뒤·높이)
CARDS = {
    "M14LFT":   dict(hide=True),                  # "M14LFT, M14CNV 표시하는 패널은 삭제해주고"
    "M14CNV":   dict(hide=True),
    "M16LFT2F": dict(hide=True),                  # "M16LFT2F 패널삭제"
    "M16LFT":   dict(hide=True),                  # "M16LFT 패널삭제"
    "M16EUV":   dict(name="M16A", tone="red"),    # "M16EUV → M16A, 빨간색으로"
    "M166F":    dict(name="M16B"),                # "M166F → M16B 로 변경"
    "M16HUBOHT": dict(name="M16HUBROOM"),         # "M16HUBOHT → M16HUBROOM 으로 표기 변경"
    "M14B":     dict(dx=-320, dy=420, dz=-150),   # "M14B 패널 아래로 그리고 앞으로" — 보는 쪽(판 왼쪽 앞) 밖으로 빼서 레일과 안 겹친다
}
AREAS = {"aside": dict(hide=True),                # "오른쪽 열 — 방해된다"
         "legend": dict(hide=True),               # "ISOMETRIC VIEW 범례 삭제"
         "kpi": dict(hide=True)}                  # "IN TRANSIT · CAPACITY · ALARM · LOCAL 삭제 — 필요없어"
TEXTS = {"title": "FAB별 실시간 상황표",           # "동간 브릿지 통합 반송 현황 말고"
         "hint": "DRAG TO ORBIT · CTRL+DRAG TO MOVE · SCROLL TO ZOOM"}    # Ctrl + 왼쪽 끌기 = 이동

# ── 틀에서 이름표 달 자리 (고객 마크업 그대로의 앞머리) ──────────────────
AREA_FIND = {
    "aside":   '<aside style="flex:1 1 240px',
    "kpi":     '<div style="display:flex;gap:9px;flex-wrap:wrap">',
    "legend":  '<div style="position:absolute;left:18px;bottom:34px;',
    "hint":    '<div style="position:absolute;left:18px;bottom:12px;',
    "toolbar": '<div style="position:absolute;right:16px;top:12px;',
}
TEXT_FIND = {
    "subtitle": ">AMHS · INTER-BUILDING BRIDGE</div>",
    "title":    ">동간 브릿지 통합 반송 현황</div>",
    "hint":     ">DRAG TO ORBIT · 360° / SCROLL TO ZOOM</div>",
}
# 바탕화면 — 색 바꿀 자리 ("바탕화면 색상변경가능하게 해주라")
#   틀이 --t 를 style 에 달고 다시 쓰므로 편집기는 인라인이 아니라 스타일시트로 덮는다.
BG_FIND = {
    "page":  '<div style="--t:{{ spd }}',                      # 뿌리 — 화면 전체
    "stage": '<section style="flex:4 1 560px',                 # 무대 판
    "grid":  '<div style="position:absolute;inset:0;background-image:linear-gradient(rgba(58,214,200,.045) 1px',
    "glow":  '<div style="position:absolute;inset:0;background:radial-gradient(60% 50% at 50% 45%',
}
# 무대 — 오른쪽 끌기 이동(translate) 을 틀의 transform 앞에 끼운다
SCENE_FIND = "transform-style:preserve-3d;transform:{{ sceneT }}"
SETTINGS = os.path.join(BASE, "OHT_Bridge_Monitor_설정.json")   # 화면 '저장' 이 쓰는 JSON

# ── 설비 (dashboard.html layout3D 와 같은 값) ───────────────────────
V3D_SCALE = 0.01            # 도면 단위 → m
OFF = 1.7 / V3D_SCALE       # 레일에서 1.7 m
STEP = 1.6 / V3D_SCALE      # 1.6 m 칸마다 하나
Q = 10                      # 설정에 적을 좌표 단위 (도면 10 = 10 cm) — 파일이 작아진다


def cache_for(fab, prefix, cache_dir=CACHE_DIR):
    """캐시 경로. 없으면 서버와 같은 길로 layout.zip 에서 만든다. 못 만들면 None."""
    p = os.path.join(cache_dir, f"{fab}_{prefix}_layout_cache.json")
    if os.path.exists(p) and os.path.getsize(p) > 100:
        return p
    try:
        sys.path.insert(0, BASE)
        import data_loader                                  # noqa: E402
        return data_loader.ensure_layout_cache(fab, prefix)
    except Exception as e:                                  # 캐시도 zip 도 없다
        print(f"  [건너뜀] {fab}/{prefix}: {e}")
        return None


# ── 레이아웃 캐시 → 그릴 재료 ──────────────────────────────────────
def load_cache(path):
    c = json.load(io.open(path, encoding="utf-8"))
    nodes = {int(k): (float(v[0]), float(v[1])) for k, v in c["nodes"].items()}
    und = set()
    for k in c.get("edges", {}):
        a, b = (int(t) for t in k.split(","))
        if a != b and a in nodes and b in nodes:
            und.add((a, b) if a < b else (b, a))
    return nodes, und, c.get("stations") or []


def chains(und):
    """엣지를 이어진 줄로 묶는다 — path 가 10분의 1로 준다."""
    nbr = {}
    for a, b in und:
        nbr.setdefault(a, []).append(b)
        nbr.setdefault(b, []).append(a)
    used, out = set(), []

    def walk(s, n):
        line = [s, n]
        used.add((s, n) if s < n else (n, s))
        prev, cur = s, n
        while len(nbr[cur]) == 2:
            nx = nbr[cur][0] if nbr[cur][1] == prev else nbr[cur][1]
            k = (cur, nx) if cur < nx else (nx, cur)
            if k in used:
                break
            used.add(k)
            line.append(nx)
            prev, cur = cur, nx
        return line

    for s in sorted(nbr):
        if len(nbr[s]) != 2:
            for n in nbr[s]:
                if ((s, n) if s < n else (n, s)) not in used:
                    out.append(walk(s, n))
    for a, b in sorted(und):                       # 남은 고리
        if (a, b) not in used:
            out.append(walk(a, b))
    return out


def equipment(nodes, und, stations):
    """dashboard.html buildRailGeom + layout3D 와 같은 자리."""
    nbr = {}
    for a, b in und:
        nbr.setdefault(a, []).append(b)
        nbr.setdefault(b, []).append(a)
    cell, out = set(), []
    for s in stations:
        k = int(s[3])
        if k not in (8, 9):
            continue
        a = nodes.get(int(s[0]))
        if a is None:
            continue
        b = nodes.get(int(s[1]))
        if b is not None and b != a:
            dx, dy = b[0] - a[0], b[1] - a[1]
        else:
            ns = nbr.get(int(s[0]))
            if not ns:
                continue
            c = nodes[ns[0]]
            dx, dy = c[0] - a[0], c[1] - a[1]
        l = math.hypot(dx, dy) or 1.0
        tx, ty = dx / l, dy / l
        r = min(1.0, max(0.0, float(s[2] or 0))) if b is not None else 0.0
        x = a[0] + ((b[0] - a[0]) * r if b is not None else 0)
        y = a[1] + ((b[1] - a[1]) * r if b is not None else 0)
        sg = 1 if k == 9 else -1                    # 9 = 진행 방향 오른쪽(법선 +)
        px, py = x + (-ty) * OFF * sg, y + tx * OFF * sg
        key = (round(px / STEP), round(py / STEP))
        if key in cell:
            continue
        cell.add(key)
        out.append((px, py))
    return out


def geo(cache_path):
    """레이아웃 캐시 → 설정에 적을 맵 좌표 (bridge_editor.js geoFromCache 와 같은 계산).

    r : 레일 — 이어진 줄마다 [x, y, x, y, …]   (단위 Q, 왼쪽 위 0)
    e : 설비 — [x, y, x, y, …]
    w, h : 맵 크기 · n : 노드 수 · ed : 레일 수
    """
    nodes, und, stations = load_cache(cache_path)
    xs = [p[0] for p in nodes.values()]
    ys = [p[1] for p in nodes.values()]
    x0, y0 = min(xs) - 250, min(ys) - 250          # 설비가 레일 밖으로 1.7 m 나온다
    x1, y1 = max(xs) + 250, max(ys) + 250

    def qx(v):
        return int(round((v - x0) / Q))

    def qy(v):
        return int(round((v - y0) / Q))

    r = []
    for ln in chains(und):
        out, last = [], None
        for n in ln:
            p = (qx(nodes[n][0]), qy(nodes[n][1]))
            if p != last:
                out += p
                last = p
        if len(out) >= 4:
            r.append(out)
    e = []
    for x, y in equipment(nodes, und, stations):
        e += [qx(x), qy(y)]
    return dict(w=int(math.ceil((x1 - x0) / Q)), h=int(math.ceil((y1 - y0) / Q)),
                r=r, e=e, n=len(nodes), ed=len(und))


def default_config(cache_dir=CACHE_DIR, log=print):
    maps = {}
    for p in PLATES:
        if not p["fab"]:
            continue
        cp = cache_for(p["fab"], p["prefix"], cache_dir)
        if not cp:
            continue
        g = geo(cp)
        maps[p["key"]] = dict(name=f'{p["fab"]}/{p["prefix"]}', fit="fill", rot=0, fx=False, fy=False, geo=g)
        log(f'  {p["tag"]:10s} ← {p["fab"]}/{p["prefix"]:3s} 노드 {g["n"]:>6,} · 레일 {g["ed"]:>6,} · '
            f'설비 {len(g["e"]) // 2:>5,}')
    return dict(version=1, saved=False,
                plates=[dict(key=p["key"], tag=p["tag"], col=p["col"]) for p in PLATES],
                maps=maps, cards=json.loads(json.dumps(CARDS)),
                areas=json.loads(json.dumps(AREAS)), texts=dict(TEXTS), bg={})


# ── 틀 손질 ────────────────────────────────────────────────────────
def _div_end(tpl, i):
    """tpl[i] 에서 열린 <div 의 짝 </div> 끝 위치."""
    depth, j = 0, i
    tag = re.compile(r"<div\b|</div>")
    for m in tag.finditer(tpl, i):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return m.end()
    raise ValueError("짝 </div> 를 못 찾았다")


def _attr(tpl, i, attr):
    """tpl[i] 의 '<tag' 바로 뒤에 속성 하나를 끼운다."""
    j = tpl.index(" ", i)
    return tpl[:j] + " " + attr + tpl[j:]


def tag_template(tpl):
    """틀에 이름표를 단다. 한 자리라도 못 찾으면 멈춘다 (고객 원본이 바뀐 것이다)."""
    if "data-bm-" in tpl:
        raise SystemExit("이미 이름표가 달린 틀이다 — 고객 원본으로 돌려라")
    # 판
    for p in PLATES:
        s = tpl.find(p["find"])
        if s < 0:
            raise SystemExit(f'판을 못 찾았다: {p["tag"]}  ({p["find"]})')
        s = tpl.rfind("<div", 0, s)
        tpl = _attr(tpl, s, f'data-bm-plate="{p["key"]}"')
    # 구역
    for k, f in AREA_FIND.items():
        s = tpl.find(f)
        if s < 0:
            raise SystemExit(f"구역을 못 찾았다: {k}  ({f})")
        tpl = _attr(tpl, s, f'data-bm-area="{k}"')
    # 글자
    for k, f in TEXT_FIND.items():
        s = tpl.find(f)
        if s < 0:
            raise SystemExit(f"글자를 못 찾았다: {k}")
        s = tpl.rfind("<div", 0, s)
        tpl = _attr(tpl, s, f'data-bm-text="{k}"')
    # 바탕화면
    for k, f in BG_FIND.items():
        if tpl.count(f) != 1:
            raise SystemExit(f"바탕 자리를 못 찾았다: {k}  ({f})")
        tpl = _attr(tpl, tpl.find(f), f'data-bm-bg="{k}"')
    # 무대
    if tpl.count(SCENE_FIND) != 1:
        raise SystemExit("무대(sceneT)를 못 찾았다")
    s = tpl.rfind("<div", 0, tpl.find(SCENE_FIND))
    tpl = _attr(tpl, s, 'data-bm-scene="1"')
    tpl = tpl.replace(SCENE_FIND, "transform-style:preserve-3d;transform:"
                      "translate(var(--bmpx,0px),var(--bmpy,0px)) {{ sceneT }}", 1)
    # 패널 — {{ billT }} 를 탄 div 마다. 뒤에서부터 (앞자리가 안 밀리게)
    cards = [m.start() for m in re.finditer(r'<div style="[^"]*\{\{ billT \}\}', tpl)]
    names = []
    for s in reversed(cards):
        e = _div_end(tpl, s)
        m = re.search(r'font-weight:700[^"]*">([A-Za-z0-9_]+)</div>', tpl[s:e])
        if not m:
            raise SystemExit("패널 이름을 못 찾았다")
        name = m.group(1)
        nd = s + tpl[s:e].rfind("<div", 0, m.start())
        block = tpl[s:e]
        # 이름 div 에 표
        rel = nd - s
        block = block[:rel] + '<div data-bm-name="1"' + block[rel + 4:]
        # 옮길 자리 — {{ billT }} 바로 앞 (판·벽 어디든 그 자리에서는 바닥과 나란하다)
        block = block.replace("{{ billT }}",
                              "translate3d(var(--bmx,0px),var(--bmy,0px),var(--bmz,0px)) {{ billT }}", 1)
        block = '<div data-bm-card="%s"' % name + block[4:]
        tpl = tpl[:s] + block + tpl[e:]
        names.append(name)
    return tpl, list(reversed(names))


def inject(raw, tpl, cfg, js):
    """틀을 되돌려 넣고, 설정과 편집기를 <head> 에 넣는다."""
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', raw, re.S)
    body = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
    raw = raw[:m.start(2)] + body + raw[m.end(2):]
    if re.search(r"</script", js, re.I):
        raise SystemExit("bridge_editor.js 안에 '</script' 가 있다 — HTML 이 먼저 닫힌다")
    cj = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    blk = ('\n  <script type="application/json" id="bm-config">' + cj + '</script>\n'
           '  <script id="bm-editor">\n' + js + '\n  </script>\n')
    k = raw.index("<head>") + len("<head>")
    k = raw.index("\n", raw.index("<meta", k)) if "<meta" in raw[k:k + 200] else k
    return raw[:k] + blk + raw[k:]


def read_config(path):
    """이미 만든 모니터에서 설정을 꺼낸다 (없으면 None)."""
    if not os.path.exists(path):
        return None
    raw = io.open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="bm-config">(.*?)</script>', raw, re.S)
    if not m:
        return None
    return json.loads(m.group(1).replace("<\\/", "</"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="판마다 실제 아이소메트리 + ✎ 수정 모드")
    ap.add_argument("monitor", nargs="?", default=None, help="고객 원본 (기본: OHT_Bridge_Monitor_원본.html)")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--cache-dir", default=CACHE_DIR)
    ap.add_argument("--reset", action="store_true", help="화면에서 저장한 설정을 버리고 표대로 새로")
    ap.add_argument("--settings", default=SETTINGS, help="화면 '저장' 이 쓴 설정 JSON (있으면 HTML 기본값으로 굳힌다)")
    ns = ap.parse_args(argv)

    if ns.monitor is None:
        if not os.path.exists(ORIG):
            head = io.open(MONITOR, encoding="utf-8").read()
            if "bm-config" in head or "mapiso-" in head or "m14aiso" in head:
                sys.exit(f"{os.path.basename(ORIG)} 가 없는데 {os.path.basename(MONITOR)} 는 이미 "
                         f"손본 것이다 — 고객 원본을 {os.path.basename(ORIG)} 로 두고 다시 돌려라")
            shutil.copyfile(MONITOR, ORIG)
            print(f"  원본을 떠 뒀다: {os.path.basename(ORIG)}")
        ns.monitor = ORIG
        ns.out = ns.out or MONITOR
    ns.out = ns.out or os.path.splitext(ns.monitor)[0] + "_MAP.html"

    raw = io.open(ns.monitor, encoding="utf-8").read()
    if "bm-config" in raw or "mapiso-" in raw or "m14aiso" in raw:
        sys.exit("이미 손본 모니터다 — 고객 원본으로 돌려라")
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', raw, re.S)
    if not m:
        sys.exit("모니터 HTML 에서 템플릿을 못 찾았다")
    tpl, names = tag_template(json.loads(m.group(2)))
    print(f"  패널 {len(names)}개: {', '.join(names)}")

    # 설정 — ① 옆의 설정 JSON(화면 '저장') ② 전에 만든 HTML 에 저장돼 있던 것 ③ 표대로
    kept, src = None, ""
    if not ns.reset:
        if os.path.exists(ns.settings):
            kept, src = json.load(io.open(ns.settings, encoding="utf-8")), os.path.basename(ns.settings)
        else:
            k = read_config(ns.out)
            if k and k.get("saved"):
                kept, src = k, "전에 만든 HTML"
    if kept:
        cfg = kept
        print(f"  ★화면에서 저장한 설정을 굳힌다 ({src}, {kept.get('savedAt', '')}) — 표대로 새로 하려면 --reset")
    else:
        cfg = default_config(ns.cache_dir)
    cfg["builtAt"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if not cfg.get("maps"):
        print("  [주의] 얹을 맵이 하나도 없다 (OHT_MAP/cache 확인) — 화면 '✎ 수정' 에서 불러와도 된다")

    js = io.open(EDITOR_JS, encoding="utf-8").read()
    out = inject(raw, tpl, cfg, js)
    os.makedirs(os.path.dirname(os.path.abspath(ns.out)), exist_ok=True)
    io.open(ns.out, "w", encoding="utf-8").write(out)
    print(f"\n→ {ns.out}  ({os.path.getsize(ns.out) // 1024:,} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
