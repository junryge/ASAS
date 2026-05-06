# -*- coding: utf-8 -*-
"""
layout.py — OHT_MAP/cache JSON 통합 로딩 + 위치 보간

여러 캐시 파일을 모두 로드해서 단일 노드 풀로 합침. 캐시 파일은 모두 진짜
fab 좌표 데이터. 가짜 좌표 생성 코드 없음.
캐시 어디에도 없는 노드 → None 반환 (차량 안 그려짐).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


class Layout:
    def __init__(self, fab: str, cache_paths: Union[Path, str, List]):
        self.fab = fab
        if isinstance(cache_paths, (str, Path)):
            self.cache_paths = [Path(cache_paths)]
        else:
            self.cache_paths = [Path(p) for p in cache_paths]
        self.nodes: Dict[int, Tuple[float, float]] = {}
        self.edges: Dict[Tuple[int, int], float] = {}
        self.bounds = (0.0, 0.0, 0.0, 0.0)
        self.loaded = False
        self._missing_nodes: Dict[int, int] = {}

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

    def get_position(self, current_node: int, next_node: int,
                     distance: float) -> Optional[Tuple[float, float]]:
        """진짜 캐시 좌표만 반환. 캐시에 둘 다 없으면 None (가짜 X)."""
        a = self.nodes.get(current_node)
        b = self.nodes.get(next_node)
        if a is not None and b is not None:
            edge = self.edges.get((current_node, next_node))
            if edge is None or edge <= 0:
                return a
            ratio = max(0.0, min(1.0, distance / edge))
            return (a[0] + (b[0] - a[0]) * ratio,
                    a[1] + (b[1] - a[1]) * ratio)
        if a is not None:
            return a
        if b is not None:
            return b
        if current_node:
            self._missing_nodes[current_node] = self._missing_nodes.get(current_node, 0) + 1
        return None

    def stats(self) -> dict:
        return {
            "fab": self.fab,
            "cache": [str(p) for p in self.cache_paths],
            "loaded": self.loaded,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "bounds": list(self.bounds),
            "missing_nodes": len(self._missing_nodes),
        }
