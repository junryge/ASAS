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

/* ── 알람 칸 ── */
const cellSrc = cut(/function almCell\(r\)\{[\s\S]*?\n\}/, 'almCell');
eval(cellSrc);
ok('빈 행은 —', almCell({}) === '<td class="acol"><span class="dim">—</span></td>', almCell({}));
ok('있는 행은 배지', almCell({alm:{lv:'위험중', d:2}}).includes('위험중<b>2</b>'),
   almCell({alm:{lv:'위험중', d:2}}));
ok('알람 칸 클래스', almCell({}).startsWith('<td class="acol">'), almCell({}));

/* ── 서명 ── */
const s0 = cutSig();
ALARM = Object.assign({}, ALARM, {window_min: 30});
ok('창을 바꾸면 서명이 바뀐다', cutSig() !== s0, cutSig());
ALARM = Object.assign({}, ALARM, {window_min: 10, enabled: false});
ok('적용을 끄면 서명이 바뀐다', cutSig() !== s0, cutSig());
ALARM = Object.assign({}, ALARM, {enabled: true});
ok('되돌리면 서명도 되돌아온다', cutSig() === s0, cutSig());
ok('등급 컷도 서명에 그대로 남아 있다', cutSig().includes('"warn":60'), cutSig());

console.log(JSON.stringify(out));
