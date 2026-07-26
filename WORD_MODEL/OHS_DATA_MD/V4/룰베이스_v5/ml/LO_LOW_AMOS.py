#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LO_LOW_AMOS — 로그프레소 조회 → 발동이벤트.csv 에 4컬럼 직접 기입 (운영용)
====================================================================
별도 병합파일 안 만들고 발동이벤트.csv 그 자체에 컬럼을 추가/기입한다.
매분 발동이벤트에 새 행이 붙으면 → 그 분만 로그프레소 조회해서 채움 (이미 채운 행은 유지).

조회 (MCP_NM=="BR"):
  table from=... to=... ATLAS_BOTTLENECK_ANOMALY | search MCP_NM == "BR" | sort _time
  table from=... to=... ATLAS_QUEUE_ANOMALY      | search MCP_NM == "BR" | sort _time

추가 4컬럼 (시간정렬: 발동이벤트 datetime T = 로그프레소 EVENT_DT T, 같은 분끼리):
  BOTTLENECK_downward_anomaly_cols, BOTTLENECK_upward_anomaly_cols
  QUEUE_downward_anomaly_cols,      QUEUE_upward_anomaly_cols
  ※ 로그프레소가 T분을 아직 안 썼으면 그 사이클엔 공란 → 다음 사이클(1분 뒤)
    최근 5분 재조회가 자동으로 채움 (수집만 늦게, 시간은 안 어긋남)

실행 (pip: requests 만):
  운영(1분 루프):  python LO_LOW_AMOS.py --event .\predict_tobe --loop
                   (--event 에 폴더를 주면 그 안의 최신 *발동이벤트*.csv 자동 선택
                    → 20260714_발동이벤트.csv 처럼 매일 새 파일이 생겨도 자동 전환)
  1회만:           python LO_LOW_AMOS.py --event .\predict_tobe\20260713_발동이벤트.csv
  과거 일괄백필:   python LO_LOW_AMOS.py --event .\predict_tobe --alldays
                   (폴더 안 모든 날짜 파일에 4컬럼 기입 — 로그프레소 보존기간 내)
  테스트(원본보존): 위에 --out .\테스트.csv 추가
  옵션: --lag 0(같은 분) · --interval 60 · --host/--port/--apikey

run_ml 통합 (스레드):
  import LO_LOW_AMOS
  threading.Thread(target=LO_LOW_AMOS.run_watch, daemon=True).start()
  # 경로 다르면: threading.Thread(target=LO_LOW_AMOS.run_watch,
  #                kwargs={'event': r'D:\경로\predict_tobe'}, daemon=True).start()

동작 원리:
  · 처음 실행: 파일 전체(안 채워진 행 전부) 범위를 한 번에 조회해서 백필
  · 루프 중: 새 행 + 최근 5분만 재조회(로그프레소 늦게 쓰인 분 자동 보정) → 쿼리 가볍다
  · 파일에 4컬럼 없으면 헤더에 추가, 있으면 그대로 이어서 기입
  · 조회 실패(서버 불안정)면 그 사이클은 파일 안 건드리고 다음 분에 재시도
  · 저장은 임시파일 → 원자 교체(os.replace), 교체 직전 파일 변경 감지되면 스킵 후 재시도
  · 자정 전환: 새 날짜 파일로 넘어가도 전날 파일을 6사이클 더 마무리 기입
    (로그프레소가 23:59 등 마지막 분을 자정 넘어 쓰기 때문 — 23:59까지 빠짐없이 채움)
"""
import argparse, csv, os, re, sys, time, urllib.parse
from datetime import datetime, timedelta
from io import StringIO

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로그프레소 접속 (logpresso_client.py 와 동일 — 검증된 직접 HTTP 방식)
HOST = '10.40.42.27'
PORT = 8888
API_KEY = 'db1d2335-49cf-e859-3519-1ca132922e38'

TABLES = {'BOTTLENECK': 'ATLAS_BOTTLENECK_ANOMALY', 'QUEUE': 'ATLAS_QUEUE_ANOMALY'}
NEW_COLS = ['BOTTLENECK_downward_anomaly_cols', 'BOTTLENECK_upward_anomaly_cols',
            'QUEUE_downward_anomaly_cols', 'QUEUE_upward_anomaly_cols']
RECHECK_MIN = 5  # 최근 N분은 매 사이클 재조회 (로그프레소 지연 기입 보정)


def query_logpresso(query, a, timeout=180):
    """LPQL 실행 → CSV 텍스트 (재시도 3회).
    반환: 텍스트(정상, 0건이면 빈 문자열) / None(서버오류·연결실패)
    ※ HTTP 200 + 본문 '\\n' = 결과 0건 (정상 응답이므로 실패로 보지 않음)"""
    clean_q = ' '.join(query.split())
    url = (f'http://{a.host}:{a.port}/logpresso/httpexport/query.csv'
           f'?_apikey={a.apikey}&_q={urllib.parse.quote(clean_q, safe="")}')
    for attempt in range(3):
        try:
            resp = requests.get(url, verify=False, timeout=timeout)
            if resp.status_code == 200:
                body = resp.text
                if body.strip().startswith('<!'):
                    print(f'  ⚠️ Logpresso HTML 에러페이지 반환 · 쿼리: {clean_q}')
                    return None
                return body if body.strip() else ''   # 빈 본문 = 0건 (정상)
            if resp.status_code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            print(f'  ⚠️ Logpresso HTTP {resp.status_code}: {resp.text[:150]!r}')
            return None
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            if attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            print('  ⚠️ Logpresso 연결 실패')
            return None
        except Exception as e:
            print(f'  ⚠️ Logpresso 예외: {e}')
            return None
    return None


MARGIN_MIN = 3  # 조회 구간 앞뒤 여유 (table from/to 는 _time 기준, EVENT_DT 와 몇 초~몇 분 차이)


def fetch_range(dt_from, dt_to, a, cache, quiet=False):
    """두 테이블을 [dt_from, dt_to] 조회 → cache[pfx][분키]=(down,up) 갱신.
    return False = 서버오류(기입 보류) / True = 정상(0건 포함)."""
    qf = dt_from - timedelta(minutes=MARGIN_MIN)
    qt = dt_to + timedelta(minutes=MARGIN_MIN)
    for pfx, tbl in TABLES.items():
        lpql = (f'table from={qf:%Y%m%d%H%M}00 to={qt:%Y%m%d%H%M}59 {tbl} '
                f'| search MCP_NM == "{a.mcp}" | sort _time')
        text = query_logpresso(lpql, a)
        if text is None:
            return False
        n = 0
        for r in csv.DictReader(StringIO(text)):
            k = (r.get('EVENT_DT') or '').strip()[:16]  # 초 버리고 분단위
            if k:
                cache[pfx][k] = ((r.get('downward_anomaly_cols') or '').strip(),
                                 (r.get('upward_anomaly_cols') or '').strip())
                n += 1
        if n == 0:
            print(f'  ⚠️ [{tbl}] {qf:%m/%d %H:%M}~{qt:%H:%M} → 0건 (공란 기입)')
            print(f'     ↳ 쿼리 확인: {lpql}')
            print(f'     ↳ 원인 진단: python LO_LOW_AMOS.py --test')
        elif not quiet:
            print(f'  [{tbl}] {qf:%H:%M}~{qt:%H:%M} → {n}분 수신')
    return True


def read_event(fp):
    with open(fp, encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        header = list(rd.fieldnames or [])
        rows = list(rd)
    return header, rows


def parse_dt(s):
    try:
        return datetime.strptime((s or '').strip()[:16], '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def resolve_event(path):
    """--event 가 폴더면 그 안의 최신 *발동이벤트*.csv 자동 선택 (매일 날짜 파일 대응).
    파일명의 날짜(YYYYMMDD)가 큰 것 우선 — mtime 은 우리가 기입할 때마다 바뀌므로 안 씀.
    파일이면 그대로. 없으면 None."""
    if os.path.isdir(path):
        cands = [f for f in os.listdir(path)
                 if f.lower().endswith('.csv') and '발동이벤트' in f]
        if not cands:
            return None
        dated = [(m.group(1), f) for f in cands
                 for m in [re.search(r'(\d{8})', f)] if m]
        if dated:
            return os.path.join(path, max(dated)[1])
        return max((os.path.join(path, f) for f in cands), key=os.path.getmtime)
    return path if os.path.exists(path) else None


def cycle(a, cache, fp=None, state={'seen': set()}):
    """1사이클: 파일 읽기 → 필요한 분 조회 → 채워서 원자 교체. return 기입행수 or None(스킵).
    fp 를 주면 그 파일만 처리 (자정 전환 시 전날 파일 마무리용)."""
    if fp is None:
        fp = resolve_event(a.event)
    if not fp:
        ab = os.path.abspath(a.event)
        if not os.path.exists(ab):
            print(f'  ⚠️ 경로 자체가 없음: {ab} (실행 위치 기준 상대경로 확인!) (대기)')
        else:
            print(f'  ⚠️ {ab} 안에 *발동이벤트*.csv 없음 (대기)')
        return None
    if fp not in state['seen']:
        print(f'  📄 대상 파일: {fp}'); state['seen'].add(fp)
    stat0 = os.stat(fp)
    header, rows = read_event(fp)
    if 'datetime' not in header:
        print("  ❌ 'datetime' 컬럼 없음"); return None

    times = [parse_dt(r.get('datetime')) for r in rows]
    valid = [t for t in times if t]
    if not valid:
        return None
    tmax = max(valid)

    # 채울 대상: 4컬럼이 물리적으로 없는 행(None) + 최근 RECHECK_MIN분(지연기입 보정)
    def unfilled(r):
        return any(r.get(c) is None for c in NEW_COLS)
    targets = [i for i, (r, t) in enumerate(zip(rows, times))
               if t and (unfilled(r) or (tmax - t) <= timedelta(minutes=RECHECK_MIN))]
    if not targets:
        return 0

    # 조회 필요한 키 = 대상 행의 (T-lag) 중 캐시에 없는 것 + 최근분(항상 갱신)
    keys = {times[i] - timedelta(minutes=a.lag) for i in targets}
    need = {k for k in keys
            if any(k.strftime('%Y-%m-%d %H:%M') not in cache[p] for p in TABLES)
            or (tmax - k) <= timedelta(minutes=RECHECK_MIN)}
    if need:
        if not fetch_range(min(need), max(need), a, cache):
            print('  ⚠️ 조회 실패 → 이번 사이클 기입 생략 (다음에 재시도)')
            return None

    # 기입
    out_header = header + [c for c in NEW_COLS if c not in header]
    for i in targets:
        k = (times[i] - timedelta(minutes=a.lag)).strftime('%Y-%m-%d %H:%M')
        for pfx in TABLES:
            v = cache[pfx].get(k)
            rows[i][f'{pfx}_downward_anomaly_cols'] = v[0] if v else ''
            rows[i][f'{pfx}_upward_anomaly_cols'] = v[1] if v else ''
    # 대상 아닌 행의 None(이론상 없음)도 '' 보정
    for r in rows:
        for c in NEW_COLS:
            if r.get(c) is None:
                r[c] = ''

    # 원자 저장 (교체 직전 생성기가 파일 바꿨으면 스킵 → 다음 사이클 재시도)
    out = a.out or fp
    tmp = out + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=out_header)
        w.writeheader(); w.writerows(rows)
    if out == fp:
        stat1 = os.stat(fp)
        if (stat1.st_mtime_ns, stat1.st_size) != (stat0.st_mtime_ns, stat0.st_size):
            os.remove(tmp)
            print('  ⚠️ 기입 중 파일 변경 감지 → 스킵 (다음 사이클 재시도)')
            return None
    try:
        os.replace(tmp, out)
    except PermissionError:
        os.remove(tmp)
        print('  ⚠️ 파일 잠김(생성기 사용 중) → 스킵 (다음 사이클 재시도)')
        return None
    return len(targets)


FINISH_CYCLES = 6  # 자정 전환 후 전날 파일을 몇 사이클 더 마무리 기입할지


def _loop(a):
    """운영 루프 본체 (main --loop 와 run_watch 공용)."""
    print(f'[LO_LOW_AMOS] {a.interval}초 간격 · 대상: {a.event}')
    cache = {p: {} for p in TABLES}  # 분키 → (down, up)
    cur = None
    finishing = {}  # 전날 파일 → 남은 마무리 사이클
    while True:
        try:
            fp = resolve_event(a.event)
            # 자정 전환 감지: 새 날짜 파일로 바뀌면 전날 파일을 몇 분 더 마무리
            # (로그프레소가 23:59 등 마지막 분을 자정 넘어 쓰기 때문)
            if fp and cur and fp != cur and os.path.exists(cur):
                finishing[cur] = FINISH_CYCLES
                print(f'  🔄 날짜 전환 — 전날 파일 마무리 시작: {os.path.basename(cur)}')
            if fp:
                cur = fp
            n = cycle(a, cache, fp=fp)
            for old in list(finishing):
                cycle(a, cache, fp=old)  # 전날 파일 끝부분(최근5분) 재조회·기입
                finishing[old] -= 1
                if finishing[old] <= 0:
                    del finishing[old]
                    print(f'  ✅ 전날 파일 마무리 완료: {os.path.basename(old)}')
            if n is not None:
                print(f"[LO_LOW_AMOS {datetime.now():%H:%M:%S}] 기입 {n}행 (캐시 {len(cache['BOTTLENECK'])}분)")
            time.sleep(a.interval)
        except KeyboardInterrupt:
            print('\n[LO_LOW_AMOS] 종료.'); break
        except Exception as e:
            print(f'  ⚠️ [LO_LOW_AMOS] 오류(계속): {e}'); time.sleep(a.interval)


def run_watch(event='./predict_tobe', interval=60, lag=0, mcp='BR',
              host=HOST, port=PORT, apikey=API_KEY):
    """run_ml 등에서 스레드로 돌리는 진입점:
        threading.Thread(target=LO_LOW_AMOS.run_watch, daemon=True).start()
    """
    a = argparse.Namespace(event=event, out=None, lag=lag, loop=True, mcp=mcp,
                           interval=interval, host=host, port=port, apikey=apikey)
    _loop(a)


def diagnose(a):
    """0건 원인 진단 — 쿼리를 단계별로 벗겨가며 어디서 0건이 되는지 찾는다."""
    now = datetime.now()
    d0 = (now - timedelta(days=1)).strftime('%Y%m%d')   # 어제(하루치 확정 데이터)
    d1 = now.strftime('%Y%m%d')

    def run(label, lpql):
        text = query_logpresso(lpql, a)
        if text is None:
            print(f'  ❌ {label}: 서버오류/연결실패')
            return None
        rows = list(csv.DictReader(StringIO(text))) if text.strip() else []
        print(f'  {"✅" if rows else "⚠️ "} {label}: {len(rows)}건')
        if rows:
            r = rows[0]
            print(f'      컬럼: {list(r.keys())}')
            print(f'      샘플: ' + ' | '.join(f'{k}={v!r}' for k, v in list(r.items())[:8]))
        return rows

    for tbl in TABLES.values():
        print(f'\n── {tbl} ' + '─' * (46 - len(tbl)))
        # ① 필터 없이 어제 하루 (테이블 자체에 데이터가 있는지)
        rows = run('① 필터없음 (어제 하루)',
                   f'table from={d0}000000 to={d0}235959 {tbl} | limit 5')
        # ② MCP_NM 필터만
        run(f'② MCP_NM=="{a.mcp}" (어제 하루)',
            f'table from={d0}000000 to={d0}235959 {tbl} | search MCP_NM == "{a.mcp}" | limit 5')
        # ③ 오늘 (실시간 기입 대상 구간)
        run(f'③ MCP_NM=="{a.mcp}" (오늘)',
            f'table from={d1}000000 to={d1}235959 {tbl} | search MCP_NM == "{a.mcp}" | limit 5')
        # ④ MCP_NM 실제 값 분포 (① 이 있는데 ② 가 0이면 여기서 답이 나옴)
        if rows:
            vals = run('④ MCP_NM 실제 값 목록 (어제)',
                       f'table from={d0}000000 to={d0}235959 {tbl} '
                       f'| stats count by MCP_NM, FAB_ID | limit 20')
            if vals:
                print('      → 위 목록에 원하는 값이 있으면 --mcp 로 지정하세요')

    print('\n[해석]')
    print('  ①0건  → 테이블에 데이터 자체가 없음 (보존기간/테이블명 확인)')
    print(f'  ①있음 ②0건 → MCP_NM 값이 "{a.mcp}" 가 아님 → ④ 목록 보고 --mcp 로 지정')
    print('  ②있음 ③0건 → 오늘 데이터가 아직 안 쌓임 (적재 지연)')
    print('  전부 있음   → 정상. 운영 로그의 0건은 그 시간대에 실제로 데이터가 없던 것')


def backfill_alldays(a):
    """폴더 내 모든 *발동이벤트*.csv 를 날짜순으로 일괄 기입 (과거 백필)."""
    if not os.path.isdir(a.event):
        print(f'❌ --alldays 는 폴더를 주세요: {a.event}'); sys.exit(2)
    files = sorted(f for f in os.listdir(a.event)
                   if f.lower().endswith('.csv') and '발동이벤트' in f)
    if not files:
        print(f'❌ {os.path.abspath(a.event)} 안에 *발동이벤트*.csv 없음'); sys.exit(2)
    print(f'[백필] 대상 {len(files)}개 파일')
    cache = {p: {} for p in TABLES}
    ok = fail = 0
    for f in files:
        n = cycle(a, cache, fp=os.path.join(a.event, f))
        if n is None:
            fail += 1; print(f'  ❌ {f} 실패 (조회오류 등)')
        else:
            ok += 1; print(f'  ✅ {f} — {n}행 기입')
    print(f'🎉 백필 완료 — 성공 {ok} / 실패 {fail}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', default=None, help='발동이벤트.csv 또는 폴더(최신 *발동이벤트*.csv 자동)')
    ap.add_argument('--out', default=None, help='(테스트용) 지정하면 원본 대신 여기에 저장')
    ap.add_argument('--lag', type=int, default=0, help='몇 분 전 로그프레소를 기입할지 (기본 0=같은 분)')
    ap.add_argument('--loop', action='store_true', help='운영: interval초마다 반복')
    ap.add_argument('--alldays', action='store_true', help='폴더 내 모든 날짜 파일 일괄 기입 (과거 백필)')
    ap.add_argument('--test', action='store_true', help='조회 0건 원인 진단 (--event 불필요)')
    ap.add_argument('--mcp', default='BR', help='MCP_NM 필터값 (기본 BR)')
    ap.add_argument('--interval', type=int, default=60)
    ap.add_argument('--host', default=HOST)
    ap.add_argument('--port', type=int, default=PORT)
    ap.add_argument('--apikey', default=API_KEY)
    a = ap.parse_args()

    print('=' * 60)
    print('발동이벤트 ← 로그프레소 이상감지 4컬럼 기입'
          + (' (진단)' if a.test else ' (운영 루프)' if a.loop
             else ' (과거 일괄백필)' if a.alldays else ' (1회)'))
    print('=' * 60)

    if a.test:
        diagnose(a); return
    if not a.event:
        print('❌ --event 가 필요합니다 (진단은 --test)'); sys.exit(2)

    if a.loop:
        _loop(a)
    elif a.alldays:
        backfill_alldays(a)
    else:
        cache = {p: {} for p in TABLES}
        n = cycle(a, cache)
        if n is None:
            sys.exit(2)
        print(f'🎉 완료 — {n}행 기입 → {a.out or resolve_event(a.event)}')


if __name__ == '__main__':
    main()
