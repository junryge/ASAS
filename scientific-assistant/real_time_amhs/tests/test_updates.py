"""업데이트 내역 — 'UI대쉬보드' 옆 탭 (날짜 · 버전 · 내용).

고객 요청 (2026-10-06)
    "UI대쉬보드 옆에 업데이트 내역 쓸 수 있게 해줘. 비밀번호는 숨김 활성화와 동일하게
     하고, 업데이트 내역 기록하고 저장하는 데 비밀번호 필요 — 날짜, 버전, 내용"

★비밀번호 글자는 이 파일에도 두지 않는다 (test_secrets). 진짜 해시 대신 시험용
  비밀번호의 해시로 바꿔 끼우고 돈다 — 진짜 해시는 '화면과 같은 값인가' 만 본다.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from . import util  # noqa: F401
import updates as U

PW = "dummy-pw-1"


def _read(*p):
    with open(os.path.join(util.BASE, *p), encoding="utf-8") as f:
        return f.read()


class 저장(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = {"storage": {"daily_csv_dir": self.tmp}}
        self._sha = U.PW_SHA
        U.PW_SHA = hashlib.sha256(PW.encode("utf-8")).hexdigest()

    def tearDown(self):
        U.PW_SHA = self._sha
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _add(self, **kw):
        b = {"date": "2026-10-06", "version": "v1.0", "content": "첫 줄", "pw": PW}
        b.update(kw)
        return U.add(b, self.cfg)

    def test_처음엔_비어_있다(self):
        self.assertEqual(U.load(self.cfg), ([], ""))

    def test_비밀번호가_맞아야_저장한다(self):
        out, code = self._add(pw="틀린거")
        self.assertEqual(code, 403)
        self.assertIn("비밀번호", out["error"])
        out, code = self._add(pw="")
        self.assertEqual(code, 403)
        out, code = self._add(pw=None)
        self.assertEqual(code, 403)
        self.assertFalse(os.path.exists(U.path(self.cfg)), "틀렸는데 파일이 생겼다")

    def test_해시를_보내면_안_된다(self):
        """화면 소스에 보이는 해시를 받아 주면 누구나 저장할 수 있다."""
        out, code = self._add(pw=U.PW_SHA)
        self.assertEqual(code, 403)

    def test_날짜_버전_내용이_다_있어야(self):
        for kw, word in ((dict(date="2026/10/06"), "날짜"), (dict(date=""), "날짜"),
                         (dict(version="  "), "버전"), (dict(content=""), "내용"),
                         (dict(version="v" * 41), "버전"), (dict(content="가" * 5001), "내용")):
            out, code = self._add(**kw)
            self.assertEqual(code, 400, kw)
            self.assertIn(word, out["error"], kw)
        self.assertFalse(os.path.exists(U.path(self.cfg)))

    def test_저장하면_파일에_남는다(self):
        out, code = self._add(content="한 줄\r\n두 줄  ")
        self.assertEqual(code, 200, out)
        e = out["item"]
        self.assertEqual((e["date"], e["version"], e["content"]), ("2026-10-06", "v1.0", "한 줄\n두 줄"))
        self.assertRegex(e["id"], r"^[0-9a-f]{12}$")
        self.assertRegex(e["saved"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
        self.assertNotIn("pw", e, "비밀번호를 같이 저장하면 안 된다")
        with open(U.path(self.cfg), encoding="utf-8") as f:
            disk = json.load(f)
        self.assertEqual(disk, [e])
        self.assertNotIn(PW, json.dumps(disk, ensure_ascii=False))
        self.assertFalse(os.path.exists(U.path(self.cfg) + ".part"), "임시 파일이 남았다")

    def test_최근_날짜가_위(self):
        self._add(date="2026-09-01", version="v0.9")
        self._add(date="2026-10-06", version="v1.1")
        self._add(date="2026-10-01", version="v1.0")
        items, err = U.load(self.cfg)
        self.assertEqual(err, "")
        self.assertEqual([x["version"] for x in items], ["v1.1", "v1.0", "v0.9"])

    def test_깨진_파일은_덮어쓰지_않는다(self):
        """빈 목록으로 보고 새로 쓰면 그동안 적은 내역이 통째로 사라진다."""
        p = U.path(self.cfg)
        with open(p, "w", encoding="utf-8") as f:
            f.write('[{"date": "2026-10-01", "version": "v1"')       # 반쯤 쓴 파일
        out, code = self._add()
        self.assertEqual(code, 500)
        self.assertIn("저장하지 않았습니다", out["error"])
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), '[{"date": "2026-10-01", "version": "v1"')
        items, err = U.load(self.cfg)
        self.assertEqual(items, [])
        self.assertIn("못 읽었습니다", err)

    def test_지우기도_비밀번호(self):
        a = self._add(version="v1")[0]["item"]
        b = self._add(version="v2")[0]["item"]
        out, code = U.delete({"delete": a["id"], "pw": "틀린거"}, self.cfg)
        self.assertEqual(code, 403)
        out, code = U.delete({"delete": "없는것", "pw": PW}, self.cfg)
        self.assertEqual(code, 404)
        out, code = U.delete({"delete": a["id"], "pw": PW}, self.cfg)
        self.assertEqual(code, 200, out)
        self.assertEqual([x["id"] for x in out["items"]], [b["id"]])
        self.assertEqual([x["id"] for x in U.load(self.cfg)[0]], [b["id"]])


class 비밀번호는_숨김_해제와_같다(unittest.TestCase):
    def test_화면의_해시와_같은_값(self):
        h = _read("static", "dashboard.html")
        m = re.search(r"const HIDE_PW_SHA = '([0-9a-f]{64})';", h)
        self.assertTrue(m, "화면에 HIDE_PW_SHA 가 없다")
        self.assertEqual(U.PW_SHA, m.group(1),
                         "숨김 해제 비밀번호를 바꿨으면 updates.py 의 PW_SHA 도 바꿔야 한다")

    def test_글자가_아니라_해시로_비교(self):
        src = _read("updates.py")
        self.assertIn("hmac.compare_digest(hashlib.sha256(", src)


class 서버에_붙어_있다(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = _read("server.py")

    def test_주소(self):
        i = self.s.index('@app.route("/api/updates", methods=["GET", "POST"])')
        body = self.s[i:self.s.index("\n\n\n", i)]
        self.assertIn("updates.delete(b, CFG) if b.get(\"delete\") else updates.add(b, CFG)", body)
        self.assertIn("updates.load(CFG)", body)
        self.assertIn("return jsonify(out), code", body, "403 · 400 을 그대로 돌려줘야 화면이 까닭을 안다")

    def test_버전_확인에도_나온다(self):
        self.assertIn('"업데이트내역탭": \'id="tab-updates"\' in body', self.s)
        self.assertIn('"API_updates"', self.s)


class 화면(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _read("static", "dashboard.html")

    def test_UI대쉬보드_바로_옆(self):
        self.assertIn('<button data-tab="ui">UI대쉬보드</button>\n'
                      '    <button data-tab="updates">업데이트 내역</button>', self.h)

    def test_숨김에도_보인다(self):
        """보는 것은 누구나 — 숨기는 탭(HIDE_TABS)에 넣지 않는다."""
        m = re.search(r"const HIDE_TABS = \[([^\]]*)\];", self.h)
        self.assertNotIn("updates", m.group(1))

    def test_날짜_버전_내용_비밀번호_칸(self):
        for need in ('<input type="date" id="upddate">', 'id="updver" maxlength="40"',
                     '<textarea id="updtext" rows="5" maxlength="5000"',
                     '<input type="password" id="updpw" autocomplete="off">',
                     '<button type="submit" class="act pri">저장</button>', 'id="updrows"'):
            self.assertIn(need, self.h)

    def test_탭을_열면_불러온다(self):
        self.assertIn("['live','past','ml','analysis','report','ui','policy','updates'].forEach", self.h)
        self.assertIn("}else if(b.dataset.tab==='updates'){\n    initUpdates();", self.h)

    def test_비밀번호는_글자로_보내고_저장_뒤_비운다(self):
        i = self.h.index("$('#updform').onsubmit = async e => {")
        body = self.h[i:self.h.index("\n};", i)]
        self.assertIn("content: $('#updtext').value, pw}", body)
        self.assertNotIn("sha256hex", body, "해시를 보내면 소스를 연 누구나 저장할 수 있다")
        self.assertIn("$('#updpw').value = '';", body)

    def test_목록_그리기(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node 가 없다")
        k = self.h.index("const esc = ")
        js = (self.h[k:self.h.index("\n", k) + 1]
              + self.h[self.h.index("function updRows(items){"):self.h.index("function updShow(")]
              + """
console.log(JSON.stringify({
  a: updRows([{id:'abc123def456', date:'2026-10-06', version:'v1.4.0',
               content:'첫 줄\\n<script>x</script>', saved:'2026-10-06 09:00:00'}]),
  b: updRows([])}));
""")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        self.assertIn(">2026-10-06</td>", got["a"])
        self.assertIn("<b>v1.4.0</b>", got["a"])
        self.assertIn("white-space:pre-wrap", got["a"], "줄바꿈을 살린다")
        self.assertIn("&lt;script&gt;", got["a"])
        self.assertNotIn("<script>", got["a"])
        self.assertIn('data-upddel="abc123def456"', got["a"])
        self.assertIn("아직 적은 내역이 없습니다", got["b"])


if __name__ == "__main__":
    unittest.main()
