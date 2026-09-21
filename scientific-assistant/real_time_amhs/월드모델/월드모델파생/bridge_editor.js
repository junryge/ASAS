/* bridge_editor.js — OHT_Bridge_Monitor.html 의 '✎ 수정' 모드.
 *
 * MAP_아이소_얹기.py 가 이 파일을 모니터 HTML 의 <head> 에 그대로 넣는다.
 * 2026-09-21. 고객: "수정하기 버튼 만들어줘 — 거기서 패널, 맵 수정 가능하게,
 *                  맵 추가도 가능하게. 그러면 MAP 에서 전부 다 해결 가능하잖아".
 *
 * 무엇을 하나
 *   · 설정(JSON, <script id="bm-config">)대로 화면을 꾸민다 — 판마다 맵(레일·설비·행거),
 *     카드(패널) 이름·색·보이기·위치, 구역(오른쪽 열·범례·KPI) 보이기, 제목 글자.
 *   · '✎ 수정' 을 누르면 편집 창이 열린다. 고친 것은 바로 화면에 선다.
 *   · '저장' 은 **설정 JSON 한 장**만 쓴다 (고객: "HTML 을 그대로 저장하냐 — JSON 만들면
 *     되지, 그걸 저장하고 로드하면 되잖아"). 기본 이름 OHT_Bridge_Monitor_설정.json.
 *     크롬·엣지는 처음 한 번 파일을 고르면 다음부터 그 파일에 바로 덮어쓴다.
 *   · 열 때 — HTML 에 든 기본 설정 · 이 브라우저에 남긴 설정 · 고른 JSON 파일 중
 *     **제일 나중에 저장한 것**으로 뜬다. 다른 PC 에서는 '불러오기' 로 그 JSON 을 고른다.
 *     (MAP_아이소_얹기.py 를 돌리면 옆의 설정 JSON 을 HTML 기본값으로 굳혀 준다)
 *   · 마우스 — 왼쪽 끌기 돌리기 · 휠 줌 (틀 그대로) · **Ctrl + 왼쪽 끌기 = 화면 이동**
 *     (오른쪽 끌기도 그대로 된다) · 수정 창이 열려 있으면 패널 끌기 = 옮기기 (Shift = 높이).
 *   · 바탕화면 색 — '화면' 칸에서 바탕·무대·격자·빛 색을 고른다. 고른 것만 바뀐다.
 *
 * 지키는 것 — 틀(React 번들)과 싸우지 않는다
 *   · 틀이 그린 요소는 **빼지 않는다**. 숨길 때는 display 만, 옮길 때는 CSS 변수
 *     (--bmx/--bmy/--bmz — 틀이 transform 안에 var() 로 받아 둔다)만 만진다.
 *     카드 transform 은 틀이 드래그·줌마다 다시 쓰므로 직접 건드리면 풀린다.
 *   · 색은 속성 하나씩 바꾼다 (cssText 를 통째로 쓰면 그 순간의 transform 이 굳는다).
 *   · 이 파일 안에 '<' + '/script' 를 그대로 쓰지 않는다 (HTML 에 박힌다).
 */
(function () {
  'use strict';

  var LSKEY = 'bm-config:' + location.pathname;   // 이 브라우저에 남기는 자리 (파일마다 따로)
  var JSON_NAME = 'OHT_Bridge_Monitor_설정.json';
  var fileHandle = null;   // 고른 설정 JSON (크롬·엣지 — 다음 저장은 여기에 바로)
  var CFG = null;          // 지금 설정
  var LOADED = null;       // 연 때의 설정 (되돌리기)
  var BUILT = null;        // HTML 에 든 기본 설정
  var dirty = false;
  var ORIG = new Map();    // 요소 → 처음 모습 (되돌릴 수 있게)
  var BLOBS = {};          // 판 → blob URL 들 (다시 그릴 때 치운다)
  var ui = null, tab = 'map';

  var K = 10;              // SVG 좌표 = 판 px × K
  var MARGIN = 3;          // 판 가장자리 여백 (px)
  var EQ_Z = 5, RAIL_Z = 12, HANG_CELL = 140, HANG_MAX = 90, EQ_UNITS = 12;
  var Q = 10;              // 도면 단위 → geo 단위 (10 cm)

  /* 카드 색 — 틀에 있는 네 벌 그대로 */
  var TONES = {
    teal:  { acc: '#3ad6c8', acc2: '#7ae7dd', rgb: '58,214,200',
             bg: 'rgba(20, 32, 44, 0.95), rgba(11, 17, 24, 0.95)', bd: '#2a3c4f', sub: '#8fa3b5', dim: '#5c7183', name: '' },
    blue:  { acc: '#8fd3ff', acc2: '#cfe9ff', rgb: '143,211,255',
             bg: 'rgba(24, 38, 52, 0.96), rgba(12, 19, 26, 0.96)', bd: '#32475c', sub: '#8fa3b5', dim: '#5c7183', name: '' },
    amber: { acc: '#ffce7a', acc2: '#ffe6b8', rgb: '255,206,122',
             bg: 'rgba(38, 32, 22, 0.95), rgba(16, 13, 10, 0.95)', bd: '#4d4130', sub: '#b3a289', dim: '#7d6f57', name: '' },
    red:   { acc: '#ff6b6b', acc2: '#ffb0b0', rgb: '255,107,107',
             bg: 'rgba(44, 24, 26, 0.96), rgba(20, 11, 12, 0.96)', bd: '#5c3034', sub: '#c09a9a', dim: '#8a5f5f', name: '#ffb0b0' }
  };
  var TONE_NAMES = { '': '원래 색', teal: '청록', blue: '파랑', amber: '앰버', red: '빨강' };

  /* 바탕화면 — 틀에 박힌 원래 색 (고른 게 없으면 이 색 그대로 둔다) */
  var BG_DEF = { page: '#121c28', stage: '#0c131b', grid: '#3ad6c8', glow: '#3ad6c8' };
  var BG_NAMES = { page: '바탕 (화면 전체)', stage: '무대 (판이 놓인 칸)', grid: '격자', glow: '은은한 빛' };
  var BG_FG = '#e8eff6';                       // 틀의 글자색
  /* 고객: "배경색상이 어두워서 기존에 다크,화이트,네이비,고대비 적용 가능하게 해주라" */
  var BG_PRESETS = [
    { name: '다크', bg: {} },                       // 틀이 원래 쓰던 색 그대로 (아무것도 안 덮는다)
    { name: '화이트', bg: { page: { col: '#eef2f7', fg: '#16212e' }, stage: { col: '#fbfcfe' },
                          grid: { col: '#54677c', a: .10 }, glow: { col: '#54677c', a: .06 } } },
    { name: '네이비', bg: { page: { col: '#15294a' }, stage: { col: '#0f1e39' },
                          grid: { col: '#7aa6ff' }, glow: { col: '#7aa6ff' } } },
    { name: '고대비', bg: { page: { col: '#000000', flat: true, fg: '#ffffff' }, stage: { col: '#000000', flat: true },
                          grid: { col: '#ffffff', a: .16 }, glow: { hide: true } } }
  ];

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // ─────────────────────────────────────────────────────────────── 시작
  document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('bm-config');
    try { CFG = JSON.parse(el ? el.textContent : '{}'); } catch (e) { CFG = {}; }
    norm(CFG);
    BUILT = clone(CFG);                                 // HTML 에 든 기본값
    var ls = lsGet();                                   // 이 브라우저에 남긴 것 — 더 나중 것이면 그걸로
    if (ls && stamp(ls) > stamp(CFG)) { norm(ls); CFG = ls; }
    LOADED = clone(CFG);
    var n = 0, t = setInterval(function () {
      if (++n > 600) { clearInterval(t); return; }
      if ($('[data-bm-plate]') && $('[data-bm-area="toolbar"]')) { clearInterval(t); setTimeout(boot, 50); }
    }, 100);
  });

  function norm(c) {
    c.version = c.version || 1;
    c.texts = c.texts || {}; c.areas = c.areas || {}; c.cards = c.cards || {};
    c.maps = c.maps || {}; c.plates = c.plates || []; c.bg = c.bg || {};
  }

  function boot() {
    injectStyle();
    snapshot();
    applyAll();
    addButton();
    initPan();
    // 전에 고른 설정 JSON 이 있고 읽기 허락이 살아 있으면 — 파일에서 새로 읽는다
    idbGet().then(function (h) {
      if (!h) return;
      fileHandle = h;
      return h.queryPermission({ mode: 'read' }).then(function (st) {
        if (st !== 'granted') return;
        return h.getFile().then(function (f) { return f.text(); }).then(function (txt) {
          var c = JSON.parse(txt);
          if (c && c.plates && stamp(c) > stamp(CFG)) { norm(c); CFG = c; LOADED = clone(c); lsSet(c); applyAll(); draw(); }
        });
      });
    }).catch(function () {});
    window.addEventListener('beforeunload', function (e) {
      if (dirty) { e.preventDefault(); e.returnValue = ''; }
    });
    window.__bm = { cfg: function () { return CFG; }, apply: applyAll, open: openUI, geoFromCache: geoFromCache };
  }

  // 틀이 그린 모습을 떠 둔다 — 되돌릴 때 이것으로
  function snapshot() {
    $$('[data-bm-card]').forEach(function (card) {
      if (ORIG.has(card)) return;
      var props = [];
      [card].concat($$('*', card)).forEach(function (e) {
        for (var i = 0; i < e.style.length; i++) {
          var p = e.style[i];
          if (/^transform|^--/.test(p)) continue;
          props.push([e, p, e.style.getPropertyValue(p)]);
        }
      });
      var ne = $('[data-bm-name]', card);
      ORIG.set(card, { name: ne ? ne.textContent : '', nameColor: ne ? ne.style.color : '', props: props,
                       display: card.style.display, tone: toneOf(card) });
    });
    $$('[data-bm-area]').forEach(function (a) { if (!ORIG.has(a)) ORIG.set(a, { display: a.style.display }); });
    $$('[data-bm-text]').forEach(function (a) { if (!ORIG.has(a)) ORIG.set(a, { text: a.textContent }); });
  }

  function toneOf(card) {
    var s = card.getAttribute('style') || '';
    for (var k in TONES) if (s.indexOf(TONES[k].acc) >= 0 || s.indexOf(hexRgb(TONES[k].acc)) >= 0) return k;
    return 'teal';
  }
  function hexRgb(h) { h = h.replace('#', ''); return 'rgb(' + parseInt(h.substr(0, 2), 16) + ', ' + parseInt(h.substr(2, 2), 16) + ', ' + parseInt(h.substr(4, 2), 16) + ')'; }

  // ─────────────────────────────────────────────────────────────── 적용
  function applyAll() {
    snapshot();
    applyTexts(); applyAreas(); applyBg(); ensurePlates(); applyMaps(); applyCards();
    var vp = CFG.view && CFG.view.pan;
    setPan(vp ? vp[0] : 0, vp ? vp[1] : 0);
  }

  function applyTexts() {
    $$('[data-bm-text]').forEach(function (e) {
      var k = e.getAttribute('data-bm-text'), o = ORIG.get(e);
      var v = CFG.texts[k];
      e.textContent = (v == null || v === '') ? o.text : v;
    });
  }

  function applyAreas() {
    $$('[data-bm-area]').forEach(function (e) {
      var k = e.getAttribute('data-bm-area'), o = ORIG.get(e);
      if (k === 'toolbar') return;
      var hide = CFG.areas[k] && CFG.areas[k].hide;
      e.style.display = hide ? 'none' : o.display;
    });
    // 오른쪽 열이 빠지면 무대가 넓어진다 — 틀의 ResizeObserver 가 알아서 다시 맞춘다
  }

  // 바탕화면 — 틀이 style 을 통째로 다시 쓰는 자리라(--t 가 들어 있다) 인라인이 아니라
  // 스타일시트에 박는다. 안 고른 자리는 규칙을 안 만든다 = 틀 색 그대로.
  function luma(hex) {                         // 0(검정) ~ 1(흰색)
    var h = String(hex || '#000').replace('#', '');
    var r = parseInt(h.substr(0, 2), 16) || 0, g = parseInt(h.substr(2, 2), 16) || 0, b = parseInt(h.substr(4, 2), 16) || 0;
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  }
  // 그러데이션 끝 색. 어두운 색은 틀 비율 그대로, 밝은 색은 살짝만 — 흰 바탕이 잿빛이 안 되게
  function dim(hex, t) { var l = luma(hex); return mul(hex, t + (1 - t) * l * l); }

  function mul(hex, t) {                       // 색을 t 배로 — 틀의 그러데이션 비율 그대로
    var h = String(hex || '#000').replace('#', '');
    return '#' + [0, 2, 4].map(function (i) {
      var v = Math.round(parseInt(h.substr(i, 2), 16) * t);
      return ('0' + Math.max(0, Math.min(255, v || 0)).toString(16)).slice(-2);
    }).join('');
  }

  var BG_A = { grid: .045, glow: .10 };        // 격자·빛의 원래 진하기
  function bgCss() {
    var b = CFG.bg || {}, out = [], p = b.page, st = b.stage, g = b.grid, w = b.glow;
    function rule(k, body) { out.push('[data-bm-bg="' + k + '"]{' + body + ' !important}'); }
    function alpha(o, k) { return o.a == null ? BG_A[k] : Math.max(0, Math.min(1, +o.a)); }
    if (p && p.col) rule('page', 'background:' + (p.flat ? p.col :
      'radial-gradient(1400px 900px at 45% 25%,' + p.col + ' 0%,' + dim(p.col, .53) + ' 55%,' + dim(p.col, .31) + ' 100%)'));
    if (p && p.fg) rule('page', 'color:' + p.fg);
    if (st && st.col) rule('stage', 'background:' + (st.flat ? st.col :
      'linear-gradient(180deg,' + st.col + ' 0%,' + dim(st.col, .66) + ' 100%)'));
    if (g && g.hide) rule('grid', 'display:none');
    else if (g && (g.col || g.a != null)) {
      var gc = hexA(g.col || BG_DEF.grid, alpha(g, 'grid'));
      rule('grid', 'background-image:linear-gradient(' + gc + ' 1px,transparent 1px),linear-gradient(90deg,' + gc + ' 1px,transparent 1px)');
    }
    if (w && w.hide) rule('glow', 'display:none');
    else if (w && (w.col || w.a != null))
      rule('glow', 'background:radial-gradient(60% 50% at 50% 45%,' + hexA(w.col || BG_DEF.glow, alpha(w, 'glow')) + ',transparent 70%)');
    return out.join('\n');
  }

  function applyBg() {
    var s = $('#bm-bg-style');
    if (!s) { s = document.createElement('style'); s.id = 'bm-bg-style'; document.head.appendChild(s); }
    s.textContent = bgCss();
  }

  function applyCards() {
    $$('[data-bm-card]').forEach(applyCard);
  }

  function applyCard(card) {
    var name = card.getAttribute('data-bm-card'), c = CFG.cards[name] || {}, o = ORIG.get(card);
    if (!o) return;
    // 색 — 처음 모습으로 되돌린 뒤 새 색
    o.props.forEach(function (r) { r[0].style.setProperty(r[1], r[2]); });
    var ne = $('[data-bm-name]', card);
    if (ne) { ne.textContent = c.name || o.name; ne.style.color = o.nameColor; }
    if (c.tone && TONES[c.tone]) {
      var to = TONES[c.tone];
      o.props.forEach(function (r) {
        var v = recolor(r[2], to);
        if (v !== r[2]) r[0].style.setProperty(r[1], v);
      });
      if (ne) ne.style.color = to.name || '';
    }
    card.style.display = c.hide ? 'none' : o.display;
    card.style.setProperty('--bmx', (+c.dx || 0) + 'px');
    card.style.setProperty('--bmy', (+c.dy || 0) + 'px');
    card.style.setProperty('--bmz', (+c.dz || 0) + 'px');
  }

  // 한 속성 값 안의 색을 to 색으로 (네 벌 어느 색이든)
  function recolor(v, to) {
    var out = v;
    Object.keys(TONES).forEach(function (k) {
      var f = TONES[k];
      if (f === to) return;
      out = swap(out, f.acc, to.acc); out = swap(out, f.acc2, to.acc2);
      out = swap(out, f.bd, to.bd); out = swap(out, f.sub, to.sub); out = swap(out, f.dim, to.dim);
      out = out.split(f.bg).join(to.bg);
      var fr = f.rgb.split(','), tr = to.rgb.split(',');
      out = out.replace(new RegExp('rgba?\\(\\s*' + fr[0] + ',\\s*' + fr[1] + ',\\s*' + fr[2] + '\\s*([,)])', 'g'),
                        function (_, end) { return (end === ')' ? 'rgb(' : 'rgba(') + tr.join(', ') + end; });
    });
    return out;
  }
  function swap(v, a, b) {
    // 스타일은 브라우저가 rgb(...) 로 바꿔 들고 있다 — 두 꼴 다 갈아 끼운다
    return v.split(a).join(b).split(hexRgb(a)).join(hexRgb(b));
  }

  // 새로 만든 판 — 설정의 plates 중 added 인 것
  function ensurePlates() {
    var scene = sceneRoot();
    if (!scene) return;
    $$('[data-bm-added]', scene).forEach(function (e) {
      if (!CFG.plates.some(function (p) { return p.added && p.key === e.getAttribute('data-bm-plate'); })) e.remove();
    });
    CFG.plates.forEach(function (p) {
      if (!p.added) return;
      var e = $('[data-bm-plate="' + p.key + '"]', scene);
      if (!e) {
        e = document.createElement('div');
        e.setAttribute('data-bm-plate', p.key); e.setAttribute('data-bm-added', '1');
        e.innerHTML = '<div class="bm-face-f"></div><div class="bm-face-s"></div><div class="bm-tag"></div>';
        scene.appendChild(e);
      }
      var col = p.col || '#8fd3ff', rgb = hexToRgbList(col);
      e.style.cssText = 'position:absolute;left:' + p.x + 'px;top:' + p.y + 'px;width:' + p.w + 'px;height:' + p.h +
        'px;transform:translateZ(' + p.z + 'px);transform-style:preserve-3d;' +
        'background:linear-gradient(135deg,rgba(' + rgb + ',.14),rgba(18,30,40,.72));border:1px solid rgba(' + rgb +
        ',.4);box-shadow:0 0 44px rgba(' + rgb + ',.1),inset 0 0 36px rgba(' + rgb + ',.05)';
      var f = $('.bm-face-f', e), s = $('.bm-face-s', e), t = $('.bm-tag', e);
      f.style.cssText = 'position:absolute;left:0;top:' + p.h + 'px;width:' + p.w + 'px;height:30px;transform-origin:top;' +
        'transform:rotateX(-90deg);background:linear-gradient(180deg,rgba(' + rgb + ',.22),rgba(8,14,18,.9));border:1px solid rgba(' + rgb + ',.25)';
      s.style.cssText = 'position:absolute;left:' + p.w + 'px;top:0;width:30px;height:' + p.h + 'px;transform-origin:left;' +
        'transform:rotateY(90deg) rotateZ(-90deg) translateY(-30px);background:linear-gradient(180deg,rgba(' + rgb + ',.16),rgba(6,10,14,.9));border:1px solid rgba(' + rgb + ',.2)';
      t.style.cssText = "position:absolute;left:10px;bottom:8px;font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:600;color:rgba(" + rgb + ',.7)';
      t.textContent = p.tag || '';
    });
  }
  function sceneRoot() { var p = $('[data-bm-plate]'); return p ? p.parentElement : null; }
  function hexToRgbList(h) { h = (h || '#8fd3ff').replace('#', ''); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }).join(','); }

  function plateInfo(key) {
    for (var i = 0; i < CFG.plates.length; i++) if (CFG.plates[i].key === key) return CFG.plates[i];
    return { key: key, tag: key, col: '#3ad6c8' };
  }

  function applyMaps() {
    $$('[data-bm-plate]').forEach(function (pe) { renderMap(pe, pe.getAttribute('data-bm-plate')); });
  }

  // ─────────────────────────────────────────────────────────────── 맵 그리기
  function renderMap(pe, key) {
    $$(':scope > .bm-map', pe).forEach(function (e) { e.remove(); });
    (BLOBS[key] || []).forEach(function (u) { URL.revokeObjectURL(u); });
    BLOBS[key] = [];
    var m = CFG.maps[key];
    if (!m || !m.geo || m.hide) return;
    var PW = pe.clientWidth, PH = pe.clientHeight;
    var g = m.geo, rot = ((+m.rot || 0) % 360 + 360) % 360;
    var W = (rot === 90 || rot === 270) ? g.h : g.w, H = (rot === 90 || rot === 270) ? g.w : g.h;
    var sx = (PW - 2 * MARGIN) / W, sy = (PH - 2 * MARGIN) / H;
    if (m.fit === 'keep') sx = sy = Math.min(sx, sy);
    var mw = W * sx, mh = H * sy, ml = (PW - mw) / 2, mt = (PH - mh) / 2;
    function T(x, y) {                       // geo → 회전·뒤집기 → 판 px
      var X, Y;
      if (rot === 90) { X = g.h - y; Y = x; } else if (rot === 180) { X = g.w - x; Y = g.h - y; }
      else if (rot === 270) { X = y; Y = g.w - x; } else { X = x; Y = y; }
      if (m.fx) X = W - X;
      if (m.fy) Y = H - Y;
      return [X * sx, Y * sy];
    }
    var d = [];
    g.r.forEach(function (ln) {
      var s = '';
      for (var i = 0; i < ln.length; i += 2) {
        var p = T(ln[i], ln[i + 1]);
        s += (i ? 'L' : 'M') + Math.round(p[0] * K) + ' ' + Math.round(p[1] * K);
      }
      d.push(s);
    });
    d = d.join('');
    var col = m.col || plateInfo(key).col || '#3ad6c8', core = light(col, .72);
    var Wi = Math.ceil(mw * K), Hi = Math.ceil(mh * K);
    var q = Math.max(2, Math.round(EQ_UNITS * sx * K)), h = q / 2, rects = '';
    for (var i = 0; i < (g.e || []).length; i += 2) {
      var p = T(g.e[i], g.e[i + 1]);
      rects += 'M' + Math.round(p[0] * K - h) + ' ' + Math.round(p[1] * K - h) + 'h' + q + 'v' + q + 'h-' + q + 'z';
    }
    var svg = function (body) {
      var u = URL.createObjectURL(new Blob(['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + Wi + ' ' + Hi +
        '" preserveAspectRatio="none">' + body + '</svg>'], { type: 'image/svg+xml' }));
      BLOBS[key].push(u); return u;
    };
    var shadow = svg('<path d="' + d + '" fill="none" stroke="#000" stroke-opacity=".55" stroke-width="' + (1.4 * K) + '" stroke-linecap="round" stroke-linejoin="round"/>');
    var eqf = svg('<path d="' + rects + '" fill="#0b1a1f" fill-opacity=".9"/>');
    var eqt = svg('<path d="' + rects + '" fill="#5f7f8e" fill-opacity=".85"/>');
    var rail = svg('<path d="' + d + '" fill="none" stroke="' + col + '" stroke-opacity=".34" stroke-width="' + (2.6 * K) +
      '" stroke-linecap="round" stroke-linejoin="round"/><path d="' + d + '" fill="none" stroke="' + core + '" stroke-width="' + (0.55 * K) +
      '" stroke-linecap="round" stroke-linejoin="round"/>');

    var box = document.createElement('div');
    box.className = 'bm-map';
    box.style.cssText = 'position:absolute;left:' + ml + 'px;top:' + mt + 'px;width:' + mw + 'px;height:' + mh +
      'px;transform-style:preserve-3d;pointer-events:none';
    function layer(u, z, extra) {
      var e = document.createElement('div');
      e.style.cssText = 'position:absolute;inset:0;background:url("' + u + '") no-repeat 0 0/100% 100%;transform:translateZ(' + z + 'px);' + (extra || '');
      box.appendChild(e);
    }
    layer(shadow, .5); layer(eqf, 1); layer(eqt, EQ_Z);
    // 행거 — 칸마다 하나, 바닥까지
    var seen = {}, nh = 0, lc = light(col, .6);
    for (var a = 0; a < g.r.length && nh < HANG_MAX; a++) {
      var ln = g.r[a];
      for (var j = 0; j + 3 < ln.length && nh < HANG_MAX; j += 2) {
        var mx = (ln[j] + ln[j + 2]) / 2, my = (ln[j + 1] + ln[j + 3]) / 2;
        var ck = Math.floor(mx / HANG_CELL) + ',' + Math.floor(my / HANG_CELL);
        if (seen[ck]) continue;
        seen[ck] = 1; nh++;
        var hp = T(mx, my), he = document.createElement('div');
        he.style.cssText = 'position:absolute;left:' + hp[0] + 'px;top:' + hp[1] + 'px;width:1px;height:' + RAIL_Z +
          'px;transform-origin:0 0;transform:translateZ(' + RAIL_Z + 'px) rotateX(-90deg);background:linear-gradient(180deg,' +
          hexA(lc, .7) + ',' + hexA(lc, .05) + ')';
        box.appendChild(he);
      }
    }
    layer(rail, RAIL_Z);                     // ★filter 를 안 쓴다 — 3D 안에서 filter 는 판을 납작하게 굳혀 카드와 겹침 순서가 틀어진다
    // 판의 맨 앞(첫 자식)에 — 카드·차량 표시보다 아래
    pe.insertBefore(box, pe.firstChild);
  }
  function light(col, t) {
    var h = col.replace('#', ''), r = [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); });
    return '#' + r.map(function (v) { return ('0' + Math.round(v + (255 - v) * t).toString(16)).slice(-2); }).join('');
  }
  function hexA(col, a) { return 'rgba(' + hexToRgbList(col) + ',' + a + ')'; }

  // ─────────────────────────────────────────────────────────────── 캐시 → geo
  //   MAP_아이소_얹기.py 의 geo() 와 같은 계산 (서버 레이아웃 캐시 그대로)
  function geoFromCache(c) {
    var nodes = c.nodes || {}, und = [], seen = {}, nbr = {};
    Object.keys(c.edges || {}).forEach(function (k) {
      var p = k.split(','), a = +p[0], b = +p[1];
      if (a === b || !nodes[a] || !nodes[b]) return;
      var lo = Math.min(a, b), hi = Math.max(a, b), key = lo + ',' + hi;
      if (seen[key]) return;
      seen[key] = 1; und.push([lo, hi]);
      (nbr[lo] = nbr[lo] || []).push(hi); (nbr[hi] = nbr[hi] || []).push(lo);
    });
    if (!und.length) throw new Error('레일(edges)이 없다 — 레이아웃 캐시 JSON 이 맞나?');
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    Object.keys(nodes).forEach(function (k) {
      var v = nodes[k]; if (v[0] < x0) x0 = v[0]; if (v[0] > x1) x1 = v[0]; if (v[1] < y0) y0 = v[1]; if (v[1] > y1) y1 = v[1];
    });
    x0 -= 250; y0 -= 250; x1 += 250; y1 += 250;
    var used = {}, lines = [];
    function uk(a, b) { return a < b ? a + ',' + b : b + ',' + a; }
    function walk(s, n) {
      var line = [s, n], prev = s, cur = n;
      used[uk(s, n)] = 1;
      while (nbr[cur].length === 2) {
        var nx = nbr[cur][1] === prev ? nbr[cur][0] : nbr[cur][1];
        var k = uk(cur, nx);
        if (used[k]) break;
        used[k] = 1; line.push(nx); prev = cur; cur = nx;
      }
      return line;
    }
    Object.keys(nbr).map(Number).sort(function (a, b) { return a - b; }).forEach(function (s) {
      if (nbr[s].length !== 2) nbr[s].forEach(function (n) { if (!used[uk(s, n)]) lines.push(walk(s, n)); });
    });
    und.forEach(function (e) { if (!used[uk(e[0], e[1])]) lines.push(walk(e[0], e[1])); });
    function qx(v) { return Math.round((v - x0) / Q); }
    function qy(v) { return Math.round((v - y0) / Q); }
    var r = lines.map(function (ln) {
      var out = [], lx = null, ly = null;
      ln.forEach(function (n) { var X = qx(nodes[n][0]), Y = qy(nodes[n][1]); if (X !== lx || Y !== ly) { out.push(X, Y); lx = X; ly = Y; } });
      return out;
    }).filter(function (a) { return a.length >= 4; });
    // 설비 — dashboard.html layout3D 와 같은 자리
    var OFF = 170, STEP = 160, cell = {}, e = [];
    (c.stations || []).forEach(function (s) {
      var k = +s[3]; if (k !== 8 && k !== 9) return;
      var a = nodes[s[0]]; if (!a) return;
      var b = nodes[s[1]], dx, dy;
      if (b && (b[0] !== a[0] || b[1] !== a[1])) { dx = b[0] - a[0]; dy = b[1] - a[1]; }
      else { var ns = nbr[s[0]]; if (!ns) return; var cc = nodes[ns[0]]; dx = cc[0] - a[0]; dy = cc[1] - a[1]; }
      var l = Math.hypot(dx, dy) || 1, tx = dx / l, ty = dy / l;
      var t = b ? Math.min(1, Math.max(0, +s[2] || 0)) : 0;
      var x = a[0] + (b ? (b[0] - a[0]) * t : 0), y = a[1] + (b ? (b[1] - a[1]) * t : 0);
      var sg = k === 9 ? 1 : -1, px = x + (-ty) * OFF * sg, py = y + tx * OFF * sg;
      var key = Math.round(px / STEP) + ',' + Math.round(py / STEP);
      if (cell[key]) return;
      cell[key] = 1; e.push(qx(px), qy(py));
    });
    return { w: Math.ceil((x1 - x0) / Q), h: Math.ceil((y1 - y0) / Q), r: r, e: e,
             n: Object.keys(nodes).length, ed: und.length };
  }

  // ─────────────────────────────────────────────────────────────── 저장
  function stamp(c) { return (c && (c.savedAt || c.builtAt)) || ''; }
  function lsGet() { try { var t = localStorage.getItem(LSKEY); return t ? JSON.parse(t) : null; } catch (e) { return null; } }
  function lsSet(c) { try { localStorage.setItem(LSKEY, JSON.stringify(c)); return true; } catch (e) { return false; } }

  // 고른 파일 자리를 기억한다 (IndexedDB — 크롬·엣지만)
  function idb() {
    return new Promise(function (ok, no) {
      if (!window.indexedDB) return no(new Error('no idb'));
      var r = indexedDB.open('bm-editor', 1);
      r.onupgradeneeded = function () { r.result.createObjectStore('h'); };
      r.onsuccess = function () { ok(r.result); }; r.onerror = function () { no(r.error); };
    });
  }
  function idbGet() {
    return idb().then(function (db) { return new Promise(function (ok) {
      var q = db.transaction('h').objectStore('h').get(LSKEY); q.onsuccess = function () { ok(q.result || null); }; q.onerror = function () { ok(null); };
    }); }).catch(function () { return null; });
  }
  function idbSet(h) {
    return idb().then(function (db) { return new Promise(function (ok) {
      var t = db.transaction('h', 'readwrite'); t.objectStore('h').put(h, LSKEY); t.oncomplete = ok; t.onerror = ok;
    }); }).catch(function () {});
  }

  function configText() { return JSON.stringify(CFG, null, 1); }

  // 저장 — 설정 JSON 한 장. 이 브라우저에도 남겨 다음에 열면 이대로 뜬다
  function save() {
    CFG.saved = true; CFG.savedAt = new Date().toISOString();
    CFG.view = CFG.view || {}; CFG.view.pan = pan.slice();
    var txt = configText(), blob = new Blob([txt], { type: 'application/json' });
    var kept = lsSet(CFG);
    function done(where) {
      LOADED = clone(CFG); setDirty(false);
      toast('저장했다 — ' + where + (kept ? ' (이 브라우저에도 남겼다)' : ''));
    }
    function writeTo(h) {
      return h.createWritable().then(function (w) { return w.write(blob).then(function () { return w.close(); }); })
        .then(function () { fileHandle = h; idbSet(h); done(h.name); });
    }
    if (window.showSaveFilePicker) {
      var p = fileHandle
        ? fileHandle.queryPermission({ mode: 'readwrite' }).then(function (st) {
            return st === 'granted' ? st : fileHandle.requestPermission({ mode: 'readwrite' });
          }).then(function (st) { if (st !== 'granted') throw new Error('perm'); return writeTo(fileHandle); })
        : Promise.reject(new Error('none'));
      p.catch(function (e) {
        if (e && e.name === 'AbortError') return;
        return window.showSaveFilePicker({ suggestedName: JSON_NAME,
          types: [{ description: '모니터 설정 JSON', accept: { 'application/json': ['.json'] } }] }).then(writeTo);
      }).catch(function (e) {
        if (e && e.name === 'AbortError') return;
        download(blob, JSON_NAME); done('내려받기 ' + JSON_NAME);
      });
    } else {
      download(blob, JSON_NAME); done('내려받기 ' + JSON_NAME);
    }
  }

  // 불러오기 — 설정 JSON 을 골라 그대로 연다
  function load() {
    function use(txt, h) {
      var c = JSON.parse(txt);
      if (!c || !c.plates || !c.cards) throw new Error('모니터 설정 JSON 이 아니다');
      norm(c); CFG = c; LOADED = clone(c); lsSet(c);
      if (h) { fileHandle = h; idbSet(h); }
      applyAll(); setDirty(false); draw();
      toast('불러왔다' + (h ? ' — ' + h.name : '') + ' (다음에 열면 이대로 뜬다)');
    }
    if (window.showOpenFilePicker) {
      window.showOpenFilePicker({ types: [{ description: '모니터 설정 JSON', accept: { 'application/json': ['.json'] } }] })
        .then(function (hs) { var h = hs[0]; return h.getFile().then(function (f) { return f.text(); }).then(function (t) { use(t, h); }); })
        .catch(function (e) { if (e && e.name === 'AbortError') return; alert('못 불러옴: ' + e.message); });
    } else {
      pickFile('.json', function (txt) { use(txt, null); });
    }
  }
  function download(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }

  function setDirty(v) {
    dirty = v;
    var s = ui && $('.bm-state', ui);
    if (s) { s.textContent = v ? '● 저장 안 됨' : '저장됨'; s.className = 'bm-state' + (v ? ' bm-dirty' : ''); }
  }
  function changed() { setDirty(true); }
  function toast(msg) {
    var t = document.createElement('div');
    t.className = 'bm-toast'; t.textContent = msg; document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }

  // ─────────────────────────────────────────────────────────────── 버튼·창
  function addButton() {
    var bar = $('[data-bm-area="toolbar"]');
    if (!bar || $('.bm-open', bar)) return;
    var b = document.createElement('button');
    b.className = 'bm-open'; b.type = 'button'; b.textContent = '✎ 수정';
    b.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    b.addEventListener('click', function (e) { e.stopPropagation(); ui ? closeUI() : openUI(); });
    bar.appendChild(b);
  }

  function openUI() {
    if (ui) return;
    ui = document.createElement('div');
    ui.className = 'bm-ui';
    ui.innerHTML =
      '<div class="bm-head"><b>✎ 수정</b><span class="bm-state">저장됨</span><span style="flex:1"></span>' +
      '<button class="bm-btn bm-pri" data-act="save" title="설정 JSON 으로 저장">저장 (JSON)</button><button class="bm-btn" data-act="close">닫기</button></div>' +
      '<div class="bm-tabs"><button data-tab="map">판 · 맵</button><button data-tab="card">패널</button><button data-tab="view">화면</button></div>' +
      '<div class="bm-body"></div>' +
      '<div class="bm-foot"><button class="bm-btn" data-act="import">설정 불러오기 (JSON)</button>' +
      '<button class="bm-btn" data-act="revert">연 때로 되돌리기</button>' +
      '<button class="bm-btn" data-act="base">HTML 기본값으로</button></div>';
    ['mousedown', 'wheel', 'pointerdown'].forEach(function (ev) { ui.addEventListener(ev, function (e) { e.stopPropagation(); }); });
    ui.addEventListener('click', onClick);
    ui.addEventListener('input', onInput);
    ui.addEventListener('change', onInput);
    ui.addEventListener('mouseover', onHover);
    ui.addEventListener('mouseout', onHover);
    document.body.appendChild(ui);
    document.documentElement.classList.add('bm-editing');
    setDirty(dirty);
    draw();
  }
  function closeUI() {
    if (ui) { ui.remove(); ui = null; }
    document.documentElement.classList.remove('bm-editing');
    unhighlight(); select(null);
  }

  function draw() {
    if (!ui) return;
    $$('.bm-tabs button', ui).forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === tab); });
    var body = $('.bm-body', ui);
    body.innerHTML = tab === 'map' ? drawMaps() : tab === 'card' ? drawCards() : drawView();
  }

  function num(path, v, step, label) {
    return '<label class="bm-num">' + label + '<input type="number" step="' + (step || 10) + '" data-path="' + path + '" value="' + (v || 0) + '"></label>';
  }

  function drawMaps() {
    var h = '<p class="bm-hint">맵은 서버의 레이아웃 캐시(<code>OHT_MAP\\cache\\*_layout_cache.json</code>)를 불러온다. ' +
            '판에 없던 맵을 불러오면 그게 <b>맵 추가</b>다.</p>';
    CFG.plates.forEach(function (p) {
      var m = CFG.maps[p.key], k = p.key;
      h += '<div class="bm-item" data-plate="' + k + '"><div class="bm-row"><b>' + esc(p.tag) + '</b><span class="bm-sub">' +
        (m && m.geo ? esc(m.name || '') + ' · 노드 ' + (m.geo.n || '?').toLocaleString() : '맵 없음') + '</span></div>';
      h += '<div class="bm-row"><button class="bm-btn" data-act="load" data-key="' + k + '">' + (m ? '맵 바꾸기' : '맵 불러오기') + '</button>';
      if (m) h += '<button class="bm-btn" data-act="unmap" data-key="' + k + '">맵 지우기</button>';
      if (p.added) h += '<button class="bm-btn bm-warn" data-act="delplate" data-key="' + k + '">판 삭제</button>';
      h += '</div>';
      if (m) {
        h += '<div class="bm-row"><label>맞춤 <select data-path="maps.' + k + '.fit"><option value="fill"' + (m.fit !== 'keep' ? ' selected' : '') +
          '>판에 꽉 채우기</option><option value="keep"' + (m.fit === 'keep' ? ' selected' : '') + '>비율 유지</option></select></label>' +
          '<label>회전 <select data-path="maps.' + k + '.rot">' + [0, 90, 180, 270].map(function (r) {
            return '<option value="' + r + '"' + ((+m.rot || 0) === r ? ' selected' : '') + '>' + r + '°</option>'; }).join('') + '</select></label></div>' +
          '<div class="bm-row"><label><input type="checkbox" data-path="maps.' + k + '.fx"' + (m.fx ? ' checked' : '') + '> 좌우 뒤집기</label>' +
          '<label><input type="checkbox" data-path="maps.' + k + '.fy"' + (m.fy ? ' checked' : '') + '> 상하 뒤집기</label>' +
          '<label>레일 색 <input type="color" data-path="maps.' + k + '.col" value="' + (m.col || p.col || '#3ad6c8') + '"></label></div>';
      }
      if (p.added) {
        h += '<div class="bm-row"><label>이름 <input type="text" data-path="plate.' + k + '.tag" value="' + esc(p.tag) + '"></label>' +
          '<label>색 <input type="color" data-path="plate.' + k + '.col" value="' + (p.col || '#8fd3ff') + '"></label></div>' +
          '<div class="bm-row">' + num('plate.' + k + '.x', p.x, 10, '좌우') + num('plate.' + k + '.y', p.y, 10, '앞뒤') +
          num('plate.' + k + '.z', p.z, 10, '높이') + '</div><div class="bm-row">' +
          num('plate.' + k + '.w', p.w, 10, '가로') + num('plate.' + k + '.h', p.h, 10, '세로') + '</div>';
      }
      h += '</div>';
    });
    h += '<div class="bm-row"><button class="bm-btn bm-pri" data-act="addplate">+ 판 추가</button></div>';
    return h;
  }

  function drawCards() {
    var h = '<p class="bm-hint"><b>화면에서 패널을 마우스로 끌면 옮겨진다</b> — 그냥 끌기 = 바닥 위 좌우·앞뒤, ' +
            '<b>Shift + 끌기 = 높이</b>. 패널을 누르면 여기 그 칸으로 온다. 위치 단위는 px. ' +
            '(<b>Ctrl + 끌기</b> 는 패널이 아니라 화면 이동이다)</p>';
    $$('[data-bm-card]').forEach(function (card) {
      var n = card.getAttribute('data-bm-card'), c = CFG.cards[n] || {}, o = ORIG.get(card) || {};
      h += '<div class="bm-item' + (sel === n ? ' bm-on' : '') + '" data-card="' + esc(n) + '"><div class="bm-row"><label><input type="checkbox" data-path="card.' + esc(n) +
        '.show"' + (c.hide ? '' : ' checked') + '> <b>' + esc(o.name || n) + '</b></label><span style="flex:1"></span>' +
        '<button class="bm-btn" data-act="cardreset" data-key="' + esc(n) + '">원래대로</button></div>' +
        '<div class="bm-row"><label>이름 <input type="text" data-path="card.' + esc(n) + '.name" value="' + esc(c.name || '') +
        '" placeholder="' + esc(o.name || n) + '"></label><label>색 <select data-path="card.' + esc(n) + '.tone">' +
        Object.keys(TONE_NAMES).map(function (t) { return '<option value="' + t + '"' + ((c.tone || '') === t ? ' selected' : '') + '>' + TONE_NAMES[t] + '</option>'; }).join('') +
        '</select></label></div><div class="bm-row">' + num('card.' + esc(n) + '.dx', c.dx, 10, '좌우') +
        num('card.' + esc(n) + '.dy', c.dy, 10, '앞뒤') + num('card.' + esc(n) + '.dz', c.dz, 10, '높이') + '</div></div>';
    });
    return h;
  }

  function drawView() {
    var areas = [['aside', '오른쪽 열 (BRIDGE STATUS · ACTIVE ALARM · HUB THROUGHPUT)'], ['kpi', '위 KPI (IN TRANSIT · CAPACITY · ALARM · LOCAL)'],
                 ['legend', '범례 (ISOMETRIC VIEW · UP · DOWN · ALARM)'], ['hint', '안내 (DRAG TO ORBIT …)']];
    var h = '<div class="bm-item"><div class="bm-row"><label style="flex:1">제목 <input type="text" style="flex:1" data-path="text.title" value="' +
      esc(CFG.texts.title || '') + '" placeholder="' + esc(origText('title')) + '"></label></div>' +
      '<div class="bm-row"><label style="flex:1">윗글 <input type="text" style="flex:1" data-path="text.subtitle" value="' +
      esc(CFG.texts.subtitle || '') + '" placeholder="' + esc(origText('subtitle')) + '"></label></div>' +
      '<div class="bm-row"><label style="flex:1">안내 <input type="text" style="flex:1" data-path="text.hint" value="' +
      esc(CFG.texts.hint || '') + '" placeholder="' + esc(origText('hint')) + '"></label></div></div><div class="bm-item">';
    areas.forEach(function (a) {
      if (!$('[data-bm-area="' + a[0] + '"]')) return;
      h += '<div class="bm-row"><label><input type="checkbox" data-path="area.' + a[0] + '"' +
        (CFG.areas[a[0]] && CFG.areas[a[0]].hide ? '' : ' checked') + '> ' + a[1] + '</label></div>';
    });
    return h + '</div>' + drawBg();
  }

  // 바탕화면 — 고객: "바탕화면 색상변경가능하게 해주라"
  function drawBg() {
    var h = '<div class="bm-item"><div class="bm-row"><b>바탕화면</b><span class="bm-sub">고른 자리만 바뀐다</span></div>' +
      '<div class="bm-row">' + BG_PRESETS.map(function (p, i) {
        return '<button class="bm-btn" data-act="bgpreset" data-key="' + i + '">' + p.name + '</button>';
      }).join('') + '</div></div>';
    return h + ['page', 'stage', 'grid', 'glow'].map(bgRow).join('');
  }
  function bgRow(k) {
    var b = (CFG.bg || {})[k] || {};
    var h = '<div class="bm-item"><div class="bm-row"><b style="flex:1">' + BG_NAMES[k] + '</b>' +
      '<button class="bm-btn" data-act="bgreset" data-key="' + k + '">원래대로</button></div><div class="bm-row">';
    if (k === 'grid' || k === 'glow')
      h += '<label><input type="checkbox" data-path="bg.' + k + '.show"' + (b.hide ? '' : ' checked') + '> 보이기</label>';
    h += '<label>색 <input type="color" data-path="bg.' + k + '.col" value="' + (b.col || BG_DEF[k]) + '"></label>';
    if (k === 'page' || k === 'stage')
      h += '<label><input type="checkbox" data-path="bg.' + k + '.flat"' + (b.flat ? ' checked' : '') + '> 단색</label>';
    if (k === 'page')
      h += '<label>글자색 <input type="color" data-path="bg.page.fg" value="' + (b.fg || BG_FG) + '"></label>';
    if (k === 'grid' || k === 'glow')
      h += '<label class="bm-num">진하기 <input type="number" min="0" max="1" step="0.01" data-path="bg.' + k +
           '.a" value="' + (b.a == null ? BG_A[k] : b.a) + '"></label>';
    return h + '</div></div>';
  }
  function origText(k) { var e = $('[data-bm-text="' + k + '"]'); return e && ORIG.get(e) ? ORIG.get(e).text : ''; }

  function onClick(e) {
    var t = e.target.closest('[data-tab],[data-act]');
    if (!t) return;
    var tb = t.getAttribute('data-tab');
    if (tb) { tab = tb; draw(); return; }
    var act = t.getAttribute('data-act'), key = t.getAttribute('data-key');
    if (act === 'close') closeUI();
    else if (act === 'save') save();
    else if (act === 'load') pickMap(key);
    else if (act === 'unmap') { delete CFG.maps[key]; renderOne(key); changed(); draw(); }
    else if (act === 'addplate') {
      var k = 'p' + Date.now().toString(36);
      CFG.plates.push({ key: k, tag: '새 판', added: true, x: 380, y: 580, w: 260, h: 170, z: 100, col: '#8fd3ff' });
      ensurePlates(); changed(); draw();
    } else if (act === 'delplate') {
      CFG.plates = CFG.plates.filter(function (p) { return p.key !== key; });
      delete CFG.maps[key]; ensurePlates(); changed(); draw();
    } else if (act === 'cardreset') { delete CFG.cards[key]; applyCards(); changed(); draw(); }
    else if (act === 'bgreset') { if (CFG.bg) delete CFG.bg[key]; applyBg(); changed(); draw(); }
    else if (act === 'bgpreset') { CFG.bg = clone(BG_PRESETS[+key].bg); applyBg(); changed(); draw(); }
    else if (act === 'import') load();
    else if (act === 'revert') {
      if (!confirm('연 때 설정으로 되돌릴까?')) return;
      CFG = clone(LOADED); applyAll(); setDirty(false); draw();
    } else if (act === 'base') {
      if (!confirm('HTML 에 든 기본 설정으로 돌아갈까? (저장해야 남는다)')) return;
      CFG = clone(BUILT); applyAll(); changed(); draw();
    }
  }

  function onInput(e) {
    var t = e.target, path = t.getAttribute && t.getAttribute('data-path');
    if (!path) return;
    var v = t.type === 'checkbox' ? t.checked : t.type === 'number' ? (+t.value || 0) : t.value;
    var p = path.split('.'), kind = p[0];
    if (kind === 'maps') {
      var m = CFG.maps[p[1]]; if (!m) return;
      m[p[2]] = p[2] === 'rot' ? +v : v;
      if (e.type === 'change' || t.type === 'color') renderOne(p[1]);
    } else if (kind === 'plate') {
      var pl = plateInfo(p[1]); pl[p[2]] = v; ensurePlates(); if (/[wh]/.test(p[2]) || p[2] === 'col') renderOne(p[1]);
    } else if (kind === 'card') {
      var c = CFG.cards[p[1]] = CFG.cards[p[1]] || {};
      if (p[2] === 'show') { if (v) delete c.hide; else c.hide = true; }
      else if (v === '' || v === 0) delete c[p[2]]; else c[p[2]] = v;
      if (!Object.keys(c).length) delete CFG.cards[p[1]];
      var card = $('[data-bm-card="' + p[1] + '"]'); if (card) applyCard(card);
    } else if (kind === 'area') {
      if (v) delete CFG.areas[p[1]]; else CFG.areas[p[1]] = { hide: true };
      applyAreas();
      setTimeout(applyMaps, 300);           // 무대 크기가 바뀌었다 — 판 크기는 그대로라 맵도 그대로지만 한 번 더
    } else if (kind === 'bg') {
      CFG.bg = CFG.bg || {};
      var bb = CFG.bg[p[1]] = CFG.bg[p[1]] || {};
      if (p[2] === 'show') { if (v) delete bb.hide; else bb.hide = true; }
      else if (v === false || v === '') delete bb[p[2]];
      else bb[p[2]] = v;
      if (!Object.keys(bb).length) delete CFG.bg[p[1]];
      applyBg();
    } else if (kind === 'text') {
      if (v === '') delete CFG.texts[p[1]]; else CFG.texts[p[1]] = v;
      applyTexts();
    }
    changed();
  }

  function renderOne(key) { var pe = $('[data-bm-plate="' + key + '"]'); if (pe) renderMap(pe, key); }

  function pickFile(accept, cb) {
    var inp = document.createElement('input');
    inp.type = 'file'; inp.accept = accept; inp.style.display = 'none';
    document.body.appendChild(inp);                  // ★떨어진 input 은 창이 안 뜨는 브라우저가 있다
    setTimeout(function () { if (inp.parentNode && !inp.files.length) inp.remove(); }, 600000);
    inp.onchange = function () {
      var f = inp.files && inp.files[0]; inp.remove(); if (!f) return;
      var r = new FileReader();
      r.onload = function () { try { cb(r.result, f.name); } catch (err) { alert('못 불러옴: ' + err.message); } };
      r.readAsText(f);
    };
    inp.click();
  }

  function pickMap(key) {
    pickFile('.json', function (txt, fname) {
      var c = JSON.parse(txt), geo;
      if (c.geo && c.geo.r) geo = c.geo;                  // 내보낸 맵
      else geo = geoFromCache(c);                          // 서버 레이아웃 캐시
      var nm = fname.replace(/_layout_cache\.json$/i, '').replace(/\.json$/i, '');
      var mm = nm.match(/^([A-Za-z0-9]+)_([A-Za-z0-9]+)$/);
      var old = CFG.maps[key] || {};
      CFG.maps[key] = { name: mm ? mm[1] + '/' + mm[2] : nm, fit: old.fit || 'fill', rot: old.rot || 0,
                        fx: !!old.fx, fy: !!old.fy, col: old.col, geo: geo };
      if (!CFG.maps[key].col) delete CFG.maps[key].col;
      renderOne(key); changed(); draw();
      toast(CFG.maps[key].name + ' → ' + plateInfo(key).tag + ' (노드 ' + (geo.n || '?') + ')');
    });
  }

  // ─────────────────────────────────────────────── Ctrl + 왼쪽 끌기 (· 오른쪽 끌기) = 화면 이동
  //   고객: "마우스 오른쪽 버튼 클릭하면 왼쪽 오른쪽으로 위로 아래로 이동되게 해주라" ·
  //        "현재 마우스로 움직이는 왼쪽으로 하는 부분은 ctrl 누르면 변경되게 해주라"
  //        → Ctrl 을 누른 채 왼쪽으로 끌면 돌리기 대신 이동. 놓으면 도로 돌리기.
  //   틀의 무대 transform 앞에 translate(var(--bmpx),var(--bmpy)) 를 끼워 두었다 —
  //   틀이 돌리기·줌마다 transform 을 다시 써도 이동은 안 풀린다. RESET 이면 0 으로.
  var pan = [0, 0];
  function sceneEl() { return $('[data-bm-scene]') || sceneRoot(); }
  function setPan(x, y) {
    pan = [Math.round(x) || 0, Math.round(y) || 0];
    var sc = sceneEl();
    if (sc) { sc.style.setProperty('--bmpx', pan[0] + 'px'); sc.style.setProperty('--bmpy', pan[1] + 'px'); }
  }
  function initPan() {
    var sc = sceneEl(), stage = sc && sc.parentElement, pd = null;
    if (!stage) return;
    stage.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    document.addEventListener('mousedown', function (e) {
      if (!stage.contains(e.target) || (ui && ui.contains(e.target))) return;
      if (!(e.button === 2 || (e.button === 0 && e.ctrlKey))) return;
      e.preventDefault(); e.stopPropagation();
      pd = { x: e.clientX, y: e.clientY, p: pan.slice() };
      document.documentElement.classList.add('bm-panning');
    }, true);
    document.addEventListener('mousemove', function (e) {
      if (!pd) return;
      e.preventDefault(); e.stopPropagation();
      setPan(pd.p[0] + e.clientX - pd.x, pd.p[1] + e.clientY - pd.y);
    }, true);
    document.addEventListener('mouseup', function (e) {
      if (!pd) return;
      e.preventDefault(); e.stopPropagation();
      pd = null;
      document.documentElement.classList.remove('bm-panning');
      if (ui) changed();                          // 수정 중이면 저장할 거리
    }, true);
    var bar = $('[data-bm-area="toolbar"]');
    $$('button', bar).forEach(function (b) {
      if (/RESET/.test(b.textContent)) b.addEventListener('click', function () { setPan(0, 0); });
    });
  }

  // ─────────────────────────────────────────────────────────────── 마우스로 패널 옮기기
  //   고객: "수정하고 패널 누를 때 마우스로 변경할 수 있게도 해주지".
  //   수정 창이 열려 있을 때만. 패널 위에서 누른 것은 틀(돌리기)에 안 넘긴다.
  //   화면에서 끈 거리를 바닥(판) 위 거리로 되돌린다 — 틀의 무대가
  //   scale(s) rotateX(rx) rotateZ(rz) 라 그 반대로 푼다.
  var sel = null, drag = null;
  function sceneAngles() {
    var sc = sceneRoot(), t = sc ? sc.style.transform : '';
    var m1 = /scale\(([-\d.e]+)\)/.exec(t), m2 = /rotateX\(([-\d.e]+)deg\)/.exec(t), m3 = /rotateZ\(([-\d.e]+)deg\)/.exec(t);
    return { s: m1 ? +m1[1] : 1, rx: (m2 ? +m2[1] : 60) * Math.PI / 180, rz: (m3 ? +m3[1] : -45) * Math.PI / 180 };
  }
  function toFloor(du, dv) {
    var a = sceneAngles(), s = a.s || 1;
    var u = du / s, v = dv / (s * Math.max(.15, Math.cos(a.rx)));
    return { dx: u * Math.cos(a.rz) + v * Math.sin(a.rz), dy: -u * Math.sin(a.rz) + v * Math.cos(a.rz),
             dz: -dv / (s * Math.max(.15, Math.sin(a.rx))) };
  }
  document.addEventListener('mousedown', function (e) {
    if (!ui || e.button !== 0 || e.ctrlKey) return;      // ★Ctrl 은 화면 이동 — 패널을 안 집는다
    var card = e.target.closest && e.target.closest('[data-bm-card]');
    if (!card) return;
    // ★틀(React)은 문서 위쪽 뿌리에서 듣는다 — 여기(document, 잡는 단계)에서 멈추면 돌리기가 안 걸린다
    e.preventDefault(); e.stopPropagation();
    var n = card.getAttribute('data-bm-card'), c = CFG.cards[n] || {};
    drag = { card: card, name: n, x: e.clientX, y: e.clientY, moved: false,
             dx: +c.dx || 0, dy: +c.dy || 0, dz: +c.dz || 0, shift: e.shiftKey };
  }, true);
  document.addEventListener('mousemove', function (e) {
    if (!drag) return;
    e.preventDefault(); e.stopPropagation();
    var du = e.clientX - drag.x, dv = e.clientY - drag.y;
    if (!drag.moved && Math.abs(du) + Math.abs(dv) < 4) return;
    drag.moved = true;
    var f = toFloor(du, dv), c = CFG.cards[drag.name] = CFG.cards[drag.name] || {};
    if (drag.shift || e.shiftKey) { c.dz = Math.round(drag.dz + f.dz); c.dx = drag.dx; c.dy = drag.dy; }
    else { c.dx = Math.round(drag.dx + f.dx); c.dy = Math.round(drag.dy + f.dy); c.dz = drag.dz; }
    ['dx', 'dy', 'dz'].forEach(function (k) { if (!c[k]) delete c[k]; });
    drag.card.style.setProperty('--bmx', (c.dx || 0) + 'px');
    drag.card.style.setProperty('--bmy', (c.dy || 0) + 'px');
    drag.card.style.setProperty('--bmz', (c.dz || 0) + 'px');
    document.documentElement.classList.add('bm-dragging');
    syncCardInputs(drag.name);
  }, true);
  document.addEventListener('mouseup', function (e) {
    if (!drag) return;
    e.preventDefault(); e.stopPropagation();
    var d = drag; drag = null;
    document.documentElement.classList.remove('bm-dragging');
    if (!Object.keys(CFG.cards[d.name] || {}).length) delete CFG.cards[d.name];
    if (d.moved) changed();
    select(d.name);                            // 누른 패널 칸으로
  }, true);
  document.addEventListener('click', function (e) {
    if (ui && e.target.closest && e.target.closest('[data-bm-card]')) { e.preventDefault(); e.stopPropagation(); }
  }, true);

  function select(n) {
    $$('.bm-sel').forEach(function (e) { e.classList.remove('bm-sel'); });
    sel = n;
    if (!n || !ui) return;
    var card = $('[data-bm-card="' + n + '"]');
    if (card) card.classList.add('bm-sel');
    if (tab !== 'card') { tab = 'card'; draw(); }
    $$('.bm-item[data-card]', ui).forEach(function (it) { it.classList.toggle('bm-on', it.getAttribute('data-card') === n); });
    var it = $('.bm-item[data-card="' + n + '"]', ui);
    if (it) it.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function syncCardInputs(n) {
    if (!ui) return;
    var c = CFG.cards[n] || {};
    ['dx', 'dy', 'dz'].forEach(function (k) {
      var inp = $('input[data-path="card.' + n + '.' + k + '"]', ui);
      if (inp && document.activeElement !== inp) inp.value = c[k] || 0;
    });
  }

  var hl = null;
  function onHover(e) {
    var it = e.target.closest && e.target.closest('[data-card],[data-plate]');
    if (e.type === 'mouseout') { if (!it || !it.contains(e.relatedTarget)) unhighlight(); return; }
    if (!it) return;
    var sel = it.hasAttribute('data-card') ? '[data-bm-card="' + it.getAttribute('data-card') + '"]'
                                           : '[data-bm-plate="' + it.getAttribute('data-plate') + '"]';
    var el = $(sel);
    if (el === hl) return;
    unhighlight();
    if (el) { hl = el; el.classList.add('bm-hl'); }
  }
  function unhighlight() { if (hl) { hl.classList.remove('bm-hl'); hl = null; } }

  function injectStyle() {
    if ($('#bm-style')) return;
    var s = document.createElement('style');
    s.id = 'bm-style';
    s.textContent = [
      '.bm-open{height:30px;padding:0 12px;background:rgba(58,214,200,.14);border:1px solid rgba(58,214,200,.55);color:#bff6f0;border-radius:7px;cursor:pointer;font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em}',
      '.bm-open:hover{background:rgba(58,214,200,.28)}',
      '.bm-ui{position:fixed;top:0;right:0;bottom:0;width:380px;max-width:92vw;z-index:2147483000;display:flex;flex-direction:column;background:#0b1118;border-left:1px solid #22313f;box-shadow:-18px 0 48px rgba(0,0,0,.55);color:#cfe0ec;font:12px/1.45 "IBM Plex Sans KR","Malgun Gothic",sans-serif}',
      '.bm-head{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid #1c2a37;font-size:13px}',
      '.bm-state{font-size:11px;color:#6b8093}.bm-state.bm-dirty{color:#ffce7a}',
      '.bm-tabs{display:flex;border-bottom:1px solid #1c2a37}.bm-tabs button{flex:1;padding:9px 0;background:none;border:0;border-bottom:2px solid transparent;color:#8fa3b5;cursor:pointer;font:inherit}',
      '.bm-tabs button.on{color:#e8eff6;border-bottom-color:#3ad6c8}',
      '.bm-body{flex:1;overflow:auto;padding:10px 12px}',
      '.bm-foot{display:flex;flex-wrap:wrap;gap:6px;padding:10px 12px;border-top:1px solid #1c2a37}',
      '.bm-item{border:1px solid #1c2a37;border-radius:8px;padding:8px 10px;margin-bottom:8px;background:#0e161f}',
      '.bm-item:hover{border-color:#2e4a5c}',
      '.bm-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:4px 0}',
      '.bm-row label{display:flex;align-items:center;gap:5px;color:#9fb6c8}',
      '.bm-sub{color:#6b8093;font-size:11px}',
      '.bm-hint{color:#6b8093;font-size:11px;margin:2px 0 10px}.bm-hint code{color:#9fb6c8}',
      '.bm-ui input[type=text],.bm-ui select,.bm-ui input[type=number]{background:#0a1016;border:1px solid #27374a;color:#e8eff6;border-radius:5px;padding:3px 6px;font:inherit}',
      '.bm-ui input[type=text]{width:120px}.bm-num input{width:62px}',
      '.bm-ui input[type=color]{width:34px;height:22px;padding:0;border:1px solid #27374a;background:none;border-radius:4px}',
      '.bm-btn{background:#121c26;border:1px solid #27374a;color:#cfe0ec;border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit}',
      '.bm-btn:hover{border-color:#3ad6c8;color:#fff}.bm-pri{background:rgba(58,214,200,.16);border-color:rgba(58,214,200,.55)}',
      '.bm-warn{border-color:#5c3034;color:#ffb0b0}',
      '.bm-toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:2147483001;background:#0e161f;border:1px solid #3ad6c8;color:#e8eff6;padding:9px 16px;border-radius:8px;font:12px "IBM Plex Sans KR",sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.5)}',
      '.bm-hl{outline:2px dashed #fff !important;outline-offset:3px;animation:bmblink .8s ease-in-out infinite}',
      '.bm-editing [data-bm-card]{cursor:move !important}',
      '.bm-editing [data-bm-card]:hover{outline:1px dashed rgba(255,255,255,.55);outline-offset:3px}',
      '.bm-dragging,.bm-dragging *{cursor:grabbing !important;user-select:none !important}',
      '.bm-panning,.bm-panning *{cursor:move !important;user-select:none !important}',
      '.bm-sel{outline:2px solid #3ad6c8 !important;outline-offset:3px}',
      '.bm-item.bm-on{border-color:#3ad6c8;box-shadow:0 0 0 1px rgba(58,214,200,.35) inset}',
      '@keyframes bmblink{50%{outline-color:rgba(255,255,255,.2)}}'
    ].join('\n');
    document.head.appendChild(s);
  }
})();
