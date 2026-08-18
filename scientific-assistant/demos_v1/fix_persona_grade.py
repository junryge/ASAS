#!/usr/bin/env python3
"""옛 등급 기준(50~70)이 어디서 나오는지 **찾아내고** 60~70 으로 고친다.

왜 필요한가
    스킬 문서와 코드를 60 기준으로 고쳐도 보고서 헤딩이 계속 '50~70' 으로
    나오는 일이 있다. 등급 문구가 저장소가 아니라 **서버 런타임 데이터**에
    복사돼 있기 때문이다. 실제로 겪은 자리들:

      · 개인 에이전트의 페르소나(시스템 프롬프트)
        demos_v1/personal-agents/<user>/<agent>.json 의 "persona"
        → 에이전트를 만들 때 붙여넣은 사본이라 스킬을 고쳐도 안 바뀐다
      · 에이전트 지식파일 / 업로드한 스킬 사본  (knowledge/, uploads/)
      · 지난 보고서 HTML — LLM 이 참고해 헤딩을 그대로 베낀다
      · 저장한 프롬프트 (saved-prompts/)

무엇을 바꾸나
    등급을 말하는 줄에서만 바꾼다 — 같은 줄에 71·85 가 있거나 '경계' 가 있을 때.
        5x ~ 70            → 60~70      (공백·54 같은 옛 값 포함)
        점수 5x 이상/미만   → 점수 60 …
    '총 50건'·'평균 50점'·'08:50~70호기' 같은 실제 숫자는 건드리지 않는다.

사용법
    python fix_persona_grade.py                 # 어디에 있는지 찾기만 (안전)
    python fix_persona_grade.py --apply         # 실제로 고침 (.bak 백업)
    python fix_persona_grade.py --dir /경로     # 폴더 추가 지정
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PKG_DIR)

# 데모스가 런타임에 읽고 쓰는 곳 전부
SEARCH_DIRS = [
    os.path.join(PKG_DIR, "personal-agents"),   # ★페르소나(시스템 프롬프트)
    os.path.join(PKG_DIR, "knowledge"),
    os.path.join(BASE_DIR, "knowledge"),
    os.path.join(BASE_DIR, "uploads"),          # 지난 보고서·업로드 문서
    os.path.join(BASE_DIR, "saved-prompts"),
    os.path.join(BASE_DIR, "scientific-skills"),
    os.path.join(BASE_DIR, "m16_hub_skills"),
]
EXTS = (".json", ".txt", ".md", ".html", ".htm", ".yaml", ".yml", ".csv")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "backup"}
MAX_BYTES = 8_000_000

GRADE_LO = 60
_RE_RANGE = re.compile(r"(?<![\d.])5\d\s*~\s*70(?![\d.])")
_RE_OVER = re.compile(r"점수\s*5\d(\s*(?:점)?\s*(?:이상|미만))")
# JSON 안에서 페르소나가 들어갈 만한 키
_FIELDS = ("persona", "system_prompt", "systemPrompt", "instructions",
           "prompt", "description", "content", "text", "body")


def fix_text(txt):
    """등급을 말하는 줄에서만 5x→60. 아니면 원문 그대로."""
    if not isinstance(txt, str) or ("~" not in txt and "점수 5" not in txt):
        return txt
    out = []
    for line in txt.split("\n"):
        if ("71" in line and "85" in line) or "경계" in line:
            line = _RE_RANGE.sub(f"{GRADE_LO}~70", line)
            line = _RE_OVER.sub(lambda m: f"점수 {GRADE_LO}{m.group(1)}", line)
        out.append(line)
    return "\n".join(out)


def _walk_json(node):
    """JSON 안의 문자열을 재귀로 고친다 → (새 노드, 바뀐 (전,후) 목록)."""
    hits = []
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and k in _FIELDS:
                nv = fix_text(v)
                if nv != v:
                    hits += [(b, a) for b, a in
                             zip(v.split("\n"), nv.split("\n")) if b != a]
                out[k] = nv
            else:
                nv, h = _walk_json(v)
                out[k] = nv
                hits += h
        return out, hits
    if isinstance(node, list):
        out = []
        for v in node:
            nv, h = _walk_json(v)
            out.append(nv)
            hits += h
        return out, hits
    return node, hits


def _process(path, apply):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception as e:
        print(f"  ⚠️ 읽기 실패 {path}: {e}")
        return None

    if path.endswith(".json"):
        try:
            data = json.loads(raw)
        except Exception:
            data = None
        if data is not None:
            new, hits = _walk_json(data)
            if not hits:
                return None
            if apply:
                shutil.copy2(path, path + ".bak")
                tmp = path + f".tmp{os.getpid()}"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(new, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            return hits
    new = fix_text(raw)
    if new == raw:
        return None
    hits = [(b, a) for b, a in zip(raw.split("\n"), new.split("\n")) if b != a]
    if apply:
        shutil.copy2(path, path + ".bak")
        tmp = path + f".tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new)
        os.replace(tmp, path)
    return hits


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    dirs = list(SEARCH_DIRS)
    if "--dir" in argv:
        dirs.insert(0, argv[argv.index("--dir") + 1])

    print(f"{'고치는' if apply else '찾는'} 중 — 등급 기준 5x~70 → {GRADE_LO}~70\n")
    total = files = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        found_here = 0
        for root, subs, names in os.walk(d):
            subs[:] = [s for s in subs if s not in SKIP_DIRS]
            for fn in sorted(names):
                if not fn.endswith(EXTS) or fn.endswith(".bak"):
                    continue
                path = os.path.join(root, fn)
                hits = _process(path, apply)
                if not hits:
                    continue
                files += 1
                total += len(hits)
                found_here += 1
                print(f"  {'✅' if apply else '·'} {os.path.relpath(path, BASE_DIR)}"
                      f"  ({len(hits)}줄)")
                for b, a in hits[:3]:
                    print(f"      - {b.strip()[:76]}")
                    print(f"      + {a.strip()[:76]}")
                if len(hits) > 3:
                    print(f"      … 외 {len(hits)-3}줄")
        if found_here:
            print()

    if not files:
        print("옛 등급 기준이 남은 파일이 없습니다.")
        print("그래도 화면에 50~70 이 나온다면 — 데모스를 재시작했는지,")
        print("그리고 그 답변이 **새로 생성한 것**인지(예전 대화를 다시 여는 게")
        print("아닌지) 확인하세요. 코드에도 안전망이 있어 새 답변은 60 으로 나갑니다.")
        return 0
    print(f"파일 {files}개 · {total}줄")
    if not apply:
        print("\n실제로 고치려면:  python fix_persona_grade.py --apply")
    else:
        print("\n적용 완료 (원본은 .bak). 데모스를 재시작하고 에이전트를 "
              "다시 열면 새 기준으로 답합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
