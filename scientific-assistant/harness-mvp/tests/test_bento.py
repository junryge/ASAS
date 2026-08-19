"""Bento 발표자료 — 받는 사람이 아무것도 설치 안 해도 되는 한 파일.

왜 바꿨나
    python-pptx 로 도형 좌표를 일일이 찍어 만들던 결과물이 좋지 않았다.
    Bento 는 문서가 파일 맨 앞 JSON 한 덩어리라 레이아웃을 값으로 다룬다.

★공장 서버에는 인터넷이 없다
    껍데기(676KB)를 저장소에 넣어 두고 문서만 끼운다. 만들 때도 열 때도
    네트워크가 필요 없다 — 이 파일이 그걸 지킨다.

★.pptx 경로는 그대로 둔다
    회사에 pptx 로 내야 하는 자리가 있다. 대체가 아니라 기본값 교체다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from demos_v1 import bento_builder as bb            # noqa: E402

BLOCKS = [
    {"type": "title", "title": "반송 정체 분석", "subtitle": "2026-08-19"},
    {"type": "section", "title": "1. 현황"},
    {"type": "content", "title": "지표", "bullets": [
        {"text": "리프터 대기", "level": 0}, {"text": "3.2 → 7.8분", "level": 1}]},
    {"type": "table", "title": "시간대별", "headers": ["시각", "점수"],
     "rows": [["01:00", "42"], ["02:00", "71"]]},
    {"type": "code", "title": "룰", "language": "python", "code": "def g(s):\n    return s"},
]


class Shell(unittest.TestCase):
    def test_껍데기가_저장소에_있다(self):
        """★공장은 인터넷이 없다 — 받아올 수 없으니 같이 들고 있어야 한다."""
        self.assertTrue(os.path.isfile(bb.SHELL_PATH), bb.SHELL_PATH)
        self.assertGreater(os.path.getsize(bb.SHELL_PATH), 200_000)

    def test_라이선스를_같이_둔다(self):
        self.assertTrue(os.path.isfile(os.path.join(bb.SHELL_DIR, "LICENSE")))
        self.assertTrue(os.path.isfile(os.path.join(bb.SHELL_DIR, "VERSION.txt")))

    def test_껍데기에_문서_자리가_있다(self):
        self.assertIn('id="bento-doc"', bb.read_shell())


class Doc(unittest.TestCase):
    def test_규격_필드를_채운다(self):
        d = bb.build_doc(BLOCKS, title="T")
        self.assertEqual(d["format"], "bento/slides")
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["size"], {"width": 1280, "height": 720})
        self.assertEqual(len(d["slides"]), 5)

    def test_슬라이드_종류마다_다르게_그린다(self):
        d = bb.build_doc(BLOCKS)
        kinds = [{e["type"] for e in s["elements"]} for s in d["slides"]]
        self.assertIn("table", kinds[3], "표 슬라이드가 table 요소를 안 쓴다")
        self.assertIn("shape", kinds[0], "표지에 강조 막대가 없다")

    def test_표는_진짜_table_요소다(self):
        """★사각형과 글자로 표처럼 '그리면' 열 너비도 못 바꾸고 편집도 안 된다."""
        d = bb.build_doc(BLOCKS)
        tbl = next(e for e in d["slides"][3]["elements"] if e["type"] == "table")
        self.assertTrue(tbl["header"])
        self.assertEqual(len(tbl["columns"]), 2)
        self.assertEqual(tbl["rows"][0]["cells"][0]["html"], "시각")
        self.assertEqual(len(tbl["rows"]), 3)          # 머리 1 + 본문 2

    def test_도형에_stroke가_있다(self):
        """★stroke/strokeWidth 를 빼면 도형이 아예 안 그려진다 (실제로 겪음)."""
        d = bb.build_doc(BLOCKS)
        for s in d["slides"]:
            for e in s["elements"]:
                if e["type"] == "shape":
                    self.assertIn("stroke", e)
                    self.assertIn("strokeWidth", e)

    def test_HTML_특수문자를_막는다(self):
        """★본문이 html 로 들어간다 — 그대로 넣으면 화면이 깨진다."""
        d = bb.build_doc([{"type": "content", "title": "t", "bullets": [
            {"text": "<script>alert(1)</script> & <b>", "level": 0}]}])
        html = d["slides"][0]["elements"][2]["html"]
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_빈_입력도_열리는_파일을_준다(self):
        """빈 파일을 주면 '고장' 으로 보인다."""
        d = bb.build_doc([], title="빈")
        self.assertEqual(len(d["slides"]), 1)

    def test_줄이_많으면_글자를_줄인다(self):
        """★넘쳐서 잘리느니 작게라도 한 장에 담는다."""
        few = bb.build_doc([{"type": "content", "title": "t",
                             "bullets": [{"text": f"{i}"} for i in range(4)]}])
        many = bb.build_doc([{"type": "content", "title": "t",
                              "bullets": [{"text": f"{i}"} for i in range(12)]}])
        f = [e for e in few["slides"][0]["elements"] if e["type"] == "text"][1]
        m = [e for e in many["slides"][0]["elements"] if e["type"] == "text"][1]
        self.assertGreater(f["fontSize"], m["fontSize"])

    def test_표가_길면_잘라내고_밝힌다(self):
        d = bb.build_doc([{"type": "table", "title": "t", "headers": ["a"],
                           "rows": [[str(i)] for i in range(40)]}])
        txt = " ".join(e.get("html", "") for e in d["slides"][0]["elements"]
                       if e["type"] == "text")
        self.assertIn("외", txt, "잘라 놓고 말을 안 하면 전부인 줄 안다")

    def test_표지에는_쪽번호를_안_넣는다(self):
        d = bb.build_doc(BLOCKS, page_numbers=True)
        first = " ".join(e.get("id", "") for e in d["slides"][0]["elements"])
        self.assertNotIn("pg", first)
        second = " ".join(e.get("id", "") for e in d["slides"][1]["elements"])
        self.assertIn("s2pg", second)

    def test_테마가_한_벌로_묶여_있다(self):
        """★배경만 바꾸면 어두운 배경에 어두운 글씨가 나온다."""
        for name in bb.THEMES:
            t = bb.theme_of(name)
            for k in ("background", "color", "accent", "sub", "band"):
                self.assertIn(k, t, f"{name} 테마에 {k} 가 없다")

    def test_모르는_테마는_기본값으로(self):
        self.assertEqual(bb.theme_of("없는테마"), bb.THEMES[bb.DEFAULT_THEME])


class SmartLayout(unittest.TestCase):
    """★MD 파서(ppt_builder._apply_smart_layout)는 글머리 슬라이드를
    statement/quote/bignumber/compare2/grid 로 알아서 바꿔 놓는다.
    그래서 실제 덱에 'content' 는 오히려 드물다 — 이걸 안 그리면 제목만
    남고 내용이 통째로 사라진다 (실제로 빈 장이 나왔다)."""

    CASES = {
        "statement": {"type": "statement", "title": "t", "statement": "한 줄 결론"},
        "quote": {"type": "quote", "title": "t", "quote": "인용문", "cite": "출처"},
        "bignumber": {"type": "bignumber", "title": "t", "number": "7.8분",
                      "label": "리프터 대기"},
        "compare2": {"type": "compare2", "title": "t",
                     "left_title": "왼쪽", "left_items": ["ㄱ", "ㄴ"],
                     "right_title": "오른쪽", "right_items": ["ㄷ"]},
        "grid": {"type": "grid", "title": "t", "cards": [
            {"title": "카드1", "desc": "설명1"}, {"title": "카드2", "desc": ""},
            {"title": "카드3", "desc": "설명3"}]},
    }

    def _texts(self, block):
        d = bb.build_doc([block])
        return " ".join(e.get("html", "") for e in d["slides"][0]["elements"]
                        if e["type"] == "text")

    def test_다섯_종류가_내용을_보여준다(self):
        want = {
            "statement": ["한 줄 결론"],
            "quote": ["인용문", "출처"],
            "bignumber": ["7.8분", "리프터 대기"],
            "compare2": ["왼쪽", "오른쪽", "ㄱ", "ㄴ", "ㄷ"],
            "grid": ["카드1", "카드2", "카드3", "설명1", "설명3"],
        }
        for kind, block in self.CASES.items():
            got = self._texts(block)
            for w in want[kind]:
                self.assertIn(w, got, f"{kind} 슬라이드에서 '{w}' 가 사라졌다")

    def test_모든_종류에_렌더러가_있다(self):
        """★파서가 내놓는 종류와 그리는 종류가 어긋나면 조용히 빈 장이 된다."""
        import demos_v1.ppt_builder as pb
        import inspect
        src = inspect.getsource(pb._apply_smart_layout)
        kinds = set(re.findall(r'"type": "([a-z0-9_]+)"', src))
        self.assertTrue(kinds, "파서에서 종류를 못 읽었다")
        self.assertEqual(kinds - set(bb._MAKERS), set(),
                         "파서는 내놓는데 Bento 가 못 그리는 종류가 있다")

    def test_모르는_종류도_빈_장을_안_만든다(self):
        """못 그리겠으면 글자라도 내보낸다 — 빈 장이 제일 나쁘다."""
        got = self._texts({"type": "듣도보도못한것", "title": "t",
                           "wow": "살아남아야 하는 글", "items": ["가", "나"]})
        for w in ("살아남아야 하는 글", "가", "나"):
            self.assertIn(w, got)

    def test_실제_MD가_통째로_살아남는다(self):
        """★회귀 — 글머리 두 줄짜리 장이 빈 장으로 나왔다."""
        import demos_v1.ppt_builder as pb
        md = ("# 반송 정체 분석\n부제\n\n## 1. 현황\n"
              "- 리프터 대기시간이 늘고 있다\n  - 3.2분 → 7.8분\n"
              "- ML 조기예측이 10분 앞을 가리킨다\n")
        d = bb.build_doc(pb.parse_md_to_outline(md)["slides"])
        body = " ".join(e.get("html", "") for s in d["slides"]
                        for e in s["elements"] if e["type"] == "text")
        for w in ("리프터 대기시간이 늘고 있다", "3.2분", "ML 조기예측"):
            self.assertIn(w, body, f"'{w}' 가 슬라이드에서 사라졌다")


class Embed(unittest.TestCase):
    def test_문서를_껍데기에_넣는다(self):
        html, doc = bb.build(BLOCKS, title="T")
        self.assertTrue(html.startswith("<!DOCTYPE html"))
        self.assertGreater(len(html), 200_000)

    def test_꺾쇠를_이스케이프한다(self):
        """★본문에 '</script>' 가 섞이면 파일이 통째로 깨진다."""
        html, _ = bb.build([{"type": "content", "title": "x", "bullets": [
            {"text": "닫는 태그 </script> 포함"}]}])
        m = re.search(r'id="bento-doc"[^>]*>(.*?)</script>', html, re.S)
        raw = m.group(1).strip()
        self.assertNotIn("<", raw, "JSON 블록에 원시 '<' 가 남아 있다")
        self.assertIn("\\u003c", raw)

    def test_되읽을_수_있다(self):
        html, doc = bb.build(BLOCKS, title="T")
        m = re.search(r'id="bento-doc"[^>]*>(.*?)</script>', html, re.S)
        back = json.loads(m.group(1).strip().replace("\\u003c", "<"))
        self.assertEqual(back["format"], "bento/slides")
        self.assertEqual(len(back["slides"]), len(doc["slides"]))

    def test_오프라인_스위치를_미리_켠다(self):
        """★열자마자 bento.page 로 새 버전을 보러 나간다 — 공장 망엔 나갈
        데가 없다. 껍데기에 있는 오프라인 스위치를 켜 두고 내보낸다."""
        html, _ = bb.build(BLOCKS)
        self.assertIn('localStorage.setItem("bento-offline","on")', html)
        # 사람이 툴바에서 끈 걸 다시 켜 버리면 안 된다
        self.assertIn('getItem("bento-offline")===null', html)
        i, j = html.index("bento-offline"), html.index('id="bento-rt"')
        self.assertLess(i, j, "앱이 뜬 뒤에 켜면 이미 나간 뒤다")
        self.assertNotIn("bento-offline",
                         bb.embed(bb.build_doc(BLOCKS), offline=False))

    def test_비밀이_섞이지_않는다(self):
        """★Bento 문서에 collab 키가 있으면 그건 방 초대장이다.
        우리가 만드는 건 절대 그걸 넣지 않는다."""
        _html, doc = bb.build(BLOCKS)
        self.assertNotIn("collab", doc)

    def test_파일명이_안전하다(self):
        n = bb.safe_filename('a/b\\c:d*e?"f<g>h|i')
        self.assertTrue(n.endswith(".bento.html"))
        for ch in '/\\:*?"<>|':
            self.assertNotIn(ch, n)


DESIGN = {
    "meta": {"title": "LLM 설계"},
    "slides": [
        {"type": "custom", "title": "표지", "shapes": [
            {"shape": "textbox", "x": 1, "y": 2.5, "w": 11, "h": 1,
             "text": "반송 정체", "font_size": 44, "bold": True},
            {"shape": "circle", "x": 1, "y": 4, "w": 1.5, "h": 1.5,
             "fill": "#1F6FEB", "text": "1", "font_size": 24},
            {"shape": "arrow_right", "x": 3, "y": 4.5, "w": 2, "h": 0.6,
             "fill": "#888888"},
            {"shape": "arrow_up", "x": 6, "y": 4, "w": 1, "h": 1.5,
             "fill": "#22AA55"},
            {"shape": "diamond", "x": 8, "y": 4, "w": 1.5, "h": 1.5,
             "fill": "#FFCC00", "text": "판정"},
            {"shape": "line", "x": 1, "y": 6.5, "w": 8, "h": 0,
             "line": "#999999", "line_width": 2},
        ]},
        {"type": "content", "title": "블록도 섞여 온다",
         "bullets": [{"text": "모델이 형식을 섞는다", "level": 0}]},
    ],
}


class Design(unittest.TestCase):
    """LLM 이 좌표로 그린 설계(inch) → Bento(px)."""

    def doc(self, **kw):
        return bb.design_to_doc(DESIGN, **kw)

    def test_도형_수가_유지된다(self):
        els = self.doc()["slides"][0]["elements"]
        shapes = [e for e in els if e["type"] == "shape"]
        self.assertEqual(len(shapes), 5, "도형이 사라졌다")

    def test_inch가_px로_바뀐다(self):
        """13.333×7.5 인치 → 1280×720 px. 배율 96."""
        c = next(e for e in self.doc()["slides"][0]["elements"]
                 if e["id"] == "s1e1")
        self.assertEqual((c["x"], c["y"], c["w"], c["h"]), (96, 384, 144, 144))

    def test_비율을_안_망가뜨린다(self):
        """★가로세로를 따로 늘리면 원이 타원이 된다 — 4:3 설계를 넣어 본다."""
        c = next(e for e in bb.design_to_doc(DESIGN, canvas=(10, 7.5))
                 ["slides"][0]["elements"] if e["id"] == "s1e1")
        self.assertEqual(c["w"], c["h"], "정사각형 상자가 찌그러졌다")

    def test_화면_밖으로_안_나간다(self):
        """★4:3 설계를 16:9 에 넣을 때 가로에만 맞추면 아래가 잘려 나간다.
        좁은 쪽에 맞추고 남는 여백을 가운데로 밀어야 한다."""
        d = bb.design_to_doc({"slides": [{"shapes": [
            {"shape": "rect", "x": 0, "y": 0, "w": 10, "h": 7.5}]}]},
            canvas=(10, 7.5))
        e = d["slides"][0]["elements"][0]
        self.assertLessEqual(e["y"] + e["h"], bb.H, "슬라이드 아래로 넘쳤다")
        self.assertLessEqual(e["x"] + e["w"], bb.W, "슬라이드 옆으로 넘쳤다")
        self.assertEqual(e["x"], (bb.W - e["w"]) // 2, "가운데로 안 밀었다")

    def test_도형_종류를_옮긴다(self):
        by = {e["id"]: e for e in self.doc()["slides"][0]["elements"]}
        self.assertEqual(by["s1e1"]["shape"], "ellipse")
        self.assertEqual(by["s1e2"]["shape"], "arrow")
        self.assertEqual(by["s1e4"]["shape"], "path")   # 마름모
        self.assertEqual(by["s1e5"]["shape"], "line")

    def test_세로_화살표는_돌려서_그린다(self):
        """Bento 화살표는 오른쪽만 있다 — 상자를 눕히고 회전시켜야 위를 본다."""
        up = next(e for e in self.doc()["slides"][0]["elements"]
                  if e["id"] == "s1e3")
        self.assertEqual(up["rotation"], -90)
        self.assertGreater(up["w"], up["h"], "상자를 안 눕혔다")

    def test_도형_안_글씨를_따로_얹는다(self):
        """★Bento shape 에는 글자칸이 없다 — 텍스트를 겹쳐 놓지 않으면 사라진다."""
        by = {e["id"]: e for e in self.doc()["slides"][0]["elements"]}
        self.assertIn("s1e1t", by)
        self.assertEqual(by["s1e1t"]["type"], "text")
        self.assertEqual(by["s1e1t"]["valign"], "middle")

    def test_어두운_도형엔_밝은_글씨(self):
        by = {e["id"]: e for e in self.doc()["slides"][0]["elements"]}
        self.assertEqual(by["s1e1t"]["color"], "#FFFFFF")   # 파란 원
        self.assertEqual(by["s1e4t"]["color"], "#111111")   # 노란 마름모

    def test_겹치는_자리엔_제목을_안_찍는다(self):
        """★LLM 이 표지 제목을 이미 그렸는데 위에 또 찍으면 겹쳐 보인다."""
        def ids(y):
            d = bb.design_to_doc({"meta": {}, "slides": [
                {"type": "custom", "title": "제목", "shapes": [
                    {"shape": "textbox", "x": 1, "y": y, "w": 6, "h": 1,
                     "text": "모델이 그린 제목"}]}]})
            return [e["id"] for e in d["slides"][0]["elements"]]

        self.assertNotIn("s1h", ids(0.4), "머리 자리에 도형이 있는데 겹쳐 찍었다")
        self.assertIn("s1h", ids(4.0), "빈 자리인데 제목을 빠뜨렸다")

    def test_도형이_없는_장은_블록으로_그린다(self):
        """모델이 두 형식을 섞어 내놓는 일이 실제로 있다."""
        s = self.doc()["slides"][1]
        self.assertTrue(any(e["type"] == "text" and "모델이" in e.get("html", "")
                            for e in s["elements"]))

    def test_글자도_같이_커진다(self):
        """pt 는 inch 기준이다 — 좌표만 키우고 글자를 두면 개미만 해진다."""
        tb = next(e for e in self.doc()["slides"][0]["elements"]
                  if e["id"] == "s1e0")
        self.assertEqual(tb["fontSize"], round(44 * 96 / 72))

    def test_줄바꿈이_살아남는다(self):
        """★HTML 은 '\\n' 을 공백으로 삼킨다 — 두 줄 카드가 한 줄로 붙었다."""
        d = bb.design_to_doc({"slides": [{"shapes": [
            {"shape": "rect", "x": 1, "y": 1, "w": 4, "h": 2,
             "text": "FREE_FLOW_SPEED\n1분 평균속도"},
            {"shape": "textbox", "x": 1, "y": 4, "w": 4, "h": 2,
             "text": "위\n아래"}]}]})
        by = {e["id"]: e for e in d["slides"][0]["elements"]}
        self.assertIn("<br>", by["s1e0t"]["html"])
        self.assertIn("<br>", by["s1e1"]["html"])

    def test_HTML을_막는다(self):
        d = bb.design_to_doc({"slides": [{"shapes": [
            {"shape": "textbox", "x": 0, "y": 0, "w": 2, "h": 1,
             "text": "<script>x</script>"}]}]})
        self.assertNotIn("<script>", d["slides"][0]["elements"][0]["html"])

    def test_망가진_도형은_건너뛴다(self):
        """LLM 출력은 못 믿는다 — 좌표가 글자여도 전체가 죽으면 안 된다."""
        d = bb.design_to_doc({"slides": [{"shapes": [
            {"shape": "rect", "x": "?", "y": 0, "w": 2, "h": 1},
            {"shape": "rect", "x": 1, "y": 1, "w": 2, "h": 1}]}]})
        self.assertEqual(len(d["slides"][0]["elements"]), 1)

    def test_통째로_HTML까지_나온다(self):
        html, doc = bb.build_from_design(DESIGN)
        self.assertTrue(html.startswith("<!DOCTYPE html"))
        self.assertEqual(len(doc["slides"]), 2)


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import demos_v1
            cls.client = demos_v1.create_app().test_client()
        except Exception as e:
            raise unittest.SkipTest(f"앱을 못 띄운다: {e}")

    MD = ("# 제목\n부제\n\n## 절\n- 하나\n  - 둘\n\n"
          "| a | b |\n|---|---|\n| 1 | 2 |\n")

    def test_MD로_만든다(self):
        r = self.client.post("/api/ppt/bento", json={"md": self.MD, "theme": "hynix"})
        self.assertEqual(r.status_code, 200, r.data[:200])
        d = r.get_json()
        self.assertGreater(d["slide_count"], 1)
        self.assertTrue(d["filename"].endswith(".bento.html"))
        # 결과 패널이 '슬라이드 구성' 을 보여 준다 — 비면 만들다 만 것처럼 보인다
        self.assertEqual(len(d["slides_summary"]), d["slide_count"])
        self.assertTrue(any(s["title"] for s in d["slides_summary"]))

    def test_내려받는다(self):
        d = self.client.post("/api/ppt/bento", json={"md": self.MD}).get_json()
        r = self.client.get(d["download_url"])
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data.startswith(b"<!DOCTYPE html"))
        self.assertGreater(len(r.data), 200_000)

    def test_빈_입력은_400(self):
        self.assertEqual(self.client.post("/api/ppt/bento", json={}).status_code, 400)

    def test_테마_목록을_준다(self):
        d = self.client.get("/api/ppt/bento/themes").get_json()
        self.assertIn(d["default"], [t["id"] for t in d["themes"]])

    def test_LLM_설계가_bento로_나온다(self):
        """★설계는 LLM 이 한다. 바뀐 건 '무엇으로 그리느냐' 뿐이다.
        모델을 부르지 않고, 부르는 자리만 가짜로 바꿔 경로를 확인한다."""
        from demos_v1 import routes_ppt as rp
        seen = {}

        def fake(model_id, user_input, theme, max_tokens=8192,
                 canvas=rp.PPTX_CANVAS):
            seen["canvas"] = canvas
            return dict(DESIGN), None

        real, rp._call_llm_for_design = rp._call_llm_for_design, fake
        try:
            r = self.client.post("/api/ppt/from-llm", json={
                "input": "반송 정체", "model": "any", "theme": "hynix"})
            self.assertEqual(r.status_code, 200, r.data[:300])
            d = r.get_json()
            self.assertEqual(d["format"], "bento")
            self.assertTrue(d["filename"].endswith(".bento.html"))
            self.assertEqual(d["slide_count"], 2)
            # 16:9 로 그릴 거면 LLM 한테도 16:9 캔버스를 줘야 한다
            self.assertEqual(seen["canvas"], rp.BENTO_CANVAS)
            body = self.client.get(d["download_url"]).data
            self.assertTrue(body.startswith(b"<!DOCTYPE html"))

            r2 = self.client.post("/api/ppt/from-llm", json={
                "input": "x", "model": "any", "format": "pptx"})
            self.assertEqual(r2.status_code, 200, r2.data[:300])
            self.assertTrue(r2.get_json()["filename"].endswith(".pptx"))
            self.assertEqual(seen["canvas"], rp.PPTX_CANVAS)
        finally:
            rp._call_llm_for_design = real

    def test_프롬프트에_캔버스가_박힌다(self):
        """★자리표시자를 안 채우면 모델이 '{CW}인치' 를 글자 그대로 읽는다."""
        from demos_v1 import routes_ppt as rp
        p = rp._design_prompt("dark", rp.BENTO_CANVAS)
        for ph in ("{CANVAS}", "{CW}", "{CH}"):
            self.assertNotIn(ph, p)
        self.assertIn("13.333인치 × 7.5인치", p)
        self.assertIn("≤ 13.333", p)
        self.assertIn("≤ 10,", rp._design_prompt("dark", rp.PPTX_CANVAS))

    def test_pptx는_그대로_동작한다(self):
        """★대체가 아니다 — 회사에 pptx 로 내야 하는 자리가 있다."""
        r = self.client.post("/api/ppt/from-md", json={"md": self.MD})
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertTrue(r.get_json()["filename"].endswith(".pptx"))


if __name__ == "__main__":
    unittest.main()
