/* 월드모델파생 — 실시간 모드 (2026-10-06).

   고객: "월드모델 파생, OHT 실시간 같은 포트 사용하게 해 주라. 리플레이 모드 · 실시간 모드 변경
         가능하게" · "10005번 포트" · "메인은 월드모델파생이 메인이야!"
   → 따로 띄우던 실시간판(10006)을 이 화면에 합쳤다. 맨 위 [⏪ 리플레이 | ● 실시간] 으로 바꾼다.

   어떻게 바꾸나
     · body[data-app] = 'replay' | 'live' — 리플레이에만 있는 것(.replay-only)과 실시간에만 있는 것
       (.live-only)을 CSS 가 숨기고 보인다 (dashboard.html 위쪽 <style>). 단추 · 칸은 dashboard.html 에
       있고, 여기는 하는 일만 있다.
     · 웹소켓(/ws) 하나를 그대로 쓴다 — {"action":"mode","mode":"live"} 를 보내면 서버가 이 탭에는
       실시간 장면을 1초마다 보낸다. 탭마다 따로라 한 탭은 리플레이, 다른 탭은 실시간으로 볼 수 있다.
       다시 붙으면(끊김) 서버는 리플레이로 시작하므로 모드를 다시 알린다 (connectWS → LiveMode.wsOpen).
     · 들어갈 때 — 리플레이는 그 자리에 세워 둔다 (서버). 맵의 리플레이 차는 지운다.
       나올 때 — 실시간 PLAY 를 놓는다 (그 FAB 을 다른 사람이 안 보면 로그프레소 조회가 멎는다).
       맵의 실시간 차는 지운다 — 리플레이 장면이 바로 다시 온다.
     · 고른 모드는 이 브라우저에 남는다. 주소 ?mode=live (&fab=M16A&prefix=BR) 로 바로 열 수 있다.
       관제에서 넘어온 구간 조회(?auto=1)는 늘 리플레이로 연다.

   실시간 안에서 — [▶ 실시간 PLAY] [⏸ 일시정지] [■ 정지]
       PLAY      로그프레소를 묻기 시작 (보는 FAB 하나만) · 시계가 흐른다
       일시정지  화면만 그 자리에 세운다 (조회는 계속 — 다시 PLAY 하면 지금으로)
       정지      조회를 멈춘다 (저절로 멈추지 않는다 — 고객 2026-10-06)
     · 상태줄: [● 실시간] 테이블 · OHT 시각(지금보다 몇 초 늦은지) · 차 · 조회 · 관제 스코어 칩.
     · 오른쪽 '스코어' 탭 (관제가 매긴 그 FAB 의 점수 — 여기서 다시 계산하지 않는다)
       지금 점수 · 등급 · 알람 · HI_FAB → 오늘 하루 추이 → 지금 걸린 것(발동 룰 · 실제지표 · HID_JAM ·
       RET) → 오늘 목록(관제 표처럼 300행씩 · 경계↑ · 위험↑ · HID·RET 는 전부). 줄을 더블클릭하면
       관제와 같은 구간 그래프.
   ★색은 화면에 있던 것만 쓴다 — 등급은 risk-NORMAL/WARNING/DANGER/CRITICAL 칩, 줄 왼쪽 띠는
     차량 목록과 같은 초록·주황·빨강. 색만으로 말하지 않는다 — 늘 글자(정상·경계·위험·초위험)와 같이. */
(function () {
  'use strict';
  var $id = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function post(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json(); });
  }
  function hms(s) { return s ? String(s).slice(11, 19) : '--:--:--'; }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  // 이 브라우저에만 남기는 것 (고른 모드) — 막혀 있어도 화면은 돈다
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 사생활 보호 창 등 */ } }

  /* ── 조각 전용 모양 — 관제 기여도 HTML 이 쓰는 이름을 이 화면 변수로 잇는다 (새 색 없음) ── */
  var css = document.createElement('style');
  css.textContent = [
    '#live-gmodal{--tx:var(--fg);--tx2:var(--fg2);--tx3:var(--muted);--txb:var(--fg);--major:#f59e0b;--crit:#ef4444}',
    '#live-gmodal .note{color:var(--fg2);font-size:11px}',
    '#live-gmodal .empty{color:var(--muted);text-align:center;padding:28px;font-size:12px}',
    '#live-gmodal .mono{font-family:Consolas,"D2Coding",monospace}',
    '#live-gmodal .chip{display:inline-block;padding:1px 6px;border-radius:3px;background:var(--chip);color:var(--chip-fg);font-size:10px}',
    '#live-gmodal .chip.lv위험{background:#7f1d1d;color:#fca5a5}',
    '#live-gmodal #lg-body svg{max-width:100%;height:auto;display:block}',
    '#live-gmodal .lg-line{font-size:12px;color:var(--fg2);margin:-2px 0 10px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}',
    '#live-gmodal select{background:var(--ctl);color:var(--ctl-fg);border:1px solid var(--ctl-line);border-radius:6px;padding:4px 8px;font-size:12px}',
    '#rtab-score .sc-big{font-size:30px;line-height:1;font-weight:800;color:var(--fg);font-variant-numeric:tabular-nums}',
    '#rtab-score .sc-cap{font-size:10px;color:var(--muted);margin:2px 2px 0}',
    '#rtab-score .sc-tip{position:absolute;top:2px;pointer-events:none;background:var(--card);color:var(--fg);border:1px solid var(--line2);border-radius:4px;padding:2px 6px;font-size:11px;white-space:nowrap;display:none}',
    '#rtab-score .sc-mono{font-family:Consolas,"D2Coding",monospace;font-size:9.5px;word-break:break-all}',
    '#rtab-score #sc-list{max-height:none}',
    '#rtab-score .sc-rule{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:normal;color:var(--fg2)}',
    '.lv-red{color:#ef4444;font-weight:700}'
  ].join('\n');
  document.head.appendChild(css);

  var APP = 'replay';         // 화면 모드 — 'replay' | 'live'
  var MODE = 'stop';          // 실시간 안에서 — 'play' | 'pause' | 'stop'
  var INIT = true;            // 실시간에 들어와 첫 장면 — 그 FAB 을 누가 이미 PLAY 중이면 같이 본다
  var LAST = null, LAST_AT = 0, LIVE = null;
  var SHOW = 0;               // 화면 시계(ms) — ★절대 뒤로 안 간다 (고객: "늘었다 다시 과거로 가면 안 돼")
  var GOT_AT = 0;             // 마지막으로 실시간 장면을 받은 때 — 끊김 표시
  var ERR = '';               // 실시간 명령이 서버에 안 닿았을 때
  var APP_KEY = 'oht_world_app_mode';
  var TITLE = document.title;

  function wsSend(o) {
    // ws 는 dashboard.html 의 웹소켓 (맨 위 let) — 아직 안 열렸으면 열릴 때 wsOpen 이 보낸다
    try { if (typeof ws !== 'undefined' && ws && ws.readyState === 1) ws.send(JSON.stringify(o)); } catch (e) { /* 다음에 */ }
  }
  function wsOpen() { if (APP === 'live') wsSend({ action: 'mode', mode: 'live' }); }

  // 다른 모드의 차를 지운다 — 남겨 두면 몇 초 동안 두 모드의 차가 섞여 보인다 (화면 전역은 dashboard.html 것)
  function clearView() {
    try { vehicleDisplay = {}; } catch (e) { /* 옛 화면 */ }
    try {
      mapData.vehicles = []; mapData.railCuts = []; mapData.blockedEdges = {};
      mapData.hotspots = []; mapData.zoneCounts = {};
    } catch (e) { /* 옛 화면 */ }
    try { obsHistory = []; jamEvents = []; _lastObsSampleTime = ''; _lastJamCount = 0; } catch (e) { /* 옛 화면 */ }
    var td = $id('time-display');
    if (td) td.textContent = '--:--:--';
    try { push3D({}); } catch (e) { /* 3D 가 꺼져 있다 */ }
    try { refreshSidebar(true); } catch (e) { /* 옛 화면 */ }
    try { drawMap(); } catch (e) { /* 옛 화면 */ }
  }

  /* ════════════ 1) [리플레이 | 실시간] ════════════ */
  function setAppMode(m) {
    m = m === 'live' ? 'live' : 'replay';
    if (m === APP) return;
    var was = APP;
    APP = m;
    document.body.dataset.app = m;
    var r = $id('app-replay'), l = $id('app-live');
    if (r) r.classList.toggle('on', m === 'replay');
    if (l) l.classList.toggle('on', m === 'live');
    save(APP_KEY, m);
    if (m === 'live') {
      INIT = true; MODE = 'stop'; LAST = null; LIVE = null; SHOW = 0; GOT_AT = 0; ERR = '';
      document.title = 'OHT 월드모델 — 실시간';
      clearView();
      wsSend({ action: 'mode', mode: 'live' });       // 서버는 리플레이를 그 자리에 세운다
      badge();
      paint(null);
      scoreLoad();
    } else {
      // 실시간 PLAY 를 놓는다 — 그 FAB 을 다른 사람이 안 보면 로그프레소 조회가 멎는다
      if (was === 'live') post('/api/live/cmd', { action: 'stop' }).catch(function () { /* 서버가 꺼졌다 */ });
      MODE = 'stop';
      document.title = TITLE;
      wsSend({ action: 'mode', mode: 'replay' });
      clearView();
      var sc = $id('rtab-score');
      if (sc && sc.style.display !== 'none' && typeof window.switchRTab === 'function') window.switchRTab('oht');
      closeGraph();
      var b = $id('status-badge');
      if (b) { b.textContent = '정지'; b.className = 'badge badge-stopped'; }   // 리플레이 장면이 곧 고친다
    }
  }

  /* ════════════ 2) 실시간 PLAY · 일시정지 · 정지 ════════════ */
  function liveCmd(m) {
    if (APP !== 'live') return;
    MODE = m;
    badge();
    if (m === 'play' || m === 'stop') {
      post('/api/live/cmd', { action: m })
        .then(function (L) { ERR = ''; if (L && !L.error) { LIVE = L; paint(L); } })
        .catch(function (e) { ERR = String((e && e.message) || e); paint(LIVE); });
    }
    paint(LIVE);
  }

  function badge() {
    if (APP !== 'live') return;
    var b = $id('status-badge');
    if (!b) return;
    if (MODE === 'play') { b.textContent = '실시간'; b.className = 'badge badge-playing'; }
    else if (MODE === 'pause') { b.textContent = '일시정지'; b.className = 'badge badge-paused'; }
    else { b.textContent = '정지'; b.className = 'badge badge-stopped'; }
  }

  function paint(L) {
    var t = $id('live-text'), dot = $id('live-dot');
    if (!t || !dot) return;
    if (ERR) {
      dot.className = 'badge badge-stopped';
      dot.textContent = '● 연결 끊김';
      t.innerHTML = '<b style="color:#dc2626">서버에 닿지 않습니다 — ' + esc(ERR) + '</b>';
      return;
    }
    if (!L) { t.textContent = '실시간 서버 응답을 기다리는 중…'; return; }
    if (MODE === 'stop' || !L.playing) {
      dot.className = 'badge badge-stopped';
      dot.textContent = '■ 정지';
      t.innerHTML = '<b style="color:var(--fg)">' + esc(L.table) + '</b> · [▶ 실시간 PLAY] 를 누르면 '
        + '지금 데이터를 받습니다 (지금 보는 FAB 하나만 묻습니다)'
        + (L.shown_time ? ' · 마지막 OHT ' + hms(L.shown_time) : '');
      return;
    }
    var p = ['<b style="color:var(--fg)">' + esc(L.table) + '</b>'];
    if (MODE === 'pause') p.push('<b style="color:var(--time)">일시정지</b> — 조회는 계속됩니다');
    if (L.shown_time) {
      p.push('OHT <b style="color:var(--time)">' + hms(L.shown_time) + '</b>'
        + (L.lag_sec != null ? ' (지금보다 ' + L.lag_sec + '초 늦음)' : ''));
    } else {
      p.push(L.polls ? '아직 받은 줄이 없습니다' : '처음 받는 중…');
    }
    p.push('차 ' + (L.vehicles || 0) + '대');
    if (L.filled_sec != null && L.filled_sec < (L.warm_sec || 300)) {
      p.push('처음 ' + Math.round((L.warm_sec || 300) / 60) + '분 중 ' + Math.floor(L.filled_sec / 60) + '분 채움');
    }
    p.push((L.poll_sec || 5) + '초마다 · 한 번에 ' + (L.step_sec || 60) + '초씩');
    if (L.cuts) p.push('응답 끊김 ' + L.cuts + '번 (받은 데까지 씀)');
    if (L.error) p.push('<b style="color:#dc2626">조회 실패 ' + esc(L.fails || '') + '번 — ' + esc(L.error) + '</b>');
    t.innerHTML = p.join(' · ');
    var stale = L.data_lag_sec != null && L.data_lag_sec > 120;
    var bad = !!L.error || stale;
    dot.className = 'badge ' + (bad ? 'badge-stopped' : MODE === 'pause' ? 'badge-paused' : 'badge-playing');
    dot.textContent = bad ? (L.error ? '● 실시간 (조회 실패)' : '● 실시간 (데이터 늦음)')
      : MODE === 'pause' ? '⏸ 일시정지' : '● 실시간';
    dot.title = '로그프레소 ' + (L.server || '') + ' · 키 ' + (L.key || '')
      + ' · 받은 데이터 ' + hms(L.data_time)
      + (L.data_lag_sec != null ? ' (지금보다 ' + L.data_lag_sec + '초 전)' : '')
      + ' · 화면은 ' + (L.buffer_sec || 0) + '초 늦춰 2초 칸을 차례로 보입니다 (부드럽게)'
      + ' · 미보고 기준 ' + (L.miss_sec || 50) + '초';
  }

  /* ════════════ 3) 장면 — 모드에 맞는 것만 화면에 얹는다 ════════════ */
  // ★웹소켓 하나로 두 모드의 장면이 오므로, 바꾼 직후 늦게 도착한 다른 모드 장면은 버린다
  //   (실시간 장면에는 'live' 가 붙어 있다). 다른 FAB 의 장면(지도를 바꾸는 사이)도 버린다.
  var origUpdate = window.updateUI;
  window.updateUI = function (d) {
    var L = d && d.live;
    if (APP !== 'live') {
      if (L) return;
      return origUpdate(d);
    }
    if (!L) return;
    if (typeof currentFab !== 'undefined' && currentFab && (L.fab !== currentFab || L.prefix !== currentPrefix)) return;
    LIVE = L;
    GOT_AT = Date.now();
    ERR = '';
    if (INIT) {
      INIT = false;
      if (L.playing && MODE !== 'play') liveCmd('play');   // 누가 이미 PLAY 중이면 같이 본다 (다시 열었을 때도)
    }
    if (MODE === 'play' && d.time) {
      origUpdate(d);
      // ★시계 기준은 **장면이 바뀔 때만** 잡는다 — 같은 장면이 1초마다 다시 오는데 그때마다
      //   잡으면 시계가 그 초에 붙어 안 흐른다
      if (!LAST || LAST.time !== d.time) LAST_AT = Date.now();
      LAST = d;
      tickClock();          // ★화면 함수가 방금 시계를 장면 시각으로 되돌려 놓았다 — 같은 차례에 다시 쓴다
    }
    badge();
    try { paint(L); } catch (e) { /* 상태줄 실패로 화면을 멈추지 않는다 */ }
  };

  // PLAY 중에는 시계가 초 단위로 흐른다 — 2초 칸 사이를 벽시계로 메운다 (칸 하나 넘게는 안 간다).
  // ★절대 뒤로 안 간다. 다음 장면이 시계보다 앞이면(칸 시각은 그 칸의 마지막 보고 시각이라 1초
  //   어긋날 수 있다) 따라올 때까지 그 자리에서 기다린다. 앞으로 크게 뛰는 것은 정지했다 다시
  //   PLAY 해서 '지금' 으로 건너뛸 때뿐이다.
  function tickClock() {
    var el = $id('time-display');
    if (!el || APP !== 'live' || MODE !== 'play' || !LAST || !LAST.time) return;
    var b = Date.parse(LAST.time.replace(' ', 'T'));
    if (isNaN(b)) return;
    var t = b + Math.min(Date.now() - LAST_AT, 2000);
    if (t < SHOW) t = SHOW;
    SHOW = t;
    var d = new Date(t);
    el.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  setInterval(tickClock, 250);
  // 실시간 장면이 끊겼을 때 (서버가 꺼졌거나 웹소켓이 다시 붙는 중)
  setInterval(function () {
    if (APP !== 'live' || !GOT_AT || Date.now() - GOT_AT < 5000) return;
    var t = $id('live-text'), dot = $id('live-dot');
    if (t) t.innerHTML = '<b style="color:#dc2626">실시간 장면이 ' + Math.round((Date.now() - GOT_AT) / 1000)
      + '초째 안 옵니다 — 서버(10005)가 켜져 있는지 보세요 (다시 붙으면 저절로 이어집니다)</b>';
    if (dot) { dot.className = 'badge badge-stopped'; dot.textContent = '● 연결 끊김'; }
  }, 2000);

  /* ════════════ 4) 관제 스코어 — 오른쪽 '스코어' 탭 ════════════ */
  var GRADE = { '정상': { cls: 'NORMAL', c: '#22c55e' }, '경계': { cls: 'WARNING', c: '#f59e0b' },
                '위험': { cls: 'DANGER', c: '#ef4444' }, '초위험': { cls: 'CRITICAL', c: '#ef4444' } };
  function gradeOf(lv) { return GRADE[lv] || { cls: 'NORMAL', c: 'var(--line2)' }; }
  function lvChip(lv) { return '<span class="risk risk-' + gradeOf(lv).cls + '">' + esc(lv || '-') + '</span>'; }
  function almText(a) {
    if (!a || !a.lv) return '';
    var n = a.lv === '초위험중' ? a.c : a.lv === '위험중' ? a.d : a.w;
    return a.lv + (n != null ? ' ' + n : '');
  }
  function almChip(a) {
    var t = almText(a);
    if (!t) return '';
    return '<span class="risk risk-' + gradeOf(a.lv.replace('중', '')).cls + '" title="' + esc(a.why || '') + '">'
      + esc(t) + '</span>';
  }
  function rulesOf(r) {
    return String((r && r.reason) || '').split(/\s*·\s*|\r?\n/).map(function (x) { return x.trim(); })
      .filter(Boolean);
  }
  function retHref(h) {
    return '/api/score/report?day=' + encodeURIComponent(h.d || '') + '&name=' + encodeURIComponent(h.file || '');
  }
  // HID_JAM · RET(레포트) — 관제 그래프 창과 같은 모양 (값 · 링크는 빨강 굵게). 없으면 아무것도 안 쓴다
  function hidLine(r) {
    var hs = (r && r.hid) || [];
    var z = hs.filter(function (h) { return h.z; }), f = hs.filter(function (h) { return h.file; });
    var out = '';
    if (z.length) out += '<b style="color:var(--fg)">HID_JAM</b> <b class="lv-red">'
      + z.map(function (h) { return esc(h.z); }).join(' · ') + '</b>';
    if (f.length) out += (z.length ? ' · ' : '') + '<b style="color:var(--fg)">RET(레포트)</b> '
      + f.map(function (h) {
        return '<a class="lv-red" href="' + retHref(h) + '" download="' + esc(h.file) + '" title="' + esc(h.file)
          + '" onclick="event.stopPropagation()">링크</a>';
      }).join(' ');
    return out;
  }

  var SCORE = null, SC_FILTER = 'all';
  // ★오늘 하루 전부를 받는다. 예전엔 최근 90분만 받아서, 그 앞에 난 경계가 목록에 없었다
  //   (고객 2026-10-07: "12:40분~현재까지 보여주네 — 오늘 하루 동안 벌어진 것 보여줘야지").
  //   목록은 관제 표처럼 300행씩 그리고 '아래 300행 더 보기' ("실시간 관제처럼 아래 300행 보기").
  //   경계↑ · 위험↑ · HID·RET 는 상한 없이 전부 ("경계 · 위험 · HID RET 는 전부 다 보여야지").
  var SC_DAY = 1440, SC_STEP = 300, SC_CAP = SC_STEP;
  // 1분에 한 번 바뀌는데 15초마다 묻는다 — 받은 글이 같으면 목록을 다시 그리지 않는다
  var SC_TXT = '', SC_VER = 0, SC_DRAWN = '';

  // 경계↑ · 위험↑ · HID·RET 가 몇 개인지 (고객: "경계, 위험, HID RET 몇 개 있는지 탭에 표시해 줘야") —
  // 필터 단추마다 개수, 탭 위 요약에 HID_JAM · RET 를 나눠서. 세는 기준은 필터와 같다 (단추 수 = 누르면 나오는 줄 수).
  var F_NAME = { all: '전체', warn: '경계↑', danger: '위험↑', hid: 'HID·RET' };
  function counts(rows) {
    var c = { all: rows.length, warn: 0, danger: 0, hid: 0, jam: 0, ret: 0,
              from: rows.length ? rows[rows.length - 1].time : '', to: rows.length ? rows[0].time : '' };
    rows.forEach(function (r) {
      var hs = r.hid || [];
      if (r.level && r.level !== '정상') c.warn++;
      if (r.level === '위험' || r.level === '초위험') c.danger++;
      if (hs.length) c.hid++;
      if (hs.some(function (h) { return h.z; })) c.jam++;
      if (hs.some(function (h) { return h.file; })) c.ret++;
    });
    return c;
  }
  function paintCounts(c) {
    document.querySelectorAll('#sc-filter button').forEach(function (b) {
      var f = b.dataset.f;
      b.innerHTML = esc(F_NAME[f] || f) + (c ? ' <b>' + c[f] + '</b>' : '');
    });
  }
  // 요약 줄 — 0 이면 흐리게, 있으면 등급 칩(경계 · 위험) · 빨강 굵게(HID_JAM · RET — 그래프 창과 같은 모양)
  function cntChip(label, n, cls) {
    return n ? '<span class="risk ' + cls + '">' + label + ' ' + n + '</span>'
      : '<span style="color:var(--muted);white-space:nowrap">' + label + ' 0</span>';
  }
  function cntRed(label, n) {
    return n ? '<span style="white-space:nowrap"><b style="color:var(--fg)">' + label + '</b> <b class="lv-red">' + n + '</b></span>'
      : '<span style="color:var(--muted);white-space:nowrap">' + label + ' 0</span>';
  }
  function countLine(c) {
    // 관제에 오늘 자료가 아직 없어 지난 날을 보여 줄 때는 '오늘' 이 아니라 그 날짜
    var day = SCORE && SCORE.fallback && SCORE.day ? esc(SCORE.day) : '오늘';
    return (c.from ? day + ' ' + esc(c.from) + '~' + esc(c.to) : day + ' ' + c.all + '분') + ' · ' + cntChip('경계↑', c.warn, 'risk-WARNING') + ' '
      + cntChip('위험↑', c.danger, 'risk-DANGER') + ' · ' + cntRed('HID_JAM', c.jam) + ' · ' + cntRed('RET', c.ret);
  }

  var chip = $id('live-score');
  if (chip) chip.onclick = function () {
    var rs = $id('rsidebar');
    if (rs && rs.classList.contains('collapsed') && typeof toggleRSidebar === 'function') toggleRSidebar();
    window.switchRTab('score');
  };
  document.querySelectorAll('#sc-filter button').forEach(function (b) {
    b.onclick = function () {
      SC_FILTER = b.dataset.f;
      SC_CAP = SC_STEP;
      document.querySelectorAll('#sc-filter button').forEach(function (x) { x.classList.toggle('active', x === b); });
      renderList();
    };
  });

  // ── 관제 주소 — 관제가 다른 서버에 있으면 여기서 그 주소로 바꾼다 (이 PC 에만 저장) ──
  // ★고객(2026-10-07): "실시간관제 외부에서 접속하게 해야지 127.0.0.1 하면 안 되지" · "실시간에서
  //   다른 서버에서 접속하는데 경계가 있어야 하는데 없네". 127.0.0.1 은 '월드모델파생이 도는 이 PC'
  //   라서, 관제가 다른 서버에 있으면 그 관제의 경계 · 위험 줄을 못 받는다.
  function gwLink(S) {
    var src = S && S.gwanje_src;
    return '<a href="#" class="sc-gw" style="color:var(--fg2);text-decoration:none" '
      + 'title="관제 주소는 스스로 찾습니다 (이 PC → 관제 설정의 IP → 관제 화면에서 넘어온 주소 → 이 서버). 직접 정하려면 누르세요">'
      + '관제 ' + esc((S && S.gwanje) || '?')
      + (src === 'default' ? ' (이 PC)' : src === 'auto' ? ' (자동)' : src === 'env' ? ' (환경변수)' : '') + '</a>';
  }
  function bindGw() {
    document.querySelectorAll('#sc-sum .sc-gw').forEach(function (a) { a.onclick = gwEdit; });
  }
  function gwEdit(e) {
    if (e) e.preventDefault();
    var cur = (SCORE && SCORE.gwanje) || '';
    var v = window.prompt('관제 주소 — 관제가 떠 있는 서버 (예: http://10.1.2.3:8989)\n'
      + '브라우저로 관제를 열 때 쓰는 주소입니다. 비우면 이 PC 의 관제로 돌아갑니다.', cur);
    if (v === null) return;
    fetch('/api/score/gwanje', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: v }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) window.alert(d.error || '관제에 닿지 않습니다');
        return scoreLoad();
      })
      .catch(function (err) { window.alert('저장하지 못했습니다 — ' + ((err && err.message) || err)); });
  }

  // 관제가 어디 있나 — 관제 화면에서 넘어왔으면 그 주소(?gw= · document.referrer)를 서버에 알려 준다.
  // ★고객(2026-10-07): "관제 주소를 왜 바꾸는데 — 처음부터 보이게 하면 되지". 서버가 이 PC · 이 주소 ·
  //   이 서버 주소 순으로 답하는 관제를 스스로 찾는다 (gwanje_score.resolve).
  var GW_HINT = (function () {
    var v = '';
    try { v = new URLSearchParams(location.search).get('gw') || ''; } catch (e) {}
    if (!v) {
      try { var u = new URL(document.referrer); if (u.origin !== location.origin) v = u.origin; } catch (e) {}
    }
    try { if (v) sessionStorage.setItem('gw_hint', v); else v = sessionStorage.getItem('gw_hint') || ''; } catch (e) {}
    return v;
  })();
  function gwQ() { return GW_HINT ? '&gw=' + encodeURIComponent(GW_HINT) : ''; }

  function scoreLoad() {
    if (APP !== 'live') return Promise.resolve();
    return fetch('/api/score/feed?limit=' + SC_DAY + gwQ(), { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (t !== SC_TXT) { SC_TXT = t; SC_VER++; }
        SCORE = JSON.parse(t);
      })
      .catch(function (e) { SCORE = { ok: false, error: '서버에 닿지 않습니다 — ' + ((e && e.message) || e) }; })
      .then(function () { paintScoreChip(); renderScore(); });
  }
  setInterval(scoreLoad, 15000);
  // 지도를 바꾸면 그 FAB 스코어로 바로 · 시계도 새로
  if (typeof window.applyFab === 'function') {
    var origApply = window.applyFab;
    window.applyFab = function (f, p) {
      SHOW = 0;               // 다른 FAB 의 시계 — 앞 FAB 시각에 붙어 기다리지 않게 새로
      LAST = null;
      if (MODE !== 'play') INIT = true;      // 새 FAB 을 누가 PLAY 중이면 같이 본다
      return Promise.resolve(origApply(f, p)).then(function (x) { scoreLoad(); return x; });
    };
  }

  function paintScoreChip() {
    var el = $id('live-score');
    if (!el) return;
    var r = SCORE && SCORE.ok && SCORE.rows && SCORE.rows[0];
    if (!r) {
      el.style.display = SCORE && !SCORE.ok ? '' : 'none';
      el.className = 'risk';
      el.style.background = 'var(--chip)';
      el.style.color = 'var(--chip-fg)';
      el.textContent = '스코어 —';
      el.title = (SCORE && SCORE.error) || '';
      return;
    }
    el.style.display = '';
    el.style.background = el.style.color = '';
    el.className = 'risk risk-' + gradeOf(r.level).cls;
    el.textContent = '스코어 ' + (r.time || '') + ' · ' + SCORE.sys + ' ' + Math.round(+r.score || 0) + ' · '
      + (r.level || '') + (almText(r.alm) ? ' · ' + almText(r.alm) : '');
    el.title = '스코어 시각 ' + (r.datetime || '') + ' — 관제가 1분마다 매긴 이 FAB 의 점수 (OHT 시각과 따로 간다)'
      + ' · 누르면 오른쪽 스코어 탭';
  }

  function minsAgo(dt) {
    var t = new Date(String(dt || '').replace(' ', 'T'));
    return isNaN(t) ? null : Math.round((Date.now() - t.getTime()) / 60000);
  }

  function renderScore() {
    var sc = $id('rtab-score');
    if (!sc || sc.style.display === 'none' || APP !== 'live') return;
    var S = SCORE;
    var sum = $id('sc-sum');
    if (!S) { sum.textContent = '관제 스코어를 불러오는 중…'; paintCounts(null); return; }
    if (!S.ok) {
      sum.innerHTML = '<b style="color:#dc2626">' + esc(S.error || '관제 스코어를 못 받았습니다') + '</b>'
        + '<div style="margin-top:4px">' + gwLink(S) + '</div>';
      bindGw();
      ['sc-now', 'sc-spark', 'sc-cur', 'sc-list'].forEach(function (id) { $id(id).innerHTML = ''; });
      SC_DRAWN = '';
      paintCounts(null);
      return;
    }
    var rows = S.rows || [], r = rows[0];
    var ago = r ? minsAgo(r.datetime) : null;
    var c = counts(rows);
    paintCounts(c);
    sum.innerHTML = '관제 <b>' + esc(S.sys) + '</b> 스코어 <b>' + esc(r ? r.time || '' : '') + '</b> · 1분마다'
      + (S.fallback ? ' · <b style="color:#f59e0b">오늘 수집이 없어 ' + esc(S.day) + ' 자료</b>' : '')
      + (ago != null && ago > 5 && !S.fallback ? ' · <b style="color:#f59e0b">마지막 ' + esc((r.datetime || '').slice(11, 16)) + ' (' + ago + '분 전)</b>' : '')
      + (rows.length ? '<div id="sc-count" style="margin-top:4px">' + countLine(c) + '</div>' : '')
      + '<div style="margin-top:2px">' + gwLink(S) + '</div>';
    bindGw();
    if (!r) {
      $id('sc-now').innerHTML = '<div class="ritem" style="cursor:default">관제 표에 아직 줄이 없습니다</div>';
      ['sc-spark', 'sc-cur', 'sc-list'].forEach(function (id) { $id(id).innerHTML = ''; });
      SC_DRAWN = '';
      return;
    }
    var g = gradeOf(r.level);
    var hi = r.hi_fab && r.hi_fab !== S.sys ? ' <span title="이 분에 제일 높은 FAB 이 다른 곳입니다">≠ ' + esc(S.sys) + '</span>' : '';
    $id('sc-now').innerHTML =
      '<div class="ritem" style="border-left-color:' + g.c + ';cursor:pointer" data-at="' + esc(r.at) + '" title="더블클릭 → 구간 그래프">'
      + '<div class="rh"><span class="rid">' + esc(S.sys) + ' 스코어</span><span class="rst">' + esc(r.time || '') + ' 기준</span></div>'
      + '<div style="display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap">'
      + '<span class="sc-big">' + Math.round(+r.score || 0) + '</span>' + lvChip(r.level) + ' ' + almChip(r.alm) + '</div>'
      + (r.hi_fab ? '<div class="rv" style="font-weight:normal;color:var(--fg2)">HI_FAB <b style="color:var(--fg)">' + esc(r.hi_fab) + '</b>' + hi + '</div>' : '')
      + '</div>';
    $id('sc-now').firstChild.ondblclick = function () { openGraph(r.at); };
    renderSpark(rows, (S.fab_cuts || {})[S.sys]);
    // 지금 걸린 것
    var rules = rulesOf(r), mets = r.metrics || [], hl = hidLine(r);
    $id('sc-cur').innerHTML =
      '<div class="ritem" style="cursor:default;margin-top:6px">'
      + '<div class="rh"><span class="rid">지금 걸린 것</span><span class="rst">' + esc(r.time || '') + '</span></div>'
      + '<div class="rdetail">'
      + '<div><b>발동 룰</b></div>'
      + (rules.length ? rules.map(function (x) { return '<div>· ' + esc(x) + '</div>'; }).join('') : '<div>정상 운영</div>')
      + (mets.length ? '<div style="margin-top:4px"><b>실제지표</b></div>' + mets.map(function (m) {
        return '<div class="sc-mono" title="' + esc(m.label || '') + '">' + esc(m.raw) + '</div>';
      }).join('') : '')
      + (hl ? '<div style="margin-top:4px">' + hl + '</div>' : '')
      + '</div></div>';
    renderList();
  }

  function renderList() {
    var box = $id('sc-list');
    if (!box || !SCORE || !SCORE.ok) return;
    var key = SC_VER + '|' + SC_FILTER + '|' + SC_CAP;
    if (key === SC_DRAWN && box.firstChild) return;        // 받은 것 · 필터 · 상한이 그대로면 그대로
    SC_DRAWN = key;
    var rows = (SCORE.rows || []).filter(function (r) {
      if (SC_FILTER === 'warn') return r.level && r.level !== '정상';
      if (SC_FILTER === 'danger') return r.level === '위험' || r.level === '초위험';
      if (SC_FILTER === 'hid') return (r.hid || []).length > 0;
      return true;
    });
    if (!rows.length) { box.innerHTML = '<div class="sc-cap" style="padding:10px 2px">해당하는 줄이 없습니다</div>'; return; }
    // 최신이 위다. '전체' 는 관제 표처럼 300행씩이되 **정상 줄만** 접는다 — 경계 · 위험 · HID·RET 줄은
    //   몇 시에 났든 늘 보인다 (고객: "경계 · 위험 · HID RET 는 전부 다 보여야지 그래도").
    //   접은 자리에는 '⋯ 정상 N행' 을 남겨 시각이 건너뛴 것을 알린다. 필터(경계↑ · 위험↑ · HID·RET)는 접지 않는다.
    var show = [], plain = 0, gap = 0, folded = 0;
    rows.forEach(function (r) {
      var must = SC_FILTER !== 'all' || (r.level && r.level !== '정상') || (r.hid || []).length > 0;
      if (must || plain < SC_CAP) {
        if (gap) { show.push({ gap: gap }); gap = 0; }
        show.push(r);
        if (!must) plain++;
      } else { gap++; folded++; }
    });
    var shown = rows.length - folded;
    box.innerHTML = show.map(function (r) {
      if (r.gap) return '<div class="sc-cap" style="padding:2px 4px">⋯ 정상 ' + r.gap + '행</div>';
      var rules = rulesOf(r), hl = hidLine(r), a = almChip(r.alm);
      return '<div class="ritem" style="border-left-color:' + gradeOf(r.level).c + '" data-at="' + esc(r.at) + '">'
        + '<div class="rh"><span class="rid">' + esc(r.time || '') + '</span>'
        + '<span><b style="font-variant-numeric:tabular-nums">' + Math.round(+r.score || 0) + '</b> ' + lvChip(r.level) + '</span></div>'
        + (rules.length ? '<div class="rv sc-rule" title="' + esc(rules.join('\n')) + '">' + esc(rules.join(' · ')) + '</div>' : '')
        + (a || hl ? '<div class="rv" style="font-weight:normal;color:var(--fg2)">' + a + (a && hl ? ' ' : '') + hl + '</div>' : '')
        + '</div>';
    }).join('') + (folded ? '<div class="rfilter" style="justify-content:center;align-items:center;margin:8px 0 2px">'
      + '<button data-more="1">아래 ' + Math.min(folded, SC_STEP) + '행 더 보기</button>'
      + '<span class="sc-cap" style="margin:0 0 0 6px">' + shown + ' / ' + rows.length + '행 표시 중 · 접은 정상 ' + folded + '행'
      + '</span></div>' : '');
    box.querySelectorAll('.ritem').forEach(function (el) {
      el.ondblclick = function () { openGraph(el.dataset.at); };
    });
    var more = box.querySelector('[data-more]');
    if (more) more.onclick = function () { SC_CAP += SC_STEP; renderList(); };
  }

  // 오늘 하루 추이 — 선 하나 · 등급 띠 · 마우스를 올리면 그 분 (더블클릭 → 그래프)
  // ★예전엔 최근 60분만 그려 그 앞의 경계가 안 보였다 (고객 2026-10-07: "오늘 하루 동안 벌어진 것 보여줘야지")
  function renderSpark(rows, cuts) {
    var box = $id('sc-spark');
    var pts = rows.slice().reverse();
    if (pts.length < 2) { box.innerHTML = ''; return; }
    var W = Math.max(200, box.clientWidth || 244), H = 70, P = 4;
    var X = function (i) { return P + i * (W - 2 * P) / (pts.length - 1); };
    var Y = function (v) { return H - P - Math.max(0, Math.min(100, +v || 0)) / 100 * (H - 2 * P); };
    var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" '
      + 'aria-label="오늘 스코어 추이" style="display:block;cursor:pointer">';
    if (cuts && cuts.warn != null) {
      var band = function (lo, hi, col, op) {
        return '<rect x="0" y="' + Y(hi) + '" width="' + W + '" height="' + Math.max(0, Y(lo) - Y(hi))
          + '" fill="' + col + '" fill-opacity="' + op + '"/>';
      };
      s += band(cuts.warn, cuts.danger, '#f59e0b', 0.12) + band(cuts.danger, cuts.critical, '#ef4444', 0.10)
        + band(cuts.critical, 100, '#ef4444', 0.18);
      [cuts.warn, cuts.danger, cuts.critical].forEach(function (c) {
        s += '<line x1="0" x2="' + W + '" y1="' + Y(c) + '" y2="' + Y(c) + '" stroke="var(--line2)" stroke-dasharray="3 3"/>';
      });
    }
    s += '<path d="' + pts.map(function (r, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(r.score).toFixed(1); }).join(' ')
      + '" fill="none" stroke="var(--accent-line)" stroke-width="2" stroke-linejoin="round"/>';
    var last = pts[pts.length - 1];
    s += '<circle cx="' + X(pts.length - 1) + '" cy="' + Y(last.score) + '" r="3.5" fill="' + gradeOf(last.level).c
      + '" stroke="var(--panel)" stroke-width="1.5"/>';
    s += '<line id="sc-x" x1="0" x2="0" y1="0" y2="' + H + '" stroke="var(--fg2)" stroke-width="1" style="display:none"/>';
    s += '</svg><div class="sc-tip" id="sc-tip"></div>';
    box.innerHTML = s + '<div class="sc-cap">' + esc(pts[0].time || '') + '~' + esc(last.time || '') + ' (' + pts.length + '분)'
      + (cuts && cuts.warn != null
      ? ' · 경계 ' + cuts.warn + ' · 위험 ' + cuts.danger + ' · 초위험 ' + cuts.critical : '') + ' · 더블클릭 → 그래프</div>';
    var svg = box.querySelector('svg'), tip = $id('sc-tip'), xl = $id('sc-x');
    var pick = -1;
    svg.onmousemove = function (e) {
      var rc = svg.getBoundingClientRect();
      var i = Math.round((e.clientX - rc.left - P) / ((W - 2 * P) / (pts.length - 1)));
      i = Math.max(0, Math.min(pts.length - 1, i));
      pick = i;
      var r = pts[i];
      xl.setAttribute('x1', X(i)); xl.setAttribute('x2', X(i)); xl.style.display = '';
      tip.innerHTML = esc(r.time || '') + ' · <b>' + Math.round(+r.score || 0) + '</b> · ' + esc(r.level || '');
      tip.style.display = 'block';
      tip.style.left = Math.min(W - tip.offsetWidth - 2, Math.max(0, X(i) - tip.offsetWidth / 2)) + 'px';
    };
    svg.onmouseleave = function () { tip.style.display = 'none'; xl.style.display = 'none'; pick = -1; };
    svg.ondblclick = function () { var r = pts[pick >= 0 ? pick : pts.length - 1]; if (r) openGraph(r.at); };
  }

  /* ════════════ 5) 더블클릭 → 구간 그래프 (관제가 그린 그림 + 기여도) ════════════ */
  var modal = document.createElement('div');
  modal.id = 'live-gmodal';
  modal.style.cssText = 'display:none;position:fixed;inset:0;z-index:9999;justify-content:center;align-items:center;background:var(--overlay)';
  modal.innerHTML =
    '<div class="ms-card" style="width:1180px">'
    + '<div class="ms-head"><h3 id="lg-title">구간 그래프</h3>'
    + '<span style="display:flex;gap:8px;align-items:center">'
    + '<select id="lg-min"><option value="30">30분</option><option value="60" selected>1시간</option>'
    + '<option value="120">2시간</option><option value="360">6시간</option></select>'
    + '<button class="ms-x" id="lg-x">✕ 닫기</button></span></div>'
    + '<div id="lg-line" class="lg-line"></div>'
    + '<div id="lg-body"><div class="empty">그리는 중…</div></div>'
    + '<div id="lg-pin"></div>'
    + '</div>';
  document.body.appendChild(modal);
  var GAT = null;
  function closeGraph() { modal.style.display = 'none'; GAT = null; }
  $id('lg-x').onclick = closeGraph;
  modal.onclick = function (e) { if (e.target === modal) closeGraph(); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.style.display !== 'none') closeGraph(); });
  $id('lg-min').onchange = function () { if (GONE) drawOne(GONE); else drawGraph(); };

  function rowAt(at) { return ((SCORE && SCORE.rows) || []).find(function (r) { return r.at === at; }); }

  function openGraph(at) {
    if (!at) return;
    GAT = at;
    var r = rowAt(at), sys = (SCORE && SCORE.sys) || '';
    $id('lg-title').textContent = (r ? (r.datetime || at).slice(0, 16) : at.replace('T', ' ').slice(0, 16))
      + ' · ' + sys + (r ? ' · ' + Math.round(+r.score || 0) + '점 ' + (r.level || '') : '');
    var line = [];
    if (r) {
      line.push(lvChip(r.level));
      if (almChip(r.alm)) line.push(almChip(r.alm));
      var hl = hidLine(r);
      if (hl) line.push('<span>' + hl + '</span>');
      if (r.hi_fab) line.push('<span>HI_FAB <b style="color:var(--fg)">' + esc(r.hi_fab) + '</b></span>');
    }
    $id('lg-line').innerHTML = line.join('');
    $id('lg-pin').innerHTML = '';
    modal.style.display = 'flex';
    drawGraph();
  }

  var GONE = null;   // 그래프 안에서 크게 본 칸 이름 — null 이면 전체 (drawOne)
  function graphTheme() {
    var bt = document.body.dataset.theme;
    return bt === 'hmi' ? 'light' : (bt === 'navy' || bt === 'contrast') ? bt : 'dark';
  }
  function drawGraph() {
    if (!GAT) return;
    GONE = null;
    var at = GAT, m = $id('lg-min').value;
    // 관제 그래프도 배경이 넷이다 (관제 graphs.THEMES: dark·light·navy·contrast) —
    // 화이트(hmi)만 이름이 달라 light 로 바꿔 보낸다. 예전엔 네이비·고대비도 dark 로
    // 보내서, 남색 화면 한가운데 다른 검정 그래프가 박혔다.
    var bt = document.body.dataset.theme;
    var theme = bt === 'hmi' ? 'light' : (bt === 'navy' || bt === 'contrast') ? bt : 'dark';
    $id('lg-body').innerHTML = '<div class="empty">그리는 중…</div>';
    // ★기여도 추정은 뺐다 (2026-10-07 고객: "기여도 추정 삭제해라 필요없어") — 그래프만
    fetch('/api/score/graph?at=' + encodeURIComponent(at) + '&minutes=' + m + '&theme=' + theme,
      { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.text() : Promise.reject(r.status); })
      .then(function (svg) {
      if (GAT !== at) return;
      $id('lg-body').innerHTML = svg.indexOf('<svg') >= 0 ? svg : '<div class="empty">그 구간에 관제 자료가 없습니다</div>';
      bindPin();
      bindCellZoom();
      pinAt(at);              // 더블클릭한 그 분의 원인부터
    }).catch(function (e) {
      $id('lg-body').innerHTML = '<div class="empty">그래프를 못 받았습니다 — 관제가 켜져 있는지 보세요 (' + esc(e) + ')</div>';
    });
  }

  // ── 칸 하나 크게 — 관제 화면과 같다 (고객 2026-10-07: "그래프 더블클릭하면 1개 크게") ──
  function bindCellZoom() {
    var svg = document.querySelector('#lg-body svg');
    if (!svg) return;
    svg.addEventListener('dblclick', function (e) {
      var hit = Array.prototype.find.call(svg.querySelectorAll('rect[data-m]'), function (r) {
        var b = r.getBoundingClientRect();
        return e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
      });
      if (hit) drawOne(hit.getAttribute('data-m'));
    });
  }
  function drawOne(name) {
    if (!GAT || !name) return;
    GONE = name;
    var at = GAT, m = $id('lg-min').value;
    $id('lg-body').innerHTML = '<div class="empty">그리는 중…</div>';
    fetch('/api/score/graph1?at=' + encodeURIComponent(at) + '&minutes=' + m + '&theme=' + graphTheme()
          + '&name=' + encodeURIComponent(name), { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.text() : Promise.reject(r.status); })
      .then(function (svg) {
        if (GAT !== at || GONE !== name) return;
        $id('lg-body').innerHTML = '<div style="margin-bottom:8px"><button class="ms-x" id="lg-back">← 전체 그래프</button>'
          + ' <span class="note">그림을 다시 더블클릭해도 돌아갑니다</span></div>'
          + (svg.indexOf('<svg') >= 0 ? svg : '<div class="empty">그 칸을 못 그렸습니다</div>');
        $id('lg-back').onclick = function () { drawGraph(); };
        var big = document.querySelector('#lg-body svg');
        if (big) big.addEventListener('dblclick', function () { drawGraph(); });
        bindPin();
        pinAt(at);
      }).catch(function (e) {
        $id('lg-body').innerHTML = '<div class="empty">그래프를 못 받았습니다 — 관제가 켜져 있는지 보세요 (' + esc(e) + ')</div>';
      });
  }

  // 그래프를 누르면 그 분을 아래에 고정 (관제와 같은 동작)
  function bindPin() {
    document.querySelectorAll('#lg-body svg .ghit').forEach(function (el) {
      el.onclick = function () { pinAt(el.dataset.at); };
    });
  }
  // 그 분 고정 — **원인**(룰마다 값 · 기준, 관제 /api/cause) · 실제지표 · HID · 발동 룰(맨 아래)
  // ★고객(2026-10-07): "원인 내용 좀 적어 주라 — 룰이잖아 · 그래프 클릭하면 원인 내용"
  // ★고객(2026-10-07): "발동 룰을 제일 아래로 · 원인 쪽 글자 조금 더 크게 굵게 · 강조 임팩트 부분은 빨간색 굵게"
  //   — 관제 고정 칸과 같은 순서 · 같은 강조. 빨갛게 할 값은 관제가 parts 로 끊어 준다 (sentinel.rule_causes).
  // 관제가 [보통, 빨강, 보통, …] 으로 끊어 준다 (parts). 없는 옛 관제면 글자 그대로.
  function causeHtml(c) {
    if (!Array.isArray(c.parts)) return esc(c.text);
    return c.parts.map(function (p, i) {
      return i % 2 ? '<b style="color:var(--crit);font-weight:800">' + esc(p) + '</b>' : esc(p);
    }).join('');
  }
  function pinAt(at) {
    var box = $id('lg-pin');
    if (!box || !at) return;
    var r = rowAt(at);
    if (!r) { box.innerHTML = '<div class="note" style="margin-top:8px">' + esc((at || '').replace('T', ' ').slice(0, 16)) + ' — 오늘 목록 밖입니다</div>'; return; }
    var rules = rulesOf(r), mets = r.metrics || [], hl = hidLine(r);
    box.innerHTML = '<div class="ms-sec" style="margin-top:12px">'
      + '<h4>' + esc((r.datetime || '').slice(0, 16)) + ' · ' + Math.round(+r.score || 0) + '점 ' + lvChip(r.level) + ' ' + almChip(r.alm) + '</h4>'
      + '<div id="lg-cause" style="font-size:14px;font-weight:700;line-height:1.5;color:var(--fg)">원인 — 불러오는 중…</div>'
      + (mets.length ? '<div class="note mono" style="margin-top:6px">' + mets.map(function (x) { return esc(x.raw); }).join(' · ') + '</div>' : '')
      + (hl ? '<div class="note" style="margin-top:4px">' + hl + '</div>' : '')
      + '<div class="note" style="margin-top:4px">발동 룰 — ' + (rules.length ? esc(rules.join(' · ')) : '정상 운영') + '</div>'
      + '</div>';
    box.dataset.at = at;
    fetch('/api/score/cause?at=' + encodeURIComponent(at), { cache: 'no-store', credentials: 'same-origin' })
      .then(function (q) { return q.ok ? q.json() : Promise.reject(q.status); })
      .then(function (d) {
        var el = $id('lg-cause');
        if (!el || box.dataset.at !== at) return;          // 그새 다른 분을 눌렀다
        var cs = (d && d.causes) || [];
        el.innerHTML = cs.length
          ? cs.map(function (c) { return '<div style="margin:3px 0">원인 · ' + esc(c.rule) + ' — ' + causeHtml(c) + '</div>'; }).join('')
          : '원인 — 없음';
      }).catch(function () { var el = $id('lg-cause'); if (el) el.textContent = '원인 — 관제에서 못 받았습니다'; });
  }

  /* ════════════ 6) 밖에서 부르는 것 · 처음 모드 ════════════ */
  window.setAppMode = setAppMode;          // 맨 위 [리플레이 | 실시간] (onclick)
  window.liveCmd = liveCmd;                // [▶ 실시간 PLAY] [⏸ 일시정지] [■ 정지] (onclick)
  window.LiveMode = { setAppMode: setAppMode, liveCmd: liveCmd, wsOpen: wsOpen, renderScore: renderScore,
                      app: function () { return APP; }, mode: function () { return MODE; } };

  // 처음 모드 — ?auto=1(관제에서 넘어온 구간 조회)은 늘 리플레이 · ?mode= · 이 브라우저가 마지막에 고른 것
  var q = new URLSearchParams(location.search);
  var want = (q.get('mode') || '').toLowerCase();
  var start = q.get('auto') === '1' ? 'replay'
    : (want === 'live' || want === 'replay') ? want
    : (load(APP_KEY) === 'live' ? 'live' : 'replay');
  document.body.dataset.app = 'replay';
  if (start === 'live') setAppMode('live');
  // ?mode=live&fab=M16A&prefix=BR — 부팅(지도 목록)이 끝난 뒤에 그 지도로
  var qf = (q.get('fab') || '').trim(), qp = (q.get('prefix') || '').trim();
  if (start === 'live' && qf && qp) {
    Promise.resolve(window.BOOT).then(function () {
      if (qf !== currentFab || qp !== currentPrefix) return window.applyFab(qf, qp);
    }).catch(function (e) { console.warn('실시간 지도 전환 실패:', e); });
  }
})();
