# -*- coding: utf-8 -*-
"""컬럼 → 점수 문서 — 예측기 소스에서 직접 읽는다.

왜 생성하나
    "FAB 별로 어느 컬럼을 쓰고, 그게 어떻게 점수가 되나" 를 손으로 적어 두면
    임계 하나 바뀔 때 문서만 옛날 값으로 남는다. 그 문서가 고객에게 나간다.

무엇을 지키나
    ① 예측기를 **import 하지 않는다** — ast 로 읽는다. 문서 하나 만들자고
       로그 폴더를 만들고 업로더를 붙일 이유가 없다
    ② 못 읽은 값은 '읽지 못함' 이라고 적는다 — 지어내지 않는다
    ③ 소스를 못 찾아도 문서는 나온다 (어디를 봐야 하는지 알려 준다)
"""
import io
import os
import re
import unittest

from . import util

DOC = os.path.join(util.BASE, "컬럼흐름_문서.py")


def _mod():
    import importlib.util
    import sys
    if not os.path.isfile(DOC):
        raise unittest.SkipTest("컬럼흐름_문서.py 가 없다")
    sys.path.insert(0, util.BASE)
    spec = importlib.util.spec_from_file_location("컬럼흐름", DOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SRC = '''
WINDOW_MIN = 90
TH_RA = _TD('TH_RA', {'M16HUB': 9.0, 'M14': 3.3})
TH_FLOW_X3_0 = _T('TH_FLOW_X3_0', 3.0)
TH_FLOW_X2_0 = _T('TH_FLOW_X2_0', 2.0)
TH_FLOW_X1_5 = _T('TH_FLOW_X1_5', 1.5)
RA_COL = {'M16HUB': 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN'}
EVENT_FIELDS = ['datetime', 'unified_risk_score', 'M14_score']

def iter_unified_rows(filepath):
    for row in []:
        d = {}
        g = row.get
        d['M16HUB'] = {
            'ra': safe_float(g('M16HUB.QUE.TIME.AVGTOTALTIME1MIN')),
            'rd_fab': safe_float(g('M16HUB.STRATE.ALL.FABSTORAGERATIO')),
            'lifters': {lid: safe_int(g(f'M16HUB.LFT.{lid}.TOTAL_CURRENTQCNT'))
                        for lid in LIFTER_IDS},
        }
        yield d

def eval_area_rules(area, window):
    ra_pts = 10 if out['ra_trig'] else 0
    rd_pts = 7 if out['rd_trig'] else 0
    mc_pts = 10 * out['maxcapa_changed_n']
    out['area_score'] = min(50, s)

def evaluate_unified(t, area_results, flow_result, propagation_history):
    for node, info in flow_result.items():
        if info['level'] == '심각':
            flow_score += 30
        elif info['level'] == '위험':
            flow_score += 15
        elif info['level'] == '주의':
            flow_score += 5
    sla_score = sum(5 for r in area_results.values() if r.get('sla_trig'))
    sorter_score = sum(3 for r in area_results.values() if r.get('sorter_trig'))
    mc_score += 10 * n
    unified_risk_score = min(500, layer1_total + flow_score)
    if unified_risk_score >= 250:
        unified_risk_level = '매우위험'
    elif unified_risk_score >= 30:
        unified_risk_level = '관심'
    else:
        unified_risk_level = '정상'
    avg_window = list(flow_history)[-30:]
# =
'''


class 소스에서_읽는다(unittest.TestCase):

    def setUp(self):
        self.m = _mod()

    def test_TD_는_두번째_인자가_기본값이다(self):
        """_TD('TH_RA', {…}) — 첫 인자는 열쇠 이름이고 값이 아니다."""
        C = self.m.read_consts(SRC)
        self.assertEqual(C["TH_RA"], {"M16HUB": 9.0, "M14": 3.3})
        self.assertEqual(C["WINDOW_MIN"], 90)
        self.assertEqual(C["RA_COL"]["M16HUB"],
                         "M16HUB.QUE.TIME.AVGTOTALTIME1MIN")

    def test_FAB별로_읽는_컬럼을_뽑는다(self):
        ex = self.m.read_extract_map(SRC)
        self.assertIn("M16HUB", ex)
        keys = {i["key"] for i in ex["M16HUB"]}
        self.assertEqual(keys, {"ra", "rd_fab", "lifters"})
        ra = next(i for i in ex["M16HUB"] if i["key"] == "ra")
        self.assertIn("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", ra["cols"])
        self.assertEqual(ra["kind"], "실수")

    def test_f문자열_컬럼은_패턴으로_적는다(self):
        """리프터는 호기 번호를 붙여 읽는다 — 컬럼 이름이 하나가 아니다."""
        ex = self.m.read_extract_map(SRC)
        lf = next(i for i in ex["M16HUB"] if i["key"] == "lifters")
        self.assertTrue(any("패턴" in c for c in lf["cols"]),
                        "f-string 컬럼을 그냥 적어 버렸다: {}".format(lf["cols"]))

    def test_배점을_읽는다(self):
        p = self.m.read_points(SRC)
        self.assertEqual(p["ra_pts"]["pts"], 10)
        self.assertEqual(p["rd_pts"]["pts"], 7)
        self.assertEqual(p["mc_pts"]["pts"], 10)
        self.assertEqual(p["_cap"], 50)

    def test_융합_규칙을_읽는다(self):
        u = self.m.read_unified(SRC)
        self.assertEqual(u["flow"], {"심각": 30, "위험": 15, "주의": 5})
        self.assertEqual(u["sla"], 5)
        self.assertEqual(u["sorter"], 3)
        self.assertEqual(u["mc"], 10)
        self.assertEqual(u["cap"], 500)
        self.assertIn((250, "매우위험"), u["levels"])
        self.assertIn((0, "정상"), u["levels"])

    def test_흐름_배수를_읽는다(self):
        f = self.m.read_flow_th(SRC)
        self.assertEqual(f["심각"], 3.0)
        self.assertEqual(f["위험"], 2.0)
        self.assertEqual(f["주의"], 1.5)
        self.assertEqual(f["_avg"], 30)


class 예측기를_돌리지_않는다(unittest.TestCase):
    """예측기를 import 하면 로그 폴더를 만들고 thresholds.json 을 찾아 읽고
    업로더를 붙인다. 문서 하나 만들자고 그럴 이유가 없다."""

    def test_import_안_한다(self):
        src = io.open(DOC, encoding="utf-8").read()
        self.assertNotIn("import hubroom_predictor", src)
        self.assertNotIn("exec_module", src)
        self.assertIn("ast.parse", src)


class 컬럼마다_설명이_있다(unittest.TestCase):
    """131개를 손으로 적으면 컬럼이 늘 때 빠진다. 꼴(패턴)로 적고, 빠진 것이
    생기면 여기서 잡는다 — 고객 문서에 빈 칸이 나가면 안 된다."""

    def test_모든_출력_컬럼에_설명이_있다(self):
        m = _mod()
        d = m.build()
        if not d["ok"]:
            self.skipTest("예측기 소스를 못 찾았다")
        ef = d["C"].get("EVENT_FIELDS") or []
        self.assertGreater(len(ef), 100, "출력 컬럼을 못 읽었다")
        miss = [c["col"] for c in m.explain_cols(ef, 50) if not c["ok"]]
        self.assertEqual(miss, [], "설명 없는 컬럼: {}".format(miss[:10]))

    def test_영역_이름만_갈아_끼운다(self):
        m = _mod()
        got = {c["col"]: c for c in m.explain_cols(
            ["M14_score", "M16A_pts_RB_fast", "sla_M16B", "M14B_ra_count"], 50)}
        self.assertIn("M14", got["M14_score"]["title"])
        self.assertIn("R-B 반입급증(10분)", got["M16A_pts_RB_fast"]["title"])
        self.assertIn("M16B", got["sla_M16B"]["title"])
        self.assertIn("M14B", got["M14B_ra_count"]["title"])

    def test_모르는_컬럼은_모른다고_한다(self):
        """설명을 지어내면 고객이 그걸 근거로 쓴다."""
        m = _mod()
        got = m.explain_cols(["듣도보도못한컬럼"], 50)[0]
        self.assertFalse(got["ok"])
        self.assertEqual(got["title"], "")


class 그림이_있다(unittest.TestCase):
    """표만 있으면 안 읽는다. 그림도 **소스에서 읽은 값**으로 그려서
    임계가 바뀌면 그림도 같이 바뀌게 둔다 — 사람은 그림을 먼저 믿는다."""

    def setUp(self):
        self.m = _mod()
        self.d = self.m.build()
        if not self.d["ok"]:
            self.skipTest("예측기 소스를 못 찾았다")

    def test_영역마다_한_장씩_있다(self):
        """HUBROOM 한 장만 있으면 다른 FAB 은 자기 그림이 없다."""
        h = self.m.render(self.d)
        areas = self.d["C"].get("AREAS_ALL") or []
        self.assertGreaterEqual(len(areas), 8)
        for i, ar in enumerate(areas, 1):
            self.assertIn("그림 A-{} · {}".format(i, ar), h,
                          "{} 그림이 없다".format(ar))
        for t in ("그림 B", "그림 C"):
            self.assertIn(t, h, "빠졌다: " + t)
        self.assertGreaterEqual(h.count("<svg"), len(areas) + 2)

    def test_영역마다_붙는_룰이_다르다(self):
        """M16 은 R-B 만, M16_PKT·M16_WT 는 R-A′ 만 붙는다 —
        모든 영역에 같은 그림을 그리면 거짓말이 된다."""
        names = lambda ar: [x[0] for x in self.m.area_rules(self.d, ar)]
        hub = names("M16HUB")
        self.assertTrue(any(n.startswith("R-C") for n in hub))
        self.assertTrue(any(n.startswith("MAXCAPA") for n in hub))
        m16 = names("M16")
        self.assertTrue(all(n.startswith("R-B") for n in m16), m16)
        for ar in ("M16_PKT", "M16_WT"):
            self.assertTrue(all(n.startswith("R-A") for n in names(ar)),
                            names(ar))
        # M14 의 R-C′ 는 리프터가 아니라 CNV 쏠림이다
        self.assertIn("R-C′ CNV 쏠림", names("M14"))

    def test_M16_이_M16A_컬럼을_안_가져간다(self):
        """area 로 startswith 만 하면 'M16' 이 'M16A.…' 까지 집어삼킨다."""
        rows = self.m.area_rules(self.d, "M16")
        for _, cols, _, _ in rows:
            for c in cols:
                self.assertFalse(c.startswith(("M16A.", "M16B.", "M16HUB.")),
                                 "M16 이 남의 컬럼을 가져갔다: " + c)

    def test_받을_수_있는_최대를_적는다(self):
        """안 적으면 '왜 M16 은 점수가 낮냐' 를 매번 다시 설명해야 한다."""
        g = self.m.svg_area(self.d, "M16", 6)
        self.assertIn("받을 수 있는 최대", g)
        self.assertIn("다 못 채운다", g)

    def test_그림_숫자가_소스에서_온다(self):
        """그림에 손으로 적은 숫자가 있으면 임계가 바뀔 때 그림만 옛날 값이
        된다. 표보다 더 나쁘다."""
        g = self.m.svg_area(self.d, "M16HUB", 1)
        ra = (self.d["C"].get("TH_RA") or {}).get("M16HUB")
        self.assertIn(str(ra), g, "R-A′ 임계가 그림에 없다")
        self.assertIn("min({}".format(self.d["pts"]["_cap"]), g)
        u = self.m.svg_unified(self.d)
        self.assertIn("min({}".format(self.d["uni"]["cap"]), u)
        self.assertIn(str(self.d["uni"]["flow"]["심각"]), u)

    def test_계산식_임계도_채운다(self):
        """TH_RB_10 은 dict 컴프리헨션이라 ast 로 못 읽는다. 비워 두면
        그림에 '—' 가 찍혀 '임계가 없다' 로 보인다."""
        C = self.d["C"]
        self.assertIsInstance(C.get("TH_RB_10"), dict)
        for k, v in (C.get("TH_RB_30") or {}).items():
            self.assertGreaterEqual(C["TH_RB_10"].get(k, 0), 10)
        g = self.m.svg_area(self.d, "M16HUB")
        # 자동으로 만든 값이라는 것을 그림에 밝혀야 한다
        self.assertIn("30분 임계의", g)
        th10 = C["TH_RB_10"]["M16HUB"]
        self.assertIn("+{} 이상".format(th10), g)

    def test_그림이_잘리지_않는다(self):
        """viewBox 높이가 내용보다 작으면 아래가 잘려 나간다."""
        import re as _re
        for g in (self.m.svg_area(self.d, "M16HUB"),
                  self.m.svg_area(self.d, "M16"),
                  self.m.svg_area(self.d, "M16_WT"),
                  self.m.svg_unified(self.d), self.m.svg_split(self.d)):
            vb = _re.search(r'viewBox="0 0 \d+ (\d+)"', g)
            self.assertTrue(vb)
            H = int(vb.group(1))
            ys = [float(y) for y in _re.findall(r'\sy="([\d.]+)"', g)]
            self.assertLessEqual(max(ys), H - 8,
                                 "내용이 viewBox({}) 밖으로 나간다".format(H))

    def test_바깥_그림_라이브러리를_안_쓴다(self):
        """사내망에는 CDN 이 없고, 이 문서는 파일 하나로 열려야 한다."""
        src = io.open(DOC, encoding="utf-8").read()
        for bad in ("http://", "https://", "<script"):
            self.assertNotIn(bad, self.m.render(self.d),
                             "문서가 바깥을 본다: " + bad)


class 문서가_나온다(unittest.TestCase):

    def test_실제_소스로_만들어진다(self):
        m = _mod()
        d = m.build()
        h = m.render(d)
        for t in ("area_score", "unified_risk_score", "M16A_HUBROOM_PR.CSV",
                  "영역분리", "iter_unified_rows"):
            self.assertIn(t, h, "문서에 없다: " + t)
        if d["ok"]:
            # 소스를 찾았으면 숫자가 채워져 있어야 한다
            self.assertNotIn("읽지 못함", h, "값을 못 읽은 자리가 있다")
            self.assertIn("min(50", h)
            self.assertIn("min(500", h)
            self.assertGreaterEqual(len(d["extract"]), 5)

    def test_소스가_없어도_문서는_나온다(self):
        """못 찾았다고 빈손으로 끝나면 안 된다 — 어디를 봐야 하는지 알려준다."""
        m = _mod()
        old = m.RULE_DIRS
        try:
            m.RULE_DIRS = ["없는폴더"]
            os.environ.pop("RULE_SRC", None)
            d = m.build()
            self.assertFalse(d["ok"])
            h = m.render(d)
            self.assertIn("RULE_SRC", h)
        finally:
            m.RULE_DIRS = old

    def test_두_자가_다르다고_밝힌다(self):
        """ALL 0~500 · FAB 0~50 을 같은 자로 비교하면 안 된다."""
        m = _mod()
        h = m.render(m.build())
        self.assertIn("같은 자로 비교하지 마십시오", h)


class 위키에_올릴_MD(unittest.TestCase):
    """MCP 지식베이스에 넣을 MD. 두 관문을 다 통과해야 한다:
      ① 위키의 머리말 파서 — 제목·타입·태그·설명이 있어야 페이지가 된다
      ② 아바타의 낱말 관문 — 태그에 없는 말로 물으면 위키를 아예 안 뒤진다
    둘 중 하나만 통과하면 '올렸는데 아바타가 모른다' 가 된다."""

    @classmethod
    def setUpClass(cls):
        cls.m = _mod()
        cls.d = cls.m.build()
        if not cls.d["ok"]:
            raise unittest.SkipTest("예측기 소스를 못 찾았다")
        cls.pages = cls.m.wiki_pages(cls.d)
        app = os.path.join(util.BASE, "LLM_WIKI_MCP", "amhs-llm-wiki", "app.py")
        if not os.path.isfile(app):
            raise unittest.SkipTest("위키 app.py 가 없다")
        src = io.open(app, encoding="utf-8").read()
        i = src.index("MD_FM_RE = re.compile")
        j = src.index("def upsert_md_page")
        ns = {"re": re}
        exec(compile(src[i:j], app, "exec"), ns)          # noqa: S102
        # ★클래스에 함수를 그대로 붙이면 self.fn["parse"](raw) 가 바운드 메서드가
        #   되어 self 가 첫 인자로 끼어든다. dict 에 담아 피한다.
        cls.fn = {"parse": ns["parse_md_front"], "desc": ns["md_desc"]}

    def test_장수가_넉넉하다(self):
        """한 장에 다 넣으면 검색이 그 큰 문서만 물어 온다."""
        self.assertGreaterEqual(len(self.pages), 10)
        names = [n for n, _ in self.pages]
        for ar in (self.d["C"].get("AREAS_ALL") or []):
            self.assertTrue(any(n.endswith("영역-{}.md".format(ar))
                                for n in names),
                            "{} 페이지가 없다".format(ar))

    def test_위키_파서를_통과한다(self):
        for name, raw in self.pages:
            meta, body = self.fn["parse"](raw)
            self.assertTrue(meta.get("title"), name + " 제목 없음")
            self.assertIn(meta.get("type"), ("concept", "entity"),
                          name + " 타입 이상")
            self.assertTrue(meta.get("tags"), name + " 태그 없음")
            self.assertTrue(body.strip(), name + " 본문 없음")

    def test_설명이_페이지마다_다르다(self):
        """한 번에 여러 개를 올리면 화면 '설명' 칸은 전부 같은 값이 붙는다.
        md 가 자기 summary 를 갖고 있어야 각자 제 설명을 갖는다."""
        got = [self.fn["desc"](*self.fn["parse"](raw)) for _, raw in self.pages]
        for g in got:
            self.assertTrue(g)
        self.assertEqual(len(set(got)), len(got), "설명이 겹친다")

    def _words(self):
        words, seen = [], set()
        for _, raw in self.pages:
            meta, _b = self.fn["parse"](raw)
            cand = [meta.get("title") or ""]
            cand += re.split(r"[,]+", meta.get("tags") or "")
            for w in cand:
                w = w.strip().strip("[]()'\"`,.")
                if len(w) >= 2 and w not in seen:
                    seen.add(w)
                    words.append(w)
        return words

    def test_아바타가_이_문서를_뒤진다(self):
        """태그에 없는 말로 물으면 위키를 아예 안 뒤진다 — 올려 봐야 소용없다."""
        import sys as _s
        _s.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
        from avatar.mcp_client import _hits
        words = self._words()
        for q in ("M14는 어느 컬럼을 봐?", "unified_risk_score 어떻게 계산해?",
                  "area_score 가 뭐야?", "m16hub 임계값 알려줘",
                  "발동이벤트 컬럼 뭐가 있어?", "영역분리 하면 뭐가 바뀌어?",
                  "M16_PKT 는 왜 점수가 낮아?", "hot_area 가 뭐지?"):
            self.assertTrue(_hits(q, words), "안 걸린다: " + q)

    def test_띄어_쓴_말도_걸린다(self):
        """태그를 '리프터정체' 로만 두면 '리프터 정체' 로 물을 때 안 걸린다.
        낱말 관문은 글자 그대로 견준다 — 실제로 놓쳤던 자리다."""
        import sys as _s
        _s.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
        from avatar.mcp_client import _hits
        words = self._words()
        for q in ("리프터 정체가 무슨 뜻이야?", "Queue 누적이 뭐야?",
                  "Storage FULL 이 뭐지?", "4분 초과 알려줘"):
            self.assertTrue(_hits(q, words), "안 걸린다: " + q)

    def test_잡담에는_안_걸린다(self):
        import sys as _s
        _s.path.insert(0, os.path.join(util.BASE, "avatar_2d"))
        from avatar.mcp_client import _hits
        words = self._words()
        for q in ("오늘 점심 뭐 먹지?", "배고파", "날씨 어때"):
            self.assertEqual(_hits(q, words), [], "잘못 걸린다: " + q)

    def test_HTML_꼬리표가_안_섞인다(self):
        """설명을 HTML 에서 그대로 옮기면 <b> 가 md 에 남는다."""
        for name, raw in self.pages:
            for bad in ("<b>", "</b>", "<span", "&lt;"):
                self.assertNotIn(bad, raw, "{} 에 {} 가 남았다".format(name, bad))


if __name__ == "__main__":
    unittest.main()
