#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LO_MAXCAPA — MAXCAPA 조작내역 → 발동이벤트.csv 에 4컬럼 직접 기입 (운영용)
====================================================================
LO_LOW_AMOS 와 동일한 구조. 별도 병합파일 안 만들고 발동이벤트.csv 자체에 기입한다.
매분 발동이벤트에 새 행이 붙으면 → 그 분의 MAXCAPA 조작을 찾아 채움.

입력: maxcapa_v3.py 산출 CSV
  조작시각,조작자사번,MACHINE,PORT,전(before),후(after),증감,방향,PROCESS,동일조작변경포트수,TRANSACTIONID

추가 4컬럼 (같은 분끼리: 발동이벤트 datetime T == 조작시각 T):
  MACHINE            같은 분에 조작된 설비 (여러개면 쉼표)
  PORT:후(after)     'PORT:후값' 을 줄바꿈으로 나열 — 예)
                       6ABL6031_AI612:1
                       6ABL6031_AI622:1
                       6ABL6031_AO623:1
  PROCESS            TS15 등 (여러개면 쉼표)
  TRANSACTIONID      MCS... (여러개면 쉼표)

실행 (표준 라이브러리만 사용):
  운영(1분 루프):  python LO_MAXCAPA.py --event .\predict_tobe --maxcapa .\maxcapa_v3.csv --loop
                   (--event 폴더를 주면 최신 *발동이벤트*.csv 자동 선택, 자정 전환 대응)
  1회만:           python LO_MAXCAPA.py --event .\predict_tobe\20260728_발동이벤트.csv --maxcapa .\maxcapa_v3.csv
  과거 일괄백필:   python LO_MAXCAPA.py --event .\predict_tobe --maxcapa .\maxcapa --alldays
                   (--maxcapa 에 폴더를 주면 그 안 CSV 전부 병합해서 사용)
  수집까지 자동:   위에 --collect 추가 → maxcapa_v3.py 를 그날 범위로 실행해 CSV 를 먼저 갱신
  테스트(원본보존): --out .\테스트.csv
  옵션: --interval 60 · --collect-every 300 · --force

동작 원리 (LO_LOW_AMOS 와 동일):
  · 시작 직후 1회 그날 파일 전체 재기입 → 공란으로 굳은 과거 행 자가복구
  · 이후 사이클은 신규행 + 최근 5분만 갱신 (조작 로그가 늦게 적재되는 경우 보정)
  · 파일에 4컬럼 없으면 헤더에 추가, 있으면 이어서 기입
  · 저장은 임시파일 → 원자 교체, 기입 중 파일 변경/잠김 감지 시 스킵 후 재시도
  · 자정 전환 시 전날 파일을 6사이클 더 마무리
  · 조작 0건인 분은 공란 (정상 — 대부분의 분에는 조작이 없다)

run_ml 통합 (스레드):
  import LO_MAXCAPA
  threading.Thread(target=LO_MAXCAPA.run_watch,
                   kwargs={'event': str(predictor.DEFAULT_OUTPUT_DIR),
                           'maxcapa': r'.\maxcapa_v3.csv'}, daemon=True).start()
"""
import argparse, csv, os, re, subprocess, sys, time
from datetime import datetime, timedelta

NEW_COLS = ['MACHINE', 'PORT:후(after)', 'PROCESS', 'TRANSACTIONID']
RECHECK_MIN = 5      # 최근 N분은 매 사이클 재확인 (조작 로그 지연 적재 보정)
FINISH_CYCLES = 6    # 자정 전환 후 전날 파일 마무리 사이클 수


# ────────────────────────────────────────────────────────────
# 시각 정규화 — '2026-07-28 8:46' / '2026-07-28 08:46:00' 모두 같은 키로
# ────────────────────────────────────────────────────────────
def parse_dt(s):
    s = (s or '').strip()
    if not s:
        return None
    try:
        d, t = s.split(' ', 1)
        y, mo, dd = [int(x) for x in d.replace('/', '-').split('-')]
        hm = t.split(':')
        return datetime(y, mo, dd, int(hm[0]), int(hm[1]))
    except (ValueError, IndexError):
        return None


def key_of(dt):
    return dt.strftime('%Y-%m-%d %H:%M') if dt else ''


# ────────────────────────────────────────────────────────────
# MAXCAPA 원본 로드
# ────────────────────────────────────────────────────────────
def _csv_files(path):
    if os.path.isdir(path):
        return sorted(os.path.join(path, f) for f in os.listdir(path)
                      if f.lower().endswith('.csv'))
    return [path] if os.path.exists(path) else []


def load_maxcapa(path):
    """분키 → {'machine':[], 'ports':[(port,after)], 'proc':[], 'tx':[]} (원본 순서 유지)"""
    files = _csv_files(path)
    if not files:
        print(f'  ⚠️ MAXCAPA 원본 없음: {os.path.abspath(path)}')
        return {}
    m, nrow = {}, 0
    for fp in files:
        try:
            with open(fp, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    dt = parse_dt(r.get('조작시각'))
                    if not dt:
                        continue
                    k = key_of(dt)
                    e = m.setdefault(k, {'machine': [], 'ports': [], 'proc': [], 'tx': []})
                    mc = (r.get('MACHINE') or '').strip()
                    port = (r.get('PORT') or '').strip()
                    after = (r.get('후(after)') or '').strip()
                    proc = (r.get('PROCESS') or '').strip()
                    tx = (r.get('TRANSACTIONID') or '').strip()
                    if mc and mc not in e['machine']:
                        e['machine'].append(mc)
                    if port:
                        pair = f'{port}:{after}'
                        if pair not in e['ports']:
                            e['ports'].append(pair)
                    if proc and proc not in e['proc']:
                        e['proc'].append(proc)
                    if tx and tx not in e['tx']:
                        e['tx'].append(tx)
                    nrow += 1
        except Exception as e:
            print(f'  ⚠️ MAXCAPA 읽기 실패 {fp}: {e}')
    print(f'  [MAXCAPA] {len(files)}개 파일 · {nrow}행 → 조작 있는 분 {len(m)}개')
    return m


def collect(a, day):
    """maxcapa_v3.py 를 그날 범위로 실행해 CSV 갱신 (--collect)."""
    script = a.collector
    if not os.path.exists(script):
        print(f'  ⚠️ 수집기 없음: {script} (--collect 무시)')
        return
    d0 = day.strftime('%Y-%m-%d 00:00:00')
    d1 = (day + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
    out = a.maxcapa if not os.path.isdir(a.maxcapa) else os.path.join(a.maxcapa, 'maxcapa_auto.csv')
    try:
        p = subprocess.run([sys.executable, script, '--from', d0, '--to', d1, '--csv', out],
                           capture_output=True, text=True, timeout=a.collect_timeout)
        if p.returncode != 0:
            print(f'  ⚠️ 수집 실패(rc={p.returncode}): {(p.stderr or p.stdout)[-200:]}')
        else:
            print(f'  🔄 MAXCAPA 수집 완료 → {out}')
    except subprocess.TimeoutExpired:
        print(f'  ⚠️ 수집 타임아웃({a.collect_timeout}초)')
    except Exception as e:
        print(f'  ⚠️ 수집 예외: {e}')


# ────────────────────────────────────────────────────────────
# 발동이벤트 파일
# ────────────────────────────────────────────────────────────
def resolve_event(path):
    """폴더면 파일명 날짜(YYYYMMDD)가 가장 큰 *발동이벤트*.csv 자동 선택."""
    if os.path.isdir(path):
        cands = [f for f in os.listdir(path)
                 if f.lower().endswith('.csv') and '발동이벤트' in f]
        if not cands:
            return None
        dated = [(m.group(1), f) for f in cands for m in [re.search(r'(\d{8})', f)] if m]
        if dated:
            return os.path.join(path, max(dated)[1])
        return max((os.path.join(path, f) for f in cands), key=os.path.getmtime)
    return path if os.path.exists(path) else None


def read_event(fp):
    with open(fp, encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        return list(rd.fieldnames or []), list(rd)


def cycle(a, mc_map, fp=None, state={'seen': set()}):
    """1사이클: 파일 읽기 → 해당 분 조작 채우기 → 원자 교체. return 기입행수 or None(스킵)."""
    if fp is None:
        fp = resolve_event(a.event)
    if not fp:
        ab = os.path.abspath(a.event)
        print(f'  ⚠️ {"경로 없음" if not os.path.exists(ab) else "발동이벤트 CSV 없음"}: {ab} (대기)')
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

    force = getattr(a, 'force', False)

    def unfilled(r):
        return any(r.get(c) is None for c in NEW_COLS)
    targets = [i for i, (r, t) in enumerate(zip(rows, times))
               if t and (force or unfilled(r) or (tmax - t) <= timedelta(minutes=RECHECK_MIN))]
    if not targets:
        return 0

    out_header = header + [c for c in NEW_COLS if c not in header]
    n_hit = 0
    for i in targets:
        e = mc_map.get(key_of(times[i]))
        rows[i]['MACHINE'] = ','.join(e['machine']) if e else ''
        rows[i]['PORT:후(after)'] = '\n'.join(e['ports']) if e else ''
        rows[i]['PROCESS'] = ','.join(e['proc']) if e else ''
        rows[i]['TRANSACTIONID'] = ','.join(e['tx']) if e else ''
        n_hit += bool(e)
    for r in rows:
        for c in NEW_COLS:
            if r.get(c) is None:
                r[c] = ''

    out = a.out or fp
    tmp = out + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=out_header)
        w.writeheader(); w.writerows(rows)
    if out == fp:
        s1 = os.stat(fp)
        if (s1.st_mtime_ns, s1.st_size) != (stat0.st_mtime_ns, stat0.st_size):
            os.remove(tmp)
            print('  ⚠️ 기입 중 파일 변경 감지 → 스킵 (다음 사이클 재시도)')
            return None
    try:
        os.replace(tmp, out)
    except PermissionError:
        os.remove(tmp)
        print('  ⚠️ 파일 잠김(생성기 사용 중) → 스킵 (다음 사이클 재시도)')
        return None
    if n_hit:
        print(f'  ✏️ 조작 있는 분 {n_hit}개 기입')
    return len(targets)


# ────────────────────────────────────────────────────────────
# 운영 루프
# ────────────────────────────────────────────────────────────
def _loop(a):
    print(f'[LO_MAXCAPA] {a.interval}초 간격 · 대상 {a.event} · 원본 {a.maxcapa}')
    healed, finishing, cur = set(), {}, None
    user_force = getattr(a, 'force', False)
    last_collect = 0.0
    while True:
        try:
            fp = resolve_event(a.event)
            if a.collect and (time.time() - last_collect) >= a.collect_every:
                collect(a, datetime.now()); last_collect = time.time()
            mc_map = load_maxcapa(a.maxcapa)

            heal = bool(fp) and fp not in healed
            a.force = user_force or heal
            if heal:
                print(f'  🩹 시작 복구: {os.path.basename(fp)} 전체 재기입')
            if fp and cur and fp != cur and os.path.exists(cur):
                finishing[cur] = FINISH_CYCLES
                print(f'  🔄 날짜 전환 — 전날 파일 마무리: {os.path.basename(cur)}')
            if fp:
                cur = fp

            n = cycle(a, mc_map, fp=fp)
            if heal and n is not None:
                healed.add(fp)
            a.force = user_force
            for old in list(finishing):
                cycle(a, mc_map, fp=old)
                finishing[old] -= 1
                if finishing[old] <= 0:
                    del finishing[old]
                    print(f'  ✅ 전날 파일 마무리 완료: {os.path.basename(old)}')
            if n is not None:
                print(f'[LO_MAXCAPA {datetime.now():%H:%M:%S}] 기입 {n}행')
            time.sleep(a.interval)
        except KeyboardInterrupt:
            print('\n[LO_MAXCAPA] 종료.'); break
        except Exception as e:
            print(f'  ⚠️ [LO_MAXCAPA] 오류(계속): {e}'); time.sleep(a.interval)


def run_watch(event='./predict_tobe', maxcapa='./maxcapa_v3.csv', interval=60,
              collect_flag=False, collector='maxcapa_v3.py', collect_every=300):
    """run_ml 등에서 스레드로 돌리는 진입점."""
    a = argparse.Namespace(event=event, maxcapa=maxcapa, out=None, interval=interval,
                           force=False, collect=collect_flag, collector=collector,
                           collect_every=collect_every, collect_timeout=600)
    _loop(a)


def backfill_alldays(a):
    """폴더 내 모든 날짜 파일 일괄 기입 (항상 전체 덮어쓰기)."""
    if not os.path.isdir(a.event):
        print(f'❌ --alldays 는 폴더를 주세요: {a.event}'); sys.exit(2)
    files = sorted(f for f in os.listdir(a.event)
                   if f.lower().endswith('.csv') and '발동이벤트' in f)
    if not files:
        print(f'❌ {os.path.abspath(a.event)} 안에 *발동이벤트*.csv 없음'); sys.exit(2)
    a.force = True
    mc_map = load_maxcapa(a.maxcapa)
    print(f'[백필] 대상 {len(files)}개 파일 — 전체 덮어쓰기')
    ok = fail = 0
    for f in files:
        n = cycle(a, mc_map, fp=os.path.join(a.event, f))
        if n is None:
            fail += 1; print(f'  ❌ {f} 실패')
        else:
            ok += 1; print(f'  ✅ {f} — {n}행 기입')
    print(f'🎉 백필 완료 — 성공 {ok} / 실패 {fail}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', required=True, help='발동이벤트.csv 또는 폴더(최신 날짜파일 자동)')
    ap.add_argument('--maxcapa', default='./maxcapa_v3.csv', help='maxcapa_v3.py 산출 CSV (파일 또는 폴더)')
    ap.add_argument('--out', default=None, help='(테스트용) 원본 대신 여기에 저장')
    ap.add_argument('--loop', action='store_true', help='운영: interval초마다 반복')
    ap.add_argument('--alldays', action='store_true', help='폴더 내 모든 날짜 파일 일괄 기입(덮어쓰기)')
    ap.add_argument('--force', action='store_true', help='단일 파일도 전체 덮어쓰기')
    ap.add_argument('--interval', type=int, default=60)
    ap.add_argument('--collect', action='store_true', help='maxcapa_v3.py 를 직접 실행해 CSV 갱신')
    ap.add_argument('--collector', default='maxcapa_v3.py')
    ap.add_argument('--collect-every', dest='collect_every', type=int, default=300,
                    help='--collect 재수집 간격(초, 기본 300)')
    ap.add_argument('--collect-timeout', dest='collect_timeout', type=int, default=600)
    a = ap.parse_args()

    print('=' * 60)
    print('발동이벤트 ← MAXCAPA 조작내역 4컬럼 기입'
          + (' (운영 루프)' if a.loop else ' (과거 일괄백필)' if a.alldays else ' (1회)'))
    print('=' * 60)

    if a.loop:
        _loop(a)
    elif a.alldays:
        backfill_alldays(a)
    else:
        if a.collect:
            collect(a, datetime.now())
        n = cycle(a, load_maxcapa(a.maxcapa))
        if n is None:
            sys.exit(2)
        print(f'🎉 완료 — {n}행 기입 → {a.out or resolve_event(a.event)}')


if __name__ == '__main__':
    main()
