#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layout_map_cre.py - layout.xml에서 layout.html 생성

사용법:
    python layout_map_cre.py [layout.zip 경로] [출력 layout.html 경로]

기본값:
    입력: layout/layout/layout.zip
    출력: layout/layout/layout.html
"""

import os
import sys
import re
import json
import zipfile
from typing import Dict, List, Tuple
from datetime import datetime


def parse_layout_xml(xml_content: str) -> Tuple[List[Dict], List[List]]:
    """
    layout.xml 파싱하여 노드와 연결 정보 추출 (라인 단위 파싱)

    Returns:
        nodes: [{'no': int, 'x': float, 'y': float, 'stations': []}, ...]
        connections: [[from_no, to_no], ...]
    """
    print("XML 파싱 시작 (라인 단위)...")

    nodes = {}
    connections = []

    # 상태 변수
    current_addr = None
    current_addr_params = {}
    in_next_addr = False
    next_addr_params = {}

    # 라인 단위로 처리
    lines = xml_content.split('\n')
    total_lines = len(lines)
    print(f"  총 라인 수: {total_lines:,}")

    for line_no, line in enumerate(lines):
        if line_no % 500000 == 0:
            print(f"  처리 중: {line_no:,}/{total_lines:,} ({line_no*100//total_lines}%)")

        line = line.strip()

        # Addr 그룹 시작
        if '<group name="Addr' in line and 'class=' in line and 'address.Addr"' in line:
            # 이전 Addr 저장
            if current_addr is not None and 'address' in current_addr_params:
                addr_no = int(current_addr_params.get('address', 0))
                if addr_no > 0:
                    x = float(current_addr_params.get('draw-x', 0))
                    y = float(current_addr_params.get('draw-y', 0))
                    nodes[addr_no] = {
                        'no': addr_no,
                        'x': round(x, 2),
                        'y': round(y, 2),
                        'stations': []
                    }

            # 새 Addr 시작
            current_addr_params = {}
            current_addr = line
            in_next_addr = False
            continue

        # NextAddr 그룹 시작
        if '<group name="NextAddr' in line and 'class=' in line and 'NextAddr"' in line:
            in_next_addr = True
            next_addr_params = {}
            continue

        # NextAddr 그룹 종료
        if in_next_addr and '</group>' in line:
            # 연결 정보 저장
            if 'address' in current_addr_params and 'next-address' in next_addr_params:
                from_addr = int(current_addr_params.get('address', 0))
                to_addr_str = next_addr_params.get('next-address', '0')
                try:
                    to_addr = int(to_addr_str)
                    if from_addr > 0 and to_addr > 0:
                        connections.append([from_addr, to_addr])
                except ValueError:
                    pass
            in_next_addr = False
            continue

        # 파라미터 파싱
        if '<param ' in line and 'key="' in line and 'value="' in line:
            # key와 value 추출
            key_match = re.search(r'key="([^"]+)"', line)
            value_match = re.search(r'value="([^"]*)"', line)

            if key_match and value_match:
                key = key_match.group(1)
                value = value_match.group(1)

                if in_next_addr:
                    next_addr_params[key] = value
                elif current_addr is not None:
                    current_addr_params[key] = value

    # 마지막 Addr 저장
    if current_addr is not None and 'address' in current_addr_params:
        addr_no = int(current_addr_params.get('address', 0))
        if addr_no > 0:
            x = float(current_addr_params.get('draw-x', 0))
            y = float(current_addr_params.get('draw-y', 0))
            nodes[addr_no] = {
                'no': addr_no,
                'x': round(x, 2),
                'y': round(y, 2),
                'stations': []
            }

    print(f"  총 노드: {len(nodes)}개")
    print(f"  총 연결: {len(connections)}개")

    # 딕셔너리를 리스트로 변환
    nodes_list = list(nodes.values())

    return nodes_list, connections


def generate_layout_html(nodes: List[Dict], connections: List[List], output_path: str):
    """
    layout.html 생성
    """
    print(f"layout.html 생성: {output_path}")

    # JSON 변환
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    connections_json = json.dumps(connections, ensure_ascii=False)

    # HTML 템플릿
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OHT Layout Data</title>
    <script>
// 노드 데이터: no(번지), x, y, stations
const A={nodes_json};

// 연결 데이터: [from_no, to_no]
const C={connections_json};

// 레이아웃 정보
const layoutInfo = {{
    nodeCount: {len(nodes)},
    connectionCount: {len(connections)},
    generated: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
}};

console.log("Layout loaded:", layoutInfo);
    </script>
</head>
<body>
    <h1>OHT Layout Data</h1>
    <p>Nodes: {len(nodes)}</p>
    <p>Connections: {len(connections)}</p>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  완료: {os.path.getsize(output_path):,} bytes")


def main():
    # 기본 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_zip = os.path.join(script_dir, 'layout', 'layout', 'layout.zip')
    default_output = os.path.join(script_dir, 'layout', 'layout', 'layout.html')

    # 명령행 인자 처리
    zip_path = sys.argv[1] if len(sys.argv) > 1 else default_zip
    output_path = sys.argv[2] if len(sys.argv) > 2 else default_output

    print("=" * 60)
    print("layout_map_cre.py - layout.xml에서 layout.html 생성")
    print("=" * 60)
    print(f"입력: {zip_path}")
    print(f"출력: {output_path}")
    print()

    # ZIP 파일 확인
    if not os.path.exists(zip_path):
        print(f"오류: ZIP 파일을 찾을 수 없습니다: {zip_path}")
        sys.exit(1)

    # ZIP에서 layout.xml 추출
    print("layout.xml 추출 중...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('layout.xml') as f:
            xml_content = f.read().decode('utf-8')

    print(f"  XML 크기: {len(xml_content):,} bytes")

    # XML 파싱
    nodes, connections = parse_layout_xml(xml_content)

    # HTML 생성
    generate_layout_html(nodes, connections, output_path)

    print()
    print("=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == '__main__':
    main()
