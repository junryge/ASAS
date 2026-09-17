/* 차량 표시 — dashboard.html 의 vehCarry() · drawCarryDot() · drawMap 판정을
   **그대로 떼어** 돌린다 (tests/iso3d.js 와 같은 수법. 베낀 코드가 아니다).

   고객 요청(2026-09, 현장 HMI 캡처):
     삼각형은 그대로 두고 **그 안에 점**을 찍는다.
       ● 검은 점 = FOUP 을 들고 이동   (VEHICLE_EXECUTE_CYCLE 4 = DEPOSIT_MOVING)
       ● 흰 점   = FOUP 을 가지러 이동  (          〃          2 = ACQUIRE_MOVING)
       그 밖에는 점을 안 찍는다.
     삼각형의 색·모양은 여전히 상태(공차·적재·OBS·정지·JAM)가 정한다.
*/
const fs = require('fs'), path = require('path');
const H = fs.readFileSync(path.join(__dirname, '..', 'dashboard.html'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };
const grab = re => { const m = H.match(re); ok(m, '못 찾음: ' + re); return m ? m[0] : ''; };

const src = grab(/const DEFAULT_MAP_SETTINGS = \{[\s\S]*?\n\};/) + '\nvar mapSettings = { ...DEFAULT_MAP_SETTINGS };\n'
  + grab(/const VC_ACQUIRE = 2[\s\S]*?\nfunction vehCarry\(v\) \{[\s\S]*?\n\}/) + '\n'
  + grab(/function drawCarryDot\([\s\S]*?\n\}/);
eval(src.replace(/\bconst (DEFAULT_MAP_SETTINGS|VC_ACQUIRE)\b/g, 'var $1'));

/* ── 삼각형은 건드리지 않았다 ── */
for (const k of ['shapeEmpty', 'shapeLoaded', 'shapeObs', 'shapeStop', 'shapeJam'])
  ok(mapSettings[k] === 'triangle', k + ' 는 세모여야 한다 — 점은 그 안에 찍는다');
ok(mapSettings.colorLoaded.toLowerCase() === '#22d3ee', '적재 색은 예전 그대로(하늘)');
ok(mapSettings.colorEmpty.toLowerCase() === '#22c55e', '공차 색은 예전 그대로(초록)');
ok(!('colorAssign' in mapSettings) && !('shapeAssign' in mapSettings),
   '삼각형을 동그라미로 바꿨던 판(v2)의 찌꺼기가 남으면 안 된다');

/* ── 점 기본값 ── */
ok(mapSettings.carryDot === 'on', '점은 기본으로 켜져 있다');
ok(mapSettings.dotLoaded.toLowerCase() === '#000000', '들고 감 = 검은 점');
ok(mapSettings.dotAssign.toLowerCase() === '#ffffff', '가지러 감 = 흰 점');
ok(mapSettings.dotSize > 0.3 && mapSettings.dotSize < 0.8, '점 크기는 삼각형 안에 들어갈 만큼');

/* ── 실행 사이클이 가장 확실한 신호 ── */
ok(vehCarry({ vhlCycle: 4 }) === 'loaded', '사이클 4 = DEPOSIT_MOVING = 들고 감');
ok(vehCarry({ vhlCycle: 2 }) === 'assign', '사이클 2 = ACQUIRE_MOVING = 가지러 감');
ok(vehCarry({ vhlCycle: '4' }) === 'loaded', '글자로 와도 같다 (CSV 는 글자다)');
ok(vehCarry({ vhlCycle: 4, isFull: 0, destination: 0 }) === 'loaded', '사이클이 적재 여부보다 이긴다');
ok(vehCarry({ vhlCycle: 2, isFull: 1, destination: 9 }) === 'assign', '〃');
for (const c of [1, 3, 5, 6, 7, 8])
  ok(vehCarry({ vhlCycle: c, isFull: 1, destination: 9 }) === '',
     '사이클 ' + c + ' 은 반송 이동이 아니다 → 점 없음');

/* ── 사이클이 없을 때(간소 조회·옛 데이터) 대신 읽는 길 ── */
ok(vehCarry({ vhlCycle: 0, isFull: 1 }) === 'loaded', '짐이 있으면 들고 가는 중으로 본다');
ok(vehCarry({ vhlCycle: 0, isFull: 0, destination: 123 }) === 'assign', '짐 없이 갈 곳이 있으면 지시받은 것');
ok(vehCarry({ vhlCycle: 0, isFull: 0, destination: 0 }) === '', '짐도 갈 곳도 없으면 점 없음');
ok(vehCarry({}) === '', '컬럼이 통째로 없어도 안 터진다');
ok(vehCarry({ vhlCycle: null, isFull: null, destination: null }) === '', 'null 이어도 안 터진다');

/* ── 점 그리기 — 캔버스 흉내로 실제 호출을 본다 ── */
function rec() {
  const c = { calls: [], _s: {} };
  return {
    log: c,
    save() { c.calls.push(['save']); }, restore() { c.calls.push(['restore']); },
    translate(x, y) { c.calls.push(['translate', x, y]); },
    rotate(a) { c.calls.push(['rotate', a]); },
    beginPath() { c.calls.push(['beginPath']); },
    arc(x, y, r) { c.calls.push(['arc', x, y, r]); },
    fill() { c.calls.push(['fill', this.fillStyle]); },
    set fillStyle(v) { c._s.fill = v; }, get fillStyle() { return c._s.fill; },
  };
}
const dot = (kind, ang, rr) => { const c = rec(); drawCarryDot(c, 100, 50, rr === undefined ? 4 : rr, kind, ang || 0); return c.log; };

let L = dot('loaded');
ok(L.calls.some(x => x[0] === 'arc'), '들고 감이면 점을 찍는다');
ok(L.calls.some(x => x[0] === 'fill' && String(x[1]).toLowerCase() === '#000000'), '검은 점');
L = dot('assign');
ok(L.calls.some(x => x[0] === 'fill' && String(x[1]).toLowerCase() === '#ffffff'), '흰 점');
ok(dot('').calls.length === 0, '반송 중이 아니면 점을 안 찍는다');
ok(dot(null).calls.length === 0, '〃 (null)');
mapSettings.carryDot = 'off';
ok(dot('loaded').calls.length === 0, '설정에서 끄면 안 찍는다');
mapSettings.carryDot = 'on';

/* 자리 — 삼각형의 무게중심, 진행 방향으로 돌아간다 */
L = dot('loaded', 1.234);
const rot = L.calls.find(x => x[0] === 'rotate');
ok(rot && rot[1] === 1.234, '점도 삼각형과 같은 각도로 돈다 (무게중심이 방향을 탄다)');
const arc = L.calls.find(x => x[0] === 'arc');
ok(arc && arc[1] < 0, '무게중심은 꼭짓점 반대쪽 — 국소 x 가 음수여야 한다');
ok(arc && Math.abs(arc[1] - (-0.133 * 4 * 1.56)) < 1e-9, '무게중심 = −0.133·tr');
ok(arc && arc[3] > 0 && arc[3] < 4, '점은 차량 반지름보다 작다');
/* 아주 작게 그려도 점이 사라지면 안 된다 */
const tiny = dot('loaded', 0, 1).calls.find(x => x[0] === 'arc');
ok(tiny && tiny[3] >= 0.9, '많이 줄여도 최소 크기는 지킨다');

/* ── drawMap — 색은 상태가 정하고, 점은 그 위에 얹는다 ── */
const draw = grab(/\/\/ 색·모양은 \*\*상태\*\*가 정한다[\s\S]*?drawCarryDot\([^\n]*\);/);
ok(/else if \(v\.isFull\)\s*\{\s*color = mapSettings\.colorLoaded/.test(draw),
   '색 판정은 예전 그대로 (isFull → 적재 색)');
ok(!/carry === 'loaded'/.test(draw), '색 판정에 반송 여부를 섞지 않는다');
ok(draw.indexOf('drawVehicleShape(') < draw.indexOf('drawCarryDot('), '점은 삼각형 **위에** 얹는다');
ok(/drawCarryDot\(mapCtx, sx, vy, r, vehCarry\(v\)/.test(draw), '점은 상태와 상관없이 vehCarry 로만 정한다');

/* ── 흰 점이 밝은 삼각형 안에서 사라지면 안 된다 (세모 테두리) ── */
const shp = grab(/function drawVehicleShape\([\s\S]*?\n\}/);
ok(!/rr >= 3 && stroke/.test(shp), '크기 조건 없이 테두리를 그려야 한다');

/* ── 저장된 옛 설정이 새 기본값을 덮으면 안 된다 ── */
ok(/MAP_SETTINGS_KEY = 'oht_world_map_settings_v3'/.test(H),
   '기본값을 바꿨으면 저장 키도 올려야 한다 ("바꿨는데 화면 그대로" 방지)');

if (bad) { console.log(bad + ' 건 실패'); process.exit(1); }
console.log('vehicle_marks.js OK');
