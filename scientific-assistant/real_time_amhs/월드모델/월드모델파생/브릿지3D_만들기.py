# -*- coding: utf-8 -*-
"""동간 브릿지 — **월드모델파생 아이소메트리(oht3d) 그대로**, 동마다 제 높이에.

    python 브릿지3D_만들기.py <도면폴더> [-o static/동간브릿지_3D.html]

2026-09-21. 고객: "그냥 기존에 사용하던 아이소메트리 하면 되잖아, 잘 만들어
              둔 걸 왜 안 써", "건물마다 틀린데 왜 한 판에 전부 다 그리냐",
              "마우스로 움직이면 뭐가 제대로 되게 해야지".

무엇을 하나
────────────────────────────────────────────────────────────────────
  ① 도면 PNG 에서 **레일 줄을 뽑는다** (긴 가로·세로 선 — FAB 베이는 거의
     축에 나란하다). 도면_얹기.py 의 그 방법을 빌려 쓴다.
  ② FAB 다섯을 **각자 제 높이(층)** 에 놓고, 그 사이를 브릿지 엣지로 잇는다.
     층이 다르면 브릿지가 비스듬한 경사로가 된다.
  ③ nodes / edges / zones 하나로 합쳐 oht3d 에 넘긴다.
     → 툴바·마우스 돌리기·확대·HID Zone 패널·차량 추적이 전부 **그대로** 산다.

★oht3d 노드에 높이(z)를 넣었다 (기본 0 — 기존 화면은 하나도 안 바뀐다).
  예전엔 {id,x,y} 뿐이라 동을 한 바닥에 깔 수밖에 없었다.
"""
from __future__ import annotations

import argparse
import importlib.util as _ilu
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location("layon", os.path.join(BASE, "도면_얹기.py"))
_lay = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_lay)          # prep() — 도면에서 레일 뽑기

OUT_DIR = os.path.join(BASE, "static")

# ── FAB 다섯 — 어디에, 몇 층에 ──────────────────────────────────────
#   ox,oy : 왼쪽아래 모서리 (m) · w : 실제 가로 (m, 세로는 도면 비로 따라간다)
#   z     : 그 층 높이 (m). ★실제 층고는 6~8 m 인데 무대가 800 m 라 그대로 쓰면
#           층이 갈린 게 안 보인다. 아래 EXAG 로 부풀린다.
EXAG = 3.2
FABS = [
    dict(key="m14b",   zone="7F · M14B",  fl=7, ox=  0, oy=250, w=210, col="#3ad6c8"),
    dict(key="m14A",   zone="3F · M14A",  fl=3, ox=  0, oy= 40, w=210, col="#3ad6c8"),
    dict(key="M16HUB", zone="HUB · M16",  fl=3, ox=300, oy=130, w=190, col="#8fd3ff"),
    dict(key="M16A",   zone="6F · M16 6F", fl=6, ox=600, oy=250, w=210, col="#ffce7a"),
    dict(key="M16B",   zone="2F · M16 2F", fl=2, ox=600, oy= 40, w=210, col="#ff8f8f"),
]
FLOOR_H = 7.0                       # 층고 (m) — 2F 를 0 으로 잡는다
ROT = {"m14b": 0, "m14A": 0, "M16HUB": 0, "M16A": 0, "M16B": 0}   # FAB 별 회전

# ── 브릿지 — a/b 는 (FAB, 그 FAB 안에서 붙을 자리 0~1) ──────────────
BRIDGES = [
    dict(id="M14LFT",   frm="M14B",     to="M16 HUB", col="#3ad6c8",
         a=("m14b",   1.0, .45), b=("M16HUB", 0.0, .72)),
    dict(id="M14CNV",   frm="M14A CNV", to="M16 HUB", col="#3ad6c8",
         a=("m14A",   1.0, .55), b=("M16HUB", 0.0, .28)),
    dict(id="M16LFT",   frm="M16 HUB",  to="M16 6F",  col="#ffce7a",
         a=("M16HUB", 1.0, .72), b=("M16A",   0.0, .45)),
    dict(id="M16LFT2F", frm="M16 HUB",  to="M16 2F",  col="#ff6b6b",
         a=("M16HUB", 1.0, .28), b=("M16B",   0.0, .55)),
    dict(id="M16EUV",   frm="M16 LFT",  to="M16 2F",  col="#8fd3ff",
         a=("M16A",   0.5, 1.0), b=("M16B",   0.5, 0.0)),
]
BR_PTS = 14          # 브릿지를 몇 토막으로 나눌지 — 층이 다르면 경사로가 된다
VPZ = 16             # FAB 한 곳에 굴릴 차 수 (보기용)


def build(draw_dir: str):
    nodes, edges, zones, ports, fabs = [], [], [], [], []
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
            W, H = H, W
        z = round((f["fl"] - 2) * FLOOR_H * EXAG, 1)          # 2F 가 0
        f["h"], f["z"] = H, z

        def put(u, v):
            v = 1 - v                                          # 도면 y 는 아래로
            if rot == 90:    u, v = v, 1 - u
            elif rot == 180: u, v = 1 - u, 1 - v
            elif rot == 270: u, v = 1 - v, u
            return round(f["ox"] + u * W, 2), round(f["oy"] + v * H, 2)

        ez = []
        for i, (x0, y0, x1, y1) in enumerate(segs):
            ax, ay = put(x0, y0); bx, by = put(x1, y1)
            n0, n1 = f'{f["key"]}_{i}a', f'{f["key"]}_{i}b'
            nodes += [dict(id=n0, x=ax, y=ay, z=z), dict(id=n1, x=bx, y=by, z=z)]
            eid = f'{f["key"]}_{i}'
            edges.append({"id": eid, "from": n0, "to": n1})
            ez.append(eid)
            if i % 5 == 0:
                ports.append(dict(x=round((ax + bx) / 2, 1),
                                  y=round((ay + by) / 2 + 3.0, 1), z=z,
                                  w=2.6, d=2.6, h=2.4, kind="eq"))
        zones.append(dict(id=f["zone"], edges=ez, z=z))
        fabs.append(dict(key=f["key"], zone=f["zone"], col=f["col"],
                         w=W, h=round(H, 1), z=z))
        print(f'  {f["zone"]:12s} {r["src"]:>10s} · 레일 {len(segs):3d}줄'
              f'  → {W}m × {H:.0f}m · {f["fl"]}F(높이 {z}m)')

    FB = {f["key"]: f for f in FABS}

    def pt(spec):
        k, rx, ry = spec
        g = FB[k]
        return (g["ox"] + rx * g["w"], g["oy"] + (1 - ry) * g["h"], g["z"])

    for b in BRIDGES:                      # 브릿지 — 층이 다르면 경사로
        (ax, ay, az), (bx, by, bz) = pt(b["a"]), pt(b["b"])
        ids = []
        for k in range(BR_PTS + 1):
            t = k / BR_PTS
            nid = f'{b["id"]}_{k}'
            nodes.append(dict(id=nid, x=round(ax + (bx - ax) * t, 2),
                              y=round(ay + (by - ay) * t, 2),
                              z=round(az + (bz - az) * t, 2)))
            ids.append(nid)
        ez = []
        for k in range(BR_PTS):
            eid = f'{b["id"]}#{k}'
            edges.append({"id": eid, "from": ids[k], "to": ids[k + 1]})
            ez.append(eid)
        zones.append(dict(id=f'브릿지 · {b["id"]}', edges=ez))
        print(f'  브릿지 {b["id"]:10s} {az:5.0f}m → {bz:5.0f}m'
              f'  ({"경사로" if abs(az - bz) > 1 else "수평"})')
    return nodes, edges, zones, ports, fabs


def main(argv=None):
    ap = argparse.ArgumentParser(description="동간 브릿지 3D (월드모델파생 아이소메트리)")
    ap.add_argument("draw", help="도면 PNG 폴더")
    ap.add_argument("-o", "--out",
                    default=os.path.join(OUT_DIR, "동간브릿지_3D.html"))
    ns = ap.parse_args(argv)

    nodes, edges, zones, ports, fabs = build(ns.draw)
    data = dict(nodes=nodes, edges=edges, zones=zones, ports=ports, fabs=fabs,
                bridges=[{k: b[k] for k in ("id", "frm", "to", "col")}
                         for b in BRIDGES],
                vperzone=VPZ)
    page = io.open(os.path.join(BASE, "브릿지3D_틀.html"), encoding="utf-8").read()
    page = page.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    os.makedirs(os.path.dirname(ns.out), exist_ok=True)
    io.open(ns.out, "w", encoding="utf-8").write(page)
    print(f'\n  노드 {len(nodes):,} · 엣지 {len(edges):,} · 존 {len(zones)}'
          f' · 설비 {len(ports)}')
    print(f'→ {ns.out}  ({os.path.getsize(ns.out)//1024} KB)')
    print("\n  로컬에서:  http://localhost:10005/static/동간브릿지_3D.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
