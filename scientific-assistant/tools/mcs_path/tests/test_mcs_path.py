# -*- coding: utf-8 -*-
"""MCS 로그 → 캐리어 이동 그림 (tools/mcs_path/mcs_path.py).

실제 로그는 저장소에 두지 않는다 — 여기서는 MCS 로그 모양(띄어 쓴 XML)을 그대로 흉내 낸 가짜 로그를 만든다.
장비 · 캐리어 ID 는 모두 지어낸 것이다.

지키는 것
  · 노트북 표 · 원본 로그 줄 · CSV 를 읽는다
  · 경로: 설비 → (위치 기록 없음) → 스토커(입고 포트 → 크레인 → 출고 포트) → OHT → ZFS
  · 한 번 보인 뒤 기록이 끊긴 시간은 머문 시간으로 세지 않는다
  · 상태: 완료 · 이동 중(OHT 에 실림) · 반송 대기 — 조회 시각(now) 기준
  · 그림(SVG)은 올바른 XML · 움직임 값(JSON)은 시간 순서
"""
import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import mcs_path as MP  # noqa: E402

CAR, EQP, STK, OHT, VEH, ZFS, ZFS0 = "TEST0001", "9EQP0001", "9XNS0001", "9XCM0001", "V09001", "9XFZ01G1", "9XFZ02G1"
SHELF = "9XFZ01-007"
JOB = "JTEST000120260102100000"


def _es(t, name, machine, fields, send=False):
    """설비 통신(STORAGE- · RAIL- · INV-) 한 줄."""
    body = " ".join("< %s > %s < /%s >" % (k, v, k) for k, v in fields.items())
    op = "EsSender.send" if send else "EsListener.onMsg"
    text = ("[ %s ] [ WELL ] [ Tibrv Dispatcher ] [ kr.x.%s ] [ < MESSAGE > < HEADER > < MESSAGENAME > %s < /MESSAGENAME > "
            "< TIME > %s < /TIME > < /HEADER > < ORIGINATED > < MACHINENAME > %s < /MACHINENAME > < /ORIGINATED > "
            "< DATA > %s < /DATA > < /MESSAGE > ]" % (t, op, name, t, machine, body))
    return {"MESSAGENAME": name, "TEXT": text, "MACHINENAME": machine, "CARRIER": CAR, "UNITNAME": "",
            "OPERATION_NAME": op, "TIME_EX": "[%s]" % t, "COMMAND": ""}


def _ui(t, machine, unit, state):
    row = _es(t, "UI-CARRIER", machine, {"CARRIERNAME": CAR, "MACHINENAME": machine, "UNITNAME": unit, "STATE": state, "TYPE": "FOUP"})
    row["UNITNAME"] = unit
    return row


def _host(t, cmd, attrs, send=True):
    """MES ↔ MCS (MCSMHS_ · MHSMCS_) 한 줄 — 값이 속성으로 온다."""
    a = " ".join('%s="%s"' % kv for kv in attrs.items())
    text = ("[ %s ] [ WELL ] [ x ] [ HostInterface.%s ] [ < ?xml version=\"1.0\"? > < Envelop > < Header > < Factory > M99 < /Factory > "
            "< Command > %s < /Command > < /Header > < Body > < DATA DESTINATION=\"MHS\" ORIGINATION=\"MCS\" > < %s %s / > < /DATA > < /Body > < /Envelop > ]"
            % (t, "send" if send else "onMsg", cmd, cmd, a))
    return {"MESSAGENAME": "", "TEXT": text, "MACHINENAME": "", "CARRIER": CAR, "UNITNAME": "",
            "OPERATION_NAME": "HostInterface." + ("send" if send else "onMsg"), "TIME_EX": "[%s]" % t, "COMMAND": cmd}


D = "2026-01-02 "


def fake_log():
    c = {"CARRIERID": CAR}
    return [
        _host(D + "10:00:00.000", "MHSMCS_CHANGED_DEVICE_INFO_EVENT",
              {"DEVICE_ID": EQP, "DEVICE_STATE": "DOWN", "CARRIER_ID": CAR, "SUB_DEVICE_ID": "2", "SUB_DEVICE_LOAD_STATE": "OCCUPIED"}, send=False),
        _es(D + "10:02:00.000", "STORAGE-CARRIERIDREAD", STK, dict(c, CARRIERLOC=STK + "M_IN03")),
        _es(D + "10:03:00.000", "STORAGE-CARRIERWAITIN", STK, dict(c, CARRIERLOC=STK + "M_IN03")),
        _ui(D + "10:03:00.050", STK, STK + "M_IN03", "WAITIN"),
        _host(D + "10:03:00.100", "MHSMCS_MATERIAL_DEST_REP",
              {"CARRIER_ID": CAR, "CARRIER_TYPE": "FOUP", "CARRIER_SUB_TYPE": "Metal", "CURRENT_FLOOR": "2F", "DESTINATION_ID": ZFS0,
               "DESTINATION_TYPE": "ZFS", "LOT_ID": "LOTX0001", "PRIORITY": "40", "SOURCE_ID": STK, "SOURCE_TYPE": "STOCKER_PORT",
               "WAFER_QTY": "13"}, send=False),
        _host(D + "10:03:00.200", "MCSMHS_TRANSPORT_JOB_CREATED_EVENT", {"CARRIER_ID": CAR, "DESTINATION_ID": ZFS0, "MCS_JOB_ID": JOB}),
        _host(D + "10:03:00.500", "MCSMHS_TRANSPORT_JOB_CHANGED_EVENT", {"CARRIER_ID": CAR, "DESTINATION_ID": ZFS, "MCS_JOB_ID": JOB}),
        _es(D + "10:03:00.600", "STORAGE-CARRIERTRANSFER", STK, dict(c, COMMANDID=JOB, SOURCEUNIT=STK + "M_IN03", DESTUNIT=STK + "A_OUT01"), send=True),
        _es(D + "10:03:00.601", "STORAGE-CARRIERTRANSFER", STK, dict(c, COMMANDID=JOB, SOURCEUNIT=STK + "M_IN03", DESTUNIT=STK + "A_OUT01"), send=True),
        _es(D + "10:03:30.000", "STORAGE-TRANSFERINITIATED", STK, dict(c, CARRIERLOC=STK + "M_IN03")),
        _host(D + "10:03:30.100", "MCSMHS_TRANSPORT_JOB_STARTED_EVENT", {"CARRIER_ID": CAR, "DESTINATION_ID": ZFS, "MCS_JOB_ID": JOB}),
        _es(D + "10:03:40.000", "STORAGE-CARRIERTRANSFERRING", STK, dict(c, CARRIERLOC=STK + "RM")),
        _es(D + "10:03:50.000", "STORAGE-CARRIERWAITOUT", STK, dict(c, CARRIERLOC=STK + "A_OUT01_OP")),
        _es(D + "10:04:00.000", "STORAGE-CARRIERWAITOUT", STK, dict(c, CARRIERLOC=STK + "A_OUT01")),
        _es(D + "10:04:00.100", "RAIL-CARRIERTRANSFER", OHT, dict(c, COMMANDID=JOB, SOURCEUNIT=STK + "A_OUT01", DESTUNIT=SHELF), send=True),
        _ui(D + "10:04:20.000", STK, STK + "A_OUT01", "MOVING"),
        _es(D + "10:04:30.000", "RAIL-VEHICLEACQUIRESTARTED", OHT, dict(c, VEHICLEID=VEH, TRANSFERPORT=STK + "A_OUT01")),
        _es(D + "10:04:36.000", "RAIL-CARRIERINSTALLED", OHT, dict(c, VEHICLEID=VEH, CARRIERLOC=VEH)),
        _es(D + "10:04:36.010", "RAIL-VEHICLEACQUIRECOMPLETED", OHT, dict(c, VEHICLEID=VEH, TRANSFERPORT=STK + "A_OUT01")),
        _ui(D + "10:04:36.020", STK, STK + "A_OUT01", "MOVING"),
        _ui(D + "10:04:36.030", OHT, VEH, "TRANSFERRING"),
        _es(D + "10:06:36.000", "RAIL-VEHICLEDEPOSITSTARTED", OHT, dict(c, VEHICLEID=VEH, TRANSFERPORT=SHELF)),
        _es(D + "10:06:44.000", "RAIL-CARRIERREMOVED", OHT, dict(c, VEHICLEID=VEH, CARRIERLOC=SHELF)),
        _ui(D + "10:06:44.050", ZFS, SHELF, "COMPLETED"),
        _host(D + "10:06:44.100", "MCSMHS_TRANSPORT_JOB_COMPLETED_EVENT", {"CARRIER_ID": CAR, "LOCATION_ID": ZFS, "MCS_JOB_ID": JOB}),
    ]


def _before(rows, hhmmss):
    return [r for r in rows if r["TIME_EX"] < "[%s%s" % (D, hhmmss)]


class 읽기(unittest.TestCase):
    def test_노트북_표(self):
        rows = fake_log()
        head = list(rows[0])
        table = "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
            "".join("<th>%s</th>" % h for h in head),
            "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % MP.html.escape(r[h]) for h in head) for r in rows))
        nb = json.dumps({"cells": [{"cell_type": "code", "source": ["x = 1\n", table], "outputs": []}]})
        got = MP.rows_from_text(nb)
        self.assertEqual(len(got), len(rows))
        self.assertEqual(got[1]["MESSAGENAME"], "STORAGE-CARRIERIDREAD")
        self.assertIn("< CARRIERLOC >", got[1]["TEXT"])

    def test_원본_로그_줄만_있어도(self):
        text = "\n".join(r["TEXT"] for r in fake_log())
        t = MP.trace(MP.rows_from_text(text))
        self.assertEqual(t["carrier"], CAR)
        self.assertEqual([L["type"] for L in t["legs"]], ["eqp", "stocker", "oht", "zfs"])

    def test_CSV(self):
        rows = fake_log()
        import csv
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        self.assertEqual(len(MP.rows_from_text(buf.getvalue())), len(rows))


class 경로(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = MP.trace(fake_log())

    def test_장비_순서와_자리(self):
        t = self.t
        self.assertEqual([(L["type"], L["machine"]) for L in t["legs"]],
                         [("eqp", EQP), ("stocker", STK), ("oht", OHT), ("zfs", ZFS)])
        self.assertEqual([(s["role"], s["short"]) for s in t["stays"]],
                         [("포트", "2"), ("입고 포트", "M_IN03"), ("크레인", "RM"), ("출고 포트", "A_OUT01"),
                          ("차량", VEH), ("선반", SHELF)])

    def test_걸린_시간(self):
        s = self.t["stays"]
        self.assertEqual(MP.dur(s[1]["dwell"]), "1분 40초")        # 10:02:00 → 10:03:40 (크레인에 오를 때까지)
        self.assertEqual(MP.dur(s[3]["dwell"]), "46초")            # 출고 포트 OP · LP 는 한 포트 (10:03:50 → 10:04:36)
        self.assertEqual(MP.dur(s[4]["drive"]), "2분")             # 집기 끝 → 내려놓기 시작
        self.assertEqual([lk["kind"] for lk in self.t["links"]], ["gap", "acquire", "deposit"])
        self.assertEqual(self.t["links"][0]["l2"], "2분")           # 설비에서 본 뒤 스토커까지 기록 없음

    def test_기록이_끊긴_시간은_머문_시간이_아니다(self):
        s0 = self.t["stays"][0]
        self.assertTrue(s0["gap_after"])
        self.assertEqual(s0["dwell"], 0)
        self.assertIn("에 보임", MP.facts_text(self.t))

    def test_완료_요약(self):
        t = self.t
        self.assertEqual(t["status"]["code"], "done")
        f = MP.facts_text(t)
        self.assertIn("지금: 반송 완료 — ZFS %s 선반 %s" % (ZFS, SHELF), f)
        self.assertIn("목적지 변경: %s → %s" % (ZFS0, ZFS), f)
        self.assertIn("설비 %s 상태 DOWN" % EQP, f)
        self.assertIn("반송 작업 없이 들어옴", f)
        self.assertEqual(t["fab"], {"fab": "M99", "floor": "2F"})
        self.assertIsNone(t["heading"])


class 지금_상태(unittest.TestCase):
    def test_OHT_에_실려_가는_중(self):
        t = MP.trace(_before(fake_log(), "10:05:00"), now=datetime(2026, 1, 2, 10, 5, 36))
        self.assertEqual(t["status"]["code"], "moving")
        self.assertEqual(t["heading"]["machine"], ZFS)
        self.assertEqual(t["heading"]["unit"], SHELF)
        f = MP.facts_text(t)
        self.assertIn("실린 지 1분", f)                          # 10:04:36 → 조회 10:05:36
        self.assertIn("가는 곳: ZFS %s 선반 %s" % (ZFS, SHELF), f)
        sc = MP._scene(t)
        tr = sc["trans"][-1]
        self.assertTrue(tr["ongoing"])
        self.assertIsNotNone(sc["oht"]) and self.assertTrue(sc["oht"]["carry"])

    def test_스토커에서_기다리는_중(self):
        t = MP.trace(_before(fake_log(), "10:03:20"), now=datetime(2026, 1, 2, 10, 3, 20))
        self.assertEqual(t["status"]["code"], "waiting")
        self.assertIn("여기서 1분 20초째", t["status"]["detail"])
        sc = MP._scene(t)
        plan = sc["trans"][-1]
        self.assertEqual(plan["kind"], "plan")
        self.assertTrue(plan.get("pre"))                          # 크레인 → 출고 포트를 거쳐서 간다


class 그림(unittest.TestCase):
    def test_SVG_와_움직임(self):
        t = MP.trace(fake_log())
        html_ = MP.render_html(t)
        svg = re.search(r"<svg .*?</svg>", html_, re.S).group(0)
        root = ET.fromstring(svg)
        self.assertTrue(root.get("id").startswith("mp"))
        for must in (CAR, "OHT " + VEH, "✓ 도착", "위치 기록 없음", "M99 FAB · 2F"):
            self.assertIn(must, svg)
        self.assertNotIn("None", svg)
        anim = json.loads(re.search(r'<script type="application/json" id="anim">(.*?)</script>', html_, re.S).group(1))
        times = [k[0] for k in anim["fk"]]
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(anim["steps"]), len(t["stays"]))
        self.assertTrue(any(k[1] is None for k in anim["ok"]))     # 내려놓고 떠난 OHT 는 사라진다

    def test_캐리어가_여럿이면_고른다(self):
        rows = fake_log()
        other = dict(rows[1], CARRIER="TEST0002", TEXT=rows[1]["TEXT"].replace(CAR, "TEST0002"))
        rows.append(other)
        self.assertEqual(MP.trace(rows)["carrier"], CAR)
        self.assertEqual(MP.trace(rows, "test0002")["carrier"], "TEST0002")
        with self.assertRaises(ValueError) as cm:
            MP.trace(rows, "NOPE")
        self.assertIn(CAR, str(cm.exception))

    def test_명령줄(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "log.txt")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("\n".join(r["TEXT"] for r in fake_log()))
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(MP._main([src]), 0)
        base = os.path.join(d, "캐리어_%s_경로" % CAR)
        for ext in (".html", ".svg", ".txt"):
            self.assertTrue(os.path.exists(base + ext), ext)
        ET.parse(base + ".svg")


if __name__ == "__main__":
    unittest.main()
