"""
Agoda YCS Session Manager

負責管理 Agoda YCS 的登入狀態，包括：
- Keep-Alive 心跳保持 session 活躍
- 自動偵測 session 過期並重新登入
- 登入失敗時發送通知
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AgodaSessionManager:
    """Agoda YCS Session 管理器"""
    
    def __init__(
        self,
        platform,  # AgodaPlatform instance
        keep_alive_interval_hours: int = 4,
        on_login_failed: Optional[Callable] = None
    ):
        """
        初始化 Session Manager
        
        Args:
            platform: AgodaPlatform 實例
            keep_alive_interval_hours: Keep-Alive 間隔（預設 4 小時）
            on_login_failed: 登入失敗時的回調函數
        """
        self.platform = platform
        self.keep_alive_interval = timedelta(hours=keep_alive_interval_hours)
        self.on_login_failed = on_login_failed
        
        self._running = False
        self._last_keep_alive: Optional[datetime] = None
        self._keep_alive_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        """啟動 Session Manager"""
        logger.info("啟動 Agoda YCS Session Manager...")
        
        if not await self.platform.ensure_logged_in():
            logger.error("無法登入 Agoda YCS，Session Manager 啟動失敗")
            if self.on_login_failed:
                await self._notify_login_failed("初始登入失敗")
            return False
        
        self._running = True
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        
        logger.info("Agoda YCS Session Manager 已啟動")
        return True
    
    async def stop(self):
        """停止 Session Manager"""
        logger.info("停止 Agoda YCS Session Manager...")
        
        self._running = False
        
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Agoda YCS Session Manager 已停止")
    
    async def _keep_alive_loop(self):
        """Keep-Alive 守護循環（含隨機化）"""
        base_interval = self.keep_alive_interval.total_seconds()
        logger.info(f"Keep-Alive daemon 已啟動，基礎間隔: {self.keep_alive_interval}")
        
        while self._running:
            try:
                # 隨機化間隔：基礎時間 ± 30 分鐘
                randomized_interval = base_interval + random.randint(-1800, 1800)
                logger.info(f"下次 Keep-Alive 將在 {randomized_interval/3600:.1f} 小時後")
                
                await asyncio.sleep(randomized_interval)
                
                if not self._running:
                    break
                
                logger.info("執行 Keep-Alive...")
                success = await self.platform.keep_alive()
                
                if success:
                    self._last_keep_alive = datetime.now()
                    logger.info("Keep-Alive 成功")
                else:
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
                await asyncio.sleep(60)
    
    async def _notify_login_failed(self, reason: str):
        """發送登入失敗通知"""
        message = f"[Agoda YCS] 登入失敗: {reason}\n時間: {datetime.now()}"
        
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
        return self._running
    
    @property
    def last_keep_alive(self) -> Optional[datetime]:
        return self._last_keep_alive
