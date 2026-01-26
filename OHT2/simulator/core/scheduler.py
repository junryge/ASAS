"""
OHT2 시뮬레이터 - 스케줄러
동적 라우팅 및 HotLot 우선순위 기반 작업 배정

기능:
- 작업 큐 관리
- 차량 배정 알고리즘
- 경로 계산 (최단 경로)
- HotLot 우선순위 처리
- 충돌 방지
"""

import heapq
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import time

from .models import (
    Vehicle, Station, Lane, Address, TransportJob,
    VehicleState, JobStatus, JobPriority, Position,
    SimulationConfig, SPEED_TABLE
)


class PathFinder:
    """경로 탐색기 (Dijkstra 알고리즘 사용)"""

    def __init__(self, addresses: Dict[int, Address], lanes: Dict[int, Lane]):
        self.addresses = addresses
        self.lanes = lanes
        self._build_graph()

    def _build_graph(self):
        """주소 연결 그래프 생성"""
        self.graph: Dict[int, List[Tuple[int, float]]] = defaultdict(list)

        for lane in self.lanes.values():
            if not lane.is_active:
                continue
            start = lane.start_address
            end = lane.end_address
            self.graph[start].append((end, lane.length))
            if lane.is_bidirectional:
                self.graph[end].append((start, lane.length))

    def find_path(self, start: int, end: int) -> Tuple[List[int], float]:
        """최단 경로 찾기

        Args:
            start: 시작 주소 ID
            end: 도착 주소 ID

        Returns:
            (경로 주소 리스트, 총 거리)
        """
        if start == end:
            return [start], 0.0

        # Dijkstra 알고리즘
        distances = {start: 0.0}
        previous: Dict[int, Optional[int]] = {start: None}
        pq = [(0.0, start)]
        visited: Set[int] = set()

        while pq:
            dist, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == end:
                break

            for neighbor, weight in self.graph[current]:
                if neighbor in visited:
                    continue
                new_dist = dist + weight
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))

        # 경로 재구성
        if end not in previous:
            return [], float('inf')

        path = []
        current: Optional[int] = end
        while current is not None:
            path.append(current)
            current = previous.get(current)
        path.reverse()

        return path, distances.get(end, float('inf'))


class Scheduler:
    """OHT 스케줄러"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.job_queue: List[TransportJob] = []
        self.active_jobs: Dict[int, TransportJob] = {}
        self.completed_jobs: List[TransportJob] = []
        self.path_finder: Optional[PathFinder] = None

    def set_path_finder(self, path_finder: PathFinder):
        """경로 탐색기 설정"""
        self.path_finder = path_finder

    def add_job(self, job: TransportJob):
        """새 이송 작업 추가"""
        # HotLot 체크
        if job.is_hotlot:
            job.priority = JobPriority.HOTLOT
            job.timeout = self.config.hotlot_timeout

        self.job_queue.append(job)
        # 우선순위 기반 정렬 (높은 우선순위 먼저)
        self.job_queue.sort(key=lambda j: (-j.priority.value, j.created_at))

    def cancel_job(self, job_id: int) -> bool:
        """작업 취소"""
        for job in self.job_queue:
            if job.id == job_id:
                job.status = JobStatus.CANCELLED
                self.job_queue.remove(job)
                return True

        if job_id in self.active_jobs:
            self.active_jobs[job_id].status = JobStatus.CANCELLED
            return True

        return False

    def get_pending_jobs(self) -> List[TransportJob]:
        """대기 중인 작업 목록"""
        return [j for j in self.job_queue if j.status == JobStatus.PENDING]

    def assign_jobs(
        self,
        vehicles: Dict[int, Vehicle],
        stations: Dict[int, Station]
    ) -> List[Tuple[int, int]]:
        """작업-차량 배정

        Returns:
            [(작업ID, 차량ID), ...] 배정 결과
        """
        assignments = []
        available_vehicles = [
            v for v in vehicles.values()
            if v.state == VehicleState.IDLE and not v.has_foup
        ]

        if not available_vehicles or not self.job_queue:
            return assignments

        pending_jobs = self.get_pending_jobs()

        for job in pending_jobs[:len(available_vehicles)]:
            # 가장 가까운 차량 찾기
            best_vehicle = None
            best_distance = float('inf')

            source_station = stations.get(job.source_station)
            if not source_station:
                continue

            for vehicle in available_vehicles:
                if self.path_finder:
                    _, distance = self.path_finder.find_path(
                        vehicle.current_address,
                        source_station.address_id
                    )
                else:
                    # 경로 탐색기가 없으면 유클리드 거리 사용
                    distance = vehicle.position.distance_to(source_station.position)

                if distance < best_distance:
                    best_distance = distance
                    best_vehicle = vehicle

            if best_vehicle:
                # 배정
                job.status = JobStatus.ASSIGNED
                job.assigned_vehicle = best_vehicle.id
                job.started_at = time.time()

                self.job_queue.remove(job)
                self.active_jobs[job.id] = job

                available_vehicles.remove(best_vehicle)
                assignments.append((job.id, best_vehicle.id))

        return assignments

    def complete_job(self, job_id: int):
        """작업 완료 처리"""
        if job_id in self.active_jobs:
            job = self.active_jobs.pop(job_id)
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            self.completed_jobs.append(job)

    def check_hotlot_timeout(self) -> List[int]:
        """HotLot 타임아웃 체크

        Returns:
            타임아웃된 작업 ID 리스트
        """
        current_time = time.time()
        timed_out = []

        for job in self.job_queue:
            if job.is_hotlot:
                elapsed = current_time - job.created_at
                if elapsed > job.timeout:
                    timed_out.append(job.id)

        return timed_out

    def get_statistics(self) -> Dict:
        """스케줄러 통계"""
        completed_times = [
            j.completed_at - j.started_at
            for j in self.completed_jobs
            if j.started_at and j.completed_at
        ]

        return {
            "pending_jobs": len(self.job_queue),
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "avg_completion_time": (
                sum(completed_times) / len(completed_times)
                if completed_times else 0
            ),
            "hotlot_count": sum(1 for j in self.job_queue if j.is_hotlot),
        }


class CollisionAvoidance:
    """충돌 방지 시스템"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.bump_distance = config.bump_distance  # mm

    def check_collision(
        self,
        vehicle: Vehicle,
        other_vehicles: List[Vehicle]
    ) -> List[Vehicle]:
        """충돌 가능 차량 체크

        Args:
            vehicle: 검사할 차량
            other_vehicles: 다른 차량들

        Returns:
            충돌 가능한 차량 리스트
        """
        collisions = []

        for other in other_vehicles:
            if other.id == vehicle.id:
                continue

            distance = vehicle.position.distance_to(other.position)
            if distance < self.bump_distance:
                collisions.append(other)

        return collisions

    def calculate_safe_speed(
        self,
        vehicle: Vehicle,
        front_vehicle: Optional[Vehicle]
    ) -> float:
        """안전 속도 계산

        Args:
            vehicle: 현재 차량
            front_vehicle: 전방 차량

        Returns:
            안전 속도 (m/min)
        """
        if not front_vehicle:
            return vehicle.max_speed

        distance = vehicle.position.distance_to(front_vehicle.position)

        # 거리에 따른 속도 조절
        if distance < self.bump_distance * 0.3:
            return 0  # 정지
        elif distance < self.bump_distance * 0.5:
            return min(front_vehicle.speed * 0.5, 20)
        elif distance < self.bump_distance * 0.7:
            return min(front_vehicle.speed * 0.8, 50)
        elif distance < self.bump_distance:
            return min(front_vehicle.speed, 100)
        else:
            return vehicle.max_speed

    def get_recommended_action(
        self,
        vehicle: Vehicle,
        collisions: List[Vehicle]
    ) -> str:
        """권장 동작 반환"""
        if not collisions:
            return "CONTINUE"

        nearest = min(
            collisions,
            key=lambda v: vehicle.position.distance_to(v.position)
        )
        distance = vehicle.position.distance_to(nearest.position)

        if distance < self.bump_distance * 0.3:
            return "EMERGENCY_STOP"
        elif distance < self.bump_distance * 0.5:
            return "SLOW_DOWN_HIGH"
        elif distance < self.bump_distance:
            return "SLOW_DOWN_LOW"
        else:
            return "CONTINUE"
