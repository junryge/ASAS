"""
OHT2 시뮬레이터 - 핵심 데이터 모델
SK하이닉스 M14 반도체 공장 OHT 시스템 시뮬레이션

데이터 모델:
- Vehicle (OHT 차량)
- Station (로딩/언로딩 스테이션)
- Lane (레일 구간)
- TransportJob (이송 작업)
- Route (경로)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
import time


class VehicleState(Enum):
    """OHT 차량 상태"""
    IDLE = "IDLE"                    # 대기 중
    MOVING = "MOVING"                # 이동 중
    LOADING = "LOADING"              # 적재 중
    UNLOADING = "UNLOADING"          # 하역 중
    CHARGING = "CHARGING"            # 충전 중
    MAINTENANCE = "MAINTENANCE"      # 유지보수 중
    ERROR = "ERROR"                  # 오류


class StationType(Enum):
    """스테이션 타입"""
    DUAL_ACCESS = "DUAL_ACCESS"      # 양방향 접근 가능
    ZFS_RIGHT = "ZFS_RIGHT"          # ZFS 우측
    ZFS_LEFT = "ZFS_LEFT"            # ZFS 좌측
    UNIVERSAL = "UNIVERSAL"          # 범용
    ACQUIRE = "ACQUIRE"              # 캐리어 수취
    MAINTENANCE = "MAINTENANCE"      # 유지보수용
    DEPOSIT = "DEPOSIT"              # 캐리어 보관
    MANUAL_ONLY = "MANUAL_ONLY"      # 수동 조작 전용
    DUMMY = "DUMMY"                  # 더미(테스트용)
    MTL_SWITCHBACK = "MTL_SWITCHBACK"  # MTL 스위치백
    MTL_ELEVATOR = "MTL_ELEVATOR"    # MTL 엘리베이터


class JobStatus(Enum):
    """이송 작업 상태"""
    PENDING = "PENDING"              # 대기
    ASSIGNED = "ASSIGNED"            # 차량 배정됨
    PICKUP = "PICKUP"                # 픽업 중
    TRANSFER = "TRANSFER"            # 이송 중
    DROPOFF = "DROPOFF"              # 하역 중
    COMPLETED = "COMPLETED"          # 완료
    CANCELLED = "CANCELLED"          # 취소
    ERROR = "ERROR"                  # 오류


class JobPriority(Enum):
    """작업 우선순위"""
    NORMAL = 1
    HIGH = 50
    URGENT = 90
    HOTLOT = 99  # 최우선 (HotLot)


@dataclass
class Position:
    """2D 위치 좌표"""
    x: float
    y: float

    def distance_to(self, other: 'Position') -> float:
        """다른 위치까지의 거리 계산"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class Address:
    """OHT 레일 주소 포인트"""
    id: int
    position: Position
    next_addresses: List[int] = field(default_factory=list)
    is_junction: bool = False  # 분기점 여부
    speed_limit: int = 15  # 속도 제한 (1-32 인덱스)


@dataclass
class Lane:
    """레일 구간"""
    id: int
    start_address: int
    end_address: int
    length: float  # mm 단위
    is_active: bool = True
    is_bidirectional: bool = False
    max_vehicles: int = 1  # 동시 진입 가능 차량 수


@dataclass
class Station:
    """로딩/언로딩 스테이션"""
    id: int
    name: str
    position: Position
    station_type: StationType
    address_id: int  # 연결된 주소 ID
    is_available: bool = True
    has_foup: bool = False  # FOUP 존재 여부
    equipment_id: Optional[str] = None  # 연결된 장비 ID


@dataclass
class Vehicle:
    """OHT 차량"""
    id: int
    name: str
    state: VehicleState = VehicleState.IDLE
    position: Position = field(default_factory=lambda: Position(0, 0))
    current_address: int = 0
    target_address: Optional[int] = None
    speed: float = 0.0  # m/min
    max_speed: float = 200.0  # m/min (CLW07-2 기준)
    has_foup: bool = False
    current_job: Optional[int] = None
    battery_level: float = 100.0

    # 시뮬레이션용 추가 필드
    path: List[int] = field(default_factory=list)
    path_index: int = 0


@dataclass
class TransportJob:
    """이송 작업"""
    id: int
    source_station: int
    dest_station: int
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    assigned_vehicle: Optional[int] = None
    carrier_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    is_hotlot: bool = False
    timeout: float = 120.0  # 초 (HotLot 기본 120초)


@dataclass
class Route:
    """경로 정의"""
    name: str
    addresses: List[int]
    stations: List[int]
    user: str
    date: str
    learn_start_address: int
    learn_end_address: int


@dataclass
class SimulationConfig:
    """시뮬레이션 설정"""
    # 시스템 용량 (M14 OHT2 기준)
    max_vehicles: int = 2000
    max_stations: int = 23000
    max_jobs: int = 4000

    # 스케줄러 설정
    sch_mode: int = 3  # 동적 최적화 모드
    sch_mode_interval: int = 100  # ms
    hotlot_priority: int = 99
    hotlot_timeout: int = 120  # 초

    # 충돌 방지 거리 (mm)
    bump_distance: float = 19932
    dispatch_distance: float = 5779
    branch_distance: float = 4929

    # 통신 설정
    communication_timeout: int = 30000  # ms
    status_report_interval: int = 10000  # ms

    # 레이아웃 파라미터
    layout_width: float = 11389
    layout_height: float = 4769
    scale: float = 30.0
    junction_entry_offset: float = 1900  # mm
    junction_exit_offset: float = 900  # mm


# 속도 테이블 (CLW07-2 기준, 인덱스 -> m/min)
SPEED_TABLE = {
    1: 1.5, 2: 3, 3: 5, 4: 10, 5: 15,
    6: 20, 7: 25, 8: 30, 9: 35, 10: 40,
    11: 45, 12: 50, 13: 55, 14: 60, 15: 65,
    16: 70, 17: 75, 18: 80, 19: 90, 20: 100,
    21: 110, 22: 120, 23: 130, 24: 140, 25: 150,
    26: 160, 27: 170, 28: 180, 29: 190, 30: 200,
    31: 200, 32: 200
}

# 곡선 반경별 속도 (진입, 곡선, 출구)
CURVE_SPEEDS = {
    400: (8, 8, 13),
    450: (16, 14, 16),
    500: (11, 11, 17),
    600: (11, 11, 14),
}
