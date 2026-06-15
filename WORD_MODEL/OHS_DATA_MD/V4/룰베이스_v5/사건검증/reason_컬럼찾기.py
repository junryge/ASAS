#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reason 컬럼찾기 — 발동이벤트/사건단위의 'reason'(또는 relation) 텍스트를 넣으면
                  그 안에서 발동한 룰이 '어느 원본 데이터 컬럼'을 봤는지 찾아준다.

단독 실행. 입력 방법 3가지:
  1) python reason_컬럼찾기.py "reason 텍스트 전체"
  2) python reason_컬럼찾기.py            ← 실행 후 붙여넣기 (Enter 2번)
  3) echo "reason..." | python reason_컬럼찾기.py

예:
  python reason_컬럼찾기.py "hot_area=M16HUB; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=20.13분/기준9.0),R-D(STB=100.0%)]; M16A[R-B(6F_TO_HUB_JOB+145/30분)]"
"""
import re
import sys

# ── 룰 → 원본 컬럼 매핑 (hubroom_predictor.py 와 동일) ──
RA_COL = {
    'M16HUB': 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN',
    'M14':    'M14.QUE.LOAD.AVGLOADTIME1MIN',
    'M14B':   'M14B.QUE.TIME.AVGTOTALTIME1MIN',
    'M16A':   'M16A.QUE.LOAD.AVGLOADTIME1MIN',
    'M16B':   'M16B.QUE.LOAD.AVGLOADTIME1MIN',
    'M16_PKT':'M16_PKT.QUE.TIME.AVGTOTALTIME1MIN',
    'M16_WT': 'M16_WT.QUE.TIME.AVGTOTALTIME1MIN',
}
RB_COL = {
    'M16HUB': 'M16HUB.QUE.ALL.CURRENTQCNT',
    'M14':    'M14.QUE.ALL.HUB_TO_M14_JOB',
    'M14B':   'M14B.QUE.ALL.HUB_TO_M14B_JOB',
    'M16A':   'M16A.QUE.ALL.6F_TO_HUB_JOB',
    'M16B':   'M16B.QUE.ALL.10F_TO_HUB_JOB',
}
SLA_COL = {
    'M16HUB': 'M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M14':    'M14.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M16A':   'M16A.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M16B':   'M16B.QUE.ALL.TRANSPORT4MINOVERRATIO',
}
SORTER_COL = {
    'M14':    'M14.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M14B':   'M14B.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M16A':   'M16A.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M16B':   'M16B.SORTER.ABN.SORTERWAITCOUNTOVER',
    'M16HUB': 'M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER',
}
OHT_COL = {
    'M16HUB': 'M16HUB.QUE.OHT.OHTUTIL',
    'M14':    'M14.QUE.OHT.OHTUTIL',
    'M14B':   'M14B.QUE.OHT.OHTUTIL',
    'M16A':   'M16A.QUE.OHT.OHTUTIL',
    'M16B':   'M16B.QUE.OHT.OHTUTIL',
}
# 단일 컬럼 (영역 고정)
FAB_COL = 'M16HUB.STRATE.ALL.FABSTORAGERATIO'
STB_COL = 'M16HUB.STRATE.STB.3F_STORAGE_UTIL'
MLUD_COL = 'M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB'
CNV_COL = 'M16HUB.QUE.CNV.3F_CNV_MAXCAPA'

AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B', 'M16', 'M16_PKT', 'M16_WT']

# 키워드 → (룰 한글명, 컬럼 dict 또는 단일컬럼)
# reason 안의 영문 토큰으로 매칭
def cols_for_area_rule(area, token):
    """영역 + reason 안 룰 토큰 → 원본 컬럼 리스트."""
    found = []
    t = token.upper()
    if "R-A" in t or 'AVGTOTALTIME' in t or 'AVGLOADTIME' in t or '반송' in token:
        if area in RA_COL: found.append(('반송시간(R-A)', RA_COL[area]))
    if 'R-B' in t or '6F_TO_HUB' in t or '10F_TO_HUB' in t or 'CURRENTQCNT' in t or 'TO_M14' in t or '큐' in token:
        if area in RB_COL: found.append(('큐누적(R-B)', RB_COL[area]))
    if 'SLA' in t or 'TRANSPORT4MIN' in t or '4분초과' in token:
        if area in SLA_COL: found.append(('SLA 4분초과', SLA_COL[area]))
        found.append(('SLA 4분초과 카운트', f'{area}.QUE.ALL.TRANSPORT4MINOVERCNT'))
    if 'SORT' in t or 'SORTERWAIT' in t or 'LOT대기' in token:
        if area in SORTER_COL: found.append(('Sorter 대기', SORTER_COL[area]))
    if 'OHT' in t:
        if area in OHT_COL: found.append(('OHT 가동률', OHT_COL[area]))
    if 'R-D' in t or 'FAB' in t or 'STB' in t or '저장' in token:
        if area == 'M16HUB':
            if 'FAB' in t or '저장' in token: found.append(('FAB 저장율(R-D)', FAB_COL))
            if 'STB' in t: found.append(('STB 저장율(R-D)', STB_COL))
        elif area in OHT_COL:
            found.append(('OHT 가동률(R-D)', OHT_COL[area]))
    if 'R-C' in t or '역증가' in token or '리프터' in token:
        if area == 'M16HUB':
            found.append(('리프터 역증가(R-C)', 'M16HUB.STK.*.LIFTER (역증가 감지)'))
    if 'MLUD' in t:
        found.append(('MLUD JOB', MLUD_COL))
    if 'CNV' in t:
        found.append(('CNV MAXCAPA', CNV_COL))
    if 'MAXCAPA' in t or 'CAPA' in token:
        found.append(('MAXCAPA 변경', f'{area}.QUE.CNV.3F_CNV_MAXCAPA'))
    return found


def parse_reason(text):
    print("=" * 72)
    print("  reason 분석 — 발동한 룰이 본 원본 데이터 컬럼")
    print("=" * 72)

    # 영역별 블록 추출:  M16HUB[ ... ];  M14[ ... ];
    blocks = re.findall(r'(M16HUB|M14B|M14|M16A|M16B|M16_PKT|M16_WT|M16)\[([^\]]*)\]', text)
    if not blocks:
        print("\n  [!] 'M16HUB[...]' 형태의 영역 블록을 못 찾음.")
        print("      reason 또는 relation 컬럼 내용을 통째로 넣어줘.")
        return

    seen = set()
    for area, body in blocks:
        # body 안 룰 토큰을 콤마로 분리 (괄호 안 콤마는 보존 어려우니 단순 split)
        tokens = re.split(r'(?<=\))\s*,\s*|,\s*(?=R-)', body)
        if not tokens:
            tokens = [body]
        cols = []
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            for label, col in cols_for_area_rule(area, tok):
                key = (area, col)
                if key in seen:
                    continue
                seen.add(key)
                cols.append((label, col, tok))
        if cols:
            print(f"\n  ▶ {area}")
            for label, col, tok in cols:
                # 실측값 추출 (예: =20.13분, +145/30분, =100.0%)
                m = re.search(r'[=+]\s*[\d.]+', tok)
                val = m.group(0).strip() if m else ''
                print(f"     · {label:18s} → {col}"
                      + (f"   (실측 {val})" if val else ""))

    # 흐름 (flow)
    flow = re.search(r'흐름[:：]\s*([^;]+)', text)
    if flow:
        print(f"\n  ▶ 흐름(flow) 정체 노드")
        for node in flow.group(1).split(';'):
            node = node.strip()
            if node:
                nm = re.match(r'([A-Za-z0-9_]+)', node)
                print(f"     · {node}   → 흐름노드 {nm.group(1) if nm else node} (FLOW_NODES 정의)")

    print()
    print("  ※ 위 컬럼들이 M16A_HUBROOM_PR.csv (원본 수집 데이터) 의 실제 컬럼명.")
    print("    이 값들이 임계 초과해서 점수가 올라간 것.")


def main():
    if len(sys.argv) >= 2:
        text = ' '.join(sys.argv[1:])
    else:
        print("reason 또는 relation 텍스트를 붙여넣고 Enter 2번 (또는 Ctrl+D):")
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        print("입력 없음.")
        return
    parse_reason(text)


if __name__ == '__main__':
    main()
