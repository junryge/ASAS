# Chapter 5 — 예제 코드

로컬 GGUF 모델을 다뤄보는 학습 도구들.

## 파일

| 파일 | 용도 |
|------|------|
| `gguf_chat.py` | GGUF 자동 감지 + 로드 + CLI 대화 |
| `gguf_bench.py` | 토큰 생성 속도(tok/s) 벤치 — CPU vs GPU 비교 |
| `hybrid_fallback.py` | 사내 API 우선, 실패 시 로컬 GGUF 자동 폴백 |

## 사전 준비

```bash
# CPU 전용
pip install llama-cpp-python requests

# NVIDIA GPU (CUDA) — 훨씬 빠름
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --no-cache-dir
```

`.gguf` 모델 파일을 프로젝트 루트(`scientific-assistant/`) 또는 `models/` 폴더에 넣어둔다.

## 사용

```bash
cd scientific-assistant/docs/examples/ch05

# 1) 로컬 모델과 대화 (자동 감지)
python gguf_chat.py
python gguf_chat.py --model /path/to/Qwen2.5-7B-Q4_K_M.gguf --n-ctx 8192

# 2) 속도 측정 — GPU vs CPU
python gguf_bench.py --model model.gguf --n-gpu-layers 99   # GPU
python gguf_bench.py --model model.gguf --n-gpu-layers 0    # CPU
python gguf_bench.py --model model.gguf --runs 3            # 3회 평균

# 3) 하이브리드 폴백
python hybrid_fallback.py "파이썬 quicksort 짜줘"
python hybrid_fallback.py "파이썬 quicksort 짜줘" --force-local
```

## 메모리 부족(OOM) 대처

| 증상 | 조치 |
|------|------|
| `CUDA out of memory` | `--n-gpu-layers` 를 줄여 부분 오프로딩 (예: 40) |
| 여전히 부족 | `--n-ctx` 축소 (예: 4096), 더 작은 양자화(Q3) |
| GPU 없음 | `--n-gpu-layers 0` (전부 CPU, 느림) |

## 탐색 규칙

- **GGUF** — 프로젝트 루트, `models/`, `model/` 의 `*.gguf` (mmproj 제외)
- **token.txt** (폴백용) — 같은 폴더 우선, 없으면 프로젝트 루트
