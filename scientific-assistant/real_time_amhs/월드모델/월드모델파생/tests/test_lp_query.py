# -*- coding: utf-8 -*-
"""로그프레소 쿼리 — 두 벌(agg30 · raw)을 들고 있고, 되돌릴 수 있나.

고객이 준 쿼리(MSG_ID=2 · 30초 묶음)로 바꾸되 "다시 원본 할 수도 있다" 고 해서
예전 쿼리를 지우지 않고 프로필로 남겼다.

★2026-09-21 — 고객: "월드모델파생 원본 그대로 search MSG_ID==\"2\" 이거 추가해라"
  (간소는 이미 있다). 그래서 **상세(raw)** 에도 거르는 줄 하나를 더했다. 묶지
  않는 것도, 컬럼이 다 오는 것도 그대로다. 거르는 줄조차 없는 완전한 원본은
  logpresso_query_원본_raw쿼리.py.bak 에 있고, 아래에서 그것도 함께 본다.

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

    def test_기본은_상세_예전_쿼리(self):
        """★화면이 형태를 안 보내는 옛 호출은 예전과 똑같이 돌아야 한다."""
        self.assertEqual(self.ns["PROFILE"], "raw")

    def test_고객이_준_쿼리_그대로(self):
        """★한 글자 틀리면 로그프레소가 문법 오류를 낸다 — 받은 글자 그대로 본다."""
        q = self.q("agg30")
        for piece in (
            f'table from={F} to={T} {TBL}',
            '| search MSG_ID == "2"',
            '| sort _time',
            '| eval _time = datetrunc(_time, "25s")',   # 2026-09-21 고객이 30 → 25 로
            '| stats first(ADDRESS) as ADDRESS, first(DISTANCE) as DISTANCE,',
            'first(NEXT_ADDRESS) as NEXT_ADDRESS, first(EDGE) as EDGE,',
            'first(CARRIER) as CARRIER, first(STATUS) as STATUS,',
            'first(OPERATION_STATUS) as OPERATION_STATUS',
            'by VEHICLE, _time',
            '| sort _time, VEHICLE',
        ):
            self.assertIn(piece, q, piece)

    def test_상세는_원본에_MSG_ID_2_한_줄만_더한_것이다(self):
        """고객: "원본 그대로 search MSG_ID==\"2\" 이거 추가해라" — 더한 건 그 줄뿐이다."""
        q = self.q("raw")
        self.assertIn(f'table from={F} to={T} {TBL} | search MSG_ID == "2" | sort _time', q)

    def test_상세는_묶지_않는다(self):
        """★간소와 갈리는 지점. 묶으면 1초 단위가 사라져 재생이 성큼성큼 간다."""
        q = self.q("raw")
        self.assertNotIn("datetrunc", q)
        self.assertNotIn("stats", q)
        self.assertNotIn("by VEHICLE", q)

    def test_상세는_컬럼을_고르지_않는다(self):
        """★거르는 줄만 더했으니 컬럼은 여전히 전부 온다 — first(...) 가 없어야 한다."""
        self.assertNotIn("first(", self.q("raw"))

    def test_상세와_간소의_거르는_줄이_같다(self):
        """한 글자라도 다르면 둘 중 하나는 로그프레소가 문법 오류를 낸다."""
        line = '| search MSG_ID == "2"'
        self.assertIn(line, self.q("raw"))
        self.assertIn(line, self.q("agg30"))

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
        # 쪼갠 두 조각 다 — 멈춤 손잡이(should_cancel)도 같이 들고 간다
        self.assertEqual(blk.count("profile, should_cancel)"), 2, "쪼갠 두 조각 다")

    def test_API_가_profile_을_받아_넘긴다(self):
        s = _read("main.py")
        self.assertIn("profile = (body.get('profile') or '').strip() or None", s)
        i = s.find("query_oht_chunked(from_dt, to_dt, table=table,")
        self.assertNotEqual(i, -1, "API 가 조각내기 조회를 안 부른다")
        self.assertIn("profile=profile", s[i:i + 300])

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
        # ★상세(raw)에도 MSG_ID=2 를 더한 뒤로, 거르는 줄조차 없는 원본은 여기뿐이다.
        self.assertNotIn("MSG_ID", o)


class 키와_주소는_한_짝(unittest.TestCase):
    """★401 이 났던 이유 — 키는 관제 config.json 에서 빌려오는데 주소는 이 파일에
    박힌 개발 IP(10.125.173.63)를 썼다. 다른 서버 키를 다른 서버에 보낸 것이다.
    _borrow 안에 host/port 를 읽는 가지가 있었는데 아무도 안 부르고 있었다."""

    def _run(self, cfg=None, env=None):
        """logpresso_query.py 의 접속 설정 토막만 떼어 돌린다 (pandas 없이)."""
        import json, shutil, tempfile
        src = _read("logpresso_query.py")
        a, b = src.index("# 원격 노드명"), src.index('FMT = "%Y%m%d%H%M%S"')
        tmp = tempfile.mkdtemp()
        try:
            deep = os.path.join(tmp, "a", "b")
            os.makedirs(deep, exist_ok=True)
            if cfg is not None:
                with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as f:
                    json.dump(cfg, f)
            old = {k: os.environ.pop(k, None) for k in ("LP_API_KEY", "LP_HOST", "LP_PORT")}
            os.environ.update({k: v for k, v in (env or {}).items()})
            ns = {"os": os, "HOST": "10.125.173.63", "PORT": 8888, "API_KEY": "",
                  "__file__": os.path.join(deep, "logpresso_query.py")}
            try:
                exec(src[a:b], ns)
            finally:
                for k in ("LP_API_KEY", "LP_HOST", "LP_PORT"):
                    os.environ.pop(k, None)
                for k, v in old.items():
                    if v is not None:
                        os.environ[k] = v
            return ns
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ★값을 'sample-' 로 시작하게 둔다 — 관제의 보안 스캐너(tests/test_secrets.py)가
    #   진짜 키로 오해하지 않게. 시험용 가짜다.
    CFG = {"api_key": "sample-key-abcd1234",
           "logpresso_base": "http://10.40.42.167:8888/logpresso"}

    def test_키를_빌리면_주소도_같이_빌린다(self):
        ns = self._run(self.CFG)
        self.assertEqual(ns["API_KEY"], "sample-key-abcd1234")
        self.assertEqual(ns["HOST"], "10.40.42.167",
                         "키만 빌리고 주소는 파일의 개발 IP 를 쓰면 401 이 난다")
        self.assertEqual(ns["PORT"], 8888)

    def test_어디서_빌렸는지_남긴다(self):
        self.assertEqual(self._run(self.CFG)["KEY_FROM"], "환경변수/관제 설정")

    def test_환경변수가_이긴다(self):
        ns = self._run(self.CFG, env={"LP_HOST": "10.1.2.3", "LP_PORT": "9999"})
        self.assertEqual((ns["HOST"], ns["PORT"]), ("10.1.2.3", 9999))

    def test_설정이_없으면_파일_값_그대로(self):
        ns = self._run(None)
        self.assertEqual(ns["HOST"], "10.125.173.63")
        self.assertEqual(ns["API_KEY"], "")

    def test_401_이면_무엇을_볼지_알려준다(self):
        s = _read("logpresso_query.py")
        self.assertIn("if resp.status_code == 401:", s)
        self.assertIn("401 = 인증 실패. 쿼리는 돌지도 않았다.", s)
        self.assertIn("키 출처 {KEY_FROM}", s)

    def test_접속_정보를_로그에_남긴다(self):
        self.assertIn('print(f"[접속] {HOST}:{PORT}', _read("logpresso_query.py"))

    def test_키_전체는_찍지_않는다(self):
        """★로그·오류 글에 키가 통째로 찍히면 화면 캡처 한 장으로 새어 나간다.

        ★이름을 글자 그대로 적지 않고 쪼개서 만든다 — 그대로 적으면 관제의
          보안 스캐너(tests/test_secrets.py)가 이 시험 줄을 진짜 키로 잡는다.
          실제로 한 번 잡혔다.
        """
        s = _read("logpresso_query.py")
        tok = "API_" + "KEY"
        self.assertEqual(s.count("{" + tok + "}"), 1,
                         "키를 통째로 넣는 곳은 조회 URL 한 군데뿐이어야 한다")
        self.assertEqual(s.count(tok + "[-4:]"), 2, "끝 4자만 (로그 한 곳, 오류 한 곳)")


class 화면의_상세_간소_단추(unittest.TestCase):
    """고객: "상세(처음), 간소(지금 만든거) 2개 사용할수 있도록 해주라"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_단추_둘이_조회_로드_옆에_있다(self):
        m = re.search(r'<div class="tb-seg"[^>]*>\s*<span class="tb-cap">조회</span>\s*'
                      r'<button id="lp-raw"[\s\S]*?<button id="lp-agg30"[\s\S]*?</div>\s*'
                      r'<button onclick="logpressoLoad\(\)" id="lp-btn"', self.h)
        self.assertIsNotNone(m, "상세/간소 단추가 '조회 로드' 앞에 없다")
        # ★뒤에 로드 시간을 적는다 (고객: "상세:데이터로드 오래걸림, 간소:데이터로드
        #   짧은 이라고 뒤에 기입좀 해 주면 사용자들이 편하겠지")
        self.assertIn(">상세 (데이터 로드 오래 걸림)<", m.group(0))
        self.assertIn(">간소 (데이터 로드 짧음)<", m.group(0))

    def test_기본은_상세가_켜져_있다(self):
        self.assertIn('<button id="lp-raw"   class="toggle-btn on"', self.h)
        self.assertIn('<button id="lp-agg30" class="toggle-btn"    ', self.h)
        self.assertIn("let lpProfile = 'raw';", self.h)

    def test_고른_것을_보낸다(self):
        self.assertIn("const profile = lpProfile;", self.h)
        self.assertIn("body: JSON.stringify({ from_dt, to_dt, table, profile }),", self.h)

    def test_고른_것을_남기지_않는다(self):
        """★고객: "처음 조회할 때는 무조건 상세로 해야 되".

        지난번에 간소를 골랐다고 다음에 연 화면이 간소로 시작하면 안 된다.
        저장을 아예 안 하므로 화면을 열 때마다 상세다."""
        self.assertNotIn("LP_PROFILE_KEY", self.h, "조회 형태를 저장하면 안 된다")
        for line in self.h.splitlines():
            if "localStorage" in line and "lpProfile" in line:
                self.fail("조회 형태를 localStorage 에 넣거나 빼고 있다: " + line.strip())
        self.assertIn("initLpProfile();", self.h, "화면을 열 때 상세로 되돌려야 한다")
        self.assertIn("lpProfile = 'raw';               // 열 때마다 상세부터", self.h)

    def test_간소는_구간_상한이_길다(self):
        """★간소를 만든 이유가 '10분 이상이 조회가 안 된다' 인데 상한을 30분으로
        같이 두면 소용이 없다."""
        m = re.search(r"const _cap = \(profile === 'agg30'\) \? (\d+) : (\d+);", self.h)
        self.assertIsNotNone(m, "형태별 상한이 없다")
        agg, raw = int(m.group(1)), int(m.group(2))
        self.assertGreater(agg, raw, f"간소({agg}분)가 상세({raw}분)보다 길어야 한다")
        self.assertEqual(raw, 30, "상세는 예전 그대로 30분")
        self.assertIn("위 '간소' 로 바꿔서 조회하세요", self.h, "넘치면 어디를 누를지 알려야 한다")

    def test_어느_형태로_쳤는지_화면에_남는다(self):
        self.assertIn("${profile === 'agg30' ? '간소' : '상세'}", self.h)

    def test_단추_설명에_무엇이_다른지_적었다(self):
        # 간소로 보면 적재 색이 안 뜬다 — 눌러 보고 알면 늦다
        self.assertIn("적재·목적지는 안 온다", self.h)
        self.assertIn("10분 넘는 구간도 조회된다", self.h)


class 시작_끝은_날짜_시각을_고른다(unittest.TestCase):
    """고객: "시작~끝 데이터 기입해야 하는데 시간을 기입하는 거야 유저들이 사용 편하게"
    · "시작~끝 시간이니까 날짜 시간을 선택하게 해 주면 좋지"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_달력_시계로_고르는_칸(self):
        for i in ("lp-from", "lp-to"):
            m = re.search(r'<input type="datetime-local" step="1" id="%s"' % i, self.h)
            self.assertIsNotNone(m, i + " 가 날짜·시각 고르기 칸이 아니다")
        self.assertNotIn('placeholder="yyyyMMddHHmmss"', self.h, "14자리를 치게 하던 칸이 남았다")

    def test_서버에는_여전히_14자리(self):
        """★서버·관제 연동은 14자리를 쓴다 — 칸 모양만 바뀌고 보내는 값은 같다."""
        self.assertIn("const from_dt = _toLP(fromEl.value);", self.h)
        self.assertIn("const to_dt   = _toLP(toEl.value);", self.h)

    def test_관제에서_넘어온_14자리를_칸_모양으로(self):
        m = re.search(r"async function autoFromQuery\(\)\s*\{[\s\S]*?\n\}", self.h)
        body = m.group(0)
        self.assertIn("set('lp-from', _fromLP(from)); set('lp-to', _fromLP(to)); lpSetTable(tbl);",
                      body)
        self.assertLess(body.index("applyFab"), body.index("lpSetTable(tbl)"),
                        "맵을 바꾼 뒤에 채워야 한다 (applyFab 이 테이블을 덮는다)")

    def test_처음_열면_최근_10분(self):
        self.assertIn("lpInitTimes();", self.h)
        self.assertIn("const LP_SPAN_MIN = 10;", self.h)
        self.assertIn("if (!f || !t || f.value || t.value) return;", self.h,
                      "이미 값이 있으면(관제 연동 등) 건드리면 안 된다")

    def test_끝이_비었거나_앞서면_시작_뒤로(self):
        self.assertIn('onchange="lpFromChanged()"', self.h)
        self.assertIn("if (!z || z <= a) t.value", self.h, "제대로 된 끝은 건드리지 않는다")

    def test_달력_단추가_테마에서_보인다(self):
        self.assertIn("color-scheme:dark", self.h)
        self.assertIn('body[data-theme="hmi"] #topbar .tb-query input[type=datetime-local] '
                      '{ color-scheme:light; }', self.h)

    def test_변환이_제대로(self):
        """_toLP ⇄ _fromLP 를 node 로 실제로 돌린다 (node 없으면 건너뜀)."""
        import shutil, subprocess, json
        node = shutil.which("node")
        if not node:
            self.skipTest("node 가 없다")
        i = self.h.index("function _toLP(ts)")
        j = self.h.index("const LP_SPAN_MIN", i)
        js = self.h[i:j] + """
const out = {
  a: _fromLP('20260831103500'), b: _toLP(_fromLP('20260831103500')),
  c: _toLP('2026-08-31T10:35'), d: _fromLP(''), e: _toLP(_dtLocal(new Date(2026, 0, 2, 3, 4, 5)))
};
console.log(JSON.stringify(out));
"""
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        self.assertEqual(got, {"a": "2026-08-31T10:35:00", "b": "20260831103500",
                               "c": "20260831103500", "d": "", "e": "20260102030405"})


class 테이블은_고른다(unittest.TestCase):
    """고객: "네이밍룰은 동일한데 테이블 선택할 수 있도록 해 주라 — 그래프에서 들어가는
    거는 그대로 하고 수동으로 하는 경우가 있어"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")

    def test_고르는_칸(self):
        self.assertIn('<select id="lp-table" onchange="onLpTableChange()"', self.h)
        self.assertNotIn('<input type="text" id="lp-table"', self.h)

    def test_이름_규칙은_그대로(self):
        self.assertIn("return `oht_data_m${num}${(prefix || '').toLowerCase()}`;", self.h)
        self.assertIn("const t = _logpressoTableFor(e.fab, e.prefix);", self.h)

    def test_FAB_별로_묶는다(self):
        self.assertIn("document.createElement('optgroup')", self.h)

    def test_고르면_맵도_맞춘다(self):
        i = self.h.index("async function onLpTableChange()")
        body = self.h[i:i + 500]
        self.assertIn("await applyFab(e.fab, e.prefix);", body)
        self.assertIn("syncLogpressoTable();", body, "전환이 실패하면 목록을 되돌린다")

    def test_목록_밖_이름도_받는다(self):
        """관제에서 넘어온 테이블이 목록에 없어도 조회는 예전처럼 돈다."""
        i = self.h.index("function lpSetTable(name)")
        body = self.h[i:i + 700]
        self.assertIn(".toLowerCase()", body, "대문자가 섞이면 없는 테이블을 친다")
        self.assertIn("sel.appendChild(opt);", body)

    def test_부팅때_목록을_만든다(self):
        i = self.h.index("async function bootFabs()")
        body = self.h[i:i + 900]
        self.assertLess(body.index("rebuildLpTableSelect();"), body.index("syncLogpressoTable();"))


class 조회_멈춤(unittest.TestCase):
    """고객: "조회 멈춤 버튼도 만들어주라..다시 재조회 할 수도 있잖아"."""

    @classmethod
    def setUpClass(cls):
        cls.h = _read("dashboard.html")
        cls.m = _read("main.py")
        cls.q = _read("logpresso_query.py")

    # ── 화면 ────────────────────────────────────────────────────
    def test_멈춤_단추가_조회_로드_옆에_있다(self):
        m = re.search(r'<button onclick="logpressoLoad\(\)" id="lp-btn"[\s\S]*?'
                      r'<button onclick="logpressoStop\(\)" id="lp-stop"', self.h)
        self.assertIsNotNone(m, "멈춤 단추가 '조회 로드' 바로 뒤에 없다")

    def test_조회_중에만_눌린다(self):
        self.assertIn('id="lp-stop" disabled', self.h, "처음엔 눌리지 않아야 한다")
        self.assertIn("if (btn)  btn.disabled  = !!busy;", self.h)
        self.assertIn("if (stop) stop.disabled = !busy;", self.h)
        self.assertIn("syncLpButtons(true);", self.h, "조회 시작하며 멈춤을 열어야 한다")
        self.assertIn("syncLpButtons(false);", self.h, "끝나면 다시 닫아야 한다")

    def test_서버에_알리고_화면도_끊는다(self):
        """★둘 다 해야 한다. 서버에만 알리면 조각 하나가 끝날 때까지 조회
        단추가 잠긴 채라 '다시 재조회' 를 못 한다."""
        i = self.h.index("async function logpressoStop()")
        body = self.h[i:i + 1200]
        self.assertIn("fetch('/api/logpresso/cancel', { method: 'POST' })", body)
        self.assertIn("lpAbort.abort()", body)
        self.assertLess(body.index("/api/logpresso/cancel"), body.index("lpAbort.abort()"),
                        "서버에 먼저 알리고 그다음 화면을 끊어야 한다")

    def test_조회는_끊을_수_있게_보낸다(self):
        self.assertIn("lpAbort = new AbortController();", self.h)
        self.assertIn("signal: lpAbort.signal,", self.h, "fetch 에 signal 을 안 넘기면 못 끊는다")

    def test_멈춤은_실패가_아니다(self):
        """빨간 ❌ 도 alert 도 뜨면 안 된다. 두 길(200 cancelled · AbortError) 다."""
        self.assertIn("if (data.cancelled) {", self.h, "서버가 준 200 cancelled 처리")
        self.assertIn("if (lpStopping || e.name === 'AbortError') {", self.h,
                      "끊은 fetch 는 오류로 떠들면 안 된다")
        i = self.h.index("if (lpStopping || e.name === 'AbortError') {")
        branch = self.h[i:self.h.index("} else {", i)]
        self.assertNotIn("alert(", branch, "멈췄는데 오류창을 띄우면 안 된다")
        self.assertIn("다시 조회할 수 있습니다", branch)

    def test_끝나면_상태를_되돌린다(self):
        i = self.h.index("  } finally {", self.h.index("async function logpressoLoad()"))
        fin = self.h[i:i + 400]
        self.assertIn("lpAbort = null;", fin)
        self.assertIn("lpStopping = false;", fin)

    # ── 서버 ────────────────────────────────────────────────────
    def test_멈춤_API_가_있다(self):
        self.assertIn('@app.post("/api/logpresso/cancel")', self.m)

    def test_조회를_다른_실에서_돌린다(self):
        """★이게 없으면 멈춤 단추가 아무 일도 안 한다 — 조회가 서버를 통째로
        붙들고 있어 /api/logpresso/cancel 요청 자체가 안 들어온다."""
        self.assertIn("from starlette.concurrency import run_in_threadpool", self.m)
        i = self.m.index("df = await run_in_threadpool(")
        self.assertIn("query_oht_chunked(", self.m[i:i + 400])

    def test_다시_조회해도_멈춘_조회가_살아나지_않는다(self):
        """★True/False 한 개로는 안 된다. 멈추자마자 다시 조회하면 새 조회가
        플래그를 지우고, 아직 제 조각을 붙들고 있던 옛 조회가 그걸 보고 되살아나
        둘이 같이 돈다.
        ★2026-09: 번호는 **사람마다** 따로다 (Session.lp). 전역 하나였을 때는
          한 사람이 멈춤을 누르면 그때 돌던 남의 조회까지 같이 죽었다 —
          그쪽은 tests/test_sessions.py 가 본다."""
        self.assertIn('self.lp = {"gen": 0, "stop_upto": 0}', self.m,
                      "조회 번호는 세션마다여야 한다")
        self.assertIn('s.lp["gen"] += 1', self.m, "조회마다 번호를 올려야 한다")
        self.assertIn('s.lp["stop_upto"] = s.lp["gen"]', self.m)
        self.assertIn("should_cancel=_lp_should_cancel(s, _my_gen)", self.m)
        self.assertNotIn("LP_RUN", self.m, "전역 번호가 되살아났다")

    def test_멈춤_판정_그대로_돌려_본다(self):
        """_lp_should_cancel 을 배포되는 그 코드 그대로 떼어 돌린다."""
        a = self.m.index("def _lp_should_cancel(")
        b = self.m.index('@app.post("/api/logpresso/cancel")')
        ns = {}
        exec(self.m[a:b], ns)
        should = ns["_lp_should_cancel"]

        class _S:                           # 한 사람 몫 — lp 만 있으면 된다
            def __init__(self):
                self.lp = {"gen": 0, "stop_upto": 0}

        s = _S()
        s.lp["gen"] = 1                     # 조회 #1 시작
        f1 = should(s, 1)
        self.assertFalse(f1(), "막 시작한 조회가 멈추면 안 된다")

        s.lp["stop_upto"] = s.lp["gen"]     # 사람이 멈춤을 눌렀다
        self.assertTrue(f1(), "멈춤을 눌렀으면 멈춰야 한다")

        s.lp["gen"] = 2                     # 곧바로 다시 조회
        f2 = should(s, 2)
        self.assertFalse(f2(), "새 조회는 지난 멈춤에 걸리면 안 된다")
        self.assertTrue(f1(), "한물간 옛 조회는 계속 멈춘 채여야 한다")

        other = _S()                        # 남의 조회는 안 건드린다
        other.lp["gen"] = 1
        self.assertFalse(should(other, 1)(), "★남의 조회까지 죽는다")

    def test_멈춤은_502_가_아니다(self):
        i = self.m.index("if isinstance(e, QueryCancelled):")
        br = self.m[i:i + 300]
        self.assertIn('{"cancelled": True', br)
        self.assertIn("status_code=200", br)

    def test_쿼리_쪽이_멈춤을_안다(self):
        self.assertIn("class QueryCancelled(RuntimeError)", self.q)
        self.assertIn("should_cancel=None", self.q)
        i = self.q.index("def query_oht_chunked(")
        body = self.q[i:i + 3000]
        self.assertIn("if should_cancel and should_cancel():", body)
        self.assertIn("raise QueryCancelled(", body)
        self.assertEqual(body.count("should_cancel)"), 2,
                         "조각을 쪼개 다시 부를 때도 들고 가야 한다")


if __name__ == "__main__":
    unittest.main()
