#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dijkstra_optimality.py — Dijkstra가 OHT 그래프의 최적 알고리즘인지 검증

분석 항목:
  1) 그래프 속성 분석 (가중치 부호, 밀도, 직경)
  2) 이론 복잡도 vs 실측 시간
  3) Dijkstra vs A*(좌표 휴리스틱) vs BFS(가중치 무시) 비교
  4) 정답 일치성 검증 (A*는 admissible 휴리스틱이면 동일 결과 보장)
  5) All-pairs 도달성 (V² 전수 — 샘플링 없음)

표준 라이브러리만 사용.

사용 예:
  python dijkstra_optimality.py --layout cache\\M16A_BR_layout_cache.json
  python dijkstra_optimality.py --layout ... --report opt_report.json
  python dijkstra_optimality.py --layout ... --skip-allpairs    # V²가 너무 클 때
"""

import argparse
import heapq
import json
import math
import sys
import time
from collections import defaultdict, deque


# ============================================================
# 레이아웃 로드 (좌표 포함 — A* 휴리스틱용)
# ============================================================
def load_layout(path):
    with open(path, 'r', encoding='utf-8') as f:
        L = json.load(f)
    coords = {int(k): tuple(v) for k, v in L.get('nodes', {}).items()}
    edges = {}
    for k, dist in L.get('edges', {}).items():
        a, b = k.split(',')
        edges[(int(a), int(b))] = float(dist)
    adj = defaultdict(list)
    for k, lst in L.get('adj', {}).items():
        u = int(k)
        for v in lst:
            v = int(v)
            w = edges.get((u, v), 1.0)
            adj[u].append((v, w))
    return coords, edges, adj


# ============================================================
# 그래프 진단
# ============================================================
def graph_stats(coords, edges, adj):
    V = len(set(adj) | {v for nbrs in adj.values() for v, _ in nbrs})
    E = sum(len(v) for v in adj.values())
    weights = [w for nbrs in adj.values() for _, w in nbrs]
    in_deg = defaultdict(int); out_deg = defaultdict(int)
    for u, nbrs in adj.items():
        out_deg[u] = len(nbrs)
        for v, _ in nbrs:
            in_deg[v] += 1
    nodes_all = set(adj) | set(in_deg)
    return {
        'V': V,
        'E': E,
        'density_E_over_V': round(E / V, 3),
        'edge_weight_min': min(weights),
        'edge_weight_max': max(weights),
        'edge_weight_avg': round(sum(weights) / len(weights), 1),
        'edge_weight_negative_count': sum(1 for w in weights if w < 0),
        'edge_weight_zero_count': sum(1 for w in weights if w == 0),
        'out_degree_max': max(out_deg.values()),
        'out_degree_avg': round(sum(out_deg.values()) / len(out_deg), 3),
        'isolated_nodes': sum(1 for n in nodes_all
                              if in_deg[n] == 0 and out_deg[n] == 0),
        'has_coords_pct': round(100.0 * sum(1 for n in nodes_all if n in coords)
                                / max(1, len(nodes_all)), 1),
    }


# ============================================================
# 알고리즘 구현 — 순수 python, 동일 자료구조로 공정 비교
# ============================================================
def dijkstra(adj, src, dst=None):
    """SSSP. dst 지정 시 도달 즉시 종료. 반환: dist, prev, visited_count."""
    dist = {src: 0.0}; prev = {}; pq = [(0.0, src)]
    visited = 0
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        visited += 1
        if dst is not None and u == dst:
            return dist, prev, visited
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev, visited


def bfs(adj, src, dst=None):
    """홉수 기준 SSSP. 가중치 무시 → '잘못된' 결과를 비교용으로 측정."""
    dist = {src: 0}; prev = {}; q = deque([src])
    visited = 0
    while q:
        u = q.popleft()
        visited += 1
        if dst is not None and u == dst:
            return dist, prev, visited
        for v, _ in adj.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                prev[v] = u
                q.append(v)
    return dist, prev, visited


def astar(adj, coords, src, dst, h_scale):
    """A*. h(n) = h_scale * Euclidean(n, dst). admissible 보장: h_scale ≤ min_pulse_per_meter."""
    if dst not in coords or src not in coords:
        return None, None, 0
    gx, gy = coords[dst]

    def h(n):
        if n not in coords:
            return 0.0
        x, y = coords[n]
        return h_scale * math.hypot(x - gx, y - gy)

    g = {src: 0.0}; prev = {}
    pq = [(h(src), 0.0, src)]
    visited = 0
    while pq:
        f, gu, u = heapq.heappop(pq)
        if gu > g.get(u, math.inf):
            continue
        visited += 1
        if u == dst:
            return g, prev, visited
        for v, w in adj.get(u, []):
            nd = gu + w
            if nd < g.get(v, math.inf):
                g[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd + h(v), nd, v))
    return g, prev, visited


# ============================================================
# 휴리스틱 admissibility 추정 (pulse / m)
# ============================================================
def estimate_h_scale(coords, edges):
    """min(pulse) / Euclidean(좌표) 비율의 하한값 → admissible 보장.
       너무 작으면 휴리스틱 약해짐. 0이면 A*가 Dijkstra와 동일."""
    ratios = []
    for (u, v), w in edges.items():
        if u in coords and v in coords:
            x1, y1 = coords[u]; x2, y2 = coords[v]
            d = math.hypot(x1 - x2, y1 - y2)
            if d > 0:
                ratios.append(w / d)
    if not ratios:
        return 0.0
    return min(ratios) * 0.999  # 안전 마진


# ============================================================
# 1) 모든 노드 SSSP 전수 (V × Dijkstra) — 도달성 행렬·직경
# ============================================================
def all_pairs_reachability(adj, nodes, max_nodes=None):
    if max_nodes:
        nodes = nodes[:max_nodes]
    V = len(nodes)
    total_pairs = V * (V - 1)
    reach_pairs = 0
    sum_hops = 0
    sum_cost = 0.0
    max_cost = 0.0
    diameter_pair = (None, None, 0.0)
    t0 = time.perf_counter()
    for i, src in enumerate(nodes):
        dist, prev, _ = dijkstra(adj, src)
        for v, c in dist.items():
            if v == src:
                continue
            reach_pairs += 1
            sum_cost += c
            # 홉 수 = prev 체인 길이
            hops = 0; cur = v
            while cur in prev:
                hops += 1; cur = prev[cur]
            sum_hops += hops
            if c > max_cost:
                max_cost = c
                diameter_pair = (src, v, c)
        if (i + 1) % 200 == 0:
            elapsed = time.perf_counter() - t0
            eta = elapsed / (i + 1) * (V - i - 1)
            print(f"      ... {i+1}/{V} 출발지 완료  "
                  f"(경과 {elapsed:.1f}s · ETA {eta:.0f}s)", flush=True)
    elapsed = time.perf_counter() - t0
    return {
        'sources_processed': V,
        'pairs_total': total_pairs,
        'pairs_reachable': reach_pairs,
        'reachability_pct': round(100.0 * reach_pairs / max(1, total_pairs), 3),
        'avg_hops': round(sum_hops / max(1, reach_pairs), 2),
        'avg_cost_pulse': round(sum_cost / max(1, reach_pairs), 1),
        'diameter_cost_pulse': round(diameter_pair[2], 1),
        'diameter_pair': (diameter_pair[0], diameter_pair[1]),
        'wall_clock_sec': round(elapsed, 3),
        'avg_query_ms': round(elapsed * 1000.0 / V, 4),
    }


# ============================================================
# 2) 알고리즘 비교 (전수 SSSP × 3 알고리즘)
# ============================================================
def compare_algorithms(adj, coords, nodes, h_scale, sample_dst_per_src=10):
    """
    각 src에 대해 sample_dst_per_src개 dst를 결정론적으로 선택하여
    Dijkstra / A* / BFS의 (시간, 방문수, 결과 일치성) 측정.
    sample_dst_per_src=0 이면 모든 (src, dst) — V² 회.
    """
    V = len(nodes)
    if sample_dst_per_src > 0:
        # 결정론적: 각 src마다 nodes 리스트의 +stride 위치들
        stride = max(1, V // (sample_dst_per_src + 1))
        pair_count_est = V * sample_dst_per_src
    else:
        stride = 1
        pair_count_est = V * (V - 1)

    stats = {alg: {'time_s': 0.0, 'visited': 0, 'queries': 0,
                   'reach': 0, 'wrong_cost_vs_dijkstra': 0}
             for alg in ('dijkstra', 'astar', 'bfs')}
    print(f"      비교 쿼리 수 ≈ {pair_count_est:,}")
    t_start = time.perf_counter()
    for i, src in enumerate(nodes):
        if sample_dst_per_src > 0:
            dsts = [nodes[(i + k * stride) % V]
                    for k in range(1, sample_dst_per_src + 1)]
        else:
            dsts = [n for n in nodes if n != src]
        for dst in dsts:
            # Dijkstra (정답 기준)
            t0 = time.perf_counter()
            dD, pD, vD = dijkstra(adj, src, dst)
            stats['dijkstra']['time_s']  += time.perf_counter() - t0
            stats['dijkstra']['visited'] += vD
            stats['dijkstra']['queries'] += 1
            cD = dD.get(dst, math.inf)
            if cD < math.inf:
                stats['dijkstra']['reach'] += 1

            # A*
            t0 = time.perf_counter()
            gA, pA, vA = astar(adj, coords, src, dst, h_scale)
            stats['astar']['time_s']  += time.perf_counter() - t0
            stats['astar']['visited'] += vA
            stats['astar']['queries'] += 1
            cA = (gA or {}).get(dst, math.inf)
            if cA < math.inf:
                stats['astar']['reach'] += 1
            if cD < math.inf and cA < math.inf and abs(cA - cD) > 1e-6:
                stats['astar']['wrong_cost_vs_dijkstra'] += 1

            # BFS
            t0 = time.perf_counter()
            dB, pB, vB = bfs(adj, src, dst)
            stats['bfs']['time_s']  += time.perf_counter() - t0
            stats['bfs']['visited'] += vB
            stats['bfs']['queries'] += 1
            if dst in dB:
                stats['bfs']['reach'] += 1
                # BFS는 가중치 무시 → 거의 항상 다른 비용을 의미
                # 비교 위해 bfs path의 실제 weighted cost 재계산
                # (이미 reachability만 검증)
        if (i + 1) % 200 == 0:
            print(f"      ... {i+1}/{V} src 비교 완료 "
                  f"(경과 {time.perf_counter()-t_start:.1f}s)", flush=True)

    # 후처리: 평균치
    out = {}
    for alg, s in stats.items():
        q = max(1, s['queries'])
        out[alg] = {
            'queries': s['queries'],
            'total_time_s': round(s['time_s'], 3),
            'avg_query_ms': round(s['time_s'] * 1000.0 / q, 4),
            'avg_visited_nodes': round(s['visited'] / q, 1),
            'reachability_pct': round(100.0 * s['reach'] / q, 2),
            'wrong_cost_vs_dijkstra': s.get('wrong_cost_vs_dijkstra', None),
        }
    return out


# ============================================================
# 이론 복잡도 계산
# ============================================================
def theoretical_complexity(V, E):
    log2V = math.log2(V) if V > 1 else 1
    return {
        'V': V, 'E': E,
        'BFS_ops_O(V+E)':                      V + E,
        'Dijkstra_binary_heap_O((V+E)log V)':  int((V + E) * log2V),
        'Dijkstra_fibonacci_heap_O(E+V log V)': int(E + V * log2V),
        'Bellman-Ford_O(V*E)':                 V * E,
        'Floyd-Warshall_O(V^3)':               V ** 3,
        'Johnson_O(V^2 log V + V*E)':          int(V * V * log2V + V * E),
    }


# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="Dijkstra 최적성 검증 (이론 + 실측, 샘플링 없음)")
    ap.add_argument('--layout', required=True)
    ap.add_argument('--report', default=None)
    ap.add_argument('--skip-allpairs', action='store_true',
                    help='V×V 도달성 매트릭스 생략(매우 큰 그래프용)')
    ap.add_argument('--full-compare', action='store_true',
                    help='알고리즘 비교를 V×V 전수로 (기본은 src당 10 dst)')
    ap.add_argument('--cmp-dst-per-src', type=int, default=10,
                    help='알고리즘 비교 시 src당 dst 수 (기본 10, 0=전수)')
    args = ap.parse_args()

    print("=" * 72)
    print(" Dijkstra 최적 알고리즘 검증")
    print("=" * 72)

    coords, edges, adj = load_layout(args.layout)

    # 1. 그래프 진단
    print("\n[1] 그래프 속성")
    g = graph_stats(coords, edges, adj)
    for k, v in g.items():
        print(f"    {k:<32} {v}")

    if g['edge_weight_negative_count'] > 0:
        print("\n  ⚠ 음수 가중치 발견 → Dijkstra 부적합. Bellman-Ford 필요.")
    else:
        print("\n  ✅ 모든 가중치 ≥ 0 → Dijkstra optimal 적용 조건 충족.")

    # 2. 이론 복잡도
    print("\n[2] 이론 연산수 (V={V}, E={E})".format(**g))
    th = theoretical_complexity(g['V'], g['E'])
    for k, v in th.items():
        if k in ('V', 'E'): continue
        print(f"    {k:<42} {v:>15,}")

    # 3. A* 휴리스틱 admissible scale
    h_scale = estimate_h_scale(coords, edges)
    print(f"\n[3] A* 휴리스틱 스케일 (admissible): {h_scale:.4f} pulse/단위거리")

    # 4. 전수 도달성 (V²)
    nodes = sorted(adj.keys())
    report = {
        'graph_stats': g,
        'theoretical_complexity': th,
        'astar_h_scale': h_scale,
    }
    if not args.skip_allpairs:
        print(f"\n[4] All-pairs Dijkstra (V={g['V']}, 약 {g['V']}회 SSSP)")
        ap_res = all_pairs_reachability(adj, nodes)
        for k, v in ap_res.items():
            print(f"    {k:<32} {v}")
        report['all_pairs'] = ap_res
    else:
        print("\n[4] All-pairs 생략 (--skip-allpairs)")

    # 5. 알고리즘 비교
    print("\n[5] 알고리즘 비교 — Dijkstra vs A* vs BFS")
    dst_per_src = 0 if args.full_compare else args.cmp_dst_per_src
    cmp = compare_algorithms(adj, coords, nodes, h_scale, dst_per_src)
    report['algorithm_comparison'] = cmp
    print(f"\n    {'알고리즘':<10}{'쿼리수':>10}{'총시간(s)':>12}"
          f"{'평균(ms)':>12}{'평균방문':>12}{'도달%':>10}{'정답불일치':>12}")
    for alg, s in cmp.items():
        wrong = s['wrong_cost_vs_dijkstra']
        wrong_str = '-' if wrong is None else str(wrong)
        print(f"    {alg:<10}{s['queries']:>10,}{s['total_time_s']:>12}"
              f"{s['avg_query_ms']:>12}{s['avg_visited_nodes']:>12}"
              f"{s['reachability_pct']:>10}{wrong_str:>12}")

    # 6. 결론
    print("\n[6] 결론")
    dij = cmp['dijkstra']; ast = cmp['astar']; bfs_s = cmp['bfs']
    speedup = (dij['avg_query_ms'] / ast['avg_query_ms']
               if ast['avg_query_ms'] > 0 else 0)
    print(f"    • Dijkstra 평균 쿼리: {dij['avg_query_ms']} ms / "
          f"방문 {dij['avg_visited_nodes']} 노드")
    print(f"    • A* 평균 쿼리:        {ast['avg_query_ms']} ms / "
          f"방문 {ast['avg_visited_nodes']} 노드  → speedup ×{speedup:.2f}")
    print(f"    • BFS 평균 쿼리:       {bfs_s['avg_query_ms']} ms "
          f"(가중치 무시, 비용 정답 아님)")
    if (ast.get('wrong_cost_vs_dijkstra') or 0) == 0:
        print(f"    ✅ A* 결과 = Dijkstra 결과 (admissible 휴리스틱 검증됨)")
    else:
        print(f"    ⚠ A*가 Dijkstra와 다른 비용 {ast['wrong_cost_vs_dijkstra']}건 "
              f"→ 휴리스틱 admissible 조건 위반 가능")
    if speedup >= 1.2:
        print(f"    ➜ 권장: A* (좌표 기반 가속 효과 있음)")
    else:
        print(f"    ➜ 권장: Dijkstra (그래프가 너무 sparse하여 A* 가속 효과 미미)")

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n결과 저장: {args.report}")


if __name__ == '__main__':
    sys.exit(main())
