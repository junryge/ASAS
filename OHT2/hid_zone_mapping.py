#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hid_zone_mapping.py - 원본 HID_Zone_Master.csv와 layout.xml 매핑

원본 CSV의 IN_Lanes를 기준으로 layout.xml의 McpZone ID를 찾아 매핑
"""

import os
import re
import csv
import zipfile
from pathlib import Path


def parse_lanes_from_csv(lanes_str):
    """CSV의 IN_Lanes/OUT_Lanes 문자열을 파싱"""
    if not lanes_str:
        return set()
    lanes = set()
    for lane in lanes_str.split('; '):
        lane = lane.strip()
        if '→' in lane:
            parts = lane.split('→')
            if len(parts) == 2:
                lanes.add((parts[0].strip(), parts[1].strip()))
    return lanes


def parse_mcp_zones_from_xml(xml_content):
    """layout.xml에서 McpZone 정보 추출"""
    print("McpZone 파싱 중...")

    zones = {}
    current_zone = None
    current_zone_id = None
    current_zone_no = None
    current_entries = []
    current_exits = []
    in_entry = False
    in_exit = False
    entry_start = None
    entry_end = None
    exit_start = None
    exit_end = None

    lines = xml_content.split('\n')
    total = len(lines)

    for i, line in enumerate(lines):
        if i % 500000 == 0:
            print(f"  {i:,}/{total:,} ({i*100//total}%)")

        line = line.strip()

        # McpZone 시작
        if '<group name="McpZone' in line and 'mcpzone.McpZone"' in line:
            # 이전 zone 저장
            if current_zone_id is not None:
                zones[current_zone_id] = {
                    'id': current_zone_id,
                    'no': current_zone_no,
                    'entries': current_entries.copy(),
                    'exits': current_exits.copy()
                }

            current_zone = line
            current_zone_id = None
            current_zone_no = None
            current_entries = []
            current_exits = []
            in_entry = False
            in_exit = False
            continue

        # Zone id/no 파라미터
        if current_zone and '<param ' in line:
            if 'key="id"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    try:
                        current_zone_id = int(match.group(1))
                    except:
                        current_zone_id = None
            elif 'key="no"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    try:
                        current_zone_no = int(match.group(1))
                    except:
                        current_zone_no = None

        # Entry 시작
        if current_zone and '<group name="Entry' in line and 'mcpzone.Entry"' in line:
            in_entry = True
            entry_start = None
            entry_end = None
            continue

        # Exit 시작
        if current_zone and '<group name="Exit' in line and 'mcpzone.Exit"' in line:
            in_exit = True
            exit_start = None
            exit_end = None
            continue

        # Entry/Exit 파라미터
        if in_entry and '<param ' in line:
            if 'key="start"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    entry_start = match.group(1)
            elif 'key="end"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    entry_end = match.group(1)

        if in_exit and '<param ' in line:
            if 'key="start"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    exit_start = match.group(1)
            elif 'key="end"' in line:
                match = re.search(r'value="([^"]*)"', line)
                if match:
                    exit_end = match.group(1)

        # 그룹 종료
        if '</group>' in line:
            if in_entry and entry_start and entry_end:
                current_entries.append((entry_start, entry_end))
                in_entry = False
            elif in_exit and exit_start and exit_end:
                current_exits.append((exit_start, exit_end))
                in_exit = False

    # 마지막 zone 저장
    if current_zone_id is not None:
        zones[current_zone_id] = {
            'id': current_zone_id,
            'no': current_zone_no,
            'entries': current_entries.copy(),
            'exits': current_exits.copy()
        }

    print(f"  총 {len(zones)}개 McpZone 파싱 완료")
    return zones


def find_matching_zone(csv_in_lanes, xml_zones):
    """CSV의 IN_Lanes와 매칭되는 XML Zone 찾기"""
    csv_lanes = parse_lanes_from_csv(csv_in_lanes)
    if not csv_lanes:
        return None, 0

    best_match = None
    best_score = 0

    for zone_id, zone_data in xml_zones.items():
        xml_lanes = set(zone_data['entries'])

        if not xml_lanes:
            continue

        # 교집합 크기로 매칭 점수 계산
        intersection = csv_lanes & xml_lanes
        if len(intersection) > best_score:
            best_score = len(intersection)
            best_match = zone_id

        # 완전 일치하면 바로 반환
        if csv_lanes == xml_lanes:
            return zone_id, len(intersection)

    return best_match, best_score


def create_mapping_csv():
    """매핑 CSV 생성"""
    script_dir = Path(__file__).parent.resolve()

    # 원본 CSV 읽기
    original_csv = script_dir / 'HID_Zone_Master.csv'
    if not original_csv.exists():
        print(f"오류: {original_csv} 파일을 찾을 수 없습니다")
        return

    print(f"원본 CSV 읽는 중: {original_csv}")
    original_zones = []
    with open(original_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_zones.append(row)
    print(f"  {len(original_zones)}개 Zone 로드")

    # layout.xml 읽기
    xml_path = script_dir / 'layout' / 'layout.xml'
    zip_path = script_dir / 'layout' / 'layout' / 'layout.zip'

    if xml_path.exists():
        print(f"layout.xml 읽는 중: {xml_path}")
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
    elif zip_path.exists():
        print(f"layout.zip에서 추출 중: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            with zf.open('layout.xml') as f:
                xml_content = f.read().decode('utf-8')
    else:
        print("오류: layout.xml 또는 layout.zip을 찾을 수 없습니다")
        return

    print(f"  XML 크기: {len(xml_content):,} bytes")

    # XML 파싱
    xml_zones = parse_mcp_zones_from_xml(xml_content)

    # 매핑 수행
    print("\n매핑 수행 중...")
    results = []
    matched = 0

    for orig in original_zones:
        csv_zone_id = orig.get('Zone_ID', '')
        in_lanes = orig.get('IN_Lanes', '')

        xml_zone_id, score = find_matching_zone(in_lanes, xml_zones)

        if xml_zone_id:
            matched += 1
            status = 'MATCHED'
        else:
            status = 'NOT_FOUND'

        results.append({
            'CSV_Zone_ID': csv_zone_id,
            'HID_No': orig.get('HID_No', ''),
            'XML_Zone_ID': xml_zone_id if xml_zone_id else '',
            'Match_Score': score,
            'Status': status,
            'Bay_Zone': orig.get('Bay_Zone', ''),
            'Full_Name': orig.get('Full_Name', ''),
            'IN_Lanes': in_lanes,
            'OUT_Lanes': orig.get('OUT_Lanes', ''),
            'Vehicle_Max': orig.get('Vehicle_Max', ''),
            'Vehicle_Precaution': orig.get('Vehicle_Precaution', ''),
            'ZCU': orig.get('ZCU', '')
        })

    print(f"  매칭 완료: {matched}/{len(original_zones)}")

    # 결과 CSV 저장
    output_path = script_dir / 'HID_Zone_Mapping.csv'
    print(f"\n결과 저장 중: {output_path}")

    headers = ['CSV_Zone_ID', 'HID_No', 'XML_Zone_ID', 'Match_Score', 'Status',
               'Bay_Zone', 'Full_Name', 'IN_Lanes', 'OUT_Lanes',
               'Vehicle_Max', 'Vehicle_Precaution', 'ZCU']

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)

    print(f"  완료! {os.path.getsize(output_path):,} bytes")
    print(f"\n=== 요약 ===")
    print(f"원본 Zone: {len(original_zones)}개")
    print(f"매칭 성공: {matched}개")
    print(f"매칭 실패: {len(original_zones) - matched}개")


if __name__ == '__main__':
    create_mapping_csv()
