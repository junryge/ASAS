"""OHT_MAP — 실시간 · 과거 표의 '실제지표' 옆 HID_JAM · RET(레포트) 두 칸.

고객 요청 (2026-10-06)
    주피터 …/m16a_hubroom_event_prediction/oht_map/OHT_MAP_{day}.csv 를 가져와
    · HID_JAM      ← HID_ZONE
    · RET(레포트)  ← FILE_PATH 의 PROBLEM_MAP html — '링크' 를 누르면 내려받는다
    · 주피터 비밀번호는 기존(발동이벤트)과 같다 — 그대로 쓴다

가짜 주피터 서버(진짜와 같은 로그인 흐름)로 끝단까지 확인한다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from copy import deepcopy

from . import util  # noqa: F401
import jupyter_csv
import oht_map as OM
from lp_client import load_config

MOCK = os.path.join(util.BASE, "tests", "mock_jupyter.py")
PORT = 9917
PW = "테스트비번!1"
DAY = "20261003"
NAME = f"PROBLEM_MAP_M16HUB_{DAY}_2014_WARNING.html"


def _read(*p):
    with open(os.path.join(util.BASE, *p), encoding="utf-8") as f:
        return f.read()


def _up(port, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/login", timeout=1).read()
            return True
        except Exception:
            time.sleep(0.15)
    return False


class 읽기(unittest.TestCase):
    """CSV 원문 → 줄. 받은 머리줄 그대로 (날짜,시간,FAB,ALARM_KR,…,FILE_NAME,FILE_PATH)."""

    RAW = ("날짜,시간,FAB,ALARM_KR,ALARM_EN,HID_ZONE,HID_section,OHT_report,OHT_missing,OHT_JAM,"
           "ZONE_STOP,FILE_NAME,FILE_PATH\n"
           "2026-10-03,20:14,M16HUB,경계,WARNING,1,B01,259,11,8,10,"
           "PROBLEM_MAP_M16HUB_20261003_2014_WARNING.html,"
           "/project/pjt_shared_pool/job/vhl_ohl/HID_BOTTLENECK/PROBLEM_MAP/M16HUB_20261003/"
           "PROBLEM_MAP_M16HUB_20261003_2014_WARNING.html\n"
           "2026-10-03,9:05,m16a,위험,DANGER,3,A07,1,2,3,4,,\n"
           "날짜없음,20:16,M16HUB,,,,,,,,,,\n").encode("utf-8-sig")

    def test_받은_한_줄_그대로(self):
        r = OM.parse(self.RAW)[0]
        self.assertEqual((r["d"], r["t"], r["f"], r["lv"], r["en"]), (DAY, "20:14", "M16HUB", "경계", "WARNING"))
        self.assertEqual((r["z"], r["s"], r["rep"], r["miss"], r["jam"], r["stop"]),
                         ("1", "B01", "259", "11", "8", "10"))
        self.assertEqual(r["file"], NAME)

    def test_시각_FAB_을_맞추고_못_읽는_줄은_버린다(self):
        rows = OM.parse(self.RAW)
        self.assertEqual(len(rows), 2, "날짜를 못 읽는 줄은 버린다")
        self.assertEqual((rows[1]["t"], rows[1]["f"]), ("09:05", "M16A"), "표의 'HH:MM' · FAB 이름과 같은 모양")

    def test_레포트_경로(self):
        """FILE_PATH 의 /project/ 는 주피터 /files/ 아래다 (CSV 주소가 /files/pjt_shared_pool/… 인 것과 같다)."""
        p = OM.parse(self.RAW)[0]["path"]
        self.assertEqual(OM.jupyter_path(p),
                         "/files/pjt_shared_pool/job/vhl_ohl/HID_BOTTLENECK/PROBLEM_MAP/"
                         f"M16HUB_{DAY}/{NAME}")
        with self.assertRaises(ValueError):
            OM.jupyter_path("/project/a/../../etc/passwd")

    def test_기본_위치는_받은_주소(self):
        self.assertEqual(OM.DEFAULTS["path"],
                         "/files/pjt_shared_pool/job/m16a_hubroom_event_prediction/oht_map/OHT_MAP_{day}.csv")


class 주피터에서(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, MOCK_PW=PW)
        cls.srv = subprocess.Popen([sys.executable, MOCK, str(PORT)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if not _up(PORT):
            cls.srv.terminate()
            raise unittest.SkipTest("가짜 주피터 서버가 안 뜸")

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait(timeout=5)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rtom")
        # ★load_config() 는 캐시된 같은 dict 다 — 복사해서 쓴다 (다른 시험을 오염시키지 않게)
        self.cfg = deepcopy(load_config())
        # 발동이벤트와 **같은 주피터 설정** 하나뿐이다 — OHT_MAP 용 비밀번호 칸은 따로 없다
        self.cfg["source"] = {"mode": "jupyter", "jupyter": {
            "enabled": True, "base_url": f"http://127.0.0.1:{PORT}",
            "path": "/files/x/{day}_발동이벤트.csv", "password": PW}}
        self.cfg.setdefault("storage", {})["daily_csv_dir"] = self.tmp
        with OM._LOCK:
            OM._DAY.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        with OM._LOCK:
            OM._DAY.clear()

    def _hits(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/mock/hits", timeout=3) as r:
            return json.loads(r.read())["om"]

    def test_기존_주피터_비밀번호로_받는다(self):
        r = OM.refresh(DAY, self.cfg)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["rows"], 3)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "oht_map", f"OHT_MAP_{DAY}.csv")),
                        "받은 원본을 data/oht_map/ 에 둔다 (다시 켜도 지난 날은 다시 안 받게)")

    def test_비밀번호가_틀리면_알린다(self):
        bad = deepcopy(self.cfg)
        bad["source"]["jupyter"]["password"] = "틀림"
        r = OM.refresh(DAY, bad)
        self.assertFalse(r["ok"])
        self.assertIn("비밀번호", r["error"])

    def test_분마다_FAB_마다(self):
        OM.refresh(DAY, self.cfg)
        allv = OM.by_time(DAY, "ALL")
        self.assertEqual([h["f"] for h in allv["20:14"]], ["M16HUB", "M16A"])
        self.assertEqual(allv["20:14"][0]["z"], "1", "HID_JAM 칸 ← HID_ZONE")
        self.assertEqual(list(OM.by_time(DAY, "M16HUB")), ["20:14", "20:15"], "FAB 화면은 그 FAB 것만")
        self.assertEqual([h["f"] for h in OM.by_time(DAY, "m16hub")["20:14"]], ["M16HUB"])
        self.assertEqual(OM.by_time(DAY, "M14"), {})

    def test_서버_경로는_화면에_안_보낸다(self):
        OM.refresh(DAY, self.cfg)
        h = OM.by_time(DAY, "ALL")["20:14"][0]
        self.assertNotIn("path", h)
        self.assertEqual(set(h), set(OM.PUBLIC))

    def test_레포트는_누를_때마다_새로_받는다(self):
        """레포트가 다시 만들어질 수 있다 — 보관본을 주지 않고 주피터에서 새로 받는다."""
        raw, err = OM.report(DAY, NAME, self.cfg)
        self.assertEqual(err, "")
        self.assertIn(NAME.encode(), raw)
        n = self._hits().count(NAME)
        raw2, err2 = OM.report(DAY, NAME, self.cfg)
        self.assertEqual((raw2, err2), (raw, ""))
        self.assertEqual(self._hits().count(NAME), n + 1)

    def test_CSV_에_없는_레포트는_안_준다(self):
        """화면이 준 이름으로 주피터에서 아무 파일이나 끌어오면 안 된다."""
        for bad in ("PROBLEM_MAP_M16HUB_20261003_9999_WARNING.html", "../config.json",
                    "a/b.html", "x.py"):
            raw, err = OM.report(DAY, bad, self.cfg)
            self.assertIsNone(raw, bad)
            self.assertTrue(err, bad)
        self.assertNotIn("PROBLEM_MAP_M16HUB_20261003_9999_WARNING.html", self._hits())

    def test_발동이벤트_이어받기는_안_건드린다(self):
        """★jupyter_csv 의 이어받기(Range) 캐시에 OHT_MAP 을 덮어쓰면 다음 발동이벤트
        수집이 통째로 다시 받는다 — 그래서 따로 받는다."""
        with jupyter_csv._BODY_LOCK:
            before = dict(jupyter_csv._BODY)
        OM.refresh(DAY, self.cfg)
        OM.report(DAY, NAME, self.cfg)
        with jupyter_csv._BODY_LOCK:
            self.assertEqual(jupyter_csv._BODY, before)

    def test_지난_날은_그_자리에서_오늘은_뒤에서(self):
        OM.ensure(DAY, self.cfg)                              # 지난 날 — 기다려 받는다
        self.assertTrue(OM.sig(DAY))
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        OM.ensure(today, self.cfg)                            # 오늘 — 바로 돌아오고 뒤에서 받는다
        for _ in range(100):
            if OM.sig(today):
                break
            time.sleep(0.05)
        self.assertTrue(OM.sig(today))

    def _bump(self, path):
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/mock/{path}", timeout=3).read()

    def test_지난_날은_바뀌면_그_날짜를_다시_등록한다(self):
        """고객: "과거 데이터는 데이터가 달라지면 재등록 — 해당 날짜에"."""
        self.cfg["source"]["oht_map"] = {"recheck_s": 0}
        try:
            OM.ensure(DAY, self.cfg)
            self.assertNotIn("20:16", OM.by_time(DAY, "ALL"))
            s0 = OM.sig(DAY)
            self._bump("om_bump")                          # 잡이 그 날 파일을 다시 썼다
            OM.ensure(DAY, self.cfg)                       # 그 날짜를 다시 본다
            self.assertNotEqual(OM.sig(DAY), s0)
            self.assertEqual(OM.by_time(DAY, "ALL")["20:16"][0]["z"], "4")
            with open(os.path.join(self.tmp, "oht_map", f"OHT_MAP_{DAY}.csv"), encoding="utf-8") as f:
                self.assertIn("20:16", f.read(), "보관본도 바뀐 것으로")
        finally:
            self._bump("reset")

    def test_10초_안에_또_보면_다시_안_받는다(self):
        OM.ensure(DAY, self.cfg)
        n = self._hits().count(f"OHT_MAP_{DAY}.csv")
        OM.ensure(DAY, self.cfg)
        self.assertEqual(self._hits().count(f"OHT_MAP_{DAY}.csv"), n)

    def test_주피터에_못_닿으면_보관본으로(self):
        OM.ensure(DAY, self.cfg)
        with OM._LOCK:
            OM._DAY.clear()                                   # 서버를 다시 켠 것과 같다
        down = deepcopy(self.cfg)
        down["source"]["jupyter"]["base_url"] = "http://127.0.0.1:9"     # 아무도 안 받는 자리
        OM.ensure(DAY, down)
        self.assertIn("20:14", OM.by_time(DAY, "ALL"), "보관본(data/oht_map)으로 보인다")


class 서버_연결(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")

    def test_feed_가_분마다_hid_를_싣는다(self):
        self.assertIn("oht_map.ensure(shown_day, CFG)", self.s)
        self.assertIn('_hid = oht_map.by_time(shown_day, C["sys"]) if _om_sig else {}', self.s)
        self.assertIn('out[-1]["hid"] = _h', self.s)

    def test_새로_받으면_응답_캐시를_다시_만든다(self):
        m = re.search(r"_sig = \(_st\.st_mtime_ns.*?files_sig\([^\n]*\)\)", self.s, re.S)
        self.assertIsNotNone(m, "/api/feed 의 캐시 키를 못 찾았다")
        self.assertIn("_om_sig,", m.group(0))

    def test_레포트_내려받기(self):
        i = self.s.index('@app.route("/api/oht_map/report")')
        body = self.s[i:i + 1500]
        self.assertIn("oht_map.report(day, name, CFG)", body)
        self.assertIn("attachment;", body, "누르면 열리지 않고 내려받아진다")


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_두_표_모두_실제지표_바로_뒤에(self):
        heads = re.findall(r'<th class="mcol"[^>]*>실제지표</th>\s*<th class="hjcol"[^>]*>HID_JAM</th>\s*'
                           r'<th class="rtcol"[^>]*>RET\(레포트\)</th>\s*<th class="amhd"', self.h)
        self.assertEqual(len(heads), 2, "실시간 · 과거 두 표")

    def test_행도_같은_자리(self):
        self.assertIn("<td>${metricCell(r.metrics)}</td>\n      ${hidCell(r)}${retCell(r)}", self.h)
        self.assertIn("const ncol = 10 + (FABS.length ? fabCols().length + 1 : 0);", self.h)

    def test_내보내기도_같은_순서(self):
        self.assertIn("'실제지표', 'HID_JAM', 'RET(레포트)',", self.h)

    def test_그래프_창_OHT_재생_줄에도(self):
        """고객: "더블 클릭하면 그래프 나오는 거기서 HID_JAM, RET(레포트) — OHT 맵 클릭하는 데"."""
        self.assertIn('<span class="ohtbtns" id="ohtbtns"></span>\n      <span class="note" id="ohthid"></span>',
                      self.h, "FAB 단추 바로 옆")
        i = self.h.index("async function openGraph(at){")
        self.assertIn("fillHid(r);", self.h[i:i + 900])
        self.assertIn("bar.classList.toggle('hidden', !$('#ohthid').innerHTML)", self.h,
                      "월드모델 연결이 꺼져 있어도 HID 가 있으면 줄은 보인다")
        self.assertIn("if(!d.enabled){ note.textContent = '';", self.h,
                      "꺼져 있으면 '불러오는 중…' 이 HID 옆에 남는다")
        node = shutil.which("node")
        if not node:
            return
        k = self.h.index("const esc = ")
        js = (self.h[k:self.h.index("\n", k) + 1]
              + self.h[self.h.index("function retHref(h)"):self.h.index("function retCell(r)")]
              + self.h[self.h.index("function fillHid(r){"):self.h.index("async function openGraph(at){")]
              + """
const el = {innerHTML: ''}; const $ = () => el;
const out = [];
fillHid({hid: [{d:'20261003', f:'M16HUB', z:'1', file:'PROBLEM_MAP_M16HUB_20261003_2014_WARNING.html'}]}); out.push(el.innerHTML);
fillHid({hid: [{d:'20261003', f:'M16HUB', z:'2', file:''}]}); out.push(el.innerHTML);
fillHid({}); out.push(el.innerHTML);
console.log(JSON.stringify(out));
""")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b, c = json.loads(r.stdout)
        # ★고객: "1 은 빨간색 굵게, 링크 빨간색 굵게" — 이름은 굵게(본문 글자색)
        red = 'style="color:var(--crit);font-weight:700"'
        self.assertIn(f'<b style="color:var(--tx)">HID_JAM</b> <b class="mono" {red}>1</b>', a)
        self.assertIn(f'<b style="color:var(--tx)">RET(레포트)</b> <a class="act" {red} '
                      'href="/api/oht_map/report?day=20261003&name=', a)
        self.assertIn(">링크</a>", a)
        self.assertEqual(b, f'<b style="color:var(--tx)">HID_JAM</b> <b class="mono" {red}>2</b>',
                         "레포트가 없으면 RET 은 안 쓴다")
        self.assertEqual(c, "", "없으면 아무것도 안 쓴다")

    def test_칸_그리기(self):
        """hidCell · retCell 을 node 로 실제로 돌린다 (node 없으면 건너뜀)."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node 가 없다")
        i, j = self.h.index("function hidTip(h)"), self.h.index("/* ── FAB 컬럼")
        k = self.h.index("const esc = ")
        esc = self.h[k:self.h.index("\n", k) + 1]
        js = esc + self.h[i:j] + """
const one = {hid: [{d:'20261003', t:'20:14', f:'M16HUB', lv:'경계', en:'WARNING', z:'1', s:'B01',
             rep:'259', miss:'11', jam:'8', stop:'10', file:'PROBLEM_MAP_M16HUB_20261003_2014_WARNING.html'}]};
const two = {hid: [one.hid[0], {d:'20261003', t:'20:14', f:'M16A', z:'3', file:''}]};
console.log(JSON.stringify({a: hidCell(one), b: retCell(one), c: hidCell(two), d: retCell(two),
                            e: hidCell({}), f: retCell({hid: [{f:'M16HUB', z:'2', file:''}]})}));
"""
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        self.assertIn(">1</div>", got["a"], "HID_JAM ← HID_ZONE")
        self.assertIn("HID_section B01", got["a"], "나머지 값은 말풍선에")
        self.assertIn('href="/api/oht_map/report?day=20261003&name=PROBLEM_MAP_M16HUB_20261003_2014_WARNING.html"',
                      got["b"])
        self.assertIn('class="act"', got["b"])
        self.assertIn(">링크</a>", got["b"])
        self.assertIn(">1</div>", got["c"])
        self.assertIn(">3</div>", got["c"])
        self.assertEqual(got["d"].count("링크"), 1, "레포트가 없는 줄은 링크가 없다")
        # ★고객: "데이터 없으면 아무것도 안 쓴다" — '–' 도 안 찍는다
        self.assertEqual(got["e"], "<td></td>")
        self.assertEqual(got["f"], "<td></td>", "레포트 파일이 없으면 빈 칸")

if __name__ == "__main__":
    unittest.main()
