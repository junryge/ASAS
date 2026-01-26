#!/usr/bin/env python3
"""
OHT2 시뮬레이터 - 메인 실행 스크립트
SK하이닉스 M14 반도체 공장 OHT 시스템 시뮬레이션

사용법:
    # 콘솔 모드
    python main.py --mode console

    # 웹 서버 모드
    python main.py --mode server

    # 데모 실행
    python main.py --mode demo
"""

import argparse
import time
import sys
from pathlib import Path

# 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    SimulationEngine, create_demo_layout,
    Vehicle, Station, TransportJob,
    VehicleState, JobStatus, JobPriority
)


def run_console_mode(engine: SimulationEngine, duration: float = 60.0):
    """콘솔 모드 실행"""
    print("\n" + "=" * 60)
    print("OHT2 Simulator - Console Mode")
    print("M14-Pro Ver.1.22.2 | SK Hynix")
    print("=" * 60)

    engine.initialize()

    # 샘플 작업 생성
    print("\n[INFO] Creating sample transport jobs...")
    for i in range(5):
        job = engine.create_job(
            source=i + 1,
            dest=i + 20,
            priority=JobPriority.NORMAL,
            is_hotlot=(i == 0)  # 첫 번째 작업은 HotLot
        )
        print(f"  - Job #{job.id}: Station {job.source_station} -> {job.dest_station}")

    print(f"\n[INFO] Starting simulation for {duration} seconds...")
    print("Press Ctrl+C to stop\n")

    start_time = time.time()
    last_report = 0

    try:
        while time.time() - start_time < duration:
            engine.tick()

            # 1초마다 상태 출력
            if engine.tick_count - last_report >= 10:
                last_report = engine.tick_count
                state = engine.get_state()
                stats = state['statistics']

                print(f"\r[Tick {engine.tick_count:5d}] "
                      f"Time: {engine.simulation_time:6.1f}s | "
                      f"Vehicles: {len(state['vehicles']):3d} | "
                      f"Jobs: P={stats['pending_jobs']} A={stats['active_jobs']} C={stats['completed_jobs']}",
                      end='', flush=True)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[INFO] Simulation stopped by user")

    # 최종 통계
    final_state = engine.get_state()
    stats = final_state['statistics']

    print("\n" + "=" * 60)
    print("Simulation Results")
    print("=" * 60)
    print(f"Total Ticks: {engine.tick_count}")
    print(f"Simulation Time: {engine.simulation_time:.1f} seconds")
    print(f"Pending Jobs: {stats['pending_jobs']}")
    print(f"Active Jobs: {stats['active_jobs']}")
    print(f"Completed Jobs: {stats['completed_jobs']}")
    print(f"Average Completion Time: {stats['avg_completion_time']:.2f} seconds")
    print("=" * 60)


def run_demo_mode():
    """데모 모드 - 시각적 데모"""
    print("\n" + "=" * 60)
    print("OHT2 Simulator - Demo Mode")
    print("=" * 60)

    engine = create_demo_layout()
    engine.initialize()

    # 작업 생성
    jobs = []
    for i in range(10):
        job = engine.create_job(
            source=i + 1,
            dest=i + 30,
            priority=JobPriority.NORMAL
        )
        jobs.append(job)

    print(f"\n[INFO] Created {len(jobs)} transport jobs")
    print("[INFO] Running demo simulation...\n")

    # 짧은 시뮬레이션 실행
    for i in range(100):
        engine.tick()

        if i % 10 == 0:
            state = engine.get_state()
            moving = sum(1 for v in state['vehicles'] if v['state'] == 'MOVING')
            print(f"Tick {engine.tick_count}: {moving} vehicles moving")

    print("\n[INFO] Demo completed!")

    # 차량 상태 출력
    state = engine.get_state()
    print("\nVehicle States:")
    for v in state['vehicles'][:10]:
        print(f"  {v['name']}: {v['state']} at ({v['x']:.0f}, {v['y']:.0f})")


def run_server_mode():
    """웹 서버 모드"""
    print("[INFO] Starting server mode...")
    print("[INFO] Run: python server.py")

    # server.py 실행
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).parent / 'server.py')])


def main():
    parser = argparse.ArgumentParser(
        description='OHT2 Simulator - M14 Pro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode demo       Run quick demo
  python main.py --mode console    Run console simulation
  python main.py --mode server     Start web server

M14-Pro Ver.1.22.2 | SK Hynix | OHT System Simulator
        """
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['console', 'server', 'demo'],
        default='demo',
        help='Simulation mode (default: demo)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=60.0,
        help='Simulation duration in seconds (console mode)'
    )
    parser.add_argument(
        '--vehicles', '-v',
        type=int,
        default=20,
        help='Number of vehicles'
    )

    args = parser.parse_args()

    if args.mode == 'console':
        engine = create_demo_layout()
        run_console_mode(engine, args.duration)
    elif args.mode == 'server':
        run_server_mode()
    else:  # demo
        run_demo_mode()


if __name__ == '__main__':
    main()
