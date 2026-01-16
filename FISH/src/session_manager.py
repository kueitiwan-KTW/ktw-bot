"""
Session 管理器
負責管理 OTA 平台的登入 Session，支援持久化保存與自動重新登入。
"""

import asyncio
import argparse
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

from .utils.logger import logger


class SessionManager:
    """Session 管理器"""
    
    def __init__(self, platform: str, config: dict):
        self.platform = platform
        self.config = config
        self.session_dir = Path(__file__).parent.parent / "sessions"
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / f"{platform}_session.json"
    
    async def interactive_login(self) -> None:
        """互動式登入，手動完成後保存 Session"""
        logger.info(f"開始 {self.platform} 互動式登入...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            url = self.config.get("url", "")
            await page.goto(url)
            
            logger.info("請在瀏覽器中手動登入...")
            logger.info("登入完成後，在此終端按 Enter 繼續...")
            
            # 等待使用者輸入
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # 保存 Session
            await context.storage_state(path=str(self.session_file))
            logger.info(f"Session 已保存至 {self.session_file}")
            
            await browser.close()
    
    async def auto_login(self, page) -> bool:
        """自動登入 (使用設定檔中的帳密)"""
        logger.info(f"嘗試自動登入 {self.platform}...")
        
        email = self.config.get("email", "")
        password = self.config.get("password", "")
        
        if not email or not password:
            logger.error("設定檔中缺少 email 或 password")
            return False
        
        try:
            if self.platform == "agoda":
                await self._login_agoda(page, email, password)
            elif self.platform == "booking":
                await self._login_booking(page, email, password)
            else:
                logger.error(f"不支援的平台: {self.platform}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"自動登入失敗: {e}")
            return False
    
    async def _login_agoda(self, page, email: str, password: str) -> None:
        """Agoda 登入流程"""
        # 等待並填寫 email
        await page.wait_for_selector('input[type="email"], input[name="email"]', timeout=10000)
        await page.fill('input[type="email"], input[name="email"]', email)
        
        # 點擊下一步或直接填寫密碼
        try:
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(2000)
        except:
            pass
        
        # 填寫密碼
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        await page.fill('input[type="password"]', password)
        
        # 提交
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
    
    async def _login_booking(self, page, email: str, password: str) -> None:
        """Booking.com 登入流程"""
        # 等待並填寫 email
        await page.wait_for_selector('input[type="email"], #loginname', timeout=10000)
        await page.fill('input[type="email"], #loginname', email)
        
        # 點擊下一步
        await page.click('button[type="submit"], .bui-button--primary')
        await page.wait_for_timeout(2000)
        
        # 填寫密碼
        await page.wait_for_selector('input[type="password"]', timeout=10000)
        await page.fill('input[type="password"]', password)
        
        # 提交
        await page.click('button[type="submit"], .bui-button--primary')
        await page.wait_for_timeout(3000)
    
    async def get_context(self, playwright) -> BrowserContext:
        """取得已登入的 Browser Context"""
        browser = await playwright.chromium.launch(
            headless=self.config.get("headless", True)
        )
        
        if self.session_file.exists():
            logger.info(f"載入已保存的 Session: {self.session_file}")
            context = await browser.new_context(storage_state=str(self.session_file))
        else:
            logger.warning("Session 檔案不存在，建立新的 Context")
            context = await browser.new_context()
        
        return context
    
    async def save_session(self, context: BrowserContext) -> None:
        """保存當前 Session"""
        await context.storage_state(path=str(self.session_file))
        logger.info(f"Session 已更新: {self.session_file}")
    
    def is_login_page(self, url: str) -> bool:
        """檢查是否為登入頁面"""
        login_indicators = ["login", "signin", "sign-in", "auth"]
        return any(indicator in url.lower() for indicator in login_indicators)


async def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(description="Session 管理器")
    parser.add_argument("--platform", choices=["agoda", "booking"], required=True)
    parser.add_argument("--login", action="store_true", help="進行互動式登入")
    args = parser.parse_args()
    
    # 簡單設定 (實際使用時從 config.yaml 讀取)
    config = {
        "agoda": {"url": "https://ycs.agoda.com/"},
        "booking": {"url": "https://admin.booking.com/"},
    }
    
    manager = SessionManager(args.platform, config.get(args.platform, {}))
    
    if args.login:
        await manager.interactive_login()


if __name__ == "__main__":
    asyncio.run(main())
