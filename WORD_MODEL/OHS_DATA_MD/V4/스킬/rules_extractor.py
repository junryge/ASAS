#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hubroom_predictor.py 의 모든 룰/임계값/컬럼을 자동 추출 → JSON 으로 덤프.

스킬 문서 (일반/카파시 MD) 작성 시 누락 방지용. 코드 변경 후 재실행하여
새 룰/임계가 모두 문서에 반영되는지 검증.

사용:
    python rules_extractor.py
        → rules_dump.json 생성 (현재 폴더)

    python rules_extractor.py --check 일반_에이전트_스킬.md
        → MD 파일에 모든 룰이 언급되는지 검증 (누락 항목 출력)
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREDICTOR_PY = HERE.parent / 'hubroom_predictor.py'


def extract_constants(source: str) -> dict:
    """hubroom_predictor.py 의 상수 블록을 ast 로 추출."""
    import ast
    tree = ast.parse(source)

    keep = {
        'WINDOW_MIN', 'INCIDENT_END_GAP_MIN', 'PREDICT_LOOKBACK_MIN',
        'TH_RA', 'TH_RA_SUSTAINED_RATIO', 'TH_RA_SUSTAINED_COUNT',
        'TH_RB_30', 'TH_RB_10', 'TH_RC_REVERSE',
        'TH_RD_FABSTORAGE', 'TH_RD_HUB_STB_UTIL', 'TH_RD_OHT_UTIL',
        'TH_SLA_RATIO', 'TH_SORTER_WAIT', 'TH_SORTER_TRANSFER_FAIL',
        'TH_FLOW_X1_5', 'TH_FLOW_X2_0', 'TH_FLOW_X3_0',
        'MAXCAPA_NORMAL', 'FLOW_NODES', 'LIFTER_IDS',
        'RA_COL', 'RB_COL', 'RD_OHT_COL', 'SLA_COL',
        'SORTER_COL', 'SORTER_FAIL_COL', 'HUB_OUT_COLS',
        'STAGE_LABEL', 'EVENT_FIELDS', 'INCIDENT_FIELDS', 'AREAS_ALL',
    }

    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in keep:
                    try:
                        out[target.id] = ast.literal_eval(node.value)
                    except Exception:
                        # 표현식 (예: TH_RB_10 dict comprehension)
                        # 평가는 못 하지만 소스 위치 기록
                        out[target.id] = f"<expression@line {node.lineno}>"
    return out


def extract_score_weights(source: str) -> dict:
    """eval_area_rules / evaluate_unified 의 점수 가중치 추출."""
    weights = {}

    # 영역 점수 — 룰별 분해 점수 형태 (RA_pts = 10 if out['ra_trig'] else 0)
    area_pattern = re.compile(
        r"(\w+?)_pts\s*=\s*(\d+)\s*if out\['(\w+)'\]\s*else 0"
    )
    for m in area_pattern.finditer(source):
        sig_lower, score, flag = m.groups()
        # sig_lower 는 ra / ra_sus / rb / rb_fast / rc / rd / sla / sort 등
        sig_name = {
            'ra': 'RA', 'ra_sus': 'RA_sus', 'rb': 'RB', 'rb_fast': 'RB_fast',
            'rc': 'RC', 'rd': 'RD', 'sla': 'SLA', 'sort': 'SORT',
        }.get(sig_lower, sig_lower.upper())
        weights.setdefault('area', {})[sig_name] = {'flag': flag, 'score': int(score)}

    # MAXCAPA (mc_pts = 10 * out['maxcapa_changed_n'])
    if "mc_pts" in source and "maxcapa_changed_n" in source:
        weights.setdefault('area', {})['MAXCAPA*n'] = {'flag': 'maxcapa_changed_n>0', 'score': 10, 'per': '개'}

    # Flow score
    flow_pattern = re.compile(
        r"if info\['level'\] == '(\S+?)':\s*flow_score \+= (\d+)"
    )
    for m in flow_pattern.finditer(source):
        level, score = m.groups()
        weights.setdefault('flow', {})[level] = int(score)

    # 추가 점수
    weights['unified'] = {
        'sla_per_area': 5,
        'sorter_per_area': 3,
        'maxcapa_per_change': 10,
        'unified_max': 500,
    }

    return weights


def extract_levels(source: str) -> dict:
    """6 단계 위험도 등급 임계."""
    pattern = re.compile(
        r"unified_risk_score\s*>=\s*(\d+):\s*\n\s*unified_risk_level\s*=\s*'(\S+?)'"
    )
    levels = {}
    for m in pattern.finditer(source):
        score, label = m.groups()
        levels[label] = int(score)
    levels['정상'] = 0  # else
    return levels


def extract_stage_conditions(source: str) -> dict:
    """unified_s1/s2/s3 발동 조건."""
    out = {}
    for stage in ('s1', 's2', 's3'):
        m = re.search(rf"unified_{stage}\s*=\s*(.+)", source)
        if m:
            out[stage] = m.group(1).strip()
    return out


def dump_all() -> dict:
    if not PREDICTOR_PY.exists():
        sys.exit(f'❌ hubroom_predictor.py 없음: {PREDICTOR_PY}')

    src = PREDICTOR_PY.read_text(encoding='utf-8')
    return {
        '_source': str(PREDICTOR_PY),
        '_extracted_at': str(Path(__file__).stat().st_mtime),
        'constants': extract_constants(src),
        'score_weights': extract_score_weights(src),
        'risk_levels': extract_levels(src),
        'stage_conditions': extract_stage_conditions(src),
    }


def collect_required_terms(dump: dict) -> list:
    """문서에 반드시 등장해야 하는 키워드 목록 (누락 검증용)."""
    terms = set()
    # 영역
    terms.update(dump['constants'].get('AREAS_ALL', []))
    # 룰 임계
    for area in dump['constants'].get('TH_RA', {}):
        terms.add(area)
    for area in dump['constants'].get('TH_RB_30', {}):
        terms.add(area)
    # FLOW_NODES 키
    terms.update(dump['constants'].get('FLOW_NODES', {}).keys())
    # 등급
    terms.update(dump['risk_levels'].keys())
    # 점수 시그널
    for sig in dump['score_weights'].get('area', {}):
        terms.add(sig)
    # 핵심 키워드
    terms.update(['R-A', 'R-B', 'R-C', 'R-D', 'SLA', 'Sorter', 'MLUD', 'MAXCAPA', '4ABLD'])
    return sorted(terms)


def check_coverage(md_path: Path, dump: dict) -> dict:
    if not md_path.exists():
        sys.exit(f'❌ 문서 없음: {md_path}')
    text = md_path.read_text(encoding='utf-8')
    required = collect_required_terms(dump)
    missing = [t for t in required if t not in text]
    present = [t for t in required if t in text]
    return {
        'md': str(md_path),
        'required_total': len(required),
        'present': len(present),
        'missing_count': len(missing),
        'missing': missing,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='rules_dump.json', help='추출 결과 JSON')
    p.add_argument('--check', help='MD 문서 누락 검증')
    args = p.parse_args()

    dump = dump_all()

    out_path = HERE / args.out
    out_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✅ 룰 덤프 → {out_path}')
    print(f'   상수 {len(dump["constants"])}개')
    print(f'   영역 점수 시그널 {len(dump["score_weights"].get("area", {}))}개')
    print(f'   위험도 등급 {len(dump["risk_levels"])}개')
    print(f'   Stage 조건 {len(dump["stage_conditions"])}개')

    if args.check:
        md_path = HERE / args.check
        cov = check_coverage(md_path, dump)
        print()
        print(f'📋 누락 검증: {cov["md"]}')
        print(f'   필수 키워드 {cov["required_total"]}개')
        print(f'   포함 {cov["present"]}개')
        if cov['missing_count'] == 0:
            print(f'   ✅ 누락 없음')
        else:
            print(f'   ❌ 누락 {cov["missing_count"]}개:')
            for t in cov['missing']:
                print(f'      - {t}')
            sys.exit(1)


if __name__ == '__main__':
    main()
