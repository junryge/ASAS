#!/usr/bin/env python3
"""m16_hub_skills/*.md → scientific-skills/m16-hub-*/SKILL.md 로 옮겨 심는다.

왜 이게 필요한가
    허브룸 도메인 문서 넷은 이미 스킬 형식(YAML 앞머리에 name/description)
    으로 쓰여 있었는데, 폴더 구조가 달라서 하네스에 등록이 안 됐다. 그래서
    정작 우리 일인 '반송 정체' 를 물으면 gtars, cmd-cr 같은 엉뚱한 게 나왔다.

    데모스는 스킬을 scientific-skills/<id>/SKILL.md 에서만 찾는다
    (demos_v1/routes_api.py 의 _skill_exists). 그래서 그 자리에 놔 줘야 한다.

원본은 m16_hub_skills/ 다
    여기서 만든 SKILL.md 는 사본이다. 한쪽만 고치면 서로 어긋나므로,
    tests/test_m16_skills.py 가 어긋남을 잡는다. 문서를 고쳤으면 이걸 다시
    돌려라:  python tools/sync_m16_skills.py
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE, "m16_hub_skills")
DST_DIR = os.path.join(BASE, "scientific-skills")

# 원본 파일 → 스킬 폴더 이름(ASCII 케밥 — 다른 스킬들과 같은 방식)
MAP = {
    "m16_hub_카파시_v3.5.md": "m16-hub-overview",
    "m16_hub_일반_v3.5.md": "m16-hub-usage",
    "m16_hub_임계값_v3.5.md": "m16-hub-thresholds",
    "m16_hub_결과해석_도메인_고객인용V3.5.md": "m16-hub-interpret",
}

# 한국어 검색어 — 라우터에서 키워드 등급(본문보다 훨씬 무겁다)으로 쓰인다.
KEYWORDS = {
    "m16-hub-overview": ["M16", "허브룸", "HUBROOM", "반송", "구조", "룰베이스",
                         "8영역", "9룰", "점수산식", "등급"],
    "m16-hub-usage": ["실행방법", "사용법", "돌리는법", "백테스트", "실시간",
                      "hubroom_predictor", "입력파일", "출력파일"],
    "m16-hub-thresholds": ["임계값", "thresholds", "임계조정", "튜닝", "룰임계",
                           "민감도"],
    "m16-hub-interpret": ["결과해석", "발동이벤트", "사건단위", "장애유형",
                          "정체", "경계", "위험", "초위험", "용어표준"],
}


def sync(write: bool = True) -> list[tuple[str, bool]]:
    """되돌려 주는 값: [(스킬이름, 내용이_같은가), ...]"""
    out = []
    for src_name, skill_id in MAP.items():
        src = os.path.join(SRC_DIR, src_name)
        if not os.path.isfile(src):
            out.append((skill_id, False))
            continue
        with open(src, "r", encoding="utf-8") as f:
            body = f.read()
        dst_dir = os.path.join(DST_DIR, skill_id)
        dst = os.path.join(dst_dir, "SKILL.md")
        same = False
        if os.path.isfile(dst):
            with open(dst, "r", encoding="utf-8") as f:
                same = f.read() == body
        if write and not same:
            os.makedirs(dst_dir, exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(body)
        out.append((skill_id, same))
    return out


if __name__ == "__main__":
    check = "--check" in sys.argv
    res = sync(write=not check)
    bad = [n for n, same in res if not same]
    for name, same in res:
        print(f"  {'그대로' if same else ('어긋남' if check else '갱신')}  {name}")
    if check and bad:
        print(f"\n어긋난 스킬 {len(bad)}개 — python tools/sync_m16_skills.py 를 돌려라")
        sys.exit(1)
