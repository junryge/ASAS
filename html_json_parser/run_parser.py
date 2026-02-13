#!/usr/bin/env python3
"""
HTML -> JSON 파서 CLI 도구

사용법:
  # 단일 파일 파싱
  python run_parser.py input.html

  # 출력 파일 지정
  python run_parser.py input.html -o output.json

  # 폴더 내 모든 HTML 일괄 파싱
  python run_parser.py --dir ./html_files/

  # 요약만 출력 (JSON 저장 없이)
  python run_parser.py input.html --summary

  # 특정 섹션만 추출
  python run_parser.py input.html --only components,flow_diagram,js_data_objects
"""

import argparse
import glob
import json
import os
import sys

from parse_layout import HTMLLayoutParser


def parse_single(html_path: str, output_path: str | None = None,
                 summary_only: bool = False,
                 only_sections: list[str] | None = None) -> dict:
    """단일 HTML 파일 파싱"""
    if not os.path.exists(html_path):
        print(f"[ERROR] 파일을 찾을 수 없습니다: {html_path}")
        sys.exit(1)

    parser = HTMLLayoutParser(html_path)
    result = parser.parse()

    # 특정 섹션만 필터링
    if only_sections:
        filtered = {
            "source_file": result["source_file"],
            "file_size_bytes": result["file_size_bytes"],
        }
        for section in only_sections:
            section = section.strip()
            if section in result:
                filtered[section] = result[section]
            else:
                print(f"[WARN] 알 수 없는 섹션: {section}")
                print(f"       사용 가능: {', '.join(result.keys())}")
        result = filtered

    if summary_only:
        print_summary(result, html_path)
        return result

    # 출력 경로 결정
    if not output_path:
        base = os.path.splitext(os.path.basename(html_path))[0]
        output_dir = os.path.join(os.path.dirname(html_path) or ".", "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base}.json")

    # JSON 저장
    output_dir_for_file = os.path.dirname(output_path)
    if output_dir_for_file:
        os.makedirs(output_dir_for_file, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 파싱 완료: {html_path}")
    print(f"     -> JSON 저장: {output_path}")
    print_summary(result, html_path)

    return result


def parse_directory(dir_path: str, output_dir: str | None = None) -> list[dict]:
    """폴더 내 모든 HTML 파일 일괄 파싱"""
    if not os.path.isdir(dir_path):
        print(f"[ERROR] 디렉토리를 찾을 수 없습니다: {dir_path}")
        sys.exit(1)

    html_files = glob.glob(os.path.join(dir_path, "*.html"))
    html_files += glob.glob(os.path.join(dir_path, "*.HTML"))
    html_files += glob.glob(os.path.join(dir_path, "*.htm"))
    html_files = sorted(set(html_files))

    if not html_files:
        print(f"[WARN] HTML 파일이 없습니다: {dir_path}")
        return []

    if not output_dir:
        output_dir = os.path.join(dir_path, "output")
    os.makedirs(output_dir, exist_ok=True)

    results = []
    print(f"[INFO] {len(html_files)}개의 HTML 파일을 파싱합니다...")
    print(f"       출력 폴더: {output_dir}")
    print("-" * 60)

    for i, html_file in enumerate(html_files, 1):
        base = os.path.splitext(os.path.basename(html_file))[0]
        output_path = os.path.join(output_dir, f"{base}.json")

        print(f"\n[{i}/{len(html_files)}] {os.path.basename(html_file)}")

        parser = HTMLLayoutParser(html_file)
        result = parser.parse()
        parser.save_json(output_path)
        results.append(result)

        print_summary(result, html_file, compact=True)

    print("\n" + "=" * 60)
    print(f"[DONE] 전체 {len(results)}개 파일 파싱 완료")
    print(f"       출력 위치: {output_dir}")
    return results


def print_summary(result: dict, html_path: str, compact: bool = False):
    """파싱 결과 요약 출력"""
    stats = result.get("statistics", {})
    meta = result.get("metadata", {})
    prefix = "     " if compact else ""

    print(f"{prefix}---")
    if meta.get("title"):
        print(f"{prefix}  제목: {meta['title']}")
    print(f"{prefix}  파일 크기: {stats.get('html_size_bytes', 0):,} bytes")
    print(f"{prefix}  CSS 변수: {stats.get('total_css_variables', 0)}개")
    print(f"{prefix}  CSS 클래스: {stats.get('total_css_classes', 0)}개")
    print(f"{prefix}  컴포넌트: {stats.get('total_components', 0)}개")
    print(f"{prefix}  섹션: {stats.get('total_sections', 0)}개")
    print(f"{prefix}  플로우 노드: {stats.get('total_flow_nodes', 0)}개")
    print(f"{prefix}  JS 객체: {stats.get('total_js_objects', 0)}개")
    print(f"{prefix}  텍스트 항목: {stats.get('total_text_items', 0)}개")


def main():
    parser = argparse.ArgumentParser(
        description="HTML Layout Parser - HTML 파일을 JSON으로 변환",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_parser.py mypage.html
  python run_parser.py mypage.html -o result.json
  python run_parser.py --dir ./html_files/
  python run_parser.py mypage.html --summary
  python run_parser.py mypage.html --only components,js_data_objects
        """,
    )

    parser.add_argument(
        "input", nargs="?", help="파싱할 HTML 파일 경로"
    )
    parser.add_argument(
        "-o", "--output", help="출력 JSON 파일 경로 (미지정 시 자동 생성)"
    )
    parser.add_argument(
        "--dir", help="폴더 내 모든 HTML 파일 일괄 파싱"
    )
    parser.add_argument(
        "--output-dir", help="일괄 파싱 시 출력 폴더 (미지정 시 input/output/)"
    )
    parser.add_argument(
        "--summary", action="store_true", help="요약만 출력 (JSON 저장 안 함)"
    )
    parser.add_argument(
        "--only",
        help="추출할 섹션 지정 (쉼표 구분). "
        "예: components,flow_diagram,js_data_objects,metadata,css_variables",
    )

    args = parser.parse_args()

    if not args.input and not args.dir:
        parser.print_help()
        print("\n[ERROR] HTML 파일 경로 또는 --dir 옵션을 지정하세요.")
        sys.exit(1)

    only_sections = args.only.split(",") if args.only else None

    if args.dir:
        parse_directory(args.dir, args.output_dir)
    else:
        parse_single(args.input, args.output, args.summary, only_sections)


if __name__ == "__main__":
    main()
