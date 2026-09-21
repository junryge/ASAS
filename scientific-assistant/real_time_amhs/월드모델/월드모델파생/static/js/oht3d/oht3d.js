/* =============================================================================
 * oht3d.js — OHT 3D 뷰어 모듈 (ES Module, 빌드 도구/Node 불필요)
 * -----------------------------------------------------------------------------
 * 의존성: three.module.min.js (r169) — 같은 폴더에 두면 자동으로 불러옴
 *
 * 사용법
 *   import { createOHT3D } from '/static/js/oht3d/oht3d.js';
 *   const v3d = await createOHT3D(document.getElementById('oht3d'), { coordScale: 1 });
 *   v3d.setLayout({ nodes, edges, zones, ports, walls });   // 맵은 1번만
 *   v3d.setVehicles(rows, { ts: '20260916143105' });         // 재생 프레임이 바뀔 때마다
 *   v3d.on('zoneclick', e => console.log(e.id, e.stats));
 *
 * 데이터 형식 (README.md 참고)
 *   nodes : [{id, x, y}]
 *   edges : [{id, from, to, length_mm?, max_speed_mpm?, points?:[[x,y],...]}]
 *   zones : [{id, edges:[edgeId,...]}]
 *   ports : [{x, y, w?, d?, h?, rot?, kind?:'eq'|'stk', lamp?:0|1|2, scr?, foup?}]   (선택)
 *   walls : [{x0, y0, x1, y1}]                                                        (선택)
 *   rows  : [{id, edge? | from?+to?, dist_mm? | ratio?, x?+y?, speed_mpm, state,
 *             stop_sec?, loaded?, hoist?(0~1)}]
 *
 * 월드모델파생에 이식하면서 보탠 것 (원본 세트와 다른 곳)
 *   · projection: 'iso' | 'persp' — **아이소메트리(직교) 카메라**. 원본은 원근뿐이었다.
 *     직교 절두체의 반높이를 dist·tan(16°) 로 잡아, 원근용으로 짜인 시점 계산
 *     (allView·zoneView·withPanel·라벨 겹침)이 그대로 맞는다. 바 단추 '아이소/원근'.
 *   · state 4 = OBS — 2D 맵이 OBS(장애물 정지)를 JAM 과 다른 색으로 보여주는데
 *     3D 가 넷뿐이면 그 구분이 사라진다.
 *   · dark / background 옵션 — 페이지 테마(body[data-theme])를 따라간다.
 *     원본은 prefers-color-scheme 만 봤다.
 *   · setActive(false) — 숨겨진 동안 루프가 헛돌지 않게.
 *   · walls: false — 벽을 안 세운다 (고객: "벽 필요없다").
 *   · 크기 패널 (바의 '크기' 단추) — 레일 굵기 · 차량 · 설비 · 글자 배수를 그 자리에서
 *     조절한다. 3D 안에서만 쓰는 값이라 2D 설정과 섞지 않는다 (고객: "따로 가야지").
 *     ★기본 레일 굵기가 0.45 인 이유: 실물 M14A 는 평행 레일 사이가 중앙값 0.30 m
 *     (p25 0.22 m) 인데 원본 레일 판은 0.56 m 라 83% 가 겹쳐 한 덩어리로 보였다.
 * ============================================================================= */

const ST_NAME = ['운행', '적재', '정지', 'JAM', 'OBS'];
const ST_MAX = ST_NAME.length - 1;
const STATE_MAP = {
  RUN: 0, MOVE: 0, RUNNING: 0, '운행': 0, '0': 0,
  LOAD: 1, LOADED: 1, '적재': 1, '1': 1,
  STOP: 2, IDLE: 2, WAIT: 2, '정지': 2, '2': 2,
  JAM: 3, '3': 3,
  OBS: 4, OBS_BZ_STOP: 4, '4': 4,
};
// 등각: 방위 +45° · 고도 35.264°. +45° 라야 2D 와 같은 방향이다 — 카메라가 (+x,+y)
// 모서리에서 원점을 보면 화면 오른쪽이 +x, 먼 쪽이 −y(2D 의 위쪽)가 된다.
const ISO_AZ = Math.PI / 4, ISO_EL = Math.atan(1 / Math.SQRT2);
const HALF_FOV = 16 * Math.PI / 180;                                     // 원근 fov 32° 의 반

const DEFAULTS = {
  threeUrl: './three.module.min.js', // oht3d.js 기준 상대경로
  THREE: null,                       // 이미 페이지에 three 가 있으면 넘겨도 됨
  coordScale: 1,                     // 맵 좌표 → m 변환 배율 (mm 좌표면 0.001)
  flipY: false,                      // 맵 y축이 위로 증가하는 좌표계면 true
  railHeight: 4.6,
  wallHeight: 7.5,
  wallCutHeight: 1.0,
  /* 크기 기본값 — 2026-09 고객이 화면에서 맞춰 보고 정한 값이다.
     '크기' 판의 '기본값' 단추는 언제나 이 네 값으로 되돌린다(szDefault).
     ★라이브러리 기본은 sizeUI:false 다 (단추를 안 만든다). 월드모델파생
       화면은 true 로 열어 단추를 띄운다 — 판 자체는 닫힌 채로 뜬다. */
  vehicleScale: 0.40,    // 차량
  railScale: 0.20,       // 레일 굵기 — 평행 레일이 붙어 보이지 않아야 한다 (위 주석)
  portScale: 0.40,       // 설비(포트) 상자
  textScale: 0.80,       // 글자(차량 라벨·존)
  sizeUI: false,         // '크기' 단추·패널을 띄울까 (기본 안 띄움 — 값은 위로 고정)
  ports: true,           // 설비(포트)를 세울까 — '설비' 단추로 끄고 켠다
  labels: true,
  heat: true,
  ui: true,        // 뷰어 내부 버튼/범례/툴팁
  panel: true,     // 오른쪽 HID Zone 패널 (단추를 둘까)
  panelOpen: true, // 처음부터 열어 둘까 (false 면 닫힌 채로 뜬다 — 단추로 연다)
  maxTweenMs: 3000,
  jamSec: 0,       // 0 이면 state 값 그대로 사용
  /* 정체 판정 — [JAM, OBS, 멈춘 차] 각각 '몇 대 이상' 이면 정체로 볼지.
     0 은 '그 종류는 안 봄'. null 이면 예전 규칙(JAM·OBS 를 대수 무관하게).
     화면(월드모델파생)이 ⚙ 설정 값을 그대로 넘긴다 — 2D·유사3D 와 같은 기준. */
  jamMin: null,
  projection: 'persp',   // 'iso' = 아이소메트리(직교) · 'persp' = 원근
  walls: true,           // false 면 벽(외곽·layout.walls)을 아예 안 세운다
  /* 바닥 색. null 이면 실제 FAB 바닥처럼 밝은 회색(0xd6d9dc) — 기본값이다.
     다크 HMI 위에 얹는 화면(동간 브릿지)은 밝은 바닥판이 화면과 싸워서
     어두운 색을 넘긴다. ★기본을 안 바꾼다 — 기존 화면은 그대로 돈다. */
  floorColor: null,
  /* false 면 바닥판·격자를 아예 안 깐다. 다른 그림(동간 브릿지의 CSS 3D
     판) 위에 겹쳐 띄울 때 바닥이 그 판을 덮어 버린다. ★기본은 true. */
  floor: true,
  /* true 면 캔버스를 **투명**하게 쓴다 — 다른 그림 위에 겹쳐 띄울 때.
     동간 브릿지 화면이 판(CSS 3D)마다 이 뷰어를 하나씩 얹는데, 배경이
     칠해져 있으면 기운 판 위에 네모가 덮인다. ★기본은 false 다. */
  transparent: false,
  dark: null,            // true/false 로 주면 그것, null 이면 prefers-color-scheme
  colors: {
    state: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#f97316'],   // 운행·적재·정지·JAM·OBS
    background: '#5c6067',
    accent: '#1f6feb',
  },
};

export async function createOHT3D(container, options = {}) {
  const o = { ...DEFAULTS, ...options, colors: { ...DEFAULTS.colors, ...(options.colors || {}) } };
  if (o.colors.state.length < ST_NAME.length)
    o.colors.state = [...o.colors.state, ...DEFAULTS.colors.state.slice(o.colors.state.length)];
  const THREE = o.THREE || await import(new URL(o.threeUrl, import.meta.url).href);
  const v = new Viewer(THREE, container, o);
  return v.api;
}

/* -------------------------------------------------------------------------- */
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fmtDur = s => s < 60 ? `${Math.floor(s)}s` : `${Math.floor(s / 60)}m${String(Math.floor(s % 60)).padStart(2, '0')}s`;
function fmtTs(ts) {
  if (ts == null) return '';
  const s = String(ts);
  const d = s.replace(/\D/g, '');
  if (d.length >= 14) return `${d.slice(8, 10)}:${d.slice(10, 12)}:${d.slice(12, 14)}`;
  return s;
}
function polyCum(pts) {
  const c = [0];
  for (let i = 1; i < pts.length; i++) c.push(c[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  return c;
}
/* ★노드 높이(z) 를 꺾인 점마다 이어 준다 — 층이 다른 동을 잇는 브릿지는
   이 값이 기울어지면서 경사로가 된다. z 를 안 주면 전부 0 이라 예전과 같다. */
function zOnPoly(zs, cum, t) {
  if (!zs) return 0;
  let i = 1;
  while (i < cum.length - 1 && cum[i] < t) i++;
  const seg = (cum[i] - cum[i - 1]) || 1e-9;
  const a = clamp((t - cum[i - 1]) / seg, 0, 1);
  return zs[i - 1] + (zs[i] - zs[i - 1]) * a;
}
function pointOnPoly(pts, cum, t) {
  let i = 1;
  while (i < cum.length - 1 && cum[i] < t) i++;
  const seg = (cum[i] - cum[i - 1]) || 1e-9;
  const a = clamp((t - cum[i - 1]) / seg, 0, 1);
  const p = pts[i - 1], q = pts[i];
  return [p[0] + (q[0] - p[0]) * a, p[1] + (q[1] - p[1]) * a, Math.atan2(q[1] - p[1], q[0] - p[0])];
}
/* ── 정체 세기(히트맵) ────────────────────────────────────────────────
   몇 대가 몰렸나로 색과 진하기가 같이 간다 — 노랑(옅음) → 주황 → 빨강 →
   짙은 적. 20대에서 꼭대기다 (고객: "20대이상이 제일 심하게 히트맵 비전").
   ★★이 표는 **dashboard.html 의 JAM_RAMP 와 같은 값**이어야 한다. 2D·유사3D
     와 아이소메트리가 다른 색을 쓰면 같은 정체를 보고 두 사람이 다른 말을
     한다. (tests/test_jam_layer.py 가 두 파일의 숫자를 맞춰 본다.) */
const JAM_HOT_N = 20;
const JAM_RAMP = [
  [0.00, 250, 204,  21, 0.30],
  [0.45, 249, 115,  22, 0.46],
  [0.75, 239,  68,  68, 0.62],
  [1.00, 153,  27,  27, 0.78],
];
function jamHeat(cnt) {
  const n = Math.max(1, +cnt || 1);
  const t = clamp((n - 1) / (JAM_HOT_N - 1), 0, 1);
  let i = 1;
  while (i < JAM_RAMP.length - 1 && JAM_RAMP[i][0] < t) i++;
  const p = JAM_RAMP[i - 1], q = JAM_RAMP[i];
  const f = (t - p[0]) / ((q[0] - p[0]) || 1e-9);
  const v = j => p[j] + (q[j] - p[j]) * f;
  return { r: Math.round(v(1)), g: Math.round(v(2)), b: Math.round(v(3)), a: v(4), t };
}
/* 정체로 볼 상태 — 3D 상태 코드다 (0 운행 · 1 적재 · 2 정지 · 3 JAM · 4 OBS).
   차례는 화면 설정과 같다: JAM · OBS · 멈춘 차. */
const JAM_ST = [3, 4, 2];
const JAM_NAME = ['JAM', 'OBS', '멈춘 차'];

function heatRGB(level) {
  const st = [[154, 161, 169], [240, 160, 40], [226, 70, 70]];
  const t = clamp(level, 0, 1) * 2, i = Math.min(1, Math.floor(t)), f = t - i;
  const c = st[i].map((v, j) => Math.round(v + (st[i + 1][j] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

const CSS = `
.o3d-root{position:relative;overflow:hidden;font:13px/1.4 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;color:#1c2430;
  --o3d-panel:rgba(255,255,255,.94);--o3d-line:#d5dbe3;--o3d-muted:#6a7686;--o3d-chip:#f2f4f7;--o3d-hl:#e6efff}
@media (prefers-color-scheme:dark){.o3d-root:not(.o3d-light){color:#e3e8ee;--o3d-panel:rgba(23,29,37,.93);--o3d-line:#2a333f;--o3d-muted:#8a96a6;--o3d-chip:#1f2630;--o3d-hl:#1c2a44}}
.o3d-root.o3d-dark{color:#e3e8ee;--o3d-panel:rgba(23,29,37,.93);--o3d-line:#2a333f;--o3d-muted:#8a96a6;--o3d-chip:#1f2630;--o3d-hl:#1c2a44}
.o3d-root canvas.o3d-cv{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:grab}
.o3d-bar{position:absolute;left:8px;top:8px;right:8px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;pointer-events:none;z-index:2}
.o3d-bar>*{pointer-events:auto}
.o3d-ts{font:700 16px ui-monospace,Consolas,monospace;color:var(--o3d-acc);background:var(--o3d-panel);border:1px solid var(--o3d-line);border-radius:6px;padding:2px 8px;margin-right:4px}
.o3d-ts:empty{display:none}
.o3d-btn{border:1px solid var(--o3d-line);background:var(--o3d-panel);color:inherit;border-radius:6px;padding:2px 8px;cursor:pointer;font:inherit;white-space:nowrap}
.o3d-btn:hover{border-color:var(--o3d-acc)}
.o3d-btn.on{background:var(--o3d-acc);border-color:var(--o3d-acc);color:#fff}
.o3d-btn[hidden]{display:none}
.o3d-size{position:absolute;left:8px;top:44px;z-index:3;background:var(--o3d-panel);border:1px solid var(--o3d-line);
  border-radius:8px;padding:8px 10px;display:none;box-shadow:0 6px 20px rgba(0,0,0,.18)}
.o3d-size.on{display:block}
.o3d-size h5{margin:0 0 6px;font-size:12px;font-weight:700}
.o3d-size label{display:flex;align-items:center;gap:6px;margin:5px 0;font-size:12px;white-space:nowrap}
.o3d-size label>span:first-child{width:62px;color:var(--o3d-muted)}
.o3d-size input[type=range]{width:120px}
.o3d-size b{width:34px;text-align:right;font-variant-numeric:tabular-nums}
.o3d-size .o3d-btn{margin-top:6px;width:100%}
.o3d-panel{position:absolute;right:8px;top:44px;bottom:8px;width:330px;display:flex;flex-direction:column;gap:6px;z-index:2;pointer-events:none}
.o3d-panel[hidden]{display:none}
.o3d-card{background:var(--o3d-panel);border:1px solid var(--o3d-line);border-radius:8px;display:flex;flex-direction:column;min-height:0;overflow:hidden;pointer-events:auto}
.o3d-card[hidden]{display:none}
.o3d-zc{flex:0 1 auto;max-height:45%}
.o3d-dc{flex:1 1 auto}
.o3d-h{padding:5px 9px;border-bottom:1px solid var(--o3d-line);display:flex;justify-content:space-between;align-items:center;font-weight:700}
.o3d-sc{overflow:auto;min-height:0}
.o3d-root table{border-collapse:collapse;width:100%;font-size:12px}
.o3d-root th,.o3d-root td{padding:3px 6px;text-align:right;border-bottom:1px solid var(--o3d-line);white-space:nowrap;font-variant-numeric:tabular-nums}
.o3d-root th{position:sticky;top:0;background:var(--o3d-panel);color:var(--o3d-muted);font-weight:600}
.o3d-root th:first-child,.o3d-root td:first-child{text-align:left}
.o3d-root tbody tr{cursor:pointer}
.o3d-root tbody tr:hover,.o3d-root tr.sel{background:var(--o3d-hl)}
.o3d-root td.jam{color:#ef4444;font-weight:700}
.o3d-st{display:flex;flex-wrap:wrap;gap:4px;padding:5px 9px;border-bottom:1px solid var(--o3d-line)}
.o3d-chip{background:var(--o3d-chip);border-radius:9px;padding:0 6px;font-size:11.5px;white-space:nowrap}
.o3d-chip.jam{background:#ef4444;color:#fff;font-weight:700}
.o3d-stc{display:inline-block;padding:0 5px;border-radius:7px;color:#fff;font-size:10.5px;font-weight:600}
.o3d-leg{position:absolute;left:8px;bottom:8px;z-index:2;display:flex;gap:9px;flex-wrap:wrap;font-size:11.5px;background:var(--o3d-panel);
  border:1px solid var(--o3d-line);border-radius:6px;padding:3px 8px;pointer-events:none}
.o3d-dot{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:3px;vertical-align:-1px}
.o3d-hb{display:inline-block;width:50px;height:8px;border-radius:4px;margin:0 4px;background:linear-gradient(90deg,#9aa1a9,#f0a028,#e24646)}
.o3d-tip{position:absolute;z-index:5;pointer-events:none;background:var(--o3d-panel);border:1px solid var(--o3d-line);border-radius:6px;
  padding:5px 8px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.25);display:none;white-space:nowrap}
.o3d-tip .k{color:var(--o3d-muted);display:inline-block;min-width:50px}
@media (max-width:700px){.o3d-panel{left:8px;width:auto;top:auto;height:42%}}
`;

/* ========================================================================== */
class Viewer {
  constructor(T, root, o) {
    this.T = T; this.o = o; this.root = root;
    this.handlers = new Map();
    this.G = null;
    this.slots = []; this.idx = new Map(); this.cap = 0; this.lastSet = 0; this.ts = null;
    this.stats = null;
    this.orb = { tx: 0, ty: 1.5, tz: 0, az: -2.3, el: 0.8, dist: 60 };
    if (o.projection === 'iso') { this.orb.az = ISO_AZ; this.orb.el = ISO_EL; }
    this.fly = null;
    this.opt = { labels: o.labels, heat: o.heat, vs: o.vehicleScale, proj: o.projection === 'iso' ? 'iso' : 'persp',
                 rs: +o.railScale || DEFAULTS.railScale, ps: +o.portScale || DEFAULTS.portScale,
                 ts: +o.textScale || DEFAULTS.textScale, ports: o.ports !== false };
    this.sel = -1; this.hover = -1; this.tracked = -1; this.follow = false;
    this.needRender = true; this.camDirty = true; this.vehDirty = true; this.resized = true; this.domDirty = true;
    this.mouse = null; this.lastDom = 0;
    this.active = true;
    this.labelPool = new Map(); this.zoneLabels = []; this.map = [];
    this.sprites = new Set();   // 만든 스프라이트 전부 — 직교에서 크기를 다시 잡으려고
    this.chainCache = new Map();
    this._setupDom();
    this._setup3D();
    this._bind();
    this._loop = this._loop.bind(this);
    this.raf = requestAnimationFrame(this._loop);
    const self = this;
    this.api = {
      setLayout: l => self.setLayout(l),
      setVehicles: (rows, meta) => self.setVehicles(rows, meta),
      clearVehicles: () => self.setVehicles([], {}),
      focusZone: (z, fly = true) => self.selectZone(typeof z === 'number' ? z : self.zoneIndex(z), fly),
      focusVehicle: id => self.focusVehicle(self.idx.get(String(id)) ?? -1),
      focusHotspot: () => self.G && self.flyTo(self.withPanel(self.hotView(self.sel))),
      viewAll: () => self.G && self.flyTo(self.allView()),
      setOptions: p => self.setOptions(p),
      setActive: on => { self.active = !!on; if (self.active) { self.resized = true; self.camDirty = true; self.needRender = true; } },
      getZoneStats: () => self.zoneStatsList(),
      snapshotPNG: name => self.snapshot(name),
      on: (ev, fn) => { if (!self.handlers.has(ev)) self.handlers.set(ev, new Set()); self.handlers.get(ev).add(fn); },
      off: (ev, fn) => self.handlers.get(ev)?.delete(fn),
      resize: () => { self.resized = true; },
      dispose: () => self.dispose(),
      get THREE() { return self.T; },
    };
  }
  emit(ev, data) { this.handlers.get(ev)?.forEach(fn => { try { fn(data); } catch (e) { console.error(e); } }); }

  /* ---------------- DOM ---------------- */
  _setupDom() {
    const o = this.o, r = this.root;
    if (!document.getElementById('o3d-style')) {
      const st = document.createElement('style');
      st.id = 'o3d-style';
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    r.classList.add('o3d-root');
    this.applyTheme();
    r.style.setProperty('--o3d-acc', o.colors.accent);
    if (getComputedStyle(r).position === 'static') r.style.position = 'relative';
    this.cv = document.createElement('canvas');
    this.cv.className = 'o3d-cv';
    r.appendChild(this.cv);
    this.tip = document.createElement('div');
    this.tip.className = 'o3d-tip';
    r.appendChild(this.tip);
    this.dom = {};
    if (!o.ui) return;
    const sc = o.colors.state;
    const bar = document.createElement('div');
    bar.className = 'o3d-bar';
    bar.innerHTML = `<span class="o3d-ts"></span>
      <button class="o3d-btn" data-a="hot" title="JAM이 가장 몰린 곳으로 근접">정체 지점</button>
      <button class="o3d-btn" data-a="all">전체</button>
      <button class="o3d-btn" data-a="follow" hidden>따라가기</button>
      <button class="o3d-btn" data-a="proj" title="아이소메트리(직교) / 원근 전환">${o.projection === 'iso' ? '원근으로' : '아이소로'}</button>
      <button class="o3d-btn ${o.labels ? 'on' : ''}" data-a="labels">ID·속도</button>
      <button class="o3d-btn ${o.heat ? 'on' : ''}" data-a="heat">히트맵</button>
      ${o.sizeUI ? '<button class="o3d-btn" data-a="size" title="레일 굵기·차량·설비·글자 크기">크기</button>' : ''}
      <button class="o3d-btn" data-a="png">이미지 저장</button>
      <button class="o3d-btn ${o.ports === false ? '' : 'on'}" data-a="ports"
        title="설비(포트) — 바닥에 선 회색 상자 · 기둥 · 초록 상태등. 끄면 레일과 차량만 남는다">설비</button>
      ${o.panel ? `<button class="o3d-btn ${o.panelOpen === false ? '' : 'on'}" data-a="panel">패널</button>` : ''}`;
    r.appendChild(bar);
    const leg = document.createElement('div');
    leg.className = 'o3d-leg';
    leg.innerHTML = ST_NAME.map((n, i) => `<span><i class="o3d-dot" style="background:${sc[i]}"></i>${n}</span>`).join('') +
      '<span>레일 원활<i class="o3d-hb"></i>정체</span>';
    r.appendChild(leg);
    // 크기 판 — 3D 안에서만 쓰는 값이라 2D 설정과 섞지 않는다 (고객: "따로 가야지")
    // ★sizeUI 일 때만 만든다. 만들어도 처음엔 닫혀 있다('크기' 단추로 연다)
    //   — 열어 둔 채로 뜨면 맵을 가린다.
    if (o.sizeUI) this._buildSizePanel(r, o);
    this.dom.bar = bar;
    this.dom.ts = bar.querySelector('.o3d-ts');
    this._wireBar(bar);
    if (!o.panel) return;
    this._buildPanel(r, bar);
  }

  _buildSizePanel(r, o) {
    const SZ = [['rs', '레일 굵기', 0.1, 1.5, 0.05], ['vs', '차량', 0.2, 4, 0.1],
                ['ps', '설비', 0.2, 3, 0.1], ['ts', '글자', 0.4, 2.5, 0.1]];
    const sz = document.createElement('div');
    sz.className = 'o3d-size';
    sz.innerHTML = '<h5>크기</h5>' + SZ.map(([k, nm, lo, hi, st]) =>
      `<label><span>${nm}</span><input type="range" data-s="${k}" min="${lo}" max="${hi}" step="${st}" value="${this.opt[k]}"><b data-v="${k}">${(+this.opt[k]).toFixed(2)}</b></label>`).join('')
      + '<button class="o3d-btn" data-s="reset">기본값</button>';
    r.appendChild(sz);
    this.dom.size = sz;
    /* ★'기본값' 단추가 돌아갈 자리는 **DEFAULTS** 다. 화면이 저장해 둔 값으로
       열리면 o.railScale 등이 곧 그 저장값이라, 그걸 기준으로 잡으면 되돌릴
       곳이 없어진다 — 누른 자리에 그대로 머문다. */
    this.szDefault = { rs: DEFAULTS.railScale, vs: DEFAULTS.vehicleScale,
                       ps: DEFAULTS.portScale, ts: DEFAULTS.textScale };
    const SKEY = { rs: 'railScale', vs: 'vehicleScale', ps: 'portScale', ts: 'textScale' };
    sz.addEventListener('input', ev => {
      const k = ev.target.dataset.s;
      if (k && k !== 'reset') this.setOptions({ [SKEY[k]]: +ev.target.value });
    });
    sz.querySelector('[data-s=reset]').addEventListener('click', () =>
      this.setOptions(Object.fromEntries(Object.entries(this.szDefault).map(([k, v]) => [SKEY[k], v]))));
  }

  _wireBar(bar) {
    bar.addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b || !this.G) return;
      const a = b.dataset.a;
      if (a === 'hot') {
        const v = this.hotView(this.sel);      // 여기서 this.hotAt 이 정해진다
        const on = this.markHot();             // 붉게 뿌옇게 — 정체가 있을 때만
        b.classList.toggle('on', on);
        this.flyTo(this.withPanel(v));
      }
      // '전체' 는 보기를 되돌리는 단추다 — 표시도 같이 지운다
      if (a === 'all') { this.selectZone(-1, false); this.clearHot();
                         bar.querySelector('[data-a=hot]')?.classList.remove('on');
                         this.flyTo(this.allView()); }
      if (a === 'proj') this.setOptions({ projection: this.opt.proj === 'iso' ? 'persp' : 'iso' });
      if (a === 'labels') this.setOptions({ labels: !this.opt.labels });
      if (a === 'heat') this.setOptions({ heat: !this.opt.heat });
      if (a === 'size' && this.dom.size) { const z = this.dom.size; z.classList.toggle('on'); b.classList.toggle('on', z.classList.contains('on')); }
      // 설비 — 바닥에 선 회색 상자 + 기둥 + 상태등 (고객이 사진으로 짚은 그것)
      if (a === 'ports') { this.setOptions({ ports: !(this.opt.ports !== false) }); }
      if (a === 'png') this.snapshot();
      if (a === 'follow') { this.follow = !this.follow; b.classList.toggle('on', this.follow); if (this.follow && this.orb.dist > 40) this.flyTo({ dist: 20 }); }
      if (a === 'panel') { const p = this.dom.panel; p.hidden = !p.hidden; b.classList.toggle('on', !p.hidden); }
    });
  }

  _buildPanel(r, bar) {
    const o = this.o;
    const p = document.createElement('div');
    p.className = 'o3d-panel';
    p.innerHTML = `<div class="o3d-card o3d-zc"><div class="o3d-h">HID Zone</div><div class="o3d-sc"><table>
        <thead><tr><th>HID Zone</th><th>대수</th><th>정지</th><th>JAM</th><th>평균</th><th>최대정체</th></tr></thead><tbody class="o3d-ztb"></tbody></table></div></div>
      <div class="o3d-card o3d-dc" hidden><div class="o3d-h"><span class="o3d-dt"></span><button class="o3d-btn" data-x="1">✕</button></div>
        <div class="o3d-st"></div><div class="o3d-sc"><table>
        <thead><tr><th>OHT</th><th>상태</th><th>m/min</th><th>정체</th><th>FOUP</th></tr></thead><tbody class="o3d-vtb"></tbody></table></div></div>`;
    r.appendChild(p);
    Object.assign(this.dom, { panel: p, ztb: p.querySelector('.o3d-ztb'), vtb: p.querySelector('.o3d-vtb'), dc: p.querySelector('.o3d-dc'),
      dt: p.querySelector('.o3d-dt'), st: p.querySelector('.o3d-st') });
    // ★처음엔 닫아 둔다(panelOpen:false). 단추는 그대로라 언제든 열 수 있다.
    //   좁은 화면(≤700px)에서도 닫는다 — 맵을 다 가린다.
    if (o.panelOpen === false || r.clientWidth <= 700) {
      p.hidden = true;
      bar.querySelector('[data-a=panel]')?.classList.remove('on');
    }
    this.dom.ztb.addEventListener('click', ev => { const tr = ev.target.closest('tr'); if (tr) this.selectZone(+tr.dataset.z); });
    this.dom.vtb.addEventListener('click', ev => { const tr = ev.target.closest('tr'); if (tr) this.focusVehicle(+tr.dataset.k); });
    p.querySelector('[data-x]').addEventListener('click', () => this.selectZone(-1, false));
  }

  /* ---------------- Three 기본 ---------------- */
  _setup3D() {
    const T = this.T;
    const r = new T.WebGLRenderer({ canvas: this.cv, antialias: true,
      alpha: !!this.o.transparent, preserveDrawingBuffer: false });
    if (this.o.transparent) r.setClearAlpha(0);
    r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    r.shadowMap.enabled = true;
    r.shadowMap.type = T.PCFSoftShadowMap;
    r.toneMapping = T.NeutralToneMapping;
    const scene = new T.Scene();
    scene.background = this.o.transparent ? null
                     : new T.Color(this.o.colors.background);
    const camP = new T.PerspectiveCamera(32, 1, 0.3, 8000);
    // 아이소메트리 — 직교 카메라. 절두체는 applyCam 이 dist 로 매번 다시 잡는다.
    const camO = new T.OrthographicCamera(-1, 1, 1, -1, -4000, 8000);
    const cam = this.opt.proj === 'iso' ? camO : camP;
    const hemi = new T.HemisphereLight(0xffffff, 0x8c9299, 1.9);
    const dir = new T.DirectionalLight(0xfffaf2, 2.7);
    dir.castShadow = true;
    dir.shadow.mapSize.set(2048, 2048);
    dir.shadow.bias = -0.0004;
    dir.shadow.normalBias = 0.03;
    const fill = new T.DirectionalLight(0xdfe8ff, 0.7);
    fill.position.set(60, 40, -80);
    scene.add(hemi, dir, dir.target, fill);
    const world = new T.Group();
    scene.add(world);
    Object.assign(this, { r, scene, cam, camP, camO, dir, world, ray: new T.Raycaster() });
    this._b = new T.Matrix4(); this._l = new T.Matrix4(); this._m = new T.Matrix4();
    this._p = new T.Vector3(); this._q = new T.Quaternion(); this._s = new T.Vector3(); this._q0 = new T.Quaternion();
    this._up = new T.Vector3(0, 1, 0); this._c = new T.Color(); this._v = new T.Vector3();
    this.stC = this.o.colors.state.map(c => new T.Color(c));
    this.ro = new ResizeObserver(() => { this.resized = true; });
    this.ro.observe(this.root);
  }
  base(x, y, z, yaw, s = 1) { this._q.setFromAxisAngle(this._up, yaw); this._p.set(x, y, z); this._s.set(s, s, s); this._b.compose(this._p, this._q, this._s); }
  local(ox, oy, oz, sx, sy, sz) { this._p.set(ox, oy, oz); this._s.set(sx, sy, sz); this._l.compose(this._p, this._q0, this._s); this._m.multiplyMatrices(this._b, this._l); }
  put(mesh, color) {
    const i = mesh.count++;
    mesh.setMatrixAt(i, this._m);
    if (color != null) mesh.setColorAt(i, color.isColor ? color : this._c.set(color));
    return i;
  }
  IM(geo, mat, cap, o = {}) {
    const m = new this.T.InstancedMesh(geo, mat, Math.max(1, cap));
    m.count = 0;
    m.castShadow = o.cast !== false;
    m.receiveShadow = !!o.recv;
    if (o.dynamic) m.frustumCulled = false;
    (o.parent || this.world).add(m);
    return m;
  }
  fin(m) {
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    m.boundingSphere = null;
  }
  mat(color, o = {}) { return new this.T.MeshStandardMaterial({ color, roughness: o.r ?? 0.6, metalness: o.m ?? 0.05 }); }
  rbox(rr = 0.07, bs = 0.045, bt = 0.045) {
    const T = this.T, a = 0.5 - bs, s = new T.Shape();
    s.moveTo(-a + rr, -a); s.lineTo(a - rr, -a); s.quadraticCurveTo(a, -a, a, -a + rr);
    s.lineTo(a, a - rr); s.quadraticCurveTo(a, a, a - rr, a); s.lineTo(-a + rr, a);
    s.quadraticCurveTo(-a, a, -a, a - rr); s.lineTo(-a, -a + rr); s.quadraticCurveTo(-a, -a, -a + rr, -a);
    const g = new T.ExtrudeGeometry(s, { depth: 1 - 2 * bt, bevelEnabled: true, bevelSize: bs, bevelThickness: bt, bevelSegments: 2, curveSegments: 3 });
    g.translate(0, 0, -(1 - 2 * bt) / 2);
    g.rotateX(-Math.PI / 2);
    return g;
  }
  disposeGroup(g) {
    g.traverse(x => {
      if (x.geometry) x.geometry.dispose();
      if (x.material) (Array.isArray(x.material) ? x.material : [x.material]).forEach(m => { m.map?.dispose(); m.dispose(); });
    });
    g.clear();
  }
  sprite(w, h, sx, sy) {
    const T = this.T, cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    const tex = new T.CanvasTexture(cv);
    tex.colorSpace = T.SRGBColorSpace;
    tex.minFilter = T.LinearFilter;
    const sp = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false, sizeAttenuation: false, transparent: true, toneMapped: false }));
    sp.center.set(0.5, 0);
    sp.renderOrder = 10;
    sp.scale.set(sx, sy, 1);
    const L = { cv, tex, sp, txt: '', bs: [sx, sy] };
    this.sprites.add(L);
    this.fitSprite(L);
    return L;
  }
  dark() { return this.o.dark != null ? !!this.o.dark : matchMedia('(prefers-color-scheme: dark)').matches; }
  /* 스프라이트 화면 크기 — 원근: 기본 scale(NDC) 그대로 · 직교: × dist
     (원근에서 -z 를 곱해 주던 것을 손으로 한다. 반높이 = dist·tan(16°) 이므로 배율은 dist). */
  fitSprite(L) {
    const k = (this.cam && this.cam.isOrthographicCamera ? this.orb.dist : 1) * (this.opt.ts || 1);
    L.sp.scale.set(L.bs[0] * k, L.bs[1] * k, 1);
  }
  fitSprites() { for (const L of this.sprites) if (L.sp.parent) this.fitSprite(L); }
  /* 정체 지점 표시 — 붉고 뿌옇게 (고객: "빨간색 뿌옇게 보기 편하게")
     ★가운데가 진하고 가장자리로 흐려지는 원을 바닥에 깔고, 그 위에 옅은 붉은
       반구를 씌운다. 테두리가 또렷한 원을 그리면 '구역' 처럼 보여 존 바닥판과
       헷갈린다 — 그래서 경계를 흐린다.
     ★깊이 쓰기를 끈다(depthWrite:false). 안 그러면 레일·설비가 이 반투명
       덩어리에 가려 사라진다. */
  /* ★무늬는 **흰색**으로 굽는다 — 색은 재료(material.color)에서 입힌다.
     대수마다 색과 진하기가 달라야 하는데, 붉은색을 무늬에 구워 버리면
     무리 하나 바뀔 때마다 캔버스를 다시 그려야 한다(느리고, 텍스처가 쌓인다). */
  _hotTex() {
    if (this._hotT) return this._hotT;
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const g = c.getContext('2d').createRadialGradient(128, 128, 0, 128, 128, 128);
    g.addColorStop(0.00, 'rgba(255,255,255,1.00)');
    g.addColorStop(0.35, 'rgba(255,255,255,0.53)');
    g.addColorStop(0.70, 'rgba(255,255,255,0.19)');
    g.addColorStop(1.00, 'rgba(255,255,255,0.00)');
    const cx = c.getContext('2d');
    cx.fillStyle = g;
    cx.fillRect(0, 0, 256, 256);
    const t = new this.T.CanvasTexture(c);
    t.colorSpace = this.T.SRGBColorSpace;
    this._hotT = t;
    return t;
  }

  buildHotMark() {
    const T = this.T, g = new T.Group();
    g.visible = false;
    const R = 26;                                  // 바닥 무리 지름(m) — 멀리서도 눈에 든다
    const disc = new T.Mesh(new T.PlaneGeometry(R, R),
      new T.MeshBasicMaterial({ map: this._hotTex(), transparent: true,
                                depthWrite: false, toneMapped: false }));
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = 0.06;                        // 존 바닥판(0.02)·격자(0.005) 위
    disc.renderOrder = 3;
    g.add(disc);
    this.hotDisc = disc;        // 대수마다 색·진하기를 바꾼다 (markHot)
    // 옅은 반구 — 위에서 봐도, 옆에서 봐도 '그 자리' 가 보이게
    const dome = new T.Mesh(new T.SphereGeometry(R * 0.30, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2),
      new T.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.10,
                                depthWrite: false, toneMapped: false }));
    dome.position.y = 0.07;
    dome.renderOrder = 3;
    g.add(dome);
    this.hotDome = dome;
    /* 이름표 — 어느 HID 구역인지 (고객: "어디 HID인지 위에 표시해줘; 구역을").
       붉은 얼룩만 있으면 '저기가 어디냐' 를 다시 물어야 한다. 존 라벨과 같은
       스프라이트 틀을 쓴다 — 줌에 따라 화면 크기가 일정하다. */
    const L = this.sprite(512, 110, 0.19, 0.041);
    L.sp.position.set(0, this.o.wallHeight + 4, 0);
    g.add(L.sp);
    this.hotLabel = L;
    this.world.add(g);
    this.hotMark = g;
  }

  /* 정체 지점에 표시를 놓는다. 정체가 없으면(hotAt 없음) 지운다. */
  markHot() {
    if (!this.hotMark) this.buildHotMark();
    const h = this.hotAt;
    if (!h) { this.clearHot(); return false; }
    this.hotMark.position.set(h[0] - this.cx, 0, h[1] - this.cy);
    this.hotMark.visible = true;
    /* 대수대로 색과 진하기 — 2D·유사3D 와 같은 눈금(JAM_RAMP)이다.
       고객: "대수마다 뿌연도 다르게 해야되...20대이상이 제일 심하게". */
    const hc = jamHeat(h[2]);
    const col = (hc.r << 16) | (hc.g << 8) | hc.b;
    if (this.hotDisc) { this.hotDisc.material.color.setHex(col); this.hotDisc.material.opacity = hc.a; }
    if (this.hotDome) { this.hotDome.material.color.setHex(col); this.hotDome.material.opacity = 0.06 + 0.12 * hc.t; }
    this.drawHotLabel(h[3], h[2], h[4]);
    this.needRender = true;
    return true;
  }

  /* 이름표 그리기 — 'HID-B19-1(026)' 같은 존 이름 + 몇 대인지.
     ★구역을 모르면(레인에 안 걸린 자리) 그렇게 적는다. 빈 이름표를 띄우거나
       엉뚱한 구역을 적으면 그게 더 나쁘다.
     ★종류가 섞였으면 무엇이 몇 대인지 적는다 (JAM 4 · OBS 2) — 2D 와 같은 표기.
       'JAM 몇 대' 와 '멈춘 차 몇 대' 는 봐야 할 것이 다르다. */
  drawHotLabel(zi, n, kinds) {
    const L = this.hotLabel;
    if (!L) return;
    const z = (zi != null && zi >= 0 && this.G) ? this.G.zones[zi] : null;
    const name = z ? String(z.id) : '구역 밖';
    const kk = Array.isArray(kinds)
      ? kinds.map((v, i) => v ? `${JAM_NAME[i]} ${v}` : '').filter(Boolean) : [];
    const num = kk.length > 1 ? kk.join(' · ') : `정체 ${n}대`;
    const txt = `${name}|${num}|${this.dark()}`;
    if (txt === L.txt) return;
    L.txt = txt;
    const g = L.cv.getContext('2d'), dark = this.dark();
    const bg = dark ? 'rgba(23,29,37,.94)' : 'rgba(255,255,255,.96)';
    g.clearRect(0, 0, 512, 110);
    g.fillStyle = bg; roundRect(g, 3, 3, 506, 84, 14); g.fill();
    g.strokeStyle = '#ef4444'; g.lineWidth = 5; g.stroke();
    g.beginPath(); g.moveTo(240, 86); g.lineTo(256, 108); g.lineTo(272, 86); g.closePath();
    g.fillStyle = bg; g.fill();
    g.textBaseline = 'middle';
    g.fillStyle = dark ? '#e3e8ee' : '#1c2430';
    g.font = '700 30px system-ui,"Malgun Gothic",sans-serif';
    g.fillText(name, 20, 30);
    g.font = '700 28px system-ui,"Malgun Gothic",sans-serif';
    const t = num, tw = g.measureText(t).width;
    g.fillStyle = '#ef4444'; roundRect(g, 490 - tw - 20, 14, tw + 20, 36, 10); g.fill();
    g.fillStyle = '#fff'; g.fillText(t, 490 - tw - 10, 33);
    L.tex.needsUpdate = true;
  }

  clearHot() {
    if (this.hotMark) this.hotMark.visible = false;
    if (this.hotLabel) this.hotLabel.txt = '';   // 다음에 켤 때 다시 그리게
    this.needRender = true;
  }

  /* 설비(포트) 보이기/숨기기 — 다시 세우지 않고 visible 만 바꾼다 (즉시 바뀐다).
     ★설비 = 바닥에 선 회색 상자 + 앞면 + 뚜껑 + 로드포트 + 기둥 + 초록 상태등.
       한 묶음(portGroup)에 들어 있어 이 한 줄로 같이 사라졌다 다시 나온다. */
  applyPorts() {
    if (this.portGroup) this.portGroup.visible = this.opt.ports !== false;
  }
  applyTheme() {
    this.root.classList.toggle('o3d-dark', this.o.dark === true);
    this.root.classList.toggle('o3d-light', this.o.dark === false);
  }

  /* ---------------- 레이아웃 ---------------- */
  setLayout(L) {
    if (!L || !Array.isArray(L.nodes) || !Array.isArray(L.edges)) throw new Error('setLayout: nodes / edges 배열 필요');
    const sc = this.o.coordScale, fy = this.o.flipY ? -1 : 1;
    const P = (x, y) => [+x * sc, +y * sc * fy];
    /* z = 그 노드가 선 높이(m). 동마다 층이 다르면 여기로 준다. 없으면 0. */
    const nodes = L.nodes.map(n => { const [x, y] = P(n.x, n.y);
      return { id: String(n.id), x, y, z: +n.z || 0, in: [], out: [] }; });
    const nIdx = new Map(nodes.map((n, i) => [n.id, i]));
    const edges = [];
    for (const e of L.edges) {
      const a = nIdx.get(String(e.from)), b = nIdx.get(String(e.to));
      if (a == null || b == null) { console.warn('[oht3d] edge 노드 없음', e); continue; }
      const pts = Array.isArray(e.points) && e.points.length >= 2 ? e.points.map(p => P(p[0], p[1]))
        : [[nodes[a].x, nodes[a].y], [nodes[b].x, nodes[b].y]];
      const cum = polyCum(pts), glen = cum[cum.length - 1];
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const [x, y] of pts) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
      /* 꺾인 점마다의 높이 — 두 끝 노드 사이를 길이 비로 나눈다 */
      const za = nodes[a].z, zb = nodes[b].z;
      const zs = (za || zb)
        ? cum.map(c => za + (zb - za) * (glen > 0 ? c / glen : 0))
        : null;
      const i = edges.length;
      edges.push({ i, id: String(e.id ?? `${e.from}-${e.to}`), from: a, to: b, pts, cum, zs, glen,
        len: e.length_mm != null ? e.length_mm / 1000 : glen, vmax: (+e.max_speed_mpm || 300) / 60, zone: -1, bb: [x0, y0, x1, y1] });
      nodes[a].out.push(i);
      nodes[b].in.push(i);
    }
    const eIdx = new Map(edges.map(e => [e.id, e.i]));
    const ftIdx = new Map(edges.map(e => [nodes[e.from].id + '>' + nodes[e.to].id, e.i]));
    const zones = [];
    for (const z of L.zones || []) {
      const zi = zones.length;
      let bb = [Infinity, Infinity, -Infinity, -Infinity], cnt = 0, zsum = 0;
      for (const id of z.edges || []) {
        const ei = eIdx.get(String(id));
        if (ei == null) continue;
        const e = edges[ei];
        e.zone = zi; cnt++;
        zsum += (nodes[e.from].z + nodes[e.to].z) / 2;     // ★그 존이 선 높이
        bb = [Math.min(bb[0], e.bb[0]), Math.min(bb[1], e.bb[1]), Math.max(bb[2], e.bb[2]), Math.max(bb[3], e.bb[3])];
      }
      const zz0 = z.z != null ? +z.z : (cnt ? zsum / cnt : 0);
      const pad = 1;
      zones.push({ id: String(z.id), z: zz0,      // ★그 존(동)이 선 높이
        bb: cnt ? [bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad] : null });
    }
    let b = [Infinity, Infinity, -Infinity, -Infinity];
    for (const e of edges) b = [Math.min(b[0], e.bb[0]), Math.min(b[1], e.bb[1]), Math.max(b[2], e.bb[2]), Math.max(b[3], e.bb[3])];
    const ports = (L.ports || []).map(p => {
      const [x, y] = P(p.x, p.y);
      return { ...p, x, y, z: +p.z || 0, w: +p.w || 3, d: +p.d || 4,
               h: +p.h || 2.4, rot: (+p.rot || 0) * fy, kind: p.kind || 'eq' };
    });
    const walls = (L.walls || []).map(w => { const [x0, y0] = P(w.x0, w.y0), [x1, y1] = P(w.x1, w.y1); return { x0, y0, x1, y1 }; });
    for (const w of walls) b = [Math.min(b[0], w.x0, w.x1), Math.min(b[1], w.y0, w.y1), Math.max(b[2], w.x0, w.x1), Math.max(b[3], w.y0, w.y1)];
    this.G = { nodes, edges, zones, ports, walls, bounds: b, eIdx, ftIdx };
    this.sprites.clear();
    this.zoneMeshes = null;
    this.hotMark = null;            // world 를 비우면 같이 날아간다 — 다시 만들게
    this.hotLabel = null;
    this.chainCache.clear();
    this.slots = []; this.idx.clear(); this.cap = 0;
    this.sel = -1; this.hover = -1; this.tracked = -1; this.follow = false;
    this.stats = this.emptyStats();
    this.buildStatic();
    this.buildVehicleMeshes(64);
    this.resizeNow();
    Object.assign(this.orb, this.allView());
    this.camDirty = true; this.vehDirty = true; this.domDirty = true;
  }
  zoneIndex(id) { return this.G ? this.G.zones.findIndex(z => z.id === String(id)) : -1; }
  emptyStats() {
    return { zs: this.G.zones.map(() => ({ n: 0, c: [0, 0, 0, 0, 0], vs: 0, mx: 0 })), ec: new Uint16Array(this.G.edges.length), ev: new Float32Array(this.G.edges.length) };
  }

  buildStatic() {
    const T = this.T, G = this.G, W0 = this.world;
    this.disposeGroup(W0);
    this.labelPool.clear();
    const MG = 8, b = G.bounds;
    const ext = [b[0] - MG, b[1] - MG, b[2] + MG, b[3] + MG];
    const cx = (ext[0] + ext[2]) / 2, cy = (ext[1] + ext[3]) / 2, W = ext[2] - ext[0], D = ext[3] - ext[1];
    Object.assign(this, { cx, cy, W, D });
    const X = x => x - cx, Z = y => y - cy;
    const H = this.o.railHeight;

    // 바닥 — walls:false 면 **두께 없는 평면**이다. 원본은 0.8 m 짜리 상자라
    //   등각으로 보면 그 옆면이 낮은 벽처럼 둘러싼다 (고객: "벽 남아있어").
    //   벽을 안 세울 때는 그 테두리도 같이 없애야 '벽이 없다' 가 된다.
    const noWall = this.o.walls === false;
    const noFloor = this.o.floor === false;
    const floor = noWall
      ? new T.Mesh(new T.PlaneGeometry(W, D),
                   this.mat(this.o.floorColor ?? 0xd6d9dc, { r: 0.9 }))
      : new T.Mesh(new T.BoxGeometry(W, 0.8, D),
          [this.mat(0xbfc3c8), this.mat(0xbfc3c8), this.mat(0xd6d9dc, { r: 0.9 }), this.mat(0x9aa0a6), this.mat(0xeef0f2), this.mat(0xeef0f2)]);
    if (noWall) { floor.rotation.x = -Math.PI / 2; floor.position.y = 0; }
    else floor.position.y = -0.4;
    floor.receiveShadow = true;
    if (!noFloor) W0.add(floor);
    const gp = [], step = 1.2;
    if (!noFloor && W / step < 1500 && D / step < 1500) {
      for (let x = -W / 2 + step; x < W / 2; x += step) gp.push(x, 0.005, -D / 2, x, 0.005, D / 2);
      for (let z = -D / 2 + step; z < D / 2; z += step) gp.push(-W / 2, 0.005, z, W / 2, 0.005, z);
      const gg = new T.BufferGeometry();
      gg.setAttribute('position', new T.Float32BufferAttribute(gp, 3));
      W0.add(new T.LineSegments(gg, new T.LineBasicMaterial({ color: 0xc9cdd1, transparent: true, opacity: 0.7 })));
    }

    // 벽 — walls:false 면 없다 (월드모델파생은 안 세운다: 등각으로 돌려 보면 벽이
    //   안쪽을 가리고, 레일·차량 말고는 보여줄 정보가 없는 상자다).
    this.walls = this.o.walls === false ? [] : G.walls.length ? G.walls : [
      { x0: ext[0] + 0.5, y0: ext[1] + 0.5, x1: ext[2] - 0.5, y1: ext[1] + 0.5 }, { x0: ext[2] - 0.5, y0: ext[1] + 0.5, x1: ext[2] - 0.5, y1: ext[3] - 0.5 },
      { x0: ext[2] - 0.5, y0: ext[3] - 0.5, x1: ext[0] + 0.5, y1: ext[3] - 0.5 }, { x0: ext[0] + 0.5, y0: ext[3] - 0.5, x1: ext[0] + 0.5, y1: ext[1] + 0.5 }];
    const wm = [this.mat(0xd9dcdf, { r: 0.85 }), this.mat(0xd9dcdf, { r: 0.85 }), this.mat(0xf7f8f9, { r: 0.9 }), this.mat(0xd9dcdf), this.mat(0xe1e4e7, { r: 0.85 }), this.mat(0xe1e4e7, { r: 0.85 })];
    this.wallMesh = this.IM(new T.BoxGeometry(1, 1, 1), wm, this.walls.length, { recv: true });

    // 레일
    const segs = [];
    for (const e of G.edges) for (let j = 1; j < e.pts.length; j++) {
      const [x0, y0] = e.pts[j - 1], [x1, y1] = e.pts[j];
      const len = Math.hypot(x1 - x0, y1 - y0);
      const mz = e.zs ? (e.zs[j - 1] + e.zs[j]) / 2 : 0;      // ★그 토막의 높이
      if (len > 0.01) segs.push([e.i, (x0 + x1) / 2, (y0 + y1) / 2, len,
                                 Math.atan2(y1 - y0, x1 - x0), mz]);
    }
    this.segs = segs;
    this.railGroup = new T.Group();
    W0.add(this.railGroup);
    this.buildRails();

    // 행거 — ★노드마다가 아니라 **4 m 칸마다 하나**. 실물 레이아웃(M14A)은 노드가
    //   0.7 m 간격이라(9,403개) 노드마다 세우면 1.8 m 봉 9천 개가 숲이 되어
    //   차량·설비가 안 보였다. 원본 세트는 노드가 성긴 견본 데이터로 만들어졌다.
    const nds = [], cell = new Set();
    for (const nd of G.nodes) {
      const k = Math.floor(nd.x / 4) + ',' + Math.floor(nd.y / 4);
      if (cell.has(k)) continue;
      cell.add(k); nds.push(nd);
    }
    const clampM = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xdfe3e7, { r: 0.3, m: 0.7 }), nds.length);
    const blk = this.IM(this.rbox(0.06, 0.03, 0.03), this.mat(0xa66f3f, { r: 0.55 }), nds.length);
    const rod = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xb9bec4, { r: 0.35, m: 0.6 }), nds.length);
    for (const nd of nds) {
      const e = G.edges[nd.out[0] ?? nd.in[0]];
      if (!e) continue;
      const a = Math.atan2(e.pts[1][1] - e.pts[0][1], e.pts[1][0] - e.pts[0][0]);
      this.base(X(nd.x), H + (nd.z || 0), Z(nd.y), -a);
      this.local(0, 0.16, 0, 0.22, 0.07, 0.7); this.put(clampM);
      this.local(0, 0.36, 0, 0.3, 0.3, 0.42); this.put(blk);
      this.local(0, 1.4, 0, 0.07, 1.8, 0.07); this.put(rod);
    }
    [clampM, blk, rod].forEach(m => this.fin(m));

    // 설비 / 스토커 — 한 그룹에, 크기 배수로 다시 세울 수 있게
    this.portGroup = new T.Group();
    this.portGroup.visible = this.opt.ports !== false;
    W0.add(this.portGroup);
    this._buildPortBodies(X, Z, this.opt.ps || 1);
  }
  _buildPortBodies(X, Z, ps) {
    const T = this.T, G = this.G, pg = { parent: this.portGroup };
    const ports = G.ports, n = ports.length, rb = this.rbox();
    const eqBody = this.IM(rb, this.mat(0xffffff, { r: 0.55 }), n, { recv: true, ...pg });
    const eqFront = this.IM(rb, this.mat(0xffffff, { r: 0.5 }), n, { recv: true, ...pg });
    const eqCap = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xaeb3b9, { r: 0.5, m: 0.3 }), n, pg);
    const screen = this.IM(new T.BoxGeometry(1, 1, 1), new T.MeshBasicMaterial({ color: 0x7c4ddb }), n, { cast: false, ...pg });
    const bezel = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0x2d3137), n, pg);
    const lp = this.IM(rb, this.mat(0x8f969e, { r: 0.45, m: 0.3 }), n * 2, pg);
    const sfoup = this.IM(rb, this.mat(0xefece6), n, pg);
    const sfWin = this.IM(new T.BoxGeometry(1, 1, 1), new T.MeshStandardMaterial({ color: 0x8b5cf6, roughness: 0.2, transparent: true, opacity: 0.85 }), n, { cast: false, ...pg });
    const lamp = this.IM(new T.BoxGeometry(1, 1, 1), new T.MeshBasicMaterial({ color: 0xffffff }), n, { cast: false, ...pg });
    const pole = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0x6b7178), n, pg);
    const panel = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xa9afb6, { r: 0.4, m: 0.3 }), n * 12, { cast: false, ...pg });
    const tones = [0xeceae5, 0xdcd9d2, 0xe5e3de], fronts = [0xf4f3f0, 0xcfccc6, 0xdedcd7], lampCol = [0x3ddc84, 0xffb020, 0xff4d4f];
    for (const p of ports) {
      const w = p.w * ps, d = p.d * ps, h = p.h * ps;
      this.base(X(p.x), p.z || 0, Z(p.y), -(p.rot || 0));   // ★그 층 높이
      if (p.kind === 'stk') {
        this.local(0, h / 2, 0, w, h, d); this.put(eqBody, 0x2a2d32);
        const k = clamp(Math.floor(d / 1.15), 2, 12);
        for (let j = 0; j < k; j++) { this.local(w / 2 + 0.012, h * 0.5, -d / 2 + (j + 0.5) * d / k, 0.03, h * 0.84, 0.09); this.put(panel); }
        this.local(-w * 0.3, h + 0.05, 0, w * 0.35, 0.1, d * 0.9); this.put(eqCap);
      } else {
        const t = (p.tone | 0) % 3;
        this.local(-0.1 * w, h / 2, 0, 0.8 * w, h, d); this.put(eqBody, tones[t]);
        this.local(0.36 * w, 0.42 * h, 0, 0.3 * w, 0.84 * h, 0.94 * d); this.put(eqFront, fronts[t]);
        this.local(-0.1 * w, h + 0.05, 0, 0.66 * w, 0.1, 0.8 * d); this.put(eqCap);
        if (p.scr) {
          this.local(0.51 * w + 0.01, 0.6 * h, -0.2 * d, 0.05, 0.62, 0.86); this.put(bezel);
          this.local(0.51 * w + 0.04, 0.6 * h, -0.2 * d, 0.02, 0.5, 0.74); this.put(screen);
        }
        if (p.loadport !== false) {
          for (const zz of [-0.25, 0.25]) { this.local(0.5 * w + 0.32, 0.43, zz * d, 0.58, 0.86, 0.7); this.put(lp); }
          if (p.foup) {
            this.local(0.5 * w + 0.32, 1.06, 0.25 * d, 0.46, 0.4, 0.44); this.put(sfoup);
            this.local(0.5 * w + 0.555, 1.06, 0.25 * d, 0.012, 0.26, 0.3); this.put(sfWin);
          }
        }
      }
      this.local(-0.38 * w, h + 0.22, 0.38 * d, 0.05, 0.34, 0.05); this.put(pole);
      this.local(-0.38 * w, h + 0.46, 0.38 * d, 0.13, 0.16, 0.13); this.put(lamp, lampCol[p.lamp | 0] ?? lampCol[0]);
    }
    [eqBody, eqFront, eqCap, screen, bezel, lp, sfoup, sfWin, lamp, pole, panel].forEach(m => this.fin(m));
    if (!this.zoneMeshes) this._buildZonesAndRest();     // 첫 세우기에만 (다시 세울 땐 설비만)
  }
  _buildZonesAndRest() {
    const T = this.T, G = this.G, W0 = this.world;
    const X = x => x - this.cx, Z = y => y - this.cy;
    // HID Zone 바닥/라벨
    this.zoneMeshes = [];
    this.zoneLabels = [];
    G.zones.forEach((z, zi) => {
      if (!z.bb) return;
      const [x0, y0, x1, y1] = z.bb;
      const m = new T.Mesh(new T.PlaneGeometry(x1 - x0, y1 - y0),
        new T.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.06, depthWrite: false, toneMapped: false }));
      m.rotation.x = -Math.PI / 2;
      const zz = z.z || 0;                 // ★그 존(동)이 선 높이
      m.position.set(X((x0 + x1) / 2), zz + 0.02, Z((y0 + y1) / 2));
      m.userData.zi = zi;
      m.renderOrder = 1;
      W0.add(m);
      const lg = new T.BufferGeometry();
      lg.setAttribute('position', new T.Float32BufferAttribute(
        [X(x0), zz + 0.03, Z(y0), X(x1), zz + 0.03, Z(y0),
         X(x1), zz + 0.03, Z(y1), X(x0), zz + 0.03, Z(y1)], 3));
      const line = new T.LineLoop(lg, new T.LineBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.5 }));
      W0.add(line);
      m.userData.line = line;
      this.zoneMeshes.push(m);
      const L = this.sprite(512, 110, 0.19, 0.041);
      L.sp.position.set(X((x0 + x1) / 2), this.o.wallHeight + 2, Z((y0 + y1) / 2));
      W0.add(L.sp);
      this.zoneLabels[zi] = L;
    });

    this.ring = new T.Mesh(new T.TorusGeometry(1, 0.05, 8, 48), new T.MeshBasicMaterial({ color: new T.Color(this.o.colors.accent), toneMapped: false }));
    this.ring.rotation.x = -Math.PI / 2;
    this.ring.visible = false;
    W0.add(this.ring);
    this.labelGroup = new T.Group();
    W0.add(this.labelGroup);
    this.vehGroup = new T.Group();
    W0.add(this.vehGroup);
  }

  /* 레일 — 굵기 배수로 다시 세운다. 판 폭 0.56 m × rs 가 평행 레일 간격(실물 0.30 m)
     보다 좁아야 두 줄로 보인다. */
  buildRails() {
    const T = this.T, g = this.railGroup, H = this.o.railHeight, rs = this.opt.rs || 1;
    const X = x => x - this.cx, Z = y => y - this.cy, segs = this.segs;
    this.disposeGroup(g);
    const pg = { parent: g };
    const bars = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xc7ccd2, { r: 0.35, m: 0.6 }), segs.length * 2, pg);
    this.plate = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xffffff, { r: 0.5, m: 0.2 }), segs.length, pg);
    for (const [, mx, my, len, a, mz] of segs) {
      this.base(X(mx), H + (mz || 0), Z(my), -a);
      this.local(0, 0, 0.21 * rs, len + 0.04, 0.13 * rs, 0.1 * rs); this.put(bars);
      this.local(0, 0, -0.21 * rs, len + 0.04, 0.13 * rs, 0.1 * rs); this.put(bars);
      this.local(0, 0.1 * rs, 0, len + 0.04, 0.05 * rs, 0.56 * rs); this.put(this.plate, 0x9aa1a9);
    }
    this.fin(bars); this.fin(this.plate);
  }
  buildPorts() {
    const X = x => x - this.cx, Z = y => y - this.cy;
    this.disposeGroup(this.portGroup);
    this._buildPortBodies(X, Z, this.opt.ps || 1);
    this.applyPorts();          // 꺼 둔 채로 다시 세우면 다시 나타나면 안 된다
  }

  buildVehicleMeshes(cap) {
    const T = this.T, g = this.vehGroup;
    this.disposeGroup(g);
    this.cap = cap;
    const dyn = { dynamic: true, parent: g };
    this.vTrol = this.IM(this.rbox(0.06, 0.03, 0.03), this.mat(0xa66f3f, { r: 0.5 }), cap * 2, dyn);
    this.vNeck = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0xd3d7dc, { r: 0.3, m: 0.7 }), cap, dyn);
    this.vBody = this.IM(this.rbox(0.1, 0.06, 0.06), this.mat(0xffffff, { r: 0.45 }), cap, dyn);
    this.vVent = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0x1f2328), cap * 2, { ...dyn, cast: false });
    this.vGrip = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0x3a3f46, { r: 0.5, m: 0.4 }), cap, dyn);
    this.vBelt = this.IM(new T.BoxGeometry(1, 1, 1), this.mat(0x1f2328), cap * 2, dyn);
    this.vFoup = this.IM(this.rbox(), this.mat(0xefece6), cap, dyn);
    this.vWin = this.IM(new T.BoxGeometry(1, 1, 1), new T.MeshStandardMaterial({ color: 0x8b5cf6, roughness: 0.2, transparent: true, opacity: 0.85 }), cap * 2, { ...dyn, cast: false });
    this.vPick = this.IM(new T.BoxGeometry(1, 1, 1), new T.MeshBasicMaterial(), cap, { ...dyn, cast: false });
    this.vPick.visible = false;
    for (let i = 0; i < cap; i++) this.vBody.setColorAt(i, this.stC[0]);
    this.vParts = [this.vTrol, this.vNeck, this.vBody, this.vVent, this.vGrip, this.vBelt, this.vFoup, this.vWin, this.vPick];
  }

  /* ---------------- 차량 데이터 ---------------- */
  setVehicles(rows, meta = {}) {
    if (!this.G) return;
    const G = this.G, now = performance.now();
    const interval = this.lastSet ? now - this.lastSet : 0;
    this.lastSet = now;
    const dur = meta.duration ?? Math.min(this.o.maxTweenMs, interval);
    this.ts = meta.ts ?? null;
    const seen = new Set();
    const stats = this.emptyStats();
    for (const r of rows || []) {
      if (r == null || r.id == null) continue;
      const id = String(r.id);
      let k = this.idx.get(id);
      if (k == null) { k = this.slots.length; this.slots.push({ id, live: false }); this.idx.set(id, k); }
      const sl = this.slots[k];
      let e = r.edge != null ? G.eIdx.get(String(r.edge)) : undefined;
      if (e == null && r.from != null && r.to != null) e = G.ftIdx.get(String(r.from) + '>' + String(r.to));
      let target;
      if (e != null) {
        const ed = G.edges[e];
        const s = r.dist_mm != null ? r.dist_mm / 1000 : r.ratio != null ? r.ratio * ed.len : 0;
        target = { e, s: clamp(+s || 0, 0, ed.len) };
      } else if (r.x != null && r.y != null) {
        const sc = this.o.coordScale, fy = this.o.flipY ? -1 : 1;
        target = { e: -1, x: +r.x * sc, y: +r.y * sc * fy, ang: r.angle != null ? +r.angle * fy : null };
      } else continue;
      seen.add(k);
      const cur = sl.live ? this.slotPos(sl, now) : null;
      sl.from = cur ? { e: cur.e, s: cur.s, x: cur.x, y: cur.y, ang: cur.ang } : target;
      sl.to = target; sl.t0 = now; sl.dur = dur; sl.live = true;
      let st = typeof r.state === 'number' ? r.state : STATE_MAP[String(r.state ?? '').toUpperCase()] ?? STATE_MAP[r.state] ?? 0;
      st = clamp(st | 0, 0, ST_MAX);
      sl.v = +r.speed_mpm || 0;
      sl.stop = +r.stop_sec || 0;
      if (this.o.jamSec > 0 && st === 2 && sl.stop >= this.o.jamSec) st = 3;
      sl.st = st;
      sl.ld = r.loaded ? 1 : 0;
      sl.hoist = r.hoist != null ? clamp(+r.hoist, 0, 1) : 0;
      sl.row = r;
      // 존/엣지 집계 (목표 위치 기준)
      let zi = -1;
      if (target.e >= 0) {
        const ed = G.edges[target.e];
        zi = ed.zone;
        stats.ec[target.e]++; stats.ev[target.e] += sl.v;
      } else {
        zi = G.zones.findIndex(z => z.bb && target.x >= z.bb[0] && target.x <= z.bb[2] && target.y >= z.bb[1] && target.y <= z.bb[3]);
      }
      sl.zone = zi;
      if (zi >= 0) {
        const zs = stats.zs[zi];
        zs.n++; zs.c[st]++; zs.vs += sl.v;
        if (st >= 2) zs.mx = Math.max(zs.mx, sl.stop);
      }
    }
    this.slots.forEach((sl, k) => { if (!seen.has(k)) sl.live = false; });
    if (this.tracked >= 0 && !this.slots[this.tracked]?.live) this.setTracked(-1);
    if (this.slots.length > this.cap) this.buildVehicleMeshes(Math.ceil(this.slots.length * 1.3));
    this.stats = stats;
    if (this.dom.ts) this.dom.ts.textContent = fmtTs(this.ts);
    this.vehDirty = true; this.domDirty = true;
  }
  chain(e0, e1) {
    const key = e0 * 1048576 + e1;
    if (this.chainCache.has(key)) return this.chainCache.get(key);
    const E = this.G.edges, N = this.G.nodes;
    let res = null;
    const dfs = (e, depth, acc) => {
      if (res || depth === 0) return;
      for (const ne of N[E[e].to].out) {
        if (ne === e1) { res = [...acc, ne]; return; }
        dfs(ne, depth - 1, [...acc, ne]);
        if (res) return;
      }
    };
    dfs(e0, 5, []);
    this.chainCache.set(key, res);
    return res;
  }
  posOn(e, s) {
    const ed = this.G.edges[e];
    const t = ed.len > 0 ? s / ed.len * ed.glen : 0;
    const q = pointOnPoly(ed.pts, ed.cum, t);
    q[3] = zOnPoly(ed.zs, ed.cum, t);        // ★그 자리의 높이
    return q;
  }
  slotPos(sl, now) {
    const E = this.G.edges;
    const a = sl.dur > 0 ? clamp((now - sl.t0) / sl.dur, 0, 1) : 1;
    const f = sl.from, t = sl.to;
    let e, s;
    if (t.e < 0 || f.e < 0) {
      if (t.e < 0 && f.e < 0 && f.x != null) {
        const x = f.x + (t.x - f.x) * a, y = f.y + (t.y - f.y) * a;
        const mv = Math.hypot(t.x - f.x, t.y - f.y);
        const ang = t.ang ?? (mv > 0.01 ? Math.atan2(t.y - f.y, t.x - f.x) : (f.ang ?? 0));
        return { e: -1, x, y, z: 0, ang, moving: a < 1 };
      }
      const p = a < 0.5 ? f : t;
      if (p.e >= 0) { const q = this.posOn(p.e, p.s);
        return { e: p.e, s: p.s, x: q[0], y: q[1], z: q[3], ang: q[2], moving: a < 1 }; }
      return { e: -1, x: p.x, y: p.y, z: 0, ang: p.ang ?? 0, moving: a < 1 };
    }
    e = f.e; s = f.s;
    if (a > 0) {
      if (f.e === t.e) {
        if (t.s >= f.s) s = f.s + (t.s - f.s) * a; else if (a >= 0.5) s = t.s;
      } else {
        const ch = this.chain(f.e, t.e);
        if (ch) {
          const r0 = Math.max(0, E[f.e].len - f.s);
          let tot = r0 + t.s;
          for (let j = 0; j < ch.length - 1; j++) tot += E[ch[j]].len;
          let d = tot * a;
          if (d <= r0) s = f.s + d;
          else {
            d -= r0;
            for (let j = 0; j < ch.length; j++) {
              const c = ch[j];
              if (j === ch.length - 1 || d <= E[c].len) { e = c; s = Math.min(d, E[c].len); break; }
              d -= E[c].len;
            }
          }
        } else if (a >= 0.5) { e = t.e; s = t.s; }
      }
    }
    const q = this.posOn(e, Math.max(0, s - 0.5));
    return { e, s, x: q[0], y: q[1], z: q[3], ang: q[2], moving: a < 1 };
  }

  /* ---------------- 차량 그리기 ---------------- */
  updateVehicles(now) {
    const H = this.o.railHeight, vs = this.opt.vs;
    this.vParts.forEach(m => { m.count = 0; });
    this.map.length = 0;
    this.ring.visible = false;
    const cand = [];
    const showAll = this.orb.dist < 130, showJam = this.orb.dist < 280;
    const drop = Math.max(0, (H - 1.55) / vs - 1.0);
    let moving = false;
    this.disp = this.disp || [];
    for (let k = 0; k < this.slots.length; k++) {
      const sl = this.slots[k];
      if (!sl.live) { this.disp[k] = null; continue; }
      const p = this.slotPos(sl, now);
      this.disp[k] = p;
      if (p.moving) moving = true;
      const px = p.x - this.cx, pz = p.y - this.cy, st = sl.st;
      this.base(px, H + (p.z || 0), pz, -p.ang, vs);
      this.local(0.27, 0.13, 0, 0.24, 0.26, 0.38); this.put(this.vTrol);
      this.local(-0.27, 0.13, 0, 0.24, 0.26, 0.38); this.put(this.vTrol);
      this.local(0, -0.12, 0, 0.72, 0.07, 0.1); this.put(this.vNeck);
      const bodyY = -0.52;
      this.local(0, bodyY, 0, 0.96, 0.62, 0.72); this.map[this.put(this.vBody, this.stC[st])] = k;
      this.local(0, bodyY + 0.05, 0.362, 0.6, 0.2, 0.01); this.put(this.vVent);
      this.local(0, bodyY + 0.05, -0.362, 0.6, 0.2, 0.01); this.put(this.vVent);
      const hz = sl.hoist * drop, gripY = bodyY - 0.34 - hz;
      this.local(0, gripY, 0, 0.5, 0.05, 0.5); this.put(this.vGrip);
      if (hz > 0.05) {
        const top = bodyY - 0.3, len = top - gripY;
        this.local(0, (top + gripY) / 2, 0.16, 0.03, len, 0.03); this.put(this.vBelt);
        this.local(0, (top + gripY) / 2, -0.16, 0.03, len, 0.03); this.put(this.vBelt);
      }
      if (sl.ld) {
        const fy = gripY - 0.23;
        this.local(0, fy, 0, 0.46, 0.4, 0.44); this.put(this.vFoup);
        this.local(0.235, fy, 0, 0.012, 0.26, 0.3); this.put(this.vWin);
        this.local(-0.235, fy, 0, 0.012, 0.26, 0.3); this.put(this.vWin);
      }
      this.local(0, -0.55, 0, 1.2, 1.5, 0.9); this.put(this.vPick);
      if (k === this.tracked) {
        this.ring.visible = true;
        this.ring.position.set(px, H - 0.5 * vs, pz);
        this.ring.scale.setScalar(1.05 * vs);
      }
      if (this.opt.labels && (showAll || (showJam && st >= 3) || k === this.tracked))
        cand.push([k, px, pz, (k === this.tracked ? 1e6 : 0) + st * 1e4 + sl.stop]);
    }
    this.vParts.forEach(m => this.fin(m));
    // 라벨 (겹침 제거)
    const used = new Set();
    if (cand.length) {
      cand.sort((a, b) => b[3] - a[3]);
      const w = this.cv.clientWidth || 1, h = this.cv.clientHeight || 1;
      // sizeAttenuation:false 스프라이트는 카메라 종류와 무관하게 NDC 크기다 —
      // 직교에서는 투영행렬[5] 가 절두체 크기라 원근의 1/tan(16°) 로 대신한다
      const pm5 = this.cam.isPerspectiveCamera ? this.cam.projectionMatrix.elements[5] : 1 / Math.tan(HALF_FOV);
      const lh = 0.033 * pm5 / 2 * h, lw = lh * 256 / 84;
      const placed = [], v = this._v;
      for (const [k, px, pz] of cand) {
        v.set(px, H + 0.5 * vs, pz).project(this.cam);
        if (v.z > 1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1) continue;
        const sx = (v.x + 1) / 2 * w, sy = (1 - v.y) / 2 * h;
        const rc = [sx - lw / 2, sy - lh, sx + lw / 2, sy];
        if (placed.some(q => rc[0] < q[2] && rc[2] > q[0] && rc[1] < q[3] && rc[3] > q[1])) continue;
        placed.push(rc);
        if (placed.length > 80) break;
        const L = this.vehLabel(k);
        L.sp.position.set(px, H + 0.5 * vs, pz);
        used.add(k);
      }
    }
    for (const [k, L] of this.labelPool) L.sp.visible = used.has(k);
    // 레일 히트맵
    const E = this.G.edges, S = this.stats;
    this.segs.forEach(([ei], i) => {
      const ed = E[ei], cnt = S.ec[ei];
      if (this.opt.heat && cnt) this._c.set(heatRGB(1 - Math.min(1, (S.ev[ei] / cnt) / (ed.vmax * 60))));
      else this._c.set(0x9aa1a9);
      this.plate.setColorAt(i, this._c);
    });
    if (this.plate.instanceColor) this.plate.instanceColor.needsUpdate = true;
    return moving;
  }
  vehLabel(k) {
    let L = this.labelPool.get(k);
    if (!L) { L = this.sprite(256, 84, 0.1, 0.033); this.labelPool.set(k, L); this.labelGroup.add(L.sp); }
    const sl = this.slots[k], st = sl.st, sc = this.o.colors.state;
    const l2 = `${Math.round(sl.v)} m/min` + (st >= 2 && sl.stop >= 3 ? ` · ${fmtDur(sl.stop)}` : '');
    const dark = this.dark();
    const txt = `${sl.id}|${l2}|${st}|${k === this.tracked}|${sl.ld}|${dark}`;
    if (txt === L.txt) return L;
    L.txt = txt;
    const g = L.cv.getContext('2d'), bg = dark ? 'rgba(23,29,37,.93)' : 'rgba(255,255,255,.95)';
    g.clearRect(0, 0, 256, 84);
    g.fillStyle = bg; roundRect(g, 2, 2, 252, 64, 10); g.fill();
    g.strokeStyle = k === this.tracked ? this.o.colors.accent : 'rgba(0,0,0,.15)';
    g.lineWidth = k === this.tracked ? 4 : 1.5; g.stroke();
    g.beginPath(); g.moveTo(118, 65); g.lineTo(128, 82); g.lineTo(138, 65); g.closePath(); g.fillStyle = bg; g.fill();
    g.fillStyle = sc[st]; roundRect(g, 9, 10, 10, 48, 4); g.fill();
    g.textBaseline = 'middle';
    g.fillStyle = st >= 3 ? sc[st] : (dark ? '#e3e8ee' : '#1c2430');
    g.font = '700 25px system-ui,"Malgun Gothic",sans-serif';
    g.fillText(`${sl.id}  ${ST_NAME[st]}${sl.ld ? ' ▣' : ''}`, 28, 21);
    g.font = '22px system-ui,"Malgun Gothic",sans-serif';
    g.fillStyle = st >= 3 ? sc[st] : st === 2 ? '#c27c00' : (dark ? '#8a96a6' : '#5b6675');
    g.fillText(l2, 28, 48);
    L.tex.needsUpdate = true;
    return L;
  }
  updateWalls() {
    const m = this.wallMesh, o = this.orb, c = this.cam.position;
    m.count = 0;
    const tx = o.tx + this.cx, tz = o.tz + this.cy, px = c.x + this.cx, pz = c.z + this.cy;
    for (const w of this.walls) {
      const dx = w.x1 - w.x0, dy = w.y1 - w.y0, len = Math.hypot(dx, dy);
      if (len < 0.01) continue;
      const side = (x, y) => Math.sign(dx * (y - w.y0) - dy * (x - w.x0));
      const h = side(px, pz) !== side(tx, tz) ? this.o.wallCutHeight : this.o.wallHeight;
      this.base((w.x0 + w.x1) / 2 - this.cx, 0, (w.y0 + w.y1) / 2 - this.cy, -Math.atan2(dy, dx));
      this.local(0, h / 2, 0, len + 0.5, h, 0.5);
      this.put(m);
    }
    this.fin(m);
  }
  updateZones() {
    const S = this.stats, dark = this.dark(), acc = this.o.colors.accent, red = this.o.colors.state[3];
    const f = clamp((this.orb.dist - 30) / 260, 0, 1);
    for (const m of this.zoneMeshes) {
      const zi = m.userData.zi, s = S.zs[zi], jam = s.c[3];
      const sel = zi === this.sel, hov = zi === this.hover;
      m.material.color.set(jam ? red : 0x3b82f6);
      m.material.opacity = (jam ? Math.min(0.22, 0.06 + jam * 0.015) : 0.04) * f + (hov ? 0.08 : 0) + (sel ? 0.03 * f : 0);
      const lm = m.userData.line.material;
      lm.color.set(sel || hov ? acc : (jam ? red : 0x3b82f6));
      lm.opacity = sel || hov ? 1 : 0.45;
    }
    this.G.zones.forEach((z, zi) => {
      const L = this.zoneLabels[zi];
      if (!L) return;
      const s = S.zs[zi], sel = zi === this.sel, hov = zi === this.hover;
      L.sp.visible = this.orb.dist > 45 && (this.orb.dist > 280 || sel || hov);
      const avg = s.n ? Math.round(s.vs / s.n) : 0;
      const txt = `${z.id}|${s.n}|${s.c[3]}|${avg}|${sel}|${hov}|${dark}`;
      if (txt === L.txt) return;
      L.txt = txt;
      const g = L.cv.getContext('2d'), bg = dark ? 'rgba(23,29,37,.94)' : 'rgba(255,255,255,.96)';
      g.clearRect(0, 0, 512, 110);
      g.fillStyle = bg; roundRect(g, 3, 3, 506, 84, 14); g.fill();
      g.strokeStyle = sel || hov ? acc : (s.c[3] ? red : 'rgba(0,0,0,.15)');
      g.lineWidth = sel || hov ? 5 : 2.5; g.stroke();
      g.beginPath(); g.moveTo(240, 86); g.lineTo(256, 108); g.lineTo(272, 86); g.closePath(); g.fillStyle = bg; g.fill();
      g.textBaseline = 'middle';
      g.fillStyle = dark ? '#e3e8ee' : '#1c2430';
      g.font = '700 30px system-ui,"Malgun Gothic",sans-serif';
      g.fillText(z.id, 20, 30);
      g.font = '24px system-ui,"Malgun Gothic",sans-serif';
      g.fillStyle = dark ? '#8a96a6' : '#5b6675';
      g.fillText(`대수 ${s.n} · 평균 ${avg} m/min`, 20, 66);
      if (s.c[3]) {
        g.font = '700 28px system-ui,"Malgun Gothic",sans-serif';
        const t = `JAM ${s.c[3]}`, tw = g.measureText(t).width;
        g.fillStyle = red; roundRect(g, 490 - tw - 20, 14, tw + 20, 36, 10); g.fill();
        g.fillStyle = '#fff'; g.fillText(t, 490 - tw - 10, 33);
      }
      L.tex.needsUpdate = true;
    });
  }

  /* ---------------- 카메라 ---------------- */
  applyCam() {
    const o = this.orb, ce = Math.cos(o.el);
    this.cam.position.set(o.tx + o.dist * ce * Math.cos(o.az), o.ty + o.dist * Math.sin(o.el), o.tz + o.dist * ce * Math.sin(o.az));
    this.cam.lookAt(o.tx, o.ty, o.tz);
    if (this.cam.isOrthographicCamera) {
      // 직교 절두체 반높이 = dist·tan(16°) — 원근 카메라가 그 거리에서 보는 높이와 같다.
      // 그래서 휠 줌(dist)·전체보기·존 보기·패널 밀기 계산을 하나도 안 바꿔도 된다.
      const hh = o.dist * Math.tan(HALF_FOV), asp = this.camP.aspect || 1.6;
      this.cam.left = -hh * asp; this.cam.right = hh * asp; this.cam.top = hh; this.cam.bottom = -hh;
      this.cam.updateProjectionMatrix();
    }
    if (this._spK !== (this.cam.isOrthographicCamera ? o.dist : 1)) { this._spK = this.cam.isOrthographicCamera ? o.dist : 1; this.fitSprites(); }
    this.cam.updateMatrixWorld();
    const s = clamp(o.dist * 1.05, 22, Math.max(this.W, this.D) * 0.62);
    const d = this.dir, sc = d.shadow.camera;
    d.target.position.set(o.tx, 0, o.tz);
    d.position.set(o.tx - 1.1 * s, 2.8 * s, o.tz - 0.5 * s);
    sc.left = sc.bottom = -s; sc.right = sc.top = s; sc.near = 1; sc.far = s * 8;
    sc.updateProjectionMatrix();
    this.updateWalls();
  }
  flyTo(t, dur = 850) {
    const o = this.orb, from = { ...o }, to = { ...o, ...t };
    let da = to.az - from.az;
    da = ((da + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    to.az = from.az + da;
    this.fly = { from, to, t0: performance.now(), dur };
  }
  withPanel(v) {
    const p = this.dom.panel;
    if (!p || p.hidden || this.root.clientWidth <= 700) return v;
    const h = this.cv.clientHeight || 1, az = v.az ?? this.orb.az, dist = v.dist ?? this.orb.dist;
    const shift = (p.offsetWidth + 16) / 2 * 2 * dist * Math.tan(16 * Math.PI / 180) / h;
    return { ...v, tx: (v.tx ?? this.orb.tx) + Math.sin(az) * shift, tz: (v.tz ?? this.orb.tz) - Math.cos(az) * shift };
  }
  /* 시점의 각도 — 원근이면 원본 값, 아이소면 등각(45°·35.264°). 원본은 -2.3 rad 을
     세 군데에 박아 두었는데, 아이소에서 그리로 날아가면 등각이 깨진다. */
  ang(el) { return this.opt.proj === 'iso' ? { el: ISO_EL, az: ISO_AZ } : { el, az: -2.3 }; }
  zoneView(zi) {
    const [x0, y0, x1, y1] = this.G.zones[zi].bb, asp = this.camP.aspect || 1.6;
    const R = Math.hypot(x1 - x0, y1 - y0) / 2;
    return { tx: (x0 + x1) / 2 - this.cx, ty: 1, tz: (y0 + y1) / 2 - this.cy, dist: Math.max(20, R / Math.tan(16 * Math.PI / 180) * (asp < 1 ? 1 / asp : 0.78)), ...this.ang(0.85) };
  }
  allView() {
    const R = Math.hypot(this.W, this.D) / 2, asp = this.camP.aspect || 1.6;
    return { tx: 0, ty: 0, tz: 0, dist: R / Math.tan(16 * Math.PI / 180) * (asp < 1 ? 1.05 / asp : 0.8), ...this.ang(0.9) };
  }
  /* 이 차가 정체로 볼 종류인가 — 0 JAM · 1 OBS · 2 멈춘 차, 아니면 -1.
     ★jamMin 을 안 받았으면(null) 예전 규칙이다: JAM·OBS 를 대수 무관하게 본다.
       다른 화면에서 이 뷰어를 그냥 열었을 때 갑자기 아무것도 안 잡히면 안 된다. */
  jamKind(st) {
    const m = this.o.jamMin;
    if (!Array.isArray(m)) return st >= 3 ? 0 : -1;
    for (let i = 0; i < JAM_ST.length; i++) if (st === JAM_ST[i] && m[i] > 0) return i;
    return -1;
  }
  hotView(zi = -1) {
    const d = this.disp || [], jams = [];
    const mins = Array.isArray(this.o.jamMin) ? this.o.jamMin : null;
    /* ★2D·유사3D 와 **같은 기준**이다 — ⚙ 설정의 '몇 대 이상' 세 칸이
         jamMin 으로 넘어온다 (고객: "아이소메트리 정체 판정 만들어야되").
       ★어느 HID 구역인지도 같이 들고 다닌다 (sl.zone) — 표시 위에 이름을 적는다. */
    this.slots.forEach((sl, k) => {
      const ki = (sl.live && d[k]) ? this.jamKind(sl.st) : -1;
      if (ki >= 0 && (zi < 0 || sl.zone === zi)) jams.push({ p: d[k], z: sl.zone, k: ki });
    });
    let best = null, bc = 0, bz = -1, bk = null;
    for (const a of jams) {
      let c = 0, sx = 0, sy = 0;
      const zc = new Map(), cnt = [0, 0, 0];
      for (const b of jams) if (Math.hypot(a.p.x - b.p.x, a.p.y - b.p.y) < 12) {
        c++; sx += b.p.x; sy += b.p.y; cnt[b.k]++;
        if (b.z != null && b.z >= 0) zc.set(b.z, (zc.get(b.z) || 0) + 1);
      }
      /* '몇 대 이상' 은 무리를 만든 **뒤에** 따진다 — 어느 한 종류라도 그 수를
         넘으면 정체다 (3 5 0 = JAM 3대 이상 **또는** OBS 5대 이상). 2D 와 같다. */
      if (mins && !cnt.some((v, i) => mins[i] > 0 && v >= mins[i])) continue;
      if (c > bc) {
        bc = c; best = [sx / c, sy / c]; bk = cnt.slice();
        // 한 무리가 두 구역에 걸칠 수 있다 — **제일 많이 든 구역**을 이름으로 쓴다
        bz = -1; let bn = 0;
        for (const [z, n] of zc) if (n > bn) { bn = n; bz = z; }
      }
    }
    // 정말 정체가 있었나 — 없으면 존 가운데(또는 맵 가운데)로 가되 **표시는 안 한다**
    this.hotAt = best ? [best[0], best[1], bc, bz, bk] : null;
    if (!best) {
      const z = zi >= 0 ? this.G.zones[zi].bb : null;
      best = z ? [(z[0] + z[2]) / 2, (z[1] + z[3]) / 2] : [this.cx, this.cy];
    }
    return { tx: best[0] - this.cx, ty: 1.5, tz: best[1] - this.cy, dist: 42, ...this.ang(0.8) };
  }
  selectZone(zi, fly = true) {
    if (!this.G || zi >= this.G.zones.length || (zi >= 0 && !this.G.zones[zi].bb)) return;
    this.sel = zi;
    if (this.dom.dc) this.dom.dc.hidden = zi < 0;
    if (zi >= 0) {
      if (this.dom.panel?.hidden && this.root.clientWidth <= 700) this.dom.bar.querySelector('[data-a=panel]')?.click();
      if (fly) this.flyTo(this.withPanel(this.zoneView(zi)));
      this.emit('zoneclick', { id: this.G.zones[zi].id, index: zi, stats: this.zoneStat(zi) });
    }
    this.domDirty = true; this.needRender = true;
  }
  focusVehicle(k) {
    this.setTracked(k);
    if (k < 0 || !this.disp?.[k]) return;
    const p = this.disp[k];
    this.flyTo(this.withPanel({ tx: p.x - this.cx, ty: 1.5, tz: p.y - this.cy, dist: 18, el: 0.6 }));
  }
  setTracked(k) {
    this.tracked = k;
    const fb = this.dom.bar?.querySelector('[data-a=follow]');
    if (fb) { fb.hidden = k < 0; if (k < 0) fb.classList.remove('on'); }
    if (k < 0) this.follow = false;
    else this.emit('vehicleclick', { id: this.slots[k].id, row: this.slots[k].row });
    this.vehDirty = true; this.domDirty = true;
  }
  setOptions(p) {
    if (p.labels != null) this.opt.labels = !!p.labels;
    if (p.heat != null) this.opt.heat = !!p.heat;
    if (p.vehicleScale != null) this.opt.vs = +p.vehicleScale || 1;
    if (p.projection != null) this.setProjection(p.projection);
    if (p.textScale != null && +p.textScale > 0 && +p.textScale !== this.opt.ts) { this.opt.ts = +p.textScale; this.fitSprites(); }
    if (p.portScale != null && +p.portScale > 0 && +p.portScale !== this.opt.ps) { this.opt.ps = +p.portScale; if (this.G) this.buildPorts(); }
    if (p.railScale != null && +p.railScale > 0 && +p.railScale !== this.opt.rs) { this.opt.rs = +p.railScale; if (this.G) this.buildRails(); }
    if (p.ports != null) { this.opt.ports = !!p.ports; this.applyPorts(); }
    /* 정체 기준 — 화면 ⚙ 설정이 바뀌면 여기로 온다. 이미 찍어 둔 표시는
       옛 기준으로 그린 것이라 지운다 ('정체 지점' 을 다시 누르면 새 기준이다). */
    if (p.jamMin !== undefined) {
      this.o.jamMin = Array.isArray(p.jamMin)
        ? p.jamMin.map(v => { const x = parseInt(v, 10); return (isNaN(x) || x < 0) ? 0 : x; })
        : null;
      this.clearHot();
      const hb = this.dom.bar && this.dom.bar.querySelector('[data-a=hot]');
      if (hb) hb.classList.remove('on');
    }
    if (p.dark !== undefined) { this.o.dark = p.dark; this.applyTheme(); this.domDirty = true; for (const L of this.labelPool.values()) L.txt = ''; }
    if (p.background) { this.o.colors.background = p.background;
      if (this.scene && this.scene.background) this.scene.background.set(p.background); }
    if (Array.isArray(p.stateColors) && p.stateColors.length) {
      const sc = [...p.stateColors, ...DEFAULTS.colors.state.slice(p.stateColors.length)];
      this.o.colors.state = sc;
      this.stC = sc.map(c => new this.T.Color(c));
      const leg = this.root.querySelector('.o3d-leg');
      if (leg) leg.innerHTML = ST_NAME.map((n, i) => `<span><i class="o3d-dot" style="background:${sc[i]}"></i>${n}</span>`).join('') + '<span>레일 원활<i class="o3d-hb"></i>정체</span>';
      for (const L of this.labelPool.values()) L.txt = '';
      this.domDirty = true;
    }
    const bar = this.dom.bar, q = a => bar && bar.querySelector(`[data-a=${a}]`);
    if (q('labels')) q('labels').classList.toggle('on', this.opt.labels);
    if (q('heat')) q('heat').classList.toggle('on', this.opt.heat);
    if (q('proj')) q('proj').textContent = this.opt.proj === 'iso' ? '원근으로' : '아이소로';
    if (q('ports')) q('ports').classList.toggle('on', this.opt.ports !== false);
    // 크기 패널 슬라이더·숫자를 지금 값으로 (기본값 단추·바깥에서 부른 setOptions 도 따라온다)
    const sz2 = this.dom.size;
    if (sz2) for (const k of ['rs', 'vs', 'ps', 'ts']) {
      const sl = sz2.querySelector(`input[data-s=${k}]`), vv = sz2.querySelector(`b[data-v=${k}]`);
      if (sl) sl.value = this.opt[k];
      if (vv) vv.textContent = (+this.opt[k]).toFixed(2);
    }
    this.emit('sizechange', { railScale: this.opt.rs, vehicleScale: this.opt.vs, portScale: this.opt.ps, textScale: this.opt.ts });
    this.vehDirty = true; this.camDirty = true; this.needRender = true;
  }
  /* 아이소메트리 ↔ 원근. 같은 orbit(tx·tz·dist)을 쓰므로 보던 자리는 그대로고,
     각도만 등각(45°·35.264°)으로 날아간다. 그 뒤 드래그로 돌리는 것은 자유다. */
  setProjection(mode) {
    const iso = mode === 'iso';
    this.opt.proj = iso ? 'iso' : 'persp';
    this.cam = iso ? this.camO : this.camP;
    if (iso) this.flyTo({ az: ISO_AZ, el: ISO_EL });
    else this.flyTo({ el: Math.min(this.orb.el, 0.9) });
    this.camDirty = true; this.needRender = true;
  }
  zoneStat(zi) {
    const s = this.stats.zs[zi];
    return { vehicles: s.n, run: s.c[0], load: s.c[1], stop: s.c[2], jam: s.c[3], obs: s.c[4], avgSpeed: s.n ? s.vs / s.n : 0, maxStopSec: s.mx };
  }
  zoneStatsList() { return this.G ? this.G.zones.map((z, i) => ({ id: z.id, ...this.zoneStat(i) })) : []; }
  snapshot(name) {
    this.r.render(this.scene, this.cam);
    const url = this.cv.toDataURL('image/png');
    if (name !== false) {
      const a = document.createElement('a');
      a.href = url;
      const z = this.sel >= 0 ? this.G.zones[this.sel].id + '_' : '';
      a.download = name || `OHT3D_${z}${fmtTs(this.ts).replace(/:/g, '') || Date.now()}.png`;
      a.click();
    }
    return url;
  }

  /* ---------------- 입력 ---------------- */
  pick(ev) {
    const r = this.cv.getBoundingClientRect();
    const nd = new this.T.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    this.ray.setFromCamera(nd, this.cam);
    const hv = this.ray.intersectObject(this.vPick, false)[0];
    if (hv && hv.instanceId != null) return { k: this.map[hv.instanceId] ?? -1, zi: -1 };
    const hz = this.ray.intersectObjects(this.zoneMeshes || [], false)[0];
    return { k: -1, zi: hz ? hz.object.userData.zi : -1 };
  }
  showTip(ev, html) {
    const t = this.tip, rr = this.root.getBoundingClientRect();
    t.innerHTML = html;
    t.style.display = 'block';
    let x = ev.clientX - rr.left + 14, y = ev.clientY - rr.top + 14;
    if (x + t.offsetWidth > rr.width - 6) x = ev.clientX - rr.left - t.offsetWidth - 14;
    if (y + t.offsetHeight > rr.height - 6) y = ev.clientY - rr.top - t.offsetHeight - 14;
    t.style.left = Math.max(4, x) + 'px';
    t.style.top = Math.max(4, y) + 'px';
  }
  hideTip() { this.tip.style.display = 'none'; }
  vehTip(k) {
    const sl = this.slots[k], sc = this.o.colors.state, G = this.G, d = this.disp[k];
    const ed = d && d.e >= 0 ? G.edges[d.e] : null;
    return `<b>${sl.id}</b> <span class="o3d-stc" style="background:${sc[sl.st]}">${ST_NAME[sl.st]}</span><br>
      <span class="k">속도</span>${Math.round(sl.v)} m/min<br>
      <span class="k">정체</span>${sl.st >= 2 ? fmtDur(sl.stop) : '-'}<br>
      ${ed ? `<span class="k">구간</span>${G.nodes[ed.from].id} → ${G.nodes[ed.to].id}<br>` : ''}
      <span class="k">HID</span>${sl.zone >= 0 ? G.zones[sl.zone].id : '-'}<br>
      <span class="k">FOUP</span>${sl.ld ? '적재' : '없음'}${sl.hoist > 0 ? ' · 호이스트' : ''}`;
  }
  zoneTip(zi) {
    const s = this.stats.zs[zi], avg = s.n ? Math.round(s.vs / s.n) : 0;
    return `<b>${this.G.zones[zi].id}</b><br>
      <span class="k">대수</span>${s.n} (운행 ${s.c[0]} · 적재 ${s.c[1]} · 정지 ${s.c[2]} · JAM ${s.c[3]} · OBS ${s.c[4]})<br>
      <span class="k">평균</span>${avg} m/min<br><span class="k">최대정체</span>${s.mx ? fmtDur(s.mx) : '-'}`;
  }
  _bind() {
    const o = this.orb, cv = this.cv, pts = new Map();
    let drag = null;
    const pdist = () => { const [a, b] = [...pts.values()]; return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
    const clampD = d => clamp(d, 3, 5000);
    this._on = [];
    const on = (el, ev, fn, opt) => { el.addEventListener(ev, fn, opt); this._on.push([el, ev, fn, opt]); };
    on(cv, 'contextmenu', e => e.preventDefault());
    on(cv, 'pointerdown', e => {
      cv.setPointerCapture(e.pointerId);
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (!drag) drag = { x: e.clientX, y: e.clientY, moved: false, pan: e.button === 2 || e.shiftKey, pinch: 0 };
      if (pts.size === 2) drag.pinch = pdist();
      cv.style.cursor = 'grabbing';
      this.hideTip();
    });
    on(cv, 'pointermove', e => {
      if (drag && pts.has(e.pointerId)) {
        const prev = pts.get(e.pointerId);
        pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (pts.size === 2) {
          const d = pdist();
          if (drag.pinch) o.dist = clampD(o.dist * drag.pinch / d);
          drag.pinch = d; drag.moved = true; this.camDirty = true; this.fly = null;
          return;
        }
        if (!drag.moved && Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 3) drag.moved = true;
        if (!drag.moved) return;
        this.fly = null;
        const dx = e.clientX - prev.x, dy = e.clientY - prev.y;
        if (drag.pan) {
          const k = o.dist * 0.0016, fx = -Math.cos(o.az), fz = -Math.sin(o.az);
          o.tx += (fz * dx + fx * dy) * k;
          o.tz += (-fx * dx + fz * dy) * k;
          this.follow = false;
          this.dom.bar?.querySelector('[data-a=follow]')?.classList.remove('on');
        } else {
          o.az += dx * 0.006;
          o.el = clamp(o.el + dy * 0.005, 0.1, 1.52);
        }
        this.camDirty = true;
        return;
      }
      this.mouse = e;
    });
    const end = e => {
      if (drag && !drag.moved && e.type === 'pointerup' && pts.size === 1 && this.G) {
        const h = this.pick(e);
        if (h.k >= 0) this.setTracked(this.tracked === h.k ? -1 : h.k);
        else if (h.zi >= 0) this.selectZone(h.zi);
      }
      pts.delete(e.pointerId);
      if (!pts.size) { drag = null; cv.style.cursor = 'grab'; }
    };
    on(cv, 'pointerup', end);
    on(cv, 'pointercancel', end);
    on(cv, 'pointerleave', () => { this.mouse = null; this.hideTip(); if (this.hover >= 0) { this.hover = -1; this.domDirty = true; } });
    on(cv, 'wheel', e => { e.preventDefault(); this.fly = null; o.dist = clampD(o.dist * Math.exp(e.deltaY * 0.0012)); this.camDirty = true; }, { passive: false });
    on(cv, 'dblclick', () => this.G && this.flyTo(this.withPanel(this.hotView(this.sel))));
  }

  /* ---------------- 패널 ---------------- */
  updateDom() {
    const d = this.dom;
    if (!d.ztb || !this.G) return;
    const S = this.stats, G = this.G, sc = this.o.colors.state;
    d.ztb.innerHTML = G.zones.map((z, i) => {
      if (!z.bb) return '';
      const s = S.zs[i], avg = s.n ? Math.round(s.vs / s.n) : '-';
      return `<tr data-z="${i}" class="${i === this.sel ? 'sel' : ''}"><td>${z.id}</td><td>${s.n}</td><td>${s.c[2]}</td>
        <td class="${s.c[3] ? 'jam' : ''}">${s.c[3]}</td><td>${avg}</td><td class="${s.mx >= 60 ? 'jam' : ''}">${s.mx ? fmtDur(s.mx) : '-'}</td></tr>`;
    }).join('');
    const zi = this.sel;
    if (zi < 0) return;
    const s = S.zs[zi], avg = s.n ? Math.round(s.vs / s.n) : 0;
    d.dt.textContent = G.zones[zi].id;
    d.st.innerHTML = `<span class="o3d-chip">대수 ${s.n}</span><span class="o3d-chip">운행 ${s.c[0]}</span><span class="o3d-chip">적재 ${s.c[1]}</span>
      <span class="o3d-chip">정지 ${s.c[2]}</span><span class="o3d-chip ${s.c[3] ? 'jam' : ''}">JAM ${s.c[3]}</span><span class="o3d-chip">OBS ${s.c[4]}</span>
      <span class="o3d-chip">평균 ${avg} m/min</span><span class="o3d-chip">최대정체 ${s.mx ? fmtDur(s.mx) : '-'}</span>`;
    const rows = [];
    this.slots.forEach((sl, k) => { if (sl.live && sl.zone === zi) rows.push(k); });
    const SL = this.slots;
    rows.sort((a, b) => (SL[b].st - SL[a].st) || (SL[b].stop - SL[a].stop) || (SL[a].v - SL[b].v));
    d.vtb.innerHTML = rows.map(k => {
      const sl = SL[k];
      return `<tr data-k="${k}" class="${k === this.tracked ? 'sel' : ''}"><td>${sl.id}</td>
        <td><span class="o3d-stc" style="background:${sc[sl.st]}">${ST_NAME[sl.st]}</span></td>
        <td>${Math.round(sl.v)}</td><td>${sl.st >= 2 ? fmtDur(sl.stop) : '-'}</td><td>${sl.ld ? '●' : '-'}</td></tr>`;
    }).join('');
  }

  /* ---------------- 루프 ---------------- */
  resizeNow() {
    const w = Math.max(1, this.root.clientWidth), h = Math.max(1, this.root.clientHeight);
    this.r.setSize(w, h, false);
    this.camP.aspect = w / h;
    this.camP.updateProjectionMatrix();
    this.resized = false;
    this.camDirty = true;         // 직교 절두체는 applyCam 이 aspect 로 다시 잡는다
  }
  _loop(now) {
    this.raf = requestAnimationFrame(this._loop);
    if (!this.G || !this.active) return;
    if (this.resized) this.resizeNow();
    if (this.fly) {
      const f = this.fly, t = Math.min(1, (now - f.t0) / f.dur), e = ease(t);
      for (const k of ['tx', 'ty', 'tz', 'az', 'el', 'dist']) this.orb[k] = f.from[k] + (f.to[k] - f.from[k]) * e;
      if (t >= 1) this.fly = null;
      this.camDirty = true;
    }
    if (this.follow && this.tracked >= 0 && this.disp?.[this.tracked] && !this.fly) {
      const p = this.disp[this.tracked], o = this.orb;
      const gx = p.x - this.cx, gz = p.y - this.cy;
      if (Math.abs(gx - o.tx) + Math.abs(gz - o.tz) > 0.01) { o.tx += (gx - o.tx) * 0.2; o.tz += (gz - o.tz) * 0.2; this.camDirty = true; }
    }
    if (this.camDirty) {
      this.camDirty = false;
      this.applyCam();
      this.vehDirty = true;
      this.updateZones();
      this.needRender = true;
    }
    if (this.vehDirty) {
      this.vehDirty = this.updateVehicles(now);   // 보간 중이면 다음 프레임도 갱신
      this.needRender = true;
    }
    if (this.mouse) {
      const e = this.mouse;
      this.mouse = null;
      const h = this.pick(e);
      if (h.k >= 0) this.showTip(e, this.vehTip(h.k));
      else if (h.zi >= 0) this.showTip(e, this.zoneTip(h.zi));
      else this.hideTip();
      this.cv.style.cursor = h.k >= 0 || h.zi >= 0 ? 'pointer' : 'grab';
      if (h.zi !== this.hover) { this.hover = h.zi; this.updateZones(); this.needRender = true; }
    }
    if (this.domDirty && now - this.lastDom > 250) {
      this.domDirty = false;
      this.lastDom = now;
      this.updateDom();
      this.updateZones();
      this.needRender = true;
    }
    if (this.needRender) { this.needRender = false; this.r.render(this.scene, this.cam); }
  }
  dispose() {
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    this._on.forEach(([el, ev, fn, opt]) => el.removeEventListener(ev, fn, opt));
    this.disposeGroup(this.world);
    this.r.dispose();
    this.root.querySelectorAll('.o3d-cv,.o3d-tip,.o3d-bar,.o3d-leg,.o3d-panel,.o3d-size').forEach(n => n.remove());
    this.root.classList.remove('o3d-root');
    this.G = null;
  }
}
