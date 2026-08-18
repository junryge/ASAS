"""사건발생 보고서 인터랙티브 블록.

★규칙: 2번 AMOS 표가 비어도 3번 '실제 이상 발생내역' 의 수동 기입은
  **무조건** 있어야 한다. AMOS 가 못 잡은 이상을 사람이 적는 칸이라
  감지 결과에 종속되면 안 된다 (페르소나: "수동 기입은 항상 가능해야 한다").
  예전엔 AMOS 헤딩이 없으면 통째로 건너뛰어 3번이 사라졌다.

★규칙: real_time_amhs/amos_block.py 와 demos_v1/amos_report.py 는
  **같은 코드**여야 한다. 한쪽만 고치면 체크박스·O/X 규격이 갈라진다.
  실제로 갈라져서 같은 버그가 양쪽에 남아 있었다.
"""
import io
import os
import tokenize
import unittest

from . import util  # noqa: F401
from amos_block import amosify

H1 = "<h1>📅 2026년 8월 12일 M16 BR 반송 이벤트 발생 확인건</h1>"
AMOS_TABLE = """<table>
<thead><tr><th>번호</th><th>이상감지 시간</th><th>이상감지 구간</th><th>심각도</th>
<th>이상감지 항목</th><th>실제 발생여부</th></tr></thead>
<tbody>
<tr><td>1</td><td>00:15</td><td>HID35, HID30</td><td>경계/주의(확인필요)</td>
<td>M16A.QUE.LOAD.AVGLOADTIME1MIN</td><td></td></tr>
<tr><td>2</td><td>07:23</td><td>HID7</td><td>경계/주의(확인필요)</td>
<td>M16HUB.QUE.LFT.3F_LFT_REVERSALCNT</td><td></td></tr>
</tbody></table>"""

FULL = (H1 + "<h2>1. 한 줄 총평</h2><p>총 2건.</p>"
        "<h2>2. AMOS 이상 감지 내역</h2>" + AMOS_TABLE +
        "<h2>3. 실제 이상 발생내역</h2><p>2번 표의 실제 발생여부를 체크하면…</p>"
        "<h2>4. 위험 이벤트 상세 분석</h2><p>…</p><h2>5. 에이전트 제안</h2><p>…</p>")
EMPTY2 = (H1 + "<h2>1. 한 줄 총평</h2><p>사건 없음.</p>"
          "<h2>2. AMOS 이상 감지 내역</h2><p>금일 AMOS 이상감지 내역 없음</p>"
          "<h2>3. 실제 이상 발생내역</h2><p>안내</p>"
          "<h2>4. 위험 이벤트 상세 분석</h2><p>해당 없음</p>")
NO_AMOS = (H1 + "<h2>1. 한 줄 총평</h2><p>사건 없음.</p>"
           "<h2>4. 위험 이벤트 상세 분석</h2><p>해당 없음</p>")
ONLY_TITLE = H1 + "<h2>1. 한 줄 총평</h2><p>사건 없음.</p>"
UNRELATED = "<h1>주간 회의록</h1><h2>1. 안건</h2><p>배포 일정</p><table><tr><td>a</td></tr></table>"


class ManualEntryAlways(unittest.TestCase):
    """★2번이 어떻든 3번 수동 기입은 살아 있어야 한다."""

    def _has_manual(self, html, label):
        out, has = amosify(html)
        self.assertTrue(has, label)
        self.assertIn("add-manual-incident", out, f"{label}: 수동 기입 버튼 없음")
        self.assertIn("actual-incident-table", out, f"{label}: 3번 표 없음")
        return out

    def test_표가_있으면_체크박스로_바뀐다(self):
        out = self._has_manual(FULL, "정상")
        self.assertIn("amos-detection-table", out)
        self.assertGreaterEqual(out.count('type="radio"'), 8)   # 2행 × O/X × 2열
        self.assertIn("작업 여부", out)

    def test_2번이_내역없음_한줄이어도(self):
        self._has_manual(EMPTY2, "2번 비어 있음")

    def test_AMOS_헤딩이_아예_없어도(self):
        out = self._has_manual(NO_AMOS, "AMOS 헤딩 없음")
        self.assertIn("3. 실제 이상 발생내역", out)

    def test_1번만_있어도(self):
        self._has_manual(ONLY_TITLE, "제목+총평만")

    def test_무관한_문서에는_안_붙는다(self):
        """데모스·리포트는 아무 문서나 HTML 로 뽑는다 — 오작동하면 안 된다."""
        out, has = amosify(UNRELATED)
        self.assertFalse(has)
        self.assertEqual(out, UNRELATED)

    def test_2번이_비면_뒤_섹션_표를_건드리지_않는다(self):
        """'내역 없음' 일 때 4번 표를 AMOS 표로 착각해 뜯어고치던 위험."""
        html = (H1 + "<h2>2. AMOS 이상 감지 내역</h2><p>금일 AMOS 이상감지 내역 없음</p>"
                "<h2>4. 위험 이벤트 상세 분석</h2>"
                "<table><tr><td>다른표</td></tr></table>")
        out, _ = amosify(html)
        self.assertIn("<td>다른표</td>", out)
        self.assertNotIn("amos-detection-table", out)

    def test_실패해도_보고서는_안_깨진다(self):
        out, has = amosify(None or "")
        self.assertFalse(has)

    def test_LLM_이_옛_등급을_써도_화면에선_60으로(self):
        """★스킬 문서를 60으로 고쳐도 LLM 이 '1. 한 줄 총평: 등급 (50~70 …)'
        을 계속 쓰는 일이 있다 (지난 보고서를 참고해 베낀다). 화면에 나가는
        마지막 길목에서 표기를 바로잡는다."""
        from amos_block import _fix_grade_text as fx
        for src in ("<h2>1. 한 줄 총평: 등급 (50~70 🟠 경계 / 71~84 🔴 위험 "
                    "/ 85~100 ⛔ 초위험)</h2>",
                    "<h2>1. 한 줄 총평:등급(50~70 🟠 경계/ 71~84 🔴 위험 "
                    "/ 85~100 ⛔ 초위험)</h2>",
                    "<td>🟠 경계</td><td>50 ~ 70</td>",
                    "<td>🟠 경계</td><td>54~70</td>"):
            out = fx(src)
            self.assertIn("60~70", out, src)
            self.assertNotIn("50~70", out)
            self.assertNotIn("50 ~ 70", out)
        self.assertIn("점수 60 이상",
                      fx("<p>금일 점수 50 이상 사건 없음 — 경계 없음</p>"))

    def test_등급과_무관한_숫자는_안_건드린다(self):
        """실제 데이터의 50 을 등급으로 착각해 고치면 값이 틀려진다."""
        from amos_block import _fix_grade_text as fx
        for keep in ("<p>총 50건 처리 · 평균 50점</p>",
                     "<p>08:50~70호기 점검</p>",
                     "<td>M16HUB</td><td>50</td>"):
            self.assertEqual(fx(keep), keep)

    def test_보고서_전체에도_적용된다(self):
        html = (H1 + "<h2>1. 한 줄 총평: 등급 (50~70 🟠 경계 / 71~84 🔴 위험 "
                "/ 85~100 ⛔ 초위험)</h2><p>총 2건.</p>"
                "<h2>2. AMOS 이상 감지 내역</h2>" + AMOS_TABLE +
                "<h2>3. 실제 이상 발생내역</h2><p>…</p>")
        out, has = amosify(html)
        self.assertTrue(has)
        self.assertNotIn("50~70", out)
        self.assertIn("60~70", out)

    def test_등급_기준표는_새_기준_60에서도_지워진다(self):
        """총평의 '점수 등급 기준' 표는 헤딩 인라인과 중복이라 지운다(고객 요청).

        ★지우는 정규식이 '50~70' 고정이라, 경계 하한을 60으로 올린 순간
          새 리포트의 기준표(60~70)가 안 지워지고 남았다 — 둘 다 잡아야 한다.
        """
        for lo in ("50", "60"):
            grade_tbl = (f"<table><tr><th>등급</th><th>점수</th></tr>"
                         f"<tr><td>🟠 경계</td><td>{lo}~70</td></tr>"
                         f"<tr><td>🔴 위험</td><td>71~84</td></tr>"
                         f"<tr><td>⛔ 초위험</td><td>85~100</td></tr></table>")
            html = (H1 + "<h2>1. 한 줄 총평</h2><p>총 2건.</p>" + grade_tbl
                    + "<h2>2. AMOS 이상 감지 내역</h2>" + AMOS_TABLE
                    + "<h2>3. 실제 이상 발생내역</h2><p>…</p>")
            out, has = amosify(html)
            self.assertTrue(has)
            self.assertNotIn(f"{lo}~70", out, f"{lo}~70 기준표가 남아 있습니다")
            self.assertIn("amos-detection-table", out, "AMOS 표 변환은 그대로여야 한다")


def _code_only(path):
    """주석·독스트링을 뺀 코드 줄 — 두 복사본이 같은지 볼 때 쓴다."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    out, last = [], tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and last in (
                tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT):
            continue                       # 독스트링
        if tok.type not in (tokenize.NL, tokenize.NEWLINE):
            last = tok.type
        out.append(tok.string)
    return [ln for ln in "".join(out).splitlines() if ln.strip()]


class CopiesInSync(unittest.TestCase):
    """리얼타임 amos_block 과 데모스 amos_report 는 같은 코드여야 한다."""

    def test_두_복사본_코드가_동일하다(self):
        mine = os.path.join(util.BASE, "amos_block.py")
        theirs = os.path.normpath(os.path.join(
            util.BASE, "..", "demos_v1", "amos_report.py"))
        if not os.path.isfile(theirs):
            self.skipTest("demos_v1/amos_report.py 없음 (리얼타임만 배포된 경우)")
        a, b = _code_only(mine), _code_only(theirs)
        if a != b:
            import difflib
            d = "\n".join(list(difflib.unified_diff(
                a, b, "real_time_amhs/amos_block.py",
                "demos_v1/amos_report.py", lineterm="", n=1))[:40])
            self.fail("두 복사본이 갈라졌습니다 — 한쪽만 고쳤습니다:\n" + d)


if __name__ == "__main__":
    unittest.main()
