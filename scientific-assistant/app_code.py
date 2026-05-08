"""
code_assist_v1/app_code.py - DEPRECATED

단독 실행은 더 이상 지원하지 않습니다.
대신 메인 app.py 를 실행하면 코드 어시스턴트가 자동 통합됩니다:

    python app.py
    → http://localhost:10009/code/  로 접근

기존 code_assist_v1 단독 부팅 코드는 git history 또는 백업 zip 에 보존되어 있습니다.
이 파일은 사용자가 옛 명령(`python -m code_assist_v1.app_code`)을 실행했을 때
명확한 안내를 띄우기 위해 남겨둡니다.
"""
import sys


def main():
    print("=" * 60)
    print("  ⚠️  code_assist_v1 단독 실행은 더 이상 지원되지 않습니다.")
    print("=" * 60)
    print()
    print("  메인 demos_v1 서버를 실행하세요:")
    print("    python app.py")
    print()
    print("  코드 어시스턴트는 자동으로 통합됩니다:")
    print("    → http://localhost:10009/code/")
    print()
    sys.exit(1)


if __name__ == "__main__":
    main()
