# AI Studio 사용법 (전체 통합 가이드)

본 문서는 SK하이닉스 HCP 기반 **AI Studio (AIU)** 의 전체 사용법을, 폴더 내 모든 텍스트(.txt) 가이드와 모든 첨부 이미지(.png) 80장의 화면 내용을 직접 확인하여 누락 없이 통합·정리한 매뉴얼입니다.

> 슬로건: **"Serve your MODEL on AI ocean"** — *From Modeling to Deployment, All in One Place*

---

## 목차

1. [AI Studio 소개](#1-ai-studio-소개)
2. [AI Studio 전체 아키텍처](#2-ai-studio-전체-아키텍처)
3. [AI Studio Main 화면](#3-ai-studio-main-화면)
4. [HCP 프로젝트 생성하기](#4-hcp-프로젝트-생성하기)
5. [HCP에서 프로젝트 멤버 추가하기](#5-hcp에서-프로젝트-멤버-추가하기)
6. [\[Home\] Overview & Info](#6-home-overview--info)
7. [AI Studio 좌측 메뉴 구조](#7-ai-studio-좌측-메뉴-구조)
8. [\[Modeling > Run\] Training을 Run(Job)으로 실행하기](#8-modeling--run--training을-runjob으로-실행하기)
9. [\[Modeling > Experiment\] 실험 결과 확인하기 (MLflow)](#9-modeling--experiment--실험-결과-확인하기-mlflow)
10. [\[Serving > Inference Service\] Single Inference 하기](#10-serving--inference-service--single-inference-하기)
11. [\[Serving > Inference Service\] Group(Ensemble) Inference 하기](#11-serving--inference-service--groupensemble-inference-하기)
12. [\[Serving > Inference Service\] Debugging 하기 (VS Code)](#12-serving--inference-service--debugging-하기-vs-code)
13. [\[Serving > Static Endpoint\] URL 고정하기 + Rollback](#13-serving--static-endpoint--url-고정하기--rollback)
14. [\[Monitoring > Resource\] 리소스 모니터링](#14-monitoring--resource--리소스-모니터링)
15. [\[Monitoring > Model\] 모델 모니터링 (Grafana)](#15-monitoring--model--모델-모니터링-grafana)
16. [Model Endpoint 모니터링 차트 해석](#16-model-endpoint-모니터링-차트-해석)
17. [Model Endpoint "잘" 모니터링하기 — 개발자 Tip](#17-model-endpoint-잘-모니터링하기--개발자-tip)
18. [Model Endpoint 모니터링 차트 FAQ](#18-model-endpoint-모니터링-차트-faq)
19. [각 서비스 접속 시 로그인 정보](#19-각-서비스-접속-시-로그인-정보)
20. [부록 — 참고 링크](#20-부록--참고-링크)

---

## 1. AI Studio 소개

**AI Studio**는 **AI/ML DevOps 시스템**입니다.
> 그러면.. AI/ML DevOps는 왜 필요할까요..?
> **한번 만들고 끝이 아닌, 지속적인 관리/배포 체계가 필요하기 때문**입니다.

### 1.1 AI 모델, 한번 만들면 끝일까?

**AI 모델의 숨겨 보이지 않는 과업이 있다.**
Model이 처음에 만든 모델은 성능이 좋지만 시간이 지남에 따라 데이터의 변화 등에 따라 Model의 "결과"의 정확도 또한 떨어지기 때문에 지속적으로 재학습/재배포 등을 모니터링·배포 등의 과업이 필요합니다.

| 신규 모델 생성 | 출시 후 성능 저하 요인 |
|---|---|
| 첫 배포 시 성능이 좋음 | 데이터 변화로 인한 열화 / 환경의 변경으로 인한 열화 / 요건 변경으로 인한 열화 |

![AI_Studio_란 1](<AI_Studio_란1.png>)

### 1.2 AI/ML DevOps를 요리에 비유한다면…

이해를 돕기 위하여 "분석 → 요리"에 비유하여 본다면, 데이터(재료) → 모델(레시피) → 머신(주방) → MLOps(주방장) → Pipeline(조리도구) → CI-CD(배달) → 모니터링/Logging(맛집평가) → Tracking(주문이력) 등으로 매핑됩니다.

![AI_Studio_란 2](<AI_Studio_란2.png>)

### 1.3 AS-IS vs To-Be (DevOps 시스템 도입 효과)

| 영역 | AS-IS (시스템 없이 개발) | To-Be (AI Studio 사용 후) |
|---|---|---|
| **Model Analysis** | • 모델 Training 시 결과를 기록하고 Logging 및 Tracking되는 툴이 없음<br>• 모델 성능 엑셀로 기록 및 관리<br>• 모델 비교 불가능 | • Parameter, Metric을 로깅하고 Model 저장<br>• 실험 로깅 및 모델 비교를 통하여 분석 과정 효율적으로 진행<br>• 재현성 확보 |
| **Testing and debugging** | • Training을 VM 혹은 Local에서 수행하다가, 리셋이 되는 경우, 원인을 알 수 없음<br>• 문제 발생 시 수동으로 모델을 조사하여 오류 근본 원인 파악에 많은 시간이 소요됨 | • Training 결과에 대하여 Log 통하여 확인 가능<br>• 자동화된 모니터링을 통하여 문제를 신속히 발견 및 해결 가능 |
| **Process Management** | • 여러 팀 간 협업이 비효율적이며 프로세스가 표준화 되지 않아 기술 부채가 증가 | • CI/CD 파이프라인을 통해 개발 및 운영 사이의 갭을 줄일 수 있음<br>• 프로세스 자동화로 효율성 증대 |
| **Serving Infrastructure** | • 프로젝트마다 별도로 개발<br>• 비전문가가 개발하는 경우 IT적 요소의 고려사항을 놓쳐 운영 Risk 증가<br>• 유지보수 어려움 | • 별도 Serving 영역 구축 필요 없음<br>• Container화 및 자동화 된 Serving Infra를 통하여 안정적으로 배포 가능<br>• Scale-out/in 에 대한 고려 |
| **Resource Management** | • 수동적 리소스 관리<br>• 개별 프로젝트 마다 리소스를 점유하여 활용 하여 자원 낭비 가능<br>• 혹은 추가 리소스가 필요할 때 마다 재구축 등의 리스크 발생 가능 | • K8S Container 기반의 자동 Provisioning을 통하여 다수의 Share 가능<br>• 리소스가 추가로 필요한 경우라도 재구축 없이 Scale-up 가능 |
| **Monitoring** | • 모델 성능 Tracking에 대한 모니터링 요소 별도 개발 필요 | • Infra적 요소부터 Application 요소까지 모두 고려된 Logging을 통하여 별도 작업 없이 Monitoring 화면을 제공받을 수 있음 |
| **Automation** | • 대부분의 작업을 수작업으로 진행 시 반복 작업 및 오류 발생 가능성 높음<br>• 자동화 개발을 진행하더라도, 모델러가 서버 환경에서 안정적으로 운영 가능한 요소를 모두 고려 한 개발이 쉽지 않음 | • 자동화 된 파이프라인을 통하여 Training시의 로깅, 배포 등 자동화 및 최적화를 통하여 모델러 입장에서 유지보수가 간소화 됨 |

![AI_Studio_란 3](<AI_Studio_란3.png>)

### 1.4 AI/ML DevOps를 위한 AI Studio

모델의 시스템화를 위하여, **AI Studio**를 통하여 표준화된 **AI/ML DevOps Tool**을 제공합니다.

```
        Training
           ↓
   Model Tracking & 모델등록
           ↓
   Serving & Inference
           ↓
   Monitoring & Feedback
           ↓
        (loop back to Training)
```

![AI_Studio_란 4](<AI_Studio_란4.png>)

---

## 2. AI Studio 전체 아키텍처

AI Studio는 HCP(Hybrid Cloud Platform) 위에서 동작하며, 모델 라이프사이클 전 과정을 자동화합니다.

```
┌─────────────────────────── AI Studio ───────────────────────────┐
│                                                                  │
│  Training Data       AI       Training   →  모델 배포  →  Inference│
│  Preparation/등록 → Model →               (Serving)               │
│       ↓             ↓        ↓                ↓          ↓        │
│  ───────────────────────────────────────────────────  Dashboard   │
│      모니터링 및 알람 ( Metric, Logging, Tracing )                    │
└──────────────────────────────────────────────────────────────────┘
                              │ HCP 연계
┌─────────────────────────── HCP ─────────────────────────────────┐
│                                                                  │
│   IDE       S3        Job        SRE       ...                   │
│   ─────────────────────────────────────────────                  │
│                       K8S                                        │
└──────────────────────────────────────────────────────────────────┘
```

- **AI Studio Layer** : Training Data Preparation/등록 → AI Model → Training → 모델 배포(Serving) → Inference, 그리고 전 단계의 **모니터링 및 알람(Metric, Logging, Tracing)** 과 **Dashboard** 제공.
- **HCP Layer** : `IDE`(Jupyter/VS Code), `S3`(Object Storage), `Job`(Run/Queue), `SRE`(Kibana 로그·Grafana 메트릭), `K8S`(쿠버네티스 자동 프로비저닝).

![Architecture](<Project_생성_하기1.png>)

---

## 3. AI Studio Main 화면

| 번호 | 메뉴 | 설명 |
|:---:|---|---|
| (1) | **ALL PROJECTS** | 전체 프로젝트 확인 및 검색 가능한 화면(즐겨찾기만 보기, 프로젝트명/생성자 검색)을 띄워 줍니다. |
| (2) | **CREATE PROJECT** | 프로젝트 생성 가능하도록, **HCP 프로젝트 생성 사이트**와 연결합니다. (안내 다이얼로그: "프로젝트 생성이 처음이신가요? … [프로젝트 생성 가이드]를 확인해 주세요.") |
| (3) | **My Project** | 내가 멤버로 속해 있는 프로젝트들을 카드 형태로 보여 줍니다. (이름, 설명, 생성자, 생성일, 사용 중인 서비스 아이콘) |
| (4) | **NOTICE** | AI Studio iflow의 공지사항과 연결되어 있습니다. |
| (5) | **GUIDE** | AI Studio iflow의 가이드와 연결되어 있습니다. |
| (6) | **VIDEO** | AI Studio HyTube 영상과 연결되어 있습니다. |

화면 좌측 상단에는 `PROJECT STATUS` 통계(Project 수, Experiment 수, Endpoint 수)가 표시됩니다.

![Main 화면 1](<[Main]Main_화면1.png>)
![Main 화면 - ALL PROJECTS 검색](<[Main]Main_화면2.png>)
![Main 화면 - 프로젝트 생성 안내 다이얼로그](<[Main]Main_화면3.png>)

---

## 4. HCP 프로젝트 생성하기

1. **AI Studio (AIU)** 는 HCP의 서비스로서, HCP의 서비스를 기반으로 AI/ML DevOps를 조금 더 쉽게 적용할 수 있도록 도움을 주는 시스템입니다.
2. AI Studio를 활용하기 위해서는 **HCP에서 프로젝트를 먼저 신청**해야 합니다.
3. <http://cloud.skhynix.com> 접속.
4. 좌측 메뉴 트리에서 **`Common` / `Project` / `DevOps`** 그룹 중 **`Project → 프로젝트`** 클릭.

   ![Project 메뉴](<Project_생성_하기2.png>)

5. 프로젝트 목록 화면 상단의 **"프로젝트 추가"** 클릭.

   ![프로젝트 추가 버튼](<Project_생성_하기3.png>)

6. **STEP1. 기본정보 입력** 단계 — 다음 항목들을 입력합니다.

   | 항목 | 설명 |
   |---|---|
   | **프로젝트** ★ | 프로젝트 이름 (예: `aiu-myfirst-test`) |
   | **프로젝트 타입** ★ | **반드시 `AI` 로 선택**해야 AI Studio 활용 가능 |
   | **프로젝트 미러 구분** ★ | 본사 등 |
   | **프로젝트 설명** ★ | (예: `myfirst test project`) |
   | **HyDesk** | 시스템그룹 / 시스템 선택 |
   | **ITSM 연계** | Y / N |
   | **관리자** ★ | 사번 검색 후 추가 |
   | **배포승인자** ★ | 사번 검색 후 추가 |
   | **개발자** ★ | 사번 검색 후 추가 |
   | **Inference Service 전용 NAS** | (선택) |
   | **Notification CUBE 채널** | (선택) |
   | **Alarm CUBE 채널** ★ | 알림 봇 채널 선택 |

   ![STEP1 기본정보 입력](<Project_생성_하기4.png>)

7. **STEP2. 검토+만들기** — 입력 정보 확인 후 **"만들기"** 클릭.

   ![STEP2 만들기](<Project_생성_하기5.png>)

8. **프로젝트 승인 후**에 AI Studio 활용 가능합니다.

---

## 5. HCP에서 프로젝트 멤버 추가하기

AI Studio에서 프로젝트를 활용하다가, 또 다른 멤버를 추가해야 할 일이 생길 수 있습니다.
이런 경우에는 **HCP Portal**에서 해당 프로젝트에 권한을 주면 됩니다.

1. **HCP에 접속**: <http://cloud.skhynix.com/>
2. 좌측 메뉴에서 **"Project > 프로젝트"** 클릭

   ![멤버 추가 1 — HCP 메뉴](<AI_Studio에멤버추가하기1.png>)

3. 프로젝트 검색창에 프로젝트명(예: `aiu-lcsa`) 입력 후 찾기

   ![멤버 추가 2 — 프로젝트 검색](<AI_Studio에멤버추가하기2.png>)

4. 해당 프로젝트를 더블클릭 → 좌측 메뉴 **"접근 권한"** 클릭하여 권한 추가 화면으로 진입

   - 좌측 메뉴 구성: `일반` (개요 / **접근 권한** / 태그) / `모니터링` (로그설정) / `Alert` (Alert 설정 / Alert History)
   - 권한은 **관리자 / 배포승인자 / 개발자** 3종으로 구분되어 표시됩니다.

   ![멤버 추가 3 — 접근 권한 화면](<AI_Studio에멤버추가하기3.png>)

5. 추가하고자 하는 멤버를 **조직도(SK하이닉스 부서 트리)** 에서 검색·선택 후 확인 버튼

   - 좌측 트리: SK하이닉스 → Data Intelligence → AI Transformation / 품질지능화 / 장비지능화 / **AI/Data Platform** / AI Solution → … / CAE / 산업보안 / AIX확산TF / 용인Cluster DT TF / CTO Culture Partner / 기반기술센터 / Memory Systems Research / 변화추진
   - 상단 탭: **구성원 / 가상그룹 / 나만의 그룹**, "ai studio" 같은 키워드로 검색 가능

   ![멤버 추가 4 — 조직도에서 멤버 선택](<AI_Studio에멤버추가하기4.png>)

6. **"저장"** 버튼 클릭으로 권한 추가 완료

   ![멤버 추가 5 — 저장 후 권한 목록](<AI_Studio에멤버추가하기5.png>)

이제 멤버 추가가 완료되었습니다!

---

## 6. \[Home\] Overview & Info

### 6.1 Overview

전체적으로 어떤 모델과 서비스가 있고, 어떤 Run 들이 있는지에 대하여 확인 가능합니다.

| 번호 | 항목 | 설명 |
|:---:|---|---|
| (1) | **Model** | 최근 등록된 모델과 최신 버전(Name, Version, Created at, Action(mlflow↗))을 보여 줍니다. |
| (2) | **Endpoint** | 최근 등록된 Endpoint(Name, Status[READY], Type[SINGLE/GROUP], Created at, Action(Log↗))를 보여 줍니다. |
| (3) | **Run Template** | 최근 등록된 Run Template(Name, Deploy Status, Created at, Action(Git↗))을 보여 줍니다. |
| (4) | **Run Instance** | 최근 실행된 Run(Name, Status[COMPLETED/FAILED], Started at, Ended at)을 보여 줍니다. |

좌측에는 `Jupyter`, `VS Code`, `MLflow` 바로가기 아이콘에 카운트 배지가 표시됩니다.

![Home Overview](<[Home]_Overview_Info1.png>)

### 6.2 Info

프로젝트 이름, 멤버 등의 정보를 조회할 수 있습니다.

표시 항목:
- **Description**, **System Code [HyDesk]**, **Cube** (알람 채널 번호 — 클릭 시 HCP의 Cube 페이지로 이동)
- **Members** : `Admin(N)` / `Deploy Approver(N)` / `Developer(N)` 그룹별 표시

![Home Info — Members & Cube](<[Home]_Overview_Info2.png>)

Cube 알람을 수정하거나, 프로젝트 멤버 등을 수정할 수 있도록 **"Cube" 링크**나 **"Edit" 버튼**을 누르면 **HCP의 수정 페이지**(개요 / 접근 권한 / 태그 / 모니터링 / Alert 등)로 이동합니다.

![Home Info — HCP 수정 페이지로 이동](<[Home]_Overview_Info3.png>)

---

## 7. AI Studio 좌측 메뉴 구조

모든 화면에서 좌측 사이드바는 다음과 같은 구조를 가집니다.

```
🏠  Home
─────────────────────
🪐 Jupyter (1)        ← 카운트 배지
🟦 VS Code (1)
🌀 MLflow  (1)
─────────────────────
📦 Modeling
   ├ Experiment ↗  (별도 탭으로 MLflow 오픈)
   └ Run
🔗 Serving
   ├ Inference Service
   └ Static Endpoint
📊 Monitoring
   ├ Model ↗  (별도 탭으로 Grafana 오픈)
   └ Resource
📋 Management
```

상단에는 `My Recent Projects` 탭(즐겨찾기 별표) + 우측에는 알림/메모/설정/프로필 아이콘이 표시됩니다.

---

## 8. \[Modeling > Run\] Training을 Run(Job)으로 실행하기

### 8.1 Run 화면 진입

`Modeling → Run` 메뉴 클릭. 한 번도 수행한 이력이 없다면 **"Latest Run Instances"** 화면은 나오지 않으며, 수행 이력이 있다면 상단에 최근 수행 이력이 카드 형태로 나타납니다.

![Run 화면 메뉴](<[Modeling_Run]Training을_Run(Job)으로_실행하기1.png>)
![Latest Run Instances 카드 + Run Template 표](<[Modeling_Run]Training을_Run(Job)으로_실행하기2.png>)

### 8.2 RUN Template 생성하기

화면 우측 하단 Run Template 표의 **"CREATE"** 버튼 클릭.

![CREATE 버튼](<[Modeling_Run]Training을_Run(Job)으로_실행하기3.png>)

### 8.3 기본 정보 입력 (Run Template 생성 폼)

`Modeling → Run → Run Template 생성` 화면에서 다음 항목들을 입력합니다.
우측 상단 **`COPY TEMPLATE`** 버튼으로 기존 템플릿을 복제할 수도 있습니다.

| 번호 | 항목 | 설명 / 예시 |
|:---:|---|---|
| (1) | **Name** ★ | Run Template 이름 (예: `runtest`) |
| (2) | **Python Version** ★ | 생성하고자 하는 파이썬 버전 (예: `3.11`) |
| (3) | **Resource** ★ | 생성하고자 하는 리소스 크기 (예: `CPU: 2, Memory: 1GiB, GPU: 0`) |
| (4) | **Repository** ★ | **`http://`** 형태의 git 주소 (ssh 불가) — 예: `http://bitbucket.skhynix.com/scm/hcp-aiu-guide-pjt/job-test.git` |
| (5) | **Branch** ★ | 실행하고자 하는 Branch 이름 (예: `master`) |
| (6) | **File** ★ | Bitbucket을 선택 후 나타나는 **파일 트리**(`.ipynb_checkpoints`, `__pycache__`, `aiu_custom`, `config`, `input_example.json`, `requirements.txt`, `runtest.py`, `saved_model` 등)에서 Run(Job)을 실행할 **메인 파일** 선택 (예: `runtest.py`) |
| (7) | **Requirements** ★ | RUN 실행 시 설치할 패키지를 한 줄에 하나씩 입력. 예:<br>`pandas==2.3.0`<br>`requests==2.32.4`<br>`scikit-learn==1.7.0` |
|  | Arguments | (선택) 실행 시 인자 |
|  | Command | (선택) 커스텀 커맨드 |
|  | Description | (선택) 설명 |

모든 정보가 입력되었으면 **"CREATE"** 버튼을 누릅니다.

![Run Template 폼 — File 트리 선택](<[Modeling_Run]Training을_Run(Job)으로_실행하기4.png>)
![Run Template 폼 — Requirements 입력](<[Modeling_Run]Training을_Run(Job)으로_실행하기5.png>)

### 8.4 RUN 환경 생성

RUN 수행을 위한 환경 생성을 시작합니다. 생성된 Run Template은 `IN PROGRESS` 상태가 되며, 해당 행을 **Double Click** 시 상세 Status인 **`Run Template Deploy TimeLine`** 다이얼로그가 열립니다 (`Docker Image Build & Push` 등 단계 진행 상황 표시).

![생성 직후 IN PROGRESS](<[Modeling_Run]Training을_Run(Job)으로_실행하기6.png>)
![Deploy TimeLine 다이얼로그 (Double Click)](<[Modeling_Run]Training을_Run(Job)으로_실행하기7.png>)

### 8.5 RUN 실행

Deploy Status가 `SUCCESS`가 되면, Action 컬럼의 **▶ 실행 버튼**을 눌러 실행합니다.

![SUCCESS 후 실행 버튼](<[Modeling_Run]Training을_Run(Job)으로_실행하기8.png>)

### 8.6 Queue 선택

`Queue List` 다이얼로그가 뜹니다.
가용 Queue 중 선택 (예: `cpu-common-queue`, Guarantee `CPU: 64, Memory: 1000Gi`, Wait Count 표시) 후 **EXECUTE**.
> 추후 **GPU** 도 Queue에 추가될 예정입니다.

![Queue List 다이얼로그](<[Modeling_Run]Training을_Run(Job)으로_실행하기9.png>)

### 8.7 실행 상태 확인

`Latest Run Instances` 영역에 카드 형태로 표시됩니다.

| 상태 | 색상 / 표시 |
|---|---|
| **WAITING** | 노란색 — 실행 대기 중 |
| **COMPLETED** | 녹색 — 완료 (Duration 녹색 배지) |
| **FAILED** | 빨간색 — 실패 (Duration 빨간 배지) |

각 카드에는 `Instance ID`, `Arguments`, `Queue`, `Duration` (예: `00:00:13`), 작성자/날짜가 표시됩니다.

![3가지 상태 카드 — WAITING / COMPLETED / FAILED](<[Modeling_Run]Training을_Run(Job)으로_실행하기10.png>)

### 8.8 전체 Run Instances 확인

최근 Run이 많은 경우, 우측 상단 **+ 버튼**을 누르면 `Run Instances` 페이지로 이동하여 전체 이력을 확인할 수 있습니다.

![+ 버튼 위치](<[Modeling_Run]Training을_Run(Job)으로_실행하기11.png>)

`Run Instances` 페이지 컬럼: `Run Template, Instance ID, Status, Arguments, Started at, Ended at, Duration, Executed by, Action(Log↗ / Metric↗)`

![Run Instances 페이지](<[Modeling_Run]Training을_Run(Job)으로_실행하기12.png>)

---

## 9. \[Modeling > Experiment\] 실험 결과 확인하기 (MLflow)

좌측 메뉴 **`Experiment ↗`** 클릭 시 **MLflow** 화면이 별도 탭으로 열립니다.

![Experiment 메뉴 클릭](<[Modeling_Experiment]_실험결과_확인하기1.png>)

MLflow에서는 다음과 같이 실험 결과를 확인합니다.
- 좌측 `Experiments` 패널에서 실험 선택 (예: `Default`, `sklearn_test`, `sklearn_job_test`, `ensemble-test`)
- 검색: `metrics.rmse < 1 and params.model = "tree"` 등 표현식 지원
- 필터: `Time created`, `State: Active`, `Datasets`, `Sort: Created`, `Columns`, `Group by`
- 탭: `Table / Chart / Evaluation / Experimental`
- 각 Run에 대해 `Run Name`(예: `auspicious-asp-15`), `Created`, `Dataset`, `Duration`, `Source`, `Models` 표시

![MLflow Experiments 화면](<[Modeling_Experiment]_실험결과_확인하기2.png>)

---

## 10. \[Serving > Inference Service\] Single Inference 하기

`Serving → Inference Service` 메뉴 진입 → 상단 **`Single`** 탭. 표 컬럼: `Name, Tag, Deploy Status, Status, Created by, Created at, Debug(OFF/ON), Action(Log↗ / Metric↗)`.

![Inference Service 메뉴](<[Serving_Inference Service]_Single_Inference하기1.png>)

### 10.1 Create

우측 상단 **"CREATE"** 버튼 클릭.

![CREATE 버튼](<[Serving_Inference Service]_Single_Inference하기2.png>)

### 10.2 Endpoint 생성 폼 — Model 선택

`Endpoint 생성` 폼이 열립니다 (상단의 **`Advanced`** 토글로 고급 옵션 노출).

| 항목 | 설명 |
|---|---|
| **Name** | 모델 선택 후 자동 생성됨 (예: `skl-model-test-v4-sequenceNo` → 실제 `skl-model-test-v4-s1`) |
| **Model** ★ | **`SELECT`** 버튼 클릭하여 모델/버전 선택 |
| **Created by / Created at** | 자동 |
| **Tag(0)** | Key:Value 입력 후 Enter |
| **Python Version** | 모델 메타에서 자동 (예: `3.11.9`) |
| **Image Path** | (선택) Docker Image Path |
| **Requirements** ★ | 자동 채워짐. 기본:<br>`kserve==0.15.0`<br>`mlflow==2.22.0`<br>`joblib==1.5.1`<br>`numpy==1.26.4`<br>`pandas==2.3.0`<br>`requests==2.32.4`<br>`scikit-learn==1.7.0` |

![Endpoint 생성 폼](<[Serving_Inference Service]_Single_Inference하기3.png>)

`SELECT` 클릭 시 `Select Model` 다이얼로그 (컬럼: `Model, Version (Time), Experiment, Action(mlflow↗)`)에서 원하는 Model · Version 선택 후 **APPLY**.

![Select Model 다이얼로그](<[Serving_Inference Service]_Single_Inference하기4.png>)

### 10.3 Requirements 확인 후 CREATE

Serving 환경에 필요한 패키지들의 **requirements**를 잘 확인합니다.
> requirements가 dependency에 의해 에러가 발생할 수 있으니 확인합니다.

확인 후 **"CREATE"** 버튼 Click 하여 서빙을 시작합니다.

![Requirements 입력 완료 → CREATE](<[Serving_Inference Service]_Single_Inference하기5.png>)

### 10.4 Status 확인

Serving 진행 중, Inference 환경을 만드는 **`Deploy Status`** 와, 필요한 코드를 다운로드하고 구동시키는 **`Status`** 를 확인합니다 (`IN PROGRESS` → `SUCCESS`, `PENDING` → `READY`).

![생성 진행 중 — IN PROGRESS / PENDING](<[Serving_Inference Service]_Single_Inference하기6.png>)

### 10.5 생성된 서비스 진입

`SUCCESS` / `READY` 가 되면 해당 행을 **Double Click** 합니다.

![SUCCESS / READY 상태](<[Serving_Inference Service]_Single_Inference하기7.png>)

### 10.6 상세 페이지 — URL / Log / Metric / Request Code

상세 페이지에서 다음을 확인할 수 있습니다.

- **URL** (예: `http://skl-model-test-v4-s1.aiu-guide-pjt.aisp01.skhynix.com:8080/v1/models/skl-model-test-v4-s1:predict`) — 복사하여 Request 가능
- **Log** : Kibana 기반 로그 화면
- **Metric** : Grafana 기반 리소스 현황
- **Trace** (`전체보기`), **Tag(0)**, **Python Version**, **Requirements**
- **Request Code** : 그대로 Copy 하여 수행하면 **Inference Test** 가능

![상세 페이지 — URL/Log/Metric/Request Code](<[Serving_Inference Service]_Single_Inference하기8.png>)

### 10.7 Inference Test 결과

복사한 코드를 Jupyter에 붙여서 실행하면 정상적으로 결과가 나옵니다.

```python
import requests
import json

req_url = "http://skl-model-test-v4-s1.aiu-guide-pjt.aisp01.skhynix.com:8080/v1/models/skl-model-test-v4-s1:predict"

data = {
    "input": [
        {
            "name": "sklearn_example",
            "shape": [10, 4],
            "datatype": "ndarray",
            "data": [[6.1, 2.8, 4.7, 1.2], [5.7, 3.8, 1.7, 0.3],
                     [7.7, 2.6, 6.9, 2.3], [6.0, 2.9, 4.5, 1.5],
                     [6.8, 2.8, 4.8, 1.4], [5.4, 3.4, 1.5, 0.4],
                     [5.6, 2.9, 3.6, 1.3], [6.9, 3.1, 5.1, 2.3],
                     [6.2, 2.2, 4.5, 1.5], [5.8, 2.7, 3.9, 1.2]]
        }
    ]
}

req_msg = json.dumps(data)
headers = {'Content-Type': 'application/json'}
resp = requests.post(req_url, headers=headers, data=req_msg)
print(resp.content)
```

응답에는 `pis_name`, `trace_id`, `output.aiu_output`, `output.aiu_monitoring` 가 포함됩니다.

```
b'{"pis_name":"skl-model-test-v4-s1","trace_id":"pis_skl-model-test-v4-s1_f7f7559a985411f0bcd3915eb45d6564",
   "output":{"aiu_output":[1.31, 0.32, 2.04, 1.24, ...],
             "aiu_monitoring":[1, 0, 2, 1, 1, 0, 1, 1, 1, 1]}}'
```

![Inference Test 코드 실행 결과](<[Serving_Inference Service]_Single_Inference하기9.png>)

---

## 11. \[Serving > Inference Service\] Group(Ensemble) Inference 하기

`Serving → Inference Service` 메뉴의 **`Group`** 탭에서 관리합니다. 표 컬럼: `Name, Tag, Deploy Status, Status, Created by, Created at, Action(Log↗ / Metric↗)`.

![Group 탭 진입](<[Serving_Inference Service]_Group_Inference하기1.png>)

### 11.1 CREATE

**"CREATE"** 버튼을 눌러 Ensemble Inference 생성을 시작합니다.
> (2025. 09. 23. 현재 **Ensemble** 만 지원중. 추후 **Sequence** 등 지원 예정)

![Group Inference CREATE](<[Serving_Inference Service]_Group_Inference하기2.png>)

### 11.2 Endpoint 생성 — SELECT

`Endpoint 생성` 폼에서 Name은 선택 모델 기반 자동 생성. 우측 상단 **`SELECT`** 또는 가운데 **`SELECT`** 버튼 클릭.

![Endpoint 생성 폼 — SELECT](<[Serving_Inference Service]_Group_Inference하기3.png>)

### 11.3 Single Inference Service 선택 → APPLY

`Select Model` 다이얼로그가 좌(선택됨) / 우(선택가능) 두 패널로 열립니다. 상단에 **`READY만 보기`** 체크박스, **이름 검색** 가능. Ensemble이 필요한 Single Inference Service들을 좌측으로 옮긴 뒤 **`APPLY`**.

![Select Model — 좌/우 패널](<[Serving_Inference Service]_Group_Inference하기4.png>)

### 11.4 CREATE

선택된 모델 목록(예: `randomforest-v2-s1`, `decisiontree-v2-s1`, `logisticregression-v2-s1` 모두 `READY`)이 표시됨. **Tag(0)** 추가 가능. **"CREATE"** 클릭.

![선택된 모델 확인 → CREATE](<[Serving_Inference Service]_Group_Inference하기5.png>)

### 11.5 Status 확인

생성된 Group Inference는 처음 `IN PROGRESS / PENDING` 상태로 시작하며, **`Deploy Status` = `SUCCESS`** 와 **`Status` = `READY`** 가 되면 활용 가능합니다. 환경 구성에는 **사내 네트워크 상태에 따라 5분~15분 정도** 소요됩니다.

![IN PROGRESS / PENDING 상태](<[Serving_Inference Service]_Group_Inference하기6.png>)

### 11.6 Double Click → 상세 정보

`SUCCESS / READY` 행을 **Double Click** 하여 상세 정보를 확인합니다.

![SUCCESS / READY 행](<[Serving_Inference Service]_Group_Inference하기7.png>)

### 11.7 상세 페이지

상세 페이지에서 다음을 확인할 수 있습니다.

- **기본정보** : Name(g3), Deploy Status, Status, Created by, Created at
- **Trace** : `전체보기` (그래프 형태로 Experiment·Model·Endpoint 흐름 시각화)
- **URL** (예: `http://g3.aiu-guide-pjt.aisp01.skhynix.com:8080`)
- **Log** ↗ , **Metric** ↗
- **Tag(0)**
- **Model** : 묶인 Single Inference 목록과 각각의 Status
- **YAML** : KServe `InferenceGraph` 정의 — 예시:
  ```yaml
  apiVersion: serving.kserve.io/v1alpha1
  kind: InferenceGraph
  metadata:
    name: g3
    namespace: aiu-guide-pjt
  spec:
    nodes:
      root:
        routerType: Sequence
        steps:
          - name: root
            serviceUrl: http://g3-trace-id-maker.aiu-guide-pjt.aisp01.skhynix.com:8080/
          - name: step1
            nodeName: step1
            data: ...
      step1:
        routerType: Ensemble
        ...
  ```

![상세 페이지 — URL / Trace / Log / YAML](<[Serving_Inference Service]_Group_Inference하기8.png>)

### 11.8 Trace 상세 보기

`전체보기`(상세보기) 클릭 시, **g3 - Trace** 그래프 다이얼로그가 열려 어떤 Inference 서비스들이 Group으로 Ensemble 되어 있는지(Experiment → Model → Endpoint 노드 다이어그램으로) 확인 가능합니다.

![Trace 그래프 보기](<[Serving_Inference Service]_Group_Inference하기9.png>)

### 11.9 URL Copy → Inference Test

URL을 Copy하여 위와 동일한 형태의 코드(`# Ensemble Model`)로 호출하면, 응답에는 ensemble된 각 모델의 결과가 인덱스 `"0"`, `"1"`, `"2"` 별로 출력됩니다.

```
b'{"0":{"output":{"aiu_monitoring":[...], "aiu_output":[...]},
       "pis_name":"randomforest-v2-s1",
       "trace_id":"pis_randomforest-v2-s1_..." },
   "1":{"output":{...}, "pis_name":"decisiontree-v2-s1", "trace_id":"..."},
   "2":{"output":{...}, "pis_name":"logisticregression-v2-s1", "trace_id":"..."}}'
```

![Group Inference Test 결과](<[Serving_Inference Service]_Group_Inference하기10.png>)

---

## 12. \[Serving > Inference Service\] Debugging 하기 (VS Code)

인퍼런스 서비스를 하다 보면 **Debugging이 필요한 순간**이 있습니다. 이때, 운영 중인 인퍼런스 서비스를 직접 디버깅하는 것은 **운영상의 이슈**가 발생할 수 있습니다. AI Studio는 동일한 인퍼런스 서비스를 **VSCode와 함께 생성**할 수 있는 기능을 제공하여, **VSCode에서 중단점을 걸고 Debugging이 가능**하도록 합니다.

### 12.1 OFF → CREATE

`Inference Service > Single` 표의 `Debug` 컬럼에 있는 **"OFF"** 버튼을 클릭 → `Endpoint Debug 생성` 다이얼로그(💡 안내: "선택한 Endpoint를 기반으로 디버깅 환경이 설정됩니다.") 표시 → Name 자동(`{service}-debug`) 확인 후 **"CREATE"**.

![OFF 클릭](<[Serving_Inference Service]_Debugging하기1.png>)
![Endpoint Debug 생성 다이얼로그](<[Serving_Inference Service]_Debugging하기2.png>)

### 12.2 OFF → ON 변환 확인

표시가 **"OFF" → "ON"** 으로 변경됩니다.

![OFF → ON](<[Serving_Inference Service]_Debugging하기3.png>)

### 12.3 ON 클릭 → Endpoint Debug 상세

**"ON"** 버튼 클릭 → `Endpoint Debug 상세` 다이얼로그.
- **Name** : `{service}-debug`
- **Deploy Status** : IN PROGRESS → SUCCESS
- **Status** : PENDING → READY
- **Created by / Created at**, **Log**, **Metric**, **URL**
- **Access** : **`VS Code ↗`** 버튼

![Endpoint Debug 상세 — IN PROGRESS](<[Serving_Inference Service]_Debugging하기4.png>)

### 12.4 SUCCESS / READY → 디버깅 가능

`SUCCESS` / `READY` 가 되면 디버깅 가능. URL 복사하여 inference 가능하며, **`VS Code ↗`** 클릭 시 VS Code (web) 환경이 새 탭으로 열립니다.

![SUCCESS / READY 상태 + URL + VS Code 버튼](<[Serving_Inference Service]_Debugging하기5.png>)

### 12.5 VS Code 접속 → Predict 함수 수정

기본 비밀번호 **`aistudio123!`** 으로 VS Code에 접속.
좌측 트리에서 `model.py` (또는 `custom_aiu_v1` 프로젝트) 열어 **`predict` 함수** 수정 → 코드 변경하면서 Inference 테스트 및 **중단점(breakpoint) 디버깅** 가능.

![VS Code — model.py / predict 함수 편집](<[Serving_Inference Service]_Debugging하기6.png>)

---

## 13. \[Serving > Static Endpoint\] URL 고정하기 + Rollback

`Serving → Static Endpoint` 메뉴. 모델을 교체해도 동일한 외부 URL을 유지하기 위한 기능. 표 컬럼: `Name, Description, Status, Link Type(SINGLE/GROUP), Link Endpoint, Created by, Created at, Action(복사/삭제/수정)`.

![Static Endpoint 목록](<[Serving_Static_Endpoint]_URL고정하기1.png>)

### 13.1 CREATE

**"CREATE"** 버튼 클릭.

![CREATE 버튼](<[Serving_Static_Endpoint]_URL고정하기2.png>)

### 13.2 Static Endpoint 기본설정

다이얼로그 입력:

| 항목 | 설명 |
|---|---|
| **Name** ★ | 예: `static-service` |
| **URL** | 자동 생성 미리보기 (예: `http://static-service.aiu-guide-pjt.aisp01.skhynix.com:8080`) |
| **Description** | 예: `static endpoint 서비스 입니다.` |

**"CREATE"** 클릭 → "기본설정이 완료되었습니다. 이어서 상세정보를 입력해주세요." 토스트.

![기본설정 다이얼로그](<[Serving_Static_Endpoint]_URL고정하기3.png>)

### 13.3 Edit — Link Type & Link Endpoint

`Edit` 화면에서 다음을 입력합니다.
- **Link Type** ★ : `Single` / `Group` 라디오
- **Link Endpoint** ★ : 드롭다운에서 연결할 Inference Service 선택 (목록에는 `skl-model-test-v4-s1`, `randomforest-v2-s1`, `decisiontree-v2-s1`, `logisticregression-v2-s1`, `skl-model-test-v2-s1` 등이 표시됨)
- **Description** (선택)

**"APPLY"** 클릭하여 저장.

![Edit — Single 선택 후 Link Endpoint 드롭다운](<[Serving_Static_Endpoint]_URL고정하기4.png>)
![Link Endpoint 드롭다운 펼침](<[Serving_Static_Endpoint]_URL고정하기5.png>)

### 13.4 상세 페이지 + EDIT

저장 후 상세 페이지에서 `기본정보` 확인 (Name, URL, Created by/at, Modified by/at, Link Type, Link Endpoint, Description). **"DELETE"** / **"EDIT"** 버튼으로 모델 교체 가능.

![상세 페이지 — EDIT 버튼](<[Serving_Static_Endpoint]_URL고정하기6.png>)

### 13.5 Group 으로 교체 (Model 교체)

`EDIT` → Link Type을 **`Group`** 으로 변경 → Link Endpoint 드롭다운에서 `g3` (또는 `g2`) 등 Group 모델 선택 → **"APPLY"**.

![Edit — Group 으로 교체](<[Serving_Static_Endpoint]_URL고정하기7.png>)

### 13.6 Inference Test (교체된 모델 결과)

이전과 **동일한 Static URL** (`http://static-service.aiu-guide-pjt.aisp01.skhynix.com:8080`) 으로 호출 시, 이번엔 **Group/Ensemble 결과**가 나옵니다.

```python
# static-endpoint
req_url = "http://static-service.aiu-guide-pjt.aisp01.skhynix.com:8080"
# ...동일한 data, post...
```

응답에는 `pif_name=static-service`, 인덱스 `"0"`, `"1"`, `"2"` 별 ensemble 결과가 포함됩니다.

![Inference Test — Group 결과](<[Serving_Static_Endpoint]_URL고정하기8.png>)

### 13.7 History — 변경 이력

상세 페이지 하단에 **`History`** 패널이 있어, 변경 이력(Link Type, Link Endpoint, Modified by, Modified at, Action)을 확인할 수 있습니다.

![History 패널](<[Serving_Static_Endpoint]_URL고정하기9.png>)

### 13.8 Rollback

History의 Action 컬럼에 마우스 hover 시 **`Rollback`** 툴팁이 보이는 아이콘 클릭으로 이전 상태로 되돌릴 수 있습니다.

![Rollback 버튼](<[Serving_Static_Endpoint]_URL고정하기10.png>)

### 13.9 Rollback 결과 확인

Rollback 수행 시 "이전 상태로 되돌렸습니다." 토스트가 표시되고, 기본정보의 Link Type / Link Endpoint가 이전 값으로 복원됩니다. History에는 Rollback 자체도 새 행으로 추가됩니다.

![Rollback 후 상태](<[Serving_Static_Endpoint]_URL고정하기11.png>)

### 13.10 동일 URL 재호출 — Single 모델 결과 복구 확인

동일한 Static URL을 동일한 Inference Code로 호출하면 이번엔 **Single Endpoint 모델의 결과** 가 다시 나오는 것을 확인할 수 있습니다 (`pif_name=static-service`, `pis_name=decisiontree-v2-s1` 등).

![Rollback 후 Single 결과](<[Serving_Static_Endpoint]_URL고정하기12.png>)

---

## 14. \[Monitoring > Resource\] 리소스 모니터링

`Monitoring → Resource` 메뉴. 현재는 **jupyterlab, vscode, mlflow, object storage** 리소스에 대해서만 표현이 되어 있으나, 추후에는 **Inference 서비스까지 통합적으로** 볼 수 있도록 합니다.

### 14.1 서비스 현황

대부분의 사용자는 이 상태만 확인해도 됩니다. 표 컬럼:

| 서비스 | Pod 개수 | CPU 할당 | CPU 사용량 | CPU 사용률 | MEM 할당 | MEM 사용량 | MEM 사용률 | NETWORK IN | NETWORK OUT |
|---|---|---|---|---|---|---|---|---|---|
| `aiu-guide-pjt-jupyterlab` | 1 | 2.0 | 0.01 | **0.4%** | 8.0 GiB | 980.3 MiB | **12.0%** | 678.3 B/s | 387.1 B/s |
| `aiu-guide-pjt-vscode` | 1 | 2.0 | 0.02 | **0.8%** | 8.0 GiB | 322.9 MiB | **3.9%** | 35.1 B/s | 119.4 B/s |

### 14.2 Pod 현황

서비스에서 조금 더 나아가 K8S의 Pod이 어떤 Host에 어떤 Pod 이름으로 떠 있는지 보여 줍니다. 컬럼: `namespace, Host Node, POD, POD Status, CPU 사용량, MEM 사용량, NETWORK IN, NETWORK OUT`. 예:
- `aiu-guide-pjt` / `icp4gpu003` / `aiu-guide-pjt-mlflow-001-54f47fbc9b-vdvhg` / Running / 0.00 / 829.7 MiB / 0 B/s / 0 B/s

### 14.3 Object Storage

mlflow의 저장소로 활용 중인 Object Storage의 사용량을 보여 줍니다.
- **Bucket 사용량** (예: `0.00 GB`)
- **Bucket Quota** (예: `1 GB`)
- **MPU 사용량** (예: `0 GB`)

![Monitoring Resource — 전체 화면](<[Monitoring_Resource]리소스모니터링_하기1.png>)

---

## 15. \[Monitoring > Model\] 모델 모니터링 (Grafana)

**모델의 Inference**를 모니터링 하기 위한 메뉴.

1. 메뉴 진입 시 모델 모니터링 대시보드가 노출됩니다.
2. **"Click"** 시 **Grafana 화면**으로 이동합니다.
3. 잘 활용하기 위해서는 아래 iflow를 참고하세요.
   - **Model Endpoint 모니터링하기** : <http://iflow.skhynix.com/group/article/4752604>
   - **Model Endpoint "잘" 모니터링하기** : <http://iflow.skhynix.com/group/article/4774037>

![Monitoring Model 메뉴](<[Monitoring_Model]_모델모니터링_하기1.png>)

### 15.1 Grafana 대시보드 화면

- **상단 통계 카드** : `Success / Fail`, `Today 호출 건수`, `Last 모델 연산 시간(sec)`, `Last 모니터링 Parameter (aiu_monitoring)` (각 카드는 표/Mean/Max 컬럼으로 분리)
- **카드 색상 의미**
  - 🟦 **파란색 카드** = 자동 집계
  - 🟩 **녹색 카드** = 모델 개발자가 값을 직접 만들어야 표시됨
- **상단 컨트롤** : `Last 14 days` 기간 선택, 새로고침
- **Total Endpoint 호출 현황 (성공)** : Total 호출 건수(일단위) 라인 차트
- **Total 호출 소요시간 (성공)** : 라인 차트

![Grafana 대시보드 상단](<[Monitoring_Model]_모델모니터링_하기2.png>)

---

## 16. Model Endpoint 모니터링 차트 해석

모델 Endpoint를 호출했을 때, **집계되는 모니터링 항목** 해석.

1. **화면 메뉴 위치** : `AI Studio Portal > My Project 카드 클릭 > Monitoring > Model`
2. 차트에서 공통으로 **Bar는 일 단위**, **Line은 트렌드**, **Point는 개별 값 분포**를 의미합니다.
3. 주요 지표 중 **파란색 카드**는 **자동 집계**, **녹색 카드**는 **모델 개발자가 값을 직접 만들어야** 표시됩니다.
4. **기본 2주 단위**로 제공되며, 우측 상단의 기간 버튼을 통해 변경 가능합니다. 조회 가능 기간은 **오늘부터 최대 2주**입니다.
5. 좌측 상단의 **MODEL 체크박스**를 펼쳐서 특정 모델만 필터링할 수 있습니다.
6. **TRACE ID** 를 입력하여 대시보드 최하단 패널에서 상세 **Raw Data** 확인 가능합니다.
7. **"호출 건수"** 는 모델 연산 단계로 넘어간 호출 건만 포함합니다. 연산 전 단계에서 오류가 발생한 경우 집계되지 않습니다.
8. **평균 산출 시**, **"호출 건수"** 는 호출 건수가 0인 일자도 분모에 포함, **연산 시간**과 **모니터링 Parameter 값**은 존재하는 Data 건수만 분모에 포함해서 계산했습니다.

### 16.1 대시보드 지표 카드 구성도

상단에는 4개의 큰 카드가 다음 세부 카드들로 구성됩니다.

| 큰 카드 | 세부 카드 |
|---|---|
| 🟦 **오늘까지 프로젝트 누적 호출 지표** | 오늘까지 누적 호출 건수, 오늘까지 누적 호출 실패 건수 |
| 🟦 **Today 호출 건수** | 오늘 성공·프로젝트 누적 호출 건수, 일 단위 평균 호출 건수, 일 단위 누적 호출 실패 건수 |
| 🟦 **Last 모델 연산 시간 (sec)** | 평균 연산 시간, 가장 최근 연산 시간, 모델 연산시간 평균/Min/Max |
| 🟩 **Last 모니터링 Parameter (aiu_monitoring)** | 평균 모니터링 Parameter, 가장 최근 모니터링 Parameter, aiu_monitoring 평균/Min/Max |

![상단 카드 지표 안내](<Model_Endpoint_모니터링하기내용1.png>)

### 16.2 Endpoint 호출 성공 현황 (Only 성공)

성공 호출에 대한 3가지 차트:
1. **Total 호출 건수 (일단위)** — 일 단위 합계의 트렌드 확인 (min/max/avg/current/total 표시)
2. **모델별 호출 건수 (일단위)** — 일 단위 합계를 모델 별 나누어 확인
3. **모델별 호출 건수 비율 (일단위)** — 일 단위 합계를 100%로, 모델 별 나누어 확인

![호출 성공 현황 — 3개 차트](<Model_Endpoint_모니터링하기내용2.png>)

### 16.3 모델 연산 및 모니터링 Parameter 현황 (Bar)

1. **Total 연산시간 (sec) & 모니터링 Parameter (값)** — 호출 1건당 연산 소요시간과 모니터링 값의 트렌드를 동시에 비교
2. **모델별 연산시간 (sec) & 모니터링 Parameter (값)** — 모델 별 나누어 동시 비교

![연산시간 & Parameter — Bar 차트](<Model_Endpoint_모니터링하기내용3.png>)

### 16.4 모델 연산 및 모니터링 Parameter 현황 (Scatter / Point)

1. **모델별 연산 시간 (sec)** — 호출 1건당 연산 소요시간의 분포
2. **모델별 모니터링 Parameter (값)** — 호출 1건당 모니터링 값의 분포

![연산시간 & Parameter — Scatter 차트](<Model_Endpoint_모니터링하기내용4.png>)

### 16.5 Raw Data — TRACE ID 검색

`TRACE ID` 입력창에 Endpoint 호출 시 자동으로 Return 되는 trace_id 값을 검색해서 조회할 수도 있습니다. 오류 발생했을 때 원인 확인 용도로 유용합니다.
- **Success Log** 컬럼: `timestamp, trace_id, project, model(pis_name), latency, mon_param(aiu_monitoring)`
- **Fail Log** 컬럼: 동일

![Raw Data — TRACE ID 검색](<Model_Endpoint_모니터링하기내용5.png>)

---

## 17. Model Endpoint "잘" 모니터링하기 — 개발자 Tip

모델 Endpoint를 호출했을 때, **수동으로 집계되는 모니터링 항목**(녹색 카드)을 잘 만드는 Tip.

1. **화면 메뉴 위치** : `AI Studio Portal > My Project 카드 클릭 > Monitoring > Model > 녹색 카드`
2. **Predict 함수의 return** 으로 **`aiu_monitoring`** 이름으로 지정된 값만 수집됩니다.

   ```python
   🔨 return {"aiu_output": [1, 2, 3], "aiu_monitoring": 1}
   ```

3. `aiu_monitoring` 값에는 **Number**, **숫자형 String**, **Single List(개별 Item은 숫자)** 타입만 허용됩니다.
   이 외 경우는 **출력되지 않거나, 평균으로 치환**되어 차트에 표시될 수 있습니다.
4. 차트에서 **Point 한 건**은 모델 Endpoint를 호출했을 때의 `aiu_monitoring` 개별 값입니다.
   - (예) `aiu_monitoring` 값이 `1` 이면 차트에는 Point **1건**
   - (예) `aiu_monitoring` 값이 `[1, 2, 3]` 이면 차트에는 `1, 2, 3` **세 건의 Point** 가 표시됩니다.

---

## 18. Model Endpoint 모니터링 차트 FAQ

### Q1. "no data" 라고만 떠요.
→ **Predict 함수의 Return값에 `aiu_monitoring` 이름이 들어있는지** 확인하세요.

### Q2. 언제 기간으로 조회되는 거예요?
→ 모니터링 화면을 조회한 **현재 시간 기준으로, 2주 전 데이터부터** 집계합니다.

### Q3. 오래된 데이터도 볼 수 있나요?
→ Log 보관 정책 용량 제한 때문에 **최근 2주만 확인 가능**합니다.
조회 기간이 임의로 **10~14일까지만 선택 가능한 이유**도 이 때문입니다.

### Q4. "모델 연산시간"은 무엇을 의미하나요?
→ **AI Studio Serving Pod 안에서 Model이 연산을 시작해서 종료하기까지의 시간**을 의미하므로, **Endpoint 호출 시작~종료 시간과 다릅니다**.

### Q5. 방금 Endpoint를 호출했는데, 대시보드에 나오지 않습니다. Error가 나긴 했는데, 왜 안 나오죠?
→ **Q4 와도 관련된 답변**입니다. **모델 연산이 시작되어야** 대시보드의 데이터도 수집됩니다. **인풋 데이터 이상**처럼, **모델 연산이 시작되기 전에 발생한 오류는 대시보드에 남지 않습니다**. Endpoint의 **Return값**으로 직접 확인하세요.

### Q6. "일단위" 차트의 데이터 기준은 무엇인가요?
→ **한국 시간 기준, 00~24시에 수집된 데이터**를 합칩니다.

### Q7. "시간단위" 차트의 시간 축에 시간도 같이 표기해 줄 수 없나요?
→ 시간 표기 시, **Grafana의 Default 설정(UTC)** 과 **데이터 집계 기준(KST)** 차이로 인해 Bar가 잘못 표시되는 구간이 있어, 의도적으로 X축에 시간을 표기하지 않았습니다. 대시보드 업그레이드하면서 직관적으로 개선해 나가겠습니다.

### Q8. Total 연산시간(sec)과 모니터링 Parameter(값)를 동시에 보여주는 이유가 무엇인가요?
→ **연산시간 지연이 발생했을 때**, 연산시간과 Parameter 간 **상관관계가 있는지 분석**하려는 목적입니다. 향후, 모델에 사용된 **데이터 사이즈**도 Logging하도록 안내하여, 시간 지연에 원인이 되는 정보를 다각화해서 제공할 계획입니다.

### Q9. Scatter 차트에서 한 Point는 무엇을 의미하나요?
→ **1초 내 집계된 데이터의 평균값**입니다. 만약 1초 이내 호출 건수가 많다면 Endpoint 호출 단일 결과값이 아니라, **1초 단위로 평균해서 집계**합니다.

### Q10. 1초보다 더 줄일 수 없나요?
→ 현 버전의 Grafana에서는 **1초가 최소 집계 시간**입니다.

---

## 19. 각 서비스 접속 시 로그인 정보

### 19.1 \[jupyter, vscode, mlflow\]

AI Studio에서 제공하는 **jupyter, vscode, mlflow** 의 경우:

| 항목 | 값 |
|---|---|
| **ID** | `aistudio` |
| **PW** | `aistudio123!` |

으로 접속합니다.

### 19.2 \[Monitoring 및 Logging\]

추가로 **Inference Service**의 **`Log↗`** 와 **`Metric↗`** 버튼들은 **HCP의 SRE를 기반**으로 하고 있습니다.
- **`Log`** → **HCP의 Kibana** 로 이동
- **`Metric`** → **HCP의 Grafana** 서비스로 이동

이때 로그인이 필요한 경우에는:

| 항목 | 값 |
|---|---|
| **ID** | `{프로젝트이름}` |
| **PW** | `{프로젝트이름}12345` |

로 접속합니다.

![Action 컬럼 — Log↗ / Metric↗](<각_서비스접속시_로그인을_필요로_할때1.png>)

---

## 20. 부록 — 참고 링크

- **HCP 포털**: <http://cloud.skhynix.com>
- **AI Studio Portal**: `https://aistudio.skhynix.com/apps/ai-studio-fe/projects/{프로젝트명}`
- **Model Endpoint 모니터링하기 (iflow)**: <http://iflow.skhynix.com/group/article/4752604>
- **Model Endpoint "잘" 모니터링하기 (iflow)**: <http://iflow.skhynix.com/group/article/4774037>

---

> 본 문서는 `AI_STUDIO_extracted/` 폴더 내 모든 텍스트(.txt) 가이드 파일과 첨부 이미지(.png) **80장의 화면 내용을 직접 확인**하여 누락 없이 통합·정리한 문서입니다. 각 단계의 화면 캡처는 본문 내 인라인 이미지 링크로 첨부되어 있으며, 이미지에서만 확인 가능했던 폼 필드, 컬럼명, YAML 정의, Request/Response 코드, Grafana 카드 구성 등 세부 내용을 모두 본문에 반영했습니다.
