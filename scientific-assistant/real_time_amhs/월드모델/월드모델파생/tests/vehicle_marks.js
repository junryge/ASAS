/* 차량 표시 — dashboard.html 의 vehCarry() 와 drawMap 의 색·모양 판정을
   **그대로 떼어** 돌린다 (tests/iso3d.js 와 같은 수법. 베낀 코드가 아니다).

   고객 요청(2026-09, 현장 HMI Status List):
     ● 검은 동그라미 = FOUP 을 들고 이동          (VEHICLE_EXECUTE_CYCLE 4 = DEPOSIT_MOVING)
     ● 흰 동그라미   = FOUP 을 가지러 이동         (          〃          2 = ACQUIRE_MOVING)
     ▲ 나머지 전부   = 세모 (진행 방향을 가리킨다)
*/
const fs = require('fs'), path = require('path');
const H = fs.readFileSync(path.join(__dirname, '..', 'dashboard.html'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };
const grab = re => { const m = H.match(re); ok(m, '못 찾음: ' + re); return m ? m[0] : ''; };

const src = grab(/const DEFAULT_MAP_SETTINGS = \{[\s\S]*?\n\};/) + '\nvar mapSettings = { ...DEFAULT_MAP_SETTINGS };\n'
  + grab(/const VC_ACQUIRE = 2[\s\S]*?\nfunction vehCarry\(v\) \{[\s\S]*?\n\}/);
eval(src.replace(/\bconst (DEFAULT_MAP_SETTINGS|VC_ACQUIRE)\b/g, 'var $1'));

/* ── 기본값 — 동그라미 둘, 나머지 세모 ── */
ok(mapSettings.shapeLoaded === 'circle', '적재 이동은 동그라미');
ok(mapSettings.shapeAssign === 'circle', '가지러 이동은 동그라미');
ok(mapSettings.colorLoaded.toLowerCase() === '#111111', '들고 가는 차는 검정');
ok(mapSettings.colorAssign.toLowerCase() === '#ffffff', '가지러 가는 차는 흰색');
for (const k of ['shapeEmpty', 'shapeObs', 'shapeStop', 'shapeJam'])
  ok(mapSettings[k] === 'triangle', k + ' 는 세모여야 한다 (동그라미는 반송 둘뿐)');

/* ── 실행 사이클이 가장 확실한 신호 ── */
ok(vehCarry({ vhlCycle: 4 }) === 'loaded', '사이클 4 = DEPOSIT_MOVING = 들고 감');
ok(vehCarry({ vhlCycle: 2 }) === 'assign', '사이클 2 = ACQUIRE_MOVING = 가지러 감');
ok(vehCarry({ vhlCycle: '4' }) === 'loaded', '글자로 와도 같다 (CSV 는 글자다)');
ok(vehCarry({ vhlCycle: 4, isFull: 0, destination: 0 }) === 'loaded',
   '사이클이 있으면 적재 여부보다 사이클이 이긴다');
ok(vehCarry({ vhlCycle: 2, isFull: 1, destination: 9 }) === 'assign', '〃');
for (const c of [1, 3, 5, 6, 7, 8])
  ok(vehCarry({ vhlCycle: c, isFull: 1, destination: 9 }) === '',
     '사이클 ' + c + ' 은 반송 이동이 아니다 → 세모');

/* ── 사이클이 없을 때(간소 조회·옛 데이터) 대신 읽는 길 ── */
ok(vehCarry({ vhlCycle: 0, isFull: 1 }) === 'loaded', '짐이 있으면 들고 가는 중으로 본다');
ok(vehCarry({ vhlCycle: 0, isFull: 0, destination: 123 }) === 'assign', '짐 없이 갈 곳이 있으면 지시받은 것');
ok(vehCarry({ vhlCycle: 0, isFull: 0, destination: 0 }) === '', '짐도 갈 곳도 없으면 그냥 세모');
ok(vehCarry({}) === '', '컬럼이 통째로 없어도 안 터진다');
ok(vehCarry({ vhlCycle: null, isFull: null, destination: null }) === '', 'null 이어도 안 터진다');

/* ── drawMap 의 순서 — 멈춘 차가 먼저다 ── */
const draw = grab(/let color, shape;\n\s*const carry = vehCarry\(v\);[\s\S]*?shapeEmpty;\s*\}/);
const at = re => draw.search(re);
ok(at(/state === 6/) >= 0 && at(/state === 7/) >= 0, 'OBS·JAM 가지가 있다');
ok(at(/state === 6/) < at(/carry === 'loaded'/), 'OBS 가 적재보다 먼저 (멈춘 차는 이동 중이 아니다)');
ok(at(/state === 7/) < at(/carry === 'loaded'/), 'JAM 이 적재보다 먼저');
ok(at(/state === 2 \|\| v\.state === 8/) < at(/carry === 'loaded'/), '정지가 적재보다 먼저');
ok(at(/carry === 'loaded'/) < at(/carry === 'assign'/), '들고 감이 가지러 감보다 먼저');
ok(at(/carry === 'assign'/) < at(/colorEmpty/), '가지러 감이 공차보다 먼저');

/* ── 흰 동그라미가 밝은 바탕에서 사라지면 안 된다 ── */
const shp = grab(/function drawVehicleShape\([\s\S]*?\n\}/);
ok(!/rr >= 3 && stroke/.test(shp), '크기 조건 없이 테두리를 그려야 한다 (흰 동그라미가 묻힌다)');
ok(/if \(stroke\) \{/.test(shp), '테두리 가지가 있다');

/* ── 저장된 옛 설정이 새 기본값을 덮으면 안 된다 ── */
ok(/MAP_SETTINGS_KEY = 'oht_world_map_settings_v2'/.test(H),
   '기본값을 바꿨으면 저장 키도 올려야 한다 (안 그러면 "바꿨는데 화면 그대로")');

if (bad) { console.log(bad + ' 건 실패'); process.exit(1); }
console.log('vehicle_marks.js OK');
