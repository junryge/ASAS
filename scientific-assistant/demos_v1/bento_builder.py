"""demos_v1/bento_builder.py — 슬라이드를 Bento 단일 HTML 로 만든다.

왜 python-pptx 대신 이걸 쓰나
    · **받는 사람이 아무것도 설치 안 해도 된다.** .bento.html 파일 하나를
      브라우저로 열면 그게 곧 뷰어이자 발표기이자 편집기다.
    · **공장 서버는 인터넷이 없다.** 껍데기(676KB)를 저장소에 넣어 두고
      거기에 문서만 끼워 넣으므로, 만들 때도 열 때도 네트워크가 필요 없다.
    · **고치기 쉽다.** 문서가 파일 맨 앞 JSON 한 덩어리다. python-pptx 로
      도형 좌표를 일일이 찍던 것과 달리, 레이아웃을 값으로 다룬다.

기존 .pptx 경로는 그대로 둔다
    회사에 .pptx 로 내야 하는 자리가 있다. 이건 대체가 아니라 기본값 교체다.

문서 형식 (bento/slides v1)
    {"format":"bento/slides","version":1,"title":…,
     "size":{"width":1280,"height":720},
     "theme":{"background","color","accent","fontFamily"},
     "slides":[{"id","background","notes","elements":[…]}]}

★JSON 을 껍데기에 넣을 때 '<' 를 \\u003c 로 바꾼다 — 안 그러면 본문에
  </script> 가 섞이는 순간 문서가 통째로 깨진다.
"""
from __future__ import annotations

import html as _html
import json
import math
import os
import re
from datetime import datetime

SHELL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bento")
SHELL_PATH = os.path.join(SHELL_DIR, "Bento_Slides.bento.html")

W, H = 1280, 720
MARGIN = 84                      # 좌우 여백
CONTENT_TOP = 210                # 제목 아래 본문 시작
FOOT = 660                       # 쪽번호 y

# ── 테마 ──
# ★배경만 바꾸는 게 아니라 글자색·강조색까지 한 벌로 묶는다. 예전 pptx 는
#   템플릿마다 색이 따로 놀아서, 어두운 배경에 어두운 글씨가 나오곤 했다.
THEMES = {
    "dark": {"background": "#0E1117", "color": "#E6EDF3", "accent": "#3DDBE8",
             "sub": "#8B949E", "band": "#161B22",
             "fontFamily": "'Malgun Gothic','Segoe UI',system-ui,sans-serif"},
    "light": {"background": "#FFFFFF", "color": "#1F2328", "accent": "#0969DA",
              "sub": "#57606A", "band": "#F6F8FA",
              "fontFamily": "'Malgun Gothic','Segoe UI',system-ui,sans-serif"},
    "corporate": {"background": "#F7F9FC", "color": "#16233A", "accent": "#1F5FBF",
                  "sub": "#5A6B85", "band": "#E7EDF7",
                  "fontFamily": "'Malgun Gothic','Segoe UI',system-ui,sans-serif"},
    "hynix": {"background": "#0B1220", "color": "#EAF1FF", "accent": "#FF9E2C",
              "sub": "#93A4BF", "band": "#141F33",
              "fontFamily": "'Malgun Gothic','Segoe UI',system-ui,sans-serif"},
}
DEFAULT_THEME = "dark"


def theme_of(name: str) -> dict:
    return THEMES.get(str(name or "").lower(), THEMES[DEFAULT_THEME])


def _esc(s) -> str:
    """슬라이드 본문은 HTML 로 들어간다 — 사용자 텍스트를 그대로 넣으면 깨진다."""
    return _html.escape(str(s if s is not None else ""), quote=False)


def _esc_br(s) -> str:
    """줄바꿈까지 살린다. ★HTML 은 '\n' 을 공백으로 삼킨다 — 두 줄로 쓴
    카드 문구가 한 줄로 붙어 나온다 (실제로 그렇게 나왔다)."""
    return _esc(s).replace("\r\n", "\n").replace("\n", "<br>")


_ID = re.compile(r"[^a-z0-9]+")


def _sid(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def _text(eid, x, y, w, h, html, size, color, *, weight=400, align="left",
          valign="top", line=1.35, family=None, opacity=1.0) -> dict:
    return {
        "id": eid, "type": "text", "x": x, "y": y, "w": w, "h": h,
        "rotation": 0, "opacity": opacity, "html": html,
        "fontSize": size, "fontWeight": weight, "color": color,
        "align": align, "valign": valign, "lineHeight": line,
        **({"fontFamily": family} if family else {}),
    }


def _rect(eid, x, y, w, h, color, *, opacity=1.0, radius=0) -> dict:
    """배경 띠·구분선. Bento 의 shape 요소.

    ★stroke / strokeWidth 를 빼면 도형이 아예 안 그려진다 (처음에 강조 막대가
      화면에서 사라져 있었다). 규격이 요구하는 칸은 전부 채운다.
    """
    return {"id": eid, "type": "shape", "shape": "rect",
            "x": x, "y": y, "w": w, "h": h, "rotation": 0,
            "opacity": opacity, "fill": color,
            "stroke": "none", "strokeWidth": 0, "radius": radius}


# ── 슬라이드 한 장씩 ──
def _slide_title(i, b, t) -> dict:
    """표지 — 큰 제목 + 부제 + 강조 막대."""
    els = [
        _rect(f"s{i}bar", MARGIN, 300, 96, 8, t["accent"], radius=4),
        _text(f"s{i}t", MARGIN, 330, W - MARGIN * 2, 180,
              _esc(b.get("title") or ""), 66, t["color"],
              weight=800, line=1.15, family=t["fontFamily"]),
    ]
    if b.get("subtitle"):
        els.append(_text(f"s{i}s", MARGIN, 512, W - MARGIN * 2, 80,
                         _esc(b["subtitle"]), 26, t["sub"],
                         line=1.4, family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_section(i, b, t) -> dict:
    """구분 표지 — 배경 띠 + 가운데 제목."""
    return {"id": _sid("s", i), "background": t["band"], "transition": "fade",
            "notes": b.get("notes", ""), "elements": [
        _rect(f"s{i}bar", 0, 336, 12, 96, t["accent"]),
        _text(f"s{i}t", MARGIN, 320, W - MARGIN * 2, 120,
              _esc(b.get("title") or ""), 46, t["color"],
              weight=700, valign="middle", family=t["fontFamily"]),
    ]}


def _head(i, title, t) -> list:
    """본문 슬라이드 공통 머리 — 제목 + 밑줄."""
    return [
        _text(f"s{i}h", MARGIN, 96, W - MARGIN * 2, 76, _esc(title), 38,
              t["color"], weight=700, family=t["fontFamily"]),
        _rect(f"s{i}rule", MARGIN, 178, W - MARGIN * 2, 2, t["accent"], opacity=0.45),
    ]


def _slide_content(i, b, t) -> dict:
    """글머리 — 단계별 들여쓰기와 크기를 다르게 준다."""
    els = _head(i, b.get("title") or "", t)
    y = CONTENT_TOP
    bullets = b.get("bullets") or []
    # ★줄이 많으면 글자를 줄여서라도 한 장에 담는다. 예전엔 넘쳐서 잘렸다.
    n = len(bullets)
    size0 = 28 if n <= 7 else (24 if n <= 10 else 20)
    gap = 58 if n <= 7 else (48 if n <= 10 else 40)
    for k, bl in enumerate(bullets):
        lv = int(bl.get("level", 0) or 0)
        size = max(15, size0 - lv * 4)
        x = MARGIN + lv * 40
        mark = "•" if lv == 0 else ("–" if lv == 1 else "·")
        els.append(_text(
            f"s{i}b{k}", x, y, W - x - MARGIN, gap,
            f'<span style="color:{t["accent"]}">{mark}</span> {_esc(bl.get("text",""))}',
            size, t["color"] if lv == 0 else t["sub"],
            weight=600 if lv == 0 else 400, line=1.3, family=t["fontFamily"]))
        y += gap
        if y > FOOT - 40:
            break
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_table(i, b, t) -> dict:
    """표 — Bento 의 table 요소를 쓴다.

    ★처음엔 사각형과 글자를 좌표로 찍어 표처럼 보이게 했는데, 그건 표가
      아니라 그림이다. 열 너비를 바꾸거나 셀을 고칠 수가 없다. 규격에 진짜
      table 요소가 있으므로 그걸 쓴다 — 열어서 편집이 된다.
    """
    els = _head(i, b.get("title") or "", t)
    headers = [str(x) for x in (b.get("headers") or [])]
    rows = [[str(c) for c in r] for r in (b.get("rows") or [])]
    ncol = max(1, len(headers) or (len(rows[0]) if rows else 1))

    cells = []
    if headers:
        cells.append({"cells": [{"html": _esc(h)} for h in headers[:ncol]]})
    MAX = 12                                  # 넘치면 잘라내고 몇 행인지 밝힌다
    for r in rows[:MAX]:
        row = list(r[:ncol]) + [""] * max(0, ncol - len(r))
        cells.append({"cells": [{"html": _esc(c)} for c in row]})

    tw = W - MARGIN * 2
    th = min(430, (len(cells) or 1) * 44 + 8)
    els.append({
        "id": f"s{i}tbl", "type": "table",
        "x": MARGIN, "y": CONTENT_TOP, "w": tw, "h": th,
        "rotation": 0, "opacity": 1,
        "header": bool(headers),
        "columns": [{"w": 1} for _ in range(ncol)],
        "rows": cells,
        "style": {
            "headerBg": t["band"], "headerColor": t["color"],
            "zebra": "rgba(255,255,255,0.04)" if t is THEMES["dark"] or t is THEMES["hynix"]
                     else "rgba(0,0,0,0.035)",
            "borderColor": "rgba(128,128,128,0.28)", "borderWidth": 1,
            "cellPadX": 14, "cellPadY": 10,
            "fontSize": 18 if len(cells) <= 8 else 15,
            "color": t["color"], "radius": 8,
        },
    })
    if len(rows) > MAX:
        els.append(_text(f"s{i}more", MARGIN, CONTENT_TOP + th + 10, tw, 30,
                         f"… 외 {len(rows) - MAX}행", 15, t["sub"],
                         family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_code(i, b, t) -> dict:
    """코드 — 고정폭 글꼴 + 어두운 판. 줄이 많으면 잘라내고 몇 줄인지 밝힌다."""
    els = _head(i, b.get("title") or "", t)
    code = str(b.get("code") or "")
    lines = code.split("\n")
    shown, cut = lines[:18], max(0, len(lines) - 18)
    body = "<br>".join(_esc(ln).replace(" ", "&nbsp;") for ln in shown)
    if cut:
        body += f'<br><span style="opacity:.6">… 외 {cut}줄</span>'
    els.append(_rect(f"s{i}pane", MARGIN, CONTENT_TOP, W - MARGIN * 2,
                     min(430, 40 + len(shown) * 22), t["band"], radius=10))
    els.append(_text(f"s{i}code", MARGIN + 20, CONTENT_TOP + 16,
                     W - MARGIN * 2 - 40, 400, body, 16, t["color"],
                     line=1.45, family="'Consolas','D2Coding',monospace"))
    if b.get("language"):
        els.append(_text(f"s{i}lang", W - MARGIN - 140, CONTENT_TOP - 34, 140, 28,
                         _esc(b["language"]), 14, t["sub"], align="right",
                         family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


# ── MD 파서가 글머리를 알아서 바꿔 놓는 종류들 ──
# ★ppt_builder._apply_smart_layout 이 content 를 statement/quote/bignumber/
#   compare2/grid 로 자동 변환한다. 그래서 실제 덱에서 'content' 는 오히려
#   드물다. 이 다섯을 안 그리면 제목만 남고 내용이 통째로 사라진다 —
#   실제로 그렇게 나왔다(글머리 두 줄짜리 장이 빈 장으로).
def _slide_statement(i, b, t) -> dict:
    """한 줄 선언 — 가운데 큼직하게."""
    els = _head(i, b.get("title") or "", t)
    stmt = str(b.get("statement") or "")
    size = 44 if len(stmt) <= 30 else (34 if len(stmt) <= 70 else 26)
    els.append(_text(f"s{i}st", MARGIN, CONTENT_TOP + 40, W - MARGIN * 2, 240,
                     _esc_br(stmt), size, t["color"], weight=700,
                     align="center", valign="middle", line=1.4,
                     family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_quote(i, b, t) -> dict:
    """인용 — 큰 따옴표 + 본문 + 출처."""
    els = _head(i, b.get("title") or "", t)
    q = str(b.get("quote") or "")
    size = 36 if len(q) <= 60 else (28 if len(q) <= 140 else 22)
    els.append(_text(f"s{i}qm", MARGIN, CONTENT_TOP - 14, 90, 100, "“", 96,
                     t["accent"], weight=800, family=t["fontFamily"],
                     opacity=0.55))
    els.append(_text(f"s{i}q", MARGIN + 96, CONTENT_TOP + 20,
                     W - MARGIN * 2 - 96, 240, _esc_br(q), size, t["color"],
                     weight=600, line=1.45, family=t["fontFamily"]))
    if b.get("cite"):
        els.append(_text(f"s{i}c", MARGIN + 96, FOOT - 90, W - MARGIN * 2 - 96,
                         40, "— " + _esc(b["cite"]), 18, t["sub"],
                         family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_bignumber(i, b, t) -> dict:
    """수치 강조 — 거대한 숫자 + 작은 라벨."""
    els = _head(i, b.get("title") or "", t)
    num = str(b.get("number") or "")
    size = 150 if len(num) <= 5 else (110 if len(num) <= 9 else 76)
    els.append(_text(f"s{i}n", MARGIN, CONTENT_TOP + 20, W - MARGIN * 2, 200,
                     _esc(num), size, t["accent"], weight=800, align="center",
                     valign="middle", line=1.1, family=t["fontFamily"]))
    if b.get("label"):
        els.append(_text(f"s{i}l", MARGIN, CONTENT_TOP + 240, W - MARGIN * 2,
                         70, _esc_br(b["label"]), 24, t["sub"], align="center",
                         line=1.35, family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _card(i, k, x, y, w, h, head, items, t, *, accent=None) -> list:
    """제목 + 항목 몇 개짜리 카드 하나."""
    accent = accent or t["accent"]
    els = [
        _rect(f"s{i}c{k}", x, y, w, h, t["band"], radius=14),
        _rect(f"s{i}c{k}b", x, y, w, 6, accent, radius=3),
        _text(f"s{i}c{k}h", x + 22, y + 26, w - 44, 76, _esc_br(head), 24,
              t["color"], weight=700, line=1.25, family=t["fontFamily"]),
    ]
    if items:
        body = "<br>".join(
            f'<span style="color:{accent}">·</span> {_esc(s)}' for s in items[:6])
        els.append(_text(f"s{i}c{k}t", x + 22, y + 112, w - 44, h - 130, body,
                         17, t["sub"], line=1.55, family=t["fontFamily"]))
    return els


def _slide_compare2(i, b, t) -> dict:
    """좌우 비교 — 카드 두 장, 색을 달리해서 구분한다."""
    els = _head(i, b.get("title") or "", t)
    gap, top = 40, CONTENT_TOP
    cw = (W - MARGIN * 2 - gap) // 2
    ch = FOOT - top - 30
    els += _card(i, 0, MARGIN, top, cw, ch, b.get("left_title") or "",
                 b.get("left_items") or [], t)
    els += _card(i, 1, MARGIN + cw + gap, top, cw, ch,
                 b.get("right_title") or "", b.get("right_items") or [], t,
                 accent=t["sub"])
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def _slide_grid(i, b, t) -> dict:
    """카드 격자 — 3개면 한 줄, 4개면 2×2."""
    els = _head(i, b.get("title") or "", t)
    cards = [c for c in (b.get("cards") or []) if isinstance(c, dict)][:6]
    n = len(cards) or 1
    cols = 2 if n == 4 else min(n, 3)
    rows = -(-n // cols)
    gap, top = 32, CONTENT_TOP
    cw = (W - MARGIN * 2 - gap * (cols - 1)) // cols
    ch = (FOOT - top - 30 - gap * (rows - 1)) // rows
    for k, c in enumerate(cards):
        x = MARGIN + (k % cols) * (cw + gap)
        y = top + (k // cols) * (ch + gap)
        desc = [s for s in str(c.get("desc") or "").split(" · ") if s]
        els += _card(i, k, x, y, cw, ch, c.get("title") or "", desc, t)
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


_MAKERS = {
    "title": _slide_title, "section": _slide_section,
    "content": _slide_content, "table": _slide_table, "code": _slide_code,
    "statement": _slide_statement, "quote": _slide_quote,
    "bignumber": _slide_bignumber, "compare2": _slide_compare2,
    "grid": _slide_grid,
}


def _slide_fallback(i, b, t) -> dict:
    """모르는 종류 — 있는 글자라도 전부 내보낸다.

    ★빈 장을 내놓는 것이 제일 나쁘다. 사람이 '내용을 안 썼나' 하고 넘어가
      버린다. 못 그리겠으면 못 그리겠다고 화면에 보여야 한다.
    """
    els = _head(i, b.get("title") or b.get("type") or "", t)
    lines = []
    for k, v in b.items():
        if k in ("type", "title", "notes"):
            continue
        if isinstance(v, str) and v.strip():
            lines.append(v.strip())
        elif isinstance(v, list):
            for it in v[:8]:
                if isinstance(it, str):
                    lines.append(it)
                elif isinstance(it, dict):
                    lines.append(" · ".join(str(x) for x in it.values() if x))
    body = "<br>".join(f'<span style="color:{t["accent"]}">•</span> {_esc(s)}'
                       for s in lines[:12]) or "(내용 없음)"
    els.append(_text(f"s{i}fb", MARGIN, CONTENT_TOP, W - MARGIN * 2,
                     FOOT - CONTENT_TOP - 20, body, 22, t["color"],
                     line=1.5, family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": t["background"],
            "transition": "fade", "notes": b.get("notes", ""), "elements": els}


def build_doc(blocks: list[dict], *, title: str = "", theme: str = DEFAULT_THEME,
              footer: str = "", page_numbers: bool = True) -> dict:
    """블록 목록 → bento/slides 문서(dict).

    blocks 는 기존 pptx 경로가 쓰던 그 형식 그대로다 — 파서를 새로 만들지
    않으려고 일부러 맞췄다 (ppt_builder.parse_markdown 을 그대로 쓴다).
    """
    t = theme_of(theme)
    slides = []
    for i, b in enumerate(blocks or [], start=1):
        kind = str(b.get("type") or "content").lower()
        mk = _MAKERS.get(kind, _slide_fallback)
        s = mk(i, b, t)
        # 쪽번호·꼬리말은 표지 빼고
        if i > 1:
            if page_numbers:
                s["elements"].append(
                    _text(f"s{i}pg", W - MARGIN - 90, FOOT, 90, 30,
                          str(i), 14, t["sub"], align="right", family=t["fontFamily"]))
            if footer:
                s["elements"].append(
                    _text(f"s{i}ft", MARGIN, FOOT, 600, 30, _esc(footer), 14,
                          t["sub"], family=t["fontFamily"]))
        slides.append(s)

    if not slides:                          # 빈 입력이어도 열리는 파일을 준다
        slides = [_slide_title(1, {"title": title or "빈 문서",
                                   "subtitle": "내용이 없습니다"}, t)]
    return {
        "format": "bento/slides", "version": 1,
        "title": title or (blocks[0].get("title") if blocks else "") or "발표자료",
        "size": {"width": W, "height": H},
        "theme": {k: t[k] for k in ("background", "color", "accent", "fontFamily")},
        "slides": slides,
    }


# ── 껍데기에 끼워 넣기 ──
_DOC_BLOCK = re.compile(
    r'(<script[^>]*id="bento-doc"[^>]*>)(.*?)(</script>)', re.S)


def read_shell() -> str:
    if not os.path.isfile(SHELL_PATH):
        raise FileNotFoundError(
            f"Bento 껍데기가 없습니다: {SHELL_PATH} — demos_v1/bento/ 를 확인하세요")
    with open(SHELL_PATH, "r", encoding="utf-8") as f:
        return f.read()


# Bento 는 열릴 때 새 버전이 있나 보러 bento.page 에 한 번 나간다.
# ★공장 망에서는 나갈 데가 없다. 껍데기에 이미 있는 오프라인 스위치를
#   미리 켜 두면 그 요청 자체가 안 나간다 (툴바 지구본으로 되돌릴 수 있다).
#   껍데기 파일은 손대지 않는다 — 나중에 새 버전을 받아 넣기 쉽도록.
_OFFLINE_JS = (
    '<script>try{if(localStorage.getItem("bento-offline")===null)'
    'localStorage.setItem("bento-offline","on")}catch(e){}</script>')


def embed(doc: dict, shell: str | None = None, *, offline: bool = True) -> str:
    """문서를 껍데기 안에 넣어 완성된 .bento.html 문자열을 만든다."""
    shell = shell if shell is not None else read_shell()
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    # ★'<' 를 이스케이프한다. 본문에 '</script>' 가 들어가면 파일이 통째로
    #   깨지는데, 사용자 글에 그런 문자열이 없으리라 믿을 수 없다.
    body = body.replace("<", "\\u003c")
    if not _DOC_BLOCK.search(shell):
        raise ValueError("껍데기에서 #bento-doc 블록을 못 찾았습니다")
    tail = _OFFLINE_JS if offline else ""
    return _DOC_BLOCK.sub(
        lambda m: m.group(1) + "\n" + body + "\n" + m.group(3) + tail,
        shell, count=1)


def build(blocks: list[dict], **kw) -> tuple[str, dict]:
    """블록 → (완성된 HTML, 문서 dict)."""
    doc = build_doc(blocks, **kw)
    return embed(doc), doc


# ══════════════════════════════════════════════════════════════
# LLM 자유배치 설계 → Bento
# ══════════════════════════════════════════════════════════════
# PPT 설계 모드는 LLM 이 도형을 직접 배치한 JSON 을 내놓는다
# ({"slides":[{"type":"custom","shapes":[{"shape":"circle","x":1.0,…}]}]}).
# 그 좌표는 inch 다 — pptx 가 inch 로 그리니까. Bento 는 px 다.
#
# ★비율을 망가뜨리지 않는다. 가로/세로를 각각 늘리면 원이 타원이 되고
#   정사각형 카드가 찌그러진다. 한 배율로만 키우고 남는 쪽을 가운데 둔다.

_SHAPE_KIND = {                     # LLM 이 쓰는 이름 → Bento 도형
    "rect": "rect", "rectangle": "rect",
    "rounded_rect": "rect", "rounded": "rect",
    "circle": "ellipse", "oval": "ellipse", "ellipse": "ellipse",
    "triangle": "triangle",
    "arrow_right": "arrow", "arrow_left": "arrow",
    "arrow_up": "arrow", "arrow_down": "arrow", "chevron": "arrow",
    "callout": "rect", "cloud": "ellipse",
}
_ARROW_ROT = {"arrow_right": 0, "arrow_left": 180,
              "arrow_up": -90, "arrow_down": 90, "chevron": 0}

# Bento 는 임의의 SVG path 를 그릴 수 있다 — 마름모·오각형·별을 사각형으로
# 뭉개지 않고 그대로 그린다 (0~100 정규 좌표, pathBox 로 늘린다).
_POLY = {
    "diamond": "M50,0 L100,50 L50,100 L0,50 Z",
    "pentagon": "M50,0 L100,38 L81,100 L19,100 L0,38 Z",
    "hexagon": "M25,0 L75,0 L100,50 L75,100 L25,100 L0,50 Z",
    "star": ("M50,0 L61,35 L98,35 L68,57 L79,92 L50,70 "
             "L21,92 L32,57 L2,35 L39,35 Z"),
}


def _rgb(hexstr: str) -> tuple[int, int, int] | None:
    s = str(hexstr or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return None
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError:
        return None


def _on_color(fill: str, t: dict) -> str:
    """도형 위 글자색. ★어두운 도형에 어두운 글씨를 얹으면 안 보인다."""
    rgb = _rgb(fill)
    if rgb is None:
        return t["color"]
    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
    return "#111111" if lum > 0.6 else "#FFFFFF"


def _overlaps(box, shapes, sc) -> bool:
    """px 상자가 도형 하나라도 건드리나 (제목·쪽번호를 겹쳐 찍지 않으려고)."""
    bx, by, bw, bh = box
    for sp in shapes:
        try:
            x, y, w, h = (float(sp.get(k, 0) or 0) for k in ("x", "y", "w", "h"))
        except (TypeError, ValueError):
            continue
        px, py, pw, ph = sc(x, y, w, h)
        if px < bx + bw and px + pw > bx and py < by + bh and py + ph > by:
            return True
    return False


def _design_slide(i: int, sd: dict, t: dict, sc) -> dict:
    """도형 목록 한 장을 Bento 요소로 옮긴다."""
    shapes = [s for s in (sd.get("shapes") or []) if isinstance(s, dict)]
    els: list[dict] = []
    bg = sd.get("background") or t["background"]

    for k, sp in enumerate(shapes):
        kind = str(sp.get("shape") or "rect").lower()
        try:
            x, y, w, h = (float(sp.get(key, 0) or 0)
                          for key in ("x", "y", "w", "h"))
        except (TypeError, ValueError):
            continue
        px, py, pw, ph = sc(x, y, w, h)
        text = str(sp.get("text") or "")
        size = max(9, round(float(sp.get("font_size", 14) or 14) * sc.pt))
        align = str(sp.get("align") or "left").lower()
        align = align if align in ("left", "center", "right") else "left"
        eid = f"s{i}e{k}"

        if kind == "textbox":
            els.append(_text(eid, px, py, max(pw, 8), max(ph, 8), _esc_br(text),
                             size, sp.get("font_color") or t["color"],
                             weight=700 if sp.get("bold") else 400,
                             align=align, valign="middle",
                             family=t["fontFamily"]))
            continue

        if kind == "line":
            # ★기울어진 선은 회전으로 그린다. 가로줄로 눕혀 버리면 화살표가
            #   엉뚱한 데를 가리킨다.
            length = math.hypot(pw, ph) or 2
            thick = max(2, int(float(sp.get("line_width", 2) or 2) * sc.pt))
            cx, cy = px + pw / 2, py + ph / 2
            e = _rect(eid, round(cx - length / 2), round(cy - thick / 2),
                      round(length), thick, sp.get("line") or t["sub"])
            e["shape"] = "line"
            e["rotation"] = round(math.degrees(math.atan2(ph, pw)), 2)
            els.append(e)
            continue

        fill = sp.get("fill")
        fill = t["accent"] if fill in (None, "") else str(fill)
        stroke = sp.get("line") or "none"
        sw = int(float(sp.get("line_width", 0) or 0) * sc.pt) if sp.get("line") else 0

        if kind in _POLY:
            e = {"id": eid, "type": "shape", "shape": "path",
                 "x": px, "y": py, "w": pw, "h": ph, "rotation": 0,
                 "opacity": 1, "fill": "none" if fill == "none" else fill,
                 "stroke": stroke, "strokeWidth": sw, "radius": 0,
                 "d": _POLY[kind], "pathBox": [0, 0, 100, 100]}
        else:
            bent = _SHAPE_KIND.get(kind, "rect")
            rx, ry, rw, rh, rot = px, py, pw, ph, 0
            if bent == "arrow":
                rot = _ARROW_ROT.get(kind, 0)
                if rot in (90, -90):     # ★세로 화살표는 상자를 눕혀서 돌린다
                    cx, cy = px + pw / 2, py + ph / 2
                    rw, rh = ph, pw
                    rx, ry = round(cx - rw / 2), round(cy - rh / 2)
            e = _rect(eid, rx, ry, rw, rh,
                      "none" if fill == "none" else fill,
                      radius=14 if kind in ("rounded_rect", "rounded",
                                            "callout") else 0)
            e["shape"] = bent
            e["rotation"] = rot
            e["stroke"], e["strokeWidth"] = stroke, sw
        els.append(e)

        if text:
            # 도형에는 글자칸이 없다 — 가운데에 텍스트를 따로 얹는다
            els.append(_text(
                f"{eid}t", px + 6, py, max(pw - 12, 8), max(ph, 8), _esc_br(text),
                size, sp.get("font_color") or _on_color(fill, t),
                weight=700 if sp.get("bold") else 400,
                align="center" if align == "left" else align,
                valign="middle", line=1.25, family=t["fontFamily"]))

    title = str(sd.get("title") or "")
    if title and not sd.get("no_title"):
        head = (MARGIN, 54, W - MARGIN * 2, 70)
        # ★LLM 이 표지 제목을 이미 그려 놨는데 위에 또 찍으면 겹쳐 보인다
        if not _overlaps(head, shapes, sc):
            els.insert(0, _text(f"s{i}h", *head, _esc(title), 32, t["color"],
                                weight=700, valign="middle",
                                family=t["fontFamily"]))
    return {"id": _sid("s", i), "background": bg, "transition": "fade",
            "notes": sd.get("notes", ""), "elements": els}


class _Scale:
    """inch → px. 한 배율로만 키우고 남는 여백을 가운데로 민다."""

    def __init__(self, cw: float, ch: float):
        self.k = min(W / float(cw or 10), H / float(ch or 7.5))
        self.ox = (W - float(cw) * self.k) / 2
        self.oy = (H - float(ch) * self.k) / 2
        self.pt = self.k / 72.0          # 폰트 pt → px (1inch = 72pt)

    def __call__(self, x, y, w, h):
        return (round(self.ox + x * self.k), round(self.oy + y * self.k),
                round(w * self.k), round(h * self.k))


def design_to_doc(design: dict, *, theme: str = DEFAULT_THEME,
                  canvas: tuple[float, float] = (13.333, 7.5),
                  footer: str = "", page_numbers: bool = True) -> dict:
    """LLM 이 만든 설계 JSON → bento/slides 문서.

    도형(shapes)이 있는 장은 좌표 그대로 옮기고, 없는 장은 기존 블록
    렌더러(title/content/table/…)로 떨어뜨린다 — 모델이 두 형식을 섞어
    내놓는 일이 실제로 있다.
    """
    t = theme_of(theme)
    sc = _Scale(*canvas)
    meta = design.get("meta") or {}
    slides = []
    for i, sd in enumerate(design.get("slides") or [], start=1):
        if not isinstance(sd, dict):
            continue
        if sd.get("shapes"):
            s = _design_slide(i, sd, t, sc)
            if i > 1 and page_numbers:
                pg = (W - MARGIN - 90, FOOT, 90, 30)
                if not _overlaps(pg, sd.get("shapes") or [], sc):
                    s["elements"].append(
                        _text(f"s{i}pg", *pg, str(i), 14, t["sub"],
                              align="right", family=t["fontFamily"]))
            if i > 1 and footer:
                ft = (MARGIN, FOOT, 600, 30)
                if not _overlaps(ft, sd.get("shapes") or [], sc):
                    s["elements"].append(
                        _text(f"s{i}ft", *ft, _esc(footer), 14, t["sub"],
                              family=t["fontFamily"]))
        else:
            mk = _MAKERS.get(str(sd.get("type") or "content").lower(),
                             _slide_fallback)
            s = mk(i, sd, t)
        slides.append(s)

    if not slides:
        slides = [_slide_title(1, {"title": meta.get("title") or "빈 문서",
                                   "subtitle": "내용이 없습니다"}, t)]
    return {
        "format": "bento/slides", "version": 1,
        "title": meta.get("title") or "발표자료",
        "size": {"width": W, "height": H},
        "theme": {k: t[k] for k in ("background", "color", "accent", "fontFamily")},
        "slides": slides,
    }


def build_from_design(design: dict, **kw) -> tuple[str, dict]:
    """설계 JSON → (완성된 HTML, 문서 dict)."""
    doc = design_to_doc(design, **kw)
    return embed(doc), doc


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", str(title or "")).strip() or "발표자료"
    return f"{name[:60]}_{datetime.now().strftime('%Y%m%d_%H%M')}.bento.html"
