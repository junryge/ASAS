# -*- coding: utf-8 -*-
"""동간 브릿지 모니터의 아이소 판 위에 **실제 OHT 레일 도면**을 얹는다.

    python 도면_얹기.py <모니터.html> <도면폴더> [-o 나온것.html]

  도면 폴더에는 FAB 마다 PNG 한 장씩 (m14b · m14A · M16HUB · M16A · M16B).
  2026-09-21. 고객: "x2323 이미지거든 이걸 위에 올려서 해주라 … 색상 살려서".

무엇을 하나
────────────────────────────────────────────────────────────────────
  ① 도면에서 **흰 여백을 잘라내고** 선을 굵힌 뒤 줄인다
  ② 다크 화면에 맞게 뒤집어(invert) 선만 밝게 남기고
  ③ 판마다 **그 판의 테마색**(청록·블루·앰버·레드)으로 물들여
  ④ 고객 마크업의 판 안에 겹 한 장으로 깐다

★고객이 잡은 자리·크기는 하나도 안 건드린다. 판 안에 div 하나만 넣는다.

겪은 것 셋 — 다시 안 밟으려고 적어 둔다
────────────────────────────────────────────────────────────────────
  ⓐ 인라인 style 에 data:URI 를 넣으면 안 된다. 이 페이지의 틀이 style 을
     **세미콜론으로 쪼개** 읽어서 `data:image/png;base64` 의 그 세미콜론에서
     URL 이 끊긴다 (`url("data:image/png")` 만 남는다). → <style> 블록으로 뺀다.
  ⓑ 템플릿 JSON 을 되돌릴 때 `</script>` 를 그대로 쓰면 스크립트 태그가 먼저
     닫힌다. 원본도 \\u002F 로 적혀 있다 — 되돌릴 때도 그렇게 적는다.
  ⓒ 도면을 그냥 줄이면 1px 선이 이웃 흰 화소와 평균 나서 사라진다. 화면에서
     판은 200px 남짓이라 도면이 통째로 안 보였다. → 줄이면서 **선을 굵힌다**
     (조금씩 어긋나게 여러 번 겹쳐 그리고 darken 으로 제일 어두운 값을 남김).

이 환경에는 PIL·ImageMagick 이 없어서 ①은 헤드리스 크로미움의 canvas 로 한다.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile

CHROME = next((p for p in (
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome-linux/chrome",
    "/usr/bin/chromium", "/usr/bin/google-chrome") if os.path.exists(p)), None)

# ── 어느 판에 어느 도면을 깔지 ──────────────────────────────────────
#   ★층 ↔ FAB 짝이 다르면 **이 표만** 고치면 된다.
#   find : 그 판을 찾을 표식 (고객 마크업의 left/top/width/height 그대로)
#   hue  : sepia(약 39°) 에서 그 판 테마색까지 돌릴 각도
PLATES = [
    dict(tag="7F · M14B", find="left:30px;top:20px;width:300px;height:210px",
         img="m14b",   hue=135, op=".34", note="청록"),
    dict(tag="3F · M14A", find="left:30px;top:420px;width:300px;height:210px",
         img="m14A",   hue=135, op=".34", note="청록"),
    dict(tag="M16 HUB",   find="left:360px;top:250px;width:340px;height:300px",
         img="M16HUB", hue=164, op=".40", note="블루"),
    dict(tag="6F · M16",  find="left:690px;top:20px;width:290px;height:220px",
         img="M16A",   hue=0,   op=".34", note="앰버"),
    dict(tag="2F · M16",  find="left:690px;top:530px;width:290px;height:210px",
         img="M16B",   hue=321, op=".34", note="레드"),
]
CLS = "ohtlay"
CAR_UP = {"m14b":"#3ad6c8", "m14A":"#3ad6c8", "M16HUB":"#8fd3ff",
          "M16A":"#ffce7a", "M16B":"#ff8f8f"}
CAR_DN = "#7aa7ff"          # 반대 방향은 원본 화면과 같은 파랑
TARGET_W = 760          # 뽑아낼 도면 가로 (판이 300px 이라 이 정도면 넉넉하다)
WHITE = 228             # 이보다 밝으면 '흰 바탕·격자' 로 보고 잘라낸다
DARK  = 170             # 이보다 어두우면 레일로 본다
NSEG  = 70              # 판 하나에서 쓸 레일 줄 수 (레일망이 성기면 안 된다)
NCAR  = 2               # 레일 한 줄에 태울 OHT 수
RAIL_Z = 22             # ★레일을 바닥에서 몇 px 띄울지 — 이게 '아이소메트리'다
CAR_Z  = 26             # 차는 레일 위에
HANG_N = 3              # 레일 한 줄에 매달 행거 수
CAR_SEG = 26            # 앞에서 몇 줄에만 차를 태울지 (너무 많으면 느리다)


# ── ① 도면 다듬기 — 흰 여백 잘라내고, 선 굵히고, 줄인다 ─────────────
_PREP_JS = """<!doctype html><meta charset=utf-8><body><div id=out>...</div><script>
const img = new Image();
img.onload = () => {
  const W = img.width, H = img.height;
  const c0 = document.createElement('canvas'); c0.width = W; c0.height = H;
  const g0 = c0.getContext('2d', { willReadFrequently: true });
  g0.drawImage(img, 0, 0);
  const d = g0.getImageData(0, 0, W, H).data;
  let x0 = W, y0 = H, x1 = 0, y1 = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    if (d[i] > __WHITE__ && d[i+1] > __WHITE__ && d[i+2] > __WHITE__) continue;
    if (x < x0) x0 = x; if (x > x1) x1 = x;
    if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  if (x1 <= x0) { x0 = 0; y0 = 0; x1 = W - 1; y1 = H - 1; }
  const pad = 8;
  x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad);
  x1 = Math.min(W - 1, x1 + pad); y1 = Math.min(H - 1, y1 + pad);
  const cw = x1 - x0 + 1, ch = y1 - y0 + 1;
  const s = Math.min(1, __TW__ / cw);
  const c1 = document.createElement('canvas');
  c1.width = Math.round(cw * s); c1.height = Math.round(ch * s);
  const g1 = c1.getContext('2d');
  g1.imageSmoothingQuality = 'high';
  g1.fillStyle = '#ffffff'; g1.fillRect(0, 0, c1.width, c1.height);
  g1.globalCompositeOperation = 'darken';          // ★선 굵히기(팽창)
  const K = Math.max(1, cw / __TW__ * 1.15);
  for (const [dx, dy] of [[0,0],[K,0],[-K,0],[0,K],[0,-K],[K,K],[-K,-K],[K,-K],[-K,K]])
    g1.drawImage(c0, x0 + dx, y0 + dy, cw, ch, 0, 0, c1.width, c1.height);
  g1.globalCompositeOperation = 'source-over';

  // ★도면만 깔면 그림이다. OHT 가 **그 레일 위를** 달려야 관제다.
  //   래스터라 레일 그래프가 없으니, 굵혀 놓은 그림에서 **긴 가로·세로 줄**을
  //   찾아 레일로 쓴다 (FAB 베이는 거의 축에 나란하다).
  const D = g1.getImageData(0, 0, c1.width, c1.height).data;
  const CW = c1.width, CH2 = c1.height;
  const dark = (x, y) => {
    const i = (y * CW + x) * 4;
    return (D[i] * .299 + D[i+1] * .587 + D[i+2] * .114) < __DARK__;
  };
  const segs = [];
  const scan = (horiz) => {
    const A = horiz ? CH2 : CW, B = horiz ? CW : CH2;
    const minLen = Math.max(24, B * 0.10);
    for (let a = 0; a < A; a += 2) {
      let run = -1;
      for (let b = 0; b <= B; b++) {
        const on = b < B && (horiz ? dark(b, a) : dark(a, b));
        if (on && run < 0) run = b;
        if (!on && run >= 0) {
          if (b - run >= minLen)
            segs.push(horiz ? [run, a, b - 1, a] : [a, run, a, b - 1]);
          run = -1;
        }
      }
    }
  };
  scan(true); scan(false);
  // 굵은 선 하나가 여러 줄로 잡힌다 — 가까운 것끼리 하나만 남긴다
  segs.sort((p, q) => (q[2]-q[0] + q[3]-q[1]) - (p[2]-p[0] + p[3]-p[1]));
  const keep = [];
  for (const s of segs) {
    const h = s[1] === s[3];
    if (keep.some(k => (k[1] === k[3]) === h &&
        Math.abs((h ? k[1] : k[0]) - (h ? s[1] : s[0])) < 9 &&
        Math.min(h ? k[2] : k[3], h ? s[2] : s[3])
          - Math.max(h ? k[0] : k[1], h ? s[0] : s[1]) > 0)) continue;
    keep.push(s);
    if (keep.length >= __NSEG__) break;
  }
  document.getElementById('out').textContent = JSON.stringify(
    { w: c1.width, h: c1.height, src: W + 'x' + H, uri: c1.toDataURL('image/png'),
      segs: keep.map(s => [ +(s[0]/CW).toFixed(4), +(s[1]/CH2).toFixed(4),
                            +(s[2]/CW).toFixed(4), +(s[3]/CH2).toFixed(4) ]) });
};
img.src = 'data:image/png;base64,__B64__';
</script>"""


def prep(path: str) -> dict:
    if not CHROME:
        sys.exit("크로미움을 못 찾았다 — 도면을 다듬을 수가 없다")
    page = (_PREP_JS.replace("__WHITE__", str(WHITE))
                    .replace("__DARK__", str(DARK))
                    .replace("__NSEG__", str(NSEG))
                    .replace("__TW__", str(TARGET_W))
                    .replace("__B64__", base64.b64encode(open(path, "rb").read()).decode()))
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as f:
        f.write(page)
        tmp = f.name
    try:
        dom = subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=20000", "--dump-dom", "file://" + tmp],
            capture_output=True, text=True).stdout
    finally:
        os.unlink(tmp)
    m = re.search(r'<div id="out">(\{.*?\})</div>', dom, re.S)
    if not m:
        sys.exit(f"도면을 못 다듬었다: {os.path.basename(path)}")
    return json.loads(m.group(1))


# ── ②③ 겹 한 장 — 색까지 입혀 <style> 로 뺀다 ───────────────────────
def plate_wh(find: str):
    """판 크기 — 레일 좌표를 이 판의 px 로 환산할 때 쓴다."""
    w = int(re.search(r"width:(\d+)px", find).group(1))
    h = int(re.search(r"height:(\d+)px", find).group(1))
    return w, h


def iso3d(p, segs) -> str:
    """★핵심 — 도면을 **입체로 세운다**.

    고객: "각 맵을 아이소메트리로 하라고, 지금 평면이잖아."
    맞다. 기운 판에 그림 한 장 깔아 놓은 건 여전히 납작한 그림이다.
    실제 FAB 은 바닥 위로 **레일이 떠 있고** 거기 OHT 가 매달려 다닌다.
    그래서 세 켜로 나눈다 — 기존 아이소메트리(oht3d.js) 와 같은 생각이다:

        ① 바닥 (Z=0)        도면 — 설비 배치가 깔린 층
        ② 레일 (Z=RAIL_Z)   도면에서 뽑은 레일을 **띄워서** 얹고, 바닥까지
                            행거를 내려 매단다 → 여기서 높이가 생긴다
        ③ 차  (Z=CAR_Z)     그 레일 위를 달린다

    판이 이미 CSS 3D(preserve-3d) 라 translateZ 만 주면 진짜로 떠오른다.
    자바스크립트는 안 쓴다.
    """
    W, H = plate_wh(p["find"])
    up = CAR_UP.get(p["img"], "#3ad6c8")
    out = []

    # ② 레일 — 띄운 들보 + 바닥으로 내린 행거
    for i, (x0, y0, x1, y1) in enumerate(segs):
        ax, ay = x0 * W, y0 * H
        bx, by = x1 * W, y1 * H
        horiz = abs(bx - ax) >= abs(by - ay)
        L = max(3.0, (bx - ax) if horiz else (by - ay))
        out.append(
            '<div class="ohtrail ohtrail-%s" style="left:%.1fpx;top:%.1fpx;'
            'width:%.1fpx;height:%.1fpx"></div>'
            % (p["img"], ax, ay, L if horiz else 2.2, 2.2 if horiz else L))
        for k in range(HANG_N):                       # 행거 — 바닥까지 내린다
            t = (k + .5) / HANG_N
            hx, hy = ax + (bx - ax) * t, ay + (by - ay) * t
            out.append('<div class="ohthang" style="left:%.1fpx;top:%.1fpx"></div>'
                       % (hx, hy))

    # ③ 차 — 레일 위. 긴 줄부터 CAR_SEG 개만 태운다 (많으면 느려진다)
    for i, (x0, y0, x1, y1) in enumerate(segs[:CAR_SEG]):
        d = "M %.1f %.1f L %.1f %.1f" % (x0 * W, y0 * H, x1 * W, y1 * H)
        for k in range(NCAR):
            back = ((i + k) % 3 == 2)
            dur = 7.0 + ((i * 7 + k * 3) % 9) * 0.55
            out.append(
                '<div class="ohtcar ohtcar-%s%s" style="offset-path:path(\'%s\');'
                'animation-duration:%.1fs;animation-delay:-%.1fs"></div>'
                % (p["img"], " ohtcar-r" if back else "", d, dur,
                   dur * k / NCAR + i * 0.37))
    return "".join(out)


def css(uri: dict) -> str:
    out = [".%s{position:absolute;inset:0;background-repeat:no-repeat;"
           "background-position:center;background-size:100%% 100%%;"
           "mix-blend-mode:screen;pointer-events:none;border-radius:1px}" % CLS]
    for p in PLATES:
        out.append(
            ".{c}-{n}{{background-image:url('{u}');"
            "filter:invert(1) grayscale(1) contrast(1.75) brightness(1.30) "
            "sepia(1) saturate(9) hue-rotate({h}deg);opacity:{o}}}".format(
                c=CLS, n=p["img"], u=uri[p["img"]], h=p["hue"], o=p["op"]))
    out.append("@keyframes ohtrun{from{offset-distance:0%}to{offset-distance:100%}}"
               ".ohtcar{position:absolute;left:0;top:0;width:7px;height:7px;"
               "border-radius:1.5px;offset-rotate:0deg;offset-anchor:center;"
               "animation-name:ohtrun;animation-timing-function:linear;"
               "animation-iteration-count:infinite;pointer-events:none;"
               "transform:translateZ(" + str(CAR_Z) + "px)}")
    out.append(".ohtcar-r{animation-direction:reverse;background:#dbe6ff !important;"
               "box-shadow:0 0 10px " + CAR_DN + ",0 0 3px #fff !important}")
    # ★레일·행거·차를 **띄운다** — 판이 preserve-3d 라 translateZ 가 먹는다
    out.append(".ohtrail{position:absolute;border-radius:1px;pointer-events:none;"
               "transform:translateZ(" + str(RAIL_Z) + "px)}")
    out.append(".ohthang{position:absolute;width:1.2px;height:" + str(RAIL_Z) + "px;"
               "transform-origin:0 0;transform:translateZ(" + str(RAIL_Z) + "px) "
               "rotateX(-90deg);background:linear-gradient(180deg,"
               "rgba(255,255,255,.55),rgba(255,255,255,.06));pointer-events:none}")
    for p in PLATES:
        c = CAR_UP.get(p["img"], "#3ad6c8")
        out.append(".ohtrail-%s{background:%s;"
                   "box-shadow:0 0 9px %s,0 0 3px %s,0 1px 0 rgba(255,255,255,.5)}"
                   % (p["img"], c, c, c))
    for p in PLATES:
        c = CAR_UP.get(p["img"], "#3ad6c8")
        out.append(".ohtcar-%s{background:#ffffff;box-shadow:0 0 11px %s,0 0 4px #fff}"
                   % (p["img"], c))
    return "<style>" + "".join(out) + "</style>"


def main(argv=None):
    ap = argparse.ArgumentParser(description="아이소 판에 실제 레일 도면을 얹는다")
    ap.add_argument("monitor", help="고객이 만든 모니터 HTML")
    ap.add_argument("draw", help="도면 PNG 가 든 폴더")
    ap.add_argument("-o", "--out", default=None)
    ns = ap.parse_args(argv)
    out = ns.out or os.path.splitext(ns.monitor)[0] + "_도면.html"

    raw = io.open(ns.monitor, encoding="utf-8").read()
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', raw, re.S)
    if not m:
        sys.exit("모니터 HTML 에서 템플릿을 못 찾았다")
    tpl = json.loads(m.group(2))

    uri, SEGS = {}, {}
    for p in PLATES:
        f = next((os.path.join(ns.draw, n) for n in os.listdir(ns.draw)
                  if os.path.splitext(n)[0].lower() == p["img"].lower()), None)
        if not f:
            sys.exit(f'도면이 없다: {p["img"]}.PNG')
        r = prep(f)
        uri[p["img"]] = r["uri"]
        SEGS[p["img"]] = r.get("segs") or []
        print(f'  {p["img"]:7s} {r["src"]:>10s} → {r["w"]}x{r["h"]}'
              f'  ({len(r["uri"])//1024} KB)')

    globals()["SEGS"] = SEGS
    k = tpl.index("</helmet>")
    tpl = tpl[:k] + css(uri) + tpl[k:]
    for p in PLATES:
        i = tpl.find(p["find"])
        if i < 0:
            sys.exit(f'판을 못 찾았다: {p["tag"]}  ({p["find"]})')
        j = tpl.index(">", i) + 1
        blk = ('<div class="%s %s-%s" data-layout="%s"></div>' % (
                   CLS, CLS, p["img"], p["img"])
               + iso3d(p, SEGS[p["img"]]))
        tpl = tpl[:j] + blk + tpl[j:]
        print(f'  {p["tag"]:12s} ← {p["img"]:7s} ({p["note"]})'
              f'  레일 {len(SEGS[p["img"]])}줄(Z+{RAIL_Z}) · '
              f'OHT {min(len(SEGS[p["img"]]), CAR_SEG)*NCAR}대')

    # ★"</script>" 를 그대로 쓰면 스크립트가 먼저 닫힌다 — 원본처럼 / 로
    js = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
    io.open(out, "w", encoding="utf-8").write(raw[:m.start(2)] + js + raw[m.end(2):])
    print(f'\n→ {out}  ({os.path.getsize(out)//1024} KB)')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
