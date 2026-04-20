#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - OHT 월드모델 시뮬레이션 서버

FastAPI 기반 통합 서버:
- 실 데이터 리플레이 (플레이/일시정지/속도조절/시간점프)
- 매크로 예측 (큐, TAT, 혼잡, 데드락)
- WebSocket 실시간 전송
- 스타/로그프레소 지표 연동 표시
"""

import asyncio
import json
import os
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SERVER_HOST, SERVER_PORT, DATA_DATES
from data_loader import LayoutData, HIDZoneData, get_available_dates
from replay_engine import ReplayEngine, ReplayState

# ============================================================
# 앱 초기화
# ============================================================

app = FastAPI(title="OHT 월드모델 시뮬레이션", version="1.0")

# 레이아웃 + Zone 로드 (서버 시작 시)
print("[초기화] layout_cache.json 로딩...")
layout = LayoutData().load()
print(f"  → 노드 {len(layout.nodes)}개, 엣지 {len(layout.edge_dist)}개")

print("[초기화] HID_Zone_Master 로딩...")
hid_zones = HIDZoneData().load()
print(f"  → Zone {len(hid_zones.zones)}개")

# 리플레이 엔진
engine = ReplayEngine(layout, hid_zones)

# WebSocket 연결 관리
ws_clients: list = []


# ============================================================
# API 엔드포인트
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """대시보드 HTML"""
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.get("/api/status")
async def get_status():
    """현재 시뮬레이션 상태"""
    snapshot = engine.get_current_snapshot()
    # 차량 위치는 WebSocket으로만 전송 (API에서는 제외)
    snapshot.pop('vehicles', None)
    return snapshot


@app.get("/api/dates")
async def get_dates():
    """사용 가능한 날짜 목록"""
    return get_available_dates()


@app.post("/api/replay/load")
async def load_date(request: Request):
    """날짜 데이터 로드"""
    body = await request.json()
    date_key = body.get('date', '')
    if date_key not in DATA_DATES:
        return JSONResponse({"error": f"Invalid date: {date_key}"}, status_code=400)

    print(f"[로드] {date_key} 데이터 로딩 시작...")
    result = engine.load_date(date_key)
    print(f"[로드] 완료: {result.get('stats', {})}")
    return result


@app.post("/api/replay/play")
async def replay_play():
    """리플레이 시작"""
    engine.play()
    return {"state": engine.state}


@app.post("/api/replay/pause")
async def replay_pause():
    """리플레이 일시정지"""
    engine.pause()
    return {"state": engine.state}


@app.post("/api/replay/stop")
async def replay_stop():
    """리플레이 정지"""
    engine.stop()
    return {"state": engine.state}


@app.post("/api/replay/speed")
async def replay_speed(request: Request):
    """재생 속도 변경"""
    body = await request.json()
    speed = float(body.get('speed', 1.0))
    engine.set_speed(speed)
    return {"speed": engine.speed}


@app.post("/api/replay/jump")
async def replay_jump(request: Request):
    """특정 시각으로 점프"""
    body = await request.json()

    # 시간 점프
    time_str = body.get('time')
    if time_str:
        ok = engine.jump_to_time(time_str)
        if ok:
            return {"jumped": True, "time": engine.current_time.strftime("%H:%M:%S") if engine.current_time else ""}
        return JSONResponse({"error": "Invalid time"}, status_code=400)

    # 프레임 점프
    frame = body.get('frame')
    if frame is not None:
        ok = engine.jump_to_frame(int(frame))
        if ok:
            return {"jumped": True, "frame": engine.current_frame_idx}
        return JSONResponse({"error": "Invalid frame"}, status_code=400)

    return JSONResponse({"error": "Provide 'time' or 'frame'"}, status_code=400)


@app.get("/api/predict")
async def get_prediction():
    """매크로 예측 결과"""
    return engine.predictor.get_prediction()


@app.get("/api/predict-deadlock")
async def predict_deadlock(force: bool = Query(False)):
    """데드락 예측"""
    if not engine.world.vehicles:
        return {"vehicleCount": 0, "horizons": {}, "summary": {"totalDeadlocks": 0}}
    return engine.world.predict_deadlocks()


@app.get("/api/correlations")
async def get_correlations():
    """데이터 간 상관관계"""
    return engine.predictor.get_correlations()


@app.get("/api/star-history")
async def get_star_history():
    """스타 전체 타임라인 (차트용)"""
    return engine.get_star_history()


@app.get("/api/hid-speeds")
async def get_hid_speeds():
    """HID 구간별 속도 통계"""
    return engine.get_hid_speed_summary()


@app.get("/api/obs-jam-history")
async def get_obs_jam_history():
    """OBS/JAM 분 단위 시계열 (전체 데이터, 재생과 무관)"""
    return engine.get_obs_jam_history()


@app.get("/api/bottleneck-analysis")
async def get_bottleneck_analysis():
    """HID_INOUT × ts_resource 교차 병목 분석 (UDP 독립)"""
    return engine.get_bottleneck_analysis()


@app.get("/api/ts-events")
async def get_ts_events():
    """ts_resource 분 단위 집계"""
    return engine.get_ts_events()


@app.get("/api/hid-zones")
async def get_hid_zones():
    """HID Zone 현황"""
    return engine.world.get_zone_status()


@app.get("/api/data-sources")
async def get_data_sources():
    """로드된 데이터 현황"""
    if engine.data_loader:
        return {
            'date': engine.current_date,
            'stats': engine.data_loader.stats,
            'time_start': str(engine.data_loader.time_start),
            'time_end': str(engine.data_loader.time_end),
        }
    return {'date': None, 'stats': {}}


@app.get("/api/layout-bounds")
async def get_layout_bounds():
    """레이아웃 바운드 정보"""
    return layout.bounds


@app.get("/api/layout-graph")
async def get_layout_graph():
    """레이아웃 노드/엣지 전체 (맵 배경용) - 초기 1회만 로드"""
    nodes = {str(nid): [round(c[0], 1), round(c[1], 1)] for nid, c in layout.nodes.items()}
    edges = [[e[0], e[1]] for e in layout.edge_dist.keys()]

    # HID Zone: IN/OUT Lane 좌표 포함
    zone_list = []
    seen = set()
    for zid, zinfo in hid_zones.zones.items():
        if zid in seen:
            continue
        seen.add(zid)

        in_lanes = []
        for (a, b), z in hid_zones.in_lane_to_zone.items():
            if z == zid and a in layout.nodes and b in layout.nodes:
                in_lanes.append({'from': a, 'to': b})
        out_lanes = []
        for (a, b), z in hid_zones.out_lane_to_zone.items():
            if z == zid and a in layout.nodes and b in layout.nodes:
                out_lanes.append({'from': a, 'to': b})

        if not in_lanes and not out_lanes:
            continue

        # 중심점 계산
        all_nodes_set = set()
        for l in in_lanes + out_lanes:
            all_nodes_set.add(l['from'])
            all_nodes_set.add(l['to'])
        xs = [layout.nodes[n][0] for n in all_nodes_set if n in layout.nodes]
        ys = [layout.nodes[n][1] for n in all_nodes_set if n in layout.nodes]
        if not xs:
            continue

        zone_list.append({
            'id': zid,
            'name': zinfo.get('fullName', f'Zone-{zid}'),
            'bay': zinfo.get('bayZone', ''),
            'hid': zinfo.get('hidNo', ''),
            'max': zinfo.get('vehicleMax', 37),
            'inLanes': in_lanes,
            'outLanes': out_lanes,
            'cx': round(sum(xs)/len(xs), 1),
            'cy': round(sum(ys)/len(ys), 1),
        })

    return {"nodes": nodes, "edges": edges, "bounds": layout.bounds, "zones": zone_list}


# ============================================================
# WebSocket
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    print(f"[WS] 연결 ({len(ws_clients)}개)")

    try:
        while True:
            # 클라이언트 메시지 수신 (keep-alive)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # 클라이언트 명령 처리
                try:
                    cmd = json.loads(data)
                    action = cmd.get('action')
                    if action == 'play':
                        engine.play()
                    elif action == 'pause':
                        engine.pause()
                    elif action == 'stop':
                        engine.stop()
                    elif action == 'speed':
                        engine.set_speed(float(cmd.get('speed', 1.0)))
                    elif action == 'jump':
                        engine.jump_to_time(cmd.get('time', ''))
                    elif action == 'jump_frame':
                        engine.jump_to_frame(int(cmd.get('frame', 0)))
                    elif action == 'load':
                        date_key = cmd.get('date', '')
                        if date_key in DATA_DATES:
                            engine.load_date(date_key)
                except (json.JSONDecodeError, ValueError):
                    pass
            except asyncio.TimeoutError:
                pass

            # 상태 전송
            if engine.state == ReplayState.PLAYING:
                # 속도에 따라 프레임 스킵
                speed = engine.speed
                if speed <= 0:
                    # MAX: 한번에 10프레임 전진
                    for _ in range(10):
                        if not engine.advance_frame():
                            break
                elif speed >= 5:
                    # x5, x10: 속도만큼 프레임 스킵
                    for _ in range(int(speed)):
                        if not engine.advance_frame():
                            break
                else:
                    engine.advance_frame()

            snapshot = engine.get_current_snapshot()
            # 차량 위치만 간소화 (빠른 전송)
            await websocket.send_text(json.dumps(snapshot, default=str))

            # 속도에 맞는 대기 시간
            if engine.state == ReplayState.PLAYING:
                spd = engine.speed
                if spd <= 0:
                    await asyncio.sleep(0.05)
                elif spd >= 5:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.4 / max(1, spd))
            else:
                await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        print(f"[WS] 연결 해제 ({len(ws_clients)}개)")
    except Exception as e:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        print(f"[WS] 오류: {e}")


# ============================================================
# 메인
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  OHT 월드모델 시뮬레이션 서버")
    print(f"  http://localhost:{SERVER_PORT}")
    print("=" * 60)
    print(f"  레이아웃: {len(layout.nodes)} 노드, {len(layout.edge_dist)} 엣지")
    print(f"  HID Zone: {len(hid_zones.zones)}개")
    print(f"  사용 가능 날짜: {list(DATA_DATES.keys())}")
    print("=" * 60)

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
