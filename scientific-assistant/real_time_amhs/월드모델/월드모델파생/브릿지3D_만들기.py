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
        nodes, edges, ports, ez = [], [], [], []
        for i, (x0, y0, x1, y1) in enumerate(segs):
            # 도면 y 는 아래로 자란다 — 바닥 좌표는 위로 자라니 뒤집는다
            ax, ay = x0 * W, (1 - y0) * H
            bx, by = x1 * W, (1 - y1) * H
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="판마다 oht3d 아이소메트리를 얹는다")
    ap.add_argument("monitor", help="고객이 만든 모니터 HTML")
    ap.add_argument("draw", help="도면 PNG 폴더")
    ap.add_argument("-o", "--out",
                    default=os.path.join(OUT_DIR, "OHT_Bridge_Monitor_3D.html"))
    ns = ap.parse_args(argv)
    os.makedirs(OUT_DIR, exist_ok=True)

    data = dict(fabs=[{k: f[k] for k in ("key", "tag", "zone", "col", "find")}
                      for f in FABS],
                layouts=layouts(ns.draw), ncar=NCAR)
    jp = os.path.join(OUT_DIR, "브릿지_레이아웃.json")
    io.open(jp, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))

    raw = io.open(ns.monitor, encoding="utf-8").read()
    if MARK in raw:
        sys.exit("이미 붙어 있다 — 원본으로 다시 돌려라")
    tag = (MARK + '\n<script type="module" src="/static/브릿지_아이소.js"></script>\n')
    i = raw.rindex("</body>")
    io.open(ns.out, "w", encoding="utf-8").write(raw[:i] + tag + raw[i:])
    print(f'\n→ {ns.out}  ({os.path.getsize(ns.out)//1024} KB)')
    print(f'→ {jp}  ({os.path.getsize(jp)//1024} KB)')
    print("\n  로컬에서:  http://localhost:10005/static/OHT_Bridge_Monitor_3D.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
