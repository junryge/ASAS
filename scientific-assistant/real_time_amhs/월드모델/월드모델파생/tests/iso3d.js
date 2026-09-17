/* 3D 아이소메트리 — dashboard.html 의 '3D 아이소메트리' 절을 **그대로 떼어** 돌린다.
   (tests/hmi_map.js 와 같은 수법. 베낀 코드가 아니라 배포되는 그 코드를 본다.)
   three.js 는 WebGL 이 있어야 돌므로 여기서는 3D 뷰어 자체가 아니라, 2D 데이터를
   3D 입력으로 바꾸는 층(layout3D · vehicle3D · state3D)을 본다.

   ★지키는 규칙
     · 차량 색 판정 순서는 2D drawMap 과 같다 — 7 JAM · 6 OBS · 2/8/9 정지 · 적재 · 공차
     · 엣지 id = 'from-to', 존은 IN/OUT 레인을 같은 꼴로 잇는다
     · 포트는 종류 9(오른쪽)·8(왼쪽)만, 법선 방향으로 띄우고, 정면은 레일을 본다
     · 도면 단위 → m 는 0.01 (실물 M14A: 1 단위 = 10 mm) */
const fs = require('fs'), path = require('path');
const H = fs.readFileSync(path.join(__dirname, '..', 'dashboard.html'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };
const grab = re => { const m = H.match(re); ok(m, '못 찾음: ' + re); return m ? m[0] : ''; };

const src = grab(/const DEFAULT_MAP_SETTINGS = \{[\s\S]*?\n\};/) + '\nvar mapSettings = { ...DEFAULT_MAP_SETTINGS };\n'
  + 'var show3D=false, v3d=null, v3dLoading=null, v3dLayoutSig="", railGraph=null, railGeom=null, currentFab="M14A", currentPrefix="A", mapData={vehicles:[]};\n'
  + 'function mapPal(){ return {bg:"#eceef2"}; }\n'
  + grab(/function buildRailGeom\(g\) \{[\s\S]*?\n\}/) + '\n'
  + grab(/\/\/ ===== 3D 아이소메트리 \(시작\) =====[\s\S]*?\/\/ ===== 3D 아이소메트리 \(끝\) =====/);
eval(src.replace(/\bconst (DEFAULT_MAP_SETTINGS|V3D_SCALE)\b/g, 'var $1'));

/* ── 도면 단위 ── */
ok(V3D_SCALE === 0.01, '도면 1 단위 = 10 mm → coordScale 0.01 (실물 M14A 에서 잰 값)');

/* ── 차량 상태 → 3D 상태 (2D 색 규칙과 같은 순서) ── */
ok(state3D({ state: 7, isFull: true }) === 3, 'JAM(7) 은 적재여도 3');
ok(state3D({ state: 6, isFull: false }) === 4, 'OBS(6) 는 4 — JAM 과 다른 색이어야 한다');
ok(state3D({ state: 2 }) === 2 && state3D({ state: 8 }) === 2 && state3D({ state: 9 }) === 2, '2/8/9 는 정지');
ok(state3D({ state: 1, isFull: true }) === 1, '달리는데 적재면 1');
ok(state3D({ state: 1, isFull: false }) === 0, '달리는데 공차면 0');
ok(state3D({ state: 0 }) === 0, '모르는 코드 0 은 공차운행');
/* 3D 색 순서 = 3D 상태 순서. 설정창 색이 그대로 간다 */
const col = v3dColors();
ok(col.length === 5, '색 다섯');
ok(col[0] === mapSettings.colorEmpty && col[1] === mapSettings.colorLoaded && col[2] === mapSettings.colorStop
   && col[3] === mapSettings.colorJam && col[4] === mapSettings.colorObs, '색 순서 = 공차·적재·정지·JAM·OBS');

/* ── 차량 한 대 ── */
const r = vehicle3D({ vid: 'V0001', x: 10.5, y: 20.5, state: 6, isFull: true, velocity: 123.4, currentNode: 4436, nextNode: 4437, ratio: 0.25 });
ok(r.id === 'V0001', 'id');
ok(r.from === '4436' && r.to === '4437', 'from/to 는 글자 — 3D 는 문자열로 찾는다');
ok(r.ratio === 0.25 && r.x === 10.5 && r.y === 20.5, 'ratio 와 좌표 둘 다 — 엣지를 못 찾으면 좌표로 떨어진다');
ok(r.speed_mpm === 123.4 && r.state === 4 && r.loaded === true, '속도·상태·적재');
const r0 = vehicle3D({ vid: 'V2', x: 1, y: 2, state: 1, isFull: false, currentNode: 0, nextNode: 0 });
ok(r0.from === null && r0.to === null && r0.ratio === null && r0.speed_mpm === 0, '주소 0 은 null — 좌표로만 놓는다');

/* ── 레이아웃 (tests/hmi_map.js 의 축약 루프 + 존) ── */
const G = { nodes: { '1':[100,100], '2':[100,160], '3':[129,194], '4':[200,194], '5':[300,194], '9':[100,40] },
  edges: [[9,1],[1,2],[2,3],[3,4],[4,5],[1,2],[4,4],[1,77]],
  zones: [{ id: 26, name: 'HID-B19-1(026)', inLanes: [{from:9,to:1},{from:1,to:2}], outLanes: [{from:4,to:5}] },
          { id: 27, name: '', inLanes: [{from:2,to:3}], outLanes: [] }],
  stations: [[1, 2, 0.5, 9, 17001, 'R'], [1, 2, 0.5, 8, 27001, 'L'], [1, 2, 0.5, 9, 17002, 'R2'],
             [3, 4, 0.5, 1, 4904, 'PSA'], [4, 5, 0.5, 5, 4905, 'ON']],
  labels: [], sensors: [] };
const geom = buildRailGeom(G);
const L = layout3D(G, geom);
ok(L.nodes.length === 6 && L.nodes.every(n => typeof n.id === 'string'), '노드 6개, id 는 글자');
ok(L.edges.length === 5, '엣지: 중복([1,2]) · 자기자신([4,4]) · 없는 노드([1,77]) 를 뺀 5개 → ' + L.edges.length);
ok(L.edges.some(e => e.id === '9-1' && e.from === '9' && e.to === '1'), "엣지 id 는 'from-to'");
ok(L.zones.length === 2 && L.zones[0].id === 'HID-B19-1(026)', '존 이름은 HID 마스터 Full_Name');
ok(L.zones[1].id === 'HID 27', '이름이 없으면 HID 번호');
ok(JSON.stringify(L.zones[0].edges) === JSON.stringify(['9-1','1-2','4-5']), 'IN + OUT 레인 → 엣지 id (' + JSON.stringify(L.zones[0].edges) + ')');

/* 포트: 9·8 만, 레일 위(1/5)는 없다. 같은 자리 두 개(17001·17002)는 하나로 */
ok(L.ports.length === 2, '포트 2개 (오른쪽 하나·왼쪽 하나) → ' + L.ports.length);
// 1→2 는 아래로 가는 세로 레일 (y 증가). 진행 방향 (0,1), 오른쪽 법선 = (-ty, tx) = (-1, 0) → 오른쪽 포트는 x 가 작다
const R = L.ports.find(p => p.x < 100), Lp = L.ports.find(p => p.x > 100);
ok(R && Lp, '오른쪽(9)은 법선 +, 왼쪽(8)은 법선 −');
ok(Math.abs(R.x - (100 - 170)) < 1e-6 && Math.abs(R.y - 130) < 1e-6, '띄우는 거리 1.7 m = 도면 170 단위 (' + R.x + ',' + R.y + ')');
// 정면(+x 방향, 각 rot)은 레일을 봐야 한다 — 포트에서 레일 쪽 = 법선의 반대
const face = p => [Math.cos(p.rot), Math.sin(p.rot)];
ok(face(R)[0] > 0.99, '오른쪽 포트 정면은 +x (레일 쪽) → ' + face(R));
ok(face(Lp)[0] < -0.99, '왼쪽 포트 정면은 −x (레일 쪽) → ' + face(Lp));
ok(L.ports.every(p => p.kind === 'eq' && p.w > 0 && p.d > 0 && p.h > 0 && p.loadport === false), '설비 상자 크기·종류');

/* ── push3D 는 안 켜져 있으면 아무것도 안 한다 ── */
let called = 0;
v3d = { setVehicles: () => { called++; } };
show3D = false; push3D({}); ok(called === 0, '3D 꺼져 있으면 setVehicles 안 부른다');
show3D = true; mapData.vehicles = [{ vid: 'V1', x: 1, y: 2, state: 1 }]; push3D({ time: '2026-04-07 07:44:16' });
ok(called === 1, '켜져 있으면 프레임마다 한 번');

/* ── sync3DLayout 은 같은 맵이면 다시 안 세운다 ── */
let built = 0;
v3d = { setLayout: () => { built++; }, setVehicles: () => {} };
railGraph = G; railGeom = geom; v3dLayoutSig = '';
sync3DLayout(); sync3DLayout();
ok(built === 1, '같은 맵 두 번 → setLayout 한 번 (' + built + ')');
currentFab = 'M16A'; sync3DLayout();
ok(built === 2, 'FAB 이 바뀌면 다시 세운다');

console.log(bad ? ('FAILED ' + bad) : 'OK');
process.exit(bad ? 1 : 0);
