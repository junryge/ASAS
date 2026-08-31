# M16 HUBROOM 반송 도메인 지식

관제 수치로는 답이 안 나오는 것들 — 용어·구조·경로다.
"LFT 가 뭐야", "M14 에서 M16 으로 어떻게 넘어가", "Sorter 대기Q 가 왜 중요해"
같은 질문의 답이 여기 있다.

**0. 이 문서는 M16 HUBROOM 을 기준으로 연관된 반도체 FAB 만 기술한다.**
무관한 건물은 적지 않는다.

## 1. M16 HUBROOM 이란

**M16 HUBROOM**(= M16 Bridge)은 **M14 와 M16 간 물류 이동을 가능하게 하는
공간**이다. 층은 **3F**.

## 2. 연관 건물·층 현황

| 건물 | 구역 (층) |
|---|---|
| M14 | M14A(3F) · M14B(7F) · M14분석실(B1F) |
| M16 | M16A(6F) · M16B(10F) · M16EUV(2F) · M16WT(2F) · R4(6F) |
| 허브 | M16 HUBROOM(3F) |

## 3. FOUP 이 경유하는 반송 장치

| 장치 | 다른 이름 | 무엇을 하나 |
|---|---|---|
| **VHL** | — | FOUP 을 레일로 이동. 각 장치 Port 에서 load / port 로 unload |
| **OHT** | — | **VHL 을 제어하는 주체/시스템** |
| **LFT** | **ZT** | 리프터. FOUP 의 **층간 반송**. input port 에 오면 rack master 로 목적지 output port 로 |
| **CNV** | — | 컨베이어. input port 에 오면 목적지 output port 로 |
| **STK** | — | 스토커. FOUP **임시 저장** |
| **STB** | **ZFS** | FOUP 임시 저장 |
| **Sorter** | — | **FOSB ↔ FOUP 변환**. Wafer 가 입고되면 FOUP 형태로 dumping 되어 반송을 거치며 각 장비에서 공정 시작 |
| **MLUD** | **FIO** | 사람이 Manual Input 에 두면 Auto Output 으로 옮겨 OHT 가 load. 반대로 OHT 가 Auto Input 에 두면 Manual Output 으로 옮겨 사람이 get |

### 포트 규칙

- **LFT · CNV · Sorter · MLUD** — FOUP 기준 **input port 로 들어가서
  output port 로 나온다.** port 는 Manual/Auto × Input/Output 으로 나뉘어
  네 가지다: **MI · MO · AI · AO**
- **STK · STB** — input port 에 오면 rack master 가 shelf 에 저장하고,
  호출하면 다시 output port 에 놓는다
- **port 는 사람/시스템이 활성화·비활성화할 수 있다.**
  → 경로가 살아 있어도 port 가 죽어 있으면 FOUP 이 멈춘다

## 4. FAB 간 연결

| 구간 | 수단 | 호기명 |
|---|---|---|
| M14A(3F) ↔ M16 HUBROOM(3F) | **CNV** | 남측 `4AFC3201` · 북측 `4AFC3301` |
| M14A(3F) ↔ M10A(2F) | **LFT** | — |
| M14B(7F) ↔ M14A | **LFT** | `4ALF` 로 시작 |
| M14B(7F) ↔ M16 HUBROOM(3F) | **LFT** | `4ABLD` 로 시작 |
| M14분석실(B1F) ↔ M16 HUBROOM(3F) | **LFT** | — |
| M16A(6F) ↔ M16 HUBROOM(3F) | **LFT** | `6ABL60~` 로 시작 |
| M16A(6F) ↔ M16B(10F) | **LFT** | `6ALF` 로 시작 |
| M16A(6F) ↔ M16EUV(2F) | **LFT** | `6ABL01~` 로 시작 |
| M16A(6F) ↔ R4(6F) | 같은 층이지만 FAB 간 반송 | 중간에 OHT 명이 바뀐다 |
| M16EUV(2F) ↔ M16WT(2F) | **WIS STK** | `WIS_M16WT` (FAB 간 반송 가상장비 STK) |

### 경유 예시

```
M14A(3F) → M16        M14A → CNV(4AFC3201/4AFC3301) → M16 HUBROOM(3F) → M16
M10A(2F) → M16        M10A → LFT → M14A → M16 HUBROOM(3F) → M16
M14A → M16WT          M14A → CNV → M16 HUBROOM → LFT → M16EUV → WIS STK → M16WT
```

## 5. 유의 지표

### Sorter — SORTERWAITCOUNTOVER

Sorter 는 Wafer 를 공정 진행할 수 있게 변환하는 장치다.
**`SORTERWAITCOUNTOVER` 같은 지표가 급격히 증가하면 반송이 정체됐음을
유추할 수 있어** 엔지니어들이 유의 깊게 관찰한다.

- 대기Q 가 많다 = **그만큼 반송해야 할 양이 많다는 방증**
- 값 자체보다 **급격한 증가**를 본다

### MLUD — M16 HUBROOM `6FIOB~`

**M16 HUBROOM 에는 다수의 MLUD 가 있으며 `6FIOB` 로 시작한다.**
상황에 따라 두 방향으로 쓰인다.

- 사람이 M14A 의 FOUP 을 **M16 HUBROOM MLUD 에 투입**
- VHL 이 운송하여 **M16 HUBROOM MLUD 에서 나온 FOUP 을 M14A 로 직접 운반**

**따라서 MLUD 관련 지표들도 유의해야 할 지표다.**
MLUD 는 사람 손이 닿는 자리라, port 활성 여부를 같이 봐야 한다.

## 이 지식을 쓸 때

- **호기명은 원문 그대로 말한다.** `6ABL60~` 를 "6ABL 계열" 로 뭉개지 마라 —
  현장이 아는 이름이 그것이고, 뭉개면 검색도 안 된다.
- 층이 다르면 **LFT**, 같은 층 건물 간이면 **CNV** 가 기본이다.
- 경로 중 **한 구간이라도 막히면 그 뒤가 전부 밀린다.**
  어디서 막혔는지는 관제 수치로 좁힌다.
- 여기 없는 호기·구간은 **없다고 말한다.** 지어내지 마라.
- 이 문서에는 **지금 수치가 없다.** 현재 상태는 관제 근거를 본다.
