#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forecast-to-Action 가드레일 (TightLoop Sentinel '역할' 자체 구현)
================================================================
Chronos-Bolt 예측 분포(q10/q50/q90)를 받아 '경계 있는·인과적' 운영 판정으로 변환.

TightLoop preprint가 공개한 인터페이스 수준 행동을 재현:
  · 인과적 지연(causal-lag): 직전 스텝까지의 context로 예측 → 미래 정보 누수 없음
  · 경계 있는(bounded) 위험도: 0~50(영역), 히스테리시스로 요동 억제
  · 분포 인식: 임계 초과 '확률'로 판단 (점 예측 한 방에 안 흔들림)
  · 선제 감지: 미래 h스텝 중 언제 임계 초과가 예상되는지 → lead 확보

핵심 아이디어:
  룰베이스   : "지금 값 >= 임계"  → 반응형, 오탐/미탐 트레이드오프에 갇힘
  가드레일   : "h분 뒤 값이 임계를 넘을 확률 P" → P가 켜짐임계 넘으면 경보,
               꺼짐임계 밑으로 내려가야 해제 (히스테리시스)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def exceed_prob(q10: float, q50: float, q90: float, threshold: float) -> float:
    """
    3개 분위수(q10/q50/q90)로 근사 CDF를 만들고 P(X > threshold) 반환.

    알려진 점: (q10, 0.10), (q50, 0.50), (q90, 0.90)
    구간 내부는 선형보간, 바깥쪽 tail은 기울기 유지해 외삽(0~1 클램프).
    단조 증가 보장을 위해 q10<=q50<=q90 로 정렬.
    """
    a, b, c = sorted((q10, q50, q90))
    pts = [(a, 0.10), (b, 0.50), (c, 0.90)]

    def cdf(x: float) -> float:
        if x <= pts[0][0]:
            # 하단 외삽: (q10,0.1)~(q50,0.5) 기울기 사용
            span = pts[1][0] - pts[0][0] or 1e-9
            slope = (pts[1][1] - pts[0][1]) / span
            return max(0.0, pts[0][1] + slope * (x - pts[0][0]))
        if x >= pts[2][0]:
            span = pts[2][0] - pts[1][0] or 1e-9
            slope = (pts[2][1] - pts[1][1]) / span
            return min(1.0, pts[2][1] + slope * (x - pts[2][0]))
        # 내부 보간
        for i in range(2):
            x0, p0 = pts[i]
            x1, p1 = pts[i + 1]
            if x0 <= x <= x1:
                span = (x1 - x0) or 1e-9
                return p0 + (p1 - p0) * (x - x0) / span
        return 0.5

    return max(0.0, min(1.0, 1.0 - cdf(threshold)))


@dataclass
class SignalConfig:
    """영역·신호 하나에 대한 가드레일 설정."""
    name: str                 # 예: "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"
    threshold: float          # 임계값 (04_임계값.md 추천값)
    weight: float = 1.0       # unified 기여 가중
    p_on: float = 0.60        # 경보 켜짐: 초과확률이 이 값 이상
    p_off: float = 0.35       # 경보 해제: 초과확률이 이 값 미만 (히스테리시스)
    max_area_score: float = 50.0


@dataclass
class SignalState:
    """히스테리시스/인과 상태 (신호별로 유지)."""
    active: bool = False
    last_prob: float = 0.0
    last_lead: Optional[int] = None
    churn: int = 0            # 켜짐↔꺼짐 전환 횟수 (알람피로 대리지표)


@dataclass
class SignalVerdict:
    name: str
    prob: float               # 대표 초과확률 (미래 h스텝 중 최대)
    lead_min: Optional[int]   # 초과가 처음 예상되는 스텝(분). None=예상 안 됨
    area_score: float         # 0~max_area_score
    active: bool
    threshold: float
    q50_at_lead: Optional[float] = None


class ForecastGuardrail:
    """
    여러 신호의 예측 분포 → 통합 위험 판정.
    상태를 들고 있어(stateful) 히스테리시스·churn 추적이 가능.
    """

    def __init__(self, configs: list[SignalConfig]):
        self.configs = {c.name: c for c in configs}
        self.states: dict[str, SignalState] = {
            c.name: SignalState() for c in configs
        }

    def _eval_signal(self, cfg: SignalConfig, forecast: dict) -> SignalVerdict:
        q10s, q50s, q90s = forecast["q10"], forecast["q50"], forecast["q90"]
        horizon = len(q50s)
        st = self.states[cfg.name]

        best_p = 0.0
        lead = None
        q50_at_lead = None
        for h in range(horizon):
            p = exceed_prob(q10s[h], q50s[h], q90s[h], cfg.threshold)
            if p > best_p:
                best_p = p
            # 처음으로 켜짐임계를 넘는 스텝 = 선제 감지 lead
            if lead is None and p >= cfg.p_on:
                lead = h + 1  # 1-indexed 분
                q50_at_lead = q50s[h]

        # 히스테리시스: 켜짐/꺼짐 임계 분리 → 경계 근처 요동 억제
        prev_active = st.active
        if best_p >= cfg.p_on:
            new_active = True
        elif best_p < cfg.p_off:
            new_active = False
        else:
            new_active = prev_active  # 중간 구간은 이전 상태 유지
        if new_active != prev_active:
            st.churn += 1
        st.active = new_active
        st.last_prob = best_p
        st.last_lead = lead

        # 경계 있는 위험도: 초과확률 → 0~max. 활성일 때만 부여.
        area_score = 0.0
        if new_active:
            # p_on~1.0 을 0~max 로 선형 매핑
            frac = (best_p - cfg.p_on) / max(1e-9, (1.0 - cfg.p_on))
            area_score = min(cfg.max_area_score,
                             cfg.max_area_score * max(0.0, frac))

        return SignalVerdict(
            name=cfg.name, prob=best_p, lead_min=lead,
            area_score=area_score, active=new_active,
            threshold=cfg.threshold, q50_at_lead=q50_at_lead,
        )

    def step(self, forecasts: dict[str, dict]) -> dict:
        """
        한 시점 판정.
        forecasts: {signal_name: {"q10":[...],"q50":[...],"q90":[...]}, ...}
        반환: 기존 predictor 스키마와 호환되는 dict
        """
        verdicts: list[SignalVerdict] = []
        for name, cfg in self.configs.items():
            if name not in forecasts:
                continue
            verdicts.append(self._eval_signal(cfg, forecasts[name]))

        active = [v for v in verdicts if v.active]

        # 통합 위험점수: 가중 area_score 합 → 0~500 스케일로 정규화
        raw = sum(v.area_score * self.configs[v.name].weight for v in verdicts)
        unified = min(500, round(raw * 5))  # 대략적 스케일 (튜닝 대상)

        # hot area (가장 위험한 신호)
        hot = max(verdicts, key=lambda v: v.area_score, default=None)

        # stage 판정 (예측 기반):
        #   3=확정: 활성 2개 이상 or 최고확률>=0.85
        #   2=주의: 활성 1개 & 확률>=p_on
        #   1=조기경보: 활성 없지만 중간확률(0.4~p_on) 신호 존재 → 선제
        #   0=없음
        max_p = max((v.prob for v in verdicts), default=0.0)
        near = [v for v in verdicts if not v.active and v.prob >= 0.40]
        if len(active) >= 2 or max_p >= 0.85:
            stage = 3
        elif len(active) == 1:
            stage = 2
        elif near:
            stage = 1
        else:
            stage = 0

        stage_names = {0: "0단계 이벤트없음", 1: "1단계 조기경보",
                       2: "2단계 주의보", 3: "3단계 ⭐확정"}

        # 최소 lead (활성 신호 중 가장 이른 감지)
        leads = [v.lead_min for v in active if v.lead_min is not None]
        best_lead = min(leads) if leads else None

        unified_level = self._risk_level(unified)

        return {
            "stage": stage,
            "stage_name": stage_names[stage],
            "unified_risk_score": unified,
            "unified_risk_level": unified_level,
            "hot_area": hot.name if hot else "",
            "hot_score": round(hot.area_score, 1) if hot else 0.0,
            "predicted_lead_min": best_lead,
            "max_exceed_prob": round(max_p, 3),
            "active_signals": [v.name for v in active],
            "total_churn": sum(s.churn for s in self.states.values()),
            "signals": {
                v.name: {
                    "prob": round(v.prob, 3),
                    "lead_min": v.lead_min,
                    "area_score": round(v.area_score, 1),
                    "active": v.active,
                    "threshold": v.threshold,
                } for v in verdicts
            },
        }

    @staticmethod
    def _risk_level(score: float) -> str:
        # 05_결과해석.md 등급표와 동일
        if score >= 250:
            return "매우위험"
        if score >= 150:
            return "위험"
        if score >= 80:
            return "주의"
        if score >= 65:
            return "경계"
        if score >= 30:
            return "관심"
        return "정상"


# 기본 신호 설정 (04_임계값.md 추천값 반영) — HUBROOM 중심 핵심 신호
def default_configs() -> list[SignalConfig]:
    return [
        SignalConfig("M16HUB.QUE.TIME.AVGTOTALTIME1MIN", threshold=12.0, weight=1.5),
        SignalConfig("M16HUB.QUE.M14TOM16.MESCURRENTQCNT", threshold=100.0, weight=1.0),
        SignalConfig("M16HUB.STRATE.ALL.FABSTORAGERATIO", threshold=30.0, weight=0.8),
        SignalConfig("M14.QUE.LOAD.AVGLOADTIME1MIN", threshold=3.6, weight=1.0),
        SignalConfig("M16A.QUE.LOAD.AVGLOADTIME1MIN", threshold=3.4, weight=1.0),
        SignalConfig("M16B.QUE.LOAD.AVGLOADTIME1MIN", threshold=6.0, weight=1.0),
    ]


if __name__ == "__main__":
    # 스모크 테스트: 임계 12.0 신호가 상승 → 초과확률/lead 확인
    g = ForecastGuardrail([SignalConfig("sig", threshold=12.0)])
    fc = {"sig": {"q10": [10.0, 10.5, 11.0, 11.6, 12.2],
                  "q50": [11.0, 11.6, 12.2, 12.9, 13.6],
                  "q90": [12.0, 12.7, 13.4, 14.2, 15.0]}}
    out = g.step(fc)
    print("stage:", out["stage"], out["stage_name"])
    print("lead_min:", out["predicted_lead_min"], "max_p:", out["max_exceed_prob"])
    print("signals:", out["signals"])
