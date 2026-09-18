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
import shutil
import subprocess
import tempfile
import threading
import unittest
from copy import deepcopy
from datetime import datetime, timedelta

from . import util  # noqa: F401
import alarm_count
import sentinel
from lp_client import load_config

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


class 시스템별(unittest.TestCase):
    """ALL·FAB 다섯이 각각 자기 설정을 갖는다 (등급 컷 by_sys 와 같은 모양)."""

    CFG = {"grade": {
        "alarm": {"window_min": 10, "warn": 3, "danger": 1, "critical": 1},
        "alarm_by_sys": {"M14": {"warn": 5, "enabled": False},
                         "M16B": {"window_min": 30}}}}

    def test_칸이_없는_시스템은_공통값(self):
        p = alarm_count.policy(self.CFG, "M16A")
        self.assertEqual((p["window_min"], p["warn"]), (10, 3))
        self.assertTrue(p["enabled"])

    def test_칸이_있으면_그게_이긴다(self):
        p = alarm_count.policy(self.CFG, "M14")
        self.assertEqual(p["warn"], 5)
        self.assertFalse(p["enabled"], "적용/미적용도 시스템마다 따로다")
        self.assertEqual(p["danger"], 1, "안 준 값은 공통값 그대로")

    def test_한_시스템만_꺼도_다른_시스템은_돈다(self):
        """고객 요구: '각각 적용,미적용이 있어야 하고'."""
        off = alarm_count.scan(seq((0, "위험"),), self.CFG, "M14")
        on = alarm_count.scan(seq((0, "위험"),), self.CFG, "M16A")
        self.assertEqual(off[-1]["label"], "")
        self.assertEqual(on[-1]["label"], "위험중")

    def test_시스템마다_창이_다르다(self):
        s_ = seq((0, "위험"), (20, "정상"))
        self.assertEqual(alarm_count.scan(s_, self.CFG, "M16B")[-1]["danger"], 1,
                         "M16B 는 30분 창")
        self.assertEqual(alarm_count.scan(s_, self.CFG, "M16A")[-1]["danger"], 0,
                         "M16A 는 10분 창")

    def test_sys_cfg_뷰가_주면_알아서_고른다(self):
        """★server.py 가 시스템을 따로 안 들고 다녀도 되게 — 함수 서명이 안 바뀐다."""
        view = dict(self.CFG, _sys="M14")     # lp_client.sys_cfg 가 만드는 모양
        self.assertEqual(alarm_count.policy(view)["warn"], 5)
        self.assertEqual(alarm_count.sys_of(view), "M14")

    def test_ALL_은__sys_가_없다(self):
        # sys_cfg(cfg, "ALL") 은 cfg 를 그대로 돌려준다 — _sys 가 안 붙는다
        self.assertEqual(alarm_count.sys_of(self.CFG), "ALL")
        self.assertEqual(alarm_count.policy(self.CFG)["warn"], 3)

    def test_지문에_시스템_이름이_들어간다(self):
        # 값이 같아도 화면이 다르면 캐시가 섞이면 안 된다
        cfg = {"grade": {"alarm": {"warn": 3}}}
        self.assertNotEqual(alarm_count.sig(cfg, "M14"), alarm_count.sig(cfg, "M16A"))
        self.assertTrue(alarm_count.sig(cfg, "M14").startswith("M14:"))

    def test_개별_설정인지_알려준다(self):
        self.assertTrue(alarm_count.is_custom(self.CFG, "M14"))
        self.assertFalse(alarm_count.is_custom(self.CFG, "M16A"))

    def test_표는_화면이_그대로_그릴_모양(self):
        rows = alarm_count.table(self.CFG, ["ALL", "M14", "M16B"])
        self.assertEqual([r["sys"] for r in rows], ["ALL", "M14", "M16B"])
        self.assertEqual([r["custom"] for r in rows], [False, True, True])
        for r in rows:
            for k in ("enabled", "window_min", *alarm_count.KEYS):
                self.assertIn(k, r, k + " 가 표에서 빠졌다")

    def test_이상한_시스템_칸은_무시(self):
        cfg = {"grade": {"alarm_by_sys": {"M14": "이상한값",
                                          "_doc": "설명글은 시스템이 아니다"}}}
        self.assertEqual(alarm_count.policy(cfg, "M14")["warn"], 3, "기본으로 떨어진다")
        self.assertFalse(alarm_count.is_custom(cfg, "M14"))


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

    def test_정책_저장이_두_블록을_다_쓴다(self):
        # 공통값(alarm)과 시스템별(alarm_by_sys) 둘 다 config.json 에 남아야 한다
        self.assertIn('for _k in ("alarm", "alarm_by_sys"):', self.src,
                      "한쪽만 적으면 재시작 때 되돌아간다")

    def test_정책_객체를_갈아끼우지_않는다(self):
        # ★sys_cfg 뷰들이 grade 블록을 공유한다 — 통째로 바꾸면 끊긴다
        self.assertIn('by_a = g.setdefault("alarm_by_sys", {})', self.src)
        self.assertIn('by_a.setdefault(s_, {}).update(v)', self.src)

    def test_모르는_시스템은_막는다(self):
        m = re.search(r'if "alarm_by_sys" in b:[\s\S]*?g\.pop\("alarm_by_sys", None\)',
                      self.src)
        self.assertIsNotNone(m, "알람 저장 자리를 못 찾았다")
        self.assertIn("known = set(systems())", m.group(0))
        self.assertIn("if row is None:", m.group(0), "null 로 기본 되돌리기가 돼야 한다")

    def test_정책_조회가_시스템_여섯과_기본값을_준다(self):
        self.assertIn('"alarm_systems": alarm_count.table(CFG, systems())', self.src)
        self.assertIn('"alarm_default": dict(alarm_count.DEFAULTS)', self.src)

    def test_status_feed_는_지금_시스템_설정을_준다(self):
        # C["cfg"] 는 sys_cfg 뷰라 _sys 가 박혀 있다 — policy 가 알아서 고른다
        self.assertIn('alarm_count.policy(C["cfg"])', self.src)

    def test_들어온_값을_범위로_막는다(self):
        self.assertIn("alarm_count.LIMITS[k]", self.src,
                      "범위 검사가 모듈의 LIMITS 와 따로 놀면 안 된다")

    def test_점수_계산은_안_건드린다(self):
        """★이 시험이 제일 중요하다 — 고객이 이 자리에 데였다."""
        for f in ("fab_score.py", "sentinel.py"):
            self.assertNotIn("alarm_count", _read(f),
                             f"{f} 에 카운터가 들어갔다 — 점수 계산은 손대지 않는다")


class ALL화면의_FAB_카운터(unittest.TestCase):
    """ALL 화면에서 '어느 FAB 이 계속 나쁜가' 를 말한다.

    고객 지적: "실시간에 알람에서 ALL에서 ALL,FAB인지 그런 알람 내용이 없는것
    같은데" — ALL 종합점수만 세면 화면에 FAB 다섯 점수 칸이 있어도 그 중
    무엇이 눌러앉아 있는지가 안 보였다.
    """

    @classmethod
    def setUpClass(cls):
        cls.src = _read("server.py")
        cls.blk = re.search(r'    _apol_fab = \{\}[\s\S]*?_apol_fab\[_f\] = _fp',
                            cls.src)

    def test_FAB_별로_센다(self):
        self.assertIsNotNone(self.blk, "FAB 카운터 자리를 못 찾았다")
        self.assertIn("alarm_count.scan(_seq, CFG, _f)", self.blk.group(0),
                      "FAB 마다 **자기 정책**으로 세야 한다")

    def test_FAB_자기_컷으로_등급을_매긴다(self):
        # 컷이 FAB 별(grade.by_sys)인데 ALL 컷으로 매기면 서버와 화면 색이 갈린다
        self.assertIn("_fcfg = sys_cfg(CFG, _f)", self.blk.group(0))
        self.assertIn('grade(_v, _fcfg)["level"]', self.blk.group(0))

    def test_ALL_화면에서만_돈다(self):
        # FAB 화면은 그 FAB 이 곧 자기 줄이라 두 번 말하게 된다
        self.assertIn('if C["sys"] == "ALL" and ftab:', self.blk.group(0))

    def test_미적용_FAB_은_세지도_않는다(self):
        m = re.search(r'_fp = alarm_count\.policy\(CFG, _f\)\s*\n'
                      r'\s*if not _fp\["enabled"\]:\s*\n\s*continue', self.src)
        self.assertIsNotNone(m, "미적용인데 계속 세면 하루치를 헛돈다")

    def test_값을_모르는_분은_정상으로_안_센다(self):
        # 0/정상으로 세면 '없는 것' 을 '괜찮다' 고 말하게 된다
        self.assertIn('if _v is not None else ""', self.blk.group(0))

    def test_말풍선_글은_행마다_안_싣는다(self):
        # 1440행 × FAB 다섯 × 30자면 그것만 200KB 다. 정책을 한 번만 싣는다.
        self.assertNotIn("alarm_count.why(_a, _fp)", self.blk.group(0))
        self.assertIn('"alarm_fab": _apol_fab,', self.src,
                      "정책을 payload 에 한 번 실어야 화면이 글을 만든다")

    def test_이름표에_맞는_카운트를_싣는다(self):
        self.assertIn('_LVKEY = {"경계중": "warn", "위험중": "danger", '
                      '"초위험중": "critical"}', self.src)
        self.assertIn('_a[_LVKEY[_a["label"]]]', self.blk.group(0))

    def test_이름표_표가_모듈과_어긋나지_않는다(self):
        """★server 의 _LVKEY 와 alarm_count.LABEL 이 따로 놀면 엉뚱한 수가 뜬다."""
        m = re.search(r'_LVKEY = \{([^}]*)\}', self.src)
        keys = set(re.findall(r'"([^"]+)": "', m.group(1)))
        self.assertEqual(keys, set(alarm_count.LABEL.values()))
        vals = set(re.findall(r': "([^"]+)"', m.group(1)))
        self.assertEqual(vals, set(alarm_count.KEYS))


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

    def test_줄마다_어느_시스템인지_적는다(self):
        m = re.search(r"function almLine\(sys, lv, n, why\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m, "almLine 을 못 찾았다")
        self.assertIn("${esc(sys)}", m.group(0),
                      "이름이 없으면 ALL 인지 M14B 인지 말할 수 없다")

    def test_FAB_줄은_ALL_화면에서만(self):
        m = re.search(r"function almCell\(r\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m)
        self.assertIn("if(SYS === 'ALL' && r.alm_fab){", m.group(0))
        self.assertIn("FABS.forEach(f =>", m.group(0),
                      "차례는 오른쪽 점수 칸과 같은 FABS 순서다")

    def test_FAB_정책도_서명에_묶인다(self):
        self.assertIn("function almSig(){ return JSON.stringify(ALARM) + '~' + "
                      "JSON.stringify(ALARM_FAB); }", self.src)
        self.assertEqual(self.src.count("ALARM_FAB = fd.alarm_fab || {};"), 2,
                         "실시간·과거 두 곳 다 받아야 한다")

    def test_배지는_점수_칸이_아니라_자기_칸(self):
        # 점수 칸(108px) 안에 넣었더니 등급 알약 밑으로 접혀 점수의 부속처럼
        # 보였다 — 고객 지적. 칸을 따로 뺐다.
        m = re.search(r"<td><div class=\"ttl\">\$\{Math\.round\(r\.score\)\}[\s\S]*?</td>",
                      self.src)
        self.assertIsNotNone(m, "종합점수 칸을 못 찾았다")
        self.assertNotIn("almChip(r)", m.group(0), "아직 점수 칸 안에 있다")
        self.assertIn("${almCell(r)}${hiCell(r)}", self.src,
                      "알람 칸은 종합점수 **바로 옆**(HI_FAB 앞)이다")

    def test_칸_수가_여덟로_늘었다(self):
        # ★머리글·빈 표·'더 보기' 줄이 다 같이 움직여야 한다
        self.assertIn("const ncol = 8 + (FABS.length ? FABS.length + 1 : 0);", self.src)
        self.assertEqual(self.src.count('<th class="acol"'), 2,
                         "실시간·과거 두 표 다 머리글이 있어야 한다")
        for t in ('<tbody id="cases"><tr><td colspan="8"',
                  '<tbody id="pcases"><tr><td colspan="8"'):
            self.assertIn(t, self.src, t)
        self.assertEqual(
            self.src.count("""$('#pcases').innerHTML = '<tr><td colspan="8" class="empty">"""), 5,
            "과거 탭의 안내 줄 다섯 개가 다 여덟 칸이어야 한다")

    def test_FAB_칸은_알람_뒤에_끼운다(self):
        # 스코어 뒤에 끼우면 HI_FAB 이 종합점수와 알람 사이로 파고든다
        self.assertIn("let at = tr.querySelector('th.acol') || sc;", self.src)

    def test_표_최소폭도_같이_올렸다(self):
        # 칸이 하나 늘었는데 min-width 가 그대로면 마지막 칸이 0으로 눌린다
        self.assertIn("min-width:1300px", self.src)

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
        for need in ('id="almrow"', 'id="alm-save"', 'id="alm-now"', 'id="almnote"'):
            self.assertTrue(need in self.src, need + " 가 없다")

    def test_줄마다_네_칸과_적용_스위치(self):
        m = re.search(r"function almRow\(a\)\{[\s\S]*?\n\}", self.src)
        self.assertTrue(m, "almRow 를 못 찾았다")
        blk = m.group(0)
        for need in ("almNum(`almw-${a.sys}`, a.window_min, 180)",
                     "almNum(`alm1-${a.sys}`, a.warn)",
                     "almNum(`alm2-${a.sys}`, a.danger)",
                     "almNum(`alm3-${a.sys}`, a.critical)",
                     'id="almon-${a.sys}"', 'data-almreset="${a.sys}"'):
            self.assertTrue(need in blk, need + " 가 없다")

    def test_지금_보는_시스템_설정이_표_배지로_간다(self):
        m = re.search(r"function almFill\(d\)\{[\s\S]*?\n\}", self.src)
        self.assertTrue(m, "almFill 을 못 찾았다")
        self.assertIn("const mine = list.find(a => a.sys === SYS);", m.group(0))
        self.assertIn("if(mine) ALARM = mine;", m.group(0))

    def test_저장이_여섯_줄을_다_보낸다(self):
        m = re.search(r"\$\('#alm-save'\)\.onclick = \(\) => \{[\s\S]*?almSave"
                      r"\(\{alarm_by_sys: by\}\);", self.src)
        self.assertTrue(m, "저장 버튼 배선을 못 찾았다")
        blk = m.group(0)
        self.assertIn("ALM_SYS.forEach(a =>", blk, "여섯 줄을 다 훑어야 한다")
        for need in ("window_min:", "warn:", "danger:", "critical:", "enabled:"):
            self.assertTrue(need in blk, need + " 가 저장에서 빠졌다")
        self.assertIn("if(ALM_RESET.has(a.sys)){ by[a.sys] = null; return; }", blk,
                      "'기본' 을 누른 시스템은 null 로 보내 되돌려야 한다")

    def test_적용_스위치는_줄마다_있고_누르는_즉시_반영(self):
        m = re.search(r"document\.querySelectorAll\('\[data-almon\]'\)"
                      r"\.forEach\(c => c\.onchange = \(\) => \{[\s\S]*?\}\);",
                      self.src)
        self.assertIsNotNone(m, "줄마다 걸리는 적용 스위치를 못 찾았다")
        self.assertIn("almSave({alarm_by_sys: {[c.dataset.almon]: {enabled: c.checked}}});",
                      m.group(0), "저장을 또 눌러야 하면 '껐는데 왜 그대로냐' 가 된다")

    def test_저장은_등급_컷과_같은_길(self):
        m = re.search(r"async function almSave\(body\)\{[\s\S]*?\n\}", self.src)
        self.assertIsNotNone(m)
        self.assertIn("post('/api/score_policy'", m.group(0), "길이 둘이면 한쪽만 저장된다")
        self.assertIn("repaintGrades()", m.group(0), "저장 뒤 지금 화면을 새 설정으로")

    def test_알람_위험은_빨강_하지만_등급_알약은_그대로(self):
        """고객 지정: 경계는 지금 색 유지, 위험·초위험은 둘 다 빨강.

        ★.lv위험 자체를 고치면 종합점수 칸의 등급 알약·추이 밴드까지
          빨개진다. 알람 배지에서만 덮어야 한다.
        """
        self.assertIn(".chip.alm.lv위험{color:var(--crit)}", self.src,
                      "알람 배지의 위험이 아직 주황이다")
        self.assertIn(".lv위험{background:color-mix(in srgb, var(--major) 16%, "
                      "var(--panel));color:var(--major)}", self.src,
                      "등급 알약의 위험 색이 바뀌었다 — 여기는 건드리면 안 된다")
        # 경계는 덮지 않는다 (지금 색 유지)
        self.assertNotIn(".chip.alm.lv경계{", self.src, "경계는 지금 색 그대로다")
        # 초위험은 원래 --crit 이라 덮을 것이 없다
        self.assertNotIn(".chip.alm.lv초위험{", self.src)

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


class 케이스_저장이_서로_밟지_않는다(unittest.TestCase):
    """LLM 자동 판단은 케이스마다 실(thread)을 하나씩 띄우고, 끝나면 각자
    store.save() 를 부른다.

    예전에는 임시파일 이름이 늘 'cases.json.tmp' 하나였고 잠금도 없었다.
    여럿이 동시에 끝나면
      · 먼저 끝난 실이 os.replace 로 그 파일을 걷어가 나머지가
        FileNotFoundError 로 터지고 (재 보니 12번 중 7번)
      · 터진 저장은 호출부(_auto_judge)가 '자동 판단 예외' 한 줄만 찍어
        **그 판단이 파일에 안 남았다**
      · 운 나쁘면 두 실의 글이 한 파일에 섞여 cases.json 이 깨진다

    ★속도 문제가 아니다 — 저장이 몰려도 화면 요청은 안 늦어졌다
      (json.dump 는 쓸 때마다 GIL 을 놓는다). 잃는 것은 판단이다.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="casesave")
        cfg = deepcopy(load_config())
        cfg.setdefault("storage", {})["cases"] = os.path.join(self.tmp, "cases.json")
        self.store = sentinel.CaseStore(cfg)
        self.store.cases = [
            {"id": "C%03d" % i, "area": "M16HUB", "status": "진행", "level": "위험",
             "timeline": [{"at": "2026-09-16T14:%02d:00" % k, "what": "감지"} for k in range(20)],
             "llm": {"판단": "가" * 200, "확신도": 82}}
            for i in range(200)
        ]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_동시에_저장해도_안_터진다(self):
        errs = []

        def work():
            try:
                self.store.save()
            except Exception as e:                       # noqa: BLE001
                errs.append("%s: %s" % (type(e).__name__, e))

        for _ in range(6):                               # 여러 판이 몰리는 상황
            ths = [threading.Thread(target=work) for _ in range(12)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
        self.assertEqual(errs, [], "동시 저장이 터진다 — 그만큼 판단이 안 남는다")

    def test_동시에_저장해도_파일이_안_깨진다(self):
        def work():
            try:
                self.store.save()
            except Exception:                            # noqa: BLE001
                pass

        ths = [threading.Thread(target=work) for _ in range(16)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        with open(self.store.path, encoding="utf-8") as f:
            got = json.load(f)                           # 깨졌으면 여기서 터진다
        self.assertEqual(len(got), 200)

    def test_임시파일을_안_남긴다(self):
        self.store.save()
        left = [n for n in os.listdir(self.tmp) if n.endswith(".tmp")]
        self.assertEqual(left, [], "임시파일이 쌓인다")

    def test_이미_잠금을_쥔_채_불러도_안_멎는다(self):
        """★ingest·ack·mark_normal·close 는 잠금을 쥔 채 save() 를 부른다.
        그냥 Lock 이면 제 잠금에 제가 걸려 서버가 그 자리에서 멎는다."""
        done = []

        def work():
            with self.store._lock:
                self.store.save()
            done.append(1)

        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join(timeout=5)
        self.assertEqual(done, [1], "잠금을 쥔 채 저장하면 멎는다 (RLock 이어야 한다)")
