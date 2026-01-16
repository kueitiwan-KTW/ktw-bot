"""
OTA 平台基底類別
定義所有平台操作的共同介面。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import date


@dataclass
class RoomAvailability:
    """房間可用性資料"""
    room_type: str          # 房型名稱
    date: date              # 日期
    available: int          # 可用房數
    price: Optional[float]  # 房價
    currency: str = "TWD"   # 幣別


@dataclass
class Booking:
    """訂單資料"""
    booking_id: str
    guest_name: str
    room_type: str
    check_in: date
    check_out: date
    total_price: float
    status: str


class BasePlatform(ABC):
    """OTA 平台基底類別"""
    
    def __init__(self, config: dict):
        self.config = config
        self.page = None
    
    @abstractmethod
    async def get_availability(self, start_date: date, end_date: date) -> List[RoomAvailability]:
        """取得指定日期範圍的房況"""
        pass
    
    @abstractmethod
    async def update_price(self, room_type: str, date: date, price: float) -> bool:
        """更新房價"""
        pass
    
    @abstractmethod
    async def update_inventory(self, room_type: str, date: date, count: int) -> bool:
        """更新庫存"""
        pass
    
    @abstractmethod
    async def get_bookings(self, start_date: date, end_date: date) -> List[Booking]:
        """取得訂單列表"""
        pass
    
    @abstractmethod
    def is_logged_in(self) -> bool:
        """檢查是否已登入"""
        pass
    
    async def navigate_to(self, path: str) -> None:
        """導航到指定路徑"""
        base_url = self.config.get("url", "").rstrip("/")
        await self.page.goto(f"{base_url}{path}")
    
    async def wait_for_load(self) -> None:
        """等待頁面載入完成"""
        await self.page.wait_for_load_state("networkidle")
