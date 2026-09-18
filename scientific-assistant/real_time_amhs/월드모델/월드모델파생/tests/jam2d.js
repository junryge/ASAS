/* 정체 구간 붉은 표시 — dashboard.html 의 jamClusters()/drawJamBlobs() 를
   **그대로 떼어** 돌린다 (tests/iso3d.js 와 같은 수법).

   고객: "2D, 유사3D도 정체구간 표시 빨간색 뿌옇게 하는거 기능 집어 넣어주라
          버튼 만들어서" · "옵션 같이 써야지 2D, 유사3D"
*/
const fs = require('fs'), path = require('path');
const H = fs.readFileSync(path.join(__dirname, '..', 'dashboard.html'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };
const grab = re => { const m = H.match(re); ok(m, '못 찾음: ' + re); return m ? m[0] : ''; };

let vehicleDisplay = {};
/* 레이아웃 — 구역 상자를 만드는 데 쓴다. 존 하나에 레인 하나로 조그맣게.
   존 A: (0,0)~(600,600) · 존 B: 멀리 떨어진 (50000,0)~(50600,600) */
let railGraph = {
  nodes: { '1': [0, 0], '2': [600, 600], '3': [50000, 0], '4': [50600, 600] },
  zones: [{ id: 11, name: 'HID-A(011)', inLanes: [{ from: 1, to: 2 }], outLanes: [] },
          { id: 22, name: 'HID-B(022)', inLanes: [{ from: 3, to: 4 }], outLanes: [] }],
};
function z3dId(z) { return z.name || ('HID ' + z.id); }
eval(grab(/const DEFAULT_MAP_SETTINGS = \{[\s\S]*?\n\};/).replace(/\bconst DEFAULT_MAP_SETTINGS\b/, 'var DEFAULT_MAP_SETTINGS'));
var mapSettings = { ...DEFAULT_MAP_SETTINGS };
eval(grab(/const JAM_R = 1200;[\s\S]*?\nfunction jamClusters\(radius\) \{[\s\S]*?\n\}/)
     .replace(/\bconst (JAM_R|JAM_KIND)\b/g, 'var $1'));
eval(grab(/function drawJamBlobs\(ctx, toS, sc\) \{[\s\S]*?\n\}/));

/* ── 정체 판정 — 종류마다 '몇 대 이상' 을 직접 적는다 ── */
ok(mapSettings.jamMinJam === 1, '기본 JAM 1대 이상');
ok(mapSettings.jamMinObs === 0, '기본 OBS 는 안 봄(0)');
ok(mapSettings.jamMinStop === 0, '기본 멈춘 차도 안 봄(0)');
ok(JAM_KIND.length === 3 && JAM_KIND[2].name === '멈춘 차', '멈춘 차가 제일 마지막');
ok(JAM_KIND[0].has(7) && JAM_KIND[1].has(6), 'JAM=7 · OBS=6');
ok(JAM_KIND[2].has(2) && JAM_KIND[2].has(8) && JAM_KIND[2].has(9), '멈춘 차 = 2·8·9');
ok(jamKindOf(7) === 0 && jamKindOf(6) === 1 && jamKindOf(8) === 2, '코드 → 종류');
ok(jamKindOf(1) === -1 && jamKindOf(3) === -1, '운행·가속은 어느 종류도 아니다');
/* 빈칸·글자·음수는 0(안 봄)으로 */
mapSettings.jamMinObs = '';   ok(jamMins()[1] === 0, '빈칸은 0');
mapSettings.jamMinObs = 'abc'; ok(jamMins()[1] === 0, '글자는 0');
mapSettings.jamMinObs = -5;   ok(jamMins()[1] === 0, '음수는 0');
mapSettings.jamMinObs = '3';  ok(jamMins()[1] === 3, '글자 숫자도 읽는다');
mapSettings.jamMinObs = 0;

const put = (id, x, y, st) => { vehicleDisplay[id] = { dx: x, dy: y, state: st == null ? 7 : st }; };

/* ── 정체가 없으면 아무것도 안 만든다 ── */
vehicleDisplay = {};
ok(jamClusters(JAM_R).length === 0, '차가 없으면 무리도 없다');
put('a', 0, 0, 1); put('b', 10, 10, 6); put('c', 20, 20, 2);
ok(jamClusters(JAM_R).length === 0, '기본(1·0·0)에서는 운행·OBS·정지를 안 센다');
/* 0 을 올리면 같은 차가 정체가 된다 */
mapSettings.jamMinObs = 1;
ok(jamClusters(JAM_R).length === 1 && jamClusters(JAM_R)[0].n === 1, 'OBS 1대 이상으로 두면 잡는다');
mapSettings.jamMinObs = 0;
ok(jamClusters(JAM_R).length === 0, '0 으로 되돌리면 다시 안 잡는다');

/* ── '몇 대 이상' — 못 넘으면 안 잡는다 ── */
vehicleDisplay = {};
for (let i = 0; i < 2; i++) put('t' + i, i * 100, 0, 7);
mapSettings.jamMinJam = 3;
ok(jamClusters(JAM_R).length === 0, 'JAM 3대 이상인데 2대면 안 잡는다');
put('t2', 200, 0, 7);
ok(jamClusters(JAM_R).length === 1 && jamClusters(JAM_R)[0].n === 3, '3대가 되면 잡는다');
mapSettings.jamMinJam = 1;

/* ── 종류가 섞이면 '어느 한 종류라도' ── */
vehicleDisplay = {};
for (let i = 0; i < 2; i++) put('x' + i, i * 100, 0, 7);        // JAM 2
for (let i = 0; i < 5; i++) put('y' + i, 300 + i * 100, 0, 6);  // OBS 5
mapSettings.jamMinJam = 3; mapSettings.jamMinObs = 5;
let cc = jamClusters(JAM_R);
ok(cc.length === 1, 'OBS 쪽이 넘어 한 무리로 잡힌다 (실제 ' + cc.length + ')');
ok(cc[0].n === 7 && cc[0].kinds[0] === 2 && cc[0].kinds[1] === 5, '종류별 대수를 같이 센다');
mapSettings.jamMinObs = 6;
ok(jamClusters(JAM_R).length === 0, '둘 다 못 넘으면 안 잡는다');
mapSettings.jamMinJam = 1; mapSettings.jamMinObs = 0;

/* ── 셋 다 0 이면 아무것도 안 잡는다 ── */
vehicleDisplay = {};
for (let i = 0; i < 9; i++) put('z' + i, i * 100, 0, 7);
mapSettings.jamMinJam = 0;
ok(jamClusters(JAM_R).length === 0, '0 이면 아무 효과 없다');
mapSettings.jamMinJam = 1;
ok(jamClusters(JAM_R).length === 1, '되돌리면 다시 잡는다');

/* ── 가까운 것끼리 한 무리 ── */
vehicleDisplay = {};
for (let i = 0; i < 5; i++) put('n' + i, i * 100, 0);        // 400 단위 안 = 한 무리
let cl = jamClusters(JAM_R);
ok(cl.length === 1, '가까운 다섯은 한 무리 (실제 ' + cl.length + ')');
ok(cl[0].n === 5, '다섯 대로 센다');
ok(Math.abs(cl[0].x - 200) < 1e-6 && cl[0].y === 0, '무리 자리는 한가운데');

/* ── 먼 것은 다른 무리 ── */
vehicleDisplay = {};
for (let i = 0; i < 3; i++) put('p' + i, i * 50, 0);
for (let i = 0; i < 4; i++) put('q' + i, 50000 + i * 50, 0);
cl = jamClusters(JAM_R);
ok(cl.length === 2, '멀리 떨어진 둘은 따로 (실제 ' + cl.length + ')');
ok(cl[0].n === 4 && cl[1].n === 3, '많이 몰린 곳부터 나온다');
ok(cl.reduce((s, c) => s + c.n, 0) === 7, '한 대도 빠지거나 겹쳐 세면 안 된다');
/* ── 어느 HID 구역인가 ── */
ok(cl[0].kinds && cl[0].kinds[0] === 4, '종류별 대수도 같이 준다');
ok(cl[0].zone && cl[0].zone.id === 22, '먼 쪽 무리는 존 B (실제 ' + JSON.stringify(cl[0].zone && cl[0].zone.id) + ')');
ok(cl[1].zone && cl[1].zone.id === 11, '가까운 쪽 무리는 존 A');
ok(zoneAt(300, 300) && zoneAt(300, 300).id === 11, '상자 안이면 그 존');
ok(zoneAt(-9e6, -9e6) === null, '아무 데도 안 들면 null — 억지로 붙이지 않는다');
ok(zoneBoxes() === zoneBoxes(), '상자는 한 번만 만든다');

/* ── 한 대도 무리다 (혼자 멈춰 있어도 보여야 한다) ── */
vehicleDisplay = {};
put('only', 7, 7);
cl = jamClusters(JAM_R);
ok(cl.length === 1 && cl[0].n === 1, '한 대짜리도 표시한다');

/* ── 많아도 안 터지고, 끝없이 돌지 않는다 ── */
vehicleDisplay = {};
for (let i = 0; i < 200; i++) put('m' + i, (i % 20) * 4000, Math.floor(i / 20) * 4000);
const t0 = Date.now();
cl = jamClusters(JAM_R);
ok(Date.now() - t0 < 2000, '200대를 2초 안에 묶는다 (' + (Date.now() - t0) + 'ms)');
ok(cl.reduce((s, c) => s + c.n, 0) === 200, '200대 전부 어딘가에 든다');

/* ── 그리기 — 캔버스 흉내로 실제 호출을 본다 ── */
function rec(w, h) {
  const c = { calls: [], grads: [] };
  const grad = () => { const g = { stops: [] }; c.grads.push(g); return { addColorStop: (o, col) => g.stops.push([o, col]) }; };
  return {
    log: c, canvas: { width: w || 1200, height: h || 800 },
    save() {}, restore() {},
    createRadialGradient(x0, y0, r0, x1, y1, r1) { c.calls.push(['grad', x1, y1, r1]); return grad(); },
    beginPath() {}, arc(x, y, r) { c.calls.push(['arc', x, y, r]); }, fill() { c.calls.push(['fill']); },
    strokeText(t, x, y) { c.calls.push(['strokeText', t]); }, fillText(t, x, y) { c.calls.push(['fillText', t]); },
    set fillStyle(v) {}, get fillStyle() { return ''; },
    set strokeStyle(v) {}, get strokeStyle() { return ''; },
    set font(v) {}, get font() { return ''; },
    set textAlign(v) {}, set textBaseline(v) {}, set lineWidth(v) {},
  };
}
const toS = (x, y) => [x / 100 + 600, y / 100 + 400];

vehicleDisplay = {};
for (let i = 0; i < 6; i++) put('z' + i, i * 60, 0);
let ctx = rec();
drawJamBlobs(ctx, toS, 0.01);
const grads = ctx.log.calls.filter(x => x[0] === 'grad');
ok(grads.length === 1, '무리 하나에 무리 하나 (실제 ' + grads.length + ')');
ok(ctx.log.grads[0].stops.length === 4, '네 단으로 흐려진다');
ok(/^rgba\(239,68,68,0\.(5|50)0?\)$/.test(ctx.log.grads[0].stops[0][1]),
   '가운데는 진한 빨강 (실제 ' + ctx.log.grads[0].stops[0][1] + ')');
ok(ctx.log.grads[0].stops[3][1] === 'rgba(239,68,68,0.00)', '가장자리는 투명 — 테두리가 또렷하면 구역처럼 보인다');
ok(!ctx.log.calls.some(x => x[0] === 'fillText'),
   '작게 그려질 때는 글자를 안 적는다 (무리 반지름 18px — 숫자가 무리보다 커진다)');
/* 크게 그려질 때는 몇 대인지 적는다 */
ctx = rec();
drawJamBlobs(ctx, toS, 0.06);
ok(ctx.log.calls.some(x => x[0] === 'fillText' && x[1] === '6대'), '크면 몇 대인지 적는다');
ok(ctx.log.calls.some(x => x[0] === 'strokeText'), '흰 테두리를 둘러 바탕에 안 묻히게');

/* 정체가 없으면 붓을 들지도 않는다 */
vehicleDisplay = {};
ctx = rec();
drawJamBlobs(ctx, toS, 0.01);
ok(ctx.log.calls.length === 0, '정체가 없으면 아무것도 안 그린다');

/* 화면 밖 무리는 건너뛴다 */
vehicleDisplay = {};
put('far', 9e7, 9e7);
ctx = rec();
drawJamBlobs(ctx, toS, 0.01);
ok(!ctx.log.calls.some(x => x[0] === 'arc'), '화면 밖은 안 그린다');

/* ── 설정 한 곳이 셋을 같이 몬다 ── */
ok(/zone: zoneAt\(bx, by\)/.test(H), '무리마다 구역을 붙인다');
ok(!/jamStates/.test(H), '옛 문자열 설정이 남아 있으면 안 된다');
for (const i of ['ms-jamMinJam', 'ms-jamMinObs', 'ms-jamMinStop'])
  ok(H.includes('id="' + i + '"'), '⚙ 에 ' + i + ' 칸이 있다');
ok(/<input type="number" id="ms-jamMinJam"/.test(H), '고르는 상자가 아니라 **직접 적는** 숫자 칸');
ok(H.indexOf('id="ms-jamMinStop"') > H.indexOf('id="ms-jamMinObs"'), '멈춘 차가 제일 마지막');
ok(/panel: false,/.test(H), '아이소메트리 안 패널은 아예 안 만든다 (사이드바 하나로 본다)');

/* ── 어느 HID 구역인가 ── */
ok(/function zoneAt\(x, y\)/.test(H), '구역 찾는 함수가 있다');
ok(/c\.zone \? z3dId\(c\.zone\) : '구역 밖'/.test(H), '모르면 "구역 밖" 이라고 적는다 (엉뚱한 이름보다 낫다)');
ok(/_zoneBoxG === railGraph/.test(H), '상자는 레이아웃마다 한 번만 만든다');

/* ── 단추 · 상태 ── */
ok(/id="btn-jam"[\s\S]{0,200}onclick="toggleLayer\('jam'\)"/.test(H), '표시 줄에 정체 단추가 있다');
ok(/let showJam = false;/.test(H), '기본은 꺼짐 — 정체가 없는 날 화면이 붉으면 안 된다');
ok(/if \(layer==='jam'\) showJam = !showJam;/.test(H), 'toggleLayer 가 받는다');
ok(/on\('btn-jam', showJam\);/.test(H), '단추 불이 상태를 따라간다');
/* 2D·유사3D 가 같은 단추를 쓴다 — setMapView 가 showJam 을 건드리면 안 된다 */
const smv = grab(/function setMapView\(mode\) \{[\s\S]*?\n\}/);
ok(!/showJam/.test(smv), '보기를 바꿔도 정체 표시는 그대로여야 한다 (같이 쓰는 옵션)');
/* 차량 밑에 깐다 */
const dm = grab(/if \(showJam\) drawJamBlobs\(mapCtx, toS, sc\);[\s\S]{0,400}/);
ok(dm.indexOf('for (const vid in vehicleDisplay)') > 0, '차량 그리기 **앞**에 와야 한다 (위에 덮으면 세모가 묻힌다)');

if (bad) { console.log(bad + ' 건 실패'); process.exit(1); }
console.log('jam2d.js OK');
