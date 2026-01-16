"""
分析選取全部的 DOM 結構
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state='sessions/agoda_session.json')
        page = await context.new_page()
        
        await page.goto('https://ycs.agoda.com/mldc/zh-tw/app/ari/calendar/1615175')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        print('1. 開選單')
        room_button = page.get_by_test_id('ycs-calendar-page-room-filter-button')
        await room_button.click()
        await page.wait_for_timeout(1500)
        
        # 分析 DOM 結構
        dom_info = await page.evaluate("""() => {
            const result = [];
            
            // 找所有 checkbox
            document.querySelectorAll('input[type=checkbox]').forEach((cb, i) => {
                const parent = cb.closest('label, li, div');
                const text = parent ? parent.innerText.trim().slice(0, 40) : '';
                const rect = cb.getBoundingClientRect();
                result.push({
                    index: i,
                    text: text,
                    checked: cb.checked,
                    visible: rect.width > 0 && rect.height > 0,
                    id: cb.id,
                    name: cb.name,
                    className: cb.className.slice(0, 50)
                });
            });
            
            return result;
        }""")
        
        print('所有 Checkbox:')
        for item in dom_info:
            ck = '☑️' if item['checked'] else '☐'
            vis = '✅' if item['visible'] else '❌'
            print(f"   [{item['index']}] {ck} {vis} '{item['text']}' id={item['id']} name={item['name']}")
        
        # 找包含"選取全部"的元素
        select_all_info = await page.evaluate("""() => {
            const elements = [];
            
            // 用 XPath 找
            const xpathResult = document.evaluate(
                "//*[contains(text(), '選取全部')]",
                document,
                null,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                null
            );
            
            for (let i = 0; i < xpathResult.snapshotLength; i++) {
                const el = xpathResult.snapshotItem(i);
                const rect = el.getBoundingClientRect();
                elements.push({
                    tag: el.tagName,
                    text: el.innerText?.slice(0, 30),
                    visible: rect.width > 0 && rect.height > 0,
                    siblingCheckbox: !!el.parentElement?.querySelector('input[type=checkbox]'),
                    outerHTML: el.outerHTML?.slice(0, 200)
                });
            }
            
            return elements;
        }""")
        
        print('\n包含「選取全部」的元素:')
        for item in select_all_info:
            print(f"   {item['tag']} | visible={item['visible']} | siblingCheckbox={item['siblingCheckbox']}")
            print(f"      HTML: {item['outerHTML']}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
