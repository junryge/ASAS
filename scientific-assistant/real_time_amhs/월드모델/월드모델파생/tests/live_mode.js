/* static/js/live_mode.js — [리플레이 | 실시간] 이 하는 일을 가짜 화면 위에서 돌려 본다.
   (tests/hmi_map.js 와 같은 수법 — 베낀 코드가 아니라 배포되는 그 파일을 읽어 돌린다.)

   ★본다
     · 처음 모드 — 기본 리플레이 · 이 브라우저가 마지막에 고른 것 · ?mode= · ?auto=1(관제 구간 조회)은 늘 리플레이
     · 실시간으로 — 웹소켓에 모드를 알리고, 리플레이 차를 지우고, 리플레이 장면은 버린다
     · PLAY · 일시정지 · 정지 — 서버에 묻는 것은 PLAY · 정지뿐 (일시정지는 화면만)
     · 시계는 뒤로 안 간다 · 다른 FAB 장면은 버린다
     · 리플레이로 — 실시간 PLAY 를 놓고(정지), 웹소켓에 알리고, 실시간 장면은 버린다
     · 다시 붙으면(웹소켓) 실시간 중일 때만 모드를 다시 알린다
     · 누가 이미 PLAY 중인 FAB 이면 같이 본다 */
const fs = require('fs'), path = require('path'), vm = require('vm');
const SRC = fs.readFileSync(process.env.LIVE_MODE_JS || path.join(__dirname, '..', 'static', 'js', 'live_mode.js'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { console.log('FAIL ' + m); bad++; } };

function page(opts) {
  opts = opts || {};
  const els = {};
  function El(id, data) {
    const cls = new Set();
    let html = '';
    return {
      id, style: {}, dataset: data || {}, textContent: '', title: '', className: '', firstChild: null,
      get innerHTML() { return html; },
      set innerHTML(v) { html = String(v); this.firstChild = html ? El(id + '>') : null; },
      classList: { toggle(c, on) { if (on === undefined ? !cls.has(c) : on) cls.add(c); else cls.delete(c); },
                   contains: c => cls.has(c), add: c => cls.add(c), remove: c => cls.delete(c) },
      appendChild() {}, querySelectorAll() { return []; }, setAttribute() {},
      // 같은 선택자면 같은 칸 — 시험이 '아래 300행 더 보기' 단추를 눌러 볼 수 있게
      _q: {}, querySelector(sel) { return this._q[sel] || (this._q[sel] = El(id + ' ' + sel)); },
      getBoundingClientRect() { return { left: 0, top: 0 }; }, clientWidth: 244, offsetWidth: 40,
    };
  }
  const filterBtns = ['all', 'warn', 'danger', 'hid'].map(f => El('f-' + f, { f }));
  const store = Object.assign({}, opts.store || {});
  const P = {
    sent: [], fetches: [], shown: [], applied: [], timers: [],
    store, els,
  };
  const g = {
    console, URLSearchParams, Date, Math, JSON, Promise, String, Object, Array, isNaN, encodeURIComponent,
    document: {
      title: 'OHT 월드모델 시뮬레이션', body: Object.assign(El('body'), { appendChild() {} }),
      head: { appendChild() {} }, getElementById: id => els[id] || (els[id] = El(id)),
      createElement: t => El('new-' + t), addEventListener() {},
      querySelectorAll: sel => (sel === '#sc-filter button' ? filterBtns : []),
    },
    localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    location: { search: opts.search || '' },
    setInterval: (fn, ms) => { P.timers.push([ms, fn]); return P.timers.length; },
    fetch: (url, o) => {
      P.fetches.push([url, o && o.body ? JSON.parse(o.body) : null]);
      const d = url.indexOf('/api/live/cmd') === 0 ? { playing: true, me_playing: true, table: 'oht_data_m16br' }
        : { ok: true, sys: 'M16HUB', rows: opts.scoreRows || [], fab_cuts: {} };
      return Promise.resolve({ ok: true, json: () => Promise.resolve(d), text: () => Promise.resolve(JSON.stringify(d)) });
    },
    ws: { readyState: 1, send: s => P.sent.push(JSON.parse(s)) },
    updateUI: d => { P.shown.push(d); g.document.getElementById('time-display').textContent = d.time_short || ''; },
    applyFab: (f, p) => { P.applied.push(f + '/' + p); g.currentFab = f; g.currentPrefix = p; return Promise.resolve(); },
    switchRTab: t => { P.tab = t; },
    currentFab: 'M16A', currentPrefix: 'BR',
    mapData: { vehicles: [1, 2], railCuts: [], blockedEdges: {}, hotspots: [], zoneCounts: {} },
    vehicleDisplay: { V1: {} }, obsHistory: [1], jamEvents: [1], _lastObsSampleTime: 'x', _lastJamCount: 2,
    drawMap() {}, refreshSidebar() {}, push3D() {},
    BOOT: Promise.resolve(),
  };
  g.window = g;
  vm.createContext(g);
  vm.runInContext(SRC, g, { filename: 'live_mode.js' });
  P.g = g;
  P.filterBtns = filterBtns;
  P.tick = () => P.timers.filter(t => t[0] === 250).forEach(t => t[1]());
  P.clock = () => g.document.getElementById('time-display').textContent;
  return P;
}
const flush = () => new Promise(r => setImmediate(r));
const replayFrame = t => ({ time: '2026-10-06 ' + t, time_short: t, state: 'paused', vehicles: [] });
const liveFrame = (t, extra) => ({ time: '2026-10-06 ' + t, time_short: t, state: 'playing', vehicles: [{ vid: 'V1' }],
  live: Object.assign({ fab: 'M16A', prefix: 'BR', table: 'oht_data_m16br', playing: false, me_playing: false,
                        shown_time: '2026-10-06 ' + t, lag_sec: 9, vehicles: 1, poll_sec: 5, step_sec: 60 }, extra || {}) });

(async () => {
  // ── 1) 기본은 리플레이 — 실시간 장면은 버리고 리플레이 장면은 그린다 ──
  let P = page();
  ok(P.g.document.body.dataset.app === 'replay', '처음엔 리플레이');
  ok(P.sent.length === 0, '리플레이로 열면 웹소켓에 모드를 안 보낸다');
  P.g.updateUI(replayFrame('10:00:00'));
  P.g.updateUI(liveFrame('10:00:01'));
  ok(P.shown.length === 1 && !P.shown[0].live, '리플레이에서는 실시간 장면을 버린다: ' + P.shown.length);

  // ── 2) 실시간으로 ──
  P.g.setAppMode('live');
  await flush();
  ok(P.g.document.body.dataset.app === 'live', 'body[data-app=live]');
  ok(P.store.oht_world_app_mode === 'live', '고른 모드를 이 브라우저에 남긴다');
  ok(JSON.stringify(P.sent[0]) === '{"action":"mode","mode":"live"}', '웹소켓에 실시간을 알린다: ' + JSON.stringify(P.sent));
  ok(Object.keys(P.g.vehicleDisplay).length === 0 && P.g.mapData.vehicles.length === 0, '리플레이 차를 지운다');
  ok(P.g.document.title.indexOf('실시간') >= 0, '창 제목');
  ok(P.fetches.some(f => f[0].indexOf('/api/score/feed') === 0), '실시간에 들어가면 관제 스코어를 부른다');
  const n0 = P.shown.length;
  P.g.updateUI(replayFrame('10:00:02'));
  ok(P.shown.length === n0, '실시간에서는 늦게 온 리플레이 장면을 버린다');
  P.g.updateUI(liveFrame('10:00:03'));
  ok(P.shown.length === n0, '■ 정지 상태에서는 장면을 화면에 얹지 않는다');
  ok(P.els['live-text'].innerHTML.indexOf('oht_data_m16br') >= 0 && P.els['live-text'].innerHTML.indexOf('실시간 PLAY') >= 0,
     '상태줄 — 테이블 · PLAY 안내: ' + P.els['live-text'].innerHTML);
  ok(P.els['status-badge'].textContent === '정지', '배지 정지');

  // ── 3) PLAY · 시계 ──
  P.g.liveCmd('play');
  await flush();
  const cmd = P.fetches.filter(f => f[0] === '/api/live/cmd');
  ok(cmd.length === 1 && cmd[0][1].action === 'play', 'PLAY 는 서버에 묻는다: ' + JSON.stringify(cmd));
  ok(P.els['status-badge'].textContent === '실시간', '배지 실시간');
  P.g.updateUI(liveFrame('10:00:10', { playing: true, me_playing: true }));
  ok(P.shown.length === n0 + 1 && P.shown[P.shown.length - 1].live, 'PLAY 중에는 실시간 장면을 그린다');
  P.tick();
  const c1 = P.clock();
  ok(c1 === '10:00:10', '시계 = 장면 시각: ' + c1);
  P.g.updateUI(liveFrame('10:00:08', { playing: true }));        // 칸 시각이 1~2초 어긋나 앞 장면이 늦게 온 것
  P.tick();
  ok(P.clock() >= c1, '★시계가 뒤로 가면 안 된다: ' + c1 + ' → ' + P.clock());
  const before = P.shown.length;
  P.g.updateUI(Object.assign(liveFrame('10:00:12'), { live: Object.assign(liveFrame('10:00:12').live, { fab: 'M14A', prefix: 'A' }) }));
  ok(P.shown.length === before, '다른 FAB 장면(지도를 바꾸는 사이)은 버린다');

  // ── 4) 일시정지는 화면만 ──
  P.g.liveCmd('pause');
  await flush();
  ok(P.fetches.filter(f => f[0] === '/api/live/cmd').length === 1, '일시정지는 서버에 안 묻는다 (조회는 계속)');
  const b2 = P.shown.length;
  P.g.updateUI(liveFrame('10:00:14', { playing: true }));
  ok(P.shown.length === b2, '일시정지 중에는 화면이 그 자리');
  ok(P.els['status-badge'].textContent === '일시정지', '배지 일시정지');

  // ── 5) 다시 붙으면 실시간일 때만 모드를 알린다 ──
  const s0 = P.sent.length;
  P.g.LiveMode.wsOpen();
  ok(P.sent.length === s0 + 1 && P.sent[P.sent.length - 1].mode === 'live', '실시간 중 다시 붙으면 모드를 다시 알린다');

  // ── 6) 리플레이로 — PLAY 를 놓고 알린다 ──
  P.g.setAppMode('replay');
  await flush();
  const cmd2 = P.fetches.filter(f => f[0] === '/api/live/cmd');
  ok(cmd2.length === 2 && cmd2[1][1].action === 'stop', '리플레이로 가면 실시간 PLAY 를 놓는다 (정지): ' + JSON.stringify(cmd2));
  ok(P.sent[P.sent.length - 1].mode === 'replay', '웹소켓에 리플레이를 알린다');
  ok(P.g.document.body.dataset.app === 'replay' && P.store.oht_world_app_mode === 'replay', 'body · 저장 둘 다 리플레이');
  ok(P.g.document.title === 'OHT 월드모델 시뮬레이션', '창 제목 되돌림');
  const b3 = P.shown.length;
  P.g.updateUI(liveFrame('10:00:20', { playing: true }));
  ok(P.shown.length === b3, '리플레이에서는 늦게 온 실시간 장면을 버린다');
  P.g.updateUI(replayFrame('09:00:00'));
  ok(P.shown.length === b3 + 1, '리플레이 장면은 다시 그린다');
  const s1 = P.sent.length;
  P.g.LiveMode.wsOpen();
  ok(P.sent.length === s1, '리플레이 중 다시 붙으면 아무것도 안 보낸다 (서버는 리플레이로 시작한다)');

  // ── 7) 처음 모드 ──
  P = page({ store: { oht_world_app_mode: 'live' } });
  ok(P.g.document.body.dataset.app === 'live' && P.sent.length === 1, '마지막에 실시간이었으면 실시간으로 연다');
  P = page({ store: { oht_world_app_mode: 'live' }, search: '?from=20261006100000&to=20261006101000&table=oht_data_m16br&auto=1' });
  ok(P.g.document.body.dataset.app === 'replay' && P.sent.length === 0, '★관제에서 넘어온 구간 조회(auto=1)는 늘 리플레이');
  P = page({ search: '?mode=live&fab=M16B&prefix=B' });
  await flush(); await flush();
  ok(P.g.document.body.dataset.app === 'live', '?mode=live');
  ok(P.applied.join() === 'M16B/B', '?fab=&prefix= 지도로 바꾼다 (부팅 뒤): ' + P.applied.join());
  P = page({ search: '?mode=replay', store: { oht_world_app_mode: 'live' } });
  ok(P.g.document.body.dataset.app === 'replay', '?mode=replay 가 저장된 것보다 먼저');

  // ── 8) 누가 이미 PLAY 중인 FAB 이면 같이 본다 ──
  P = page();
  P.g.setAppMode('live');
  P.g.updateUI(liveFrame('11:00:00', { playing: true, me_playing: false }));
  await flush();
  ok(P.fetches.some(f => f[0] === '/api/live/cmd' && f[1].action === 'play'), '첫 장면이 PLAY 중이면 같이 PLAY');
  ok(P.g.LiveMode.mode() === 'play', 'MODE = play');

  // ── 9) 스코어 탭 — 경계↑ · 위험↑ · HID·RET 개수 (고객: "몇 개 있는지 탭에 표시해 줘야") ──
  const row = (lv, hid) => ({ at: 'a' + Math.random(), datetime: '2026-10-06 10:00', time: '10:00', score: 50,
                              level: lv, reason: '', metrics: [], hid: hid || [] });
  P = page({ scoreRows: [row('정상'), row('경계'), row('위험', [{ z: '2' }]), row('초위험'), row('경계', [{ file: 'R.html' }]),
                         row('정상', [{ z: '3', file: 'S.html' }])] });
  P.g.setAppMode('live');
  await flush(); await flush();
  P.els['rtab-score'].style.display = 'block';
  P.g.LiveMode.renderScore();
  const lab = P.filterBtns.map(b => b.innerHTML).join(' | ');
  ok(lab === '전체 <b>6</b> | 경계↑ <b>4</b> | 위험↑ <b>2</b> | HID·RET <b>3</b>', '필터 단추에 개수: ' + lab);
  const sum = P.els['sc-sum'].innerHTML;
  ok(sum.indexOf('오늘 10:00~10:00') >= 0 && sum.indexOf('경계↑ 4') >= 0 && sum.indexOf('위험↑ 2') >= 0, '요약에 오늘 · 경계↑ · 위험↑ 개수: ' + sum);
  ok(/HID_JAM<\/b> <b class="lv-red">2</.test(sum) && /RET<\/b> <b class="lv-red">2</.test(sum), '요약에 HID_JAM · RET 따로: ' + sum);
  P = page({ scoreRows: [row('정상')] });
  P.g.setAppMode('live');
  await flush(); await flush();
  P.els['rtab-score'].style.display = 'block';
  P.g.LiveMode.renderScore();
  ok(P.els['sc-sum'].innerHTML.indexOf('위험↑ 0') >= 0 && P.els['sc-sum'].innerHTML.indexOf('risk-DANGER') < 0, '0 이면 칩 대신 흐린 글자');

  // ── 10) 오늘 하루 전부 — '전체' 는 정상 줄만 300행씩 접고, 경계 · 위험 · HID·RET 는 몇 시든 늘 보인다 ──
  //   고객(2026-10-07): "12:40분~현재까지 보여주네 — 오늘 하루 동안 벌어진 것 보여줘야지" ·
  //   "실시간 관제처럼 아래 300행 보기" · "경계 · 위험 · HID RET 는 전부 다 보여야지 그래도"
  const hm = i => { const m = 699 - i; return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };
  const day = [];
  for (let i = 0; i < 700; i++) {            // 최신이 위 — d0 = 11:39 · d699 = 00:00
    const lv = (i === 650 || i === 651) ? '경계' : '정상';
    day.push({ at: 'd' + i, datetime: '2026-10-07 ' + hm(i), time: hm(i), score: lv === '경계' ? 64 : 40,
               level: lv, reason: '', metrics: [], hid: i === 680 ? [{ z: '9' }] : [] });
  }
  P = page({ scoreRows: day });
  P.g.setAppMode('live');
  await flush(); await flush();
  P.els['rtab-score'].style.display = 'block';
  P.g.LiveMode.renderScore();
  ok(P.fetches.some(f => f[0].indexOf('/api/score/feed?limit=1440') === 0), '하루치(1440분)를 묻는다');
  const cnt = h => (h.match(/class="ritem"/g) || []).length;
  let L = P.els['sc-list'].innerHTML;
  ok(cnt(L) === 303, '전체 = 최근 정상 300 + 300행 밖 경계 2 · HID 1: ' + cnt(L));
  ok(L.indexOf('data-at="d650"') >= 0 && L.indexOf('data-at="d651"') >= 0 && L.indexOf('data-at="d680"') >= 0,
     '300행 밖의 경계 · HID 줄도 그린다');
  ok(L.indexOf('⋯ 정상 350행') >= 0 && L.indexOf('⋯ 정상 28행') >= 0, '접은 자리에 몇 행인지');
  ok(L.indexOf('아래 300행 더 보기') >= 0 && L.indexOf('303 / 700행 표시 중 · 접은 정상 397행') >= 0, '더 보기 · 몇 행 표시 중');
  ok(P.els['sc-sum'].innerHTML.indexOf('오늘 00:00~11:39') >= 0, '요약은 오늘 처음~지금: ' + P.els['sc-sum'].innerHTML.slice(0, 120));
  ok(P.els['sc-spark'].innerHTML.indexOf('00:00~11:39 (700분)') >= 0, '추이도 오늘 하루');
  P.els['sc-list'].querySelector('[data-more]').onclick();
  L = P.els['sc-list'].innerHTML;
  ok(cnt(L) === 603 && L.indexOf('아래 97행 더 보기') >= 0 && L.indexOf('⋯ 정상 50행') >= 0, '더 보기 → 정상 300행 더: ' + cnt(L));
  P.filterBtns[1].onclick();                 // 경계↑ — 접지 않는다
  L = P.els['sc-list'].innerHTML;
  ok(cnt(L) === 2 && L.indexOf('더 보기') < 0 && L.indexOf('⋯ 정상') < 0, '경계↑ 는 전부 · 접지 않는다');
  P.filterBtns[3].onclick();                 // HID·RET
  L = P.els['sc-list'].innerHTML;
  ok(cnt(L) === 1 && L.indexOf('data-at="d680"') >= 0, 'HID·RET 는 전부');
  P.filterBtns[0].onclick();                 // 전체로 돌아오면 다시 300행부터
  ok(cnt(P.els['sc-list'].innerHTML) === 303, '필터를 바꾸면 다시 300행부터');

  console.log(bad ? 'FAILED ' + bad : 'OK');
  process.exit(bad ? 1 : 0);
})();
