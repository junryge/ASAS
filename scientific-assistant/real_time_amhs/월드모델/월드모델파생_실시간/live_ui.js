/* 월드모델파생_실시간 — 같은 화면을 '실시간' 으로 쓰게 하는 조각.
   서버가 월드모델파생 dashboard.html 의 </body> 바로 앞에 끼운다 (화면 파일은 그대로다).
   · 재생 · 정지 · 속도 · 프레임 막대 · 로그프레소 구간 조회 칸을 숨긴다 — 실시간에는 없다.
   · 그 자리에 상태줄: [● 실시간] 테이블 · 화면 시각(지연) · 받은 데이터 · 몇 초마다 · 오류.
   · 새 색 · 새 모양을 만들지 않는다 — 화면에 있던 badge · tb-group · 글자색 변수를 쓴다. */
(function () {
  document.title = 'OHT 월드모델 — 실시간';
  try { statusMap.playing = '실시간'; } catch (e) { /* 옛 화면 */ }

  function hide(el) { if (el) el.style.display = 'none'; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // 1) 구간 조회 칸 · 재생 단추 · 속도 · 프레임 막대
  var query = document.querySelector('#topbar .tb-query');
  document.querySelectorAll('#topbar button[onclick^="sendCmd("], #topbar .speed-btn').forEach(function (b) {
    hide(b.closest('.tb-group') || b);
  });
  hide(document.getElementById('slider-container'));
  hide(document.getElementById('frame-display'));

  // 2) 상태줄 — 조회 칸이 있던 자리에
  var chip = document.createElement('div');
  chip.className = 'tb-group';
  chip.id = 'live-chip';
  chip.innerHTML = '<span class="badge badge-playing" id="live-dot">● 실시간</span>'
    + '<span id="live-text" style="font-size:12px;color:var(--fg2)">연결 중…</span>';
  if (query && query.parentNode) {
    query.parentNode.insertBefore(chip, query);
    hide(query);
  } else {
    var tb = document.querySelector('#topbar .tb-row');
    if (tb) tb.insertBefore(chip, tb.firstChild.nextSibling);
  }

  function hms(s) { return s ? String(s).slice(11, 19) : '--:--:--'; }

  function paint(L) {
    var t = document.getElementById('live-text');
    var dot = document.getElementById('live-dot');
    if (!t || !dot) return;
    if (!L) { t.textContent = '실시간 서버 응답을 기다리는 중…'; return; }
    var p = ['<b style="color:var(--fg)">' + esc(L.table) + '</b>'];
    if (L.shown_time) {
      p.push('화면 <b style="color:var(--time)">' + hms(L.shown_time) + '</b>'
        + (L.lag_sec != null ? ' (지금보다 ' + L.lag_sec + '초 늦음)' : ''));
    } else if (!L.polls) {
      p.push('처음 받는 중… (최근 ' + Math.round((L.warm_sec || 300) / 60) + '분)');
    } else {
      p.push('아직 받은 줄이 없습니다');
    }
    p.push('차 ' + (L.vehicles || 0) + '대');
    p.push((L.poll_sec || 5) + '초마다 조회' + (L.last_poll ? ' · 마지막 ' + esc(L.last_poll) : ''));
    if (L.error) p.push('<b style="color:#dc2626">조회 실패 ' + esc(L.fails || '') + '번 — ' + esc(L.error) + '</b>');
    t.innerHTML = p.join(' · ');
    // 늦거나 실패하면 빨간 배지 — 기준: 받은 데이터가 2분 넘게 묵음
    var stale = L.data_lag_sec != null && L.data_lag_sec > 120;
    var bad = !!L.error || stale;
    dot.className = 'badge ' + (bad ? 'badge-stopped' : 'badge-playing');
    dot.textContent = bad ? (L.error ? '● 실시간 (조회 실패)' : '● 실시간 (데이터 늦음)') : '● 실시간';
    dot.title = '로그프레소 ' + (L.server || '') + ' · 키 ' + (L.key || '')
      + ' · 받은 데이터 ' + hms(L.data_time)
      + (L.data_lag_sec != null ? ' (지금보다 ' + L.data_lag_sec + '초 전)' : '')
      + ' · 화면은 ' + (L.buffer_sec || 0) + '초 늦춰 2초 칸을 차례로 보입니다 (부드럽게)'
      + ' · 미보고 기준 ' + (L.miss_sec || 50) + '초';
  }

  // 3) 스냅샷마다 상태줄 — updateUI 를 감싼다 (화면 함수는 그대로 부른다)
  var orig = window.updateUI;
  if (typeof orig === 'function') {
    window.updateUI = function (d) {
      orig(d);
      try { paint(d && d.live); } catch (e) { /* 상태줄 실패로 화면을 멈추지 않는다 */ }
    };
  }
  // 서버가 아예 응답이 없을 때도 알린다
  setInterval(function () {
    if (window.__liveErr && (!window.__liveOk || Date.now() - window.__liveOk > 5000)) {
      var t = document.getElementById('live-text'), dot = document.getElementById('live-dot');
      if (t) t.innerHTML = '<b style="color:#dc2626">실시간 서버에 닿지 않습니다 — ' + esc(window.__liveErr) + '</b>';
      if (dot) { dot.className = 'badge badge-stopped'; dot.textContent = '● 연결 끊김'; }
    }
  }, 2000);
})();
