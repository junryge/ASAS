# 제5장. 로컬 GGUF 모델로 완전 오프라인 동작시키기

> **이 장의 목표**
> - **GGUF**와 **양자화(Quantization)** 가 무엇인지 한 문단으로 이해한다.
> - `llama-cpp-python` 을 설치하고 첫 모델을 로드한다.
> - 본 프로젝트의 **자동 감지 → 로드 → 풀(pool)** 흐름(`demos_v1/gguf.py`)을 이해한다.
> - **CPU vs GPU** 추론 속도를 직접 측정한다.
> - 사내 LLM이 죽었을 때 **로컬 모델로 자동 폴백**하는 구성을 만든다.

---

## 5.1 왜 로컬 GGUF인가?

지금까지(2~4장)는 사내 LLM 게이트웨이(`http://common.llm.skhynix.com`)를 호출했다. 하지만 다음 상황에서는 **내 PC 안에서 도는 모델**이 필요하다.

| 상황 | 사내 API | 로컬 GGUF |
|------|---------|-----------|
| 인터넷/사내망 단절 | ❌ | ✅ |
| 게이트웨이 점검·과부하 | ❌ | ✅ |
| 극도로 민감한 데이터 | △(망내 전송) | ✅(완전 로컬) |
| 출장·외부 데모 | ❌ | ✅ |
| 비용(호출량 폭증) | 과금/쿼터 | ✅(무료) |

> **핵심** — 사내 API와 로컬 GGUF는 **경쟁이 아니라 보완**이다. 5.8절에서 둘을 자동 폴백으로 묶는다.

---

## 5.2 GGUF & 양자화 — 1분 정리

**GGUF**(GPT-Generated Unified Format)는 llama.cpp 진영의 **단일 파일 모델 포맷**이다. 가중치 + 토크나이저 + 메타데이터가 `.gguf` 파일 하나에 다 들어있어, 별도 설치 없이 파일만 있으면 돌릴 수 있다.

**양자화(Quantization)** 는 모델 가중치를 16비트(FP16)에서 4~8비트 정수로 **압축**해 용량·메모리를 줄이는 기술이다.

| 양자화 태그 | 비트 | 30B 모델 크기 | 품질 | 권장 |
|------------|------|--------------|------|------|
| `Q8_0` | 8bit | ~32 GB | 최상 | GPU 큰 경우 |
| `Q6_K` | 6bit | ~25 GB | 매우 좋음 | 균형 |
| `Q5_K_M` | 5bit | ~21 GB | 좋음 | 균형 |
| **`Q4_K_M`** | 4bit | ~18 GB | 충분히 좋음 | **가장 무난** |
| `Q3_K_M` | 3bit | ~14 GB | 약간 저하 | RAM 부족 시 |
| `Q2_K` | 2bit | ~11 GB | 눈에 띄게 저하 | 최후의 수단 |

> **TIP** — 처음에는 **`Q4_K_M`** 으로 시작하라. 품질/용량 균형이 가장 좋다. 파일명에 `Q4_K_M` 이 포함된 GGUF를 받으면 된다.

### 어디서 받나?
- Hugging Face의 `*-GGUF` 리포지토리 (예: `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF`)
- 사내 모델 저장소(있다면)

받은 `.gguf` 파일을 `scientific-assistant/` 또는 `scientific-assistant/models/` 폴더에 넣으면 끝이다.

---

## 5.3 설치 — `llama-cpp-python`

```bash
# CPU 전용 (가장 간단, GPU 없어도 됨)
pip install llama-cpp-python

# NVIDIA GPU (CUDA) — 훨씬 빠름
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --no-cache-dir

# Apple Silicon (Metal)
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --no-cache-dir
```

> **주의** — GPU 빌드는 CUDA Toolkit이 미리 깔려 있어야 한다(`nvcc --version` 확인). 빌드 실패 시 우선 CPU 버전으로 동작 확인 후 GPU로 넘어가라.

설치 확인:
```bash
python -c "from llama_cpp import Llama; print('llama-cpp-python OK')"
```

---

## 5.4 본 프로젝트의 GGUF 자동 감지 흐름

`app.py` 는 부팅 시 GGUF를 **자동으로 찾아 로드**한다 (`app.py` 95~121줄). 핵심은 `demos_v1/gguf.py` 의 `find_gguf_files()`.

```python
# demos_v1/gguf.py
def find_gguf_files():
    patterns = [
        os.path.join(BASE_DIR, "*.gguf"),            # app.py 옆
        os.path.join(BASE_DIR, "models", "*.gguf"),  # models/ 폴더
        os.path.join(BASE_DIR, "model", "*.gguf"),   # model/ 폴더
    ]
    ...
    # mmproj(비전 프로젝션) 파일은 제외
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
```

부팅 로그 예시:
```
  💻 GGUF 자동 감지! (2개 모델)
     [gguf-0] Qwen2.5-Coder-32B-Q4_K_M.gguf (18.5 GB)
     [gguf-1] Qwen2.5-7B-Q4_K_M.gguf (4.7 GB)
     모델 로딩 중: Qwen2.5-Coder-32B-Q4_K_M.gguf...
     ⚡ Qwen3 가속: flash_attn=True, n_batch=2048
     ✅ 기본 모델 로드 완료: Qwen2.5-Coder-32B-Q4_K_M.gguf
```

| 단계 | 코드 | 의미 |
|------|------|------|
| 검색 | `find_gguf_files()` | 3개 경로에서 `*.gguf` 스캔 |
| 정렬 | `sort(size_gb, reverse=True)` | 큰 모델을 기본으로 |
| 등록 | `ENV_CONFIG["gguf-0"]` | UI 드롭다운에 추가 |
| 로드 | `load_gguf_model()` | 첫(가장 큰) 모델 메모리 적재 |

---

## 5.5 핵심 로딩 옵션 이해

`load_gguf_model(model_path, n_ctx=32768, n_gpu_layers=99, n_batch=2048)`

| 파라미터 | 의미 | 튜닝 가이드 |
|---------|------|------------|
| `n_ctx` | 컨텍스트 길이(토큰) | RAM/VRAM 부족 시 줄임 (예: 8192) |
| `n_gpu_layers` | GPU에 올릴 레이어 수 | `99`=전부 GPU, `0`=전부 CPU, 중간값=하이브리드 |
| `n_batch` | 프롬프트 배치 크기 | 클수록 빠르나 메모리↑ |
| `flash_attn` | 플래시 어텐션 | Qwen3 계열만 자동 활성 |

### GPU 메모리가 부족할 때 (핵심)
`n_gpu_layers` 를 줄여 **일부만 GPU, 나머지는 CPU** 로 돌리는 "오프로딩"이 가능하다.
```python
# 예: 32B 모델을 8GB GPU에서 — 절반만 GPU로
load_gguf_model(path, n_gpu_layers=40)   # 전체 64레이어 중 40개만 GPU
```
느려지지만 **돌긴 돈다.** OOM(Out of Memory)으로 죽는 것보다 낫다.

---

## 5.6 멀티모델 풀 (`_pool_get_or_load`)

병렬 에이전트가 여러 모델을 동시에 쓸 때를 대비해, 본 프로젝트는 **모델 풀**을 운영한다. `api_config.json` 의 `gguf` 블록으로 제어한다.

```json
"gguf": {
  "max_pool_size": 4,      // 동시에 올릴 모델 최대 개수
  "vram_budget_gb": 14     // 풀 전체 VRAM 예산(GB)
}
```

풀의 동작 원리(`demos_v1/gguf.py`):

```
모델 요청
  │
  ├─ 풀에 이미 있음 + 안 쓰는 중 → 즉시 재사용 (reuse)
  ├─ 풀에 있음 + 사용 중 → 최대 120초 대기 후 재사용
  └─ 풀에 없음
        │
        ├─ VRAM 예산 초과? → LRU(가장 오래 안 쓴 모델) 제거 (evict)
        └─ 새로 로드 (load)
```

| 개념 | 의미 |
|------|------|
| **reuse** | 이미 로드된 모델 재활용 — 가장 빠름 |
| **evict (LRU)** | 예산 초과 시 가장 오래 안 쓴 모델 내림 |
| **VRAM budget** | 풀 전체가 넘지 못하는 메모리 상한 |

> **TIP** — GPU가 작으면 `max_pool_size: 1`, `vram_budget_gb` 를 실제 VRAM의 80%로 설정해 OOM을 예방하라.

---

## 5.7 동봉 예제 코드

`docs/examples/ch05/` 에 다음을 두었다.

| 파일 | 용도 |
|------|------|
| `gguf_chat.py` | GGUF 한 개를 로드해 **CLI 대화** (자동 감지 포함) |
| `gguf_bench.py` | **토큰 생성 속도(tok/s) 벤치마크** — CPU vs GPU 비교 |
| `hybrid_fallback.py` | 사내 API 우선, 실패 시 **로컬 GGUF 자동 폴백** |
| `README.md` | 사용법 |

### 5.7.1 `gguf_chat.py`

```bash
cd scientific-assistant/docs/examples/ch05

# 자동 감지 (프로젝트 폴더의 *.gguf 검색)
python gguf_chat.py

# 경로 직접 지정
python gguf_chat.py --model /path/to/Qwen2.5-7B-Q4_K_M.gguf

# CPU 강제 / 컨텍스트 축소
python gguf_chat.py --model ... --n-gpu-layers 0 --n-ctx 8192
```

### 5.7.2 `gguf_bench.py` — 속도 측정

```bash
# GPU 전부
python gguf_bench.py --model model.gguf --n-gpu-layers 99

# CPU 전부 (비교)
python gguf_bench.py --model model.gguf --n-gpu-layers 0

# 출력 예:
#   prompt:   34 tokens
#   gen:     128 tokens in 3.21 s  →  39.9 tok/s
#   load:    4.8 s
```

CPU와 GPU 결과를 나란히 두면 GPU 가속 효과를 정량으로 알 수 있다 (보통 5~30배).

### 5.7.3 `hybrid_fallback.py`

```bash
# 정상: 사내 API 사용
python hybrid_fallback.py "파이썬 quicksort 짜줘"

# 사내 API가 죽은 상황 시뮬레이션 → 로컬 GGUF로 폴백
python hybrid_fallback.py "파이썬 quicksort 짜줘" --force-local
```

흐름:
```
질문 → ① 사내 API 호출 시도
        ├─ 200 OK → 그대로 반환
        └─ 실패(타임아웃/4xx/5xx) → ② 로컬 GGUF 로드 → 응답
```

---

## 5.8 실전 폴백 전략

운영에서 권장하는 3단계 폴백:

```
1순위: 사내 API (빠르고 강력, 정상 시)
   ↓ 실패
2순위: 로컬 GGUF 중형 (Q4_K_M, 품질 유지)
   ↓ 로드 실패(메모리 부족)
3순위: 로컬 GGUF 소형 (Q3_K_M/7B, 최소 품질 보장)
```

`api_config.json` 의 `priority` 필드(3장)와 본 장의 GGUF 풀을 결합하면, 코드 수정 없이 정책으로 표현할 수 있다.

---

## 5.9 자주 발생하는 문제

### `llama-cpp-python 패키지 없음`
→ `pip install llama-cpp-python` (5.3절)

### `CUDA out of memory` / 로드 중 죽음
→ `n_gpu_layers` 를 줄이거나(부분 오프로딩), 더 작은 양자화(Q4→Q3) 사용. `n_ctx` 도 축소.

### 너무 느림 (CPU에서 1 tok/s 미만)
→ ① GPU 빌드로 재설치 ② 더 작은 모델(7B) ③ `n_batch` 상향

### Qwen3가 영어로 "생각"을 길게 출력
→ 본 프로젝트는 `_inject_no_think_for_qwen3()` 로 `/no_think` 를 자동 주입해 막는다. 직접 호출 시에도 system/user 메시지 끝에 `/no_think` 를 붙이면 된다.

### GGUF는 찾았는데 비전이 안 됨
→ 비전 모델은 `*mmproj*.gguf` 프로젝터 파일이 같은 폴더에 있어야 한다. 텍스트 전용이면 무시해도 된다.

---

## 5.10 5장 체크리스트

- [ ] GGUF와 양자화 태그(Q4_K_M 등)의 의미를 안다
- [ ] `llama-cpp-python` 설치 후 `from llama_cpp import Llama` 가 된다
- [ ] `.gguf` 파일을 폴더에 넣고 `app.py` 부팅 로그에서 자동 감지를 확인했다
- [ ] `gguf_chat.py` 로 로컬 모델과 대화해봤다
- [ ] `gguf_bench.py` 로 CPU와 GPU 속도를 각각 측정해 비교했다
- [ ] `hybrid_fallback.py --force-local` 로 폴백 동작을 확인했다
- [ ] `n_gpu_layers` 를 조절해 OOM을 피하는 법을 안다

---

## 5.11 다음 장 예고

**제6장 — 내 문서로 답하게 만들기: RAG 입문**
- RAG(검색 증강 생성)란 무엇인가
- `demos_v1/knowledge.py` 의 지식 검색 구조
- 내 PDF·사내 문서를 임베딩해 색인하기
- 청크(chunk) 분할·검색·재순위(rerank) 전략
- 스킬 vs RAG — 언제 무엇을 쓰나

---

*문서 버전: v1.0 (2026-04-29)*
*브랜치: `claude/create-llm-guide-chapter-one-RDZ12`*
