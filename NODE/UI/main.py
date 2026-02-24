"""
================================================================================
M14 반송 큐 모니터링 서버
- Flask 웹 서버
- m14_data.py: 로그프레소에서 280분 데이터 조회
- predictor_10min.py: 10분 예측
- predictor_30min.py: 30분 예측
- evaluator.py: 예측 평가 (내부/외부 데이터 소스 지원)
- logpresso_alarm.py: 로그프레소 알람 조회
================================================================================
"""

from flask import Flask, jsonify, send_file, request
import pandas as pd
from datetime import datetime

# 모듈 import
import m14_data
import predictor_10min
import predictor_30min
import evaluator
import logpresso_alarm

app = Flask(__name__)

# CORS 허용 (3D 캠퍼스 등 다른 포트에서 /api 접근 허용)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# 데이터 매니저 (280분 윈도우, data 폴더에 저장)
data_manager = m14_data.M14DataManager(window_minutes=280, data_dir='data')

# 예측 모듈 연결
data_manager.set_predictors(predictor_10min, predictor_30min)


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/mini')
def mini():
    return send_file('mini.html')


@app.route('/api/data')
def get_data():
    """
    실시간 데이터 + 예측값 API
    - 데이터 매니저에서 저장된 데이터/예측값 반환
    """
    
    # 데이터가 없으면 초기화
    if data_manager.data is None or len(data_manager.data) == 0:
        if not data_manager.initialize():
            return jsonify({'error': 'Data load failed'}), 500
    
    df = data_manager.get_data()
    predict_10_all, predict_30_all = data_manager.get_predictions()
    
    if df is None or len(df) == 0:
        return jsonify({'error': 'No data'}), 500
    
    # 차트용 데이터 (최근 60분만)
    chart_len = min(60, len(df))
    df_chart = df.tail(chart_len).reset_index(drop=True)
    predict_10_list = predict_10_all[-chart_len:]
    predict_30_list = predict_30_all[-chart_len:]
    
    # 시간 포맷 변환
    times = []
    times_full = []
    for t in df_chart['CURRTIME'].values:
        t_str = str(t)
        if len(t_str) >= 12:
            times.append(f"{t_str[8:10]}:{t_str[10:12]}")
            times_full.append(f"{t_str[0:4]}-{t_str[4:6]}-{t_str[6:8]} {t_str[8:10]}:{t_str[10:12]}")
        else:
            times.append(t_str)
            times_full.append(t_str)
    
    # 현재 시간 포맷
    last_t = str(df['CURRTIME'].iloc[-1])
    if len(last_t) >= 12:
        full_time = f"{last_t[0:4]}-{last_t[4:6]}-{last_t[6:8]} {last_t[8:10]}:{last_t[10:12]}"
    else:
        full_time = last_t
    
    current_val = int(df['TOTALCNT'].iloc[-1]) if pd.notna(df['TOTALCNT'].iloc[-1]) else 0
    
    # 알람 기록 + 상태
    alert_10, alert_30 = data_manager.get_alerts()
    alarm_state = data_manager.get_alarm_state()
    
    # 급증 컬럼 계산 (최근 10분 대비)
    spike_columns = []
    SPIKE_THRESHOLD = 50  # 50 이상 증가 시 급증으로 판단
    ANALYSIS_COLS = ['M14AM10A', 'M10AM14A', 'M14AM10ASUM', 
                     'M14AM14B', 'M14BM14A', 'M14AM14BSUM',
                     'M14AM16', 'M16M14A', 'M14AM16SUM',
                     'M14.QUE.ALL.CURRENTQCREATED',
                     'M14.QUE.ALL.CURRENTQCOMPLETED',
                     'M14.QUE.OHT.OHTUTIL',
                     'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
                     'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT']
    
    if len(df) >= 11:  # 최소 11개 데이터 필요 (현재 + 10분전)
        current_row = df.iloc[-1]
        prev_row = df.iloc[-11]  # 10분 전
        
        # 컬럼별 임계값 설정 (warning, danger)
        THRESHOLD_60_COLS = ['M14.QUE.ALL.CURRENTQCREATED', 'M14.QUE.ALL.CURRENTQCOMPLETED']
        
        for col in ANALYSIS_COLS:
            if col in df.columns:
                curr_val = current_row.get(col, 0)
                prev_val = prev_row.get(col, 0)
                
                if pd.notna(curr_val) and pd.notna(prev_val):
                    change = float(curr_val) - float(prev_val)
                    
                    # 컬럼별 임계값
                    if col in THRESHOLD_60_COLS:
                        warn_threshold, danger_threshold = 60, 70
                    else:
                        warn_threshold, danger_threshold = 50, 60
                    
                    if change >= warn_threshold:
                        level = 'danger' if change >= danger_threshold else 'warning'
                        spike_columns.append({
                            'column': col,
                            'change': int(change),
                            'current': int(curr_val),
                            'previous': int(prev_val),
                            'level': level
                        })
        
        # 변화량 기준 정렬
        spike_columns.sort(key=lambda x: x['change'], reverse=True)
    
    # 상태 예상 계산 (급증 컬럼 기준) + 쿨타임 로직
    warning_count = len([s for s in spike_columns if s.get('level') == 'warning'])
    danger_count = len([s for s in spike_columns if s.get('level') == 'danger'])
    predict_10_val = predict_10_list[-1] if predict_10_list else 0
    predict_30_val = predict_30_list[-1] if predict_30_list else 0
    
    # 현재 상태 판단 (TOTALCNT + 급증 컬럼 기준)
    if current_val >= 1650 and danger_count >= 3:
        current_status = '병목예상'
    elif current_val >= 1550 and danger_count >= 2:
        current_status = '위험예상'
    elif current_val < 1550 and danger_count >= 2:
        current_status = '관찰'
    else:
        current_status = '양호예상'
    
    # 양호예상일 때 예측값 추가 체크 (쿨타임 없음)
    predict_based_status = None
    if current_status == '양호예상':
        if predict_10_val >= 1700 and predict_30_val >= 1700:
            predict_based_status = '병목(1700예측-10분,30분)'
        elif predict_10_val >= 1700:
            predict_based_status = '병목(1700예측-10분)'
        elif predict_30_val >= 1700:
            predict_based_status = '병목(1700예측-30분)'
        elif predict_10_val >= 1650 or predict_30_val >= 1650:
            predict_based_status = '병목예상'
    
    # 쿨타임 상태 관리 (파일 기반)
    import os
    from datetime import datetime, timedelta
    
    status_cooldown_file = os.path.join(data_manager.data_dir, 'm14_status_cooldown.csv')
    last_danger_time = None
    last_bottleneck_time = None
    
    # 기존 쿨타임 상태 로드
    if os.path.exists(status_cooldown_file):
        try:
            df_cooldown = pd.read_csv(status_cooldown_file)
            if len(df_cooldown) > 0:
                row = df_cooldown.iloc[0]
                if pd.notna(row.get('last_danger_time')) and row.get('last_danger_time'):
                    last_danger_time = datetime.strptime(str(row['last_danger_time']), '%Y%m%d%H%M')
                if pd.notna(row.get('last_bottleneck_time')) and row.get('last_bottleneck_time'):
                    last_bottleneck_time = datetime.strptime(str(row['last_bottleneck_time']), '%Y%m%d%H%M')
        except:
            pass
    
    # 현재 시간
    now = datetime.now()
    
    # 쿨타임 갱신 (급증 컬럼 기준 상태만, 예측 기반은 쿨타임 없음)
    if current_status == '병목예상':
        last_bottleneck_time = now
    elif current_status == '위험예상':
        last_danger_time = now
    
    # 쿨타임 상태 저장
    cooldown_data = {
        'last_danger_time': [last_danger_time.strftime('%Y%m%d%H%M') if last_danger_time else ''],
        'last_bottleneck_time': [last_bottleneck_time.strftime('%Y%m%d%H%M') if last_bottleneck_time else '']
    }
    pd.DataFrame(cooldown_data).to_csv(status_cooldown_file, index=False)
    
    # 최종 상태 결정
    status_prediction = current_status
    
    # 예측 기반 상태가 있으면 우선 (쿨타임 없음)
    if predict_based_status:
        status_prediction = predict_based_status
    elif current_status in ['양호예상', '관찰']:
        # 쿨타임 확인
        # 병목 쿨타임 확인 (30분)
        if last_bottleneck_time:
            elapsed = (now - last_bottleneck_time).total_seconds() / 60
            if elapsed < 30:
                cooldown_mins = int(30 - elapsed)
                status_prediction = f'병목 쿨타임 {cooldown_mins}분'
        # 위험 쿨타임 확인 (30분) - 병목 쿨타임이 없을 때만
        if '쿨타임' not in status_prediction and last_danger_time:
            elapsed = (now - last_danger_time).total_seconds() / 60
            if elapsed < 30:
                cooldown_mins = int(30 - elapsed)
                status_prediction = f'위험 쿨타임 {cooldown_mins}분'
    
    return jsonify({
        'x': times,
        'x_full': times_full,
        'y': df_chart['TOTALCNT'].fillna(0).astype(int).tolist(),
        'predict_10_list': predict_10_list,
        'predict_30_list': predict_30_list,
        'current': current_val,
        'predict_10': predict_10_list[-1] if predict_10_list else 0,
        'predict_30': predict_30_list[-1] if predict_30_list else 0,
        'currtime': full_time,
        'idx': len(df),
        'total': len(df),
        'alert_10': alert_10,
        'alert_30': alert_30,
        'alarm_state': alarm_state,
        'spike_columns': spike_columns,
        'status_prediction': status_prediction,
        'warning_count': warning_count,
        'danger_count': danger_count
    })


@app.route('/api/next')
def next_step():
    """다음 스텝 - 새 데이터 추가 후 조회"""
    data_manager.update()
    return get_data()


@app.route('/api/reset')
def reset():
    """리셋 - 전체 데이터 새로고침"""
    data_manager.refresh()
    return jsonify({'status': 'ok'})


@app.route('/api/status')
def status():
    """서버 상태"""
    return jsonify({
        'status': 'running',
        'data_count': len(data_manager.data) if data_manager.data is not None else 0,
        'last_update': str(data_manager.last_update) if data_manager.last_update else None,
        'sequence_length': 280,
    })


@app.route('/history')
def history():
    """과거 데이터 조회 페이지"""
    return send_file('history.html')


@app.route('/api/history')
def get_history():
    """
    과거 데이터 조회 API
    
    Parameters:
        date: YYYYMMDD 형식의 날짜
    
    Returns:
        data: 해당 날짜의 데이터 + 예측값
        alerts_10: 10분 예측 알람 기록
        alerts_30: 30분 예측 알람 기록
    """
    import os
    
    date_str = request.args.get('date', '')
    
    if not date_str or len(date_str) != 8:
        return jsonify({'error': '날짜 형식이 잘못되었습니다 (YYYYMMDD)'}), 400
    
    data_dir = data_manager.data_dir
    data_file = os.path.join(data_dir, f'm14_data_{date_str}.csv')
    pred_file = os.path.join(data_dir, f'm14_pred_{date_str}.csv')
    alert_file = os.path.join(data_dir, f'm14_alert_{date_str}.csv')
    
    # 데이터 파일 확인
    if not os.path.exists(data_file):
        return jsonify({'error': f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 데이터가 없습니다'})
    
    try:
        # 항상 data 파일 로드 (분석 컬럼 포함)
        df_data = pd.read_csv(data_file)
        
        # 예측 파일이 있으면 merge
        if os.path.exists(pred_file):
            df_pred = pd.read_csv(pred_file)
            
            if 'CURRTIME' in df_pred.columns:
                # 예측 컬럼만 merge
                pred_cols = ['CURRTIME', 'PREDICT_10', 'PREDICT_30', 'PRED_TIME_10', 'PRED_TIME_30']
                pred_cols_exist = [c for c in pred_cols if c in df_pred.columns]
                df_merged = pd.merge(df_data, df_pred[pred_cols_exist], on='CURRTIME', how='left')
            else:
                # CURRTIME 없으면 직접 복사
                for col in ['PREDICT_10', 'PREDICT_30', 'PRED_TIME_10', 'PRED_TIME_30']:
                    if col in df_pred.columns:
                        df_data[col] = df_pred[col].values[:len(df_data)]
                df_merged = df_data
        else:
            df_merged = df_data
        
        # NaN 처리
        df_merged = df_merged.fillna(0)
        
        # 알람 기록 로드
        alerts_10 = []
        alerts_30 = []
        
        if os.path.exists(alert_file):
            df_alert = pd.read_csv(alert_file)
            # TYPE을 문자열로 변환 (CSV에서 정수로 읽힐 수 있음)
            df_alert['TYPE'] = df_alert['TYPE'].astype(str)
            for _, row in df_alert.iterrows():
                alert_item = {
                    'CURRTIME': row.get('CURRTIME', ''),
                    'VALUE': int(row.get('VALUE', 0)),
                    'ALARM_NO': int(row.get('ALARM_NO', 0)),
                    'IS_ALARM': bool(row.get('IS_ALARM', False)),
                    'COOLDOWN_MINS': int(row.get('COOLDOWN_MINS', 0)) if pd.notna(row.get('COOLDOWN_MINS')) else 0
                }
                # TYPE이 '10' 또는 '30'으로 저장됨
                if row.get('TYPE') == '10':
                    alerts_10.append(alert_item)
                elif row.get('TYPE') == '30':
                    alerts_30.append(alert_item)
        
        # 10분 대비 급증 컬럼 계산 (+50 이상)
        SPIKE_THRESHOLD = 50
        ANALYSIS_COLS = ['M14AM10A', 'M10AM14A', 'M14AM10ASUM', 
                         'M14AM14B', 'M14BM14A', 'M14AM14BSUM',
                         'M14AM16', 'M16M14A', 'M14AM16SUM',
                         'M14.QUE.ALL.CURRENTQCREATED',
                         'M14.QUE.ALL.CURRENTQCOMPLETED',
                         'M14.QUE.OHT.OHTUTIL',
                         'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
                         'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT']
        
        spike_info_list = []
        status_prediction_list = []
        # 컬럼별 임계값 설정 (warning, danger)
        THRESHOLD_60_COLS = ['M14.QUE.ALL.CURRENTQCREATED', 'M14.QUE.ALL.CURRENTQCOMPLETED']
        
        # 쿨타임 추적용 변수
        last_danger_time = None
        last_bottleneck_time = None
        
        # CURRTIME을 datetime으로 변환하는 함수
        def parse_currtime(ct):
            try:
                s = str(int(ct))
                if len(s) >= 12:
                    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]))
            except:
                pass
            return None
        
        for idx in range(len(df_merged)):
            spike_cols = []
            warning_count = 0
            danger_count = 0
            
            if idx >= 10:  # 10분 전 데이터가 있어야 비교 가능
                current_row = df_merged.iloc[idx]
                prev_row = df_merged.iloc[idx - 10]
                
                for col in ANALYSIS_COLS:
                    if col in df_merged.columns:
                        curr_val = current_row.get(col, 0)
                        prev_val = prev_row.get(col, 0)
                        
                        if pd.notna(curr_val) and pd.notna(prev_val):
                            change = float(curr_val) - float(prev_val)
                            
                            # 컬럼별 임계값
                            if col in THRESHOLD_60_COLS:
                                warn_threshold, danger_threshold = 60, 70
                            else:
                                warn_threshold, danger_threshold = 50, 60
                            
                            if change >= warn_threshold:
                                if change >= danger_threshold:
                                    level = 'D'
                                    danger_count += 1
                                else:
                                    level = 'W'
                                    warning_count += 1
                                spike_cols.append(f"{level}:{col} +{int(change)}")
            
            spike_info_list.append(', '.join(spike_cols) if spike_cols else '')
            
            # 상태 예상 계산 (30분 예측값 기준) + 쿨타임
            predict_30 = df_merged.iloc[idx].get('PREDICT_30', 0)
            if pd.isna(predict_30):
                predict_30 = 0
            predict_30 = float(predict_30)
            
            # 현재 상태 판단
            if predict_30 >= 1650 and danger_count >= 3:
                current_status = '병목예상'
            elif predict_30 >= 1550 and danger_count >= 2:
                current_status = '위험예상'
            elif predict_30 < 1550 and danger_count >= 2:
                current_status = '관찰'
            else:
                current_status = '양호예상'
            
            # 현재 시간 파싱
            curr_time = parse_currtime(df_merged.iloc[idx].get('CURRTIME', 0))
            
            # 새로운 위험/병목 발생 시 쿨타임 갱신
            if current_status == '병목예상' and curr_time:
                last_bottleneck_time = curr_time
            elif current_status == '위험예상' and curr_time:
                last_danger_time = curr_time
            
            # 최종 상태 결정 (쿨타임 포함)
            status_pred = current_status
            
            if current_status in ['양호예상', '관찰'] and curr_time:
                # 병목 쿨타임 확인 (30분)
                if last_bottleneck_time:
                    elapsed = (curr_time - last_bottleneck_time).total_seconds() / 60
                    if elapsed < 30 and elapsed > 0:
                        cooldown_mins = int(30 - elapsed)
                        status_pred = f'병목 쿨타임 {cooldown_mins}분'
                # 위험 쿨타임 확인 (30분) - 병목 쿨타임이 없을 때만
                if '쿨타임' not in status_pred and last_danger_time:
                    elapsed = (curr_time - last_danger_time).total_seconds() / 60
                    if elapsed < 30 and elapsed > 0:
                        cooldown_mins = int(30 - elapsed)
                        status_pred = f'위험 쿨타임 {cooldown_mins}분'
            
            status_prediction_list.append(status_pred)
        
        df_merged['SPIKE_INFO'] = spike_info_list
        df_merged['STATUS_PREDICTION'] = status_prediction_list
        
        # 결과 반환
        return jsonify({
            'date': date_str,
            'data': df_merged.to_dict('records'),
            'alerts_10': alerts_10,
            'alerts_30': alerts_30
        })
        
    except Exception as e:
        return jsonify({'error': f'데이터 로드 실패: {str(e)}'}), 500


# ============================================================================
# 로그프레소 알람 API
# ============================================================================

@app.route('/api/logpresso_alarm')
def get_logpresso_alarm():
    """
    로그프레소 알람 조회 API
    
    Parameters:
        from: 시작 시간 (YYYYMMDDHHMM00)
        to: 종료 시간 (YYYYMMDDHHMM00)
    
    Returns:
        data: 알람 리스트 [{MEAS_TM, LSTM_FCAST_TM, ALARM_DESC, ALARM_YN}, ...]
    """
    from_time = request.args.get('from', '')
    to_time = request.args.get('to', '')
    
    if not from_time or not to_time:
        return jsonify({'error': 'from, to 파라미터 필요'}), 400
    
    try:
        alarms = logpresso_alarm.get_alarm_data(from_time, to_time)
        return jsonify({
            'from': from_time,
            'to': to_time,
            'count': len(alarms),
            'data': alarms
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 평가 관련 라우트 (백그라운드 실행)
# ============================================================================

@app.route('/evaluate')
def evaluate_page():
    """예측 평가 페이지"""
    return send_file('evaluate.html')


@app.route('/api/evaluate/start', methods=['POST', 'GET'])
def start_evaluate():
    """
    백그라운드 평가 시작 API
    
    Parameters:
        date_start: 시작 날짜 (YYYYMMDD)
        date_end: 종료 날짜 (YYYYMMDD)
        time_start: 시작 시간 (HHMM)
        time_end: 종료 시간 (HHMM)
        pred_type: '10' 또는 '30'
        data_source: 'internal' (파일) 또는 'external' (로그프레소)
    """
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    time_start = request.args.get('time_start', '0000')
    time_end = request.args.get('time_end', '2359')
    pred_type = request.args.get('pred_type', '10')
    data_source = request.args.get('data_source', 'internal')  # 기본값: 내부(파일)
    
    if not date_start or not date_end:
        return jsonify({'error': '시작/종료 날짜를 지정해주세요'}), 400
    
    if len(date_start) != 8 or len(date_end) != 8:
        return jsonify({'error': '날짜 형식이 잘못되었습니다 (YYYYMMDD)'}), 400
    
    if pred_type not in ['10', '30']:
        return jsonify({'error': 'pred_type은 10 또는 30이어야 합니다'}), 400
    
    if data_source not in ['internal', 'external']:
        return jsonify({'error': 'data_source는 internal 또는 external이어야 합니다'}), 400
    
    success, msg = evaluator.eval_manager.start(
        data_dir=data_manager.data_dir,
        date_start=date_start,
        date_end=date_end,
        time_start=time_start,
        time_end=time_end,
        pred_type=pred_type,
        data_source=data_source
    )
    
    if success:
        return jsonify({'status': 'started', 'message': msg, 'data_source': data_source})
    else:
        return jsonify({'error': msg}), 400


@app.route('/api/evaluate/status')
def get_evaluate_status():
    """평가 진행 상태 조회"""
    return jsonify(evaluator.eval_manager.get_status())


@app.route('/api/evaluate/result')
def get_evaluate_result():
    """평가 결과 조회"""
    result = evaluator.eval_manager.get_result()
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': '결과가 없습니다 (평가 진행 중이거나 시작되지 않음)'}), 400


@app.route('/api/evaluate/reset')
def reset_evaluate():
    """평가 상태 초기화"""
    evaluator.eval_manager.reset()
    return jsonify({'status': 'reset'})


@app.route('/api/evaluate/dates')
def get_available_dates():
    """사용 가능한 날짜 목록 반환 (내부 파일용)"""
    dates = evaluator.get_available_dates(data_manager.data_dir)
    return jsonify({'dates': dates})


@app.route('/api/detail')
def get_detail():
    """
    상세 분석 API - 특정 시점의 컬럼별 변화량 분석
    
    Parameters:
        date: YYYYMMDD 형식의 날짜
        time: HHMM 형식의 시간
        range: 분석 범위 (분 단위, 기본값 10)
    
    Returns:
        current: 현재 시점 데이터
        previous: 이전 시점 데이터 (range분 전)
        changes: 컬럼별 변화량/변화율
    
    분석 대상 컬럼:
        - M14AM10A, M10AM14A, M14AM10ASUM
        - M14AM14B, M14BM14A, M14AM14BSUM
        - M14AM16, M16M14A, M14AM16SUM
        - M14.QUE.ALL.CURRENTQCREATED (미수집 가능)
        - M14.QUE.ALL.CURRENTQCOMPLETED (미수집 가능)
        - M14.QUE.OHT.OHTUTIL (미수집 가능)
        - M14.QUE.ALL.TRANSPORT4MINOVERCNT (미수집 가능)
        - M14B.QUE.SENDFAB.VERTICALQUEUECOUNT (미수집 가능)
    """
    import os
    
    date_str = request.args.get('date', '')
    time_str = request.args.get('time', '')
    range_min = int(request.args.get('range', '10'))
    
    if not date_str or len(date_str) != 8:
        return jsonify({'error': '날짜 형식이 잘못되었습니다 (YYYYMMDD)'}), 400
    
    if not time_str or len(time_str) != 4:
        return jsonify({'error': '시간 형식이 잘못되었습니다 (HHMM)'}), 400
    
    # 분석 대상 컬럼
    ANALYSIS_COLUMNS = [
        'M14AM10A', 'M10AM14A', 'M14AM10ASUM',
        'M14AM14B', 'M14BM14A', 'M14AM14BSUM',
        'M14AM16', 'M16M14A', 'M14AM16SUM',
        'M14.QUE.ALL.CURRENTQCREATED',
        'M14.QUE.ALL.CURRENTQCOMPLETED',
        'M14.QUE.OHT.OHTUTIL',
        'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
        'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT'
    ]
    
    # 미수집 가능 컬럼 (star_transport_view에서 오는 컬럼)
    UNCOLLECTED_COLUMNS = [
        'M14.QUE.ALL.CURRENTQCREATED',
        'M14.QUE.ALL.CURRENTQCOMPLETED',
        'M14.QUE.OHT.OHTUTIL',
        'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
        'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT'
    ]
    
    data_dir = data_manager.data_dir
    
    # 현재 시간과 이전 시간 계산
    current_time = date_str + time_str
    
    # 이전 시간 계산 (range분 전)
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(current_time, "%Y%m%d%H%M")
        dt_prev = dt - timedelta(minutes=range_min)
        prev_date_str = dt_prev.strftime("%Y%m%d")
        prev_time_str = dt_prev.strftime("%H%M")
        prev_time_full = dt_prev.strftime("%Y%m%d%H%M")
    except Exception as e:
        return jsonify({'error': f'시간 계산 실패: {str(e)}'}), 400
    
    # 데이터 파일들 로드 (현재 날짜 + 이전 날짜가 다르면 둘 다)
    all_data = []
    dates_to_load = list(set([date_str, prev_date_str]))
    
    for d in dates_to_load:
        data_file = os.path.join(data_dir, f'm14_data_{d}.csv')
        if os.path.exists(data_file):
            try:
                df = pd.read_csv(data_file)
                df['CURRTIME'] = df['CURRTIME'].astype(str)
                all_data.append(df)
            except Exception as e:
                print(f"[detail] 파일 로드 실패 {d}: {e}")
    
    if not all_data:
        return jsonify({'error': '데이터 파일이 없습니다'}), 404
    
    # 데이터 병합
    df_all = pd.concat(all_data, ignore_index=True)
    df_all = df_all.drop_duplicates(subset=['CURRTIME'], keep='last')
    df_all = df_all.sort_values('CURRTIME').reset_index(drop=True)
    
    # 현재 시점 데이터 찾기
    current_row = df_all[df_all['CURRTIME'] == current_time]
    if len(current_row) == 0:
        return jsonify({'error': f'{date_str} {time_str[:2]}:{time_str[2:]} 데이터가 없습니다'}), 404
    
    current_row = current_row.iloc[0]
    
    # 이전 시점 데이터 찾기
    prev_row = df_all[df_all['CURRTIME'] == prev_time_full]
    if len(prev_row) == 0:
        # 정확한 시간이 없으면 가장 가까운 이전 시간 찾기
        prev_candidates = df_all[df_all['CURRTIME'] < current_time]
        if len(prev_candidates) > 0:
            prev_row = prev_candidates.iloc[-1]
            prev_time_full = prev_row['CURRTIME']
        else:
            return jsonify({'error': f'{range_min}분 전 데이터가 없습니다'}), 404
    else:
        prev_row = prev_row.iloc[0]
    
    # 변화량 계산
    changes = []
    for col in ANALYSIS_COLUMNS:
        current_val = current_row.get(col, 0) if col in current_row.index else 0
        prev_val = prev_row.get(col, 0) if col in prev_row.index else 0
        
        # NaN 처리
        if pd.isna(current_val):
            current_val = 0
        if pd.isna(prev_val):
            prev_val = 0
        
        current_val = float(current_val)
        prev_val = float(prev_val)
        
        change = current_val - prev_val
        change_rate = (change / prev_val * 100) if prev_val != 0 else 0
        
        # 미수집 여부 판단 (값이 모두 0이면 미수집 가능성)
        is_uncollected = col in UNCOLLECTED_COLUMNS and current_val == 0 and prev_val == 0
        
        changes.append({
            'column': col,
            'current': current_val,
            'previous': prev_val,
            'change': change,
            'change_rate': round(change_rate, 1),
            'is_uncollected': is_uncollected
        })
    
    # 변화량 절대값 기준 정렬
    changes.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return jsonify({
        'current_time': current_time,
        'previous_time': prev_time_full,
        'range': range_min,
        'current': {
            'CURRTIME': str(current_row.get('CURRTIME', '')),
            'TOTALCNT': int(current_row.get('TOTALCNT', 0)) if pd.notna(current_row.get('TOTALCNT')) else 0
        },
        'previous': {
            'CURRTIME': str(prev_row.get('CURRTIME', '')),
            'TOTALCNT': int(prev_row.get('TOTALCNT', 0)) if pd.notna(prev_row.get('TOTALCNT')) else 0
        },
        'changes': changes
    })


# ============================================================================
# LLM 분석 서버 프록시 (llm_analysis_server.py:8002로 전달)
# ============================================================================
LLM_SERVER_URL = "http://127.0.0.1:8002"

@app.route('/api/llm_mode', methods=['POST'])
def proxy_llm_mode():
    """LLM 모드 설정 프록시"""
    import requests as req
    try:
        resp = req.post(f"{LLM_SERVER_URL}/api/llm_mode", json=request.get_json(), timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/llm_history_analyze', methods=['POST'])
def proxy_llm_history_analyze():
    """LLM 히스토리 분석 프록시 (스트리밍)"""
    import requests as req
    try:
        resp = req.post(
            f"{LLM_SERVER_URL}/api/llm_history_analyze",
            json=request.get_json(),
            stream=True,
            timeout=300
        )
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        
        return app.response_class(generate(), mimetype='text/event-stream')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prompts', methods=['GET', 'POST'])
def proxy_prompts():
    """프롬프트 설정 프록시"""
    import requests as req
    try:
        if request.method == 'GET':
            resp = req.get(f"{LLM_SERVER_URL}/api/prompts", timeout=30)
        else:
            resp = req.post(f"{LLM_SERVER_URL}/api/prompts", json=request.get_json(), timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/llm_status', methods=['GET'])
def proxy_llm_status():
    """LLM 상태 조회 프록시"""
    import requests as req
    try:
        resp = req.get(f"{LLM_SERVER_URL}/api/status", timeout=30)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'offline'}), 500


@app.route('/api/realtime_detail')
def get_realtime_detail():
    """
    실시간 상세 분석 API - 메모리 데이터에서 컬럼별 변화량 분석
    
    Parameters:
        time: YYYYMMDDHHMM 형식의 시간
        range: 분석 범위 (분 단위, 기본값 10)
    
    Returns:
        current: 현재 시점 데이터
        previous: 이전 시점 데이터 (range분 전)
        changes: 컬럼별 변화량/변화율
    """
    time_str = request.args.get('time', '')
    range_min = int(request.args.get('range', '10'))
    
    if not time_str or len(time_str) != 12:
        return jsonify({'error': '시간 형식이 잘못되었습니다 (YYYYMMDDHHMM)'}), 400
    
    # 분석 대상 컬럼
    ANALYSIS_COLUMNS = [
        'M14AM10A', 'M10AM14A', 'M14AM10ASUM',
        'M14AM14B', 'M14BM14A', 'M14AM14BSUM',
        'M14AM16', 'M16M14A', 'M14AM16SUM',
        'M14.QUE.ALL.CURRENTQCREATED',
        'M14.QUE.ALL.CURRENTQCOMPLETED',
        'M14.QUE.OHT.OHTUTIL',
        'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
        'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT'
    ]
    
    # 미수집 가능 컬럼
    UNCOLLECTED_COLUMNS = [
        'M14.QUE.ALL.CURRENTQCREATED',
        'M14.QUE.ALL.CURRENTQCOMPLETED',
        'M14.QUE.OHT.OHTUTIL',
        'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
        'M14B.QUE.SENDFAB.VERTICALQUEUECOUNT'
    ]
    
    # 메모리에서 데이터 가져오기
    df = data_manager.get_data()
    
    if df is None or len(df) == 0:
        return jsonify({'error': '실시간 데이터가 없습니다'}), 404
    
    df['CURRTIME'] = df['CURRTIME'].astype(str)
    
    # 현재 시점 데이터 찾기
    current_row = df[df['CURRTIME'] == time_str]
    if len(current_row) == 0:
        return jsonify({'error': f'{time_str} 시점 데이터가 없습니다'}), 404
    
    current_idx = current_row.index[0]
    current_row = current_row.iloc[0]
    
    # 이전 시점 찾기 (range_min 전)
    prev_idx = max(0, current_idx - range_min)
    prev_row = df.iloc[prev_idx]
    prev_time_full = str(prev_row['CURRTIME'])
    
    # 변화량 계산
    changes = []
    for col in ANALYSIS_COLUMNS:
        current_val = current_row.get(col, 0) if col in current_row.index else 0
        prev_val = prev_row.get(col, 0) if col in prev_row.index else 0
        
        # NaN 처리
        if pd.isna(current_val):
            current_val = 0
        if pd.isna(prev_val):
            prev_val = 0
        
        current_val = float(current_val)
        prev_val = float(prev_val)
        
        change = current_val - prev_val
        change_rate = (change / prev_val * 100) if prev_val != 0 else 0
        
        # 미수집 여부 판단
        is_uncollected = col in UNCOLLECTED_COLUMNS and current_val == 0 and prev_val == 0
        
        changes.append({
            'column': col,
            'current': current_val,
            'previous': prev_val,
            'change': change,
            'change_rate': round(change_rate, 1),
            'is_uncollected': is_uncollected
        })
    
    # 변화량 절대값 기준 정렬
    changes.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return jsonify({
        'current_time': time_str,
        'previous_time': prev_time_full,
        'range': range_min,
        'current': {
            'CURRTIME': str(current_row.get('CURRTIME', '')),
            'TOTALCNT': int(current_row.get('TOTALCNT', 0)) if pd.notna(current_row.get('TOTALCNT')) else 0
        },
        'previous': {
            'CURRTIME': str(prev_row.get('CURRTIME', '')),
            'TOTALCNT': int(prev_row.get('TOTALCNT', 0)) if pd.notna(prev_row.get('TOTALCNT')) else 0
        },
        'changes': changes
    })


if __name__ == '__main__':
    print('=' * 60)
    print('M14 반송 큐 모니터링 서버')
    print('=' * 60)
    print('📦 모듈:')
    print('  - m14_data.py: 로그프레소 280분 데이터 조회')
    print('  - predictor_10min.py: V10_4 10분 예측')
    print('  - predictor_30min.py: V10_4 30분 예측')
    print('  - evaluator.py: 예측 평가 (내부/외부 지원)')
    print('  - logpresso_alarm.py: 로그프레소 알람 조회')
    print('=' * 60)
    print('🌐 http://localhost:5000')
    print('   /evaluate - 예측 평가 페이지')
    print('     📁 내부: data 폴더 CSV 파일 사용')
    print('     🌐 외부: 로그프레소 API 직접 조회')
    print('   /api/logpresso_alarm - 로그프레소 알람 조회')
    print('=' * 60)
    
    # 초기 데이터 로드
    print('\n[초기화] 280분 데이터 로드 중...')
    data_manager.initialize()
    
    # 서버 시작
    app.run(debug=False, port=5000)#, host='0.0.0.0')