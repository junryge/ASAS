/* =============================================================================
 * 브릿지_아이소.js — 동간 브릿지 화면의 **판마다 oht3d 아이소메트리를 얹는다**
 * -----------------------------------------------------------------------------
 * 2026-09-21. 고객: "아이소메트리를 각각 맞게 해주고 실행하게 해주라.
 *                    어차피 월드모델파생에 있잖아, 그걸 위에 로드하면 되잖아."
 *
 * 왜 판 '안' 이 아니라 판 '위' 인가
 *   판은 CSS 3D(rotateX·rotateZ)로 기울어 있다. 그 안에 캔버스를 넣으면 CSS 가
 *   한 번 더 기울여 **두 번 투영**된다 — 3D 로 세운 레일이 다시 눕는다.
 *   그래서 캔버스는 화면에 납작하게 두고 **판의 화면상 자리**에 맞춰 띄운다.
 *   oht3d 카메라가 직교(아이소메트리)라 이렇게 겹쳐도 각이 맞는다.
 *
 * 고객 마크업은 한 글자도 안 고친다 — 판을 자리(left/top/width/height)로 찾는다.
 * =========================================================================== */
import { createOHT3D } from '/static/js/oht3d/oht3d.js';
/* ★three 를 **정적으로** 불러 THREE 로 넘긴다. oht3d 는 안 넘기면 동적 import
   를 하는데(await import), 그게 이 페이지의 번들러 로더와 겹치는 타이밍에
   걸려 뷰어가 만들어지다 멈췄다. 정적 import 는 모듈이 돌기 전에 끝난다. */
import * as THREE from '/static/js/oht3d/three.module.min.js';

/* 붙다가 터지면 화면에 띄운다 — 조용히 실패하면 왜 안 나오는지 알 수가 없다 */
function boom(e) {
  console.error('[브릿지 아이소]', e);
  let b = document.getElementById('bridge3d-err');
  if (!b) {
    b = document.createElement('div');
    b.id = 'bridge3d-err';
    b.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:9999;max-width:60vw;'
      + 'background:#2b1416;border:1px solid #5c3034;color:#ffb4b4;border-radius:8px;'
      + 'padding:9px 12px;font:12px/1.5 ui-monospace,Consolas,monospace;white-space:pre-wrap';
    document.body.appendChild(b);
  }
  b.textContent = '[브릿지 아이소] ' + (e && e.stack || e);
}
addEventListener('error', ev => boom(ev.error || ev.message));
addEventListener('unhandledrejection', ev => boom(ev.reason));

const DATA = await (await fetch('/static/브릿지_레이아웃.json')).json();
const ISO_EL = Math.atan(1 / Math.SQRT2);   // oht3d 등각 고도 35.264°

/* 판 찾기 — 고객 마크업의 인라인 style 로 찾는다 (클래스가 없다) */
function findPlate(f) {
  for (const el of document.querySelectorAll('div[style*="translateZ"]')) {
    const s = el.style;
    if (parseFloat(s.left) === f.find.left && parseFloat(s.top) === f.find.top &&
        parseFloat(s.width) === f.find.width && parseFloat(s.height) === f.find.height)
      return el;
  }
  return null;
}

/* 판들이 그려질 때까지 기다린다 (틀이 React 라 한 박자 늦게 붙는다) */
async function waitPlates(tries = 60) {
  for (let i = 0; i < tries; i++) {
    const got = DATA.fabs.map(findPlate);
    if (got.every(Boolean)) return got;
    await new Promise(r => setTimeout(r, 120));
  }
  throw new Error('판을 못 찾았다 — 고객 마크업이 바뀌었나?');
}

const plates = await waitPlates();
/* ★무대도 틀이 다시 그린다 — 붙잡아 두면 rect 가 0 이 되고, 그러면 아래
   clip-path 가 화면 **전부**를 잘라 버린다 (아무것도 안 보였던 진짜 이유). */
let _stage = null;
function getStage() {
  if (_stage && document.contains(_stage)) return _stage;
  const p = findPlate(DATA.fabs[0]);
  return (_stage = (p && p.closest('section')) || document.body);
}

/* ★겹을 무대 **안**에 넣으면 안 된다. 이 페이지의 틀(DC/React)이 무대를 다시
   그리면서 내가 넣은 것을 지워 버린다 (캔버스만 1x1 로 남아 있었다).
   그래서 body 에 붙이고 화면 좌표(fixed)로 판을 따라간다. */
const layer = document.createElement('div');
layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:50';
document.body.appendChild(layer);

const VIEWS = [];
for (let i = 0; i < DATA.fabs.length; i++) {
  const f = DATA.fabs[i], L = DATA.layouts[f.key];
  const box = document.createElement('div');
  box.dataset.fab = f.key;
  /* ★크기를 **먼저** 준다. 0×0 으로 만들면 뷰어가 종횡비 0 인 카메라로 서서
     아무것도 안 그린다 (캔버스만 생기고 화면은 비어 있었다). */
  const r0 = plates[i].getBoundingClientRect();
  box.style.cssText = 'position:absolute;pointer-events:auto;'
    + `left:${r0.left}px;top:${r0.top}px;`
    + `width:${Math.max(120, r0.width * 1.55)}px;`
    + `height:${Math.max(80, r0.height * 1.55)}px`;
  layer.appendChild(box);

  const v = await createOHT3D(box, {
    THREE,
    coordScale: 1,             // 이미 m 로 만들어 넘긴다
    flipY: true,               // 바닥 좌표는 y 가 위로 자란다
    projection: 'iso',         // ★판이 기울어 있으니 카메라도 등각이어야 겹친다
    transparent: true,         // ★판이 비쳐야 한다 (안 그러면 네모가 덮인다)
    floor: false,              // ★바닥도 끈다 — 고객 판이 바닥이다
    dark: true,
    walls: false,              // 벽 없음 (고객 지시)
    ports: true,
    ui: false, panel: false,   // 판 위에 띄우는 것이라 뷰어 제 UI 는 끈다
    labels: false,
    /* ★판이 화면에서 200~300px 밖에 안 된다. oht3d 기본값(레일 0.2 m)은
       한 FAB 을 꽉 채워 볼 때 맞춘 값이라 여기선 한 픽셀도 안 된다. */
    railScale: 2.2, vehicleScale: 2.0, portScale: 1.2, textScale: 0.6,
    /* ★레일 높이 4.6m 를 그대로 쓰면 도면이 판 위로 붕 떠서 어긋나
       보인다. 판이 바닥이니 레일은 판에 바짝 붙인다. */
    railHeight: 1.6,
  });
  v.setLayout({ nodes: L.nodes, edges: L.edges, zones: L.zones, ports: L.ports });
  v.resize();
  v.viewAll();

  /* 차 — 보기용. 실제 대수·상태는 피드가 setVehicles 로 준다 */
  const cars = [];
  for (let k = 0; k < DATA.ncar; k++)
    cars.push({ id: f.key + k, edge: L.edges[(k * 7) % L.edges.length].id,
                ratio: Math.random(), sp: 0.05 + Math.random() * 0.05,
                state: k % 6 === 4 ? 1 : 0 });
  /* ★판을 붙잡아 두면 안 된다 — 틀이 무대를 다시 그리면 그 노드는 문서에서
     떨어져 나가고, getBoundingClientRect() 가 0x0 을 준다 (겹이 좌상단에
     40x30 으로 쭈그리고 있었다). 그래서 **쓸 때마다 다시 찾는다**. */
  VIEWS.push({ f, box, v, cars,
               plate() { return (this._p && document.contains(this._p))
                         ? this._p : (this._p = findPlate(this.f)); } });
}

/* 판이 움직이면(돌리기·확대) 겹도 따라간다 */
function place() {
  const sr = getStage().getBoundingClientRect();
  /* 무대 밖으로 삐져나가지 않게 잘라 준다 (오른쪽 패널을 덮으면 안 된다).
     ★자리를 못 잡았으면 자르지 않는다 — 잘못 자르면 통째로 사라진다. */
  layer.style.clipPath = (sr.width > 10 && sr.height > 10)
    ? `inset(${sr.top}px ${innerWidth - sr.right}px `
      + `${innerHeight - sr.bottom}px ${sr.left}px)`
    : 'none';
  for (const o of VIEWS) {
    const pe = o.plate();
    if (!pe) continue;
    const r = pe.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    /* ★판과 도면의 **각을 맞춘다**.
       판은 CSS rotateX(60°) 라 바닥이 세로로 cos60 = 0.500 만큼 눌린다.
       oht3d 등각은 고도 35.264° 라 sin35.264 = 0.577 만큼 눌린다.
       그대로 겹치면 도면이 판보다 세로로 15% 길다 — 그래서 canvas 를
       1/0.866 만큼 높게 잡고 scaleY(0.866) 으로 눌러 판에 맞춘다.
       K 는 viewAll 이 두는 여백을 되돌리는 값이다. */
    const K = 1.62, SY = Math.cos(60 * Math.PI / 180) / Math.sin(ISO_EL);
    const w = Math.max(40, r.width * K), h = Math.max(30, r.height * K / SY);
    const s = o.box.style;
    const nx = (r.left - (w - r.width) / 2) + 'px';
    const ny = (r.top - (h - r.height) / 2) + 'px';
    if (s.left !== nx || s.top !== ny || s.width !== w + 'px' || s.height !== h + 'px') {
      s.left = nx; s.top = ny; s.width = w + 'px'; s.height = h + 'px';
      s.transform = `scaleY(${SY})`;
      s.transformOrigin = 'center';
      o.v.resize();
    }
  }
}
place();
/* 자리를 잡은 뒤 한 번 더 맞춘다 — 처음엔 판이 아직 안 움직였을 수 있다 */
setTimeout(() => { for (const o of VIEWS) { o.v.resize(); o.v.viewAll(); } }, 400);
new ResizeObserver(place).observe(getStage());
addEventListener('resize', place);
setInterval(place, 120);          // 돌리기·확대는 React 상태라 값만 훑는다

/* 차 굴리기 */
setInterval(() => {
  for (const o of VIEWS) {
    for (const c of o.cars) { c.ratio += c.sp * 0.25; if (c.ratio > 1) c.ratio -= 1; }
    o.v.setVehicles(o.cars.map(c => ({
      id: c.id, edge: c.edge, ratio: c.ratio, state: c.state,
      speed_mpm: Math.round(c.sp * 1800), loaded: c.state === 1 ? 1 : 0 })));
  }
}, 250);

/* 밖에서 차를 꽂는 길 — 실제 피드를 붙일 자리
     OHTBridge3D.setVehicles('m14A', rows)   rows 는 oht3d 의 그 모양 그대로 */
globalThis.OHTBridge3D = {
  views: VIEWS,
  setVehicles(key, rows, meta) {
    const o = VIEWS.find(v => v.f.key === key);
    if (o) { o.cars.length = 0; o.v.setVehicles(rows, meta || {}); }
  },
  fabs: DATA.fabs.map(f => f.key),
};
console.log('[브릿지 아이소] 판', VIEWS.length, '장에 3D 를 얹었다');

/* 진단 — ?diag 를 붙이면 상태를 화면에 찍는다 (안 보일 때 왜인지 알려고) */
if (location.search.includes('diag')) setTimeout(() => {
  const d = document.createElement('pre');
  d.id = 'bridge3d-diag';
  d.style.cssText = 'position:fixed;right:8px;top:8px;z-index:99999;background:#0b1118;'
    + 'border:1px solid #2a3c4f;color:#8fd3ff;padding:8px;font:11px/1.5 monospace;'
    + 'max-height:90vh;overflow:auto';
  d.textContent = VIEWS.map(o => {
    const b = o.box.getBoundingClientRect(), c = o.box.querySelector('canvas');
    const pe0 = o.plate(); const p = pe0 ? pe0.getBoundingClientRect() : {width:0,height:0,left:0,top:0};
    return `${o.f.key}\n  box ${b.width|0}x${b.height|0} @${b.left|0},${b.top|0}`
      + `\n  plate ${p.width|0}x${p.height|0} @${p.left|0},${p.top|0}`
      + `\n  canvas ${c ? c.width + 'x' + c.height : '없음'}`
      + ` css ${c ? (c.clientWidth + 'x' + c.clientHeight) : '-'}`
      + `\n  inDoc ${document.body.contains(o.box)} edges ${DATA.layouts[o.f.key].edges.length}`;
  }).join('\n') + `\n판후보 ${document.querySelectorAll('div[style*="translateZ"]').length}`;
  document.body.appendChild(d);
}, 1500);
