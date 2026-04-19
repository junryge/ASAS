#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macro_predictor.py - OHT 매크로 예측기

MD 문서에서 검증된 예측 모델:
- 큐: 10분 이동평균 + 선형 외삽
- TAT: 상수 2.88분 (24시간 균일)
- 물동량: ~20,000건/시 (균일)
- 혼잡 구간: HID 저속 구간 고정
- 데드락 위험: OBS 추세 (36분 빌드업)
"""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import (
    TAT_AVERAGE_MIN, TAT_MEDIAN_MIN,
    THROUGHPUT_PER_HOUR,
    QUEUE_NORMAL_RANGE, QUEUE_AVG,
    OBS_NORMAL_RANGE, OBS_WARNING_THRESHOLD,
    OBS_DANGER_THRESHOLD, OBS_DEADLOCK_THRESHOLD,
)


class MacroPredictor:
    """매크로 예측기"""

    def __init__(self, history_size: int = 30):
        # 최근 N분 히스토리 (이동평균용)
        self.queue_history: deque = deque(maxlen=history_size)
        self.obs_history: deque = deque(maxlen=history_size)
        self.driving_history: deque = deque(maxlen=history_size)

        # 현재 값
        self.current_queue: int = 0
        self.current_obs: int = 0
        self.current_driving: int = 0
        self.current_time: Optional[datetime] = None

        # 상관관계 데이터 (전체 기간)
        self.queue_tat_pairs: List[Tuple[int, float]] = []  # (큐, TAT) 쌍
        self.queue_obs_pairs: List[Tuple[int, int]] = []

    def update(self, t: datetime, star: dict, vehicle_stats: dict):
        """스타 지표 + 차량 통계로 업데이트"""
        self.current_time = t

        if star:
            q = star.get('queue_total', 0)
            obs = star.get('obs_bz_stop', 0)
            driving = star.get('driving', 0)

            if q > 0:
                self.current_queue = q
                self.queue_history.append((t, q))
            if obs >= 0:
                self.current_obs = obs
                self.obs_history.append((t, obs))
            if driving > 0:
                self.current_driving = driving
                self.driving_history.append((t, driving))

            # 상관관계 데이터 축적
            if q > 0 and obs >= 0:
                self.queue_obs_pairs.append((q, obs))

    def get_prediction(self) -> dict:
        """매크로 예측 결과"""
        return {
            'queue_10min': self._predict_queue_10min(),
            'tat': self._predict_tat(),
            'throughput': self._predict_throughput(),
            'deadlock_risk': self._predict_deadlock_risk(),
            'obs_trend': self._get_obs_trend(),
            'current': {
                'queue': self.current_queue,
                'obs': self.current_obs,
                'driving': self.current_driving,
            },
        }

    def _predict_queue_10min(self) -> dict:
        """10분 후 큐 예측 — 이동평균 + 선형 외삽"""
        if len(self.queue_history) < 3:
            return {
                'value': self.current_queue,
                'confidence': 'low',
                'method': 'insufficient_data',
            }

        # 최근 10분 이동평균
        recent = list(self.queue_history)[-10:]
        avg = sum(v for _, v in recent) / len(recent)

        # 선형 추세 (최근 5분)
        if len(recent) >= 5:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]
            avg_first = sum(v for _, v in first_half) / len(first_half)
            avg_second = sum(v for _, v in second_half) / len(second_half)
            trend_per_min = (avg_second - avg_first) / (len(recent) / 2)

            predicted = avg + trend_per_min * 10  # 10분 외삽
        else:
            predicted = avg
            trend_per_min = 0

        # 범위 (±50)
        return {
            'value': round(predicted),
            'range_low': round(predicted - 50),
            'range_high': round(predicted + 50),
            'trend': round(trend_per_min, 1),
            'trend_direction': 'up' if trend_per_min > 5 else 'down' if trend_per_min < -5 else 'stable',
            'moving_avg': round(avg),
            'confidence': 'high' if len(recent) >= 8 else 'medium',
            'method': 'linear_extrapolation',
        }

    def _predict_tat(self) -> dict:
        """TAT 예측 — 상수 2.88분 (24시간 균일 확인됨)"""
        return {
            'average': TAT_AVERAGE_MIN,
            'median': TAT_MEDIAN_MIN,
            'prediction_10min': TAT_AVERAGE_MIN,  # 변동 없음
            'confidence': 'high',
            'method': 'constant (24h uniform)',
            'note': '큐 1000~1800 범위에서 TAT 2.4~2.6분으로 안정적',
        }

    def _predict_throughput(self) -> dict:
        """물동량 예측 — ~20,000건/시 균일"""
        return {
            'per_hour': THROUGHPUT_PER_HOUR,
            'per_minute': round(THROUGHPUT_PER_HOUR / 60),
            'confidence': 'high',
            'method': 'constant (day/night same)',
            'note': '주간 ~20,000건/시, 야간 ~19,700건/시',
        }

    def _predict_deadlock_risk(self) -> dict:
        """데드락 위험도 예측 — OBS 추세 기반"""
        if len(self.obs_history) < 3:
            return {
                'level': 'unknown',
                'obs_current': self.current_obs,
                'method': 'insufficient_data',
            }

        recent_obs = [v for _, v in list(self.obs_history)[-10:]]
        avg_obs = sum(recent_obs) / len(recent_obs)

        # 추세 분석
        if len(recent_obs) >= 5:
            first = sum(recent_obs[:len(recent_obs)//2]) / (len(recent_obs)//2)
            second = sum(recent_obs[len(recent_obs)//2:]) / (len(recent_obs) - len(recent_obs)//2)
            trend = second - first
        else:
            trend = 0

        # 위험 레벨 판단
        if avg_obs >= OBS_DEADLOCK_THRESHOLD:
            level = "CRITICAL"
            message = f"OBS {int(avg_obs)}대 — 데드락 발생 가능"
        elif avg_obs >= OBS_DANGER_THRESHOLD:
            level = "DANGER"
            message = f"OBS {int(avg_obs)}대 — 위험 수준, 빌드업 중"
        elif avg_obs >= OBS_WARNING_THRESHOLD:
            level = "WARNING"
            message = f"OBS {int(avg_obs)}대 — 주의 필요"
        elif trend > 10:
            level = "WATCH"
            message = f"OBS {int(avg_obs)}대 — 상승 추세 감지"
        else:
            level = "NORMAL"
            message = f"OBS {int(avg_obs)}대 — 정상 범위"

        return {
            'level': level,
            'message': message,
            'obs_current': self.current_obs,
            'obs_avg': round(avg_obs, 1),
            'obs_trend': round(trend, 1),
            'obs_trend_direction': 'rising' if trend > 5 else 'falling' if trend < -5 else 'stable',
            'thresholds': {
                'normal': f"{OBS_NORMAL_RANGE[0]}~{OBS_NORMAL_RANGE[1]}",
                'warning': str(OBS_WARNING_THRESHOLD),
                'danger': str(OBS_DANGER_THRESHOLD),
                'deadlock': str(OBS_DEADLOCK_THRESHOLD),
            },
        }

    def _get_obs_trend(self) -> List[dict]:
        """OBS 추이 (차트용)"""
        return [
            {'time': t.strftime("%H:%M"), 'value': v}
            for t, v in self.obs_history
        ]

    def get_correlations(self) -> dict:
        """데이터 간 상관관계 (MD 문서 검증 결과 반영)"""
        # 큐↔OBS 상관계수
        queue_obs_r = self._calc_correlation(self.queue_obs_pairs) if len(self.queue_obs_pairs) > 10 else None

        return {
            'queue_tat': {
                'correlation': 'weak_positive',
                'r_value': 0.12,
                'description': '큐가 올라가면 TAT도 약간 증가 (2.4~2.6분 범위)',
                'data_source': 'OHT_데이터_연관관계_월드모델_예측.md',
                'detail': [
                    {'queue_range': '1000~1200', 'tat': 2.49},
                    {'queue_range': '1200~1400', 'tat': 2.53},
                    {'queue_range': '1600~1800', 'tat': 2.62},
                ],
            },
            'queue_obs': {
                'correlation': 'none',
                'r_value': round(queue_obs_r, 3) if queue_obs_r else 0.03,
                'description': 'OBS 정지는 큐와 거의 무관. 물리적 구간 혼잡이 원인',
                'detail': [
                    {'queue_range': '<1300', 'obs': 154},
                    {'queue_range': '>1600', 'obs': 157},
                ],
            },
            'queue_hid_speed': {
                'correlation': 'none',
                'r_value': -0.01,
                'description': '큐가 올라가도 HID 구간 속도 변화 없음. 물리적 구조에 의해 결정',
                'detail': [
                    {'queue_range': '1000~1200', 'avg_speed': 92.0},
                    {'queue_range': '1200~1400', 'avg_speed': 91.9},
                ],
            },
            'time_tat': {
                'correlation': 'none',
                'description': 'TAT는 24시간 균일 (~2.88분)',
            },
            'time_throughput': {
                'correlation': 'none',
                'description': '물동량은 24시간 균일 (~20,000건/시)',
            },
        }

    def _calc_correlation(self, pairs: List[Tuple]) -> float:
        """피어슨 상관계수 계산"""
        n = len(pairs)
        if n < 3:
            return 0.0

        x = [p[0] for p in pairs]
        y = [p[1] for p in pairs]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)
