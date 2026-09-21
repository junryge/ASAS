# -*- coding: utf-8 -*-
"""PIO_ERROR 룰 전/후 비교 문서 — 숫자를 지어내지 않는다.

고객: "새로운 룰 키워서 스코어 PIO_ERROR FAB별 추가했어 이거 전 후로
       비교해서 해줄래 결과도 만들어주고!! 어떻게 더 나은지"

★이 시험이 지키는 것은 '문서가 예쁜가' 가 아니라 **뭘 좋아졌다고 부르는가** 다.
  점수가 올랐다고 좋아진 게 아니다. 운전원이 보는 것은 등급(경계 60 ·
  위험 71 · 초위험 85)이고, 컷을 안 넘으면 화면에는 아무 일도 안 일어난다.
  실제로 받은 자료가 그랬다 — 784분에서 점수가 올랐는데 등급이 바뀐 분은 1분.
"""
import io
import os
import unittest

from . import util  # noqa: F401

import importlib.util as _ilu

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = _ilu.spec_from_file_location("pio_doc", os.path.join(_BASE, "PIO_전후비교_문서.py"))
P = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(P)


UP26 = ("/root/.claude/uploads/d02bef53-654d-5efc-a5eb-2c6bb7b9e067/"
        "e033ebbd-spspss.ipynb_26.txt")          # 2026-09-21 세 열짜리
UP24 = ("/root/.claude/uploads/d02bef53-654d-5efc-a5eb-2c6bb7b9e067/"
        "730996b1-spspss.ipynb_24.txt")          # 2026-09-18 두 열짜리


def _csv(fab, label, rows):
    head = (f"datetime,{label}_변경전_{fab}_area_score,"
            f"datetime,{label}_변경후_{fab}_area_score")
    body = "\n".join(f"{t},{b},{t},{a}" for t, b, a in rows)
    return head + "\n" + body


class 읽기(unittest.TestCase):
    def test_두_열을_시각으로_맞춘다(self):
        d = P.parse(_csv("m14", "9월", [("2026-09-13 11:38", 21, 29),
                                        ("2026-09-13 11:39", 30, 30)]))
        self.assertEqual(d["fab"], "M14")
        self.assertEqual(len(d["rows"]), 2)

    def test_시각이_어긋난_행은_버린다(self):
        """★두 열의 시각이 다르면 '전/후 비교' 가 아니다 — 세면 거짓이 된다."""
        src = ("datetime,a_변경전_m14_area_score,datetime,a_변경후_m14_area_score\n"
               "2026-09-13 11:38,21,2026-09-13 11:39,29\n"
               "2026-09-13 11:40,10,2026-09-13 11:40,17\n")
        d = P.parse(src)
        self.assertEqual(len(d["rows"]), 1)
        self.assertEqual(d["skew"], 1)


class 등급으로_센다(unittest.TestCase):
    def test_컷은_설정과_같다(self):
        from lp_client import load_config
        bands = (load_config().get("grade") or {}).get("bands") or []
        self.assertEqual(list(P.CUTS), [b["min"] for b in bands[:3]],
                         "문서가 쓰는 컷이 config.grade.bands 와 다르다")

    def test_등급_경계값(self):
        self.assertEqual(P.level(59), "정상")
        self.assertEqual(P.level(60), "경계")
        self.assertEqual(P.level(70), "경계")
        self.assertEqual(P.level(71), "위험")
        self.assertEqual(P.level(85), "초위험")

    def test_점수가_올라도_등급이_같으면_안_센다(self):
        from datetime import datetime
        rows = [(datetime(2026, 9, 13, 11, 38), 21.0, 29.0),
                (datetime(2026, 9, 13, 11, 39), 30.0, 40.0)]
        st = P.stats(rows)
        self.assertEqual(st["ch"], 2, "점수는 두 분 다 올랐다")
        self.assertEqual(sum(st["moved"].values()), 0, "그런데 등급은 그대로다")


class 좋아졌다고_부르는_기준(unittest.TestCase):
    """고객: "지금 경계값에 몰려있는데 위험이 있어야 돼. 그게 핵심이야.
            전보다 좋아졌는지 안 좋아졌는지 그게 핵심이야."

    ★그래서 기준은 **위험 이상 분이 늘었나** 다. 점수가 오른 것도, 경계가
      늘어난 것도 답이 아니다 — 경계만 늘면 "또 경계네" 가 되어 오히려 덜 본다.
    """

    def _doc(self, rows):
        return P.build([P.parse(_csv("m14", "t", rows))])

    def test_컷(self):
        """★M14 는 36/52/72 다. 저장소 기본값(60/71/85)으로 재면 결론이 통째로
        틀린다 — 실제로 무언정지가 '경계 0분' 으로 나왔다(진짜는 23분)."""
        self.assertEqual(P.cuts_of("M14"), (36, 52, 72))
        self.assertEqual(P.cuts_of("M16HUBROOM"), (40, 55, 75), "M16HUBROOM → M16HUB")
        self.assertEqual(P.cuts_of("ALL"), (48, 60, 80))

    def test_경계만_늘면_좋아진_게_아니다(self):
        """경계는 늘었지만 위험은 그대로 — 화면은 '또 경계네' 가 된다."""
        rows = [("2026-09-13 11:%02d" % m, 30, 40) for m in range(10, 40)]   # 36 넘김
        h = self._doc(rows)
        i = h.index("0. 한 줄로")
        self.assertIn("note miss", h[i:i + 500], "경계만 늘었는데 초록이다")
        self.assertIn("위험이 늘지 않았습니다", h)

    def test_위험이_늘면_좋아진_것이다(self):
        rows = [("2026-09-13 11:%02d" % m, 40, 40) for m in range(10, 30)]
        rows += [("2026-09-13 12:%02d" % m, 45, 55) for m in range(0, 10)]   # 52 넘김
        h = self._doc(rows)
        i = h.index("0. 한 줄로")
        self.assertIn("note good", h[i:i + 500])
        self.assertIn("위험으로 올라갔습니다", h)

    def test_경계_쏠림도_같이_본다(self):
        """★경계가 같이 늘면 쏠림은 안 내려간다 — '전체를 끌어올린 것' 이지
        '경계를 위험으로 올린 것' 이 아니다. 둘을 가르려고 비율을 같이 본다."""
        c = (36, 52, 72)
        from datetime import datetime
        t = datetime(2026, 9, 13, 11, 0)
        rows = [(t, 40.0, 40.0)] * 9 + [(t, 40.0, 55.0)]      # 10분 중 1분만 위험
        pr = P.promote(rows, c)
        self.assertEqual(pr["before"]["danger"], 0)
        self.assertEqual(pr["after"]["danger"], 1)
        self.assertEqual(len(pr["up"]), 1)
        self.assertGreater(pr["before"]["share"], pr["after"]["share"],
                           "위험이 생기면 쏠림은 내려가야 한다")

    def test_위험_문턱_바로_아래도_센다(self):
        """조금만 더 올리면 위험이 되는 분이 몇인지 — 배점을 얼마나 올릴지의 근거."""
        from datetime import datetime
        t = datetime(2026, 9, 13, 11, 0)
        pr = P.promote([(t, 40.0, 50.0), (t, 40.0, 41.0)], (36, 52, 72))
        self.assertEqual(pr["near5"], 1, "52까지 2점 남은 분")
        self.assertEqual(pr["near10"], 1)


class 문서(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = [("2026-09-13 11:%02d" % m, 21, 29) for m in range(38, 58)]
        cls.h = P.build([P.parse(_csv("m14", "9월13일", rows))])

    def test_뼈대(self):
        for t in ("0. 한 줄로", "① 룰이 먹었나", "② 화면이 달라졌나",
                  "③ 잡고 싶던 것을 잡았나", "배점을 키웠다면",
                  "4. 이 문서가 말하지 않는 것"):
            self.assertIn(t, self.h, t)

    def test_알려진_사건은_장애분석_문서에서_가져온다(self):
        """지어낸 구간이면 결론이 통째로 거짓이 된다."""
        self.assertTrue(any(e["what"] == "OHT 무언정지" for e in P.KNOWN))
        for e in P.KNOWN:
            self.assertTrue(os.path.isfile(os.path.join(_BASE, "docs", e["doc"])),
                            f'근거 문서가 없다: {e["doc"]}')

    def test_배점을_키웠을_때_얼마나_늘지도_적는다(self):
        """★배점 올리기는 양날이다 — 사건 없는 날에도 같이 뛴다."""
        from datetime import datetime
        rows = [(datetime(2026, 9, 13, 11, 38), 50.0, 57.0)] * 10
        tb = P.scale_table(rows)
        self.assertEqual(tb[0][0], 1)
        self.assertEqual(tb[0][1], 0, "×1 에서는 아직 경계 아래")
        self.assertEqual(tb[-1][1], 10, "×5 면 전부 경계 위")

    def test_문서의_숫자를_원본에서_다시_세어_대조한다(self):
        """★고객: "이상한거 하지마라. 실제 데이터 기반으로 하고 있는데."

        문서를 만든 코드로 다시 재면 검증이 아니다. 여기서는 올려주신 원본을
        **처음부터 따로 세어**(제 CSV 파서 · 제 등급 함수) 문서에 찍힌 숫자와
        맞춰 본다. 하나라도 다르면 문서가 자료에 없는 말을 하고 있다는 뜻이다.
        ★2026-09-21 자료부터 다리가 셋이다 — 세 다리를 다 센다.
        """
        import csv as _csvmod
        import json as _json
        import re as _re
        from datetime import datetime as _dt
        up = UP26
        if not os.path.isfile(up):
            self.skipTest("받은 자료가 이 환경에 없다")
        nb = _json.load(io.open(up, encoding="utf-8"))
        cuts = {"M14": (36, 52, 72), "M16HUBROOM": (40, 55, 75)}
        docs = {"M14": "M14_20260913_장애분석.html",
                "M16HUBROOM": "M16HUB_데드락_분석.html"}
        seen = set()
        for cell in nb["cells"]:
            src = cell.get("source")
            if isinstance(src, list):
                src = "".join(src)
            if not src or "변경전" not in src:
                continue
            rows = list(_csvmod.reader(io.StringIO(src)))
            fab = _re.search(r"변경전_(.+?)_area_score", rows[0][1]).group(1).upper()
            c = cuts[fab]
            seen.add(fab)
            d = []
            for r in rows[1:]:
                if len(r) < 4 or not r[0].strip():
                    continue
                d.append((_dt.strptime(r[0].strip(), "%Y-%m-%d %H:%M"),
                          float(r[1]), float(r[2]), float(r[3])))
            self.assertEqual(len(d), 2880, f"{fab} 원본 행 수")

            def lv(v):
                return 3 if v >= c[2] else 2 if v >= c[1] else 1 if v >= c[0] else 0

            h = io.open(os.path.join(_BASE, "docs", docs[fab]), encoding="utf-8").read()
            self.assertIn(P.MARK0, h, f"{fab} 문서에 절이 안 붙어 있다")
            sec = h[h.index(P.MARK0):h.index(P.MARK1)]
            txt = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", sec))

            # 등급 분포 — 다리마다 한 줄 (정상 경계 위험 초위험 위험이상 쏠림% 최고 0점)
            for tag, k in (("변경 전", 1), ("변경 후", 2), (r"\+1분 cnt", 3)):
                cnt = [0, 0, 0, 0]
                for r in d:
                    cnt[lv(r[k])] += 1
                m = _re.search(tag + r" (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)% (\d+) ([\d,]+) ",
                               txt)
                self.assertIsNotNone(m, f"{fab} {tag} 줄을 못 찾았다")
                self.assertEqual([int(m.group(x)) for x in (1, 2, 3, 4)], cnt,
                                 f"{fab} {tag} 등급 분포가 원본과 다르다")
                self.assertEqual(int(m.group(5)), cnt[2] + cnt[3], f"{fab} {tag} 위험 이상")
                self.assertEqual(int(m.group(7)), int(max(r[k] for r in d)),
                                 f"{fab} {tag} 최고점")
                self.assertEqual(int(m.group(8).replace(",", "")),
                                 sum(1 for r in d if r[k] == 0), f"{fab} {tag} 0점")

            # 걸음마다 — 변경 후 → +1분 cnt
            ch = sum(1 for r in d if r[2] != r[3])
            upn = sum(1 for r in d if r[3] > r[2])
            dn = sum(1 for r in d if r[3] < r[2])
            mv = sum(1 for r in d if lv(r[2]) != lv(r[3]))
            db = sum(1 for r in d if r[2] >= c[1])
            da = sum(1 for r in d if r[3] >= c[1])
            pu = sum(1 for r in d if c[0] <= r[2] < c[1] <= r[3])
            pl = sum(1 for r in d if r[3] < c[1] <= r[2])
            m = _re.search(r"변경 후 → \+1분 cnt ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) "
                           r"(\d+) → (\d+) (\d+) (\d+) ", txt)
            self.assertIsNotNone(m, f"{fab} 걸음 표를 못 찾았다")
            got = [int(m.group(x).replace(",", "")) for x in range(1, 9)]
            self.assertEqual(got, [ch, upn, dn, mv, db, da, pu, pl],
                             f"{fab} 걸음 숫자가 원본과 다르다")

            # 0점이 된 분 중 앞 다리에서 경계 이상이던 분 — 이 숫자가 이 절의 핵심
            zhot = sum(1 for r in d if r[3] == 0 and r[2] >= c[0])
            m = _re.search(r"0점이 된 분 ([\d,]+) 그중 변경 후에 경계 이상이던 분 (\d+)", txt)
            self.assertIsNotNone(m, f"{fab} 헛울림 표를 못 찾았다")
            self.assertEqual(int(m.group(1).replace(",", "")),
                             sum(1 for r in d if r[3] == 0), f"{fab} 0점 분")
            self.assertEqual(int(m.group(2)), zhot, f"{fab} 0점인데 경계 이상이던 분")
        self.assertEqual(seen, {"M14", "M16HUBROOM"}, "두 FAB 을 다 못 읽었다")

    def test_사건_구간_숫자도_원본에서_다시_센다(self):
        """★M14 무언정지 구간이 이 문서의 결론이다 — 따로 한 번 더 센다."""
        import csv as _csvmod
        import json as _json
        import re as _re
        from datetime import datetime as _dt
        if not os.path.isfile(UP26):
            self.skipTest("받은 자료가 이 환경에 없다")
        nb = _json.load(io.open(UP26, encoding="utf-8"))
        src = next("".join(c["source"]) if isinstance(c.get("source"), list)
                   else c.get("source") for c in nb["cells"]
                   if "변경전_m14" in "".join(c.get("source") or ""))
        c = (36, 52, 72)
        d = []
        for r in list(_csvmod.reader(io.StringIO(src)))[1:]:
            if len(r) < 4 or not r[0].strip():
                continue
            d.append((_dt.strptime(r[0].strip(), "%Y-%m-%d %H:%M"),
                      float(r[1]), float(r[2]), float(r[3])))
        w = [r for r in d if r[0].strftime("%Y-%m-%d") == "2026-09-13"
             and "11:38" <= r[0].strftime("%H:%M") <= "14:30"]
        self.assertEqual(len(w), 173, "무언정지 구간 길이")
        cn = [sum(1 for r in w if r[k] >= c[1]) for k in (1, 2, 3)]
        self.assertEqual(cn, [0, 0, 6],
                         "무언정지 구간의 위험 분이 달라졌다 — 결론이 바뀐다")
        h = io.open(os.path.join(_BASE, "docs", "M14_20260913_장애분석.html"),
                    encoding="utf-8").read()
        txt = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ",
                                           h[h.index(P.MARK0):h.index(P.MARK1)]))
        self.assertIn("11:38~14:30 173 46 → 46 → 57 0 → 0 → 6", txt,
                      "문서에 찍힌 무언정지 줄이 원본과 다르다")

    def test_실제_받은_자료로도_돈다(self):
        """받은 노트북이 아직 있으면 그것으로도 한 번 돌려 본다."""
        up = UP24
        if not os.path.isfile(up):
            self.skipTest("받은 자료가 이 환경에 없다")
        sets = [p for p in (P.parse(c) for c in P.read_cells(up)) if p]
        self.assertEqual({s["fab"] for s in sets}, {"M14", "M16HUBROOM"})
        got = {s["fab"]: sum(P.stats(s["rows"])["moved"].values()) for s in sets}
        self.assertEqual(got, {"M16HUBROOM": 0, "M14": 1},
                         "등급이 바뀐 분 수가 달라졌다 — 결론이 바뀐다")


class 세_번째_다리(unittest.TestCase):
    """2026-09-21 — PIO 점수에 **그 분(1분) 값**을 같이 보게 하고 다시 받았다.

    고객: "cnt 1분 추가했어. pio_error 1분 스코어값 변경하고 임계값 변경했어.
           …M14, M16HUB 완전 잘 나왔는데, 헛울림도 많이 줄고."

    ★다리가 둘에서 셋이 되면서 **무엇을 견주는지**가 바뀐다. (1,2) 로 계속
      세면 '지난번에 뭐가 달라졌나' 를 적게 된다 — 숫자는 멀쩡해 보이는데
      문서가 딴소리를 하게 된다. 그래서 여기서 pair_of 를 못박는다.
    ★그리고 이번 다리는 **점수가 내려간 분이 더 많다**. 내려간 것을 안 세면
      '좋아졌다' 만 남는다. 깎인 것이 잡음인지 신호인지를 같이 적게 한다.
    """

    def _s3(self, rows, fab="m14", label="t"):
        head = (f"datetime,{label}_변경전_{fab}_area_score,"
                f"{label}_변경후_{fab}_area_score,"
                f"{label}_추가(1분cnt추가)_{fab}_area_score")
        body = "\n".join(f"{t},{a},{b},{c}" for t, a, b, c in rows)
        return P.parse(head + "\n" + body)

    def _rows(self, day="2026-09-13"):
        return [(f"{day} {h:02d}:{m:02d}", 30 + (h % 5) * 6, 30 + (h % 5) * 6,
                 30 + (h % 5) * 6 + (14 if m % 7 == 0 else -6))
                for h in range(24) for m in range(60)]

    # ── 읽기 ────────────────────────────────────────────────────
    def test_세_열짜리를_읽는다(self):
        d = self._s3([("2026-09-13 11:38", 21, 29, 35),
                      ("2026-09-13 11:39", 30, 30, 12)])
        self.assertEqual(d["legs"], ["변경 전", "변경 후", "+1분 cnt"])
        self.assertEqual(len(d["rows"]), 2)
        self.assertEqual(d["rows"][0][1:], (21.0, 29.0, 35.0))
        self.assertEqual(d["skew"], 0, "시각 열이 하나면 어긋날 수가 없다")

    def test_두_열짜리는_예전대로_읽는다(self):
        d = P.parse(_csv("m14", "9월", [("2026-09-13 11:38", 21, 29)]))
        self.assertEqual(d["legs"], ["변경 전", "변경 후"])
        self.assertEqual(len(d["rows"][0]), 3)

    def test_마지막_두_다리를_견준다(self):
        """★이걸 놓치면 문서가 조용히 지난번 얘기를 한다."""
        self.assertEqual(P.pair_of({"legs": ["a", "b"]}), (1, 2))
        self.assertEqual(P.pair_of({"legs": ["a", "b", "c"]}), (2, 3))
        self.assertEqual(P.pair_of({}), (1, 2), "다리 정보가 없으면 예전대로")

    def test_견주는_다리가_바뀌면_숫자도_바뀐다(self):
        from datetime import datetime as dt
        rows = [(dt(2026, 9, 13, 11, m), 40.0, 40.0, 55.0) for m in range(10)]
        self.assertEqual(P.promote(rows, (36, 52, 72), (1, 2))["after"]["danger"], 0)
        self.assertEqual(P.promote(rows, (36, 52, 72), (2, 3))["after"]["danger"], 10)

    # ── 내려간 것도 센다 ────────────────────────────────────────
    def test_위험에서_내려온_분을_센다(self):
        from datetime import datetime as dt
        rows = [(dt(2026, 9, 13, 11, m), 40.0, 55.0, 40.0) for m in range(4)]
        pr = P.promote(rows, (36, 52, 72), (2, 3))
        self.assertEqual(len(pr["lost"]), 4)
        self.assertEqual(len(pr["up"]), 0)

    def test_올린_폭_평균이라고_안_쓴다(self):
        """★이번 다리는 평균이 음수다. 칸 이름이 '올린 폭' 이면 거짓말이 된다."""
        sec = P.fab_section(self._s3(self._rows()))
        self.assertNotIn("올린 폭 평균", sec)
        for w in ("바뀐 폭 평균", "제일 많이 내린 폭", "내린 분"):
            self.assertIn(w, sec, w)

    def test_0점이_된_분이_무엇이었는지_적는다(self):
        """★깎인 것이 잡음인지 신호인지 — 이걸 안 적으면 '좋아졌다' 만 남는다."""
        sec = P.fab_section(self._s3(self._rows()))
        self.assertIn("⑤ 내려간 분은 어디였나", sec)
        self.assertIn("그중 변경 후에 경계 이상이던 분", sec)

    def test_경계_이상이던_분이_0점이_되면_붉게_쓴다(self):
        from datetime import datetime as dt
        rows = [(f"2026-09-13 11:{m:02d}", 40, 40, 0) for m in range(30)]
        sec = P.fab_section(self._s3(rows))
        i = sec.index("0점이 된 분")
        self.assertIn('class="bad"', sec[i:i + 400],
                      "경계 이상이던 분이 0점이 됐는데 조용히 넘어갔다")

    # ── 그림 ────────────────────────────────────────────────────
    def test_칸이_다리마다_하나씩(self):
        sec = P.fab_section(self._s3(self._rows()))
        self.assertEqual(sec.count("<polyline"), 3, "다리마다 곡선 하나씩")
        for t in ("① 변경 전", "② 변경 후", "③ +1분 cnt", "④ 차이(+1분 cnt − 변경 후)"):
            self.assertIn(t, sec, t)

    def test_세_칸이_같은_자를_쓴다(self):
        sec = P.fab_section(self._s3(self._rows()))
        self.assertEqual(sec.count(">100<"), 3, "칸마다 100 눈금")

    def test_내려간_자리도_그린다(self):
        """★내려간 것을 안 그리면 '헛울림이 줄었다' 를 눈으로 못 본다."""
        sec = P.fab_section(self._s3(self._rows()))
        self.assertIn("#0ea5e9", sec, "내려간 막대 색이 없다")
        self.assertIn("내려간 자리", sec)

    def test_세_칸_모두_같은_빨강으로_칠한다(self):
        """★칸끼리 '빨간 면이 얼마나 늘었나' 를 견주는 그림이다 —
        칸마다 색이 다르면 넓이를 견줄 수 없다."""
        rows = [(f"2026-09-13 11:{m:02d}", 55, 60, 65) for m in range(30)]
        sec = P.fab_section(self._s3(rows))
        i = sec.index("<svg")
        j = sec.index("</svg>")
        self.assertEqual(sec[i:j].count('fill="#b91c1c" opacity=".9"'), 3)

    # ── 덩어리 ──────────────────────────────────────────────────
    def test_덩어리는_가장_가까운_것끼리_짝짓는다(self):
        """★앞에서부터 집어가면 2분짜리가 먼 덩어리를 채가고, 정작 그 자리에
        있던 덩어리가 '사라짐' 으로 찍힌다 (M14 9/12 17:59 ↔ 18:22)."""
        from datetime import datetime as dt
        from datetime import timedelta as td
        def mk(h, m, n):
            b = dt(2026, 9, 12, h, m)
            return {"beg": b, "end": b + td(minutes=n - 1), "n": n, "hi": 60}
        bb = [mk(17, 59, 2), mk(18, 22, 15)]
        aa = [mk(18, 22, 14)]
        pr = P.match_blocks(bb, aa)
        d = {(p[0] or {}).get("beg"): p[1] for p in pr}
        self.assertIsNone(d[dt(2026, 9, 12, 17, 59)], "2분짜리가 먼 덩어리를 채갔다")
        self.assertIsNotNone(d[dt(2026, 9, 12, 18, 22)])

    def test_뭉친_것을_사라졌다고_안_쓴다(self):
        """★둘이 하나로 뭉치면 1:1 짝짓기에서 한쪽이 '사라짐' 으로 찍힌다.
        시간이 겹치면 없어진 게 아니라 뭉친 것이다."""
        rows = ([(f"2026-09-12 21:{m:02d}", 40, 40, 60) for m in range(32, 59)]
                + [(f"2026-09-12 22:{m:02d}", 40, 60, 40) for m in range(0, 6)]
                + [(f"2026-09-12 23:{m:02d}", 10, 10, 10) for m in range(0, 30)])
        rows = [(t, a, b, c) for t, a, b, c in rows]
        sec = P.fab_section(self._s3(rows))
        i = sec.index("④ 언제부터 울렸나")
        self.assertIn("합쳐짐", sec[i:], "뭉친 것을 사라졌다고 썼다")

    def test_덩어리_표에_첫_경보가_있다(self):
        sec = P.fab_section(self._s3(self._rows()))
        self.assertIn("④ 언제부터 울렸나", sec)
        self.assertIn("첫 경보", sec)

    # ── 변경내역서 옮겨적기 ─────────────────────────────────────
    def test_변경내역서_값을_그대로_옮겼다(self):
        """★구간표를 잘못 옮기면 문서가 남의 숫자를 말하게 된다.
        고객이 준 변경내역서에서 다시 읽어 대조한다."""
        import re as _re
        doc = ("/root/.claude/uploads/d02bef53-654d-5efc-a5eb-2c6bb7b9e067/"
               "e15ecd0c-_____20260921.html")
        if not os.path.isfile(doc):
            self.skipTest("변경내역서가 이 환경에 없다")
        h = io.open(doc, encoding="utf-8").read()
        i = h.index("FAB별 구간표")
        tbl = h[i:h.index("</table>", i)]
        got = {}
        for fab, b10, b1, cap in _re.findall(
                r"<tr><td>(\w+)</td><td>([\d·]+)</td><td>([^<]+)</td>"
                r"<td[^>]*>(\d+)</td></tr>", tbl):
            nums = lambda t: tuple(int(x) for x in _re.findall(r"\d+", t.split("(")[0]))
            got[fab] = {"b10": nums(b10), "b1": nums(b1), "cap": int(cap)}
        self.assertTrue(got, "변경내역서에서 구간표를 못 읽었다")
        for fab, v in got.items():
            self.assertIn(fab, P.PIO_1MIN, f"{fab} 구간표가 빠졌다")
            self.assertEqual(P.PIO_1MIN[fab], v, f"{fab} 구간표가 변경내역서와 다르다")
        self.assertEqual(set(got), set(P.PIO_1MIN), "FAB 수가 다르다")
        self.assertEqual(P.PIO_1MIN["M16B"]["cap"], 5, "M16B 만 상한 5 다")

    def test_임계를_안_바꾼_FAB_을_문서에_적는다(self):
        """★이 두 FAB 은 임계를 하나도 안 바꿨다. 그걸 안 적으면 읽는 사람이
        숫자가 움직인 몫을 임계 탓으로 읽는다."""
        sec = P.fab_section(self._s3(self._rows()))
        self.assertIn("임계는 이번에 하나도 안 바꿨습니다", sec)
        self.assertIn("M14", P.PIO_TH_UNTOUCHED)
        self.assertIn("M16HUB", P.PIO_TH_UNTOUCHED)

    def test_지난_걸음도_문서에_남긴다(self):
        """★①② 칸이 마지막 걸음만 재게 됐다 — 지난 걸음(전 → 후)을 잃으면
        문서 한 장으로 다 못 읽는다."""
        sec = P.fab_section(self._s3(self._rows()))
        self.assertIn("걸음마다 무엇이 달라졌나", sec)
        self.assertIn("변경 전 → 변경 후", sec)
        self.assertIn("변경 후 → +1분 cnt", sec)

    # ── 실제 자료 ───────────────────────────────────────────────
    def test_실제_받은_새_자료로_돈다(self):
        if not os.path.isfile(UP26):
            self.skipTest("받은 자료가 이 환경에 없다")
        sets = [p for p in (P.parse(c) for c in P.read_cells(UP26)) if p]
        self.assertEqual({s["fab"] for s in sets}, {"M14", "M16HUBROOM"})
        got = {}
        for s in sets:
            c = P.cuts_of(s["fab"])
            pr = P.promote(s["rows"], c, P.pair_of(s))
            got[s["fab"]] = (pr["before"]["danger"], pr["after"]["danger"],
                             len(pr["up"]), len(pr["lost"]))
            self.assertEqual(len(s["rows"]), 2880, s["fab"])
            self.assertEqual(s["legs"], ["변경 전", "변경 후", "+1분 cnt"])
        self.assertEqual(got, {"M14": (82, 120, 41, 3),
                               "M16HUBROOM": (22, 58, 49, 13)},
                         "위험 분 수가 달라졌다 — 결론이 바뀐다")

    def test_좋아졌다고_부를_만한_자료다(self):
        """★'좋아졌다' 는 위험이 늘고 경계에서 올라온 것이 5분 이상일 때만
        쓴다. 이번 자료가 그 기준을 넘는지 못박아 둔다."""
        if not os.path.isfile(UP26):
            self.skipTest("받은 자료가 이 환경에 없다")
        for s in [p for p in (P.parse(c) for c in P.read_cells(UP26)) if p]:
            sec = P.fab_section(s)
            self.assertIn("좋아졌습니다", sec, s["fab"])
            self.assertIn("note good", sec, s["fab"])


if __name__ == "__main__":
    unittest.main()


class 기존_문서에_붙인다(unittest.TestCase):
    """고객: "하나 하나식 분리해줘!! 기존 내용에다가!! 전후로 해서
            M14A·M16HUB 각각 해달라고. 기존 내용 있었잖아".

    ★새 문서를 따로 만들면 나중에 어느 쪽이 최신인지 알 수 없다. FAB 마다
      **이미 있는 그 FAB 의 분석 문서 뒤에** 한 절로 붙인다.
    """

    def test_어느_문서에_붙일지_정해져_있다(self):
        self.assertEqual(set(P.INTO), {"M14", "M16HUB"})
        for code, name in P.INTO.items():
            self.assertTrue(os.path.isfile(os.path.join(_BASE, "docs", name)),
                            f"{code} 가 붙을 문서가 없다: {name}")

    def test_기존_내용을_안_지운다(self):
        import tempfile, shutil
        src = os.path.join(_BASE, "docs", P.INTO["M14"])
        tmp = tempfile.mkdtemp(prefix="pioinit")
        try:
            p = os.path.join(tmp, "doc.html")
            raw = io.open(src, encoding="utf-8").read()
            # ★이미 붙어 있으면 떼고 시작한다 — '붙기 전' 과 견주려는 것이다
            if P.MARK0 in raw:
                i, j = raw.index(P.MARK0), raw.index(P.MARK1) + len(P.MARK1)
                raw = raw[:i] + raw[j:]
            io.open(p, "w", encoding="utf-8").write(raw)
            before = raw
            key = "0. 한 줄로"                       # 기존 문서의 첫 절
            self.assertIn(key, before)
            rows = [("2026-09-13 11:%02d" % m, 40, 55) for m in range(10, 30)]
            P.splice(p, P.fab_section(P.parse(_csv("m14", "t", rows))))
            after = io.open(p, encoding="utf-8").read()
            self.assertIn(key, after, "기존 내용이 사라졌다")
            self.assertGreater(len(after), len(before), "붙은 게 없다")
            self.assertIn("PIO_ERROR", after)
            self.assertTrue(after.rstrip().endswith("</html>"), "문서가 깨졌다")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_두_번_돌려도_한_벌만_남는다(self):
        """★다시 돌릴 때마다 쌓이면 문서가 못 쓰게 된다."""
        import tempfile, shutil
        tmp = tempfile.mkdtemp(prefix="pioinit")
        try:
            p = os.path.join(tmp, "doc.html")
            shutil.copy(os.path.join(_BASE, "docs", P.INTO["M14"]), p)
            rows = [("2026-09-13 11:%02d" % m, 40, 55) for m in range(10, 30)]
            sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
            P.splice(p, sec)
            n1 = len(io.open(p, encoding="utf-8").read())
            P.splice(p, sec)
            h = io.open(p, encoding="utf-8").read()
            self.assertEqual(len(h), n1, "두 번째가 덧쌓였다")
            self.assertEqual(h.count(P.MARK0), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_절_제목이_한_번만_나온다(self):
        rows = [("2026-09-13 11:%02d" % m, 40, 55) for m in range(10, 30)]
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertEqual(sec.count("<h2>"), 1, "제목이 두 번 찍힌다")

    def test_2분_늘어난_것을_좋아졌다고_안_쓴다(self):
        """M14 는 위험이 80 → 82분(경계에서 올라온 것 2분)이다.
        그걸 초록으로 쓰면 고객이 잘못 읽는다."""
        rows = [("2026-09-13 11:%02d" % m, 40, 40) for m in range(0, 40)]
        rows += [("2026-09-13 12:%02d" % m, 45, 55) for m in range(0, 2)]
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertIn("조금 올랐을 뿐입니다", sec)
        self.assertIn("note miss", sec)

    def test_5분_이상_올라오면_좋아진_것이다(self):
        rows = [("2026-09-13 11:%02d" % m, 40, 40) for m in range(0, 40)]
        rows += [("2026-09-13 12:%02d" % m, 45, 55) for m in range(0, 6)]
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertIn("좋아졌습니다", sec)
        self.assertIn("note good", sec)


class 제안은_안_쓴다(unittest.TestCase):
    """고객: "제안 빼라. 지금 PIO 들어가잖아. 현재 데이터를 보고 이야기하는 거야."

    ★이 문서는 **지금 들어간 룰이 무엇을 했는지**만 적는다. 가정한 배점으로
      센 숫자('배점을 N 배로 키웠다면')나 '이렇게 하는 게 낫다' 를 같이 놓으면,
      읽는 사람이 그것도 잰 값으로 읽는다.
    """

    def _sec(self):
        rows = [("2026-09-13 11:%02d" % m, 30, 38) for m in range(0, 40)]
        return P.fab_section(P.parse(_csv("m14", "t", rows)))

    def test_가정한_배점_표가_없다(self):
        sec = self._sec()
        self.assertNotIn("배점을 키웠다면", sec)
        self.assertNotIn("배수", sec)

    def test_그래서_이렇게_하자가_없다(self):
        sec = self._sec()
        for w in ("어떻게 해야", "먼저입니다", "제안", "권장", "하는 쪽이",
                  "신호가 아닙니다", "또 경계네"):
            self.assertNotIn(w, sec, f"제안투가 남아 있다: {w}")

    def test_잰_값은_그대로_있다(self):
        sec = self._sec()
        for w in ("① 룰이 먹었나", "② 화면이 달라졌나", "위험 이상",
                  "경계 쏠림", "변경 전 / 후 — 하루치 점수"):
            self.assertIn(w, sec, w)


class 그래프가_들어간다(unittest.TestCase):
    """고객: "변경전·변경후 그래프도 보여줘야지. 그게 내용이 들어가 있어야 알지."

    표의 숫자만으로는 **어디서** 올랐는지가 안 보인다. 두 곡선을 같은 자리에
    겹쳐 놓고, 등급 컷과 사건 구간을 같이 그려야 '그래서 화면이 바뀌었나' 를
    읽을 수 있다.
    """

    def _rows(self, day="2026-09-13"):
        return [(f"{day} {h:02d}:{m:02d}", 30 + (h % 5) * 6, 30 + (h % 5) * 6 + (8 if m % 7 == 0 else 0))
                for h in range(24) for m in range(60)]

    def test_날마다_한_장(self):
        rows = self._rows("2026-09-12") + self._rows("2026-09-13")
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertEqual(sec.count("<svg"), 2, "날짜 수만큼 있어야 한다")
        self.assertIn("변경 전 / 후 — 하루치 점수", sec)

    def test_전과_후를_칸을_나눠_따로_그린다(self):
        """★고객: "한 그래프에 전부 다 그리면 어떻게 알아."
        두 곡선은 97% 가 겹쳐 있어서 한 칸에 포개면 뒤 선이 앞 선을 덮는다.
        칸을 셋으로 나눈다 — ① 변경 전 ② 변경 후 ③ 차이."""
        sec = P.fab_section(P.parse(_csv("m14", "t", self._rows())))
        self.assertIn("① 변경 전", sec)
        self.assertIn("② 변경 후", sec)
        self.assertIn("③ 차이(후 − 전)", sec)
        self.assertEqual(sec.count("<polyline"), 2, "칸마다 곡선 하나씩")

    def test_두_칸이_같은_자를_쓴다(self):
        """★자가 다르면 위아래를 견줄 수 없다 — 둘 다 0~100 고정."""
        sec = P.fab_section(P.parse(_csv("m14", "t", self._rows())))
        self.assertEqual(sec.count(">100<"), 2, "칸마다 100 눈금")
        self.assertIn("같은 자(0~100)·같은 시간축", sec)

    def test_위험_이상인_구간은_면을_칠한다(self):
        """'점수가 얼마다' 가 아니라 '화면이 무슨 색이었나' 가 우리가 보는 것이다."""
        # 변경 전부터 위험(52) 위인 분 · 후에 위험으로 올라온 분을 같이 둔다
        rows = [("2026-09-13 11:%02d" % m, 55, 60) for m in range(0, 20)]
        rows += [("2026-09-13 12:%02d" % m, 40, 60) for m in range(0, 10)]
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertIn('fill="#b91c1c"', sec, "변경 후 위험 구간 칠이 없다")
        self.assertIn('fill="#9ca3af"', sec, "변경 전 위험 구간 칠이 없다")

    def test_등급_컷을_같이_그린다(self):
        """★점수 곡선만 있으면 '그래서 화면이 바뀌었나' 를 못 읽는다."""
        sec = P.fab_section(P.parse(_csv("m14", "t", self._rows())))
        for nm, v in (("경계", 36), ("위험", 52), ("초위험", 72)):
            self.assertIn(f">{nm} {v}<", sec, f"{nm} 컷 선이 없다")

    def test_올라간_자리를_표시한다(self):
        """두 곡선은 대부분 겹쳐 있어서(M14 는 2,880분 중 28분만 다르다)
        곡선만 보면 어디가 바뀌었는지 눈에 안 들어온다."""
        sec = P.fab_section(P.parse(_csv("m14", "t", self._rows())))
        self.assertIn("#f59e0b", sec, "올라간 자리 표시가 없다")
        self.assertIn("올라간 자리", sec)
        self.assertIn("위험을 넘긴 자리", sec)

    def test_사건_구간을_띠로_깐다(self):
        rows = self._rows("2026-09-13")
        sec = P.fab_section(P.parse(_csv("m14", "t", rows)))
        self.assertIn("OHT 무언정지", sec, "알려진 사건 구간이 그림에 없다")

    def test_점수축은_0에서_100_고정(self):
        """★날마다 자가 바뀌면 두 날을 견줄 수 없다."""
        sec = P.fab_section(P.parse(_csv("m14", "t", self._rows())))
        self.assertIn('y="', sec)
        self.assertIn(">100<", sec)
        self.assertIn(">0<", sec)

    def test_기존_문서에_붙어도_그래프가_산다(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp(prefix="piog")
        try:
            p = os.path.join(tmp, "doc.html")
            shutil.copy(os.path.join(_BASE, "docs", P.INTO["M14"]), p)
            P.splice(p, P.fab_section(P.parse(_csv("m14", "t", self._rows()))))
            h = io.open(p, encoding="utf-8").read()
            i = h.index(P.MARK0)
            self.assertIn("<svg", h[i:], "붙인 절에 그림이 없다")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
