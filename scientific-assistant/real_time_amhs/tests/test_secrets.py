"""저장소에 실제 비밀번호·키가 들어가지 않게 막는다.

실제로 두 번 새어 나갔다.
  · config.json 의 source.jupyter.password 에 실제 값
  · tests/mock_jupyter.py 의 MOCK_PW **기본값**에 실제 값
    (스크래치패드에서 복사할 때 딸려 들어옴 — 눈에 잘 안 띈다)

그래서 값을 외워 두고 비교하는 게 아니라(그럼 테스트 파일에 비밀이 생긴다)
**모양**으로 잡는다: password/token/key 류 이름에 '진짜처럼 생긴' 문자열이
박혀 있으면 실패한다. 비밀은 전부 아래 셋 중 하나로 둔다.

    config 의 빈 문자열 ""        → 실행할 때 채운다
    *_password.txt / token.txt    → .gitignore 됨
    환경변수                       → 코드가 이름만 안다
"""
import os
import re
import subprocess
import unittest

from . import util  # noqa: F401

# 검사할 파일 — 실제로 저장소에 올라가는 것들
EXTS = (".py", ".json", ".html", ".md", ".yaml", ".yml", ".sh", ".cfg", ".ini")
SKIP_DIRS = {"__pycache__", ".git", "data", "node_modules", "fixtures"}
# 키 파일 자체는 .gitignore 되므로 검사 대상이 아니다 (있어도 커밋 안 됨)
SKIP_FILES = {"api_key.txt", "token.txt", "jupyter_password.txt"}
# 생성물(압축된 HTML·base64 덩어리)은 건너뛴다. 한 줄이 수 MB 라 검사도
# 무의미하고 느리다 — 사람이 비밀을 적어 넣는 자리가 아니다.
MAX_FILE_BYTES = 1_000_000
MAX_LINE_CHARS = 500

# 이름이 이거면 값이 비밀일 수 있다.
#   ★\b 를 쓰면 안 된다 — '_' 가 단어 문자라 jupyter_password / MOCK_PW 처럼
#     snake_case 로 붙은 이름을 통째로 놓친다. 앞뒤를 '글자가 아닌 것' 으로
#     끊어서 tokenizer·author 같은 말은 걸러낸다.
SECRETISH = re.compile(
    r"(?i)(?:^|[^A-Za-z])(pass(?:word|wd)?|pwd?|secret|token|api[_-]?key"
    r"|credential|auth)(?:[^A-Za-z]|$)")

# 값이 이러면 비밀이 아니다 (자리표시자·환경변수 이름·파일명·URL·설명문)
PLACEHOLDER = re.compile(
    r"(?i)(더미|테스트|샘플|예시|여기에|dummy|sample|example|placeholder|"
    r"change[-_ ]?me|your[-_]|xxx+|\.\.\.|<[^>]*>|^$)")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")          # JUPYTER_PASSWORD
FILE_NAME = re.compile(r"(?i)\.(txt|json|pem|key|cfg|env)$")
URLISH = re.compile(r"(?i)^(https?://|/|\{|%)")

# 값이 이렇게 생겼으면 '진짜 비밀' 로 본다 — 8자 이상이고 대/소/숫자/기호가 섞임
def _looks_secret(v: str) -> bool:
    if len(v) < 8 or len(v) > 128:
        return False
    if PLACEHOLDER.search(v) or ENV_NAME.match(v) or FILE_NAME.search(v) \
            or URLISH.match(v):
        return False
    if " " in v:                       # 설명문·문장은 비밀이 아니다
        return False
    kinds = sum(bool(re.search(p, v)) for p in
                (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    return kinds >= 3                  # 예: Xy7$kLm2Qz → 소·대문자·숫자·기호


# 값이 박힌 자리 — 파이썬 대입 / JSON 필드 / 셸 변수
ASSIGN = re.compile(r"""([A-Za-z_][\w\-]*)\s*[:=]\s*["']([^"']{1,128})["']""")
# 그 줄에 있는 모든 문자열 — 대입문만 보면 놓친다.
#   ★실제로 샜던 형태가 이거였다: os.environ.get("MOCK_PW", "실제비번")
#     '=' 뒤가 함수 호출이라 ASSIGN 에 안 걸린다.
STRINGS = re.compile(r"""["']([^"'\n]{1,128})["']""")


def _line_hits(line: str):
    """한 줄에서 (이름, 값) 후보. 비밀스러운 이름이 줄에 있으면 그 줄의
    **모든 문자열**을 값 후보로 본다 (함수 인자로 넘기는 경우 포함)."""
    out = []
    named = {v: n for n, v in ASSIGN.findall(line)}
    if not SECRETISH.search(line):
        return out
    for v in STRINGS.findall(line):
        if _looks_secret(v):
            out.append((named.get(v) or _nearest_name(line) or "?", v))
    return out


def _nearest_name(line: str) -> str:
    m = SECRETISH.search(line)
    return m.group(1) if m else ""


def _files(root: str):
    """검사할 파일 목록. git 이 있으면 추적 중인 것만(= 커밋되는 것만)."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, timeout=20,
                             capture_output=True, check=True).stdout
        names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        if names:
            return [os.path.join(root, n) for n in names
                    if n.endswith(EXTS)
                    and os.path.basename(n) not in SKIP_FILES
                    and not any(p in SKIP_DIRS for p in n.split(os.sep))]
    except Exception:
        pass
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(EXTS) and f not in SKIP_FILES:
                out.append(os.path.join(base, f))
    return out


class NoHardcodedSecrets(unittest.TestCase):
    def test_저장소_파일에_실제_비밀번호가_없다(self):
        hits = []
        for path in _files(util.BASE):
            rel = os.path.relpath(path, util.BASE)
            if rel.startswith("tests" + os.sep + "test_secrets"):
                # 이 파일은 검사 대상에서 뺀다 — 정규식과 '가짜 예시' 가
                # 당연히 걸리기 때문이다. 그래서 **여기 예시에는 진짜 값을
                # 절대 쓰지 마라.** 스스로는 못 잡는다.
                continue
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
            except Exception:
                continue
            for n, ln in enumerate(lines, 1):
                if len(ln) > MAX_LINE_CHARS:
                    continue
                for name, val in _line_hits(ln):
                    # ★값은 절대 찍지 않는다 — 실패 로그에 비밀이 남는다.
                    #   어디인지만 알려주면 사람이 열어 보면 된다.
                    hits.append(f"  {rel}:{n}  {name} = …({len(val)}자)")
        self.assertEqual(hits, [], "\n실제 비밀번호·키로 보이는 값이 있습니다 —\n"
                                   + "\n".join(hits)
                                   + "\n\n빈 문자열로 두고 *_password.txt(.gitignore)"
                                     " 나 환경변수로 옮기세요.")

    def test_config_의_비밀_칸은_비어_있다(self):
        """운영값은 실행할 때 채운다 — config.json 은 저장소에 올라간다."""
        import json
        with open(os.path.join(util.BASE, "config.json"), encoding="utf-8-sig") as f:
            cfg = json.load(f)
        checks = [
            ("llm.api_key", (cfg.get("llm") or {}).get("api_key")),
            ("api_key", cfg.get("api_key")),
            ("source.jupyter.password",
             ((cfg.get("source") or {}).get("jupyter") or {}).get("password")),
            ("source.jupyter.token",
             ((cfg.get("source") or {}).get("jupyter") or {}).get("token")),
        ]
        for key, val in checks:
            v = str(val or "").strip()
            if not v or v.startswith("<"):
                continue
            self.fail(f"config.json 의 {key} 에 값이 들어 있습니다 "
                      f"({len(v)}자). 비우고 키 파일·환경변수로 옮기세요.")

    def test_키_파일들이_gitignore_되어_있다(self):
        p = os.path.join(util.BASE, ".gitignore")
        if not os.path.isfile(p):
            self.skipTest(".gitignore 없음")
        with open(p, encoding="utf-8") as f:
            body = f.read()
        for name in ("api_key.txt", "token.txt", "jupyter_password.txt"):
            self.assertIn(name, body, f"{name} 이 .gitignore 에 없습니다")

    def test_검사기가_진짜로_잡는다(self):
        """그물이 헐거우면 있으나 마나다 — 실제로 샜던 모양을 넣어 본다."""
        leaked = [
            # ★예시에 **진짜 값을 쓰면 안 된다** — 이 파일도 저장소에 올라간다.
            #   (실제로 여기 진짜 비밀번호를 적어 놨다가 다시 샐 뻔했다.
            #    이 파일은 자기 자신을 검사에서 빼므로 스스로 못 잡는다.)
            #   모양만 같은 가짜를 쓴다.
            'PW = os.environ.get("MOCK_PW", "Xy7$kLm2Qz")',
            '"password": "Xy7$kLm2Qz",',
            'jupyter_password = "S0me!Pass9"',
            'api_key = "sk-abc123XYZ!def"',
            'MOCK_PW = "R3al!Fake9"',
            '{"jupyter": {"password": "P@ssw0rd12"}}',
        ]
        for ln in leaked:
            self.assertTrue(_line_hits(ln), f"못 잡음: {ln}")

    def test_정상적인_값은_안_잡는다(self):
        """자리표시자·환경변수 이름·파일명까지 잡으면 쓸 수가 없다."""
        fine = [
            '"password": ""',
            '"password_file": "jupyter_password.txt"',
            '"password_env": "JUPYTER_PASSWORD"',
            'PW = os.environ.get("MOCK_PW", "테스트용-더미-비번")',
            '"api_key": "<여기에 키를 넣으세요>"',
            '"token": ""',
            '"api_key_file": "token.txt"',
            'password = "change-me"',
            'tokenizer = "Kiwi-v1.2!x"',       # token 이 들어갔지만 다른 말
            'author = "Hong-Gildong!1"',       # auth 가 들어갔지만 다른 말
        ]
        for ln in fine:
            self.assertEqual(_line_hits(ln), [], f"잘못 잡음: {ln}")


if __name__ == "__main__":
    unittest.main()
