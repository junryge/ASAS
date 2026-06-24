#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하루치 데이터 한 번에 처리 — 발동이벤트 24h + 위험사건 그래프 + (옵션) 원본 raw

사용:
  python 일괄생성.py <YYYYMMDD> [--in <발동이벤트폴더>] [--raw <raw_CSV>] [-o <출력폴더>] [-l <최소등급>]

예:
  python 일괄생성.py 20260525
  python 일괄생성.py 20260609 --raw ../20260609DATA/M16A_HUBROOM_PR.CSV
"""
import os
import sys
import glob
import subprocess

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    day = sys.argv[1]
    in_dir = '../predict_tobe'
    out_dir = './out_그래프'
    min_lv = '주의'
    raw_path = None
    for i, a in enumerate(sys.argv):
        if a == '--in' and i+1 < len(sys.argv): in_dir = sys.argv[i+1]
        if a == '--raw' and i+1 < len(sys.argv): raw_path = sys.argv[i+1]
        if a == '-o' and i+1 < len(sys.argv): out_dir = sys.argv[i+1]
        if a == '-l' and i+1 < len(sys.argv): min_lv = sys.argv[i+1]
    os.makedirs(out_dir, exist_ok=True)

    here = os.path.dirname(os.path.abspath(__file__))
    evt = os.path.join(in_dir, f'{day}_발동이벤트.csv')
    inc = os.path.join(in_dir, f'{day}_사건단위.csv')

    if not os.path.exists(evt):
        print(f"❌ 발동이벤트 없음: {evt}"); return
    print(f"📂 발동이벤트: {evt}")
    if os.path.exists(inc):
        print(f"📂 사건단위:   {inc}")
    if raw_path and os.path.exists(raw_path):
        print(f"📂 raw 원본:   {raw_path}")
    print(f"📂 출력:       {out_dir}\n")

    # ① 발동이벤트 24h
    print("=" * 50 + "\n① 발동이벤트 24h (CSV 축약값 + raw 라벨)\n" + "=" * 50)
    subprocess.run([sys.executable, os.path.join(here, '발동이벤트_24h.py'),
                    evt, '-o', out_dir])

    # ② 위험사건 그래프
    if os.path.exists(inc):
        print("\n" + "=" * 50 + f"\n② 위험사건 그래프 (≥{min_lv})\n" + "=" * 50)
        subprocess.run([sys.executable, os.path.join(here, '위험사건_그래프.py'),
                        inc, evt, '-o', out_dir, '-l', min_lv])

    # ③ 원본 raw 그래프 (옵션)
    if raw_path and os.path.exists(raw_path):
        print("\n" + "=" * 50 + "\n③ 원본 raw 그래프 (raw CSV 풀네임 컬럼 직접)\n" + "=" * 50)
        subprocess.run([sys.executable, os.path.join(here, '원본컬럼_그래프.py'),
                        raw_path, evt, '-o', out_dir])

    print(f"\n🎉 완료 — {out_dir}/")
    for f in sorted(glob.glob(os.path.join(out_dir, '*.svg'))):
        print(f"   {os.path.basename(f)}")


if __name__ == '__main__':
    main()
