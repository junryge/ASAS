"""화이트보드 1단계 — 답변 속 ```mermaid 글을 서버가 그림(SVG)으로 그린다.

폐쇄망이라 mermaid.min.js 를 받을 수 없다(CDN · npm 모두 막힘). 그래서 데모스 서버의
demos_v1/wb_render.py 가 Mermaid 글을 직접 읽어 배치하고 SVG 로 그리고,
/api/whiteboard/render 로 데모스 · 개인 에이전트 창 · 코딩 어시스턴트가 같이 쓴다.

여기서 지키는 것
  · LLM 이 흔히 쓰는 문법이 실제로 그려진다 — 특히 띄어쓰기 없는 A-->B (한때 못 그렸다)
  · 글자는 모두 이스케이프된다 — 그림은 innerHTML 로 들어가므로 <script> 가 새면 안 된다
  · 못 그리는 글은 ok=False 와 몇째 줄인지로 돌려준다 (답변 전체가 죽지 않는다)
  · 라우트 계약(하나 · 여러 개 · 크기 제한)
  · 화면 연결 — 세 화면이 whiteboard.js 를 싣고, 마크다운 변환기가 mermaid 원문을
    빈 줄에서 쪼개지 않는다
"""
from __future__ import annotations

import html
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from demos_v1 import wb_render  # noqa: E402


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _texts(svg):
    return re.findall(r">([^<>]+)</text>", svg)


# LLM 답변에 흔히 나오는 모양들 — 하나라도 못 그리면 사용자는 그림 대신 원문을 본다
COMMON = {
    "띄어쓰기 없는 화살표": "graph TD\nA-->B",
    "모양 이어 쓰기": "flowchart LR\nA[시작]-->B(처리)-->C{판단}",
    "선 글자(파이프)": "flowchart TD\nA{ok?}-->|예|B[진행]\nA-->|아니오|C[중지]",
    "선 가운데 글자": "flowchart TD\nA-- 글 -->B\nB-. 점선 글 .->C\nC== 굵은 글 ==>D",
    "선 종류": "flowchart LR\nA-.->B\nB==>C\nC---D\nD<-->E\nE --o F\nF --x G",
    "꾸밈 줄(무시)": "flowchart TD\nclassDef red fill:#f00;\nA:::red --> B\nclass B red\n"
                    "style A fill:#f9f\nlinkStyle 0 stroke:#f00\nclick A \"https://x\" \"팁\"",
    "묶음": "flowchart TB\nsubgraph one [첫 묶음]\n  direction LR\n  a1-->a2\nend\n"
            "subgraph \"두 번째\"\n  b1-->b2\nend\none --> b1",
    "& 묶어 잇기": "flowchart TD\nA & B --> C & D",
    "init · 주석": "%%{init: {'theme':'dark'}}%%\nflowchart TD\n%% 주석\nA-->B",
    "세미콜론": "graph LR;\nA-->B;\nB-->C;",
    "v11 모양 문법": "flowchart TD\nA@{ shape: diam, label: \"판단\" } --> B",
    "선 이름": "flowchart TD\nA e1@--> B",
    "시퀀스 전부": "sequenceDiagram\nautonumber\nactor U as 사용자\nparticipant S as 서버\n"
                "U->>+S: 요청\nS-->>-U: 응답\nU-)S: 비동기\nS-xU: 실패\nNote over U,S: 메모\n"
                "loop 1분마다\nU->>S: ping\nend\nalt 성공\nS->>U: ok\nelse 실패\nS->>U: fail\nend",
    "ERD 기호": "erDiagram\nCUSTOMER ||--o{ ORDER : places\nORDER ||--|{ LINE-ITEM : contains\n"
               "CUSTOMER {\n  string id PK \"번호\"\n  string name\n}",
    "ERD 낱말": "erDiagram\nCAR 1 to zero or more NAMED-DRIVER : allows\nPERSON many(0) optionally to 1 CAR : drives",
    "상태도": "stateDiagram-v2\n[*] --> 대기\n대기 --> 수집 : 60초\nstate 판정 {\n  [*] --> 점수\n  점수 --> [*]\n}\n"
             "수집 --> 판정\n판정 --> [*]",
    "상태 설명": "stateDiagram-v2\nstate \"긴 이름\" as LN\nLN : 설명\nstate s2 : 또 설명\nLN --> s2",
    "분기 · 합류 · 선택": "stateDiagram-v2\nstate f <<fork>>\nstate j <<join>>\nstate c <<choice>>\n"
                     "[*] --> f\nf --> A\nf --> B\nA --> j\nB --> j\nj --> c\nc --> C : n < 0\nc --> D : n >= 0",
}


class 흔한_문법이_그려진다(unittest.TestCase):
    def test_모두_그려지고_올바른_XML_이다(self):
        for name, src in COMMON.items():
            with self.subTest(name):
                r = wb_render.render(src)
                self.assertTrue(r["ok"], f"{name}: {r.get('error')} ({r.get('line')}째 줄)")
                ET.fromstring(r["svg"])                          # 짝이 맞는 XML — 이스케이프가 빠지면 깨진다
                self.assertGreater(r["w"], 0)
                self.assertGreater(r["h"], 0)

    def test_띄어쓰기_없는_화살표는_화살촉이다(self):
        """★회귀. 'A-->B' 가 '상자 이름이 와야 할 자리입니다' 로 실패했다('>' 뒤에 이름이 붙어서)."""
        r = wb_render.render("flowchart TD\nA-->B")
        self.assertTrue(r["ok"], r.get("error"))
        self.assertIn("-arr)", r["svg"])                           # 화살촉 표시가 붙었다
        self.assertEqual(sorted(_texts(r["svg"])), ["A", "B"])

    def test_상태_설명은_이름_대신_보인다(self):
        """Mermaid 와 같게 — 'state "긴 이름" as LN' 이면 LN 은 안 보이고 '긴 이름' 이 보인다."""
        t = _texts(wb_render.render(COMMON["상태 설명"])["svg"])
        self.assertIn("긴 이름", t)
        self.assertIn("또 설명", t)
        self.assertNotIn("LN", t)

    def test_제목과_요약(self):
        r = wb_render.render("---\ntitle: 주문 흐름\n---\nflowchart LR\nA-->B")
        self.assertEqual(r["title"], "주문 흐름")
        self.assertTrue(r["desc"].startswith("흐름도"))
        self.assertEqual(wb_render.render("flowchart LR\nA-->B")["title"], "")   # 글쓴이 제목만


class 글자는_이스케이프된다(unittest.TestCase):
    # 따옴표 안에 넣을 것(Mermaid 는 따옴표 안의 " 를 #quot; 로 쓴다) · 따옴표 밖에 넣을 것
    EVIL_Q = "<script>alert(1)</script><img src=x onerror=alert(2)></style>&amp;"
    EVIL = '<script>alert(1)</script>"><img src=x onerror=alert(2)></style>&'

    def test_어느_자리에_넣어도_태그가_새지_않는다(self):
        q, e = self.EVIL_Q, self.EVIL
        srcs = [
            f'flowchart TD\nA["{q}"] -->|"{q}"| B[{e}]\nsubgraph S ["{q}"]\nB\nend',
            f"flowchart TD\nA-- {e.replace('-', '')} -->B",
            f"sequenceDiagram\nparticipant A as {e}\nA->>B: {e}\nNote over A: {e}\nloop {e}\nA->>B: x\nend",
            f'erDiagram\nA ||--o{{ B : "{q}"\nA {{\n  string name "{q}"\n}}',
            f'stateDiagram-v2\nstate "{q}" as X\nX : {e}\n[*] --> X\nX --> Y : {e}',
            f"---\ntitle: {e}\n---\nflowchart TD\nA-->B",
        ]
        for src in srcs:
            with self.subTest(src[:30]):
                r = wb_render.render(src)
                self.assertTrue(r["ok"], r.get("error"))
                svg = r["svg"]
                ET.fromstring(svg)
                low = svg.lower()
                self.assertNotIn("<script", low)
                self.assertNotIn("<img", low)
                self.assertEqual(low.count("</style>"), 1)          # 그림 자신의 <style> 하나뿐
                self.assertIn("alert(1)", svg)                       # 태그만 빠지고 글은 남는다

    def test_꺾쇠가_든_글은_그대로_보인다(self):
        """태그로 보이는 것만 뺀다 — 코드 그림의 List<T> · 비교식이 사라지면 뜻이 바뀐다."""
        r = wb_render.render('flowchart TD\nA["Map<String, Int>"] --> B{a < b and c > d}\n'
                             'B --> C[List#lt;T#gt;]\nC --> D["<b>굵게</b>"]')
        self.assertTrue(r["ok"], r.get("error"))
        t = [html.unescape(x) for x in _texts(r["svg"])]
        for want in ("Map<String, Int>", "a < b and c > d", "List<T>", "굵게"):
            self.assertIn(want, t)

    def test_click_줄의_주소는_그림에_들어가지_않는다(self):
        r = wb_render.render('flowchart TD\nA-->B\nclick A "javascript:alert(1)" "팁"\nclick B href "https://x.y"')
        self.assertTrue(r["ok"], r.get("error"))
        self.assertNotIn("javascript", r["svg"])
        self.assertNotIn("x.y", r["svg"])


class 못_그리는_글(unittest.TestCase):
    def test_틀린_줄_번호를_알려_준다(self):
        r = wb_render.render("flowchart TD\n    A[시작] --> B{확인}\n    B -->|예| ")
        self.assertFalse(r["ok"])
        self.assertEqual(r["line"], 3)
        self.assertTrue(r["error"])

    def test_아직_안_그리는_종류는_종류를_알려_준다(self):
        for kind, src in (("pie", 'pie title x\n"a" : 1'), ("gantt", "gantt\ntitle x"),
                          ("classDiagram", "classDiagram\nclass A")):
            r = wb_render.render(src)
            self.assertFalse(r["ok"])
            self.assertEqual(r["kind"], kind)

    def test_빈_글과_너무_긴_글(self):
        self.assertFalse(wb_render.render("")["ok"])
        r = wb_render.render("flowchart TD\n" + "A-->B\n" * 10000)
        self.assertFalse(r["ok"])
        self.assertIn("너무 깁니다", r["error"])

    def test_이상한_글이_와도_예외가_새지_않는다(self):
        for src in ("flowchart TD\n" + "[" * 500, "sequenceDiagram\n" + "alt x\n" * 300,
                    "stateDiagram-v2\n" + "state a {\n" * 200, "erDiagram\nA {\n", None, 123):
            r = wb_render.render(src)
            self.assertIn("ok", r)


class 라우트(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from flask import Flask
        from demos_v1.whiteboard import register_whiteboard_routes, MAX_ITEMS
        app = Flask("wb_test")
        register_whiteboard_routes(app)
        cls.c = app.test_client()
        cls.MAX_ITEMS = MAX_ITEMS

    def test_하나(self):
        r = self.c.post("/api/whiteboard/render", json={"src": "flowchart TD\nA-->B"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertTrue(d["svg"].startswith("<svg"))

    def test_여러_개는_순서대로(self):
        r = self.c.post("/api/whiteboard/render", json={"items": [
            {"src": "flowchart TD\nA-->B"}, {"src": "pie\n\"a\": 1"}, {"src": 5}]})
        self.assertEqual(r.status_code, 200)
        items = r.get_json()["items"]
        self.assertEqual([i["ok"] for i in items], [True, False, False])
        self.assertEqual(items[1]["kind"], "pie")

    def test_너무_많으면_413(self):
        r = self.c.post("/api/whiteboard/render",
                        json={"items": [{"src": "flowchart TD\nA-->B"}] * (self.MAX_ITEMS + 1)})
        self.assertEqual(r.status_code, 413)

    def test_잘못된_본문은_400(self):
        self.assertEqual(self.c.post("/api/whiteboard/render", json={"items": "x"}).status_code, 400)
        self.assertEqual(self.c.post("/api/whiteboard/render", data="x",
                                     headers={"Content-Type": "text/plain"}).status_code, 400)

    def test_정보(self):
        d = self.c.get("/api/whiteboard/info").get_json()
        self.assertEqual(set(d["supported"]), {"flowchart", "sequence", "er", "state"})


class 화면_연결(unittest.TestCase):
    """세 화면이 whiteboard.js 를 싣고, 마크다운 변환기가 mermaid 원문을 지킨다."""

    def test_데모스_본창(self):
        html = _read("demos_v1", "templates", "index.html")
        self.assertIn('<script src="/static/whiteboard.js', html)
        self.assertIn("WB.watch(document.getElementById('msgs'))", html)
        # ★renderMd 는 빈 줄에서 문단을 나누고 * 를 기울임으로 바꾼다 — mermaid 는 그 전에 싸 둔다
        i_mer = html.index("s=s.replace(/```mermaid")
        i_gen = html.index("s=s.replace(/```(\\w*)\\s*([\\s\\S]*?)```/g")
        self.assertLess(i_mer, i_gen)
        blk = html[i_mer:i_gen]
        for ent in ("&#10;", "&#42;", "&#96;"):
            self.assertIn(ent, blk)

    def test_개인_에이전트_창(self):
        html = _read("demos_v1", "templates", "agent_window.html")
        self.assertIn('<script src="/static/whiteboard.js', html)
        self.assertIn("WB.watch(document.getElementById('chatMsgs'))", html)

    def test_코딩_어시스턴트(self):
        html = _read("code_assist_v1", "static", "index.html")
        self.assertIn('<script src="/static/whiteboard.js', html)   # /code/ 아래가 아니라 데모스 /static
        js = _read("code_assist_v1", "static", "chat.js")
        self.assertIn("WB.renderIn(root)", js)                        # 스트리밍이 끝난 뒤
        self.assertIn("WB.renderIn(c)", js)                           # 지난 세션 다시 열기
        # 폐쇄망에선 marked 대신 miniRenderMd 가 돈다 — 여기도 mermaid 를 먼저 싼다
        mini = js[js.index("function miniRenderMd"):]
        self.assertLess(mini.index("```mermaid"), mini.index("// 코드블록"))

    def test_라우트_등록과_정적_파일(self):
        self.assertIn("register_whiteboard_routes(app)", _read("demos_v1", "__init__.py"))
        js = _read("demos_v1", "static", "whiteboard.js")
        self.assertIn("window.WB =", js)
        self.assertIn("'/api/whiteboard/render'", js)


if __name__ == "__main__":
    unittest.main()
