#!/usr/bin/env python3
"""
COL_SPLIT_40 → 단일 CSV 머지
사용법:
  python3 merge_split40.py [입력디렉토리=D:/data] [출력=ALL_MERGED.csv]

동작:
  각 월별로 8개 영역 CSV를 CRT_TM 기준 가로 join
  → 월별 CSV 5개 (또는 옵션으로 전체 1개)
"""
import csv, sys
from pathlib import Path
from collections import OrderedDict

AREAS = ['M16HUB','M14','M14B','M16A','M16B','M16','M16_PKT','M16_WT']
MONTHS = ['202601','202602','202603','202604','202605']

def load_csv(path):
    """CSV 로드: dict {CRT_TM: {col: val}}, 헤더 목록 반환"""
    with open(path, 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        hdr = next(rdr)
        crt_idx = hdr.index('CRT_TM')
        cols = [c for i, c in enumerate(hdr) if i != crt_idx]
        data = OrderedDict()
        for row in rdr:
            t = row[crt_idx]
            data[t] = {hdr[i]: row[i] for i in range(len(hdr)) if i != crt_idx}
    return data, cols

def main():
    in_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('D:/data')
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('ALL_MERGED.csv')

    # 월별 머지
    monthly = {}
    for ym in MONTHS:
        merged = OrderedDict()   # {time: row_dict}
        all_cols = ['CRT_TM']
        for area in AREAS:
            fn = in_dir / f'IDC_{area}_{ym}.csv'
            if not fn.exists():
                print(f"  ⚠ 누락: {fn}")
                continue
            data, cols = load_csv(fn)
            all_cols.extend(cols)
            for t, vals in data.items():
                if t not in merged:
                    merged[t] = {'CRT_TM': t}
                merged[t].update(vals)
        monthly[ym] = (all_cols, merged)
        print(f"  {ym}: {len(merged)}행, {len(all_cols)-1}컬럼")

    # 통합 출력 (시간순 정렬)
    final_cols = ['CRT_TM']
    for ym in MONTHS:
        if ym in monthly:
            for c in monthly[ym][0]:
                if c != 'CRT_TM' and c not in final_cols:
                    final_cols.append(c)

    all_rows = OrderedDict()
    for ym in MONTHS:
        if ym not in monthly: continue
        _, merged = monthly[ym]
        for t in sorted(merged.keys()):
            all_rows[t] = merged[t]

    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(final_cols)
        for t in sorted(all_rows.keys()):
            row_dict = all_rows[t]
            w.writerow([row_dict.get(c, '') for c in final_cols])
    print(f"\n✅ 머지 완료: {out_path}  ({len(all_rows)}행, {len(final_cols)}컬럼)")

if __name__ == '__main__':
    main()
