"""
Booking.com Extranet 平台操作

注意：Booking.com 需要使用 persistent context 保存登入狀態
使用 user_data_dir 方式比 storage_state JSON 更穩定
"""

from datetime import date
from typing import List, Optional
import os

from playwright.async_api import async_playwright, BrowserContext, Page

from .base import BasePlatform, RoomAvailability, Booking
from ..utils.logger import logger


class BookingPlatform(BasePlatform):
    """Booking.com Extranet 平台操作"""
    
    PLATFORM_NAME = "booking"
    BASE_URL = "https://admin.booking.com"
    USER_DATA_DIR = "sessions/booking_profile"
    
    # 房型 ID 對照表
    ROOM_MAP = {
        "低奢兩人房": "211358301",
        "鄉村四人房": "211358302",
        "家庭六人房": "211358304",
    }
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.context: Optional[BrowserContext] = None
        self._playwright = None
        self._browser = None
    
    async def init_browser(self, headless: bool = True) -> None:
        """
        初始化瀏覽器（使用 persistent context）
        
        注意：Booking.com 的 session 只能用 persistent context 保存
        """
        os.makedirs(self.USER_DATA_DIR, exist_ok=True)
        
        self._playwright = await async_playwright().start()
        
        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.USER_DATA_DIR,
            headless=headless,
            locale='zh-TW',
            timezone_id='Asia/Taipei',
            viewport={'width': 1280, 'height': 800},
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        logger.info("Booking.com 瀏覽器已初始化 (persistent context)")
    
    async def close_browser(self) -> None:
        """關閉瀏覽器"""
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Booking.com 瀏覽器已關閉")
    
    def get_calendar_url(self) -> str:
        """取得日曆頁面 URL"""
        hotel_id = self.config.get("hotel_id", "2113583")
        return f"{self.BASE_URL}/hotel/hoteladmin/extranet_ng/manage/calendar/index.html?hotel_id={hotel_id}"
    
    async def navigate_to_calendar(self) -> bool:
        """導航到日曆頁面"""
        try:
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # 驗證是否在日曆頁面
            current_url = self.page.url
            if 'calendar' in current_url:
                logger.info("已導航到 Booking.com 日曆頁面")
                return True
            elif 'sign-in' in current_url:
                logger.error("需要登入 Booking.com")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"導航到日曆頁面失敗: {e}")
            return False
    
    async def select_room_type(self, room_id: str) -> bool:
        """
        選擇房型
        
        Args:
            room_id: 房型 ID（如 211358301）或房型名稱（如 低奢兩人房）
        """
        # 如果傳入的是名稱，轉換為 ID
        if room_id in self.ROOM_MAP:
            room_id = self.ROOM_MAP[room_id]
        
        logger.info(f"選擇房型: {room_id}")
        
        try:
            # Booking.com 使用 select 元素
            room_selector = self.page.locator('#room-selector-control')
            
            if await room_selector.count() > 0:
                await room_selector.select_option(value=room_id)
                await self.page.wait_for_timeout(1000)
                logger.info(f"已選擇房型: {room_id}")
                return True
            else:
                logger.error("找不到房型選擇器")
                return False
            
        except Exception as e:
            logger.error(f"選擇房型失敗: {e}")
            return False
    
    async def click_bulk_edit(self) -> bool:
        """點擊 Bulk edit 按鈕"""
        try:
            bulk_edit_btn = self.page.locator('button:has-text("Bulk edit")').first
            
            if await bulk_edit_btn.count() > 0:
                await bulk_edit_btn.click()
                await self.page.wait_for_timeout(1500)
                logger.info("已點擊 Bulk edit")
                return True
            else:
                logger.error("找不到 Bulk edit 按鈕")
                return False
            
        except Exception as e:
            logger.error(f"點擊 Bulk edit 失敗: {e}")
            return False
    
    async def set_date_range(self, start_date: date, end_date: date) -> bool:
        """
        設定日期範圍
        
        注意：Booking.com 的日期選擇器需要進一步分析
        """
        logger.info(f"設定日期範圍: {start_date} - {end_date}")
        
        try:
            # 找日期輸入框
            date_input = self.page.locator('input[type="text"]').first
            
            if await date_input.count() > 0:
                await date_input.click()
                await self.page.wait_for_timeout(1000)
                
                # TODO: 根據實際 DOM 結構完善日期選擇
                # Booking.com 可能有自定義日期選擇器
                
                logger.warning("日期選擇器需要進一步分析")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"設定日期範圍失敗: {e}")
            return False
    
    async def get_availability(self, start_date: date, end_date: date) -> List[RoomAvailability]:
        """取得房況"""
        logger.info(f"取得 Booking.com 房況: {start_date} ~ {end_date}")
        
        try:
            await self.navigate_to_calendar()
            
            availability = []
            
            # 解析日曆表格
            for room_name, room_id in self.ROOM_MAP.items():
                await self.select_room_type(room_id)
                await self.page.wait_for_timeout(1000)
                
                # TODO: 解析日曆表格資料
                
            logger.warning("Booking.com get_availability 尚未完整實作")
            return availability
            
        except Exception as e:
            logger.error(f"取得房況失敗: {e}")
            return []
    
    async def update_price(self, room_type: str, target_date: date, price: float) -> bool:
        """更新房價"""
        logger.info(f"更新 Booking.com 房價: {room_type} / {target_date} = {price}")
        
        try:
            await self.navigate_to_calendar()
            await self.select_room_type(room_type)
            await self.click_bulk_edit()
            
            # TODO: 在 Bulk edit 彈窗中設定價格
            
            logger.warning("Booking.com update_price 尚未完整實作")
            return False
            
        except Exception as e:
            logger.error(f"更新房價失敗: {e}")
            return False
    
    async def update_inventory(self, room_type: str, target_date: date, count: int) -> bool:
        """更新庫存"""
        logger.info(f"更新 Booking.com 庫存: {room_type} / {target_date} = {count}")
        
        try:
            await self.navigate_to_calendar()
            await self.select_room_type(room_type)
            await self.click_bulk_edit()
            
            # TODO: 在 Bulk edit 彈窗中設定庫存
            
            logger.warning("Booking.com update_inventory 尚未完整實作")
            return False
            
        except Exception as e:
            logger.error(f"更新庫存失敗: {e}")
            return False
    
    async def set_room_status(self, room_type: str, start_date: date, end_date: date, 
                               status: str = "bookable") -> bool:
        """
        設定房型狀態
        
        Args:
            room_type: 房型 ID 或名稱
            start_date: 開始日期
            end_date: 結束日期
            status: bookable 或 not_bookable
        """
        logger.info(f"設定房型狀態: {room_type} / {start_date}-{end_date} = {status}")
        
        try:
            await self.navigate_to_calendar()
            await self.select_room_type(room_type)
            await self.click_bulk_edit()
            
            # TODO: 在 Bulk edit 彈窗中設定狀態
            
            logger.warning("Booking.com set_room_status 尚未完整實作")
            return False
            
        except Exception as e:
            logger.error(f"設定房型狀態失敗: {e}")
            return False
    
    async def get_bookings(self, start_date: date, end_date: date) -> List[Booking]:
        """取得訂單列表"""
        logger.info(f"取得 Booking.com 訂單: {start_date} ~ {end_date}")
        
        try:
            # 導航到訂單頁面
            hotel_id = self.config.get("hotel_id", "2113583")
            await self.page.goto(
                f"{self.BASE_URL}/hotel/hoteladmin/extranet_ng/manage/booking_list.html?hotel_id={hotel_id}"
            )
            await self.page.wait_for_load_state('networkidle')
            
            bookings = []
            
            # TODO: 解析訂單列表
            
            logger.warning("Booking.com get_bookings 尚未完整實作")
            return bookings
            
        except Exception as e:
            logger.error(f"取得訂單失敗: {e}")
            return []
    
    def is_logged_in(self) -> bool:
        """檢查是否已登入"""
        if not self.page:
            return False
        
        current_url = self.page.url
        return "extranet_ng" in current_url or "hoteladmin" in current_url
