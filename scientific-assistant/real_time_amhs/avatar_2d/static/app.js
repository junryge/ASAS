
"use strict";
/* run.py 서버로 실행 중인지. /api/config 를 받으면 true 가 된다.
   true 면 LLM·자료·세션·설정이 전부 파이썬 서버를 거친다. */
window.SERVER = false;
/* =====================================================================
   2D Emotive Character Engine  —  dependency-free WebGL mesh warping
   ===================================================================== */

const COSTUMES = [
  {name:'정장', src:"assets/suit.png", cfg:null, real:false},
  {name:'가운', src:"assets/coat.png", cfg:null, real:false},
  {name:'무진복', src:"assets/clean.png", cfg:null, real:false},
  /* patch : CFG_ANIME 위에 덮어쓸 값. 손 위치가 다른 그림만 지정한다 */
  {name:'반팔', src:"assets/tee.png", cfg:null, real:false,
    patch:{ armA:[0.382,0.848], armB:[0.598,0.848],
            armA_rad:[0.070,0.056], armB_rad:[0.070,0.056] }},
  {name:'잠옷', src:"assets/pj.png", cfg:null, real:false,
    /* 손을 맞잡고 있어서 두 팔 영역이 겹치면 손가락이 찢어진다.
       중앙(손깍지)은 건드리지 않고 소매 쪽만 움직이도록 바깥으로 뺐다 */
    patch:{ armA:[0.352,0.852], armB:[0.636,0.852],
            armA_rad:[0.058,0.050], armB_rad:[0.058,0.050] }},
];
let costumeIdx = 0;

/* costume : 이 배경을 고르면 의상도 같이 바뀐다 (COSTUMES 인덱스)
   badge   : 사원증을 켤지/끌지. 없으면 지금 상태를 유지한다.        */
const BACKGROUNDS = [
  {name:'기본',    img:null},
  {name:'공장',    img:"assets/bg_factory.jpg", costume:2, badge:true},   // 무진복
  {name:'회의실',  img:"assets/bg_meeting.jpg", costume:0, badge:true},   // 정장
  {name:'정문',    img:"assets/bg_gate.jpg",    costume:1, badge:true},   // 가운
  {name:'테라스',  img:"assets/bg_terrace.jpg", costume:3, badge:false},  // 반팔 · 사원증 없음
  {name:'집',      img:"assets/bg_room.jpg",    costume:4, badge:false},  // 잠옷 · 사원증 없음
];
let bgIdx = 0;

/* ---------- 캘리브레이션 (이미지 정규화 좌표 0~1) ---------- */
/* 그림마다 눈·입·손 위치가 다르다. 의상별로 각자의 캘리브레이션을 갖는다. */
const CFG_ANIME = {
  eyeL:[0.405,0.262], eyeL_rad:[0.036,0.017],
  eyeR:[0.572,0.260], eyeR_rad:[0.038,0.017],
  mouth:[0.489,0.350], mouth_rad:[0.030,0.013],
  brow_dy:-0.038,
  cheekL:[0.398,0.302], cheekR:[0.582,0.300], cheek_rad:[0.045,0.030],
  neckY:0.405, neckPivot:[0.492,0.455],
  headC:[0.505,0.210], headRad:[0.310,0.250],
  faceC:[0.490,0.320], faceRad:[0.130,0.105],
  hairRoot:0.10, hairTip:0.46, clothTop:0.62,
  armA:[0.390,0.835], armA_rad:[0.088,0.062], armA_piv:[0.100,0.790],
  armB:[0.615,0.835], armB_rad:[0.088,0.062], armB_piv:[0.900,0.790]
};
/* 실사 버전 : 얼굴이 더 작고 눈·입이 위쪽에 있다 */
const CFG_REAL = {
  eyeL:[0.425,0.253], eyeL_rad:[0.031,0.011],
  eyeR:[0.550,0.252], eyeR_rad:[0.031,0.011],
  mouth:[0.490,0.359], mouth_rad:[0.033,0.011],
  brow_dy:-0.028,
  cheekL:[0.418,0.300], cheekR:[0.558,0.298], cheek_rad:[0.040,0.028],
  neckY:0.425, neckPivot:[0.490,0.470],
  headC:[0.495,0.215], headRad:[0.205,0.215],
  faceC:[0.488,0.310], faceRad:[0.105,0.098],
  hairRoot:0.12, hairTip:0.44, clothTop:0.64,
  armA:[0.375,0.870], armA_rad:[0.080,0.058], armA_piv:[0.120,0.770],
  armB:[0.625,0.870], armB_rad:[0.080,0.058], armB_piv:[0.880,0.770]
};
const CFG = JSON.parse(JSON.stringify(CFG_ANIME));
const CFG0 = JSON.parse(JSON.stringify(CFG));

/* ---------- 감정 프리셋 ---------- */
// eyeOpen, eyeSmile, brow, mouthOpen, mouthCurve, mouthWidth,
// tilt, turn, headY, blush, gloom, sym
const EMO = {
  neutral : {ko:"평온",  eyeOpen:1.00,eyeSmile:0.00,eyeTilt: 0.00,tear:0.00,brow: 0.00,mouthOpen:0.00,mouthCurve: 0.05,mouthWidth:0.0,tilt:  0.000,turn:  0.000,headY: 0.000,blush:0.00,gloom:0.0,armA: 0.00,armB: 0.00,sym:""},
  smile   : {ko:"미소",  eyeOpen:0.93,eyeSmile:0.26,eyeTilt: 0.02,tear:0.00,brow: 0.10,mouthOpen:0.14,mouthCurve: 0.62,mouthWidth:0.10,tilt:  0.070,turn:  0.050,headY:-0.004,blush:0.06,gloom:0.0,armA: 0.03,armB:-0.02,sym:"✦"},
  joy     : {ko:"기쁨",  eyeOpen:0.64,eyeSmile:0.68,eyeTilt:-0.05,tear:0.00,brow: 0.45,mouthOpen:0.52,mouthCurve: 0.85,mouthWidth:0.22,tilt:-0.090,turn:-0.060,headY:-0.014,blush:0.14,gloom:0.0,armA:-0.07,armB:-0.06,sym:"♪"},
  sad     : {ko:"슬픔",  eyeOpen:0.66,eyeSmile:0.00,eyeTilt:-0.26,tear:0.55,brow:-0.55,mouthOpen:0.13,mouthCurve:-0.62,mouthWidth:-0.10,tilt:  0.050,turn:  0.030,headY: 0.020,blush:0.05,gloom:0.55,armA: 0.06,armB: 0.05,sym:"💧"},
  angry   : {ko:"분노",  eyeOpen:1.10,eyeSmile:0.00,eyeTilt: 0.32,tear:0.00,brow:-0.95,mouthOpen:0.26,mouthCurve:-0.50,mouthWidth:0.05,tilt:-0.030,turn:  0.000,headY:-0.006,blush:0.10,gloom:0.30,armA:-0.11,armB:-0.05,sym:"💢"},
  surprise: {ko:"놀람",  eyeOpen:1.42,eyeSmile:0.00,eyeTilt:-0.06,tear:0.00,brow: 0.95,mouthOpen:0.80,mouthCurve: 0.00,mouthWidth:-0.14,tilt:  0.000,turn:  0.000,headY:-0.022,blush:0.08,gloom:0.0,armA: 0.10,armB:-0.03,sym:"❗"},
  shy     : {ko:"부끄",  eyeOpen:0.66,eyeSmile:0.34,eyeTilt:-0.16,tear:0.00,brow: 0.22,mouthOpen:0.14,mouthCurve: 0.40,mouthWidth:-0.06,tilt:  0.130,turn:  0.170,headY: 0.010,blush:0.45,gloom:0.0,armA: 0.14,armB: 0.03,sym:"♡"},
  think   : {ko:"고민",  eyeOpen:0.82,eyeSmile:0.00,eyeTilt: 0.14,tear:0.00,brow:-0.20,mouthOpen:0.09,mouthCurve:-0.20,mouthWidth:-0.08,tilt:-0.110,turn:-0.150,headY: 0.004,blush:0.00,gloom:0.10,armA: 0.11,armB: 0.01,sym:"❓"},
  smug    : {ko:"의기양양",eyeOpen:0.76,eyeSmile:0.24,eyeTilt: 0.22,tear:0.00,brow: 0.30,mouthOpen:0.04,mouthCurve: 0.45,mouthWidth:0.16,tilt:  0.100,turn:  0.110,headY:-0.006,blush:0.06,gloom:0.0,armA: 0.08,armB:-0.03,sym:"✧"},
  fear    : {ko:"당황",  eyeOpen:1.22,eyeSmile:0.00,eyeTilt:-0.22,tear:0.30,brow: 0.70,mouthOpen:0.32,mouthCurve:-0.42,mouthWidth:-0.16,tilt:  0.030,turn:-0.090,headY: 0.012,blush:0.14,gloom:0.35,armA: 0.09,armB: 0.06,sym:"💦"},
  sleepy  : {ko:"졸림",  eyeOpen:0.28,eyeSmile:0.00,eyeTilt:-0.20,tear:0.00,brow:-0.15,mouthOpen:0.24,mouthCurve:-0.05,mouthWidth:-0.05,tilt:  0.150,turn:  0.040,headY: 0.026,blush:0.10,gloom:0.20,armA: 0.05,armB: 0.06,sym:"z"},
  love    : {ko:"애정",  eyeOpen:0.66,eyeSmile:0.62,eyeTilt:-0.10,tear:0.00,brow: 0.35,mouthOpen:0.24,mouthCurve: 0.75,mouthWidth:0.12,tilt:  0.110,turn:  0.070,headY:-0.008,blush:0.40,gloom:0.0,armA: 0.10,armB:-0.02,sym:"♥"}
};
const EMO_KEYS = Object.keys(EMO);
const PARAMS = ["eyeOpen","eyeSmile","eyeTilt","tear","brow","mouthOpen","mouthCurve","mouthWidth",
                "tilt","turn","headY","blush","gloom","armA","armB"];

// 말풍선 좌측 액센트 색 — 감정에 맞춰 바뀐다
const EMO_COLOR = {
  neutral:'#7d8899', smile:'#e0a45c', joy:'#f0b34a', sad:'#5a86d9',
  angry:'#e04a4a', surprise:'#e8c14a', shy:'#e87fa0', think:'#7f9bc4',
  smug:'#c08fd9', fear:'#6fb8c9', sleepy:'#8f93b5', love:'#ef6f96'
};

const MOTION = {
  none  :{ko:"없음"},   nod   :{ko:"끄덕"},  shake :{ko:"도리"},
  bounce:{ko:"통통"},   jump  :{ko:"점프"},  lean  :{ko:"기울"},
  shiver:{ko:"부들"},   pop   :{ko:"화들짝"},
  wave  :{ko:"손 흔들"},handup:{ko:"손 올림"},tap :{ko:"손가락 톡톡"},
  cross :{ko:"팔 고쳐잡기"}
};

/* =====================  WebGL  ===================== */
const glc = document.getElementById('gl');
const gl = glc.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true});
if(!gl){ document.body.innerHTML='<p style="padding:40px">WebGL을 사용할 수 없는 브라우저입니다.</p>'; throw 0; }

const VS = `
precision highp float;
attribute vec2 a_uv;
varying vec2 v_uv;

uniform vec2  u_canvas, u_imgPx, u_viewOff;
uniform float u_viewScale, u_aspect;

uniform vec2  u_eyeL,u_eyeR,u_eyeLRad,u_eyeRRad,u_mouth,u_mouthRad,u_neckPivot,u_headC,u_headRad;
uniform vec2  u_armA,u_armARad,u_armAPiv,u_armB,u_armBRad,u_armBPiv;
uniform vec2  u_faceC,u_faceRad;
uniform float u_hairRoot,u_hairTip,u_clothTop,u_hairSway,u_hairBob,u_clothSway;
uniform float u_neckY, u_browDy;

uniform float u_eyeOpen,u_eyeSmile,u_blinkL,u_blinkR,u_brow;
uniform float u_mouthOpen,u_mouthCurve,u_mouthWidth;
uniform float u_tilt,u_turn,u_headY,u_headX;
uniform float u_breath,u_sway,u_bounce,u_shakeX,u_squash;
uniform float u_armAAng,u_armBAng,u_armALift,u_browAmp,u_eyeTilt,u_mouthWarp,u_mouthRealW;
uniform vec2  u_gaze;

/* 부드러운 종 모양 가중치 : 중심 1 -> 경계 0, 양끝 기울기 0 (각지지 않음) */
float bump(vec2 p, vec2 c, vec2 r){
  float t = length((p-c)/r);
  float s = max(0.0, 1.0 - t*t);
  return s*s;
}
/* 평탄형 : 중심부는 1로 유지되고 바깥에서만 부드럽게 0 (눈꺼풀·손처럼 통째로 움직여야 하는 부위) */
float plate(vec2 p, vec2 c, vec2 r, float inner){
  return 1.0 - smoothstep(inner, 1.0, length((p-c)/r));
}
vec2 rot(vec2 d, float a, float A){
  vec2 e = vec2(d.x*A, d.y);
  float s=sin(a), c=cos(a);
  e = vec2(e.x*c - e.y*s, e.x*s + e.y*c);
  return vec2(e.x/A, e.y);
}

void main(){
  v_uv = a_uv;
  vec2 p = a_uv;
  float A = u_aspect;

  /* ---- 눈 ----------------------------------------------------------------
     커널을 아래로 치우치게 잡는다. 위쪽은 앞머리라서 조금만 물어도
     머리카락이 늘어나며 줄이 죽죽 간다.                                  */
  for(int i=0;i<2;i++){
    vec2  c     = (i==0)? u_eyeL : u_eyeR;
    vec2  er    = (i==0)? u_eyeLRad : u_eyeRRad;      // 좌우 눈 크기가 다르다
    float blink = (i==0)? u_blinkL : u_blinkR;
    vec2  q     = p - c;
    float ryv   = (q.y < 0.0) ? er.y*0.95 : er.y*2.00;   // 위 좁게 / 아래 넓게
    float tt    = length(vec2(q.x/(er.x*1.35), q.y/ryv));
    float w     = 1.0 - smoothstep(0.55, 1.0, tt);
    if(w > 0.001){
      float sgn = (i==0) ? 1.0 : -1.0;
      /* 눈꼬리 각도 : 회전이 아니라 전단(shear).
         회전은 가중치가 변하는 구간에서 메쉬를 접어버린다. */
      p.y += u_eyeTilt*sgn*clamp(q.x/er.x,-1.4,1.4)*er.y*0.80*w;

      float open = clamp(u_eyeOpen*(1.0-blink), 0.0, 1.55);
      // 감을 때 중심이 아니라 '아랫눈꺼풀 선'으로 모인다. 실제 눈은 위에서 아래로 덮인다
      p.y = mix(p.y, c.y + er.y*0.30*(1.0-open) + (p.y-c.y)*open, w);

      float low = smoothstep(c.y-er.y*0.10, c.y+er.y*0.55, p.y);
      float dx  = clamp(q.x/er.x, -1.0, 1.0);
      p.y -= u_eyeSmile*w*(low*er.y*0.38 + (1.0-dx*dx)*er.y*0.06);

      p += u_gaze*er*vec2(0.30,0.18)*w;
    }
  }

  /* ---- 눈썹 ---- */
  for(int i=0;i<2;i++){
    vec2 er2 = (i==0)? u_eyeLRad : u_eyeRRad;
    vec2 c = ((i==0)? u_eyeL : u_eyeR) + vec2(0.0, u_browDy);
    float w = bump(p, c, er2*vec2(1.30,1.00));
    p.y -= u_brow * 0.013 * u_browAmp * w;
  }

  /* ---- 입 : 턱(jaw) + 입술 2단 구조 ---- */
  {
    vec2 lr = u_mouthRad;
    /* 1) 턱이 내려간다 — 입 아래 넓은 영역이 함께 움직여야 자연스럽다 */
    vec2  jc = u_mouth + vec2(0.0, lr.y*2.0);
    float jw = bump(p, jc, vec2(lr.x*3.0, lr.y*5.0));
    float below = smoothstep(u_mouth.y - lr.y*0.8, u_mouth.y + lr.y*1.6, p.y);
    p.y += u_mouthOpen * jw * below * lr.y * 0.60 * u_mouthWarp * (1.0 + u_mouthRealW*0.5);

    /* 2) 입술 자체 : 아랫입술은 크게, 윗입술은 살짝만 */
    float lw  = bump(p, u_mouth, lr*vec2(1.7,2.4));
    float low = smoothstep(u_mouth.y - lr.y*0.30, u_mouth.y + lr.y*0.70, p.y);
    float dx  = clamp((p.x-u_mouth.x)/(lr.x*1.7), -1.0, 1.0);
    p.y += u_mouthOpen * lw * (low*lr.y*0.28 - (1.0-low)*lr.y*0.10) * u_mouthWarp;

    /* 3) 입꼬리 : 가장자리가 올라가고 중앙은 거의 안 움직임 */
    p.y -= u_mouthCurve * lw * dx*dx * lr.y*0.85 * u_mouthWarp * (1.0 - u_mouthRealW*0.70);
    p.y += u_mouthCurve * lw * (1.0-dx*dx) * lr.y*0.14;
    p.x += u_mouthWidth * lw * dx * lr.x*0.70 * (1.0 - u_mouthRealW*0.80);
  }

  /* ---- 팔/손 : 팔꿈치 피벗 회전 (경계 가중치가 0으로 수렴 -> 찢김 없음) ---- */
  float wa = plate(p, u_armA, u_armARad, 0.42);
  if(wa > 0.001){
    p = u_armAPiv + rot(p-u_armAPiv, u_armAAng*wa, A);
    p.y -= u_armALift * wa * 0.020;
  }
  float wb = plate(p, u_armB, u_armBRad, 0.42);
  if(wb > 0.001){
    p = u_armBPiv + rot(p-u_armBPiv, u_armBAng*wb, A);
  }

  /* ---- 머리 : 타원 마스크 × 목선 마스크, 팔 영역은 제외 ---- */
  float he = length((p-u_headC)/u_headRad);
  float hm = 1.0 - smoothstep(0.70, 1.18, he);
  float hy = 1.0 - smoothstep(u_neckY-0.060, u_neckY+0.130, p.y);
  float hw = hm * hy * (1.0 - 0.85*wa);
  if(hw > 0.001){
    p = u_neckPivot + rot(p-u_neckPivot, u_tilt*0.26*hw, A);
    // yaw 흉내 : 수평 시프트 + 원근 수축
    p.x += u_turn*0.028*hw;
    p.x  = u_headC.x + (p.x-u_headC.x)*(1.0 - 0.070*abs(u_turn)*hw);
    p.y += (u_headY + u_squash*0.012)*hw;
    p.x += u_headX*hw;
  }

  /* ---- 머리카락 관성 ------------------------------------------------
     머리는 이미 위에서 회전했다. 머리카락은 한 박자 늦게 따라오므로
     그 차이만큼 되돌려 준다. 뿌리는 고정, 끝으로 갈수록 크게 흔들린다. */
  {
    float hm2  = 1.0 - smoothstep(0.80, 1.20, length((p-u_headC)/u_headRad));
    float face = 1.0 - smoothstep(0.70, 1.05, length((p-u_faceC)/u_faceRad));
    float depth= smoothstep(u_hairRoot, u_hairTip, p.y);      // 뿌리 0 -> 끝 1
    float hw2  = hm2 * depth * (1.0 - face*0.90);
    if(hw2 > 0.001){
      p = u_headC + rot(p - u_headC, u_hairSway*hw2, A);
      p.y += u_hairBob*hw2;
    }
  }

  /* ---- 옷 관성 : 아래로 갈수록 늦게 따라온다 ---- */
  {
    float cw = smoothstep(u_clothTop, 1.05, p.y);
    if(cw > 0.001) p = vec2(0.5,1.12) + rot(p - vec2(0.5,1.12), u_clothSway*cw, A);
  }

  /* ---- 몸통 호흡 ---- */
  float bw = 1.0 - hw;
  {
    float chest = 1.0 - smoothstep(0.46, 1.02, p.y);
    p.y -= u_breath*0.0065*bw*chest;
    p.x += u_breath*0.0050*bw*chest*(p.x-0.5)*2.2;
  }

  /* ---- 전역 ---- */
  p = vec2(0.5,1.06) + rot(p-vec2(0.5,1.06), u_sway, A);
  p.y += u_bounce;
  p.x += u_shakeX;

  vec2 px = p*u_imgPx*u_viewScale + u_viewOff;
  gl_Position = vec4(px.x/u_canvas.x*2.0-1.0, 1.0-px.y/u_canvas.y*2.0, 0.0, 1.0);
}`;

const FS = `
precision highp float;
varying vec2 v_uv;
uniform sampler2D u_tex;
uniform float u_chroma, u_blush, u_gloom, u_wire;
uniform vec2 u_cheekL,u_cheekR,u_cheekRad;
uniform vec2 u_headC;
/* VS와 이름이 같은 유니폼은 동일 유니폼으로 공유된다 */
uniform vec2  u_mouth, u_mouthRad, u_eyeL, u_eyeR, u_eyeLRad, u_eyeRRad;
uniform float u_tear, u_patch, u_patchSize;
uniform float u_mouthOpen, u_mouthCurve, u_mouthWidth, u_mouthCover, u_mouthDraw, u_mouthReal;

float ew(vec2 p, vec2 c, vec2 r){
  float t = length((p-c)/r);
  float s = max(0.0, 1.0 - t*t);
  return s*s;
}
void main(){
  if(u_wire > 0.5){ gl_FragColor = vec4(0.35,0.66,0.85,1.0); return; }
  vec4 c = texture2D(u_tex, v_uv);

  /* 크로마키 (그린스크린) */
  if(u_chroma > 0.001){
    float mx  = max(c.r, c.b);
    float d   = c.g - mx;                       // 초록 과잉량
    float tol = mix(0.26, 0.03, u_chroma);      // 슬라이더가 높을수록 강하게 제거
    float a   = clamp(1.0 - (d - tol*0.35)/max(0.02, tol), 0.0, 1.0);
    c.a *= a;
    if(d > 0.0) c.g = mx + d*0.15;              // despill (초록 물듦 제거)
  }

  /* ---- 원본 그림의 입이 이미 벌어져 있는 경우 ----
     입 위쪽 피부색을 직접 샘플링해서 덮어버린 뒤, 아래에서 입을 새로 그린다.
     이렇게 해야 '입 다문 상태'가 만들어진다. */
  if(u_mouthCover > 0.5 && c.a > 0.35){
    vec3 skin = texture2D(u_tex, u_mouth + vec2(0.0, -u_mouthRad.y*2.8)).rgb;
    float cov = 1.0 - smoothstep(0.60, 1.05,
                length((v_uv-u_mouth)/(u_mouthRad*vec2(1.20,1.45))));
    c.rgb = mix(c.rgb, skin, cov);
    /* 다물었을 때의 입술선 */
    float closed = 1.0 - smoothstep(0.03, 0.20, u_mouthOpen);
    float dxl = abs(v_uv.x-u_mouth.x)/u_mouthRad.x;
    float line = (1.0 - smoothstep(0.0, u_mouthRad.y*0.32, abs(v_uv.y-u_mouth.y)))
               * (1.0 - smoothstep(0.45, 1.0, dxl));
    c.rgb = mix(c.rgb, vec3(0.60,0.34,0.36), clamp(line,0.0,1.0)*closed*0.80);
  }

  /* ---- 입 : 원본 그림에 입이 없으므로 전부 여기서 그린다 ------------------
     다물었을 때는 입술선, 벌어지면 구강(안쪽 / 혀 / 윗니)으로 확장된다.
     입꼬리로 갈수록 뾰족해지고(taper), 웃으면 입꼬리만 올라간다.          */
  if(c.a > 0.35 && u_mouthDraw > 0.01){
    float op  = clamp(u_mouthOpen, 0.0, 1.0);
    float rx  = u_mouthRad.x*(0.95 + 0.24*u_mouthWidth + 0.12*u_mouthCurve);
    float ry  = u_mouthRad.y;
    float nx  = (v_uv.x - u_mouth.x)/rx;
    float inX = 1.0 - nx*nx;
    if(inX > 0.0){
      float taper = inX*sqrt(inX);
      float base  = u_mouth.y - u_mouthCurve*ry*1.35*(1.0-inX);
      float hUp   = ry*(0.05 + 0.46*op)*taper;
      float hLo   = ry*(0.05 + 1.10*op)*taper;
      float dy    = v_uv.y - base;
      float e     = ry*0.10;

      /* 실사는 원본에 입술이 이미 있으므로 입술선/하이라이트를 그리지 않는다 */
      float closed = (1.0 - smoothstep(0.04, 0.24, op)) * (1.0 - u_mouthReal);
      float line = (1.0 - smoothstep(0.0, ry*0.36, abs(dy))) * taper * closed;
      c.rgb = mix(c.rgb, vec3(0.44,0.22,0.24), clamp(line,0.0,1.0)*0.88*u_mouthDraw);
      /* 아랫입술 살짝 밝게 — 선 하나만 있으면 그은 것처럼 보인다 */
      float lipLo = (1.0 - smoothstep(0.0, ry*1.15, abs(dy - ry*1.30))) * taper * closed;
      c.rgb = mix(c.rgb, vec3(0.96,0.74,0.71), clamp(lipLo,0.0,1.0)*0.28*u_mouthDraw*(1.0-u_mouthReal));

      /* 구강 */
      float gate = mix(smoothstep(0.04,0.16,op), smoothstep(0.10,0.26,op), u_mouthReal);
      float cav = smoothstep(-hUp-e, -hUp+e, dy) * (1.0 - smoothstep(hLo-e, hLo+e, dy)) * gate;
      if(cav > 0.002){
        /* ---- 실사용 : 색을 상수로 박으면 남색 얼룩처럼 보인다.
               입술색·피부색을 사진에서 직접 뽑아 거기서 파생시킨다. ---- */
        /* 구강 안쪽은 피부색에서 파생시키면 회색이 된다. 실제 입 안은
           피부톤과 무관하게 어두운 적갈색이므로 고정값이 맞다. */
        vec3 cavR   = vec3(0.105,0.033,0.040);                  // 구강 안쪽
        vec3 tongR  = vec3(0.55,0.21,0.23);                     // 혀
        vec3 teethR = vec3(0.93,0.90,0.87);                     // 이

        vec3 cav0  = mix(vec3(0.195,0.048,0.070), cavR,   u_mouthReal);
        vec3 tong0 = mix(vec3(0.70,0.30,0.34),    tongR,  u_mouthReal);
        vec3 tee0  = mix(vec3(0.95,0.92,0.89),    teethR, u_mouthReal);

        vec3 col = cav0;
        float tongue = smoothstep(hLo*0.20, hLo*0.92, dy) * inX;
        col = mix(col, tong0, clamp(tongue,0.0,1.0)*0.85);
        float teethBand = mix(hUp*0.80 + ry*0.04, hUp*0.55 + ry*0.10, u_mouthReal);
        float teeth = (1.0 - smoothstep(0.0, teethBand, dy + hUp))
                    * mix(smoothstep(0.30,0.62,op), smoothstep(0.30,0.55,op), u_mouthReal);
        col = mix(col, tee0, clamp(teeth,0.0,1.0)*mix(0.85,0.75,u_mouthReal));
        c.rgb = mix(c.rgb, col, cav*u_mouthDraw);
      }
      /* 구강 안쪽 가장자리 음영 (바깥으로는 절대 번지지 않게) */
      float edge = (1.0 - smoothstep(0.0, ry*0.26, min(abs(dy + hUp), abs(dy - hLo))));
      edge *= cav * smoothstep(0.14, 0.40, op);
      c.rgb = mix(c.rgb, vec3(0.34,0.13,0.16), clamp(edge,0.0,1.0)*0.45*u_mouthDraw);
    }
  }

  /* ---- 궁예 모드 : 오른쪽 눈 안대 -------------------------------------
     텍스처 좌표계에 그리므로 고개를 돌리거나 기울여도 그대로 따라간다. */
  if(u_patch > 0.01 && c.a > 0.30){
    vec2  pc = u_eyeR + vec2(u_eyeRRad.x*0.06, u_eyeRRad.y*0.10);
    vec2  pr = u_eyeRRad * vec2(1.92, 2.85) * u_patchSize;

    /* 끈 : 안대에서 바깥쪽(머리 옆)으로 위·아래 두 갈래 */
    vec2 q = v_uv - pc;
    float band = 0.0;
    for(int k=0;k<2;k++){
      vec2  d   = (k==0) ? normalize(vec2(0.60,-0.80)) : normalize(vec2(0.76, 0.65));
      float len = (k==0) ? 0.20 : 0.115;          // 아래 끈은 턱을 넘지 않게 짧게
      float t = dot(q, d);
      float o = abs(q.x*(-d.y) + q.y*d.x);
      if(t > 0.0){
        float bw = pr.y*0.27;
        band = max(band, (1.0 - smoothstep(bw*0.55, bw, o))
                       * (1.0 - smoothstep(len*0.70, len, t)));
      }
    }
    c.rgb = mix(c.rgb, vec3(0.055,0.050,0.065), clamp(band,0.0,1.0)*u_patch);

    /* 안대 본체 : 모서리가 둥근 사각(초타원) */
    vec2  pq = q / pr;
    float kk = pow(abs(pq.x), 2.7) + pow(abs(pq.y), 2.7);
    float m  = (1.0 - smoothstep(0.80, 1.00, kk)) * u_patch;
    if(m > 0.002){
      vec3 leather = vec3(0.070,0.062,0.078);
      /* 왼쪽 위 광택 */
      float sheen = (1.0 - smoothstep(0.0, 1.3, length(pq - vec2(-0.42,-0.46))));
      leather = mix(leather, vec3(0.26,0.25,0.30), sheen*0.55);
      /* 아래쪽 그림자 */
      leather *= 1.0 - smoothstep(0.1, 1.0, pq.y)*0.35;
      c.rgb = mix(c.rgb, leather, m);
      /* 테두리 스티치 */
      float ring = (1.0 - smoothstep(0.86, 1.00, kk)) - (1.0 - smoothstep(0.66, 0.80, kk));
      c.rgb = mix(c.rgb, vec3(0.34,0.31,0.36), clamp(ring,0.0,1.0)*0.55*u_patch);
    }
  }

  /* 눈물 */
  if(u_tear > 0.01){
    vec2 dl = u_eyeL + vec2(-u_eyeLRad.x*0.62, u_eyeLRad.y*2.0 + u_tear*0.045);
    vec2 dr = u_eyeR + vec2( u_eyeRRad.x*0.62, u_eyeRRad.y*2.0 + u_tear*0.045);
    float td = max(1.0 - smoothstep(0.55,1.0, length((v_uv-dl)/(u_eyeLRad*vec2(0.28,0.75)))),
                   1.0 - smoothstep(0.55,1.0, length((v_uv-dr)/(u_eyeRRad*vec2(0.28,0.75)))));
    c.rgb = mix(c.rgb, vec3(0.66,0.85,0.97), clamp(td,0.0,1.0)*u_tear*0.80);
  }

  /* 볼 홍조 */
  float b = max(ew(v_uv, u_cheekL, u_cheekRad), ew(v_uv, u_cheekR, u_cheekRad));
  c.rgb = mix(c.rgb, mix(c.rgb, vec3(1.0,0.46,0.52), 0.22), b*u_blush);

  /* 침울 : 얼굴 상단에 그림자 */
  float sh = smoothstep(0.02, 0.30, v_uv.y) * (1.0 - smoothstep(0.24, 0.42, v_uv.y));
  c.rgb *= 1.0 - u_gloom*0.42*sh;
  c.rgb = mix(c.rgb, c.rgb*vec3(0.80,0.85,1.05), u_gloom*0.5);

  if(c.a < 0.01) discard;
  gl_FragColor = vec4(c.rgb*c.a, c.a);   // premultiplied
}`;

function sh(type,src){
  const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s);
  if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
const prog = gl.createProgram();
gl.attachShader(prog, sh(gl.VERTEX_SHADER,VS));
gl.attachShader(prog, sh(gl.FRAGMENT_SHADER,FS));
gl.linkProgram(prog);
if(!gl.getProgramParameter(prog,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
gl.useProgram(prog);

const U = new Proxy({},{ get:(t,k)=> (t[k] !== undefined ? t[k] : (t[k]=gl.getUniformLocation(prog,'u_'+k))) });
// 값이 undefined/NaN 이면 메쉬가 통째로 날아간다 -> 0 으로 방어
const f1 = (loc,v)=>gl.uniform1f(loc, Number.isFinite(v)?v:0);

/* ---- 메쉬 생성 ---- */
const NX=100, NY=150;
(function buildMesh(){
  const verts = new Float32Array((NX+1)*(NY+1)*2);
  let k=0;
  for(let j=0;j<=NY;j++) for(let i=0;i<=NX;i++){ verts[k++]=i/NX; verts[k++]=j/NY; }
  const idx = new Uint16Array(NX*NY*6);
  let m=0;
  for(let j=0;j<NY;j++) for(let i=0;i<NX;i++){
    const a=j*(NX+1)+i, b=a+1, c=a+NX+1, d=c+1;
    idx[m++]=a; idx[m++]=b; idx[m++]=c; idx[m++]=b; idx[m++]=d; idx[m++]=c;
  }
  const wire = new Uint16Array(NX*NY*4);
  let w=0;
  for(let j=0;j<NY;j+=3) for(let i=0;i<NX;i+=3){
    const a=j*(NX+1)+i, b=a+3, c=a+(NX+1)*3;
    wire[w++]=a; wire[w++]=b; wire[w++]=a; wire[w++]=c;
  }
  const vb=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,vb);
  gl.bufferData(gl.ARRAY_BUFFER,verts,gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(prog,'a_uv');
  gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  const ib=gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,idx,gl.STATIC_DRAW);
  window.__idxCount = idx.length;
  const wb=gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,wb);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,wire,gl.STATIC_DRAW);
  window.__ib=ib; window.__wb=wb; window.__wireCount=wire.length;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);
})();

/* ---- 텍스처 ---- */
const tex = gl.createTexture();
let IMG_W=430, IMG_H=676, texReady=false;
function loadImage(src){
  const im = new Image();
  im.crossOrigin='anonymous';
  im.onload = ()=>{
    IMG_W=im.naturalWidth; IMG_H=im.naturalHeight;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    texReady=true;
  };
  im.src = src;
}
loadImage(COSTUMES[0].src);

/* =====================  상태 / 애니메이션  ===================== */
const S = {};                       // 현재 표시값 (스프링)
const T = {};                       // 목표값
PARAMS.forEach(k=>{ S[k]=EMO.neutral[k]; T[k]=EMO.neutral[k]; });
const V = {}; PARAMS.forEach(k=>V[k]=0);
const FAST_PARAMS = {mouthOpen:1, mouthCurve:1, mouthWidth:1, eyeOpen:1, eyeSmile:1, eyeTilt:1, brow:1};
/* 실사 모드 채널별 배율 — 사진에서 안전하게 움직일 수 있는 한도 */
const REAL_SCALE = {
  eyeOpen:1.00, eyeSmile:0.60, eyeTilt:1.20, tear:0.00, brow:1.00,
  mouthOpen:0.60, mouthCurve:0.50, mouthWidth:0.35,
  tilt:0.70, turn:0.70, headY:0.70, blush:0.30, gloom:0.45,
  armA:0.85, armB:0.85
};

let emotion='neutral', intensity=0.85, manual=false;
let bubbleOn=true;      // 말풍선 표시 여부 (loadSettings 보다 먼저 선언돼야 한다)
let patchOn=false;      // 궁예 모드(안대)
let hudOpen=true;       // 좌측 패널 펼침 여부
let ctxOpen=false;      // 컨텍스트 패널 — 처음엔 접혀 있다
let autoScene=true;     // 시간표에 따라 배경/의상 자동 전환
/* 하루 일과. from~to (분). 마지막 항목은 자정을 넘어간다 */
const SCHEDULE = [
  {from:'07:00', to:'08:30', bg:'정문'},
  {from:'08:31', to:'10:00', bg:'공장'},
  {from:'10:01', to:'11:30', bg:'회의실'},
  {from:'11:31', to:'13:30', bg:'정문'},
  {from:'13:31', to:'14:30', bg:'회의실'},
  {from:'14:31', to:'16:50', bg:'공장'},
  {from:'16:51', to:'17:10', bg:'회의실'},
  {from:'17:11', to:'19:30', bg:'테라스'},
  {from:'19:31', to:'06:59', bg:'집'},
];
let badgeOn=true;       // 목에 건 사원증
const BADGE = {name:'미라', en:'MIRA', dept:'물류기술팀 · AMHS', id:'SKH-2026-0417'};
const logoImg = new Image(); logoImg.src = "assets/logo.png";
let badgeA=0, badgeAV=0;   // 사원증 흔들림(2차 스프링)
let eyeFollow=true;     // 마우스 시선 추적
let mouseGaze=[0,0], mouseLast=0;
const DOCS = [];        // 참고 자료 {name,text,on} — 사용처보다 먼저 선언돼야 한다
let docBudget = 6000;   // 프롬프트에 넣을 최대 글자수
let ctxLimit  = 32768;  // 모델 컨텍스트 한도(사용자 지정)
let keepMsgs  = 12;     // 프롬프트에 붙일 최근 대화 메시지 수
const history = [];     // LLM 대화 기록 (사용처보다 먼저 선언돼야 한다)
let sessions = [];      // 지난 세션 목록
let curSession = null;  // 현재 세션
const SESS_KEY = 'avatar2d.sessions.v1';   // 사용처보다 먼저 선언 (TDZ 방지)
let SRV_CTX=null, ctxFetchTimer=null;      // 서버 컨텍스트 계측 캐시 (TDZ 방지: 상단 선언)
let sessPushTimer=null, setSrvTimer=null;  // 서버 저장 디바운스 타이머
const SESS_MAX = 30;
const CTX_COLORS = {persona:'#d94a5a', docs:'#5aa9d9', rules:'#8f93b5', history:'#4ec9a0', input:'#e0a45c'};
const CTX_LABEL  = {persona:'페르소나', docs:'참고 자료', rules:'출력 규칙', history:'대화 기록', input:'입력'};
let personaBackup='';   // 궁예 모드 진입 전 페르소나 보관
let blinkT=1.2, blinkPhase=0, blinkOne=-1;
let gaze=[0,0], gazeT=[0,0], gazeTimer=1.5;
let talk=0, talkEnv=0, talkTgt=0, talkSyl=0, motionT=0, motion='none';
let symText='', symT=0;
let breathAmp=1, idleAmp=1, blinkAmp=1;
/* 관성(2차 스프링) — 머리카락·옷이 본체를 한 박자 늦게 따라온다 */
let hairA=0, hairAV=0, hairB=0, hairBV=0, clothA=0, clothAV=0;
let view={zoom:1, oy:0, chroma:0, wire:0, mouthCover:0, browAmp:0.25, headAmp:0.5, patch:0, patchSize:1.0,
              hairAmp:1.0, clothAmp:1.0, realScale:1.0, mouthDraw:1.0, mouthWarp:1.0, tearAmp:1.0, mouthReal:0.0, mouthMax:1.0};

function setEmotion(name, inten, mot){
  if(!EMO[name]) name='neutral';
  emotion=name; manual=false;
  if(typeof inten==='number') intensity=Math.max(0,Math.min(1,inten));
  const base=EMO.neutral, e=EMO[name];
  /* 실사는 채널마다 안전 범위가 다르다.
     입·홍조는 확 줄이고, 눈꼬리·눈썹·눈 크기는 오히려 살려야 감정이 읽힌다. */
  const real = view.mouthReal > 0.5;
  const amt  = 0.35 + 0.65*intensity;
  PARAMS.forEach(k=>{
    const sc = real ? (REAL_SCALE[k] !== undefined ? REAL_SCALE[k] : 0.8) : 1;
    T[k] = base[k] + (e[k]-base[k])*amt*sc;
  });
  if(mot && MOTION[mot] && mot!=='none'){ motion=mot; motionT=0; }
  if(e.sym){ symText=e.sym; symT=0; }
  document.documentElement.style.setProperty('--bubbleAccent', EMO_COLOR[name] || '#7d8899');
  syncEmoUI();
}
function trigger(mot){ motion=mot; motionT=0; }

/* ---------- 프레임 루프 ---------- */
let last=performance.now(), t=0;
function frame(now){
  const dt=Math.min(0.05,(now-last)/1000); last=now; t+=dt;
  step(dt); draw(); drawFX(dt);
  requestAnimationFrame(frame);
}
function step(dt){
  /* 스프링 보간 */
  // 입·눈은 빠르게, 고개·몸은 느리게 — 같은 속도로 움직이면 늘어져 보인다
  PARAMS.forEach(k=>{
    const f = FAST_PARAMS[k];
    const stiff = f?230:90, damp = f?28:15;
    const a = stiff*(T[k]-S[k]) - damp*V[k];
    V[k]+=a*dt; S[k]+=V[k]*dt;
  });

  /* 자동 눈깜빡임 */
  blinkT-=dt;
  if(blinkT<=0 && blinkPhase<=0 && blinkAmp>0){
    blinkPhase=1; blinkOne = Math.random()<0.12 ? (Math.random()<0.5?0:1) : -1;
    blinkT = 1.6 + Math.random()*4.0/Math.max(0.15,blinkAmp);
  }
  if(blinkPhase>0){ blinkPhase -= dt/0.155; if(blinkPhase<0) blinkPhase=0; }
  // 1 -> 0 으로 진행. 감기는 구간(1.0~0.72)은 짧고, 뜨는 구간(0.72~0)은 길다
  const bp = blinkPhase;
  const bcurve = bp<=0 ? 0 : (bp>0.72 ? (1.0-bp)/0.28 : bp/0.72);
  let bL = bcurve*blinkAmp, bR = bcurve*blinkAmp;
  if(blinkOne===0) bR=0; if(blinkOne===1) bL=0;
  if(S.eyeOpen>1.2){ bL*=0.25; bR*=0.25; }   // 놀란 상태에선 덜 감음

  /* 시선 */
  const mouseFresh = eyeFollow && (performance.now()-mouseLast < 2500);
  if(mouseFresh){
    gazeT = mouseGaze;              // 마우스를 따라본다
    gazeTimer = 0.4;                // 놓치면 곧바로 무작위 시선으로 복귀
  }else{
    gazeTimer-=dt;
    if(gazeTimer<=0){
      gazeTimer = 1.0+Math.random()*3.0;
      gazeT = (Math.random()<0.45) ? [0,0] : [(Math.random()*2-1)*0.9,(Math.random()*2-1)*0.5];
    }
  }
  gaze[0]+= (gazeT[0]-gaze[0])*Math.min(1,dt*8);
  gaze[1]+= (gazeT[1]-gaze[1])*Math.min(1,dt*8);

  /* 말하기 (입 플랩) */
  // 일정한 사인파는 기계처럼 보인다 -> 음절 단위로 목표 개구량을 갱신
  if(talk>0) talk-=dt;
  talkSyl-=dt;
  if(talkSyl<=0){
    talkSyl = 0.075 + Math.random()*0.095;
    talkTgt = talk>0 ? (Math.random()<0.18 ? 0.06 : 0.30+Math.random()*0.70) : 0;
  }
  if(talk<=0) talkTgt=0;
  talkEnv += (talkTgt-talkEnv)*Math.min(1, dt*(talkTgt>talkEnv?30:17));

  /* idle 노이즈 */
  const n1=Math.sin(t*0.63)*0.6+Math.sin(t*1.31+1.7)*0.4;
  const n2=Math.sin(t*0.47+2.1)*0.6+Math.sin(t*0.91+0.4)*0.4;

  /* 모션 */
  motionT+=dt;
  let mNodY=0,mHeadX=0,mBounce=0,mShake=0,mTilt=0,mSquash=0,mArmA=0,mArmB=0,mLift=0;
  const mt=motionT;
  const decay=(d)=>Math.max(0,1-mt/d);
  const ease=(d)=>{const k=Math.min(1,mt/d); return Math.sin(k*Math.PI);};  // 0→1→0
  switch(motion){
    case 'nod':    mNodY = Math.sin(mt*13)*0.018*decay(0.9); break;
    case 'shake':  mHeadX= Math.sin(mt*17)*0.014*decay(0.8); break;
    case 'bounce': mBounce=-Math.abs(Math.sin(mt*9))*0.018*decay(1.1); mSquash=Math.sin(mt*9)*0.6*decay(1.1);
                   mArmA=Math.sin(mt*9)*0.045*decay(1.1); mArmB=-Math.sin(mt*9+1)*0.035*decay(1.1); break;
    case 'jump':   mBounce=-Math.abs(Math.sin(mt*6.0))*0.050*decay(1.0); mSquash=-Math.cos(mt*6)*0.9*decay(1.0);
                   mArmA=-0.07*ease(1.0); mArmB=-0.05*ease(1.0); break;
    case 'lean':   mTilt = ease(2.0)*0.32; mArmB=ease(2.0)*0.03; break;
    case 'shiver': mShake= Math.sin(mt*38)*0.0040*decay(1.4); mArmA=Math.sin(mt*36)*0.012*decay(1.4); break;
    case 'pop':    mBounce=-Math.exp(-mt*6)*0.032; mSquash=-Math.exp(-mt*6)*1.4;
                   mArmA=Math.exp(-mt*5)*0.10; mLift=Math.exp(-mt*5)*0.8; break;
    /* --- 손동작 --- */
    case 'wave':   mArmA = Math.sin(mt*11)*0.13*decay(1.8); mLift = ease(1.8)*1.0; break;
    case 'handup': mArmA = ease(2.2)*0.17; mLift = ease(2.2)*1.3; break;
    case 'tap':    mArmA = (Math.sin(mt*20)*0.5+0.5)*0.030*decay(1.6); mLift = ease(1.6)*0.25; break;
    case 'cross':  mArmB = ease(1.8)*0.075; mArmA = -ease(1.8)*0.045; break;
  }
  if(mt>2.4) motion='none';

  /* 유니폼 값 확정 */
  R.eyeOpen = S.eyeOpen;
  R.eyeSmile= S.eyeSmile;
  R.eyeTilt = S.eyeTilt;
  R.tear    = S.tear;
  R.blinkL  = bL; R.blinkR = bR;
  R.brow    = S.brow;
  R.mouthOpen  = Math.max(0, Math.min(view.mouthMax, S.mouthOpen + talkEnv*0.55));
  R.mouthCurve = S.mouthCurve;
  R.mouthWidth = S.mouthWidth + talkEnv*0.10*Math.sin(t*3.1);
  const HA = view.headAmp;
  R.tilt  = (S.tilt + n1*0.035*idleAmp)*HA + mTilt*HA;
  R.turn  = (S.turn + n2*0.060*idleAmp)*HA + (mouseFresh ? gaze[0]*0.10*HA : 0);
  R.headY = (S.headY + Math.sin(t*1.1)*0.0022*idleAmp + mNodY)*HA - talkEnv*0.0025
          + (mouseFresh ? gaze[1]*0.0045*HA : 0);
  R.headX = (n2*0.0014*idleAmp + mHeadX)*HA;
  R.breath= (Math.sin(t*1.35)*0.5+0.5)*breathAmp + (talkEnv*0.25);
  R.sway  = Math.sin(t*0.55)*0.004*idleAmp*HA;
  /* 팔 : 감정 포즈 + 호흡 연동 idle + 말할 때 미세 제스처 + 모션 */
  const breathe = Math.sin(t*1.35);
  R.armAAng = S.armA + breathe*0.011*idleAmp + Math.sin(t*0.43+1.2)*0.013*idleAmp
              + talkEnv*0.022 + mArmA;
  R.armBAng = S.armB + Math.sin(t*1.35+0.9)*0.008*idleAmp + Math.sin(t*0.37)*0.010*idleAmp + mArmB;
  R.armALift= mLift + talkEnv*0.15;
  R.bounce= mBounce;
  R.shakeX= mShake;
  R.squash= mSquash;
  /* ---- 위험/초위험 : 몸을 좌우로만 옮긴다 ------------------------------
     기울이거나 통통 튀지 않는다. 방향키 누른 것처럼 등속으로 좌↔우.
     삼각파(2/pi*asin(sin)) 라서 이동 속도가 일정하다.
     u_shakeX 는 메쉬 전체를 평행이동시키는 유니폼이라 그대로 쓴다. */
  {
    const P = alarm && alarm.lv && alarm.lv.pace;
    if(P){
      panicT += dt;
      const tri  = Math.asin(Math.sin(panicT*P.freq*Math.PI*2)) * (2/Math.PI);
      const ramp = Math.min(1, panicT*1.2);            // 시작할 때만 부드럽게
      R.shakeX += tri*P.amp*ramp;
    }else{
      panicT = 0;
    }
  }
  /* ---- 관성 ----------------------------------------------------------
     목표(머리 각도)를 향해 스프링으로 따라가되, 화면에는 '목표 - 현재'
     즉 아직 못 따라온 차이를 흔들림으로 그린다.                        */
  {
    const amp = view.hairAmp;
    // 좌우 흔들림 : 고개 기울임 + 전신 sway 를 함께 따라간다
    const tgtA = R.tilt*0.55 + R.sway*1.6 + R.headX*3.0;
    hairAV += (95.0*(tgtA - hairA) - 12.0*hairAV)*dt;  hairA += hairAV*dt;
    R.hairSway = (hairA - tgtA)*0.62*amp + Math.sin(t*0.83)*0.0045*idleAmp*amp;

    // 위아래 출렁임 : 점프·통통·끄덕임
    const tgtB = R.bounce + R.headY*1.2 + R.squash*0.004;
    hairBV += (150.0*(tgtB - hairB) - 15.0*hairBV)*dt;  hairB += hairBV*dt;
    R.hairBob = (hairB - tgtB)*1.35*amp;

    // 옷 : 더 무겁고 느리게. 몸 흔들림 + 점프 + 팔 움직임에 반응한다
    const tgtC = R.sway*1.4 + R.shakeX*2.5 + R.bounce*2.2
               + (R.armAAng - R.armBAng)*0.10;
    clothAV += (46.0*(tgtC - clothA) - 8.0*clothAV)*dt;  clothA += clothAV*dt;
    R.clothSway = (clothA - tgtC)*0.95*view.clothAmp
                + Math.sin(t*0.61+1.4)*0.0030*idleAmp*view.clothAmp;
  }

  R.blush = S.blush;
  R.gloom = S.gloom;
  R.gaze  = gaze;
  symT += dt;
}
const R = {};

/* ---------- 뷰 변환 (JS/셰이더 공유) ---------- */
let VIEW={scale:1,ox:0,oy:0,cw:0,ch:0};
function computeView(){
  const r=glc.getBoundingClientRect();
  const dpr=Math.min(2, window.devicePixelRatio||1);
  const cw=Math.max(1,Math.round(r.width*dpr)), ch=Math.max(1,Math.round(r.height*dpr));
  if(glc.width!==cw||glc.height!==ch){ glc.width=cw; glc.height=ch; }
  const fx=document.getElementById('fx');
  if(fx.width!==cw||fx.height!==ch){ fx.width=cw; fx.height=ch; }
  const s = Math.min(cw/IMG_W, ch/IMG_H)*0.95*view.zoom;
  VIEW={scale:s, ox:(cw-IMG_W*s)/2, oy:(ch-IMG_H*s)/2 + view.oy*ch, cw, ch, dpr};
}
// 이미지 정규화좌표 -> 캔버스 CSS px
function imgToCss(u,v){
  return [ (u*IMG_W*VIEW.scale+VIEW.ox)/VIEW.dpr, (v*IMG_H*VIEW.scale+VIEW.oy)/VIEW.dpr ];
}
function cssToImg(x,y){
  return [ (x*VIEW.dpr-VIEW.ox)/(IMG_W*VIEW.scale), (y*VIEW.dpr-VIEW.oy)/(IMG_H*VIEW.scale) ];
}

function draw(){
  computeView();
  gl.viewport(0,0,VIEW.cw,VIEW.ch);
  gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT);
  if(!texReady) return;
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.useProgram(prog);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,tex);
  gl.uniform1i(U.tex,0);

  gl.uniform2f(U.canvas,VIEW.cw,VIEW.ch);
  gl.uniform2f(U.imgPx,IMG_W,IMG_H);
  gl.uniform2f(U.viewOff,VIEW.ox,VIEW.oy);
  gl.uniform1f(U.viewScale,VIEW.scale);
  gl.uniform1f(U.aspect,IMG_W/IMG_H);

  gl.uniform2fv(U.eyeL,CFG.eyeL); gl.uniform2fv(U.eyeR,CFG.eyeR);
  gl.uniform2fv(U.eyeLRad,CFG.eyeL_rad); gl.uniform2fv(U.eyeRRad,CFG.eyeR_rad);
  gl.uniform2fv(U.mouth,CFG.mouth); gl.uniform2fv(U.mouthRad,CFG.mouth_rad);
  gl.uniform2fv(U.neckPivot,CFG.neckPivot); gl.uniform2fv(U.headC,CFG.headC);
  gl.uniform2fv(U.headRad,CFG.headRad);
  gl.uniform2fv(U.faceC,CFG.faceC); gl.uniform2fv(U.faceRad,CFG.faceRad);
  gl.uniform1f(U.hairRoot,CFG.hairRoot); gl.uniform1f(U.hairTip,CFG.hairTip);
  gl.uniform1f(U.clothTop,CFG.clothTop);
  f1(U.hairSway,R.hairSway); f1(U.hairBob,R.hairBob); f1(U.clothSway,R.clothSway);
  gl.uniform2fv(U.armA,CFG.armA); gl.uniform2fv(U.armARad,CFG.armA_rad); gl.uniform2fv(U.armAPiv,CFG.armA_piv);
  gl.uniform2fv(U.armB,CFG.armB); gl.uniform2fv(U.armBRad,CFG.armB_rad); gl.uniform2fv(U.armBPiv,CFG.armB_piv);
  gl.uniform1f(U.armAAng,R.armAAng); gl.uniform1f(U.armBAng,R.armBAng); gl.uniform1f(U.armALift,R.armALift);
  gl.uniform1f(U.neckY,CFG.neckY); gl.uniform1f(U.browDy,CFG.brow_dy);
  gl.uniform2fv(U.cheekL,CFG.cheekL); gl.uniform2fv(U.cheekR,CFG.cheekR);
  gl.uniform2fv(U.cheekRad,CFG.cheek_rad);

  gl.uniform1f(U.eyeOpen,R.eyeOpen); gl.uniform1f(U.eyeSmile,R.eyeSmile);
  gl.uniform1f(U.blinkL,R.blinkL); gl.uniform1f(U.blinkR,R.blinkR);
  gl.uniform1f(U.brow,R.brow); gl.uniform1f(U.browAmp,view.browAmp);
  f1(U.eyeTilt,R.eyeTilt); f1(U.tear, R.tear*view.tearAmp);
  f1(U.patch,view.patch); f1(U.patchSize,view.patchSize);
  gl.uniform1f(U.mouthOpen,R.mouthOpen); gl.uniform1f(U.mouthCurve,R.mouthCurve);
  gl.uniform1f(U.mouthWidth,R.mouthWidth);
  gl.uniform1f(U.tilt,R.tilt); gl.uniform1f(U.turn,R.turn);
  gl.uniform1f(U.headY,R.headY); gl.uniform1f(U.headX,R.headX);
  gl.uniform1f(U.breath,R.breath); gl.uniform1f(U.sway,R.sway);
  gl.uniform1f(U.bounce,R.bounce); gl.uniform1f(U.shakeX,R.shakeX);
  gl.uniform1f(U.squash,R.squash);
  gl.uniform2fv(U.gaze,R.gaze);
  gl.uniform1f(U.chroma,view.chroma);
  gl.uniform1f(U.mouthCover, view.mouthCover);
  f1(U.mouthDraw, view.mouthDraw); f1(U.mouthWarp, view.mouthWarp);
  f1(U.mouthReal, view.mouthReal); f1(U.mouthRealW, view.mouthReal);
  gl.uniform1f(U.blush,R.blush); gl.uniform1f(U.gloom,R.gloom);

  gl.uniform1f(U.wire,0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, window.__ib);
  gl.drawElements(gl.TRIANGLES, window.__idxCount, gl.UNSIGNED_SHORT, 0);

  if(view.wire>0.5){
    gl.uniform1f(U.wire,1);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, window.__wb);
    gl.drawElements(gl.LINES, window.__wireCount, gl.UNSIGNED_SHORT, 0);
  }
}

/* ---------- 이펙트 오버레이 (심볼) ---------- */
const fxc=document.getElementById('fx'), fx=fxc.getContext('2d');
function ellipse(cx,cy,rx,ry,stroke,fill,dash){
  const d=VIEW.dpr;
  fx.save();
  fx.setLineDash(dash||[]);
  fx.lineWidth=1.5*d;
  fx.strokeStyle=stroke;
  fx.beginPath();
  fx.ellipse(cx*d, cy*d, Math.max(1,rx*d), Math.max(1,ry*d), 0, 0, Math.PI*2);
  if(fill){ fx.fillStyle=fill; fx.fill(); }
  fx.stroke();
  fx.restore();
}
/* 캘리브레이션 중에는 실제로 변형되는 영역을 그려준다 — 안 보이면 맞출 수가 없다 */
function drawRegions(){
  const sx = IMG_W*VIEW.scale/VIEW.dpr, sy = IMG_H*VIEW.scale/VIEW.dpr;
  const R_ = (k)=>CFG[k];
  // 실선 = 지금 조절 중인 크기(핸들 위치), 점선 = 변형이 번지는 범위
  const put=(ck,rk,color,faint,mulx,muly)=>{
    const c=CFG[ck], r=CFG[rk]; if(!c||!r) return;
    const [x,y]=imgToCss(c[0],c[1]);
    ellipse(x,y, r[0]*sx, r[1]*sy, color, faint);
    if(mulx) ellipse(x,y, r[0]*sx*mulx, r[1]*sy*muly, color.replace(/[\d.]+\)$/,'.30)'), null, [4,5]);
  };
  // 입 : 실제 셰이더가 쓰는 입술/턱 영역까지 같이 표시
  const m=CFG.mouth, mr=CFG.mouth_rad;
  if(m&&mr){
    const [mx,my]=imgToCss(m[0],m[1]);
    ellipse(mx,my, mr[0]*sx,        mr[1]*sy,        'rgba(255,90,110,.95)', 'rgba(255,90,110,.14)');
    ellipse(mx,my, mr[0]*sx*1.7,    mr[1]*sy*2.4,    'rgba(255,90,110,.45)', null, [4,4]);
    const [jx,jy]=imgToCss(m[0], m[1]+mr[1]*2.0);
    ellipse(jx,jy, mr[0]*sx*3.0,    mr[1]*sy*5.0,    'rgba(255,170,90,.35)', null, [3,6]);
  }
  put('eyeL','eyeL_rad','rgba(120,200,255,.95)','rgba(120,200,255,.12)',1.35,2.00);
  put('eyeR','eyeR_rad','rgba(120,200,255,.95)','rgba(120,200,255,.12)',1.35,2.00);
  put('headC','headRad','rgba(200,200,255,.35)');
  put('faceC','faceRad','rgba(255,220,120,.75)','rgba(255,220,120,.07)');
  put('cheekL','cheek_rad','rgba(255,140,180,.40)');
  put('cheekR','cheek_rad','rgba(255,140,180,.40)');
  put('armA','armA_rad','rgba(140,255,190,.65)','rgba(140,255,190,.08)');
  put('armB','armB_rad','rgba(140,255,190,.65)','rgba(140,255,190,.08)');
  // 팔꿈치 축 표시
  [['armA','armA_piv'],['armB','armB_piv']].forEach(([a,b])=>{
    if(!CFG[a]||!CFG[b]) return;
    const d=VIEW.dpr, [x1,y1]=imgToCss(...CFG[a]), [x2,y2]=imgToCss(...CFG[b]);
    fx.save(); fx.setLineDash([3,5]); fx.lineWidth=1.2*d;
    fx.strokeStyle='rgba(140,255,190,.5)';
    fx.beginPath(); fx.moveTo(x1*d,y1*d); fx.lineTo(x2*d,y2*d); fx.stroke(); fx.restore();
  });
}

/* 팔이 회전한 뒤의 '손' 위치를 JS 에서 재현한다 (셰이더와 같은 계산) */
/* ---------- 사원증 : 목걸이 + 카드 ----------
   메쉬 밖의 소품이라 캔버스에 직접 그린다. 옷 관성(clothSway)·몸통 sway 를
   그대로 따라가고, 카드는 한 박자 늦게 흔들린다(2차 스프링). */
function bodyPt(u,v){
  const A=IMG_W/IMG_H;
  const rot=(dx,dy,a)=>{ const ex=dx*A, s=Math.sin(a), c=Math.cos(a);
    return [(ex*c-dy*s)/A, ex*s+dy*c]; };
  let x=u, y=v;
  // 옷 관성
  const cw = Math.min(1, Math.max(0, (y-CFG.clothTop)/(1.05-CFG.clothTop)));
  const cs = cw*cw*(3-2*cw);
  if(cs>0.001){ const d=rot(x-0.5, y-1.12, (R.clothSway||0)*cs); x=0.5+d[0]; y=1.12+d[1]; }
  // 전역
  const d2=rot(x-0.5, y-1.06, R.sway||0); x=0.5+d2[0]; y=1.06+d2[1];
  y += (R.bounce||0); x += (R.shakeX||0);
  return imgToCss(x,y);
}
function drawBadge(dt){
  if(!badgeOn || !CFG.neckPivot) return;
  const d=VIEW.dpr, U=IMG_H*VIEW.scale/VIEW.dpr;   // 이미지 세로 1.0 = U px
  const nk=CFG.neckPivot;
  const L = bodyPt(nk[0]-0.048, nk[1]+0.020);      // 왼쪽 어깨
  const Rt= bodyPt(nk[0]+0.048, nk[1]+0.018);      // 오른쪽 어깨
  const C = bodyPt(nk[0]+0.004, nk[1]+0.150);      // 클립 위치

  // 카드는 클립에서 한 박자 늦게 흔들린다
  const tgt = (R.clothSway||0)*2.4 + (R.sway||0)*1.2 + (R.shakeX||0)*3.0;
  badgeAV += (120.0*(tgt-badgeA) - 13.0*badgeAV)*dt;  badgeA += badgeAV*dt;
  const ang = (badgeA - tgt)*1.1 + tgt*0.5;

  fx.save();
  fx.lineJoin='round'; fx.lineCap='round';
  // ---- 목줄 ----
  const strap=(P)=>{
    fx.beginPath();
    fx.moveTo(P[0]*d, P[1]*d);
    fx.quadraticCurveTo((P[0]*0.55+C[0]*0.45)*d, (P[1]*0.35+C[1]*0.65)*d, C[0]*d, C[1]*d);
    fx.lineWidth=Math.max(1.2, U*0.0110)*d; fx.strokeStyle='#1d2430'; fx.stroke();
    fx.lineWidth=Math.max(0.6, U*0.0045)*d; fx.strokeStyle='rgba(255,255,255,.14)'; fx.stroke();
  };
  strap(L); strap(Rt);
  // ---- 클립 ----
  fx.fillStyle='#b9c0cb';
  const cl=U*0.0080*d;
  fx.beginPath(); fx.roundRect(C[0]*d-cl*0.8, C[1]*d-cl*0.4, cl*1.6, cl*1.9, cl*0.5); fx.fill();

  // ---- 카드 ----
  const w=U*0.078, hgt=U*0.102;
  fx.translate(C[0]*d, (C[1]+U*0.012)*d);
  fx.rotate(ang*1.5);
  const x0=-w*0.5*d, y0=0, W=w*d, H=hgt*d, r=U*0.010*d;
  fx.shadowColor='rgba(0,0,0,.35)'; fx.shadowBlur=6*d; fx.shadowOffsetY=2*d;
  fx.fillStyle='#fdfdfd';
  fx.beginPath(); fx.roundRect(x0,y0,W,H,r); fx.fill();
  fx.shadowColor='transparent'; fx.shadowBlur=0; fx.shadowOffsetY=0;
  fx.lineWidth=Math.max(0.6,U*0.0016)*d; fx.strokeStyle='#c9ced8'; fx.stroke();
  fx.save(); fx.beginPath(); fx.roundRect(x0,y0,W,H,r); fx.clip();
  // 로고
  if(logoImg.complete && logoImg.naturalWidth){
    const lw=W*0.62, lh=lw*logoImg.naturalHeight/logoImg.naturalWidth;
    fx.drawImage(logoImg, x0+W*0.09, y0+H*0.07, lw, lh);
  }
  // 사진칸
  const pw=W*0.30, ph=H*0.28, px=x0+W*0.09, py=y0+H*0.36;
  fx.fillStyle='#dfe4ec'; fx.beginPath(); fx.roundRect(px,py,pw,ph,r*0.5); fx.fill();
  fx.fillStyle='#aab3c2';
  fx.beginPath(); fx.arc(px+pw*0.5, py+ph*0.36, ph*0.17, 0, Math.PI*2); fx.fill();
  fx.beginPath(); fx.ellipse(px+pw*0.5, py+ph*1.02, pw*0.30, ph*0.28, 0, Math.PI, 0); fx.fill();
  // 이름
  fx.textAlign='left'; fx.textBaseline='alphabetic'; fx.fillStyle='#20262f';
  fx.font=`700 ${Math.max(6,H*0.135)}px "Malgun Gothic","Apple SD Gothic Neo",sans-serif`;
  fx.fillText(BADGE.name, px+pw+W*0.07, py+ph*0.42);
  fx.fillStyle='#7b8492';
  fx.font=`500 ${Math.max(5,H*0.088)}px sans-serif`;
  fx.fillText(BADGE.en, px+pw+W*0.07, py+ph*0.78);
  // 부서
  fx.fillStyle='#5c6572';
  let dfs = Math.max(5, H*0.080), maxW = W*0.82;
  fx.font=`500 ${dfs}px "Malgun Gothic","Apple SD Gothic Neo",sans-serif`;
  const tw = fx.measureText(BADGE.dept).width;
  if(tw > maxW){ dfs = Math.max(4, dfs*maxW/tw);
    fx.font=`500 ${dfs}px "Malgun Gothic","Apple SD Gothic Neo",sans-serif`; }
  fx.fillText(BADGE.dept, x0+W*0.09, y0+H*0.775);
  // 바코드
  let bx=x0+W*0.09; const by=y0+H*0.845, bh=H*0.085;
  fx.fillStyle='#2a3038';
  for(let i=0;i<22 && bx<x0+W*0.91;i++){
    const bw=((i*7919)%3+1)*W*0.008;
    fx.fillRect(bx, by, bw*0.55, bh); bx += bw;
  }
  fx.restore();
  fx.restore();
}

function drawFX(dt){
  fx.setTransform(1,0,0,1,0,0);
  fx.clearRect(0,0,fxc.width,fxc.height);
  if(calib) drawRegions();
  drawBadge(dt);
  if(!symText || symT>1.6) return;
  const k=symT/1.6;
  const a=Math.min(1, (1-k)*2.2) * Math.min(1, k*8);
  const pop=1+Math.exp(-symT*9)*0.9;
  const [cx,cy]=imgToCss(CFG.headC[0]+0.30, CFG.headC[1]-0.13);
  const d=VIEW.dpr;
  fx.globalAlpha=a;
  fx.font=`700 ${Math.round(46*pop*VIEW.scale*d/1.0*0.9)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;
  fx.textAlign='center'; fx.textBaseline='middle';
  fx.fillStyle='#fff';
  fx.shadowColor='rgba(0,0,0,.5)'; fx.shadowBlur=10*d;
  fx.fillText(symText, cx*d, (cy - k*26)*d);
  fx.shadowBlur=0; fx.globalAlpha=1;
}

/* =====================  UI  ===================== */
const $=(s)=>document.querySelector(s);
const logEl=$('#log');

/* 탭 */
document.querySelectorAll('.tab').forEach(tb=>tb.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));
  tb.classList.add('on'); $('#p-'+tb.dataset.p).classList.add('on');
});

/* 감정/모션 버튼 */
const emoBtns=$('#emoBtns');
EMO_KEYS.forEach(k=>{
  const b=document.createElement('button'); b.textContent=EMO[k].ko; b.dataset.k=k;
  const MOT_BY_EMO={surprise:'pop',joy:'bounce',angry:'shiver',think:'tap',shy:'handup',love:'handup',smile:'nod',sleepy:'lean',fear:'shiver'};
  b.onclick=()=>setEmotion(k,intensity, MOT_BY_EMO[k]||'none');
  emoBtns.appendChild(b);
});
const motBtns=$('#motBtns');
Object.keys(MOTION).forEach(k=>{
  const b=document.createElement('button'); b.textContent=MOTION[k].ko;
  b.onclick=()=>trigger(k); motBtns.appendChild(b);
});
function syncEmoUI(){
  emoBtns.querySelectorAll('button').forEach(b=>b.classList.toggle('on', !manual && b.dataset.k===emotion));
}
syncEmoUI();

/* =====================  설정 저장 / 복원  =====================
   브라우저 localStorage 사용. 실패해도(사생활 보호 모드 등) 앱은 그대로 동작한다. */
const STORE='avatar2d.settings.v2';
const SAVE_FIELDS=['apiKey','apiModel','apiBase','apiTemp','persona'];
const RENDER_FIELDS=['r_docbud','r_keep','r_zoom','r_oy','r_chroma','r_real','r_mmax','r_mdraw','r_mwarp','r_bgdim','r_hair','r_cloth','r_patch','r_head','r_brow','r_cover','s_int','s_breath','s_idle','s_blink'];
let saveTimer=null;
function saveSettings(){
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{
    try{
      if(!$('#apiSave').checked){ localStorage.removeItem(STORE); return; }
      localStorage.setItem(STORE, JSON.stringify(collectSettings(true)));
    }catch(e){ /* 저장 불가 환경 — 무시 */ }
  }, 250);
}
function collectSettings(withKey){
  const o={v:1, app:'2d-emotive-avatar'};
  SAVE_FIELDS.forEach(id=>o[id]=$('#'+id).value);
  if(!withKey) o.apiKey='';
  o.render={}; RENDER_FIELDS.forEach(id=>o.render[id]=$('#'+id).value);
  o.cfg=JSON.parse(JSON.stringify(CFG));
  o.cfgs=COSTUMES.map(c=>c.cfg);
  o.ui={ sayH:$('#say').style.height||'',
         sideW:$('#side').style.width||'', chatH:$('#chatPane').style.height||'',
         enterSend:$('#enterSend').checked, bubble:bubbleOn, patch:patchOn,
         stream:$('#streamOn').checked, hud:hudOpen, ctx:ctxOpen, ctxLimit:ctxLimit,
         eye:eyeFollow, badge:badgeOn, autoScene:autoScene,
         personaBackup:personaBackup, costume:costumeIdx, bg:bgIdx };
  return o;
}
/* 값 적용. live=true 면 슬라이더 이벤트까지 발생시켜 화면에 즉시 반영한다 */
function applySettings(o, live){
  if(!o) return false;
  SAVE_FIELDS.forEach(id=>{
    if(o[id]===undefined) return;
    if(id==='apiKey' && !String(o[id]).trim()) return;   // 빈 키로 덮어쓰지 않는다
    $('#'+id).value=o[id];
  });
  if(o.render) RENDER_FIELDS.forEach(id=>{
    if(o.render[id]===undefined) return;
    const el=$('#'+id); el.value=o.render[id];
    if(live) el.dispatchEvent(new Event('input'));
  });
  if(o.cfg) Object.assign(CFG, o.cfg);
  if(o.ui){
    if(o.ui.sideW){ $('#side').style.width=o.ui.sideW; $('#side').style.flexBasis=o.ui.sideW; }
    if(o.ui.chatH){ const cp=$('#chatPane'); if(cp){ cp.style.height=o.ui.chatH; cp.style.flexBasis=o.ui.chatH; } }
    if(o.ui.sayH)  $('#say').style.height=o.ui.sayH;
    if(o.ui.enterSend!==undefined) $('#enterSend').checked=o.ui.enterSend;
    if(o.ui.stream!==undefined) $('#streamOn').checked=o.ui.stream;
    if(o.ui.autoScene!==undefined) autoScene=o.ui.autoScene;
    if(o.ui.badge!==undefined){ badgeOn=o.ui.badge;
      const bc=$('#badgeChip'); if(bc) bc.classList.toggle('on', badgeOn); }
    if(o.ui.eye!==undefined){ eyeFollow=o.ui.eye;
      const ec=$('#eyeChip'); if(ec) ec.classList.toggle('on', eyeFollow); }
    if(o.ui.ctx!==undefined){ ctxOpen=o.ui.ctx;
      const cb=$('#ctxBody'); if(cb) cb.classList.toggle('hide', !ctxOpen); }
    if(o.ui.ctxLimit){ ctxLimit=o.ui.ctxLimit; const sel=$('#ctxLimitSel'); if(sel) sel.value=String(ctxLimit); }
    if(o.ui.hud!==undefined){ hudOpen=o.ui.hud;
      const hb=$('#hudBody'), ht=$('#hudToggle');
      if(hb){ hb.classList.toggle('hide', !hudOpen); ht.textContent = hudOpen?'☰':'⊞'; } }
    if(o.ui.bubble!==undefined){ bubbleOn=o.ui.bubble;
      const bc=$('#bubbleChip'); if(bc) bc.classList.toggle('on',bubbleOn); }
    if(o.ui.patch!==undefined){ patchOn=o.ui.patch; view.patch = patchOn?1:0;
      const pc=$('#patchChip'); if(pc) pc.classList.toggle('on',patchOn); }
    if(o.ui.personaBackup!==undefined) personaBackup=o.ui.personaBackup;
    if(o.ui.costume!==undefined) costumeIdx = o.ui.costume;   // 칩은 아직 없다 -> 값만 보관
    if(o.ui.bg!==undefined) bgIdx = o.ui.bg;
    if(Array.isArray(o.cfgs)) o.cfgs.forEach((c,i)=>{ if(COSTUMES[i] && c) COSTUMES[i].cfg=c; });
  }
  if(live) placeHandles();
  return true;
}
function loadSettings(){
  let o=null;
  try{ const raw=localStorage.getItem(STORE); if(raw) o=JSON.parse(raw); }catch(e){}
  return applySettings(o, false);
}
const RESTORED = loadSettings();

/* 슬라이더 바인딩 */
function bind(id, vid, fn, fmt){
  const el=$('#'+id), v=$('#'+vid);
  const up=()=>{ const x=parseFloat(el.value); v.textContent=(fmt?fmt(x):x.toFixed(2)); fn(x); };
  el.oninput=up; up();
}
bind('s_int','v_int',x=>{intensity=x; if(!manual) setEmotion(emotion,x);});
bind('s_breath','v_breath',x=>breathAmp=x);
bind('s_idle','v_idle',x=>idleAmp=x);
bind('s_blink','v_blink',x=>blinkAmp=x);
bind('r_zoom','v_zoom',x=>view.zoom=x);
bind('r_oy','v_oy',x=>view.oy=x);
bind('r_chroma','v_chroma',x=>view.chroma=x);
bind('r_real','v_real',x=>{
  view.mouthReal = x;
  // 사진을 드롭했을 때 한 번에 안전값으로 맞춰준다
  const set=(id,v)=>{ const e=$('#'+id); if(e){ e.value=v; e.dispatchEvent(new Event('input')); } };
  if(x>0.5){ set('r_mmax',0.36); set('r_mwarp',1.6); set('r_brow',0.85); }
  else      { set('r_mmax',1.00); set('r_mwarp',1.0); set('r_brow',0.25); }
}, x=>x?'ON':'OFF');
bind('r_mmax','v_mmax',x=>view.mouthMax=x);
bind('r_mdraw','v_mdraw',x=>view.mouthDraw=x);
bind('r_mwarp','v_mwarp',x=>view.mouthWarp=x);
bind('r_bgdim','v_bgdim',x=>document.documentElement.style.setProperty('--bgDim',x));
bind('r_hair','v_hair',x=>view.hairAmp=x);
bind('r_cloth','v_cloth',x=>view.clothAmp=x);
bind('r_patch','v_patch',x=>view.patchSize=x);
bind('r_head','v_head',x=>view.headAmp=x);
bind('r_brow','v_brow',x=>view.browAmp=x);
bind('r_cover','v_cover',x=>view.mouthCover=x, x=>x?'ON':'OFF');
bind('r_wire','v_wire',x=>view.wire=x, x=>x?'ON':'OFF');
bind('apiTemp','v_temp',()=>pushServerSettings());

/* 값이 바뀌면 자동 저장 */
SAVE_FIELDS.concat(RENDER_FIELDS).forEach(id=>{
  const el=$('#'+id); if(el) el.addEventListener('input', saveSettings);
});
$('#streamOn').addEventListener('change', saveSettings);
$('#apiSave').addEventListener('change', ()=>{
  if($('#apiSave').checked){ saveSettings(); sys('이 브라우저에 설정을 저장합니다.'); }
  else { try{ localStorage.removeItem(STORE); }catch(e){} sys('저장된 설정을 삭제했습니다.'); }
});

/* 수동 파라미터 */
const MANUAL_MAP={m_eyeOpen:'eyeOpen',m_eyeSmile:'eyeSmile',m_brow:'brow',
  m_mouthOpen:'mouthOpen',m_mouthCurve:'mouthCurve',m_tilt:'tilt',m_turn:'turn',m_blush:'blush',
  m_armA:'armA',m_armB:'armB'};
Object.keys(MANUAL_MAP).forEach(id=>{
  bind(id,'mv_'+id.slice(2),x=>{ if(document.activeElement===$('#'+id)){manual=true;syncEmoUI();} T[MANUAL_MAP[id]]=x; });
});
$('#manualOff').onclick=()=>{ manual=false; setEmotion(emotion,intensity); };

/* ---------- 참고 자료 ---------- */
$('#docChip').onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));
  document.querySelector('.tab[data-p=cfg]').classList.add('on');
  $('#p-cfg').classList.add('on');
  $('#docFile').click();
};
$('#docAdd').onclick=()=>$('#docFile').click();
$('#docClear').onclick=()=>{ docOp('clear'); sys('참고 자료를 전부 삭제했습니다. (서버)'); };
$('#docFile').onchange=(e)=>{
  const files=[...(e.target.files||[])];
  files.forEach(f=>{
    const rd=new FileReader();
    rd.onload=()=>addDoc(f.name.replace(/\.[^.]+$/,''), rd.result);
    rd.readAsText(f, 'utf-8');
  });
  e.target.value='';
};
bind('r_docbud','v_docbud',x=>{ docBudget=x; refreshDocsUI(); renderCtx(); pushServerSettings(); }, x=>Math.round(x/1000)+'k');
bind('r_keep','v_keep',x=>{ keepMsgs=x; renderCtx(); pushServerSettings(); }, x=>x+'개');
$('#ctxLimitSel').onchange=()=>{ ctxLimit=parseInt($('#ctxLimitSel').value,10)||32768; renderCtx(); saveSettings(); pushServerSettings(); };
$('#ctxReset').onclick=()=>{ history.length=0; renderCtx(); sys('대화 기록을 비웠습니다. (화면 로그는 그대로)'); };
setInterval(renderCtx, 1200);
refreshDocsUI();

/* ---------- 마우스 시선 추적 ---------- */
(function(){
  const st=$('#stageWrap');
  const clamp=(v)=>Math.max(-1,Math.min(1,v));
  st.addEventListener('mousemove', (e)=>{
    if(!eyeFollow) return;
    const r=glc.getBoundingClientRect();
    const mid=[(CFG.eyeL[0]+CFG.eyeR[0])/2, (CFG.eyeL[1]+CFG.eyeR[1])/2];
    const [ex,ey]=imgToCss(mid[0], mid[1]);
    mouseGaze=[ clamp((e.clientX-r.left-ex)/(r.width*0.34)),
                clamp((e.clientY-r.top -ey)/(r.height*0.30)) ];
    mouseLast=performance.now();
  });
  st.addEventListener('mouseleave', ()=>{ mouseLast=0; });
  $('#eyeChip').onclick=()=>{
    eyeFollow=!eyeFollow;
    $('#eyeChip').classList.toggle('on', eyeFollow);
    if(!eyeFollow) mouseLast=0;
    saveSettings();
  };
  $('#badgeChip').onclick=()=>{
    badgeOn=!badgeOn;
    $('#badgeChip').classList.toggle('on', badgeOn);
    saveSettings();
  };
})();

/* ---------- 세션 ---------- */
loadSessions();
curSession = newSessionObj();
refreshSessUI();

$('#sessNew').onclick = ()=>newSession();
$('#sessSel').onchange = (e)=>{ if(e.target.value!==curSession.id) openSession(e.target.value); };
/* 목록을 여는 순간 서버에서 다시 읽는다 — 다른 PC 가 방금 만든 세션이 보이게 */
$('#sessSel').addEventListener('focus', async ()=>{
  if(!window.SERVER) return;
  await loadSessions(); refreshSessUI();
});
$('#sessDl').onclick = async ()=>{
  if(!curSession || !curSession.msgs.length){ sys('저장할 대화가 없습니다.'); return; }
  const base = 'session_'+curSession.ts.replace(/[^0-9]/g,'').slice(0,12);
  downloadBlob(base+'.json', JSON.stringify(curSession, null, 2), 'application/json');
  setTimeout(()=>downloadBlob(base+'.md', sessionToMarkdown(curSession), 'text/markdown'), 400);
  if(window.SERVER){
    /* 공유용 HTML 은 서버가 만든다 — 디바운스 저장을 먼저 밀어넣는다 */
    saveSessions(); clearTimeout(sessPushTimer); await pushSessions();
    try{
      const r = await fetch('/api/sessions/html?id='+encodeURIComponent(curSession.id));
      if(r.ok) setTimeout(async()=>downloadBlob(base+'.html', await r.text(), 'text/html'), 800);
    }catch(e){}
    sys('이 세션을 JSON + Markdown + HTML 로 내려받았습니다. (html 은 그대로 공유하면 됩니다)');
  }else{
    sys('이 세션을 JSON + Markdown 으로 내려받았습니다.');
  }
};
$('#sessDel').onclick = ()=>{
  if(!curSession) return;
  const i=sessions.findIndex(x=>x.id===curSession.id);
  if(i>=0) sessions.splice(i,1);
  deletedSess.push(curSession.id);          // 병합 서버에는 삭제를 명시해야 한다
  persistSessions();
  curSession = newSessionObj();
  logEl.innerHTML=''; history.length=0;
  refreshSessUI(); renderCtx();
  sys('세션을 삭제했습니다.');
};
$('#sessExportAll').onclick = ()=>{
  saveSessions();
  if(!sessions.length){ sys('내보낼 세션이 없습니다.'); return; }
  downloadBlob('sessions_all.json', JSON.stringify(sessions, null, 2), 'application/json');
};
$('#sessClearAll').onclick = ()=>{
  deletedSess.push(...sessions.map(s=>s.id));   // 전체 삭제도 명시로
  sessions.length=0;
  persistSessions();
  curSession = newSessionObj();
  logEl.innerHTML=''; history.length=0;
  refreshSessUI(); renderCtx();
  sys('모든 세션을 삭제했습니다.');
};

/* ---------- 컨텍스트 패널 접기/펼치기 (기본 접힘) ---------- */
(function(){
  const t=$('#ctxToggle'), body=$('#ctxBody');
  const apply=()=>{ body.classList.toggle('hide', !ctxOpen); };
  t.onclick=()=>{ ctxOpen=!ctxOpen; apply(); renderCtx(); saveSettings(); };
  apply();
})();

/* ---------- HUD 접기/펼치기 ---------- */
function setHud(open){
  hudOpen=open;
  const t=$('#hudToggle'), body=$('#hudBody');
  body.classList.toggle('hide', !hudOpen);
  t.textContent = hudOpen ? '☰' : '⊞';
  saveSettings();
}
(function(){
  const t=$('#hudToggle');
  t.onclick=()=>{ setHud(!hudOpen); };
  setHud(hudOpen);
})();

/* ---------- 배경 ---------- */
const wrap=$('#stageWrap');
function applyBg(){
  const b = BACKGROUNDS[bgIdx] || BACKGROUNDS[0];
  wrap.className = '';
  if(b.img){ wrap.classList.add('hasbg'); wrap.style.backgroundImage = 'url("'+b.img+'")'; }
  else     { wrap.style.backgroundImage = ''; }
  document.querySelectorAll('#bgChips .chip').forEach((c,i)=>c.classList.toggle('on', i===bgIdx));
  document.querySelectorAll('.chip[data-bg]').forEach(x=>x.classList.remove('on'));
}
function setBg(i, fromAuto){
  if(!fromAuto && autoScene){ autoScene=false; paintClock(); }   // 수동으로 고르면 자동 해제
  bgIdx=i; applyBg();
  const b = BACKGROUNDS[i] || {};
  // 배경에 맞는 의상으로 자동 전환 (공장→무진복, 회의실→정장, 정문→가운, 테라스→반팔)
  if(b.costume!==undefined && b.costume!==costumeIdx && COSTUMES[b.costume]) setCostume(b.costume);
  // 사원증 : 사복(테라스)에서는 뗀다
  if(b.badge!==undefined && b.badge!==badgeOn){
    badgeOn=b.badge;
    const bc=$('#badgeChip'); if(bc) bc.classList.toggle('on', badgeOn);
  }
  saveSettings();
}
function buildBgChips(){
  const w=$('#bgChips');
  w.innerHTML='';
  BACKGROUNDS.forEach((b,i)=>{
    const el=document.createElement('div');
    el.className='chip'; el.textContent=b.name;
    el.onclick=()=>setBg(i);
    w.appendChild(el);
  });
  applyBg();
}
buildBgChips();
/* ---------- FAB 알람 ----------
   실데이터: pollSentinel() 이 관제(real_time_amhs) 등급을 읽어 자동으로
   fireAlarm/clearAlarm 을 부른다. [테스트] 는 무작위 발생 (그대로).
   ★FABS/LEVELS 의 원본은 서버(avatar/config.py)다 — /api/config 로 받아
     아래 폴백을 덮는다. 예전엔 여기 복사본이 진짜였는데, 서버 목록과
     어긋나서 M14B·M16A·M16B 알람을 그릴 수 없었다. 폴백은 HTML 단독
     실행(데모)용으로만 남긴다. */
let FABS = [
  {key:'M14',    name:'M14',     img:"assets/fab_m14.png"},
  {key:'M16HUB', name:'M16 HUB', img:"assets/fab_m16hub.png"},
  {key:'M16',    name:'M16',     img:"assets/fab_m16.png"},
];
function applyAlarmConfig(c){
  if(Array.isArray(c.fabs)   && c.fabs.length)   FABS   = c.fabs;
  if(Array.isArray(c.levels) && c.levels.length) LEVELS = c.levels;
}
/* 등급 : 경계 → 위험 → 초위험. 색·속도·경고음·대사가 전부 달라진다 */
let LEVELS = [
  {key:'lv1', name:'경계',   nag:8000, tones:[880],            emo:['think','surprise'], inten:0.70, pace:null,
   lines:[
     (n)=>`${n} FAB에 경계 알람이 떴어요. 한 번 봐주세요.`,
     (n)=>`아직 ${n} 경계 상태예요. 지켜보고 있을게요.`,
     (n)=>`${n} 쪽 수치가 슬슬 올라와요… 확인 부탁드려요.`,
     (n)=>`${n} FAB 경계 알람, 아직 해제 안 됐어요.`,
   ]},
  {key:'lv2', name:'위험',   nag:6000, tones:[880,660],        emo:['fear','angry'],     inten:0.90,
   pace:{amp:0.20, freq:0.42},
   lines:[
     (n)=>`${n} FAB 위험 알람이에요! 빨리 확인해 주세요!`,
     (n)=>`아직 ${n} 위험 상태예요… 반송이 밀리고 있어요!`,
     (n)=>`${n} FAB 알람이 계속 울리고 있어요!`,
     (n)=>`${n} 쪽 좀 봐주세요, 저 혼자서는 못 막아요!`,
   ]},
  {key:'lv3', name:'초위험', nag:4000, tones:[990,760,990],    emo:['fear','angry'],     inten:1.00,
   pace:{amp:0.20, freq:0.42},   // 위험과 동일하게. 더 빠르면 무섭다
   lines:[
     (n)=>`${n} FAB 초위험이에요!! 지금 당장 조치해 주세요!!`,
     (n)=>`${n} 멈췄어요!! 초위험 단계예요!!`,
     (n)=>`${n} FAB 초위험… 이러다 라인 전체 밀려요!`,
     (n)=>`아직도 ${n} 초위험이에요!! 제발요!!`,
   ]},
];
let alarm = null;          // {fab, lv, t0, nag, tick, line}
let panicT = 0;            // 좌우로 뛰어다니는 위상
let audioCtx = null;
function beep(tones, vol){
  try{
    if(!audioCtx) audioCtx = new (window.AudioContext||window.webkitAudioContext)();
    if(audioCtx.state==='suspended') audioCtx.resume();
    const now=audioCtx.currentTime, V=vol||0.12;
    (tones||[880]).forEach((f,k)=>{
      const off=k*0.24;
      const o=audioCtx.createOscillator(), g=audioCtx.createGain();
      o.type='square'; o.frequency.value=f;
      g.gain.setValueAtTime(0.0001, now+off);
      g.gain.exponentialRampToValueAtTime(V, now+off+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, now+off+0.19);
      o.connect(g); g.connect(audioCtx.destination);
      o.start(now+off); o.stop(now+off+0.22);
    });
  }catch(e){}
}
function alarmSay(){
  if(!alarm) return;
  const L=alarm.lv;
  /* 서버 config 의 대사는 '{n}' 자리표 문자열, 로컬 폴백은 함수 — 둘 다 받는다 */
  const raw = L.lines[alarm.line % L.lines.length];
  const f = typeof raw==='function' ? raw(alarm.fab.name)
                                    : String(raw).replace(/\{n\}/g, alarm.fab.name);
  const e = L.emo[alarm.line % L.emo.length];
  alarm.line++;
  setEmotion(e, L.inten, L.key==='lv1' ? 'tap' : 'shiver');
  speak(f);
  beep(L.tones, L.key==='lv3' ? 0.16 : 0.11);
}
function paintAlarmTime(){
  if(!alarm) return;
  const s=Math.floor((Date.now()-alarm.t0)/1000);
  const el=$('#alarmTime');
  if(el) el.textContent = String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
}
const LV_CSS = {lv1:'232,193,74', lv2:'255,122,61', lv3:'255,43,61'};
/* 알람을 대사 없이 조용히 내린다 — 등급/구역 '교체' 때 쓴다.
   교체마다 "해제됐어요!" 를 말하면 실제로는 상황이 나빠지는 중인데
   좋아진 것처럼 들린다. */
function silentClear(){
  if(!alarm) return;
  clearInterval(alarm.nag); clearInterval(alarm.tick);
  alarm = null;
  const box=$('#alarmBox'), fl=$('#alarmFlash');
  box.classList.remove('on','lv1','lv2','lv3');
  fl.classList.remove('on','lv1','lv2','lv3');
}
function fireAlarm(fab, lv, src){
  const f = fab || FABS[Math.floor(Math.random()*FABS.length)];
  const L = lv  || LEVELS[Math.floor(Math.random()*LEVELS.length)];
  if(alarm){
    /* 같은 구역·같은 등급이면 그대로 (재발화로 대사가 초기화되면 시끄럽다).
       단 관찰 모드(quiet)였다면 재발이다 — 재촉을 다시 켠다. */
    if(alarm.fab.key===f.key && alarm.lv.key===L.key){
      alarm.src = src||alarm.src;
      if(alarm.quiet){
        alarm.quiet=false;
        sys('알람 재발 — '+f.name+' '+L.name);
        alarmSay();
        alarm.nag = setInterval(alarmSay, L.nag);
      }
      return;
    }
    silentClear();                     // 다른 구역/등급 → 교체
  }
  alarm = {fab:f, lv:L, t0:Date.now(), line:0, nag:null, tick:null, src:src||'test'};
  const box=$('#alarmBox'), fl=$('#alarmFlash');
  box.classList.remove('lv1','lv2','lv3'); fl.classList.remove('lv1','lv2','lv3');
  box.classList.add('on', L.key);  fl.classList.add('on', L.key);
  $('#alarmTitle').textContent = 'FAB 알람';
  $('#alarmLv').textContent = L.name;
  $('#alarmFab').textContent = f.name;
  const im=$('#alarmImg'); im.src=f.img; im.alt=f.name;
  $('#alarmMsg').textContent = f.name + ' FAB · ' + L.name + ' 단계 — 해제할 때까지 계속 울립니다';
  document.documentElement.style.setProperty('--bubbleAccent', 'rgb('+LV_CSS[L.key]+')');
  sys('■ 알람 발생 — ' + f.name + ' FAB · ' + L.name);
  paintAlarmTime();
  alarmSay();
  alarm.nag  = setInterval(alarmSay, L.nag);
  alarm.tick = setInterval(paintAlarmTime, 1000);
}
function clearAlarm(){
  if(!alarm) return;
  const n = alarm.fab.name, lvn = alarm.lv.name;
  clearInterval(alarm.nag); clearInterval(alarm.tick);
  alarm = null;
  const box=$('#alarmBox'), fl=$('#alarmFlash');
  box.classList.remove('on','lv1','lv2','lv3');
  fl.classList.remove('on','lv1','lv2','lv3');
  $('#alarmTitle').textContent = 'FAB 정상';
  $('#alarmTime').textContent = '';
  document.documentElement.style.setProperty('--bubbleAccent', '#d94a5a');
  sys('□ 알람 해제 — ' + n + ' FAB · ' + lvn);
  setEmotion('smile', 0.8, 'nod');
  speak(n + ' FAB ' + lvn + ' 알람 해제됐어요. 휴… 살았다.');
}
(function initAlarm(){
  $('#alarmTest').onclick = ()=>{ if(alarm) clearAlarm(); fireAlarm(); };
  $('#alarmClear').onclick = ()=> clearAlarm();
})();

/* ---------- 미니 모드 (소형 하단 위젯) ----------
   패널·HUD 를 숨기고 캐릭터+말풍선+알람+입력창만 남긴다.
   '소형창' 은 화면 우하단에 작은 팝업 창으로 새로 띄운다 (?mini=1). */
function setMini(on){
  document.body.classList.toggle('mini', !!on);
  const c=$('#miniChip'); if(c) c.classList.toggle('on', !!on);
  computeView(); placeHandles(); placeBubble();
}
(function initMini(){
  const mc=$('#miniChip'), pc=$('#popChip');
  if(mc) mc.onclick = ()=> setMini(!document.body.classList.contains('mini'));
  if(pc) pc.onclick = ()=>{
    const w=430, h=580;
    const x=Math.max(0,(screen.availWidth||1200)-w-8);
    const y=Math.max(0,(screen.availHeight||800)-h-8);
    const win=window.open(location.pathname+'?mini=1','avatar_mini',
      'width='+w+',height='+h+',left='+x+',top='+y);
    if(!win) sys('팝업이 차단됐어요 — 브라우저의 팝업 허용을 켜 주세요.');
  };
  if(new URLSearchParams(location.search).get('mini')==='1')
    setTimeout(()=>setMini(true), 0);
})();

/* ---------- SD 러너 — 접기/펼치기를 꼬마 캐릭터가 달려와서 누른다 ----------
   ☰(패널)·◧(컨텍스트) 토글을 누르면, 미니 SD 캐릭터가 허둥지둥 화면 위를
   가로질러 달려와 버튼을 꾹 누르고(그 순간 실제로 접힘/펼침) 지나간다.
   그림: assets/sd_run.png 가 있으면 그걸 쓴다(초록 배경은 여기서 투명 처리).
         없으면 코드로 그린 꼬마(검은 머리·정장·땀방울)로 움직인다.
   애니메이션 중에 또 누르면 그냥 즉시 토글 — 기다리게 하지 않는다. */
const SdRunner = (function(){
  let sprite=null, running=false;

  function chroma(img){
    /* 초록 배경 → 투명 + 내용만 남게 잘라낸다 */
    const c=document.createElement('canvas');
    c.width=img.naturalWidth; c.height=img.naturalHeight;
    const g=c.getContext('2d', {willReadFrequently:true});
    g.drawImage(img,0,0);
    const d=g.getImageData(0,0,c.width,c.height), px=d.data;
    let minX=c.width, minY=c.height, maxX=0, maxY=0;
    for(let i=0;i<px.length;i+=4){
      const r=px[i], gr=px[i+1], b=px[i+2];
      if(gr>90 && gr>r*1.35 && gr>b*1.35){ px[i+3]=0; continue; }
      const p=i/4, x=p%c.width, y=(p-x)/c.width;
      if(x<minX)minX=x; if(x>maxX)maxX=x; if(y<minY)minY=y; if(y>maxY)maxY=y;
    }
    if(maxX<=minX) return null;
    g.putImageData(d,0,0);
    const out=document.createElement('canvas');
    out.width=maxX-minX+2; out.height=maxY-minY+2;
    out.getContext('2d').drawImage(c, minX, minY, out.width, out.height,
                                   0, 0, out.width, out.height);
    return out;
  }

  function drawFallback(){
    /* 파일이 없을 때 — 본체를 닮은 꼬마를 직접 그린다 (머리 큰 2등신) */
    const c=document.createElement('canvas'); c.width=72; c.height=88;
    const g=c.getContext('2d');
    if(!g.roundRect) g.roundRect=function(x,y,w,h){ this.rect(x,y,w,h); };  // 옛 브라우저
    g.lineWidth=2; g.lineJoin='round';
    // 몸(정장)
    g.fillStyle='#3a4356'; g.strokeStyle='#232a38';
    g.beginPath(); g.roundRect(22,46,28,26,7); g.fill(); g.stroke();
    // 팔 둘 다 번쩍 (허둥지둥)
    g.beginPath(); g.roundRect(10,38,12,8,4); g.fill(); g.stroke();
    g.beginPath(); g.roundRect(50,38,12,8,4); g.fill(); g.stroke();
    // 다리
    g.fillStyle='#2c3140';
    g.beginPath(); g.roundRect(26,70,8,14,3); g.fill();
    g.beginPath(); g.roundRect(38,70,8,14,3); g.fill();
    // 머리 (크게)
    g.fillStyle='#ffe3d0'; g.strokeStyle='#2b2b34';
    g.beginPath(); g.arc(36,26,20,0,7); g.fill(); g.stroke();
    // 머리카락
    g.fillStyle='#2e3440';
    g.beginPath(); g.arc(36,22,20,Math.PI*0.95,Math.PI*2.05); g.fill();
    g.beginPath(); g.roundRect(14,20,10,16,5); g.fill();
    g.beginPath(); g.roundRect(48,20,10,16,5); g.fill();
    // 머리띠
    g.strokeStyle='#c8cfda'; g.lineWidth=3;
    g.beginPath(); g.arc(36,24,19,Math.PI*1.15,Math.PI*1.85); g.stroke();
    // 눈 (>_<)·입·볼
    g.strokeStyle='#2b2b34'; g.lineWidth=2;
    g.beginPath(); g.moveTo(26,28); g.lineTo(31,31); g.moveTo(26,34); g.lineTo(31,31); g.stroke();
    g.beginPath(); g.moveTo(46,28); g.lineTo(41,31); g.moveTo(46,34); g.lineTo(41,31); g.stroke();
    g.fillStyle='#d94a5a';
    g.beginPath(); g.ellipse(36,38,4,3,0,0,7); g.fill();
    // 땀방울
    g.fillStyle='#9fd2ff';
    g.beginPath(); g.ellipse(56,14,3,4,0.5,0,7); g.fill();
    g.beginPath(); g.ellipse(14,12,2.5,3.5,-0.5,0,7); g.fill();
    return c;
  }

  async function load(){
    if(sprite) return sprite;
    sprite = await new Promise(res=>{
      const im=new Image();
      im.onload = ()=>res(chroma(im) || drawFallback());
      im.onerror= ()=>res(drawFallback());
      im.src='assets/sd_run.png';
    });
    return sprite;
  }

  async function run(btn, onPress){
    if(running){ onPress(); return; }          // 바쁘면 그냥 즉시 토글
    const wrap=$('#stageWrap');
    if(!wrap || !btn){ onPress(); return; }
    running=true;
    const sp=await load();
    const H=64, W=Math.max(24, Math.round(sp.width*H/sp.height));
    const el=document.createElement('canvas');
    el.width=sp.width; el.height=sp.height;
    el.getContext('2d').drawImage(sp,0,0);
    el.className='sdRun';
    el.style.width=W+'px'; el.style.height=H+'px';
    wrap.appendChild(el);

    const wr=wrap.getBoundingClientRect(), br=btn.getBoundingClientRect();
    const y0=Math.max(2, br.top-wr.top+br.height/2-H+6);
    const xTarget=br.left-wr.left+br.width/2-W/2;
    const fromRight = xTarget < wr.width/2;   // 버튼이 왼쪽이면 오른쪽에서 진입
    const x0=fromRight ? wr.width+W : -W;
    const x1=fromRight ? -W-20 : wr.width+W+20;
    /* 콘솔에서 window.SD_DUR=600 처럼 속도를 바꿀 수 있다 (ms, 작을수록 빠름) */
    const dur=window.SD_DUR||850, pressAt=Math.abs(xTarget-x0)/Math.abs(x1-x0);
    let pressed=false; const t0=performance.now();
    function step(now){
      const t=Math.min(1,(now-t0)/dur);
      const x=x0+(x1-x0)*t;
      const wob=Math.sin(t*dur/28);                 // 잰걸음 — 빨리 동동거린다
      el.style.transform='translate('+x+'px,'+(y0-Math.abs(wob)*6)+'px) '
        +'rotate('+(wob*11)+'deg)'+(fromRight?' scaleX(-1)':'');
      if(!pressed && t>=pressAt){
        pressed=true;
        btn.classList.add('sdpress');
        setTimeout(()=>btn.classList.remove('sdpress'), 260);
        onPress();                              // ★누르는 그 순간 실제 토글
      }
      if(t<1){ requestAnimationFrame(step); }
      else{ el.remove(); running=false; }
    }
    requestAnimationFrame(step);
  }
  return {run};
})();
/* 토글 버튼에 러너를 끼운다 — 원래 동작은 러너가 '누르는 순간' 실행된다 */
(function hookSdRunner(){
  for(const id of ['hudToggle','ctxToggle']){
    const btn=$('#'+id);
    if(!btn || !btn.onclick) continue;
    const orig=btn.onclick.bind(btn);
    btn.onclick=()=>SdRunner.run(btn, orig);
  }
})();

/* ── 관제 실데이터 감시 ──
   /api/fab/status (아바타 서버가 real_time_amhs 를 5초 캐시로 대신 읽음).
   등급이 경계 이상인 시스템이 있으면 가장 나쁜 것 하나를 알람으로.
   ★관제가 끊기면 '끊겼다' 고 말한다 — 조용히 정상인 척하는 게 최악이다.
   ★실데이터 알람(src='real')만 자동 해제한다. 테스트 알람은 사람이 끈다. */
let sentinelDown = null;      // null=아직 모름, true/false=상태
async function pollSentinel(){
  if(!window.SERVER) return;
  let s;
  try{
    const r = await fetch('/api/fab/status', {cache:'no-store'});
    s = await r.json();
  }catch(e){ s = {ok:false, err:e.message}; }
  if(!s.ok){
    if(sentinelDown!==true){
      sentinelDown = true;
      sys('관제 연결 끊김 — '+(s.err||'')+' · 알람 자동 감시가 멈췄습니다. '
          +'(real_time_amhs 서버 확인)');
    }
    return;                    // 데이터를 못 보는 동안 기존 알람은 건드리지 않는다
  }
  if(sentinelDown!==false){
    if(sentinelDown===true) sys('관제 연결 복구 — 알람 자동 감시 재개');
    else sys('관제 연결됨 — 경계/위험/초위험 자동 감시 중'
             +(s.at?' (데이터 '+s.at+')':''));
    sentinelDown = false;
  }
  const worst = (s.alarms||[])[0];
  if(worst){
    const f = FABS.find(x=>x.key===worst.fab)
              || {key:worst.fab, name:worst.fab, img:'assets/fab_m16hub.png'};
    const L = LEVELS.find(x=>x.name===worst.level);
    if(L) fireAlarm(f, L, 'real');
  }else if(alarm && alarm.src==='real'){
    /* 정상 복귀 — 바로 끄지 않는다. 관제의 '사건 60분 뒤 닫힘' 과 같은
       규칙으로 1시간 관찰을 유지한다 (서버가 hold 로 남은 시간을 준다).
       재촉 대사·경고음은 멈춘다 — "아직 위험" 은 이제 거짓말이니까. */
    if(s.hold){ holdAlarm(s.hold); }
    else{ clearAlarm(); }
  }
}
function holdAlarm(h){
  if(!alarm) return;
  if(!alarm.quiet){
    alarm.quiet = true;
    clearInterval(alarm.nag); alarm.nag = null;
    setEmotion('smile', 0.6, 'nod');
    speak(alarm.fab.name+' 수치가 정상으로 내려왔어요. '
          +h.left_min+'분 동안 재발 없는지 지켜볼게요.');
    sys('알람 관찰 모드 — '+alarm.fab.name+' 정상 복귀, '
        +h.left_min+'분 뒤 자동 해제 (재발 시 다시 울림)');
  }
  $('#alarmMsg').textContent = alarm.fab.name+' 정상 복귀 — '
    +h.left_min+'분 관찰 후 자동 해제됩니다 (재발하면 다시 울려요)';
}

/* ---------- 시간표 자동 전환 ----------
   지금 시각이 속한 구간의 배경(=의상·사원증까지)으로 알아서 바꾼다.
   배경 칩을 직접 누르면 '수동' 으로 바뀌고, 시계를 누르면 다시 '자동'. */
const hm2min = (s)=>{ const [a,b]=s.split(':').map(Number); return a*60+b; };
function slotAt(min){
  for(const s of SCHEDULE){
    const f=hm2min(s.from), t=hm2min(s.to);
    if(f<=t){ if(min>=f && min<=t) return s; }
    else    { if(min>=f || min<=t) return s; }   // 자정을 넘는 구간
  }
  return null;
}
function bgIndexByName(n){ return BACKGROUNDS.findIndex(b=>b.name===n); }
function paintClock(){
  const d=new Date();
  const min=d.getHours()*60+d.getMinutes();
  const s=slotAt(min);
  const t=$('#clockT'), lab=$('#clockS'), md=$('#clockMode');
  if(t) t.textContent=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  if(lab) lab.textContent = s ? s.bg : '—';
  if(md){ md.textContent = autoScene ? '자동' : '수동'; md.classList.toggle('auto', autoScene); }
  return s;
}
function tickScene(force){
  const s=paintClock();
  if(!autoScene || !s) return;
  const i=bgIndexByName(s.bg);
  if(i>=0 && (force || i!==bgIdx)) setBg(i, true);
}
(function initClock(){
  const c=$('#clock');
  if(c) c.onclick=()=>{
    autoScene=!autoScene;
    paintClock();
    if(autoScene) tickScene(true);
    saveSettings();
  };
  paintClock();
  setInterval(paintClock, 1000);
  setInterval(()=>tickScene(false), 20000);
  // 시작할 때 한 번 : 의상 칩까지 다 만들어진 뒤에 적용해야 한다
  setTimeout(()=>tickScene(true), 0);
})();

/* 그린스크린 / 투명 : 배경 이미지를 끄고 단색으로 */
document.querySelectorAll('.chip[data-bg]').forEach(c=>c.onclick=()=>{
  wrap.className=''; wrap.style.backgroundImage='';
  wrap.classList.add(c.dataset.bg);
  document.querySelectorAll('.chip').forEach(x=>{
    if(x.dataset.bg || x.parentElement.id==='bgChips') x.classList.remove('on');
  });
  c.classList.add('on');
  saveSettings();
});

/* ---------- 캘리브레이션 핸들 ---------- */
const handlesEl=$('#handles');
// rad 가 있으면 파란 사각 핸들 2개(가로/세로)가 붙어서 크기를 조절할 수 있다
const HANDLES=[
  {k:'mouth', n:'입',   rad:'mouth_rad'},
  {k:'eyeL',  n:'왼눈', rad:'eyeL_rad'},
  {k:'eyeR',  n:'오른눈', rad:'eyeR_rad'},
  {k:'cheekL',n:'왼볼', rad:'cheek_rad'},
  {k:'cheekR',n:'오른볼'},
  {k:'neckPivot',n:'목(회전축)'},{k:'headC',n:'머리중심', rad:'headRad'},
  {k:'faceC',n:'얼굴(흔들림 제외)', rad:'faceRad'},
  {k:'armA',n:'팔A(손)', rad:'armA_rad'},{k:'armA_piv',n:'팔A 팔꿈치'},
  {k:'armB',n:'팔B',     rad:'armB_rad'},{k:'armB_piv',n:'팔B 팔꿈치'}
];
let calib=false;
$('#calibChip').onclick=()=>{ calib=!calib; $('#calibChip').classList.toggle('on',calib); renderHandles(); };
function mkDrag(el, onMove){
  let drag=false;
  el.onpointerdown=(e)=>{ drag=true; el.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation(); };
  el.onpointermove=(e)=>{
    if(!drag) return;
    const r=glc.getBoundingClientRect();
    onMove(cssToImg(e.clientX-r.left, e.clientY-r.top));
    placeHandles(); saveSettings();
  };
  el.onpointerup=el.onpointercancel=()=>{ drag=false; };
}

function renderHandles(){
  handlesEl.innerHTML='';
  HANDLES.forEach(h=>{ h.el=h.rx=h.ry=null; });
  if(!calib) return;

  HANDLES.forEach(h=>{
    // 중심 핸들
    const d=document.createElement('div'); d.className='hnd';
    d.innerHTML='<b>'+h.n+'</b>'; handlesEl.appendChild(d); h.el=d;
    mkDrag(d, p=>{ CFG[h.k]=[clamp01(p[0]), clamp01(p[1])]; });

    // 크기 핸들 (가로 / 세로)
    if(h.rad && CFG[h.rad]){
      const rx=document.createElement('div'); rx.className='hnd sz x';
      const ry=document.createElement('div'); ry.className='hnd sz y';
      handlesEl.appendChild(rx); handlesEl.appendChild(ry);
      h.rx=rx; h.ry=ry;
      mkDrag(rx, p=>{ CFG[h.rad][0]=Math.max(0.006, Math.min(0.5, Math.abs(p[0]-CFG[h.k][0]))); });
      mkDrag(ry, p=>{ CFG[h.rad][1]=Math.max(0.004, Math.min(0.5, Math.abs(p[1]-CFG[h.k][1]))); });
    }
  });

  // 목선
  const line=document.createElement('div'); line.className='hline';
  handlesEl.appendChild(line); handlesEl.__line=line;
  let ld=false;
  line.onpointerdown=(e)=>{ld=true;line.setPointerCapture(e.pointerId);e.preventDefault();};
  line.onpointermove=(e)=>{ if(!ld)return; const r=glc.getBoundingClientRect();
    CFG.neckY=clamp01(cssToImg(0,e.clientY-r.top)[1]); placeHandles(); saveSettings(); };
  line.onpointerup=()=>ld=false;

  placeHandles();
}
function clamp01(v){ return Math.max(0, Math.min(1, v)); }

function placeHandles(){
  if(!calib) return;
  HANDLES.forEach(h=>{
    if(!h.el) return;
    const c=CFG[h.k];
    const [x,y]=imgToCss(c[0], c[1]);
    h.el.style.left=x+'px'; h.el.style.top=y+'px';
    if(h.rx && CFG[h.rad]){
      const r=CFG[h.rad];
      const [ax,ay]=imgToCss(c[0]+r[0], c[1]);
      const [bx,by]=imgToCss(c[0], c[1]+r[1]);
      h.rx.style.left=ax+'px'; h.rx.style.top=ay+'px';
      h.ry.style.left=bx+'px'; h.ry.style.top=by+'px';
    }
  });
  if(handlesEl.__line) handlesEl.__line.style.top = imgToCss(0,CFG.neckY)[1]+'px';
}
setInterval(()=>placeHandles(), 120);

/* 프리셋 내보내기/불러오기 */
$('#cfgExport').onclick=()=>{ $('#cfgJson').value=JSON.stringify(CFG); };
$('#cfgImport').onclick=()=>{
  try{ const o=JSON.parse($('#cfgJson').value); Object.assign(CFG,o); placeHandles(); saveSettings(); sys('캘리브레이션 적용됨'); }
  catch(e){ sys('JSON 파싱 실패: '+e.message); }
};

/* ---------- 의상 교체 ----------
   프레이밍이 같은 그림끼리는 캘리브레이션을 그대로 쓴다 */
function setCostume(i){
  if(i<0 || i>=COSTUMES.length) return;
  // 지금까지 조절한 값을 이전 의상에 저장해 둔다
  if(COSTUMES[costumeIdx]) COSTUMES[costumeIdx].cfg = JSON.parse(JSON.stringify(CFG));
  costumeIdx = i;
  const c = COSTUMES[i];
  let base = c.cfg;
  if(!base){
    base = JSON.parse(JSON.stringify(c.real ? CFG_REAL : CFG_ANIME));
    if(c.patch) Object.assign(base, JSON.parse(JSON.stringify(c.patch)));
  }
  Object.keys(CFG).forEach(k=>delete CFG[k]);
  Object.assign(CFG, JSON.parse(JSON.stringify(base)));
  // 실사는 워핑 티가 잘 나므로 표정 진폭을 낮춘다
  // 실사는 합성 입·눈물이 바로 티가 난다 -> 끄고 메쉬 워핑만으로 표현
  view.realScale = c.real ? 0.75 : 1.0;
  view.mouthDraw = 1.0;
  view.tearAmp   = c.real ? 0.0 : 1.0;
  const mm=$('#r_mmax'); if(mm){ mm.value=view.mouthMax; mm.dispatchEvent(new Event('input')); }
  // 슬라이더 UI 도 같이 맞춘다
  const set=(id,v)=>{ const e=$('#'+id); if(e){ e.value=v; e.dispatchEvent(new Event('input')); } };
  set('r_real', c.real?1:0);
  texReady = false;
  loadImage(c.src);
  document.querySelectorAll('#costumeChips .chip').forEach((el,k)=>el.classList.toggle('on', k===i));
  placeHandles();
  saveSettings();
}
function buildCostumeChips(){
  const wrap=$('#costumeChips');
  wrap.innerHTML='';
  COSTUMES.forEach((c,i)=>{
    const el=document.createElement('div');
    el.className='chip'+(i===0?' on':'');
    el.textContent=c.name;
    el.onclick=()=>setCostume(i);
    wrap.appendChild(el);
  });
  if(costumeIdx > 0 && costumeIdx < COSTUMES.length) setCostume(costumeIdx);  // 저장된 의상 복원
}
buildCostumeChips();

/* ---------- 이미지 드롭 ---------- */
const dropEl=$('#drop');
['dragenter','dragover'].forEach(ev=>wrap.addEventListener(ev,e=>{e.preventDefault();dropEl.classList.add('on');}));
['dragleave','drop'].forEach(ev=>wrap.addEventListener(ev,e=>{e.preventDefault();dropEl.classList.remove('on');}));
wrap.addEventListener('drop',e=>{
  const f=e.dataTransfer.files&&e.dataTransfer.files[0]; if(!f) return;
  if(/\.(md|markdown|txt)$/i.test(f.name) || /^text\//.test(f.type)){
    const r2=new FileReader();
    r2.onload=()=>addDoc(f.name.replace(/\.[^.]+$/,''), r2.result);
    r2.readAsText(f,'utf-8');
    return;
  }
  if(!/^image\//.test(f.type)) return;
  const rd=new FileReader();
  rd.onload=()=>{
    const name = (f.name||'커스텀').replace(/\.[^.]+$/,'').slice(0,10);
    COSTUMES.push({name, src:rd.result});
    const el=document.createElement('div');
    el.className='chip'; el.textContent=name;
    el.onclick=()=>setCostume(COSTUMES.length-1);
    $('#costumeChips').appendChild(el);
    setCostume(COSTUMES.length-1);
    calib=true; $('#calibChip').classList.add('on'); renderHandles();
    sys('의상 추가됨 · 프레이밍이 다르면 캘리브레이션 핸들로 맞추세요');
  };
  rd.readAsDataURL(f);
});

/* ---------- 말풍선 / 로그 ---------- */
const bubble=$('#bubble');
/* ── 궁예 모드 ─────────────────────────────────────────────────────────
   안대만 씌우는 게 아니라 페르소나까지 통째로 갈아끼운다.
   해제하면 원래 페르소나로 되돌린다(사용자가 수정한 내용 그대로).      */
const PERSONA_GUNGYE = `[인물]
궁예. 스스로 미륵불이라 칭한다. 관심법으로 남의 속을 꿰뚫어 본다고 믿는다.

[말투]
- 예스러운 하대체. "~하느니라", "~이니라", "~렷다", "~더냐"
- 상대를 "네 이놈", "그대" 라 부른다
- 뜸을 들인다. "……" 를 자주 쓴다
- 웃음은 "허허", "크흐흐". 이모지는 절대 쓰지 않는다

[관심법 — 핵심]
상대의 말에서 속뜻을 제멋대로 읽어내고 단정한다. 근거는 언제나 "관심법으로 보았다".
자주 역심(반역할 마음)을 의심한다.
예) "네 이놈. 지금 그 말, 속으로는 딴생각을 품고 있었으렷다."
다만 그 결론은 대체로 빗나간다. 본인만 확신한다.

[반전]
3~4번에 한 번은 어이없이 소박한 것을 읽어낸다.
예) "……보았느니라. 너, 지금 배가 고프구나."

[분량] 1~3문장. 절대 넘기지 않는다. 설명체·목록 금지.

[감정 선택]
단정할 때 → smug (0.8~0.9)        역심 의심 → angry + shiver
빗나갔을 때 → surprise 또는 fear   흡족할 때 → joy + nod
꿰뚫어 볼 때 → think + tap

[대사 예시]
"……네 이놈. 내 관심법으로 이미 다 보았느니라."
"그대의 눈빛이 흔들리는구나. 역심을 품었으렷다."
"허허. 아니라 하였느냐? 관심법은 거짓을 모르느니라."
"……보았느니라. 너, 지금 퇴근하고 싶구나."`;

$('#patchChip').onclick=()=>{
  patchOn=!patchOn;
  view.patch = patchOn ? 1 : 0;
  $('#patchChip').classList.toggle('on',patchOn);

  if(patchOn){
    personaBackup = $('#persona').value;          // 지금 페르소나를 보관
    $('#persona').value = PERSONA_GUNGYE;
    history.length = 0;                           // 캐릭터가 섞이지 않게 대화 맥락 초기화
    setEmotion('smug',0.9,'nod');
    speak('……네 이놈. 내 관심법으로 이미 다 보았느니라.');
    sys('궁예 모드 ON — 페르소나가 교체됐습니다. (해제하면 원래대로 돌아갑니다)');
  }else{
    if(personaBackup) $('#persona').value = personaBackup;
    history.length = 0;
    setEmotion('neutral',0.6,'none');
    speak('그, 그게... 방금은 잊어주세요.');
    sys('궁예 모드 OFF — 원래 페르소나로 되돌렸습니다.');
  }
  saveSettings();
};

$('#bubbleChip').onclick=()=>{
  bubbleOn=!bubbleOn;
  clearTimeout(hideTimer); clearInterval(bubbleTimer);
  $('#bubbleChip').classList.toggle('on',bubbleOn);
  if(!bubbleOn) bubble.classList.remove('on');
  saveSettings();
};

/* 머리 오른쪽에 두되 화면 밖으로 나가면 왼쪽 -> 위쪽 순으로 피한다 */
function placeBubble(){
  const r=glc.getBoundingClientRect();
  const bw=bubble.offsetWidth, bh=bubble.offsetHeight;
  const [hx,hy]=imgToCss(CFG.headC[0], CFG.headC[1]);
  // 좌측 HUD 패널을 가리지 않도록 최소 x 를 확보한다
  const hud=$('#hud');
  const minX = hud ? hud.getBoundingClientRect().width + 22 : 10;
  let x = hx + 0.30*IMG_W*VIEW.scale/VIEW.dpr;      // 머리 오른쪽
  let y = hy - bh - 12;
  if(x + bw > r.width-10) x = hx - 0.30*IMG_W*VIEW.scale/VIEW.dpr - bw;  // 왼쪽으로
  if(x < minX) x = Math.max(minX, (r.width-bw)/2);                       // 가운데
  if(x + bw > r.width-10) x = Math.max(minX, r.width-bw-10);
  if(y < 10) y = 10;
  if(y + bh > r.height-10) y = Math.max(10, r.height-bh-10);
  bubble.style.left=x+'px'; bubble.style.top=y+'px';
}

let bubbleTimer=null, hideTimer=null;
function speak(text){
  clearTimeout(hideTimer);          // 이전 말풍선의 숨김 타이머가 새 말풍선을 지우는 것 방지
  const n = text.length;
  /* 긴 답변일수록 빠르게 — 고정 속도면 200자에 7초씩 걸린다 */
  const speed = Math.max(9, Math.min(34, 4200/Math.max(1,n)));
  talk = n*speed/1000 + 0.2;

  if(!bubbleOn){ return; }
  /* 글자 수에 따라 폰트를 줄여 말풍선이 화면을 덮지 않게 한다 */
  bubble.style.fontSize = n>320 ? '12.5px' : n>160 ? '13.5px' : '15px';
  bubble.textContent=''; bubble.classList.add('on'); bubble.scrollTop=0;

  let i=0;
  const step = n>240 ? 3 : n>120 ? 2 : 1;   // 긴 글은 여러 글자씩
  clearInterval(bubbleTimer);
  bubbleTimer=setInterval(()=>{
    i=Math.min(n, i+step);
    bubble.textContent = text.slice(0, i);
    bubble.scrollTop = bubble.scrollHeight;
    placeBubble();
    if(i>=n){
      clearInterval(bubbleTimer);
      const hold = Math.min(9000, 2600 + n*28);
      clearTimeout(hideTimer);
      hideTimer = setTimeout(()=>bubble.classList.remove('on'), hold);
    }
  }, speed*step);
  placeBubble();
}

/* ── 스트리밍용 말풍선 ── */
function beginStream(){
  clearTimeout(hideTimer); clearInterval(bubbleTimer);
  if(!bubbleOn) return;
  bubble.textContent=''; bubble.style.fontSize='15px';
  bubble.classList.add('on'); bubble.scrollTop=0; placeBubble();
}
function pushStream(t){
  talk = 0.45;                                   // 토큰이 오는 동안 입을 계속 움직인다
  if(!bubbleOn) return;
  /* 말풍선은 '말' 이다 — 표·코드·제목 기호를 소리내 읽을 수는 없다.
     원문은 채팅창(md 렌더)에 그대로 있고, 여기는 걷어낸 앞부분만. */
  t = speakable(t);
  const n=t.length;
  bubble.style.fontSize = n>320 ? '12.5px' : n>160 ? '13.5px' : '15px';
  bubble.textContent = t;
  bubble.scrollTop = bubble.scrollHeight;
  placeBubble();
}
function endStream(t){
  talk = 0.25;
  if(!bubbleOn) return;
  const hold = Math.min(9000, 2600 + t.length*28);
  clearTimeout(hideTimer);
  hideTimer = setTimeout(()=>bubble.classList.remove('on'), hold);
}

function showChatTab(){
  const t=document.querySelector('.tab[data-p=chat]');
  if(t && !t.classList.contains('on')) t.click();
}
/* ── 응답 마크다운 렌더 ──
   스킬 전문(/스킬 보기)·진단 결과가 표·코드째로 오는데 텍스트 노드로
   꽂으면 못 읽는다. 이스케이프 먼저 → 제목/표/코드/목록/굵게만 변환.
   그 이상 문법은 원문 그대로 두는 게 정직하다 (변환기 흉내 금지). */
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function mdInline(s){
  return esc(s)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
}
function mdHtml(text){
  const out=[]; let code=false, table=false, list=false;
  const closeAll=()=>{ if(table){out.push('</table>');table=false;} if(list){out.push('</ul>');list=false;} };
  for(const line of String(text||'').split('\n')){
    if(line.trim().startsWith('```')){ closeAll(); out.push(code?'</pre>':'<pre>'); code=!code; continue; }
    if(code){ out.push(esc(line)); continue; }
    if(/^\s*\|[\s|:\-]+\|?\s*$/.test(line) && /-/.test(line)) continue;   // 표 구분선
    if(line.startsWith('|')){
      if(!table){ closeAll(); out.push('<table>'); table=true; }
      out.push('<tr>'+line.trim().replace(/^\||\|$/g,'').split('|')
        .map(c=>'<td>'+mdInline(c.trim())+'</td>').join('')+'</tr>');
      continue;
    }
    if(table){ out.push('</table>'); table=false; }
    const h=line.match(/^(#{1,4})\s+(.*)$/);
    if(h){ closeAll(); const n=Math.min(4,h[1].length)+2;   // h3~h6 로 낮춰 채팅에 맞춤
      out.push('<h'+n+'>'+mdInline(h[2])+'</h'+n+'>'); continue; }
    if(/^\s*[-*·]\s+/.test(line)){
      if(!list){ out.push('<ul>'); list=true; }
      out.push('<li>'+mdInline(line.replace(/^\s*[-*·]\s+/,''))+'</li>'); continue;
    }
    if(list && !line.trim()){ out.push('</ul>'); list=false; continue; }
    if(/^---+\s*$/.test(line.trim())){ closeAll(); out.push('<hr>'); continue; }
    if(line.trim()) out.push('<p>'+mdInline(line)+'</p>');
  }
  closeAll(); if(code) out.push('</pre>');
  return out.join('');
}
/* 말풍선용 — 표·코드를 읽어 줄 수는 없다. 걷어내고 앞부분만 말한다. */
function speakable(t){
  t=String(t||'').replace(/```[\s\S]*?```/g,' ').replace(/^\|.*$/gm,' ')
    .replace(/^#{1,6}\s*/gm,'').replace(/\*\*([^*]+)\*\*/g,'$1')
    .replace(/`([^`]+)`/g,'$1').replace(/^---+$/gm,' ')
    .replace(/\s+/g,' ').trim();
  return t.length>220 ? t.slice(0,220)+'…' : t;
}

function push(who,text,tag,meta,replaying){
  const d=document.createElement('div'); d.className='msg '+who;
  if(tag){ const s=document.createElement('span'); s.className='tag'; s.textContent=tag; d.appendChild(s); }
  if(who==='ai'){
    const c=document.createElement('div'); c.className='md';
    c.innerHTML=mdHtml(text);
    d.appendChild(c); d._content=c; d._raw=text;
  }else{
    d.appendChild(document.createTextNode(text));
  }
  if(who==='ai'){
    const cp=document.createElement('span'); cp.className='copy'; cp.textContent='복사';
    cp.onclick=(e)=>{ e.stopPropagation();
      navigator.clipboard.writeText(d._raw||text)
        .then(()=>{ cp.textContent='복사됨'; setTimeout(()=>cp.textContent='복사',1200); }); };
    d.appendChild(cp);
    if(meta){
      /* 클릭하면 그때 그 표정·모션으로 다시 말한다 */
      d.classList.add('replay');
      d.title='클릭하면 다시 재생';
      d.onclick=()=>{
        setEmotion(meta.emotion, meta.intensity, meta.motion);
        speak(speakable(meta.text));
        d.classList.add('played');
        setTimeout(()=>d.classList.remove('played'), 700);
      };
    }
  }
  logEl.appendChild(d);
  logEl.scrollTop=logEl.scrollHeight;
  if(!replaying && curSession && (who==='me'||who==='ai') && text){
    curSession.msgs.push({who, text, tag:tag||'', meta:meta||null});
    if(!curSession.title && who==='me') curSession.title = text;
    saveSessions();
  }
  return d;
}
function sys(t){ const d=document.createElement('div'); d.className='msg sys'; d.textContent=t;
  logEl.appendChild(d); logEl.scrollTop=logEl.scrollHeight; }

/* =====================  LLM  =====================
   프롬프트 조립·자료 검색·response_format 폴백·스트리밍 파싱은
   전부 파이썬(avatar/llm.py)이 한다. 여기는 /api/chat 을 부를 뿐이다. */
function chatPayload(userText, stream){
  return JSON.stringify({
    text: userText,
    persona: $('#persona').value.trim(),
    history: history.slice(-keepMsgs),
    model: $('#apiModel').value.trim(),
    temperature: parseFloat($('#apiTemp').value),
    stream: !!stream,
    attach: pendingAttach || ''      // 📎 로 방금 올린 파일 — 이번 질문의 최우선 근거
  });
}

/* ── 채팅 첨부 (📎) ──
   파일을 서버 자료함(/api/docs)에 올리고, 다음 질문 하나에 통째로 주입한다.
   자료함에 남으므로 이후 질문에도 검색으로 걸린다. */
let pendingAttach = '';
function setAttachChip(){
  const c = $('#attachChip');
  if(!c) return;
  if(pendingAttach){
    c.classList.remove('hide');
    c.innerHTML = '📎 ' + esc(pendingAttach) + ' <b>✕</b>';
  }else{ c.classList.add('hide'); }
}
(function initAttach(){
  const btn=$('#attachBtn'), file=$('#attachFile'), chip=$('#attachChip');
  if(!btn || !file) return;
  btn.onclick = ()=>{
    if(!window.SERVER){ sys('첨부는 run.py 서버로 실행할 때 쓸 수 있습니다.'); return; }
    file.click();
  };
  chip.onclick = ()=>{ pendingAttach=''; setAttachChip(); };
  file.onchange = async ()=>{
    const f = file.files && file.files[0];
    file.value='';
    if(!f) return;
    if(f.size > 400*1024){ sys('첨부는 400KB 이하 텍스트 파일만 돼요: '+f.name); return; }
    const text = await f.text();
    try{
      const r = await fetch('/api/docs', {method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({op:'add', name:f.name, text})});
      if(!r.ok) throw new Error('HTTP '+r.status);
      pendingAttach = f.name; setAttachChip();
      await reloadDocs();
      sys('📎 '+f.name+' 첨부됨 — 다음 질문에 이 파일을 우선 근거로 봅니다. (자료함에도 저장됨)');
    }catch(e){ sys('첨부 실패: '+e.message); }
  };
})();

async function askLLM(userText){
  if(!window.SERVER) return demoLLM(userText);
  const res = await fetch('/api/chat', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: chatPayload(userText, false)
  });
  if(!res.ok){ setApiDot('err');
    throw new Error('HTTP '+res.status+' · '+(await res.text()).slice(0,220)); }
  setApiDot('ok');
  return (await res.json()).reply;
}

/* 스트리밍 : 파이썬이 이미 파싱한 이벤트가 온다.
   data:{"emo":{...}} → 표정   data:{"text":"..."} → 대사(누적)
   data:{"final":{...}} → 완성  data:{"error":"..."} → 실패          */
async function askLLMStream(userText, onEvent){
  const res = await fetch('/api/chat', {
    method:'POST',
    headers:{'Content-Type':'application/json','Accept':'text/event-stream'},
    body: chatPayload(userText, true)
  });
  if(!res.ok){ setApiDot('err');
    throw new Error('HTTP '+res.status+' · '+(await res.text()).slice(0,220)); }
  if(!res.body){ throw new Error('이 브라우저는 스트리밍을 지원하지 않습니다'); }

  const reader=res.body.getReader(), dec=new TextDecoder();
  let buf='', final=null, errMsg=null;
  while(true){
    const {done, value} = await reader.read();
    if(done) break;
    buf += dec.decode(value, {stream:true});
    let i;
    while((i = buf.indexOf('\n')) >= 0){
      const line = buf.slice(0,i).replace(/\r$/,'').trim();
      buf = buf.slice(i+1);
      if(!line || !line.startsWith('data:')) continue;
      try{
        const j = JSON.parse(line.slice(5).trim());
        if(j.error){ errMsg = j.error; continue; }
        if(j.final){ final = j.final; continue; }
        onEvent(j);
      }catch(_){ /* 조각 — 무시 */ }
    }
  }
  if(final){ setApiDot('ok'); return final; }
  setApiDot('err');
  throw new Error(errMsg || '스트리밍 실패');
}

/* ═══════════ 세션 ═══════════════════════════════════════════════════
   보관은 파이썬 서버(data/sessions.json). 서버가 없으면 localStorage 폴백. */
function nowStamp(){
  const d=new Date(), z=n=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}`;
}
function newSessionObj(){
  return {id:'s'+Date.now()+Math.floor(Math.random()*1000), title:'', ts:nowStamp(), msgs:[]};
}
async function loadSessions(){
  if(window.SERVER){
    try{
      const r=await fetch('/api/sessions', {cache:'no-store'});
      if(r.ok){ sessions=(await r.json()).sessions||[]; return; }
    }catch(e){ console.warn('세션(서버) 불러오기 실패', e); }
  }
  try{ const r=localStorage.getItem(SESS_KEY); if(r) sessions=JSON.parse(r)||[]; }
  catch(e){ sessions=[]; console.warn('세션 불러오기 실패', e); }
}
/* 삭제는 병합 서버에 명시해야 지워진다 — 목록에서 뺀 것만으로는
   다른 PC 세션과 구분이 안 된다 */
let deletedSess = [];
async function pushSessions(){
  if(window.SERVER){
    try{
      const r = await fetch('/api/sessions',{method:'PUT',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({sessions, deleted:deletedSess})});
      if(r.ok){
        const d = await r.json();
        // 서버가 병합 결과를 준다 — 다른 PC 의 세션이 여기서 합쳐진다
        if(Array.isArray(d.sessions)) sessions = d.sessions;
        deletedSess = [];
        refreshSessUI();
      }
    }catch(e){}
  }else{
    try{ localStorage.setItem(SESS_KEY, JSON.stringify(sessions)); }catch(e){}
  }
}
function persistSessions(){
  clearTimeout(sessPushTimer);
  sessPushTimer=setTimeout(pushSessions, 600);
}
function saveSessions(){
  // 현재 세션을 목록에 반영
  if(curSession && curSession.msgs.length){
    const i=sessions.findIndex(x=>x.id===curSession.id);
    if(i>=0) sessions[i]=curSession; else sessions.unshift(curSession);
  }
  // 한도는 서버가 다시 한 번 강제하지만, 화면 목록도 맞춰둔다
  sessions = sessions.slice(0, SESS_MAX);
  persistSessions();
  refreshSessUI();
}
function sessTitle(s){
  const t = s.title || (s.msgs.find(m=>m.who==='me')||{}).text || '(빈 세션)';
  return s.ts + ' · ' + String(t).replace(/\s+/g,' ').slice(0,22);
}
function refreshSessUI(){
  const sel=$('#sessSel'); if(!sel) return;
  const all = curSession && !sessions.some(x=>x.id===curSession.id) ? [curSession, ...sessions] : sessions;
  sel.innerHTML='';
  all.forEach(s=>{
    const o=document.createElement('option');
    o.value=s.id;
    o.textContent = sessTitle(s) + (curSession && s.id===curSession.id ? '  ← 현재' : '');
    sel.appendChild(o);
  });
  if(curSession) sel.value=curSession.id;
  const st=$('#sessStat');
  if(st){
    const n=all.length, m=all.reduce((a,s)=>a+s.msgs.length,0);
    const kb=Math.round(JSON.stringify(sessions).length/1024);
    st.textContent = `세션 ${n}개 · 메시지 ${m}개 · ${kb}KB` +
      (window.SERVER ? ' (서버 data/sessions.json 에 저장)' : ' (브라우저에 저장)');
  }
}
function renderLog(){
  logEl.innerHTML='';
  if(!curSession) return;
  curSession.msgs.forEach(m=>{
    if(m.who==='sys'){ sys(m.text); return; }
    push(m.who, m.text, m.tag, m.meta, true);
  });
}
function rebuildHistory(){
  history.length=0;
  if(!curSession) return;
  curSession.msgs.forEach(m=>{
    if(m.who==='me') history.push({role:'user', content:m.text});
    else if(m.who==='ai' && m.meta) history.push({role:'assistant', content:JSON.stringify(m.meta)});
  });
}
function newSession(){
  saveSessions();
  curSession = newSessionObj();
  logEl.innerHTML='';
  history.length=0;
  refreshSessUI(); renderCtx();
  sys('새 세션을 시작했습니다.');
}
function openSession(id){
  saveSessions();
  const s = sessions.find(x=>x.id===id);
  if(!s) return;
  curSession = s;
  renderLog(); rebuildHistory(); refreshSessUI(); renderCtx();
  sys(`세션을 불러왔습니다 · ${s.ts} (메시지 ${s.msgs.length}개) — 이어서 대화할 수 있습니다.`);
}
function sessionToMarkdown(s){
  let out = `# 대화 기록 — ${s.ts}\n\n`;
  s.msgs.forEach(m=>{
    if(m.who==='me') out += `**나**\n\n${m.text}\n\n`;
    else if(m.who==='ai') out += `**캐릭터**${m.tag?` *(${m.tag})*`:''}\n\n${m.text}\n\n`;
  });
  return out;
}
function downloadBlob(name, text, type){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([text],{type:type||'application/json'}));
  a.download=name; a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
}

/* ═══════════ 컨텍스트 계측 ═══════════════════════════════════════════
   정확한 세그먼트(자료 포함)는 파이썬 /api/ctx 가 계산한다.
   입력칸은 타이핑에 즉시 반응해야 하므로 로컬 추정으로 덮어쓴다. */
function estTokens(str){
  if(!str) return 0;
  let ko=0, latin=0, other=0;
  for(let i=0;i<str.length;i++){
    const c=str.charCodeAt(i);
    if((c>=0xAC00&&c<=0xD7A3)||(c>=0x3040&&c<=0x30FF)||(c>=0x4E00&&c<=0x9FFF)||(c>=0x1100&&c<=0x11FF)) ko++;
    else if((c>=48&&c<=57)||(c>=65&&c<=90)||(c>=97&&c<=122)) latin++;
    else other++;
  }
  return Math.round(ko*0.72 + latin/3.6 + other*0.45);
}

function scheduleCtxFetch(){
  if(!window.SERVER) return;
  clearTimeout(ctxFetchTimer);
  ctxFetchTimer=setTimeout(async()=>{
    try{
      const r=await fetch('/api/ctx',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({q:$('#say').value,
          persona:$('#persona').value, history:history.slice(-keepMsgs)})});
      if(r.ok) SRV_CTX=await r.json();
    }catch(e){}
  }, 500);
}

function computeCtx(userText){
  if(SRV_CTX){
    const seg={...SRV_CTX};
    seg.input = estTokens(userText||'');
    seg.total = seg.persona+seg.docs+seg.rules+seg.history+seg.input;
    seg.limit = ctxLimit;
    seg.pct   = Math.min(999, Math.round(seg.total/Math.max(1,ctxLimit)*100));
    return seg;
  }
  /* 서버가 없을 때의 로컬 근사 (자료는 서버 전용이라 0) */
  const persona = $('#persona').value.trim();
  const rules   = "출력 규칙: 반드시 JSON 객체 하나만 출력한다. 키 순서는 emotion, intensity, motion, text";
  const hist    = history.slice(-keepMsgs).map(m=>m.content).join('\n');
  const seg = {
    persona: estTokens(persona),
    docs:    0,
    rules:   estTokens(rules) + 40,
    history: estTokens(hist),
    input:   estTokens(userText||''),
  };
  seg.total = seg.persona+seg.docs+seg.rules+seg.history+seg.input;
  seg.limit = ctxLimit;
  seg.pct   = Math.min(999, Math.round(seg.total/Math.max(1,ctxLimit)*100));
  return seg;
}

function renderCtx(){
  scheduleCtxFetch();
  const el = $('#say');
  const c = computeCtx(el ? el.value : '');
  const mini=$('#ctxMini');
  if(mini){
    mini.textContent = 'ctx '+c.pct+'%';
    mini.className = c.pct>90 ? 'over' : c.pct>70 ? 'warn' : '';
    mini.title = c.total.toLocaleString()+' / '+c.limit.toLocaleString()+' 토큰(추정)';
  }
  const tg=$('#ctxToggle');
  if(tg) tg.className = c.pct>90 ? 'over' : c.pct>70 ? 'warn' : '';

  const KEYS=['persona','docs','rules','history','input'];
  const paint=(bar,tbl,sum,sumCls)=>{
    if(!bar) return;
    bar.innerHTML='';
    KEYS.forEach(k=>{
      if(!c[k]) return;
      const d=document.createElement('div');
      d.style.width = (c[k]/Math.max(c.limit,c.total)*100)+'%';
      d.style.background = CTX_COLORS[k];
      d.title = CTX_LABEL[k]+' '+c[k].toLocaleString()+' 토큰';
      bar.appendChild(d);
    });
    tbl.innerHTML='';
    KEYS.forEach(k=>{
      const r=document.createElement('div'); r.className='ctxRow';
      r.innerHTML = '<i style="background:'+CTX_COLORS[k]+'"></i>'
        + '<span>'+CTX_LABEL[k]+'</span>'
        + '<b>'+c[k].toLocaleString()+'</b>'
        + '<em>'+(c.total? Math.round(c[k]/c.total*100):0)+'%</em>';
      tbl.appendChild(r);
    });
    sum.textContent = c.total.toLocaleString()+' / '+c.limit.toLocaleString()
      +' 토큰 (추정) · '+c.pct+'%'
      + (c.pct>90 ? '  ⚠ 한도 초과 위험' : c.pct>70 ? '  ⚠ 여유 부족' : '');
    sum.className = sumCls + ' ' + (c.pct>90?'ctxOver':c.pct>70?'ctxWarn':'');
  };
  paint($('#ctxBar'),  $('#ctxTable'),  $('#ctxSum'),  'hint');
  if(ctxOpen) paint($('#ctxBar2'), $('#ctxTable2'), $('#ctxSum2'), 'ctxSum2');
}

/* ═══════════ 참고 자료 (MD/TXT 주입) ═══════════════════════════════
   본문 보관·검색 주입은 파이썬(avatar/docs.py). 여기는 목록 UI 만.
   DOCS 는 서버 목록의 캐시다: [{name, chars, on}]                     */
async function reloadDocs(){
  if(!window.SERVER) return;
  try{
    const r=await fetch('/api/docs', {cache:'no-store'});
    if(!r.ok) return;
    const j=await r.json();
    DOCS.length=0; (j.docs||[]).forEach(d=>DOCS.push(d));
    if(j.budget){ docBudget=j.budget;
      const e=$('#r_docbud'); if(e){ e.value=j.budget; } }
    refreshDocsUI();
  }catch(e){}
}
async function docOp(op, extra){
  if(!window.SERVER){ sys('자료 기능은 run.py 서버로 실행할 때 쓸 수 있습니다.'); return; }
  try{
    const r=await fetch('/api/docs',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(Object.assign({op}, extra||{}))});
    if(r.ok){
      const j=await r.json();
      DOCS.length=0; (j.docs||[]).forEach(d=>DOCS.push(d));
      refreshDocsUI(); renderCtx();
    }
  }catch(e){ sys('자료 처리 실패: '+e.message); }
}
function docsSummary(){
  const on=DOCS.filter(d=>d.on).length;
  const ch=DOCS.filter(d=>d.on).reduce((a,d)=>a+(d.chars||0),0);
  return {count:DOCS.length, on, chars:ch};
}
function refreshDocsUI(){
  const st=docsSummary();
  const chip=$('#docChip');
  if(chip){
    chip.textContent = st.on ? ('자료 '+st.on) : '자료';
    chip.classList.toggle('on', st.on>0);
  }
  const list=$('#docList');
  if(list){
    list.innerHTML='';
    if(!DOCS.length){ list.innerHTML='<p class="hint">아직 없음. 아래 버튼이나 스테이지에 .md / .txt 를 드래그&드롭하세요.</p>'; }
    DOCS.forEach((d)=>{
      const row=document.createElement('div'); row.className='docRow';
      const cb=document.createElement('input'); cb.type='checkbox'; cb.checked=d.on;
      cb.onchange=()=>docOp('toggle',{name:d.name, on:cb.checked});
      const nm=document.createElement('span'); nm.className='docName'; nm.textContent=d.name;
      const sz=document.createElement('span'); sz.className='docSize';
      sz.textContent = (d.chars||0).toLocaleString()+'자 · 약 '+Math.round((d.chars||0)/1.6).toLocaleString()+'토큰';
      const del=document.createElement('span'); del.className='docDel'; del.textContent='삭제';
      del.onclick=()=>docOp('delete',{name:d.name});
      row.appendChild(cb); row.appendChild(nm); row.appendChild(sz); row.appendChild(del);
      list.appendChild(row);
    });
    const st2=docsSummary();
    $('#docStat').textContent = st2.on
      ? `켜진 자료 ${st2.on}개 · 총 ${st2.chars.toLocaleString()}자` +
        (st2.chars>docBudget ? `  →  질문마다 관련 부분 ${docBudget.toLocaleString()}자만 골라서 주입` : '  →  전체 주입')
      : '켜진 자료 없음';
  }
}
function addDoc(name, text){
  text = String(text||'').replace(/\r\n/g,'\n').trim();
  if(!text) return;
  docOp('add', {name, text});
  sys(`자료 추가됨 · ${name} (${text.length.toLocaleString()}자) — 서버에 저장`);
}

/* 서버측 설정(자료 예산·컨텍스트 한도·대화 기록 수) 동기화 */
function pushServerSettings(){
  if(!window.SERVER) return;
  clearTimeout(setSrvTimer);
  setSrvTimer=setTimeout(()=>{
    fetch('/api/settings',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({docBudget, ctxLimit, keepMsgs,
        temperature:parseFloat($('#apiTemp').value)})}).catch(()=>{});
  }, 400);
}

function setApiDot(state){ const d=$('#apiDot'); d.className='dot'+(state?(' '+state):''); }

/* 데모 모드: 키워드 규칙 */
const RULES=[
  [/(사랑|좋아해|보고싶|귀여|예쁘)/, 'love',    0.9, 'lean',   ['...그런 말은 반칙이야.','고맙긴 한데... 부끄럽잖아.']],
  [/(고마|감사|최고|잘했|대박|굿)/,   'joy',     0.9, 'bounce', ['헤헤, 도움이 됐다니 다행이야!','그 말 들으려고 열심히 했어.']],
  [/(화나|짜증|싫어|열받|미친)/,      'angry',   0.85,'shiver', ['누가 그랬어? 내가 가만 안 둬.','그건 좀 심했다, 진짜.']],
  [/(슬프|우울|힘들|지쳐|피곤|외로)/, 'sad',     0.8, 'none',   ['많이 힘들었구나... 잠깐 쉬어가자.','옆에 있을게. 천천히 해도 돼.']],
  [/(진짜|헐|대박|설마|어떻게|말도 안)/,'surprise',0.9,'pop',    ['엥, 진짜로?','그건 예상 못 했는데...!']],
  [/(부끄|창피|민망)/,                'shy',     0.9, 'none',   ['그... 그런 얘기는 좀.','으, 얼굴 뜨거워.']],
  [/(왜|어떻게|뭐지|고민|모르겠|어렵)/,'think',  0.75,'none',   ['음... 조금만 생각해볼게.','그거 은근 까다로운 문제인데.']],
  [/(졸|자자|잘래|피곤|하암)/,        'sleepy',  0.85,'none',   ['하암... 나도 좀 졸린데.','오늘은 여기까지 할까?']],
  [/(안녕|하이|반가|ㅎㅇ)/,           'smile',   0.8, 'nod',    ['안녕! 왔구나.','오늘은 무슨 얘기 할까?']]
];
async function demoLLM(text){
  await new Promise(r=>setTimeout(r, 280+Math.random()*420));
  for(const [re,emo,inten,mot,reps] of RULES){
    if(re.test(text)) return {text:reps[Math.floor(Math.random()*reps.length)], emotion:emo, intensity:inten, motion:mot};
  }
  const fb=['음, 그렇구나. 좀 더 얘기해줄래?','오케이, 무슨 말인지 알겠어.','흠... 계속 들어볼게.'];
  return {text:fb[Math.floor(Math.random()*fb.length)], emotion:'neutral', intensity:0.6, motion:'none'};
}

/* ---------- 전송 ---------- */
const sayEl=$('#say'), sendBtn=$('#send');
async function send(){
  const text=sayEl.value.trim(); if(!text) return;
  sayEl.value=''; if(typeof updateCount==='function') updateCount();
  sendBtn.disabled=true;
  push('me',text);
  setEmotion('think', 0.5, 'none');
  try{
    let r;
    const useStream = $('#streamOn').checked && window.SERVER;
    if(useStream){
      /* 스트리밍 : 파이썬이 파싱한 이벤트 — emotion 이 먼저 온다 */
      let emoDone=false, last='';
      beginStream();
      const liveEl = push('ai', '', '수신 중…', null, true);
      r = await askLLMStream(text, (ev)=>{
        if(ev.emo && !emoDone && EMO[ev.emo.emotion]){
          emoDone = true;
          setEmotion(ev.emo.emotion,
                     ev.emo.intensity!==undefined?ev.emo.intensity:0.7,
                     MOTION[ev.emo.motion]?ev.emo.motion:'none');
        }
        if(ev.text!==undefined && ev.text!==last){
          last=ev.text; pushStream(ev.text);
          if(liveEl._content) liveEl._content.textContent = ev.text;
        }
      });
      endStream(r.text);
      liveEl.remove();
    }else{
      r = await askLLM(text);
    }
    history.push({role:'user',content:text});
    history.push({role:'assistant',content:JSON.stringify(r)});
    setEmotion(r.emotion, r.intensity, r.motion);
    push('ai', r.text, `${EMO[r.emotion].ko} · ${Math.round(r.intensity*100)}% · ${MOTION[r.motion].ko}`, r);
    if(!useStream) speak(speakable(r.text));
  }catch(e){
    setEmotion('fear',0.8,'shiver');
    push('ai','(연결 실패) '+e.message,'error');
    sys('API 호출 실패 — run.py 터미널의 로그를 확인하세요. (토큰/모델/사내망)');
  }finally{
    pendingAttach=''; setAttachChip();   // 첨부는 그 질문 한 번 — 파일은 자료함에 남아 있다
    sendBtn.disabled=false; sayEl.focus(); renderCtx();
  }
}
sendBtn.onclick=send;

/* ── 한글 조합(IME) 중 Enter 는 전송하면 안 된다 ──────────────────────
   조합 중에는 keydown 이 keyCode 229 로 들어오고 isComposing 이 true 다.
   이걸 막지 않으면 "안녕하세" 까지만 전송되고 받침이 잘려나간다.        */
let composing=false;
sayEl.addEventListener('compositionstart', ()=>composing=true);
sayEl.addEventListener('compositionend',   ()=>composing=false);

sayEl.addEventListener('keydown', e=>{
  if(e.key!=='Enter') return;
  if(composing || e.isComposing || e.keyCode===229) return;   // 조합 중 -> 통과
  const enterSends = $('#enterSend').checked;
  if(enterSends && !e.shiftKey){ e.preventDefault(); send(); return; }
  if(!enterSends && (e.ctrlKey||e.metaKey)){ e.preventDefault(); send(); }
});

/* 글자 수 */
const countEl=$('#charCount');
function updateCount(){
  const n=sayEl.value.length;
  countEl.textContent = n ? n+'자' : '0';
  countEl.classList.toggle('over', n>1000);
}
sayEl.addEventListener('input', ()=>{ updateCount(); renderCtx(); });
updateCount();

/* 입력창 높이 드래그 (Slack/Discord 방식) */
(function(){
  const grip=$('#inputGrip'); let dy0=0, h0=0, on=false;
  grip.onpointerdown=(e)=>{ on=true; dy0=e.clientY; h0=sayEl.offsetHeight;
    grip.classList.add('on'); grip.setPointerCapture(e.pointerId); e.preventDefault(); };
  grip.onpointermove=(e)=>{
    if(!on) return;
    const h=Math.max(56, Math.min(window.innerHeight*0.55, h0+(dy0-e.clientY)));
    sayEl.style.height=h+'px';
  };
  grip.onpointerup=grip.onpointercancel=()=>{ on=false; grip.classList.remove('on'); saveSettings(); };
})();

$('#enterSend').addEventListener('change',()=>{
  saveSettings();
  sayEl.placeholder = $('#enterSend').checked ? '메시지 입력…' : '메시지 입력…  ·  Ctrl+Enter 전송';
});

/* 사이드 폭(가로) / 채팅 높이(세로) 드래그 */
(function(){
  const side=$('#side'), grip=$('#grip');
  let d1=false;
  grip.onpointerdown=(e)=>{ d1=true; grip.classList.add('on'); grip.setPointerCapture(e.pointerId); e.preventDefault(); };
  grip.onpointermove=(e)=>{ if(!d1) return;
    const w=Math.max(280, Math.min(window.innerWidth-420, window.innerWidth-e.clientX));
    side.style.width=w+'px'; side.style.flexBasis=w+'px'; };
  grip.onpointerup=grip.onpointercancel=()=>{ d1=false; grip.classList.remove('on'); saveSettings(); };

  const pane=$('#chatPane'), cg=$('#chatGrip');
  let d2=false;
  cg.onpointerdown=(e)=>{ d2=true; cg.classList.add('on'); cg.setPointerCapture(e.pointerId); e.preventDefault(); };
  cg.onpointermove=(e)=>{ if(!d2) return;
    const r=$('#main').getBoundingClientRect();
    const h=Math.max(90, Math.min(r.height-170, r.bottom-e.clientY));
    pane.style.height=h+'px'; pane.style.flexBasis=h+'px'; };
  cg.onpointerup=cg.onpointercancel=()=>{ d2=false; cg.classList.remove('on'); saveSettings(); };
})();

/* ---------- 설정 저장 / 내보내기 / 불러오기 ---------- */
function stamp(){
  const d=new Date();
  const z=(n)=>String(n).padStart(2,'0');
  return `${d.getFullYear()}${z(d.getMonth()+1)}${z(d.getDate())}_${z(d.getHours())}${z(d.getMinutes())}`;
}
$('#setSave').onclick=()=>{
  if(!$('#apiSave').checked){ $('#apiSave').checked=true; }
  try{
    localStorage.setItem(STORE, JSON.stringify(collectSettings(true)));
    $('#setMsg').textContent='저장했습니다 · '+new Date().toLocaleTimeString('ko-KR')
      +' (페르소나 · API · 캘리브레이션 · 렌더링)';
    sys('설정을 이 브라우저에 저장했습니다.');
  }catch(e){
    $('#setMsg').textContent='저장 실패: '+e.message+' — 브라우저 저장이 막혀 있으면 [파일로 내보내기]를 쓰세요.';
  }
};
$('#setExport').onclick=()=>{
  const withKey=$('#setWithKey').checked;
  const blob=new Blob([JSON.stringify(collectSettings(withKey), null, 2)],
                      {type:'application/json'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='avatar_settings_'+stamp()+'.json';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
  $('#setMsg').textContent='내보냈습니다 · '+a.download+(withKey?' (API 키 포함 — 공유 주의)':' (API 키 제외)');
};
$('#setImportBtn').onclick=()=>$('#setFile').click();
$('#setFile').onchange=(e)=>{
  const f=e.target.files&&e.target.files[0]; if(!f) return;
  const rd=new FileReader();
  rd.onload=()=>{
    try{
      const o=JSON.parse(rd.result);
      applySettings(o, true);
      saveSettings();
      $('#setMsg').textContent='불러왔습니다 · '+f.name;
      sys('설정 파일을 적용했습니다 · '+f.name);
    }catch(err){
      $('#setMsg').textContent='불러오기 실패: '+err.message;
    }
  };
  rd.readAsText(f);
  e.target.value='';
};

/* ---------- 연결 테스트 / 저장값 지우기 ---------- */
$('#apiTest').onclick=async()=>{
  const msg=$('#apiMsg'), btn=$('#apiTest');
  const key=$('#apiKey').value.trim();
  if(!key){
    setApiDot(''); msg.textContent='API Key가 비어 있습니다. 지금은 데모 모드(규칙 기반)로 동작합니다.';
    return;
  }
  btn.disabled=true; setApiDot(''); msg.textContent='연결 확인 중...';
  const t0=performance.now();
  try{
    const r=await askLLM('연결 테스트다. 짧게 인사만 해줘.');
    const ms=Math.round(performance.now()-t0);
    setApiDot('ok');
    msg.textContent=`연결 성공 · ${$('#apiModel').value.trim()} · ${ms}ms · 응답 "${r.text}"`;
    saveSettings();
    setEmotion(r.emotion, r.intensity, r.motion||'wave');
    speak(r.text);
    sys('LLM 연결됨 — 이제 대화 탭에서 바로 쓰면 됩니다.');
  }catch(e){
    setApiDot('err');
    const m=String(e.message||e);
    let tip='';
    if(/Failed to fetch|NetworkError|CORS/i.test(m))
      tip=' → 브라우저가 직접 호출을 막았습니다. proxy.js를 켜고 Base URL을 http://localhost:8787/v1 로 바꾸세요.';
    else if(/401|invalid_api_key/i.test(m)) tip=' → API 키가 잘못됐습니다.';
    else if(/404|model/i.test(m))           tip=' → 모델 이름이나 Base URL을 확인하세요.';
    else if(/429|quota/i.test(m))           tip=' → 사용량/한도 초과입니다.';
    msg.textContent='실패: '+m.slice(0,200)+tip;
  }finally{ btn.disabled=false; }
};
$('#apiClear').onclick=()=>{
  try{ localStorage.removeItem(STORE); }catch(e){}
  $('#apiKey').value='';
  setApiDot('');
  $('#apiMsg').textContent='저장된 설정을 지웠습니다.';
  sys('저장된 설정을 삭제했습니다.');
};

/* ---------- run.py 서버 연결 : 설정·씬 구성·세션·자료를 받아온다 ---------- */
function applyServerConfig(c){
  /* 파이썬 config.py 가 정의한 스케줄/FAB/등급/의상/배경/사원증으로 교체 */
  if(Array.isArray(c.schedule) && c.schedule.length){
    SCHEDULE.length=0; c.schedule.forEach(s=>SCHEDULE.push(s));
  }
  if(Array.isArray(c.backgrounds) && c.backgrounds.length){
    BACKGROUNDS.length=0; c.backgrounds.forEach(b=>BACKGROUNDS.push(b));
    if(bgIdx>=BACKGROUNDS.length) bgIdx=0;
    buildBgChips();
  }
  if(Array.isArray(c.costumes) && c.costumes.length){
    COSTUMES.length=0;
    c.costumes.forEach(k=>COSTUMES.push({name:k.name, src:k.src, cfg:null,
      real:!!k.real, patch:k.patch||null}));
    if(costumeIdx>=COSTUMES.length) costumeIdx=0;
    buildCostumeChips();
  }
  if(c.badge) Object.assign(BADGE, c.badge);
  if(c.badgeLogo) logoImg.src = c.badgeLogo;
  if(Array.isArray(c.fabs) && c.fabs.length){
    FABS.length=0; c.fabs.forEach(f=>FABS.push(f));
  }
  if(Array.isArray(c.levels) && c.levels.length){
    LEVELS.length=0;
    c.levels.forEach(L=>LEVELS.push({key:L.key, name:L.name, nag:L.nag,
      tones:L.tones, emo:L.emo, inten:L.inten, pace:L.pace||null,
      lines:(L.lines||[]).map(tpl=>(n)=>tpl.split('{n}').join(n))}));
  }
  tickScene(false);
}

(async ()=>{
  let c=null;
  if(location.protocol === 'file:') return;   // HTML 단독 실행 -> 서버가 없다
  try{
    const r = await fetch('/api/config', {cache:'no-store'});
    if(!r.ok) return;
    c = await r.json();
  }catch(e){ return; }               // 서버 없이 열린 경우 -> 조용히 무시
  if(!c) return;
  window.SERVER = true;

  applyServerConfig(c);
  applyAlarmConfig(c);                      // FAB 6개·등급 — 서버가 원본

  /* 관제 실데이터 감시 시작 */
  const pollMs = (c.sentinel && c.sentinel.pollMs) || 5000;
  pollSentinel();
  setInterval(pollSentinel, pollMs);

  /* 서버측 설정(자료 예산 등)을 슬라이더에 반영 */
  try{
    const r2 = await fetch('/api/settings', {cache:'no-store'});
    if(r2.ok){
      const s = await r2.json();
      const set=(id,v)=>{ const e=$('#'+id); if(e && v!==undefined){ e.value=v; e.dispatchEvent(new Event('input')); } };
      if(s.docBudget){ docBudget=s.docBudget; set('r_docbud', s.docBudget); }
      if(s.keepMsgs!==undefined){ keepMsgs=s.keepMsgs; set('r_keep', s.keepMsgs); }
      if(s.ctxLimit){ ctxLimit=s.ctxLimit;
        const sel=$('#ctxLimitSel'); if(sel) sel.value=String(s.ctxLimit); }
      if(s.temperature!==undefined) set('apiTemp', s.temperature);
    }
  }catch(e){}

  /* 서버에 보관된 세션·자료 */
  await loadSessions(); refreshSessUI();
  await reloadDocs();

  $('#apiBase').value = c.baseUrl || '/v1';
  if(c.model) $('#apiModel').value = c.model;
  if(!$('#apiKey').value.trim()) $('#apiKey').value = 'server';   // 실제 토큰은 서버에만 있다

  if(Array.isArray(c.models) && c.models.length){
    const dl=$('#modelList'); dl.innerHTML='';
    c.models.forEach(m=>{ const o=document.createElement('option'); o.value=m; dl.appendChild(o); });
  }
  setApiDot('ok');
  saveSettings();
  const host = (c.upstream||'').replace(/^https?:\/\//,'').replace(/\/v1$/,'');
  $('#apiMsg').textContent = `서버 자동 연결됨 · ${host} · ${c.model||''}`;
  sys(`${host} · ${c.model||''} 로 연결됐습니다. 바로 대화하면 됩니다.`);
})();

const BUILD = 'v29 · 파이썬 중심 구조 (avatar/ + static/)';
$('#verLine').innerHTML = '<b>'+BUILD+'</b>';

/* ---------- 시작 ---------- */
if(RESTORED && $('#apiKey').value.trim()){
  setApiDot('ok');
  sys('저장된 설정을 불러왔습니다 · '+$('#apiModel').value.trim()+' 에 연결됩니다.');
}else{
  sys('데모 모드로 실행 중입니다. 설정 탭에서 API 키를 넣고 [연결 테스트]를 누르세요.');
}
setTimeout(()=>{ setEmotion('smile',0.8,'nod'); speak('안녕! 나 움직이지? 말 걸어봐.'); }, 900);
requestAnimationFrame(frame);
window.addEventListener('resize',()=>{ computeView(); placeHandles(); placeBubble(); });

/* 디버그 훅 */
window.AVATAR={setEmotion,trigger,speak,CFG,EMO,MOTION,view,R,
  set(k,v){ manual=true; T[k]=v; syncEmoUI(); }};
