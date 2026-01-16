"""
房型基準管理器
負責載入基準設定，並提供價格計算與比對功能。
"""

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import yaml

from .utils.logger import logger


@dataclass
class RoomTypeConfig:
    """房型設定"""
    id: str
    name: str
    platform_names: Dict[str, str]
    base_inventory: int
    base_prices: Dict[str, float]


class RoomConfigManager:
    """房型基準管理器"""
    
    def __init__(self, config_path: str = "room_config.yaml"):
        self.config_file = Path(__file__).parent.parent / config_path
        self.room_types: Dict[str, RoomTypeConfig] = {}
        self.holidays: List[date] = []
        self.special_dates: Dict[date, dict] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """載入設定檔"""
        if not self.config_file.exists():
            logger.warning(f"房型設定檔不存在: {self.config_file}")
            logger.info("請複製 room_config.example.yaml 為 room_config.yaml")
            return
        
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 載入房型
        for room_id, room_data in config.get("room_types", {}).items():
            self.room_types[room_id] = RoomTypeConfig(
                id=room_id,
                name=room_data.get("name", room_id),
                platform_names=room_data.get("platform_names", {}),
                base_inventory=room_data.get("base_inventory", 0),
                base_prices=room_data.get("base_prices", {})
            )
        
        # 載入假日
        for holiday_str in config.get("holidays", []):
            self.holidays.append(date.fromisoformat(holiday_str))
        
        # 載入特殊日期
        for date_str, settings in config.get("special_dates", {}).items():
            self.special_dates[date.fromisoformat(date_str)] = settings
        
        logger.info(f"已載入 {len(self.room_types)} 個房型設定")
    
    def get_base_price(self, room_id: str, target_date: date) -> Optional[float]:
        """取得指定房型在指定日期的基準價格"""
        if room_id not in self.room_types:
            return None
        
        room = self.room_types[room_id]
        prices = room.base_prices
        
        # 判斷是否為假日
        if target_date in self.holidays:
            base_price = prices.get("holiday", prices.get("weekday", 0))
        else:
            # 判斷星期
            weekday = target_date.weekday()
            if weekday == 4:      # 週五
                base_price = prices.get("friday", prices.get("weekday", 0))
            elif weekday == 5:    # 週六
                base_price = prices.get("saturday", prices.get("weekday", 0))
            elif weekday == 6:    # 週日
                base_price = prices.get("sunday", prices.get("weekday", 0))
            else:                 # 週一~週四
                base_price = prices.get("weekday", 0)
        
        # 套用特殊日期調整
        if target_date in self.special_dates:
            multiplier = self.special_dates[target_date].get("multiplier", 1.0)
            base_price *= multiplier
        
        return base_price
    
    def get_base_inventory(self, room_id: str) -> int:
        """取得指定房型的基準庫存"""
        if room_id not in self.room_types:
            return 0
        return self.room_types[room_id].base_inventory
    
    def get_platform_room_name(self, room_id: str, platform: str) -> Optional[str]:
        """取得房型在指定平台上的名稱"""
        if room_id not in self.room_types:
            return None
        return self.room_types[room_id].platform_names.get(platform)
    
    def find_room_by_platform_name(self, platform: str, platform_name: str) -> Optional[str]:
        """根據平台上的房型名稱，反查內部房型 ID"""
        for room_id, room in self.room_types.items():
            if room.platform_names.get(platform) == platform_name:
                return room_id
        return None
    
    def print_overview(self, start_date: date, days: int = 7) -> None:
        """印出房型基準總覽"""
        print("\n" + "=" * 70)
        print("📊 房型基準設定總覽")
        print("=" * 70)
        
        for room_id, room in self.room_types.items():
            print(f"\n🏨 {room.name} (ID: {room_id})")
            print(f"   基準庫存: {room.base_inventory} 間")
            print(f"   平台名稱: {room.platform_names}")
            print(f"   基準價格:")
            
            # 顯示未來幾天的價格
            for i in range(days):
                target_date = start_date + __import__("datetime").timedelta(days=i)
                price = self.get_base_price(room_id, target_date)
                weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
                weekday = weekday_names[target_date.weekday()]
                
                holiday_mark = "🎉" if target_date in self.holidays else ""
                special_mark = "⭐" if target_date in self.special_dates else ""
                
                print(f"      {target_date} (週{weekday}) {holiday_mark}{special_mark}: ${price:,.0f}")
        
        print("\n" + "=" * 70)


# CLI 入口
if __name__ == "__main__":
    from datetime import date
    
    manager = RoomConfigManager()
    manager.print_overview(date.today())
