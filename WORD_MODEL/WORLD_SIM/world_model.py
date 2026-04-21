#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
world_model.py - OHT 월드모델 엔진

그래프 기반 차량 시뮬레이션 + Tarjan SCC 데드락 탐지.
deadlock_predictor.py를 기반으로 재구성.
"""

import heapq
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Callable

from config import (
    DEFAULT_VELOCITY, SIM_STEP_SEC, PREDICTION_HORIZONS,
    LINECOST_IDLE_VHL_PENALTY, LINECOST_WORK_VHL_PENALTY,
    EMA_OLD_WEIGHT, EMA_NEW_WEIGHT,
    HID_CONGESTION_THRESHOLD_PCT,
)
from velocity_tracker import VelocityTracker


# ============================================================
# 데이터 구조
# ============================================================

@dataclass
class PredVehicle:
    """예측용 경량 차량 객체"""
    vid: str
    currentNode: int
    nextNode: int
    ratio: float            # 엣지 위 위치 (0.0 ~ 1.0)
    velocity: Optional[float]  # m/min (0=정지, None=측정 불가)
    destination: int
    state: int              # 1=RUN, 2=STOP, 7=JAM
    isFull: int = 0
    path: List[int] = field(default_factory=list)
    pathIndex: int = 0
    stoppedTicks: int = 0
    blockedBy: str = ""


@dataclass
class DeadlockGroup:
    """탐지된 데드락 그룹"""
    groupId: str
    dlType: str             # "CIRCULAR_WAIT" | "ZONE_DEADLOCK"
    vehicles: List[str]
    edges: List[Tuple[int, int]]
    zoneId: Optional[int]
    detectedAtStep: int
    detectedAtMinute: float
    severity: str           # "HIGH" | "MEDIUM" | "LOW"


# ============================================================
# Tarjan SCC 알고리즘
# ============================================================

def tarjan_scc(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Tarjan SCC — 크기 >= 2인 SCC만 반환 (순환 대기 = 데드락)"""
    index_counter = [0]
    stack = []
    on_stack = set()
    index_map = {}
    lowlink = {}
    result = []

    def strongconnect(v):
        index_map[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, []):
            if w not in index_map:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index_map[w])

        if lowlink[v] == index_map[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            if len(component) >= 2:
                result.append(component)

    for v in graph:
        if v not in index_map:
            strongconnect(v)

    return result


# ============================================================
# Dijkstra 경로 탐색
# ============================================================

def dijkstra_path(
    adj: Dict[int, List[Tuple[int, float]]],
    start: int,
    end: int,
) -> List[int]:
    """Dijkstra 최단 경로"""
    if start == end or start not in adj:
        return []
    dist_map = {start: 0}
    prev = {}
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == end:
            break
        if d > dist_map.get(u, float('inf')):
            continue
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist_map.get(v, float('inf')):
                dist_map[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if end not in prev:
        return []
    path = []
    curr = end
    while curr in prev:
        path.append(curr)
        curr = prev[curr]
    path.append(start)
    path.reverse()
    return path


# ============================================================
# WorldModel - 시뮬레이션 엔진
# ============================================================

STOPPED_THRESHOLD = 2  # 연속 정지 틱 수 (5초×2=10초)


class WorldModel:
    """결정론적 전방 시뮬레이터"""

    def __init__(
        self,
        graph: Dict[int, List[Tuple[int, float]]],
        edge_dist_map: Dict[Tuple[int, int], float],
        zone_data: Dict[int, dict] = None,
        in_lane_to_zone: Dict[Tuple[int, int], int] = None,
        out_lane_to_zone: Dict[Tuple[int, int], int] = None,
    ):
        self.graph = graph
        self.edge_dist_map = edge_dist_map
        self.in_lane_to_zone = in_lane_to_zone or {}
        self.out_lane_to_zone = out_lane_to_zone or {}

        # Zone 상태
        self.zone_capacity: Dict[int, int] = {}
        self.zone_count: Dict[int, int] = {}
        self.zone_vehicles: Dict[int, Set[str]] = defaultdict(set)
        if zone_data:
            for zid, zinfo in zone_data.items():
                self.zone_capacity[zid] = zinfo.get('vehicleMax', 37)
                self.zone_count[zid] = zinfo.get('currentCount', 0)

        # 차량 저장소
        self.vehicles: Dict[str, PredVehicle] = {}
        self.edge_vehicles: Dict[Tuple[int, int], List[str]] = defaultdict(list)
        self.vehicle_zone: Dict[str, int] = {}

        # UDP 위치 변화 기반 차량별 순간 속도 트래커 (m/min)
        # adj_map 전달 → 불연속 발생 시 BFS 경로 추정 가능
        # graph 형식: Dict[node, [(neighbor, weight), ...]] → 이웃만 추출
        adj_map = {n: [nb for nb, _ in nbrs] for n, nbrs in graph.items()} if graph else {}
        self.velocity_tracker = VelocityTracker(self.edge_dist_map, adj_map)

        self.current_step = 0
        self.detected_deadlocks: List[DeadlockGroup] = []
        self._deadlock_counter = 0

    def load_vehicles_from_frame(self, vehicle_list: List[dict], frame_time: Optional[datetime] = None):
        """CSV 프레임의 차량 데이터로 상태 설정.

        frame_time이 주어지면 VelocityTracker로 차량별 순간 속도를 계산.
        없으면 state 기반 fallback (DEFAULT_VELOCITY/0).
        """
        self.vehicles.clear()
        self.edge_vehicles.clear()

        for vdata in vehicle_list:
            vid = vdata.get('vid', '')
            if not vid:
                continue

            current_node = vdata.get('currentNode', 0)
            next_node = vdata.get('nextNode', 0)
            if current_node == 0 or next_node == 0:
                continue

            state = vdata.get('state', 1)
            distance = vdata.get('distance', 0)

            edge_key = (current_node, next_node)
            edge_dist = self.edge_dist_map.get(edge_key, 1.0)
            ratio = min(1.0, distance / edge_dist) if edge_dist > 0 else 0.0

            # UDP 위치 변화 기반 실제 속도 계산 (m/min)
            # 차량별 실 UDP 도착 시각(_time) 우선, 없으면 프레임 시각
            udp_time = vdata.get('_time') or frame_time
            velocity = None
            if udp_time is not None:
                velocity = self.velocity_tracker.update(
                    vid, udp_time, current_node, next_node, distance
                )
            # velocity가 None이면 측정 불가 — 가짜 값으로 메우지 않음 (Option B 정직화)

            pv = PredVehicle(
                vid=vid,
                currentNode=current_node,
                nextNode=next_node,
                ratio=ratio,
                velocity=velocity,
                destination=vdata.get('destination', 0),
                state=state,
                isFull=vdata.get('isFull', 0),
            )
            self.vehicles[vid] = pv
            self.edge_vehicles[edge_key].append(vid)

    def get_vehicle_stats(self) -> dict:
        """현재 차량 상태 통계"""
        total = len(self.vehicles)
        if total == 0:
            return {'total': 0}

        running = sum(1 for v in self.vehicles.values() if v.state == 1)
        stopped = sum(1 for v in self.vehicles.values() if v.state == 2)
        obs = sum(1 for v in self.vehicles.values() if v.state == 6)
        jam = sum(1 for v in self.vehicles.values() if v.state == 7)
        loaded = sum(1 for v in self.vehicles.values() if v.isFull == 1)

        return {
            'total': total,
            'running': running,
            'stopped': stopped,
            'obs_bz_stop': obs,
            'jam': jam,
            'loaded': loaded,
            'utilization': round((total - stopped) / total * 100, 1) if total > 0 else 0,
            'loaded_pct': round(loaded / total * 100, 1) if total > 0 else 0,
        }

    def get_deadlock_hotspots(self, layout=None) -> List[dict]:
        """
        실시간 데드락 핫스팟 탐지 — 주소 클러스터 기반.

        감지 패턴:
         1) 단일 주소 — state=6/7/8/9 차량이 3대 이상 몰려있으면 핫스팟
         2) 체인 클러스터 — 인접 주소(±3) 3개 이상에 정지차량 총 5대+ 이면 체인 데드락

        Returns:
            [{ 'kind': 'cluster'|'chain',
               'addrs': [..], 'stopped': N, 'severity': 'WARN'|'DANGER'|'CRITICAL',
               'x': cx, 'y': cy,  # layout 있을 때 중심 좌표
               'state_breakdown': {'6': n, '7': n, ...} }, ...]
        """
        stopped_states = {2, 6, 7, 8, 9}
        # 주소별 정지 차량 집계
        addr_stopped: Dict[int, List[PredVehicle]] = defaultdict(list)
        for v in self.vehicles.values():
            if v.state in stopped_states and v.currentNode > 0:
                addr_stopped[v.currentNode].append(v)

        hotspots = []

        # 1) 단일 주소 클러스터 (3대+)
        single_addr_set = set()
        for addr, vs in addr_stopped.items():
            if len(vs) < 3:
                continue
            single_addr_set.add(addr)
            sb = defaultdict(int)
            for v in vs:
                sb[str(v.state)] += 1
            sev = 'CRITICAL' if len(vs) >= 8 else 'DANGER' if len(vs) >= 5 else 'WARN'
            entry = {
                'kind': 'cluster',
                'addrs': [addr],
                'stopped': len(vs),
                'severity': sev,
                'state_breakdown': dict(sb),
            }
            if layout and addr in layout.nodes:
                entry['x'], entry['y'] = layout.nodes[addr]
            hotspots.append(entry)

        # 2) 체인 클러스터 — 인접 주소(±3) 묶기 (정지 2대+ 인 주소들을 시드로)
        seed_addrs = sorted(a for a, vs in addr_stopped.items() if len(vs) >= 2)
        visited = set()
        for a in seed_addrs:
            if a in visited:
                continue
            chain = [a]
            visited.add(a)
            # 오른쪽으로 확장
            for nb in seed_addrs:
                if nb in visited:
                    continue
                if any(abs(nb - c) <= 3 for c in chain):
                    chain.append(nb)
                    visited.add(nb)
            if len(chain) < 3:
                continue
            total = sum(len(addr_stopped[c]) for c in chain)
            if total < 5:
                continue
            sb = defaultdict(int)
            for c in chain:
                for v in addr_stopped[c]:
                    sb[str(v.state)] += 1
            sev = 'CRITICAL' if total >= 15 else 'DANGER' if total >= 10 else 'WARN'
            entry = {
                'kind': 'chain',
                'addrs': sorted(chain),
                'stopped': total,
                'severity': sev,
                'state_breakdown': dict(sb),
            }
            if layout:
                xs, ys = [], []
                for c in chain:
                    if c in layout.nodes:
                        xs.append(layout.nodes[c][0])
                        ys.append(layout.nodes[c][1])
                if xs:
                    entry['x'] = round(sum(xs)/len(xs), 1)
                    entry['y'] = round(sum(ys)/len(ys), 1)
            hotspots.append(entry)

        # 정렬: 심각도 + 정지차량 수
        sev_rank = {'CRITICAL': 0, 'DANGER': 1, 'WARN': 2}
        hotspots.sort(key=lambda h: (sev_rank.get(h['severity'], 3), -h['stopped']))
        return hotspots

    def get_vehicle_positions(self, layout) -> List[dict]:
        """차량 위치를 좌표로 변환 (맵 표시용)"""
        positions = []
        for vid, v in self.vehicles.items():
            pos = layout.get_position(v.currentNode, v.nextNode, v.ratio * self.edge_dist_map.get((v.currentNode, v.nextNode), 1.0))
            if pos:
                positions.append({
                    'vid': vid,
                    'x': round(pos[0], 1),
                    'y': round(pos[1], 1),
                    'state': v.state,
                    'isFull': v.isFull,
                    'velocity': round(v.velocity, 1) if v.velocity is not None else None,
                    'currentNode': v.currentNode,
                    'nextNode': v.nextNode,
                    'destination': v.destination,
                    'ratio': round(v.ratio, 3),
                })
        return positions

    # --------------------------------------------------------
    # 시뮬레이션 스텝
    # --------------------------------------------------------
    def step(self, dt: float = SIM_STEP_SEC):
        """시간 dt(초) 만큼 전방 시뮬레이션"""
        self.current_step += 1

        for vid, v in self.vehicles.items():
            if v.velocity <= 0 or v.state in (2, 6, 7, 8, 9):
                v.stoppedTicks += 1
                self._check_blocking(v)
                continue

            blocked = self._check_blocking(v)
            if blocked:
                v.velocity = 0.0
                v.stoppedTicks += 1
                continue

            v.stoppedTicks = 0
            v.blockedBy = ""
            edge_key = (v.currentNode, v.nextNode)
            edge_dist = self.edge_dist_map.get(edge_key, 1000.0)

            move_mm = v.velocity * 1000.0 / 60.0 * dt
            move_ratio = move_mm / edge_dist if edge_dist > 0 else 0
            v.ratio += move_ratio

            if v.ratio >= 1.0:
                self._advance_to_next_edge(v)

    def _check_blocking(self, v: PredVehicle) -> bool:
        edge_key = (v.currentNode, v.nextNode)
        for other_vid in self.edge_vehicles.get(edge_key, []):
            if other_vid == v.vid:
                continue
            other = self.vehicles.get(other_vid)
            if other and other.ratio > v.ratio and other.velocity <= 0:
                if other.ratio - v.ratio < 0.3:
                    v.blockedBy = other_vid
                    return True

        if v.ratio > 0.7 and v.path and v.pathIndex + 2 < len(v.path):
            next_from = v.nextNode
            next_to = v.path[v.pathIndex + 2]
            for other_vid in self.edge_vehicles.get((next_from, next_to), []):
                other = self.vehicles.get(other_vid)
                if other and other.ratio < 0.3 and other.velocity <= 0:
                    v.blockedBy = other_vid
                    return True

        return False

    def _advance_to_next_edge(self, v: PredVehicle):
        old_edge = (v.currentNode, v.nextNode)
        if v.vid in self.edge_vehicles.get(old_edge, []):
            self.edge_vehicles[old_edge].remove(v.vid)

        if v.path and v.pathIndex + 1 < len(v.path):
            v.pathIndex += 1
            v.currentNode = v.path[v.pathIndex]
            if v.pathIndex + 1 < len(v.path):
                v.nextNode = v.path[v.pathIndex + 1]
            else:
                v.nextNode = v.currentNode
                v.velocity = 0.0
                v.state = 2
                return
        else:
            v.currentNode = v.nextNode
            neighbors = self.graph.get(v.currentNode, [])
            if neighbors:
                v.nextNode = neighbors[0][0]
            else:
                v.velocity = 0.0
                v.state = 2
                return

        # Zone 용량 체크
        new_edge = (v.currentNode, v.nextNode)
        zone_id = self.in_lane_to_zone.get(new_edge)
        if zone_id is not None and zone_id in self.zone_capacity:
            current_count = self.zone_count.get(zone_id, 0)
            if current_count >= self.zone_capacity[zone_id]:
                v.velocity = 0.0
                v.state = 7
                v.blockedBy = f"ZONE_{zone_id}_FULL"
                v.currentNode = old_edge[0]
                v.nextNode = old_edge[1]
                v.ratio = 0.99
                self.edge_vehicles[old_edge].append(v.vid)
                return
            else:
                self.zone_count[zone_id] = current_count + 1
                self.zone_vehicles[zone_id].add(v.vid)

        v.ratio = 0.0
        self.edge_vehicles[new_edge].append(v.vid)

    # --------------------------------------------------------
    # 데드락 탐지
    # --------------------------------------------------------
    def detect_deadlocks(self) -> List[DeadlockGroup]:
        wfg: Dict[str, List[str]] = defaultdict(list)

        stuck = {
            vid: v for vid, v in self.vehicles.items()
            if v.stoppedTicks >= STOPPED_THRESHOLD and v.velocity <= 0
        }

        for vid, v in stuck.items():
            if v.blockedBy and v.blockedBy.startswith("ZONE_"):
                continue

            if v.blockedBy and v.blockedBy in stuck:
                blocker = stuck[v.blockedBy]
                if not (blocker.blockedBy and blocker.blockedBy.startswith("ZONE_")):
                    wfg[vid].append(v.blockedBy)
                continue

            edge_key = (v.currentNode, v.nextNode)
            closest_vid = None
            closest_gap = float('inf')
            for other_vid in self.edge_vehicles.get(edge_key, []):
                if other_vid == vid:
                    continue
                other = stuck.get(other_vid)
                if other and other.ratio > v.ratio:
                    gap = other.ratio - v.ratio
                    if gap < closest_gap:
                        closest_gap = gap
                        closest_vid = other_vid
            if closest_vid:
                wfg[vid].append(closest_vid)

            if not wfg.get(vid) and v.ratio > 0.7:
                reverse_edge = (v.nextNode, v.currentNode)
                for other_vid in self.edge_vehicles.get(reverse_edge, []):
                    other = stuck.get(other_vid)
                    if other and other.ratio > 0.7:
                        wfg[vid].append(other_vid)
                        break

        if not wfg:
            return []

        sccs = tarjan_scc(dict(wfg))
        new_deadlocks = []

        for scc in sccs:
            if len(scc) > 50:
                continue

            self._deadlock_counter += 1
            edges = set()
            zone_ids = set()
            for vid in scc:
                v = self.vehicles.get(vid)
                if v:
                    edges.add((v.currentNode, v.nextNode))

            severity = "HIGH" if len(scc) >= 5 else "MEDIUM" if len(scc) >= 3 else "LOW"
            minute = (self.current_step * SIM_STEP_SEC) / 60.0

            dl = DeadlockGroup(
                groupId=f"DL-{self._deadlock_counter:03d}",
                dlType="CIRCULAR_WAIT",
                vehicles=list(scc),
                edges=list(edges),
                zoneId=list(zone_ids) if zone_ids else None,
                detectedAtStep=self.current_step,
                detectedAtMinute=round(minute, 1),
                severity=severity,
            )
            new_deadlocks.append(dl)

        self.detected_deadlocks.extend(new_deadlocks)
        return new_deadlocks

    def get_zone_status(self) -> List[dict]:
        """Zone 상태 반환"""
        result = []
        for zid, cap in self.zone_capacity.items():
            count = self.zone_count.get(zid, 0)
            occ = (count / cap * 100) if cap > 0 else 0
            status = 'FULL' if count >= cap else 'PRECAUTION' if occ >= HID_CONGESTION_THRESHOLD_PCT else 'NORMAL'
            result.append({
                'zoneId': zid,
                'vehicleCount': count,
                'vehicleMax': cap,
                'occupancy': round(occ, 1),
                'status': status,
            })
        return sorted(result, key=lambda z: z['occupancy'], reverse=True)

    def predict_deadlocks(self, horizons: List[int] = None) -> dict:
        """데드락 예측 (전방 시뮬레이션)"""
        if horizons is None:
            horizons = PREDICTION_HORIZONS

        start_time = time.time()
        results = {}
        total_deadlocks = 0
        all_affected = set()

        prev_horizon = 0
        for horizon_sec in sorted(horizons):
            steps_needed = int((horizon_sec - prev_horizon) / SIM_STEP_SEC)
            for _ in range(steps_needed):
                self.step(SIM_STEP_SEC)

            deadlocks = self.detect_deadlocks()
            dl_list = []
            for dl in deadlocks:
                dl_list.append({
                    'id': dl.groupId,
                    'type': dl.dlType,
                    'vehicleCount': len(dl.vehicles),
                    'vehicles': dl.vehicles,
                    'edges': [{'from': e[0], 'to': e[1]} for e in dl.edges],
                    'detectedAtMinute': dl.detectedAtMinute,
                    'severity': dl.severity,
                })
                all_affected.update(dl.vehicles)
                total_deadlocks += 1

            risk_zones = [z for z in self.get_zone_status() if z['occupancy'] >= HID_CONGESTION_THRESHOLD_PCT]

            label = f"T+{horizon_sec // 60}min"
            results[label] = {
                'deadlockCount': len(dl_list),
                'deadlocks': dl_list,
                'riskZones': risk_zones,
            }
            prev_horizon = horizon_sec

        return {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S"),
            'vehicleCount': len(self.vehicles),
            'elapsedMs': round((time.time() - start_time) * 1000, 1),
            'horizons': results,
            'summary': {
                'totalDeadlocks': total_deadlocks,
                'affectedVehicles': len(all_affected),
                'affectedVehicleIds': list(all_affected),
            },
        }
