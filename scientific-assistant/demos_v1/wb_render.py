# -*- coding: utf-8 -*-
"""
demos_v1/wb_render.py — 화이트보드 그림 엔진: Mermaid 글 → SVG (파이썬 표준 라이브러리만)

고객: "파이썬으로 커스텀 해서 할수는 없어??"
  Whiteboard(devdotfast)는 Node 24 · pnpm · npm 으로 빌드하는 데스크톱 앱이라 폐쇄망에
  들일 수 없다. 그림 라이브러리(mermaid.min.js) 한 파일도 받을 길이 없었다(CDN · npm 모두
  회사 정책으로 막힘). 그래서 데모스 서버가 Mermaid 글을 직접 읽어 배치하고 SVG 로 그린다.

그리는 것
  flowchart / graph      상자 모양 14가지 · 실선/점선/굵은 선 · 글자 · 묶음(subgraph) · TD/LR/BT/RL
  sequenceDiagram        참가자 · 사람 · 메시지(요청/응답/실패/비동기) · 메모 · loop/alt/opt/par 틀 · 번호
  erDiagram              표(속성 · PK/FK/UK · 설명) · 관계선 · 개수 표시(까마귀발) · 관계 이름
  stateDiagram(-v2)      상태 · 시작 · 끝 · 선택/분기/합류 · 묶음 상태 · 전이 글자
그 밖(pie · gantt · classDiagram …)은 ok=False · kind 로 알려 주고, 화면은 글을 그대로 둔다.

★색은 박지 않는다 — currentColor(둘레의 글자색)와 --wb-* CSS 변수만 쓴다. 그래서 데모스
  (밝은 화면)와 코딩 어시스턴트(어두운/밝은 테마)에서 각 앱의 색을 그대로 따른다.
★폭은 글자 수로 어림한다(한글 1em · 영문 약 0.6em). 서버에는 글꼴이 없어서다.
★배치는 층을 나눠 쌓는 방식(가장 긴 경로로 층 → 가운데값으로 순서 → 겹침 없이 위치)이다.
  상자가 수십 개인 큰 그림은 Mermaid 원본보다 선이 더 겹칠 수 있다 — 나눠 그리게 한다.
"""
from __future__ import annotations

import hashlib
import html
import re
import threading
from collections import defaultdict, deque

__all__ = ["render", "detect_kind", "paper_svg", "WbError", "SUPPORTED"]

SUPPORTED = ("flowchart", "sequence", "er", "state")

MAX_NODES = 160
MAX_EDGES = 320
MAX_EVENTS = 260
MAX_SRC = 40000

FS = 13            # 기본 글자 크기(px)
LH = 17            # 줄 높이
FS_S = 12          # 작은 글자(선 위 글자 · 메시지)
LH_S = 15


class WbError(Exception):
    """그림으로 못 그린 이유 — line 은 원문의 몇째 줄(1부터, 모르면 0)."""

    def __init__(self, msg: str, line: int = 0):
        super().__init__(msg)
        self.line = line


# ─────────────────────────── 글자 폭 · 줄 바꿈 ───────────────────────────
def _cw(ch: str) -> float:
    o = ord(ch)
    if (0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F
            or 0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0xFF01 <= o <= 0xFF60
            or 0x3000 <= o <= 0x303F):
        return 1.0
    if ch == " ":
        return 0.32
    if ch in "il.,:;|!'`[]()":
        return 0.34
    if ch in "mwMW@%&":
        return 0.9
    if ch.isupper():
        return 0.68
    if ch.isdigit():
        return 0.6
    if o > 0x2000:          # 기호 · 화살표 · 이모지
        return 1.0
    return 0.58


def _tw(s: str, fs: float = FS) -> float:
    return sum(_cw(c) for c in s) * fs


# 지우는 것은 진짜 HTML 태그뿐 — List<T> · Map<K, V> · 'a < b and c > d' 같은 글은 그대로 둔다
_TAG = re.compile(
    r"</?(?:a|abbr|b|big|blockquote|center|code|del|div|em|font|h[1-6]|hr|i|img|ins|kbd|li|mark|ol|p|pre|q|s|"
    r"samp|small|span|strike|strong|sub|sup|table|tbody|td|th|thead|tr|tt|u|ul|var|script|style|iframe|object|"
    r"embed|svg|math|link|meta|input|button|form|textarea|select|option|label|video|audio|source|foreignobject)"
    r"""(?:\s+[\w:-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>]+))?){0,12}\s*/?>""", re.I)
_ENT = re.compile(r"#(\d{1,6}|[A-Za-z]{2,8});")        # Mermaid 글자 코드: #quot; #lt; #35; #9829;
_BR = re.compile(r"<br\s*/?>|\\n", re.I)


def _ent(m) -> str:
    v = m.group(1)
    if v.isdigit():
        return chr(int(v)) if 0 < int(v) < 0x110000 else m.group(0)
    u = html.unescape("&" + v + ";")
    return m.group(0) if u == "&" + v + ";" else u      # 모르는 이름은 그대로


def _clean(s: str) -> str:
    """Mermaid 글자 → 보이는 글자. <br> 은 줄바꿈, 다른 태그 · **굵게** · `코드` 표시는 뺀다."""
    s = str(s or "")
    s = _ENT.sub(_ent, s)
    s = _TAG.sub("", s)
    s = _BR.sub("\n", s)
    md = re.fullmatch(r"\s*`([\s\S]*)`\s*", s)
    if md:                           # 마크다운 글("`**굵게** _기울임_`") — 꾸밈 표시는 뺀다
        s = md.group(1)
        s = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"\1", s)
        s = re.sub(r"(?<!\w)_(?![\s_])(.+?)(?<![\s_])_(?!\w)", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = html.unescape(s)
    return s.strip()


def _wrap(s: str, max_w: float, fs: float = FS) -> list[str]:
    out: list[str] = []
    for para in (s.split("\n") if s else [""]):
        words = para.split(" ")
        line = ""
        for w in words:
            cand = (line + " " + w) if line else w
            if _tw(cand, fs) <= max_w or not line:
                line = cand
            else:
                out.append(line)
                line = w
            while _tw(line, fs) > max_w and len(line) > 1:       # 한 낱말이 너무 길면 글자로 자른다
                cut = len(line)
                while cut > 1 and _tw(line[:cut], fs) > max_w:
                    cut -= 1
                out.append(line[:cut])
                line = line[cut:]
        out.append(line)
    return out or [""]


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ─────────────────────────── SVG 틀 ───────────────────────────
_STYLE = (
    '#{u}{{font-family:var(--wb-font,"Malgun Gothic","맑은 고딕","Apple SD Gothic Neo","Noto Sans KR",sans-serif);'
    "font-size:13px}}"
    "#{u} text{{fill:currentColor}}"
    "#{u} .n{{fill:currentColor;fill-opacity:.06;stroke:var(--wb-accent,currentColor);stroke-opacity:.8;stroke-width:1.3}}"
    "#{u} .n2{{fill:none;stroke:var(--wb-accent,currentColor);stroke-opacity:.8;stroke-width:1.1}}"
    "#{u} .nf{{fill:var(--wb-accent,currentColor);fill-opacity:.85;stroke:none}}"
    "#{u} .e{{fill:none;stroke:currentColor;stroke-opacity:.7;stroke-width:1.3}}"
    "#{u} .e.d{{stroke-dasharray:5 4}}"
    "#{u} .e.k{{stroke-width:2.6;stroke-opacity:.8}}"
    "#{u} .ah{{fill:currentColor;fill-opacity:.8;stroke:none}}"
    "#{u} .ao{{fill:var(--wb-bg,#fff);stroke:currentColor;stroke-opacity:.8;stroke-width:1.2}}"
    "#{u} .ax{{fill:none;stroke:currentColor;stroke-opacity:.85;stroke-width:1.6}}"
    "#{u} .lb{{fill:var(--wb-bg,#fff);fill-opacity:.94}}"
    "#{u} .lt{{font-size:12px}}"
    "#{u} .sg{{fill:currentColor;fill-opacity:.03;stroke:currentColor;stroke-opacity:.35;stroke-dasharray:5 4;stroke-width:1.1}}"
    "#{u} .sgt{{font-size:12px;font-weight:700;fill-opacity:.85}}"
    "#{u} .life{{stroke:currentColor;stroke-opacity:.35;stroke-dasharray:4 4}}"
    "#{u} .note{{fill:var(--wb-accent,currentColor);fill-opacity:.1;stroke:var(--wb-accent,currentColor);stroke-opacity:.55}}"
    "#{u} .frame{{fill:none;stroke:currentColor;stroke-opacity:.5;stroke-width:1.1}}"
    "#{u} .tab{{fill:currentColor;fill-opacity:.08;stroke:currentColor;stroke-opacity:.5;stroke-width:1.1}}"
    "#{u} .sep{{stroke:currentColor;stroke-opacity:.45;stroke-dasharray:5 4}}"
    "#{u} .badge{{fill:var(--wb-accent,currentColor)}}"
    "#{u} .badget{{fill:var(--wb-bg,#fff);font-size:10px;font-weight:700}}"
    "#{u} .hd{{fill:var(--wb-accent,currentColor);fill-opacity:.16}}"
    "#{u} .alt{{fill:currentColor;fill-opacity:.035}}"
    "#{u} .b{{font-weight:700}}"
    "#{u} .m{{fill-opacity:.72}}"
    "#{u} .s{{font-size:11px}}"
    "#{u} .ttl{{font-size:15px;font-weight:700}}"
)


class _Svg:
    """그릴 것을 모아 두었다가 전체 크기를 재서 한 장으로 닫는다."""

    def __init__(self, uid: str):
        self.uid = uid
        self.parts: list[str] = []
        self.x0 = self.y0 = float("inf")
        self.x1 = self.y1 = float("-inf")
        self.markers: dict[str, str] = {}
        self.title = ""        # 글쓴이가 붙인 제목(시퀀스의 title 줄) — 없으면 빈 글

    def box(self, x0, y0, x1, y1):
        self.x0 = min(self.x0, x0)
        self.y0 = min(self.y0, y0)
        self.x1 = max(self.x1, x1)
        self.y1 = max(self.y1, y1)

    def add(self, s: str, bbox=None):
        self.parts.append(s)
        if bbox:
            self.box(*bbox)

    def text(self, x, y, lines, cls="", anchor="middle", lh=LH, fs=FS, weight=None):
        """여러 줄 글자 — (x, y) 가 글 덩어리의 가운데."""
        lines = [ln for ln in lines]
        n = len(lines)
        top = y - (n - 1) * lh / 2
        c = f' class="{cls}"' if cls else ""
        wa = f' font-weight="{weight}"' if weight else ""
        for i, ln in enumerate(lines):
            self.parts.append(
                f'<text x="{_f(x)}" y="{_f(top + i * lh)}" text-anchor="{anchor}" '
                f'dominant-baseline="central"{c}{wa}>{_e(ln)}</text>')
        wmax = max((_tw(ln, fs) for ln in lines), default=0)
        if anchor == "middle":
            self.box(x - wmax / 2, top - lh / 2, x + wmax / 2, top + (n - 1) * lh + lh / 2)
        elif anchor == "start":
            self.box(x, top - lh / 2, x + wmax, top + (n - 1) * lh + lh / 2)
        else:
            self.box(x - wmax, top - lh / 2, x, top + (n - 1) * lh + lh / 2)

    def marker(self, name: str) -> str:
        mid = f"{self.uid}-{name}"
        if name not in self.markers:
            self.markers[name] = _MARKERS[name].format(id=mid)
        return f"url(#{mid})"

    def close(self, label: str, pad: float = 10) -> tuple[str, float, float]:
        if self.x0 == float("inf"):
            self.x0 = self.y0 = 0
            self.x1 = self.y1 = 10
        w = self.x1 - self.x0 + 2 * pad
        h = self.y1 - self.y0 + 2 * pad
        tx, ty = pad - self.x0, pad - self.y0
        style = _STYLE.format(u=self.uid)
        defs = "".join(self.markers.values())
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" id="{self.uid}" class="wb-svg" '
               f'viewBox="0 0 {_f(w)} {_f(h)}" width="{_f(w)}" height="{_f(h)}" role="img" '
               f'aria-label="{_e(label)}"><style>{style}</style>'
               + (f"<defs>{defs}</defs>" if defs else "")
               + f'<g transform="translate({_f(tx)},{_f(ty)})">' + "".join(self.parts) + "</g></svg>")
        return svg, w, h


_M = ('<marker id="{{id}}" viewBox="{vb}" refX="{rx}" refY="{ry}" markerWidth="{mw}" markerHeight="{mh}" '
      'markerUnits="userSpaceOnUse" orient="auto-start-reverse">{body}</marker>')
_MARKERS = {
    "arr": _M.format(vb="0 0 10 10", rx=9.5, ry=5, mw=10, mh=10, body='<path class="ah" d="M0,0 L10,5 L0,10 z"/>'),
    "open": _M.format(vb="0 0 10 10", rx=9.5, ry=5, mw=11, mh=11,
                      body='<path class="ax" d="M1,1 L9.5,5 L1,9"/>'),
    "cir": _M.format(vb="0 0 10 10", rx=9, ry=5, mw=10, mh=10, body='<circle class="ao" cx="5" cy="5" r="4"/>'),
    "crs": _M.format(vb="0 0 10 10", rx=6, ry=5, mw=11, mh=11,
                     body='<path class="ax" d="M2,2 L9,8 M9,2 L2,8"/>'),
    # ERD 개수 표시 — +x 가 표(상자) 쪽, 상자 경계가 x=18
    "one": _M.format(vb="0 -9 20 18", rx=18, ry=0, mw=20, mh=18,
                     body='<path class="ax" d="M9,-6 L9,6 M13,-6 L13,6"/>'),
    "zo": _M.format(vb="0 -9 20 18", rx=18, ry=0, mw=20, mh=18,
                    body='<path class="ax" d="M13,-6 L13,6"/><circle class="ao" cx="6" cy="0" r="3.5"/>'),
    "om": _M.format(vb="0 -9 20 18", rx=18, ry=0, mw=20, mh=18,
                    body='<path class="ax" d="M8,0 L18,-7 M8,0 L18,7 M8,0 L18,0 M5,-6 L5,6"/>'),
    "zm": _M.format(vb="0 -9 20 18", rx=18, ry=0, mw=20, mh=18,
                    body='<path class="ax" d="M10,0 L18,-7 M10,0 L18,7 M10,0 L18,0"/>'
                         '<circle class="ao" cx="5" cy="0" r="3.5"/>'),
}


# ─────────────────────────── 원문 다듬기 ───────────────────────────
def _lines(src: str) -> list[tuple[int, str]]:
    """(원문 줄 번호, 줄) — 앞머리(--- … ---) · %%{…}%% · %% 주석은 뺀다."""
    raw = str(src or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ").split("\n")
    out: list[tuple[int, str]] = []
    i = 0
    if raw and raw[0].strip() == "---":           # YAML 앞머리
        j = 1
        while j < len(raw) and raw[j].strip() != "---":
            j += 1
        i = j + 1 if j < len(raw) else 0
    for n in range(i, len(raw)):
        s = raw[n].strip()
        if not s or s.startswith("%%"):
            continue
        out.append((n + 1, s))
    return out


def _front_title(src: str) -> str:
    """앞머리(--- / title: … / ---)에 적힌 제목. 없으면 빈 글."""
    raw = str(src or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not raw or raw[0].strip() != "---":
        return ""
    for s in raw[1:]:
        if s.strip() == "---":
            break
        m = re.match(r"^\s*title\s*:\s*(.+?)\s*$", s)
        if m:
            return _clean(m.group(1).strip().strip('"').strip("'"))
    return ""


def detect_kind(src: str) -> str:
    """첫 줄로 종류를 가린다 → flowchart · sequence · er · state · (그 밖의 첫 낱말)."""
    ls = _lines(src)
    if not ls:
        return ""
    head = ls[0][1].split()[0] if ls[0][1].split() else ""
    low = head.lower()
    if low in ("flowchart", "graph", "flowchart-elk"):
        return "flowchart"
    if low == "sequencediagram":
        return "sequence"
    if low == "erdiagram":
        return "er"
    if low in ("statediagram", "statediagram-v2"):
        return "state"
    return head


# ═══════════════════════════ 층 쌓기 배치 (흐름도 · ERD · 상태도 공용) ═══════════════════════════
class _Graph:
    def __init__(self, direction: str = "TD"):
        d = (direction or "TD").upper()
        self.dir = "TD" if d == "TB" else d if d in ("TD", "BT", "LR", "RL") else "TD"
        self.nodes: dict[str, dict] = {}
        self.order: list[str] = []
        self.edges: list[dict] = []
        self.sgs: dict[str, dict] = {}
        self.sg_order: list[str] = []

    def node(self, nid: str, label=None, shape=None, sg=None) -> dict:
        n = self.nodes.get(nid)
        if n is None:
            if len(self.nodes) >= MAX_NODES:
                raise WbError(f"상자가 {MAX_NODES}개를 넘습니다 — 그림을 나눠 그려 주세요")
            n = {"id": nid, "label": nid, "shape": "rect", "sg": sg}
            self.nodes[nid] = n
            self.order.append(nid)
            if sg:
                self._join(nid, sg)
        if label is not None:
            n["label"] = label
        if shape is not None:
            n["shape"] = shape
        return n

    def _join(self, nid, sg):
        while sg:
            self.sgs[sg]["members"].add(nid)
            sg = self.sgs[sg]["parent"]

    def edge(self, u, v, **kw):
        if len(self.edges) >= MAX_EDGES:
            raise WbError(f"선이 {MAX_EDGES}개를 넘습니다 — 그림을 나눠 그려 주세요")
        e = {"u": u, "v": v, "label": "", "style": "solid", "head": "arr", "tail": None}
        e.update(kw)
        self.edges.append(e)
        return e

    def subgraph(self, sid, title, parent):
        if sid not in self.sgs:
            self.sgs[sid] = {"id": sid, "title": title, "parent": parent, "members": set()}
            self.sg_order.append(sid)
        return self.sgs[sid]

    def sg_path(self, nid) -> tuple:
        """바깥 묶음 → 안쪽 묶음 순서의 경로."""
        sg = self.nodes[nid].get("sg")
        path = []
        while sg:
            path.append(sg)
            sg = self.sgs[sg]["parent"]
        return tuple(reversed(path))


def _median(vals):
    vals = sorted(vals)
    n = len(vals)
    if not n:
        return None
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def _pava(t, w):
    """가중 등위 회귀 — 순서를 지키며 원하는 위치에 가장 가깝게."""
    blocks = []
    for ti, wi in zip(t, w):
        blocks.append([ti, wi, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, c2 = blocks.pop()
            v1, w1, c1 = blocks.pop()
            blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, c1 + c2])
    out = []
    for v, _w, c in blocks:
        out.extend([v] * c)
    return out


def _inversions(seq):
    n = 0
    for i in range(len(seq)):
        a = seq[i]
        for j in range(i + 1, len(seq)):
            if seq[j] < a:
                n += 1
    return n


def _layout(g: _Graph, rank_gap: float = 18.0, node_sep: float = 26.0):
    """층을 나눠 배치 → 상자 가운데 좌표 · 선의 점 목록 · 선 글자 자리."""
    ids = list(g.order)
    horiz = g.dir in ("LR", "RL")
    N = g.nodes

    def rs(n):
        return n["w"] if horiz else n["h"]

    def os_(n):
        return n["h"] if horiz else n["w"]

    edges = [(k, e) for k, e in enumerate(g.edges) if e["u"] != e["v"]]
    # ① 되돌아가는 선 찾기 (DFS) — 층을 매길 때만 뒤집는다
    indeg0 = {i: 0 for i in ids}
    succ = defaultdict(list)
    for k, e in edges:
        succ[e["u"]].append((e["v"], k))
        indeg0[e["v"]] += 1
    state, rev = {}, set()
    starts = [i for i in ids if indeg0[i] == 0] + [i for i in ids if indeg0[i] > 0]
    for s0 in starts:
        if s0 in state:
            continue
        state[s0] = 1
        stack = [(s0, iter(succ[s0]))]
        while stack:
            u, it = stack[-1]
            for v, k in it:
                st = state.get(v)
                if st == 1:
                    rev.add(k)
                    continue
                if st is None:
                    state[v] = 1
                    stack.append((v, iter(succ[v])))
                    break
            else:
                state[u] = 2
                stack.pop()
    L = []
    for k, e in edges:
        a, b = (e["v"], e["u"]) if k in rev else (e["u"], e["v"])
        L.append((a, b, k))
    # ② 층 (두 칸씩 — 가운데 칸에 선 글자가 선다)
    out, inn, deg = defaultdict(list), defaultdict(list), {i: 0 for i in ids}
    for a, b, k in L:
        out[a].append(b)
        inn[b].append(a)
        deg[b] += 1
    q = deque([i for i in ids if deg[i] == 0])
    topo = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in out[u]:
            deg[v] -= 1
            if deg[v] == 0:
                q.append(v)
    rank = {i: 0 for i in ids}
    for u in topo:
        for v in out[u]:
            rank[v] = max(rank[v], rank[u] + 2)
    for u in reversed(topo):                     # 시작 상자는 다음 상자 가까이로 내린다
        if not inn[u] and out[u]:
            rank[u] = max(rank[u], min(rank[v] for v in out[u]) - 2)
    # ③ 가짜 점(여러 층을 건너는 선) · 선 글자 점
    nodes_l: dict = {}
    for i in ids:
        nodes_l[i] = {"rank": rank[i], "os": os_(N[i]), "rs": rs(N[i]), "real": True,
                      "sgp": g.sg_path(i), "idx": ids.index(i)}
    pred_l, succ_l = defaultdict(list), defaultdict(list)
    chains = {}
    for a, b, k in L:
        e = g.edges[k]
        ra, rb = rank[a], rank[b]
        lab_rank = None
        if e.get("lw"):
            lab_rank = ra + 1 + 2 * ((rb - ra - 2) // 4)
        pa, pb = nodes_l[a]["sgp"], nodes_l[b]["sgp"]
        common = []
        for x, y in zip(pa, pb):
            if x != y:
                break
            common.append(x)
        chain = [a]
        for r in range(ra + 1, rb):
            key = ("d", k, r)
            lab = r == lab_rank
            if lab:
                o, t = (e["lh"], e["lw"]) if horiz else (e["lw"], e["lh"])
            else:
                o, t = 6.0, 0.0
            nodes_l[key] = {"rank": r, "os": o, "rs": t, "real": False, "label": lab, "edge": k,
                            "sgp": tuple(common), "idx": nodes_l[a]["idx"] + 0.001 * (k + 1)}
            chain.append(key)
        chain.append(b)
        chains[k] = chain
        for x, y in zip(chain, chain[1:]):
            succ_l[x].append(y)
            pred_l[y].append(x)
    # ★묶음(subgraph) 경계 — 층마다 왼쪽 · 오른쪽 경계점을 두고 위아래로 잇는다. 경계점도
    #   묶음 식구라 순서를 매길 때 식구 양 끝에 서고, 묶음 밖 상자는 그 바깥에 선다.
    #   (없을 때는 층마다 폭이 달라 묶음 상자 안에 남의 상자가 끼어 보였다.)
    for sid in g.sg_order:
        mem = [i for i in g.sgs[sid]["members"] if i in nodes_l]
        if not mem:
            continue
        r0 = min(nodes_l[i]["rank"] for i in mem)
        r1 = max(nodes_l[i]["rank"] for i in mem)
        path, p = [], sid
        while p:
            path.append(p)
            p = g.sgs[p]["parent"]
        path = tuple(reversed(path))
        first = min(nodes_l[i]["idx"] for i in mem)
        for side in ("bl", "br"):
            prev = None
            for r in range(r0, r1 + 1):
                key = (side, sid, r)
                nodes_l[key] = {"rank": r, "os": 1.0, "rs": 0.0, "real": False, "border": side, "sg": sid,
                                "sgp": path, "idx": first + (-0.0005 if side == "bl" else 0.4999)}
                if prev is not None:
                    succ_l[prev].append(key)
                    pred_l[key].append(prev)
                prev = key
    maxr = max((v["rank"] for v in nodes_l.values()), default=0)
    layers = [[] for _ in range(maxr + 1)]
    for key, v in nodes_l.items():
        layers[v["rank"]].append(key)
    for layer in layers:
        layer.sort(key=lambda kk: nodes_l[kk]["idx"])

    # ④ 순서 — 이웃 가운데값(barycenter)으로 몇 번 훑고, 엇갈림이 가장 적은 것
    def sort_grouped(items, bc, level=0, owner=None):
        groups, order_keys = {}, []
        for it in items:
            path = nodes_l[it]["sgp"]
            gk = ("sg", path[level]) if level < len(path) else ("n", it)
            if gk not in groups:
                groups[gk] = []
                order_keys.append(gk)
            groups[gk].append(it)
        def gval(gk):
            mem = groups[gk]
            return sum(bc[m] for m in mem) / len(mem)
        order_keys.sort(key=gval)
        res = []
        for gk in order_keys:
            mem = groups[gk]
            if gk[0] == "sg" and len(mem) > 1:
                res.extend(sort_grouped(mem, bc, level + 1, gk[1]))
            else:
                res.extend(sorted(mem, key=lambda m: bc[m]))
        if owner is not None:                    # 그 묶음의 경계점은 맨 앞 · 맨 뒤
            lb = [m for m in res if nodes_l[m].get("border") == "bl" and nodes_l[m].get("sg") == owner]
            rb = [m for m in res if nodes_l[m].get("border") == "br" and nodes_l[m].get("sg") == owner]
            res = lb + [m for m in res if m not in lb and m not in rb] + rb
        return res

    def crossings(lys):
        tot = 0
        for r in range(len(lys) - 1):
            pb = {kk: i for i, kk in enumerate(lys[r + 1])}
            segs = []
            for i, a in enumerate(lys[r]):
                for b in succ_l[a]:
                    if b in pb:
                        segs.append((i, pb[b]))
            segs.sort()
            tot += _inversions([s[1] for s in segs])
        return tot

    best = [list(ly) for ly in layers]
    best_c = crossings(best)
    for it in range(14):
        down = it % 2 == 0
        rng = range(1, len(layers)) if down else range(len(layers) - 2, -1, -1)
        for r in rng:
            ref = layers[r - 1] if down else layers[r + 1]
            pos = {kk: i for i, kk in enumerate(ref)}
            cur = layers[r]
            scale = len(ref) / max(len(cur), 1)
            bc = {}
            for i, kk in enumerate(cur):
                nb = pred_l[kk] if down else succ_l[kk]
                ps = [pos[x] for x in nb if x in pos]
                bc[kk] = sum(ps) / len(ps) if ps else i * scale
            layers[r] = sort_grouped(cur, bc)
        c = crossings(layers)
        if c < best_c:
            best_c, best = c, [list(ly) for ly in layers]
        if best_c == 0:
            break
    layers = best

    # ⑤ 가로 위치 — 이웃 가운데값에 맞추되 겹치지 않게 (가중 등위 회귀)
    def sep(a, b):
        va, vb = nodes_l[a], nodes_l[b]
        if va.get("border") or vb.get("border"):
            inside = va.get("border") == "bl" or vb.get("border") == "br" or va["sgp"] == vb["sgp"]
            if inside and horiz and va.get("border") == "bl":
                return 34.0                      # 가로 그림 — 묶음 제목이 위쪽에 선다
            return 12.0 if inside else 18.0
        if not va["real"] and not vb["real"]:
            s = 8.0
        elif not va["real"] or not vb["real"]:
            s = 14.0
        else:
            s = node_sep
        if va["sgp"] != vb["sgp"]:
            s += 16.0
        return s

    posx = {}
    for layer in layers:
        x = 0.0
        for i, kk in enumerate(layer):
            w = nodes_l[kk]["os"]
            if i == 0:
                x = w / 2
            else:
                p = layer[i - 1]
                x = posx[p] + nodes_l[p]["os"] / 2 + sep(p, kk) + w / 2
            posx[kk] = x
    for it in range(16):
        down = it % 2 == 0
        both = it >= 10
        rng = range(len(layers)) if down else range(len(layers) - 1, -1, -1)
        for r in rng:
            layer = layers[r]
            if not layer:
                continue
            desired, wts = [], []
            for kk in layer:
                nb = (pred_l[kk] + succ_l[kk]) if both else (pred_l[kk] if down else succ_l[kk])
                md = _median([posx[x] for x in nb])
                desired.append(posx[kk] if md is None else md)
                wts.append(2.0 if not nodes_l[kk]["real"] else 1.0)
            offs = [0.0]
            for a, b in zip(layer, layer[1:]):
                offs.append(offs[-1] + nodes_l[a]["os"] / 2 + sep(a, b) + nodes_l[b]["os"] / 2)
            ys = _pava([d - o for d, o in zip(desired, offs)], wts)
            for kk, y, o in zip(layer, ys, offs):
                posx[kk] = y + o
    # ⑤-2 묶음 밖 상자가 묶음 상자 안으로 들어오지 않게 — 층마다 경계 밖으로 민다
    #   (경계점은 층마다 따로 움직여서, 넓은 층의 경계로 그린 상자가 좁은 층의 이웃을 덮었다)
    def cluster_depth(sid):
        d, pp = 0, g.sgs[sid]["parent"]
        while pp:
            d, pp = d + 1, g.sgs[pp]["parent"]
        return d

    for sid in sorted(g.sg_order, key=cluster_depth, reverse=True):
        lefts = [posx[kk] for kk, v in nodes_l.items() if v.get("border") == "bl" and v.get("sg") == sid]
        rights = [posx[kk] for kk, v in nodes_l.items() if v.get("border") == "br" and v.get("sg") == sid]
        if not lefts:
            continue
        lo, hi = min(lefts), max(rights)
        for layer in layers:
            idx_l = [i for i, kk in enumerate(layer) if nodes_l[kk].get("border") == "bl" and nodes_l[kk].get("sg") == sid]
            idx_r = [i for i, kk in enumerate(layer) if nodes_l[kk].get("border") == "br" and nodes_l[kk].get("sg") == sid]
            if not idx_l or not idx_r:
                continue
            posx[layer[idx_l[0]]], posx[layer[idx_r[0]]] = lo, hi
            edge_ = hi
            for kk in layer[idx_r[0] + 1:]:
                need_ = edge_ + 18.0 + nodes_l[kk]["os"] / 2
                if posx[kk] < need_:
                    posx[kk] = need_
                edge_ = posx[kk] + nodes_l[kk]["os"] / 2
            edge_ = lo
            for kk in reversed(layer[:idx_l[0]]):
                need_ = edge_ - 18.0 - nodes_l[kk]["os"] / 2
                if posx[kk] > need_:
                    posx[kk] = need_
                edge_ = posx[kk] - nodes_l[kk]["os"] / 2
    # ⑥ 층의 두께 → 세로 위치 (묶음이 시작하는 층 앞엔 제목 칸, 끝나는 층 뒤엔 여백)
    thick = [max((nodes_l[kk]["rs"] for kk in layer), default=0.0) for layer in layers]
    extra_b, extra_a = defaultdict(float), defaultdict(float)
    for sid in g.sg_order:
        rr = [v["rank"] for v in nodes_l.values() if v.get("border") == "bl" and v.get("sg") == sid]
        if rr:
            extra_b[min(rr)] += 12.0 if horiz else 34.0
            extra_a[max(rr)] += 12.0
    cy, cur = [], 0.0
    for r in range(len(layers)):
        cur += extra_b[r]
        cy.append(cur + thick[r] / 2)
        cur += thick[r] + rank_gap + extra_a[r]
    total = cur

    def xy(key):
        o = posx[key]
        rr = cy[nodes_l[key]["rank"]]
        if horiz:
            x, y = rr, o
        else:
            x, y = o, rr
        if g.dir == "BT":
            y = total - y
        elif g.dir == "RL":
            x = total - x
        return x, y

    for i in ids:
        N[i]["x"], N[i]["y"] = xy(i)
    dmid, borders = {}, defaultdict(list)
    for key, v in nodes_l.items():
        if v.get("border"):
            borders[v["sg"]].append(xy(key))
        elif not v["real"]:
            dmid[key] = xy(key)
    g.border_pts = borders
    return {"chains": chains, "rev": rev, "dummies": dmid, "nodes_l": nodes_l, "horiz": horiz}


def _down(dirn):
    return {"TD": (0, 1), "BT": (0, -1), "LR": (1, 0), "RL": (-1, 0)}[dirn]


_ROUND_SHAPES = {"diamond", "circle", "dcircle", "start", "end", "choice"}


def _ports(g: _Graph, lay):
    """상자에서 선이 나가고 들어오는 자리 — 여러 선이면 변을 따라 나란히 벌린다."""
    dx, dy = _down(g.dir)
    horiz = lay["horiz"]
    outs, ins = defaultdict(list), defaultdict(list)
    for k, chain in lay["chains"].items():
        a, b = chain[0], chain[-1]
        nxt = chain[1]
        prv = chain[-2]
        pn = lay["dummies"].get(nxt) or (g.nodes[nxt]["x"], g.nodes[nxt]["y"])
        pp = lay["dummies"].get(prv) or (g.nodes[prv]["x"], g.nodes[prv]["y"])
        outs[a].append((pn[1] if horiz else pn[0], k))
        ins[b].append((pp[1] if horiz else pp[0], k))
    port = {}

    def place(nid, lst, sign):
        n = g.nodes[nid]
        lst.sort()
        m = len(lst)
        ext = (n["h"] if horiz else n["w"])
        step = 0 if (m < 2 or n["shape"] in _ROUND_SHAPES) else min(16.0, ext * 0.62 / (m - 1))
        for i, (_c, k) in enumerate(lst):
            off = (i - (m - 1) / 2) * step
            half = (n["w"] if horiz else n["h"]) / 2
            if horiz:
                x = n["x"] + sign * dx * half
                y = n["y"] + off
            else:
                x = n["x"] + off
                y = n["y"] + sign * dy * half
            port[(nid, k, sign)] = (x, y)

    for nid, lst in outs.items():
        place(nid, lst, +1)
    for nid, lst in ins.items():
        place(nid, lst, -1)
    return port


def _curve(pts, horiz):
    """점들을 층 방향으로 부드럽게 잇는다 (S자 곡선)."""
    d = f"M{_f(pts[0][0])},{_f(pts[0][1])}"
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs((y2 - y1) if horiz else (x2 - x1)) < 10:     # 거의 나란하면 곧은 선 — 작은 S자 흔들림이 없게
            d += f" L{_f(x2)},{_f(y2)}"
        elif horiz:
            mx = (x1 + x2) / 2
            d += f" C{_f(mx)},{_f(y1)} {_f(mx)},{_f(y2)} {_f(x2)},{_f(y2)}"
        else:
            my = (y1 + y2) / 2
            d += f" C{_f(x1)},{_f(my)} {_f(x2)},{_f(my)} {_f(x2)},{_f(y2)}"
    return d


def _straighten(pts, horiz, tol=8.0):
    """가운데 점(층 사이 빈 자리)이 양옆을 잇는 곧은 선에서 몇 px 만 비켜 있으면 선 위로 옮긴다.
    그대로 두면 거의 나란한 두 상자 사이 선이 작은 V 자로 꺾여 보인다."""
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = out[-1], pts[i], pts[i + 1]
        if horiz:
            want = y0 + (y2 - y0) * ((x1 - x0) / (x2 - x0) if x2 != x0 else 0.5)
            if abs(y1 - want) < tol:
                y1 = want
        else:
            want = x0 + (x2 - x0) * ((y1 - y0) / (y2 - y0) if y2 != y0 else 0.5)
            if abs(x1 - want) < tol:
                x1 = want
        out.append((x1, y1))
    out.append(pts[-1])
    return out


def _edge_paths(g: _Graph, lay, sv: _Svg, er=False):
    """선 · 화살촉 · 선 글자를 그린다."""
    horiz = lay["horiz"]
    port = _ports(g, lay)
    labels = []
    for k, chain in lay["chains"].items():
        e = g.edges[k]
        if e.get("style") == "invisible":
            continue
        a, b = chain[0], chain[-1]
        pts = _straighten([port[(a, k, +1)]] + [lay["dummies"][c] for c in chain[1:-1]] + [port[(b, k, -1)]],
                          horiz)
        along = pts                               # 층 순서 그대로 (선 글자 자리를 찾을 때)
        head, tail = e.get("head"), e.get("tail")
        if k in lay["rev"]:                       # 되돌아가는 선은 원래 방향으로
            pts = list(reversed(pts))
        cls = "e" + (" d" if e["style"] == "dotted" else " k" if e["style"] == "thick" else "")
        mk = ""
        if head:
            mk += f' marker-end="{sv.marker(head)}"'
        if tail:
            mk += f' marker-start="{sv.marker(tail)}"'
        sv.add(f'<path class="{cls}" d="{_curve(pts, horiz)}"{mk}/>',
               (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts)))
        if e.get("lw"):
            lab = [i for i, c in enumerate(chain[1:-1], 1) if lay["nodes_l"][c].get("label")]
            if lab:
                lx, ly = along[lab[0]]
            else:
                lx, ly = pts[len(pts) // 2]
            labels.append((lx, ly, e))
    for lx, ly, e in labels:                      # 글자는 선 위에 — 나중에 그린다
        w, h = e["lw"], e["lh"]
        sv.add(f'<rect class="lb" x="{_f(lx - w / 2)}" y="{_f(ly - h / 2)}" width="{_f(w)}" '
               f'height="{_f(h)}" rx="3"/>', (lx - w / 2, ly - h / 2, lx + w / 2, ly + h / 2))
        sv.text(lx, ly, e["llines"], cls="lt", lh=LH_S, fs=FS_S)
    # 제 자리로 돌아오는 선
    for e in g.edges:
        if e["u"] != e["v"] or e.get("style") == "invisible":
            continue
        n = g.nodes[e["u"]]
        cls = "e" + (" d" if e["style"] == "dotted" else " k" if e["style"] == "thick" else "")
        mk = f' marker-end="{sv.marker(e["head"])}"' if e.get("head") else ""
        if horiz:
            x, y = n["x"], n["y"] + n["h"] / 2
            d = (f"M{_f(x - 8)},{_f(y)} C{_f(x - 22)},{_f(y + 32)} {_f(x + 22)},{_f(y + 32)} "
                 f"{_f(x + 8)},{_f(y)}")
            sv.add(f'<path class="{cls}" d="{d}"{mk}/>', (x - 24, y, x + 24, y + 34))
            if e.get("lw"):
                sv.text(x, y + 44, e["llines"], cls="lt", lh=LH_S, fs=FS_S)
        else:
            x, y = n["x"] + n["w"] / 2, n["y"]
            d = (f"M{_f(x)},{_f(y - 8)} C{_f(x + 34)},{_f(y - 24)} {_f(x + 34)},{_f(y + 24)} "
                 f"{_f(x)},{_f(y + 8)}")
            sv.add(f'<path class="{cls}" d="{d}"{mk}/>', (x, y - 24, x + 36, y + 24))
            if e.get("lw"):
                sv.text(x + 40, y, e["llines"], cls="lt", anchor="start", lh=LH_S, fs=FS_S)


def _subgraph_boxes(g: _Graph, sv: _Svg, title_attr="title"):
    """묶음 상자 — 안쪽 묶음부터 재서 바깥 묶음이 감싸게."""
    boxes = {}

    def depth(s):
        d, p = 0, g.sgs[s]["parent"]
        while p:
            d, p = d + 1, g.sgs[p]["parent"]
        return d

    for sid in sorted(g.sg_order, key=depth, reverse=True):
        sg = g.sgs[sid]
        xs0, ys0, xs1, ys1 = [], [], [], []
        for m in sg["members"]:
            n = g.nodes[m]
            xs0.append(n["x"] - n["w"] / 2)
            ys0.append(n["y"] - n["h"] / 2)
            xs1.append(n["x"] + n["w"] / 2)
            ys1.append(n["y"] + n["h"] / 2)
        for cid, cb in boxes.items():
            if g.sgs[cid]["parent"] == sid:
                xs0.append(cb[0])
                ys0.append(cb[1])
                xs1.append(cb[2])
                ys1.append(cb[3])
        if not xs0:
            continue
        bp = getattr(g, "border_pts", {}).get(sid)
        if bp:                                   # 경계점이 정한 폭 (층 방향 쪽은 식구 크기로)
            if g.dir in ("LR", "RL"):
                ys0.append(min(p[1] for p in bp) + 12)
                ys1.append(max(p[1] for p in bp) - 12)
            else:
                xs0.append(min(p[0] for p in bp) + 12)
                xs1.append(max(p[0] for p in bp) - 12)
        pad, top = 12.0, 22.0
        title = sg.get(title_attr) or ""
        x0, y0 = min(xs0) - pad, min(ys0) - pad - (top if title else 0)
        x1, y1 = max(xs1) + pad, max(ys1) + pad
        tw = _tw(title, 12) + 20
        if x1 - x0 < tw:
            x1 = x0 + tw
        boxes[sid] = (x0, y0, x1, y1)
    out = []
    for sid in sorted(boxes, key=depth):
        x0, y0, x1, y1 = boxes[sid]
        title = g.sgs[sid].get(title_attr) or ""
        s = (f'<rect class="sg" x="{_f(x0)}" y="{_f(y0)}" width="{_f(x1 - x0)}" height="{_f(y1 - y0)}" rx="8"/>')
        if title:
            s += (f'<text class="sgt" x="{_f(x0 + 10)}" y="{_f(y0 + 13)}" dominant-baseline="central">'
                  f'{_e(title)}</text>')
        out.append(s)
        sv.box(x0, y0, x1, y1)
    return out


# ═══════════════════════════ 흐름도 ═══════════════════════════
_IDC = "A-Za-z0-9_\u0080-￿"
_ID_RE = re.compile(rf"[{_IDC}](?:[{_IDC}]|[-.](?=[{_IDC}]))*")
_SHAPES = [
    ("(((", ")))", "dcircle"), ("((", "))", "circle"), ("([", "])", "stadium"), ("[[", "]]", "subroutine"),
    ("[(", ")]", "cyl"), ("{{", "}}", "hex"), ("[/", "/]", "para"), ("[/", "\\]", "trap"),
    ("[\\", "\\]", "para2"), ("[\\", "/]", "trap2"), ("(", ")", "round"), ("[", "]", "rect"),
    ("{", "}", "diamond"), (">", "]", "asym"),
]
_LINK_MID = re.compile(
    r"(?P<l>[<ox])?(?P<open>--|==|-\.)(?![-=>.])\s*(?P<txt>[^|]+?)\s*"
    r"(?P<close>-{2,}[>ox]|={2,}[>ox]|\.-+[>ox]|-{3,}|={3,}|\.-+)(?=\s|$|[" + _IDC + r"])")
# 끝 화살촉: '>' 는 바로 뒤에 이름이 붙어도(A-->B) 화살촉이다. o·x 는 이름 글자와 헷갈리므로
#   뒤에 이름 글자가 없을 때만 (A --o B · A --x B).
_LINK = re.compile(r"(?P<l>[<ox])?(?P<body>-{2,}|={2,}|-\.+-|~{3,})(?P<r>>|[ox](?![" + _IDC + r"]))?")
_PIPE = re.compile(r"\s*\|(?P<lab>[^|]*)\|")


def _split_stmts(line: str) -> list[str]:
    out, cur, depth, quote = [], [], 0, False
    for ch in line:
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            elif ch == ";" and depth == 0:
                out.append("".join(cur))
                cur = []
                continue
        cur.append(ch)
    out.append("".join(cur))
    return [s for s in (x.strip() for x in out) if s]


def _parse_shape(s: str, i: int, ln: int):
    for op, cl, shape in _SHAPES:
        if not s.startswith(op, i):
            continue
        j = i + len(op)
        k = j
        while k < len(s) and s[k] == " ":
            k += 1
        if k < len(s) and s[k] == '"':
            q = s.find('"', k + 1)
            if q < 0:
                raise WbError('따옴표(")가 닫히지 않았습니다', ln)
            text = s[k + 1:q]
            end = s.find(cl, q + 1)
            if end < 0 or s[q + 1:end].strip():
                continue
        else:
            end = s.find(cl, j)
            if end < 0:
                continue
            text = s[j:end]
        # "[/" 는 "/]"(평행사변형) 과 "\\]"(사다리꼴) 둘 다 될 수 있다 — 먼저 닫히는 쪽
        if op in ("[/", "[\\"):
            alt = [(c2, sh2) for op2, c2, sh2 in _SHAPES if op2 == op and c2 != cl]
            for c2, sh2 in alt:
                e2 = s.find(c2, j)
                if 0 <= e2 < end:
                    end, cl, shape = e2, c2, sh2
                    text = s[j:end].strip().strip('"')
        return _clean(text), shape, end + len(cl)
    return None, None, i


# Mermaid v11 새 문법: A@{ shape: diam, label: "판단" } — 모양 이름을 가진 모양 중 가까운 것으로
_AT_SHAPE = {
    "rounded": "round", "event": "round",
    "stadium": "stadium", "pill": "stadium", "terminal": "stadium",
    "fr-rect": "subroutine", "framed-rectangle": "subroutine", "subproc": "subroutine",
    "subprocess": "subroutine", "subroutine": "subroutine",
    "cyl": "cyl", "cylinder": "cyl", "database": "cyl", "db": "cyl", "h-cyl": "cyl", "das": "cyl",
    "horizontal-cylinder": "cyl", "lin-cyl": "cyl", "disk": "cyl", "lined-cylinder": "cyl",
    "circle": "circle", "circ": "circle", "sm-circ": "circle", "small-circle": "circle", "start": "circle",
    "f-circ": "circle", "filled-circle": "circle", "junction": "circle", "cross-circ": "circle",
    "crossed-circle": "circle", "summary": "circle",
    "dbl-circ": "dcircle", "double-circle": "dcircle", "fr-circ": "dcircle", "framed-circle": "dcircle",
    "stop": "dcircle",
    "diam": "diamond", "diamond": "diamond", "decision": "diamond", "question": "diamond",
    "hex": "hex", "hexagon": "hex", "prepare": "hex",
    "lean-r": "para", "lean-right": "para", "in-out": "para",
    "lean-l": "para2", "lean-left": "para2", "out-in": "para2",
    "trap-b": "trap", "trapezoid": "trap", "trapezoid-bottom": "trap", "priority": "trap",
    "trap-t": "trap2", "trapezoid-top": "trap2", "inv-trapezoid": "trap2", "manual": "trap2",
    "odd": "asym",
}
_AT_KEY = re.compile(r'(?P<k>shape|label)\s*:\s*(?:"(?P<q>(?:[^"\\]|\\.)*)"|(?P<v>[^,}]+))', re.I)
_EDGE_ID = re.compile(r"\s*[A-Za-z_][\w-]*@(?=[-=.<~])")


def _parse_at(s: str, i: int, ln: int):
    """i 가 '@{' 를 가리킬 때 → (글, 모양, 다음 자리). 닫는 '}' 는 따옴표 밖의 것."""
    j, quote = i + 2, False
    while j < len(s):
        if s[j] == '"' and s[j - 1] != "\\":
            quote = not quote
        elif s[j] == "}" and not quote:
            break
        j += 1
    if j >= len(s):
        raise WbError("'@{' 를 닫는 '}' 가 없습니다", ln)
    label, shape = None, "rect"
    for m in _AT_KEY.finditer(s[i + 2:j]):
        val = m.group("q") if m.group("q") is not None else (m.group("v") or "").strip()
        if m.group("k").lower() == "shape":
            shape = _AT_SHAPE.get(val.lower(), "rect")
        else:
            label = _clean(val.replace('\\"', '"'))
    return label, shape, j + 1


def _parse_link(s: str, i: int, ln: int):
    m = _LINK_MID.match(s, i)
    if m:
        close = m.group("close")
        style = "thick" if "=" in m.group("open") else "dotted" if "." in m.group("open") else "solid"
        head = {">": "arr", "o": "cir", "x": "crs"}.get(close[-1])
        tail = {"<": "arr", "o": "cir", "x": "crs"}.get(m.group("l") or "")
        return {"style": style, "head": head, "tail": tail,
                "label": _clean(m.group("txt").strip().strip('"'))}, m.end()
    m = _LINK.match(s, i)
    if not m:
        raise WbError(f"선(-->, ---, -.->, ==>)이 와야 할 자리입니다: {s[i:i + 24]!r}", ln)
    body = m.group("body")
    style = ("invisible" if body.startswith("~") else "thick" if "=" in body
             else "dotted" if "." in body else "solid")
    head = {">": "arr", "o": "cir", "x": "crs"}.get(m.group("r") or "")
    tail = {"<": "arr", "o": "cir", "x": "crs"}.get(m.group("l") or "")
    j = m.end()
    label = ""
    p = _PIPE.match(s, j)
    if p:
        label = _clean(p.group("lab").strip().strip('"'))
        j = p.end()
    return {"style": style, "head": head, "tail": tail, "label": label}, j


def _parse_chain(g: _Graph, s: str, ln: int, cur_sg):
    i, n = 0, len(s)
    groups, links = [], []
    while True:
        grp = []
        while True:
            while i < n and s[i] == " ":
                i += 1
            m = _ID_RE.match(s, i)
            if not m:
                raise WbError(f"상자 이름이 와야 할 자리입니다: {s[i:i + 24]!r}", ln)
            nid = m.group(0)
            i = m.end()
            if s.startswith(":::", i):
                j = i + 3
                while j < n and (s[j].isalnum() or s[j] in "_-"):
                    j += 1
                i = j
            label, shape, i = _parse_shape(s, i, ln)
            if shape is None and s.startswith("@{", i):
                label, shape, i = _parse_at(s, i, ln)
            if nid in g.sgs and label is None:
                grp.append(("sg", nid))
            else:
                g.node(nid, label, shape, cur_sg)
                grp.append(nid)
            if s.startswith(":::", i):
                j = i + 3
                while j < n and (s[j].isalnum() or s[j] in "_-"):
                    j += 1
                i = j
            j = i
            while j < n and s[j] == " ":
                j += 1
            if j < n and s[j] == "&":
                i = j + 1
                continue
            i = j
            break
        groups.append(grp)
        if i >= n:
            break
        m_id = _EDGE_ID.match(s, i)             # 선 이름(e1@-->)은 그림에 쓰지 않는다
        if m_id:
            i = m_id.end()
        link, i = _parse_link(s, i, ln)
        links.append(link)
        while i < n and s[i] == " ":
            i += 1
        if i >= n:
            raise WbError("선 끝에 이어질 상자가 없습니다", ln)

    def real(x):
        if isinstance(x, tuple):                 # 묶음으로 잇는 선 → 그 묶음의 첫 상자
            mem = [m for m in g.order if m in g.sgs[x[1]]["members"]]
            return mem[0] if mem else None
        return x

    for gi, link in enumerate(links):
        for a in groups[gi]:
            for b in groups[gi + 1]:
                ra, rb = real(a), real(b)
                if ra and rb:
                    g.edge(ra, rb, **link)


def _size_flow_node(n):
    lines = _wrap(n["label"], 200)
    tw = max(_tw(x) for x in lines)
    th = len(lines) * LH
    sh = n["shape"]
    if sh == "circle":
        w = h = max(max(tw, th) + 26, 46)
    elif sh == "dcircle":
        w = h = max(max(tw, th) + 34, 54)
    elif sh == "diamond":
        w = tw * 1.5 + 30
        h = max(46.0, th / max(0.25, 1 - tw / w) + 12)
    elif sh == "hex":
        w, h = tw + 46, th + 22
    elif sh in ("para", "para2", "trap", "trap2"):
        w, h = tw + 52, th + 20
    elif sh == "cyl":
        w, h = tw + 30, th + 36
    elif sh == "stadium":
        w, h = tw + th + 30, th + 18
    elif sh in ("subroutine", "asym"):
        w, h = tw + 42, th + 18
    else:
        w, h = tw + 30, th + 18
    n["lines"] = lines
    n["w"] = max(w, 56.0)
    n["h"] = max(h, 36.0)


def _draw_node(sv: _Svg, n):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
    sh = n["shape"]
    P = lambda pts: " ".join(f"{_f(a)},{_f(b)}" for a, b in pts)
    if sh == "circle":
        s = f'<circle class="n" cx="{_f(x)}" cy="{_f(y)}" r="{_f(w / 2)}"/>'
    elif sh == "dcircle":
        s = (f'<circle class="n" cx="{_f(x)}" cy="{_f(y)}" r="{_f(w / 2)}"/>'
             f'<circle class="n2" cx="{_f(x)}" cy="{_f(y)}" r="{_f(w / 2 - 5)}"/>')
    elif sh == "diamond":
        s = f'<polygon class="n" points="{P([(x, y0), (x1, y), (x, y1), (x0, y)])}"/>'
    elif sh == "hex":
        c = min(h / 2, 14)
        s = f'<polygon class="n" points="{P([(x0 + c, y0), (x1 - c, y0), (x1, y), (x1 - c, y1), (x0 + c, y1), (x0, y)])}"/>'
    elif sh in ("para", "para2", "trap", "trap2"):
        c = min(h / 2, 16)
        pts = {"para": [(x0 + c, y0), (x1, y0), (x1 - c, y1), (x0, y1)],
               "para2": [(x0, y0), (x1 - c, y0), (x1, y1), (x0 + c, y1)],
               "trap": [(x0 + c, y0), (x1 - c, y0), (x1, y1), (x0, y1)],
               "trap2": [(x0, y0), (x1, y0), (x1 - c, y1), (x0 + c, y1)]}[sh]
        s = f'<polygon class="n" points="{P(pts)}"/>'
    elif sh == "cyl":
        ry = min(8.0, h / 6)
        s = (f'<path class="n" d="M{_f(x0)},{_f(y0 + ry)} A{_f(w / 2)},{_f(ry)} 0 0 1 {_f(x1)},{_f(y0 + ry)} '
             f'L{_f(x1)},{_f(y1 - ry)} A{_f(w / 2)},{_f(ry)} 0 0 1 {_f(x0)},{_f(y1 - ry)} Z"/>'
             f'<path class="n2" d="M{_f(x0)},{_f(y0 + ry)} A{_f(w / 2)},{_f(ry)} 0 0 0 {_f(x1)},{_f(y0 + ry)}"/>')
        y = y + ry / 2
    elif sh == "subroutine":
        s = (f'<rect class="n" x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" rx="2"/>'
             f'<path class="n2" d="M{_f(x0 + 7)},{_f(y0)} L{_f(x0 + 7)},{_f(y1)} M{_f(x1 - 7)},{_f(y0)} L{_f(x1 - 7)},{_f(y1)}"/>')
    elif sh == "asym":
        c = min(h / 2, 12)
        s = f'<polygon class="n" points="{P([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0 + c, y)])}"/>'
        x = x + c / 2
    else:
        rx = {"round": 10, "stadium": h / 2}.get(sh, 4)
        s = f'<rect class="n" x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" rx="{_f(rx)}"/>'
    sv.add(s, (x0, y0, x1, y1))
    sv.text(x, y, n["lines"])


def _label_size(e):
    if e.get("label"):
        lines = _wrap(e["label"], 170, FS_S)
        e["llines"] = lines
        e["lw"] = max(_tw(x, FS_S) for x in lines) + 12
        e["lh"] = len(lines) * LH_S + 6
    else:
        e["lw"] = 0


def _render_flow(ls, uid):
    head = ls[0][1].split()
    g = _Graph(head[1] if len(head) > 1 else "TD")
    sg_stack: list[str] = []
    for ln, line in ls[1:]:
        for st in _split_stmts(line):
            low = st.lower()
            if low.startswith(("classdef ", "class ", "style ", "linkstyle ", "click ", "acctitle",
                               "accdescr", "direction ")):
                continue
            if low == "end":
                if not sg_stack:
                    raise WbError("'end' 가 짝이 되는 'subgraph' 없이 나왔습니다", ln)
                sg_stack.pop()
                continue
            if low.startswith("subgraph"):
                rest = st[8:].strip()
                m = re.match(r'^(?P<id>[^\s\["]+)\s*\[\s*"?(?P<t>[^"\]]*)"?\s*\]\s*$', rest)
                if m:
                    sid, title = m.group("id"), _clean(m.group("t"))
                else:
                    m2 = re.match(r'^"(?P<t>[^"]*)"\s*$', rest)
                    title = _clean(m2.group("t")) if m2 else _clean(rest)
                    sid = rest or f"__sg{len(g.sgs)}"
                g.subgraph(sid, title, sg_stack[-1] if sg_stack else None)
                sg_stack.append(sid)
                continue
            _parse_chain(g, st, ln, sg_stack[-1] if sg_stack else None)
    if sg_stack:
        raise WbError(f"'subgraph {sg_stack[-1]}' 를 닫는 'end' 가 없습니다", ls[-1][0])
    if not g.nodes:
        raise WbError("그릴 상자가 없습니다", ls[0][0])
    for n in g.nodes.values():
        _size_flow_node(n)
    for e in g.edges:
        _label_size(e)
    lay = _layout(g, rank_gap=22.0 if g.sgs else 18.0)
    sv = _Svg(uid)
    for s in _subgraph_boxes(g, sv):
        sv.add(s)
    _edge_paths(g, lay, sv)
    for nid in g.order:
        _draw_node(sv, g.nodes[nid])
    return sv, f"흐름도 — 상자 {len(g.nodes)}개 · 선 {len(g.edges)}개"


# ═══════════════════════════ 시퀀스 ═══════════════════════════
_SEQ_MSG = re.compile(
    r"^(?P<a>[^:]+?)\s*(?P<arr><<-->>|<<->>|-->>|->>|--x|-x|--\)|-\)|-->|->)\s*(?P<act>[+-]?)\s*"
    r"(?P<b>[^:]+?)\s*(?::\s?(?P<t>.*))?$")
_SEQ_ARR = {"->>": ("solid", "arr", None), "-->>": ("dotted", "arr", None), "->": ("solid", None, None),
            "-->": ("dotted", None, None), "-x": ("solid", "crs", None), "--x": ("dotted", "crs", None),
            "-)": ("solid", "open", None), "--)": ("dotted", "open", None),
            "<<->>": ("solid", "arr", "arr"), "<<-->>": ("dotted", "arr", "arr")}
_SEQ_PART = re.compile(r"^(?:create\s+)?(?P<k>participant|actor)\s+(?P<id>.+?)(?:\s+as\s+(?P<al>.+))?$", re.I)
_SEQ_NOTE = re.compile(r"^note\s+(?P<pos>left of|right of|over)\s+(?P<ps>[^:]+?)\s*:\s*(?P<t>.*)$", re.I)
_SEQ_BLOCK = re.compile(r"^(?P<k>loop|alt|opt|par|critical|break|rect|box)\b\s*(?P<t>.*)$", re.I)
_SEQ_ELSE = re.compile(r"^(?P<k>else|and|option)\b\s*(?P<t>.*)$", re.I)


def _render_seq(ls, uid):
    parts: list[str] = []
    plabel: dict[str, str] = {}
    pkind: dict[str, str] = {}
    events: list[tuple] = []
    auto = False
    title = ""
    stack: list[str] = []

    def part(pid, kind="participant", label=None):
        pid = pid.strip().strip('"')
        if pid not in plabel:
            parts.append(pid)
            plabel[pid] = pid
            pkind[pid] = kind
        if label is not None:
            plabel[pid] = _clean(label.strip().strip('"'))
        return pid

    for ln, st in ls[1:]:
        low = st.lower()
        if low == "autonumber" or low.startswith("autonumber "):
            auto = True
            continue
        if low.startswith(("activate ", "deactivate ", "destroy ", "links ", "link ", "properties ",
                           "details ")):
            continue
        m = re.match(r"^title\s*:?\s*(.*)$", st, re.I)
        if m:
            title = _clean(m.group(1))
            continue
        m = _SEQ_PART.match(st)
        if m:
            part(m.group("id"), m.group("k").lower(), m.group("al"))
            continue
        m = _SEQ_NOTE.match(st)
        if m:
            ps = [part(p) for p in m.group("ps").split(",") if p.strip()]
            events.append(("note", m.group("pos").lower(), ps, _clean(m.group("t")), ln))
            continue
        if low == "end":
            if not stack:
                raise WbError("'end' 가 짝이 되는 loop/alt/opt 없이 나왔습니다", ln)
            kind = stack.pop()
            if kind != "box":
                events.append(("end", ln))
            continue
        m = _SEQ_BLOCK.match(st)
        if m:
            k = m.group("k").lower()
            stack.append(k)
            if k != "box":
                events.append(("block", k, "" if k == "rect" else _clean(m.group("t")), ln))
            continue
        m = _SEQ_ELSE.match(st)
        if m:
            events.append(("else", m.group("k").lower(), _clean(m.group("t")), ln))
            continue
        m = _SEQ_MSG.match(st)
        if m:
            a, b = part(m.group("a")), part(m.group("b"))
            style, head, tail = _SEQ_ARR[m.group("arr")]
            events.append(("msg", a, b, style, head, tail, _clean(m.group("t") or ""), ln))
            continue
        raise WbError(f"이 줄을 읽지 못했습니다: {st[:40]!r}", ln)
    if stack:
        raise WbError(f"'{stack[-1]}' 를 닫는 'end' 가 없습니다", ls[-1][0])
    if len(events) > MAX_EVENTS:
        raise WbError(f"메시지가 {MAX_EVENTS}개를 넘습니다 — 나눠 그려 주세요")
    if not parts:
        raise WbError("참가자가 없습니다", ls[0][0])

    idx = {p: i for i, p in enumerate(parts)}
    np_ = len(parts)
    bw, blines = [], []
    for p in parts:
        lines = _wrap(plabel[p], 240)
        blines.append(lines)
        bw.append(max(92.0, max(_tw(x) for x in lines) + 26))
    bh = max(38.0, max(len(x) for x in blines) * LH + 18)
    actor_h = 34.0 if any(pkind[p] == "actor" for p in parts) else 0.0
    gaps = [34.0] * max(np_ - 1, 0)
    right_extra = 0.0
    need: list[tuple[int, int, float]] = []
    for ev in events:
        if ev[0] == "msg":
            _, a, b, _s, _h, _t, text, _ln = ev
            lw = max((_tw(x, FS_S) for x in _wrap(text, 320, FS_S)), default=0)
            ia, ib = idx[a], idx[b]
            if ia == ib:
                if ia < np_ - 1:
                    need.append((ia, ia + 1, 44 + lw + 16 + bw[ia + 1] / 2))
                else:
                    right_extra = max(right_extra, 44 + lw + 10)
            else:
                need.append((min(ia, ib), max(ia, ib), lw + 40))
        elif ev[0] == "note":
            _, pos, ps, text, _ln = ev
            nw = max(_tw(x, FS_S) for x in _wrap(text, 240, FS_S)) + 20
            i0 = idx[ps[0]]
            if pos == "right of":
                if i0 < np_ - 1:
                    need.append((i0, i0 + 1, nw + 24))
                else:
                    right_extra = max(right_extra, nw + 20)
            elif pos == "left of":
                if i0 > 0:
                    need.append((i0 - 1, i0, nw + 20))
            elif len(ps) > 1:
                i1 = idx[ps[-1]]
                if i1 != i0:
                    need.append((min(i0, i1), max(i0, i1), nw - 30))
    need.sort(key=lambda t: t[1] - t[0])
    for _ in range(3):
        for i, j, dist in need:
            cx = [0.0]
            for k in range(np_ - 1):
                cx.append(cx[-1] + bw[k] / 2 + gaps[k] + bw[k + 1] / 2)
            if cx[j] - cx[i] < dist:
                gaps[j - 1] += dist - (cx[j] - cx[i])
    cx = [bw[0] / 2]
    for k in range(np_ - 1):
        cx.append(cx[-1] + bw[k] / 2 + gaps[k] + bw[k + 1] / 2)

    sv = _Svg(uid)
    top = 0.0
    if title:
        sv.text((cx[0] + cx[-1]) / 2, 8, [title], cls="ttl", fs=15)
        top = 30.0
    head_y = top + actor_h
    fronts: list[str] = []            # 틀(뒤에 깔림)
    mids: list[str] = []              # 메시지 · 메모

    def draw_parts(y_top):
        for i, p in enumerate(parts):
            x = cx[i]
            if pkind[p] == "actor":
                hy = y_top - actor_h + 7
                mids.append(f'<circle class="n" cx="{_f(x)}" cy="{_f(hy)}" r="7"/>'
                            f'<path class="n2" d="M{_f(x)},{_f(hy + 7)} L{_f(x)},{_f(hy + 19)} '
                            f'M{_f(x - 10)},{_f(hy + 11)} L{_f(x + 10)},{_f(hy + 11)} '
                            f'M{_f(x)},{_f(hy + 19)} L{_f(x - 8)},{_f(hy + 27)} M{_f(x)},{_f(hy + 19)} '
                            f'L{_f(x + 8)},{_f(hy + 27)}"/>')
                sv.box(x - 10, hy - 7, x + 10, hy + 27)
            mids.append(f'<rect class="n" x="{_f(x - bw[i] / 2)}" y="{_f(y_top)}" width="{_f(bw[i])}" '
                        f'height="{_f(bh)}" rx="4"/>')
            sv.box(x - bw[i] / 2, y_top, x + bw[i] / 2, y_top + bh)

    draw_parts(head_y)
    y = head_y + bh + 22
    num = 0
    blocks: list[dict] = []           # 열린 틀
    ext_stack: list[list[float]] = []

    def grow(x0, x1):
        for ex in ext_stack:
            ex[0] = min(ex[0], x0)
            ex[1] = max(ex[1], x1)

    texts_after: list[tuple] = []
    for ev in events:
        if ev[0] == "msg":
            _, a, b, style, headm, tailm, text, _ln = ev
            ia, ib = idx[a], idx[b]
            xa, xb = cx[ia], cx[ib]
            lines = _wrap(text, 320, FS_S) if text else []
            th = len(lines) * LH_S
            cls = "e" + (" d" if style == "dotted" else "")
            mk = (f' marker-end="{sv.marker(headm)}"' if headm else "") + \
                 (f' marker-start="{sv.marker(tailm)}"' if tailm else "")
            if ia == ib:
                ay = y + max(th, 0) + 6
                d = (f"M{_f(xa)},{_f(ay)} C{_f(xa + 44)},{_f(ay - 4)} {_f(xa + 44)},{_f(ay + 24)} "
                     f"{_f(xa + 2)},{_f(ay + 20)}")
                mids.append(f'<path class="{cls}" d="{d}"{mk}/>')
                sv.box(xa, ay - 4, xa + 46, ay + 24)
                if lines:
                    texts_after.append((xa + 50, y + th / 2, lines, "start"))
                    grow(xa - 20, xa + 50 + max(_tw(x, FS_S) for x in lines) + 10)
                else:
                    grow(xa - 20, xa + 56)
                y = ay + 34
            else:
                ay = y + th + 6
                sgn = 1 if xb > xa else -1
                x_end = xb - sgn * 1.5
                mids.append(f'<path class="{cls}" d="M{_f(xa)},{_f(ay)} L{_f(x_end)},{_f(ay)}"{mk}/>')
                if lines:
                    texts_after.append(((xa + xb) / 2, y + th / 2, lines, "middle"))
                sv.box(min(xa, xb), y, max(xa, xb), ay + 4)
                grow(min(xa, xb) - 20, max(xa, xb) + 20)
                if auto:
                    num += 1
                    bx = xa + sgn * 0
                    mids.append(f'<circle class="badge" cx="{_f(bx)}" cy="{_f(ay)}" r="8"/>'
                                f'<text class="badget" x="{_f(bx)}" y="{_f(ay)}" text-anchor="middle" '
                                f'dominant-baseline="central">{num}</text>')
                y = ay + 22
        elif ev[0] == "note":
            _, pos, ps, text, _ln = ev
            lines = _wrap(text, 240, FS_S)
            nw = max(_tw(x, FS_S) for x in lines) + 20
            nh = len(lines) * LH_S + 14
            i0 = idx[ps[0]]
            if pos == "right of":
                x0 = cx[i0] + 12
            elif pos == "left of":
                x0 = cx[i0] - 12 - nw
            else:
                i1 = idx[ps[-1]]
                a0, a1 = min(cx[i0], cx[i1]), max(cx[i0], cx[i1])
                nw = max(nw, a1 - a0 + 60)
                x0 = (a0 + a1) / 2 - nw / 2
            mids.append(f'<rect class="note" x="{_f(x0)}" y="{_f(y)}" width="{_f(nw)}" height="{_f(nh)}" rx="3"/>')
            texts_after.append((x0 + nw / 2, y + nh / 2, lines, "middle"))
            sv.box(x0, y, x0 + nw, y + nh)
            grow(x0 - 8, x0 + nw + 8)
            y += nh + 14
        elif ev[0] == "block":
            _, kind, label, _ln = ev
            blocks.append({"kind": kind, "label": label, "y0": y, "elses": []})
            ext_stack.append([float("inf"), float("-inf")])
            y += 30
        elif ev[0] == "else":
            _, kind, label, _ln = ev
            if blocks:
                blocks[-1]["elses"].append((y + 4, label))
            y += 28
        elif ev[0] == "end":
            b = blocks.pop()
            ex = ext_stack.pop()
            if ex[0] == float("inf"):
                ex = [cx[0] - 30, cx[-1] + 30]
            depth = len(blocks)
            x0, x1 = ex[0] - 6, ex[1] + 6
            y0, y1 = b["y0"], y + 2
            if ext_stack:                       # 바깥 틀이 안쪽 틀을 감싸게
                ext_stack[-1][0] = min(ext_stack[-1][0], x0 - 4)
                ext_stack[-1][1] = max(ext_stack[-1][1], x1 + 4)
            name = {"loop": "loop", "alt": "alt", "opt": "opt", "par": "par", "critical": "critical",
                    "break": "break", "rect": ""}[b["kind"]]
            fr = f'<rect class="frame" x="{_f(x0)}" y="{_f(y0)}" width="{_f(x1 - x0)}" height="{_f(y1 - y0)}" rx="2"/>'
            if b["kind"] == "rect":
                fr = f'<rect class="tab" x="{_f(x0)}" y="{_f(y0)}" width="{_f(x1 - x0)}" height="{_f(y1 - y0)}" rx="2"/>'
            if name:
                tw = _tw(name, 11) + 16
                fr += (f'<path class="tab" d="M{_f(x0)},{_f(y0)} L{_f(x0 + tw)},{_f(y0)} L{_f(x0 + tw)},{_f(y0 + 13)} '
                       f'L{_f(x0 + tw - 7)},{_f(y0 + 20)} L{_f(x0)},{_f(y0 + 20)} Z"/>'
                       f'<text class="s b" x="{_f(x0 + 7)}" y="{_f(y0 + 10)}" dominant-baseline="central">{_e(name)}</text>')
                if b["label"]:
                    fr += (f'<text class="lt m" x="{_f(x0 + tw + 8)}" y="{_f(y0 + 10)}" dominant-baseline="central">'
                           f'[{_e(b["label"])}]</text>')
                    sv.box(x0, y0, x0 + tw + 12 + _tw(b["label"], FS_S) + 16, y0 + 20)
            for ey, lab in b["elses"]:
                fr += f'<path class="sep" d="M{_f(x0)},{_f(ey)} L{_f(x1)},{_f(ey)}"/>'
                if lab:
                    fr += (f'<text class="lt m" x="{_f(x0 + 10)}" y="{_f(ey + 12)}" dominant-baseline="central">'
                           f'[{_e(lab)}]</text>')
            fronts.insert(0, fr) if depth == 0 else fronts.append(fr)
            sv.box(x0, y0, x1, y1)
            y += 12
    y_end = y + 6
    for i in range(np_):
        mids.insert(0, f'<path class="life" d="M{_f(cx[i])},{_f(head_y + bh)} L{_f(cx[i])},{_f(y_end)}"/>')
    sv.box(cx[0] - bw[0] / 2, 0, cx[-1] + bw[-1] / 2 + right_extra, y_end)
    mirror = sum(1 for ev in events if ev[0] == "msg") >= 7
    if mirror:
        draw_parts(y_end)
    sv.parts.extend(fronts)
    sv.parts.extend(mids)
    for i, p in enumerate(parts):
        sv.text(cx[i], head_y + bh / 2, blines[i])
        if mirror:
            sv.text(cx[i], y_end + bh / 2, blines[i])
    for x, yy, lines, anchor in texts_after:
        sv.text(x, yy, lines, cls="lt", anchor=anchor, lh=LH_S, fs=FS_S)
    n_msgs = sum(1 for ev in events if ev[0] == "msg")
    sv.title = title
    return sv, f"시퀀스 — 참가자 {np_}명 · 메시지 {n_msgs}개"


# ═══════════════════════════ ERD ═══════════════════════════
_ER_REL = re.compile(
    r'^(?P<a>[^\s{}|]+)\s*(?P<l>\|o|\|\||\}o|\}\|)(?P<line>--|\.\.)(?P<r>o\||\|\||o\{|\|\{)\s*'
    r'(?P<b>[^\s{}|:]+)\s*(?::\s*(?P<lab>.*))?$')
_ER_ENT = re.compile(r'^(?P<n>[^\s{}\[]+)\s*(?:\[\s*"?(?P<al>[^"\]]*)"?\s*\])?\s*\{\s*(?P<rest>\})?\s*$')
_ER_ATTR = re.compile(
    r'^(?P<type>[^\s]+)\s+(?P<name>[^\s"]+)(?:\s+(?P<keys>(?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*))?'
    r'(?:\s+"(?P<c>[^"]*)")?\s*$', re.I)
_CARD = {"|o": "zo", "o|": "zo", "||": "one", "}o": "zm", "o{": "zm", "}|": "om", "|{": "om"}
# 낱말로 쓴 개수 — 'only one' · 'zero or more' · 'many(1)' · '1+' …
_CARD_W = {"only one": "one", "1": "one", "zero or one": "zo", "one or zero": "zo",
           "one or more": "om", "one or many": "om", "many(1)": "om", "1+": "om",
           "zero or more": "zm", "zero or many": "zm", "many(0)": "zm", "0+": "zm"}
_CW = "|".join(re.escape(k) for k in sorted(_CARD_W, key=len, reverse=True))
_ER_REL_W = re.compile(
    rf'^(?P<a>[^\s{{}}|]+)\s+(?P<l>{_CW})\s+(?P<t>optionally to|to)\s+(?P<r>{_CW})\s+'
    r'(?P<b>[^\s{}|:]+)\s*(?::\s*(?P<lab>.*))?$', re.I)


def _render_er(ls, uid):
    g = _Graph("TD")
    ents: dict[str, dict] = {}
    cur = None
    for ln, st in ls[1:]:
        if cur is not None:
            if st == "}":
                cur = None
                continue
            m = _ER_ATTR.match(st)
            if not m:
                raise WbError(f"속성 줄을 읽지 못했습니다 (형식: 타입 이름 [PK|FK|UK] [\"설명\"]): {st[:40]!r}", ln)
            ents[cur]["attrs"].append((m.group("type"), m.group("name"),
                                       (m.group("keys") or "").upper().replace(" ", ""), m.group("c") or ""))
            continue
        low = st.lower()
        if low.startswith(("direction ", "title", "classdef ", "class ", "style ")):
            d = re.match(r"^direction\s+(TB|TD|BT|LR|RL)\s*$", st, re.I)
            if d:
                g.dir = "TD" if d.group(1).upper() == "TB" else d.group(1).upper()
            continue
        m = _ER_ENT.match(st)
        if m:
            name = m.group("n")
            ents.setdefault(name, {"alias": None, "attrs": []})
            if m.group("al"):
                ents[name]["alias"] = _clean(m.group("al"))
            g.node(name, shape="entity")
            if not m.group("rest"):
                cur = name
            continue
        m = _ER_REL.match(st)
        if m:
            a, b = m.group("a"), m.group("b")
            for x in (a, b):
                ents.setdefault(x, {"alias": None, "attrs": []})
                g.node(x, shape="entity")
            lab = _clean((m.group("lab") or "").strip().strip('"'))
            g.edge(a, b, label=lab, style="dotted" if m.group("line") == ".." else "solid",
                   tail=_CARD[m.group("l")], head=_CARD[m.group("r")])
            continue
        m = _ER_REL_W.match(st)
        if m:
            a, b = m.group("a"), m.group("b")
            for x in (a, b):
                ents.setdefault(x, {"alias": None, "attrs": []})
                g.node(x, shape="entity")
            lab = _clean((m.group("lab") or "").strip().strip('"'))
            g.edge(a, b, label=lab, style="dotted" if m.group("t").lower().startswith("optionally") else "solid",
                   tail=_CARD_W[m.group("l").lower()], head=_CARD_W[m.group("r").lower()])
            continue
        raise WbError(f"이 줄을 읽지 못했습니다: {st[:40]!r}", ln)
    if cur is not None:
        raise WbError(f"'{cur} {{' 를 닫는 '}}' 가 없습니다", ls[-1][0])
    if not g.nodes:
        raise WbError("그릴 표가 없습니다", ls[0][0])
    for name, n in g.nodes.items():
        ent = ents.get(name, {"alias": None, "attrs": []})
        title = ent["alias"] or name
        attrs = ent["attrs"]
        n["title"], n["attrs"] = title, attrs
        cw = [0.0, 0.0, 0.0, 0.0]
        for t, nm, k, c in attrs:
            cw[0] = max(cw[0], _tw(t, FS_S))
            cw[1] = max(cw[1], _tw(nm, FS_S))
            cw[2] = max(cw[2], _tw(k, 11))
            cw[3] = max(cw[3], _tw(c[:40], 11))
        n["cw"] = cw
        width = 14 + cw[0] + 14 + cw[1] + (14 + cw[2] if cw[2] else 0) + (14 + cw[3] if cw[3] else 0) + 14
        n["w"] = max(120.0, width, _tw(title) + 34)
        n["h"] = 28.0 + max(len(attrs), 0) * 21.0 + (4.0 if attrs else 0)
    for e in g.edges:
        _label_size(e)
    lay = _layout(g, rank_gap=26.0, node_sep=40.0)
    sv = _Svg(uid)
    _edge_paths(g, lay, sv, er=True)
    for nid in g.order:
        n = g.nodes[nid]
        x0, y0 = n["x"] - n["w"] / 2, n["y"] - n["h"] / 2
        w, h = n["w"], n["h"]
        s = (f'<rect class="n" x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" rx="4"/>'
             f'<rect class="hd" x="{_f(x0 + .6)}" y="{_f(y0 + .6)}" width="{_f(w - 1.2)}" height="27.4" rx="3.5"/>')
        sv.add(s, (x0, y0, x0 + w, y0 + h))
        sv.text(n["x"], y0 + 14, [n["title"]], cls="b")
        cw = n["cw"]
        for r, (t, nm, k, c) in enumerate(n["attrs"]):
            ry = y0 + 28 + r * 21 + 2
            if r % 2 == 1:
                sv.add(f'<rect class="alt" x="{_f(x0 + 1)}" y="{_f(ry)}" width="{_f(w - 2)}" height="21"/>')
            cx0 = x0 + 14
            sv.text(cx0, ry + 10.5, [t], cls="lt m", anchor="start", fs=FS_S)
            cx0 += cw[0] + 14
            sv.text(cx0, ry + 10.5, [nm], cls="lt", anchor="start", fs=FS_S)
            cx0 += cw[1] + 14
            if cw[2]:
                if k:
                    sv.text(cx0, ry + 10.5, [k], cls="s b", anchor="start", fs=11)
                cx0 += cw[2] + 14
            if cw[3] and c:
                sv.text(cx0, ry + 10.5, [c[:40]], cls="s m", anchor="start", fs=11)
    return sv, f"ERD — 표 {len(g.nodes)}개 · 관계 {len(g.edges)}개"


# ═══════════════════════════ 상태도 ═══════════════════════════
_ST_ID = r"(?:\[\*\]|[A-Za-z0-9_\u0080-￿][A-Za-z0-9_\u0080-￿\-.]*)"
_ST_TRANS = re.compile(rf"^(?P<a>{_ST_ID})\s*-->\s*(?P<b>{_ST_ID})\s*(?::\s*(?P<lab>.*))?$")
_ST_AS = re.compile(r'^state\s+"(?P<d>[^"]+)"\s+as\s+(?P<id>[^\s{]+)\s*(?P<open>\{)?\s*$', re.I)
_ST_OPEN = re.compile(r"^state\s+(?P<id>[^\s{\"]+)\s*\{\s*$", re.I)
_ST_TYPE = re.compile(r"^state\s+(?P<id>[^\s<]+)\s*<<(?P<t>choice|fork|join|end)>>\s*$", re.I)
_ST_DESC = re.compile(rf"^(?P<id>{_ST_ID})\s*:\s*(?P<d>.+)$")


def _render_state(ls, uid):
    g = _Graph("TD")
    scope: list[str] = []
    labels: dict[str, list] = {}      # 상태 → 보이는 글 줄들 (Mermaid 처럼: 'state "X" as id' · 'id : 설명' 순서대로)
    in_note = False
    # ★묶음 상태(state X { … })는 먼저 모아 둔다. 선언보다 앞 줄에서 X 를 쓰면
    #   같은 이름의 보통 상자가 하나 더 생겼다(실제로 '판정' 이 둘 그려졌다).
    comps = set()
    for _ln, st in ls[1:]:
        m = _ST_OPEN.match(st)
        if m:
            comps.add(m.group("id"))
        m = _ST_AS.match(st)
        if m and m.group("open"):
            comps.add(m.group("id"))
    pending: list[tuple] = []

    def ref(tok, as_src):
        if tok == "[*]":
            sc = scope[-1] if scope else "root"
            nid = f"__{'s' if as_src else 'e'}_{sc}"
            g.node(nid, "", "start" if as_src else "end", scope[-1] if scope else None)
            return nid
        if tok in comps:
            return ("comp", tok, "src" if as_src else "dst")
        n = g.node(tok, None, None, scope[-1] if scope else None)
        if n["shape"] == "rect":
            n["shape"] = "state"
        return tok

    for ln, st in ls[1:]:
        low = st.lower()
        if in_note:
            if low.startswith("end note"):
                in_note = False
            continue
        if low.startswith("note "):
            if ":" not in st:
                in_note = True
            continue
        if low.startswith(("classdef ", "class ", "hide empty", "scale ", "acctitle", "accdescr")) or st == "--":
            continue
        m = re.match(r"^direction\s+(TB|TD|BT|LR|RL)\s*$", st, re.I)
        if m:
            if not scope:
                g.dir = "TD" if m.group(1).upper() == "TB" else m.group(1).upper()
            continue
        if st == "}":
            if not scope:
                raise WbError("'}' 가 짝이 되는 'state … {' 없이 나왔습니다", ln)
            scope.pop()
            continue
        m = _ST_AS.match(st)
        if m:
            nid = m.group("id")
            if m.group("open"):
                g.subgraph(nid, _clean(m.group("d")), scope[-1] if scope else None)
                scope.append(nid)
            else:
                g.node(nid, None, "state", scope[-1] if scope else None)
                labels.setdefault(nid, []).append(_clean(m.group("d")))
            continue
        m = _ST_OPEN.match(st)
        if m:
            nid = m.group("id")
            g.subgraph(nid, nid, scope[-1] if scope else None)
            scope.append(nid)
            continue
        m = _ST_TYPE.match(st)
        if m:
            t = m.group("t").lower()
            g.node(m.group("id"), "", {"choice": "choice", "fork": "bar", "join": "bar", "end": "end"}[t],
                   scope[-1] if scope else None)
            continue
        m = _ST_TRANS.match(st)
        if m:
            pending.append((ref(m.group("a"), True), ref(m.group("b"), False),
                            _clean(m.group("lab") or ""), ln))
            continue
        m = _ST_DESC.match(re.sub(r"^state\s+(?=[^\s:]+\s*:)", "", st, flags=re.I))   # state X : 설명 도
        if m and m.group("id") != "[*]" and m.group("id") not in comps:
            nid = m.group("id")
            g.node(nid, None, "state", scope[-1] if scope else None)
            labels.setdefault(nid, []).append(_clean(m.group("d")))
            continue
        m = re.match(r"^state\s+(?P<id>[^\s{]+)\s*$", st, re.I)
        if m:
            g.node(m.group("id"), None, "state", scope[-1] if scope else None)
            continue
        raise WbError(f"이 줄을 읽지 못했습니다: {st[:40]!r}", ln)

    def resolve(r):
        if not isinstance(r, tuple):
            return r
        _k, comp, role = r
        inner = [m for m in g.order if comp in g.sgs and m in g.sgs[comp]["members"]]
        if role == "dst":
            cand = f"__s_{comp}"
            return cand if cand in g.nodes else (inner[0] if inner else g.node(comp, None, "state")["id"])
        cand = f"__e_{comp}"
        real = [m for m in inner if not m.startswith("__")]
        return cand if cand in g.nodes else (real[-1] if real else (inner[-1] if inner else g.node(comp, None, "state")["id"]))

    for a, b, lab, _ln in pending:
        g.edge(resolve(a), resolve(b), label=lab)
    if scope:
        raise WbError(f"'state {scope[-1]} {{' 를 닫는 '}}' 가 없습니다", ls[-1][0])
    if not g.nodes:
        raise WbError("그릴 상태가 없습니다", ls[0][0])
    for nid, n in g.nodes.items():
        sh = n["shape"]
        if sh == "start":
            n["w"] = n["h"] = 16.0
            n["lines"] = []
        elif sh == "end":
            n["w"] = n["h"] = 20.0
            n["lines"] = []
        elif sh == "choice":
            n["w"] = n["h"] = 28.0
            n["lines"] = []
        elif sh == "bar":
            n["w"], n["h"] = (8.0, 70.0) if g.dir in ("LR", "RL") else (70.0, 8.0)
            n["lines"] = []
        else:
            n["shape"] = "state"
            # 설명이 있으면 설명만 보인다(이름은 안 보임) — Mermaid 와 같다. 둘 이상이면 줄줄이
            text = "\n".join(labels[nid]) if labels.get(nid) else nid
            lines = _wrap(text, 200)
            n["lines"] = lines
            n["w"] = max(70.0, max(_tw(x) for x in lines) + 30)
            n["h"] = max(36.0, len(lines) * LH + 16)
    for e in g.edges:
        e["head"] = "arr"
        _label_size(e)
    lay = _layout(g, rank_gap=20.0 if g.sgs else 18.0)
    sv = _Svg(uid)
    for s in _subgraph_boxes(g, sv):
        sv.add(s)
    _edge_paths(g, lay, sv)
    for nid in g.order:
        n = g.nodes[nid]
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        sh = n["shape"]
        if sh == "start":
            sv.add(f'<circle class="nf" cx="{_f(x)}" cy="{_f(y)}" r="8"/>', (x - 8, y - 8, x + 8, y + 8))
        elif sh == "end":
            sv.add(f'<circle class="n2" cx="{_f(x)}" cy="{_f(y)}" r="10"/>'
                   f'<circle class="nf" cx="{_f(x)}" cy="{_f(y)}" r="6"/>', (x - 10, y - 10, x + 10, y + 10))
        elif sh == "choice":
            sv.add(f'<polygon class="n" points="{_f(x)},{_f(y - 14)} {_f(x + 14)},{_f(y)} {_f(x)},{_f(y + 14)} '
                   f'{_f(x - 14)},{_f(y)}"/>', (x - 14, y - 14, x + 14, y + 14))
        elif sh == "bar":
            sv.add(f'<rect class="nf" x="{_f(x - w / 2)}" y="{_f(y - h / 2)}" width="{_f(w)}" height="{_f(h)}" rx="2"/>',
                   (x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        else:
            sv.add(f'<rect class="n" x="{_f(x - w / 2)}" y="{_f(y - h / 2)}" width="{_f(w)}" height="{_f(h)}" rx="10"/>',
                   (x - w / 2, y - h / 2, x + w / 2, y + h / 2))
            sv.text(x, y, n["lines"])
    real = sum(1 for n in g.nodes.values() if n["shape"] == "state")
    return sv, f"상태도 — 상태 {real}개 · 전이 {len(g.edges)}개"


# ═══════════════════════════ 밖으로 ═══════════════════════════
_CACHE: dict[str, dict] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_MAX = 300
_KIND_KO = {"flowchart": "흐름도", "sequence": "시퀀스", "er": "ERD", "state": "상태도"}


def render(src: str) -> dict:
    """Mermaid 글 → {"ok", "kind", "kind_ko", "svg", "w", "h", "title", "desc", "error", "line"}.

    title 은 글쓴이가 붙인 제목(앞머리 title: · 시퀀스 title 줄)뿐이다 — 없으면 빈 글.
    desc 는 '흐름도 — 상자 8개 · 선 8개' 같은 요약(화면 읽기 프로그램용 aria-label 에도 쓴다).

    ok=False 면 error(무엇이 틀렸나) · line(원문 몇째 줄, 모르면 0). 그 밖의 종류는
    kind 에 첫 낱말(pie · gantt …)이 담긴다 — 화면은 글을 그대로 둔다.
    같은 글은 다시 계산하지 않는다(최근 300개).
    """
    src = str(src or "")
    if len(src) > MAX_SRC:
        return {"ok": False, "kind": "", "error": f"글이 너무 깁니다({len(src):,}자) — 나눠 그려 주세요", "line": 0}
    key = hashlib.sha1(src.encode("utf-8")).hexdigest()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    if hit is not None:
        return dict(hit)
    res = _render_uncached(src, "wb" + key[:10])
    with _CACHE_LOCK:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = res
    return dict(res)


def _render_uncached(src: str, uid: str) -> dict:
    ls = _lines(src)
    if not ls:
        return {"ok": False, "kind": "", "error": "그릴 내용이 없습니다", "line": 0}
    kind = detect_kind(src)
    fn = {"flowchart": _render_flow, "sequence": _render_seq, "er": _render_er, "state": _render_state}.get(kind)
    if fn is None:
        return {"ok": False, "kind": kind, "line": ls[0][0],
                "error": f"'{kind}' 는 아직 그림으로 그리지 않습니다 (흐름도 · 시퀀스 · ERD · 상태도만)"}
    try:
        sv, desc = fn(ls, uid)
        title = _front_title(src) or sv.title
        svg, w, h = sv.close(f"{title} — {desc}" if title else desc)
        return {"ok": True, "kind": kind, "kind_ko": _KIND_KO[kind], "svg": svg,
                "w": round(w, 1), "h": round(h, 1), "title": title, "desc": desc, "error": "", "line": 0}
    except WbError as e:
        return {"ok": False, "kind": kind, "error": str(e), "line": e.line}
    except RecursionError:
        return {"ok": False, "kind": kind, "error": "그림이 너무 복잡합니다 — 나눠 그려 주세요", "line": 0}
    except Exception as e:                                   # noqa: BLE001 — 그림 하나 때문에 답변 전체가 죽으면 안 된다
        return {"ok": False, "kind": kind, "error": f"그리다가 멈췄습니다: {type(e).__name__}: {e}", "line": 0}


def paper_svg(svg: str, accent: str = "#4f46e5") -> str:
    """파일로 내보낼 SVG — 둘레 글자색 · CSS 변수를 못 받는 곳(뷰어 · 문서 · PPT)에서도 같게
    보이도록 색을 박고 흰 바탕을 깐다. 화면의 'SVG 저장'(whiteboard.js)과 같은 모습이다."""
    def fix(m):
        st = m.group(1).replace("var(--wb-accent,currentColor)", accent).replace("var(--wb-bg,#fff)", "#fff")
        st = re.sub(r"var\(--wb-font,([^)]*)\)", r"\1", st).replace("currentColor", "#1f2328")
        return "<style>" + st + "</style>"
    svg = re.sub(r"<style>(.*?)</style>", fix, svg, count=1, flags=re.S)
    return svg.replace("<g transform=", '<rect width="100%" height="100%" fill="#fff"/><g transform=', 1)


def _main(argv) -> int:
    """데모스 없이 그림만 뽑기.
        python wb_render.py 그림.mmd         → 그림.svg
        python wb_render.py 보고서.md        → 보고서-1.svg, 보고서-2.svg … (```mermaid 마다)
        python wb_render.py < 그림.mmd > 그림.svg
    """
    import os
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")         # 윈도 콘솔(cp949)에서 글자 때문에 멈추지 않게
        except (AttributeError, ValueError):
            pass
    if not argv:
        r = render(sys.stdin.read())
        if not r["ok"]:
            sys.stderr.write(f"못 그림 ({r.get('line')}째 줄): {r['error']}\n")
            return 1
        sys.stdout.buffer.write(paper_svg(r["svg"]).encode("utf-8"))
        return 0
    bad = 0
    for path in argv:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        blocks = re.findall(r"^```mermaid[^\n]*\n(.*?)^```", text, re.S | re.M | re.I)
        if not blocks:
            if "```" in text:
                print(f"{path}: ```mermaid 블록이 없습니다")
                bad += 1
                continue
            blocks = [text]                           # 파일 전체가 Mermaid 글
        base = os.path.splitext(path)[0]
        for i, src in enumerate(blocks, 1):
            out = base + (f"-{i}" if len(blocks) > 1 else "") + ".svg"
            r = render(src)
            if r["ok"]:
                with open(out, "w", encoding="utf-8") as f:
                    f.write(paper_svg(r["svg"]))
                print(f"그림 → {out}  ({r['kind_ko']} {r['w']:.0f}×{r['h']:.0f})")
            else:
                bad += 1
                where = f" {r['line']}째 줄" if r.get("line") else ""
                print(f"못 그림: {path} {i}번째 그림{where} — {r['error']}")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
