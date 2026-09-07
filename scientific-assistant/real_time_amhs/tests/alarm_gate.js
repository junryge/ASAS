/* app.js 의 'FAB 알람' 토막을 **그대로** 떼어 돌린다.

   왜 이렇게 하나
     화면 시험(playwright)은 폐쇄망에 못 깐다. 그렇다고 알람 문지기를
     안 보면, "껐는데 계속 울린다" 를 또 손으로 찾아야 한다 — 실제로 그
     자리에서 두 번 물렸다 (설정이 저장 안 됨 · 창을 안 열면 안 읽음).
     그래서 app.js 원본을 잘라 얇은 DOM 위에서 돌린다. 베낀 코드가 아니라
     **배포되는 그 코드**를 본다.
   node 가 없으면 파이썬 쪽 시험이 알아서 건너뛴다. */
const fs = require('fs');
const path = require('path');
const BASE = path.resolve(__dirname, '..');
const src = fs.readFileSync(path.join(BASE, 'avatar_2d', 'static', 'app.js'), 'utf8');
const a = src.indexOf('/* ---------- FAB 알람 ----------');
const b = src.indexOf('/* ---------- 알람 기록 창 ----------');
if (a < 0 || b < 0) throw new Error('토막을 못 찾았다');
let block = src.slice(a, b);
/* (function initAlarm(){...})() 는 DOM 이벤트 연결이라 뺀다 */
block = block.replace(/\(function initAlarm\(\)\{[\s\S]*?\n\}\)\(\);/, '');
/* let 로 선언된 것은 context 객체에 안 올라온다 — 창구를 하나 낸다 */
block += `
;globalThis.__A = {
  get FABS(){return FABS}, get LEVELS(){return LEVELS},
  get alarm(){return alarm}, set alarm(v){alarm=v},
  fireAlarm, clearAlarm, silentClear, alarmSay, alarmOn, beep,
  paintAlarmMuted};`;

/* ── 아주 얇은 DOM ── */
const els = {};
function el(id){
  if(!els[id]) els[id] = {
    id, textContent:'', src:'', alt:'', title:'', value:'', _c:new Set(),
    classList:{
      add:(...v)=>v.forEach(x=>els[id]._c.add(x)),
      remove:(...v)=>v.forEach(x=>els[id]._c.delete(x)),
      toggle:(x,on)=>{ on ? els[id]._c.add(x) : els[id]._c.delete(x); },
      contains:(x)=>els[id]._c.has(x),
    },
  };
  return els[id];
}
const said = [];
const sandbox = {
  $: (sel)=>el(String(sel).replace('#','')),
  document:{ documentElement:{ style:{ setProperty(){} } } },
  window:{ SERVER:true },
  setEmotion(){}, speak(t){ said.push(t); }, sys(){},
  setInterval:(fn,ms)=>({fn,ms,_t:'i'}), clearInterval(){},
  ALOG_CFG:{hold_min:60, keep:500, on:true},
  console,
};
const vm = require('vm');
const ctx = vm.createContext(sandbox);
vm.runInContext(block, ctx);
const G = ctx.__A;

function fire(){ G.alarm = null; G.fireAlarm(G.FABS[0], G.LEVELS[1], 'test'); }

let fails = 0;
const ok = (c, m)=>{ console.log((c?'  OK  ':'  ✗   ')+m); if(!c) fails++; };

console.log('① 켜짐 (기본)');
ctx.ALOG_CFG.on = true; said.length = 0;
fire();
ok(G.alarm !== null, '알람이 잡힌다');
ok(!!G.alarm.nag, '재촉 타이머가 걸린다');
ok(said.length === 1, '대사가 한 번 나온다 — ' + JSON.stringify(said[0]||''));
ok(!el('alarmBox').classList.contains('muted'), '꺼짐 표시가 없다');
ok(el('alarmMsg').textContent.includes('계속 울립니다'), '안내: 계속 울립니다');

console.log('② 꺼짐 — 팝업창도 안 뜬다');
ctx.ALOG_CFG.on = false; said.length = 0;
fire();
ok(G.alarm === null, '★알람이 아예 안 잡힌다');
ok(said.length === 0, '★대사가 없다');
ok(!el('alarmBox').classList.contains('on'), '★알람 팝업창이 안 뜬다');
ok(!el('alarmFlash').classList.contains('on'), '★화면 번쩍임도 없다');

console.log('③ 꺼진 채로 재촉 함수를 억지로 불러도');
said.length = 0;
G.alarmSay(); G.alarmSay();
ok(said.length === 0, '★아무 말도 안 한다');

console.log('④ 켜진 채 떠 있다가 끄면');
ctx.ALOG_CFG.on = true; fire();
ok(el('alarmBox').classList.contains('on'), '먼저 떠 있고');
ctx.ALOG_CFG.on = false; said.length = 0;
G.silentClear();                       // saveAlogCfg 가 하는 일
ok(G.alarm === null, '★그 자리에서 내려간다');
ok(!el('alarmBox').classList.contains('on'), '★팝업창이 사라진다');
ok(said.length === 0, '★내려가면서 대사도 없다 (끈 것이지 해제가 아니다)');

console.log('⑤ 다시 켜면');
ctx.ALOG_CFG.on = true; said.length = 0;
fire();
ok(G.alarm !== null, '알람이 다시 잡힌다');
ok(!!G.alarm.nag, '재촉이 다시 돈다');
ok(said.length === 1, '대사가 다시 나온다');
ok(el('alarmBox').classList.contains('on'), '팝업창이 다시 뜬다');
ok(el('alarmMsg').textContent.includes('계속 울립니다'), '안내가 원래대로');

console.log('⑥ alarmOn() 판단');
ctx.ALOG_CFG.on = undefined;  ok(G.alarmOn() === true,  '값이 없으면 켜짐 (관제라 기본이 켜짐)');
ctx.ALOG_CFG.on = false;      ok(G.alarmOn() === false, 'false 면 꺼짐');
ctx.ALOG_CFG.on = true;       ok(G.alarmOn() === true,  'true 면 켜짐');

console.log(fails ? ('\n★ ' + fails + '개 실패') : '\n전부 통과');
process.exit(fails ? 1 : 0);
