"""
Booking.com Session Manager

負責管理 Booking.com 的登入狀態，包括：
- Keep-Alive 心跳保持 session 活躍
- 自動偵測 session 過期並重新登入
- 登入失敗時發送通知
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class BookingSessionManager:
    """Booking.com Session 管理器"""
    
    def __init__(
        self,
        platform,  # BookingPlatform instance
        keep_alive_interval_hours: int = 4,
        on_login_failed: Optional[Callable] = None
    ):
        """
        初始化 Session Manager
        
        Args:
            platform: BookingPlatform 實例
            keep_alive_interval_hours: Keep-Alive 間隔（預設 4 小時）
            on_login_failed: 登入失敗時的回調函數（用於發送通知）
        """
        self.platform = platform
        self.keep_alive_interval = timedelta(hours=keep_alive_interval_hours)
        self.on_login_failed = on_login_failed
        
        self._running = False
        self._last_keep_alive: Optional[datetime] = None
        self._keep_alive_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        """
        啟動 Session Manager
        
        1. 確保已登入
        2. 啟動 Keep-Alive daemon
        
        Returns:
            True: 啟動成功
            False: 啟動失敗（無法登入）
        """
        logger.info("啟動 Booking.com Session Manager...")
        
        # 確保已登入
        if not await self.platform.ensure_logged_in():
            logger.error("無法登入 Booking.com，Session Manager 啟動失敗")
            if self.on_login_failed:
                await self._notify_login_failed("初始登入失敗")
            return False
        
        # 啟動 Keep-Alive daemon
        self._running = True
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        
        logger.info("Booking.com Session Manager 已啟動")
        return True
    
    async def stop(self):
        """停止 Session Manager"""
        logger.info("停止 Booking.com Session Manager...")
        
        self._running = False
        
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Booking.com Session Manager 已停止")
    
    async def _keep_alive_loop(self):
        """Keep-Alive 守護循環"""
        logger.info(f"Keep-Alive daemon 已啟動，間隔: {self.keep_alive_interval}")
        
        while self._running:
            try:
                # 等待到下次 Keep-Alive 時間
                await asyncio.sleep(self.keep_alive_interval.total_seconds())
                
                if not self._running:
                    break
                
                # 執行 Keep-Alive
                logger.info("執行 Keep-Alive...")
                success = await self.platform.keep_alive()
                
                if success:
                    self._last_keep_alive = datetime.now()
                    logger.info(f"Keep-Alive 成功，下次: {datetime.now() + self.keep_alive_interval}")
                else:
                    # Keep-Alive 失敗，嘗試重新登入
                    logger.warning("Keep-Alive 失敗，嘗試重新登入...")
                    
                    if await self.platform.auto_login():
                        logger.info("重新登入成功")
                    else:
                        logger.error("重新登入失敗")
                        if self.on_login_failed:
                            await self._notify_login_failed("Keep-Alive 後重新登入失敗")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep-Alive 循環錯誤: {e}")
                await asyncio.sleep(60)  # 錯誤後等待 1 分鐘再試
    
    async def _notify_login_failed(self, reason: str):
        """發送登入失敗通知"""
        message = f"[Booking.com] 登入失敗: {reason}\n時間: {datetime.now()}"
        
        logger.error(message)
        
        if self.on_login_failed:
            try:
                if asyncio.iscoroutinefunction(self.on_login_failed):
                    await self.on_login_failed(message)
                else:
                    self.on_login_failed(message)
            except Exception as e:
                logger.error(f"發送通知失敗: {e}")
    
    @property
    def is_running(self) -> bool:
        """是否正在運行"""
        return self._running
    
    @property
    def last_keep_alive(self) -> Optional[datetime]:
        """上次 Keep-Alive 時間"""
        return self._last_keep_alive


# 使用範例
async def example_usage():
    """使用範例"""
    from .booking import BookingPlatform
    
    # 建立 platform
    platform = BookingPlatform({"hotel_id": "2113583"})
    await platform.init_browser(headless=True)
    
    # 定義登入失敗通知函數
    async def notify_login_failed(message: str):
        # TODO: 整合 LINE Bot 或其他通知管道
        print(f"[通知] {message}")
    
    # 建立 Session Manager
    manager = BookingSessionManager(
        platform=platform,
        keep_alive_interval_hours=4,
        on_login_failed=notify_login_failed
    )
    
    # 啟動
    if await manager.start():
        print("Session Manager 已啟動，按 Ctrl+C 停止")
        
        try:
            # 保持運行
            while manager.is_running:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            pass
        finally:
            await manager.stop()
            await platform.close_browser()


if __name__ == "__main__":
    asyncio.run(example_usage())
