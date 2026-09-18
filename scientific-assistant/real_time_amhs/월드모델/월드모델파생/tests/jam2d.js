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
     .replace(/\bconst JAM_R\b/, 'var JAM_R'));
eval(grab(/function drawJamBlobs\(ctx, toS, sc\) \{[\s\S]*?\n\}/));

/* ── 무엇을 정체로 볼까 — ⚙ 설정 한 곳에서 나온다 ── */
ok(mapSettings.jamStates === '7', '기본은 JAM 만 (2D 가 예전부터 보던 그대로)');
ok(jamStateSet().has(7) && !jamStateSet().has(6), '기본으로는 OBS 를 안 센다');
mapSettings.jamStates = '6,7';
ok(jamStateSet().has(6) && jamStateSet().has(7), '고르면 OBS 도 센다');
mapSettings.jamStates = '';
ok(jamStateSet().has(7) && jamStateSet().size === 1, '다 지워도 JAM 만은 남는다 (빈 기준은 없다)');
mapSettings.jamStates = '7,아무거나,6';
ok(jamStateSet().size === 2, '숫자 아닌 것은 무시한다');
/* ★아이소메트리는 이 설정을 **안 따른다** (고객: "아이소메트리 그냥 나둬라").
   거기 '정체 지점' 은 예전대로 늘 JAM+OBS(st >= 3) 다. */
ok(typeof jamStates3D === 'undefined', '3D 로 옮기는 길을 만들지 않았다');
mapSettings.jamStates = '7';

/* ── 묶는 크기 ── */
ok(JAM_R === 1200, '도면 1 단위 = 10 mm → 1200 단위 = 12 m (3D 의 12 m 와 같게)');

const put = (id, x, y, st) => { vehicleDisplay[id] = { dx: x, dy: y, state: st == null ? 7 : st }; };

/* ── 정체가 없으면 아무것도 안 만든다 ── */
vehicleDisplay = {};
ok(jamClusters(JAM_R).length === 0, '차가 없으면 무리도 없다');
put('a', 0, 0, 1); put('b', 10, 10, 6); put('c', 20, 20, 2);
ok(jamClusters(JAM_R).length === 0, '기본(7)에서는 운행·OBS·정지를 안 센다');
/* 설정을 바꾸면 같은 차가 정체가 된다 */
mapSettings.jamStates = '6,7';
ok(jamClusters(JAM_R).length === 1 && jamClusters(JAM_R)[0].n === 1, 'OBS 를 켜면 그 차를 잡는다');
mapSettings.jamStates = '7';
ok(jamClusters(JAM_R).length === 0, '되돌리면 다시 안 잡는다');

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
ok(/id="ms-jamStates"/.test(H), '⚙ 설정에 정체 판정 줄이 있다');
ok(!/jamStates3D/.test(H), '아이소메트리로 넘기는 길이 남아 있으면 안 된다');
ok(/panel: false,/.test(H), '아이소메트리 안 패널은 아예 안 만든다 (사이드바 하나로 본다)');

/* ── 어느 HID 구역인가 ── */
ok(/function zoneAt\(x, y\)/.test(H), '구역 찾는 함수가 있다');
ok(/out\.push\(\{ x: bx, y: by, n: bc, zone: zoneAt\(bx, by\) \}\)/.test(H), '무리마다 구역을 붙인다');
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
