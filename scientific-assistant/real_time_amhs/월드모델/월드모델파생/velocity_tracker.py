#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
velocity_tracker.py - UDP 위치 변화 기반 차량별 순간 속도 계산

UDP 메시지(CurrentAddress, Distance, NextAddress) + 수신시각 차분으로
차량별 속도(m/min)를 산출. ATLAS Java(OhtMsgWorkerRunnable)는 edge 전환
시에만(Case B) 계산하지만, 본 트래커는 같은 edge 안(Case A)도 계산하여
0.5초 해상도의 차량별 속도 시계열을 만든다.

단위:
  - 입력 distance : dm (=100mm). data_loader.py와 layout_cache.json 모두 dm.
  - 입력 elapsed  : seconds (datetime 차)
  - 출력 speed    : m/min (config.DEFAULT_VELOCITY와 동일 단위)

공식:
  speed [m/min] = delta_dm × 6 / elapsed_sec
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class _PrevState:
    time: datetime
    edge: Tuple[int, int]
    distance: int  # dm


class VelocityTracker:
    """차량별 순간 속도(m/min) 트래커.

    edge_dist_map: {(from_node, to_node): length_dm}
    adj_map: {node_id: [neighbor_node_ids]} — 불연속 시 BFS 경로 추정용 (선택)
    """

    MIN_SPEED = 0.0     # 정지 표현을 위해 0 허용 (ATLAS는 1.5)
    MAX_SPEED = 300.0   # 안전 상한 (m/min). 18 km/h.
    MAX_GAP_SEC = 30.0  # 이 이상 갭은 측정 불가 처리
    BFS_MAX_HOPS = 20   # 불연속 보간 BFS 탐색 한도

    def __init__(
        self,
        edge_dist_map: Dict[Tuple[int, int], float],
        adj_map: Optional[Dict[int, List[int]]] = None,
    ):
        self._edge_len = edge_dist_map
        self._adj = adj_map or {}
        self._prev: Dict[str, _PrevState] = {}
        self._last_speed: Dict[str, float] = {}  # 캐시: 같은 UDP 재호출 시 재사용
        self._bfs_cache: Dict[Tuple[int, int], Optional[float]] = {}

    def update(
        self,
        vid: str,
        t: datetime,
        curr_node: int,
        next_node: int,
        distance: int,
    ) -> Optional[float]:
        """차량의 새 UDP 메시지를 받아 속도(m/min)를 반환.

        같은 t로 재호출되면(= 새 UDP 안 옴) 마지막 계산값 캐시 반환.
        첫 관측 또는 산정 불가 시 None.
        """
        edge = (curr_node, next_node)
        prev = self._prev.get(vid)

        # 첫 관측: prev 저장 후 None 반환
        if prev is None:
            self._prev[vid] = _PrevState(t, edge, distance)
            return None

        # 같은 시각 재호출(= cumulative state 그대로) → 캐시 반환, prev 갱신 X
        if t == prev.time:
            return self._last_speed.get(vid)

        # 순서 어긋난 메시지(늦게 도착한 과거 UDP) → 무시. prev 갱신 X.
        if t < prev.time:
            return self._last_speed.get(vid)

        # 새 UDP 정상 도착: 속도 계산 후 prev 갱신
        elapsed = (t - prev.time).total_seconds()
        if elapsed <= 0:
            return self._last_speed.get(vid)

        # 갭이 너무 크면 평균 속도가 무의미 → 측정 불가
        if elapsed > self.MAX_GAP_SEC:
            self._prev[vid] = _PrevState(t, edge, distance)
            return self._last_speed.get(vid)

        if prev.edge == edge:
            # Case A: 같은 edge 안
            delta_dm = distance - prev.distance
        elif prev.edge[1] == edge[0]:
            # Case B: 자연스러운 edge 전환 (prev.next == curr.curr)
            prev_len = self._edge_len.get(prev.edge, 0)
            delta_dm = (prev_len - prev.distance) + distance
        else:
            # Case C: 불연속 — BFS로 경로 길이 추정
            path_len = self._shortest_path_length(prev.edge[1], edge[0])
            if path_len is None:
                # 경로 못 찾음 → 측정 불가
                self._prev[vid] = _PrevState(t, edge, distance)
                return self._last_speed.get(vid)
            prev_len = self._edge_len.get(prev.edge, 0)
            delta_dm = (prev_len - prev.distance) + path_len + distance

        if delta_dm < 0:
            speed = 0.0  # 후진 또는 distance 리셋 이상치
        else:
            speed = delta_dm * 6.0 / elapsed  # m/min
            if speed != speed or speed == float('inf'):
                self._prev[vid] = _PrevState(t, edge, distance)
                return self._last_speed.get(vid)
            speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))

        # 정상 계산 완료 → prev 갱신
        self._prev[vid] = _PrevState(t, edge, distance)
        self._last_speed[vid] = speed
        return speed

    def reset(self, vid: Optional[str] = None) -> None:
        """프레임 점프 등으로 상태를 비울 때 호출."""
        if vid is None:
            self._prev.clear()
            self._last_speed.clear()
        else:
            self._prev.pop(vid, None)
            self._last_speed.pop(vid, None)

    def _shortest_path_length(self, src: int, dst: int) -> Optional[float]:
        """src → dst 까지 layout 그래프에서 BFS 최단 경로 길이(dm).

        adj_map이 없거나 경로가 없거나 BFS_MAX_HOPS를 넘으면 None.
        결과는 캐시에 저장하여 같은 노드쌍 반복 조회 가속.
        """
        if not self._adj or src == dst:
            return 0.0 if src == dst else None

        key = (src, dst)
        if key in self._bfs_cache:
            return self._bfs_cache[key]

        # BFS — hop 수 기반, edge 길이 합산
        visited = {src}
        queue = deque([(src, 0.0, 0)])  # (node, accumulated_length_dm, hops)
        result: Optional[float] = None

        while queue:
            node, length, hops = queue.popleft()
            if hops >= self.BFS_MAX_HOPS:
                continue
            for nxt in self._adj.get(node, []):
                if nxt in visited:
                    continue
                visited.add(nxt)
                edge_len = self._edge_len.get((node, nxt), 0)
                new_length = length + edge_len
                if nxt == dst:
                    result = new_length
                    break
                queue.append((nxt, new_length, hops + 1))
            if result is not None:
                break

        self._bfs_cache[key] = result
        return result
