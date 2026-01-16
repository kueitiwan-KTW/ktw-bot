"""
Agoda YCS 平台操作
基於 2026-01-16 分析的 DOM 結構
"""

from datetime import date, timedelta
from typing import List, Optional, Dict

from .base import BasePlatform, RoomAvailability, Booking
from ..utils.logger import logger


class AgodaPlatform(BasePlatform):
    """Agoda YCS 平台操作"""
    
    PLATFORM_NAME = "agoda"
    BASE_URL = "https://ycs.agoda.com"
    
    # 選擇器 (基於 2026-01-16 DOM 分析)
    SELECTORS = {
        "room_filter_button": '[data-testid="ycs-calendar-page-room-filter-button"]',
        "date_range_input": '#calendar-date-range-picker-input',
        "status_radio_open": 'input[type="radio"]:nth-of-type(1)',
        "status_radio_close": 'input[type="radio"]:nth-of-type(2)',
        "daily_inventory_input": 'input[type="number"]:nth-of-type(1)',
        "price_input": 'input[type="number"]:nth-of-type(2)',
        "calendar_cell": '[data-testid*="calendar-cell"], .calendar-day',
        "save_button": 'button[type="submit"], [data-testid*="save"]',
    }
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.property_id = config.get("property_id", "1615175")
    
    def get_calendar_url(self) -> str:
        """取得日曆頁面 URL"""
        return f"{self.BASE_URL}/mldc/zh-tw/app/ari/calendar/{self.property_id}"
    
    async def get_availability(self, start_date: date, end_date: date) -> List[RoomAvailability]:
        """取得房況"""
        logger.info(f"取得 Agoda 房況: {start_date} ~ {end_date}")
        
        try:
            # 導航到日曆頁面
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            availability = []
            
            # 取得當前選中的房型名稱
            room_button = await self.page.query_selector(self.SELECTORS["room_filter_button"])
            current_room = ""
            if room_button:
                current_room = await room_button.get_attribute("label") or ""
                logger.info(f"當前房型: {current_room}")
            
            # 取得右側面板的資訊
            panel_data = await self._extract_panel_data()
            
            if panel_data:
                # 取得選中的日期 (從日期輸入框)
                date_input = await self.page.query_selector(self.SELECTORS["date_range_input"])
                selected_date_str = ""
                if date_input:
                    selected_date_str = await date_input.get_attribute("value") or ""
                
                availability.append(RoomAvailability(
                    room_type=current_room,
                    date=start_date,  # 使用開始日期，實際應該解析選中日期
                    available=panel_data.get("inventory", 0),
                    price=panel_data.get("price"),
                    currency="TWD"
                ))
            
            logger.info(f"取得 {len(availability)} 筆房況資料")
            return availability
            
        except Exception as e:
            logger.error(f"取得房況失敗: {e}")
            return []
    
    async def _extract_panel_data(self) -> Dict:
        """從右側面板提取資料"""
        try:
            data = await self.page.evaluate('''() => {
                const result = {inventory: null, price: null, status: null};
                
                // 找所有 number 輸入框
                const numberInputs = document.querySelectorAll('input[type="number"]');
                if (numberInputs.length >= 1) {
                    result.inventory = parseInt(numberInputs[0].value) || null;
                }
                if (numberInputs.length >= 2) {
                    result.price = parseFloat(numberInputs[1].value) || null;
                }
                
                // 找 radio button 狀態
                const radioInputs = document.querySelectorAll('input[type="radio"]');
                for (const radio of radioInputs) {
                    if (radio.checked) {
                        // 嘗試找鄰近的 label
                        const label = radio.closest('label') || radio.nextElementSibling;
                        result.status = label?.innerText || 'unknown';
                        break;
                    }
                }
                
                return result;
            }''')
            
            logger.info(f"面板資料: {data}")
            return data
            
        except Exception as e:
            logger.error(f"提取面板資料失敗: {e}")
            return {}
    
    async def select_room_type(self, room_ids: list[str]) -> bool:
        """
        選擇指定房型（支援多選）
        
        Agoda 房型選擇器邏輯:
        1. 預設選中「選取全部」(包含所有房型)
        2. 要選指定房型需要:
           - 點擊「選取全部」2 次清空所有選擇
           - 使用 React controlled checkbox 方式選中目標房型
           - 點擊「套用」按鈕
        
        Args:
            room_ids: 房型 ID 列表，例如 ['9899987', '9900054']
        """
        logger.info(f"選擇房型: {room_ids}")
        
        try:
            from playwright.async_api import expect
            
            # 點擊房型選擇器按鈕
            room_button = self.page.get_by_test_id("ycs-calendar-page-room-filter-button")
            await room_button.click()
            await self.page.wait_for_timeout(1000)
            
            # 用 checkbox[0] + React setter 清空所有選擇
            # 第 1 次點擊：如果未全選則全選，如果已全選則取消
            # 第 2 次點擊：確保清空所有選擇
            for _ in range(2):
                await self.page.evaluate("""() => {
                    const checkboxes = document.querySelectorAll('input[type=checkbox]');
                    if (checkboxes.length > 0) {
                        const selectAllCb = checkboxes[0];
                        const proto = selectAllCb.ownerDocument.defaultView.HTMLInputElement.prototype;
                        const desc = Object.getOwnPropertyDescriptor(proto, 'checked');
                        const newValue = !selectAllCb.checked;
                        desc.set.call(selectAllCb, newValue);
                        selectAllCb.dispatchEvent(new Event('input', { bubbles: true }));
                        selectAllCb.dispatchEvent(new Event('change', { bubbles: true }));
                        selectAllCb.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                    }
                }""")
                await self.page.wait_for_timeout(500)
            
            # 使用 React controlled checkbox 方式選中目標房型
            for room_id in room_ids:
                result = await self.page.evaluate("""(roomId) => {
                    const lis = document.querySelectorAll('li');
                    for (const li of lis) {
                        if (li.innerText.includes(roomId)) {
                            const input = li.querySelector('input[type=checkbox]');
                            if (input) {
                                // React controlled input: use native setter + events
                                const proto = input.ownerDocument.defaultView.HTMLInputElement.prototype;
                                const desc = Object.getOwnPropertyDescriptor(proto, 'checked');
                                if (!input.checked) {
                                    desc.set.call(input, true);
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                    input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                                }
                                return {success: true, roomId: roomId, checked: input.checked};
                            } else {
                                li.click();
                                return {success: true, roomId: roomId, method: 'li-click'};
                            }
                        }
                    }
                    return {success: false, roomId: roomId, error: 'not found'};
                }""", room_id)
                
                logger.info(f"選擇房型 {room_id}: {result}")
                await self.page.wait_for_timeout(300)
            
            # 點擊「套用」按鈕
            apply_btn = self.page.locator('button:has-text("套用")')
            await apply_btn.click()
            await self.page.wait_for_timeout(1000)
            
            logger.info(f"已選擇房型: {room_ids}")
            return True
            
        except Exception as e:
            logger.error(f"選擇房型失敗: {e}")
            return False
    
    async def select_date_range(self, start_date: date, end_date: date) -> bool:
        """
        選擇日期範圍
        
        注意：Agoda 一次最多只能選半年的日期範圍
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
        """
        logger.info(f"選擇日期範圍: {start_date} - {end_date}")
        
        try:
            # 開啟日期選擇器
            date_input = self.page.get_by_test_id('ycs-calendar-page-dateselect-input')
            await date_input.click()
            await self.page.wait_for_timeout(1000)
            
            # 計算開始日期的 test id
            start_month = start_date.strftime("%B")  # e.g. "January"
            start_day = start_date.day
            start_year = start_date.year
            # 格式: January 16th, 2026
            day_suffix = "th" if 11 <= start_day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(start_day % 10, "th")
            start_selector = f'[data-testid*="{start_month} {start_day}{day_suffix}, {start_year}"]'
            
            # 取消當前選擇（點擊開始日期）
            start_btn = self.page.locator(start_selector)
            if await start_btn.count() > 0:
                await start_btn.click()
                await self.page.wait_for_timeout(300)
            
            # 選擇開始日期
            start_btn = self.page.locator(start_selector)
            if await start_btn.count() > 0:
                await start_btn.click()
                await self.page.wait_for_timeout(300)
                logger.info(f"選擇開始日期: {start_date}")
            
            # 計算需要翻幾個月
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            
            # 翻月
            if months_diff > 0:
                for _ in range(months_diff):
                    next_btn = self.page.locator('button[aria-label="Go to the Next Month"]')
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await self.page.wait_for_timeout(400)
            
            # 計算結束日期的 test id
            end_month = end_date.strftime("%B")
            end_day = end_date.day
            end_year = end_date.year
            day_suffix = "th" if 11 <= end_day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(end_day % 10, "th")
            end_selector = f'[data-testid*="{end_month} {end_day}{day_suffix}, {end_year}"]'
            
            # 選擇結束日期
            end_btn = self.page.locator(end_selector)
            if await end_btn.count() > 0:
                await end_btn.click()
                await self.page.wait_for_timeout(300)
                logger.info(f"選擇結束日期: {end_date}")
            
            # 套用
            await self.page.locator('button:has-text("套用")').click()
            await self.page.wait_for_timeout(1000)
            
            logger.info(f"已選擇日期範圍: {start_date} - {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"選擇日期範圍失敗: {e}")
            return False
    
    async def update_price(self, room_type: str, target_date: date, price: float) -> bool:
        """更新房價"""
        logger.info(f"更新 Agoda 房價: {room_type} / {target_date} = {price}")
        
        try:
            # 導航到日曆頁面
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # 選擇房型
            await self.select_room_type(room_type)
            
            # 選擇日期
            await self.select_date(target_date)
            
            # 找到價格輸入框並填入
            price_inputs = await self.page.query_selector_all('input[type="number"]')
            if len(price_inputs) >= 2:
                price_input = price_inputs[1]  # 第二個 number input 是價格
                await price_input.fill(str(int(price)))
                logger.info(f"已填入價格: {price}")
                
                # 等待自動儲存或點擊儲存按鈕
                await self.page.wait_for_timeout(1000)
                return True
            
            logger.warning("找不到價格輸入框")
            return False
            
        except Exception as e:
            logger.error(f"更新房價失敗: {e}")
            return False
    
    async def update_inventory(self, room_type: str, target_date: date, count: int) -> bool:
        """更新庫存"""
        logger.info(f"更新 Agoda 庫存: {room_type} / {target_date} = {count}")
        
        try:
            # 導航到日曆頁面
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # 選擇房型
            await self.select_room_type(room_type)
            
            # 選擇日期
            await self.select_date(target_date)
            
            # 找到庫存輸入框並填入
            number_inputs = await self.page.query_selector_all('input[type="number"]')
            if len(number_inputs) >= 1:
                inventory_input = number_inputs[0]  # 第一個 number input 是庫存
                await inventory_input.fill(str(count))
                logger.info(f"已填入庫存: {count}")
                
                # 等待自動儲存
                await self.page.wait_for_timeout(1000)
                return True
            
            logger.warning("找不到庫存輸入框")
            return False
            
        except Exception as e:
            logger.error(f"更新庫存失敗: {e}")
            return False
    
    async def get_bookings(self, start_date: date, end_date: date) -> List[Booking]:
        """取得訂單列表"""
        logger.info(f"取得 Agoda 訂單: {start_date} ~ {end_date}")
        
        try:
            # 導航到訂單頁面
            await self.page.goto(f"{self.BASE_URL}/mldc/zh-tw/app/bookings/{self.property_id}")
            await self.page.wait_for_load_state('networkidle')
            
            bookings = []
            
            # TODO: 根據實際 DOM 結構解析訂單
            logger.warning("get_bookings 尚未完整實作")
            return bookings
            
        except Exception as e:
            logger.error(f"取得訂單失敗: {e}")
            return []
    
    def is_logged_in(self) -> bool:
        """檢查是否已登入"""
        if not self.page:
            return False
        
        current_url = self.page.url
        # 已登入時 URL 不會包含 login
        return "login" not in current_url.lower() and "signin" not in current_url.lower()
    
    async def set_room_status(self, room_type: str, target_date: date, is_open: bool) -> bool:
        """
        設定房型開放/關閉狀態
        
        Args:
            room_type: 房型名稱
            target_date: 目標日期
            is_open: True=開放, False=關閉
        
        Returns:
            是否成功
        """
        status_text = "開放" if is_open else "關閉"
        logger.info(f"設定 Agoda 房型狀態: {room_type} / {target_date} = {status_text}")
        
        try:
            # 導航到日曆頁面
            await self.page.goto(self.get_calendar_url())
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # 選擇房型
            await self.select_room_type(room_type)
            
            # 選擇日期
            await self.select_date(target_date)
            
            # 點擊對應的 radio button
            if is_open:
                # 開放 - data-testid="open-room-radio-button-{room_id}"
                open_radio = await self.page.query_selector('[data-testid*="open-room-radio-button"]')
                if open_radio:
                    await open_radio.click()
                    await self.page.wait_for_timeout(500)
                    logger.info(f"已設定為: 開放")
            else:
                # 關閉 - data-testid="close-room-radio-button-{room_id}"
                close_radio = await self.page.query_selector('[data-testid*="close-room-radio-button"]')
                if close_radio:
                    await close_radio.click()
                    await self.page.wait_for_timeout(500)
                    logger.info(f"已設定為: 關閉")
            
            # 點擊更新按鈕
            update_btn = await self.page.query_selector('[data-testid="ycs-calendar-update-button"]')
            if update_btn:
                await update_btn.click()
                await self.page.wait_for_timeout(1000)
                logger.info("已點擊更新按鈕")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"設定房型狀態失敗: {e}")
            return False
    
    async def close_room(self, room_type: str, target_date: date) -> bool:
        """關閉房型 (不可預訂)"""
        return await self.set_room_status(room_type, target_date, is_open=False)
    
    async def open_room(self, room_type: str, target_date: date) -> bool:
        """開放房型 (可預訂)"""
        return await self.set_room_status(room_type, target_date, is_open=True)

