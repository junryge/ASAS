"""
code_assist_v1/gguf_loader.py - 자체 GGUF 로딩 (demos_v1 와 독립)

- code_assist_v1/MODEL_GGUF/ 폴더에서만 .gguf 인식.
- llama-cpp-python 직접 호출.
- mmproj 비전 자동 감지, Qwen3 flash_attn 가속.
"""
from __future__ import annotations
import glob
import os
import sys

import code_assist_v1.utils as _u
from code_assist_v1.models import (
    GGUF_DEFAULT_N_CTX,
    GGUF_DEFAULT_N_GPU_LAYERS,
    GGUF_DEFAULT_N_BATCH,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _gguf_dir() -> str:
    """code_assist_v1/MODEL_GGUF 의 절대 경로."""
    from code_assist_v1.models import GGUF_MODEL_DIR_NAME
    return os.path.join(_THIS_DIR, GGUF_MODEL_DIR_NAME)


def find_gguf_files() -> list[dict]:
    """code_assist_v1/MODEL_GGUF/*.gguf 만 검색 (mmproj 제외)."""
    d = _gguf_dir()
    if not os.path.isdir(d):
        return []
    files = glob.glob(os.path.join(d, "*.gguf"))
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    return [
        {"path": f, "name": os.path.basename(f), "size_gb": round(os.path.getsize(f) / 1e9, 1)}
        for f in files
    ]


def _find_mmproj_file(model_path: str) -> str | None:
    """모델과 같은 폴더에서 mmproj 자동 탐색."""
    model_dir = os.path.dirname(model_path)
    for p in glob.glob(os.path.join(model_dir, "*mmproj*.gguf")):
        return p
    # MODEL_GGUF 폴더에서도 탐색
    for p in glob.glob(os.path.join(_gguf_dir(), "*mmproj*.gguf")):
        return p
    return None


def load_gguf_model(
    model_path: str,
    n_ctx: int = GGUF_DEFAULT_N_CTX,
    n_gpu_layers: int = GGUF_DEFAULT_N_GPU_LAYERS,
    n_batch: int = GGUF_DEFAULT_N_BATCH,
) -> bool:
    """llama-cpp-python 으로 GGUF 모델 로드.

    같은 모델 + 충분한 ctx 면 스킵, 부족하면 재로드.
    mmproj 파일이 있으면 비전(멀티모달) 모드.
    Qwen3 시리즈는 flash_attn 가속.
    """
    if _u.gguf_loaded_path == model_path and _u.gguf_model is not None:
        try:
            _cur_ctx_attr = getattr(_u.gguf_model, "n_ctx", None)
            _cur_ctx = _cur_ctx_attr() if callable(_cur_ctx_attr) else (_cur_ctx_attr if _cur_ctx_attr else 0)
        except Exception:
            _cur_ctx = 0
        if _cur_ctx >= n_ctx:
            print(f"     ℹ️  이미 로드됨: {os.path.basename(model_path)} (ctx={_cur_ctx})")
            return True
        print(f"     🔄 ctx 부족 ({_cur_ctx} < {n_ctx}) → 재로드")

    try:
        from llama_cpp import Llama
    except ImportError:
        print(f"     ❌ llama-cpp-python 패키지 없음 — pip install llama-cpp-python")
        return False

    print(f"     모델 로딩 중: {os.path.basename(model_path)}...")

    if _u.gguf_model is not None:
        print(f"     🔄 기존 모델 해제: {os.path.basename(_u.gguf_loaded_path or '')}")
        _u.gguf_model = None
        _u.gguf_loaded_path = None

    mmproj_path = _find_mmproj_file(model_path)
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    try:
        base_kwargs = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            "n_batch": n_batch,
            "verbose": False,
        }

        if mmproj_path:
            # 비전 모드 (clip_model_path → ChatHandler 폴백)
            try:
                _u.gguf_model = Llama(**base_kwargs, clip_model_path=mmproj_path)
                print(f"     👁️ 비전 모드 (clip_model_path): {os.path.basename(mmproj_path)}")
            except (TypeError, Exception):
                _handlers = []
                try:
                    from llama_cpp.llama_chat_format import Gemma3ChatHandler
                    _handlers.append(("Gemma3", Gemma3ChatHandler))
                except ImportError:
                    pass
                try:
                    from llama_cpp.llama_chat_format import Llava16ChatHandler
                    _handlers.append(("Llava16", Llava16ChatHandler))
                except ImportError:
                    pass
                try:
                    from llama_cpp.llama_chat_format import Llava15ChatHandler
                    _handlers.append(("Llava15", Llava15ChatHandler))
                except ImportError:
                    pass
                loaded = False
                for hname, HCls in _handlers:
                    try:
                        _u.gguf_model = Llama(**base_kwargs, chat_handler=HCls(clip_model_path=mmproj_path))
                        print(f"     👁️ 비전 모드 ({hname}): {os.path.basename(mmproj_path)}")
                        loaded = True
                        break
                    except Exception:
                        continue
                if not loaded:
                    print(f"     ⚠️ 비전 로드 실패 → 텍스트 전용")
                    _u.gguf_model = Llama(**base_kwargs)
        else:
            # 텍스트 전용 (Qwen3 시리즈는 flash_attn)
            is_qwen3 = "qwen3" in os.path.basename(model_path).lower()
            if is_qwen3:
                try:
                    _u.gguf_model = Llama(**base_kwargs, flash_attn=True)
                    print(f"     ⚡ Qwen3 가속: flash_attn=True, n_batch={n_batch}")
                except TypeError:
                    try:
                        _u.gguf_model = Llama(**base_kwargs)
                        print(f"     ℹ️  flash_attn 미지원 (구버전)")
                    except TypeError:
                        del base_kwargs["n_batch"]
                        _u.gguf_model = Llama(**base_kwargs)
            else:
                try:
                    _u.gguf_model = Llama(**base_kwargs)
                except TypeError:
                    del base_kwargs["n_batch"]
                    _u.gguf_model = Llama(**base_kwargs)
    except Exception as e:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        print(f"     ❌ 모델 로드 실패: {e}")
        return False
    finally:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr

    _u.gguf_loaded_path = model_path
    return True


def gguf_chat_stream(messages: list[dict], temperature: float = 0.5, max_tokens: int = 4096):
    """로드된 GGUF 로 채팅 스트리밍. yield 토큰 텍스트."""
    if _u.gguf_model is None:
        raise RuntimeError("GGUF 모델이 로드되지 않았습니다")
    for chunk in _u.gguf_model.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    ):
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content") or ""
        if content:
            yield content
