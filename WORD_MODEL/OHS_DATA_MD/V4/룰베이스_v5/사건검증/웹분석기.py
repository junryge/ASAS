#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹분석기 — 한줄분석/발동이벤트_점수분석/reason_컬럼찾기 를 브라우저에서 한 번에

설치 필요 X (Python 표준 라이브러리만 사용).

실행:
  python 웹분석기.py
  → 브라우저 자동으로 http://localhost:8765 열림.
  → 3개 탭에 각각 데이터 넣으면 결과 즉시 표시.

같은 폴더에 다음 3개 파일 필요:
  · 한줄분석.py
  · 발동이벤트_점수분석.py
  · reason_컬럼찾기.py
"""
import http.server
import socketserver
import subprocess
import sys
import os
import urllib.parse
import webbrowser
import tempfile
import html as _html
from pathlib import Path

# 윈도우 cp949 콘솔에서도 한글/유니코드 깨지지 않게 stdout UTF-8 강제
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PORT = 8765
BASE = Path(__file__).resolve().parent
PY = sys.executable  # 현재 파이썬
# subprocess 로 호출되는 하위 스크립트도 UTF-8 출력하도록 환경변수 강제
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')

SCRIPTS = {
    'oneline':   BASE / '한줄분석.py',
    'fileanl':   BASE / '발동이벤트_점수분석.py',
    'reason':    BASE / 'reason_컬럼찾기.py',
}

INDEX_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>룰베이스 v6 — 웹 분석기</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', '맑은 고딕', sans-serif; margin: 0;
         background: #f4f6f8; color: #222; }
  header { background: #1f2937; color: #fff; padding: 14px 24px; }
  header h1 { margin: 0; font-size: 18px; }
  header .sub { font-size: 12px; opacity: .7; margin-top: 4px; }
  .tabs { display: flex; background: #fff; border-bottom: 1px solid #e5e7eb;
          padding: 0 16px; }
  .tab { padding: 12px 20px; cursor: pointer; border-bottom: 3px solid transparent;
         font-weight: 600; color: #6b7280; }
  .tab.active { color: #1f2937; border-color: #2563eb; }
  .panel { padding: 22px 24px; max-width: 1200px; }
  .panel h2 { font-size: 16px; margin: 0 0 10px 0; color: #111; }
  .panel .desc { font-size: 13px; color: #6b7280; margin-bottom: 12px; }
  textarea, input[type=text], input[type=file] {
    width: 100%; font-family: 'Consolas', monospace; font-size: 13px;
    padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; }
  textarea { min-height: 100px; }
  .row { display: flex; gap: 10px; align-items: center; margin-top: 8px; }
  .row > * { flex-shrink: 0; }
  .row .grow { flex-grow: 1; }
  button { background: #2563eb; color: #fff; border: 0; padding: 10px 22px;
           border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; }
  button:hover { background: #1d4ed8; }
  button.sec { background: #6b7280; }
  pre.result { background: #1f2937; color: #f3f4f6; padding: 18px;
               border-radius: 8px; font-size: 13px; line-height: 1.6;
               white-space: pre-wrap; word-break: break-all; margin-top: 16px;
               max-height: 70vh; overflow: auto; }
  pre.result:empty { display: none; }
  .hidden { display: none; }
  label { font-size: 13px; color: #374151; font-weight: 600; }
  .hint { font-size: 12px; color: #9ca3af; margin-top: 4px; }
</style></head>
<body>
<header>
  <h1>🔍 룰베이스 v6 — 웹 분석기</h1>
  <div class="sub">한줄분석 / 발동이벤트 점수분석 / reason 컬럼찾기 — 통합 UI</div>
</header>

<div class="tabs">
  <div class="tab active" data-tab="oneline">① 한줄분석 (행 한 줄)</div>
  <div class="tab" data-tab="fileanl">② 발동이벤트 파일분석</div>
  <div class="tab" data-tab="reason">③ reason 컬럼찾기</div>
</div>

<!-- ① 한줄분석 -->
<div class="panel" id="panel-oneline">
  <h2>① 한줄분석</h2>
  <div class="desc">발동이벤트.csv 의 데이터 한 줄을 복사해서 붙여넣기. (헤더 X, 데이터만)</div>
  <textarea id="oneline-input" placeholder="M16A_HUBROOM_PR.csv,2026-06-16 07:50,..."></textarea>
  <div class="row"><button onclick="run('oneline')">분석 실행</button></div>
  <pre class="result" id="oneline-out"></pre>
</div>

<!-- ② 발동이벤트 파일분석 -->
<div class="panel hidden" id="panel-fileanl">
  <h2>② 발동이벤트 파일분석</h2>
  <div class="desc">파일 업로드 후 모드 선택. 최고점 N개 또는 특정 시각(HH:MM) 분석.</div>
  <div class="row">
    <label class="grow">파일: <input type="file" id="fileanl-file" accept=".csv"></label>
  </div>
  <div class="row">
    <label>모드:
      <select id="fileanl-mode">
        <option value="top">최고점 N개</option>
        <option value="time">특정 시각 (HH:MM)</option>
      </select>
    </label>
    <label>값: <input type="text" id="fileanl-arg" placeholder="3  또는  06:55" style="width:140px"></label>
    <button onclick="run('fileanl')">분석 실행</button>
  </div>
  <div class="hint">예) 모드=최고점 + 값=3 → 점수 높은 3개 / 모드=시각 + 값=07:50 → 그 시각</div>
  <pre class="result" id="fileanl-out"></pre>
</div>

<!-- ③ reason 컬럼찾기 -->
<div class="panel hidden" id="panel-reason">
  <h2>③ reason 컬럼찾기</h2>
  <div class="desc">사건단위.csv 또는 발동이벤트.csv 의 reason / relation 텍스트 붙여넣기.</div>
  <textarea id="reason-input" placeholder="hot_area=M16HUB; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=20.13분/기준9.0),R-D(STB=100.0%)]; ..."></textarea>
  <div class="row"><button onclick="run('reason')">분석 실행</button></div>
  <pre class="result" id="reason-out"></pre>
</div>

<script>
// 탭 전환
document.querySelectorAll('.tab').forEach(t => {
  t.onclick = () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.getElementById('panel-' + t.dataset.tab).classList.remove('hidden');
  };
});

async function run(kind) {
  const out = document.getElementById(kind + '-out');
  out.textContent = '⏳ 실행 중...';
  try {
    const fd = new FormData();
    if (kind === 'oneline') {
      fd.append('data', document.getElementById('oneline-input').value);
    } else if (kind === 'reason') {
      fd.append('data', document.getElementById('reason-input').value);
    } else if (kind === 'fileanl') {
      const file = document.getElementById('fileanl-file').files[0];
      if (!file) { out.textContent = '❌ 파일 선택 안 됨'; return; }
      fd.append('file', file);
      fd.append('mode', document.getElementById('fileanl-mode').value);
      fd.append('arg',  document.getElementById('fileanl-arg').value);
    }
    const res = await fetch('/run/' + kind, { method: 'POST', body: fd });
    const text = await res.text();
    out.textContent = text;
  } catch (e) {
    out.textContent = '❌ 오류: ' + e.message;
  }
}
</script>
</body></html>
"""


def parse_multipart(content_type, body):
    """간이 multipart/form-data 파서 (Python 표준 cgi 모듈 없이)."""
    # boundary 추출
    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part[9:].strip('"')
            break
    if not boundary:
        return {}
    sep = b'--' + boundary.encode()
    parts = body.split(sep)
    fields = {}
    for p in parts:
        p = p.strip(b'\r\n')
        if not p or p == b'--':
            continue
        # 헤더와 본문 분리
        if b'\r\n\r\n' not in p:
            continue
        hdr_blob, val = p.split(b'\r\n\r\n', 1)
        val = val.rstrip(b'\r\n')
        hdr_text = hdr_blob.decode('utf-8', errors='replace')
        # name 추출
        name = None
        filename = None
        for line in hdr_text.split('\r\n'):
            if line.lower().startswith('content-disposition'):
                for token in line.split(';'):
                    token = token.strip()
                    if token.startswith('name='):
                        name = token[5:].strip('"')
                    elif token.startswith('filename='):
                        filename = token[9:].strip('"')
        if not name:
            continue
        if filename is not None:
            # 파일 — bytes 그대로
            fields[name] = {'filename': filename, 'data': val}
        else:
            fields[name] = val.decode('utf-8', errors='replace')
    return fields


def call_oneline(data):
    """한줄분석.py 호출 (stdin 으로 데이터 + q)."""
    inp = f"{data}\nq\n"
    res = subprocess.run([PY, str(SCRIPTS['oneline'])],
                         input=inp, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', cwd=str(BASE),
                         env=_CHILD_ENV)
    return (res.stdout or '') + (('\n' + res.stderr) if res.stderr else '')


def call_reason(data):
    inp = f"{data}\nq\n"
    res = subprocess.run([PY, str(SCRIPTS['reason'])],
                         input=inp, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', cwd=str(BASE),
                         env=_CHILD_ENV)
    return (res.stdout or '') + (('\n' + res.stderr) if res.stderr else '')


def call_fileanl(file_bytes, mode, arg):
    """발동이벤트_점수분석.py 호출 (임시파일에 데이터 저장 후 인자 전달)."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tf:
        tf.write(file_bytes)
        tmp_path = tf.name
    try:
        args = [PY, str(SCRIPTS['fileanl']), tmp_path]
        if mode == 'time' and arg.strip():
            args.append(arg.strip())
        elif mode == 'top':
            n = arg.strip() or '1'
            args += ['--top', n]
        res = subprocess.run(args, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', cwd=str(BASE),
                             env=_CHILD_ENV)
        return (res.stdout or '') + (('\n' + res.stderr) if res.stderr else '')
    finally:
        try: os.unlink(tmp_path)
        except: pass


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass  # 콘솔 조용

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._send(200, INDEX_HTML); return
        self._send(404, 'Not Found', 'text/plain; charset=utf-8')

    def do_POST(self):
        if not self.path.startswith('/run/'):
            self._send(404, 'Not Found', 'text/plain; charset=utf-8'); return
        kind = self.path[5:]
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            ctype = self.headers.get('Content-Type', '')
            fields = parse_multipart(ctype, body)
            if kind == 'oneline':
                text = call_oneline(fields.get('data', ''))
            elif kind == 'reason':
                text = call_reason(fields.get('data', ''))
            elif kind == 'fileanl':
                f = fields.get('file')
                if not f or not isinstance(f, dict):
                    text = '❌ 파일이 업로드 안 됨'
                else:
                    text = call_fileanl(f['data'], fields.get('mode','top'),
                                        fields.get('arg',''))
            else:
                text = '❌ 알 수 없는 분석 종류: ' + kind
            self._send(200, text, 'text/plain; charset=utf-8')
        except Exception as e:
            self._send(500, f'❌ 서버 오류: {e}', 'text/plain; charset=utf-8')


def main():
    # 스크립트 존재 확인
    missing = [k for k, p in SCRIPTS.items() if not p.exists()]
    if missing:
        print(f"⚠️ 같은 폴더에 다음 파일이 없습니다: {missing}")
        print(f"   경로: {BASE}")
        return
    print(f"\n  🔍 룰베이스 v6 웹 분석기 시작")
    print(f"  📂 작업 폴더: {BASE}")
    print(f"  🌐 주소: http://localhost:{PORT}")
    print(f"  ⛔ 종료: Ctrl+C\n")
    try:
        webbrowser.open(f'http://localhost:{PORT}')
    except Exception:
        pass
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  종료.")


if __name__ == '__main__':
    main()
