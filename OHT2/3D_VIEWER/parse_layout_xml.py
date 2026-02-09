#!/usr/bin/env python3
"""
Layout XML → 3D HTML 변환기
OHT 레이아웃 XML 파일을 파싱하여 3D 시각화 HTML 생성
그냥 클릭해서 열 수 있음!
"""

import xml.etree.ElementTree as ET
import json
import zipfile
import os
import sys

def parse_layout_xml(xml_path_or_zip):
    """XML 파일 파싱하여 노드와 엣지 추출"""

    print(f"파싱 시작: {xml_path_or_zip}")

    # ZIP 파일이면 압축 해제
    if xml_path_or_zip.endswith('.zip'):
        with zipfile.ZipFile(xml_path_or_zip, 'r') as zf:
            xml_content = zf.read('layout.xml')
            root = ET.fromstring(xml_content)
    else:
        tree = ET.parse(xml_path_or_zip)
        root = tree.getroot()

    nodes = {}
    edges = []

    # AddrControl 내의 모든 Addr 그룹 찾기
    addr_control = root.find(".//group[@name='AddrControl']")
    if addr_control is None:
        print("AddrControl을 찾을 수 없습니다.")
        return nodes, edges

    for addr_group in addr_control.findall("group"):
        if not addr_group.get('name', '').startswith('Addr'):
            continue

        # 노드 정보 추출
        address = None
        draw_x = None
        draw_y = None

        for param in addr_group.findall("param"):
            key = param.get('key')
            value = param.get('value')

            if key == 'address':
                address = int(value)
            elif key == 'draw-x':
                draw_x = float(value)
            elif key == 'draw-y':
                draw_y = float(value)

        if address is not None and draw_x is not None and draw_y is not None:
            nodes[address] = {'id': address, 'x': draw_x, 'y': draw_y}

        # 엣지 정보 추출
        for next_addr_group in addr_group.findall("group"):
            if not next_addr_group.get('name', '').startswith('NextAddr'):
                continue

            for param in next_addr_group.findall("param"):
                if param.get('key') == 'next-address':
                    next_address = int(param.get('value'))
                    if address is not None and next_address > 0:
                        edges.append({'from': address, 'to': next_address})

    print(f"파싱 완료: {len(nodes)} 노드, {len(edges)} 엣지")
    return nodes, edges

def normalize_coords(nodes):
    """좌표 정규화 (0-1000 범위)"""
    if not nodes:
        return

    min_x = min(n['x'] for n in nodes.values())
    max_x = max(n['x'] for n in nodes.values())
    min_y = min(n['y'] for n in nodes.values())
    max_y = max(n['y'] for n in nodes.values())

    scale_x = 1000 / (max_x - min_x) if max_x != min_x else 1
    scale_y = 1000 / (max_y - min_y) if max_y != min_y else 1
    scale = min(scale_x, scale_y)

    for node in nodes.values():
        node['x'] = (node['x'] - min_x) * scale
        node['y'] = (node['y'] - min_y) * scale

def generate_html(nodes, edges, output_path):
    """데이터가 내장된 HTML 파일 생성"""

    data = {
        'nodes': list(nodes.values()),
        'edges': edges,
        'stats': {'nodeCount': len(nodes), 'edgeCount': len(edges)}
    }

    json_data = json.dumps(data)

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>OHT Layout 3D Viewer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #1a1a2e; overflow: hidden; font-family: 'Segoe UI', sans-serif; }}
        #container {{ width: 100vw; height: 100vh; }}
        #info {{
            position: fixed; top: 20px; left: 20px; color: #fff;
            background: rgba(0,0,0,0.7); padding: 20px; border-radius: 10px;
            font-size: 14px; z-index: 100; min-width: 200px;
        }}
        #info h1 {{ font-size: 18px; margin-bottom: 15px; color: #00d4ff; }}
        #info p {{ margin: 5px 0; }}
        #info .stat {{ color: #00ff88; }}
        #controls {{
            position: fixed; bottom: 20px; left: 20px; color: #fff;
            background: rgba(0,0,0,0.7); padding: 15px; border-radius: 10px; font-size: 12px;
        }}
        #controls p {{ margin: 3px 0; }}
    </style>
</head>
<body>
    <div id="info">
        <h1>OHT Layout 3D</h1>
        <p>노드: <span id="nodeCount" class="stat">{len(nodes):,}</span>개</p>
        <p>엣지: <span id="edgeCount" class="stat">{len(edges):,}</span>개</p>
        <p>FPS: <span id="fps" class="stat">0</span></p>
    </div>
    <div id="controls">
        <p>🖱️ 드래그: 회전</p>
        <p>🖱️ 우클릭 드래그: 이동</p>
        <p>🖱️ 스크롤: 줌</p>
        <p>⌨️ R: 리셋</p>
    </div>
    <div id="container"></div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        const layoutData = {json_data};

        let scene, camera, renderer, controls;
        let frameCount = 0, lastTime = performance.now();

        function init() {{
            const container = document.getElementById('container');

            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a2e);
            scene.fog = new THREE.Fog(0x1a1a2e, 500, 2000);

            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 5000);
            camera.position.set(500, 800, 500);
            camera.lookAt(500, 0, 500);

            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.target.set(500, 0, 500);

            const ambientLight = new THREE.AmbientLight(0x404040, 2);
            scene.add(ambientLight);
            const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
            directionalLight.position.set(500, 1000, 500);
            scene.add(directionalLight);

            const gridHelper = new THREE.GridHelper(1000, 50, 0x444444, 0x222222);
            scene.add(gridHelper);

            renderLayout();
            window.addEventListener('resize', onWindowResize);
            window.addEventListener('keydown', (e) => {{
                if (e.key === 'r' || e.key === 'R') {{
                    camera.position.set(500, 800, 500);
                    controls.target.set(500, 0, 500);
                }}
            }});
            animate();
        }}

        function renderLayout() {{
            const nodeMap = {{}};
            layoutData.nodes.forEach(node => {{ nodeMap[node.id] = node; }});

            const edgePositions = [];
            layoutData.edges.forEach(edge => {{
                const fromNode = nodeMap[edge.from];
                const toNode = nodeMap[edge.to];
                if (fromNode && toNode) {{
                    edgePositions.push(fromNode.x, 0, fromNode.y);
                    edgePositions.push(toNode.x, 0, toNode.y);
                }}
            }});

            const edgeGeometry = new THREE.BufferGeometry();
            edgeGeometry.setAttribute('position', new THREE.Float32BufferAttribute(edgePositions, 3));
            const edgeMaterial = new THREE.LineBasicMaterial({{ color: 0x00d4ff }});
            scene.add(new THREE.LineSegments(edgeGeometry, edgeMaterial));

            const nodeGeometry = new THREE.SphereGeometry(2, 8, 8);
            const nodeMaterial = new THREE.MeshPhongMaterial({{ color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 0.3 }});
            const instancedNodes = new THREE.InstancedMesh(nodeGeometry, nodeMaterial, layoutData.nodes.length);
            const matrix = new THREE.Matrix4();
            layoutData.nodes.forEach((node, i) => {{
                matrix.setPosition(node.x, 0, node.y);
                instancedNodes.setMatrixAt(i, matrix);
            }});
            scene.add(instancedNodes);
        }}

        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
            frameCount++;
            const now = performance.now();
            if (now - lastTime >= 1000) {{
                document.getElementById('fps').textContent = frameCount;
                frameCount = 0;
                lastTime = now;
            }}
        }}

        init();
    </script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML 저장: {output_path}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    else:
        xml_path = os.path.join(script_dir, 'layout.xml')
        if not os.path.exists(xml_path):
            xml_path = os.path.join(script_dir, 'layout.zip')

    if not os.path.exists(xml_path):
        print(f"파일을 찾을 수 없습니다: {xml_path}")
        print("사용법: python parse_layout_xml.py [layout.xml 또는 layout.zip]")
        print("또는 같은 폴더에 layout.xml 파일을 넣으세요.")
        sys.exit(1)

    nodes, edges = parse_layout_xml(xml_path)
    normalize_coords(nodes)

    output_path = os.path.join(script_dir, 'layout_3d.html')
    generate_html(nodes, edges, output_path)

    print(f"\n완료! layout_3d.html 파일을 더블클릭해서 열어!")

if __name__ == '__main__':
    main()
