"""
foundry_server.py - 자율 제조 공장 v6.3 독립 실행 서버
의존성 없이 단일 파일로 작동. demos_v1 패키지 불필요.

실행:  python foundry_server.py
브라우저:  http://localhost:5001/foundry

필요 패키지:
  pip install flask llama-cpp-python
"""
import os
import sys
import gc
import glob
import time
import threading
import traceback

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("[!] Flask가 설치되지 않았습니다. 다음 명령으로 설치하세요:")
    print("    pip install flask")
    sys.exit(1)


# ============================================================
# 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VRAM_BUDGET_GB = 22         # RTX 3090 24GB 중 22GB 사용 (여유 2GB)
MAX_POOL_SIZE = 4           # 풀에 동시 보관 가능한 모델 수
DEFAULT_N_CTX = 16384       # GGUF 컨텍스트 길이
DEFAULT_PORT = 5001         # 메인 app과 충돌 안 나게 다른 포트

# ============================================================
# 전역 상태
# ============================================================
gguf_model = None
gguf_loaded_path = None
_gguf_pool = []
_gguf_pool_lock = threading.Lock()


# ============================================================
# GGUF 헬퍼
# ============================================================
def find_gguf_files():
    """BASE_DIR / models / model 폴더에서 GGUF 파일 검색 (mmproj 제외)."""
    patterns = [
        os.path.join(BASE_DIR, "*.gguf"),
        os.path.join(BASE_DIR, "models", "*.gguf"),
        os.path.join(BASE_DIR, "model", "*.gguf"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    files = sorted(set(files))
    return [
        {
            "path": f,
            "name": os.path.basename(f),
            "size_gb": round(os.path.getsize(f) / 1e9, 1),
            "folder": os.path.dirname(f),
        }
        for f in files
    ]


def load_gguf_model(model_path, n_ctx=DEFAULT_N_CTX, n_gpu_layers=99, n_batch=2048):
    """llama-cpp-python으로 GGUF 로드. 이미 같은 모델 있으면 스킵."""
    global gguf_model, gguf_loaded_path

    if gguf_loaded_path == model_path and gguf_model is not None:
        print(f"[GGUF] 이미 로드됨: {os.path.basename(model_path)}")
        return True

    try:
        from llama_cpp import Llama
    except ImportError:
        raise RuntimeError("llama-cpp-python이 설치되지 않았습니다. pip install llama-cpp-python")

    # 기존 모델 해제
    if gguf_model is not None:
        print(f"[GGUF] 기존 해제: {os.path.basename(gguf_loaded_path or '')}")
        gguf_model = None
        gguf_loaded_path = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    print(f"[GGUF] 로딩 중: {os.path.basename(model_path)} (ctx={n_ctx})")
    t0 = time.time()
    try:
        llama = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_batch=n_batch,
            verbose=False,
        )
    except TypeError:
        # 구버전 llama-cpp 호환
        llama = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    gguf_model = llama
    gguf_loaded_path = model_path

    # 풀에도 등록
    size_gb = round(os.path.getsize(model_path) / 1e9, 1)
    with _gguf_pool_lock:
        # 기존 같은 path 항목 제거
        _gguf_pool[:] = [e for e in _gguf_pool if e.get("path") != model_path]
        _gguf_pool.append({
            "model": llama,
            "path": model_path,
            "size_gb": size_gb,
            "n_ctx": n_ctx,
            "in_use": False,
            "last_used": time.time(),
        })

    elapsed = time.time() - t0
    print(f"[GGUF] 로드 완료: {os.path.basename(model_path)} ({size_gb}GB, {elapsed:.1f}초)")
    return True


def unload_gguf():
    """현재 로드된 모델 + 풀에서 idle 모두 언로드."""
    global gguf_model, gguf_loaded_path
    prev = gguf_loaded_path
    gguf_model = None
    gguf_loaded_path = None
    with _gguf_pool_lock:
        idle = [e for e in _gguf_pool if not e.get("in_use")]
        for e in idle:
            _gguf_pool.remove(e)
            try:
                del e["model"]
            except Exception:
                pass
        removed = len(idle)
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("[GGUF] torch.cuda.empty_cache() 호출")
    except Exception:
        pass
    print(f"[GGUF] 언로드 완료: {os.path.basename(prev) if prev else '(없음)'} · 풀에서 {removed}개 제거")
    return prev, removed


def pool_status():
    """현재 풀 상태."""
    with _gguf_pool_lock:
        return [
            {
                "model": os.path.basename(e["path"]),
                "size_gb": e["size_gb"],
                "n_ctx": e["n_ctx"],
                "in_use": e["in_use"],
                "last_used": e.get("last_used"),
            }
            for e in _gguf_pool
        ]


# ============================================================
# Flask 앱
# ============================================================
app = Flask(__name__)

# 5대 요소 라우트 등록 (backend/routes_elements.py).
# 등록 실패해도 GGUF 단독 경로는 동작하도록 try/except.
try:
    from backend.routes_elements import register as register_elements
    register_elements(app)
    print("[BOOT] backend/routes_elements 등록 완료 (/api/elements/*)")
except Exception as _e:
    print(f"[BOOT][WARN] backend/routes_elements 등록 실패: {_e}")


# CORS - file:// 또는 다른 포트에서 열어도 작동하게
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["GET"])
@app.route("/foundry", methods=["GET"])
def foundry_page():
    """foundry_v1.html 서빙."""
    path = os.path.join(BASE_DIR, "foundry_v1.html")
    if not os.path.exists(path):
        return f"foundry_v1.html을 찾을 수 없습니다: {path}", 404
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/gguf/list", methods=["GET"])
def api_gguf_list():
    files = find_gguf_files()
    return jsonify({
        "files": files,
        "count": len(files),
        "vram_budget_gb": VRAM_BUDGET_GB,
        "base_dir": BASE_DIR,
    })


@app.route("/api/gguf-pool-status", methods=["GET"])
def api_pool_status():
    """단일 모델 상태 반환. 'pool' 키는 UI 호환용 (최대 1개 항목)."""
    pool = pool_status()
    single = pool[:1]  # 단일 운영 — 첫 항목만
    return jsonify({
        "pool": single,
        "max_pool_size": 1,
        "vram_budget_gb": VRAM_BUDGET_GB,
        "loaded": os.path.basename(gguf_loaded_path) if gguf_loaded_path else None,
    })


@app.route("/api/gguf/load", methods=["POST"])
def api_gguf_load():
    data = request.json or {}
    path = data.get("path")
    n_ctx = int(data.get("n_ctx", DEFAULT_N_CTX))
    if not path:
        return jsonify({"ok": False, "error": "path 필수"}), 400
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": f"파일 없음: {path}"}), 404
    try:
        ok = load_gguf_model(path, n_ctx=n_ctx)
        size_gb = round(os.path.getsize(path) / 1e9, 1)
        pool = pool_status()
        vram_used = sum(e.get("size_gb", 0) for e in pool)
        return jsonify({
            "ok": bool(ok),
            "loaded": os.path.basename(path),
            "path": path,
            "size_gb": size_gb,
            "n_ctx": n_ctx,
            "vram_used_gb": vram_used,
            "vram_budget_gb": VRAM_BUDGET_GB,
            "pool": pool,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e), "type": type(e).__name__}), 500


@app.route("/api/gguf/unload", methods=["POST"])
def api_gguf_unload():
    prev, removed = unload_gguf()
    return jsonify({
        "ok": True,
        "unloaded": os.path.basename(prev) if prev else None,
        "removed_from_pool": removed,
        "pool": pool_status(),
    })


@app.route("/api/gguf/chat", methods=["POST"])
def api_gguf_chat():
    """로드된 GGUF로 단일 추론 (4대 요소 순차 호출용)."""
    global gguf_model
    if gguf_model is None:
        return jsonify({"ok": False, "error": "모델이 로드되지 않았습니다. 먼저 /api/gguf/load 호출하세요."}), 400
    data = request.json or {}
    messages = data.get("messages") or []
    if not messages:
        return jsonify({"ok": False, "error": "messages 필수 — [{'role':'user','content':'...'}] 형식"}), 400
    try:
        resp = gguf_model.create_chat_completion(
            messages=messages,
            temperature=float(data.get("temperature", 0.5)),
            max_tokens=int(data.get("max_tokens", 4096)),
        )
        text = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        return jsonify({"ok": True, "text": text, "usage": usage})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/fs/browse", methods=["POST"])
def api_fs_browse():
    """폴더 탐색 — 디렉토리 내용 반환 (드라이브 목록, 하위 폴더, GGUF 파일)."""
    data = request.json or {}
    path = data.get("path") or BASE_DIR

    # 빈 path면 BASE_DIR
    if not path:
        path = BASE_DIR

    # Windows 드라이브 목록 (항상 반환)
    drives = []
    if os.name == "nt":
        import string
        for letter in string.ascii_uppercase:
            d = f"{letter}:\\"
            if os.path.exists(d):
                drives.append(d)

    if not os.path.exists(path):
        return jsonify({"ok": False, "error": f"경로 없음: {path}", "drives": drives}), 404
    if not os.path.isdir(path):
        return jsonify({"ok": False, "error": f"디렉토리 아님: {path}", "drives": drives}), 400

    items = []
    try:
        for name in sorted(os.listdir(path), key=lambda x: x.lower()):
            # 숨김 파일/시스템 폴더 스킵
            if name.startswith(".") or name.lower() in ("$recycle.bin", "system volume information"):
                continue
            full = os.path.join(path, name)
            try:
                if os.path.isdir(full):
                    items.append({"name": name, "is_dir": True, "path": full})
                elif name.lower().endswith(".gguf") and "mmproj" not in name.lower():
                    items.append({
                        "name": name,
                        "is_dir": False,
                        "path": full,
                        "size_gb": round(os.path.getsize(full) / 1e9, 2),
                    })
            except (OSError, PermissionError):
                continue
    except PermissionError:
        return jsonify({"ok": False, "error": "권한 없음", "drives": drives, "path": path}), 403

    parent = os.path.dirname(path)
    if parent == path or not parent:
        parent = None

    # 디렉토리 먼저, 그 다음 파일
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    return jsonify({
        "ok": True,
        "path": path,
        "parent": parent,
        "items": items,
        "drives": drives,
    })


@app.route("/api/nanabot/stream", methods=["POST"])
def api_nanabot_stream():
    """나노봇 4단 체인 (Analyzer → Architect → Writer → Reviewer) SSE 스트림."""
    from flask import Response
    import json as _json

    data = request.json or {}
    requirement = (data.get("requirement") or "").strip()
    type_label = data.get("type_label", "일반 프로그램")
    lang_label = data.get("language_label", "Python")
    fw_label = data.get("framework_label", "")

    if not requirement:
        return jsonify({"ok": False, "error": "requirement 필수"}), 400
    if gguf_model is None:
        return jsonify({"ok": False, "error": "GGUF 모델이 로드되지 않았습니다. 먼저 모델을 로드하세요."}), 400

    fw_str = f" + {fw_label}" if fw_label and "추천" not in fw_label and fw_label != "" else ""
    ctx_str = f"[{type_label}] {lang_label}{fw_str}"

    def generate():
        def emit(obj):
            return "data: " + _json.dumps(obj, ensure_ascii=False) + "\n\n"

        stages = [
            {
                "id": 1, "name": "Analyzer",
                "sys": "당신은 소프트웨어 요구사항 분석가입니다. 사용자 요구사항을 분석해서 다음을 짧고 명확하게 추출하세요:\n- 핵심 의도\n- 입력 형식\n- 출력 형식\n- 주요 제약\n- 성공 기준\n마크다운 불릿 사용. 1200자 이내.",
                "user": f"요구사항:\n{requirement}\n\n프로젝트: {ctx_str}"
            },
            {
                "id": 2, "name": "Architect",
                "sys": "당신은 시스템 아키텍트입니다. 분석 결과를 받아 1-2개 적합한 구조를 제안하고 핵심 모듈을 나열하세요. 1200자 이내, 마크다운.",
                "user_idx": 0,
                "user_fmt": "분석 결과:\n{}\n\n위를 기반으로 구조 설계를 제안하세요."
            },
            {
                "id": 3, "name": "Writer",
                "sys": "당신은 기술 문서 작가입니다. 분석과 설계를 종합해 구현 가이드 MD를 작성하세요. 섹션: 개요 / 입출력 명세 / 모듈 구조 / 핵심 함수 시그니처 / 검증 방법. 한국어 주석. 1800자 이내.",
                "user_idx": (0, 1),
                "user_fmt": "분석:\n{}\n\n설계:\n{}\n\n위를 통합해 완성된 MD 설계도를 작성하세요."
            },
            {
                "id": 4, "name": "Reviewer",
                "sys": "당신은 시니어 코드 리뷰어입니다. MD 설계도를 검토해 모호한 부분, 누락, 테스트 가능성을 짚으세요. 개선점만 짧게 (800자 이내).",
                "user_idx": 2,
                "user_fmt": "검토할 MD:\n{}\n\n위 MD를 검토하여 개선점만 짧게 나열하세요."
            },
        ]

        outputs = []
        for stage in stages:
            try:
                yield emit({"stage": stage["id"], "name": stage["name"], "status": "running"})

                # 사용자 메시지 구성
                if "user" in stage:
                    user_msg = stage["user"]
                elif isinstance(stage["user_idx"], tuple):
                    user_msg = stage["user_fmt"].format(*[outputs[i] for i in stage["user_idx"]])
                else:
                    user_msg = stage["user_fmt"].format(outputs[stage["user_idx"]])

                resp = gguf_model.create_chat_completion(
                    messages=[
                        {"role": "system", "content": stage["sys"]},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.4,
                    max_tokens=900,
                )
                text = resp["choices"][0]["message"]["content"]
                outputs.append(text)
                yield emit({
                    "stage": stage["id"], "name": stage["name"],
                    "status": "done", "output": text
                })
            except Exception as e:
                traceback.print_exc()
                yield emit({"stage": stage["id"], "status": "error", "error": str(e)})
                return

        # 최종 MD = Writer + Reviewer 코멘트
        final_md = outputs[2] + "\n\n---\n\n## 🔍 자체 검토 (Reviewer)\n\n" + outputs[3]
        yield emit({"stage": "complete", "status": "done", "final_md": final_md})

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "ok": True,
        "service": "foundry-server",
        "version": "v6.3",
        "base_dir": BASE_DIR,
        "gguf_loaded": os.path.basename(gguf_loaded_path) if gguf_loaded_path else None,
    })


# ============================================================
# 실행
# ============================================================
def main():
    port = int(os.environ.get("FOUNDRY_PORT", DEFAULT_PORT))
    bar = "=" * 60
    print(bar)
    print("  자율 제조 공장 v6.3 — 독립 실행 서버")
    print(bar)
    print(f"  BASE_DIR  : {BASE_DIR}")
    print(f"  VRAM 예산 : {VRAM_BUDGET_GB} GB")
    print(f"  포트      : {port}")
    print(f"  UI        : http://localhost:{port}/foundry")
    print(f"  헬스체크  : http://localhost:{port}/api/health")
    print(bar)

    # GGUF 파일 미리보기
    files = find_gguf_files()
    if files:
        print(f"  발견된 GGUF: {len(files)}개")
        for f in files[:5]:
            print(f"    - {f['name']} ({f['size_gb']} GB)")
        if len(files) > 5:
            print(f"    ... 외 {len(files) - 5}개")
    else:
        print(f"  [!] GGUF 파일 없음 — 다음 위치에 .gguf 두기:")
        print(f"      {BASE_DIR}")
        print(f"      {BASE_DIR}{os.sep}models{os.sep}")
        print(f"      {BASE_DIR}{os.sep}model{os.sep}")
    print(bar)

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
