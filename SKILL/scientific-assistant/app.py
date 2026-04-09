"""
Demos V1.0 - Flask 웹앱 (모듈 분리 버전)
=====================================================
cla-main + zircote/.claude 통합: 355개 스킬 (과학 174 + 개발도구 52 + 에이전트 117 + 가이드 12)

사용법:
  1. scientific-skills 폴더를 이 파일과 같은 위치에 복사
  2. TOKEN.TXT 파일에 API 키를 넣어두기 (같은 폴더)
  3. pip install flask requests
  4. python app.py
  5. 브라우저에서 http://localhost:10009 접속

폴더 구조:
  app.py                 ← 엔트리포인트
  demos_v1/              ← 모듈 패키지
  TOKEN.TXT              ← API 키 (한 줄)
  scientific-skills/     ← 355개 스킬
"""

import os
import sys

# Create Flask app and register all routes
from demos_v1 import app, create_app
create_app()

# Import everything needed for startup
from demos_v1.utils import BASE_DIR, SKILLS_DIR, HARNESS_AVAILABLE
from demos_v1.config import API_TOKEN, TOKEN_SETTINGS
from demos_v1.models import ENV_CONFIG
from demos_v1.skills import scan_skills, SKILL_KEYWORDS, load_skill_content
from demos_v1.gguf import find_gguf_files, load_gguf_model
from demos_v1.logpresso import _refresh_logpresso_tables

# Re-export TOKEN_FILE for startup message
TOKEN_FILE = os.path.join(BASE_DIR, "TOKEN.TXT")

if __name__ == "__main__":
    # Windows 콘솔 인코딩 사전 보호 (colorama/click 충돌 방지)
    if sys.platform == "win32":
        # UTF-8 콘솔 모드 강제
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")
        try:
            os.system("chcp 65001 >nul 2>&1")
        except Exception:
            pass
        # colorama 초기화 문제 방지
        os.environ.setdefault("NO_COLOR", "1")
        os.environ.setdefault("TERM", "dumb")

    print("=" * 50)
    print("  Demos V1.0")
    print("=" * 50)

    # 스킬 폴더 확인
    if os.path.isdir(SKILLS_DIR):
        skills = scan_skills()
        print(f"  📂 스킬 폴더: {SKILLS_DIR}")
        print(f"  ✅ 발견된 스킬: {len(skills)}개")
        for s in sorted(skills.keys())[:10]:
            print(f"     - {s}")
        if len(skills) > 10:
            print(f"     ... 외 {len(skills)-10}개")
    else:
        print(f"  ⚠️  스킬 폴더 없음: {SKILLS_DIR}")
        print(f"     scientific-skills 폴더를 app.py와 같은 위치에 복사하세요.")

    # 토큰 확인
    if API_TOKEN:
        print(f"  🔑 TOKEN.TXT: 로드됨 ({len(API_TOKEN)}자)")
    else:
        print(f"  ⚠️  TOKEN.TXT: 없음 또는 비어있음")
        print(f"     → {TOKEN_FILE} 에 API 키를 넣어주세요")

    # 하네스 브릿지 초기화 (스킬 레지스트리 + API 엔드포인트)
    if HARNESS_AVAILABLE:
        try:
            from harness_bridge import init_harness, register_harness_routes
            harness_reg = init_harness(SKILLS_DIR, SKILL_KEYWORDS)
            register_harness_routes(app)
            print(f"  🔧 하네스: {len(harness_reg.list_all())}개 스킬 레지스트리 등록 완료")
            print(f"     → /api/harness/skills, /api/harness/session/*, /api/harness/status")
        except Exception as e:
            print(f"  ⚠️  하네스 초기화 실패: {e}")
    else:
        print(f"  ℹ️  하네스 브릿지 미설치 (harness_bridge.py 없음 → 기존 모드)")

    # 로그프레소 테이블 목록 자동 업데이트
    _refresh_logpresso_tables()

    # ============================================
    # GGUF 자동 감지 & Python으로 직접 로드 (다중 모델 지원)
    # ============================================
    gguf_files = find_gguf_files()

    if gguf_files:
        # 크기 내림차순 정렬
        gguf_files.sort(key=lambda x: x["size_gb"], reverse=True)
        print(f"\n  💻 GGUF 자동 감지! ({len(gguf_files)}개 모델)")

        for idx, gf in enumerate(gguf_files):
            env_key = f"gguf-{idx}"
            model_name = gf["name"].replace(".gguf", "")
            ENV_CONFIG[env_key] = {
                "url": "python://llama-cpp-python",
                "model": model_name,
                "name": f"LOCAL ({model_name})",
                "_gguf_path": gf["path"],  # 내부용: 모델 파일 경로
                "_size_gb": gf["size_gb"],  # 병렬 에이전트 VRAM 예산용
            }
            print(f"     [{env_key}] {gf['name']} ({gf['size_gb']} GB)")

        # 첫 번째(가장 큰) 모델을 기본 로드
        first_gguf = gguf_files[0]
        if load_gguf_model(first_gguf["path"]):
            print(f"     ✅ 기본 모델 로드 완료: {first_gguf['name']}")
        else:
            print(f"     ⚠️  기본 모델 로드 실패 (환경 전환 시 재시도)")
    else:
        print(f"\n  ℹ️  GGUF 파일 없음 → LOCAL GGUF 비활성")

    # 환경 목록
    print()
    print("  🖥️  사용 가능한 LLM 환경:")
    for eid, ecfg in ENV_CONFIG.items():
        print(f"     [{eid}] {ecfg['name']} → {ecfg['url']}")

    print()
    print(f"  🌐 http://localhost:10009 에서 접속하세요")
    print("=" * 50)

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Windows: GGUF 모델 로드 후 콘솔 핸들이 깨질 수 있으므로 복원
    if sys.platform == "win32":
        import io as _io

        # 1) colorama/click 배너 출력 시 OSError: Windows error 6 방지
        #    → 환경변수로 Flask CLI 배너를 비활성화
        os.environ.setdefault("WERKZEUG_RUN_MAIN", "false")

        # 2) stdout/stderr 핸들 복원 시도
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
                    # fileno()도 죽은 경우 → devnull로 대체 (서버는 정상 동작)
                    setattr(sys, _stream_name, open(os.devnull, "w", encoding="utf-8"))

        # 3) click의 echo가 colorama를 통해 쓸 때 터지는 것 방지
        try:
            import click
            click.echo = lambda message=None, file=None, nl=True, err=False, color=None: None
        except ImportError:
            pass

    app.run(host="0.0.0.0", port=10009, debug=False)
    #app.run(host="127.0.0.1", port=18080, debug=False, use_reloader=False)
