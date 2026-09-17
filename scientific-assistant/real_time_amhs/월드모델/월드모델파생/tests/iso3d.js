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
  + 'var show3D=false, v3d=null, v3dLoading=null, v3dLayoutSig="", railGraph=null, railGeom=null, currentFab="M14A", currentPrefix="A", mapData={vehicles:[], blockedEdges:{}, hotspots:[]};\n'
  + 'var showZone=true, showRailCut=true, showId=false, showName=true, showStation=true, showLabel=true, showJunction=true, showSensor=false, showHotspot=true;\n'
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
  labels: [['B44', 1, 0, -30, 'bay'], ['ZC590A', 2, 20, 20, 'zc'], ['X', 77, 0, 0, 'bay']], sensors: [[150, 150, 0], [160, 194, 1]],
  meta: { '1': [2, 0, 0], '3': [1, 1, 0], '5': [0, 0, 1] } };
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

/* 노드 메타(글자방향·합류·분기) · 센서 · 라벨 — 표시 토글이 3D 에서도 먹으려면 재료가 가야 한다 */
const n3 = L.nodes.find(n => n.id === '3'), n5 = L.nodes.find(n => n.id === '5'), n1 = L.nodes.find(n => n.id === '1');
ok(n3.junction === true && n3.branch === false, '합류 노드(meta[1])');
ok(n5.branch === true && n5.junction === false, '분기 노드(meta[2])');
ok(n1.dir === 2 && n1.junction === false, '글자 방향(meta[0])');
ok(L.sensors.length === 2 && L.sensors[0].x === 150 && L.sensors[0].y === 150, '센서 좌표 그대로');
ok(L.labels.length === 2, '앵커 노드가 없는 라벨(77)은 뺀다 → ' + L.labels.length);
ok(L.labels[0].text === 'B44' && L.labels[0].x === 100 && L.labels[0].y === 70 && L.labels[0].kind === 'bay', '라벨 = 앵커 + (dx,dy) ' + JSON.stringify(L.labels[0]));

/* 차단 엣지 — 2D 의 'from_to' 를 3D 'from-to' 로, 반대 방향도 같이 (같은 레일이다) */
mapData.blockedEdges = { '1_2': { from: 1, to: 2 } };
ok(JSON.stringify(blocked3D()) === JSON.stringify(['1-2', '2-1']), '차단 엣지 양방향 → ' + JSON.stringify(blocked3D()));
mapData.blockedEdges = {};
ok(blocked3D().length === 0, '차단 없으면 빈 목록');

/* 핫스팟 — 좌표 없는 것은 빼고, 글자는 2D 와 같다 */
mapData.hotspots = [{ x: 10, y: 20, stopped: 5, severity: 'CRITICAL', kind: 'chain' }, { stopped: 3 }];
const hs = hotspots3D();
ok(hs.length === 1 && hs[0].text === '5대 (체인)' && hs[0].severity === 'CRITICAL', '핫스팟 → ' + JSON.stringify(hs));
ok(hs[0].r === 2 + 5 * 0.6, '반지름 = 2 + 정지대수×0.6');
mapData.hotspots = [];

/* 표시 토글 → 3D 레이어 이름 */
let got = null;
v3d = { setLayers: l => { got = l; }, setVehicles: () => {}, setBlocked: () => {}, setHotspots: () => {}, setOptions: () => {} };
syncLayers3D();
ok(JSON.stringify(got) === JSON.stringify({ zones: true, railcut: true, labels: false, addrs: true, ports: true, texts: true, junctions: true, sensors: false, hotspots: true }),
   '토글 아홉 → 레이어 아홉 (' + JSON.stringify(got) + ')');
showSensor = true; showZone = false; syncLayers3D();
ok(got.sensors === true && got.zones === false, '토글이 바뀌면 그대로 따라간다');

/* 설정 → 3D 크기 배수 */
let opts = null;
v3d.setOptions = o => { opts = o; };
mapSettings.v3dVehicle = 2; mapSettings.v3dPort = 1.3; mapSettings.v3dText = 1.6; mapSettings.v3dRail = 0.8;
sync3DTheme();
ok(opts.vehicleScale === 2 && opts.portScale === 1.3 && opts.textScale === 1.6 && opts.railScale === 0.8, '설정의 배수 넷이 그대로 간다 ' + JSON.stringify(opts));
ok(Array.isArray(opts.stateColors) && opts.stateColors.length === 5, '차량 색 다섯도 같이');

/* ── push3D 는 안 켜져 있으면 아무것도 안 한다 ── */
let called = 0, gotBlocked = null, gotHot = null;
mapData.blockedEdges = { '3_4': { from: 3, to: 4 } }; mapData.hotspots = [{ x: 1, y: 2, stopped: 1 }];
v3d = { setVehicles: () => { called++; }, setBlocked: b => { gotBlocked = b; }, setHotspots: h => { gotHot = h; }, setOptions: () => {} };
show3D = false; push3D({}); ok(called === 0, '3D 꺼져 있으면 setVehicles 안 부른다');
show3D = true; mapData.vehicles = [{ vid: 'V1', x: 1, y: 2, state: 1 }]; push3D({ time: '2026-04-07 07:44:16' });
ok(called === 1, '켜져 있으면 프레임마다 한 번');
ok(gotBlocked && gotBlocked.includes('3-4') && gotHot && gotHot.length === 1, '프레임마다 차단·핫스팟도 같이 넘긴다');
mapData.blockedEdges = {}; mapData.hotspots = [];

/* ── sync3DLayout 은 같은 맵이면 다시 안 세운다 ── */
let built = 0;
v3d = { setLayout: () => { built++; }, setVehicles: () => {}, setBlocked: () => {}, setHotspots: () => {}, setOptions: () => {} };
railGraph = G; railGeom = geom; v3dLayoutSig = '';
sync3DLayout(); sync3DLayout();
ok(built === 1, '같은 맵 두 번 → setLayout 한 번 (' + built + ')');
currentFab = 'M16A'; sync3DLayout();
ok(built === 2, 'FAB 이 바뀌면 다시 세운다');

console.log(bad ? ('FAILED ' + bad) : 'OK');
process.exit(bad ? 1 : 0);
