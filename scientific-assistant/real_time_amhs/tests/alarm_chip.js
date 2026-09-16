/* dashboard.html 의 '등급 카운터 배지' 토막을 **그대로** 떼어 돌린다.

   왜 이렇게 하나
     화면 시험(playwright)은 폐쇄망에 못 깐다. 그렇다고 배지를 안 보면
     "미적용인데 배지가 남아 있다" · "초위험인데 위험이라 쓴다" 를 또 손으로
     찾아야 한다. 그래서 dashboard.html 원본을 잘라 얇은 껍데기 위에서
     돌린다 — 베낀 코드가 아니라 **배포되는 그 코드**를 본다.
     (tests/alarm_gate.js 와 같은 수법이다.)
   node 가 없으면 파이썬 쪽 시험이 알아서 건너뛴다. */
const fs = require('fs');
const path = require('path');
const BASE = path.resolve(__dirname, '..');
const src = fs.readFileSync(path.join(BASE, 'static', 'dashboard.html'), 'utf8');

function cut(re, what){
  const m = src.match(re);
  if(!m) throw new Error(what + ' 토막을 못 찾았다');
  return m[0];
}
/* 떼어 올 것: almChip · almSig · cutSig. esc 와 상태는 껍데기로 준다. */
const block = [
  cut(/function almChip\(r\)\{[\s\S]*?\n\}/, 'almChip'),
  cut(/function almSig\(\)\{[^\n]*\}/, 'almSig'),
  cut(/function cutSig\(\)\{[\s\S]*?\n\}/, 'cutSig'),
].join('\n');

const esc = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');
let ALARM = {enabled: true, window_min: 10, warn: 3, danger: 1, critical: 1};
let CUTS = {warn: 60, danger: 71, critical: 85};
let FCUTS = {};
eval(block);

const out = [];
const ok = (name, cond, got) => out.push({name, ok: !!cond, got: String(got)});

/* ── 배지 ── */
ok('없으면 안 붙는다', almChip({}) === '', almChip({}));
ok('lv 가 비면 안 붙는다', almChip({alm: {lv: '', w: 9}}) === '', almChip({alm: {lv: ''}}));

const w = almChip({alm: {lv: '경계중', w: 4, d: 0, c: 0, why: '최근 10분에 경계 이상 4회 (기준 3회)'}});
ok('경계 배지 글자', w.includes('경계중<b>4</b>'), w);
ok('경계 색 클래스는 lv경계', /class="chip alm lv경계"/.test(w), w);
ok('근거는 title 에', w.includes('title="최근 10분에 경계 이상 4회 (기준 3회)"'), w);

const d = almChip({alm: {lv: '위험중', w: 5, d: 2, c: 0}});
ok('위험 배지는 위험 카운트를 쓴다', d.includes('위험중<b>2</b>'), d);
ok('위험 색 클래스는 lv위험', /class="chip alm lv위험"/.test(d), d);

const c = almChip({alm: {lv: '초위험중', w: 6, d: 3, c: 1}});
ok('초위험 배지는 초위험 카운트를 쓴다', c.includes('초위험중<b>1</b>'), c);
/* ★'초위험' 은 '위험' 을 품는다 — 글자 포함으로 색을 고르면 lv위험 이 된다 */
ok('초위험 색 클래스는 lv초위험', /class="chip alm lv초위험"/.test(c), c);

/* 근거 글이 따옴표를 물고 와도 속성을 깨면 안 된다 */
const x = almChip({alm: {lv: '위험중', d: 1, why: '앞"뒤<b>'}});
ok('근거를 escape 한다', !/title="앞"/.test(x) && x.includes('&quot;'), x);

/* ── 알람 칸 — ALL + FAB 다섯이 줄로 쌓인다 ── */
let SYS = 'ALL';
let FABS = ['M14','M14B','M16A','M16B','M16HUB'];
let ALARM_FAB = {M14B: {window_min:10, warn:3, danger:1, critical:1},
                 M16B: {window_min:30, warn:4, danger:2, critical:1}};
eval([
  cut(/function almLine\(sys, lv, n, why\)\{[\s\S]*?\n\}/, 'almLine'),
  cut(/function almWhyFab\(fab, a\)\{[\s\S]*?\n\}/, 'almWhyFab'),
  cut(/function almCell\(r\)\{[\s\S]*?\n\}/, 'almCell'),
].join('\n'));
const lines = h => (h.match(/class="almln"/g) || []).length;

ok('빈 행은 —', almCell({}) === '<td class="acol"><span class="dim">—</span></td>', almCell({}));
ok('알람 칸 클래스', almCell({}).startsWith('<td class="acol">'), almCell({}));

const own = almCell({alm:{lv:'위험중', d:2, why:'왜'}});
ok('자기 줄에 시스템 이름', own.includes('>ALL</i>'), own);
ok('자기 줄 배지', own.includes('위험중<b>2</b>'), own);
ok('ALL 은 청록 표시', own.includes('<i class="all">'), own);

const both = almCell({alm:{lv:'위험중', d:1, why:'왜'},
                      alm_fab:{M14B:{lv:'초위험중', n:1}, M16B:{lv:'경계중', n:4}}});
ok('ALL + FAB 둘 = 세 줄', lines(both) === 3, lines(both));
ok('FAB 이름이 줄에 있다', both.includes('>M14B</i>') && both.includes('>M16B</i>'), both);
/* ★차례는 오른쪽 FAB 점수 칸과 같아야 한다 — 제일 센 것을 위로 올리면
   행마다 줄이 뒤바뀌어 눈이 못 따라간다 */
ok('차례는 ALL → FABS 순서',
   both.indexOf('>ALL<') < both.indexOf('>M14B<') &&
   both.indexOf('>M14B<') < both.indexOf('>M16B<'), both);
ok('FAB 줄도 자기 색', /lv초위험[\s\S]*?초위험중<b>1<\/b>/.test(both), both);

/* FAB 화면에서는 FAB 줄을 또 붙이지 않는다 (그 FAB 이 곧 자기 줄이다) */
SYS = 'M14B';
const fabScreen = almCell({alm:{lv:'위험중', d:1}, alm_fab:{M14B:{lv:'초위험중', n:1}}});
ok('FAB 화면은 한 줄', lines(fabScreen) === 1, fabScreen);
ok('FAB 화면 줄 이름은 그 FAB', fabScreen.includes('>M14B</i>'), fabScreen);
SYS = 'ALL';

/* 말풍선 — 서버 alarm_count.why 와 **같은 문장**이어야 한다 */
ok('FAB 말풍선(초위험)',
   almWhyFab('M14B', {lv:'초위험중', n:1}) === 'M14B — 최근 10분에 초위험 1회 (기준 1회)',
   almWhyFab('M14B', {lv:'초위험중', n:1}));
ok('FAB 말풍선(위험)',
   almWhyFab('M16B', {lv:'위험중', n:3}) === 'M16B — 최근 30분에 위험 이상 3회 (기준 2회)',
   almWhyFab('M16B', {lv:'위험중', n:3}));
ok('FAB 말풍선(경계)',
   almWhyFab('M16B', {lv:'경계중', n:5}) === 'M16B — 최근 30분에 경계 이상 5회 (기준 4회)',
   almWhyFab('M16B', {lv:'경계중', n:5}));
ok('정책이 없으면 말풍선은 빈 글', almWhyFab('M14', {lv:'위험중', n:1}) === '',
   almWhyFab('M14', {lv:'위험중', n:1}));

/* ── 서명 ── */
const s0 = cutSig();
ALARM = Object.assign({}, ALARM, {window_min: 30});
ok('창을 바꾸면 서명이 바뀐다', cutSig() !== s0, cutSig());
ALARM = Object.assign({}, ALARM, {window_min: 10, enabled: false});
ok('적용을 끄면 서명이 바뀐다', cutSig() !== s0, cutSig());
ALARM = Object.assign({}, ALARM, {enabled: true});
ok('되돌리면 서명도 되돌아온다', cutSig() === s0, cutSig());
ok('등급 컷도 서명에 그대로 남아 있다', cutSig().includes('"warn":60'), cutSig());
const s4 = cutSig();
ALARM_FAB = Object.assign({}, ALARM_FAB, {M14: {window_min:10, warn:3, danger:1, critical:1}});
ok('FAB 정책이 바뀌어도 서명이 바뀐다', cutSig() !== s4, cutSig());

console.log(JSON.stringify(out));
