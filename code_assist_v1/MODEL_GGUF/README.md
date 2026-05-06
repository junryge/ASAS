# MODEL_GGUF/

이 폴더에 `.gguf` 파일을 넣으면 `code_assist_v1` 이 자동으로 인식해 로드합니다.

## 사용법

1. 이 폴더에 GGUF 모델 파일을 복사하거나 이동.
   - 예: `Qwen3.5-9B.Q5_K_M.gguf`, `Qwen3.6-27B-UD-Q4_K_XL.gguf`

2. 비전 모델을 쓰려면 `mmproj-*.gguf` 파일도 같은 폴더에 두면 자동 감지.

3. `python -m code_assist_v1.app_code` 로 기동.

## VRAM 예산

`api_config.json` 의 `gguf.vram_budget_gb` (기본 14GB) 안에서 가장 큰 모델이 자동 로드됩니다.

환경변수로 덮어쓸 수도 있습니다:

```powershell
$env:GGUF_VRAM_BUDGET_GB = "20"
python -m code_assist_v1.app_code
```

## 독립성

이 폴더는 `demos_v1` 또는 루트의 GGUF 파일과 **무관**합니다.
`code_assist_v1` 은 오직 이 폴더 안의 파일만 봅니다.
