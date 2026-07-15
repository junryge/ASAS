#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TightLoop Sentinel — 행동(Action) 계층
======================================
문서 구조의 2단. Chronos-Bolt 가 준 미래 분포(q10/q50/q90)를
'경계 있는·인과적 운영 조치'로 변환한다.

    [예측/Forecast]  Chronos-Bolt  →  미래 값 분포 (quantile)
                          │
                          ▼
    [행동/Action]    TightLoop Sentinel  →  운영 조치
                        · 경보 단계 (alert stage 0~3)
                        · 예비 조정 (reserve adjustment, bounded)
                        · center drift (선제 운영중심 이동, bounded)
                        · tail 위험 (상단/하단 분리)
                        · 선제 감지 lead(분)

원본 TightLoop Sentinel 은 구현 비공개(뉴로모픽 엔진, IP 보호)이므로,
논문이 공개한 '인터페이스 수준 행동'만 충실히 재현한다:
  · causal-lag  : 조치는 직전까지의 예측만 사용 (미래 누수 없음)
  · bounded     : 모든 조치는 정해진 범위로 클램프 (폭주 방지)
  · distribution-aware : 상단/하단 tail·center·reserve 분리 표현
  · low churn   : 히스테리시스 + 지수평활로 조치 요동 억제
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ----------------------------------------------------------------------
# 분위수 → 임계 초과 확률 (근사 CDF)
# ----------------------------------------------------------------------
def exceed_prob(q10: float, q50: float, q90: float, threshold: float) -> float:
    """(q10,0.1)(q50,0.5)(q90,0.9) 로 CDF 근사 → P(X > threshold)."""
    a, b, c = sorted((q10, q50, q90))
    pts = [(a, 0.10), (b, 0.50), (c, 0.90)]

    def cdf(x):
        if x <= pts[0][0]:
            span = (pts[1][0] - pts[0][0]) or 1e-9
            slope = (pts[1][1] - pts[0][1]) / span
            return max(0.0, pts[0][1] + slope * (x - pts[0][0]))
        if x >= pts[2][0]:
            span = (pts[2][0] - pts[1][0]) or 1e-9
            slope = (pts[2][1] - pts[1][1]) / span
            return min(1.0, pts[2][1] + slope * (x - pts[2][0]))
        for i in range(2):
            x0, p0 = pts[i]; x1, p1 = pts[i + 1]
            if x0 <= x <= x1:
                span = (x1 - x0) or 1e-9
                return p0 + (p1 - p0) * (x - x0) / span
        return 0.5

    return max(0.0, min(1.0, 1.0 - cdf(threshold)))


# ----------------------------------------------------------------------
# 설정 / 상태 / 출력
# ----------------------------------------------------------------------
@dataclass
class SentinelConfig:
    threshold: float                 # 임계값 (학습기간에서 산출 권장)
    p_on: float = 0.60               # 경보 켜짐: 초과확률 이상
    p_off: float = 0.35              # 경보 해제: 초과확률 미만 (히스테리시스)
    reserve_gain: float = 0.5        # 예비 조정 게인 (문서 기본 0.5)
    action_gain: float = 1.0         # center 조정 게인 (문서 기본 1.0)
    reserve_max: float = 1.0         # 예비 조정 상한 (정규화, bounded)
    center_max: float = 1.0          # center 조정 상한 (bounded)
    smooth: float = 0.5              # 조치 지수평활 계수 (0=평활강, 1=평활없음)


@dataclass
class SentinelState:
    active: bool = False
    prev_center: float = 0.0
    prev_reserve: float = 0.0
    churn: int = 0


@dataclass
class SentinelAction:
    # 경보
    stage: int                       # 0 없음 / 1 조기경보 / 2 주의보 / 3 확정
    stage_name: str
    exceed_prob: float               # 미래 지평 중 최대 초과확률
    lead_min: int | None             # 초과가 처음 예상되는 스텝(분). None=예상 안 됨
    # 운영 조치 (bounded)
    center_adjust: float             # 운영중심 선제 이동 [-center_max, +center_max]
    reserve_adjust: float            # 예비(버퍼) 증설 [0, reserve_max]
    # 분포 인식
    tail_upper: float                # 상단 tail 위험 = P(X>threshold)
    tail_lower: float                # 하단 tail 위험 = P(X<lower_ref)
    # 권고 (사람이 읽는 조치)
    recommendation: str


STAGE_NAME = {0: "0단계 이벤트없음", 1: "1단계 조기경보",
              2: "2단계 주의보", 3: "3단계 ⭐확정"}


class TightLoopSentinel:
    """단일 신호(item)에 대한 Sentinel 행동 계층."""

    def __init__(self, cfg: SentinelConfig):
        self.cfg = cfg
        self.state = SentinelState()

    def step(self, q10: list, q50: list, q90: list) -> SentinelAction:
        cfg = self.cfg
        st = self.state
        H = len(q50)

        # 1) 지평별 초과확률 → 최대치 + 최초 초과 스텝(lead)
        best_p, lead = 0.0, None
        for h in range(H):
            p = exceed_prob(q10[h], q50[h], q90[h], cfg.threshold)
            if p > best_p:
                best_p = p
            if lead is None and p >= cfg.p_on:
                lead = h + 1

        # 2) 히스테리시스 (경보 요동 억제 = low churn)
        prev = st.active
        if best_p >= cfg.p_on:
            active = True
        elif best_p < cfg.p_off:
            active = False
        else:
            active = prev
        if active != prev:
            st.churn += 1
        st.active = active

        # 3) 경보 단계
        if not active:
            stage = 1 if best_p >= 0.40 else 0        # 중간확률=조기경보(선제)
        else:
            stage = 3 if best_p >= 0.85 else 2

        # 4) center drift (선제 운영중심 이동) — bounded, causal
        #    미래 q50 추세가 임계를 향해 오르면 미리 중심을 올림.
        drift = (q50[min(H - 1, 4)] - q50[0])         # 5스텝 앞 중심 이동량
        norm_drift = drift / max(1e-9, cfg.threshold)
        raw_center = cfg.action_gain * norm_drift
        raw_center = max(-cfg.center_max, min(cfg.center_max, raw_center))
        # 지수평활 (직전 조치와 블렌딩 → 요동↓)
        center = cfg.smooth * raw_center + (1 - cfg.smooth) * st.prev_center
        st.prev_center = center

        # 5) reserve adjustment (예비/버퍼 증설) — bounded, 상단 tail·구간폭 기반
        #    상단 초과확률 + 예측구간폭(불확실성)에 비례해 예비를 늘림.
        interval_w = max(0.0, (q90[0] - q10[0])) / max(1e-9, cfg.threshold)
        raw_reserve = cfg.reserve_gain * (best_p * 0.7 + min(1.0, interval_w) * 0.3)
        raw_reserve = max(0.0, min(cfg.reserve_max, raw_reserve))
        reserve = cfg.smooth * raw_reserve + (1 - cfg.smooth) * st.prev_reserve
        st.prev_reserve = reserve

        # 6) tail 위험 (상단/하단 분리)
        tail_upper = best_p
        lower_ref = cfg.threshold * 0.3               # 하단 참조(과소, 예: 예비 낭비)
        tail_lower = 1.0 - exceed_prob(q10[0], q50[0], q90[0], lower_ref)

        # 7) 권고 문구
        rec = self._recommend(stage, lead, center, reserve)

        return SentinelAction(
            stage=stage, stage_name=STAGE_NAME[stage],
            exceed_prob=round(best_p, 3), lead_min=lead,
            center_adjust=round(center, 3), reserve_adjust=round(reserve, 3),
            tail_upper=round(tail_upper, 3), tail_lower=round(tail_lower, 3),
            recommendation=rec,
        )

    @staticmethod
    def _recommend(stage, lead, center, reserve) -> str:
        if stage == 0:
            return "정상 — 조치 불필요"
        parts = []
        if stage >= 2:
            parts.append("경보 격상")
        else:
            parts.append("조기 관찰")
        if reserve >= 0.5:
            parts.append(f"예비 증설(+{reserve:.2f})")
        elif reserve >= 0.2:
            parts.append(f"예비 소폭(+{reserve:.2f})")
        if center >= 0.2:
            parts.append("운영중심 선제 상향")
        if lead is not None:
            parts.append(f"약 {lead}분 뒤 임계 예상")
        return " · ".join(parts)


if __name__ == "__main__":
    # 스모크: 임계 12 를 향해 상승하는 예측 분포
    cfg = SentinelConfig(threshold=12.0)
    s = TightLoopSentinel(cfg)
    q10 = [10.0, 10.5, 11.0, 11.6, 12.2]
    q50 = [11.0, 11.6, 12.2, 12.9, 13.6]
    q90 = [12.0, 12.7, 13.4, 14.2, 15.0]
    a = s.step(q10, q50, q90)
    print("stage:", a.stage, a.stage_name)
    print("exceed_prob:", a.exceed_prob, "lead:", a.lead_min)
    print("center_adjust:", a.center_adjust, "reserve_adjust:", a.reserve_adjust)
    print("tail_upper:", a.tail_upper, "tail_lower:", a.tail_lower)
    print("권고:", a.recommendation)
