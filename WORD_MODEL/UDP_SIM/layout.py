# -*- coding: utf-8 -*-
"""
layout.py — OHT_MAP/cache JSON 통합 로딩 + 위치 보간

여러 캐시 파일을 모두 로드해서 단일 노드 풀로 합침. 어떤 fab CSV 가 와도
노드 ID 만 같으면 좌표 발견. 그래도 안 발견되면 ID 해시로 가짜 좌표 생성
(차량이 무조건 화면에 보이도록).
"""

import json
import os
import math
from pathlib import Path
from typing import Dict, Optional, Tuple, List


class Layout:
    def __init__(self, fab: str, cache_paths):
        """cache_paths: 단일 path 또는 list. 모든 파일을 합침."""
        self.fab = fab
        if isinstance(cache_paths, (str, Path)):
            self.cache_paths = [Path(cache_paths)]
        else:
            self.cache_paths = [Path(p) for p in cache_paths]
        self.nodes: Dict[int, Tuple[float, float]] = {}
        self.edges: Dict[Tuple[int, int], float] = {}
        self.bounds = (0.0, 0.0, 0.0, 0.0)
        self.loaded = False
        self._missing_warned = False
        # 임의 좌표 풀 (캐시에 없는 노드용)
        self._fake_pos: Dict[int, Tuple[float, float]] = {}

    def load(self) -> "Layout":
        merged = 0
        for p in self.cache_paths:
            if not p.exists():
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                continue
            for k, v in (d.get("nodes") or {}).items():
                try:
                    nid = int(k)
                    if nid not in self.nodes:
                        self.nodes[nid] = (float(v[0]), float(v[1]))
                except (ValueError, TypeError, IndexError):
                    continue
            for k, dist in (d.get("edges") or {}).items():
                try:
                    a, b = k.split(",")
                    ek = (int(a), int(b))
                    if ek not in self.edges:
                        self.edges[ek] = float(dist)
                except (ValueError, TypeError):
                    continue
            merged += 1

        if self.nodes:
            xs = [p[0] for p in self.nodes.values()]
            ys = [p[1] for p in self.nodes.values()]
            self.bounds = (min(xs), min(ys), max(xs), max(ys))
        self.loaded = bool(self.nodes)
        print(f"[layout {self.fab}] {merged} 캐시 통합 → 노드 {len(self.nodes)}, 엣지 {len(self.edges)}")
        return self

    # ── 미발견 노드용 결정적 가짜 좌표 ─────────────
    def _fake(self, nid: int) -> Tuple[float, float]:
        cached = self._fake_pos.get(nid)
        if cached is not None:
            return cached
        # bounds 안에 균등 분포 (해시 기반, 노드 별 결정적)
        if self.bounds == (0, 0, 0, 0):
            xmin, ymin, xmax, ymax = 0, 0, 10000, 5000
        else:
            xmin, ymin, xmax, ymax = self.bounds
        # 단순 해시
        h1 = (nid * 2654435761) & 0xFFFFFFFF
        h2 = (nid * 40503     ) & 0xFFFFFFFF
        rx = (h1 % 100000) / 100000.0
        ry = (h2 % 100000) / 100000.0
        x = xmin + rx * (xmax - xmin)
        y = ymin + ry * (ymax - ymin)
        self._fake_pos[nid] = (x, y)
        return (x, y)

    def get_position(self, current_node: int, next_node: int,
                     distance: float) -> Optional[Tuple[float, float]]:
        a = self.nodes.get(current_node)
        b = self.nodes.get(next_node)
        # 한 쪽이라도 캐시에 있으면 그 좌표 사용
        if a is not None and b is not None:
            edge = self.edges.get((current_node, next_node))
            if edge is None or edge <= 0:
                return a
            ratio = max(0.0, min(1.0, distance / edge))
            return (a[0] + (b[0] - a[0]) * ratio,
                    a[1] + (b[1] - a[1]) * ratio)
        if a is not None: return a
        if b is not None: return b

        # 둘 다 없음 → 가짜 좌표 (차량이 무조건 보이도록)
        if current_node:
            return self._fake(current_node)
        if next_node:
            return self._fake(next_node)
        return None

    def stats(self) -> dict:
        return {
            "fab": self.fab,
            "cache": [str(p) for p in self.cache_paths],
            "loaded": self.loaded,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "bounds": list(self.bounds),
            "fake_nodes": len(self._fake_pos),
        }

