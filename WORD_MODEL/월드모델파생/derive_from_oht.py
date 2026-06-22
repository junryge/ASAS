#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
derive_from_oht.py — 월드모델 파생 분석기 (입력: 맵 + OHT CSV 1개)

WORLD_SIM의 Dijkstra/LineCost 엔진을 활용해, OHT 데이터 1개 CSV 스냅샷으로부터
다음 산출물을 derive 한다:

  ① 차량별 현재 → DESTINATION 최단경로 + ETA
  ② 엣지별 혼잡도(차량 밀도) 핫스팟 Top-N
  ③ 동일 엣지 다중 점유 = 블로킹 위험 차량 그룹
  ④ DESTINATION 도달 가능성 (맵 매칭 결과)

입력은 두 가지만:
  - layout_cache.json (그래프)
  - OHT CSV 1개 (parsed 포맷: ADDRESS/NEXT_ADDRESS/STATUS/VEHICLE/DESTINATION 컬럼)

사용 예 (Windows):
  python derive_from_oht.py ^
      --layout ..\\OHT_MAP\\cache\\M16A_BR_layout_cache.json ^
      --oht    sample.csv ^
      --topn   20 ^
      --report derived.json
"""

import argparse
import csv
import heapq
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


# LineCost 가중치 (WORLD_SIM/config.py 와 동일)
W_IDLE = 3000
W_BUSY = 5000
PULSE_PER_SECOND = 89614


# ============================================================
# 레이아웃 로드
# ============================================================
def load_layout(path):
    L = json.load(open(path, encoding='utf-8'))
    coords = {int(k): tuple(v) for k, v in L.get('nodes', {}).items()}
    edges = {}
    for k, d in L.get('edges', {}).items():
        a, b = k.split(',')
        edges[(int(a), int(b))] = float(d)
    adj_static = defaultdict(list)
    for k, lst in L.get('adj', {}).items():
        adj_static[int(k)] = [int(x) for x in lst]
    return coords, edges, adj_static


# ============================================================
# OHT CSV 1패스 — 차량 스냅샷 + 엣지 점유 카운트
# ============================================================
def load_oht_snapshot(path):
    rows_total = 0
    skipped = 0
    snapshot = {}   # vid -> 최신 행
    idle = Counter()
    busy = Counter()
    edge_vehicles = defaultdict(list)
    status_hist = Counter()
    invalid_status = 0

    with open(path, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for r in reader:
            rows_total += 1
            try:
                a = int(r.get('ADDRESS', '') or 0)
                n = int(r.get('NEXT_ADDRESS', '') or 0)
            except ValueError:
                skipped += 1
                continue
            if a == 0 or n == 0 or a == n:
                skipped += 1
                continue

            vid = (r.get('VEHICLE') or '').strip()
            st = (r.get('STATUS') or '').strip()
            dest_raw = (r.get('DESTINATION') or '').strip()
            t = r.get('_time', '')

            # STATUS는 숫자여야 함 (샘플에 일부 포트명이 섞여 들어옴 → 파싱 밀림)
            try:
                st_int = int(st)
                status_hist[st_int] += 1
            except ValueError:
                invalid_status += 1
                # 유효하지 않은 행도 위치 자체는 사용 가능 — busy로 분류
                st_int = -1
                status_hist[-1] += 1

            if st_int == 0:
                idle[(a, n)] += 1
            else:
                busy[(a, n)] += 1

            edge_vehicles[(a, n)].append(vid)

            if vid:
                # 최신 시간만 유지
                prev = snapshot.get(vid)
                if prev is None or t > prev['_time']:
                    snapshot[vid] = {
                        '_time': t,
                        'ADDRESS': a, 'NEXT_ADDRESS': n,
                        'STATUS': st_int,
                        'DESTINATION': dest_raw,
                        'CARRIER': (r.get('CARRIER') or '').strip(),
                        'DISTANCE': r.get('DISTANCE', '') or '0',
                    }
    stats = {
        'rows_total': rows_total,
        'rows_skipped': skipped,
        'rows_invalid_status': invalid_status,
        'unique_vehicles': len(snapshot),
        'unique_edges_with_traffic': len(set(idle) | set(busy)),
        'status_histogram': dict(status_hist.most_common()),
        'columns': cols,
    }
    return snapshot, idle, busy, edge_vehicles, stats


# ============================================================
# LineCost 그래프 빌드
# ============================================================
def build_linecost(adj_static, edges, idle, busy):
    g = defaultdict(list)
    for u, lst in adj_static.items():
        for v in lst:
            d = edges.get((u, v), 1.0)
            cost = max(d, 1.0) + idle[(u, v)] * W_IDLE + busy[(u, v)] * W_BUSY
            g[u].append((v, cost))
    return g


# ============================================================
# Dijkstra
# ============================================================
def dijkstra(g, src, dst):
    if src == dst:
        return 0.0, [src]
    dist = {src: 0.0}; prev = {}; pq = [(0.0, src)]
    while pq:
        c, u = heapq.heappop(pq)
        if c > dist.get(u, math.inf): continue
        if u == dst: break
        for v, w in g.get(u, []):
            nd = c + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd; prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in dist:
        return None, []
    path = [dst]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return dist[dst], path


# ============================================================
# ① 차량별 경로 예측
# ============================================================
def derive_vehicle_paths(snapshot, node_ids, g):
    rows = []
    unreachable_dest_not_in_map = 0
    unreachable_no_path = 0
    for vid, v in snapshot.items():
        a = v['ADDRESS']
        dest_raw = v['DESTINATION']
        try:
            dest = int(dest_raw)
        except ValueError:
            dest = None

        rec = {
            'vehicle': vid,
            'carrier': v['CARRIER'],
            'address': a,
            'next_address': v['NEXT_ADDRESS'],
            'status': v['STATUS'],
            'destination_raw': dest_raw,
            'dest_in_map': bool(dest and dest in node_ids),
            'path_cost_pulse': None,
            'eta_sec': None,
            'hops': None,
            'path_head': [],
            'reachable': False,
        }
        if dest is None or dest not in node_ids:
            unreachable_dest_not_in_map += 1
            rows.append(rec)
            continue

        t0 = time.perf_counter()
        cost, path = dijkstra(g, a, dest)
        ms = (time.perf_counter() - t0) * 1000
        if cost is None:
            unreachable_no_path += 1
            rec['query_ms'] = round(ms, 3)
            rows.append(rec)
            continue
        rec.update({
            'reachable': True,
            'path_cost_pulse': round(cost, 1),
            'eta_sec': round(cost / PULSE_PER_SECOND, 2),
            'hops': len(path),
            'path_head': path[:10],
            'query_ms': round(ms, 3),
        })
        rows.append(rec)
    return rows, unreachable_dest_not_in_map, unreachable_no_path


# ============================================================
# ② 엣지별 혼잡도 핫스팟
# ============================================================
def derive_congestion(idle, busy, edges, topn=20):
    rows = []
    for e in set(idle) | set(busy):
        cnt = idle[e] + busy[e]
        d = edges.get(e, 0)
        rows.append({
            'edge': f"{e[0]}→{e[1]}",
            'vehicle_count': cnt,
            'idle': idle[e],
            'busy': busy[e],
            'distance_pulse': d,
            'linecost': round(max(d, 1) + idle[e]*W_IDLE + busy[e]*W_BUSY, 1),
        })
    rows.sort(key=lambda r: r['vehicle_count'], reverse=True)
    return rows[:topn]


# ============================================================
# ③ 블로킹 위험 그룹 (동일 엣지에 ≥2대)
# ============================================================
def derive_blocking_groups(edge_vehicles):
    groups = []
    for e, vids in edge_vehicles.items():
        # 중복 제거 + 다중 점유만
        uniq = list(dict.fromkeys(vids))
        if len(uniq) >= 2:
            groups.append({
                'edge': f"{e[0]}→{e[1]}",
                'vehicle_count': len(uniq),
                'vehicles': uniq,
            })
    groups.sort(key=lambda g: g['vehicle_count'], reverse=True)
    return groups


def resolve_oht_path(p):
    """경로가 폴더면 그 안의 CSV 1개를 자동 선택. 파일이면 그대로."""
    path = Path(p)
    if path.is_file():
        return str(path)
    if path.is_dir():
        csvs = sorted(list(path.glob('*.csv')) + list(path.glob('*.CSV')))
        if not csvs:
            raise FileNotFoundError(f"{path} 안에 CSV가 없습니다")
        if len(csvs) > 1:
            print(f"  ⚠ {path} 안에 CSV {len(csvs)}개 — 첫 번째 사용: {csvs[0].name}")
        return str(csvs[0])
    raise FileNotFoundError(f"경로 없음: {p}")


# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="월드모델 파생 분석 — 맵 + OHT CSV 1개만 사용")
    ap.add_argument('--layout', required=True, help='layout_cache.json')
    ap.add_argument('--oht',    required=True,
                    help='OHT CSV 파일 또는 CSV가 들어있는 폴더 (예: M16A_BR_DATA)')
    ap.add_argument('--topn',   type=int, default=20, help='혼잡 핫스팟 상위 N')
    ap.add_argument('--report', default=None, help='JSON 결과 저장 경로')
    args = ap.parse_args()

    print("=" * 70)
    print(" 월드모델 파생 분석기 (layout + OHT CSV 1개)")
    print("=" * 70)

    # 0. 입력 경로 정리 (폴더면 안의 CSV 자동 선택)
    oht_path = resolve_oht_path(args.oht)
    print(f"\n[0] 입력 CSV: {oht_path}")

    # 1. 맵
    coords, edges, adj_static = load_layout(args.layout)
    node_ids = set(adj_static.keys()) | {v for nbrs in adj_static.values() for v in nbrs}
    print(f"\n[1] 맵: nodes={len(node_ids):,}  edges={len(edges):,}")

    # 2. OHT 스냅샷
    print(f"\n[2] OHT CSV 로드")
    snapshot, idle, busy, edge_vehicles, stats = load_oht_snapshot(args.oht)
    print(f"    rows={stats['rows_total']:,}  유효 차량={stats['unique_vehicles']:,}")
    print(f"    트래픽 엣지={stats['unique_edges_with_traffic']:,}  "
          f"이상 STATUS={stats['rows_invalid_status']}")
    print(f"    STATUS hist: {stats['status_histogram']}")

    # 3. LineCost 그래프
    g = build_linecost(adj_static, edges, idle, busy)
    print(f"\n[3] LineCost 그래프 빌드 완료 (idle×{W_IDLE} + busy×{W_BUSY})")

    # ① 차량 경로 derive
    print(f"\n[4] 차량별 경로 예측 (Dijkstra)")
    vrows, no_map_dest, no_path = derive_vehicle_paths(snapshot, node_ids, g)
    reachable = sum(1 for r in vrows if r['reachable'])
    print(f"    분석 차량 {len(vrows)}대 →  도달 OK {reachable}대  "
          f"맵외 DEST {no_map_dest}  경로없음 {no_path}")
    print(f"\n    [상위 5대 예측 경로]")
    print(f"    {'VEHICLE':<8}{'POS':>6}→{'DEST':>5}  {'홉':>4}{'pulse':>10}{'ETA(s)':>8}  PATH 처음...")
    for r in sorted([x for x in vrows if x['reachable']],
                    key=lambda x: x['eta_sec'], reverse=True)[:5]:
        path_str = '→'.join(str(x) for x in r['path_head'][:6]) + (' ...' if r['hops'] > 6 else '')
        print(f"    {r['vehicle']:<8}{r['address']:>6} {r['destination_raw']:>5}  "
              f"{r['hops']:>4}{r['path_cost_pulse']:>10.0f}{r['eta_sec']:>8.1f}  {path_str}")

    # ② 혼잡도
    print(f"\n[5] 혼잡 엣지 Top-{args.topn}")
    hot = derive_congestion(idle, busy, edges, args.topn)
    print(f"    {'edge':<15}{'차량':>5}{'idle':>5}{'busy':>5}{'dist':>8}{'LineCost':>12}")
    for r in hot[:args.topn]:
        print(f"    {r['edge']:<15}{r['vehicle_count']:>5}{r['idle']:>5}{r['busy']:>5}"
              f"{r['distance_pulse']:>8.0f}{r['linecost']:>12.0f}")

    # ③ 블로킹 위험
    groups = derive_blocking_groups(edge_vehicles)
    print(f"\n[6] 동일 엣지 다중 점유 그룹: {len(groups)}건")
    for g_ in groups[:10]:
        print(f"    {g_['edge']:<15} {g_['vehicle_count']}대  {g_['vehicles']}")

    # ④ JSON 저장
    if args.report:
        out = {
            'map_stats': {'nodes': len(node_ids), 'edges': len(edges)},
            'oht_stats': stats,
            'vehicles': vrows,
            'reachability_summary': {
                'total': len(vrows),
                'reachable': reachable,
                'dest_not_in_map': no_map_dest,
                'no_path': no_path,
            },
            'congestion_topN': hot,
            'blocking_groups': groups,
        }
        Path(args.report).write_text(
            json.dumps(out, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8')
        print(f"\n[7] 결과 저장: {args.report}")

    print("\n완료.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
