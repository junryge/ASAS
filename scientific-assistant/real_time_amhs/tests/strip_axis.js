/* 추이 그래프 시간축 — 선과 글자가 같은 자리인가.

   ★고객 지적: "표기 시간이 00:00, 12:00, 24:00 이러면 안 되지."
     글자는 12시간마다인데 세로 실선은 2시간마다 그어서, 어느 선이 몇 시인지
     셀 수가 없었다. 그리고 '24:00' 은 없는 시각이다 — 하루의 마지막 분은 23:59.

   ★소스에 글자가 있나가 아니라 **선 위치와 글자 위치가 같은가**를 본다.
     둘을 따로 적어 두면 또 어긋난다. */
const fs = require('fs');
const path = require('path');
const H = fs.readFileSync(
  path.join(__dirname, '..', 'static', 'dashboard.html'), 'utf8');

let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };

const mt = H.match(/const STRIP_TICK_H = (\d+)/);
ok(mt, '눈금 간격 상수(STRIP_TICK_H)가 없다 — 선과 글자가 따로 놀게 된다');
if (!mt) { console.log('FAILED ' + bad); process.exit(1); }
const TICK = +mt[1];
ok(TICK >= 1 && TICK <= 6 && 24 % TICK === 0,
   `눈금 간격 ${TICK}시간은 24를 나누지 못한다 — 끝이 안 맞는다`);

// 선을 긋는 쪽과 글자를 찍는 쪽이 **같은 상수**를 쓰는가
const gridLoop = H.match(/for\(let hh=STRIP_TICK_H; hh<24; hh\+=STRIP_TICK_H\)/);
const labLoop  = H.match(/for\(let hh=0; hh<24; hh\+=STRIP_TICK_H\)/);
ok(gridLoop, '세로 실선이 STRIP_TICK_H 를 안 쓴다');
ok(labLoop,  '시각 글자가 STRIP_TICK_H 를 안 쓴다');

// 실제로 만들어 보고 대조
const hm = n => String(n).padStart(2, '0') + ':00';
const STRIP_TICK_H = TICK;
const src = H.match(/const ticks = \[\];[\s\S]*?ticks\.push\('<span class="sxt" style="right:0;transform:none">23:59<\/span>'\);/);
ok(src, '글자 만드는 조각을 못 찾았다');
if (src) {
  let ticks;
  eval(src[0].replace('const ticks = [];', 'ticks = [];'));
  const texts = ticks.map(t => t.match(/>([^<]+)</)[1]);
  const hours = [];
  for (let hh = TICK; hh < 24; hh += TICK) hours.push(hh);
  for (const h of hours) {
    ok(texts.includes(hm(h)), `격자선 ${hm(h)} 에 글자가 없다`);
  }
  ok(texts[0] === '00:00', '왼쪽 끝이 00:00 이 아니다');
  ok(texts[texts.length - 1] === '23:59',
     `오른쪽 끝이 23:59 가 아니다 (${texts[texts.length - 1]})`);
  ok(!texts.includes('24:00'), "'24:00' 은 없는 시각이다");
  // 자리(%)가 선과 같은 식인가 — 3시면 12.5%
  for (const h of hours) {
    const want = (h / 24 * 100).toFixed(4);
    ok(ticks.some(t => t.includes(`left:${want}%`)),
       `${hm(h)} 글자가 선(${want}%)과 다른 자리에 있다`);
  }
  ok(ticks[0].includes('left:0'), '00:00 이 왼쪽 끝에 안 붙었다');
}

// flex 로 흘리면 글자 상자가 균등 분배될 뿐이라 선과 어긋난다
ok(/\.stripax\{[^}]*position:relative/.test(H),
   '.stripax 가 절대 배치를 받칠 준비가 안 됐다');
ok(!/\.stripax\{[^}]*justify-content:space-between/.test(H),
   'flex space-between 으로 흘리면 선과 어긋난다');

console.log(bad ? ('FAILED ' + bad) : 'OK');
process.exit(bad ? 1 : 0);
