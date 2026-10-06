# -*- coding: utf-8 -*-
"""
fix_alarm_en.py — vhl_ohl 영문 등급 이름 바꾸기 (한 번만 돌리면 됨)

    python fix_alarm_en.py            미리보기 — 바뀔 줄만 보여 주고 파일은 안 건드림
    python fix_alarm_en.py --apply    실제로 바꿈 (원본은 *.py.bak 으로 남김)

  정상   NORMAL   → NONE
  경계   WARNING  → WARNING (그대로)
  위험   DANGER   → CRITICAL
  초위험 CRITICAL → EMERGENCY

  대상: 이 폴더의 HID_VHL_OHT.py · Rule_hid.py · HID_ALARM_MERGE.py · run_oht.py
  한글 ↔ 영문이 짝으로 붙어 있는 곳만 바꾼다 ("위험": "DANGER", 위험:'DANGER',
  "DANGER": "위험" 같은 꼴). 판정 로직은 건드리지 않는다.
  다 바꾼 뒤에도 NORMAL · DANGER 가 남아 있으면 그 줄을 따로 보여 준다 → 직접 확인.
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["HID_VHL_OHT.py", "Rule_hid.py", "HID_ALARM_MERGE.py", "run_oht.py"]

Q = r"""(["']?)"""          # 따옴표 있어도 없어도 (JS 객체 키 대비)
# 순서 중요 — 초위험 CRITICAL → EMERGENCY 를 먼저 바꾼 뒤 위험 DANGER → CRITICAL
RULES = [
    # 한글: 영문
    (rf"{Q}초위험\1(\s*:\s*)([\"'])CRITICAL\3",          r"\1초위험\1\2\3EMERGENCY\3"),
    (rf"(?<!초){Q}위험\1(\s*:\s*)([\"'])DANGER\3",        r"\1위험\1\2\3CRITICAL\3"),
    (rf"{Q}정상\1(\s*:\s*)([\"'])NORMAL\3",              r"\1정상\1\2\3NONE\3"),
    # 영문: 한글 (거꾸로 된 사전)
    (r"""(["'])CRITICAL\1(\s*:\s*)(["'])초위험\3""",       r"\1EMERGENCY\1\2\3초위험\3"),
    (r"""(["'])DANGER\1(\s*:\s*)(["'])위험\3""",           r"\1CRITICAL\1\2\3위험\3"),
    (r"""(["'])NORMAL\1(\s*:\s*)(["'])정상\3""",           r"\1NONE\1\2\3정상\3"),
]
LEFT = re.compile(r"\b(NORMAL|DANGER)\b")


def fix_text(s):
    for pat, rep in RULES:
        s = re.sub(pat, rep, s)
    return s


def main():
    apply = "--apply" in sys.argv
    total = 0
    for name in FILES:
        p = HERE / name
        if not p.exists():
            print(f"  · {name}: 없음 — 건너뜀")
            continue
        old = p.read_text(encoding="utf-8")
        new = fix_text(old)
        ch = [(i + 1, a, b) for i, (a, b) in enumerate(zip(old.splitlines(), new.splitlines())) if a != b]
        print(f"\n== {name}: {len(ch)}줄 바뀜")
        for n, a, b in ch:
            print(f"  {n:>5}  - {a.strip()}")
            print(f"         + {b.strip()}")
        left = [(i + 1, l.strip()) for i, l in enumerate(new.splitlines()) if LEFT.search(l)]
        if left:
            print(f"  ⚠ 아직 NORMAL/DANGER 가 남은 줄 {len(left)}개 — 직접 확인:")
            for n, l in left:
                print(f"  {n:>5}  {l}")
        if ch and apply:
            shutil.copy2(p, p.with_name(p.name + ".bak"))
            p.write_text(new, encoding="utf-8")
            print(f"  ✅ 저장 (원본 → {p.name}.bak)")
        total += len(ch)
    print(f"\n{'바꿈' if apply else '미리보기'}: 모두 {total}줄"
          + ("" if apply else " — 맞으면  python fix_alarm_en.py --apply"))


if __name__ == "__main__":
    main()
