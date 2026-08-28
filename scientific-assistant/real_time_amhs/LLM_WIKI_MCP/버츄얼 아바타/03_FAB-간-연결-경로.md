---
title: FAB 간 연결 경로
type: concept
domain: 버츄얼 아바타
tags: [연결, CNV, LFT, 4AFC3201, 4AFC3301, 4ALF, 4ABLD, 6ABL60, 6ALF, 6ABL01, WIS_M16WT, 경로]
summary: M16 HUBROOM(3F)을 기준으로 각 FAB이 무엇으로 이어지는가 — 연결 수단과 호기명, 경유 예시.
sources: []
author: 
updated: 
---

## 개요

어느 FAB이 무엇으로 이어지는지, **호기명까지** 적는다.
장치가 각각 무엇인지는 [[반송 장치 종류와 역할]] 을 본다.

## 연결표

| 구간 | 수단 | 호기명 |
|---|---|---|
| M14A(3F) ↔ M16 HUBROOM(3F) | **CNV** | 남측 `4AFC3201` / 북측 `4AFC3301` |
| M14A(3F) ↔ M10A(2F) | **LFT** | — |
| M14B(7F) ↔ M14A | **LFT** | `4ALF` 로 시작 |
| M14B(7F) ↔ M16 HUBROOM(3F) | **LFT** | `4ABLD` 로 시작 |
| M14분석실(B1F) ↔ M16 HUBROOM(3F) | **LFT** | — |
| M16A(6F) ↔ M16 HUBROOM(3F) | **LFT** | `6ABL60~` 로 시작 |
| M16A(6F) ↔ M16B(10F) | **LFT** | `6ALF` 로 시작 |
| M16A(6F) ↔ M16EUV(2F) | **LFT** | `6ABL01~` 로 시작 |
| M16A(6F) ↔ R4(6F) | 같은 층 — 아래 참고 | — |
| M16EUV(2F) ↔ M16WT(2F) | **WIS STK** | `WIS_M16WT` (FAB간반송 가상장비 STK) |

### M16A(6F) ↔ R4(6F)

두 곳은 **같은 층에 있지만 이동 시 FAB간 반송으로 간주**한다.
중간에 **OHT명이 바뀌기** 때문이다.

## 경유 예시

**M14A(3F) → M16**
```
M14A(3F) → CNV(4AFC3201 / 4AFC3301) → M16 HUBROOM(3F) → M16
```

**M10A(2F) → M16**
```
M10A(2F) → LFT → M14A(3F) → M16 HUBROOM(3F) → M16
```

**M14A → M16WT** (가장 긴 경로)
```
M14A → CNV → M16 HUBROOM → LFT → M16EUV → WIS STK → M16WT
```

## 읽는 법

- 호기명은 **원문 그대로** 쓴다. `6ABL60~` 를 "6ABL 계열" 로 뭉개면 검색에서 못 찾는다.
- 층이 다르면 **LFT**, 같은 층 건물 간이면 **CNV** 가 기본이다.
- 경로 중 한 구간이라도 막히면 그 뒤가 전부 밀린다 —
  [[M16 HUBROOM 유의 지표]] 로 어디서 막혔는지 좁힌다.

## 관련 페이지

- [[M16 HUBROOM 개요]]
- [[반송 장치 종류와 역할]]
- [[M16 HUBROOM 유의 지표]]

## 참고 소스

(연결도 이미지를 소스로 올린 뒤 `(소스 #N)` 으로 여기에 적는다)
