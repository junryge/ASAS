#!/usr/bin/env python3
"""
OHT 3D Layout Builder v1.0
===========================
반도체 FAB OHT 레이아웃 GUI 빌더

기능:
  - XML/ZIP에서 layout 데이터 파싱
  - 2D 캔버스에서 노드/레일/스테이션/Zone 시각화 및 편집
  - HTML(Three.js), Blender(.py), JSX(React Three Fiber) 내보내기

Author: Claude Code Generator
Date: 2025-02
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import math
import zipfile
import tempfile
import threading
import time
import uuid
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple


# ============================================================================
# DATA MODELS (Dataclasses)
# ============================================================================

@dataclass
class OHTNode:
    """OHT Address Node 데이터 클래스

    Attributes:
        id: Address ID (고유 식별자)
        x, y: Draw coordinate (2D 시각화 좌표)
        cad_x, cad_y: CAD 원본 좌표
        symbol: 심볼 이름
        is_station: 1이면 스테이션 노드
        branch: True이면 분기점
        junction: True이면 교차점
        hid_included: HID 포함 여부 (-1: 미포함)
        stopzone: Stop Zone ID
        stations: 이 노드에 연결된 스테이션 리스트
    """
    id: int = 0
    x: float = 0.0
    y: float = 0.0
    cad_x: float = 0.0
    cad_y: float = 0.0
    symbol: str = ""
    is_station: int = 0
    branch: bool = False
    junction: bool = False
    hid_included: int = -1
    stopzone: int = 0
    stations: List[Dict] = field(default_factory=list)


@dataclass
class OHTEdge:
    """OHT 레일 연결 정보 (Address A → Address B)

    Attributes:
        from_id: 시작 Address ID
        to_id: 종료 Address ID
        distance: 거리 (pulses)
        speed: 이동 속도
        direction: 방향 (0=양방향, 1=한방향)
        branch_dir: 분기 방향
    """
    from_id: int = 0
    to_id: int = 0
    distance: int = 0
    speed: int = 0
    direction: int = 0
    branch_dir: int = 0


@dataclass
class OHTStation:
    """스테이션 정보

    Attributes:
        port_id: Port ID (예: P-001, P-002)
        category: 스테이션 카테고리
        type: 스테이션 타입 (장비/로드 등)
        no: 스테이션 번호
        position: 위치 코드
        node_id: 연결된 Address Node ID
        x, y: 화면 좌표
    """
    port_id: str = ""
    category: int = 0
    type: int = 0
    no: int = 0
    position: int = 0
    node_id: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class MCPZone:
    """MCP (Material Control Point) Zone - 자재 흐름 제어 영역

    Attributes:
        id: Zone ID
        no: Zone Number
        name: Zone 이름
        vehicle_max: 최대 차량 수
        vehicle_precaution: 주의 차량 수
        type: Zone 타입
        cut_lanes: 절단 레인 (통로 차단)
        entries: 진입 경로
        exits: 퇴출 경로
    """
    id: int = 0
    no: int = 0
    name: str = ""
    vehicle_max: int = 0
    vehicle_precaution: int = 0
    type: int = 0
    cut_lanes: List[Dict] = field(default_factory=list)
    entries: List[Dict] = field(default_factory=list)
    exits: List[Dict] = field(default_factory=list)


@dataclass
class HIDZone:
    """HID (Hoist Interface Device) Zone - 장비 인터페이스 영역

    Attributes:
        label_name: HID 라벨 이름
        machine_id: 장비 ID (예: HID-B01-1(001))
        address: Address 번호
        draw_x, draw_y: 화면 표시 좌표
        point: 포인트 정보
    """
    label_name: str = ""
    machine_id: str = ""
    address: int = 0
    draw_x: float = 0.0
    draw_y: float = 0.0
    point: int = 0


@dataclass
class OHTVehicle:
    """OHT (Overhead Hoist Transport) 차량 정보

    Attributes:
        id: 차량 고유 ID
        path_index: 현재 경로 인덱스
        speed: 이동 속도 (mm/s)
        state: 상태 (running, loaded, stopped, jam)
        has_foup: FOUP 탑재 여부
        color: 색상 코드
    """
    id: str = ""
    path_index: int = 0
    speed: float = 200.0
    state: str = "running"
    has_foup: bool = False
    color: str = "#ff6600"

    def __post_init__(self):
        """Initialize ID if not provided"""
        if not self.id:
            self.id = f"V{uuid.uuid4().hex[:5].upper()}"


@dataclass
class HIDMaster:
    """HID 통합 마스터 데이터 (HID Label + HidControl + MCP Zone 통합)

    Attributes:
        zone_id: MCP Zone ID
        hid_id: HID 식별자 (예: B01-1)
        full_name: 전체 이름 (예: HID-B01-1(001))
        address: Address 번호
        vehicle_max: 최대 차량 수
        vehicle_precaution: 주의 차량 수
        zone_type: Zone 타입
        in_count: 진입 경로 개수
        out_count: 퇴출 경로 개수
        in_lanes: 진입 레인 (문자열)
        out_lanes: 퇴출 레인 (문자열)
        zcu: ZCU 정보
    """
    zone_id: int = 0
    hid_id: str = ""
    full_name: str = ""
    address: int = 0
    vehicle_max: int = 0
    vehicle_precaution: int = 0
    zone_type: int = 0
    in_count: int = 0
    out_count: int = 0
    in_lanes: str = ""
    out_lanes: str = ""
    zcu: str = ""


@dataclass
class OHTProject:
    """OHT 레이아웃 프로젝트 데이터 전체 구조

    Attributes:
        fab_name: FAB 이름 (예: M14-Pro, M14-Q)
        project: 프로젝트 이름
        version: 버전 정보
        nodes: 모든 Address 노드 리스트
        edges: 모든 연결 리스트
        stations: 모든 스테이션 리스트
        mcp_zones: MCP Zone 리스트
        hid_zones: HID Zone 라벨 리스트
        hid_master: HID 통합 마스터 리스트
        vehicles: OHT 차량 리스트
        bounds: 좌표 범위 {min_x, max_x, min_y, max_y}
        oht_count: OHT 차량 개수
        zone_addr_map: Zone ID → Address 리스트 매핑
        rail_height: 레일 높이 (3D)
        rail_color: 레일 색상
        node_color: 노드 색상
        station_color: 스테이션 색상
        floor_color: 바닥 색상
    """
    fab_name: str = "M14-Pro"
    project: str = "OHT Layout"
    version: str = "1.0"
    nodes: List[Dict] = field(default_factory=list)
    edges: List[Dict] = field(default_factory=list)
    stations: List[Dict] = field(default_factory=list)
    mcp_zones: List[Dict] = field(default_factory=list)
    hid_zones: List[Dict] = field(default_factory=list)
    hid_master: List[Dict] = field(default_factory=list)
    vehicles: List[Dict] = field(default_factory=list)
    bounds: Dict = field(default_factory=lambda: {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0})
    oht_count: int = 35
    zone_addr_map: Dict = field(default_factory=dict)
    rail_height: float = 15.0
    rail_color: str = "#00d4ff"
    node_color: str = "#44ff88"
    station_color: str = "#ff4444"
    floor_color: str = "#0a0a1a"


# ============================================================================
# XML/ZIP PARSER
# ============================================================================

class OHTLayoutParser:
    """OHT Layout XML/ZIP 파서

    layout.xml 파일에서 Address, Station, MCP Zone, HID Zone 데이터를
    파싱하여 구조화된 딕셔너리로 변환합니다.
    """

    @staticmethod
    def parse_xml(xml_path, fab_name='M14-Pro', progress_callback=None):
        """Parse layout XML using iterparse for memory efficiency.

        Args:
            xml_path: Path to layout.xml
            fab_name: FAB 이름 (예: M14-Pro)
            progress_callback: 진행 상황 콜백 함수 (message, percent)

        Returns:
            dict: 파싱된 레이아웃 데이터
                {
                    'fab_name': str,
                    'nodes': [dict],
                    'edges': [dict],
                    'stations': [dict],
                    'mcp_zones': [dict],
                    'hid_zones': [dict],
                    'hid_master': [dict],
                    'zone_addr_map': dict,
                    'bounds': dict
                }
        """
        if progress_callback:
            progress_callback("파싱 시작...", 0)

        nodes = {}
        edges = []
        mcp_zones = []
        hid_zones = []
        hid_controls = []

        # iterparse로 메모리 효율적으로 파싱
        context = ET.iterparse(xml_path, events=('start', 'end'))

        # 상태 변수들
        current_addr_name = None
        in_addr_group = False
        in_next_addr = False
        in_station = False
        in_mcp_zone_control = False
        in_mcp_zone = False
        in_mcp_sub = False
        in_hid_control = False
        in_hid_entry = False
        in_hid_label = False

        # 임시 저장소
        addr_data = {}
        next_addr_data = {}
        station_data = {}
        mcp_zone_data = {}
        mcp_sub_data = {}
        mcp_sub_type = ''
        hid_entry_data = {}
        hid_label_data = {}

        depth = 0
        addr_depth = 0
        count = 0

        for event, elem in context:
            if event == 'start':
                depth += 1

                if elem.tag == 'group':
                    name = elem.get('name', '')
                    cls = elem.get('class', '')

                    # ===== HID Control =====
                    if 'hid.HidControl' in cls:
                        in_hid_control = True

                    elif in_hid_control and 'hid.Hid' in cls and 'HidControl' not in cls:
                        in_hid_entry = True
                        hid_entry_data = {'hid_id': '', 'mcpzone_no': 0, 'group_name': name}

                    # ===== MCP Zone Control =====
                    elif 'McpZoneControl' in cls:
                        in_mcp_zone_control = True

                    elif in_mcp_zone_control and 'McpZone' in cls and 'CutLane' not in cls and 'Entry' not in cls and 'Exit' not in cls:
                        in_mcp_zone = True
                        mcp_zone_data = {
                            'id': 0, 'no': 0, 'name': name,
                            'vehicle_max': 0, 'vehicle_precaution': 0,
                            'type': 0,
                            'cut_lanes': [], 'entries': [], 'exits': []
                        }

                    elif in_mcp_zone and ('CutLane' in cls or 'Entry' in cls or 'Exit' in cls):
                        in_mcp_sub = True
                        mcp_sub_type = 'cut_lane' if 'CutLane' in cls else ('entry' if 'Entry' in cls else 'exit')
                        mcp_sub_data = {'start': 0, 'end': 0, 'stop_no': 0, 'stop_zcu': '', 'count_type': True}

                    # ===== HID Label =====
                    elif name.startswith('LabelHID') and 'label.Label' in cls:
                        in_hid_label = True
                        hid_label_data = {
                            'label_name': name.replace('Label', ''),
                            'machine_id': '',
                            'address': 0,
                            'draw_x': 0,
                            'draw_y': 0,
                            'point': 0
                        }

                    # ===== Address Node =====
                    elif name.startswith('Addr') and 'address.Addr' in cls:
                        in_addr_group = True
                        addr_depth = depth
                        current_addr_name = name
                        addr_data = {
                            'draw_x': 0, 'draw_y': 0,
                            'cad_x': 0, 'cad_y': 0,
                            'address': 0,
                            'symbol_name': '',
                            'is_station': 0,
                            'branch': False,
                            'junction': False,
                            'hid_included': -1,
                            'stopzone': 0,
                            'next_addrs': [],
                            'stations': []
                        }

                    # ===== NextAddr Connection =====
                    elif in_addr_group and name.startswith('NextAddr') and 'address.NextAddr' in cls:
                        in_next_addr = True
                        next_addr_data = {
                            'next_address': 0,
                            'distance_puls': 0,
                            'speed': 0,
                            'direction': 0,
                            'branch_direction': 0,
                            'basic_direction': True,
                            'nextposition': 0.0
                        }

                    # ===== Station =====
                    elif in_addr_group and name.startswith('Station') and 'address.Station' in cls:
                        in_station = True
                        station_data = {
                            'no': 0,
                            'port_id': '',
                            'category': 0,
                            'type': 0,
                            'position': 0
                        }

                # ===== Parameter 파싱 =====
                elif elem.tag == 'param':
                    key = elem.get('key', '')
                    value = elem.get('value', '')

                    # HID Entry 파라미터
                    if in_hid_entry and in_hid_control:
                        if key == 'id':
                            hid_entry_data['hid_id'] = value
                        elif key == 'mcpzone-no':
                            try:
                                hid_entry_data['mcpzone_no'] = int(value)
                            except:
                                hid_entry_data['mcpzone_no'] = 0

                    # MCP Sub (CutLane/Entry/Exit) 파라미터
                    elif in_mcp_sub and in_mcp_zone:
                        if key == 'start':
                            mcp_sub_data['start'] = int(value)
                        elif key == 'end':
                            mcp_sub_data['end'] = int(value)
                        elif key == 'stop-no':
                            mcp_sub_data['stop_no'] = int(value)
                        elif key == 'stop-zcu':
                            mcp_sub_data['stop_zcu'] = value
                        elif key == 'count-type':
                            mcp_sub_data['count_type'] = value == 'true'

                    # MCP Zone 파라미터
                    elif in_mcp_zone and not in_mcp_sub:
                        if key == 'id':
                            mcp_zone_data['id'] = int(value)
                        elif key == 'no':
                            mcp_zone_data['no'] = int(value)
                        elif key == 'vehicle-max':
                            mcp_zone_data['vehicle_max'] = int(value)
                        elif key == 'vehicle-precaution':
                            mcp_zone_data['vehicle_precaution'] = int(value)
                        elif key == 'type':
                            mcp_zone_data['type'] = int(value)

                    # HID Label 파라미터
                    elif in_hid_label:
                        if key == 'machine-id':
                            hid_label_data['machine_id'] = value
                        elif key == 'address':
                            try:
                                hid_label_data['address'] = int(value)
                            except:
                                hid_label_data['address'] = 0
                        elif key == 'draw-x':
                            hid_label_data['draw_x'] = float(value)
                        elif key == 'draw-y':
                            hid_label_data['draw_y'] = float(value)
                        elif key == 'point':
                            try:
                                hid_label_data['point'] = int(value)
                            except:
                                hid_label_data['point'] = 0

                    # Address Node 파라미터
                    elif in_addr_group:
                        if in_next_addr:
                            if key == 'next-address':
                                next_addr_data['next_address'] = int(value)
                            elif key == 'distance-puls':
                                next_addr_data['distance_puls'] = int(value)
                            elif key == 'speed':
                                next_addr_data['speed'] = int(value)
                            elif key == 'direction':
                                next_addr_data['direction'] = int(value)
                            elif key == 'branch-direction':
                                next_addr_data['branch_direction'] = int(value)
                            elif key == 'basic-direction':
                                next_addr_data['basic_direction'] = value == 'true'
                            elif key == 'nextposition':
                                try:
                                    next_addr_data['nextposition'] = float(value)
                                except:
                                    next_addr_data['nextposition'] = 0.0

                        elif in_station:
                            if key == 'no':
                                station_data['no'] = int(value)
                            elif key == 'port-id':
                                station_data['port_id'] = value
                            elif key == 'category':
                                station_data['category'] = int(value)
                            elif key == 'type':
                                station_data['type'] = int(value)
                            elif key == 'position':
                                station_data['position'] = int(value)

                        else:
                            if key == 'draw-x':
                                addr_data['draw_x'] = float(value)
                            elif key == 'draw-y':
                                addr_data['draw_y'] = float(value)
                            elif key == 'cad-x':
                                try:
                                    addr_data['cad_x'] = float(value)
                                except:
                                    addr_data['cad_x'] = 0.0
                            elif key == 'cad-y':
                                try:
                                    addr_data['cad_y'] = float(value)
                                except:
                                    addr_data['cad_y'] = 0.0
                            elif key == 'address':
                                addr_data['address'] = int(value)
                            elif key == 'symbol-name':
                                addr_data['symbol_name'] = value
                            elif key == 'isstation':
                                addr_data['is_station'] = int(value)
                            elif key == 'branch':
                                addr_data['branch'] = value == 'true'
                            elif key == 'junction':
                                addr_data['junction'] = value == 'true'
                            elif key == 'hid-included':
                                try:
                                    addr_data['hid_included'] = int(value)
                                except:
                                    addr_data['hid_included'] = 0
                            elif key == 'stopzone':
                                try:
                                    addr_data['stopzone'] = int(value)
                                except:
                                    addr_data['stopzone'] = 0

            elif event == 'end':
                if elem.tag == 'group':
                    name = elem.get('name', '')
                    cls = elem.get('class', '')

                    # ===== End MCP Sub =====
                    if in_mcp_sub and ('CutLane' in cls or 'Entry' in cls or 'Exit' in cls):
                        in_mcp_sub = False
                        if mcp_sub_type == 'cut_lane':
                            mcp_zone_data['cut_lanes'].append(dict(mcp_sub_data))
                        elif mcp_sub_type == 'entry':
                            mcp_zone_data['entries'].append(dict(mcp_sub_data))
                        elif mcp_sub_type == 'exit':
                            mcp_zone_data['exits'].append(dict(mcp_sub_data))

                    # ===== End MCP Zone =====
                    elif in_mcp_zone and 'McpZone' in cls and 'CutLane' not in cls and 'Entry' not in cls and 'Exit' not in cls:
                        in_mcp_zone = False
                        in_mcp_sub = False
                        mcp_zones.append(dict(mcp_zone_data))

                    # ===== End MCP Zone Control =====
                    elif 'McpZoneControl' in cls:
                        in_mcp_zone_control = False

                    # ===== End HID Entry =====
                    elif in_hid_entry and 'hid.Hid' in cls and 'HidControl' not in cls:
                        in_hid_entry = False
                        if hid_entry_data['hid_id']:
                            hid_controls.append(dict(hid_entry_data))

                    # ===== End HID Control =====
                    elif in_hid_control and 'hid.HidControl' in cls:
                        in_hid_control = False

                    # ===== End HID Label =====
                    elif in_hid_label and name.startswith('LabelHID') and 'label.Label' in cls:
                        in_hid_label = False
                        if hid_label_data['machine_id']:
                            hid_zones.append(dict(hid_label_data))

                    # ===== End NextAddr =====
                    elif in_next_addr and name.startswith('NextAddr') and 'address.NextAddr' in cls:
                        in_next_addr = False
                        if next_addr_data['next_address'] > 0:
                            addr_data['next_addrs'].append(dict(next_addr_data))

                    # ===== End Station =====
                    elif in_station and name.startswith('Station') and 'address.Station' in cls:
                        in_station = False
                        if station_data['port_id']:
                            addr_data['stations'].append(dict(station_data))

                    # ===== End Address Node =====
                    elif in_addr_group and name.startswith('Addr') and 'address.Addr' in cls:
                        in_addr_group = False
                        in_next_addr = False
                        in_station = False

                        addr_id = addr_data['address']
                        if addr_id > 0:
                            nodes[addr_id] = {
                                'id': addr_id,
                                'x': addr_data['draw_x'],
                                'y': addr_data['draw_y'],
                                'cad_x': addr_data['cad_x'],
                                'cad_y': addr_data['cad_y'],
                                'symbol': addr_data['symbol_name'],
                                'is_station': addr_data['is_station'],
                                'branch': addr_data['branch'],
                                'junction': addr_data['junction'],
                                'hid_included': addr_data['hid_included'],
                                'stopzone': addr_data['stopzone'],
                                'stations': addr_data['stations']
                            }

                            for na in addr_data['next_addrs']:
                                edges.append({
                                    'from': addr_id,
                                    'to': na['next_address'],
                                    'distance': na['distance_puls'],
                                    'speed': na['speed'],
                                    'direction': na['direction'],
                                    'branch_dir': na['branch_direction']
                                })

                            count += 1
                            if count % 500 == 0 and progress_callback:
                                progress_callback(f"파싱 중... {count}개 노드", int(count / 50))

                depth -= 1
                elem.clear()

        # ===== Post-Processing =====

        # 좌표 범위 계산
        if nodes:
            xs = [n['x'] for n in nodes.values()]
            ys = [n['y'] for n in nodes.values()]
            bounds = {
                'min_x': min(xs), 'max_x': max(xs),
                'min_y': min(ys), 'max_y': max(ys)
            }
        else:
            bounds = {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}

        # 스테이션 요약
        station_nodes = [n for n in nodes.values() if n['stations']]
        all_stations = []
        for n in station_nodes:
            for s in n['stations']:
                all_stations.append({
                    'port_id': s['port_id'],
                    'category': s['category'],
                    'type': s['type'],
                    'no': s['no'],
                    'position': s['position'],
                    'node_id': n['id'],
                    'x': n['x'],
                    'y': n['y']
                })

        # Zone → Address 매핑
        zone_addr_map = {}
        for z in mcp_zones:
            zid = z['id']
            addrs = set()
            for e in z['entries']:
                addrs.add(e['start']); addrs.add(e['end'])
            for e in z['exits']:
                addrs.add(e['start']); addrs.add(e['end'])
            for c in z['cut_lanes']:
                addrs.add(c['start']); addrs.add(c['end'])
            zone_addr_map[zid] = list(addrs)

        # HID → MCP Zone 매핑 및 마스터 데이터 구축
        mcp_zone_map = {z['no']: z for z in mcp_zones}
        hid_label_map = {}
        for h in hid_zones:
            mid = h['machine_id']
            if mid.startswith('HID-'):
                hid_id = mid[4:]
                paren = hid_id.find('(')
                if paren > 0:
                    hid_id = hid_id[:paren]
                hid_label_map[hid_id] = h

        hid_master = []
        for hc in sorted(hid_controls, key=lambda x: x['mcpzone_no']):
            hid_id = hc['hid_id']
            mcpzone_no = hc['mcpzone_no']
            zone = mcp_zone_map.get(mcpzone_no, {})
            label = hid_label_map.get(hid_id, {})
            full_name = label.get('machine_id', f'HID-{hid_id}')

            entries = zone.get('entries', [])
            exits = zone.get('exits', [])
            in_lanes = '; '.join([f"{e['start']}→{e['end']}" for e in entries])
            out_lanes = '; '.join([f"{e['start']}→{e['end']}" for e in exits])

            zcu = ''
            for e in entries:
                if e.get('stop_zcu'):
                    zcu = e['stop_zcu']
                    break

            hid_master.append({
                'zone_id': mcpzone_no,
                'hid_id': hid_id,
                'full_name': full_name,
                'address': label.get('address', 0),
                'vehicle_max': zone.get('vehicle_max', 0),
                'vehicle_precaution': zone.get('vehicle_precaution', 0),
                'zone_type': zone.get('type', 0),
                'in_count': len(entries),
                'out_count': len(exits),
                'in_lanes': in_lanes,
                'out_lanes': out_lanes,
                'zcu': zcu,
            })

        result = {
            'fab_name': fab_name,
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'total_stations': len(all_stations),
            'total_mcp_zones': len(mcp_zones),
            'total_hid_zones': len(hid_zones),
            'bounds': bounds,
            'nodes': list(nodes.values()),
            'edges': edges,
            'stations': all_stations,
            'mcp_zones': mcp_zones,
            'hid_zones': hid_zones,
            'hid_master': hid_master,
            'zone_addr_map': zone_addr_map
        }

        if progress_callback:
            progress_callback("파싱 완료!", 100)

        return result

    @staticmethod
    def parse_zip(zip_path, fab_name='M14-Pro', progress_callback=None):
        """Extract layout.xml from ZIP and parse it.

        Searches for: layout.xml, LAYOUT/LAYOUT.XML, */layout.xml

        Args:
            zip_path: Path to ZIP file
            fab_name: FAB 이름
            progress_callback: 진행 상황 콜백 함수

        Returns:
            dict: 파싱된 레이아웃 데이터
        """
        if progress_callback:
            progress_callback("ZIP 추출 중...", 10)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            xml_name = None
            for name in zf.namelist():
                if name.lower().endswith('layout.xml'):
                    xml_name = name
                    break

            if not xml_name:
                raise FileNotFoundError("ZIP 내에 layout.xml을 찾을 수 없습니다")

            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extract(xml_name, tmpdir)
                xml_path = os.path.join(tmpdir, xml_name)
                return OHTLayoutParser.parse_xml(xml_path, fab_name, progress_callback)

    @staticmethod
    def load_json(json_path):
        """Load previously parsed JSON data

        Args:
            json_path: Path to JSON file

        Returns:
            dict: 레이아웃 데이터
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)


# ============================================================================
# HTML EXPORT ENGINE (Three.js 3D Viewer)
# ============================================================================

def generate_oht_html(project_data: Dict[str, Any]) -> str:
    """Generate a complete standalone HTML file with Three.js 3D visualization.

    Creates an interactive 3D OHT layout viewer with:
    - Rail tracks using InstancedMesh
    - Address nodes and stations
    - MCP zone visualization
    - OHT vehicle simulation
    - Control panels and statistics

    Args:
        project_data: OHT project data dictionary from parser

    Returns:
        str: Complete HTML file content
    """

    # Data sanitization (GUI 변환 후 데이터 또는 파서 원본 데이터 모두 지원)
    fab_name = project_data.get('fab_name', 'M14-Pro')
    nodes = project_data.get('nodes', [])
    stations = project_data.get('stations', [])
    mcp_zones = project_data.get('mcp_zones', project_data.get('zones', []))
    hid_zones = project_data.get('hid_zones', [])
    hid_master = project_data.get('hid_master', [])
    zone_addr_map = project_data.get('zone_addr_map', {})

    # edges: 'start'/'end' 또는 'from'/'to' 둘 다 지원
    raw_edges = project_data.get('edges', [])
    edges = []
    for e in raw_edges:
        edges.append({
            'from': e.get('from', e.get('start', 0)),
            'to': e.get('to', e.get('end', 0)),
            'distance': e.get('distance', 0),
            'speed': e.get('speed', 0),
            'direction': e.get('direction', 0),
        })

    # bounds 계산 (없으면 nodes에서 자동 계산)
    bounds = project_data.get('bounds', {})
    if not bounds or (bounds.get('min_x', 0) == 0 and bounds.get('max_x', 0) == 0 and nodes):
        xs = [n.get('x', 0) for n in nodes]
        ys = [n.get('y', 0) for n in nodes]
        bounds = {
            'min_x': min(xs) if xs else 0, 'max_x': max(xs) if xs else 100,
            'min_y': min(ys) if ys else 0, 'max_y': max(ys) if ys else 100
        }

    width = (bounds.get('max_x', 100) - bounds.get('min_x', 0)) or 100
    height = (bounds.get('max_y', 100) - bounds.get('min_y', 0)) or 100
    center_x = bounds.get('min_x', 0) + width / 2
    center_y = bounds.get('min_y', 0) + height / 2

    # 맵 전용 데이터 (3D 렌더링 + Zone 위치 조회용)
    layout_data = {
        'fab_name': fab_name,
        'nodes': nodes,
        'edges': edges,
        'stations': stations,
        'mcp_zones': mcp_zones,
        'zone_addr_map': zone_addr_map,
        'bounds': bounds,
        'total_nodes': len(nodes),
        'total_edges': len(edges),
        'total_stations': len(stations),
    }

    layout_json = json.dumps(layout_data, indent=2)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AMOS MAP SYSTEM PRO - OHT Layout Viewer</title>

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            overflow: hidden;
            height: 100vh;
        }}

        #canvas {{
            display: block;
            width: 100%;
            height: 100%;
        }}

        /* Header */
        #header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 100%);
            border-bottom: 2px solid #00d4ff;
            display: flex;
            align-items: center;
            padding: 0 20px;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0, 212, 255, 0.2);
        }}

        .header-title {{
            font-size: 20px;
            font-weight: bold;
            color: #00d4ff;
            text-shadow: 0 0 10px #00d4ff;
            margin-right: 20px;
            letter-spacing: 2px;
        }}

        .fab-badge {{
            background: linear-gradient(135deg, #ff6600, #ff9900);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }}

        .header-spacer {{
            flex: 1;
        }}

        .header-controls {{
            display: flex;
            gap: 10px;
        }}

        .header-btn {{
            background: rgba(0, 212, 255, 0.2);
            border: 1px solid #00d4ff;
            color: #00d4ff;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.3s;
        }}

        .header-btn:hover {{
            background: rgba(0, 212, 255, 0.4);
            box-shadow: 0 0 10px #00d4ff;
        }}

        /* Left Panel */
        #leftPanel {{
            position: fixed;
            left: 0;
            top: 60px;
            width: 250px;
            height: calc(100vh - 60px);
            background: rgba(10, 10, 26, 0.95);
            border-right: 1px solid #00d4ff;
            overflow-y: auto;
            z-index: 90;
            padding: 15px;
        }}

        .panel-section {{
            margin-bottom: 20px;
            background: rgba(0, 212, 255, 0.05);
            padding: 12px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 4px;
        }}

        .section-title {{
            font-size: 12px;
            font-weight: bold;
            color: #00d4ff;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin: 5px 0;
            color: #a0a0a0;
        }}

        .stat-value {{
            color: #44ff88;
            font-weight: bold;
        }}

        .control-group {{
            margin: 10px 0;
        }}

        .control-label {{
            font-size: 11px;
            color: #a0a0a0;
            margin-bottom: 5px;
        }}

        .slider {{
            width: 100%;
            height: 4px;
            border-radius: 2px;
            background: rgba(0, 212, 255, 0.3);
            outline: none;
            -webkit-appearance: none;
            appearance: none;
        }}

        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00d4ff;
            cursor: pointer;
            box-shadow: 0 0 5px #00d4ff;
        }}

        .slider::-moz-range-thumb {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00d4ff;
            cursor: pointer;
            border: none;
            box-shadow: 0 0 5px #00d4ff;
        }}

        .btn-group {{
            display: flex;
            gap: 5px;
            margin-top: 5px;
        }}

        .btn {{
            flex: 1;
            padding: 6px;
            background: rgba(0, 212, 255, 0.2);
            border: 1px solid #00d4ff;
            color: #00d4ff;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            transition: all 0.2s;
        }}

        .btn:hover {{
            background: rgba(0, 212, 255, 0.4);
        }}

        .btn.active {{
            background: #00d4ff;
            color: #0a0a1a;
        }}

        /* Right Panel */
        #rightPanel {{
            position: fixed;
            right: 0;
            top: 60px;
            width: 280px;
            height: calc(100vh - 60px);
            background: rgba(10, 10, 26, 0.95);
            border-left: 1px solid #00d4ff;
            overflow-y: auto;
            z-index: 90;
            padding: 15px;
        }}

        .tab-buttons {{
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
        }}

        .tab-btn {{
            flex: 1;
            padding: 6px;
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            color: #a0a0a0;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            transition: all 0.2s;
        }}

        .tab-btn.active {{
            background: #00d4ff;
            color: #0a0a1a;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .list-item {{
            background: rgba(0, 212, 255, 0.05);
            padding: 8px;
            margin: 5px 0;
            border-radius: 3px;
            border-left: 2px solid #00d4ff;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .list-item:hover {{
            background: rgba(0, 212, 255, 0.15);
            transform: translateX(3px);
        }}

        .item-name {{
            color: #00d4ff;
            font-weight: bold;
        }}

        .item-detail {{
            color: #a0a0a0;
            font-size: 10px;
            margin-top: 3px;
        }}

        /* Floating Control Panel */
        #floatingControl {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(10, 10, 26, 0.95);
            border: 1px solid #00d4ff;
            border-radius: 8px;
            padding: 15px;
            z-index: 85;
            min-width: 250px;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        }}

        .control-row {{
            display: flex;
            align-items: center;
            margin: 8px 0;
            gap: 10px;
        }}

        .control-row label {{
            font-size: 11px;
            color: #a0a0a0;
            min-width: 80px;
        }}

        .control-row input {{
            flex: 1;
        }}

        /* Minimap */
        #minimap {{
            position: fixed;
            top: 80px;
            left: 20px;
            width: 150px;
            height: 150px;
            background: rgba(10, 10, 26, 0.9);
            border: 1px solid #00d4ff;
            border-radius: 4px;
            z-index: 80;
            cursor: pointer;
        }}

        /* Popup */
        #popup {{
            position: fixed;
            background: rgba(10, 10, 26, 0.98);
            border: 2px solid #00d4ff;
            border-radius: 8px;
            padding: 15px;
            z-index: 200;
            display: none;
            min-width: 200px;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }}

        .popup-title {{
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 13px;
        }}

        .popup-content {{
            color: #a0a0a0;
            font-size: 11px;
        }}

        .popup-row {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }}

        .popup-label {{
            color: #a0a0a0;
        }}

        .popup-value {{
            color: #44ff88;
            font-weight: bold;
        }}

        .close-btn {{
            position: absolute;
            top: 5px;
            right: 5px;
            background: rgba(255, 68, 68, 0.5);
            border: 1px solid #ff4444;
            color: #ff4444;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }}

        .close-btn:hover {{
            background: rgba(255, 68, 68, 0.8);
            box-shadow: 0 0 10px #ff4444;
        }}

        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 6px;
        }}

        ::-webkit-scrollbar-track {{
            background: rgba(0, 212, 255, 0.05);
        }}

        ::-webkit-scrollbar-thumb {{
            background: rgba(0, 212, 255, 0.3);
            border-radius: 3px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(0, 212, 255, 0.5);
        }}
    </style>
</head>
<body>
    <!-- Canvas for Three.js -->
    <canvas id="canvas"></canvas>

    <!-- Header -->
    <div id="header">
        <div class="header-title">AMOS MAP SYSTEM PRO</div>
        <div style="color: #44ff88; font-size: 12px;">OHT FAB Layout</div>
        <div class="header-spacer"></div>
        <div class="fab-badge">{fab_name}</div>
        <div class="header-spacer" style="flex: 0.5;"></div>
        <div class="header-controls">
            <button class="header-btn" id="dayNightBtn">🌙 Night</button>
            <button class="header-btn" id="exportBtn">📥 Export</button>
            <button class="header-btn" id="resetViewBtn">🔄 Reset</button>
        </div>
    </div>

    <!-- Left Panel: Statistics & Controls -->
    <div id="leftPanel">
        <div class="panel-section">
            <div class="section-title">📊 Layout Statistics</div>
            <div class="stat-row">
                <span>Nodes:</span>
                <span class="stat-value" id="nodeCount">{len(nodes)}</span>
            </div>
            <div class="stat-row">
                <span>Edges:</span>
                <span class="stat-value" id="edgeCount">{len(edges)}</span>
            </div>
            <div class="stat-row">
                <span>Stations:</span>
                <span class="stat-value" id="stationCount">{len(stations)}</span>
            </div>
            <div class="stat-row">
                <span>MCP Zones:</span>
                <span class="stat-value" id="zoneCount">{len(mcp_zones)}</span>
            </div>
        </div>

        <div class="panel-section">
            <div class="section-title">👁️ View Presets</div>
            <div class="btn-group">
                <button class="btn" id="viewTopBtn">Top</button>
                <button class="btn" id="viewFrontBtn">Front</button>
                <button class="btn" id="viewSideBtn">Side</button>
            </div>
            <div class="btn-group">
                <button class="btn" id="viewIsometric">ISO</button>
                <button class="btn" id="viewPerspective">3D</button>
            </div>
        </div>

        <div class="panel-section">
            <div class="section-title">🔍 Search</div>
            <input type="text" id="searchInput" placeholder="Node ID..."
                   style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #00d4ff;
                          background: rgba(0, 212, 255, 0.1); color: #e0e0e0; font-size: 11px;">
            <div id="searchResults" style="margin-top: 8px; max-height: 100px; overflow-y: auto;"></div>
        </div>
    </div>

    <!-- Right Panel: Zone List -->
    <div id="rightPanel">
        <div class="panel-section" style="margin-top: 10px;">
            <div class="section-title">📍 MCP Zones</div>
            <div style="margin-bottom: 8px;">
                <input type="text" id="zoneSearch" placeholder="Search Zone..."
                       style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #00d4ff;
                              background: rgba(0, 212, 255, 0.1); color: #e0e0e0; font-size: 11px;">
            </div>
            <div id="zoneList"></div>
        </div>
    </div>

    <!-- Minimap -->
    <canvas id="minimap"></canvas>

    <!-- Floating Control Panel -->
    <div id="floatingControl">
        <div class="control-row">
            <label>Rail Height</label>
            <input type="range" class="slider" id="railHeightSlider" min="5" max="50" value="15">
        </div>
        <div class="control-row">
            <label>Rail Thickness</label>
            <input type="range" class="slider" id="railThicknessSlider" min="0.5" max="5" value="2">
        </div>
    </div>

    <!-- Info Popup -->
    <div id="popup">
        <button class="close-btn">✕</button>
        <div class="popup-title" id="popupTitle">Node Info</div>
        <div class="popup-content" id="popupContent"></div>
    </div>

    <!-- Three.js Script (동기 로딩 필수) -->
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>

    <script>
        // Embedded Layout Data
        const LAYOUT_DATA = {layout_json};

        // 노드 맵 (O(1) 조회용) - 전역
        const nodeMap = {{}};
        LAYOUT_DATA.nodes.forEach(n => {{ nodeMap[n.id] = n; }});

        // 스테이션 맵 (node_id → station)
        const stationByNode = {{}};
        (LAYOUT_DATA.stations || []).forEach(s => {{
            const nid = s.node_id || s.node;
            if (nid) stationByNode[nid] = s;
        }});

        // Global state
        const state = {{
            camera: null,
            scene: null,
            renderer: null,
            controls: null,
            dayMode: false,
            selectedNode: null,
            rails: [],
            nodeMarkers: null,
            labelSprites: [],
            minimapCtx: null,
            showLabels: true,
        }};

        // Initialize Three.js scene
        function initScene() {{
            if (typeof THREE === 'undefined') {{
                console.error('Three.js not loaded!');
                document.body.innerHTML = '<h1 style="color:red;text-align:center;margin-top:200px">Three.js 로딩 실패. 인터넷 연결을 확인하세요.</h1>';
                return;
            }}

            const canvas = document.getElementById('canvas');
            const width = window.innerWidth;
            const height = window.innerHeight;

            // 좌표 범위 계산
            const cx = (LAYOUT_DATA.bounds.min_x + LAYOUT_DATA.bounds.max_x) / 2;
            const cy = (LAYOUT_DATA.bounds.min_y + LAYOUT_DATA.bounds.max_y) / 2;
            const rangeX = LAYOUT_DATA.bounds.max_x - LAYOUT_DATA.bounds.min_x;
            const rangeY = LAYOUT_DATA.bounds.max_y - LAYOUT_DATA.bounds.min_y;
            const rangeMax = Math.max(rangeX, rangeY) || 100;
            const camDist = rangeMax * 0.8;

            // 좌표 범위에 비례하는 크기 상수
            const UNIT = rangeMax / 500;  // 기본 단위 (노드 크기 등에 사용)
            const RAIL_H = rangeMax * 0.01;  // 레일 높이

            // Scene setup
            state.scene = new THREE.Scene();
            state.scene.background = new THREE.Color(0x0a0a1a);
            state.scene.fog = new THREE.Fog(0x0a0a1a, rangeMax * 2, rangeMax * 8);

            state.camera = new THREE.PerspectiveCamera(60, width / height, UNIT * 0.1, rangeMax * 10);
            state.camera.position.set(cx, camDist, cy + camDist * 0.8);

            // Renderer
            state.renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
            state.renderer.setSize(width, height);
            state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

            // Controls
            state.controls = new THREE.OrbitControls(state.camera, canvas);
            state.controls.enableDamping = true;
            state.controls.dampingFactor = 0.05;
            state.controls.target.set(cx, 0, cy);
            state.controls.minDistance = UNIT * 5;
            state.controls.maxDistance = rangeMax * 5;

            // Lighting
            state.scene.add(new THREE.AmbientLight(0xffffff, 0.6));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(cx + rangeMax * 0.5, rangeMax, cy + rangeMax * 0.5);
            state.scene.add(dirLight);

            // Floor
            const floorSize = rangeMax * 1.5;
            const floorGeom = new THREE.PlaneGeometry(floorSize, floorSize);
            const floorMat = new THREE.MeshStandardMaterial({{ color: 0x0a0a2a, roughness: 0.8 }});
            const floor = new THREE.Mesh(floorGeom, floorMat);
            floor.rotation.x = -Math.PI / 2;
            floor.position.set(cx, -UNIT * 2, cy);
            state.scene.add(floor);

            // Grid
            const gridHelper = new THREE.GridHelper(floorSize, 50, 0x00d4ff, 0x1a3a4a);
            gridHelper.position.set(cx, -UNIT, cy);
            state.scene.add(gridHelper);

            // 맵만 그리기: 레일 선 + 노드 점 + 텍스트 라벨
            createRails();
            createNodes();
            createLabels();

            // Minimap
            initMinimap();

            // Event listeners
            setupEventListeners();
            populateZoneList();

            console.log(`[OHT 3D] 초기화 완료: ${{LAYOUT_DATA.nodes.length}} nodes, ${{LAYOUT_DATA.edges.length}} edges`);

            // Start animation loop
            animate();
        }}

        function createRails() {{
            // 레일을 LineSegments로 렌더링 (대규모 최적화)
            const positions = [];
            let validEdges = 0;
            LAYOUT_DATA.edges.forEach(edge => {{
                const fromN = nodeMap[edge.from];
                const toN = nodeMap[edge.to];
                if (!fromN || !toN) return;
                positions.push(fromN.x, RAIL_H, fromN.y);
                positions.push(toN.x, RAIL_H, toN.y);
                validEdges++;
            }});

            console.log(`[Rails] ${{validEdges}} / ${{LAYOUT_DATA.edges.length}} edges rendered`);

            if (positions.length > 0) {{
                const railGeom = new THREE.BufferGeometry();
                railGeom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
                const railMat = new THREE.LineBasicMaterial({{ color: 0x00d4ff, linewidth: 2 }});
                const railLines = new THREE.LineSegments(railGeom, railMat);
                state.rails.push(railLines);
                state.scene.add(railLines);
            }}

        }}

        function createNodes() {{
            const nodeCount = LAYOUT_DATA.nodes.length;
            if (nodeCount === 0) return;

            // 노드: 아주 작은 구 (스테이션=빨강, 분기=주황, 교차=파랑, 일반=녹색)
            const geometry = new THREE.SphereGeometry(UNIT * 1.5, 6, 6);
            const material = new THREE.MeshBasicMaterial({{ color: 0x44ff88 }});

            const instancedMesh = new THREE.InstancedMesh(geometry, material, nodeCount);
            const dummy = new THREE.Object3D();
            const stationColor = new THREE.Color(0xff4444);
            const branchColor = new THREE.Color(0xffaa00);
            const junctionColor = new THREE.Color(0x4488ff);
            const defaultColor = new THREE.Color(0x44ff88);

            LAYOUT_DATA.nodes.forEach((node, i) => {{
                dummy.position.set(node.x, RAIL_H, node.y);
                dummy.updateMatrix();
                instancedMesh.setMatrixAt(i, dummy.matrix);
                if (node.is_station) instancedMesh.setColorAt(i, stationColor);
                else if (node.branch) instancedMesh.setColorAt(i, branchColor);
                else if (node.junction) instancedMesh.setColorAt(i, junctionColor);
                else instancedMesh.setColorAt(i, defaultColor);
            }});

            instancedMesh.instanceMatrix.needsUpdate = true;
            if (instancedMesh.instanceColor) instancedMesh.instanceColor.needsUpdate = true;
            state.nodeMarkers = instancedMesh;
            state.scene.add(instancedMesh);
        }}

        // 텍스트 라벨 생성 (스테이션 Port_ID만 표시 — 깔끔하게)
        function createLabels() {{
            function makeTextSprite(text, color) {{
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 256;
                canvas.height = 64;
                ctx.fillStyle = 'rgba(0,0,0,0.6)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.font = 'bold 28px monospace';
                ctx.fillStyle = color || '#ffffff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, 128, 32);
                const tex = new THREE.CanvasTexture(canvas);
                const mat = new THREE.SpriteMaterial({{ map: tex, transparent: true }});
                const sprite = new THREE.Sprite(mat);
                sprite.scale.set(UNIT * 40, UNIT * 10, 1);
                return sprite;
            }}

            // 스테이션 라벨
            (LAYOUT_DATA.stations || []).forEach(s => {{
                const nid = s.node_id || s.node;
                const node = nodeMap[nid];
                if (!node) return;
                const label = s.port_id || ('S-' + nid);
                const sprite = makeTextSprite(label, '#ff6666');
                sprite.position.set(node.x, RAIL_H + UNIT * 10, node.y);
                state.scene.add(sprite);
                state.labelSprites.push(sprite);
            }});

            console.log(`[Labels] ${{state.labelSprites.length}} station labels created`);
        }}

        // Raycaster: 노드/스테이션 클릭 → 정보 팝업
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        document.getElementById('canvas').addEventListener('click', (event) => {{
            mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

            raycaster.setFromCamera(mouse, state.camera);

            if (state.nodeMarkers) {{
                const intersects = raycaster.intersectObject(state.nodeMarkers);
                if (intersects.length > 0) {{
                    const idx = intersects[0].instanceId;
                    if (idx !== undefined && idx < LAYOUT_DATA.nodes.length) {{
                        const node = LAYOUT_DATA.nodes[idx];
                        const station = stationByNode[node.id];

                        let info = `<b>Node ID:</b> ${{node.id}}<br>`;
                        info += `<b>좌표:</b> (${{node.x.toFixed(1)}}, ${{node.y.toFixed(1)}})<br>`;
                        if (node.cad_x) info += `<b>CAD:</b> (${{node.cad_x.toFixed(1)}}, ${{node.cad_y.toFixed(1)}})<br>`;
                        info += `<b>타입:</b> ${{node.is_station ? '스테이션' : node.branch ? '분기점' : node.junction ? '교차점' : '일반'}}<br>`;
                        if (node.symbol) info += `<b>Symbol:</b> ${{node.symbol}}<br>`;
                        if (node.stopzone) info += `<b>StopZone:</b> ${{node.stopzone}}<br>`;

                        if (station) {{
                            info += `<hr style="border-color:#00d4ff;margin:4px 0">`;
                            info += `<b style="color:#ff6666">🏭 Station</b><br>`;
                            info += `<b>Port ID:</b> ${{station.port_id || '-'}}<br>`;
                            info += `<b>Category:</b> ${{station.category || '-'}}<br>`;
                            info += `<b>Type:</b> ${{station.type || '-'}}<br>`;
                            info += `<b>No:</b> ${{station.no || '-'}}<br>`;
                        }}

                        const popup = document.getElementById('popup');
                        document.getElementById('popupTitle').textContent = station ? `Station: ${{station.port_id}}` : `Node #${{node.id}}`;
                        document.getElementById('popupContent').innerHTML = info;
                        popup.style.display = 'block';
                        popup.style.left = (event.clientX + 15) + 'px';
                        popup.style.top = (event.clientY - 10) + 'px';
                    }}
                }}
            }}
        }});

        function initMinimap() {{
            const mmCanvas = document.getElementById('minimap');
            if (!mmCanvas) return;
            state.minimapCtx = mmCanvas.getContext('2d');

            const w = mmCanvas.width;
            const h = mmCanvas.height;
            const margin = 5;
            const contentW = w - 2 * margin;
            const contentH = h - 2 * margin;

            const bounds = LAYOUT_DATA.bounds;
            const rangeX = (bounds.max_x - bounds.min_x) || 1;
            const rangeY = (bounds.max_y - bounds.min_y) || 1;

            function drawMinimap() {{
                const ctx = state.minimapCtx;
                ctx.fillStyle = '#0a0a1a';
                ctx.fillRect(0, 0, w, h);
                ctx.strokeStyle = '#00d4ff';
                ctx.strokeRect(margin, margin, contentW, contentH);

                // edges 샘플링
                ctx.strokeStyle = '#004466';
                ctx.lineWidth = 0.5;
                const edgeStep = Math.max(1, Math.floor(LAYOUT_DATA.edges.length / 5000));
                ctx.beginPath();
                for (let ei = 0; ei < LAYOUT_DATA.edges.length; ei += edgeStep) {{
                    const edge = LAYOUT_DATA.edges[ei];
                    const fromN = nodeMap[edge.from];
                    const toN = nodeMap[edge.to];
                    if (fromN && toN) {{
                        ctx.moveTo(margin + ((fromN.x - bounds.min_x) / rangeX) * contentW,
                                   margin + ((fromN.y - bounds.min_y) / rangeY) * contentH);
                        ctx.lineTo(margin + ((toN.x - bounds.min_x) / rangeX) * contentW,
                                   margin + ((toN.y - bounds.min_y) / rangeY) * contentH);
                    }}
                }}
                ctx.stroke();

                // nodes 샘플링
                ctx.fillStyle = '#44ff88';
                const nodeStep = Math.max(1, Math.floor(LAYOUT_DATA.nodes.length / 3000));
                for (let ni = 0; ni < LAYOUT_DATA.nodes.length; ni += nodeStep) {{
                    const node = LAYOUT_DATA.nodes[ni];
                    ctx.fillRect(
                        margin + ((node.x - bounds.min_x) / rangeX) * contentW,
                        margin + ((node.y - bounds.min_y) / rangeY) * contentH, 1, 1);
                }}

                // 스테이션 노드만 빨간색으로 미니맵에 표시
                ctx.fillStyle = '#ff4444';
                const stationSet = new Set();
                (LAYOUT_DATA.stations || []).forEach(s => {{ if (s.node_id) stationSet.add(s.node_id); }});
                for (let ni = 0; ni < LAYOUT_DATA.nodes.length; ni += nodeStep) {{
                    const node = LAYOUT_DATA.nodes[ni];
                    if (stationSet.has(node.id)) {{
                        ctx.fillRect(
                            margin + ((node.x - bounds.min_x) / rangeX) * contentW - 1,
                            margin + ((node.y - bounds.min_y) / rangeY) * contentH - 1, 2, 2);
                    }}
                }}
            }}

            drawMinimap();
            // 미니맵 주기적 갱신
            setInterval(drawMinimap, 2000);
        }}

        function setupEventListeners() {{
            // Day/Night toggle
            document.getElementById('dayNightBtn').addEventListener('click', () => {{
                state.dayMode = !state.dayMode;
                const bgColor = state.dayMode ? 0xccddff : 0x0a0a1a;
                state.scene.background = new THREE.Color(bgColor);
                state.scene.fog.color = new THREE.Color(bgColor);
                document.getElementById('dayNightBtn').textContent = state.dayMode ? '🌞 Day' : '🌙 Night';
            }});

            // Reset view
            document.getElementById('resetViewBtn').addEventListener('click', () => {{
                const cx = (LAYOUT_DATA.bounds.min_x + LAYOUT_DATA.bounds.max_x) / 2;
                const cy = (LAYOUT_DATA.bounds.min_y + LAYOUT_DATA.bounds.max_y) / 2;
                const rangeX = LAYOUT_DATA.bounds.max_x - LAYOUT_DATA.bounds.min_x;
                const rangeY = LAYOUT_DATA.bounds.max_y - LAYOUT_DATA.bounds.min_y;
                const dist = Math.max(rangeX, rangeY) * 0.8;
                state.camera.position.set(cx, dist, cy + dist * 0.8);
                state.controls.target.set(cx, 0, cy);
            }});

            // View presets
            const cx = (LAYOUT_DATA.bounds.min_x + LAYOUT_DATA.bounds.max_x) / 2;
            const cy = (LAYOUT_DATA.bounds.min_y + LAYOUT_DATA.bounds.max_y) / 2;
            const rangeMax = Math.max(LAYOUT_DATA.bounds.max_x - LAYOUT_DATA.bounds.min_x,
                                       LAYOUT_DATA.bounds.max_y - LAYOUT_DATA.bounds.min_y);

            document.getElementById('viewTopBtn').addEventListener('click', () => {{
                state.camera.position.set(cx, rangeMax, cy);
                state.controls.target.set(cx, 0, cy);
            }});
            document.getElementById('viewFrontBtn').addEventListener('click', () => {{
                state.camera.position.set(cx, rangeMax * 0.3, cy + rangeMax * 0.8);
                state.controls.target.set(cx, 0, cy);
            }});
            document.getElementById('viewSideBtn').addEventListener('click', () => {{
                state.camera.position.set(cx + rangeMax * 0.8, rangeMax * 0.3, cy);
                state.controls.target.set(cx, 0, cy);
            }});

            // Close popup
            document.getElementById('popup').querySelector('.close-btn').addEventListener('click', () => {{
                document.getElementById('popup').style.display = 'none';
            }});

            // Window resize
            window.addEventListener('resize', () => {{
                state.camera.aspect = window.innerWidth / window.innerHeight;
                state.camera.updateProjectionMatrix();
                state.renderer.setSize(window.innerWidth, window.innerHeight);
            }});

            // Search
            document.getElementById('searchInput').addEventListener('keyup', (e) => {{
                if (e.key === 'Enter') {{
                    const q = e.target.value.trim();
                    const nid = parseInt(q);
                    const found = nodeMap[nid];
                    if (found) {{
                        state.camera.position.set(found.x, rangeMax * 0.05, found.y + rangeMax * 0.05);
                        state.controls.target.set(found.x, 0, found.y);
                        document.getElementById('searchResults').innerHTML =
                            `<div style="color:#44ff88;font-size:11px">Node #${{nid}} → (${{found.x.toFixed(0)}}, ${{found.y.toFixed(0)}})</div>`;
                    }} else {{
                        // 스테이션 검색
                        const st = LAYOUT_DATA.stations.find(s => s.port_id && s.port_id.toUpperCase().includes(q.toUpperCase()));
                        if (st) {{
                            state.camera.position.set(st.x, rangeMax * 0.05, st.y + rangeMax * 0.05);
                            state.controls.target.set(st.x, 0, st.y);
                            document.getElementById('searchResults').innerHTML =
                                `<div style="color:#ff6666;font-size:11px">Station ${{st.port_id}} → (${{st.x.toFixed(0)}}, ${{st.y.toFixed(0)}})</div>`;
                        }} else {{
                            document.getElementById('searchResults').innerHTML =
                                `<div style="color:#ff4444;font-size:11px">검색 결과 없음</div>`;
                        }}
                    }}
                }}
            }});
        }}

        // Zone 하이라이트용 (이전 하이라이트 제거)
        let zoneHighlight = null;
        let zoneHighlightBorder = null;

        function focusZone(zoneId) {{
            // 이전 하이라이트 제거
            if (zoneHighlight) {{ state.scene.remove(zoneHighlight); zoneHighlight = null; }}
            if (zoneHighlightBorder) {{ state.scene.remove(zoneHighlightBorder); zoneHighlightBorder = null; }}

            const addrs = (LAYOUT_DATA.zone_addr_map || {{}})[String(zoneId)] || [];
            const zNodes = addrs.map(id => nodeMap[id]).filter(Boolean);
            if (zNodes.length === 0) return;

            const xs = zNodes.map(n => n.x);
            const ys = zNodes.map(n => n.y);
            const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
            const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
            const w = (Math.max(...xs) - Math.min(...xs)) || 100;
            const h = (Math.max(...ys) - Math.min(...ys)) || 100;
            const span = Math.max(w, h);

            // 카메라 이동
            state.camera.position.set(cx, span * 0.8, cy + span * 0.6);
            state.controls.target.set(cx, 0, cy);

            // 반투명 하이라이트 평면
            const geom = new THREE.PlaneGeometry(w + 40, h + 40);
            const mat = new THREE.MeshBasicMaterial({{
                color: 0xff6600, transparent: true, opacity: 0.15, side: THREE.DoubleSide
            }});
            zoneHighlight = new THREE.Mesh(geom, mat);
            zoneHighlight.rotation.x = -Math.PI / 2;
            zoneHighlight.position.set(cx, RAIL_H + UNIT, cy);
            state.scene.add(zoneHighlight);

            // 경계선
            const bGeom = new THREE.BufferGeometry();
            const minX = Math.min(...xs) - 20, maxX = Math.max(...xs) + 20;
            const minY = Math.min(...ys) - 20, maxY = Math.max(...ys) + 20;
            const bVerts = new Float32Array([
                minX, RAIL_H + UNIT*1.5, minY,  maxX, RAIL_H + UNIT*1.5, minY,
                maxX, RAIL_H + UNIT*1.5, minY,  maxX, RAIL_H + UNIT*1.5, maxY,
                maxX, RAIL_H + UNIT*1.5, maxY,  minX, RAIL_H + UNIT*1.5, maxY,
                minX, RAIL_H + UNIT*1.5, maxY,  minX, RAIL_H + UNIT*1.5, minY
            ]);
            bGeom.setAttribute('position', new THREE.Float32BufferAttribute(bVerts, 3));
            const bMat = new THREE.LineBasicMaterial({{ color: 0xff6600, linewidth: 2 }});
            zoneHighlightBorder = new THREE.LineSegments(bGeom, bMat);
            state.scene.add(zoneHighlightBorder);

            // 5초 후 하이라이트 자동 제거
            setTimeout(() => {{
                if (zoneHighlight) {{ state.scene.remove(zoneHighlight); zoneHighlight = null; }}
                if (zoneHighlightBorder) {{ state.scene.remove(zoneHighlightBorder); zoneHighlightBorder = null; }}
            }}, 5000);
        }}

        function populateZoneList() {{
            const list = document.getElementById('zoneList');
            (LAYOUT_DATA.mcp_zones || []).forEach(z => {{
                const item = document.createElement('div');
                item.className = 'list-item';
                item.style.cursor = 'pointer';
                item.innerHTML = `
                    <div class="item-name">Zone #${{z.no}}: ${{z.name}}</div>
                    <div class="item-detail">Max: ${{z.vehicle_max}} | Type: ${{z.type}}</div>
                `;
                item.addEventListener('click', () => {{
                    focusZone(z.id || z.no);
                    // 선택 표시
                    list.querySelectorAll('.list-item').forEach(el => el.style.borderColor = '');
                    item.style.borderColor = '#ff6600';
                }});
                list.appendChild(item);
            }});

            // Zone 검색 필터
            const searchInput = document.getElementById('zoneSearch');
            if (searchInput) {{
                searchInput.addEventListener('input', (e) => {{
                    const q = e.target.value.toLowerCase();
                    list.querySelectorAll('.list-item').forEach(el => {{
                        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
                    }});
                }});
            }}
        }}

        function animate() {{
            requestAnimationFrame(animate);
            state.controls.update();
            state.renderer.render(state.scene, state.camera);
        }}

        // Initialize on load
        window.addEventListener('load', initScene);
    </script>
</body>
</html>
'''

    return html


# ============================================================================
# PART 2: EXPORT FUNCTIONS & GUI APPLICATION
# ============================================================================

def generate_oht_obj(project_data: dict, obj_path: str) -> None:
    """
    Wavefront OBJ 형식으로 OHT 레이아웃 내보내기 (Blender 호환)
    Export OHT layout to Wavefront OBJ format (Blender compatible)

    좌표 변환 / Coordinate mapping:
    - Layout 2D (x, y) → OBJ 3D (x, y_height, z)
    - layout_x → OBJ_x
    - 0 → OBJ_y (높이/height)
    - layout_y → OBJ_z
    """
    try:
        mtl_path = obj_path.replace('.obj', '.mtl')
        mtl_name = Path(mtl_path).stem

        # 좌표 스케일 계산 / Calculate coordinate scale
        nodes = project_data.get('nodes', [])
        if not nodes:
            print("경고: 노드 데이터 없음 / Warning: No node data")
            return

        xs = [n.get('x', 0) for n in nodes]
        ys = [n.get('y', 0) for n in nodes]
        max_coord = max(max(xs) if xs else 1, max(ys) if ys else 1)
        scale = 100.0 / max(max_coord, 1)  # 스케일을 100 units 이내로 / Scale to ~100 units

        vertices = []
        vertex_map = {}  # node_id → vertex_index

        # === 정점 수집 / Collect vertices ===

        # 1. 노드를 정점으로 / Nodes as vertices
        for node in nodes:
            node_id = node.get('id')
            x = node.get('x', 0) * scale
            y = 0  # 높이 / height
            z = node.get('y', 0) * scale
            vertices.append((x, y, z))
            vertex_map[node_id] = len(vertices)

        # 2. 레일 박스 메시 생성 / Rail box meshes from edges
        edges = project_data.get('edges', [])
        rail_vertices = []
        rail_faces = []

        rail_height = project_data.get('rail_height', 5.0)
        rail_width = 1.0

        for edge in edges:
            start_id = edge.get('start', edge.get('from'))
            end_id = edge.get('end', edge.get('to'))

            if start_id in vertex_map and end_id in vertex_map:
                v_start_idx = vertex_map[start_id] - 1
                v_end_idx = vertex_map[end_id] - 1

                x1, _, z1 = vertices[v_start_idx]
                x2, _, z2 = vertices[v_end_idx]

                # 박스의 8개 정점 / 8 vertices for box
                base_v = len(vertices) + 1

                # 낮은 쪽 정점 / Lower vertices
                vertices.append((x1 - rail_width/2, 0, z1 - rail_width/2))
                vertices.append((x1 + rail_width/2, 0, z1 - rail_width/2))
                vertices.append((x2 + rail_width/2, 0, z2 - rail_width/2))
                vertices.append((x2 - rail_width/2, 0, z2 - rail_width/2))

                # 높은 쪽 정점 / Upper vertices
                vertices.append((x1 - rail_width/2, rail_height, z1 - rail_width/2))
                vertices.append((x1 + rail_width/2, rail_height, z1 - rail_width/2))
                vertices.append((x2 + rail_width/2, rail_height, z2 - rail_width/2))
                vertices.append((x2 - rail_width/2, rail_height, z2 - rail_width/2))

                # 박스의 6개 면 / 6 faces for box
                rail_faces.extend([
                    (base_v, base_v+1, base_v+2, base_v+3),      # 아래 / bottom
                    (base_v+4, base_v+7, base_v+6, base_v+5),    # 위 / top
                    (base_v, base_v+4, base_v+5, base_v+1),      # 앞 / front
                    (base_v+2, base_v+6, base_v+7, base_v+3),    # 뒤 / back
                    (base_v, base_v+3, base_v+7, base_v+4),      # 좌 / left
                    (base_v+1, base_v+5, base_v+6, base_v+2),    # 우 / right
                ])

        # 3. 스테이션 마커 (작은 정육면체) / Station markers (small cubes)
        stations = project_data.get('stations', [])
        station_faces = []
        station_size = 2.0

        for station in stations:
            node_id = station.get('node', station.get('node_id'))
            if node_id in vertex_map:
                v_idx = vertex_map[node_id] - 1
                cx, cy, cz = vertices[v_idx]

                base_v = len(vertices) + 1
                d = station_size / 2

                # 스테이션 큐브의 8개 정점 / 8 vertices for station cube
                vertices.extend([
                    (cx-d, cy-d, cz-d), (cx+d, cy-d, cz-d),
                    (cx+d, cy+d, cz-d), (cx-d, cy+d, cz-d),
                    (cx-d, cy-d, cz+d), (cx+d, cy-d, cz+d),
                    (cx+d, cy+d, cz+d), (cx-d, cy+d, cz+d),
                ])

                # 6 faces
                station_faces.extend([
                    (base_v, base_v+1, base_v+2, base_v+3),
                    (base_v+4, base_v+7, base_v+6, base_v+5),
                    (base_v, base_v+4, base_v+5, base_v+1),
                    (base_v+2, base_v+6, base_v+7, base_v+3),
                    (base_v, base_v+3, base_v+7, base_v+4),
                    (base_v+1, base_v+5, base_v+6, base_v+2),
                ])

        # 4. 바닥 평면 / Floor plane
        floor_pad = 20.0 * scale
        floor_faces = []

        floor_v = len(vertices) + 1
        vertices.extend([
            (-floor_pad, -1, -floor_pad),
            (max(xs)*scale + floor_pad, -1, -floor_pad),
            (max(xs)*scale + floor_pad, -1, max(ys)*scale + floor_pad),
            (-floor_pad, -1, max(ys)*scale + floor_pad),
        ])
        floor_faces.append((floor_v, floor_v+1, floor_v+2, floor_v+3))

        # 5. 지지 기둥 (원기둥 근사) / Support pillars (cylinder approximation)
        pillar_faces = []
        pillar_segments = 8

        # 모서리 기둥 4개 / 4 corner pillars
        pillar_positions = [
            (-floor_pad, -1, -floor_pad),
            (max(xs)*scale + floor_pad, -1, -floor_pad),
            (max(xs)*scale + floor_pad, -1, max(ys)*scale + floor_pad),
            (-floor_pad, -1, max(ys)*scale + floor_pad),
        ]

        pillar_radius = 2.0
        pillar_height = rail_height + 5.0

        for px, py, pz in pillar_positions:
            base_v = len(vertices) + 1

            # 원기둥의 하단 원주 정점 / Bottom circle vertices
            for i in range(pillar_segments):
                angle = 2 * 3.14159 * i / pillar_segments
                vx = px + pillar_radius * (3.14159 * angle) ** 0.5
                vz = pz + pillar_radius * ((1 - (3.14159 * angle) ** 0.5) % 1)
                vertices.append((vx, py, vz))

            # 상단 원주 정점 / Top circle vertices
            for i in range(pillar_segments):
                angle = 2 * 3.14159 * i / pillar_segments
                vx = px + pillar_radius * (3.14159 * angle) ** 0.5
                vz = pz + pillar_radius * ((1 - (3.14159 * angle) ** 0.5) % 1)
                vertices.append((vx, py + pillar_height, vz))

            # 옆면 / Side faces
            for i in range(pillar_segments):
                v1 = base_v + i
                v2 = base_v + (i + 1) % pillar_segments
                v3 = base_v + pillar_segments + (i + 1) % pillar_segments
                v4 = base_v + pillar_segments + i
                pillar_faces.append((v1, v2, v3, v4))

        # === OBJ 파일 작성 / Write OBJ file ===
        with open(obj_path, 'w', encoding='utf-8') as f:
            f.write(f"# OHT Layout 3D Model\n")
            f.write(f"# FAB: {project_data.get('fab_name', 'Unknown')}\n")
            f.write(f"# OHT Count: {project_data.get('oht_count', 0)}\n")
            f.write(f"# Nodes: {len(nodes)}, Edges: {len(edges)}, Stations: {len(stations)}\n")
            f.write(f"mtllib {Path(mtl_path).name}\n\n")

            # 정점 / Vertices
            for x, y, z in vertices:
                f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            f.write(f"\n")

            # 노드 (점으로 표현) / Nodes (as points)
            f.write(f"usemtl Node\n")
            for i, node in enumerate(nodes):
                if i < len(vertices):
                    f.write(f"p {i+1}\n")

            # 레일 / Rails
            f.write(f"\nusemtl Rail\n")
            for face in rail_faces:
                f.write(f"f {face[0]} {face[1]} {face[2]} {face[3]}\n")

            # 스테이션 / Stations
            f.write(f"\nusemtl Station\n")
            for face in station_faces:
                f.write(f"f {face[0]} {face[1]} {face[2]} {face[3]}\n")

            # 바닥 / Floor
            f.write(f"\nusemtl Floor\n")
            for face in floor_faces:
                f.write(f"f {face[0]} {face[1]} {face[2]} {face[3]}\n")

            # 기둥 / Pillars
            f.write(f"\nusemtl Pillar\n")
            for face in pillar_faces:
                f.write(f"f {face[0]} {face[1]} {face[2]} {face[3]}\n")

        # === MTL 파일 작성 / Write MTL file ===
        with open(mtl_path, 'w', encoding='utf-8') as f:
            f.write("# OHT Layout Materials\n\n")

            materials = {
                'Rail': (0.0, 0.8, 1.0),      # 청색 / Cyan
                'Node': (0.3, 1.0, 0.5),      # 녹색 / Green
                'Station': (1.0, 0.3, 0.3),   # 빨강 / Red
                'Floor': (0.6, 0.6, 0.6),     # 회색 / Gray
                'Pillar': (0.5, 0.5, 0.5),    # 어두운 회색 / Dark Gray
            }

            for name, (r, g, b) in materials.items():
                f.write(f"newmtl {name}\n")
                f.write(f"Ka {r:.2f} {g:.2f} {b:.2f}\n")
                f.write(f"Kd {r:.2f} {g:.2f} {b:.2f}\n")
                f.write(f"Ks 0.2 0.2 0.2\n")
                f.write(f"Ns 10.0\n")
                f.write(f"d 1.0\n\n")

        print(f"✓ OBJ 내보내기 완료 / OBJ export complete: {obj_path}")
        print(f"  정점: {len(vertices)}, 면: {len(rail_faces) + len(station_faces) + len(floor_faces) + len(pillar_faces)}")

    except Exception as e:
        print(f"✗ OBJ 내보내기 오류 / OBJ export error: {e}")
        raise


def generate_oht_jsx(project_data: dict) -> str:
    """
    React Three Fiber 컴포넌트로 내보내기
    Export as React Three Fiber component
    """
    nodes = project_data.get('nodes', [])
    edges = project_data.get('edges', [])
    stations = project_data.get('stations', [])

    # 좌표 스케일 계산 / Calculate scale
    xs = [n.get('x', 0) for n in nodes] if nodes else [0]
    ys = [n.get('y', 0) for n in nodes] if nodes else [0]
    max_coord = max(max(xs), max(ys)) if xs and ys else 1
    scale = 100.0 / max(max_coord, 1)

    jsx = f"""import React, {{ useRef, useMemo }} from 'react';
import {{ Canvas, useFrame }} from '@react-three/fiber';
import {{ OrbitControls, Grid }} from '@react-three/drei';
import * as THREE from 'three';

// 데이터 / Data (맵: 노드, 엣지, 스테이션)
const PROJECT_DATA = {{
  fab_name: '{project_data.get("fab_name", "Unknown")}',
  oht_count: {project_data.get("oht_count", 0)},
  rail_height: {project_data.get("rail_height", 5.0)},
  nodes: {nodes},
  edges: {edges},
  stations: {stations},
}};

// 노드 인스턴스 메시 / Node InstancedMesh
function NodeMesh() {{
  const meshRef = useRef(null);
  const count = PROJECT_DATA.nodes.length;

  const positions = useMemo(() => {{
    const pos = new Float32Array(count * 3);
    PROJECT_DATA.nodes.forEach((node, i) => {{
      pos[i * 3] = node.x * {scale};
      pos[i * 3 + 1] = 0;
      pos[i * 3 + 2] = node.y * {scale};
    }});
    return pos;
  }}, []);

  return (
    <instancedMesh
      ref={{meshRef}}
      args={{[null, null, count]}}
      position={{[0, 0, 0]}}
    >
      <sphereGeometry args={{[0.5, 8, 8]}} />
      <meshStandardMaterial color="#44ff88" />
    </instancedMesh>
  );
}}

// 레일 선 / Rail Lines
function RailMesh() {{
  const linesRef = useRef(null);

  const positions = useMemo(() => {{
    const pos = [];
    const nodeMap = {{}};

    PROJECT_DATA.nodes.forEach((node) => {{
      nodeMap[node.id] = [node.x * {scale}, 0, node.y * {scale}];
    }});

    PROJECT_DATA.edges.forEach((edge) => {{
      const start = nodeMap[edge.from || edge.start];
      const end = nodeMap[edge.to || edge.end];
      if (start && end) {{
        pos.push(...start, ...end);
      }}
    }});

    return new Float32Array(pos);
  }}, []);

  return (
    <lineSegments position={{[0, 0, 0]}}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={{positions.length / 3}}
          array={{positions}}
          itemSize={{3}}
        />
      </bufferGeometry>
      <lineBasicMaterial color="#00d4ff" linewidth={{1}} />
    </lineSegments>
  );
}}

// 스테이션 마커 / Station Markers
function StationMesh() {{
  const meshRef = useRef(null);
  const count = PROJECT_DATA.stations.length;

  const positions = useMemo(() => {{
    const pos = new Float32Array(count * 3);
    const nodeMap = {{}};

    PROJECT_DATA.nodes.forEach((node) => {{
      nodeMap[node.id] = [node.x * {scale}, 0, node.y * {scale}];
    }});

    PROJECT_DATA.stations.forEach((station, i) => {{
      const nodePos = nodeMap[station.node] || [0, 0, 0];
      pos[i * 3] = nodePos[0];
      pos[i * 3 + 1] = nodePos[1];
      pos[i * 3 + 2] = nodePos[2];
    }});
    return pos;
  }}, []);

  return (
    <instancedMesh
      ref={{meshRef}}
      args={{[null, null, count]}}
    >
      <boxGeometry args={{[1.5, 1.5, 1.5]}} />
      <meshStandardMaterial color="#ff4444" />
    </instancedMesh>
  );
}}

// 메인 장면 / Main Scene (맵만: 노드 + 레일 + 스테이션)
function OHTScene() {{
  return (
    <>
      <GridHelper args={{[200, 20, '#1a1a2e', '#333344']}} />
      <axesHelper args={{[50]}} />
      <NodeMesh />
      <RailMesh />
      <StationMesh />
      <ambientLight intensity={{0.6}} />
      <pointLight position={{[50, 50, 50]}} intensity={{1}} />
      <OrbitControls makeDefault />
    </>
  );
}}

// 기본 컴포넌트 / Main Component
export default function OHTLayoutViewer() {{
  return (
    <div style={{{{ width: '100%', height: '100vh', background: '#0a0a1a' }}}}>
      <Canvas
        camera={{{{ position: [100, 80, 100], fov: 50 }}}}
        style={{{{ width: '100%', height: '100%' }}}}
      >
        <OHTScene />
      </Canvas>
    </div>
  );
}}
"""
    return jsx


def generate_blender_script(project_data: dict) -> str:
    """
    Blender Python 스크립트 생성 (bpy 사용)
    Generate Blender Python script using bpy
    """
    nodes = project_data.get('nodes', [])
    edges = project_data.get('edges', [])
    stations = project_data.get('stations', [])

    xs = [n.get('x', 0) for n in nodes] if nodes else [0]
    ys = [n.get('y', 0) for n in nodes] if nodes else [0]
    max_coord = max(max(xs), max(ys)) if xs and ys else 1
    scale = 100.0 / max(max_coord, 1)

    script = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Blender OHT Layout Import Script
블렌더 OHT 레이아웃 임포트 스크립트
\"\"\"

import bpy
import bmesh
from mathutils import Vector

# 프로젝트 정보 / Project info
FAB_NAME = '{project_data.get("fab_name", "Unknown")}'
OHT_COUNT = {project_data.get("oht_count", 0)}
RAIL_HEIGHT = {project_data.get("rail_height", 5.0)}
SCALE = {scale}

# 컬렉션 생성 / Create collections
def create_collections():
    scene = bpy.context.scene

    collections = {{}}
    for name in ['Rails', 'Nodes', 'Stations', 'Floor', 'Pillars']:
        coll = bpy.data.collections.new(name)
        scene.collection.children.link(coll)
        collections[name] = coll

    return collections

# 머터리얼 생성 / Create materials
def create_materials():
    materials = {{}}

    colors = {{
        'Rail': (0.0, 0.8, 1.0, 1.0),
        'Node': (0.3, 1.0, 0.5, 1.0),
        'Station': (1.0, 0.3, 0.3, 1.0),
        'Floor': (0.6, 0.6, 0.6, 1.0),
        'Pillar': (0.5, 0.5, 0.5, 1.0),
    }}

    for name, color in colors.items():
        mat = bpy.data.materials.new(name=name)
        mat.diffuse_color = color
        materials[name] = mat

    return materials

# 노드 메시 생성 / Create node meshes
def create_nodes(collections, materials):
    nodes_data = {nodes}

    for node in nodes_data:
        x = node.get('x', 0) * SCALE
        y = 0
        z = node.get('y', 0) * SCALE

        mesh = bpy.data.meshes.new(f"Node_{{node.get('id')}}")
        bm = bmesh.new()

        # 간단한 큐브 / Simple cube
        verts = [
            bm.verts.new((-0.25 + x, -0.25 + y, -0.25 + z)),
            bm.verts.new((0.25 + x, -0.25 + y, -0.25 + z)),
            bm.verts.new((0.25 + x, 0.25 + y, -0.25 + z)),
            bm.verts.new((-0.25 + x, 0.25 + y, -0.25 + z)),
            bm.verts.new((-0.25 + x, -0.25 + y, 0.25 + z)),
            bm.verts.new((0.25 + x, -0.25 + y, 0.25 + z)),
            bm.verts.new((0.25 + x, 0.25 + y, 0.25 + z)),
            bm.verts.new((-0.25 + x, 0.25 + y, 0.25 + z)),
        ]

        # 면 생성 / Create faces
        for face_verts in [
            (verts[0], verts[1], verts[2], verts[3]),
            (verts[4], verts[7], verts[6], verts[5]),
        ]:
            bm.faces.new(face_verts)

        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(f"Node_{{node.get('id')}}", mesh)
        obj.data.materials.append(materials['Node'])
        collections['Nodes'].objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

# 엣지(레일) 메시 생성 / Create edge (rail) meshes
def create_edges(collections, materials):
    edges_data = {edges}
    nodes_map = {{}};

    for node in {nodes}:
        nodes_map[node.get('id')] = (node.get('x', 0) * SCALE, 0, node.get('y', 0) * SCALE)

    for i, edge in enumerate(edges_data):
        start_id = edge.get('start', edge.get('from'))
        end_id = edge.get('end', edge.get('to'))

        if start_id in nodes_map and end_id in nodes_map:
            x1, y1, z1 = nodes_map[start_id]
            x2, y2, z2 = nodes_map[end_id]

            mesh = bpy.data.meshes.new(f"Rail_{{i}}")
            bm = bmesh.new()

            w = 0.5

            # 박스 정점 / Box vertices
            verts = [
                bm.verts.new((x1 - w, 0, z1 - w)),
                bm.verts.new((x1 + w, 0, z1 - w)),
                bm.verts.new((x2 + w, 0, z2 - w)),
                bm.verts.new((x2 - w, 0, z2 - w)),
                bm.verts.new((x1 - w, RAIL_HEIGHT, z1 - w)),
                bm.verts.new((x1 + w, RAIL_HEIGHT, z1 - w)),
                bm.verts.new((x2 + w, RAIL_HEIGHT, z2 - w)),
                bm.verts.new((x2 - w, RAIL_HEIGHT, z2 - w)),
            ]

            # 면 / Faces
            for face_verts in [
                (verts[0], verts[1], verts[2], verts[3]),
                (verts[4], verts[7], verts[6], verts[5]),
            ]:
                bm.faces.new(face_verts)

            bm.to_mesh(mesh)
            bm.free()

            obj = bpy.data.objects.new(f"Rail_{{i}}", mesh)
            obj.data.materials.append(materials['Rail'])
            collections['Rails'].objects.link(obj)

# 스테이션 마커 / Create station markers
def create_stations(collections, materials):
    stations_data = {stations}
    nodes_map = {{}};

    for node in {nodes}:
        nodes_map[node.get('id')] = (node.get('x', 0) * SCALE, 0, node.get('y', 0) * SCALE)

    for i, station in enumerate(stations_data):
        node_id = station.get('node', station.get('node_id'))
        if node_id in nodes_map:
            x, y, z = nodes_map[node_id]

            mesh = bpy.data.meshes.new(f"Station_{{i}}")
            bm = bmesh.new()

            d = 1.0
            verts = [
                bm.verts.new((x - d, y - d, z - d)),
                bm.verts.new((x + d, y - d, z - d)),
                bm.verts.new((x + d, y + d, z - d)),
                bm.verts.new((x - d, y + d, z - d)),
                bm.verts.new((x - d, y - d, z + d)),
                bm.verts.new((x + d, y - d, z + d)),
                bm.verts.new((x + d, y + d, z + d)),
                bm.verts.new((x - d, y + d, z + d)),
            ]

            for face_verts in [
                (verts[0], verts[1], verts[2], verts[3]),
                (verts[4], verts[7], verts[6], verts[5]),
            ]:
                bm.faces.new(face_verts)

            bm.to_mesh(mesh)
            bm.free()

            obj = bpy.data.objects.new(f"Station_{{i}}", mesh)
            obj.data.materials.append(materials['Station'])
            collections['Stations'].objects.link(obj)

# 메인 실행 / Main execution (맵만: 노드 + 레일 + 스테이션)
def main():
    print(f"Importing OHT Layout: {{FAB_NAME}}")
    print(f"Nodes: {len(nodes)}, Edges: {len(edges)}, Stations: {len(stations)}")

    collections = create_collections()
    materials = create_materials()

    create_nodes(collections, materials)
    create_edges(collections, materials)
    create_stations(collections, materials)

    print("Import complete!")

if __name__ == '__main__':
    main()
"""
    return script


# ============================================================================
# GUI APPLICATION CLASS
# ============================================================================

class OHTLayoutBuilderApp:
    """OHT 레이아웃 빌더 GUI 애플리케이션 / OHT Layout Builder GUI Application"""

    # 도구 모드 / Tool modes
    TOOL_SELECT = "select"
    TOOL_NODE = "node"
    TOOL_STATION = "station"
    TOOL_VEHICLE = "vehicle"
    TOOL_ZONE = "zone"

    # 노드 타입 색상 / Node type colors
    NODE_COLORS = {
        'default': '#44ff88',      # 녹색 / Green
        'station': '#ff4444',      # 빨강 / Red
        'branch': '#ffaa00',       # 주황 / Orange
        'junction': '#4488ff',     # 파랑 / Blue
        'hid': '#ff44ff',          # 자주 / Magenta
    }

    EDGE_COLOR = '#00d4ff'         # 청록 / Cyan
    STATION_COLOR = '#ff4444'      # 빨강 / Red
    VEHICLE_COLOR = '#ffaa44'      # 주황 / Orange

    ZONE_COLORS = ['#663322', '#226633', '#223366', '#552255', '#665522',
                    '#336655', '#553366', '#664422', '#225566', '#663355']

    def __init__(self, root):
        """앱 초기화 / Initialize application"""
        self.root = root
        self.root.title("OHT 3D Layout Builder v1.0")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 600)

        # 데이터 저장소 / Data storage
        self.project_data = {
            'fab_name': 'New Project',
            'oht_count': 1,
            'rail_height': 5.0,
            'nodes': [],
            'edges': [],
            'stations': [],
            'zones': [],
            'vehicles': [],
        }

        self.current_file = None
        self.current_tool = self.TOOL_SELECT
        self.selected_object = None
        self.selected_type = None

        # 캔버스 상태 / Canvas state
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.canvas_scale = 1.0
        self.pan_start = None

        # 표시 토글 / Visibility toggles
        self.show_nodes = True
        self.show_edges = True
        self.show_stations = True
        self.show_zones = True
        self.show_vehicles = True
        self.show_labels = True

        # 성능 최적화 / Performance optimization
        self.node_cache = {}
        self.edge_cache = {}

        # 진행 대화창 / Progress window
        self.progress_window = None

        # UI 구성 / Build UI
        self._apply_theme()
        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_status_bar()

        # 초기 업데이트 / Initial updates
        self._update_status()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        print("OHT Layout Builder 시작됨 / OHT Layout Builder initialized")

    def _apply_theme(self):
        """다크 테마 적용 / Apply dark theme"""
        style = ttk.Style()
        style.theme_use('clam')

        # 색상 팔레트 / Color palette
        bg_dark = '#0a0a1a'
        bg_panel = '#1a1a2e'
        bg_frame = '#0f0f1a'
        fg_light = '#cccccc'
        fg_bright = '#00d4ff'

        # 일반 스타일 / General styles
        style.configure('.', background=bg_panel, foreground=fg_light)
        style.configure('TFrame', background=bg_panel)
        style.configure('TLabel', background=bg_panel, foreground=fg_light)
        style.configure('TButton', background='#252540', foreground=fg_bright)
        style.map('TButton', background=[('active', '#333355')])

        # Treeview 스타일 / Treeview styles
        style.configure('Treeview',
                       background=bg_frame,
                       foreground=fg_light,
                       fieldbackground=bg_frame,
                       rowheight=22)
        style.map('Treeview',
                 background=[('selected', fg_bright)],
                 foreground=[('selected', bg_dark)])

        # 메뉴바 스타일 / Menu bar styles
        self.root.option_add('*Menu*background', bg_panel)
        self.root.option_add('*Menu*foreground', fg_light)
        self.root.option_add('*Menu*activeBackground', fg_bright)
        self.root.option_add('*Menu*activeForeground', bg_dark)

    def _build_menu(self):
        """메뉴바 구성 / Build menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 파일 메뉴 / File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일(File)", menu=file_menu)
        file_menu.add_command(label="새 프로젝트(New)", command=self.new_project)
        file_menu.add_command(label="XML 가져오기(Import XML)", command=self.import_xml)
        file_menu.add_command(label="ZIP 가져오기(Import ZIP)", command=self.import_zip)
        file_menu.add_separator()
        file_menu.add_command(label="JSON 열기(Open JSON)", command=self.open_project)
        file_menu.add_command(label="JSON 저장(Save JSON)", command=self.save_project)
        file_menu.add_command(label="다른이름 저장(Save As)", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="종료(Exit)", command=self._on_closing)

        # 편집 메뉴 / Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="편집(Edit)", menu=edit_menu)
        edit_menu.add_command(label="삭제(Delete)", command=self.delete_selected)
        edit_menu.add_command(label="선택해제(Deselect)", command=self.deselect_all)
        edit_menu.add_command(label="모두선택(Select All)", command=self.select_all)

        # 보기 메뉴 / View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보기(View)", menu=view_menu)
        view_menu.add_command(label="전체보기(Fit All)", command=self.fit_all_view)
        view_menu.add_command(label="확대(Zoom In)", command=lambda: self.zoom(1.2))
        view_menu.add_command(label="축소(Zoom Out)", command=lambda: self.zoom(0.8))
        view_menu.add_separator()
        view_menu.add_command(label="노드 표시토글(Toggle Nodes)", command=self.toggle_nodes)
        view_menu.add_command(label="레일 표시토글(Toggle Rails)", command=self.toggle_edges)
        view_menu.add_command(label="스테이션 표시토글(Toggle Stations)", command=self.toggle_stations)
        view_menu.add_command(label="Zone 표시토글(Toggle Zones)", command=self.toggle_zones)

        # 내보내기 메뉴 / Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="내보내기(Export)", menu=export_menu)
        export_menu.add_command(label="3D 맵 → HTML (브라우저)", command=self.export_html)
        export_menu.add_command(label="3D 맵 → HTML & 열기", command=self.export_html_open)
        export_menu.add_command(label="3D 맵 → OBJ (Blender)", command=self.export_obj)
        export_menu.add_command(label="3D 맵 → JSX (React)", command=self.export_jsx)
        export_menu.add_command(label="3D 맵 → Blender Script", command=self.export_blender)
        export_menu.add_separator()
        export_menu.add_command(label="마스터 데이터 CSV 저장", command=self.export_master_csv)
        export_menu.add_command(label="전체 레이아웃 JSON 저장", command=self.export_layout_json)

        # 도구 메뉴 / Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도구(Tools)", menu=tools_menu)
        tools_menu.add_command(label="검색(Search)", command=self.search_dialog)
        tools_menu.add_command(label="통계(Statistics)", command=self.show_stats)
        tools_menu.add_command(label="경로탐색(Path Finding)", command=self.show_pathfinding)

        # 도움말 메뉴 / Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말(Help)", menu=help_menu)
        help_menu.add_command(label="사용법(How to Use)", command=self.show_help)
        help_menu.add_command(label="정보(About)", command=self.show_about)

    def _build_toolbar(self):
        """도구바 구성 / Build toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # 도구 버튼들 / Tool buttons
        buttons = [
            ("선택", self.TOOL_SELECT),
            ("노드+", self.TOOL_NODE),
            ("스테이션+", self.TOOL_STATION),
            ("차량+", self.TOOL_VEHICLE),
            ("Zone+", self.TOOL_ZONE),
        ]

        self.tool_buttons = {}
        for label, tool in buttons:
            btn = tk.Button(toolbar, text=label, width=8,
                           bg='#252540', fg='#00d4ff', relief=tk.RAISED,
                           activebackground='#00d4ff', activeforeground='#000',
                           command=lambda t=tool: self._set_tool(t))
            btn.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[tool] = btn

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 줌 버튼 / Zoom buttons
        tk.Button(toolbar, text="🔍+", width=4, bg='#252540', fg='#00d4ff',
                  command=lambda: self.zoom(1.3)).pack(side=tk.LEFT, padx=1)
        tk.Button(toolbar, text="🔍-", width=4, bg='#252540', fg='#00d4ff',
                  command=lambda: self.zoom(0.7)).pack(side=tk.LEFT, padx=1)
        tk.Button(toolbar, text="전체보기", width=7, bg='#252540', fg='#00ff88',
                  command=self.fit_all_view).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # FAB 이름 입력 / FAB name input
        ttk.Label(toolbar, text="FAB:").pack(side=tk.LEFT)
        self.fab_name_var = tk.StringVar(value=self.project_data['fab_name'])
        fab_entry = ttk.Entry(toolbar, textvariable=self.fab_name_var, width=15)
        fab_entry.pack(side=tk.LEFT, padx=5)
        fab_entry.bind('<Return>', lambda e: self._update_fab_name())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # 액션 버튼들 / Action buttons
        ttk.Button(toolbar, text="💾저장", command=self.save_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🌐HTML", command=self.export_html).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📦OBJ", command=self.export_obj).pack(side=tk.LEFT, padx=2)

        self._set_tool(self.TOOL_SELECT)

        # === 두번째 줄: 표시 토글 버튼 / Second row: visibility toggle buttons ===
        toggle_bar = tk.Frame(self.root, bg='#12122a')
        toggle_bar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.show_edges_var = tk.BooleanVar(value=True)
        self.show_nodes_var = tk.BooleanVar(value=True)
        self.show_stations_var = tk.BooleanVar(value=True)
        self.show_zones_var = tk.BooleanVar(value=True)
        self.show_vehicles_var = tk.BooleanVar(value=True)
        self.show_labels_var = tk.BooleanVar(value=True)

        # 토글 버튼 설정: (표시 텍스트, 변수, 켰을때 색상, 속성 이름)
        self._toggle_buttons = {}
        toggle_defs = [
            ("━ 레일", self.show_edges_var,   '#00cc66', 'show_edges'),
            ("● 노드", self.show_nodes_var,   '#44ff88', 'show_nodes'),
            ("◆ 스테이션", self.show_stations_var, '#ff4444', 'show_stations'),
            ("▧ Zone", self.show_zones_var,    '#6688ff', 'show_zones'),
            ("■ 차량", self.show_vehicles_var, '#ffaa00', 'show_vehicles'),
            ("Aa 라벨", self.show_labels_var,  '#ff66aa', 'show_labels'),
        ]

        tk.Label(toggle_bar, text="표시 ▸", bg='#12122a', fg='#888888',
                 font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(5,4))

        def _make_toggle(btn, var, on_color, attr_name):
            def _do_toggle():
                new_val = not var.get()
                var.set(new_val)
                setattr(self, attr_name, new_val)
                if new_val:
                    btn.config(bg=on_color, fg='#000000', font=("Arial", 9, "bold"))
                else:
                    btn.config(bg='#333344', fg='#666666', font=("Arial", 9))
                self.redraw_canvas()
            return _do_toggle

        for text, var, on_color, attr_name in toggle_defs:
            btn = tk.Button(toggle_bar, text=text,
                           bg=on_color, fg='#000000',
                           font=("Arial", 9, "bold"),
                           bd=0, padx=8, pady=2,
                           activebackground=on_color, activeforeground='#000000',
                           cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2, pady=1)
            btn.config(command=_make_toggle(btn, var, on_color, attr_name))
            self._toggle_buttons[attr_name] = (btn, var, on_color)

    def _build_main_area(self):
        """메인 영역 구성 (3-pane) / Build main area (3-pane layout)"""
        # 메인 paned window
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ===== 왼쪽 패널: 객체 트리 / Left panel: Object tree =====
        left_frame = ttk.Frame(paned, width=250)
        paned.add(left_frame, weight=0)

        ttk.Label(left_frame, text="객체 목록", font=("Arial", 10, "bold")).pack(fill=tk.X)

        # 트리뷰 / Treeview
        tree_scroll = ttk.Scrollbar(left_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.object_tree = ttk.Treeview(left_frame, yscrollcommand=tree_scroll.set, height=30)
        tree_scroll.config(command=self.object_tree.yview)
        self.object_tree.pack(fill=tk.BOTH, expand=True)
        self.object_tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # ===== 중앙 패널: 2D 캔버스 / Center panel: 2D Canvas =====
        center_frame = ttk.Frame(paned)
        paned.add(center_frame, weight=1)

        ttk.Label(center_frame, text="레이아웃 시각화", font=("Arial", 10, "bold")).pack(fill=tk.X)

        self.canvas = tk.Canvas(center_frame, bg='#0a0a1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 캔버스 이벤트 바인딩 / Canvas event binding
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<Button-3>', self._on_canvas_drag_start)
        self.canvas.bind('<B3-Motion>', self._on_canvas_drag)
        self.canvas.bind('<MouseWheel>', self._on_canvas_scroll)
        self.canvas.bind('<Button-4>', self._on_canvas_scroll)
        self.canvas.bind('<Button-5>', self._on_canvas_scroll)
        self.canvas.bind('<Button-2>', self._on_canvas_middle)

        # ===== 오른쪽 패널: 속성 / Right panel: Properties =====
        right_frame = ttk.Frame(paned, width=280)
        paned.add(right_frame, weight=0)

        ttk.Label(right_frame, text="속성", font=("Arial", 10, "bold")).pack(fill=tk.X)

        prop_scroll = ttk.Scrollbar(right_frame)
        prop_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.prop_text = tk.Text(right_frame, width=35, height=30,
                                bg='#0f0f1a', fg='#cccccc',
                                yscrollcommand=prop_scroll.set)
        prop_scroll.config(command=self.prop_text.yview)
        self.prop_text.pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self):
        """상태바 구성 / Build status bar"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        self.status_label = tk.Label(self.status_frame, text="",
                                     relief=tk.SUNKEN, anchor=tk.W,
                                     bg='#1a1a2e', fg='#888888', font=("Consolas", 9))
        self.status_label.pack(fill=tk.X)

    def _set_tool(self, tool):
        """도구 변경 / Change tool"""
        self.current_tool = tool

        # 버튼 상태 업데이트 / Update button states
        for t, btn in self.tool_buttons.items():
            if t == tool:
                btn.config(relief=tk.SUNKEN, bg='#00d4ff', fg='#000')
            else:
                btn.config(relief=tk.RAISED, bg='#252540', fg='#00d4ff')

    def _on_canvas_click(self, event):
        """캔버스 클릭 이벤트 / Canvas click event"""
        wx, wy = self.canvas_to_world(event.x, event.y)
        obj, obj_type = self._find_nearest_object(wx, wy)

        if obj and obj_type:
            self.selected_object = obj
            self.selected_type = obj_type
            self._show_properties(obj, obj_type)
        else:
            self.selected_object = None
            self.selected_type = None
            self.prop_text.config(state=tk.NORMAL)
            self.prop_text.delete('1.0', tk.END)
            self.prop_text.config(state=tk.DISABLED)

        self.redraw_canvas()

    def _on_canvas_drag_start(self, event):
        """캔버스 드래그 시작 / Start canvas drag"""
        self.pan_start = (event.x, event.y)

    def _on_canvas_drag(self, event):
        """캔버스 드래그 / Canvas drag"""
        if self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]

            self.canvas_offset_x += dx
            self.canvas_offset_y += dy
            self.pan_start = (event.x, event.y)

            self.redraw_canvas()

    def _on_canvas_scroll(self, event):
        """캔버스 스크롤 / Canvas scroll (zoom)"""
        if event.num == 5 or event.delta < 0:
            self.zoom(0.9)
        elif event.num == 4 or event.delta > 0:
            self.zoom(1.1)

    def _on_canvas_middle(self, event):
        """캔버스 중간 클릭 / Canvas middle click (reset view)"""
        self.fit_all_view()

    def world_to_canvas(self, wx, wy):
        """월드 좌표 → 캔버스 좌표 / World to canvas coordinates"""
        cx = int(wx * self.canvas_scale + self.canvas_offset_x)
        cy = int(wy * self.canvas_scale + self.canvas_offset_y)
        return cx, cy

    def canvas_to_world(self, cx, cy):
        """캔버스 좌표 → 월드 좌표 / Canvas to world coordinates"""
        wx = (cx - self.canvas_offset_x) / self.canvas_scale
        wy = (cy - self.canvas_offset_y) / self.canvas_scale
        return wx, wy

    def _find_nearest_object(self, wx, wy, radius=100):
        """가장 가까운 객체 찾기 / Find nearest object"""
        hit_threshold = radius / self.canvas_scale if self.canvas_scale > 0 else radius

        # 노드 검사 / Check nodes
        for node in self.project_data.get('nodes', []):
            dx = node.get('x', 0) - wx
            dy = node.get('y', 0) - wy
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < hit_threshold:
                return node, 'node'

        # 스테이션 검사 / Check stations
        for station in self.project_data.get('stations', []):
            for node in self.project_data.get('nodes', []):
                if node.get('id') == station.get('node'):
                    dx = node.get('x', 0) - wx
                    dy = node.get('y', 0) - wy
                    dist = (dx*dx + dy*dy) ** 0.5
                    if dist < hit_threshold:
                        return station, 'station'
                    break

        # 차량 검사 / Check vehicles
        for vehicle in self.project_data.get('vehicles', []):
            if 'x' in vehicle and 'y' in vehicle:
                dx = vehicle.get('x', 0) - wx
                dy = vehicle.get('y', 0) - wy
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < hit_threshold:
                    return vehicle, 'vehicle'

        return None, None

    def _show_properties(self, obj, obj_type):
        """속성 표시 / Show properties"""
        self.prop_text.config(state=tk.NORMAL)
        self.prop_text.delete('1.0', tk.END)

        if obj_type == 'node':
            text = f"""노드 / Node
━━━━━━━━━━━━━━━━━━━
ID: {obj.get('id', 'N/A')}
X: {obj.get('x', 0):.2f}
Y: {obj.get('y', 0):.2f}
Symbol: {obj.get('symbol', '-')}
Station: {obj.get('is_station', False)}
Branch: {obj.get('branch', False)}
Junction: {obj.get('junction', False)}
HID: {obj.get('hid', False)}

엣지 연결 수 / Connected Edges: {len(obj.get('connected_edges', []))}
"""
        elif obj_type == 'station':
            text = f"""스테이션 / Station
━━━━━━━━━━━━━━━━━━━
Port ID: {obj.get('port_id', 'N/A')}
Category: {obj.get('category', 'N/A')}
Type: {obj.get('type', 'N/A')}
Node: {obj.get('node', 'N/A')}
Addresses: {len(obj.get('addresses', []))}
"""
        elif obj_type == 'vehicle':
            text = f"""차량 / Vehicle
━━━━━━━━━━━━━━━━━━━
ID: {obj.get('id', 'N/A')}
X: {obj.get('x', 0):.2f}
Y: {obj.get('y', 0):.2f}
State: {obj.get('state', 'N/A')}
Zone: {obj.get('zone', 'N/A')}
"""
        else:
            text = "선택된 객체 없음 / No object selected"

        self.prop_text.insert('1.0', text)
        self.prop_text.config(state=tk.DISABLED)

    def _show_project_properties(self):
        """프로젝트 속성 표시 / Show project properties"""
        self.prop_text.config(state=tk.NORMAL)
        self.prop_text.delete('1.0', tk.END)

        text = f"""프로젝트 설정 / Project Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAB: {self.project_data.get('fab_name', 'N/A')}
OHT Count: {self.project_data.get('oht_count', 0)}
Rail Height: {self.project_data.get('rail_height', 5.0)}

통계 / Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━
노드 / Nodes: {len(self.project_data.get('nodes', []))}
엣지 / Edges: {len(self.project_data.get('edges', []))}
스테이션 / Stations: {len(self.project_data.get('stations', []))}
Zone: {len(self.project_data.get('zones', []))}
차량 / Vehicles: {len(self.project_data.get('vehicles', []))}

좌표 범위 / Coordinate Range
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        nodes = self.project_data.get('nodes', [])
        if nodes:
            xs = [n.get('x', 0) for n in nodes]
            ys = [n.get('y', 0) for n in nodes]
            text += f"X: {min(xs):.2f} ~ {max(xs):.2f}\n"
            text += f"Y: {min(ys):.2f} ~ {max(ys):.2f}\n"

        self.prop_text.insert('1.0', text)
        self.prop_text.config(state=tk.DISABLED)

    def _update_tree(self):
        """트리 업데이트 / Update tree view"""
        self.object_tree.delete(*self.object_tree.get_children())

        # 통계 섹션 / Statistics
        stats_item = self.object_tree.insert('', 'end', text="📊 통계", open=True)
        nodes_count = len(self.project_data.get('nodes', []))
        edges_count = len(self.project_data.get('edges', []))
        stations_count = len(self.project_data.get('stations', []))
        zones_count = len(self.project_data.get('zones', []))

        self.object_tree.insert(stats_item, 'end', text=f"노드: {nodes_count}")
        self.object_tree.insert(stats_item, 'end', text=f"엣지: {edges_count}")
        self.object_tree.insert(stats_item, 'end', text=f"스테이션: {stations_count}")
        self.object_tree.insert(stats_item, 'end', text=f"Zone: {zones_count}")

        # 스테이션 목록 / Stations list
        if stations_count > 0:
            stations_item = self.object_tree.insert('', 'end', text="🚉 스테이션", open=False)
            for station in self.project_data.get('stations', [])[:20]:  # 처음 20개만 / First 20
                port_id = station.get('port_id', 'N/A')
                self.object_tree.insert(stations_item, 'end', text=f"{port_id}")

        # Zone 목록 / Zones list
        if zones_count > 0:
            zones_item = self.object_tree.insert('', 'end', text="🔲 Zone", open=False)
            for zone in self.project_data.get('zones', [])[:10]:
                zone_name = zone.get('name', 'N/A')
                self.object_tree.insert(zones_item, 'end', text=f"{zone_name}")

        # 차량 목록 / Vehicles list
        vehicles_count = len(self.project_data.get('vehicles', []))
        if vehicles_count > 0:
            vehicles_item = self.object_tree.insert('', 'end', text="🚗 차량", open=False)
            for i, vehicle in enumerate(self.project_data.get('vehicles', [])[:10]):
                vehicle_id = vehicle.get('id', f'Vehicle_{i}')
                self.object_tree.insert(vehicles_item, 'end', text=f"{vehicle_id}")

    def _on_tree_select(self, event):
        """트리 선택 이벤트 / Tree selection event"""
        selection = self.object_tree.selection()
        if selection:
            item = selection[0]
            text = self.object_tree.item(item, 'text')
            # TODO: 선택된 항목에 따라 캔버스 포커스

    def _update_status(self):
        """상태바 업데이트 / Update status bar"""
        nodes_count = len(self.project_data.get('nodes', []))
        edges_count = len(self.project_data.get('edges', []))
        stations_count = len(self.project_data.get('stations', []))
        zones_count = len(self.project_data.get('zones', []))
        vehicles_count = len(self.project_data.get('vehicles', []))

        status_text = (f"노드: {nodes_count} | 엣지: {edges_count} | 스테이션: {stations_count} | "
                      f"Zone: {zones_count} | 차량: {vehicles_count} | "
                      f"Zoom: {self.canvas_scale:.2f}x | [{self.project_data.get('fab_name', 'N/A')}]")

        self.status_label.config(text=status_text)

    def fit_all_view(self):
        """모든 객체에 맞춰서 뷰 조정 / Fit all objects in view"""
        nodes = self.project_data.get('nodes', [])
        if not nodes:
            return

        xs = [n.get('x', 0) for n in nodes]
        ys = [n.get('y', 0) for n in nodes]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        width = max_x - min_x if max_x > min_x else 1
        height = max_y - min_y if max_y > min_y else 1

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 800
            canvas_height = 600

        scale_x = (canvas_width * 0.9) / width
        scale_y = (canvas_height * 0.9) / height

        self.canvas_scale = min(scale_x, scale_y, 50.0)  # Max 50x zoom
        self.canvas_scale = max(self.canvas_scale, 0.01)  # Min 0.01x zoom

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        self.canvas_offset_x = canvas_width / 2 - center_x * self.canvas_scale
        self.canvas_offset_y = canvas_height / 2 - center_y * self.canvas_scale

        self.redraw_canvas()

    def zoom(self, factor):
        """확대/축소 / Zoom in/out"""
        old_scale = self.canvas_scale
        self.canvas_scale *= factor
        self.canvas_scale = max(0.01, min(self.canvas_scale, 50.0))

        # 마우스 위치 기준으로 확대 / Zoom around mouse position
        canvas_center_x = self.canvas.winfo_width() / 2
        canvas_center_y = self.canvas.winfo_height() / 2

        scale_change = self.canvas_scale / old_scale

        self.canvas_offset_x = canvas_center_x - (canvas_center_x - self.canvas_offset_x) * scale_change
        self.canvas_offset_y = canvas_center_y - (canvas_center_y - self.canvas_offset_y) * scale_change

        self.redraw_canvas()

    def redraw_canvas(self):
        """캔버스 그리기 / Redraw canvas"""
        self.canvas.delete("all")

        # 배경 격자 / Background grid
        self._draw_grid()

        # 데이터 없으면 안내 메시지 / Show guide when no data
        if not self.project_data.get('nodes'):
            cw = self.canvas.winfo_width() or 800
            ch = self.canvas.winfo_height() or 600
            self.canvas.create_text(cw//2, ch//2 - 40,
                text="OHT 3D Layout Builder", fill='#00d4ff',
                font=("Arial", 24, "bold"))
            self.canvas.create_text(cw//2, ch//2 + 10,
                text="파일 → XML 가져오기 / ZIP 가져오기 / JSON 열기", fill='#888888',
                font=("Arial", 14))
            self.canvas.create_text(cw//2, ch//2 + 40,
                text="또는 Ctrl+I (XML)  |  Ctrl+Z (ZIP)  |  Ctrl+O (JSON)", fill='#555555',
                font=("Arial", 11))
            self._update_status()
            return

        # 토글 플래그에 따라 렌더링 / Render based on toggle flags
        if self.show_zones:
            self._draw_zones()
        if self.show_edges:
            self._draw_edges()
        if self.show_nodes:
            self._draw_nodes()
        if self.show_stations:
            self._draw_stations()
        if self.show_vehicles:
            self._draw_vehicles()

        self._update_status()

    def _draw_grid(self):
        """격자선 그리기 / Draw grid"""
        grid_spacing = 1000
        grid_color = '#1a1a2e'

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # 월드 좌표로 변환 / Convert to world coordinates
        x0, y0 = self.canvas_to_world(0, 0)
        x1, y1 = self.canvas_to_world(canvas_w, canvas_h)

        start_x = int(x0 / grid_spacing) * grid_spacing
        start_y = int(y0 / grid_spacing) * grid_spacing

        # 수직선 / Vertical lines
        x = start_x
        while x <= x1:
            cx = int(x * self.canvas_scale + self.canvas_offset_x)
            self.canvas.create_line(cx, 0, cx, canvas_h, fill=grid_color, width=1)
            x += grid_spacing

        # 수평선 / Horizontal lines
        y = start_y
        while y <= y1:
            cy = int(y * self.canvas_scale + self.canvas_offset_y)
            self.canvas.create_line(0, cy, canvas_w, cy, fill=grid_color, width=1)
            y += grid_spacing

    def _draw_zones(self):
        """Zone 그리기 — 뷰포트 안 것만 / Draw only visible zones"""
        zones = self.project_data.get('zones', [])
        nodes = {n.get('id'): n for n in self.project_data.get('nodes', [])}
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600

        for i, zone in enumerate(zones):
            addresses = zone.get('addresses', [])
            if not addresses:
                continue

            # 주소에 해당하는 노드들의 경계 계산 / Calculate bounding box
            zone_xs = []
            zone_ys = []

            for addr in addresses:
                if addr in nodes:
                    zone_xs.append(nodes[addr].get('x', 0))
                    zone_ys.append(nodes[addr].get('y', 0))

            if zone_xs and zone_ys:
                min_x, max_x = min(zone_xs), max(zone_xs)
                min_y, max_y = min(zone_ys), max(zone_ys)

                pad = 50
                min_x -= pad
                max_x += pad
                min_y -= pad
                max_y += pad

                x1, y1 = self.world_to_canvas(min_x, min_y)
                x2, y2 = self.world_to_canvas(max_x, max_y)

                # 뷰포트 밖이면 건너뛰기
                if x2 < -50 or x1 > cw + 50 or y2 < -50 or y1 > ch + 50:
                    continue

                color = self.ZONE_COLORS[i % len(self.ZONE_COLORS)]
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#ffffff', width=1,
                                            stipple='gray25')

                # Zone 이름 표시 / Draw zone name
                label_x = (x1 + x2) / 2
                label_y = (y1 + y2) / 2
                zone_name = zone.get('name', f"Zone-{zone.get('id', '?')}")
                vmax = zone.get('vehicle_max', 0)
                label_text = f"{zone_name}\n(max:{vmax})" if self.show_labels else zone_name
                fsize = max(7, min(11, int(9 * min(self.canvas_scale / 0.05, 2))))
                self.canvas.create_text(label_x, label_y, text=label_text,
                                       fill='white', font=("Arial", fsize, "bold"))

    def _is_visible(self, cx, cy, margin=20):
        """캔버스 좌표가 화면 안에 있는지 / Check if canvas coords are in viewport"""
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        return -margin <= cx <= cw + margin and -margin <= cy <= ch + margin

    def _draw_edges(self):
        """엣지(레일) 그리기 — 뷰포트 안 것만 / Draw only visible edges"""
        edges = self.project_data.get('edges', [])
        nodes = {n.get('id'): n for n in self.project_data.get('nodes', [])}

        # 줌 아웃 시 샘플링 (너무 많으면 건너뛰기)
        total = len(edges)
        step = max(1, total // 15000)  # 최대 15000개만

        drawn = 0
        for i in range(0, total, step):
            edge = edges[i]
            start_id = edge.get('start')
            end_id = edge.get('end')

            if start_id in nodes and end_id in nodes:
                start_node = nodes[start_id]
                end_node = nodes[end_id]

                x1, y1 = self.world_to_canvas(start_node.get('x', 0), start_node.get('y', 0))
                x2, y2 = self.world_to_canvas(end_node.get('x', 0), end_node.get('y', 0))

                # 양쪽 점 모두 화면 밖이면 건너뛰기
                if not (self._is_visible(x1, y1, 50) or self._is_visible(x2, y2, 50)):
                    continue

                self.canvas.create_line(x1, y1, x2, y2, fill=self.EDGE_COLOR, width=1)
                drawn += 1

    def _draw_nodes(self):
        """노드 그리기 — 뷰포트 안 것만 + 샘플링 / Draw only visible nodes"""
        nodes = self.project_data.get('nodes', [])

        # 줌 아웃 시 샘플링
        total = len(nodes)
        step = max(1, total // 10000)  # 최대 10000개만

        size = 2 if self.canvas_scale < 0.1 else (3 if self.canvas_scale < 0.5 else 4)
        drawn = 0

        for i in range(0, total, step):
            node = nodes[i]
            x, y = self.world_to_canvas(node.get('x', 0), node.get('y', 0))

            # 뷰포트 밖이면 건너뛰기
            if not self._is_visible(x, y):
                continue

            # 노드 타입별 색상 / Color by node type
            if node.get('is_station'):
                color = self.NODE_COLORS['station']
            elif node.get('branch'):
                color = self.NODE_COLORS['branch']
            elif node.get('junction'):
                color = self.NODE_COLORS['junction']
            else:
                color = self.NODE_COLORS['default']

            self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline=color)
            drawn += 1

            # 선택됨 표시 / Highlight if selected
            if self.selected_object == node and self.selected_type == 'node':
                self.canvas.create_oval(x-size-2, y-size-2, x+size+2, y+size+2,
                                       outline='yellow', width=2)

    def _draw_stations(self):
        """스테이션 그리기 — 뷰포트 안 것만 / Draw only visible stations"""
        stations = self.project_data.get('stations', [])
        nodes = {n.get('id'): n for n in self.project_data.get('nodes', [])}

        # 줌 충분히 확대했을 때만 라벨 표시
        show_labels = self.canvas_scale > 0.05 and self.show_labels

        for station in stations:
            node_id = station.get('node')
            if node_id in nodes:
                node = nodes[node_id]
                x, y = self.world_to_canvas(node.get('x', 0), node.get('y', 0))

                # 뷰포트 밖이면 건너뛰기
                if not self._is_visible(x, y, 30):
                    continue

                size = 6
                self.canvas.create_polygon(
                    x, y-size,          # 위
                    x+size, y,          # 오른쪽
                    x, y+size,          # 아래
                    x-size, y,          # 왼쪽
                    fill=self.STATION_COLOR, outline=self.STATION_COLOR
                )

                # 선택됨 표시 / Highlight if selected
                if self.selected_object == station and self.selected_type == 'station':
                    self.canvas.create_polygon(
                        x, y-size-2,
                        x+size+2, y,
                        x, y+size+2,
                        x-size-2, y,
                        outline='yellow', width=2, fill=''
                    )

                # 라벨 표시 / Draw label (토글 + 줌 기반)
                if self.show_labels and self.canvas_scale > 0.05:
                    port_id = station.get('port_id', '')
                    if port_id:
                        fsize = max(7, min(12, int(8 * self.canvas_scale / 0.1)))
                        self.canvas.create_text(x, y-size-10, text=port_id[:12],
                                               fill='#ff6666', font=("Arial", fsize))

    def _draw_vehicles(self):
        """차량 그리기 / Draw vehicles"""
        vehicles = self.project_data.get('vehicles', [])

        for vehicle in vehicles:
            x, y = self.world_to_canvas(vehicle.get('x', 0), vehicle.get('y', 0))

            size = 4
            self.canvas.create_rectangle(x-size, y-size, x+size, y+size,
                                        fill=self.VEHICLE_COLOR, outline=self.VEHICLE_COLOR)

            # 선택됨 표시 / Highlight if selected
            if self.selected_object == vehicle and self.selected_type == 'vehicle':
                self.canvas.create_rectangle(x-size-2, y-size-2, x+size+2, y+size+2,
                                            outline='yellow', width=2)

    def import_xml(self):
        """XML 파일 가져오기 / Import XML file"""
        filepath = filedialog.askopenfilename(
            title="XML 파일 선택",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )

        if filepath:
            self._show_progress("XML 파일 파싱 중...")

            try:
                parser = OHTLayoutParser()
                data = parser.parse_xml(filepath)
                self._load_parsed_data(data)
                self._auto_fit_view()
                print(f"✓ XML 가져오기 완료 / XML import complete: {filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"XML 가져오기 실패: {e}")
                print(f"✗ XML 가져오기 오류 / XML import error: {e}")
            finally:
                self._hide_progress()

    def import_zip(self):
        """ZIP 파일 가져오기 / Import ZIP file"""
        filepath = filedialog.askopenfilename(
            title="ZIP 파일 선택",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )

        if filepath:
            self._show_progress("ZIP 파일 파싱 중...")

            try:
                parser = OHTLayoutParser()
                data = parser.parse_zip(filepath)
                self._load_parsed_data(data)
                self._auto_fit_view()
                print(f"✓ ZIP 가져오기 완료 / ZIP import complete: {filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"ZIP 가져오기 실패: {e}")
                print(f"✗ ZIP 가져오기 오류 / ZIP import error: {e}")
            finally:
                self._hide_progress()

    def _load_parsed_data(self, parsed_data):
        """파싱된 데이터 로드 + 키 정규화 / Load parsed data + normalize keys"""
        # 파서 출력 키 → GUI 내부 키 변환
        # Parser output uses: 'mcp_zones', edge 'from'/'to', station 'node_id'
        # GUI uses: 'zones', edge 'start'/'end', station 'node'

        # nodes: 그대로 사용 (id, x, y, symbol, is_station, branch, junction, hid_included)
        nodes = parsed_data.get('nodes', [])

        # edges: 'from'→'start', 'to'→'end' 변환
        raw_edges = parsed_data.get('edges', [])
        edges = []
        for e in raw_edges:
            edges.append({
                'start': e.get('from', e.get('start', 0)),
                'end': e.get('to', e.get('end', 0)),
                'distance': e.get('distance', 0),
                'speed': e.get('speed', 0),
                'direction': e.get('direction', 0),
            })

        # stations: 'node_id'→'node' 변환
        raw_stations = parsed_data.get('stations', [])
        stations = []
        for s in raw_stations:
            stations.append({
                'port_id': s.get('port_id', ''),
                'category': s.get('category', 0),
                'type': s.get('type', 0),
                'no': s.get('no', 0),
                'node': s.get('node_id', s.get('node', 0)),
                'x': s.get('x', 0),
                'y': s.get('y', 0),
            })

        # zones: 'mcp_zones' → 'zones', zone_addr_map 병합
        raw_zones = parsed_data.get('mcp_zones', parsed_data.get('zones', []))
        zone_addr_map = parsed_data.get('zone_addr_map', {})
        zones = []
        for z in raw_zones:
            zone_id = z.get('id', z.get('no', 0))
            addrs = zone_addr_map.get(str(zone_id), zone_addr_map.get(zone_id, z.get('addresses', [])))
            zones.append({
                'id': zone_id,
                'no': z.get('no', 0),
                'name': z.get('name', f'Zone-{zone_id}'),
                'vehicle_max': z.get('vehicle_max', 0),
                'vehicle_precaution': z.get('vehicle_precaution', 0),
                'type': z.get('type', 0),
                'entries': z.get('entries', []),
                'exits': z.get('exits', []),
                'cut_lanes': z.get('cut_lanes', []),
                'addresses': addrs,
            })

        self.project_data = {
            'fab_name': parsed_data.get('fab_name', parsed_data.get('project', 'Unknown')),
            'oht_count': parsed_data.get('oht_count', 35),
            'rail_height': parsed_data.get('rail_height', 15.0),
            'bounds': parsed_data.get('bounds', {}),
            'total_nodes': parsed_data.get('total_nodes', len(nodes)),
            'total_edges': parsed_data.get('total_edges', len(edges)),
            'total_stations': parsed_data.get('total_stations', len(stations)),
            'total_mcp_zones': parsed_data.get('total_mcp_zones', len(zones)),
            'nodes': nodes,
            'edges': edges,
            'stations': stations,
            'zones': zones,
            'hid_zones': parsed_data.get('hid_zones', []),
            'hid_master': parsed_data.get('hid_master', []),
            'vehicles': parsed_data.get('vehicles', []),
        }

        self.fab_name_var.set(self.project_data['fab_name'])
        self._update_tree()
        self._update_status()
        self.redraw_canvas()
        self._show_project_properties()

        # 로드 완료 요약 / Load summary
        n = len(nodes)
        e = len(edges)
        s = len(stations)
        z = len(zones)
        messagebox.showinfo("로드 완료",
            f"FAB: {self.project_data['fab_name']}\n"
            f"노드: {n:,}개 | 엣지: {e:,}개\n"
            f"스테이션: {s:,}개 | Zone: {z:,}개")

    def _auto_fit_view(self):
        """자동 뷰 조정 / Auto fit view"""
        self.root.after(100, self.fit_all_view)

    def save_project(self):
        """프로젝트 JSON 저장 / Save project as JSON"""
        if self.current_file:
            self._save_json(self.current_file)
        else:
            self.save_project_as()

    def save_project_as(self):
        """프로젝트 다른 이름으로 저장 / Save project as"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filepath:
            self._save_json(filepath)
            self.current_file = filepath

    def _save_json(self, filepath):
        """JSON 파일에 저장 / Save to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=2, ensure_ascii=False)
            print(f"✓ 프로젝트 저장 / Project saved: {filepath}")
            messagebox.showinfo("저장 완료", f"프로젝트가 저장되었습니다.\n{filepath}")
        except Exception as e:
            messagebox.showerror("저장 오류", f"프로젝트 저장 실패: {e}")
            print(f"✗ 저장 오류 / Save error: {e}")

    def open_project(self):
        """프로젝트 JSON 열기 / Open project from JSON"""
        filepath = filedialog.askopenfilename(
            title="JSON 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.project_data = json.load(f)
                self.current_file = filepath
                self._update_tree()
                self._update_status()
                self._auto_fit_view()
                print(f"✓ 프로젝트 열기 / Project opened: {filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"프로젝트 열기 실패: {e}")
                print(f"✗ 열기 오류 / Open error: {e}")

    def _prepare_export_data(self):
        """내보내기용 데이터 준비: GUI 내부 키 → 파서 형식 키 변환
        Export data preparation: convert GUI internal keys to parser format keys"""
        data = dict(self.project_data)

        # edges: GUI 'start'/'end' → 파서 'from'/'to'
        raw_edges = data.get('edges', [])
        export_edges = []
        for e in raw_edges:
            export_edges.append({
                'from': e.get('start', e.get('from', 0)),
                'to': e.get('end', e.get('to', 0)),
                'distance': e.get('distance', 0),
                'speed': e.get('speed', 0),
                'direction': e.get('direction', 0),
            })
        data['edges'] = export_edges

        # zones: GUI 'zones' → 'mcp_zones'
        if 'zones' in data and 'mcp_zones' not in data:
            data['mcp_zones'] = data['zones']

        # stations: GUI 'node' → 'node_id'
        raw_stations = data.get('stations', [])
        export_stations = []
        for s in raw_stations:
            export_stations.append({
                'port_id': s.get('port_id', ''),
                'category': s.get('category', 0),
                'type': s.get('type', 0),
                'no': s.get('no', 0),
                'node_id': s.get('node', s.get('node_id', 0)),
                'x': s.get('x', 0),
                'y': s.get('y', 0),
            })
        data['stations'] = export_stations

        # zone_addr_map 재구성
        if 'zone_addr_map' not in data or not data['zone_addr_map']:
            zone_addr_map = {}
            for z in data.get('mcp_zones', data.get('zones', [])):
                zid = z.get('id', z.get('no', 0))
                addrs = z.get('addresses', [])
                if addrs:
                    zone_addr_map[str(zid)] = addrs
            data['zone_addr_map'] = zone_addr_map

        return data

    def export_html(self):
        """HTML 내보내기 / Export HTML"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )

        if filepath:
            try:
                export_data = self._prepare_export_data()
                html = generate_oht_html(export_data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"✓ HTML 내보내기 완료 / HTML export complete: {filepath}")
                messagebox.showinfo("내보내기 완료", f"HTML 파일이 저장되었습니다.\n{filepath}")
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"HTML 내보내기 실패: {e}")
                print(f"✗ HTML 내보내기 오류 / HTML export error: {e}")

    def export_html_open(self):
        """HTML 내보내기 및 열기 / Export HTML and open"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )

        if filepath:
            try:
                export_data = self._prepare_export_data()
                html = generate_oht_html(export_data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"✓ HTML 내보내기 완료 / HTML export complete: {filepath}")

                # 웹브라우저로 열기 / Open in browser
                import webbrowser
                webbrowser.open('file://' + filepath)
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"HTML 내보내기 실패: {e}")
                print(f"✗ HTML 내보내기 오류 / HTML export error: {e}")

    def export_obj(self):
        """OBJ 내보내기 (Blender) / Export OBJ for Blender"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".obj",
            filetypes=[("Wavefront OBJ", "*.obj"), ("All files", "*.*")]
        )

        if filepath:
            try:
                generate_oht_obj(self.project_data, filepath)
                messagebox.showinfo("내보내기 완료", f"OBJ 파일이 저장되었습니다.\n{filepath}")
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"OBJ 내보내기 실패: {e}")

    def export_jsx(self):
        """JSX 내보내기 (React Three Fiber) / Export JSX"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".jsx",
            filetypes=[("JSX files", "*.jsx"), ("JavaScript files", "*.js"), ("All files", "*.*")]
        )

        if filepath:
            try:
                jsx = generate_oht_jsx(self.project_data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(jsx)
                print(f"✓ JSX 내보내기 완료 / JSX export complete: {filepath}")
                messagebox.showinfo("내보내기 완료", f"JSX 파일이 저장되었습니다.\n{filepath}")
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"JSX 내보내기 실패: {e}")

    def export_blender(self):
        """Blender Python 스크립트 내보내기 / Export Blender script"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )

        if filepath:
            try:
                script = generate_blender_script(self.project_data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(script)
                print(f"✓ Blender 스크립트 내보내기 완료 / Blender script export complete: {filepath}")
                messagebox.showinfo("내보내기 완료", f"Blender 스크립트가 저장되었습니다.\n{filepath}")
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"Blender 스크립트 내보내기 실패: {e}")

    def export_master_csv(self):
        """마스터 데이터 CSV 저장 (스테이션, MCP Zone, HID Zone, Zone-Address 매핑)
        parse_layout.py 의 CSV 출력과 동일한 형식"""
        if not self.project_data.get('nodes'):
            messagebox.showwarning("경고", "데이터가 없습니다. XML/ZIP을 먼저 가져오세요.")
            return

        dirpath = filedialog.askdirectory(title="CSV 마스터 데이터 저장 폴더 선택")
        if not dirpath:
            return

        fab = self.project_data.get('fab_name', 'Unknown')
        export_data = self._prepare_export_data()
        saved = []

        try:
            # 1) 스테이션 마스터 CSV
            stations = export_data.get('stations', [])
            if stations:
                p = os.path.join(dirpath, f'{fab}_Station_Master.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['Port_ID', 'Category', 'Type', 'No', 'Node_ID', 'X', 'Y', 'FAB'])
                    for s in stations:
                        w.writerow([
                            s.get('port_id', ''),
                            s.get('category', 0),
                            s.get('type', 0),
                            s.get('no', 0),
                            s.get('node_id', s.get('node', 0)),
                            round(s.get('x', 0), 2),
                            round(s.get('y', 0), 2),
                            fab
                        ])
                saved.append(f'Station: {len(stations)}행 → {fab}_Station_Master.csv')

            # 2) MCP Zone 마스터 CSV
            mcp_zones = export_data.get('mcp_zones', export_data.get('zones', []))
            if mcp_zones:
                p = os.path.join(dirpath, f'{fab}_MCP_Zone_Master.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['Zone_ID', 'Zone_No', 'Zone_Name', 'Type',
                                'Vehicle_Max', 'Vehicle_Precaution',
                                'Entry_Count', 'Exit_Count', 'CutLane_Count', 'FAB'])
                    for z in mcp_zones:
                        w.writerow([
                            z.get('id', 0),
                            z.get('no', 0),
                            z.get('name', ''),
                            z.get('type', 0),
                            z.get('vehicle_max', 0),
                            z.get('vehicle_precaution', 0),
                            len(z.get('entries', [])),
                            len(z.get('exits', [])),
                            len(z.get('cut_lanes', [])),
                            fab
                        ])
                saved.append(f'MCP Zone: {len(mcp_zones)}행 → {fab}_MCP_Zone_Master.csv')

            # 3) HID Zone 마스터 CSV (parse_layout.py 형식과 동일)
            hid_master = export_data.get('hid_master', [])
            if hid_master:
                p = os.path.join(dirpath, f'{fab}_HID_Zone_Master.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['Zone_ID', 'HID_ID', 'Full_Name', 'Address',
                                'Type', 'IN_Count', 'OUT_Count', 'IN_Lanes', 'OUT_Lanes',
                                'Vehicle_Max', 'Vehicle_Precaution', 'ZCU', 'FAB'])
                    for h in hid_master:
                        w.writerow([
                            h.get('zone_id', 0),
                            h.get('hid_id', ''),
                            h.get('full_name', ''),
                            h.get('address', 0),
                            h.get('zone_type', 0),
                            h.get('in_count', 0),
                            h.get('out_count', 0),
                            h.get('in_lanes', ''),
                            h.get('out_lanes', ''),
                            h.get('vehicle_max', 0),
                            h.get('vehicle_precaution', 0),
                            h.get('zcu', ''),
                            fab
                        ])
                saved.append(f'HID Zone: {len(hid_master)}행 → {fab}_HID_Zone_Master.csv')

            # 4) Zone ↔ Address 매핑 CSV
            zone_addr_map = export_data.get('zone_addr_map', {})
            if zone_addr_map:
                p = os.path.join(dirpath, f'{fab}_Zone_Address_Map.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['Zone_ID', 'Address_ID', 'FAB'])
                    total_rows = 0
                    for zid, addrs in zone_addr_map.items():
                        for addr in addrs:
                            w.writerow([zid, addr, fab])
                            total_rows += 1
                saved.append(f'Zone-Addr: {total_rows}행 → {fab}_Zone_Address_Map.csv')

            # 5) 노드 좌표 CSV
            nodes = export_data.get('nodes', [])
            if nodes:
                p = os.path.join(dirpath, f'{fab}_Node_Master.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['Address_ID', 'X', 'Y', 'CAD_X', 'CAD_Y',
                                'Symbol', 'Is_Station', 'Branch', 'Junction',
                                'HID_Included', 'StopZone', 'FAB'])
                    for n in nodes:
                        w.writerow([
                            n.get('id', 0),
                            round(n.get('x', 0), 2),
                            round(n.get('y', 0), 2),
                            round(n.get('cad_x', 0), 2),
                            round(n.get('cad_y', 0), 2),
                            n.get('symbol', ''),
                            n.get('is_station', 0),
                            1 if n.get('branch') else 0,
                            1 if n.get('junction') else 0,
                            n.get('hid_included', -1),
                            n.get('stopzone', 0),
                            fab
                        ])
                saved.append(f'Node: {len(nodes)}행 → {fab}_Node_Master.csv')

            # 6) 엣지(연결) CSV
            edges = export_data.get('edges', [])
            if edges:
                p = os.path.join(dirpath, f'{fab}_Edge_Master.csv')
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['From_Address', 'To_Address', 'Distance', 'Speed', 'Direction', 'FAB'])
                    for e in edges:
                        w.writerow([
                            e.get('from', e.get('start', 0)),
                            e.get('to', e.get('end', 0)),
                            e.get('distance', 0),
                            e.get('speed', 0),
                            e.get('direction', 0),
                            fab
                        ])
                saved.append(f'Edge: {len(edges)}행 → {fab}_Edge_Master.csv')

            msg = f"FAB: {fab}\n폴더: {dirpath}\n\n" + "\n".join(saved)
            messagebox.showinfo("CSV 마스터 데이터 저장 완료", msg)
            print(f"✓ CSV 마스터 데이터 저장: {dirpath}")
            for s in saved:
                print(f"  {s}")

        except Exception as e:
            messagebox.showerror("오류", f"CSV 저장 실패: {e}")
            print(f"✗ CSV 저장 오류: {e}")

    def export_layout_json(self):
        """전체 레이아웃 데이터를 layout_data.json 형식으로 저장
        (parse_layout.py 출력과 동일한 형식)"""
        if not self.project_data.get('nodes'):
            messagebox.showwarning("경고", "데이터가 없습니다. XML/ZIP을 먼저 가져오세요.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="layout_data.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            export_data = self._prepare_export_data()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False)

            size_mb = os.path.getsize(filepath) / 1024 / 1024
            n = len(export_data.get('nodes', []))
            e = len(export_data.get('edges', []))
            messagebox.showinfo("저장 완료",
                f"layout_data.json 저장 완료\n"
                f"노드: {n:,} | 엣지: {e:,}\n"
                f"파일 크기: {size_mb:.1f} MB\n"
                f"경로: {filepath}")
            print(f"✓ layout_data.json 저장: {filepath} ({size_mb:.1f} MB)")

        except Exception as e:
            messagebox.showerror("오류", f"JSON 저장 실패: {e}")

    def new_project(self):
        """새 프로젝트 / New project"""
        if messagebox.askyesno("새 프로젝트", "현재 프로젝트를 닫고 새 프로젝트를 만들까요?"):
            self.project_data = {
                'fab_name': 'New Project',
                'oht_count': 1,
                'rail_height': 5.0,
                'nodes': [],
                'edges': [],
                'stations': [],
                'zones': [],
                'vehicles': [],
            }
            self.current_file = None
            self._update_tree()
            self._update_status()
            self.redraw_canvas()
            self._show_project_properties()
            self.fab_name_var.set('New Project')

    def delete_selected(self):
        """선택된 객체 삭제 / Delete selected object"""
        if not self.selected_object or not self.selected_type:
            messagebox.showinfo("정보", "삭제할 객체가 선택되지 않았습니다.")
            return

        if self.selected_type == 'node':
            node_id = self.selected_object.get('id')
            self.project_data['nodes'] = [n for n in self.project_data['nodes'] if n.get('id') != node_id]
            # 관련 엣지도 삭제 / Also delete related edges
            self.project_data['edges'] = [e for e in self.project_data['edges']
                                         if e.get('start') != node_id and e.get('end') != node_id]

        elif self.selected_type == 'station':
            port_id = self.selected_object.get('port_id')
            self.project_data['stations'] = [s for s in self.project_data['stations']
                                            if s.get('port_id') != port_id]

        self.selected_object = None
        self.selected_type = None
        self._update_tree()
        self.redraw_canvas()
        messagebox.showinfo("삭제 완료", "객체가 삭제되었습니다.")

    def deselect_all(self):
        """선택 해제 / Deselect all"""
        self.selected_object = None
        self.selected_type = None
        self.prop_text.config(state=tk.NORMAL)
        self.prop_text.delete('1.0', tk.END)
        self.prop_text.config(state=tk.DISABLED)
        self.redraw_canvas()

    def select_all(self):
        """모두 선택 (미구현) / Select all (not implemented)"""
        messagebox.showinfo("정보", "전체 선택 기능은 아직 구현되지 않았습니다.")

    def _sync_toggle_button(self, attr_name):
        """토글 버튼 색상 동기화 / Sync toggle button appearance"""
        if attr_name in self._toggle_buttons:
            btn, var, on_color = self._toggle_buttons[attr_name]
            if getattr(self, attr_name):
                btn.config(bg=on_color, fg='#000000', font=("Arial", 9, "bold"))
            else:
                btn.config(bg='#333344', fg='#666666', font=("Arial", 9))

    def toggle_nodes(self):
        """노드 표시/숨기기 토글 / Toggle nodes visibility"""
        self.show_nodes = not self.show_nodes
        self.show_nodes_var.set(self.show_nodes)
        self._sync_toggle_button('show_nodes')
        self.redraw_canvas()

    def toggle_edges(self):
        """엣지 표시/숨기기 토글 / Toggle edges visibility"""
        self.show_edges = not self.show_edges
        self.show_edges_var.set(self.show_edges)
        self._sync_toggle_button('show_edges')
        self.redraw_canvas()

    def toggle_stations(self):
        """스테이션 표시/숨기기 토글 / Toggle stations visibility"""
        self.show_stations = not self.show_stations
        self.show_stations_var.set(self.show_stations)
        self._sync_toggle_button('show_stations')
        self.redraw_canvas()

    def toggle_zones(self):
        """Zone 표시/숨기기 토글 / Toggle zones visibility"""
        self.show_zones = not self.show_zones
        self.show_zones_var.set(self.show_zones)
        self._sync_toggle_button('show_zones')
        self.redraw_canvas()

    def _update_fab_name(self):
        """FAB 이름 업데이트 / Update FAB name"""
        self.project_data['fab_name'] = self.fab_name_var.get()
        self._update_status()

    def search_dialog(self):
        """검색 대화창 / Search dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("검색")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="노드 ID 또는 스테이션 검색:").pack(padx=10, pady=10)

        search_var = tk.StringVar()
        search_entry = ttk.Entry(dialog, textvariable=search_var, width=40)
        search_entry.pack(padx=10, pady=5)
        search_entry.focus()

        results_text = tk.Text(dialog, height=10, width=50, bg='#0f0f1a', fg='#cccccc')
        results_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        def do_search():
            query = search_var.get().lower()
            results_text.config(state=tk.NORMAL)
            results_text.delete('1.0', tk.END)

            # 노드 검색 / Search nodes
            for node in self.project_data.get('nodes', []):
                node_id = str(node.get('id', '')).lower()
                if query in node_id:
                    text = f"노드: {node.get('id')} @ ({node.get('x', 0):.0f}, {node.get('y', 0):.0f})\n"
                    results_text.insert(tk.END, text)

            # 스테이션 검색 / Search stations
            for station in self.project_data.get('stations', []):
                port_id = str(station.get('port_id', '')).lower()
                if query in port_id:
                    text = f"스테이션: {station.get('port_id')}\n"
                    results_text.insert(tk.END, text)

            results_text.config(state=tk.DISABLED)

        ttk.Button(dialog, text="검색", command=do_search).pack(padx=10, pady=5)
        search_entry.bind('<Return>', lambda e: do_search())

    def show_stats(self):
        """통계 대화창 / Statistics dialog"""
        stats = {
            '노드': len(self.project_data.get('nodes', [])),
            '엣지': len(self.project_data.get('edges', [])),
            '스테이션': len(self.project_data.get('stations', [])),
            'Zone': len(self.project_data.get('zones', [])),
            '차량': len(self.project_data.get('vehicles', [])),
        }

        nodes = self.project_data.get('nodes', [])
        if nodes:
            xs = [n.get('x', 0) for n in nodes]
            ys = [n.get('y', 0) for n in nodes]
            stats['좌표 범위 (X)'] = f"{min(xs):.0f} ~ {max(xs):.0f}"
            stats['좌표 범위 (Y)'] = f"{min(ys):.0f} ~ {max(ys):.0f}"

        dialog = tk.Toplevel(self.root)
        dialog.title("통계")
        dialog.geometry("300x400")

        text_widget = tk.Text(dialog, height=20, width=35, bg='#0f0f1a', fg='#cccccc')
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        text_widget.config(state=tk.NORMAL)
        text_widget.insert('1.0', "=" * 30 + "\n프로젝트 통계\n" + "=" * 30 + "\n\n")
        for key, value in stats.items():
            text_widget.insert(tk.END, f"{key:20s}: {value}\n")
        text_widget.config(state=tk.DISABLED)

    def show_pathfinding(self):
        """경로탐색 대화창 / Path finding dialog"""
        messagebox.showinfo("경로탐색", "경로탐색 기능은 아직 구현되지 않았습니다.")

    def show_help(self):
        """도움말 표시 / Show help"""
        help_text = """
OHT 3D Layout Builder - 사용법

기본 조작:
- 마우스 왼쪽 클릭: 객체 선택
- 마우스 오른쪽 드래그: 캔버스 이동 (Pan)
- 마우스 휠: 확대/축소 (Zoom)
- 마우스 중간 클릭: 전체 보기로 리셋

메뉴:
- 파일: 프로젝트 생성, 열기, 저장, 불러오기
- 보기: 확대/축소, 그리기 토글
- 내보내기: HTML, OBJ (Blender), JSX (React), Blender Script

성능:
- 45,000개 이상의 노드를 효율적으로 렌더링합니다.
- 줌 레벨에 따라 자동으로 세부사항이 조정됩니다 (LOD).
"""
        messagebox.showinfo("도움말", help_text)

    def show_about(self):
        """정보 표시 / Show about"""
        about_text = """OHT 3D Layout Builder v1.0

OHT 자동화된 운송 시스템 레이아웃 에디터
Editor for OHT (Overhead Track) automated transport systems

기능:
- XML/ZIP 파일에서 레이아웃 가져오기
- 2D 캔버스에서 시각화 및 편집
- HTML/OBJ/JSX/Blender 형식으로 내보내기
- 대규모 데이터 처리 (45,000+ 노드)

개발: Claude Code
라이선스: MIT
"""
        messagebox.showinfo("정보", about_text)

    def _show_progress(self, message):
        """진행 대화창 표시 / Show progress window"""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("처리 중...")
        self.progress_window.geometry("300x100")
        self.progress_window.resizable(False, False)

        ttk.Label(self.progress_window, text=message).pack(padx=20, pady=20)
        progress = ttk.Progressbar(self.progress_window, mode='indeterminate')
        progress.pack(padx=20, pady=10, fill=tk.X)
        progress.start()

        self.progress_window.update()

    def _hide_progress(self):
        """진행 대화창 숨기기 / Hide progress window"""
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None

    def _on_closing(self):
        """창 닫기 / On window close"""
        if self.project_data['nodes']:
            if messagebox.askyesno("종료", "저장하지 않은 변경사항이 있을 수 있습니다. 정말 종료하시겠습니까?"):
                self.root.destroy()
        else:
            self.root.destroy()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """메인 엔트리포인트 / Main entry point"""
    root = tk.Tk()
    root.title("OHT 3D Layout Builder v1.0")
    root.geometry("1400x900")
    root.minsize(1000, 600)

    app = OHTLayoutBuilderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
