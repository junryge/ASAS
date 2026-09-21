# -*- coding: utf-8 -*-
"""고객이 만든 동간 브릿지 화면의 **판마다 oht3d 아이소메트리를 하나씩 얹는다**.

    python 브릿지3D_만들기.py <모니터.html> <도면폴더>

2026-09-21. 고객: "기존 처음에 준 html 사용하고 아이소메트리를 각각 맞게 해주고
              실행하게 해주라. 어차피 월드모델파생에 있잖아, 그걸 위에 로드하면
              되잖아", "하나씩이 아니라 그 화면에 각각 맞게 띄우면 되잖아".

무엇을 만드나 (전부 static/ 에 떨어진다 — 로컬 서버가 /static 을 이미 서빙한다)
────────────────────────────────────────────────────────────────────
  static/OHT_Bridge_Monitor_3D.html   고객 원본 + 붙이는 스크립트 한 줄
  static/브릿지_레이아웃.json          FAB 다섯의 레일 그래프 (도면에서 뽑음)
  static/브릿지_아이소.js              판을 찾아 그 위에 oht3d 를 띄우는 것

왜 판 '안' 이 아니라 판 '위' 인가
────────────────────────────────────────────────────────────────────
  판은 CSS 3D(rotateX·rotateZ)로 기울어 있다. 그 안에 캔버스를 넣으면 CSS 가
  한 번 더 기울여서 **두 번 투영**된다 (3D 로 그린 게 다시 눕는다).
  그래서 캔버스는 화면에 납작하게 두고, 판의 화면상 자리에 맞춰 띄운다.
  oht3d 카메라가 직교(아이소메트리)라 이렇게 겹쳐도 각이 맞는다 —
  아이소메트리 스프라이트를 쌓는 것과 같은 이치다.

★고객 마크업은 **한 글자도 안 고친다**. </body> 앞에 스크립트 한 줄만 넣는다.
"""
from __future__ import annotations

import argparse
import importlib.util as _ilu
import io
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location("layon", os.path.join(BASE, "도면_얹기.py"))
_lay = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_lay)          # prep() — 도면에서 레일 뽑기를 빌려 쓴다

OUT_DIR = os.path.join(BASE, "static")

# ── 판 ↔ FAB ↔ 도면 ────────────────────────────────────────────────
#   find : 고객 마크업에서 그 판을 찾을 표식 (left/top/width/height 그대로)
#   w    : 그 FAB 의 실제 가로 (m) — 세로는 도면 비로 따라간다
FABS = [
    dict(key="m14b",   tag="7F · M14B", zone="M14B",     w=210, col="#3ad6c8",
         find=dict(left=30,  top=20,  width=300, height=210)),
    dict(key="m14A",   tag="3F · M14A", zone="M14A",     w=210, col="#3ad6c8",
         find=dict(left=30,  top=420, width=300, height=210)),
    dict(key="M16HUB", tag="M16 HUB",   zone="M16 HUB",  w=190, col="#8fd3ff",
         find=dict(left=360, top=250, width=340, height=300)),
    dict(key="M16A",   tag="6F · M16",  zone="M16 6F",   w=210, col="#ffce7a",
         find=dict(left=690, top=20,  width=290, height=220)),
    dict(key="M16B",   tag="2F · M16",  zone="M16 2F",   w=210, col="#ff8f8f",
         find=dict(left=690, top=530, width=290, height=210)),
]
NCAR = 12            # 판 하나에 굴릴 차 수 (보기용 — 실제는 피드가 준다)

# ★도면을 판에 맞춰 몇 도 돌릴지 (0·90·180·270).
#   판은 CSS rotateZ(-45°) 로 눕고 oht3d 등각은 방위 +45° 다 — 그대로 두면
#   도면이 판에 대해 **90° 틀어져** 가로지른다 (고객: "방향이 맞아?" — 아니었다).
#   FAB 마다 도면을 놓은 방향이 다를 수 있으니 한 줄로 돌릴 수 있게 둔다.
ROT = {"m14b": 90, "m14A": 90, "M16HUB": 90, "M16A": 90, "M16B": 90}

# ★판을 **실제 FAB 비율**로 고쳐 쓴다.
#   고객 판은 300x210 (1.4:1) 인데 실제 M14A 베이는 210m x 60m (3.5:1) 이다.
#   모양이 다르면 3D 를 아무리 맞춰도 판에 안 들어간다 (고객: "판에 맞게
#   그려지게 해야지"). 가로는 그대로 두고 세로만 도면 비로 줄이되,
#   **판의 가운데를 그대로 둔다** — 그래야 브릿지가 붙어 있던 자리가 안 틀어진다.
RESHAPE = True
# 그래도 어긋나는 통로 하나 — HUB→M16 2F 리프트는 2F 판이 올라간 만큼 내린다
NUDGE = [("left:700px;top:520px;width:120px;height:140px",
          "left:700px;top:600px;width:120px;height:140px")]
MARK = "<!-- 브릿지 아이소메트리 (자동 생성 · 브릿지3D_만들기.py) -->"


def layouts(draw_dir: str) -> dict:
    """도면 → FAB 마다 {nodes, edges, zones, ports}. oht3d 가 받는 모양 그대로."""
    out = {}
    for f in FABS:
        path = next((os.path.join(draw_dir, n) for n in os.listdir(draw_dir)
                     if os.path.splitext(n)[0].lower() == f["key"].lower()), None)
        if not path:
            sys.exit(f'도면이 없다: {f["key"]}')
        r = _lay.prep(path)
        segs = r.get("segs") or []
        W = f["w"]; H = W * r["h"] / r["w"]
        rot = ROT.get(f["key"], 0) % 360
        if rot in (90, 270):
            W, H = H, W                              # 돌리면 가로·세로가 바뀐다
        def put(u, v):
            """도면 안의 비율 자리(0~1) → 바닥 좌표(m). 돌리기까지 여기서."""
            v = 1 - v                                # 도면 y 는 아래로 자란다
            if rot == 90:    u, v = v, 1 - u
            elif rot == 180: u, v = 1 - u, 1 - v
            elif rot == 270: u, v = 1 - v, u
            return u * W, v * H
        nodes, edges, ports, ez = [], [], [], []
        for i, (x0, y0, x1, y1) in enumerate(segs):
            ax, ay = put(x0, y0)
            bx, by = put(x1, y1)
            n0, n1 = f"{i}a", f"{i}b"
            nodes += [dict(id=n0, x=round(ax, 2), y=round(ay, 2)),
                      dict(id=n1, x=round(bx, 2), y=round(by, 2))]
            edges.append({"id": str(i), "from": n0, "to": n1})
            ez.append(str(i))
            if i % 5 == 0:                       # 설비 — 레일 옆에 세운다
                ports.append(dict(x=round((ax + bx) / 2, 1),
                                  y=round((ay + by) / 2 + 3.0, 1),
                                  w=2.6, d=2.6, h=2.4, kind="eq"))
        out[f["key"]] = dict(nodes=nodes, edges=edges, ports=ports,
                             zones=[dict(id=f["zone"], edges=ez)],
                             size=[round(W, 1), round(H, 1)])
        print(f'  {f["tag"]:12s} {r["src"]:>10s} · 레일 {len(segs):3d}줄'
              f'  → {W}m × {H:.0f}m · 설비 {len(ports)}')
    return out


def reshape(tpl: str, sizes: dict) -> str:
    """판을 그 FAB 의 도면 비로 고친다 — 판 안의 벽·선·앵커까지 같이."""
    import re
    for f in FABS:
        d = f["find"]
        w, h0 = d["width"], d["height"]
        ratio = sizes[f["key"]]                      # 가로/세로
        h = max(40, round(w / ratio))
        top = d["top"] + (h0 - h) // 2               # 가운데를 그대로 둔다
        head = (f'left:{d["left"]}px;top:{d["top"]}px;'
                f'width:{w}px;height:{h0}px')
        i = tpl.find(head)
        if i < 0:
            sys.exit(f'판을 못 찾았다: {f["tag"]}')
        j = tpl.find("<!-- ", i + 10)                 # 다음 절 주석까지가 이 판
        blk = tpl[i:j if j > 0 else len(tpl)]
        nb = blk
        nb = nb.replace(head, f'left:{d["left"]}px;top:{top}px;width:{w}px;height:{h}px', 1)
        nb = nb.replace(f'left:0;top:{h0}px;width:{w}px;height:30px',      # 앞 벽
                        f'left:0;top:{h}px;width:{w}px;height:30px', 1)
        nb = nb.replace(f'left:{w}px;top:0;width:30px;height:{h0}px',      # 옆 벽
                        f'left:{w}px;top:0;width:30px;height:{h}px', 1)
        nb = re.sub(r'(left:24px;top:)\d+(px;right:24px;height:4px)',      # 강조선
                    lambda m: m.group(1) + str(h // 2 - 2) + m.group(2), nb, count=1)
        nb = re.sub(r'(left:0;right:0;top:)\d+(px;height:12px)',           # 차 띠
                    lambda m: m.group(1) + str(h // 2 - 6) + m.group(2), nb, count=1)
        nb = re.sub(r'(left:)\d+(px;top:0;width:0;height:0)',              # 카드 앵커
                    lambda m: m.group(1) + str(w // 2) + m.group(2), nb, count=1)
        tpl = tpl[:i] + nb + tpl[i + len(blk):]
        # ★찾는 값도 같이 바꿔야 한다 — 안 바꾸면 스크립트가 판을 못 찾는다
        f["find"] = dict(left=d["left"], top=top, width=w, height=h)
        print(f'  {f["tag"]:12s} 판 {w}x{h0} → {w}x{h}  (top {d["top"]}→{top})')
    for a, b in NUDGE:
        if a in tpl:
            tpl = tpl.replace(a, b, 1)
            print(f'  통로 한 줄 내림  {a[:34]}…')
    return tpl


def main(argv=None):
    ap = argparse.ArgumentParser(description="판마다 oht3d 아이소메트리를 얹는다")
    ap.add_argument("monitor", help="고객이 만든 모니터 HTML")
    ap.add_argument("draw", help="도면 PNG 폴더")
    ap.add_argument("-o", "--out",
                    default=os.path.join(OUT_DIR, "OHT_Bridge_Monitor_3D.html"))
    ns = ap.parse_args(argv)
    os.makedirs(OUT_DIR, exist_ok=True)

    lay = layouts(ns.draw)
    raw = io.open(ns.monitor, encoding="utf-8").read()
    if MARK in raw:
        sys.exit("이미 붙어 있다 — 원본으로 다시 돌려라")

    if RESHAPE:                                      # 판을 FAB 비율로
        import re as _re
        m = _re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', raw, _re.S)
        tpl = json.loads(m.group(2))
        sizes = {k: max(v["size"]) / min(v["size"]) for k, v in lay.items()}
        print()
        tpl = reshape(tpl, sizes)      # ★FABS[i]["find"] 를 새 값으로 고쳐 준다
        js = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
        raw = raw[:m.start(2)] + js + raw[m.end(2):]

    # 판을 고친 **뒤** 의 자리로 JSON 을 쓴다
    data = dict(fabs=[{k: f[k] for k in ("key", "tag", "zone", "col", "find")}
                      for f in FABS], layouts=lay, ncar=NCAR)
    jp = os.path.join(OUT_DIR, "브릿지_레이아웃.json")
    io.open(jp, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))

    tag = (MARK + '\n<script type="module" src="/static/브릿지_아이소.js"></script>\n')
    i = raw.rindex("</body>")
    io.open(ns.out, "w", encoding="utf-8").write(raw[:i] + tag + raw[i:])
    print(f'\n→ {ns.out}  ({os.path.getsize(ns.out)//1024} KB)')
    print(f'→ {jp}  ({os.path.getsize(jp)//1024} KB)')
    print("\n  로컬에서:  http://localhost:10005/static/OHT_Bridge_Monitor_3D.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
