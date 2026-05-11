# AI Studio 사용법 (전체 가이드)

본 문서는 SK하이닉스 HCP 기반 **AI Studio (AIU)** 의 전체 사용법을 정리한 통합 매뉴얼입니다.
프로젝트 신청 → 모델링(Run/Experiment) → 서빙(Inference/Static Endpoint/Debugging) → 모니터링(Resource/Model)까지 전 과정을 다룹니다.

---

## 목차

1. [AI Studio 소개](#1-ai-studio-소개)
2. [Main 화면](#2-main-화면)
3. [프로젝트 생성하기](#3-프로젝트-생성하기)
4. [프로젝트에 멤버 추가하기](#4-프로젝트에-멤버-추가하기)
5. [\[Home\] Overview & Info](#5-home-overview--info)
6. [\[Modeling > Run\] Training을 Run(Job)으로 실행하기](#6-modeling--run--training을-runjob으로-실행하기)
7. [\[Modeling > Experiment\] 실험 결과 확인하기](#7-modeling--experiment--실험-결과-확인하기)
8. [\[Serving > Inference Service\] Single Inference 하기](#8-serving--inference-service--single-inference-하기)
9. [\[Serving > Inference Service\] Group(Ensemble) Inference 하기](#9-serving--inference-service--groupensemble-inference-하기)
10. [\[Serving > Inference Service\] Debugging 하기](#10-serving--inference-service--debugging-하기)
11. [\[Serving > Static Endpoint\] URL 고정하기](#11-serving--static-endpoint--url-고정하기)
12. [\[Monitoring > Resource\] 리소스 모니터링 하기](#12-monitoring--resource--리소스-모니터링-하기)
13. [\[Monitoring > Model\] 모델 모니터링 하기](#13-monitoring--model--모델-모니터링-하기)
14. [Model Endpoint 모니터링 내용 (지표 해석)](#14-model-endpoint-모니터링-내용-지표-해석)
15. [Model Endpoint "잘" 모니터링하기 (Tip)](#15-model-endpoint-잘-모니터링하기-tip)
16. [Model Endpoint 모니터링 차트 FAQ](#16-model-endpoint-모니터링-차트-faq)
17. [각 서비스 접속 시 로그인 정보](#17-각-서비스-접속-시-로그인-정보)

---

## 1. AI Studio 소개

**AI Studio**는 **AI/ML DevOps 시스템**입니다.

> 그러면.. AI/ML DevOps는 왜 필요할까요..?
>
> **한번 만들고 끝이 아닌, 지속적인 관리/배포 체계가 필요하기 때문**입니다.

![AI_Studio_란 1](<AI_Studio_란1.png>)
![AI_Studio_란 2](<AI_Studio_란2.png>)
![AI_Studio_란 3](<AI_Studio_란3.png>)
![AI_Studio_란 4](<AI_Studio_란4.png>)

---

## 2. Main 화면

AI Studio Main 화면 구성 요소는 다음과 같습니다.

| 번호 | 메뉴 | 설명 |
|:---:|---|---|
| (1) | **ALL PROJECTS** | 전체 프로젝트 확인 및 검색 가능한 화면을 띄워 줍니다. |
| (2) | **CREATE PROJECT** | 프로젝트 생성 가능하도록, **HCP 프로젝트 생성 사이트**와 연결합니다. |
| (3) | **My Project** | 내가 멤버로 속해 있는 프로젝트들을 보여 줍니다. |
| (4) | **NOTICE** | AI Studio iflow의 공지사항과 연결되어 있습니다. |
| (5) | **GUIDE** | AI Studio iflow의 가이드와 연결되어 있습니다. |
| (6) | **VIDEO** | AI Studio HyTube 영상과 연결되어 있습니다. |

![Main 화면 1](<[Main]Main_화면1.png>)
![Main 화면 2](<[Main]Main_화면2.png>)
![Main 화면 3](<[Main]Main_화면3.png>)

---

## 3. 프로젝트 생성하기

1. **AI Studio (AIU)** 는 HCP의 서비스로서, HCP의 서비스를 기반으로 AI/ML DevOps를 조금 더 쉽게 적용할 수 있도록 도움을 주는 시스템입니다.
2. 따라서, AI Studio를 활용하기 위해서는 **HCP에서 프로젝트를 먼저 신청**해야 합니다.
3. <http://cloud.skhynix.com> 접속합니다.
4. 좌측 메뉴에서 **Project → "프로젝트"** 클릭합니다.

   ![Project 생성 1](<Project_생성_하기1.png>)

5. **"프로젝트 추가"** 클릭합니다.

   ![Project 생성 2](<Project_생성_하기2.png>)

6. 기본 정보를 입력합니다.
   - 이때, **"프로젝트 타입"을 반드시 "AI" 로 선택**해야 AI Studio를 활용할 수 있습니다.

   ![Project 생성 3](<Project_생성_하기3.png>)
   ![Project 생성 4](<Project_생성_하기4.png>)

7. **"만들기"** 클릭합니다.

   ![Project 생성 5](<Project_생성_하기5.png>)

8. **프로젝트 승인 후**에 AI Studio 활용 가능합니다.

---

## 4. 프로젝트에 멤버 추가하기

AI Studio에서 프로젝트를 활용하다가, 또 다른 멤버를 추가해야 할 일이 생길 수 있습니다.
이런 경우에는 **HCP Portal**에서 해당 프로젝트에 권한을 주면 됩니다.

1. **HCP에 접속**: <http://cloud.skhynix.com/>
2. 좌측 메뉴에서 **"Project > 프로젝트"** 클릭

   ![멤버 추가 1](<AI_Studio에멤버추가하기1.png>)

3. 프로젝트 찾기

   ![멤버 추가 2](<AI_Studio에멤버추가하기2.png>)

4. 해당 프로젝트를 눌러서 **"접근 권한"**을 눌러 권한 추가 화면 접근

   ![멤버 추가 3](<AI_Studio에멤버추가하기3.png>)

5. 추가하고자 하는 **멤버 선택 후 확인** 버튼

   ![멤버 추가 4](<AI_Studio에멤버추가하기4.png>)

6. **"저장"** 버튼 클릭

   ![멤버 추가 5](<AI_Studio에멤버추가하기5.png>)

이제 멤버 추가가 완료되었습니다!

---

## 5. \[Home\] Overview & Info

### Overview

전체적으로 어떤 모델과 서비스가 있고, 어떤 Run 들이 있는지에 대하여 확인 가능합니다.

| 번호 | 항목 | 설명 |
|:---:|---|---|
| (1) | **Model** | 최근 등록된 모델과 최신 버전을 보여 줍니다. |
| (2) | **Endpoint** | 최근 등록된 Endpoint 를 보여 줍니다. |
| (3) | **Run Template** | 최근 등록된 Run Template을 보여 줍니다. |
| (4) | **Run Instance** | 최근 실행된 Run 을 보여 줍니다. |

![Home Overview 1](<[Home]_Overview_Info1.png>)
![Home Overview 2](<[Home]_Overview_Info2.png>)

### Info

프로젝트 이름, 멤버 등의 정보를 조회할 수 있습니다.

Cube 알람을 수정하거나, 프로젝트 멤버 등을 수정할 수 있도록 **"Cube" 링크**나 **"Edit" 버튼**을 누르면 **HCP의 수정 페이지**로 이동합니다.

![Home Info 3](<[Home]_Overview_Info3.png>)

---

## 6. \[Modeling > Run\] Training을 Run(Job)으로 실행하기

### 1) Run 화면 진입

Run 화면을 클릭하면 아래와 같은 화면이 나타납니다.

- 한 번도 수행한 이력이 없다면 **"Latest Run Instances"** 화면은 나오지 않게 됩니다.
- 수행한 이력이 있다면 상단에 **최근 수행 이력**이 나타나게 됩니다.

![Run 1](<[Modeling_Run]Training을_Run(Job)으로_실행하기1.png>)
![Run 2](<[Modeling_Run]Training을_Run(Job)으로_실행하기2.png>)

### 2) RUN Template 생성하기

**"CREATE"** 버튼 클릭

![Run 3](<[Modeling_Run]Training을_Run(Job)으로_실행하기3.png>)

### 3) 기본 정보 입력

| 번호 | 항목 | 설명 |
|:---:|---|---|
| (1) | **Name** | 이름 |
| (2) | **Python Version** | 생성하고자 하는 파이썬 버전 |
| (3) | **리소스** | 생성하고자 하는 리소스 크기 |
| (4) | **Bitbucket Repository 주소** | ssh가 아닌 **http**의 git 주소 |
| (5) | **Branch** | 실행하고자 하는 Branch 이름 |
| (6) | **File** | Bitbucket을 선택 후 나타나는 파일 중, Run(Job)을 실행하고자 하는 **Main이 되는 File**을 선택 |
| (7) | **Requirements** | RUN 실행 시 설치하고자 하는 패키지들을 입력 |

모든 정보가 입력되었으면 **"CREATE"** 버튼을 누릅니다.

![Run 4](<[Modeling_Run]Training을_Run(Job)으로_실행하기4.png>)
![Run 5](<[Modeling_Run]Training을_Run(Job)으로_실행하기5.png>)

### 4) RUN 환경 생성

RUN 수행을 하기 위한 환경 만드는 작업을 시작합니다.
아래와 같이 **IN PROGRESS** 상태는 만드는 중이며, 해당 컬럼을 **Double Click** 시 상세 Status를 확인할 수 있습니다.

![Run 6](<[Modeling_Run]Training을_Run(Job)으로_실행하기6.png>)
![Run 7](<[Modeling_Run]Training을_Run(Job)으로_실행하기7.png>)

### 5) RUN 실행

RUN 실행 버튼을 눌러 실행합니다.

![Run 8](<[Modeling_Run]Training을_Run(Job)으로_실행하기8.png>)

### 6) Queue 선택

가용 가능한 **Queue List** 가 뜨고, 선택합니다. 추후 **GPU** 도 Queue에 추가될 예정입니다.

![Run 9](<[Modeling_Run]Training을_Run(Job)으로_실행하기9.png>)

### 7) 실행 상태 확인

실행 대기 중인 경우 **Waiting**, 완료된 경우 **COMPLETED**, 실패인 경우 **FAILED** 로 카드 형태로 표시됩니다.

![Run 10](<[Modeling_Run]Training을_Run(Job)으로_실행하기10.png>)
![Run 11](<[Modeling_Run]Training을_Run(Job)으로_실행하기11.png>)

### 8) 전체 Run Instances 확인

최근 Run이 많은 경우에는 **+ 버튼**을 누르면 전체 Run Instances를 확인할 수 있습니다.

![Run 12](<[Modeling_Run]Training을_Run(Job)으로_실행하기12.png>)

---

## 7. \[Modeling > Experiment\] 실험 결과 확인하기

**Experiment**는 **MLFlow의 실험 결과 화면**으로 별도 탭으로 접속합니다.
아래와 같이 MLFlow 화면에서 실험 결과를 확인할 수 있습니다.

![Experiment 1](<[Modeling_Experiment]_실험결과_확인하기1.png>)
![Experiment 2](<[Modeling_Experiment]_실험결과_확인하기2.png>)

---

## 8. \[Serving > Inference Service\] Single Inference 하기

### 1) Create

**"Create"** 버튼 클릭

![Single Inference 1](<[Serving_Inference Service]_Single_Inference하기1.png>)

### 2) Model 선택

Model 선택을 위하여 **Select** 버튼을 누릅니다.
원하는 Model과 버전을 선택하여 **"APPLY"** 버튼을 누릅니다.
이후 **Serving이 진행**됩니다.

![Single Inference 2](<[Serving_Inference Service]_Single_Inference하기2.png>)
![Single Inference 3](<[Serving_Inference Service]_Single_Inference하기3.png>)

### 3) Requirements 확인 후 CREATE

Serving 환경에 필요한 패키지들의 **requirements**를 잘 확인합니다.

> requirements가 dependency에 의해 에러가 발생할 수 있으니 확인합니다.

**"CREATE"** 버튼을 Click 하여 서빙을 시작합니다.

![Single Inference 4](<[Serving_Inference Service]_Single_Inference하기4.png>)

### 4) Status 확인

Serving 진행 중, Inference 환경을 만드는 **"Deploy Status"** 와 필요한 코드를 다운로드하고 구동시키는 **"Status"** 를 확인합니다.

![Single Inference 5](<[Serving_Inference Service]_Single_Inference하기5.png>)

### 5) 생성된 서비스 진입

생성 완료 후 생성된 Inference 서비스를 **Double Click** 합니다.

![Single Inference 6](<[Serving_Inference Service]_Single_Inference하기6.png>)
![Single Inference 7](<[Serving_Inference Service]_Single_Inference하기7.png>)

### 6) URL 복사 / Log / Metric / Request Code

- **URL** 을 복사하여 Request 하여 Inference 서비스를 제공할 수 있습니다.
- 관련 로그는 **"Log"** 에서 볼 수 있으며, **"Metric"** 에서 리소스 현황을 볼 수 있습니다.
- **"Request Code"** 를 Copy 하여 수행하면 **Inference Test** 를 할 수 있습니다.

![Single Inference 8](<[Serving_Inference Service]_Single_Inference하기8.png>)

### 7) Inference Test 결과

Inference Test 결과 아래와 같이 값이 잘 나오는 것을 확인할 수 있습니다.

![Single Inference 9](<[Serving_Inference Service]_Single_Inference하기9.png>)

---

## 9. \[Serving > Inference Service\] Group(Ensemble) Inference 하기

### 1) CREATE

**"CREATE"** 버튼을 눌러 Ensemble Inference를 생성합니다.

> (2025. 09. 23. 현재 **Ensemble** 만 지원중. 추후 **Sequence** 등 지원 예정)

![Group Inference 1](<[Serving_Inference Service]_Group_Inference하기1.png>)

### 2) SELECT

**"SELECT"** 버튼을 눌러 Ensemble 모델 생성을 위한 선택 화면을 띄웁니다.

![Group Inference 2](<[Serving_Inference Service]_Group_Inference하기2.png>)
![Group Inference 3](<[Serving_Inference Service]_Group_Inference하기3.png>)

### 3) Single Inference Service 선택 → APPLY

Single Inference Service 중 Ensemble이 필요한 서비스들을 클릭 후 **"APPLY"** 버튼을 누릅니다.

![Group Inference 4](<[Serving_Inference Service]_Group_Inference하기4.png>)

### 4) CREATE

**"CREATE"** 버튼을 눌러 Ensemble Service를 생성합니다.

![Group Inference 5](<[Serving_Inference Service]_Group_Inference하기5.png>)

### 5) Status 확인

환경을 구성하는 **"Deploy Status"** 와 서비스 상태인 **"Status"** 가 각각 **"SUCCESS"** 와 **"READY"** 가 되면 Ensemble Inference Service를 활용 가능하며, 서비스 환경 구성하는 데 사내 네트워크 상태에 따라 다르지만 **대략 5분~15분 정도** 소요됩니다.

![Group Inference 6](<[Serving_Inference Service]_Group_Inference하기6.png>)

### 6) 상세 정보 확인

Ensemble Inference를 **Double Click** 하여 상세 정보를 확인합니다.

![Group Inference 7](<[Serving_Inference Service]_Group_Inference하기7.png>)

### 7) 상세 페이지

상세 페이지에서 Inference 가능한 **"URL"** 정보, **Trace View** 확인 가능한 **"전체보기"**, **"Log"** 정보 등을 확인할 수 있습니다.

![Group Inference 8](<[Serving_Inference Service]_Group_Inference하기8.png>)

### 8) 상세보기 → Group 구성 확인

**"상세보기"** 를 클릭하면 아래와 같이, 어떤 Inference 서비스들이 Group으로 Ensemble 되어 있는지 확인 가능합니다.

![Group Inference 9](<[Serving_Inference Service]_Group_Inference하기9.png>)

### 9) URL Copy → Test

**"URL"** 을 Copy 하여 아래와 같이 Inference Test 후 결과를 볼 수 있습니다.

![Group Inference 10](<[Serving_Inference Service]_Group_Inference하기10.png>)

---

## 10. \[Serving > Inference Service\] Debugging 하기

인퍼런스 서비스를 하다 보면, **Debugging이 필요한 순간**이 있습니다.
이때, 인퍼런스 서비스를 직접 디버깅하는 것은 **운영상의 이슈**가 발생할 수 있습니다.
동일한 인퍼런스 서비스를 **VSCode** 와 함께 생성할 수 있는 기능을 제공하여, **VSCode에서 중단점을 걸고 Debugging이 가능**하도록 합니다.

### 1) OFF → CREATE

**"OFF"** 버튼을 클릭 후 **"CREATE"** 버튼을 Click 합니다.

![Debugging 1](<[Serving_Inference Service]_Debugging하기1.png>)
![Debugging 2](<[Serving_Inference Service]_Debugging하기2.png>)

### 2) OFF → ON

아래와 같이 **"OFF" → "ON"** 으로 변경됩니다.

![Debugging 3](<[Serving_Inference Service]_Debugging하기3.png>)

### 3) ON 클릭 후 Status 확인

**"ON"** 버튼을 클릭합니다. 아래와 같이 **Deploy Status**와 **Status**를 확인합니다.

![Debugging 4](<[Serving_Inference Service]_Debugging하기4.png>)

### 4) SUCCESS / READY → 디버깅 가능

잠시 뒤 아래와 같이 Status가 **SUCCESS** 와 **READY** 가 된 것이 확인되면 디버깅 가능합니다.
URL copy 하여 inference 가능하면 **"VS Code"** 클릭 시 VS Code 환경이 뜹니다.

![Debugging 5](<[Serving_Inference Service]_Debugging하기5.png>)

### 5) VS Code 접속

default 비밀번호인 **`aistudio123!`** 을 입력 후 VS Code에 접속합니다.
Code 중, **"Predict" 함수**를 수정하면, 코드 변경하면서 Inference 테스트를 할 수 있으며, **디버그도 가능**합니다.

![Debugging 6](<[Serving_Inference Service]_Debugging하기6.png>)

---

## 11. \[Serving > Static Endpoint\] URL 고정하기

### 1) CREATE

**"CREATE"** 버튼 클릭

![Static Endpoint 1](<[Serving_Static_Endpoint]_URL고정하기1.png>)
![Static Endpoint 2](<[Serving_Static_Endpoint]_URL고정하기2.png>)

### 2) Name 설정 후 CREATE

Name을 설정 후 **"CREATE"** 버튼을 눌러 줍니다.

![Static Endpoint 3](<[Serving_Static_Endpoint]_URL고정하기3.png>)

### 3) Service 선택 후 APPLY

이후 화면에서 연결하고자 하는 **Single Inference Service** 나 **Group Inference Service** 를 클릭 후 **"APPLY"** 버튼을 클릭합니다.

![Static Endpoint 4](<[Serving_Static_Endpoint]_URL고정하기4.png>)

### 4) Model 교체 (EDIT)

Model을 교체 시, 다시 해당 Static 서비스를 **Double Click** 하여 상세 페이지로 이동 후 **"EDIT"** 버튼을 클릭하여 원하는 모델로 교체합니다.

![Static Endpoint 5](<[Serving_Static_Endpoint]_URL고정하기5.png>)
![Static Endpoint 6](<[Serving_Static_Endpoint]_URL고정하기6.png>)
![Static Endpoint 7](<[Serving_Static_Endpoint]_URL고정하기7.png>)

### 5) Inference Test (Ensemble 결과 확인)

Inference Test 시 Ensemble 결과로 변경된 모델 결과가 나오는 것을 확인할 수 있습니다.

![Static Endpoint 8](<[Serving_Static_Endpoint]_URL고정하기8.png>)

### 6) History / Rollback

변경된 이력 관리를 위하여 **History** 가 보이고, **"Rollback"** 기능을 통하여 이전 모델로 되돌리는 것도 가능합니다.

![Static Endpoint 9](<[Serving_Static_Endpoint]_URL고정하기9.png>)
![Static Endpoint 10](<[Serving_Static_Endpoint]_URL고정하기10.png>)

### 7) Rollback 수행

아래와 같이 Rollback을 합니다.

![Static Endpoint 11](<[Serving_Static_Endpoint]_URL고정하기11.png>)

### 8) Rollback 결과 확인

동일한 Endpoint의 동일한 Inference Code를 수행해 보았을 때 **Single End Point 모델의 결과**가 나오는 것을 확인할 수 있습니다.

![Static Endpoint 12](<[Serving_Static_Endpoint]_URL고정하기12.png>)

---

## 12. \[Monitoring > Resource\] 리소스 모니터링 하기

현재는 **jupyterlab, vscode, mlflow, object storage** 리소스에 대해서만 표현이 되어 있으나, 추후에는 **Inference 서비스까지 통합적으로** 볼 수 있도록 합니다.

- **서비스 현황** : 현재 제공받은 서비스들의 현황입니다. 대부분의 사용자분들은 이 상태만 확인해도 됩니다.
- **Pod 현황** : 서비스에서 조금 더 나아가 K8S의 Pod 것이 어떤 Host에 어떤 Pod 이름으로 떠 있는지 보여 줍니다.
- **Object Storage** : mlflow의 저장소로 활용 중인 Object Storage의 사용량을 보여 줍니다.

![Monitoring Resource 1](<[Monitoring_Resource]리소스모니터링_하기1.png>)

---

## 13. \[Monitoring > Model\] 모델 모니터링 하기

**모델의 Inference**를 모니터링 하기 위한 메뉴입니다.

1. 메뉴 진입 시 모델 모니터링 대시보드가 노출됩니다.
2. **"Click"** 시 **Grafana 화면**으로 이동이 되게 됩니다.
3. 잘 활용하기 위해서는 아래 iflow를 참고하세요.
   - **Model Endpoint 모니터링하기** : <http://iflow.skhynix.com/group/article/4752604>
   - **Model Endpoint "잘" 모니터링하기** : <http://iflow.skhynix.com/group/article/4774037>

![Monitoring Model 1](<[Monitoring_Model]_모델모니터링_하기1.png>)
![Monitoring Model 2](<[Monitoring_Model]_모델모니터링_하기2.png>)

---

## 14. Model Endpoint 모니터링 내용 (지표 해석)

모델 Endpoint를 호출했을 때, 집계되는 모니터링 항목을 해석해 드립니다.

1. **화면 메뉴 위치** : `AI Studio Portal > My Project 카드 클릭 > Monitoring > Model`
2. 차트에서 공통으로 **Bar는 일 단위**, **Line은 트렌드**, **Point는 개별 값 분포**를 의미합니다.
3. 주요 지표 중 **파란색 카드**는 **자동 집계**, **녹색 카드**는 **모델 개발자가 값을 직접 만들어야** 표시됩니다.
4. **기본 2주 단위**로 제공되며, 우측 상단의 기간 버튼을 통해 변경 가능합니다. 조회 가능 기간은 **오늘부터 최대 2주**입니다.
5. 좌측 상단의 **MODEL 체크박스**를 펼쳐서 특정 모델만 필터링할 수 있습니다.
6. **TRACE ID** 를 입력하여 대시보드 최하단 패널에서 상세 **Raw Data** 확인도 가능합니다.
7. **"호출 건수"** 는 모델 연산 단계로 넘어간 호출 건만 포함합니다. 연산 전 단계에서 오류가 발생한 경우 집계되지 않습니다.
8. **평균 산출 시**, **"호출 건수"** 는 호출 건수가 0인 일자도 분모에 포함, **연산 시간**과 **모니터링 Parameter 값**은 존재하는 Data 건수만 분모에 포함해서 계산했습니다.

![Endpoint 모니터링 내용 1](<Model_Endpoint_모니터링하기내용1.png>)
![Endpoint 모니터링 내용 2](<Model_Endpoint_모니터링하기내용2.png>)
![Endpoint 모니터링 내용 3](<Model_Endpoint_모니터링하기내용3.png>)
![Endpoint 모니터링 내용 4](<Model_Endpoint_모니터링하기내용4.png>)
![Endpoint 모니터링 내용 5](<Model_Endpoint_모니터링하기내용5.png>)

---

## 15. Model Endpoint "잘" 모니터링하기 (Tip)

모델 Endpoint를 호출했을 때, **수동으로 집계되는 모니터링 항목**을 잘 만드는 Tip을 드립니다.

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

## 16. Model Endpoint 모니터링 차트 FAQ

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

→ **Q4 와도 관련된 답변**입니다.
**모델 연산이 시작되어야** 대시보드의 데이터도 수집됩니다.
**인풋 데이터 이상**처럼, **모델 연산이 시작되기 전에 발생한 오류는 대시보드에 남지 않습니다**.
Endpoint의 **Return값**으로 직접 확인하세요.

### Q6. "일단위" 차트의 데이터 기준은 무엇인가요?

→ **한국 시간 기준, 00~24시에 수집된 데이터**를 합칩니다.

### Q7. "시간단위" 차트의 시간 축에 시간도 같이 표기해 줄 수 없나요?

→ 시간 표기 시, **Grafana의 Default 설정(UTC)** 과 **데이터 집계 기준(KST)** 차이로 인해 Bar가 잘못 표시되는 구간이 있어, 의도적으로 X축에 시간을 표기하지 않았습니다.
대시보드 업그레이드하면서 직관적으로 개선해 나가겠습니다.

### Q8. Total 연산시간(sec)과 모니터링 Parameter(값)를 동시에 보여주는 이유가 무엇인가요?

→ **연산시간 지연이 발생했을 때**, 연산시간과 Parameter 간 **상관관계가 있는지 분석**하려는 목적입니다.
향후, 모델에 사용된 **데이터 사이즈**도 Logging하도록 안내하여, 시간 지연에 원인이 되는 정보를 다각화해서 제공할 계획입니다.

### Q9. Scatter 차트에서 한 Point는 무엇을 의미하나요?

→ **1초 내 집계된 데이터의 평균값**입니다.
만약 1초 이내 호출 건수가 많다면 Endpoint 호출 단일 결과값이 아니라, **1초 단위로 평균해서 집계**합니다.

### Q10. 1초보다 더 줄일 수 없나요?

→ 현 버전의 Grafana에서는 **1초가 최소 집계 시간**입니다.

---

## 17. 각 서비스 접속 시 로그인 정보

### \[jupyter, vscode, mlflow\]

AI Studio에서 제공하는 **jupyter, vscode, mlflow** 의 경우:

| 항목 | 값 |
|---|---|
| **ID** | `aistudio` |
| **PW** | `aistudio123!` |

으로 접속합니다.

### \[Monitoring 및 Logging\]

추가로 **Inference Service**의 **"Log"** 와 **"Metric"** 버튼들은 **HCP의 SRE를 기반**으로 하고 있습니다.
따라서 **"Log"** 는 **HCP의 Kibana**로, **"Metric"** 은 **HCP의 Grafana** 서비스로 이동하는데,
이때 로그인이 필요한 경우에는:

| 항목 | 값 |
|---|---|
| **ID** | `{프로젝트이름}` |
| **PW** | `{프로젝트이름}12345` |

로 접속합니다.

![서비스 접속 로그인 1](<각_서비스접속시_로그인을_필요로_할때1.png>)

---

## 부록 — 참고 링크

- HCP 포털: <http://cloud.skhynix.com>
- Model Endpoint 모니터링하기 (iflow): <http://iflow.skhynix.com/group/article/4752604>
- Model Endpoint "잘" 모니터링하기 (iflow): <http://iflow.skhynix.com/group/article/4774037>

---

> 본 문서는 `AI_STUDIO_extracted/` 폴더 내 모든 텍스트(.txt) 가이드 파일과 첨부 이미지(.png)를 누락 없이 통합·정리한 문서입니다.
