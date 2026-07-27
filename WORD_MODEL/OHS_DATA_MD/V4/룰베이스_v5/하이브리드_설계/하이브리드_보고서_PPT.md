---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section{font-family:'Malgun Gothic',sans-serif;font-size:26px;background:#f8fafc;color:#1e293b}
  h1{color:#0f766e;font-size:44px}
  h2{color:#0f766e;border-bottom:3px solid #14b8a6;padding-bottom:6px}
  strong{color:#dc2626}
  table{font-size:22px}
  th{background:#0f766e;color:#fff}
  .big{font-size:34px;text-align:center;margin-top:40px}
  .note{color:#64748b;font-size:20px}
---

# 정체 30분 사전예측
## 하이브리드 AI 시스템

<br>

**"운영자가 알기 30분 전에, AI가 미리 알린다"**

<span class="note">M16A Hubroom 반송 정체 · 2026-07</span>

---

## 1. 지금 뭐가 문제인가?

<br>

- 정체가 나면 → 운영자가 **뒤늦게** 발견하고 대응
- 기존 **룰(규칙)** 은 정해진 조건만 봐서 → **미묘한 전조를 놓침**
- 정체를 **미리** 알 수 있다면? → 30분 먼저 손 쓸 수 있음

<br>

<div class="big">🎯 목표 : 정체 <strong>30분 전</strong> 미리 경보</div>

---

## 2. 어떻게? — 3명의 전문가에게 물어본다

전문가 한 명만 믿으면 틀릴 수 있다 → **3명에게 물어보고 합의**

| 전문가 | 역할 | 비유 |
|--------|------|------|
| 🟠 **룰베이스** | 확실한 정체를 딱 잡음 | 규정집 든 베테랑 |
| 🔵 **정상 AI** | 평소와 다른 낌새를 먼저 챔 | 눈치 빠른 신입 |
| 🩷 **비정상 AI** | "진짜 정체 맞아?" 확인 | 꼼꼼한 검수자 |

<span class="note">→ 세 명의 판단을 <strong>하이브리드 판정</strong>이 종합</span>

---

## 3. 핵심 아이디어 — "정상만 가르친다"

<br>

- AI에게 **정상 상태만** 잔뜩 보여줌 → "이게 평소 모습"이라고 배움
- 실제 운영 중 **평소와 다르면** → AI가 "어? 이상한데?" 하고 감지
- 이 낌새가 **정체보다 30분 먼저** 나타남

<br>

<div class="big">평소를 알면, <strong>달라진 순간</strong>을 안다</div>

---

## 4. 하이브리드 판정 — 3명이 합의하면 진짜

<br>

| 룰베이스 | 정상 AI | 비정상 AI | 결과 |
|:---:|:---:|:---:|---|
| 위험 | 이상 | 정체 | **🔴 확실 정체 — 즉시 대응** |
| 정상 | **이상** | **정체** | **🟡 30분 전 조기경보 ⭐** |
| 정상 | 이상 | 정체아님 | ⚪ 무시 (설비작업 등) |
| 정상 | 정상 | — | ✅ 안전 |

<span class="note">⭐ 룰은 아직 조용한데 AI 둘이 "곧 정체" → <strong>30분 먼저 경보</strong></span>

---

## 5. 이 시스템의 가치

<br>

| | 효과 |
|---|---|
| ⏱️ **선행 예측** | 정체 **30분 전** 미리 알림 |
| 🎯 **오탐 감소** | "정체 아닌 이상"(설비작업)은 걸러냄 |
| 🔍 **설명 가능** | 어느 지표가 왜 위험한지 근거 제시 |
| 🛡️ **안전** | 3명 합의라 한 명 틀려도 버팀 |

<br>

<div class="big">더 <strong>빠르고</strong>, 더 <strong>정확하고</strong>, 더 <strong>믿을 수 있게</strong></div>

---

## 6. 진행 계획

<br>

| 단계 | 내용 | 상태 |
|---|---|:---:|
| 1 | 정상 데이터 준비 | ✅ 완료 |
| 2 | 정상 AI 학습 | 🔄 진행 |
| 3 | **30분 선행 검증** | ⬜ 핵심 |
| 4 | 비정상 AI 학습 | ⬜ |
| 5 | 하이브리드 판정 완성 | ⬜ |
| 6 | 룰 + AI 병행 운영 | ⬜ |

---

# 요약

<br>

<div class="big">
룰베이스 + 정상 AI + 비정상 AI<br>
→ <strong>하이브리드 판정</strong><br><br>
"세 개가 합의하면 진짜다"<br>
= 정체 <strong>30분 사전예측</strong>
</div>
