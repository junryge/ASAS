"""demos_v1/auto_deck.py — 그냥 적은 글을 발표자료로 바꾼다.

왜 이게 있나
    "MD 문법을 알아야 하고, 탭을 고르고, 모델을 고르고" 는 도구가 사람한테
    일을 시키는 것이다. 회의록이든 메모든 붙여 넣으면 나와야 한다.

두 갈래로 만든다
    1) LLM 이 있으면 — **무슨 내용인지만** JSON 으로 내게 한다.
       ★도형 좌표(x/y/w/h)를 모델한테 시키지 않는다. 작은 모델은 겹치거나
         화면 밖으로 나가는 걸 잘 낸다. 배치는 우리가 한다 — 좌우비교·
         카드격자·큰숫자·표 렌더러가 이미 있다.
    2) LLM 이 없거나 실패하면 — 규칙으로 만든다.
       ★"모델이 안 붙어서 못 만들었습니다" 는 답이 아니다. 뭐라도 나와야
         한다. 대신 무엇으로 만들었는지는 정직하게 알린다.

내놓는 것은 기존 블록 형식 그대로다 (title/section/content/table/code/
statement/quote/bignumber/compare2/grid) — 렌더러를 새로 만들지 않으려고.
"""
from __future__ import annotations

import json
import re

MAX_BULLETS = 6                 # 한 장에 담을 글머리 수
MAX_SLIDES = 14                 # 규칙 변환이 무한정 늘어나지 않게

_BULLET = re.compile(r"^\s*(?:[-*+•·○▪◦]|\d{1,2}[.)])\s+(?P<t>.+)$")
_HEAD_MD = re.compile(r"^\s*(?P<h>#{1,6})\s*(?P<t>.+?)\s*#*\s*$")
_HEAD_COLON = re.compile(r"^\s*(?P<t>[^\s].{0,38})\s*[:：]\s*$")
_NUM_HEAD = re.compile(r"^\s*(?P<t>\d{1,2}\s*[.)]\s*\S.{0,40})$")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_FENCE = re.compile(r"^\s*```\s*(?P<lang>[\w+-]*)\s*$")
# "3.2분 → 7.8분", "42건", "88%" 처럼 숫자가 주인공인 줄
_BIGNUM = re.compile(r"^[^\d]{0,6}[\d.,]+\s*[%가-힣a-zA-Z/]{0,8}"
                     r"(?:\s*(?:→|->|~)\s*[\d.,]+\s*[%가-힣a-zA-Z/]{0,8})?$")
_SENT = re.compile(r"(?<=[.!?。])\s+|(?<=[다요])\.\s+")


def _clean(s: str) -> str:
    """마크다운 장식만 걷어낸다 — 내용은 건드리지 않는다."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", str(s or ""))
    s = re.sub(r"(?<!\w)[*_](.+?)[*_](?!\w)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return s.strip()


def _drop_period(s: str) -> str:
    """끝 마침표를 뗀다. ★한 장 안에서 어떤 줄엔 붙고 어떤 줄엔 없으면
    지저분해 보인다 (문장 쪼개기가 앞쪽 마침표만 먹어 실제로 그랬다).
    숫자 뒤('0.30.')는 건드리지 않는다."""
    s = s.strip()
    if len(s) > 1 and s[-1] in ".。" and not s[-2].isdigit():
        return s[:-1].rstrip()
    return s


def _split_sentences(p: str) -> list[str]:
    """긴 단락을 문장으로 쪼갠다. ★통째로 박으면 아무도 안 읽는다."""
    parts = [_drop_period(x) for x in _SENT.split(p) if x and x.strip()]
    parts = [x for x in parts if x]
    return parts or ([_drop_period(p)] if p.strip() else [])


def _is_lone_heading(lines: list[str], i: int) -> bool:
    """'원인으로 보이는 것' 처럼 홀로 선 짧은 줄은 제목이다.

    ★사람은 콜론을 항상 찍지 않는다. 앞이 비어 있고, 짧고, 문장부호로
      끝나지 않고, 다음 줄에 내용이 이어지면 그건 제목으로 읽어야 한다.
      (글머리로 처리하면 제목이 본문 한가운데 섞여 버린다.)
    """
    s = lines[i].strip()
    if not s or len(s) > 30 or _BULLET.match(lines[i]):
        return False
    if s[-1] in ".!?,;:。、":
        return False
    if lines[i][:1].isspace():                 # 들여쓴 줄은 하위 항목이다
        return False
    prev = lines[i - 1].strip() if i > 0 else ""
    nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
    return not prev and bool(nxt)


# ══════════════════════════════════════════════════════════════
# 1) 규칙으로 만들기 — LLM 없이도 뭐라도 나오게
# ══════════════════════════════════════════════════════════════
def plain_to_outline(text: str, *, title_hint: str = "") -> dict:
    """그냥 적은 글 → 블록 목록.

    회의록·메모·MD 아무거나 받는다. 문법을 몰라도 되게 하는 게 목적이라
    '#' 이 없어도, 글머리표가 없어도 동작해야 한다.
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")

    slides: list[dict] = []
    cur: dict | None = None            # 지금 쌓고 있는 content 슬라이드
    doc_title, doc_sub = "", ""

    def flush():
        nonlocal cur
        if cur and cur.get("bullets"):
            slides.append(cur)
        cur = None

    def open_slide(t: str):
        nonlocal cur
        flush()
        cur = {"type": "content", "title": _clean(t)[:60], "bullets": []}

    def add(t: str, level: int = 0):
        nonlocal cur
        t = _clean(t)
        if not t:
            return
        if cur is None:
            open_slide(doc_title or "내용")
        # ★한 장에 너무 많으면 글씨만 작아진다. 넘치면 장을 나눈다.
        if len([b for b in cur["bullets"] if b["level"] == 0]) >= MAX_BULLETS \
                and level == 0:
            head = cur["title"]
            open_slide(head if head.endswith(")") else f"{head} (계속)")
        cur["bullets"].append({"text": t[:120], "level": min(level, 2)})

    i, n = 0, len(lines)
    first_seen = False
    while i < n:
        ln = lines[i]
        s = ln.strip()

        # 코드 블록
        m = _FENCE.match(ln)
        if m:
            lang, body, i = m.group("lang"), [], i + 1
            while i < n and not _FENCE.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1
            if body:
                flush()
                slides.append({"type": "code", "title": "코드",
                               "language": lang or "", "code": "\n".join(body)})
            continue

        # 표
        if _TABLE_ROW.match(ln):
            rows, i = [], i
            while i < n and _TABLE_ROW.match(lines[i]):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells):
                    rows.append([_clean(c) for c in cells])
                i += 1
            if rows:
                flush()
                slides.append({"type": "table",
                               "title": (cur or {}).get("title") or "표",
                               "headers": rows[0], "rows": rows[1:]})
            continue

        if not s:
            i += 1
            continue

        # 맨 앞 짧은 줄 = 제목
        if not first_seen:
            first_seen = True
            cand = _clean(_HEAD_MD.match(ln).group("t") if _HEAD_MD.match(ln) else s)
            if len(cand) <= 60 and not _BULLET.match(ln):
                doc_title = cand
                nxt = lines[i + 1].strip() if i + 1 < n else ""
                if nxt and len(nxt) <= 60 and not _BULLET.match(nxt) \
                        and not _HEAD_MD.match(nxt) and not _TABLE_ROW.match(nxt):
                    doc_sub = _clean(nxt)
                    i += 1
                i += 1
                continue

        # 제목줄 — '#', '항목:', '1) 항목'
        mh = _HEAD_MD.match(ln)
        if mh:
            open_slide(mh.group("t"))
            i += 1
            continue
        if _HEAD_COLON.match(ln) or (_NUM_HEAD.match(ln) and len(s) <= 44
                                     and not _BULLET.match(ln)):
            open_slide(_HEAD_COLON.match(ln).group("t") if _HEAD_COLON.match(ln)
                       else _NUM_HEAD.match(ln).group("t"))
            i += 1
            continue
        if _is_lone_heading(lines, i):
            open_slide(s)
            i += 1
            continue

        # 글머리 — 들여쓰기 깊이를 단계로
        mb = _BULLET.match(ln)
        if mb:
            indent = len(ln) - len(ln.lstrip())
            add(mb.group("t"), 1 if indent >= 2 else 0)
            i += 1
            continue

        # 그냥 문장 — 길면 쪼개서 글머리로
        for sent in _split_sentences(s):
            add(sent)
        i += 1

    flush()

    if doc_title:
        slides.insert(0, {"type": "title", "title": doc_title,
                          "subtitle": doc_sub})
    elif title_hint:
        slides.insert(0, {"type": "title", "title": _clean(title_hint)[:60],
                          "subtitle": ""})

    if len(slides) > MAX_SLIDES:
        kept = slides[:MAX_SLIDES]
        # ★잘라 놓고 말을 안 하면 전부인 줄 안다
        kept.append({"type": "statement", "title": "이하 생략",
                     "statement": f"내용이 길어 {len(slides) - MAX_SLIDES}장을 "
                                  f"줄였습니다 — 나눠서 만들어 보세요"})
        slides = kept
    if not slides:
        slides = [{"type": "title", "title": _clean(title_hint) or "발표자료",
                   "subtitle": "내용이 비어 있습니다"}]
    _promote(slides)
    return {"meta": {"title": doc_title or _clean(title_hint) or "발표자료",
                     "subtitle": doc_sub},
            "slides": slides}


def _promote(slides: list[dict]) -> None:
    """밋밋한 글머리 장을 보기 좋은 종류로 승격 — 제자리에서 바꾼다.

    ppt_builder._apply_smart_layout 과 같은 생각이지만, 여기서는 '규칙으로
    만든' 결과에만 적용한다. (파서를 거친 MD 는 이미 승격돼 있다.)
    """
    for s in slides:
        if s.get("type") != "content":
            continue
        tops = [b for b in s.get("bullets", []) if b.get("level", 0) == 0]
        if len(tops) == 1 and _BIGNUM.match(tops[0]["text"]):
            # ★제목을 먼저 챙긴다. clear() 뒤에 읽으면 빈 문자열이다.
            head = s.get("title", "")
            s.clear()
            s.update({"type": "bignumber", "title": head,
                      "number": tops[0]["text"], "label": ""})
        elif len(tops) == 1 and len(tops[0]["text"]) <= 70:
            s.update({"type": "statement", "statement": tops[0]["text"]})
            s.pop("bullets", None)


# ══════════════════════════════════════════════════════════════
# 2) LLM 에게 시키기 — 좌표가 아니라 '무슨 내용인지' 를 받는다
# ══════════════════════════════════════════════════════════════
AUTO_SYSTEM_PROMPT = """너는 발표자료 기획자다. 사용자가 던진 글(회의록·메모·
문서 아무거나)을 읽고 **발표용 슬라이드 구성**을 만든다. 출력은 **오직 유효한
JSON** 만. 앞뒤 설명도, 코드펜스도 붙이지 마라.

가장 중요한 것 — 너는 **요약**한다. 받은 문장을 그대로 옮기지 마라.
  ❌ 긴 문장 통째로 박기
  ✅ 핵심만 한 줄로 (한 줄 40자 이내)

배치·좌표·색은 신경 쓰지 마라. 그건 프로그램이 한다. 너는 **무슨 내용을
어떤 모양으로 보여줄지**만 고르면 된다.

==== 출력 스키마 ====
{"meta": {"title": "제목", "subtitle": "부제 또는 날짜"},
 "slides": [ <아래 중 하나를 골라 5~8개> ]}

슬라이드 종류 (필요한 것만 골라 섞어 써라):
1. {"type":"section","title":"장 구분 제목"}
2. {"type":"content","title":"제목",
    "bullets":[{"text":"항목","level":0},{"text":"하위","level":1}]}
3. {"type":"statement","title":"제목","statement":"한 줄 결론"}
4. {"type":"bignumber","title":"제목","number":"7.8분","label":"리프터 대기"}
5. {"type":"compare2","title":"제목",
    "left_title":"왼쪽","left_items":["ㄱ","ㄴ"],
    "right_title":"오른쪽","right_items":["ㄷ"]}
6. {"type":"grid","title":"제목",
    "cards":[{"title":"카드","desc":"한 줄 설명"}]}   ← 카드 3~4개
7. {"type":"table","title":"제목","headers":["열1","열2"],
    "rows":[["값","값"]]}
8. {"type":"quote","title":"제목","quote":"인용문","cite":"출처"}

==== 고르는 요령 ====
· 전/후, A vs B, 두 가지 → compare2
· 항목 3~4개 나열 → grid
· 수치 하나가 핵심 → bignumber
· 결론 한 줄 → statement
· 숫자 표 → table
· 그 외 → content

==== 규칙 ====
1. 표지(title)는 넣지 마라 — 프로그램이 meta 로 만든다.
2. 슬라이드 5~8장. 입력이 길어도 늘리지 마라.
3. 글머리는 한 장에 6개까지. 한 줄 40자 이내.
4. 코드는 슬라이드에 넣지 말고 "코드 변경" 같은 한 마디로 바꿔라.
5. 한글 그대로 쓴다.
"""

_ALLOWED = {
    "section": ("title",),
    "content": ("title", "bullets"),
    "statement": ("title", "statement"),
    "bignumber": ("title", "number", "label"),
    "compare2": ("title", "left_title", "left_items",
                 "right_title", "right_items"),
    "grid": ("title", "cards"),
    "table": ("title", "headers", "rows"),
    "quote": ("title", "quote", "cite"),
    "code": ("title", "language", "code"),
    "title": ("title", "subtitle"),
}


def _s(v, limit=120) -> str:
    return _clean(v if isinstance(v, str) else ("" if v is None else str(v)))[:limit]


def _slist(v, limit=8, each=90) -> list[str]:
    if not isinstance(v, list):
        return []
    return [_s(x, each) for x in v[:limit] if _s(x, each)]


def normalize_outline(obj, *, title_hint: str = "") -> dict | None:
    """LLM 이 낸 JSON 을 우리 블록 형식으로 다듬는다.

    ★모델 출력은 못 믿는다. 종류를 지어내거나, 필드 이름을 바꾸거나,
      리스트 자리에 문자열을 넣는다. 살릴 수 있는 건 살리고 나머지는
      버린다 — 반쯤 깨진 걸 그대로 그리면 화면이 이상해진다.
    """
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except Exception:
            return None
    if not isinstance(obj, dict):
        return None
    raw = obj.get("slides")
    if not isinstance(raw, list):
        return None

    out: list[dict] = []
    for sd in raw:
        if not isinstance(sd, dict):
            continue
        kind = str(sd.get("type") or "content").lower().strip()
        if kind not in _ALLOWED:
            kind = "content"
        b: dict = {"type": kind, "title": _s(sd.get("title"), 60)}

        if kind == "content":
            bl = []
            for it in (sd.get("bullets") or [])[:8]:
                if isinstance(it, str):
                    bl.append({"text": _s(it, 110), "level": 0})
                elif isinstance(it, dict):
                    txt = _s(it.get("text"), 110)
                    if txt:
                        try:
                            lv = int(it.get("level", 0) or 0)
                        except (TypeError, ValueError):
                            lv = 0
                        bl.append({"text": txt, "level": max(0, min(lv, 2))})
            if not bl:
                continue                       # 빈 장은 만들지 않는다
            b["bullets"] = bl
        elif kind == "statement":
            b["statement"] = _s(sd.get("statement") or sd.get("text"), 160)
            if not b["statement"]:
                continue
        elif kind == "bignumber":
            b["number"] = _s(sd.get("number"), 24)
            b["label"] = _s(sd.get("label"), 60)
            if not b["number"]:
                continue
        elif kind == "compare2":
            b["left_title"] = _s(sd.get("left_title"), 60)
            b["right_title"] = _s(sd.get("right_title"), 60)
            b["left_items"] = _slist(sd.get("left_items"), 6)
            b["right_items"] = _slist(sd.get("right_items"), 6)
            if not (b["left_title"] and b["right_title"]):
                continue
        elif kind == "grid":
            cards = []
            for c in (sd.get("cards") or [])[:6]:
                if isinstance(c, str):
                    cards.append({"title": _s(c, 40), "desc": ""})
                elif isinstance(c, dict):
                    ct = _s(c.get("title"), 40)
                    if ct:
                        cards.append({"title": ct, "desc": _s(c.get("desc"), 80)})
            if not cards:
                continue
            b["cards"] = cards
        elif kind == "table":
            heads = _slist(sd.get("headers"), 6, 40)
            rows = []
            for r in (sd.get("rows") or [])[:14]:
                if isinstance(r, list):
                    cells = _slist(r, len(heads) or 6, 60)
                    if cells:
                        rows.append(cells)
            if not rows:
                continue
            b["headers"], b["rows"] = heads, rows
        elif kind == "quote":
            b["quote"] = _s(sd.get("quote"), 220)
            b["cite"] = _s(sd.get("cite"), 60)
            if not b["quote"]:
                continue
        elif kind == "code":
            b["code"] = str(sd.get("code") or "")[:2000]
            b["language"] = _s(sd.get("language"), 20)
            if not b["code"].strip():
                continue
        elif kind == "title":
            b["subtitle"] = _s(sd.get("subtitle"), 80)
        elif kind == "section":
            if not b["title"]:
                continue
        out.append(b)

    if not out:
        return None

    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    doc_title = _s(meta.get("title"), 60) or _clean(title_hint)[:60] or "발표자료"
    # 표지는 우리가 만든다 (모델이 넣었으면 그걸 쓴다)
    if out[0]["type"] != "title":
        out.insert(0, {"type": "title", "title": doc_title,
                       "subtitle": _s(meta.get("subtitle"), 80)})
    return {"meta": {"title": doc_title,
                     "subtitle": _s(meta.get("subtitle"), 80)},
            "slides": out[:16]}
