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
    """★'좋아졌다' 는 **못 보던 것을 보게 됐다** 는 뜻이다.
    이미 9분 잡히던 구간이 10분이 된 것은 운전원에게 아무 차이가 없다."""

    def _doc(self, rows):
        return P.build([P.parse(_csv("m14", "t", rows))])

    def test_컷을_못_넘으면_초록으로_안_쓴다(self):
        h = self._doc([("2026-09-13 11:%02d" % m, 21, 29) for m in range(38, 58)])
        i = h.index("0. 한 줄로")
        self.assertIn("note miss", h[i:i + 400], "화면이 안 바뀌었는데 초록이다")
        self.assertIn("화면은 거의 그대로", h)

    def test_이미_잡히던_구간이_1분_늘어도_초록이_아니다(self):
        rows = [("2026-09-13 05:%02d" % m, 90, 90) for m in range(16, 26)]   # 이미 초위험
        rows.append(("2026-09-13 05:30", 53, 60))                            # 한 분 더
        h = self._doc(rows)
        i = h.index("0. 한 줄로")
        self.assertIn("note miss", h[i:i + 400],
                      "이미 보이던 구간이 1분 늘었는데 좋아졌다고 쓴다")

    def test_0에서_1로_올라가면_초록이다(self):
        """못 보던 사건이 보이기 시작한 것 — 이건 진짜 좋아진 것이다."""
        rows = [("2026-09-13 11:%02d" % m, 30, 30) for m in range(38, 58)]
        rows.append(("2026-09-13 12:00", 55, 62))
        h = self._doc(rows)
        i = h.index("0. 한 줄로")
        self.assertIn("note good", h[i:i + 400])
        self.assertIn("못 보던 사건을 보기 시작", h)


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

    def test_실제_받은_자료로도_돈다(self):
        """받은 노트북이 아직 있으면 그것으로도 한 번 돌려 본다."""
        up = ("/root/.claude/uploads/d02bef53-654d-5efc-a5eb-2c6bb7b9e067/"
              "730996b1-spspss.ipynb_24.txt")
        if not os.path.isfile(up):
            self.skipTest("받은 자료가 이 환경에 없다")
        sets = [p for p in (P.parse(c) for c in P.read_cells(up)) if p]
        self.assertEqual({s["fab"] for s in sets}, {"M14", "M16HUBROOM"})
        got = {s["fab"]: sum(P.stats(s["rows"])["moved"].values()) for s in sets}
        self.assertEqual(got, {"M16HUBROOM": 0, "M14": 1},
                         "등급이 바뀐 분 수가 달라졌다 — 결론이 바뀐다")


if __name__ == "__main__":
    unittest.main()
