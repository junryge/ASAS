"""
code_assist_v1/app_code.py - 코딩 어시스턴트 진입점

실행:
    python -m code_assist_v1.app_code
"""
from __future__ import annotations
import os
import sys

# 이 파일을 직접 실행하면 부모(루트) 가 sys.path 에 없을 수 있음
_THIS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_THIS)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from code_assist_v1 import app, create_app
from code_assist_v1.config import (
    API_TOKEN,
    MODEL_REGISTRY,
    ENV_CONFIG,
    PORT,
    SKILLS_DIR,
    KNOWLEDGE_DIR,
    WORKSPACE_DIR,
    MODEL_GGUF_DIR,
    VRAM_BUDGET_GB,
    TOKEN_FILE,
)


def _setup_windows_console():
    if sys.platform != "win32":
        return
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass


def _auto_register_gguf():
    """code_assist_v1/MODEL_GGUF/ 의 .gguf 파일을 ENV_CONFIG 에 'gguf-N' 으로 등록 + 가장 큰 모델 자동 로드."""
    from code_assist_v1.gguf_loader import find_gguf_files, load_gguf_model

    files = find_gguf_files()
    if not files:
        print(f"  ℹ️  GGUF 파일 없음 → 로컬 모델 비활성")
        print(f"     (이 폴더에 .gguf 를 넣으세요: {MODEL_GGUF_DIR})")
        return

    files.sort(key=lambda x: x["size_gb"], reverse=True)
    print(f"  💻 GGUF 자동 감지: {len(files)}개  (from MODEL_GGUF/)")
    for idx, gf in enumerate(files):
        env_key = f"gguf-{idx}"
        model_name = gf["name"].replace(".gguf", "")
        ENV_CONFIG[env_key] = {
            "url": "python://llama-cpp-python",
            "model": model_name,
            "name": f"LOCAL ({model_name})",
            "_gguf_path": gf["path"],
            "_size_gb": gf["size_gb"],
        }
        print(f"     [{env_key}] {gf['name']} ({gf['size_gb']} GB)")

    # 자동 로드: VRAM 예산 안에서 가장 큰 모델
    fit = [g for g in files if g["size_gb"] <= VRAM_BUDGET_GB]
    target = fit[0] if fit else files[-1]
    if not fit:
        print(f"     ⚠️  모든 모델이 VRAM 예산({VRAM_BUDGET_GB}GB) 초과 → 가장 작은 모델 로드")
    if load_gguf_model(target["path"]):
        print(f"     ✅ 기본 GGUF 로드: {target['name']} ({target['size_gb']} GB)")
    else:
        print(f"     ⚠️  GGUF 로드 실패 (수동 전환 가능)")


def main():
    _setup_windows_console()
    create_app()

    print("=" * 60)
    print("  Freedom 코딩 어시스턴트")
    print("=" * 60)

    # 첫 기동 시: scientific-skills 에서 코딩 스킬 자동 시드
    from code_assist_v1.seed import seed_skills_if_empty
    seed_skills_if_empty()

    # TOKEN
    if API_TOKEN:
        print(f"  🔑 TOKEN.TXT: 로드됨 ({len(API_TOKEN)}자)")
    else:
        print(f"  ⚠️  TOKEN.TXT 비어있음 — API 모델 비활성. 채워주세요: {TOKEN_FILE}")

    # 디렉토리 (모두 자체)
    print(f"  📁 skills    : {SKILLS_DIR}")
    print(f"  📁 knowledge : {KNOWLEDGE_DIR}")
    print(f"  📁 workspace : {WORKSPACE_DIR}")
    print(f"  📁 MODEL_GGUF: {MODEL_GGUF_DIR}")

    # API 모델
    print(f"  🌐 API 모델: {len(MODEL_REGISTRY)}개")
    for mid in MODEL_REGISTRY:
        print(f"     - {mid}")

    # GGUF
    _auto_register_gguf()

    print()
    print(f"  🚀 http://localhost:{PORT}")
    print("=" * 60)

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # GGUF 로드 시 llama-cpp-python 이 Windows 콘솔 핸들을 망가뜨림.
    # 그 상태에서 Flask 가 click 으로 배너를 찍으면 OSError 6 (handle is invalid).
    # 기존 app.py 와 동일한 복원 로직.
    if sys.platform == "win32":
        import io as _io

        # 1) Flask CLI 배너 비활성
        os.environ.setdefault("WERKZEUG_RUN_MAIN", "false")

        # 2) stdout/stderr 핸들 복원
        for _stream_name in ("stdout", "stderr"):
            try:
                getattr(sys, _stream_name).write("")
            except (OSError, AttributeError, ValueError):
                try:
                    _orig = getattr(sys, f"__{_stream_name}__")
                    _fd = _orig.fileno()
                    setattr(sys, _stream_name, _io.TextIOWrapper(
                        open(_fd, "wb", closefd=False),
                        encoding="utf-8", errors="replace"
                    ))
                except (OSError, AttributeError, ValueError):
                    setattr(sys, _stream_name, open(os.devnull, "w", encoding="utf-8"))

        # 3) click.echo 무력화 (banner·기타 출력)
        try:
            import click
            click.echo = lambda message=None, file=None, nl=True, err=False, color=None: None
        except ImportError:
            pass

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
