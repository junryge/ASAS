# -*- coding: utf-8 -*-
"""로그프레소 쿼리 — 두 벌(agg30 · raw)을 들고 있고, 되돌릴 수 있나.

고객이 준 쿼리(MSG_ID=2 · 30초 묶음)로 바꾸되 "다시 원본 할 수도 있다" 고 해서
예전 쿼리를 지우지 않고 프로필로 남겼다.

★pandas·requests 없이 돌아야 한다 (폐쇄망·이 시험 환경 둘 다). 그래서 모듈을
  import 하지 않고 쿼리 만드는 토막만 떼어 exec 한다 — 배포되는 그 코드다.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)


def _read(*p):
    with open(os.path.join(APP, *p), encoding="utf-8") as fh:
        return fh.read()


def _load(remote="icamcslogdt01", env=None):
    """logpresso_query.py 의 쿼리 토막만 떼어 돌린다."""
    src = _read("logpresso_query.py")
    a, b = src.index("def _q_raw("), src.index("def _fetch(")
    ns = {"os": os, "REMOTE_NODE": remote}
    old = os.environ.get("LP_QUERY_PROFILE")
    if env is None:
        os.environ.pop("LP_QUERY_PROFILE", None)
    else:
        os.environ["LP_QUERY_PROFILE"] = env
    try:
        exec(src[a:b], ns)
    finally:
        if old is None:
            os.environ.pop("LP_QUERY_PROFILE", None)
        else:
            os.environ["LP_QUERY_PROFILE"] = old
    return ns


F, T, TBL = "20260917050000", "20260917051000", "oht_data_m16a"


class 쿼리두벌(unittest.TestCase):
    def setUp(self):
        self.ns = _load()
        self.q = lambda pf=None: self.ns["_build_query"](F, T, TBL, pf)

    def test_둘_다_있다(self):
        self.assertEqual(sorted(self.ns["QUERY_PROFILES"]), ["agg30", "raw"])

    def test_기본은_고객이_준_쿼리(self):
        self.assertEqual(self.ns["PROFILE"], "agg30")

    def test_고객이_준_쿼리_그대로(self):
        """★한 글자 틀리면 로그프레소가 문법 오류를 낸다 — 받은 글자 그대로 본다."""
        q = self.q("agg30")
        for piece in (
            f'table from={F} to={T} {TBL}',
            '| search MSG_ID == "2"',
            '| sort _time',
            '| eval _time = datetrunc(_time, "30s")',
            '| stats first(ADDRESS) as ADDRESS, first(DISTANCE) as DISTANCE,',
            'first(NEXT_ADDRESS) as NEXT_ADDRESS, first(EDGE) as EDGE,',
            'first(CARRIER) as CARRIER, first(STATUS) as STATUS,',
            'first(OPERATION_STATUS) as OPERATION_STATUS',
            'by VEHICLE, _time',
            '| sort _time, VEHICLE',
        ):
            self.assertIn(piece, q, piece)

    def test_예전_쿼리도_그대로_남아_있다(self):
        self.assertIn(f'table from={F} to={T} {TBL} | sort _time', self.q("raw"))
        self.assertNotIn("MSG_ID", self.q("raw"), "raw 는 거르지 않는다")
        self.assertNotIn("datetrunc", self.q("raw"))

    def test_remote_로_감싼다(self):
        for pf in ("agg30", "raw"):
            self.assertTrue(self.q(pf).startswith("remote icamcslogdt01 [ "), pf)
            self.assertTrue(self.q(pf).endswith(" ]"), pf)

    def test_REMOTE_NODE_를_비우면_안_감싼다(self):
        ns = _load(remote="")
        self.assertFalse(ns["_build_query"](F, T, TBL).startswith("remote"))

    def test_환경변수로_되돌린다(self):
        self.assertEqual(_load(env="raw")["PROFILE"], "raw")

    def test_모르는_프로필은_막는다(self):
        """조용히 기본으로 떨어지면 무엇으로 쳤는지 모른 채 빈 결과를 본다."""
        with self.assertRaises(ValueError):
            self.q("없는거")

    def test_테이블_이름을_그대로_넣는다(self):
        self.assertIn("oht_data_m16a", self.q("agg30"))
        self.assertNotIn("oht_data_m16A", self.q("agg30"))


class 배선(unittest.TestCase):
    def test_조각내기도_프로필을_들고_간다(self):
        """★30MB 넘어 반으로 쪼갤 때 프로필을 안 넘기면 그 조각만 기본 쿼리로 친다."""
        s = _read("logpresso_query.py")
        m = re.search(r"def query_oht_chunked\([\s\S]*?\n    return result", s)
        self.assertIsNotNone(m)
        blk = m.group(0)
        self.assertIn("profile: str = None", blk)
        self.assertIn("_fetch(f_s, t_s, table, profile)", blk)
        self.assertEqual(blk.count("chunk_minutes, profile)"), 2, "쪼갠 두 조각 다")

    def test_API_가_profile_을_받아_넘긴다(self):
        s = _read("main.py")
        self.assertIn("profile = (body.get('profile') or '').strip() or None", s)
        self.assertIn("chunk_minutes=chunk_minutes, profile=profile)", s)

    def test_어느_쿼리로_쳤는지_로그에_남는다(self):
        s = _read("logpresso_query.py")
        self.assertIn('print(f"[쿼리] 프로필 {used}', s)
        self.assertIn('print(f"  [Q] {q}")', s, "실제 쿼리 글도 그대로 찍혀야 한다")

    BAK = "logpresso_query_원본_raw쿼리.py.bak"

    def test_원본_백업이_있다(self):
        """고객: "다시 원본 할 수도 있어, 백업도 만들어 두라" — 파일째로 남긴다.
        (프로필 raw 로 되돌리는 길이 먼저지만, 파일이 통째로 필요할 때를 대비한다.)"""
        self.assertTrue(os.path.isfile(os.path.join(APP, self.BAK)), self.BAK + " 가 없다")
        o = _read(self.BAK)
        self.assertIn("inner = f'table from={from_dt} to={to_dt} {table} | sort _time'", o)
        self.assertNotIn("MSG_ID", o)


if __name__ == "__main__":
    unittest.main()
