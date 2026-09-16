# -*- coding: utf-8 -*-
"""등급 카운터 — 최근 N분에 경계·위험·초위험이 **몇 번** 떴나.

고객 지시(그대로):
    "10분동안 얼마나 경계,위험,초위험 이 계속 되는지 확인
     => 10분동안 3회~4회 경계값 발동시 모니터링
     => 10분동안 1회~2회 위험값 무조건 확인 필요함
     => 10분동안 1회 초위험 무조건확인 필요함
     기본은 10분 일수도 있고, 정책에서 분을 설정하여 횟수를 변경
     실시간 관제에서 종합점수 옆에 경계중/위험중/초위험중 표시
     정책에서 적용·미적용으로 표시되고 안 되게"

★점수를 만들거나 등급 컷을 바꾸지 않는다. 이미 매겨진 등급을 **세기만** 한다.
  (고객이 이 자리에 한 번 데였다 — 여기 시험이 그 경계선을 지킨다.)
"""
import json
import os
import re
import subprocess
import unittest
from datetime import datetime, timedelta

from . import util  # noqa: F401
import alarm_count

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = datetime(2026, 9, 16, 14, 0)


def _read(*parts):
    with open(os.path.join(_BASE, *parts), encoding="utf-8") as fh:
        return fh.read()


def seq(*items):
    """(분, 등급) … → [(시각, 등급)] 오름차순."""
    return [(T0 + timedelta(minutes=m), lv) for m, lv in items]


def labels(rows):
    return [r["label"] for r in rows]


class 현장규칙(unittest.TestCase):
    """고객이 준 세 줄이 그대로 나오는가."""

    def test_10분에_경계_3회면_경계중(self):
        r = alarm_count.scan(seq((0, "정상"), (1, "경계"), (3, "경계"), (5, "경계")))
        self.assertEqual(labels(r), ["", "", "", "경계중"],
                         "세 번째 경계가 뜬 그 분부터 붙는다 (두 번째까진 아니다)")

    def test_10분에_위험_1회면_바로_위험중(self):
        r = alarm_count.scan(seq((0, "정상"), (1, "위험")))
        self.assertEqual(labels(r), ["", "위험중"])

    def test_10분에_초위험_1회면_바로_초위험중(self):
        r = alarm_count.scan(seq((0, "정상"), (1, "초위험")))
        self.assertEqual(labels(r), ["", "초위험중"])

    def test_높은_등급이_이긴다(self):
        # 경계 3회로 이미 '경계중' 인 자리에 위험이 하나 들어오면 '위험중'
        r = alarm_count.scan(seq((0, "경계"), (1, "경계"), (2, "경계"), (3, "위험")))
        self.assertEqual(labels(r), ["", "", "경계중", "위험중"])

    def test_초위험이_제일_세다(self):
        r = alarm_count.scan(seq((0, "위험"), (1, "초위험")))
        self.assertEqual(r[-1]["label"], "초위험중")


class 상위등급은_하위도_켠다(unittest.TestCase):
    """위험인 1분은 '경계값도 넘은' 1분이다.

    ★안 그러면 점수가 위험에 눌러앉은 동안 경계 카운트가 0이 되어,
      **제일 나쁜 구간에서 경계 알람이 꺼진다**.
    """

    def test_위험은_경계로도_센다(self):
        r = alarm_count.scan(seq((0, "위험"), (1, "위험"), (2, "위험")))[-1]
        self.assertEqual((r["warn"], r["danger"], r["critical"]), (3, 3, 0))

    def test_초위험은_셋_다_센다(self):
        r = alarm_count.scan(seq((0, "초위험"), (1, "초위험")))[-1]
        self.assertEqual((r["warn"], r["danger"], r["critical"]), (2, 2, 2))

    def test_정상은_아무것도_안_센다(self):
        r = alarm_count.scan(seq((0, "정상"), (1, "정상")))[-1]
        self.assertEqual((r["warn"], r["danger"], r["critical"]), (0, 0, 0))
        self.assertEqual(r["label"], "")

    def test_모르는_글자는_정상_취급(self):
        r = alarm_count.scan(seq((0, ""), (1, None), (2, "이상")))[-1]
        self.assertEqual(r["warn"], 0, "등급 이름이 아니면 세지 않는다")


class 창은_시각으로_센다(unittest.TestCase):
    """행 개수가 아니라 **시각**이다.

    ★수집이 몇 분 빠진 날 행으로 세면 10분 창이 20분이 된다 —
      한참 전에 지나간 경계 세 번으로 지금 알람이 울린다.
    """

    def test_창을_벗어나면_꺼진다(self):
        r = alarm_count.scan(seq((0, "위험"), (11, "정상")))
        self.assertEqual(labels(r), ["위험중", ""], "11분 전 위험은 10분 창 밖")

    def test_구멍이_뚫려도_창은_10분_그대로(self):
        # 14:00·14:02 에 경계 → 한 시간 쉬었다가 14:62 에 경계.
        # 행으로 세면 3회지만 시각으로는 1회다.
        r = alarm_count.scan(seq((0, "경계"), (2, "경계"), (62, "경계")))
        self.assertEqual(r[-1]["warn"], 1)
        self.assertEqual(r[-1]["label"], "")

    def test_딱_10분_전은_창_밖(self):
        # 창은 (t − 10분, t] 이다 — 경계가 정확히 10분 전이면 안 센다
        r = alarm_count.scan(seq((0, "위험"), (10, "정상")))
        self.assertEqual(r[-1]["danger"], 0)

    def test_9분_59초_전은_창_안(self):
        s = [(T0, "위험"), (T0 + timedelta(minutes=9, seconds=59), "정상")]
        self.assertEqual(alarm_count.scan(s)[-1]["danger"], 1)

    def test_순서대로_같은_길이로_돌려준다(self):
        s = seq((0, "정상"), (1, "경계"), (2, "위험"))
        self.assertEqual(len(alarm_count.scan(s)), len(s),
                         "부른 쪽이 zip 으로 붙인다 — 길이가 어긋나면 행이 밀린다")

    def test_하루치도_맞게_센다(self):
        # 1440행. 창 밖을 실제로 버리는 길(head > 256)이 여기서 돈다 —
        # 버리면서 색인을 안 맞추면 카운트가 어긋난다.
        s = [(T0 + timedelta(minutes=i), "위험" if i % 3 == 0 else "정상")
             for i in range(1440)]
        r = alarm_count.scan(s)
        self.assertEqual(len(r), 1440)
        # 1439분 = 3의 배수 아님. 창 (1429, 1439] 안의 3배수: 1431·1434·1437 → 3
        self.assertEqual(r[-1]["danger"], 3)
        self.assertEqual(r[-1]["warn"], 3)

    def test_빈_입력(self):
        self.assertEqual(alarm_count.scan([]), [])


class 정책(unittest.TestCase):
    def test_기본값은_고객_규칙(self):
        p = alarm_count.policy({})
        self.assertEqual((p["window_min"], p["warn"], p["danger"], p["critical"]),
                         (10, 3, 1, 1))
        self.assertTrue(p["enabled"])

    def test_설정이_기본을_이긴다(self):
        p = alarm_count.policy({"grade": {"alarm": {"window_min": 30, "warn": 5}}})
        self.assertEqual(p["window_min"], 30)
        self.assertEqual(p["warn"], 5)
        self.assertEqual(p["danger"], 1, "안 준 값은 기본 그대로")

    def test_분을_바꾸면_세는_창이_바뀐다(self):
        cfg = {"grade": {"alarm": {"window_min": 30}}}
        r = alarm_count.scan(seq((0, "위험"), (20, "정상")), cfg)
        self.assertEqual(r[-1]["danger"], 1, "30분 창이면 20분 전도 센다")
        self.assertEqual(r[-1]["window_min"], 30)

    def test_횟수를_바꾸면_기준이_바뀐다(self):
        cfg = {"grade": {"alarm": {"danger": 3}}}
        r = alarm_count.scan(seq((0, "위험"), (1, "위험")), cfg)
        self.assertEqual(r[-1]["label"], "", "위험 2회는 기준 3회에 못 미친다")
        r = alarm_count.scan(seq((0, "위험"), (1, "위험"), (2, "위험")), cfg)
        self.assertEqual(r[-1]["label"], "위험중")

    def test_0이면_그_단계는_안_쓴다(self):
        cfg = {"grade": {"alarm": {"warn": 0}}}
        r = alarm_count.scan(seq((0, "경계"), (1, "경계"), (2, "경계"), (3, "경계")), cfg)
        self.assertEqual(r[-1]["warn"], 4, "세기는 센다")
        self.assertEqual(r[-1]["label"], "", "이름표만 안 붙는다")

    def test_미적용이면_이름표가_없다(self):
        cfg = {"grade": {"alarm": {"enabled": False}}}
        r = alarm_count.scan(seq((0, "초위험"), (1, "초위험")), cfg)
        self.assertEqual(labels(r), ["", ""])
        self.assertTrue(all(x["enabled"] is False for x in r))
        self.assertEqual(len(r), 2, "꺼도 행 수는 같아야 zip 이 안 밀린다")

    def test_범위_밖은_자른다(self):
        p = alarm_count.policy({"grade": {"alarm": {"window_min": 9999, "warn": -3}}})
        self.assertEqual(p["window_min"], 180)
        self.assertEqual(p["warn"], 0)

    def test_이상한_값은_무시하고_기본(self):
        p = alarm_count.policy({"grade": {"alarm": {"window_min": "열분", "danger": None}}})
        self.assertEqual(p["window_min"], 10)
        self.assertEqual(p["danger"], 1)

    def test_grade가_없어도_안_터진다(self):
        for cfg in (None, {}, {"grade": None}, {"grade": {"alarm": None}}):
            self.assertEqual(alarm_count.policy(cfg)["window_min"], 10)

    def test_지문은_설정마다_다르다(self):
        base = alarm_count.sig({})
        for k, v in (("enabled", False), ("window_min", 20),
                     ("warn", 4), ("danger", 2), ("critical", 2)):
            self.assertNotEqual(alarm_count.sig({"grade": {"alarm": {k: v}}}), base,
                                f"{k} 를 바꿨는데 지문이 같다 — 캐시가 옛 응답을 낸다")

    def test_같은_설정은_같은_지문(self):
        a = {"grade": {"alarm": {"warn": 4, "window_min": 20}}}
        b = {"grade": {"alarm": {"window_min": 20, "warn": 4}}}
        self.assertEqual(alarm_count.sig(a), alarm_count.sig(b),
                         "키 순서가 달라졌다고 캐시가 깨지면 매 폴링이 재계산이다")


class 근거글(unittest.TestCase):
    def test_등급마다_다른_문장(self):
        pol = alarm_count.policy({})
        w = alarm_count.why(alarm_count.scan(
            seq((0, "경계"), (1, "경계"), (2, "경계")))[-1], pol)
        self.assertEqual(w, "최근 10분에 경계 이상 3회 (기준 3회)")
        d = alarm_count.why(alarm_count.scan(seq((0, "위험"),))[-1], pol)
        self.assertEqual(d, "최근 10분에 위험 이상 1회 (기준 1회)")
        c = alarm_count.why(alarm_count.scan(seq((0, "초위험"),))[-1], pol)
        self.assertEqual(c, "최근 10분에 초위험 1회 (기준 1회)")

    def test_이름표가_없으면_빈_글(self):
        self.assertEqual(alarm_count.why({"label": ""}), "")
        self.assertEqual(alarm_count.why(None), "")

    def test_바꾼_분이_문장에_들어간다(self):
        cfg = {"grade": {"alarm": {"window_min": 25}}}
        r = alarm_count.scan(seq((0, "위험"),), cfg)[-1]
        self.assertIn("최근 25분", alarm_count.why(r, alarm_count.policy(cfg)))


class 서버배선(unittest.TestCase):
    """flask 가 없는 곳에서도 배선은 확인한다 (원본 글자를 본다)."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read("server.py")

    def test_import_가_함수_밖에_있다(self):
        # ★함수 안으로 들어가면 /api/status 에서만 살아 있고 /api/feed 에선
        #   NameError 가 난다. 실제로 한 번 그렇게 넣었다.
        m = re.search(r"^import alarm_count$", self.src, re.M)
        self.assertIsNotNone(m, "top-level import alarm_count 가 없다")
        head = self.src[:m.start()]
        self.assertNotIn("def ", head.split("\n")[-3] if head else "",
                         "import 가 함수 안이다")

    def test_status_가_설정을_준다(self):
        self.assertIn('"alarm": alarm_count.policy(C["cfg"])', self.src,
                      "화면이 배지를 그리려면 /api/status 에 설정이 있어야 한다")

    def test_캐시_키에_지문이_있다(self):
        m = re.search(r"_sig = \(_st\.st_mtime_ns.*?files_sig\([^\n]*\)\)",
                      self.src, re.S)
        self.assertIsNotNone(m)
        self.assertIn("alarm_count.sig", m.group(0),
                      "빠지면 정책을 바꿔도 옛 응답이 캐시에서 그대로 나간다")

    def test_정렬_전에_센다(self):
        # ★out 은 최신순으로 뒤집힌다. 뒤집힌 뒤에 세면 창이 거꾸로 간다.
        i_scan = self.src.index("alarm_count.scan(")
        i_sort = self.src.index('out.sort(key=lambda x: x["at"], reverse=True)')
        self.assertLess(i_scan, i_sort, "세기가 정렬 뒤로 밀렸다")

    def test_시각을_isoformat_으로_읽는다(self):
        self.assertIn('datetime.fromisoformat(x["at"])', self.src,
                      "at 은 우리가 isoformat 으로 만든 글자다")

    def test_feed_가_설정과_지금_상태를_같이_준다(self):
        self.assertIn('"alarm": _apol, "alarm_now": alm_now', self.src)

    def test_행마다_배지_재료를_붙인다(self):
        for need in ('_x["alm"] = {"lv"', '"why": alarm_count.why('):
            self.assertIn(need, self.src, need + " 가 없다")

    def test_정책_저장이_grade_alarm_을_쓴다(self):
        self.assertIn('g["alarm"] = alm', self.src, "config.json 에 안 적힌다")

    def test_정책_객체를_갈아끼우지_않는다(self):
        # ★sys_cfg 뷰들이 grade 블록을 공유한다 — 통째로 바꾸면 끊긴다
        self.assertIn('g.setdefault("alarm", {}).update(new)', self.src)

    def test_정책_조회가_설정과_기본값을_준다(self):
        self.assertIn('"alarm": alarm_count.policy(CFG)', self.src)
        self.assertIn('"alarm_default": dict(alarm_count.DEFAULTS)', self.src)

    def test_들어온_값을_범위로_막는다(self):
        self.assertIn("alarm_count.LIMITS[k]", self.src,
                      "범위 검사가 모듈의 LIMITS 와 따로 놀면 안 된다")

    def test_점수_계산은_안_건드린다(self):
        """★이 시험이 제일 중요하다 — 고객이 이 자리에 데였다."""
        for f in ("fab_score.py", "sentinel.py"):
            self.assertNotIn("alarm_count", _read(f),
                             f"{f} 에 카운터가 들어갔다 — 점수 계산은 손대지 않는다")


class 화면배선(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = _read("static", "dashboard.html")

    def test_서명에_알람_설정이_들어간다(self):
        m = re.search(r"function cutSig\(\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m)
        self.assertIn("almSig()", m.group(0),
                      "빠지면 정책을 바꿔도 표를 다시 안 그린다 (컷에서 겪은 그것)")

    def test_설정을_세_군데서_받는다(self):
        self.assertIn("if(s.alarm) ALARM = s.alarm;", self.src, "/api/status")
        self.assertEqual(self.src.count("if(fd.alarm) ALARM = fd.alarm;"), 2,
                         "실시간·과거 **두 곳** 다 받아야 한다")

    def test_배지가_점수_칸에_붙는다(self):
        m = re.search(r"<td><div class=\"ttl\">\$\{Math\.round\(r\.score\)\}[\s\S]*?</td>",
                      self.src)
        self.assertIsNotNone(m, "종합점수 칸을 못 찾았다")
        self.assertIn("almChip(r)", m.group(0), "고객 요청은 '종합점수 옆' 이다")

    def test_칸을_새로_만들지_않았다(self):
        # ★colspan 이 세 군데 박혀 있고 내려받기 컬럼도 거기 맞춰져 있다
        self.assertEqual(self.src.count('colspan="7"'),
                         len(re.findall(r'colspan="7"', self.src)))
        self.assertIn("const ncol = 7 + (FABS.length ? FABS.length + 1 : 0);", self.src,
                      "표 칸 수가 바뀌었다 — 머리글·빈 표·내려받기가 어긋난다")

    def test_내려받기에도_들어간다(self):
        m = re.search(r"function viewCsv\(list\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m)
        blk = m.group(0)
        self.assertIn("'알람', '알람근거'", blk)
        self.assertIn("(r.alm || {}).lv", blk)
        self.assertIn("(r.alm || {}).why", blk)
        head = re.search(r"const head = \[([\s\S]*?)\];", blk).group(1)
        body = re.search(r"const rows = list\.map\(r => \[([\s\S]*?)\]\);", blk).group(1)
        self.assertEqual(head.count("...FABS"), body.count("...FABS.map"),
                         "머리글과 행의 FAB 자리가 어긋났다")

    def test_정책_탭에_카드가_있다(self):
        for need in ('id="almrow"', 'id="alm-save"', 'id="alm-on"',
                     'id="alm-reset"', 'id="alm-now"', 'id="almnote"'):
            self.assertTrue(need in self.src, need + " 가 없다")

    def test_네_칸을_다_그린다(self):
        # 입력 칸은 almFill 이 만든다 — 분·경계·위험·초위험 네 개
        m = re.search(r"function almFill\(d\)\{[\s\S]*?\n\}", self.src)
        self.assertTrue(m, "almFill 을 못 찾았다")
        blk = m.group(0)
        for need in ("almNum('alm-win', a.window_min, 180)", "almNum('alm-w', a.warn)",
                     "almNum('alm-d', a.danger)", "almNum('alm-c', a.critical)"):
            self.assertTrue(need in blk, need + " 가 없다")
        self.assertTrue("ALARM = a;" in blk, "표 배지도 같은 설정을 봐야 한다")

    def test_저장이_네_값을_다_보낸다(self):
        m = re.search(r"\$\('#alm-save'\)\.onclick = \(\) => almSave\(\{alarm: \{"
                      r"[\s\S]*?\}\}\);", self.src)
        self.assertTrue(m, "저장 버튼 배선을 못 찾았다")
        for need in ("window_min:", "warn:", "danger:", "critical:", "enabled:"):
            self.assertTrue(need in m.group(0), need + " 가 저장에서 빠졌다")

    def test_적용_스위치는_누르는_즉시_반영(self):
        self.assertIn("$('#alm-on').onchange = () => almSave({alarm: "
                      "{enabled: $('#alm-on').checked}});", self.src,
                      "저장을 또 눌러야 하면 '껐는데 왜 그대로냐' 가 된다")

    def test_저장은_등급_컷과_같은_길(self):
        m = re.search(r"async function almSave\(body\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m)
        self.assertIn("post('/api/score_policy'", m.group(0), "길이 둘이면 한쪽만 저장된다")
        self.assertIn("repaintGrades()", m.group(0), "저장 뒤 지금 화면을 새 설정으로")

    def test_등급_색_클래스가_실제로_있다(self):
        # almChip 이 lv경계·lv위험·lv초위험 을 쓴다
        for lv in ("경계", "위험", "초위험"):
            self.assertIn(f".lv{lv}{{", self.src)


class 설정파일(unittest.TestCase):
    def test_config_에_기본이_적혀_있다(self):
        with open(os.path.join(_BASE, "config.json"), encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        a = cfg["grade"]["alarm"]
        self.assertEqual((a["window_min"], a["warn"], a["danger"], a["critical"]),
                         (10, 3, 1, 1), "고객이 준 규칙 그대로")
        self.assertTrue(a["enabled"])
        self.assertEqual(alarm_count.policy(cfg)["window_min"], 10)

    def test_등급_컷은_안_건드렸다(self):
        with open(os.path.join(_BASE, "config.json"), encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        g = cfg["grade"]
        self.assertEqual(g.get("normal_max"), 59, "컷은 손대지 않는다")


class 화면토막_실행(unittest.TestCase):
    """dashboard.html 의 almChip·cutSig 를 **그대로 떼어** 돌린다."""

    def test_배지와_서명(self):
        node = None
        for c in ("/opt/node22/bin/node", "node", "nodejs"):
            try:
                subprocess.run([c, "-v"], capture_output=True, check=True)
                node = c
                break
            except (OSError, subprocess.CalledProcessError):
                continue
        if not node:
            self.skipTest("node 가 없다 (폐쇄망)")
        p = subprocess.run([node, os.path.join(_BASE, "tests", "alarm_chip.js")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr[-800:])
        bad = [r["name"] + " → " + r["got"][:120]
               for r in json.loads(p.stdout) if not r["ok"]]
        self.assertFalse(bad, "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
