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

    def get_obs_jam_history(self) -> List[dict]:
        """전체 OHT 타임라인에서 분 단위 OBS / JAM 카운트 집계.

        UDP 누적 상태를 시간 흐름대로 따라가며 매 분마다
        state=6(OBS_BZ_STOP) 차량 수와 state=7(JAM) 차량 수를 측정.
        """
        if not self.data_loader or not self.data_loader.oht_timeline:
            return []

        from collections import defaultdict
        cumulative_state: Dict[str, dict] = {}
        per_minute: Dict[str, dict] = {}

        for t, updates in self.data_loader.oht_timeline:
            for v in updates:
                vid = v.get('vid', '')
                if vid:
                    cumulative_state[vid] = v
            t_min = t.strftime('%H:%M')
            obs_count = sum(1 for v in cumulative_state.values() if v.get('state') == 6)
            jam_count = sum(1 for v in cumulative_state.values() if v.get('state') == 7)
            # 같은 분에 여러 sample이 있으면 마지막 값 (분 끝)을 유지
            per_minute[t_min] = {'time': t_min, 'obs': obs_count, 'jam': jam_count}

        return list(per_minute.values())

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

    def get_bottleneck_analysis(self) -> dict:
        """HID_INOUT 구간 통과 × ts_resource 작업 부하 교차 분석.

        UDP 와 무관하게 HID_INOUT(구간 통과 이벤트) 과 ts_resource(작업 명령
        타임라인) 만으로 병목 구간을 찾고, 원인이 외부(작업 몰림) 인지 내부
        (그 구간 자체 문제) 인지 분류해 반환한다.
        """
        # 진단 정보를 항상 summary 에 실어 반환 (데이터 없을 때 원인 파악용)
        diag = {
            "hid_events": 0,
            "ts_events": 0,
            "sections_raw": 0,
            "sections_with_limit": 0,
            "sections_above_threshold": 0,
            "reason": "",
        }
        if not self.data_loader:
            diag["reason"] = "data_loader 없음 (날짜 로드 안됨)"
            return {"sections": [], "workload_timeline": [], "summary": diag}
        diag["hid_events"] = len(self.data_loader.hid_events)
        diag["ts_events"] = len(self.data_loader.ts_events)

        if not self.data_loader.hid_events:
            diag["reason"] = "HID_INOUT 파일 없음/비어있음 (이 날짜에 hid_inout CSV 없음)"
            return {"sections": [], "workload_timeline": [], "summary": diag}

        from collections import defaultdict

        # 1) HID 이벤트를 (from_hid, to_hid, 분) 으로 그룹핑
        section_buckets: Dict[tuple, Dict[datetime, list]] = defaultdict(lambda: defaultdict(list))
        section_limit: Dict[tuple, int] = {}
        for t, ev in self.data_loader.hid_events:
            fh, th = ev.get('from_hid'), ev.get('to_hid')
            if not fh or not th:
                continue
            key = (fh, th)
            t_min = t.replace(second=0, microsecond=0)
            section_buckets[key][t_min].append((t, ev.get('vhl_id', '')))
            lim = ev.get('vhl_count_limit')
            if lim and lim > 0:
                section_limit[key] = lim
        diag["sections_raw"] = len(section_buckets)
        diag["sections_with_limit"] = len(section_limit)

        # 2) ts_resource 분별 부하 timeline — 없어도 병목은 보여주되 상관분석만 스킵
        ts_timeline: Dict[datetime, int] = {t_min: ev.get('total', 0) for t_min, ev in self.data_loader.ts_events}
        has_ts = bool(ts_timeline)
        if has_ts:
            ts_mins_sorted = sorted(ts_timeline.keys())
            ts_values = [ts_timeline[t] for t in ts_mins_sorted]
            ts_peak_time = ts_mins_sorted[ts_values.index(max(ts_values))]
            ts_mean = sum(ts_values) / len(ts_values)
        else:
            ts_mins_sorted = []
            ts_values = []
            ts_peak_time = None
            ts_mean = 0.0

        def _pearson(xs, ys):
            n = len(xs)
            if n < 2:
                return 0.0
            mx = sum(xs) / n
            my = sum(ys) / n
            num = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys))
            dx2 = sum((xi - mx) ** 2 for xi in xs)
            dy2 = sum((yi - my) ** 2 for yi in ys)
            if dx2 == 0 or dy2 == 0:
                return 0.0
            return num / ((dx2 ** 0.5) * (dy2 ** 0.5))

        # 3) 구간별 분석. vhl_count_limit 이 없으면 차량 Max 기본값(37) 사용.
        DEFAULT_LIMIT = 37
        sections: List[dict] = []
        sections_analyzed = 0
        for key, minute_map in section_buckets.items():
            limit = section_limit.get(key, 0)
            if limit <= 0:
                limit = DEFAULT_LIMIT  # fallback — 제거하지 않음

            # 분별 사용률 + 차량별 이벤트 시각 (체류시간 proxy 계산용)
            usage_series: Dict[datetime, float] = {}
            vid_times: Dict[str, List[datetime]] = defaultdict(list)
            for t_min, evs in minute_map.items():
                usage_series[t_min] = (len(evs) / limit) * 100.0
                for t, vid in evs:
                    if vid:
                        vid_times[vid].append(t)

            # 같은 차량의 연속 이벤트 간격 = 구간 체류시간 proxy (초)
            intervals: List[float] = []
            for times in vid_times.values():
                times.sort()
                for i in range(1, len(times)):
                    delta = (times[i] - times[i - 1]).total_seconds()
                    if 1 <= delta <= 600:  # 1초~10분 범위만 유효 (노이즈 제거)
                        intervals.append(delta)

            usage_values = list(usage_series.values())
            if not usage_values:
                continue

            usage_avg = sum(usage_values) / len(usage_values)
            sv = sorted(usage_values)
            p95_idx = min(int(len(sv) * 0.95), len(sv) - 1)
            usage_p95 = sv[p95_idx]
            # 병목 후보 임계값 낮춤: 너무 높으면 모두 필터링됨. 10% 이상만 후보.
            if usage_p95 < 10:
                continue

            sections_analyzed += 1
            dwell_avg = (sum(intervals) / len(intervals)) if intervals else 0.0

            # 구간 피크 시각
            peak_time = max(usage_series, key=usage_series.get)

            # ts 와 usage 시계열 상관 (공통 분에서만, ts 있을 때만)
            if has_ts:
                common_mins = sorted(set(usage_series.keys()) & set(ts_timeline.keys()))
                if len(common_mins) >= 10:
                    u_arr = [usage_series[t] for t in common_mins]
                    t_arr = [ts_timeline[t] for t in common_mins]
                    corr = _pearson(u_arr, t_arr)
                else:
                    corr = 0.0
            else:
                corr = 0.0

            # 원인 판정 — ts_events 있을 때만 external 판정 가능
            if has_ts and ts_peak_time is not None:
                time_diff_sec = abs((peak_time - ts_peak_time).total_seconds())
                if time_diff_sec <= 600 and corr >= 0.5:
                    cause = "external"
                elif usage_p95 >= 50:
                    cause = "internal"
                else:
                    cause = "mixed"
            else:
                # ts_resource 없으면 사용률만으로 판정
                cause = "internal" if usage_p95 >= 50 else "mixed"

            # 좌표 (layout.nodes 에서 from/to 중 찾아지는 쪽 사용)
            cx, cy = 0.0, 0.0
            if key[0] in self.layout.nodes:
                cx, cy = self.layout.nodes[key[0]]
            elif key[1] in self.layout.nodes:
                cx, cy = self.layout.nodes[key[1]]

            # zone 이름 (있으면)
            zone_id = self.hid_zones.in_lane_to_zone.get(key) or self.hid_zones.out_lane_to_zone.get(key)
            zone_name = f"{key[0]}→{key[1]}"
            if zone_id and zone_id in self.hid_zones.zones:
                zone_name = self.hid_zones.zones[zone_id].get('fullName', zone_name)

            # 병목 스코어: 사용률 P95 × 체류시간 (둘 다 0~1 정규화)
            bottleneck_score = (usage_p95 / 100.0) * min(dwell_avg / 60.0, 1.0)

            sections.append({
                "from_hid": key[0],
                "to_hid": key[1],
                "zone_name": zone_name,
                "count_total": sum(len(evs) for evs in minute_map.values()),
                "usage_pct_avg": round(usage_avg, 1),
                "usage_pct_peak": round(usage_p95, 1),
                "dwell_avg_sec": round(dwell_avg, 1),
                "bottleneck_score": round(bottleneck_score, 3),
                "cause": cause,
                "peak_time": peak_time.strftime("%H:%M"),
                "ts_correlation": round(corr, 2),
                "cx": round(cx, 1),
                "cy": round(cy, 1),
            })

        # 4) 정렬 + TOP-20
        sections.sort(key=lambda s: s["bottleneck_score"], reverse=True)
        top_sections = sections[:20]
        diag["sections_above_threshold"] = sections_analyzed
        if not sections_analyzed:
            diag["reason"] = f"구간 {len(section_buckets)}개 모두 사용률 10% 미만 (해당 날짜는 전반적으로 여유 운영)"

        # 5) 요약
        external_count = sum(1 for s in top_sections if s["cause"] == "external")
        internal_count = sum(1 for s in top_sections if s["cause"] == "internal")
        total_top = max(1, len(top_sections))

        if ts_peak_time is not None:
            peak_end = ts_peak_time + timedelta(hours=1)
            peak_hour_str = f"{ts_peak_time.strftime('%H:00')}-{peak_end.strftime('%H:00')}"
        else:
            peak_hour_str = "-"

        workload_timeline = [
            {
                "time": t_min.strftime("%H:%M"),
                "total": ev.get('total', 0),
                "unassigned": ev.get('unassigned', 0),
            }
            for t_min, ev in self.data_loader.ts_events
        ]

        return {
            "sections": top_sections,
            "workload_timeline": workload_timeline,
            "summary": {
                "section_count": len(section_buckets),
                "bottleneck_count": len(top_sections),
                "external_pct": round(external_count / total_top * 100),
                "internal_pct": round(internal_count / total_top * 100),
                "peak_hour": peak_hour_str,
                "ts_peak_total": int(max(ts_values)) if ts_values else 0,
                "ts_avg_total": round(ts_mean, 1),
                # 진단 정보 병합 — 결과 비었을 때 원인 파악용
                "hid_events": diag["hid_events"],
                "ts_events": diag["ts_events"],
                "sections_raw": diag["sections_raw"],
                "sections_with_limit": diag["sections_with_limit"],
                "sections_above_threshold": diag["sections_above_threshold"],
                "reason": diag["reason"] or ("ts_resource 없음 → 외부/내부 판정 제한" if not has_ts else ""),
            },
        }

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
