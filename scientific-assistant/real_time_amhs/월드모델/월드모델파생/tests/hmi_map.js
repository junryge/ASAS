/* HMI 맵 레이어 — 기하가 데이터대로 나오나 (캔버스 호출을 기록해서 본다).

   ★현장 캡처와 대조해 정한 규칙들을 여기서 못 박는다:
     · 대각선 '모서리 노드' 는 둥글린다 (quadraticCurveTo), 일직선 노드는 안 한다
     · 포트: 종류 9 = 진행 방향 오른쪽, 8 = 왼쪽, 1 = 레일 위 · 자리 = offset 비율
     · 노드 번호: 2 = 오른쪽, 3 = 왼쪽, 0/1 = 위
     · 차량 삼각형은 현재→다음 노드 방향을 가리킨다 */
const fs = require('fs'), path = require('path');
const H = fs.readFileSync(path.join(__dirname, '..', 'dashboard.html'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };
const grab = re => { const m = H.match(re); ok(m, '못 찾음: ' + re); return m ? m[0] : ''; };
const src = grab(/const DEFAULT_MAP_SETTINGS = \{[\s\S]*?\n\};/) + '\nlet mapSettings = { ...DEFAULT_MAP_SETTINGS };\n'
  + grab(/const MAP_THEMES = \{[\s\S]*?\n\};\nfunction mapPal\(\) \{[\s\S]*?\n\}/) + '\n'
  + grab(/\/\/ ===== HMI 맵 레이어 \(시작\) =====[\s\S]*?\/\/ ===== HMI 맵 레이어 \(끝\) =====/);
// eval 안의 const/let 은 밖으로 안 나온다 (function 만 나온다) — var 로 바꿔 넣는다
eval(src.replace(/\bconst (DEFAULT_MAP_SETTINGS|MAP_THEMES|HMI_SC)\b/g, 'var $1').replace(/\blet mapSettings\b/, 'var mapSettings'));

// 기록하는 가짜 캔버스
function rec() {
  const calls = [];
  const p = new Proxy({}, { get(_, k) {
    if (k === 'calls') return calls;
    if (k === 'measureText') return t => ({ width: String(t).length * 6 });
    return (...a) => { calls.push([k, ...a]); };
  }, set() { return true; } });
  return p;
}
// 실물 16001 루프의 축약 — 세로 레일 → 대각 모서리(16004) → 가로 레일
const G = { nodes: { '1':[100,100], '2':[100,160], '3':[129,194], '4':[200,194], '5':[300,194], '9':[100,40] },
  edges: [[9,1],[1,2],[2,3],[3,4],[4,5]],
  meta: { '1':[2,0,0], '2':[2,0,0], '3':[1,0,0], '4':[0,0,0], '5':[0,1,0], '9':[3,0,1] },
  stations: [[1, 2, 0.5, 9, 17001, 'R'], [1, 2, 0.5, 8, 27001, 'L'], [3, 4, 0.5, 1, 4904, 'PSA']],
  labels: [['ZC590A', 2, 20, 20, 'zc'], ['B44', 1, 0, -30, 'bay'], ['C1', 1, 0, -30, 'col'], ['E9', 5, 0, 30, 'col'], ['B01', 5, 0, 30, 'bay'], ['MTL003', 4, 20, 20, 'mtl']], sensors: [] };
const geom = buildRailGeom(G);
ok(geom.und.length === 5, '무방향 엣지 5개');
// ★2 와 3 둘 다 둥글린다 — 세로 레일이 대각 모서리 노드로 들어가는 자리(2)도
//   40° 꺾임이라, 둘을 이어 한 호(弧)가 된다. 실물 16007→16008→16009 가 이렇다.
//   처음엔 '대각 노드만' 이라고 시험을 썼다가 틀렸다. 일직선 1 만 직선이다.
ok(!!geom.smooth['3'] && !!geom.smooth['2'], '꺾이는 2·3 은 둥글린다: ' + JSON.stringify(Object.keys(geom.smooth)));
ok(!geom.smooth['1'], '일직선 노드 1 은 직선');
// 포트 자리·법선
const st = Object.fromEntries(geom.st.map(s => [s[5], s]));
ok(Math.abs(st[17001][0]-100) < 1e-9 && Math.abs(st[17001][1]-130) < 1e-9, '포트 자리 = 1→2 의 0.5 (100,130): ' + st[17001].slice(0,2));
ok(st[17001][2] === -1 && st[17001][3] === 0, '아래로 가는 레일의 오른쪽 법선은 (-1,0): ' + st[17001].slice(2,4));

const toS = (x, y) => [x, y];          // 1:1
const pal = mapPal();
const ctx = rec();
drawRailLayer(ctx, G, geom, toS, 1.6, 400, 300, 0, { pal, showStation: true, showLabel: true, showSensor: false, showJunction: true, showName: true, stationSize: 1 });
const C = ctx.calls;
const quads = C.filter(c => c[0] === 'quadraticCurveTo');
ok(quads.length === 2 && quads.some(q => q[1] === 129 && q[2] === 194) && quads.some(q => q[1] === 100 && q[2] === 160),
   '둥근 모서리는 노드 2·3 을 제어점으로: ' + JSON.stringify(quads));
const rects = C.filter(c => c[0] === 'rect');
ok(rects.length === 3, '포트 네모 3개: ' + rects.length);
const cx = r => r[1] + r[3]/2;
const right = rects.find(r => cx(r) > 100.5), left = rects.find(r => cx(r) < 99.5), on = rects.find(r => Math.abs(cx(r)-164.5) < 1);
ok(!!right && !!left, '오른쪽(9)·왼쪽(8) 포트가 레일 양옆에 선다: ' + rects.map(cx));
ok(!!on, '레일 위(1) 포트는 레일 위(3→4 의 중간 x≈164.5): ' + rects.map(cx));
const texts = C.filter(c => c[0] === 'fillText').map(c => [c[1], c[2], c[3]]);
const t = Object.fromEntries(texts.map(x => [x[0], x]));
ok(t['1'] && t['1'][1] > 100, '노드 1 (방향 2) 번호는 오른쪽: ' + JSON.stringify(t['1']));
ok(t['9'] && t['9'][1] < 100, '노드 9 (방향 3) 번호는 왼쪽: ' + JSON.stringify(t['9']));
ok(t['4'] && Math.abs(t['4'][1]-200) < 0.01 && t['4'][2] < 194, '노드 4 (방향 0) 번호는 위: ' + JSON.stringify(t['4']));
ok(t['4904'] && t['4904'][2] > 194, '레일 위 포트 번호는 네모 아래: ' + JSON.stringify(t['4904']));
ok(t['ZC590A'] && t['ZC590A'][1] > 120 && t['ZC590A'][2] > 180, 'ZC 라벨 = 노드2 + (20,20) 근처: ' + JSON.stringify(t['ZC590A']));
ok(t['B44'] && Math.abs(t['B44'][2]-70) < 0.01, '베이 라벨 = 노드1 + (0,-30) → y 70: ' + JSON.stringify(t['B44']));
ok(t['MTL003'], 'MTL 상자는 늘 보인다');
ok(t['C1'] && t['C1'][2] < t['B44'][2] - 5, '위쪽 열 라벨(C1)은 베이(B44)보다 한 줄 더 위: ' + JSON.stringify([t['C1'], t['B44']]));
ok(t['E9'] && t['E9'][2] > t['B01'][2] + 5, '아래쪽 열 라벨(E9)은 베이(B01)보다 한 줄 더 아래: ' + JSON.stringify([t['E9'], t['B01']]));
const fills = C.filter(c => c[0] === 'fillRect');
ok(fills.length >= 2, 'ZC·MTL 상자 배경: ' + fills.length);
// 합류 ✕ — 노드 5 에 대각선 두 개
const moves = C.filter(c => c[0] === 'moveTo' && Math.abs(c[1]-300) < 8 && Math.abs(c[2]-194) < 8);
ok(moves.length >= 2, '합류 노드 5 에 ✕: ' + moves.length);

// 축소 상태 (sc 작음): 번호·포트·ZC 상자는 숨고, 베이·MTL 은 남는다
const c2 = rec();
drawRailLayer(c2, G, geom, toS, 0.14, 400, 300, 0, { pal, showStation: true, showLabel: true, showSensor: false, showJunction: true, showName: true, stationSize: 1 });
const t2 = c2.calls.filter(c => c[0] === 'fillText').map(c => c[1]);
ok(!t2.includes('1') && !c2.calls.some(c => c[0] === 'rect'), '축소하면 번호·포트를 숨긴다: ' + JSON.stringify(t2));
ok(t2.includes('B44') && t2.includes('MTL003') && !t2.includes('ZC590A'), '축소해도 베이·MTL 은 남고 ZC 는 숨는다: ' + JSON.stringify(t2));

// 차량 방향
const v = { dx: 100, dy: 130, currentNode: 1, nextNode: 2 };
ok(Math.abs(vehicleHeading(v, G) - Math.PI/2) < 1e-9, '1→2 (아래) 는 +90°');
const v2 = { dx: 150, dy: 194, currentNode: 3, nextNode: 4 };
ok(Math.abs(vehicleHeading(v2, G)) < 1e-9, '3→4 (오른쪽) 는 0°');
const v3 = { dx: 10, dy: 10 }; vehicleHeading(v3, G); v3.dx = 10; v3.dy = 0;
ok(Math.abs(vehicleHeading(v3, G) + Math.PI/2) < 1e-9, '노드를 모르면 움직인 쪽(위)');
const c3 = rec(); drawVehicleShape(c3, 50, 50, 4, 'triangle', 0, '#0f0', '#000');
ok(c3.calls.some(c => c[0] === 'rotate') && c3.calls.some(c => c[0] === 'stroke'), '삼각형은 회전하고 테두리를 두른다');

// 기본값이 현장 HMI
ok(DEFAULT_MAP_SETTINGS.mapTheme === 'hmi' && DEFAULT_MAP_SETTINGS.shapeEmpty === 'triangle', '기본 = HMI 테마 · 삼각형');
console.log(bad ? 'FAILED ' + bad : 'OK');
process.exit(bad ? 1 : 0);
