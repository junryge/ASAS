/* 월드모델파생_실시간 — 같은 화면을 'FAB별 OHT 실시간' 으로 쓰게 하는 조각.
   서버가 월드모델파생 dashboard.html 의 </body> 바로 앞에 끼운다 (화면 파일은 그대로다).

   위 도구줄
     · [▶ 실시간 PLAY] [⏸ 일시정지] [■ 정지] — 재생판 단추 자리·모양 그대로, 하는 일만 바꾼다.
         PLAY  로그프레소를 묻기 시작 (보는 FAB 하나만) · 시계가 흐른다
         일시정지  화면만 그 자리에 세운다 (조회는 계속 — 다시 PLAY 하면 지금으로)
         정지  조회를 멈춘다 (저절로 멈추지 않는다 — 고객 2026-10-06)
     · 속도 · 프레임 막대 · 구간 조회 칸은 숨긴다 — 실시간에는 없다.
     · 상태줄: [● 실시간] 테이블 · 화면 시각(지연) · 차 · 조회 · 관제 스코어 칩.
   오른쪽 '스코어' 탭 (관제가 매긴 그 FAB 의 점수 — 여기서 다시 계산하지 않는다)
     · 지금 점수 · 등급 · 알람 · HI_FAB → 최근 60분 추이 → 지금 걸린 것(발동 룰 · 실제지표 ·
       HID_JAM · RET) → 최근 목록. 줄을 더블클릭하면 관제와 같은 구간 그래프 + 기여도.
   ★색은 화면에 있던 것만 쓴다 — 등급은 risk-NORMAL/WARNING/DANGER/CRITICAL 칩, 줄 왼쪽 띠는
     차량 목록과 같은 초록·주황·빨강. 색만으로 말하지 않는다 — 늘 글자(정상·경계·위험·초위험)와 같이. */
(function () {
  'use strict';
  document.title = 'OHT 월드모델 — 실시간';
  try { statusMap.playing = '실시간'; } catch (e) { /* 옛 화면 */ }

  var $id = function (id) { return document.getElementById(id); };
  function hide(el) { if (el) el.style.display = 'none'; }
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

  /* ════════════ 1) 위 도구줄 — PLAY · 일시정지 · 정지 ════════════ */
  var query = document.querySelector('#topbar .tb-query');
  document.querySelectorAll('#topbar .speed-btn').forEach(function (b) { hide(b.closest('.tb-group') || b); });
  hide($id('slider-container'));
  hide($id('frame-display'));
  var btnPlay = document.querySelector('#topbar button[onclick="sendCmd(\'play\')"]');
  var btnPause = document.querySelector('#topbar button[onclick="sendCmd(\'pause\')"]');
  var btnStop = document.querySelector('#topbar button[onclick="sendCmd(\'stop\')"]');
  if (btnPlay) {
    btnPlay.innerHTML = '&#9654; 실시간 PLAY';
    btnPlay.title = '로그프레소를 묻기 시작 — 지금 보는 FAB 하나만 · 시계가 흐른다';
    btnPlay.onclick = function () { setMode('play'); };
  }
  if (btnPause) {
    btnPause.title = '화면만 이 자리에 세운다 (조회는 계속) — 다시 PLAY 하면 지금으로';
    btnPause.onclick = function () { setMode('pause'); };
  }
  if (btnStop) {
    btnStop.title = '로그프레소 조회를 멈춘다 — 다시 PLAY 하면 이어서 묻는다';
    btnStop.onclick = function () { setMode('stop'); };
  }

  // 큰 시계 앞에 'OHT' — 이 시계는 OHT 시각(로그프레소 데이터)이다. 스코어 시각(관제)은 칩에 따로
  var tdisp = $id('time-display');
  if (tdisp && tdisp.parentNode) {
    var cap = document.createElement('span');
    cap.className = 'tb-cap';
    cap.textContent = 'OHT';
    cap.title = 'OHT 시각 — 로그프레소에서 받은 OHT 데이터의 시각 (화면은 몇 초 늦춰 부드럽게 보입니다)';
    tdisp.parentNode.insertBefore(cap, tdisp);
    tdisp.title = cap.title;
  }

  // 상태줄 — 구간 조회 칸 자리에
  var chip = document.createElement('div');
  chip.className = 'tb-group';
  chip.id = 'live-chip';
  chip.innerHTML = '<span class="badge badge-stopped" id="live-dot">■ 정지</span>'
    + '<span id="live-text" style="font-size:12px;color:var(--fg2)">연결 중…</span>'
    + '<span id="live-score" class="risk risk-NORMAL" style="display:none;cursor:pointer"'
    + ' title="관제가 매긴 이 FAB 의 스코어 (1분마다) — 누르면 오른쪽 스코어 탭"></span>';
  if (query && query.parentNode) {
    query.parentNode.insertBefore(chip, query);
    hide(query);
  } else {
    var tbr = document.querySelector('#topbar .tb-row');
    if (tbr) tbr.insertBefore(chip, tbr.firstChild.nextSibling);
  }

  var MODE = 'stop';          // 'play' | 'pause' | 'stop'
  var INIT = true;            // 첫 스냅샷 — 서버 피드가 이미 PLAY 중이면 따라간다
  var LAST = null, LAST_AT = 0, LIVE = null;
  var SHOW = 0;               // 화면 시계(ms) — ★절대 뒤로 안 간다 (고객: "늘었다 다시 과거로 가면 안 돼")

  function badge() {
    var b = $id('status-badge');
    if (!b) return;
    if (MODE === 'play') { b.textContent = '실시간'; b.className = 'badge badge-playing'; }
    else if (MODE === 'pause') { b.textContent = '일시정지'; b.className = 'badge badge-paused'; }
    else { b.textContent = '정지'; b.className = 'badge badge-stopped'; }
  }
  function setMode(m) {
    MODE = m;
    badge();
    if (m === 'play' || m === 'stop') {
      post('/api/live/cmd', { action: m }).then(function (L) { LIVE = L; paint(L); })
        .catch(function (e) { window.__liveErr = String((e && e.message) || e); });
    }
    paint(LIVE);
  }

  function paint(L) {
    var t = $id('live-text'), dot = $id('live-dot');
    if (!t || !dot) return;
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

  // 스냅샷마다 — PLAY 일 때만 화면에 얹는다 (일시정지 · 정지는 그 자리)
  var origUpdate = window.updateUI;
  if (typeof origUpdate === 'function') {
    window.updateUI = function (d) {
      var L = d && d.live;
      if (L) LIVE = L;
      if (INIT && L) {
        INIT = false;
        if (L.playing) setMode('play');        // 다른 화면이 PLAY 중이면 같이 본다
      }
      if (MODE === 'play' && d && d.time) {
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
  }
  // PLAY 중에는 시계가 초 단위로 흐른다 — 2초 칸 사이를 벽시계로 메운다 (칸 하나 넘게는 안 간다).
  // ★절대 뒤로 안 간다. 다음 장면이 시계보다 앞이면(칸 시각은 그 칸의 마지막 보고 시각이라 1초
  //   어긋날 수 있다) 따라올 때까지 그 자리에서 기다린다. 앞으로 크게 뛰는 것은 정지했다 다시
  //   PLAY 해서 '지금' 으로 건너뛸 때뿐이다.
  function tickClock() {
    var el = $id('time-display');
    if (!el || MODE !== 'play' || !LAST || !LAST.time) return;
    var b = Date.parse(LAST.time.replace(' ', 'T'));
    if (isNaN(b)) return;
    var t = b + Math.min(Date.now() - LAST_AT, 2000);
    if (t < SHOW) t = SHOW;
    SHOW = t;
    var d = new Date(t);
    el.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  setInterval(tickClock, 250);
  // 서버가 아예 응답이 없을 때
  setInterval(function () {
    if (window.__liveErr && (!window.__liveOk || Date.now() - window.__liveOk > 5000)) {
      var t = $id('live-text'), dot = $id('live-dot');
      if (t) t.innerHTML = '<b style="color:#dc2626">실시간 서버에 닿지 않습니다 — ' + esc(window.__liveErr) + '</b>';
      if (dot) { dot.className = 'badge badge-stopped'; dot.textContent = '● 연결 끊김'; }
    }
  }, 2000);

  /* ════════════ 2) 관제 스코어 — 오른쪽 '스코어' 탭 ════════════ */
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

  // 탭 단추 · 화면
  var tabs = document.querySelector('#rsidebar .rtabs');
  var pane = document.createElement('div');
  pane.id = 'rtab-score';
  pane.style.display = 'none';
  pane.innerHTML =
    '<div id="sc-sum" class="rsum" style="font-size:12px;padding:4px 2px 8px;line-height:1.6">관제 스코어를 불러오는 중…</div>'
    + '<div id="sc-now"></div>'
    + '<div id="sc-spark" style="position:relative;margin:6px 0 2px"></div>'
    + '<div id="sc-cur"></div>'
    + '<div class="rfilter" id="sc-filter" style="margin-top:8px">'
    + '<button class="active" data-f="all">전체</button><button data-f="warn">경계↑</button>'
    + '<button data-f="danger">위험↑</button><button data-f="hid">HID·RET</button></div>'
    + '<div id="sc-list" class="rlist"></div>'
    + '<div class="sc-cap" style="margin:6px 2px">줄을 더블클릭하면 그 시각 구간 그래프 (관제와 같은 그림)</div>';
  if (tabs) {
    var tb = document.createElement('button');
    tb.className = 'rtab';
    tb.textContent = '스코어';
    tb.dataset.rt = 'score';
    tb.onclick = function () { window.switchRTab('score'); };
    tabs.appendChild(tb);
    var rs = $id('rsidebar');
    if (rs) rs.appendChild(pane);
  }
  var origSwitch = window.switchRTab;
  window.switchRTab = function (tab) {
    var sc = $id('rtab-score');
    if (tab === 'score') {
      ['rtab-oht', 'rtab-zone'].forEach(function (id) { var e = $id(id); if (e) e.style.display = 'none'; });
      if (sc) sc.style.display = 'block';
      document.querySelectorAll('#rsidebar .rtab').forEach(function (b) {
        b.classList.toggle('active', b.dataset.rt === 'score');
      });
      renderScore();
      return;
    }
    if (sc) sc.style.display = 'none';
    if (typeof origSwitch === 'function') origSwitch(tab);
  };
  $id('live-score').onclick = function () {
    var rs = $id('rsidebar');
    if (rs && rs.classList.contains('collapsed') && typeof toggleRSidebar === 'function') toggleRSidebar();
    window.switchRTab('score');
  };
  document.querySelectorAll('#sc-filter button').forEach(function (b) {
    b.onclick = function () {
      SC_FILTER = b.dataset.f;
      document.querySelectorAll('#sc-filter button').forEach(function (x) { x.classList.toggle('active', x === b); });
      renderList();
    };
  });

  function scoreLoad() {
    return fetch('/api/score/feed?limit=90', { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) { SCORE = d; })
      .catch(function (e) { SCORE = { ok: false, error: '실시간 서버에 닿지 않습니다 — ' + ((e && e.message) || e) }; })
      .then(function () { paintScoreChip(); renderScore(); });
  }
  setInterval(scoreLoad, 15000);
  scoreLoad();
  // 지도를 바꾸면 그 FAB 스코어로 바로
  if (typeof window.applyFab === 'function') {
    var origApply = window.applyFab;
    window.applyFab = function (f, p) {
      SHOW = 0;               // 다른 FAB 의 시계 — 앞 FAB 시각에 붙어 기다리지 않게 새로
      LAST = null;
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
    if (!sc || sc.style.display === 'none') return;
    var S = SCORE;
    var sum = $id('sc-sum');
    if (!S) { sum.textContent = '관제 스코어를 불러오는 중…'; return; }
    if (!S.ok) {
      sum.innerHTML = '<b style="color:#dc2626">' + esc(S.error || '관제 스코어를 못 받았습니다') + '</b>';
      ['sc-now', 'sc-spark', 'sc-cur', 'sc-list'].forEach(function (id) { $id(id).innerHTML = ''; });
      return;
    }
    var rows = S.rows || [], r = rows[0];
    var ago = r ? minsAgo(r.datetime) : null;
    sum.innerHTML = '관제 <b>' + esc(S.sys) + '</b> 스코어 <b>' + esc(r ? r.time || '' : '') + '</b> · 1분마다'
      + (S.fallback ? ' · <b style="color:#f59e0b">오늘 수집이 없어 ' + esc(S.day) + ' 자료</b>' : '')
      + (ago != null && ago > 5 && !S.fallback ? ' · <b style="color:#f59e0b">마지막 ' + esc((r.datetime || '').slice(11, 16)) + ' (' + ago + '분 전)</b>' : '');
    if (!r) {
      $id('sc-now').innerHTML = '<div class="ritem" style="cursor:default">관제 표에 아직 줄이 없습니다</div>';
      ['sc-spark', 'sc-cur', 'sc-list'].forEach(function (id) { $id(id).innerHTML = ''; });
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
    var rows = (SCORE.rows || []).filter(function (r) {
      if (SC_FILTER === 'warn') return r.level && r.level !== '정상';
      if (SC_FILTER === 'danger') return r.level === '위험' || r.level === '초위험';
      if (SC_FILTER === 'hid') return (r.hid || []).length > 0;
      return true;
    });
    if (!rows.length) { box.innerHTML = '<div class="sc-cap" style="padding:10px 2px">해당하는 줄이 없습니다</div>'; return; }
    box.innerHTML = rows.map(function (r) {
      var rules = rulesOf(r), hl = hidLine(r), a = almChip(r.alm);
      return '<div class="ritem" style="border-left-color:' + gradeOf(r.level).c + '" data-at="' + esc(r.at) + '">'
        + '<div class="rh"><span class="rid">' + esc(r.time || '') + '</span>'
        + '<span><b style="font-variant-numeric:tabular-nums">' + Math.round(+r.score || 0) + '</b> ' + lvChip(r.level) + '</span></div>'
        + (rules.length ? '<div class="rv sc-rule" title="' + esc(rules.join('\n')) + '">' + esc(rules.join(' · ')) + '</div>' : '')
        + (a || hl ? '<div class="rv" style="font-weight:normal;color:var(--fg2)">' + a + (a && hl ? ' ' : '') + hl + '</div>' : '')
        + '</div>';
    }).join('');
    box.querySelectorAll('.ritem').forEach(function (el) {
      el.ondblclick = function () { openGraph(el.dataset.at); };
    });
  }

  // 최근 60분 추이 — 선 하나 · 등급 띠 · 마우스를 올리면 그 분 (더블클릭 → 그래프)
  function renderSpark(rows, cuts) {
    var box = $id('sc-spark');
    var pts = rows.slice(0, 60).reverse();
    if (pts.length < 2) { box.innerHTML = ''; return; }
    var W = Math.max(200, box.clientWidth || 244), H = 70, P = 4;
    var X = function (i) { return P + i * (W - 2 * P) / (pts.length - 1); };
    var Y = function (v) { return H - P - Math.max(0, Math.min(100, +v || 0)) / 100 * (H - 2 * P); };
    var s = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" '
      + 'aria-label="최근 60분 스코어 추이" style="display:block;cursor:pointer">';
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
    box.innerHTML = s + '<div class="sc-cap">최근 ' + pts.length + '분' + (cuts && cuts.warn != null
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

  /* ════════════ 3) 더블클릭 → 구간 그래프 (관제가 그린 그림 + 기여도) ════════════ */
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
    + '<div id="lg-contrib" style="margin-top:14px;padding-top:12px;border-top:1px solid var(--line)"></div>'
    + '</div>';
  document.body.appendChild(modal);
  var GAT = null;
  function closeGraph() { modal.style.display = 'none'; GAT = null; }
  $id('lg-x').onclick = closeGraph;
  modal.onclick = function (e) { if (e.target === modal) closeGraph(); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.style.display !== 'none') closeGraph(); });
  $id('lg-min').onchange = function () { drawGraph(); };

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

  function drawGraph() {
    if (!GAT) return;
    var at = GAT, m = $id('lg-min').value;
    var theme = document.body.dataset.theme === 'hmi' ? 'light' : 'dark';
    $id('lg-body').innerHTML = '<div class="empty">그리는 중…</div>';
    $id('lg-contrib').innerHTML = '';
    Promise.all([
      fetch('/api/score/graph?at=' + encodeURIComponent(at) + '&minutes=' + m + '&theme=' + theme,
        { cache: 'no-store', credentials: 'same-origin' }).then(function (r) { return r.ok ? r.text() : Promise.reject(r.status); }),
      fetch('/api/score/contrib?at=' + encodeURIComponent(at), { cache: 'no-store', credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.text() : ''; }).catch(function () { return ''; })
    ]).then(function (res) {
      if (GAT !== at) return;
      $id('lg-body').innerHTML = res[0].indexOf('<svg') >= 0 ? res[0] : '<div class="empty">그 구간에 관제 자료가 없습니다</div>';
      $id('lg-contrib').innerHTML = res[1] || '';
      $id('lg-contrib').style.display = res[1] ? '' : 'none';
      bindPin();
    }).catch(function (e) {
      $id('lg-body').innerHTML = '<div class="empty">그래프를 못 받았습니다 — 관제가 켜져 있는지 보세요 (' + esc(e) + ')</div>';
    });
  }

  // 그래프를 누르면 그 분을 아래에 고정 (관제와 같은 동작)
  function bindPin() {
    var box = $id('lg-pin');
    document.querySelectorAll('#lg-body svg .ghit').forEach(function (el) {
      el.onclick = function () {
        var r = rowAt(el.dataset.at);
        if (!r) { box.innerHTML = '<div class="note" style="margin-top:8px">' + esc((el.dataset.at || '').replace('T', ' ').slice(0, 16)) + ' — 최근 90분 목록 밖입니다</div>'; return; }
        var rules = rulesOf(r), mets = r.metrics || [], hl = hidLine(r);
        box.innerHTML = '<div class="ms-sec" style="margin-top:12px">'
          + '<h4>' + esc((r.datetime || '').slice(0, 16)) + ' · ' + Math.round(+r.score || 0) + '점 ' + lvChip(r.level) + ' ' + almChip(r.alm) + '</h4>'
          + '<div class="note">발동 룰 — ' + (rules.length ? esc(rules.join(' · ')) : '정상 운영') + '</div>'
          + (mets.length ? '<div class="note mono" style="margin-top:4px">' + mets.map(function (x) { return esc(x.raw); }).join(' · ') + '</div>' : '')
          + (hl ? '<div class="note" style="margin-top:4px">' + hl + '</div>' : '')
          + '</div>';
      };
    });
  }
})();
