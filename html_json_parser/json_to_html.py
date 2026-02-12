"""
JSON -> HTML 생성기

JSON 데이터에서 SK Hynix 스타일의 인터랙티브 HTML 페이지를 생성합니다.

사용법:
  from json_to_html import HTMLGenerator
  gen = HTMLGenerator(json_data)
  html = gen.generate()
  gen.save("output.html")
"""

import json
import os
from typing import Any


# 기본 색상 팔레트
DEFAULT_COLORS = {
    "bg": "#0a0e1a",
    "card": "#111827",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "muted": "#64748b",
    "blue": "#3b82f6",
    "cyan": "#06b6d4",
    "purple": "#8b5cf6",
    "amber": "#f59e0b",
    "emerald": "#10b981",
    "rose": "#f43f5e",
    "orange": "#f97316",
    "sky": "#0ea5e9",
}

# 카테고리별 색상 매핑
CATEGORY_COLORS = {
    "oht": "blue", "mcs": "purple", "stk": "emerald", "cnv": "sky",
    "lft": "orange", "inv": "rose", "que": "amber", "rtc": "#a78bfa",
    "foup": "#34d399", "pdt": "#fb923c", "fio": "#94a3b8",
}


class HTMLGenerator:
    """JSON 데이터에서 HTML 페이지를 생성"""

    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def load_json(self, json_path: str):
        """JSON 파일에서 데이터 로드"""
        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self

    def generate(self, title: str = "", theme: dict | None = None) -> str:
        """전체 HTML 페이지 생성"""
        colors = {**DEFAULT_COLORS, **(self.data.get("css_variables", {}))}
        if theme:
            colors.update(theme)

        meta = self.data.get("metadata", {})
        page_title = title or meta.get("title", "Generated Layout")
        lang = meta.get("lang", "ko")

        components = self.data.get("components", {})
        cards = components.get("cards", [])
        sections = components.get("sections", [])
        flow = self.data.get("flow_diagram", {})
        js_data = self.data.get("js_data_objects", {})

        html_parts = [
            self._gen_doctype(lang, page_title, colors),
            self._gen_header(page_title, meta),
        ]

        # 섹션이 있으면 섹션 기반 레이아웃
        if sections:
            html_parts.append(self._gen_sections_layout(sections, cards, colors))
        elif cards:
            html_parts.append(self._gen_cards_grid(cards, colors))

        # 상세 패널
        if js_data.get("details"):
            html_parts.append(self._gen_detail_panel())

        # 플로우 다이어그램
        if flow.get("nodes"):
            html_parts.append(self._gen_flow_diagram(flow, colors))

        # JavaScript
        html_parts.append(self._gen_script(js_data))

        # 푸터 & 닫기
        html_parts.append(self._gen_footer(page_title))

        return "\n".join(html_parts)

    def save(self, output_path: str, title: str = "", theme: dict | None = None) -> str:
        """HTML 파일로 저장"""
        html = self.generate(title=title, theme=theme)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] HTML 저장: {output_path} ({len(html):,} bytes)")
        return output_path

    # ── 내부 생성 메서드 ──

    def _gen_doctype(self, lang: str, title: str, colors: dict) -> str:
        css_vars = "\n".join(f"            --{k}: {v};" for k, v in colors.items())
        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
{css_vars}
        }}
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background:
                linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; position: relative; z-index: 1; }}
        .header {{ text-align: center; margin-bottom: 50px; }}
        .header-badge {{
            display: inline-block; padding: 6px 16px;
            background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3);
            border-radius: 20px; font-size: 12px; font-weight: 500; color: var(--blue);
            letter-spacing: 2px; text-transform: uppercase; margin-bottom: 16px;
            font-family: 'JetBrains Mono', monospace;
        }}
        .header h1 {{
            font-size: 2.8rem; font-weight: 900;
            background: linear-gradient(135deg, #3b82f6, #06b6d4, #8b5cf6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 12px; letter-spacing: -1px;
        }}
        .header p {{ color: var(--muted); font-size: 1rem; font-weight: 300; }}
        .wrapper {{
            background: linear-gradient(135deg, rgba(59,130,246,0.08), rgba(139,92,246,0.08));
            border: 1px solid rgba(59,130,246,0.2); border-radius: 20px;
            padding: 30px; margin-bottom: 30px; position: relative; overflow: hidden;
        }}
        .section-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px; position: relative;
        }}
        .section-box {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; transition: all 0.3s;
        }}
        .section-box:hover {{ border-color: rgba(59,130,246,0.4); box-shadow: 0 0 30px rgba(59,130,246,0.1); }}
        .section-header {{
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid var(--border);
        }}
        .section-name {{ font-size: 1.3rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
        .section-badge {{
            padding: 4px 12px; border-radius: 12px; font-size: 11px;
            font-weight: 600; font-family: 'JetBrains Mono', monospace;
        }}
        .comp-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .comp-card {{
            padding: 14px; background: rgba(255,255,255,0.02);
            border: 1px solid var(--border); border-radius: 10px;
            cursor: pointer; transition: all 0.25s; position: relative; overflow: hidden;
        }}
        .comp-card::before {{
            content: ''; position: absolute; top: 0; left: 0;
            width: 3px; height: 100%; border-radius: 3px 0 0 3px; transition: all 0.25s;
        }}
        .comp-card:hover {{ transform: translateY(-2px); background: rgba(255,255,255,0.04); }}
        .comp-card.active {{ background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.15); }}
        .comp-emoji {{ font-size: 22px; margin-bottom: 6px; }}
        .comp-name {{ font-size: 13px; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-bottom: 2px; }}
        .comp-full {{ font-size: 10px; color: var(--muted); font-weight: 300; }}
        .detail-panel {{ margin-top: 30px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; transition: all 0.3s; }}
        .detail-panel.hidden {{ opacity: 0; max-height: 0; margin-top: 0; border: none; }}
        .detail-header {{ padding: 20px 24px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid var(--border); }}
        .detail-icon {{ width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; }}
        .detail-title {{ font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
        .detail-subtitle {{ font-size: 0.85rem; color: var(--muted); }}
        .detail-body {{ padding: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .detail-item {{ padding: 14px; background: rgba(255,255,255,0.02); border-radius: 10px; border: 1px solid var(--border); }}
        .detail-item-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
        .detail-item-value {{ font-size: 14px; font-weight: 500; line-height: 1.6; }}
        .flow-section {{ margin-top: 30px; padding: 28px; background: var(--card); border: 1px solid var(--border); border-radius: 16px; }}
        .flow-title {{ font-size: 1rem; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }}
        .flow-diagram {{ display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; padding: 20px; }}
        .flow-node {{
            padding: 12px 20px; border-radius: 10px; font-size: 13px;
            font-weight: 600; text-align: center; min-width: 100px;
        }}
        .flow-arrow {{ font-size: 20px; color: var(--muted); animation: flowPulse 2s ease-in-out infinite; }}
        @keyframes flowPulse {{ 0%, 100% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} }}
        .footer {{ text-align: center; margin-top: 40px; padding: 20px; color: var(--muted); font-size: 12px; font-weight: 300; }}
        @media (max-width: 768px) {{
            .section-grid {{ grid-template-columns: 1fr; }}
            .detail-body {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 2rem; }}
            .flow-diagram {{ flex-direction: column; }}
            .flow-arrow {{ transform: rotate(90deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">"""

    def _gen_header(self, title: str, meta: dict) -> str:
        badge = meta.get("badge", "SK Hynix System Architecture")
        subtitle = meta.get("subtitle", "")
        # title에서 subtitle 추출 시도
        if not subtitle:
            parts = title.split(" - ")
            if len(parts) > 1:
                subtitle = parts[1]

        return f"""
        <!-- 헤더 -->
        <div class="header">
            <div class="header-badge">{badge}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>"""

    def _gen_sections_layout(self, sections: list, cards: list, colors: dict) -> str:
        cards_by_cat = {c.get("category", c.get("name", "")): c for c in cards}

        html = '\n        <div class="wrapper">\n            <div class="section-grid">'

        for idx, section in enumerate(sections):
            name = section.get("name", f"Section {idx+1}")
            badge = section.get("badge", "")
            comp_list = section.get("components", [])
            color_class = "color: var(--cyan);" if idx == 0 else "color: var(--amber);"
            badge_bg = "rgba(6,182,212,0.15)" if idx == 0 else "rgba(249,158,11,0.15)"
            badge_color = "var(--cyan)" if idx == 0 else "var(--amber)"

            html += f"""
                <div class="section-box">
                    <div class="section-header">
                        <span class="section-name" style="{color_class}">{name}</span>
                        <span class="section-badge" style="background:{badge_bg};color:{badge_color};border:1px solid {badge_color}40;">{badge}</span>
                    </div>
                    <div class="comp-grid">"""

            for cat in comp_list:
                card = cards_by_cat.get(cat, {})
                emoji = card.get("emoji", "")
                card_name = card.get("name", cat.upper())
                full_name = card.get("full_name", "")
                cat_color = CATEGORY_COLORS.get(cat, "blue")
                # CSS 변수인지 직접 색상인지 판단
                if cat_color.startswith("#"):
                    bar_style = f"background:{cat_color};"
                    hover_border = cat_color
                else:
                    bar_style = f"background:var(--{cat_color});"
                    hover_border = f"var(--{cat_color})"

                html += f"""
                        <div class="comp-card" data-cat="{cat}" onclick="showDetail('{cat}')"
                             style="--card-color:{hover_border};"
                             onmouseenter="this.style.borderColor='{hover_border}'"
                             onmouseleave="this.style.borderColor='var(--border)'">
                            <div style="position:absolute;top:0;left:0;width:3px;height:100%;{bar_style}border-radius:3px 0 0 3px;"></div>
                            <div class="comp-emoji">{emoji}</div>
                            <div class="comp-name">{card_name}</div>
                            <div class="comp-full">{full_name}</div>
                        </div>"""

            html += """
                    </div>
                </div>"""

        html += """
            </div>
        </div>"""
        return html

    def _gen_cards_grid(self, cards: list, colors: dict) -> str:
        html = '        <div class="wrapper">\n            <div class="comp-grid" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr));">'
        for card in cards:
            cat = card.get("category", "")
            emoji = card.get("emoji", "")
            name = card.get("name", "")
            full_name = card.get("full_name", "")
            html += f"""
                <div class="comp-card" data-cat="{cat}" onclick="showDetail('{cat}')">
                    <div class="comp-emoji">{emoji}</div>
                    <div class="comp-name">{name}</div>
                    <div class="comp-full">{full_name}</div>
                </div>"""
        html += "\n            </div>\n        </div>"
        return html

    def _gen_detail_panel(self) -> str:
        return """
        <!-- 상세 패널 -->
        <div class="detail-panel hidden" id="detailPanel">
            <div class="detail-header" id="detailHeader">
                <div class="detail-icon" id="detailIcon"></div>
                <div>
                    <div class="detail-title" id="detailTitle"></div>
                    <div class="detail-subtitle" id="detailSubtitle"></div>
                </div>
            </div>
            <div class="detail-body" id="detailBody"></div>
        </div>"""

    def _gen_flow_diagram(self, flow: dict, colors: dict) -> str:
        title = flow.get("title", "Flow Diagram")
        nodes = flow.get("nodes", [])

        html = f"""
        <!-- 플로우 다이어그램 -->
        <div class="flow-section">
            <div class="flow-title">{title}</div>
            <div class="flow-diagram">"""

        for i, node in enumerate(nodes):
            ntype = node.get("type", "")
            main_text = node.get("main_text", "")
            sub_label = node.get("sub_label", "")
            cat_color = CATEGORY_COLORS.get(ntype, "blue")

            if cat_color.startswith("#"):
                bg = f"{cat_color}26"
                border = f"{cat_color}66"
                color = cat_color
            else:
                bg = f"var(--{cat_color})"
                border = f"var(--{cat_color})"
                color = f"var(--{cat_color})"

            html += f"""
                <div class="flow-node" style="background:rgba(59,130,246,0.15);border:1px solid {border};color:{color};">
                    {main_text}
                    <small style="display:block;font-size:10px;font-weight:400;opacity:0.7;margin-top:2px;">{sub_label}</small>
                </div>"""

            if i < len(nodes) - 1:
                html += '\n                <div class="flow-arrow">&rarr;</div>'

        html += """
            </div>
        </div>"""
        return html

    def _gen_script(self, js_data: dict) -> str:
        details = js_data.get("details", {})
        if not details:
            return ""

        # details 객체를 JS로 변환
        details_js = json.dumps(details, ensure_ascii=False, indent=8)

        return f"""
    <script>
        const details = {details_js};

        function showDetail(cat) {{
            const panel = document.getElementById('detailPanel');
            const d = details[cat];
            if (!d) return;

            document.querySelectorAll('.comp-card').forEach(c => c.classList.remove('active'));
            document.querySelectorAll(`.comp-card[data-cat="${{cat}}"]`).forEach(c => c.classList.add('active'));

            document.getElementById('detailIcon').textContent = d.emoji || '';
            document.getElementById('detailIcon').style.background = (d.color || '#3b82f6') + '20';
            document.getElementById('detailTitle').textContent = d.name || cat;
            document.getElementById('detailTitle').style.color = d.color || '#3b82f6';
            document.getElementById('detailSubtitle').textContent = d.full || '';

            const body = document.getElementById('detailBody');
            const items = d.items || [];
            body.innerHTML = items.map(item => `
                <div class="detail-item">
                    <div class="detail-item-label">${{item.label}}</div>
                    <div class="detail-item-value">${{item.value}}</div>
                </div>
            `).join('');

            panel.classList.remove('hidden');
            panel.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}
    </script>"""

    def _gen_footer(self, title: str) -> str:
        return f"""
        <div class="footer">
            {title} &middot; Generated by HTML Layout Parser
        </div>
    </div>
</body>
</html>"""
