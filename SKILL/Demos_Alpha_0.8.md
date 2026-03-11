# Demos(민중) Alpha 0.8 - 기술 문서

> SK Hynix 폐쇄망 환경용 과학 연구 & 소프트웨어 개발 AI 어시스턴트
> Flask 단일 파일 웹앱 | 372개 전문 스킬 | 회사 LLM API + GGUF 로컬 모델

---

## 1. 시스템 아키텍처

Demos는 단일 `app.py` 파일(약 3,500줄)로 구성된 Flask 웹 애플리케이션입니다.
프론트엔드(HTML/CSS/JS)와 백엔드(Python Flask)가 하나의 파일에 통합되어 있어 폐쇄망 환경에서 별도 빌드 도구 없이 바로 실행할 수 있습니다.

### 1.1 폴더 구조

```
scientific-assistant/
├── app.py                 ← 메인 애플리케이션 (전체 코드)
├── TOKEN.TXT              ← 회사 LLM API 키 (한 줄)
├── saved-prompts/         ← 사용자 저장 시스템 프롬프트 (.txt)
├── scientific-skills/     ← 372개 스킬 폴더
│   ├── biopython/SKILL.md
│   ├── agent-python-pro/SKILL.md
│   ├── guide-python/SKILL.md
│   └── ... (나머지 스킬 폴더들)
└── *.gguf                 ← (선택) GGUF 로컬 모델 파일
```

### 1.2 실행 방법

```bash
pip install flask requests
# GGUF 로컬 모델 사용 시:
pip install llama-cpp-python
python app.py
# → http://localhost:10009
```

---

## 2. LLM 환경 (모델 선택)

Demos는 4가지 LLM 환경을 지원합니다. 상황에 따라 적합한 모델을 선택하세요.

### 2.1 회사 API 모델

| 환경 | 모델 | 특징 | 언제 사용? |
|------|------|------|-----------|
| **DEV (4.7)** | GLM-4.7 | 개발 서버, 빠른 응답 | 간단한 코딩 질문, 빠른 테스트, 일반 대화 |
| **PROD (397B)** | Qwen3.5-397B-A17B | 최대 모델, 고품질 | 복잡한 분석, 긴 코드 생성, 논문/보고서 수준 답변 |
| **COMMON (120B)** | gpt-oss-120b | 범용 모델, 균형 잡힌 성능 | 일반적인 개발 작업, 적당한 품질+속도 |

### 2.2 GGUF 로컬 모델

| 환경 | 모델 | 특징 | 언제 사용? |
|------|------|------|-----------|
| **GGUF 로컬** | Qwen3-8B-Q6_K | 오프라인, 32K 컨텍스트 | 네트워크 불가 시, 민감 데이터 처리, API 서버 점검 시 |

**GGUF 주의사항:**
- 컨텍스트 32,768 토큰 제한 → 스킬 많이 로드하면 잘릴 수 있음
- 토큰 예산 자동 관리: 시스템 프롬프트 + 히스토리 + 스킬 크기 자동 계산
- `<think>` 태그 사고 과정이 한글로 표시됨 (접이식 박스)

---

## 3. 핵심 기능

### 3.1 스킬 시스템 (372개)

스킬은 SKILL.md 파일에 저장된 전문 지식으로, 시스템 프롬프트에 주입되어 LLM의 전문성을 높입니다.

**스킬 로드 방식:**

| 방식 | 설명 | 언제 사용? |
|------|------|-----------|
| **수동 선택** | 사이드바에서 직접 스킬 클릭 | 정확히 필요한 스킬을 알 때, 특정 분야 집중 작업 |
| **자동 추천** | 질문 입력 시 키워드 매칭으로 자동 추천 | 어떤 스킬이 필요한지 모를 때, 일반적인 질문 |
| **컨텍스트 인식** | 최근 3턴 대화 분석 + 현재 질문으로 추천 | 대화가 이어지는 상황, 맥락 유지가 필요할 때 |

**자동 스킬 라우팅 동작 원리:**
1. 현재 질문에서 키워드 매칭 (가중치 1.0)
2. 최근 3턴 대화 히스토리 분석 (가중치 0.3)
3. 질문 유형 감지 → 부스팅 (에러/버그 → 디버깅 스킬 +5점, 데이터 분석 → 통계 스킬 +5점 등)
4. 점수 상위 최대 7개 스킬 자동 선택

### 3.2 멀티에이전트 오케스트레이션

스킬이 2개 이상 로드되면 자동으로 오케스트레이션 모드가 활성화됩니다.

**동작 원리:**
- 각 스킬을 "전문가"로 취급
- LLM에게 여러 전문가의 지식을 조합하여 통합 답변을 생성하도록 지시
- 예: biopython + matplotlib → 서열 분석 + 시각화를 하나의 코드로 조합

**언제 활용?**
- "DNA 서열 분석하고 시각화해줘" → biopython + matplotlib 자동 조합
- "이 코드 리뷰하고 테스트 작성해줘" → code-review + agent-test-automator 조합
- "데이터 분석하고 보고서 써줘" → exploratory-data-analysis + scientific-writing 조합

### 3.3 시스템 프롬프트

LLM의 기본 행동을 설정하는 지시문입니다.

**내장 프리셋 5종:**

| 프리셋 | 아이콘 | 용도 | 언제 사용? |
|--------|--------|------|-----------|
| **코딩 전문가** | 💻 | import 포함 즉시 실행 코드, 에러 처리, 타입 힌트 | 새 코드를 처음부터 작성할 때 |
| **코드 수정/디버깅** | 🔧 | 진단→수정 전/후 비교→이유 설명, 최소 변경 원칙 | 기존 코드의 버그를 고칠 때 |
| **데이터 분석** | 📊 | pandas/matplotlib 기반, 시각화 포함, 인사이트 도출 | CSV 데이터 분석, 통계, 차트 생성 |
| **개발 올라운더** | 🛠️ | 설계→코드→테스트→문서화까지 전체 파이프라인 | 프로젝트 전체를 다룰 때 |
| **반도체 엔지니어** | 🔬 | 반도체 공정/장비/소자 전문, 산업 데이터 해석 | 반도체 관련 분석, 공정 최적화 |

**사용자 정의 프롬프트:**
- 직접 작성 → 저장 버튼 → `saved-prompts/` 폴더에 TXT로 저장
- 서버 재시작해도 유지됨
- 불필요한 프롬프트는 삭제 가능

### 3.4 작성 스타일 프리셋

답변의 톤과 형식을 조절합니다. 시스템 프롬프트와 별도로 작동합니다.

| 스타일 | 아이콘 | 설명 | 언제 사용? |
|--------|--------|------|-----------|
| **간결** | ⚡ | 핵심만 짧게 | 빠른 답변이 필요할 때, 코드 한 줄 질문 |
| **상세** | 📖 | 친절하고 꼼꼼하게 | 개념 이해가 필요할 때, 신입 교육 |
| **실용적** | 🔨 | 바로 복붙 가능 | 당장 실행할 코드가 필요할 때 |
| **학술** | 🎓 | 학술적 톤, 근거 제시 | 논문/보고서 작성, 학술 분석 |
| **한글주석** | 💬 | 코드 주석 상세 한국어 | 코드 공유, 팀 리뷰, 교육 자료 |
| **시니어** | 👨‍💻 | 시니어 개발자 관점 | 설계 판단, 트레이드오프 분석 |
| **디버그** | 🐛 | 에러 원인 분석 중심 | 에러 추적, 로그 분석 |
| **데이터** | 📊 | 데이터 스토리텔링 | 데이터 결과 발표, 경영진 보고 |

### 3.5 응답 깊이 (Effort)

슬라이더로 답변의 상세 수준을 조절합니다.

| 단계 | 설명 | 온도(Temperature) | 언제 사용? |
|------|------|-------------------|-----------|
| **0** | 매우 간결, 핵심만 | 0.1 | Yes/No 질문, 한 줄 답변 |
| **1** | 간결하게 | 0.3 | 짧은 코드 조각, 간단한 설명 |
| **2** | 표준 (기본값) | 0.5 | 일반적인 질문, 코드+설명 |
| **3** | 매우 상세/전문적 | 0.7 | 심층 분석, 원리 설명, 주석 가득 |

### 3.6 출력 형식 (Format)

답변의 구조를 지정합니다.

| 형식 | 설명 | 언제 사용? |
|------|------|-----------|
| **코드 중심** | Python 코드 위주, import 포함 | 코드 생성 요청 |
| **코드 수정** | 진단→수정 전/후 비교→이유 | 기존 코드 수정 |
| **분석** | 개요→코드→시각화→인사이트 | 데이터 분석 |
| **보고서** | 제목→요약→본문→결론 | 보고서/문서 작성 |
| **단계별** | 1,2,3... 순서, 각 단계 설명 | 절차 안내, 튜토리얼 |

### 3.7 CSV 데이터 업로드

CSV/TSV 파일을 업로드하면 시스템 프롬프트에 데이터 미리보기(최대 50행)가 포함됩니다.

**사용법:**
1. 사이드바 "데이터 업로드" 영역에 파일 드래그 앤 드롭 (또는 클릭)
2. 최대 50MB, UTF-8/CP949 자동 인식
3. 업로드 후 데이터에 대해 자유롭게 질문

**언제 사용?**
- "이 데이터의 평균/표준편차 구해줘"
- "이 CSV로 그래프 그려줘"
- "컬럼 간 상관관계 분석해줘"
- "이상치 찾아줘"

### 3.8 응답 중지

응답 생성 중에 ⏹ 버튼을 눌러 즉시 중단할 수 있습니다.

**동작 방식:**
- 전송(▶) 누르면 버튼이 빨간 ⏹로 변환
- ⏹ 클릭 시: API 요청 즉시 취소 (AbortController) + GGUF 스트리밍 중단
- GGUF: 지금까지 생성된 부분까지만 표시 + "⏹️ 응답이 중단되었습니다" 메시지
- Enter 키로도 동작 (응답 중이면 중지, 평소엔 전송)

**언제 사용?**
- 원하는 답변이 아닌 방향으로 가고 있을 때
- 너무 긴 응답이 생성되고 있을 때
- 잘못된 질문을 보냈을 때

### 3.9 세션 관리

대화를 세션 단위로 저장/관리합니다 (localStorage 기반).

**기능:**
- **새 세션**: 히스토리, 선택된 스킬, 스타일 등 모든 상태 초기화
- **세션 전환**: 사이드바에서 이전 세션 클릭하면 대화/스킬/설정 복원
- **체크박스 선택**: 여러 세션을 선택하여 일괄 작업
- **보관(📦)**: 자주 안 쓰는 세션을 보관 섹션으로 이동
- **복원(↩)**: 보관된 세션을 다시 활성 목록으로 복원
- **삭제(🗑️)**: 선택한 세션 영구 삭제

### 3.10 사이드바 접기/펼치기

◀/▶ 버튼으로 전체 사이드바를 접거나 펼 수 있습니다.
접힌 상태는 localStorage에 저장되어 새로고침해도 유지됩니다.

### 3.11 `<think>` 사고 과정 (CoT)

Qwen3 등 Chain-of-Thought 모델이 `<think>` 태그로 사고 과정을 출력하면, 프론트엔드에서 접이식 "💭 사고 과정" 박스로 렌더링됩니다.

**특징:**
- 시스템 프롬프트에서 한국어 사고를 지시
- 기본은 접혀있고, 클릭하면 펼쳐서 확인 가능
- 사고 과정이 어떤 언어로 나오든 보라색 박스에 표시

---

## 4. 스킬 카탈로그 (24개 카테고리, 372개 스킬)

### 4.1 🧬 생물정보학 (22개)

유전체, 단백질, 세포 분석 관련 스킬입니다.

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| biopython | 생물 서열/구조 분석 | DNA/RNA/단백질 서열 파싱, BLAST, PDB 구조 |
| scanpy | 단일세포 RNA-seq 분석 | scRNA-seq 데이터 QC, 클러스터링, 마커 유전자 |
| pydeseq2 | 차등 유전자 발현 분석 | RNA-seq DEG 분석, 조건 간 발현 비교 |
| bioservices | 40+ 생물정보학 DB 통합 | 여러 DB를 한번에 쿼리할 때 |
| anndata | 단일세포 주석 행렬 | AnnData 객체 생성/조작, h5ad 파일 |
| arboreto | 유전자 조절 네트워크 추론 | GRN 분석, GENIE3/GRNBoost2 |
| cellxgene-census | 6100만+ 단일세포 데이터 | 대규모 단일세포 데이터셋 접근 |
| deeptools | NGS BAM/bigWig 분석 | ChIP-seq, ATAC-seq 신호 분석 |
| gget | 20+ 생물DB 빠른 조회 | 유전자/단백질 정보 빠른 검색 |
| geniml | 유전체 구간 ML | 유전체 영역 기반 머신러닝 |
| gtars | 유전체 구간 고성능 분석 | BED/GTF 파일 대량 처리 |
| pysam | SAM/BAM/VCF 파일 처리 | NGS 정렬 파일, 변이 파일 직접 조작 |
| scikit-bio | 서열/다양성/마이크로바이옴 | 알파/베타 다양성, 미생물 군집 분석 |
| scvelo | RNA velocity 분석 | 세포 분화 방향/속도 예측 |
| scvi-tools | 단일세포 딥러닝 | VAE 기반 단일세포 모델링 |
| tiledbvcf | 유전체 변이 저장/조회 | 대용량 VCF 데이터 관리 |
| flowio | 유세포분석 FCS 파싱 | FCS 파일 읽기/분석 |
| phylogenetics | 계통수 구축 | 계통발생학적 분석 |
| etetoolkit | 계통수 조작/시각화 | 계통수 그리기, 주석 달기 |
| cobrapy | 대사 모델링 FBA/FVA | 대사 네트워크 플럭스 분석 |
| glycoengineering | 글리코실화 분석 | 당쇄 공학, 당단백질 분석 |
| esm | 단백질 언어모델 구조예측 | ESM-2 임베딩, 구조 예측 |

### 4.2 🗄️ 생물 DB (22개)

생물학 데이터베이스 API 연동 스킬입니다.

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| gene-database | NCBI Gene 조회 | 유전자 ID로 정보 검색 |
| ensembl-database | Ensembl 250+ 종 유전체 | 종별 유전체/전사체 정보 |
| uniprot-database | UniProt 단백질 검색 | 단백질 서열/기능/구조 정보 |
| geo-database | GEO 유전자 발현 | 발현 데이터셋 검색/다운로드 |
| clinvar-database | ClinVar 변이 의미 | 변이의 임상적 의미 조회 |
| gnomad-database | gnomAD 대립유전자 빈도 | 변이 빈도, 인구집단별 통계 |
| gtex-database | GTEx 조직별 발현 | 조직 특이적 유전자 발현 |
| gwas-database | GWAS SNP-형질 연관 | 유전체 전장 연관 분석 결과 |
| ena-database | 유럽 뉴클레오타이드 아카이브 | 서열 데이터 검색/다운로드 |
| biorxiv-database | bioRxiv 프리프린트 | 최신 생물학 프리프린트 검색 |
| string-database | 단백질 상호작용 | PPI 네트워크 조회/분석 |
| reactome-database | Reactome 경로 분석 | 생물학적 경로/반응 검색 |
| kegg-database | KEGG 대사경로 | 대사경로 매핑, 경로 분석 |
| interpro-database | 단백질 도메인 주석 | 도메인/모티프 예측 |
| jaspar-database | 전사인자 결합 프로파일 | TF 결합 부위 모티프 검색 |
| monarch-database | 질병-유전자 연관 | 질병-유전자-표현형 관계 |
| alphafold-database | AI 단백질 구조 | AlphaFold 예측 구조 조회 |
| pdb-database | PDB 3D 구조 | 실험적 단백질 3D 구조 |
| cosmic-database | COSMIC 암 돌연변이 | 체세포 돌연변이 데이터 |
| cbioportal-database | 암 유전체 | 암 유전체 다차원 분석 |
| depmap | 암 유전자 의존성 | 암 세포주 의존성 매핑 |
| opentargets-database | 치료 표적 발굴 | 약물-표적-질병 연관 |

### 4.3 ⚗️ 화학/신약 (22개)

화학정보학, 약물 발견, 분자 모델링 스킬입니다.

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| rdkit | 분자 처리 SMILES/SDF | 분자 구조 파싱, 핑거프린트, 유사도 |
| datamol | RDKit 래퍼/분자기술자 | RDKit을 더 쉽게 사용 |
| deepchem | 분자 ML | 분자 특성 예측 딥러닝 |
| molfeat | 100+ 분자 특성화기 | 분자 특성 벡터 생성 |
| matchms | 질량스펙트럼 유사도 | MS/MS 스펙트럼 비교 |
| medchem | 약물유사성/PAINS필터 | 약물 후보 필터링 |
| diffdock | 분자 도킹 결합예측 | 단백질-리간드 도킹 |
| molecular-dynamics | 분자동역학 OpenMM | MD 시뮬레이션 설정/실행 |
| torchdrug | 분자 그래프NN | 그래프 신경망 기반 분자 분석 |
| chembl-database | ChEMBL 생활성 분자 | 약물 활성 데이터 검색 |
| drugbank-database | 약물 정보/상호작용 | 약물 상호작용, 부작용 조회 |
| pubchem-database | PubChem 화합물 | 화합물 검색, 활성 데이터 |
| bindingdb-database | 약물-표적 친화도 | 결합 친화도 데이터 |
| zinc-database | 2.3억 화합물 스크리닝 | 가상 스크리닝용 화합물 라이브러리 |
| hmdb-database | 22만 대사체 DB | 대사체 정보 검색 |
| clinpgx-database | 약물유전체학 | 약물-유전자 관계 |
| brenda-database | 효소 동역학 | 효소 Km, Vmax 등 파라미터 |
| metabolomics-workbench-database | 대사체학 API | 대사체학 데이터 접근 |
| primekg | 정밀의학 지식그래프 | 다중 생물의학 데이터 통합 |
| pytdc | 신약 벤치마크 | 약물 발견 벤치마크 데이터셋 |
| rowan | 클라우드 양자화학 | 양자화학 계산 API |
| pyopenms | 질량분석 데이터 처리 | mzML/mzXML 파일 분석 |

### 4.4 ⚛️ 재료/물리/양자 (8개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| pymatgen | 재료과학 결정/상도 | 결정 구조 분석, 상태도 계산 |
| astropy | 천문학/천체물리 | 천체 좌표, 스펙트럼, FITS 파일 |
| fluidsim | 전산유체역학 | CFD 시뮬레이션 |
| sympy | 기호 수학 | 미적분, 선형대수, 방정식 풀이 |
| qiskit | IBM 양자 컴퓨팅 | 양자 회로 설계/시뮬레이션 |
| cirq | Google 양자 회로 | Google 양자 프로세서용 회로 |
| pennylane | 양자 ML | 양자-고전 하이브리드 ML |
| qutip | 양자계 시뮬레이션 | 양자 상태 진화, 마스터 방정식 |

### 4.5 📊 데이터/ML (27개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| matplotlib | 과학 시각화 | 논문/보고서용 그래프 |
| seaborn | 통계 시각화 | 히트맵, 분포도, 상관 플롯 |
| plotly | 인터랙티브 차트 | 웹 기반 대화형 시각화 |
| scikit-learn | ML 학습/평가 | 분류, 회귀, 클러스터링, 파이프라인 |
| pytorch-lightning | 딥러닝 멀티GPU | PyTorch 모델 훈련 구조화 |
| polars | 고속 DataFrame | pandas 대체, 대용량 데이터 고속 처리 |
| dask | 분산 컴퓨팅 | 메모리 초과 대용량 데이터 병렬 처리 |
| vaex | 대규모 테이블 | 수십억 행 데이터 out-of-core 처리 |
| networkx | 네트워크 분석 | 그래프 이론, 소셜 네트워크, 경로 분석 |
| shap | 모델 해석 SHAP | ML 모델 예측 설명 |
| umap-learn | UMAP 차원축소 | 고차원 데이터 시각화 |
| statsmodels | 통계 모델 OLS/GLM | 회귀분석, 시계열, 가설 검정 |
| statistical-analysis | 통계 분석 가이드 | 통계 방법론 선택, 해석 가이드 |
| exploratory-data-analysis | 탐색적 데이터 분석 | 데이터 품질 확인, 분포 파악, 패턴 발견 |
| torch-geometric | 그래프 신경망 | GNN, 노드/엣지 분류, 링크 예측 |
| stable-baselines3 | 강화학습 | RL 에이전트 훈련 |
| pufferlib | 고성능 RL | 대규모 강화학습 환경 |
| transformers | 트랜스포머 NLP/CV | BERT, GPT, ViT 등 사전학습 모델 |
| simpy | 이산사건 시뮬레이션 | 공정 시뮬레이션, 대기열 모델링 |
| pymoo | 다목적 최적화 | 파레토 최적화, 유전 알고리즘 |
| pymc | 베이지안 MCMC | 베이지안 추론, 확률적 프로그래밍 |
| aeon | 시계열 ML | 시계열 분류, 회귀, 이상 감지 |
| timesfm-forecasting | 시계열 예측 | Google TimesFM 예측 모델 |
| geopandas | 지리공간 분석 | 지도 시각화, 공간 조인 |
| geomaster | GIS/원격탐사 | 위성영상, 지리정보 처리 |
| scikit-survival | 생존 분석 ML | 생존곡선, Cox 모델, 생존 예측 |

### 4.6 💰 금융/경제 (8개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| alpha-vantage | 주식/외환/암호화폐 | 실시간/과거 시세 데이터 |
| edgartools | SEC 재무제표 | 미국 상장사 재무 데이터 |
| hedgefundmonitor | 헤지펀드 리스크 | 펀드 리스크 분석 |
| fred-economic-data | FRED 경제 데이터 | 경제 지표 (GDP, 실업률 등) |
| usfiscaldata | 미국 재정 데이터 | 미국 정부 재정 통계 |
| datacommons-client | 공공 통계 | Google Data Commons 통합 통계 |
| market-research-reports | 시장조사 보고서 | 시장 규모, 트렌드 분석 |
| uspto-database | 특허/상표 검색 | 특허 조회, IP 분석 |

### 4.7 🏥 임상/의학 (13개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| clinical-decision-support | 임상 의사결정 | 진단/치료 의사결정 지원 |
| clinical-reports | 임상보고서 작성 | 임상 보고서 구조화 |
| clinicaltrials-database | 임상시험 조회 | ClinicalTrials.gov API |
| fda-database | FDA 의약품/기기 | FDA 승인 정보, 라벨링 |
| treatment-plans | 치료 계획 생성 | 근거 기반 치료 계획 |
| pydicom | DICOM 의료영상 | CT/MRI 영상 파일 처리 |
| pyhealth | 의료 AI 예측 | EHR 기반 예측 모델 |
| pathml | 전산병리학 | 병리 슬라이드 AI 분석 |
| histolab | 조직영상 타일추출 | 조직 영상 전처리, 타일링 |
| imaging-data-commons | 암 영상 데이터 | NCI 암 영상 데이터 접근 |
| iso-13485-certification | 의료기기 품질인증 | ISO 13485 인증 프로세스 |
| neurokit2 | 생체신호 처리 | ECG, EEG, EMG 신호 분석 |
| neuropixels-analysis | 신경 기록 분석 | 다채널 전기생리학 분석 |

### 4.8 📝 논문/연구 (20개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| scientific-writing | 논문 작성 IMRAD | 논문 구조(서론/방법/결과/토론) 작성 |
| literature-review | 체계적 문헌 검토 | 체계적 리뷰, 메타분석 설계 |
| citation-management | 인용/BibTeX 관리 | 참고문헌 정리, BibTeX 생성 |
| peer-review | 논문 심사 평가 | 리뷰어 코멘트 작성/대응 |
| research-grants | 연구비 제안서 | 연구 제안서/과제 신청서 작성 |
| scientific-brainstorming | 연구 아이디어 발상 | 새로운 연구 주제/접근법 탐색 |
| scientific-critical-thinking | 과학적 근거 평가 | 연구 방법론 비판적 분석 |
| hypothesis-generation | 가설 수립/실험 설계 | 가설 도출, 실험 디자인 |
| scholar-evaluation | 학술 업적 평가 | h-index, 인용 분석 |
| scientific-visualization | 출판용 그림 | 저널 투고용 Figure 제작 |
| scientific-schematics | 과학 다이어그램 AI | 실험 흐름도, 메커니즘 도식 |
| scientific-slides | 발표 슬라이드 | 학회 발표 자료 구성 |
| venue-templates | 학술지 LaTeX 템플릿 | Nature, IEEE 등 저널 템플릿 |
| latex-posters | LaTeX 포스터 | 학회 포스터 LaTeX 제작 |
| pptx-posters | 연구 포스터 HTML/PDF | 포스터 HTML/PDF 제작 |
| infographics | 인포그래픽 AI | 정보 시각화 디자인 |
| markdown-mermaid-writing | 마크다운/Mermaid | 문서/다이어그램 작성 |
| paper-2-web | 논문→웹사이트 | 논문을 웹 형태로 변환 |
| pubmed-database | PubMed 논문 검색 | 의학/생명과학 논문 검색 |
| openalex-database | 2.4억 학술문헌 | 대규모 학술 데이터 분석 |

### 4.9 🤖 랩 자동화 (12개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| adaptyv | 클라우드랩 단백질 검증 | 클라우드 랩 단백질 실험 |
| benchling-integration | Benchling R&D | Benchling 플랫폼 연동 |
| ginkgo-cloud-lab | Ginkgo 클라우드랩 | Ginkgo 합성생물학 랩 |
| opentrons-integration | Opentrons 로봇 | 액체 핸들링 로봇 프로토콜 |
| pylabrobot | 랩 자동화 프레임워크 | 범용 랩 자동화 |
| labarchive-integration | 전자실험노트 | LabArchives ELN 연동 |
| lamindb | 생물 데이터 관리 | 실험 데이터 추적/관리 |
| latchbio-integration | 서버리스 생물정보 | Latch 바이오 파이프라인 |
| dnanexus-integration | 클라우드 유전체 | DNAnexus 유전체 분석 |
| omero-integration | 현미경 영상 관리 | OMERO 영상 데이터 관리 |
| protocolsio-integration | 과학 프로토콜 | protocols.io 프로토콜 공유 |
| pyzotero | Zotero 참고문헌 | Zotero 라이브러리 조작 |

### 4.10 🔧 유틸리티 (21개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| docx | Word 문서 처리 | docx 생성/편집 |
| xlsx | Excel 스프레드시트 | xlsx 생성/분석 |
| pdf | PDF 처리/OCR | PDF 생성/추출/병합 |
| pptx | PowerPoint 처리 | pptx 슬라이드 생성/편집 |
| markitdown | 파일→마크다운 | 다양한 파일을 마크다운으로 변환 |
| matlab | MATLAB/Octave | MATLAB 코드 변환/실행 |
| modal | 클라우드 GPU 실행 | GPU 워크로드 클라우드 실행 |
| generate-image | AI 이미지 생성 | 이미지 생성 프롬프트 작성 |
| zarr-python | 청크 N-D 배열 저장 | 대용량 다차원 배열 관리 |

### 4.11 🛠️ 개발 도구 (37개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| aesthetic | UI/UX 미학 디자인 | 디자인 원칙, 색상/레이아웃 |
| backend-development | 백엔드 개발 가이드 | 서버 아키텍처, API 설계 |
| better-auth | 인증/보안 구현 | 로그인, OAuth, JWT |
| code-review | 코드 리뷰 프로세스 | 체계적 코드 리뷰 수행 |
| databases | 데이터베이스 설계/최적화 | DB 스키마, 쿼리 최적화 |
| devops | DevOps CI/CD 파이프라인 | 배포 자동화, Docker, K8s |
| debugging | 체계적 디버깅 방법론 | 버그 추적, 로그 분석 |
| problem-solving | 고급 문제 해결 프레임워크 | 복잡한 기술 문제 분석 |
| frontend-development | 프론트엔드 개발 | React, Vue, 웹 기술 |
| github-ecosystem | GitHub 생태계 활용 | GitHub API, Actions, Pages |
| python-project-skel | Python 프로젝트 스캐폴딩 | 프로젝트 구조 생성 |
| web-frameworks | 웹 프레임워크 가이드 | Flask, Django, FastAPI 비교 |
| webapp-testing | 웹앱 테스팅 | E2E, 유닛, 통합 테스트 |
| common | 공통 유틸리티/API 키 관리 | 공통 패턴, 설정 관리 |

### 4.12 ⚙️ 코어 개발 에이전트 (11개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-api-designer | API 설계 전문가 | REST/GraphQL API 설계 |
| agent-backend-developer | 백엔드 개발 전문가 | 서버 로직, DB 연동 |
| agent-frontend-developer | 프론트엔드 개발 전문가 | UI 구현, 컴포넌트 설계 |
| agent-fullstack-developer | 풀스택 개발 전문가 | 프론트+백엔드 통합 |
| agent-microservices-architect | 마이크로서비스 설계 | 분산 시스템 아키텍처 |
| agent-mobile-developer | 모바일 개발 전문가 | iOS/Android 앱 개발 |
| agent-ui-designer | UI 디자인 전문가 | 와이어프레임, 프로토타입 |
| agent-websocket-engineer | WebSocket 엔지니어 | 실시간 통신 구현 |

### 4.13 📜 언어 전문 에이전트 (23개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-python-pro | Python 전문가 | Python 고급 패턴, 최적화 |
| agent-javascript-pro | JavaScript 전문가 | JS/ES6+ 고급 기법 |
| agent-typescript-pro | TypeScript 전문가 | 타입 시스템, 제네릭 |
| agent-java-architect | Java 아키텍처 | Java 엔터프라이즈 설계 |
| agent-cpp-pro | C++ 전문가 | 시스템/성능 프로그래밍 |
| agent-rust-engineer | Rust 시스템 프로그래밍 | 안전한 시스템 프로그래밍 |
| agent-golang-pro | Go 언어 전문가 | 동시성, 마이크로서비스 |
| agent-react-specialist | React 프론트엔드 | React 컴포넌트, 훅, 상태 관리 |
| agent-nextjs-developer | Next.js 풀스택 | SSR, ISR, App Router |
| agent-django-developer | Django 개발 | Django ORM, DRF |
| agent-spring-boot-engineer | Spring Boot 서버 | Java 웹 서버, JPA |
| agent-sql-pro | SQL 쿼리 전문가 | 복잡한 SQL, 쿼리 최적화 |
| agent-flutter-expert | Flutter 크로스플랫폼 | Dart/Flutter 앱 개발 |
| agent-swift-expert | Swift iOS/macOS | Apple 플랫폼 개발 |
| agent-kotlin-specialist | Kotlin 전문가 | Android, 서버사이드 Kotlin |
| agent-vue-expert | Vue.js 프론트엔드 | Vue 3, Composition API |
| agent-angular-architect | Angular 아키텍처 | Angular 모듈/DI 설계 |
| agent-csharp-developer | C# 개발 전문가 | .NET, Unity 개발 |
| agent-laravel-specialist | Laravel PHP | PHP 웹 프레임워크 |
| agent-php-pro | PHP 전문가 | PHP 8+, 패턴 |
| agent-rails-expert | Ruby on Rails | Rails 웹 개발 |
| agent-dotnet-core-expert | .NET Core 전문가 | 크로스플랫폼 .NET |
| agent-dotnet-framework-4.8-expert | .NET Framework 전문가 | 레거시 .NET |

### 4.14 ☁️ 인프라 에이전트 (12개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-cloud-architect | 클라우드 아키텍처 | AWS/Azure/GCP 설계 |
| agent-kubernetes-specialist | Kubernetes 전문가 | K8s 배포, 헬름 차트 |
| agent-terraform-engineer | Terraform IaC | 인프라 코드화 |
| agent-devops-engineer | DevOps 엔지니어 | CI/CD, 모니터링 |
| agent-sre-engineer | SRE 엔지니어 | 안정성, SLO/SLI |
| agent-security-engineer | 보안 엔지니어 | 인프라 보안, IAM |
| agent-network-engineer | 네트워크 엔지니어 | 네트워크 설계, VPN |
| agent-database-administrator | DB 관리 전문가 | DB 운영, 백업, 복제 |
| agent-deployment-engineer | 배포 엔지니어 | 블루/그린, 카나리 배포 |
| agent-platform-engineer | 플랫폼 엔지니어 | 개발 플랫폼 구축 |
| agent-incident-responder | 인시던트 대응 | 장애 대응 절차 |
| agent-devops-incident-responder | DevOps 인시던트 대응 | DevOps 특화 장애 대응 |

### 4.15 🛡️ 품질/보안 에이전트 (12개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-debugger | 디버깅 전문가 | 체계적 버그 추적 |
| agent-error-detective | 에러 탐지/분석 | 에러 로그 분석, 원인 추적 |
| agent-code-reviewer | 코드 리뷰 전문가 | 심층 코드 리뷰 |
| agent-qa-expert | QA 전문가 | 테스트 전략, 품질 보증 |
| agent-test-automator | 테스트 자동화 | 자동화 테스트 프레임워크 |
| agent-security-auditor | 보안 감사 | 코드 보안 취약점 분석 |
| agent-penetration-tester | 침투 테스트 | 모의 해킹, 취약점 진단 |
| agent-performance-engineer | 성능 엔지니어 | 성능 프로파일링, 최적화 |
| agent-architect-reviewer | 아키텍처 리뷰어 | 설계 리뷰, 기술 부채 분석 |
| agent-chaos-engineer | 카오스 엔지니어링 | 장애 주입 테스트 |
| agent-accessibility-tester | 접근성 테스트 | WCAG, 접근성 검사 |
| agent-compliance-auditor | 컴플라이언스 감사 | 규정 준수 감사 |

### 4.16 🧠 데이터/AI 에이전트 (12개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-data-analyst | 데이터 분석가 | EDA, 시각화, 인사이트 |
| agent-data-scientist | 데이터 사이언티스트 | ML 파이프라인 전체 |
| agent-data-engineer | 데이터 엔지니어 | ETL, 데이터 파이프라인 |
| agent-ai-engineer | AI 엔지니어 | AI 시스템 설계/배포 |
| agent-ml-engineer | ML 엔지니어 (생산) | 프로덕션 ML 시스템 |
| agent-machine-learning-engineer | ML 엔지니어 | ML 모델 개발/훈련 |
| agent-mlops-engineer | MLOps 엔지니어 | ML 파이프라인 운영 |
| agent-nlp-engineer | NLP 전문가 | 자연어 처리 시스템 |
| agent-llm-architect | LLM 아키텍처 | LLM 시스템 설계 |
| agent-prompt-engineer | 프롬프트 엔지니어 | 프롬프트 설계/최적화 |
| agent-database-optimizer | DB 최적화 | 쿼리 최적화, 인덱스 튜닝 |
| agent-postgres-pro | PostgreSQL 전문가 | PostgreSQL 운영/최적화 |

### 4.17 🔧 개발자경험 에이전트 (10개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-refactoring-specialist | 리팩토링 전문가 | 코드 구조 개선 |
| agent-legacy-modernizer | 레거시 현대화 | 레거시 코드 마이그레이션 |
| agent-git-workflow-manager | Git 워크플로 관리 | 브랜치 전략, PR 프로세스 |
| agent-dependency-manager | 의존성 관리 | 패키지 버전 관리 |
| agent-build-engineer | 빌드 엔지니어 | 빌드 시스템 최적화 |
| agent-cli-developer | CLI 도구 개발 | 커맨드라인 도구 제작 |
| agent-documentation-engineer | 문서화 엔지니어 | API 문서, 기술 문서 |
| agent-dx-optimizer | 개발자 경험 최적화 | DX 개선, 도구 선정 |
| agent-mcp-developer | MCP 개발 | Model Context Protocol |
| agent-tooling-engineer | 도구 엔지니어 | 개발 도구 제작/통합 |

### 4.18 🎯 특수 도메인 에이전트 (11개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-blockchain-developer | 블록체인 개발 | 스마트 컨트랙트, Web3 |
| agent-game-developer | 게임 개발 | Unity, Unreal, 게임 로직 |
| agent-iot-engineer | IoT 엔지니어 | 센서, 임베디드 연동 |
| agent-embedded-systems | 임베디드 시스템 | 펌웨어, MCU 프로그래밍 |
| agent-fintech-engineer | 핀테크 엔지니어 | 금융 시스템, 결제 |
| agent-quant-analyst | 퀀트 분석 | 금융 모델링, 알고 트레이딩 |
| agent-risk-manager | 리스크 관리 | 리스크 평가/완화 |
| agent-payment-integration | 결제 시스템 통합 | PG사 연동, 결제 플로우 |
| agent-mobile-app-developer | 모바일 앱 개발 | 네이티브/하이브리드 앱 |
| agent-seo-specialist | SEO 전문가 | 검색 엔진 최적화 |
| agent-api-documenter | API 문서 작성 | OpenAPI/Swagger 문서 |

### 4.19 📊 비즈니스 에이전트 (10개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-product-manager | 프로덕트 매니저 | 제품 로드맵, PRD 작성 |
| agent-project-manager | 프로젝트 매니저 | 프로젝트 관리, 일정 |
| agent-scrum-master | 스크럼 마스터 | 애자일, 스프린트 관리 |
| agent-business-analyst | 비즈니스 분석가 | 요구사항 분석, BRD |
| agent-technical-writer | 테크니컬 라이터 | 사용자 매뉴얼, 가이드 |
| agent-ux-researcher | UX 리서처 | 사용자 연구, 설문 설계 |
| agent-content-marketer | 콘텐츠 마케터 | 마케팅 콘텐츠 전략 |
| agent-sales-engineer | 세일즈 엔지니어 | 기술 영업 지원 |
| agent-customer-success-manager | 고객성공 매니저 | 고객 온보딩, 리텐션 |
| agent-legal-advisor | 법률 자문 | 계약, 규정, 법률 검토 |

### 4.20 🎼 오케스트레이션 에이전트 (8개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-multi-agent-coordinator | 멀티에이전트 조율 | 여러 에이전트 협업 |
| agent-workflow-orchestrator | 워크플로 오케스트레이션 | 복잡한 작업 흐름 관리 |
| agent-task-distributor | 작업 배분 | 작업 분배/우선순위 |
| agent-context-manager | 컨텍스트 관리 | 대화 맥락 유지 |
| agent-knowledge-synthesizer | 지식 통합 | 여러 소스 지식 종합 |
| agent-agent-organizer | 에이전트 조직화 | 에이전트 구성/관리 |
| agent-error-coordinator | 에러 코디네이터 | 에러 수집/분류/대응 |
| agent-performance-monitor | 성능 모니터링 | 시스템 성능 추적 |

### 4.21 🔍 리서치 에이전트 (8개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| agent-research-analyst | 리서치 분석가 | 종합 리서치 수행 |
| agent-data-researcher | 데이터 리서처 | 데이터 소스 탐색 |
| agent-market-researcher | 시장 조사 | 시장 분석, 경쟁사 조사 |
| agent-competitive-analyst | 경쟁사 분석 | 경쟁사 벤치마킹 |
| agent-trend-analyst | 트렌드 분석 | 기술/시장 트렌드 파악 |
| agent-search-specialist | 검색 전문가 | 효율적 정보 검색 전략 |
| agent-datadog-api-expert | Datadog API 전문가 | Datadog 모니터링 API |
| agent-datadog-pro | Datadog 전문가 | Datadog 대시보드/알림 |

### 4.22 📖 개발 가이드 (15개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| guide-python | Python 코딩 표준 | Python 컨벤션, 베스트 프랙티스 |
| guide-git | Git 워크플로 가이드 | Git 브랜치 전략, 명령어 |
| guide-react | React 개발 가이드 | React 패턴, 모범 사례 |
| guide-testing | 테스팅 표준 가이드 | 테스트 작성 가이드라인 |
| guide-documentation | 문서화 표준 가이드 | 코드/프로젝트 문서화 |
| guide-github-actions | GitHub Actions CI/CD | 워크플로 YAML 작성 |
| guide-golang | Go 언어 가이드 | Go 패턴, 관용 표현 |
| guide-mcp-reference | MCP 프로토콜 참조 | MCP 규격 가이드 |
| guide-claude-md | CLAUDE.md 설정 가이드 | Claude 프로젝트 설정 |
| guide-hooks | Claude 훅 시스템 가이드 | Claude 훅 구현 |
| guide-opus-4-5 | Opus 4.5 모델 가이드 | Claude Opus 활용 |
| guide-opus-4-5-agent | Opus 4.5 에이전트 가이드 | Opus 에이전트 구축 |
| guide-opus-migration | Opus 마이그레이션 가이드 | 모델 마이그레이션 |
| guide-hmhco | HMHCO 조직 가이드 | HMHCO 조직 정보 |
| guide-version-discovery | 버전 관리 탐색 | 버전 정보 탐색 |

### 4.23 ⌨️ 커맨드 스킬 (11개)

| 스킬 | 설명 | 언제 사용? |
|------|------|-----------|
| cmd-cr | 코드 리뷰 커맨드 | 자동 코드 리뷰 실행 |
| cmd-cr-fx | 코드 리뷰 수정 커맨드 | 리뷰 결과 자동 수정 |
| cmd-deep-research | 딥 리서치 커맨드 | 심층 리서치 자동화 |
| cmd-explore | 코드베이스 탐색 커맨드 | 프로젝트 구조 분석 |
| cmd-git-cm | Git 커밋 커맨드 | 커밋 메시지 자동 생성 |
| cmd-git-cp | Git 체리픽 커맨드 | 체리픽 자동화 |
| cmd-git-ff | Git 패스트포워드 커맨드 | FF 머지 자동화 |
| cmd-git-fr | Git 프레시 브랜치 커맨드 | 새 브랜치 자동 생성 |
| cmd-git-pr | Git PR 생성 커맨드 | PR 자동 생성 |
| cmd-git-prune | Git 정리 커맨드 | 불필요한 브랜치 정리 |
| cmd-git-sync | Git 동기화 커맨드 | 브랜치 동기화 |

---

## 5. 추천 사용 시나리오

### 5.1 일상적인 코딩 작업

**설정:** 프리셋 "코딩 전문가" + 스타일 "실용적" + Effort 2 + 형식 "코드 중심"
**자동 스킬:** 질문에 따라 agent-python-pro, debugging 등 자동 선택
**예시 질문:** "Flask에서 파일 업로드 API 만들어줘"

### 5.2 버그 수정

**설정:** 프리셋 "코드 수정/디버깅" + 스타일 "디버그" + Effort 3 + 형식 "코드 수정"
**자동 스킬:** agent-debugger, agent-error-detective 자동 부스팅
**예시 질문:** "이 에러 왜 나는지 분석해줘: TypeError: cannot unpack non-iterable NoneType object"

### 5.3 데이터 분석

**설정:** 프리셋 "데이터 분석" + 스타일 "데이터" + CSV 업로드 + Effort 3 + 형식 "분석"
**자동 스킬:** exploratory-data-analysis, matplotlib, statsmodels 등 자동 선택
**예시 질문:** "이 데이터에서 이상치 찾고 시각화해줘"

### 5.4 반도체 공정 분석

**설정:** 프리셋 "반도체 엔지니어" + 스타일 "상세" + CSV 업로드 + Effort 3
**수동 스킬:** pymatgen, statistical-analysis 등 선택
**예시 질문:** "웨이퍼 수율 데이터에서 공정 변수와 불량률의 상관관계 분석"

### 5.5 논문 작성 지원

**설정:** 프리셋 기본 + 스타일 "학술" + Effort 3 + 형식 "보고서"
**수동 스킬:** scientific-writing, literature-review, citation-management
**예시 질문:** "이 실험 결과로 IMRAD 형식 논문 초안 작성해줘"

### 5.6 멀티스킬 조합 (오케스트레이션)

**설정:** 자동 스킬 모드 ON + Effort 3
**예시:**
- "DNA 서열 분석하고 시각화" → biopython + matplotlib 자동 조합
- "이 코드 리뷰하고 테스트 작성" → code-review + agent-test-automator 조합
- "데이터베이스 스키마 설계하고 API 만들어줘" → databases + agent-api-designer + agent-backend-developer

---

## 6. API 엔드포인트 참조

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 메인 웹 페이지 |
| GET | `/api/config` | 환경 설정 + GGUF 상태 |
| GET | `/api/skills` | 전체 스킬 카탈로그 |
| GET | `/api/skill/<name>` | 스킬 상세 정보 |
| GET | `/api/skill/<name>/file` | 스킬 SKILL.md 원문 |
| POST | `/api/skill/<name>/run` | 스킬 스크립트 실행 |
| POST | `/api/auto-skills` | 자동 스킬 추천 (컨텍스트 인식) |
| POST | `/api/chat` | LLM 대화 (메인 채팅) |
| POST | `/api/chat/stop` | 응답 생성 중지 |
| POST | `/api/upload_csv` | CSV/TSV 파일 업로드 |
| POST | `/api/clear_csv` | 업로드된 CSV 초기화 |
| GET | `/api/prompts` | 시스템 프롬프트 목록 |
| GET | `/api/prompts/<id>` | 프롬프트 내용 조회 |
| POST | `/api/prompts` | 사용자 프롬프트 저장 |
| DELETE | `/api/prompts/<id>` | 저장된 프롬프트 삭제 |

---

## 7. 기술 스택 요약

| 구성요소 | 기술 |
|----------|------|
| 백엔드 | Python 3, Flask |
| 프론트엔드 | 순수 HTML/CSS/JS (빌드 도구 없음) |
| LLM 통신 | requests (OpenAI 호환 API) |
| 로컬 모델 | llama-cpp-python (GGUF) |
| 데이터 저장 | localStorage (세션), 파일시스템 (프롬프트) |
| 배포 | 단일 파일, `python app.py` 실행 |
| 포트 | 10009 |

---

*Demos(민중) Alpha 0.8 - SK Hynix 폐쇄망 과학/개발 AI 어시스턴트*
*최종 업데이트: 2026-03-11*
