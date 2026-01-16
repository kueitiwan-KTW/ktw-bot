"""
FISH 主程式
定時輪詢 OTA 後台，監控房況變化。
"""

import asyncio
from datetime import date, timedelta
from pathlib import Path
from typing import Dict

import yaml
from playwright.async_api import async_playwright

from .session_manager import SessionManager
from .platforms import AgodaPlatform, BookingPlatform
from .utils.logger import logger


class FISHMonitor:
    """OTA 房況監控器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.platforms: Dict[str, any] = {}
        self.session_managers: Dict[str, SessionManager] = {}
    
    def _load_config(self, config_path: str) -> dict:
        """載入設定檔"""
        config_file = Path(__file__).parent.parent / config_path
        
        if not config_file.exists():
            logger.error(f"設定檔不存在: {config_file}")
            logger.info("請複製 config.example.yaml 為 config.yaml 並填入設定")
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    async def initialize(self) -> None:
        """初始化平台連線"""
        logger.info("初始化 FISH Monitor...")
        
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
    
    async def run_once(self) -> None:
        """執行一次輪詢"""
        logger.info("=" * 50)
        logger.info("開始輪詢...")
        
        async with async_playwright() as playwright:
            for platform_name, platform in self.platforms.items():
                await self._poll_platform(playwright, platform_name, platform)
        
        logger.info("輪詢完成")
    
    async def _poll_platform(self, playwright, platform_name: str, platform) -> None:
        """輪詢單一平台"""
        logger.info(f"輪詢 {platform_name}...")
        
        session_mgr = self.session_managers[platform_name]
        
        try:
            # 取得已登入的 context
            context = await session_mgr.get_context(playwright)
            page = await context.new_page()
            platform.page = page
            
            # 導航到主頁
            await platform.navigate_to("/")
            await platform.wait_for_load()
            
            # 檢查是否已登入
            if not platform.is_logged_in():
                logger.warning(f"{platform_name} Session 已過期，嘗試重新登入...")
                if await session_mgr.auto_login(page):
                    await session_mgr.save_session(context)
                else:
                    logger.error(f"{platform_name} 自動登入失敗，請手動登入")
                    await context.close()
                    return
            
            # 取得房況
            today = date.today()
            end_date = today + timedelta(days=30)
            
            availability = await platform.get_availability(today, end_date)
            
            # 顯示房況摘要
            for room in availability[:5]:  # 只顯示前 5 筆
                logger.info(f"  {room.room_type} | {room.date} | 可訂: {room.available} | 價格: {room.price}")
            
            if len(availability) > 5:
                logger.info(f"  ... 還有 {len(availability) - 5} 筆")
            
            # 保存 session
            await session_mgr.save_session(context)
            await context.close()
            
        except Exception as e:
            logger.error(f"輪詢 {platform_name} 失敗: {e}")
    
    async def run_forever(self) -> None:
        """持續監控"""
        interval = self.config.get("polling", {}).get("interval_minutes", 5)
        logger.info(f"開始持續監控，每 {interval} 分鐘輪詢一次")
        logger.info("按 Ctrl+C 停止")
        
        while True:
            try:
                await self.run_once()
                logger.info(f"下次輪詢: {interval} 分鐘後")
                await asyncio.sleep(interval * 60)
            except KeyboardInterrupt:
                logger.info("收到停止訊號，結束監控")
                break
            except Exception as e:
                logger.error(f"輪詢發生錯誤: {e}")
                retry = self.config.get("polling", {}).get("retry_attempts", 3)
                logger.info(f"{retry} 秒後重試...")
                await asyncio.sleep(retry)


async def main():
    """主程式入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FISH - OTA 房況監控")
    parser.add_argument("--once", action="store_true", help="只執行一次")
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑")
    args = parser.parse_args()
    
    monitor = FISHMonitor(args.config)
    await monitor.initialize()
    
    if args.once:
        await monitor.run_once()
    else:
        await monitor.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
