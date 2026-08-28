---
title: M16 HUBROOM 유의 지표
type: concept
domain: 버츄얼 아바타
tags: [SORTERWAITCOUNTOVER, Sorter, MLUD, 6FIOB, 지표, 정체]
summary: 반송 정체를 먼저 드러내는 지표 — Sorter 대기(SORTERWAITCOUNTOVER)와 M16 HUBROOM MLUD(6FIOB~) 관련 지표.
sources: []
author: 
updated: 
---

## 개요

엔지니어들이 **유의 깊게 관찰하는 지표**들이다. 점수나 알람보다 먼저
움직이는 경우가 있어, 정체를 앞서 알아채는 데 쓴다.

## Sorter — SORTERWAITCOUNTOVER

Sorter는 Wafer를 공정을 진행할 수 있게끔 변환하는 장치다
([[반송 장치 종류와 역할]] 참고).

**`SORTERWAITCOUNTOVER` 와 같은 지표가 급격히 증가하면 반송이 정체됐음을
유추할 수 있다.** 그래서 엔지니어들이 유의 깊게 관찰한다.

- 대기Q가 많다 = **그만큼 반송해야 할 양이 많다는 방증**
- 값 자체보다 **급격한 증가**를 본다

## MLUD — M16 HUBROOM `6FIOB~`

**M16 HUBROOM에는 다수의 MLUD가 있으며 `6FIOB` 로 시작한다.**

상황에 따라 두 방향으로 쓰인다.

- 사람이 M14A의 FOUP을 **M16 HUBROOM MLUD에 투입**
- VHL이 운송하여 **M16 HUBROOM MLUD에서 나온 FOUP을 M14A로 직접 운반**

**따라서 MLUD 관련 지표들도 유의해야 할 지표다.**

> MLUD는 사람 손이 닿는 자리다. port가 비활성화되어 있으면 경로가 살아
> 있어도 FOUP이 멈춘다 — 포트 활성 여부를 같이 본다
> ([[반송 장치 종류와 역할]] 의 포트 규칙).

## 관련 페이지

- [[M16 HUBROOM 개요]]
- [[반송 장치 종류와 역할]]
- [[FAB 간 연결 경로]]

## 참고 소스

(이미지·문서를 소스로 올린 뒤 `(소스 #N)` 으로 여기에 적는다)
