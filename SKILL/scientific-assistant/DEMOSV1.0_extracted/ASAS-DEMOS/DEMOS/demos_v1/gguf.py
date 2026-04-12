"""
demos_v1/gguf.py - GGUF model management: find, load, chat, multi-model pool
"""
import os
import sys
import time
import glob
import demos_v1.utils as _utils_mod
from demos_v1.utils import BASE_DIR
from demos_v1.config import (
    _gguf_pool, _gguf_pool_lock, MAX_POOL_SIZE, VRAM_BUDGET_GB, TOKEN_SETTINGS
)

# ============================================
# GGUF 모델 관리 (llama-cpp-python)
# ============================================
def find_gguf_files():
    """app.py 주변에서 GGUF 파일 검색"""
    patterns = [
        os.path.join(BASE_DIR, "*.gguf"),
        os.path.join(BASE_DIR, "models", "*.gguf"),
        os.path.join(BASE_DIR, "model", "*.gguf"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    # mmproj(비전 프로젝션) 파일은 LLM이 아니므로 제외
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    return [{"path": f, "name": os.path.basename(f), "size_gb": round(os.path.getsize(f) / 1e9, 1)} for f in files]


def load_gguf_model(model_path, n_ctx=32768, n_gpu_layers=99, n_batch=128):
    """llama-cpp-python으로 GGUF 모델 로드 (이미 같은 모델이면 스킵)"""
    # 이미 같은 모델이 로드되어 있으면 스킵
    if _utils_mod.gguf_loaded_path == model_path and _utils_mod.gguf_model is not None:
        print(f"     ℹ️  이미 로드됨: {os.path.basename(model_path)}")
        return True

    try:
        from llama_cpp import Llama
        print(f"     모델 로딩 중: {os.path.basename(model_path)}...")

        # 기존 모델 해제
        if _utils_mod.gguf_model is not None:
            print(f"     🔄 기존 모델 해제: {os.path.basename(_utils_mod.gguf_loaded_path or '')}")
            _utils_mod.gguf_model = None
            _utils_mod.gguf_loaded_path = None

        # Windows: llama.cpp C 라이브러리가 stdout/stderr 핸들을 건드려서
        # Flask(click/colorama) 콘솔 출력이 깨지는 문제 방지
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr
        try:
            # 일부 환경에서 n_batch를 크게 잡으면 디코드 실패가 증가해 보수적으로 설정
            try:
                _utils_mod.gguf_model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                    n_batch=n_batch,
                    verbose=False,
                )
            except TypeError:
                # 구버전 llama-cpp-python 호환
                _utils_mod.gguf_model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                    verbose=False,
                )
        finally:
            # 핸들 복원
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr

        _utils_mod.gguf_loaded_path = model_path
        return True
    except ImportError:
        print(f"     ❌ llama-cpp-python 패키지 없음")
        print(f"        → pip install llama-cpp-python")
        return False
    except Exception as e:
        print(f"     ❌ 모델 로드 실패: {e}")
        return False


def gguf_chat(messages, temperature=0.5, max_tokens=4096, stop_flag=None):
    """로드된 GGUF 모델로 채팅 (스트리밍으로 중단 가능)"""
    if _utils_mod.gguf_model is None:
        return None, "GGUF 모델이 로드되지 않았습니다."
    try:
        # 중단 플래그가 있으면 스트리밍 모드로 토큰별 체크
        if stop_flag is not None:
            chunks = []
            for chunk in _utils_mod.gguf_model.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            ):
                if stop_flag.get("stop", False):
                    # 중단 요청 → 지금까지 생성된 부분 반환
                    partial = "".join(chunks)
                    return (partial + "\n\n⏹️ (응답이 중단되었습니다)") if partial else None, None
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    chunks.append(content)
            return "".join(chunks), None
        else:
            resp = _utils_mod.gguf_model.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if resp and "choices" in resp and len(resp["choices"]) > 0:
                return resp["choices"][0].get("message", {}).get("content") or "", None
            return None, f"예상치 못한 응답: {resp}"
    except Exception as e:
        return None, f"GGUF 추론 오류: {str(e)}"


# ============================================
# GGUF 멀티모델 풀 (병렬 에이전트용)
# ============================================
def _pool_get_or_load(model_path, n_ctx=16384):
    """풀에서 GGUF 모델 인스턴스를 가져오거나 새로 로드.
    Thread-safe: 각 스레드가 독립 Llama 인스턴스를 받음.
    """
    from llama_cpp import Llama

    size_gb = round(os.path.getsize(model_path) / 1e9, 1) if os.path.exists(model_path) else 0

    def _safe_print(msg):
        """Windows cp949 환경에서도 안전하게 출력 (이모지 등 유니코드 대응)."""
        try:
            print(msg)
        except (UnicodeEncodeError, OSError):
            try:
                print(msg.encode("utf-8", errors="replace").decode("ascii", errors="replace"))
            except Exception:
                pass

    with _gguf_pool_lock:
        # 1) 이미 풀에 같은 path가 있으면 재사용 (n_ctx 다르더라도)
        _wait_entry = None
        for entry in _gguf_pool:
            if entry["path"] == model_path and entry["model"] is not None:
                if not entry["in_use"]:
                    entry["in_use"] = True
                    entry["last_used"] = time.time()
                    _safe_print(f"     [POOL] reuse: {os.path.basename(model_path)} (ctx={entry['n_ctx']})")
                    return entry["model"]
                else:
                    # 같은 모델이 사용 중 → 대기 후 재시도 (합성 단계 등)
                    _safe_print(f"     [POOL] waiting for: {os.path.basename(model_path)}...")
                    _wait_entry = entry
                    break

    # 락 밖에서 대기 (최대 120초)
    if _wait_entry is not None:
        for _ in range(240):
            time.sleep(0.5)
            with _gguf_pool_lock:
                if not _wait_entry["in_use"]:
                    _wait_entry["in_use"] = True
                    _wait_entry["last_used"] = time.time()
                    _safe_print(f"     [POOL] reuse after wait: {os.path.basename(model_path)}")
                    return _wait_entry["model"]
        # 타임아웃 → 새 인스턴스를 로드 (비 thread-safe 객체 공유 방지)
        _safe_print(f"     [POOL] timeout, loading NEW instance: {os.path.basename(model_path)}")
        try:
            llama_new = Llama(
                model_path=model_path, n_ctx=n_ctx,
                n_gpu_layers=99, n_batch=128, verbose=False,
            )
        except TypeError:
            llama_new = Llama(
                model_path=model_path, n_ctx=n_ctx,
                n_gpu_layers=99, verbose=False,
            )
        new_entry = {
            "model": llama_new, "path": model_path, "size_gb": size_gb,
            "n_ctx": n_ctx, "in_use": True, "last_used": time.time(),
        }
        with _gguf_pool_lock:
            _gguf_pool.append(new_entry)
        return llama_new

    with _gguf_pool_lock:

        # 2) VRAM 예산 확인 → 초과 시 LRU 제거
        current_vram = sum(e["size_gb"] for e in _gguf_pool)
        while (current_vram + size_gb > VRAM_BUDGET_GB or len(_gguf_pool) >= MAX_POOL_SIZE):
            # 사용 중 아닌 것 중 가장 오래된 것 제거
            idle = [e for e in _gguf_pool if not e["in_use"]]
            if not idle:
                break  # 모두 사용 중이면 어쩔 수 없음
            lru = min(idle, key=lambda e: e["last_used"])
            _safe_print(f"     [POOL] evict LRU: {os.path.basename(lru['path'])} ({lru['size_gb']}GB)")
            _gguf_pool.remove(lru)
            try:
                del lru["model"]
            except Exception:
                pass
            current_vram = sum(e["size_gb"] for e in _gguf_pool)

        # 자리 확보 완료, 풀에 placeholder 등록 (로딩 중 표시)
        placeholder = {
            "model": None, "path": model_path, "size_gb": size_gb,
            "n_ctx": n_ctx, "in_use": True, "last_used": time.time(),
        }
        _gguf_pool.append(placeholder)

    # 3) 락 밖에서 모델 로드 (느리지만 다른 스레드 블록 안 함)
    _safe_print(f"     [POOL] loading: {os.path.basename(model_path)} (ctx={n_ctx})...")
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    try:
        try:
            llama = Llama(
                model_path=model_path, n_ctx=n_ctx,
                n_gpu_layers=99, n_batch=128, verbose=False,
            )
        except TypeError:
            llama = Llama(
                model_path=model_path, n_ctx=n_ctx,
                n_gpu_layers=99, verbose=False,
            )
    except Exception as _load_err:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        # 로드 실패 → placeholder 제거 (풀 오염 방지)
        with _gguf_pool_lock:
            if placeholder in _gguf_pool:
                _gguf_pool.remove(placeholder)
        _safe_print(f"     [POOL] load FAILED: {os.path.basename(model_path)} -> {_load_err}")
        raise
    finally:
        sys.stdout, sys.stderr = saved_stdout, saved_stderr

    with _gguf_pool_lock:
        placeholder["model"] = llama
    _safe_print(f"     [POOL] loaded: {os.path.basename(model_path)} ({size_gb}GB, ctx={n_ctx})")
    return llama


def _pool_release(model_path):
    """모델 사용 완료 표시."""
    with _gguf_pool_lock:
        for entry in _gguf_pool:
            if entry["path"] == model_path and entry["in_use"]:
                entry["in_use"] = False
                entry["last_used"] = time.time()
                return


def _pool_status():
    """현재 풀 상태 반환 (디버그용)."""
    with _gguf_pool_lock:
        return [{
            "model": os.path.basename(e["path"]),
            "size_gb": e["size_gb"],
            "n_ctx": e["n_ctx"],
            "in_use": e["in_use"],
        } for e in _gguf_pool]


