---
title: AMOS 개요와 메뉴
type: concept
domain: 버츄얼 아바타
tags: [AMOS, 모니터링, 메뉴, AIAMHSMonitoringSystem]
summary: AMOS(AI AMHS Monitoring System)는 AMHS 운영 현황·설비 상태·통신 이상·서버 리소스 이상을 한곳에서 보는 지능형 통합 모니터링 시스템이다. 화면은 12개 메뉴로 나뉜다.
sources: []
author: 
updated: 
---

## AMOS 가 무엇인가

**AMOS** = **A**I A**M**HS M**o**nitoring **S**ystem.

AMHS 의 **운영 현황 · 설비 상태 · 통신 이상 · 서버 리소스 이상**을
**통합적으로** 보기 위한 지능형 모니터링 시스템이다.

Site · FAB · Layout · Bridge 등 **여러 관점의 화면**을 제공해서
AMHS 이상 상황을 빨리 찾아내고, Alarm 이력과 설정을 체계적으로 관리한다.
AI Agent Chatbot 으로 운영 정보 조회와 업무 지원도 한다.

### 세 가지 축

| 축 | 하는 일 |
|---|---|
| 통합 모니터링 | Site · FAB 단위 AMHS 운영 현황을 **한 화면**에서 확인 |
| 이상 감지 | 통신 상태 · 서버 리소스 이상을 탐지해 신속한 대응 지원 |
| 사용자 맞춤 구성 | 필요한 데이터를 조합해 **사용자별** 모니터링 화면 구성 |

## ★AMOS 화면 설명이지, 지금 수치가 아니다

이 문서는 **AMOS 라는 시스템이 무엇을 보여 주는가**를 적은 것이다.
지금 이 순간의 점수·건수·등급은 여기에 없다.
현재 수치는 관제(real_time_amhs) 실시간 데이터로 답한다 — 둘을 섞지 않는다.

## 메뉴 구성 (12개)

| 메뉴 | 무엇을 보나 |
|---|---|
| Site 모니터링 | 이천 Site 의 AMHS 이상 현황을 통합 확인 |
| Layout 모니터링 | FAB Layout 기반 VHL 이동 현황과 구간별 이상 상태 |
| Bridge 모니터링 | M14–M16 간 이동 현황, Bridge Conveyor · Lifter · Queue 상태 |
| Custom 모니터링 | 원하는 데이터를 골라 맞춤형 화면 구성 |
| FAB 모니터링 | FAB 별 AMHS 운영 상태와 주요 이상 현황을 종합 |
| FAB 상세 모니터링 | 선택한 FAB 의 장비 · 구간 · 이상 상태를 상세 조회 |
| MES-MCS-MCP 통신 이상 감지 | 시스템 간 통신 상태 확인, 비정상 통신 탐지 |
| 서버 리소스 이상 감지 | 서버 CPU · Memory · Disk 등 주요 리소스 감시 |
| Alarm 발생 이력 | 발생한 Alarm 의 시간 · 대상 · 유형 · 처리 상태 조회 |
| Alarm 설정 | 이상 감지 조건 · Alarm 기준 · 알림 정책 설정 |
| 연락처 관리 | Alarm 통보 대상자와 조직별 연락처 정보 관리 |
| AI Agent Chatbot | 자연어로 운영 현황 조회, 사용자 업무 지원 |

## 어느 메뉴로 가야 하나

찾는 것이 정해져 있으면 바로 간다.

- **전체가 어떤가** → Site 모니터링 → FAB 모니터링
- **어디서 막혔나** → Layout 모니터링 (구간) · Bridge 모니터링 (M14–M16)
- **한 FAB 을 파고든다** → FAB 상세 모니터링
- **시스템끼리 말이 안 통한다** → MES-MCS-MCP 통신 이상 감지
- **서버가 무겁다** → 서버 리소스 이상 감지
- **지난 일을 본다** → Alarm 발생 이력
- **기준을 바꾼다** → Alarm 설정 · 연락처 관리
- **말로 묻는다** → AI Agent Chatbot

## 관련 페이지

- [[AMOS 모니터링 화면]]
- [[AMOS 이상 감지]]
- [[AMOS Alarm 과 연락처]]
- [[AMOS AI Agent Chatbot]]

## 참고 소스

(AMOS USER GUIDE 원문을 소스로 올린 뒤 `(소스 #N)` 으로 여기에 적는다)
