/* 실제 화면 함수를 그대로 떼어 와 돌린다 — 소스에 글자가 있나가 아니라
   **컷을 바꾸면 색이 바뀌나**를 본다.

   dashboard.html 은 통째로 못 돌린다(로드하면서 DOM 을 만진다). 색을 정하는
   작은 함수들만 이름으로 떼어 내 한 스코프 안에서 되살린다. 조각을 못 찾으면
   실패시킨다 — 이름이 바뀌었는데 시험만 통과하는 일이 없어야 한다. */
const fs = require('fs');
const path = require('path');
const HTML = fs.readFileSync(
  path.join(__dirname, '..', 'static', 'dashboard.html'), 'utf8');

function grab(re, what){
  const m = HTML.match(re);
  if(!m){ console.log('MISSING ' + what); process.exit(2); }
  return m[0];
}
const parts = [
  grab(/const lvTx = [\s\S]*?;\n/, 'lvTx'),
  grab(/const fabTx\s+=[^\n]*\n/, 'fabTx'),
  grab(/const fabBold =[^\n]*\n/, 'fabBold'),
  grab(/const fabLv = [\s\S]*?';\n/, 'fabLv'),
  grab(/function fabCells\(r\)\{[\s\S]*?\n\}/, 'fabCells'),
  grab(/function hiCell\(r\)\{[\s\S]*?\n\}/, 'hiCell'),
  grab(/function cutSig\(\)\{[\s\S]*?\n\}/, 'cutSig'),
];
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

const M = new Function('esc', `
  let FABS = ['M14'], FCUTS = {}, CUTS = {warn:60, danger:71, critical:85};
  ${parts.join('\n')}
  return {lvTx, fabTx, fabBold, fabLv, fabCells, hiCell, cutSig,
          setF: v => { FCUTS = v; }, setC: v => { CUTS = v; }};
`)(esc);

let bad = 0;
const ok = (cond, msg) => { if(!cond){ console.log('FAIL ' + msg); bad++; } };
const colorOf = html => (html.match(/color:([^"]+)"/) || [, ''])[1].trim();

const C60 = {M14:{warn:60, danger:71, critical:85}};
const C36 = {M14:{warn:36, danger:52, critical:72}};
// 43점 — 컷 60 에서는 정상, 컷 36 에서는 경계. CSV 에는 '정상' 이라 적혀 있다.
const row = {fab:{M14:43}, hi_fab:'M14', fab_lv:{M14:'정상'}};

/* ① 정책 컷을 바꾸면 색이 바뀐다 — 고객이 "안 된다" 고 한 바로 그것 */
M.setF(C60); const c60 = colorOf(M.fabCells(row));
M.setF(C36); const c36 = colorOf(M.fabCells(row));
ok(c60 !== c36, `컷을 60→36 으로 바꿔도 색이 그대로다 (${c60})`);
ok(c36 === 'var(--minor)', `43점이 컷 36 에서 경계색이어야 하는데 ${c36}`);
ok(c60 === 'var(--txb)', `43점이 컷 60 에서는 정상색이어야 하는데 ${c60}`);

/* ② 예측기가 CSV 에 적어 둔 등급이 정책을 덮지 않는다 */
M.setF(C36);
ok(colorOf(M.fabCells(row)) === colorOf(M.fabCells({...row, fab_lv:{}})),
   'fab_lv 가 있고 없고에 따라 색이 달라진다 — 정책이 져 버린다');
ok(M.fabCells(row).includes('예측기 표기'),
   '예측기가 다르게 적어 뒀다는 사실이 툴팁에서 사라졌다');
ok(!M.fabCells({...row, fab_lv:{M14:'경계'}}).includes('예측기 표기'),
   '정책과 같은 등급인데 굳이 "다름" 을 적는다');

/* ③ 경계부터 칠하고, 굵게는 위험 이상만 */
ok(M.fabTx('경계') === 'var(--minor)', '경계를 안 칠한다');
ok(M.fabTx('정상') === 'var(--txb)', '정상까지 칠하면 색이 뜻을 잃는다');
ok(M.fabBold('경계') === false, '경계를 굵게 하면 위험처럼 읽힌다');
ok(M.fabBold('위험') === true, '위험은 굵게');

/* ④ HI_FAB 칸도 같은 색 — 같은 수를 두 칸이 다르게 칠하면 안 된다 */
ok(colorOf(M.hiCell(row)) === colorOf(M.fabCells(row)),
   `HI_FAB(${colorOf(M.hiCell(row))}) 과 FAB 칸(${colorOf(M.fabCells(row))}) 색이 다르다`);

/* ⑤ 컷이 바뀌면 표 서명도 바뀐다 (안 바뀌면 표를 다시 안 그린다) */
const s1 = M.cutSig();
M.setF({M14:{warn:40, danger:52, critical:72}});
ok(M.cutSig() !== s1, 'FAB 컷을 바꿔도 서명이 그대로다 — 표를 다시 안 그린다');
const s2 = M.cutSig();
M.setC({warn:36, danger:52, critical:72});
ok(M.cutSig() !== s2, '시스템 컷을 바꿔도 서명이 그대로다');

/* ⑥ 컷이 없으면 칠하지 않는다 — 모르는 것과 정상은 다르다 */
M.setF({});
ok(colorOf(M.fabCells(row)) === 'var(--txb)', '컷을 모르는데 색을 지어낸다');

console.log(bad ? ('FAILED ' + bad) : 'OK');
process.exit(bad ? 1 : 0);
