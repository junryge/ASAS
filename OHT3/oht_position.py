#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oht_position.py - OHT 위치 계산기

layout.xml(레일 지도)을 읽어서,
OHT 데이터(현재번지, 거리, 다음번지)로 실제 좌표(x, y)를 계산합니다.

=== 사용법 ===

1) 최초 1회: layout.xml → JSON 변환
   python oht_position.py convert A.layout.zip
   python oht_position.py convert layout.xml
   → layout_cache.json 생성 (이후 즉시 로드)

2) 노드 정보 조회
   python oht_position.py node 12340
   → 12340번지의 좌표, 연결 노드 표시

3) OHT 위치 계산
   python oht_position.py calc 12340 14 12341
   → 현재번지=12340, 거리=14, 다음번지=12341 → (x, y) 계산

4) OHT 메시지에서 위치 계산
   python oht_position.py parse "2,OHT,V00795,1,1,0000,1,12340,14,12341,..."
   → 메시지 파싱 → 위치 계산

5) 전체 노드 목록 출력
   python oht_position.py list
   → 전체 노드 좌표 출력

=== 코드에서 사용 ===

   from oht_position import OHTPosition
   pos = OHTPosition("layout_cache.json")
   x, y = pos.calc(현재번지=12340, 거리=14, 다음번지=12341)
"""

import json
import math
import os
import re
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CACHE = os.path.join(SCRIPT_DIR, "layout_cache.json")


class OHTPosition:
    """OHT 위치 계산기"""

    def __init__(self, cache_path=DEFAULT_CACHE):
        """
        layout_cache.json 로드

        Args:
            cache_path: JSON 캐시 파일 경로
                        없으면 convert()로 먼저 생성 필요
        """
        if not os.path.exists(cache_path):
            raise FileNotFoundError(
                f"layout_cache.json 없음: {cache_path}\n"
                f"  → python oht_position.py convert layout.xml  (먼저 변환 필요)"
            )

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 노드: {번지번호: (x, y)}
        self.nodes = {int(k): tuple(v) for k, v in data["nodes"].items()}

        # 인접맵: {번지: [다음번지, ...]}
        self.adj = {int(k): v for k, v in data["adj"].items()}

        # 엣지 거리: {(from, to): 거리(100mm)}
        self.edge_dist = {}
        for k, v in data["edges"].items():
            parts = k.split(",")
            self.edge_dist[(int(parts[0]), int(parts[1]))] = v

    def calc(self, current, distance, next_node):
        """
        OHT 위치 계산

        Args:
            current:   현재 번지 (int)
            distance:  이동 거리 (int, 100mm 단위)
            next_node: 다음 번지 (int)

        Returns:
            (x, y) 좌표 튜플

        예시:
            x, y = pos.calc(12340, 14, 12341)
        """
        if current not in self.nodes:
            return None, None
        if next_node not in self.nodes:
            return self.nodes[current]

        x1, y1 = self.nodes[current]
        x2, y2 = self.nodes[next_node]

        # 두 노드 사이 거리
        edge_len = self.edge_dist.get((current, next_node), 0)
        if edge_len <= 0:
            dx = x2 - x1
            dy = y2 - y1
            edge_len = math.sqrt(dx*dx + dy*dy) * 10
            if edge_len <= 0:
                return x1, y1

        # 보간 비율 (0.0 ~ 1.0)
        ratio = min(distance / edge_len, 1.0)

        x = x1 + (x2 - x1) * ratio
        y = y1 + (y2 - y1) * ratio

        return round(x, 2), round(y, 2)

    def calc_from_message(self, message):
        """
        OHT raw 메시지에서 위치 계산

        Args:
            message: "2,OHT,V00795,1,1,0000,1,12340,14,12341,..."

        Returns:
            dict: {vehicleId, x, y, currentNode, distance, nextNode}
        """
        fields = message.strip().split(",")
        if len(fields) < 10 or fields[1] != "OHT":
            return None

        current = int(fields[7])
        distance = int(fields[8])
        next_node = int(fields[9])
        x, y = self.calc(current, distance, next_node)

        return {
            "vehicleId": fields[2],
            "currentNode": current,
            "distance": distance,
            "nextNode": next_node,
            "x": x,
            "y": y,
            "destPort": fields[17] if len(fields) > 17 else "",
        }

    def get_node(self, node_no):
        """노드 정보 조회"""
        if node_no not in self.nodes:
            return None
        x, y = self.nodes[node_no]
        neighbors = self.adj.get(node_no, [])
        return {
            "no": node_no,
            "x": x,
            "y": y,
            "neighbors": neighbors,
            "neighbor_distances": {
                n: self.edge_dist.get((node_no, n), 0) for n in neighbors
            }
        }


# ============================================================
# XML → JSON 변환
# ============================================================
def convert_xml_to_json(xml_content, output_path=DEFAULT_CACHE):
    """layout.xml 내용을 파싱해서 layout_cache.json 저장"""
    node_xy = {}
    connections = []
    current_addr = None
    current_addr_params = {}
    in_next_addr = False
    next_addr_params = {}

    for line in xml_content.split('\n'):
        line = line.strip()

        if '<group name="Addr' in line and 'class=' in line and 'address.Addr"' in line:
            if current_addr is not None and 'address' in current_addr_params:
                addr_no = int(current_addr_params.get('address', 0))
                if addr_no > 0:
                    x = float(current_addr_params.get('draw-x', 0))
                    y = float(current_addr_params.get('draw-y', 0))
                    node_xy[addr_no] = (x, y)
            current_addr_params = {}
            current_addr = line
            in_next_addr = False
            continue

        if '<group name="NextAddr' in line and 'class=' in line and 'NextAddr"' in line:
            in_next_addr = True
            next_addr_params = {}
            continue

        if in_next_addr and '</group>' in line:
            if 'address' in current_addr_params and 'next-address' in next_addr_params:
                from_addr = int(current_addr_params.get('address', 0))
                try:
                    to_addr = int(next_addr_params.get('next-address', '0'))
                    if from_addr > 0 and to_addr > 0:
                        connections.append((from_addr, to_addr))
                except ValueError:
                    pass
            in_next_addr = False
            continue

        if '<param ' in line and 'key="' in line and 'value="' in line:
            key_match = re.search(r'key="([^"]+)"', line)
            value_match = re.search(r'value="([^"]*)"', line)
            if key_match and value_match:
                key = key_match.group(1)
                value = value_match.group(1)
                if in_next_addr:
                    next_addr_params[key] = value
                elif current_addr is not None:
                    current_addr_params[key] = value

    # 마지막 노드
    if current_addr is not None and 'address' in current_addr_params:
        addr_no = int(current_addr_params.get('address', 0))
        if addr_no > 0:
            x = float(current_addr_params.get('draw-x', 0))
            y = float(current_addr_params.get('draw-y', 0))
            node_xy[addr_no] = (x, y)

    # 인접맵 + 거리
    adj = {}
    edge_dist = {}
    for from_n, to_n in connections:
        adj.setdefault(from_n, []).append(to_n)
        if from_n in node_xy and to_n in node_xy:
            x1, y1 = node_xy[from_n]
            x2, y2 = node_xy[to_n]
            dist = int(math.sqrt((x2-x1)**2 + (y2-y1)**2) * 10)
            edge_dist[(from_n, to_n)] = max(dist, 10)

    # JSON 저장
    data = {
        "nodes": {str(k): list(v) for k, v in node_xy.items()},
        "adj": {str(k): v for k, v in adj.items()},
        "edges": {f"{k[0]},{k[1]}": v for k, v in edge_dist.items()},
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return len(node_xy), len(edge_dist)


def convert_file(filepath):
    """layout.xml 또는 .zip 파일 → layout_cache.json 변환"""
    print(f"변환: {filepath}")

    if filepath.endswith('.zip'):
        with zipfile.ZipFile(filepath, 'r') as z:
            xml_names = [n for n in z.namelist() if n.endswith('layout.xml')]
            if not xml_names:
                print("오류: ZIP 안에 layout.xml 없음")
                return
            print(f"  → {xml_names[0]}")
            xml_content = z.read(xml_names[0]).decode('utf-8')
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()

    nodes, edges = convert_xml_to_json(xml_content)
    print(f"  노드: {nodes}개  엣지: {edges}개")
    print(f"  → {DEFAULT_CACHE}")


# ============================================================
# CLI
# ============================================================
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    # convert: XML → JSON
    if cmd == "convert":
        if len(sys.argv) < 3:
            print("사용법: python oht_position.py convert layout.xml")
            print("        python oht_position.py convert A.layout.zip")
            return
        convert_file(sys.argv[2])
        return

    # 이하 명령은 layout_cache.json 필요
    try:
        pos = OHTPosition()
    except FileNotFoundError as e:
        print(e)
        return

    # node: 노드 정보
    if cmd == "node":
        if len(sys.argv) < 3:
            print("사용법: python oht_position.py node 12340")
            return
        node_no = int(sys.argv[2])
        info = pos.get_node(node_no)
        if info:
            print(f"번지: {info['no']}")
            print(f"좌표: ({info['x']}, {info['y']})")
            print(f"연결: {info['neighbors']}")
            for n, d in info['neighbor_distances'].items():
                print(f"  → {n} (거리 {d} = {d/10:.1f}m)")
        else:
            print(f"노드 {node_no} 없음")

    # calc: 위치 계산
    elif cmd == "calc":
        if len(sys.argv) < 5:
            print("사용법: python oht_position.py calc 현재번지 거리 다음번지")
            print("예시:   python oht_position.py calc 12340 14 12341")
            return
        cur = int(sys.argv[2])
        dist = int(sys.argv[3])
        nxt = int(sys.argv[4])
        x, y = pos.calc(cur, dist, nxt)
        print(f"현재번지: {cur}  거리: {dist}  다음번지: {nxt}")
        print(f"계산 위치: ({x}, {y})")

    # parse: 메시지에서 위치 계산
    elif cmd == "parse":
        if len(sys.argv) < 3:
            print('사용법: python oht_position.py parse "2,OHT,V00795,..."')
            return
        msg = sys.argv[2]
        result = pos.calc_from_message(msg)
        if result:
            print(f"차량: {result['vehicleId']}")
            print(f"현재번지: {result['currentNode']}  거리: {result['distance']}  다음번지: {result['nextNode']}")
            print(f"계산 위치: ({result['x']}, {result['y']})")
            if result['destPort']:
                print(f"목적지: {result['destPort']}")
        else:
            print("파싱 실패")

    # list: 전체 노드
    elif cmd == "list":
        print(f"전체 노드 {len(pos.nodes)}개:")
        for no in sorted(pos.nodes.keys())[:50]:
            x, y = pos.nodes[no]
            neighbors = pos.adj.get(no, [])
            print(f"  {no:>6d}: ({x:>8.2f}, {y:>8.2f})  → {neighbors}")
        if len(pos.nodes) > 50:
            print(f"  ... 외 {len(pos.nodes)-50}개")

    else:
        print(f"알 수 없는 명령: {cmd}")
        print("  convert / node / calc / parse / list")


if __name__ == "__main__":
    main()
