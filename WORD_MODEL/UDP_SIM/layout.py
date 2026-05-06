# -*- coding: utf-8 -*-
"""
layout.py — OHT_MAP/cache JSON 읽어서 노드 좌표 + 엣지 거리 + 위치 보간

캐시 포맷
{
  "nodes": { "1": [x, y], ... },
  "edges": { "1,2": 666, ... },
  "adj":   { ... }       # 사용 안 함
}
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple


class Layout:
    def __init__(self, fab: str, cache_path: Path):
        self.fab = fab
        self.cache_path = Path(cache_path)
        self.nodes: Dict[int, Tuple[float, float]] = {}
        self.edges: Dict[Tuple[int, int], float] = {}
        self.bounds = (0.0, 0.0, 0.0, 0.0)   # (xmin, ymin, xmax, ymax)
        self.loaded = False

    def load(self) -> "Layout":
        if not self.cache_path.exists():
            return self
        with open(self.cache_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k, v in (d.get("nodes") or {}).items():
            try:
                self.nodes[int(k)] = (float(v[0]), float(v[1]))
            except (ValueError, TypeError, IndexError):
                continue
        for k, dist in (d.get("edges") or {}).items():
            try:
                a, b = k.split(",")
                self.edges[(int(a), int(b))] = float(dist)
            except (ValueError, TypeError):
                continue

        if self.nodes:
            xs = [p[0] for p in self.nodes.values()]
            ys = [p[1] for p in self.nodes.values()]
            self.bounds = (min(xs), min(ys), max(xs), max(ys))
        self.loaded = True
        return self

    def get_position(self, current_node: int, next_node: int,
                     distance: float) -> Optional[Tuple[float, float]]:
        """현재 노드에서 next 노드 방향으로 distance 만큼 이동한 좌표.
        엣지 거리를 모르면 current 좌표 반환. 둘 다 없으면 None.
        """
        a = self.nodes.get(current_node)
        b = self.nodes.get(next_node)
        if a is None and b is None:
            return None
        if a is None:
            return b
        if b is None:
            return a

        edge = self.edges.get((current_node, next_node))
        if edge is None or edge <= 0:
            return a
        ratio = max(0.0, min(1.0, distance / edge))
        return (a[0] + (b[0] - a[0]) * ratio,
                a[1] + (b[1] - a[1]) * ratio)

    def stats(self) -> dict:
        return {
            "fab": self.fab,
            "cache": str(self.cache_path),
            "loaded": self.loaded,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "bounds": list(self.bounds),
        }
