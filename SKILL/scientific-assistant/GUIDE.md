# Demos 데모스 프로젝트 베타 V0.2 — 사용자 가이드

## 개요

Demos(데모스)는 174개 과학 스킬을 활용하는 LLM 웹 어시스턴트입니다.
회사 내부 LLM API(DEV/PROD/COMMON) 또는 로컬 GGUF 모델에 연결하여,
선택한 과학 스킬(SKILL.md)을 시스템 프롬프트로 자동 주입해 전문적인 답변을 생성합니다.

---

## 1. 폴더 구조

```
scientific-assistant/
├── app.py                  ← 메인 Flask 앱 (단일 파일)
├── TOKEN.TXT               ← API 키 (한 줄, ASCII)
├── GUIDE.md                ← 이 파일
├── scientific-skills/      ← 174개 스킬 폴더
│   ├── biopython/
│   │   └── SKILL.md
│   ├── rdkit/
│   │   └── SKILL.md
│   ├── scanpy/
│   │   └── SKILL.md
│   └── ... (나머지 171개)
└── models/                 ← (선택) GGUF 모델 파일 위치
    └── Qwen3-8B-Q6_K.gguf
```

---

## 2. 설치 및 실행

### 2.1 필수 요구사항

- Python 3.8 이상
- Flask, requests 패키지

```bash
pip install flask requests
```

> 폐쇄망 환경이면 인터넷이 되는 PC에서 `pip download flask requests`로 받아 복사 후 `pip install --no-index --find-links=. flask requests`

### 2.2 TOKEN.TXT 설정

app.py와 같은 폴더에 `TOKEN.TXT` 파일을 만들고, 회사 API 키를 한 줄로 넣으세요.

```
eyJhbGciOiJIUzI1NiIs...실제API키...
```

> TOKEN.TXT에 한글이 포함되면 무시됩니다. 반드시 영문/숫자만 사용하세요.
> LOCAL GGUF 모드만 사용할 경우 TOKEN.TXT는 비워둬도 됩니다.

### 2.3 실행

```bash
cd scientific-assistant
python app.py
```

실행 시 콘솔에 다음이 표시됩니다:

```
==================================================
  Demos 데모스 프로젝트 베타 V0.2
==================================================
  📂 스킬 폴더: .../scientific-skills
  ✅ 발견된 스킬: 174개
  🔑 TOKEN.TXT: 로드됨 (42자)

  💻 GGUF 자동 감지!
     모델: Qwen3-8B-Q6_K.gguf (5.2 GB)
     모델 로딩 중: Qwen3-8B-Q6_K.gguf...
     ✅ GGUF 모델 로드 완료!

  🖥️  사용 가능한 LLM 환경:
     [dev] DEV (30B) → http://dev.assistant.llm.skhynix.com/...
     [prod] PROD (80B) → http://summary.llm.skhynix.com/...
     [common] COMMON (20B) → http://common.llm.skhynix.com/...
     [gguf-local] LOCAL GGUF (Qwen3-8B-Q6_K.gguf) → python://llama-cpp-python

  🌐 http://localhost:10009 에서 접속하세요
==================================================
```

> GGUF 파일이나 llama-server가 없으면 LOCAL GGUF는 자동으로 비활성화됩니다.

브라우저에서 **http://localhost:10009** 접속하면 웹 UI가 나타납니다.

---

## 3. 웹 UI 사용법

### 3.1 LLM 환경 선택

화면 상단에 4개 환경 버튼이 나타납니다. 클릭하여 선택하세요.

| 환경 | 모델 | 설명 |
|------|------|------|
| 🧪 DEV (30B) | Qwen3-Coder-30B-A3B-Instruct | 개발용 서버 |
| 🚀 PROD (80B) | Qwen3-Next-80B-A3B-Instruct | 운영 서버 (고품질) |
| 🌐 COMMON (20B) | gpt-oss-20b | 공용 서버 (빠름) |
| 💻 LOCAL GGUF | local-gguf | 로컬 GGUF 모델 |

### 3.2 LOCAL GGUF (자동 감지)

GGUF는 앱 시작 시 **Python(llama-cpp-python)으로 자동 로드**됩니다. llama-server 같은 외부 실행 파일이 필요 없습니다!

**자동 실행 조건**:
1. `.gguf` 파일이 app.py 폴더, `models/`, 또는 `model/` 안에 존재
2. `llama-cpp-python` 패키지 설치됨

```bash
pip install llama-cpp-python
```

> GPU 사용 시: `CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python`

조건 충족 시 `python app.py` 실행하면 자동으로 모델이 메모리에 로드되고,
웹 UI 환경 선택에 "💻 LOCAL GGUF" 버튼이 나타납니다.

조건 미충족 시 LOCAL GGUF 옵션은 아예 표시되지 않습니다.

### 3.3 분야/스킬 선택

10개 분야 태그 중 원하는 분야를 클릭하면 해당 스킬 카드가 나타납니다.

| 분야 | 스킬 수 | 예시 |
|------|---------|------|
| 🧬 생물정보학 | 22개 | biopython, scanpy, esm |
| 🗄️ 생물 DB | 22개 | uniprot, KEGG, AlphaFold |
| ⚗️ 화학/신약 | 21개 | rdkit, deepchem, diffdock |
| ⚛️ 재료/물리/양자 | 8개 | pymatgen, qiskit, cirq |
| 📊 데이터/ML | 26개 | scikit-learn, pytorch, polars |
| 💰 금융/경제 | 8개 | FRED, edgar, USPTO |
| 🏥 임상/의학 | 13개 | pydicom, pathml, ClinicalTrials |
| 📝 논문/연구 | 20개 | scientific-writing, PubMed |
| 🤖 랩 자동화 | 12개 | opentrons, benchling, lamindb |
| 🔧 유틸리티 | 21개 | docx, xlsx, pdf, pptx |

- ✅ 표시: SKILL.md 파일이 있어 사용 가능
- ❌ 표시: 폴더가 없어 사용 불가 (해당 스킬 폴더를 추가하면 자동 인식)

**여러 스킬을 동시에 선택**할 수 있습니다. 선택한 스킬의 SKILL.md 내용이 시스템 프롬프트에 주입됩니다.

### 3.4 응답 수준

슬라이더로 4단계 조절:

| 단계 | 이름 | 설명 | Temperature |
|------|------|------|-------------|
| 0 | 즉시 | 핵심만 간결하게 | 0.1 |
| 1 | 빠름 | 간결한 답변 | 0.3 |
| 2 | 표준 | 표준 깊이 (기본값) | 0.5 |
| 3 | 프로 | 상세 분석 + 주석 | 0.7 |

### 3.5 출력 형식

4가지 형식 중 선택:

- 💻 **코드**: Python 코드 중심
- 📄 **보고서**: 보고서 형식
- 📊 **표**: 표 활용
- 📝 **단계별**: Step-by-step

### 3.6 채팅

- 텍스트 입력 후 **Enter** 전송
- **Shift+Enter** 줄바꿈
- 빠른 프롬프트 버튼: 데이터 분석, 코드 작성, 시각화, 논문 정리

---

## 4. 스킬 작동 원리

스킬은 단순한 마크다운 텍스트 파일(SKILL.md)입니다.

채팅 시 선택된 스킬의 내용이 LLM API의 **시스템 프롬프트**에 자동 삽입됩니다:

```
[시스템 프롬프트]
당신은 Demos(데모스) - 과학 연구를 돕는 전문 AI 어시스턴트입니다.

=== SKILL: rdkit ===
(rdkit SKILL.md 전체 내용)

=== SKILL: deepchem ===
(deepchem SKILL.md 전체 내용)

[로드된 스킬: rdkit, deepchem]
표준적인 깊이로 설명하세요.
답변을 Python 코드 중심으로 작성하세요.
```

이 시스템 프롬프트 + 사용자 메시지가 회사 API로 전달되고, 응답이 웹에 표시됩니다.

---

## 5. 스킬 추가/수정

### 새 스킬 추가

```bash
mkdir scientific-skills/my-new-skill
```

`scientific-skills/my-new-skill/SKILL.md` 파일을 만들고 내용을 작성하세요.
서버 재시작 없이, 다음 요청부터 자동 인식됩니다.

### SKILL.md 작성 팁

```markdown
# 스킬 이름

## 역할
이 스킬이 활성화되면 당신은 ○○ 전문가입니다.

## 핵심 지식
- 라이브러리 사용법
- 주요 함수/클래스
- 코드 패턴

## 응답 규칙
- Python 코드 예시를 반드시 포함
- 한글로 주석 작성
```

---

## 6. API 설정 변경

app.py 상단의 `ENV_CONFIG`를 수정하여 API 엔드포인트를 변경할 수 있습니다:

```python
ENV_CONFIG = {
    "dev": {
        "url": "http://dev.assistant.llm.skhynix.com/v1/chat/completions",
        "model": "Qwen3-Coder-30B-A3B-Instruct",
        "name": "DEV (30B)"
    },
    # ... 필요에 따라 추가/수정
}
```

---

## 7. 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| TOKEN.TXT 에러 | 한글/특수문자 포함 | ASCII 문자만 사용 |
| API 연결 실패 | 서버 주소 오류 / 네트워크 | URL 확인, 방화벽 확인 |
| GGUF 모델 로드 안됨 | llama-cpp-python 없음 | `pip install llama-cpp-python` |
| 스킬이 ❌ 표시 | SKILL.md 파일 없음 | scientific-skills/폴더명/SKILL.md 생성 |
| 포트 충돌 | 10009 포트 사용중 | app.py 맨 아래 port=10009 변경 |
| latin-1 인코딩 에러 | TOKEN.TXT에 비ASCII | TOKEN.TXT를 영문 API 키로 교체 |

---

## 8. 기술 사양

- **서버**: Flask (Python), 포트 10009
- **프론트엔드**: 단일 HTML 인라인 (외부 의존성 없음)
- **API 형식**: OpenAI-compatible Chat Completions
- **스킬 수**: 174개 (10개 분야)
- **GGUF 지원**: llama.cpp 서버 내장 관리
- **인증서**: verify=False (폐쇄망 대응)
- **타임아웃**: 120초

---

*Demos 데모스 프로젝트 베타 V0.2*
