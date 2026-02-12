"""
HTML Layout Parser - HTML 파일을 분석하여 구조화된 JSON 데이터로 추출하는 도구

지원하는 추출 항목:
  - 메타데이터 (title, charset, viewport 등)
  - CSS 변수 (:root 커스텀 프로퍼티)
  - 헤더/섹션 구조
  - 컴포넌트 카드 (data-* 속성 포함)
  - JavaScript 데이터 객체 (인라인 스크립트 내 dict/object)
  - 플로우 다이어그램 노드
  - 텍스트 콘텐츠 계층 구조

사용법:
  from parse_layout import HTMLLayoutParser
  parser = HTMLLayoutParser("파일경로.html")
  result = parser.parse()
  parser.save_json("출력파일.json")
"""

import json
import re
import os
from html.parser import HTMLParser
from typing import Any


class HTMLLayoutParser:
    """HTML 파일을 파싱하여 JSON 구조로 변환하는 파서"""

    def __init__(self, html_path: str):
        self.html_path = html_path
        self.html_content = ""
        self.result: dict[str, Any] = {}

    def load(self) -> str:
        """HTML 파일을 로드"""
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.html_content = f.read()
        return self.html_content

    def parse(self) -> dict[str, Any]:
        """HTML을 파싱하여 전체 구조를 JSON으로 변환"""
        if not self.html_content:
            self.load()

        self.result = {
            "source_file": os.path.basename(self.html_path),
            "file_size_bytes": os.path.getsize(self.html_path),
            "metadata": self._extract_metadata(),
            "css_variables": self._extract_css_variables(),
            "css_classes": self._extract_css_classes(),
            "layout_structure": self._extract_layout_structure(),
            "components": self._extract_components(),
            "flow_diagram": self._extract_flow_diagram(),
            "js_data_objects": self._extract_js_data(),
            "text_content": self._extract_text_content(),
            "statistics": {},
        }

        # 통계 계산
        self.result["statistics"] = self._compute_statistics()

        return self.result

    def _extract_metadata(self) -> dict:
        """HTML 메타데이터 추출 (title, meta 태그 등)"""
        metadata = {}

        # lang 속성
        lang_match = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', self.html_content)
        if lang_match:
            metadata["lang"] = lang_match.group(1)

        # title
        title_match = re.search(r"<title>(.*?)</title>", self.html_content, re.DOTALL)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # meta 태그들
        meta_tags = re.findall(
            r'<meta\s+([^>]+?)/?>', self.html_content, re.IGNORECASE
        )
        meta_list = []
        for attrs_str in meta_tags:
            attrs = {}
            for m in re.finditer(r'(\w[\w-]*)=["\']([^"\']*)["\']', attrs_str):
                attrs[m.group(1)] = m.group(2)
            if attrs:
                meta_list.append(attrs)
        metadata["meta_tags"] = meta_list

        # 외부 리소스 (link, script src)
        links = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', self.html_content)
        metadata["external_links"] = links

        scripts = re.findall(
            r'<script[^>]+src=["\']([^"\']+)["\']', self.html_content
        )
        metadata["external_scripts"] = scripts

        return metadata

    def _extract_css_variables(self) -> dict:
        """CSS :root 커스텀 프로퍼티(변수) 추출"""
        variables = {}
        root_match = re.search(
            r":root\s*\{([^}]+)\}", self.html_content, re.DOTALL
        )
        if root_match:
            root_block = root_match.group(1)
            for var_match in re.finditer(
                r"--([\w-]+)\s*:\s*([^;]+);", root_block
            ):
                variables[var_match.group(1).strip()] = var_match.group(2).strip()
        return variables

    def _extract_css_classes(self) -> list[str]:
        """정의된 CSS 클래스 목록 추출"""
        style_match = re.search(
            r"<style[^>]*>(.*?)</style>", self.html_content, re.DOTALL
        )
        if not style_match:
            return []

        style_content = style_match.group(1)
        classes = re.findall(r"\.([\w-]+)\s*[{,:]", style_content)
        return sorted(set(classes))

    def _extract_layout_structure(self) -> list[dict]:
        """HTML DOM의 계층적 레이아웃 구조를 추출"""
        structure = []
        parser = _StructureParser()
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", self.html_content, re.DOTALL
        )
        if body_match:
            # script/style 태그 제거 후 파싱
            body_html = body_match.group(1)
            body_clean = re.sub(
                r"<script[^>]*>.*?</script>", "", body_html, flags=re.DOTALL
            )
            body_clean = re.sub(
                r"<style[^>]*>.*?</style>", "", body_clean, flags=re.DOTALL
            )
            parser.feed(body_clean)
            structure = parser.structure
        return structure

    def _extract_components(self) -> list[dict]:
        """컴포넌트 카드/위젯 추출 (data-* 속성, 클래스 기반)"""
        components = []

        # 개별 comp-card 태그를 하나씩 매칭 (각 카드의 시작~다음 카드 시작 사이)
        card_starts = list(re.finditer(
            r'<div[^>]*class="[^"]*comp-card[^"]*"[^>]*data-cat="(\w+)"[^>]*>',
            self.html_content,
        ))

        seen = set()
        for i, m in enumerate(card_starts):
            cat = m.group(1)
            start = m.end()
            # 다음 카드 시작 또는 comp-grid 종료까지
            if i + 1 < len(card_starts):
                end = card_starts[i + 1].start()
            else:
                end = start + 500  # 마지막 카드는 적당한 범위

            inner = self.html_content[start:end]

            emoji = ""
            name = ""
            full_name = ""

            emoji_m = re.search(r'class="comp-emoji"[^>]*>(.*?)</div>', inner, re.DOTALL)
            if emoji_m:
                emoji = emoji_m.group(1).strip()

            name_m = re.search(r'class="comp-name"[^>]*>(.*?)</div>', inner, re.DOTALL)
            if name_m:
                name = name_m.group(1).strip()

            full_m = re.search(r'class="comp-full"[^>]*>(.*?)</div>', inner, re.DOTALL)
            if full_m:
                full_name = full_m.group(1).strip()

            key = f"{cat}_{name}"
            if key not in seen:
                seen.add(key)
                components.append(
                    {
                        "category": cat,
                        "name": name,
                        "full_name": full_name,
                        "emoji": emoji,
                    }
                )

        # data-cat 외에도 범용 카드 패턴 (class에 card/item/widget 포함)
        for card_m in re.finditer(
            r'<div[^>]*class="([^"]*(?:card|item|widget)[^"]*)"[^>]*'
            r'(?:data-(\w+)="([^"]*)")?[^>]*>',
            self.html_content,
        ):
            cls = card_m.group(1)
            if "comp-card" in cls:
                continue  # 이미 처리됨
            data_key = card_m.group(2)
            data_val = card_m.group(3)
            if data_key and data_val:
                key = f"{cls}_{data_val}"
                if key not in seen:
                    seen.add(key)
                    components.append({
                        "class": cls,
                        f"data_{data_key}": data_val,
                    })

        # fab-section 기반 섹션 추출
        fab_sections = []
        for fab_match in re.finditer(
            r'class="fab-section"[^>]*>(.*?)(?=class="fab-section"|class="connection-arrow"|</div>\s*</div>\s*</div>\s*</div>)',
            self.html_content,
            re.DOTALL,
        ):
            fab_inner = fab_match.group(1)
            fab_name_m = re.search(
                r'class="fab-name[^"]*"[^>]*>(.*?)</span>', fab_inner
            )
            fab_badge_m = re.search(
                r'class="fab-badge[^"]*"[^>]*>(.*?)</span>', fab_inner
            )
            if fab_name_m:
                # 이 섹션에 포함된 컴포넌트 카드 목록
                section_cards = []
                for sc in re.finditer(r'data-cat="(\w+)"', fab_inner):
                    section_cards.append(sc.group(1))

                fab_sections.append({
                    "name": fab_name_m.group(1).strip(),
                    "badge": fab_badge_m.group(1).strip() if fab_badge_m else "",
                    "components": section_cards,
                })

        return {
            "cards": components,
            "sections": fab_sections,
        }

    def _extract_flow_diagram(self) -> dict:
        """플로우 다이어그램 노드 및 흐름 추출"""
        flow = {"title": "", "nodes": [], "arrows": []}

        # 플로우 제목
        flow_title_m = re.search(
            r'class="flow-title"[^>]*>(.*?)</div>', self.html_content, re.DOTALL
        )
        if flow_title_m:
            flow["title"] = re.sub(r"<[^>]+>", "", flow_title_m.group(1)).strip()

        # 플로우 노드
        for node_match in re.finditer(
            r'<div[^>]*class="flow-node\s+(\w+)"[^>]*>(.*?)</div>',
            self.html_content,
            re.DOTALL,
        ):
            node_type = node_match.group(1)
            node_content = node_match.group(2)

            # 텍스트 추출
            clean = re.sub(r"<[^>]+>", " ", node_content).strip()
            parts = [p.strip() for p in clean.split() if p.strip()]

            # small 태그 내용
            small_m = re.search(r"<small>(.*?)</small>", node_content, re.DOTALL)
            label = small_m.group(1).strip() if small_m else ""

            # 메인 텍스트 (small 제외)
            main_text = re.sub(r"<small>.*?</small>", "", node_content, flags=re.DOTALL)
            main_text = re.sub(r"<[^>]+>", "", main_text).strip()

            flow["nodes"].append(
                {
                    "type": node_type,
                    "main_text": main_text,
                    "sub_label": label,
                }
            )

        # 화살표 수 카운트
        arrow_count = len(re.findall(r'class="flow-arrow"', self.html_content))
        flow["arrow_count"] = arrow_count

        return flow

    def _extract_js_data(self) -> dict:
        """인라인 JavaScript에서 데이터 객체(변수) 추출"""
        js_data = {}

        script_match = re.search(
            r"<script[^>]*>(.*?)</script>", self.html_content, re.DOTALL
        )
        if not script_match:
            return js_data

        script_content = script_match.group(1)

        # const/let/var 로 정의된 객체 리터럴 찾기
        obj_pattern = re.compile(
            r"(?:const|let|var)\s+(\w+)\s*=\s*(\{)", re.DOTALL
        )

        for obj_match in obj_pattern.finditer(script_content):
            var_name = obj_match.group(1)
            start_idx = obj_match.start(2)

            # 중괄호 매칭으로 객체 전체 추출
            obj_str = self._extract_balanced_braces(script_content, start_idx)
            if obj_str:
                parsed = self._parse_js_object(obj_str)
                if parsed:
                    js_data[var_name] = parsed

        # function 정의 목록
        functions = re.findall(
            r"function\s+(\w+)\s*\(([^)]*)\)", script_content
        )
        if functions:
            js_data["_functions"] = [
                {"name": fn[0], "params": fn[1].strip()} for fn in functions
            ]

        return js_data

    def _extract_balanced_braces(self, text: str, start: int) -> str | None:
        """중괄호 균형을 맞춰 객체/블록 전체 문자열을 추출"""
        depth = 0
        in_string = False
        string_char = None
        i = start

        while i < len(text):
            ch = text[i]

            if in_string:
                if ch == "\\" and i + 1 < len(text):
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
            else:
                if ch in ("'", '"', "`"):
                    in_string = True
                    string_char = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]

            i += 1

        return None

    def _parse_js_object(self, js_str: str) -> dict | None:
        """JavaScript 객체 리터럴을 Python dict로 변환"""
        try:
            # JS -> JSON 변환 시도
            json_str = js_str

            # 후행 쉼표 제거
            json_str = re.sub(r",\s*([}\]])", r"\1", json_str)

            # 키에 따옴표 추가 (이미 따옴표가 없는 키)
            json_str = re.sub(
                r"(?<=[{,])\s*(\w+)\s*:", r' "\1":', json_str
            )

            # 작은따옴표를 큰따옴표로 변환 (문자열 내부 제외, 간단한 케이스)
            # 먼저 작은따옴표 문자열을 큰따옴표로 변환
            json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)

            # 템플릿 리터럴 처리 (backtick -> 큰따옴표)
            json_str = re.sub(r"`([^`]*)`", lambda m: '"' + m.group(1).replace('"', '\\"').replace("\n", "\\n") + '"', json_str)

            # ${...} 템플릿 표현식을 간단한 문자열로
            json_str = re.sub(r"\$\{([^}]+)\}", r"[EXPR:\1]", json_str)

            result = json.loads(json_str)
            return result
        except (json.JSONDecodeError, ValueError):
            # JSON 파싱 실패 시 키-값 패턴으로 수동 추출
            return self._manual_parse_js_object(js_str)

    def _manual_parse_js_object(self, js_str: str) -> dict | None:
        """JSON 파싱 실패 시 정규식으로 최상위 키-값 추출"""
        result = {}
        # 최상위 키 추출: key: { ... } 패턴
        top_keys = re.finditer(
            r"(\w+)\s*:\s*\{", js_str
        )
        for km in top_keys:
            key = km.group(1)
            inner_start = km.start() + len(km.group(0)) - 1
            inner_str = self._extract_balanced_braces(js_str, inner_start)
            if inner_str:
                # 내부 값 추출
                inner_data = {}
                # 단순 키: '값' 또는 키: "값" 패턴
                for kv in re.finditer(
                    r"(\w+)\s*:\s*['\"]([^'\"]*)['\"]", inner_str
                ):
                    inner_data[kv.group(1)] = kv.group(2)

                # 배열 패턴: key: [ {...}, {...} ]
                for arr_match in re.finditer(
                    r"(\w+)\s*:\s*\[", inner_str
                ):
                    arr_key = arr_match.group(1)
                    arr_start = arr_match.end() - 1
                    arr_str = self._extract_balanced_bracket(
                        inner_str, arr_start
                    )
                    if arr_str:
                        arr_items = []
                        for item_match in re.finditer(r"\{([^}]+)\}", arr_str):
                            item = {}
                            for kv2 in re.finditer(
                                r"(\w+)\s*:\s*['\"]([^'\"]*)['\"]",
                                item_match.group(1),
                            ):
                                item[kv2.group(1)] = kv2.group(2)
                            if item:
                                arr_items.append(item)
                        if arr_items:
                            inner_data[arr_key] = arr_items

                if inner_data:
                    result[key] = inner_data

        return result if result else None

    def _extract_balanced_bracket(self, text: str, start: int) -> str | None:
        """대괄호 균형을 맞춰 배열 전체 문자열을 추출"""
        depth = 0
        in_string = False
        string_char = None
        i = start

        while i < len(text):
            ch = text[i]
            if in_string:
                if ch == "\\" and i + 1 < len(text):
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
            else:
                if ch in ("'", '"', "`"):
                    in_string = True
                    string_char = ch
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
            i += 1
        return None

    def _extract_text_content(self) -> list[dict]:
        """HTML에서 의미 있는 텍스트 콘텐츠를 계층별로 추출"""
        text_items = []

        # 주요 텍스트 요소 패턴
        patterns = [
            ("heading", r"<h([1-6])[^>]*>(.*?)</h\1>"),
            ("paragraph", r"<p[^>]*>(.*?)</p>"),
            ("span", r'<span[^>]*class="([^"]*)"[^>]*>(.*?)</span>'),
            ("div_text", r'<div[^>]*class="([^"]*(?:title|sub|label|value|badge|full|name)[^"]*)"[^>]*>(.*?)</div>'),
        ]

        for ptype, pattern in patterns:
            for m in re.finditer(pattern, self.html_content, re.DOTALL):
                if ptype == "heading":
                    level = m.group(1)
                    text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    if text:
                        text_items.append(
                            {"type": f"h{level}", "text": text}
                        )
                elif ptype == "paragraph":
                    text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                    if text:
                        text_items.append({"type": "p", "text": text})
                elif ptype in ("span", "div_text"):
                    cls = m.group(1)
                    text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    if text and len(text) > 0:
                        text_items.append(
                            {"type": ptype, "class": cls, "text": text}
                        )

        return text_items

    def _compute_statistics(self) -> dict:
        """파싱 결과 통계 계산"""
        stats = {
            "total_css_variables": len(self.result.get("css_variables", {})),
            "total_css_classes": len(self.result.get("css_classes", [])),
            "total_components": len(
                self.result.get("components", {}).get("cards", [])
            ),
            "total_sections": len(
                self.result.get("components", {}).get("sections", [])
            ),
            "total_flow_nodes": len(
                self.result.get("flow_diagram", {}).get("nodes", [])
            ),
            "total_js_objects": len(self.result.get("js_data_objects", {})),
            "total_text_items": len(self.result.get("text_content", [])),
            "html_size_bytes": self.result.get("file_size_bytes", 0),
        }
        return stats

    def save_json(self, output_path: str, indent: int = 2) -> str:
        """파싱 결과를 JSON 파일로 저장"""
        if not self.result:
            self.parse()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.result, f, ensure_ascii=False, indent=indent)

        print(f"[OK] JSON 저장 완료: {output_path}")
        return output_path

    def to_json_string(self, indent: int = 2) -> str:
        """파싱 결과를 JSON 문자열로 반환"""
        if not self.result:
            self.parse()
        return json.dumps(self.result, ensure_ascii=False, indent=indent)


class _StructureParser(HTMLParser):
    """HTML DOM 계층 구조를 추출하는 내부 파서"""

    SKIP_TAGS = {"script", "style", "link", "meta", "br", "hr", "img", "input"}
    IMPORTANT_ATTRS = {"class", "id", "data-cat", "data-type", "role", "onclick"}

    def __init__(self):
        super().__init__()
        self.structure = []
        self.stack = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            return

        attrs_dict = dict(attrs)
        filtered = {k: v for k, v in attrs_dict.items() if k in self.IMPORTANT_ATTRS}

        node = {
            "tag": tag,
            "depth": self.depth,
        }
        if filtered:
            node["attributes"] = filtered

        if self.stack:
            parent = self.stack[-1]
            if "children" not in parent:
                parent["children"] = []
            parent["children"].append(node)
        else:
            self.structure.append(node)

        self.stack.append(node)
        self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            return
        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()
            self.depth -= 1

    def handle_data(self, data):
        text = data.strip()
        if text and self.stack:
            self.stack[-1]["text"] = text
