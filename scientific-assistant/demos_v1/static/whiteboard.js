/* demos_v1/static/whiteboard.js — 화이트보드 1단계: 답변 속 ```mermaid 글을 그림으로
 *
 * 데모스(/) · 개인 에이전트 창 · 코딩 어시스턴트(/code/) 가 이 한 파일을 같이 쓴다.
 *   WB.setup({cls:{block,head,title,acts,btn}, accent})  앱마다 한 번. 틀·머리·버튼은 그 앱의
 *                                                       기존 클래스를 받아 쓴다(여기서 꾸미지 않는다).
 *                                                       accent: 상자 테두리 색 — CSS 값, 또는
 *                                                       'button'(그 앱 버튼 색을 따라간다)
 *   WB.renderIn(root)   root 안의 <pre><code class="language-mermaid"> 를 그림으로 (Promise → 그린 수)
 *   WB.watch(el)        el 안에 글이 새로 붙을 때마다 renderIn(el) — 세션 복원까지 한 줄로
 *   WB.render(src)      글 하나 → {ok, svg, w, h, kind_ko, title, error, line} (2단계 보드가 쓴다)
 *
 * ★그림은 서버가 그린다(POST /api/whiteboard/render). 폐쇄망이라 mermaid.min.js 가 없다.
 * ★원문은 지우지 않는다 — <pre> 를 숨겨 두고 [원문] 으로 연다. 못 그린 글은 그대로 두고
 *   무엇이 틀렸는지(몇째 줄)만 위에 한 줄 적는다.
 * ★버튼 처리는 문서 한 곳(data-wb-act)에서 받는다. 데모스는 대화를 innerHTML 로 저장했다가
 *   되살리므로, 버튼마다 붙인 처리기는 되살린 뒤에 사라진다.
 * ★그림 속 글자·선은 currentColor(둘레 글자색), 글 뒤 바탕은 --wb-bg 다. --wb-bg 는 그림이
 *   놓인 자리의 실제 바탕색을 재서 넣고, 테마를 바꾸면 다시 잰다.
 */
(function () {
  'use strict';
  if (window.WB) return;

  var API = '/api/whiteboard/render';
  var BATCH = 20;
  var CACHE_MAX = 200;
  var cfg = { cls: {}, accent: '' };
  var cache = new Map();            // 원문 → 서버 결과
  var busy = new WeakSet();         // 지금 서버에 물어보는 중인 <pre>
  var downUntil = 0;                // 서버에 못 닿았으면 잠깐 쉰다(스트리밍 중 연타 방지)
  var seq = 0;

  var CSS =
    '.wb-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px}' +
    '.wb-acts{display:flex;flex-wrap:wrap;gap:6px}' +
    '.wb-view{overflow:auto;padding:12px 10px}' +
    '.wb-view svg{display:block;height:auto;margin:0 auto}' +
    '.wb-note{font-size:11.5px;opacity:.75;margin:8px 0 4px;white-space:normal}' +
    'pre[data-wb="ok"][hidden]{display:none!important}';

  function addCss() {
    if (document.getElementById('wb-css')) return;
    var st = document.createElement('style');
    st.id = 'wb-css';
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  function el(tag, cls) {
    var e = document.createElement(tag);
    if (cls) e.className = cls.trim();
    return e;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── 서버 ──
  function remember(src, r) {
    if (cache.has(src)) cache.delete(src);
    cache.set(src, r);
    if (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
  }

  function post(srcs) {
    return fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: srcs.map(function (s) { return { src: s }; }) })
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      if (!d || !Array.isArray(d.items)) throw new Error('답이 이상합니다');
      srcs.forEach(function (s, i) { if (d.items[i]) remember(s, d.items[i]); });
    });
  }

  function fetchAll(srcs) {
    var need = srcs.filter(function (s) { return !cache.has(s); });
    if (!need.length) return Promise.resolve();
    if (Date.now() < downUntil) return Promise.reject(new Error('잠시 쉬는 중'));
    var jobs = [];
    for (var i = 0; i < need.length; i += BATCH) jobs.push(post(need.slice(i, i + BATCH)));
    return Promise.all(jobs).catch(function (e) {
      downUntil = Date.now() + 30000;
      throw e;
    });
  }

  function render(src) {
    src = String(src || '').trim();
    return fetchAll([src]).then(function () { return cache.get(src); });
  }

  // ── 바탕색 · 강조색 ──
  function rgba(s) {
    var m = /rgba?\(([^)]+)\)/.exec(s || '');
    if (!m) return null;
    var p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
    if (p.length < 3) return null;
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }

  // 그림이 놓인 자리의 실제 바탕색 — 반투명 바탕(카드 등)은 아래 것과 섞어서 잰다
  function bgOf(node) {
    var layers = [];
    for (var n = node; n && n.nodeType === 1; n = n.parentElement) {
      var c = rgba(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) {
        layers.push(c);
        if (c[3] >= 1) break;
      }
    }
    var base = [255, 255, 255];
    if (layers.length && layers[layers.length - 1][3] >= 1) base = layers.pop().slice(0, 3);
    for (var i = layers.length - 1; i >= 0; i--) {
      var L = layers[i];
      base = base.map(function (v, k) { return L[k] * L[3] + v * (1 - L[3]); });
    }
    return 'rgb(' + base.map(Math.round).join(',') + ')';
  }

  function sync(fig) {
    var view = fig.querySelector('.wb-view');
    if (!view || !view.isConnected) return;
    view.style.setProperty('--wb-bg', bgOf(view));
    var ac = cfg.accent;
    if (ac === 'button') {
      var b = fig.querySelector('[data-wb-act]');
      ac = b ? getComputedStyle(b).backgroundColor : '';
    }
    if (ac) view.style.setProperty('--wb-accent', ac);
  }

  function syncAll(root) {
    var figs = (root || document).querySelectorAll('.wb-fig');
    Array.prototype.forEach.call(figs, sync);
  }

  // ── 그림 틀 ──
  // 같은 그림이 한 화면에 두 번 나와도 서로의 화살표 모양(marker id)을 빌려 쓰지 않게 id 를 새로 붙인다
  function freshIds(svg) {
    var m = /\sid="(wb[0-9a-f]+)"/.exec(svg);
    if (!m) return svg;
    var nid = m[1] + '-' + (++seq).toString(36) + Math.random().toString(36).slice(2, 6);
    return svg.split(m[1]).join(nid);
  }

  function figure(r) {
    var c = cfg.cls || {};
    var fig = el('div', 'wb-fig ' + (c.block || ''));
    fig.setAttribute('data-wb-kind', r.kind_ko || r.kind || '');
    if (r.title) fig.setAttribute('data-wb-title', r.title);
    fig.setAttribute('data-wb-w', r.w);
    fig.setAttribute('data-wb-h', r.h);

    var head = el('div', 'wb-head ' + (c.head || ''));
    var t = el('span', 'wb-title ' + (c.title || ''));
    t.textContent = '📐 ' + (r.kind_ko || '그림') + (r.title ? ' · ' + r.title : '');
    var acts = el('div', 'wb-acts ' + (c.acts || ''));
    [['big', '🔍 크게 보기', '새 창에서 크게'], ['svg', '💾 SVG', 'SVG 파일로 저장'],
     ['png', '📥 PNG', 'PNG 그림으로 저장 (문서·PPT 붙여넣기용)'], ['src', '📝 원문', 'Mermaid 원문 보기/닫기']
    ].forEach(function (b) {
      var btn = el('button', c.btn || '');
      btn.type = 'button';
      btn.setAttribute('data-wb-act', b[0]);
      btn.title = b[2];
      btn.textContent = b[1];
      acts.appendChild(btn);
    });
    head.appendChild(t);
    head.appendChild(acts);

    var view = el('div', 'wb-view');
    view.innerHTML = freshIds(r.svg);
    var svg = view.querySelector('svg');
    // 넓은 그림도 글자가 읽히게 — 70% 밑으로는 줄이지 않고 옆으로 밀어 보게 한다
    if (svg) svg.style.maxWidth = 'max(100%, ' + Math.round((r.w || 0) * 0.7) + 'px)';
    fig.appendChild(head);
    fig.appendChild(view);
    return fig;
  }

  function note(pre, r) {
    var n = el('div', 'wb-note');
    var sup = ['flowchart', 'sequence', 'er', 'state'].indexOf(r.kind) >= 0;
    n.textContent = sup
      ? '⚠ 그림으로 못 그렸습니다' + (r.line ? ' — ' + r.line + '째 줄' : '') + ': ' + (r.error || '')
      : 'ℹ ' + (r.error || '그림으로 그리지 않는 종류입니다');
    pre.parentNode.insertBefore(n, pre);
  }

  function place(pre, r) {
    if (pre.getAttribute('data-wb')) return false;
    if (r && r.ok && r.svg) {
      var fig = figure(r);
      pre.parentNode.insertBefore(fig, pre);
      pre.hidden = true;
      pre.setAttribute('data-wb', 'ok');
      sync(fig);
      return true;
    }
    pre.setAttribute('data-wb', 'no');
    note(pre, r || {});
    return false;
  }

  function renderIn(root) {
    root = root || document;
    if (!root.querySelectorAll) return Promise.resolve(0);
    var jobs = [];
    Array.prototype.forEach.call(root.querySelectorAll('pre > code[class~="language-mermaid" i]'), function (code) {
      var pre = code.parentNode;
      if (pre.getAttribute('data-wb') || busy.has(pre)) return;
      var src = (code.textContent || '').trim();
      if (src) jobs.push({ pre: pre, src: src });
    });
    if (!jobs.length) return Promise.resolve(0);
    jobs.forEach(function (j) { busy.add(j.pre); });
    var uniq = Array.from(new Set(jobs.map(function (j) { return j.src; })));
    return fetchAll(uniq).then(function () {
      var n = 0;
      jobs.forEach(function (j) {
        busy.delete(j.pre);
        // 기다리는 사이 다른 세션으로 옮겨 갔으면 건너뛴다 — 돌아오면 다시 그린다(캐시에서 바로)
        if (!j.pre.isConnected || !cache.has(j.src)) return;
        if (place(j.pre, cache.get(j.src))) n++;
      });
      return n;
    }, function () {
      jobs.forEach(function (j) { busy.delete(j.pre); });
      return 0;   // 서버에 못 닿으면 글을 그대로 둔다
    });
  }

  function watch(target) {
    if (!target || target.__wbWatch) return;
    var t = 0;
    var mo = new MutationObserver(function () {
      clearTimeout(t);
      t = setTimeout(function () { renderIn(target); }, 80);
    });
    mo.observe(target, { childList: true, subtree: true });
    target.__wbWatch = mo;
    renderIn(target);
  }

  // ── 내보내기: 밝은 종이 위 그림 한 장(색을 박아서 다른 프로그램에서도 같게) ──
  function paper(fig) {
    var svg = fig.querySelector('.wb-view svg');
    if (!svg) return null;
    var view = fig.querySelector('.wb-view');
    var ac = getComputedStyle(view).getPropertyValue('--wb-accent').trim() || '#4f46e5';
    var fg = '#1f2328', bg = '#ffffff';
    var c = svg.cloneNode(true);
    c.removeAttribute('style');
    var st = c.querySelector('style');
    if (st) {
      st.textContent = st.textContent
        .replace(/var\(--wb-accent,currentColor\)/g, ac)
        .replace(/var\(--wb-bg,#fff\)/g, bg)
        .replace(/var\(--wb-font,([^)]*)\)/g, '$1')
        .replace(/currentColor/g, fg);
    }
    var rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('width', '100%');
    rect.setAttribute('height', '100%');
    rect.setAttribute('fill', bg);
    c.insertBefore(rect, c.querySelector(':scope > g'));
    var w = parseFloat(fig.getAttribute('data-wb-w')) || parseFloat(c.getAttribute('width')) || 600;
    var h = parseFloat(fig.getAttribute('data-wb-h')) || parseFloat(c.getAttribute('height')) || 400;
    var title = fig.getAttribute('data-wb-title') || ('그림-' + (fig.getAttribute('data-wb-kind') || ''));
    return {
      node: c, w: w, h: h, title: title,
      name: title.replace(/[\\\/:*?"<>|\s]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60) || '그림',
      text: function () { return new XMLSerializer().serializeToString(c); }
    };
  }

  function download(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }

  function saveSvg(fig) {
    var p = paper(fig);
    if (p) download(new Blob([p.text()], { type: 'image/svg+xml;charset=utf-8' }), p.name + '.svg');
  }

  function savePng(fig) {
    var p = paper(fig);
    if (!p) return;
    var k = Math.min(2, 8000 / Math.max(p.w, p.h));
    var img = new Image();
    img.onload = function () {
      var cv = document.createElement('canvas');
      cv.width = Math.ceil(p.w * k);
      cv.height = Math.ceil(p.h * k);
      var ctx = cv.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.drawImage(img, 0, 0, cv.width, cv.height);
      cv.toBlob(function (b) { if (b) download(b, p.name + '.png'); }, 'image/png');
    };
    img.onerror = function () { saveSvg(fig); };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(p.text());
  }

  function openBig(fig) {
    var p = paper(fig);
    if (!p) return;
    p.node.setAttribute('width', Math.round(p.w * 1.4));
    p.node.setAttribute('height', Math.round(p.h * 1.4));
    var t = esc(p.title);
    var html = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>' + t + '</title>' +
      '<style>body{margin:0;background:#fff;color:#1f2328;font-family:"Malgun Gothic","맑은 고딕",sans-serif}' +
      'header{padding:10px 16px;font-size:14px;font-weight:600;border-bottom:1px solid #e5e7eb}' +
      'header small{font-weight:400;opacity:.6;margin-left:8px}' +
      'main{padding:16px;overflow:auto}svg{display:block;margin:0 auto;max-width:100%;height:auto}</style>' +
      '</head><body><header>' + t + '<small>Ctrl + 마우스 휠로 확대·축소</small></header><main>' +
      p.text() + '</main></body></html>';
    var url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }));
    var w = window.open(url, '_blank');
    if (!w) saveSvg(fig);      // 팝업이 막혔으면 파일로라도
    setTimeout(function () { URL.revokeObjectURL(url); }, 120000);
  }

  function toggleSrc(fig, btn) {
    var pre = fig.nextElementSibling;
    if (!pre || pre.tagName !== 'PRE') return;
    pre.hidden = !pre.hidden;
    btn.textContent = pre.hidden ? '📝 원문' : '📝 원문 닫기';
  }

  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('[data-wb-act]') : null;
    if (!b) return;
    var fig = b.closest('.wb-fig');
    if (!fig) return;
    e.preventDefault();
    e.stopPropagation();
    var act = b.getAttribute('data-wb-act');
    if (act === 'src') toggleSrc(fig, b);
    else if (act === 'big') openBig(fig);
    else if (act === 'svg') saveSvg(fig);
    else if (act === 'png') savePng(fig);
  }, true);

  // 테마를 바꾸면(html/body 의 class · data-theme) 글 뒤 바탕색을 다시 잰다
  function watchTheme() {
    var t = 0;
    var mo = new MutationObserver(function () {
      clearTimeout(t);
      t = setTimeout(function () { syncAll(document); }, 60);
    });
    var opt = { attributes: true, attributeFilter: ['class', 'data-theme'] };
    mo.observe(document.documentElement, opt);
    if (document.body) mo.observe(document.body, opt);
  }

  function setup(o) {
    o = o || {};
    cfg.cls = o.cls || {};
    cfg.accent = o.accent || '';
    addCss();
    syncAll(document);
  }

  addCss();
  if (document.body) watchTheme();
  else document.addEventListener('DOMContentLoaded', watchTheme);

  window.WB = { setup: setup, renderIn: renderIn, watch: watch, render: render, version: '1.0' };
})();
