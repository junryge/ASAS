#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 탐지현황_판정 — 사건단위 CSV + 메신저 대화 → 탐지현황 컬럼 생성
# ====================================================================
# 판정 기준 (사용자 정의)
#   정탐     : 메신저 이슈보다 10~30분 전에 탐지
#   지연탐지 : 이슈보다 1~20분 늦게 탐지
#   오탐     : 매칭되는 이슈가 없는데 탐지
#   미탐     : 메신저에 이슈가 있는데 탐지 못함 → 그 시각으로 행을 추가하고 미탐 표기
#
#   ※ 0~9분 전 탐지는 정탐에 포함(사유에 실제 분차 표기).
#     사건 지속시간을 고려해 매칭 창은 [탐지-30분, 탐지+20분] 이다.
#
# 메신저에서 "이슈"로 보는 것 (반송에 실제 영향이 있었다고 말한 것만)
#   · 정체 / 몰림 / 밀림·밀려 / Delay / 지연 / 풉 쌓임 / QUE 많음
#   · Rail Cut 실시
#   · HUB·Bridge OHT Error 발생
#   · 반송 경로 차단 (A_IN/A_OUT/PORT/INPUT ... 차단)
#   제외: 작업 공지·예정, 앞으로 지연될 예정, 조치완료·원복·Clear, "특이사항 없음" 답변
#   보조(--include-minor 로 포함): 반송영향 언급 없는 장비 Error (리프터 AI Close 등)
#
# 질문형 메시지("~풉이 쌓이는 중인데 특이사항 있을까요?")는 실제 관측을 말한 것이므로
# 이슈로 잡되, 바로 뒤 회신이 "특이사항 없음"이면 근거메시지에 (회신: …) 로 같이 적어
# 사람이 최종 판단할 수 있게 한다.
#
# 그 밖에
#   · 사건단위 CSV 의 따옴표가 유실돼 칸이 밀린 파일은 propagation_chain 을 다시
#     이어붙여 자동 복구한다 (뒤 4칸은 쉼표가 없어 항상 제자리라 구조로 되돌릴 수 있음)
#   · 메신저 파일이 월 경계를 넘어가도, 사건단위가 다루는 날짜 범위 밖 이슈는 미탐에 넣지 않는다
#
# 사용법
#   python 탐지현황_판정.py --events .\7월_사건단위.csv --msg .\7월.txt -o .\7월_탐지현황.csv
#   python 탐지현황_판정.py --events .\6월_사건단위.csv --msg .\6월.txt -o .\6월_탐지현황.csv
#   옵션: --include-minor(장비Error도 이슈로) · --early 30 --late 20 --good 10 · --merge-min 30
import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta

csv.field_size_limit(10 ** 7)

# ── 메신저 분류 사전 ────────────────────────────────────────
CORE_PAT = [
    r'정체', r'몰림', r'밀림', r'밀려', r'밀리는', r'Delay', r'delay', r'지연',
    r'풉이\s*쌓', r'쌓이는', r'쌓였', r'FOUP\s*배출\s*Delay', r'QUE\s*가?\s*많',
    r'QUE\s*가?\s*\d+\s*개', r'물량\s*이동이\s*많',
    # "Rail Cut 실시하겠습니다"(작업 예고)는 제외하고 실제로 자른 것만
    r'Rail\s*Cut\s*(실시했|실시\s*했|실시하였|했|하였)', r'RAIL\s*CUT\s*(실시|했|하였)',
]
# 반송 경로 차단 — Error/알람 때문에 급히 막은 것만 이슈. 계획작업용 차단은 제외.
BLOCK_PAT = r'(A_?IN|A_?OUT|INPUT|IN\s*PUT|PORT|포트|방향)[^\n]{0,25}차단'
BLOCK_CAUSE = r'(Error|ERROR|Err|알람|Alarm|불량|고장)'
HUBERR_PAT = [
    r'(M16HUB|HUB|Bridge|BRIDGE)\s*측?\s*OHT\s*(Error|ERROR|Err)',
    r'OHT\s*(Error|ERROR|Err)\s*발생',
    r'OHT\s*고장',
]
MINOR_PAT = [r'(Error|ERROR|Err)\s*(발생|다발)', r'알람\s*발생', r'Alarm']
# 이슈가 아님 — 공지/완료/부정
DROP_PAT = [
    r'예정입니다', r'예정이오니', r'진행\s*예정', r'작업\s*일시', r'작업\s*시간', r'작업\s*내용',
    r'공유\s*드립니다', r'공유드립니다', r'참고\s*(바랍니다|부탁)', r'업무\s*참(조|고)',
    r'되었나요', r'일까요',
    r'알겠습니다', r'감사합니다', r'부탁드리겠습니다', r'넵',
    r'특이사항\s*(없|있는지)', r'이력\s*없', r'문제\s*없', r'영향(성)?\s*(은\s*)?(적|없)',
    r'조치\s*(완료|되었|하였)', r'처리\s*(완료|되었)', r'작업\s*(완료|종료)', r'원복',
    r'Clear', r'해소', r'정상화\s*(되었|하였)', r'Open\s*(했|하였|완료)',
    r'(지연|Delay)\s*(이\s*)?될\s*(꺼|거|것)',   # "지연 될꺼 같습니다" = 앞으로의 작업 지연 예고
    r'정체\s*(가\s*)?없', r'정체\s*(유발하지|나지)\s*않', r'정체\s*회피',  # "아직은 정체 없습니다"
    r'정체[가는]?\s*\S{0,6}면\s',                                     # "정체가 버티면 …" = 가정

    r'확인\s*해?\s*보?겠습니다', r'영향\s*(이\s*)?없는',                  # 답변·설명 메시지
    r'Rail\s*Cut\s*(해제|원복)',
]
# DROP 에 걸려도 이건 실제 발생 — 되살린다
ALIVE_PAT = (r'정체\s*(발생|중|되오|풀리|해소되면)|몰림|Rail\s*Cut\s*(실시|했)|'
             r'Delay\s*중|지연\s*(되어|발생)|밀려\s*영향|쌓이는')
# 바로 뒤 회신이 이러면 "이슈 아님" 쪽 근거 → 근거메시지에 같이 표기
DENY_PAT = r'특이사항\s*없|이력\s*없|문제\s*없|해당\s*없'


def parse_msgs(fp):
    """메신저 txt → [(시각, 작성자, 본문)] · 인용답변(┖)은 답변 부분만 사용."""
    txt = open(fp, encoding='utf-8', errors='replace').read()
    blocks = re.split(r'\n(?=[가-힣]{2,4},[^,\n]+,\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', txt)
    out = []
    for b in blocks:
        m = re.match(r'([가-힣]{2,4}),([^,\n]+),(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\n(.*)', b, re.S)
        if not m:
            continue
        # 사건단위가 분 단위라 초는 버린다 (10:32:20 vs 10:02 → 30.3분 이 되어 경계에서 탈락하는 것 방지)
        t = datetime.strptime(m.group(3), '%Y-%m-%d %H:%M:%S').replace(second=0)
        body = m.group(4)
        if '┖' in body:                      # 인용답변 → 답변만
            body = body.split('┖', 1)[1]
        body = ' '.join(body.split())
        if body:
            out.append((t, m.group(1), body))
    out.sort(key=lambda x: x[0])
    return out


def classify(body):
    """'core' (반송영향) / 'minor' (장비Error) / None (이슈 아님)"""
    if any(re.search(p, body) for p in DROP_PAT):
        # 완료·공지라도 '정체 발생/몰림/Rail Cut 실시' 같은 실발생 표현이 있으면 이슈로 본다
        if not re.search(ALIVE_PAT, body):
            return None
    if any(re.search(p, body) for p in CORE_PAT):
        return 'core'
    if any(re.search(p, body) for p in HUBERR_PAT):
        return 'core'
    if re.search(BLOCK_PAT, body) and re.search(BLOCK_CAUSE, body):
        return 'core'
    if any(re.search(p, body) for p in MINOR_PAT):
        return 'minor'
    return None


def find_deny(msgs, i, within=10):
    """i 번째 메시지 뒤에 붙은 '특이사항 없음' 류 회신 찾기 (다른 사람, within 분 내)."""
    t0, who0 = msgs[i][0], msgs[i][1]
    for t, who, body in msgs[i + 1:]:
        if (t - t0) > timedelta(minutes=within):
            break
        if who != who0 and re.search(DENY_PAT, body):
            return body
    return None


def build_issues(msgs, include_minor, merge_min):
    """이슈 메시지 → 연속된 것끼리 묶어 사건 목록으로."""
    picked = []
    for i, (t, who, body) in enumerate(msgs):
        k = classify(body)
        if k == 'core' or (include_minor and k == 'minor'):
            picked.append({'time': t, 'who': who, 'body': body, 'kind': k,
                           'deny': find_deny(msgs, i)})
    issues, cur = [], None
    for p in picked:
        if cur and (p['time'] - cur['end']) <= timedelta(minutes=merge_min):
            cur['end'] = p['time']
            cur['lines'].append(p)
        else:
            if cur:
                issues.append(cur)
            cur = {'start': p['time'], 'end': p['time'], 'lines': [p]}
    if cur:
        issues.append(cur)
    for it in issues:
        it['text'] = ' / '.join(x['body'][:60] for x in it['lines'][:3])
        deny = next((x['deny'] for x in it['lines'] if x['deny']), None)
        if deny and len(it['lines']) == 1:      # 단발 문의에 "없음" 회신이 달린 건만 표기
            it['text'] += f'  ※회신: {deny[:40]}'
        it['kind'] = 'core' if any(x['kind'] == 'core' for x in it['lines']) else 'minor'
    return issues


def repair_row(r, header):
    """따옴표가 유실된 행 복구.

    사건단위는 propagation_chain 안의 'M16A(10:27, RA+RB)' 쉼표 때문에만 칸이 밀린다.
    뒤쪽 4칸(triggered_rules·risk_factors·maxcapa_changes·relation)은 쉼표가 없어
    항상 그대로이므로, 14번째부터 뒤 4칸 전까지를 다시 이어붙이면 원형이 된다.
    """
    n = len(header)
    if len(r) <= n:
        return r + [''] * (n - len(r))
    try:
        ci = header.index('propagation_chain')
    except ValueError:
        return r[:n]
    tail = n - ci - 1                       # chain 뒤에 남는 칸 수 (=4)
    chain = r[ci:len(r) - tail]
    if not chain or not chain[-1].rstrip().endswith(')'):
        return r[:n]                        # 예상 모양이 아니면 손대지 않음
    return r[:ci] + [', '.join(chain)] + r[len(r) - tail:]


def read_events(fp):
    """사건단위 CSV → (헤더, 행들, 인덱스). 따옴표 유실 파일은 구조로 복구한다."""
    rows = list(csv.reader(open(fp, encoding='utf-8-sig')))
    if not rows:
        sys.exit(f'❌ 빈 파일: {fp}')
    header = rows[0]
    body = [r for r in rows[1:] if any(x.strip() for x in r)]
    drift = [r for r in body if len(r) != len(header)]
    if drift:
        print(f'  🩹 따옴표가 유실된 행 {len(drift)}건 → propagation_chain 을 다시 이어붙여 복구')
        body = [repair_row(r, header) for r in body]
        left = sum(1 for r in body if len(r) != len(header))
        if left:
            print(f'     ⚠️ {left}건은 모양이 달라 복구 못 함 (원본 CSV 를 다시 받는 게 좋음)')
    idx = {c: i for i, c in enumerate(header)}
    for need in ('date', 'start_time'):
        if need not in idx:
            sys.exit(f"❌ '{need}' 컬럼이 없습니다: {header[:8]}")
    return header, body, idx


def to_dt(d, hm):
    d, hm = (d or '').strip(), (hm or '').strip()
    if not d or not hm:
        return None
    try:
        y, mo, dd = [int(x) for x in d.replace('/', '-').split('-')]
        p = hm.split(':')
        return datetime(y, mo, dd, int(p[0]), int(p[1]))
    except (ValueError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', required=True, help='사건단위 CSV (합본)')
    ap.add_argument('--msg', required=True, help='메신저 대화 txt')
    ap.add_argument('-o', '--out', default=None, help='출력 CSV (기본: <입력>_탐지현황.csv)')
    ap.add_argument('--early', type=int, default=30, help='정탐 최대 선행 분 (기본 30)')
    ap.add_argument('--good', type=int, default=10, help='정탐 최소 선행 분 (기본 10)')
    ap.add_argument('--late', type=int, default=20, help='지연탐지 허용 분 (기본 20)')
    ap.add_argument('--merge-min', dest='merge_min', type=int, default=30,
                    help='메신저 이슈를 한 사건으로 묶는 간격 (기본 30분)')
    ap.add_argument('--include-minor', action='store_true',
                    help='반송영향 언급 없는 장비 Error 도 이슈로 취급')
    a = ap.parse_args()

    print('=' * 64)
    print('탐지현황 판정 — 사건단위 × 메신저')
    print('=' * 64)

    msgs = parse_msgs(a.msg)
    issues = build_issues(msgs, a.include_minor, a.merge_min)
    print(f'  [메신저] 메시지 {len(msgs)}건 → 이슈 {len(issues)}건'
          f' (핵심 {sum(1 for i in issues if i["kind"]=="core")}'
          f' / 장비 {sum(1 for i in issues if i["kind"]=="minor")})')

    header, rows, idx = read_events(a.events)
    print(f'  [사건단위] {len(rows)}건')

    width = max([len(header)] + [len(r) for r in rows])
    head_out = header + [f'열{i+1}' for i in range(len(header), width)]
    NEW = ['탐지현황', '시간차(분)', '근거메시지']

    used = set()
    out_rows, cnt = [], {'정탐': 0, '지연탐지': 0, '오탐': 0, '미탐': 0}
    for r in rows:
        r = r + [''] * (width - len(r))
        det = to_dt(r[idx['date']], r[idx['start_time']])
        verdict, gap, basis = '오탐', '', ''
        if det:
            best = None
            for k, it in enumerate(issues):
                # 이슈 시작 기준 매칭 (사건이 진행 중이면 그 구간도 허용)
                d0 = (it['start'] - det).total_seconds() / 60.0
                d1 = (it['end'] - det).total_seconds() / 60.0
                if -a.late <= d0 <= a.early or (d0 < 0 <= d1):
                    if best is None or abs(d0) < abs(best[1]):
                        best = (k, d0, it)
            if best:
                k, d0, it = best
                used.add(k)
                gap = f'{d0:+.0f}'
                basis = f"{it['start']:%m/%d %H:%M} {it['text'][:70]}"
                if d0 >= a.good:
                    verdict = '정탐'
                elif d0 >= 0:
                    verdict = '정탐'
                    basis = f'(선행 {d0:.0f}분) ' + basis
                else:
                    verdict = '지연탐지'
        cnt[verdict] += 1
        out_rows.append((det or datetime.max, r + [verdict, gap, basis]))

    # 미탐 — 어떤 탐지에도 매칭 안 된 이슈를 행으로 추가
    # (메신저 파일이 월 경계를 넘어가는 경우가 있어, 사건단위가 다루는 날짜 범위 안의 이슈만)
    dates = [d for d, _ in out_rows if d != datetime.max]
    d_lo = min(dates).replace(hour=0, minute=0) if dates else datetime.min
    d_hi = max(dates).replace(hour=23, minute=59) if dates else datetime.max
    out_of_range = 0
    for k, it in enumerate(issues):
        if k in used:
            continue
        if not (d_lo <= it['start'] <= d_hi):
            out_of_range += 1
            continue
        r = [''] * width
        def put(col, v):
            if col in idx:
                r[idx[col]] = v
        put('file', '(메신저)')
        put('date', it['start'].strftime('%Y-%m-%d'))
        put('start_time', it['start'].strftime('%H:%M'))
        put('end_time', it['end'].strftime('%H:%M'))
        put('duration_min', str(int((it['end'] - it['start']).total_seconds() / 60)))
        put('predicted_fault_type', '메신저 이슈' + ('' if it['kind'] == 'core' else '(장비)'))
        put('hot_area', '-')
        out_rows.append((it['start'], r + ['미탐', '', f"{it['start']:%m/%d %H:%M} {it['text'][:70]}"]))
        cnt['미탐'] += 1

    out_rows.sort(key=lambda x: x[0])
    out = a.out or (os.path.splitext(a.events)[0] + '_탐지현황.csv')
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(head_out + NEW)
        for _, r in out_rows:
            w.writerow(r)

    tot_det = len(rows)
    hit = cnt['정탐'] + cnt['지연탐지']
    print()
    print(f"  {'정탐':<6} {cnt['정탐']:>3}건   (이슈보다 {a.good}~{a.early}분 전 탐지)")
    print(f"  {'지연탐지':<5} {cnt['지연탐지']:>3}건   (이슈보다 1~{a.late}분 늦게 탐지)")
    print(f"  {'오탐':<6} {cnt['오탐']:>3}건   (매칭 이슈 없음)")
    print(f"  {'미탐':<6} {cnt['미탐']:>3}건   (메신저에만 있고 탐지 없음)")
    if out_of_range:
        print(f"         └ 사건단위 기간({d_lo:%m/%d}~{d_hi:%m/%d}) 밖 이슈 {out_of_range}건은 제외")
    print(f"  ─────────────────────────────")
    print(f"  탐지 {tot_det}건 중 적중 {hit}건 ({hit/max(tot_det,1)*100:.0f}%)"
          f" · 이슈 {len(issues)}건 중 잡은 것 {len(used)}건 ({len(used)/max(len(issues),1)*100:.0f}%)")

    # 오탐이 어느 유형에서 나오는지 — 튜닝 우선순위 판단용
    if 'predicted_fault_type' in idx:
        fp_kind = {}
        for _, r in out_rows:
            if r[len(head_out) + 0] == '오탐':
                k = r[idx['predicted_fault_type']] or '(없음)'
                fp_kind[k] = fp_kind.get(k, 0) + 1
        if fp_kind:
            print('\n  오탐 유형별:')
            for k, v in sorted(fp_kind.items(), key=lambda x: -x[1]):
                print(f'    · {k:<18} {v:>3}건')

    # 완전히 같은 행이 여러 번 있으면 알림 (합본 과정에서 중복됐을 수 있음)
    seen_key, dup = set(), 0
    for _, r in out_rows:
        k = (r[idx['date']], r[idx['start_time']], r[idx.get('end_time', 0)])
        if k in seen_key:
            dup += 1
        seen_key.add(k)
    if dup:
        print(f'\n  ℹ️ 날짜·시각이 똑같은 행 {dup}건 — 합본 때 중복 여부 확인 필요')

    print(f'\n💾 → {os.path.abspath(out)}')


if __name__ == '__main__':
    main()
