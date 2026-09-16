# -*- coding: utf-8 -*-
"""layout.xml → 캐시 JSON — HMI 맵을 그리는 데 필요한 것이 빠짐없이 나오나.

왜 고쳤나
    예전 파서는 Addr/NextAddr 만 봤다. layout.xml 에는 스테이션(22,971)·라벨
    (ZC/HID/베이/열/MTL 1,205)·센서(5,621)·노드 글자방향/합류/분기가 다 있는데
    그리지 않았다 — 고객이 "정보는 다 있으니 현장 HMI 맵처럼 그려 달라" 고
    한 그것이다.
    예전 파서는 Addr 그룹을 닫지 않고 다음 Addr 이 열릴 때 커밋해서, 그 사이
    다른 그룹(라벨·센서)의 draw-y/address 가 새어 들어갔다 — 실물에서 노드
    하나가 사라지고(16245) 하나는 좌표가 틀렸다(13315). 그룹을 스택으로 닫는다.

여기서 지키는 것
    · nodes / adj / edges 는 예전 정의 그대로 (재생 엔진이 쓴다)
    · 스테이션 자리 = 기본 진행 엣지 위 offset ÷ distance-puls
    · 라벨 = 앵커 노드 + (dx, dy), 종류 분류
    · 스키마 번호가 캐시 앞머리에 있어 옛 캐시를 다시 만든다
"""
import json
import os
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import data_loader as DL                                     # noqa: E402

REAL_ZIP = "/home/user/ASAS/OHT2/layout/layout/layout.zip"


def _param(k, v):
    return f'<param division="" update="false" comment="" version="1" value="{v}" key="{k}"/>'


def _addr(no, x, y, nxt, puls, tdir=2, junction=False, branch=False, stations=(), extra_next=None):
    """실물과 같은 꼴의 Addr 그룹 — NextAddr 둘(기본·비기본) + Station 들."""
    out = [f'<group name="Addr{no:05d}" class="jp.co.daifuku.tsc.common.layoutdata.layout.address.Addr">',
           '<list key="cad-right-vhlarea"><param value="15"/><param value="15"/></list>',
           _param("address", no), _param("draw-x", x), _param("draw-y", y),
           _param("draw-text-direction", tdir),
           _param("junction", "true" if junction else "false"),
           _param("branch", "true" if branch else "false"),
           '<group name="NextAddr00000" class="jp.co.daifuku.tsc.common.layoutdata.layout.address.NextAddr">',
           _param("basic-direction", "true"), _param("next-address", nxt), _param("distance-puls", puls),
           '<list key="nextpoint-disp"><param value="0"/><param value="0"/></list>',
           '</group>',
           '<group name="NextAddr00001" class="jp.co.daifuku.tsc.common.layoutdata.layout.address.NextAddr">',
           _param("basic-direction", "false"), _param("next-address", extra_next or 0), _param("distance-puls", puls),
           '</group>']
    for i, (sno, typ, off, port) in enumerate(stations):
        out += [f'<group name="Station{i}" class="jp.co.daifuku.tsc.common.layoutdata.layout.address.Station">',
                _param("no", sno), _param("type", typ), _param("offset", off), _param("port-id", port),
                _param("category", 3), '</group>']
    out.append('</group>')
    return "\n".join(out)


def _label(name, text, addr, dx, dy, point=0):
    return "\n".join([f'<group name="Label{name}" class="jp.co.daifuku.tsc.common.layoutdata.layout.label.Label">',
                      _param("address", addr), _param("draw-y", dy), _param("draw-x", dx),
                      _param("machine-id", text), _param("point", point), '</group>'])


def _sensor(x, y, d):
    return "\n".join(['<group name="SensorS-1" class="jp.co.daifuku.tsc.common.layoutdata.layout.zcu.Sensor">',
                      _param("draw-x", x), _param("draw-y", y), _param("draw-direction", d),
                      _param("address", 0), '</group>'])


def mini_xml():
    """네모 루프 하나 + 모서리 노드 + 스테이션 + 라벨 — 실물 16001~ 루프를 축약."""
    body = [
        '<?xml version="1.0"?>',
        '<group name="Layout" class="jp.co.daifuku.tsc.common.layoutdata.layout.Layout">',
        _param("scale", "30.0"),
        '<group name="AddrControl" class="jp.co.daifuku.tsc.common.layoutdata.layout.address.AddrControl">',
        # 세로 레일 (오른쪽 글자) — 스테이션 오른쪽 3개 · 왼쪽 1개
        _addr(1, 100, 100, 2, 200000, tdir=2,
              stations=((17001, 9, 50000, "P-1"), (17002, 9, 100000, "P-2"), (17003, 9, 150000, "P-3"),
                        (27001, 8, 100000, "L-1"))),
        _addr(2, 100, 160, 3, 100000, tdir=2, branch=True, extra_next=9),
        _addr(3, 129, 194, 4, 195000, tdir=1,
              stations=((4904, 1, 115000, "4PSA1902_R0"), (4905, 1, 143000, "4PSA1902_R1"))),   # 모서리(대각) 노드
        _addr(4, 200, 194, 5, 100000, tdir=0),
        _addr(5, 200, 100, 1, 100000, tdir=3, junction=True),
        _addr(9, 300, 160, 0, 0, tdir=0),                                  # 다음 없음 (막다른)
        '</group>',
        '<group name="LabelControl" class="jp.co.daifuku.tsc.common.layoutdata.layout.label.LabelControl">',
        _label("ZC590A", "ZC590A", 2, 20, 20), _label("HID-B21-1(029)", "HID-B21-1(029)", 4, 20, 20),
        _label("B44", "B44", 1, 0, -30, 1), _label("C1", "C1", 5, 0, -30, 1),
        _label("MTL003", "MTL003", 4, 20, 20), _label("HSU001", "HSU001", 3, 20, 40),
        '</group>',
        '<group name="ZcuControl" class="jp.co.daifuku.tsc.common.layoutdata.layout.zcu.ZcuControl">',
        _sensor(100.5, 130.2, 3),
        '</group>',
        # ★예전 파서를 무너뜨린 꼴 — Addr 뒤에 draw-y/address 를 가진 다른 그룹
        '<group name="ApAP" class="jp.co.daifuku.tsc.common.layoutdata.layout.ap.Ap">',
        _param("draw-x", 999), _param("draw-y", 999), _param("id", "AP"),
        '</group>',
        '</group>',
    ]
    return "\n".join(body)


class 캐시_JSON(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="wm_layout")
        cls.path = os.path.join(cls.tmp, "cache.json")
        cls.n, cls.e = DL._parse_layout_xml_to_json(mini_xml(), cls.path)
        cls.d = json.load(open(cls.path, encoding="utf-8"))
        cls.L = DL.LayoutData().load(cls.path)

    def test_노드_엣지_정의는_예전_그대로(self):
        self.assertEqual(self.n, 6)
        self.assertEqual(self.d["nodes"]["1"], [100.0, 100.0])
        self.assertEqual(self.d["adj"]["2"], [3, 9])          # 기본 + 분기, 문서 순서
        self.assertIn("1,2", self.d["edges"]); self.assertEqual(self.d["edges"]["1,2"], 600)  # 60 × 10
        self.assertNotIn("9,0", self.d["edges"])             # next-address 0 은 연결이 아니다
        self.assertEqual(self.e, len(self.d["edges"]))

    def test_뒤따르는_그룹의_좌표가_새어_들어오지_않는다(self):
        """예전 파서의 실수 — Ap 그룹의 draw-y=999 가 마지막 Addr 에 붙었다."""
        self.assertEqual(self.d["nodes"]["9"], [300.0, 160.0])

    def test_스키마_번호가_앞머리에_있다(self):
        head = open(self.path, encoding="utf-8").read(40)
        self.assertIn('"schema": 2', head)
        self.assertTrue(DL._cache_schema_ok(self.path))

    def test_옛_캐시는_다시_만든다(self):
        old = os.path.join(self.tmp, "old.json")
        json.dump({"nodes": {}, "adj": {}, "edges": {}}, open(old, "w"))
        self.assertFalse(DL._cache_schema_ok(old))

    def test_스테이션_자리는_기본_엣지_위_비율(self):
        st = {s[4]: s for s in self.L.stations}
        self.assertEqual(st[17001][:2], [1, 2])               # 노드 1 → 다음 2
        self.assertAlmostEqual(st[17001][2], 0.25, places=3)  # 50000 / 200000
        self.assertAlmostEqual(st[17003][2], 0.75, places=3)
        self.assertEqual(st[17001][3], 9)                     # 오른쪽
        self.assertEqual(st[27001][3], 8)                     # 왼쪽
        self.assertEqual(st[4904][5], "4PSA1902_R0")

    def test_스테이션은_노드_안에_있는_것만_센다(self):
        self.assertEqual(len(self.L.stations), 6)

    def test_라벨은_앵커_노드와_오프셋(self):
        lb = {l[0]: l for l in self.L.labels}
        self.assertEqual(lb["ZC590A"][1:5], [2, 20.0, 20.0, "zc"])
        self.assertEqual(lb["HID-B21-1(029)"][4], "hid")
        self.assertEqual(lb["B44"][4], "bay")
        self.assertEqual(lb["C1"][4], "col")
        self.assertEqual(lb["MTL003"][4], "mtl")
        self.assertEqual(lb["HSU001"][4], "eq")
        self.assertEqual(lb["B44"][2:4], [0.0, -30.0])

    def test_노드_메타(self):
        self.assertEqual(self.L.meta[5], [3, 1, 0])           # 왼쪽 글자 · 합류
        self.assertEqual(self.L.meta[2], [2, 0, 1])           # 오른쪽 글자 · 분기

    def test_센서(self):
        self.assertEqual(self.L.sensors, [[100.5, 130.2, 3]])

    def test_옛_캐시를_읽어도_죽지_않는다(self):
        old = os.path.join(self.tmp, "old2.json")
        json.dump({"nodes": {"1": [0, 0]}, "adj": {}, "edges": {}}, open(old, "w"))
        L = DL.LayoutData().load(old)
        self.assertEqual(L.schema, 1)
        self.assertEqual(L.stations, []); self.assertEqual(L.labels, [])


@unittest.skipUnless(os.path.isfile(REAL_ZIP), "실물 layout.zip 없음")
class 실물_M14(unittest.TestCase):
    """실물 220MB 로 한 번 — 수치는 현장 문서(layout_일부분석.md)와 맞아야 한다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="wm_real")
        xml = zipfile.ZipFile(REAL_ZIP).read("layout.xml").decode("utf-8", "replace")
        cls.n, cls.e = DL._parse_layout_xml_to_json(xml, os.path.join(cls.tmp, "c.json"))
        cls.L = DL.LayoutData().load(os.path.join(cls.tmp, "c.json"))

    def test_수량이_문서와_같다(self):
        self.assertEqual(self.n, 9403)                        # Address 9,403
        self.assertEqual(len(self.L.stations), 22971)         # Station 22,971
        self.assertEqual(len(self.L.labels), 1205)
        self.assertEqual(len(self.L.sensors), 5621)

    def test_캡처의_루프가_그대로_있다(self):
        """고객 캡처(16001~16020) — 글자방향·합류·스테이션이 데이터와 맞는다."""
        self.assertEqual(self.L.meta[16013][:2], [3, 1])      # 왼쪽 글자 · 합류(✕)
        self.assertEqual(self.L.meta[16003], [2, 0, 1])       # 오른쪽 글자 · 분기
        st = sorted(s[4] for s in self.L.stations if s[0] == 16004)
        self.assertEqual(st, [4904, 4905])                    # 캡처의 겹친 '490804' 글자
        lb = {l[0]: l for l in self.L.labels}
        self.assertEqual(lb["ZC590A"][1], 16011)
        self.assertEqual(lb["HID-B21-1(029)"][1], 4611)

    def test_예전_파서가_잃던_노드가_있다(self):
        self.assertIn(16245, self.L.nodes)


if __name__ == "__main__":
    unittest.main()
