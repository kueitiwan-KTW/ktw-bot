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
    
    # 房型名稱對照（用於 UI 顯示）
    ROOM_NAMES = {
        "211358301": "低奢兩人房",
        "211358302": "鄉村四人房", 
        "211358304": "家庭六人房",
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
            viewport={'width': 1280, 'height': 900},
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
    
    async def check_session_valid(self) -> bool:
        """
        檢查 session 是否有效
        
        Returns:
            True: session 有效，已登入
            False: session 過期，需要重新登入
        """
        try:
            # 訪問一個需要登入的頁面
            await self.page.goto(self.BASE_URL)
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            current_url = self.page.url
            
            # 如果被重定向到登入頁，則 session 過期
            if 'sign-in' in current_url or 'account.booking.com' in current_url:
                logger.warning("Booking.com session 已過期")
                return False
            
            # 如果在管理頁面，則 session 有效
            if 'extranet_ng' in current_url or 'hoteladmin' in current_url:
                logger.info("Booking.com session 有效")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"檢查 session 失敗: {e}")
            return False
    
    async def auto_login(self, email: str = None, password: str = None) -> bool:
        """
        自動登入 Booking.com
        
        Args:
            email: 登入郵箱（可從環境變數讀取）
            password: 登入密碼（可從環境變數讀取）
        
        Returns:
            True: 登入成功
            False: 登入失敗（可能需要 2FA 或其他原因）
        """
        import os
        
        email = email or os.getenv('BOOKING_EMAIL')
        password = password or os.getenv('BOOKING_PASSWORD')
        
        if not email or not password:
            logger.error("未設定 BOOKING_EMAIL 或 BOOKING_PASSWORD 環境變數")
            return False
        
        try:
            # 導航到登入頁
            await self.page.goto('https://account.booking.com/sign-in')
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # 輸入郵箱
            email_input = self.page.locator('input[type="email"], input[name="username"]').first
            if await email_input.count() > 0:
                await email_input.fill(email)
                await self.page.wait_for_timeout(500)
                
                # 點擊繼續
                continue_btn = self.page.locator('button[type="submit"], button:has-text("繼續")').first
                if await continue_btn.count() > 0:
                    await continue_btn.click()
                    await self.page.wait_for_timeout(2000)
            
            # 輸入密碼
            password_input = self.page.locator('input[type="password"]').first
            if await password_input.count() > 0:
                await password_input.fill(password)
                await self.page.wait_for_timeout(500)
                
                # 點擊登入
                login_btn = self.page.locator('button[type="submit"], button:has-text("登入")').first
                if await login_btn.count() > 0:
                    await login_btn.click()
                    await self.page.wait_for_timeout(5000)
            
            # 檢查是否登入成功
            current_url = self.page.url
            
            if 'extranet_ng' in current_url or 'hoteladmin' in current_url:
                logger.info("Booking.com 自動登入成功")
                return True
            elif '2fa' in current_url or 'verify' in current_url:
                logger.warning("Booking.com 需要 2FA 驗證，無法自動完成")
                return False
            else:
                logger.warning(f"Booking.com 登入狀態不明: {current_url}")
                return False
            
        except Exception as e:
            logger.error(f"自動登入失敗: {e}")
            return False
    
    async def ensure_logged_in(self) -> bool:
        """
        確保已登入（組合方法）
        
        1. 先檢查 session 是否有效
        2. 如果過期，嘗試自動登入
        
        Returns:
            True: 已登入（原本有效或自動登入成功）
            False: 未登入（自動登入失敗）
        """
        if await self.check_session_valid():
            return True
        
        logger.info("嘗試自動登入 Booking.com...")
        return await self.auto_login()
    
    async def keep_alive(self) -> bool:
        """
        發送心跳保持 session 活躍
        
        建議每 4 小時執行一次
        
        Returns:
            True: 心跳成功
            False: session 可能已過期
        """
        import random
        
        try:
            # 人類行為模擬：隨機延遲 1-5 秒
            await self.page.wait_for_timeout(random.randint(1000, 5000))
            
            # 訪問日曆頁面刷新 session
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            
            # 人類行為模擬：隨機等待 2-4 秒
            await self.page.wait_for_timeout(random.randint(2000, 4000))
            
            # 人類行為模擬：隨機滾動頁面
            await self.page.evaluate(f'''() => {{
                window.scrollTo(0, {random.randint(100, 300)});
            }}''')
            await self.page.wait_for_timeout(random.randint(500, 1500))
            
            current_url = self.page.url
            
            if 'calendar' in current_url:
                logger.info("Booking.com Keep-Alive 成功")
                return True
            elif 'sign-in' in current_url:
                logger.warning("Booking.com Keep-Alive 失敗，session 已過期")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Keep-Alive 失敗: {e}")
            return False


    def get_calendar_url(self, lang: str = "xt") -> str:
        """取得日曆頁面 URL（繁體中文版）"""
        hotel_id = self.config.get("hotel_id", "2113583")
        return f"{self.BASE_URL}/hotel/hoteladmin/extranet_ng/manage/calendar/index.html?hotel_id={hotel_id}&lang={lang}"
    
    async def navigate_to_calendar(self) -> bool:
        """導航到日曆頁面"""
        try:
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
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
    
    async def open_group_edit(self, room_id: str = None) -> bool:
        """
        開啟群組編輯彈窗
        
        Args:
            room_id: 房型 ID（可選），如果指定會嘗試開啟該房型的群組編輯
        """
        try:
            # 點擊群組編輯按鈕
            group_btn = self.page.locator('button:has-text("群組編輯")').first
            
            if await group_btn.count() > 0:
                await group_btn.click()
                await self.page.wait_for_timeout(2000)
                logger.info("已開啟群組編輯彈窗")
                return True
            else:
                logger.error("找不到群組編輯按鈕")
                return False
            
        except Exception as e:
            logger.error(f"開啟群組編輯失敗: {e}")
            return False
    
    async def _click_section_by_text(self, text: str) -> bool:
        """使用 JavaScript 點擊彈窗內指定文字的區塊"""
        clicked = await self.page.evaluate(f'''() => {{
            const modal = document.querySelector('[data-test-id="general-modal"]');
            if (modal) {{
                const btns = modal.querySelectorAll('button.cec0620c60');
                for (const btn of btns) {{
                    if (btn.innerText?.includes("{text}")) {{
                        btn.click();
                        return true;
                    }}
                }}
            }}
            return false;
        }}''')
        return clicked

    async def _click_save_button(self) -> bool:
        """點擊彈窗內的儲存變更按鈕"""
        clicked = await self.page.evaluate('''() => {
            const modal = document.querySelector('[data-test-id="general-modal"]');
            if (modal) {
                const btns = modal.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText?.includes("儲存變更")) {
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        if clicked:
            await self.page.wait_for_timeout(2000)
        return clicked

    async def _get_modal_locator(self):
        """取得群組編輯彈窗的 locator"""
        return self.page.locator('[data-test-id="general-modal"]').last


    async def set_date_range_in_group_edit(self, start_date: date, end_date: date) -> bool:
        """
        在群組編輯彈窗中設定日期範圍
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
        """
        try:
            # 設定起始日
            start_input = self.page.locator('input[value*="2026"]').first
            if await start_input.count() > 0:
                await start_input.fill(start_date.strftime('%Y-%m-%d'))
                await self.page.wait_for_timeout(500)
            
            # 設定截止日
            end_input = self.page.locator('input[value*="2026"]').nth(1)
            if await end_input.count() > 0:
                await end_input.fill(end_date.strftime('%Y-%m-%d'))
                await self.page.wait_for_timeout(500)
            
            logger.info(f"已設定日期範圍: {start_date} ~ {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"設定日期範圍失敗: {e}")
            return False
    
    async def expand_price_section(self) -> bool:
        """展開價格區塊"""
        try:
            price_btn = self.page.locator('button:has-text("價格")').first
            if await price_btn.count() > 0:
                await price_btn.click()
                await self.page.wait_for_timeout(1000)
                logger.info("已展開價格區塊")
                return True
            else:
                logger.warning("找不到價格區塊按鈕")
                return False
            
        except Exception as e:
            logger.error(f"展開價格區塊失敗: {e}")
            return False
    
    async def set_price(self, price: float, rate_plan: str = "Standard Rate") -> bool:
        """
        設定房價
        
        Args:
            price: 價格（TWD）
            rate_plan: 房價方案名稱（預設 Standard Rate）
        """
        try:
            # 選擇房價方案
            rate_select = self.page.locator('select').filter(has_text='Standard Rate').first
            if await rate_select.count() > 0:
                await rate_select.select_option(label=rate_plan)
                await self.page.wait_for_timeout(1000)
            
            # 輸入價格（找 TWD 旁邊的輸入框）
            price_input = self.page.locator('input[type="text"]').filter(has=self.page.locator('text=TWD'))
            if await price_input.count() == 0:
                # 備用方式：找數字輸入框
                price_input = self.page.locator('input[type="number"]').first
            
            if await price_input.count() > 0:
                await price_input.fill(str(int(price)))
                await self.page.wait_for_timeout(500)
                logger.info(f"已設定價格: TWD {price}")
                return True
            else:
                logger.error("找不到價格輸入框")
                return False
            
        except Exception as e:
            logger.error(f"設定價格失敗: {e}")
            return False
    
    async def expand_inventory_section(self) -> bool:
        """展開可售數量區塊"""
        try:
            inventory_btn = self.page.locator('button:has-text("可售數量")').first
            if await inventory_btn.count() > 0:
                await inventory_btn.click()
                await self.page.wait_for_timeout(1000)
                logger.info("已展開可售數量區塊")
                return True
            else:
                logger.warning("找不到可售數量區塊按鈕")
                return False
            
        except Exception as e:
            logger.error(f"展開可售數量區塊失敗: {e}")
            return False
    
    async def set_inventory(self, count: int) -> bool:
        """
        設定可售房量
        
        Args:
            count: 可售房間數
        """
        try:
            # 找數字輸入框
            inventory_input = self.page.locator('input[type="number"]').first
            
            if await inventory_input.count() > 0:
                await inventory_input.fill(str(count))
                await self.page.wait_for_timeout(500)
                logger.info(f"已設定可售數量: {count}")
                return True
            else:
                logger.error("找不到可售數量輸入框")
                return False
            
        except Exception as e:
            logger.error(f"設定可售數量失敗: {e}")
            return False
    
    async def expand_status_section(self) -> bool:
        """展開房況區塊"""
        try:
            status_btn = self.page.locator('button:has-text("房況")').first
            if await status_btn.count() > 0:
                await status_btn.click()
                await self.page.wait_for_timeout(1000)
                logger.info("已展開房況區塊")
                return True
            else:
                logger.warning("找不到房況區塊按鈕")
                return False
            
        except Exception as e:
            logger.error(f"展開房況區塊失敗: {e}")
            return False
    
    async def set_room_status(self, status: str = "open") -> bool:
        """
        設定房型狀態
        
        Args:
            status: "open" 開放 或 "close" 關閉
        """
        try:
            if status == "open":
                open_btn = self.page.locator('text=開放').first
                if await open_btn.count() > 0:
                    await open_btn.click()
            else:
                close_btn = self.page.locator('text=關閉').first
                if await close_btn.count() > 0:
                    await close_btn.click()
            
            await self.page.wait_for_timeout(500)
            logger.info(f"已設定房況: {status}")
            return True
            
        except Exception as e:
            logger.error(f"設定房況失敗: {e}")
            return False
    
    async def save_group_edit(self) -> bool:
        """儲存群組編輯變更"""
        try:
            save_btn = self.page.locator('button:has-text("儲存變更")').first
            
            if await save_btn.count() > 0:
                await save_btn.click()
                await self.page.wait_for_timeout(3000)
                logger.info("已儲存群組編輯變更")
                return True
            else:
                logger.error("找不到儲存變更按鈕")
                return False
            
        except Exception as e:
            logger.error(f"儲存變更失敗: {e}")
            return False
    
    async def cancel_group_edit(self) -> bool:
        """取消群組編輯"""
        try:
            cancel_btn = self.page.locator('button:has-text("取消")').first
            
            if await cancel_btn.count() > 0:
                await cancel_btn.click()
                await self.page.wait_for_timeout(1000)
                logger.info("已取消群組編輯")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"取消群組編輯失敗: {e}")
            return False
    
    async def batch_update(
        self,
        room_type: str,
        start_date: date,
        end_date: date,
        price: float = None,
        inventory: int = None,
        status: str = None
    ) -> bool:
        """
        批次更新房型資訊
        
        Args:
            room_type: 房型 ID 或名稱
            start_date: 開始日期
            end_date: 結束日期
            price: 價格（可選）
            inventory: 可售房量（可選）
            status: 房況 "open"/"close"（可選）
        """
        try:
            # 導航到日曆頁面
            if not await self.navigate_to_calendar():
                return False
            
            # 開啟群組編輯
            if not await self.open_group_edit():
                return False
            
            # 設定日期範圍
            await self.set_date_range_in_group_edit(start_date, end_date)
            
            # 設定價格
            if price is not None:
                await self.expand_price_section()
                await self.set_price(price)
            
            # 設定可售數量
            if inventory is not None:
                await self.expand_inventory_section()
                await self.set_inventory(inventory)
            
            # 設定房況
            if status is not None:
                await self.expand_status_section()
                await self.set_room_status(status)
            
            # 儲存變更
            await self.save_group_edit()
            
            logger.info(f"批次更新完成: {room_type} / {start_date} ~ {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"批次更新失敗: {e}")
            return False
    
    # 以下為基類抽象方法的實作
    
    async def get_availability(self, start_date: date, end_date: date) -> List[RoomAvailability]:
        """取得房況"""
        logger.info(f"取得 Booking.com 房況: {start_date} ~ {end_date}")
        
        try:
            await self.navigate_to_calendar()
            
            availability = []
            # TODO: 解析日曆表格取得房況資料
            
            logger.warning("Booking.com get_availability 尚未完整實作")
            return availability
            
        except Exception as e:
            logger.error(f"取得房況失敗: {e}")
            return []
    
    async def update_price(self, room_type: str, target_date: date, price: float) -> bool:
        """更新房價"""
        return await self.batch_update(
            room_type=room_type,
            start_date=target_date,
            end_date=target_date,
            price=price
        )
    
    async def update_inventory(self, room_type: str, target_date: date, count: int) -> bool:
        """更新庫存"""
        return await self.batch_update(
            room_type=room_type,
            start_date=target_date,
            end_date=target_date,
            inventory=count
        )
    
    async def get_bookings(self, start_date: date, end_date: date) -> List[Booking]:
        """取得訂單列表"""
        logger.info(f"取得 Booking.com 訂單: {start_date} ~ {end_date}")
        
        try:
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
