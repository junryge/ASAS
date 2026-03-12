# -*- coding: utf-8 -*-
"""데이터취합 m14.py - draw.io 호환 XML 생성기
실행하면 .drawio 파일이 생성되어 draw.io 에서 바로 열 수 있습니다.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import uuid


class DrawIOGenerator:
    """draw.io 호환 XML 생성기"""

    def __init__(self, width=1169, height=827):
        self.width = width
        self.height = height

        self.styles = {
            'input': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE4B5;strokeColor=#000000;fontColor=#000000;align=center;verticalAlign=middle;',
            'process': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#ADD8E6;strokeColor=#000000;fontColor=#000000;align=center;verticalAlign=middle;',
            'merge': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#DDA0DD;strokeColor=#000000;fontColor=#000000;align=center;verticalAlign=middle;',
            'output': 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFB6C1;strokeColor=#000000;fontColor=#000000;align=center;verticalAlign=middle;',
            'stats': 'shape=note;whiteSpace=wrap;html=1;fillColor=#F0F0F0;strokeColor=#000000;fontColor=#000000;align=center;verticalAlign=middle;size=15;',
        }

    def create_mxfile(self, diagram_name="데이터흐름도"):
        mxfile = ET.Element("mxfile")
        mxfile.set("host", "app.diagrams.net")
        mxfile.set("modified", datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        mxfile.set("agent", "Python Script")
        mxfile.set("version", "21.0.0")
        mxfile.set("type", "device")

        diagram = ET.SubElement(mxfile, "diagram")
        diagram.set("id", str(uuid.uuid4()))
        diagram.set("name", diagram_name)

        return mxfile, diagram

    def create_graph_model(self, diagram):
        graph_model = ET.SubElement(diagram, "mxGraphModel")
        graph_model.set("dx", str(self.width))
        graph_model.set("dy", str(self.height))
        graph_model.set("grid", "1")
        graph_model.set("gridSize", "10")
        graph_model.set("guides", "1")
        graph_model.set("tooltips", "1")
        graph_model.set("connect", "1")
        graph_model.set("arrows", "1")
        graph_model.set("fold", "1")
        graph_model.set("page", "1")
        graph_model.set("pageScale", "1")
        graph_model.set("pageWidth", str(self.width))
        graph_model.set("pageHeight", str(self.height))
        graph_model.set("math", "0")
        graph_model.set("shadow", "0")

        root = ET.SubElement(graph_model, "root")

        # Draw.io 필수: id="0" 루트셀 + id="1" 기본 레이어
        cell0 = ET.SubElement(root, "mxCell")
        cell0.set("id", "0")

        cell1 = ET.SubElement(root, "mxCell")
        cell1.set("id", "1")
        cell1.set("parent", "0")

        return root

    def create_vertex(self, root, cell_id, label, x, y, width, height, style_name):
        cell = ET.SubElement(root, "mxCell")
        cell.set("id", cell_id)
        cell.set("value", label)
        cell.set("vertex", "1")
        cell.set("parent", "1")

        style = self.styles.get(style_name, self.styles['process'])
        cell.set("style", style)

        geometry = ET.SubElement(cell, "mxGeometry")
        geometry.set("x", str(x))
        geometry.set("y", str(y))
        geometry.set("width", str(width))
        geometry.set("height", str(height))
        geometry.set("as", "geometry")

        return cell

    def create_edge(self, root, cell_id, source_id, target_id, label=""):
        cell = ET.SubElement(root, "mxCell")
        cell.set("id", cell_id)
        cell.set("value", label)
        cell.set("edge", "1")
        cell.set("parent", "1")
        cell.set("source", source_id)
        cell.set("target", target_id)
        cell.set("style", "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jetSize=auto;html=1;endArrow=blockThin;endFill=1;")

        geometry = ET.SubElement(cell, "mxGeometry")
        geometry.set("relative", "1")
        geometry.set("as", "geometry")

        return cell

    def prettify(self, mxfile):
        rough_string = ET.tostring(mxfile, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        lines = reparsed.toprettyxml(indent="  ").split('\n')
        # minidom의 <?xml ?> 선언 제거 (Draw.io는 없어도 됨, 있어도 됨)
        return '\n'.join(lines)

    def save(self, filename, mxfile):
        xml_string = self.prettify(mxfile)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        print(f"  저장 완료: {filename}")
        return filename


def create_data_flow_drawio():
    """메인 파이프라인 draw.io 다이어그램 생성"""

    gen = DrawIOGenerator(width=1169, height=827)
    mxfile, diagram = gen.create_mxfile("데이터취합_파이프라인")
    root = gen.create_graph_model(diagram)

    node_x = 400
    node_width = 300
    node_height = 80
    node_spacing = 120
    start_y = 80

    nodes = [
        {"id": "2", "label": "입력 CSV\nR3_20251101_20260131.CSV", "style": "input"},
        {"id": "3", "label": "인코딩 감지\nutf-8 -> cp949 -> euc-kr", "style": "process"},
        {"id": "4", "label": "컬럼 정리\n공백/특수문자 제거\nUnnamed 컬럼 제거", "style": "process"},
        {"id": "5", "label": "CRT_TM 병합\ngroupby + first()", "style": "merge"},
        {"id": "6", "label": "출력 CSV\nR3_20251101_20260131_ASP.csv", "style": "output"},
    ]

    for i, node_info in enumerate(nodes):
        y_pos = start_y + (i * node_spacing)
        gen.create_vertex(
            root=root,
            cell_id=node_info["id"],
            label=node_info["label"],
            x=node_x,
            y=y_pos,
            width=node_width,
            height=node_height,
            style_name=node_info["style"]
        )

    # 통계 정보 노드 (옆에 배치)
    gen.create_vertex(
        root=root,
        cell_id="7",
        label="통계 정보\n- 원본 행 수\n- 유니크 CRT_TM 개수\n- 병합 후 행 수",
        x=800,
        y=start_y + (3 * node_spacing),
        width=200,
        height=100,
        style_name="stats"
    )

    edges = [
        {"id": "10", "source": "2", "target": "3", "label": "파일 로드"},
        {"id": "11", "source": "3", "target": "4", "label": "DataFrame 생성"},
        {"id": "12", "source": "4", "target": "5", "label": "정제된 데이터"},
        {"id": "13", "source": "5", "target": "6", "label": "병합 결과 저장"},
        {"id": "14", "source": "5", "target": "7", "label": "로그 출력"},
    ]

    for edge_info in edges:
        gen.create_edge(
            root=root,
            cell_id=edge_info["id"],
            source_id=edge_info["source"],
            target_id=edge_info["target"],
            label=edge_info["label"]
        )

    return gen, mxfile


def create_detail_flow_drawio():
    """상세 처리 로직 draw.io 다이어그램 생성"""

    gen = DrawIOGenerator(width=1400, height=600)
    mxfile, diagram = gen.create_mxfile("상세처리_로직")
    root = gen.create_graph_model(diagram)

    # 인코딩 감지 단계
    enc_y = 80
    enc_x_start = 100
    enc_spacing = 200

    enc_nodes = [
        ("20", "utf-8 시도", enc_x_start),
        ("21", "cp949 시도", enc_x_start + enc_spacing),
        ("22", "euc-kr 시도", enc_x_start + enc_spacing * 2),
    ]

    for cell_id, label, x_pos in enc_nodes:
        gen.create_vertex(
            root=root,
            cell_id=cell_id,
            label=label,
            x=x_pos,
            y=enc_y,
            width=150,
            height=60,
            style_name="process"
        )

    gen.create_edge(root, "30", "20", "21", "실패시")
    gen.create_edge(root, "31", "21", "22", "실패시")

    # 컬럼 정리 단계
    clean_y = 250
    clean_nodes = [
        ("40", "컬럼명 정제\nstrip() + replace()", 100),
        ("41", "Unnamed 제거\n정규식 필터링", 300),
        ("42", "CRT_TM 정제\n타입 변환", 500),
    ]

    for cell_id, label, x_pos in clean_nodes:
        gen.create_vertex(
            root=root,
            cell_id=cell_id,
            label=label,
            x=x_pos,
            y=clean_y,
            width=150,
            height=70,
            style_name="process"
        )

    gen.create_edge(root, "50", "40", "41", "")
    gen.create_edge(root, "51", "41", "42", "")

    # 병합 단계
    merge_y = 420
    merge_nodes = [
        ("60", "groupby\nCRT_TM 기준", 100),
        ("61", "first()\n첫 번째 값 선택", 300),
        ("62", "reset_index\n인덱스 재설정", 500),
    ]

    for cell_id, label, x_pos in merge_nodes:
        gen.create_vertex(
            root=root,
            cell_id=cell_id,
            label=label,
            x=x_pos,
            y=merge_y,
            width=150,
            height=70,
            style_name="merge"
        )

    gen.create_edge(root, "70", "60", "61", "")
    gen.create_edge(root, "71", "61", "62", "")
    gen.create_edge(root, "80", "22", "40", "성공시")
    gen.create_edge(root, "81", "42", "60", "")

    # 제목
    title = ET.SubElement(root, "mxCell")
    title.set("id", "90")
    title.set("value", "상세 처리 로직 흐름도")
    title.set("vertex", "1")
    title.set("parent", "1")
    title.set("style", "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=18;fontStyle=1;")

    title_geo = ET.SubElement(title, "mxGeometry")
    title_geo.set("x", "350")
    title_geo.set("y", "20")
    title_geo.set("width", "300")
    title_geo.set("height", "30")
    title_geo.set("as", "geometry")

    return gen, mxfile


if __name__ == "__main__":
    print("=" * 60)
    print("데이터취합 m14.py - draw.io 흐름도 생성기")
    print("=" * 60)

    try:
        print("\n[1/2] 메인 파이프라인 생성 중...")
        gen1, pipeline_mxfile = create_data_flow_drawio()
        gen1.save("데이터흐름도_파이프라인.drawio", pipeline_mxfile)

        print("\n[2/2] 상세 처리 로직 생성 중...")
        gen2, detail_mxfile = create_detail_flow_drawio()
        gen2.save("데이터흐름도_상세로직.drawio", detail_mxfile)

        print("\n" + "=" * 60)
        print("draw.io 파일 생성 완료!")
        print("=" * 60)
        print("\n생성된 파일:")
        print("  1. 데이터흐름도_파이프라인.drawio")
        print("  2. 데이터흐름도_상세로직.drawio")
        print("\n사용 방법:")
        print("  1. https://app.diagrams.net/ 접속")
        print("  2. 파일 -> 열기 -> 장치에서 선택")
        print("  3. 생성된 .drawio 파일 선택")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
