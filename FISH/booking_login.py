"""
Booking.com Persistent Context 登入
使用 user_data_dir 保存登入狀態
"""
import asyncio
import sys
from playwright.async_api import async_playwright
import os

# 強制刷新 stdout
sys.stdout.reconfigure(line_buffering=True)

USER_DATA_DIR = 'sessions/booking_profile'
SCREENSHOT_DIR = '/Users/ktw/.gemini/antigravity/brain/5f810689-2e68-41f2-81c6-f7b378213462'


async def main():
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    print('=== Booking.com Persistent Context ===', flush=True)
    print(f'User Data Dir: {USER_DATA_DIR}', flush=True)
    
    async with async_playwright() as p:
        print('啟動 Chromium...', flush=True)
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            locale='zh-TW',
            timezone_id='Asia/Taipei',
            viewport={'width': 1280, 'height': 800},
            slow_mo=200,
        )
        
        print('瀏覽器已開啟!', flush=True)
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        print('導航到 Booking.com...', flush=True)
        await page.goto('https://admin.booking.com')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        current_url = page.url
        title = await page.title()
        print(f'URL: {current_url}', flush=True)
        print(f'標題: {title}', flush=True)
        
        if 'home.html' in current_url or 'extranet' in current_url or 'manage' in current_url:
            print('\n✅ 已登入！（Persistent Profile 生效）', flush=True)
        else:
            print('\n⏳ 需要登入（首次使用此 Profile）', flush=True)
            print('請在瀏覽器中登入 Booking.com Extranet...', flush=True)
            
            for i in range(180):  # 3 分鐘
                await page.wait_for_timeout(1000)
                current_url = page.url
                if 'hotel/' in current_url or 'home.html' in current_url:
                    print(f'\n✅ 登入成功！', flush=True)
                    print(f'URL: {current_url}', flush=True)
                    break
                if i % 30 == 0 and i > 0:
                    print(f'   等待中... ({i}秒)', flush=True)
        
        await page.screenshot(path=f'{SCREENSHOT_DIR}/booking_persistent.png')
        print('📸 截圖已保存', flush=True)
        
        print('\nProfile 已保存！下次開啟將自動登入', flush=True)
        
        await page.wait_for_timeout(3000)
        await context.close()
        
    print('\n完成!', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
