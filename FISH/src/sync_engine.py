"""
庫存同步引擎
負責跨平台 (Agoda, Booking.com 等) 庫存同步
"""

import asyncio
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import yaml
from playwright.async_api import async_playwright

from .platforms.agoda import AgodaPlatform
from .platforms.booking import BookingPlatform
from .session_manager import SessionManager
from .utils.logger import logger


@dataclass
class RoomState:
    """房型狀態"""
    name: str
    total: int              # 總房數
    sold: int = 0           # 已售出
    available: int = 0      # 可用房數
    agoda_id: str = ""
    booking_id: str = ""
    
    def __post_init__(self):
        if self.available == 0:
            self.available = self.total - self.sold


@dataclass
class InventoryState:
    """整體庫存狀態"""
    last_sync: str = ""
    rooms: Dict[str, RoomState] = field(default_factory=dict)


class InventorySyncEngine:
    """跨平台庫存同步引擎"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.state_file = Path(__file__).parent.parent / "inventory_state.yaml"
        self.state: Optional[InventoryState] = None
        
        # 平台實例
        self.platforms: Dict[str, any] = {}
        self.session_managers: Dict[str, SessionManager] = {}
    
    def _load_config(self, config_path: str) -> dict:
        """載入設定檔"""
        config_file = Path(__file__).parent.parent / config_path
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}
    
    def load_state(self) -> InventoryState:
        """載入庫存狀態"""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            state = InventoryState(last_sync=data.get("last_sync", ""))
            
            for room_id, room_data in data.get("rooms", {}).items():
                state.rooms[room_id] = RoomState(
                    name=room_data.get("name", room_id),
                    total=room_data.get("total", 0),
                    sold=room_data.get("sold", 0),
                    available=room_data.get("available", 0),
                    agoda_id=room_data.get("agoda_id", ""),
                    booking_id=room_data.get("booking_id", "")
                )
            
            logger.info(f"載入庫存狀態: {len(state.rooms)} 個房型")
            return state
        
        # 首次運行，從 room_config 初始化
        return self._init_state_from_config()
    
    def _init_state_from_config(self) -> InventoryState:
        """從 room_config.yaml 初始化狀態"""
        room_config_file = Path(__file__).parent.parent / "room_config.yaml"
        
        state = InventoryState()
        
        if room_config_file.exists():
            with open(room_config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            for room_id, room_data in data.get("room_types", {}).items():
                state.rooms[room_id] = RoomState(
                    name=room_data.get("name", room_id),
                    total=room_data.get("base_inventory", 0),
                    sold=0,
                    agoda_id=room_data.get("agoda_room_id", ""),
                    booking_id=room_data.get("booking_room_id", "")
                )
            
            logger.info(f"從 room_config 初始化: {len(state.rooms)} 個房型")
        
        return state
    
    def save_state(self) -> None:
        """保存庫存狀態"""
        data = {
            "last_sync": datetime.now().isoformat(),
            "rooms": {}
        }
        
        for room_id, room in self.state.rooms.items():
            data["rooms"][room_id] = {
                "name": room.name,
                "total": room.total,
                "sold": room.sold,
                "available": room.available,
                "agoda_id": room.agoda_id,
                "booking_id": room.booking_id
            }
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"狀態已保存至 {self.state_file}")
    
    async def initialize(self) -> None:
        """初始化平台連線"""
        logger.info("初始化同步引擎...")
        
        self.state = self.load_state()
        
        # 初始化 Agoda
        if self.config.get("agoda", {}).get("enabled"):
            agoda_config = self.config["agoda"]
            agoda_config["headless"] = self.config.get("browser", {}).get("headless", True)
            self.session_managers["agoda"] = SessionManager("agoda", agoda_config)
            self.platforms["agoda"] = AgodaPlatform(agoda_config)
            logger.info("Agoda 平台已初始化")
        
        # 初始化 Booking.com
        if self.config.get("booking", {}).get("enabled"):
            booking_config = self.config["booking"]
            booking_config["headless"] = self.config.get("browser", {}).get("headless", True)
            self.session_managers["booking"] = SessionManager("booking", booking_config)
            self.platforms["booking"] = BookingPlatform(booking_config)
            logger.info("Booking.com 平台已初始化")
    
    async def sync_cycle(self) -> None:
        """執行一次同步週期"""
        logger.info("=" * 50)
        logger.info("開始同步週期...")
        
        async with async_playwright() as playwright:
            # 收集各平台當前庫存
            platform_inventories = {}
            
            for platform_name, platform in self.platforms.items():
                try:
                    inventory = await self._get_platform_inventory(
                        playwright, platform_name, platform
                    )
                    platform_inventories[platform_name] = inventory
                except Exception as e:
                    logger.error(f"取得 {platform_name} 庫存失敗: {e}")
            
            # 比對差異並同步
            await self._sync_inventories(playwright, platform_inventories)
        
        # 保存狀態
        self.save_state()
        logger.info("同步週期完成")
    
    async def _get_platform_inventory(
        self,
        playwright,
        platform_name: str,
        platform
    ) -> Dict[str, int]:
        """取得指定平台的庫存"""
        inventory = {}
        
        session_mgr = self.session_managers[platform_name]
        context = await session_mgr.get_context(playwright)
        page = await context.new_page()
        platform.page = page
        
        # 取得房況
        today = date.today()
        availability = await platform.get_availability(today, today + timedelta(days=1))
        
        for room in availability:
            # 找到對應的 room_id
            for room_id, room_state in self.state.rooms.items():
                if room.room_type == room_state.name:
                    inventory[room_id] = room.available
                    break
        
        await session_mgr.save_session(context)
        await context.close()
        
        return inventory
    
    async def _sync_inventories(
        self,
        playwright,
        platform_inventories: Dict[str, Dict[str, int]]
    ) -> None:
        """比對並同步庫存"""
        
        for room_id, room in self.state.rooms.items():
            # 收集各平台的庫存
            inventories = {}
            for platform_name, inv in platform_inventories.items():
                if room_id in inv:
                    inventories[platform_name] = inv[room_id]
            
            if not inventories:
                continue
            
            # 找出最小值 (最新的可用數)
            min_available = min(inventories.values())
            
            # 如果有平台庫存減少，更新其他平台
            if min_available < room.available:
                sold = room.available - min_available
                
                # 找出是哪個平台賣的
                for pname, pinv in inventories.items():
                    if pinv == min_available:
                        logger.info(f"偵測到 {pname} 賣出 {sold} 間 {room.name}")
                        break
                
                # 更新中央狀態
                room.sold += sold
                room.available = min_available
                
                # 同步到其他平台
                for platform_name, platform in self.platforms.items():
                    if inventories.get(platform_name, 0) > min_available:
                        logger.info(f"同步 {room.name} 到 {platform_name}: {min_available}")
                        await self._update_platform_inventory(
                            playwright, platform_name, room_id, min_available
                        )
    
    async def _update_platform_inventory(
        self,
        playwright,
        platform_name: str,
        room_id: str,
        new_count: int
    ) -> None:
        """更新指定平台的庫存"""
        platform = self.platforms.get(platform_name)
        session_mgr = self.session_managers.get(platform_name)
        
        if not platform or not session_mgr:
            return
        
        context = await session_mgr.get_context(playwright)
        page = await context.new_page()
        platform.page = page
        
        room = self.state.rooms.get(room_id)
        if room:
            today = date.today()
            await platform.update_inventory(room.name, today, new_count)
        
        await session_mgr.save_session(context)
        await context.close()
    
    async def run_forever(self, interval_minutes: int = 5) -> None:
        """持續同步"""
        logger.info(f"開始持續同步，每 {interval_minutes} 分鐘同步一次")
        
        while True:
            try:
                await self.sync_cycle()
                logger.info(f"下次同步: {interval_minutes} 分鐘後")
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("收到停止訊號")
                break
            except Exception as e:
                logger.error(f"同步錯誤: {e}")
                await asyncio.sleep(60)  # 錯誤後等 1 分鐘再試
    
    def print_status(self) -> None:
        """印出當前狀態"""
        print("\n" + "=" * 50)
        print("📊 庫存狀態")
        print("=" * 50)
        
        for room_id, room in self.state.rooms.items():
            print(f"\n🏨 {room.name} (ID: {room_id})")
            print(f"   總房數: {room.total}")
            print(f"   已售出: {room.sold}")
            print(f"   可用: {room.available}")
        
        print("\n" + "=" * 50)


# CLI 入口
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="FISH 庫存同步引擎")
    parser.add_argument("--once", action="store_true", help="只同步一次")
    parser.add_argument("--status", action="store_true", help="顯示狀態")
    parser.add_argument("--init", action="store_true", help="初始化狀態")
    args = parser.parse_args()
    
    engine = InventorySyncEngine()
    await engine.initialize()
    
    if args.status:
        engine.print_status()
    elif args.init:
        engine.save_state()
        engine.print_status()
    elif args.once:
        await engine.sync_cycle()
    else:
        await engine.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
