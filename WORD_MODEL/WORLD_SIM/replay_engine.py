#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_engine.py - OHT 실 데이터 리플레이 엔진

CSV 데이터를 시간순으로 재생하며 차량 위치를 업데이트한다.
플레이/일시정지/속도조절/시간점프 지원.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

from data_loader import DateDataLoader, LayoutData, HIDZoneData
from world_model import WorldModel
from macro_predictor import MacroPredictor


class ReplayState:
    """리플레이 상태"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class ReplayEngine:
    """실 데이터 리플레이 엔진"""

    def __init__(self, layout: LayoutData, hid_zones: HIDZoneData):
        self.layout = layout
        self.hid_zones = hid_zones

        # 월드모델
        adj = {}
        for nid, neighbors in layout.adj.items():
            adj[nid] = [(nb, layout.edge_dist.get((nid, nb), 1000.0)) for nb in neighbors]

        zone_data = {zid: z for zid, z in hid_zones.zones.items()}
        self.world = WorldModel(
            graph=adj,
            edge_dist_map=layout.edge_dist,
            zone_data=zone_data,
            in_lane_to_zone=hid_zones.in_lane_to_zone,
            out_lane_to_zone=hid_zones.out_lane_to_zone,
        )

        # 예측기
        self.predictor = MacroPredictor()

        # 데이터 로더
        self.data_loader: Optional[DateDataLoader] = None
        self.current_date: str = ""

        # 리플레이 상태
        self.state = ReplayState.STOPPED
        self.speed = 1.0  # 재생 속도 배율
        self.current_frame_idx = 0
        self.current_time: Optional[datetime] = None

        # 누적 차량 상태 (vid → 최신 상태)
        self._cumulative_state: Dict[str, dict] = {}

        # 현재 프레임 데이터
        self.current_vehicles: List[dict] = []
        self.current_star: Optional[dict] = None
        self.current_hid_events: List[dict] = []
        self.current_rail_cuts: List[dict] = []

        # 콜백
        self._on_frame: Optional[Callable] = None

    def load_date(self, date_key: str) -> dict:
        """특정 날짜 데이터 로드"""
        self.state = ReplayState.STOPPED
        self.current_date = date_key
        self.current_frame_idx = 0
        self._cumulative_state = {}

        self.data_loader = DateDataLoader(date_key)
        stats = self.data_loader.load_all()

        if self.data_loader.time_start:
            self.current_time = self.data_loader.time_start

        return {
            'date': date_key,
            'stats': stats,
            'time_start': str(self.data_loader.time_start) if self.data_loader.time_start else None,
            'time_end': str(self.data_loader.time_end) if self.data_loader.time_end else None,
            'total_frames': len(self.data_loader.oht_timeline),
            'description': self.data_loader.date_config.get('description', ''),
        }

    def play(self):
        """재생 시작"""
        if not self.data_loader or not self.data_loader.oht_timeline:
            return
        self.state = ReplayState.PLAYING

    def pause(self):
        """일시정지"""
        self.state = ReplayState.PAUSED

    def stop(self):
        """정지 (처음으로)"""
        self.state = ReplayState.STOPPED
        self.current_frame_idx = 0
        if self.data_loader and self.data_loader.time_start:
            self.current_time = self.data_loader.time_start

    def set_speed(self, speed: float):
        """재생 속도 설정 (1=실시간, 2=2배, 10=10배, 0=MAX)"""
        self.speed = max(0, speed)

    def jump_to_time(self, target_time_str: str) -> bool:
        """특정 시각으로 점프 (HH:MM:SS 또는 HH:MM)"""
        if not self.data_loader or not self.data_loader.oht_timeline:
            return False

        # 시간 파싱
        base_date = self.data_loader.oht_timeline[0][0].date()
        try:
            parts = target_time_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            target = datetime(base_date.year, base_date.month, base_date.day, hour, minute, second)

            # 자정 넘어간 경우
            if target < self.data_loader.oht_timeline[0][0]:
                target += timedelta(days=1)
        except (ValueError, IndexError):
            return False

        # 해당 시각의 프레임 인덱스 찾기
        idx = self.data_loader._bisect_time(self.data_loader.oht_timeline, target)
        if 0 <= idx < len(self.data_loader.oht_timeline):
            self.current_frame_idx = idx
            self.current_time = self.data_loader.oht_timeline[idx][0]
            self._update_current_frame()
            return True
        return False

    def jump_to_frame(self, frame_idx: int) -> bool:
        """특정 프레임으로 점프 (누적 상태 재구축)"""
        if not self.data_loader or not self.data_loader.oht_timeline:
            return False
        if 0 <= frame_idx < len(self.data_loader.oht_timeline):
            # 누적 상태 재구축: 처음부터 해당 프레임까지 모든 업데이트 적용
            self._cumulative_state = {}
            for i in range(frame_idx + 1):
                _, updates = self.data_loader.oht_timeline[i]
                for v in updates:
                    if v.get('vid'):
                        self._cumulative_state[v['vid']] = v

            self.current_frame_idx = frame_idx
            self.current_time = self.data_loader.oht_timeline[frame_idx][0]
            self.current_vehicles = list(self._cumulative_state.values())
            # 점프 시 속도 누적 상태 초기화
            self.world.velocity_tracker.reset()
            self.world.load_vehicles_from_frame(self.current_vehicles, self.current_time)

            # 스타/HID/RAIL_CUT도 업데이트
            _, self.current_star, self.current_hid_events, self.current_rail_cuts = \
                self.data_loader.get_frame_at(self.current_time)
            if self.current_star:
                self.predictor.update(self.current_time, self.current_star, self.world.get_vehicle_stats())

            return True
        return False

    def advance_frame(self) -> bool:
        """한 프레임 전진. 끝이면 False 반환."""
        if not self.data_loader or not self.data_loader.oht_timeline:
            return False

        if self.current_frame_idx >= len(self.data_loader.oht_timeline):
            self.state = ReplayState.STOPPED
            return False

        self._update_current_frame()
        self.current_frame_idx += 1
        return True

    def _update_current_frame(self):
        """현재 프레임 데이터 업데이트 (누적 상태 기반)"""
        if not self.data_loader or self.current_frame_idx >= len(self.data_loader.oht_timeline):
            return

        t, updates = self.data_loader.oht_timeline[self.current_frame_idx]
        self.current_time = t

        # 누적 상태에 업데이트 적용
        for v in updates:
            if v.get('vid'):
                self._cumulative_state[v['vid']] = v

        self.current_vehicles = list(self._cumulative_state.values())

        # 월드모델에 차량 상태 로드 (frame_time 전달 → 차량별 속도 계산)
        self.world.load_vehicles_from_frame(self.current_vehicles, self.current_time)

        # 다른 데이터 소스에서 현재 시각 데이터 가져오기
        _, self.current_star, self.current_hid_events, self.current_rail_cuts = \
            self.data_loader.get_frame_at(t)

        # 예측기 업데이트
        if self.current_star:
            self.predictor.update(t, self.current_star, self.world.get_vehicle_stats())

    def get_current_snapshot(self) -> dict:
        """현재 시점 전체 스냅샷 (WebSocket 전송용)"""
        vehicle_stats = self.world.get_vehicle_stats()
        positions = self.world.get_vehicle_positions(self.layout)

        prediction = self.predictor.get_prediction()

        # HID 구간 속도 (현재 시점)
        hid_speeds = {}
        for ev in self.current_hid_events:
            hid_id = ev.get('from_hid', 0)
            if hid_id > 0:
                if hid_id not in hid_speeds:
                    hid_speeds[hid_id] = []
                hid_speeds[hid_id].append(ev.get('speed', 0))

        hid_summary = {}
        for hid_id, speeds in hid_speeds.items():
            hid_summary[hid_id] = round(sum(speeds) / len(speeds), 1) if speeds else 0

        # Zone별 차량 수 계산
        zone_counts = {}
        for v in self.current_vehicles:
            edge = (v.get('currentNode', 0), v.get('nextNode', 0))
            zid = self.hid_zones.in_lane_to_zone.get(edge)
            if zid is None:
                zid = self.hid_zones.out_lane_to_zone.get(edge)
            if zid is not None:
                zone_counts[zid] = zone_counts.get(zid, 0) + 1

        return {
            'time': self.current_time.strftime("%Y-%m-%d %H:%M:%S") if self.current_time else "",
            'time_short': self.current_time.strftime("%H:%M:%S") if self.current_time else "",
            'frame': self.current_frame_idx,
            'totalFrames': len(self.data_loader.oht_timeline) if self.data_loader else 0,
            'state': self.state,
            'speed': self.speed,
            'date': self.current_date,

            # 차량 통계
            'vehicleStats': vehicle_stats,

            # 차량 위치 (맵용)
            'vehicles': positions,

            # 스타 지표
            'star': self.current_star,

            # 매크로 예측
            'prediction': prediction,

            # HID 속도
            'hidSpeeds': hid_summary,

            # RAIL_CUT 이벤트
            'railCuts': self.current_rail_cuts,

            # Zone별 차량 수
            'zoneCounts': zone_counts,
        }

    def get_star_history(self) -> List[dict]:
        """스타 전체 타임라인 (차트용)"""
        if self.data_loader:
            return self.data_loader.get_star_history()
        return []

    def get_hid_speed_summary(self) -> dict:
        """HID 구간별 속도 통계"""
        if self.data_loader:
            return self.data_loader.get_hid_speed_summary()
        return {}

    def get_ts_events(self) -> List[dict]:
        """ts_resource 분 단위 집계"""
        if not self.data_loader:
            return []
        result = []
        for t, ev in self.data_loader.ts_events:
            entry = {'time': t.strftime("%H:%M")}
            entry.update(ev)
            result.append(entry)
        return result

    async def replay_loop(self, on_frame: Callable):
        """비동기 리플레이 루프"""
        while True:
            if self.state == ReplayState.PLAYING:
                if not self.advance_frame():
                    self.state = ReplayState.STOPPED

                snapshot = self.get_current_snapshot()
                await on_frame(snapshot)

                # 속도에 따른 대기
                if self.speed > 0:
                    wait = 0.5 / self.speed  # 기본 0.5초 간격
                    await asyncio.sleep(max(0.01, wait))
                else:
                    # MAX 속도: 최소 대기
                    await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.1)
