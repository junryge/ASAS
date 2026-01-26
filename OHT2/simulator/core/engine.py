"""
OHT2 시뮬레이터 - 시뮬레이션 엔진
차량 이동, 작업 처리, 상태 업데이트

기능:
- 차량 위치 업데이트
- 경로 추종
- 적재/하역 처리
- 시뮬레이션 틱 관리
"""

import time
import random
import json
from typing import Dict, List, Optional, Callable
from dataclasses import asdict

from .models import (
    Vehicle, Station, Lane, Address, TransportJob,
    VehicleState, StationType, JobStatus, JobPriority, Position,
    SimulationConfig, Route, SPEED_TABLE
)
from .scheduler import Scheduler, PathFinder, CollisionAvoidance


class SimulationEngine:
    """시뮬레이션 엔진"""

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.tick_count = 0
        self.simulation_time = 0.0  # 초
        self.tick_interval = 0.1  # 100ms

        # 데이터 저장소
        self.addresses: Dict[int, Address] = {}
        self.lanes: Dict[int, Lane] = {}
        self.stations: Dict[int, Station] = {}
        self.vehicles: Dict[int, Vehicle] = {}
        self.routes: Dict[str, Route] = {}

        # 시스템 컴포넌트
        self.scheduler = Scheduler(self.config)
        self.collision_avoidance = CollisionAvoidance(self.config)
        self.path_finder: Optional[PathFinder] = None

        # 콜백
        self.on_tick: Optional[Callable] = None
        self.on_job_completed: Optional[Callable] = None
        self.on_vehicle_state_changed: Optional[Callable] = None

        # 실행 상태
        self.is_running = False
        self.is_paused = False

    def initialize(self):
        """시뮬레이션 초기화"""
        if self.addresses and self.lanes:
            self.path_finder = PathFinder(self.addresses, self.lanes)
            self.scheduler.set_path_finder(self.path_finder)

    def add_address(self, address: Address):
        """주소 추가"""
        self.addresses[address.id] = address

    def add_lane(self, lane: Lane):
        """레인 추가"""
        self.lanes[lane.id] = lane

    def add_station(self, station: Station):
        """스테이션 추가"""
        self.stations[station.id] = station

    def add_vehicle(self, vehicle: Vehicle):
        """차량 추가"""
        self.vehicles[vehicle.id] = vehicle

    def add_route(self, route: Route):
        """경로 추가"""
        self.routes[route.name] = route

    def create_job(
        self,
        source: int,
        dest: int,
        priority: JobPriority = JobPriority.NORMAL,
        is_hotlot: bool = False,
        carrier_id: Optional[str] = None
    ) -> TransportJob:
        """이송 작업 생성"""
        job_id = len(self.scheduler.job_queue) + len(self.scheduler.active_jobs) + 1
        job = TransportJob(
            id=job_id,
            source_station=source,
            dest_station=dest,
            priority=priority,
            is_hotlot=is_hotlot,
            carrier_id=carrier_id
        )
        self.scheduler.add_job(job)
        return job

    def tick(self):
        """시뮬레이션 한 틱 실행"""
        if self.is_paused:
            return

        self.tick_count += 1
        self.simulation_time += self.tick_interval

        # 1. 작업 배정
        if self.tick_count % 10 == 0:  # 1초마다
            assignments = self.scheduler.assign_jobs(self.vehicles, self.stations)
            for job_id, vehicle_id in assignments:
                self._start_job(job_id, vehicle_id)

        # 2. 차량 업데이트
        for vehicle in self.vehicles.values():
            self._update_vehicle(vehicle)

        # 3. HotLot 타임아웃 체크
        if self.tick_count % 100 == 0:  # 10초마다
            timed_out = self.scheduler.check_hotlot_timeout()
            for job_id in timed_out:
                print(f"[WARNING] HotLot job {job_id} timed out!")

        # 콜백 호출
        if self.on_tick:
            self.on_tick(self.get_state())

    def _start_job(self, job_id: int, vehicle_id: int):
        """작업 시작"""
        job = self.scheduler.active_jobs.get(job_id)
        vehicle = self.vehicles.get(vehicle_id)

        if not job or not vehicle:
            return

        # 픽업 스테이션으로 이동 시작
        source_station = self.stations.get(job.source_station)
        if not source_station:
            return

        vehicle.current_job = job_id
        vehicle.state = VehicleState.MOVING
        vehicle.target_address = source_station.address_id

        # 경로 계산
        if self.path_finder:
            path, _ = self.path_finder.find_path(
                vehicle.current_address,
                source_station.address_id
            )
            vehicle.path = path
            vehicle.path_index = 0

        job.status = JobStatus.PICKUP

    def _update_vehicle(self, vehicle: Vehicle):
        """차량 상태 업데이트"""
        if vehicle.state == VehicleState.IDLE:
            return

        if vehicle.state == VehicleState.MOVING:
            self._move_vehicle(vehicle)

        elif vehicle.state == VehicleState.LOADING:
            self._process_loading(vehicle)

        elif vehicle.state == VehicleState.UNLOADING:
            self._process_unloading(vehicle)

    def _move_vehicle(self, vehicle: Vehicle):
        """차량 이동 처리"""
        if not vehicle.path or vehicle.path_index >= len(vehicle.path):
            # 목적지 도착
            self._on_vehicle_arrived(vehicle)
            return

        # 충돌 체크
        other_vehicles = [v for v in self.vehicles.values() if v.id != vehicle.id]
        collisions = self.collision_avoidance.check_collision(vehicle, other_vehicles)

        if collisions:
            # 안전 속도 계산
            front_vehicle = min(
                collisions,
                key=lambda v: vehicle.position.distance_to(v.position)
            )
            vehicle.speed = self.collision_avoidance.calculate_safe_speed(
                vehicle, front_vehicle
            )
        else:
            vehicle.speed = vehicle.max_speed

        # 다음 목표 주소
        target_addr_id = vehicle.path[vehicle.path_index]
        target_addr = self.addresses.get(target_addr_id)

        if not target_addr:
            vehicle.path_index += 1
            return

        # 이동
        target_pos = target_addr.position
        current_pos = vehicle.position

        dx = target_pos.x - current_pos.x
        dy = target_pos.y - current_pos.y
        distance = (dx**2 + dy**2) ** 0.5

        if distance < 1:  # 도착
            vehicle.position = Position(target_pos.x, target_pos.y)
            vehicle.current_address = target_addr_id
            vehicle.path_index += 1
        else:
            # 속도 기반 이동 (m/min -> 단위 변환)
            speed_per_tick = (vehicle.speed / 60) * self.tick_interval * 1000  # mm/tick
            move_ratio = min(speed_per_tick / distance, 1.0)

            vehicle.position = Position(
                current_pos.x + dx * move_ratio,
                current_pos.y + dy * move_ratio
            )

    def _on_vehicle_arrived(self, vehicle: Vehicle):
        """차량 도착 처리"""
        job = self.scheduler.active_jobs.get(vehicle.current_job)

        if not job:
            vehicle.state = VehicleState.IDLE
            vehicle.target_address = None
            return

        if job.status == JobStatus.PICKUP:
            # 픽업 지점 도착 -> 적재 시작
            vehicle.state = VehicleState.LOADING
            vehicle.speed = 0

        elif job.status == JobStatus.TRANSFER:
            # 목적지 도착 -> 하역 시작
            vehicle.state = VehicleState.UNLOADING
            vehicle.speed = 0

    def _process_loading(self, vehicle: Vehicle):
        """적재 처리 (간소화)"""
        # 실제로는 호이스트 동작 시뮬레이션 필요
        # 여기서는 3틱(0.3초) 후 완료로 간주
        if not hasattr(vehicle, '_loading_ticks'):
            vehicle._loading_ticks = 0

        vehicle._loading_ticks += 1

        if vehicle._loading_ticks >= 30:  # 3초
            vehicle._loading_ticks = 0
            vehicle.has_foup = True

            # 스테이션 업데이트
            job = self.scheduler.active_jobs.get(vehicle.current_job)
            if job:
                station = self.stations.get(job.source_station)
                if station:
                    station.has_foup = False

                # 목적지로 이동 시작
                dest_station = self.stations.get(job.dest_station)
                if dest_station:
                    vehicle.target_address = dest_station.address_id
                    vehicle.state = VehicleState.MOVING

                    if self.path_finder:
                        path, _ = self.path_finder.find_path(
                            vehicle.current_address,
                            dest_station.address_id
                        )
                        vehicle.path = path
                        vehicle.path_index = 0

                    job.status = JobStatus.TRANSFER

    def _process_unloading(self, vehicle: Vehicle):
        """하역 처리 (간소화)"""
        if not hasattr(vehicle, '_unloading_ticks'):
            vehicle._unloading_ticks = 0

        vehicle._unloading_ticks += 1

        if vehicle._unloading_ticks >= 30:  # 3초
            vehicle._unloading_ticks = 0
            vehicle.has_foup = False
            vehicle.state = VehicleState.IDLE
            vehicle.target_address = None
            vehicle.path = []

            # 스테이션 업데이트
            job = self.scheduler.active_jobs.get(vehicle.current_job)
            if job:
                station = self.stations.get(job.dest_station)
                if station:
                    station.has_foup = True

                # 작업 완료
                self.scheduler.complete_job(job.id)

                if self.on_job_completed:
                    self.on_job_completed(job)

            vehicle.current_job = None

    def get_state(self) -> Dict:
        """현재 시뮬레이션 상태 반환"""
        return {
            "tick": self.tick_count,
            "time": self.simulation_time,
            "vehicles": [
                {
                    "id": v.id,
                    "name": v.name,
                    "state": v.state.value,
                    "x": v.position.x,
                    "y": v.position.y,
                    "speed": v.speed,
                    "has_foup": v.has_foup,
                    "current_job": v.current_job,
                    "current_address": v.current_address,
                }
                for v in self.vehicles.values()
            ],
            "stations": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.station_type.value,
                    "x": s.position.x,
                    "y": s.position.y,
                    "has_foup": s.has_foup,
                    "is_available": s.is_available,
                }
                for s in list(self.stations.values())[:100]  # 처음 100개만
            ],
            "jobs": {
                "pending": len(self.scheduler.job_queue),
                "active": len(self.scheduler.active_jobs),
                "completed": len(self.scheduler.completed_jobs),
            },
            "statistics": self.scheduler.get_statistics(),
        }

    def run(self, duration: float = 60.0):
        """시뮬레이션 실행

        Args:
            duration: 실행 시간 (초)
        """
        self.is_running = True
        self.initialize()

        target_ticks = int(duration / self.tick_interval)

        for _ in range(target_ticks):
            if not self.is_running:
                break
            self.tick()
            time.sleep(self.tick_interval)

        self.is_running = False

    def stop(self):
        """시뮬레이션 중지"""
        self.is_running = False

    def pause(self):
        """시뮬레이션 일시정지"""
        self.is_paused = True

    def resume(self):
        """시뮬레이션 재개"""
        self.is_paused = False

    def reset(self):
        """시뮬레이션 리셋"""
        self.tick_count = 0
        self.simulation_time = 0.0
        self.is_running = False
        self.is_paused = False

        # 차량 상태 리셋
        for vehicle in self.vehicles.values():
            vehicle.state = VehicleState.IDLE
            vehicle.has_foup = False
            vehicle.current_job = None
            vehicle.path = []
            vehicle.speed = 0

        # 스케줄러 리셋
        self.scheduler.job_queue.clear()
        self.scheduler.active_jobs.clear()
        self.scheduler.completed_jobs.clear()


def create_demo_layout() -> SimulationEngine:
    """데모용 레이아웃 생성"""
    engine = SimulationEngine()

    # 샘플 주소 생성 (그리드 형태)
    addr_id = 1
    for row in range(10):
        for col in range(20):
            x = col * 500 + 100  # 500mm 간격
            y = row * 400 + 100  # 400mm 간격
            addr = Address(
                id=addr_id,
                position=Position(x, y),
                next_addresses=[],
                is_junction=(col % 5 == 0)
            )
            engine.add_address(addr)
            addr_id += 1

    # 주소 연결 (레인 생성)
    lane_id = 1
    for addr in list(engine.addresses.values()):
        # 오른쪽 연결
        right_addr_id = addr.id + 1
        if right_addr_id in engine.addresses:
            right_addr = engine.addresses[right_addr_id]
            if int((addr.id - 1) / 20) == int((right_addr_id - 1) / 20):  # 같은 행
                addr.next_addresses.append(right_addr_id)
                lane = Lane(
                    id=lane_id,
                    start_address=addr.id,
                    end_address=right_addr_id,
                    length=500.0
                )
                engine.add_lane(lane)
                lane_id += 1

        # 아래 연결
        down_addr_id = addr.id + 20
        if down_addr_id in engine.addresses:
            addr.next_addresses.append(down_addr_id)
            lane = Lane(
                id=lane_id,
                start_address=addr.id,
                end_address=down_addr_id,
                length=400.0
            )
            engine.add_lane(lane)
            lane_id += 1

    # 샘플 스테이션 생성
    station_types = list(StationType)
    for i in range(50):
        addr_id = random.randint(1, len(engine.addresses))
        addr = engine.addresses.get(addr_id)
        if addr:
            station = Station(
                id=i + 1,
                name=f"STN_{i+1:04d}",
                position=Position(addr.position.x + 50, addr.position.y),
                station_type=random.choice(station_types[:4]),
                address_id=addr_id,
                has_foup=random.random() < 0.3
            )
            engine.add_station(station)

    # 샘플 차량 생성
    for i in range(20):
        addr_id = random.randint(1, len(engine.addresses))
        addr = engine.addresses.get(addr_id)
        if addr:
            vehicle = Vehicle(
                id=i + 1,
                name=f"OHT_{i+1:04d}",
                position=Position(addr.position.x, addr.position.y),
                current_address=addr_id,
                max_speed=200.0
            )
            engine.add_vehicle(vehicle)

    engine.initialize()
    return engine
