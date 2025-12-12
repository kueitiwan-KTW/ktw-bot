"""
Notion AI 文檔整理助手

功能：
1. 讀取本地 Markdown 文檔
2. 使用 Gemini AI 分析並優化內容
3. 自動排版並上傳到 Notion
4. 生成美觀的頁面結構

使用方式：
python organize_and_upload.py <文檔路徑>
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
import google.generativeai as genai
import re

# 載入環境變數
load_dotenv(Path(__file__).parent.parent / '.env')

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
PARENT_PAGE_ID = os.getenv('NOTION_PARENT_PAGE_ID', '2c5c3f7d0f51809aadd0cad363f798a5')

# 初始化
notion = Client(auth=NOTION_TOKEN)
genai.configure(api_key=GOOGLE_API_KEY)


class NotionAIOrganizer:
    """AI 驅動的 Notion 文檔整理器"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.current_branch = self._get_current_branch()
    
    def _get_current_branch(self):
        """獲取當前Git分支名稱"""
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else 'unknown'
        except:
            return 'unknown'
    
    def _get_branch_tag(self):
        """獲取分支標籤（如果不是main分支則標記[分支]）"""
        if self.current_branch in ['main', 'master']:
            return ''
        return f' [分支: {self.current_branch}]'
    
    def read_markdown(self, file_path):
        """讀取 Markdown 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def analyze_and_optimize(self, content, add_ai_insights=True):
        """使用 AI 分析並優化文檔"""
        
        insights_instruction = ""
        if add_ai_insights:
            insights_instruction = """
5. **添加 AI 建議與洞察**（重要！）：
   - 在適當位置添加 AI 的分析、建議或補充說明
   - 每個建議必須用特殊格式標記：
     {{"type": "callout", "icon": "🤖", "color": "purple_background", "content": "💡 AI 建議：[你的建議內容]"}}
   - 建議類型：
     * 最佳實踐建議
     * 潛在風險提醒
     * 優化建議
     * 相關知識補充
     * 實作注意事項
   - 原則：簡潔扼要，每個建議不超過 3 句話
"""
        
        prompt = f"""
你是一個專業的技術文檔編輯器 + 技術顧問。請將以下 Markdown 文檔轉換為結構化的 Notion 格式。

⚠️ 重要原則：
1. **保留所有原始內容** - 不要刪減任何段落、列表或細節
2. **保持完整性** - 所有版本號、日期、功能說明都要完整保留
3. **優化格式** - 添加適當的視覺元素（emoji、callout）但不改變內容
4. **原文與 AI 建議分離** - 用特殊顏色標記 AI 添加的內容

任務：
1. 提取文檔標題
2. 生成一個簡短摘要（2-3 句話）
3. 提取 3-5 個關鍵字
4. **完整轉換**所有內容為 Notion blocks，包括：
   - 所有標題（H1-H6）
   - 所有段落（完整保留）
   - 所有列表項目
   - 所有代碼塊
   - 重要提示用 callout 標記
{insights_instruction}

請用 JSON 格式回覆（sections 必須包含**所有**原始內容 + AI 建議）：
{{
  "title": "文檔標題",
  "summary": "簡短摘要",
  "keywords": ["關鍵字1", "關鍵字2"],
  "sections": [
    {{"type": "heading_1", "content": "完整標題"}},
    {{"type": "heading_2", "content": "子標題"}},
    {{"type": "paragraph", "content": "完整段落內容"}},
    
    // AI 建議必須用這個格式（紫色背景 + 🤖 圖示）
    {{"type": "callout", "icon": "🤖", "color": "purple_background", "content": "💡 AI 建議：這裡建議使用 XXX 方法，因為..."}},
    
    {{"type": "bulleted_list_item", "content": "列表項目"}},
    {{"type": "code", "language": "python", "content": "代碼內容"}},
    {{"type": "callout", "icon": "⚠️", "color": "yellow_background", "content": "重要提示"}}
  ]
}}

原始 Markdown 文檔：
```markdown
{content}
```

請確保：
1. sections 陣列包含文檔的**每一行內容**
2. AI 建議用紫色 callout + 🤖 圖示標記
3. AI 建議簡潔有用，每個 2-3 句話
"""
        
        response = self.model.generate_content(prompt)
        return response.text
    
    def create_notion_page(self, analysis_result, parent_id=PARENT_PAGE_ID, source_file=None):
        """根據分析結果創建 Notion 頁面"""
        # 解析 AI 回應（移除 markdown 代碼塊標記）
        import json
        import subprocess
        from datetime import datetime
        
        # 清理 JSON（移除 ```json 和 ```）
        cleaned = re.sub(r'```json\s*|\s*```', '', analysis_result.strip())
        data = json.loads(cleaned)
        
        # 獲取當前Git分支
        branch_tag = self._get_branch_tag()
        
        # 查詢現有頁面數量以自動編號
        try:
            children = notion.blocks.children.list(block_id=parent_id)
            page_count = sum(1 for block in children['results'] if block['type'] == 'child_page')
            page_number = page_count + 1
        except:
            page_number = 1
        
        # 在標題前加上編號、分支標記和時間戳記
        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title_with_number_and_time = f"{page_number}. {data['title']}{branch_tag} {upload_time}"
        
        # 創建頁面
        page = notion.pages.create(
            parent={'page_id': parent_id},
            icon={'type': 'emoji', 'emoji': '📄' if not branch_tag else '🔀'},
            properties={
                'title': {
                    'title': [{
                        'type': 'text',
                        'text': {'content': title_with_number_and_time}
                    }]
                }
            }
        )
        
        # 準備內容區塊
        blocks = []
        
        # 添加來源檔案資訊（簡化版，不含時間）
        if source_file:
            from pathlib import Path
            file_path = Path(source_file)
            
            blocks.append({
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': [{
                        'type': 'text',
                        'text': {'content': f'📁 來源檔案：{file_path.name}\n📂 路徑：{source_file}'}
                    }],
                    'icon': {'type': 'emoji', 'emoji': '📌'},
                    'color': 'gray_background'
                }
            })
        
        # 添加摘要
        blocks.append({
            'object': 'block',
            'type': 'callout',
            'callout': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f"摘要：{data['summary']}"}
                }],
                'icon': {'type': 'emoji', 'emoji': '📋'},
                'color': 'blue_background'
            }
        })
        
        # 添加關鍵字
        keywords_text = '、'.join(data['keywords'])
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f'🏷️ 關鍵字：{keywords_text}'}
                }]
            }
        })
        
        blocks.append({
            'object': 'block',
            'type': 'divider',
            'divider': {}
        })
        
        # 添加主要內容
        for section in data['sections']:
            block = self._create_block(section)
            if block:
                blocks.append(block)
        
        # 分批添加區塊（Notion API 限制每次 100 個）
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i+batch_size]
            notion.blocks.children.append(
                block_id=page['id'],
                children=batch
            )
        
        return page
    
    def _create_block(self, section):
        """根據 section 類型創建對應的 Notion block"""
        block_type = section.get('type')
        content = section.get('content', '')  # 使用 get() 避免 KeyError
        
        # 跳過無效的 section
        if not block_type or not content:
            return None
        
        if block_type == 'heading_1':
            return {
                'object': 'block',
                'type': 'heading_1',
                'heading_1': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'heading_2':
            return {
                'object': 'block',
                'type': 'heading_2',
                'heading_2': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'heading_3':
            return {
                'object': 'block',
                'type': 'heading_3',
                'heading_3': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'paragraph':
            return {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'callout':
            # 解析 Markdown 超連結並轉換為 Notion rich_text
            rich_text = self._parse_hyperlinks(content)
            
            return {
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': rich_text,
                    'icon': {'type': 'emoji', 'emoji': section.get('icon', '💡')},
                    'color': section.get('color', 'yellow_background')
                }
            }
        elif block_type == 'code':
            # 確保 language 符合 Notion API 規範
            language = section.get('language', 'plain text')
            
            # 語言標準化映射
            language_map = {
                'text': 'plain text',
                'plain_text': 'plain text',
                'plaintext': 'plain text',  # AI 有時會生成這個
                'env': 'plain text',
                'dotenv': 'plain text',
                'ini': 'plain text',
                'config': 'plain text',
                'conf': 'plain text',
                'gitignore': 'plain text',
                'txt': 'plain text',
                'http': 'plain text',
                'properties': 'plain text',
                'log': 'plain text',
                'sh': 'shell',
                'zsh': 'shell',
                'bat': 'shell',
                'cmd': 'shell',
                'ps1': 'powershell',
                'js': 'javascript',
                'ts': 'typescript',
                'py': 'python',
                'rb': 'ruby',
                'yml': 'yaml'
            }
            
            # 轉換語言（不區分大小寫）
            language = language_map.get(language.lower(), language)
            
            return {
                'object': 'block',
                'type': 'code',
                'code': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}],
                    'language': language
                }
            }
        elif block_type == 'bulleted_list_item':
            return {
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'numbered_list_item':
            return {
                'object': 'block',
                'type': 'numbered_list_item',
                'numbered_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}]
                }
            }
        elif block_type == 'quote':
            # 將 quote 轉換為 callout（Notion 支援）
            return {
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': [{'type': 'text', 'text': {'content': content}}],
                    'icon': {'type': 'emoji', 'emoji': '📌'},
                    'color': 'gray_background'
                }
            }
        elif block_type == 'divider':
            return {
                'object': 'block',
                'type': 'divider',
                'divider': {}
            }
        
        # 不支援的類型，跳過
        return None
    
    def _parse_hyperlinks(self, text):
        """解析 Markdown 超連結並轉換為 Notion rich_text 格式"""
        import re
        
        # 正則表達式匹配 Markdown 超連結：[文字](URL)
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        
        rich_text = []
        last_end = 0
        
        for match in re.finditer(link_pattern, text):
            # 添加連結前的文本
            if match.start() > last_end:
                plain_text = text[last_end:match.start()]
                if plain_text:
                    rich_text.append({
                        'type': 'text',
                        'text': {'content': plain_text}
                    })
            
            # 添加超連結
            link_text = match.group(1)
            link_url = match.group(2)
            rich_text.append({
                'type': 'text',
                'text': {
                    'content': link_text,
                    'link': {'url': link_url}
                }
            })
            
            last_end = match.end()
        
        # 添加最後剩餘的文本
        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text:
                rich_text.append({
                    'type': 'text',
                    'text': {'content': remaining_text}
                })
        
        # 如果沒有找到任何連結，返回純文本
        if not rich_text:
            rich_text = [{'type': 'text', 'text': {'content': text}}]
        
        return rich_text
    
    def process_document(self, file_path, add_insights=True, mode='new'):
        """完整的文檔處理流程
        
        Args:
            file_path: 文檔路徑
            add_insights: 是否添加 AI 建議
            mode: 'new' 創建新頁面 | 'update' 更新現有頁面
        """
        print(f'📖 讀取文檔: {file_path}')
        content = self.read_markdown(file_path)
        
        insights_text = '（含 AI 建議）' if add_insights else ''
        print(f'🤖 AI 分析與優化中{insights_text}...')
        analysis = self.analyze_and_optimize(content, add_ai_insights=add_insights)
        
        if mode == 'update':
            # 更新模式
            from page_updater import NotionPageUpdater
            updater = NotionPageUpdater(notion)
            
            print('🔍 查找現有頁面...')
            existing_page_id = updater.find_existing_page(file_path, PARENT_PAGE_ID)
            
            if existing_page_id:
                print(f'✅ 找到現有頁面，準備更新...')
                
                # 解析新內容
                import json
                cleaned = re.sub(r'```json\s*|\s*```', '', analysis.strip())
                data = json.loads(cleaned)
                
                # 準備新區塊（不含 page 創建）
                blocks = self._prepare_blocks(data, file_path)
                
                # 更新頁面
                page_id = updater.update_page(existing_page_id, blocks, preserve_user_content=True)
                
                page_info = notion.pages.retrieve(page_id=page_id)
                print(f'✅ 更新完成！')
                print(f'💾 已保留您的手動內容')
                print(f'🟡 變更已標記')
                if add_insights:
                    print(f'💡 已添加 AI 建議（紫色標記 🤖）')
                print(f'📁 來源檔案已標註')
                print(f'🔗 頁面連結: {page_info["url"]}')
                
                return page_info
            else:
                print('⚠️ 未找到現有頁面，將創建新頁面...')
                mode = 'new'
        
        # 新建模式（或更新模式未找到頁面時）
        print('📝 創建 Notion 頁面...')
        page = self.create_notion_page(analysis, source_file=file_path)
        
        print(f'✅ 完成！')
        if add_insights:
            print(f'💡 已添加 AI 建議（紫色標記 🤖）')
        print(f'📁 來源檔案已標註')
        print(f'🔗 頁面連結: {page["url"]}')
        
        return page
    
    def _prepare_blocks(self, data, source_file):
        """準備區塊內容（用於更新模式）"""
        from pathlib import Path
        from datetime import datetime
        
        blocks = []
        
        # 添加來源檔案資訊
        if source_file:
            file_path = Path(source_file)
            
            blocks.append({
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': [{
                        'type': 'text',
                        'text': {'content': f'📁 來源檔案：{file_path.name}\n📂 路徑：{source_file}'}
                    }],
                    'icon': {'type': 'emoji', 'emoji': '📌'},
                    'color': 'gray_background'
                }
            })
        
        # 添加摘要
        blocks.append({
            'object': 'block',
            'type': 'callout',
            'callout': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f"摘要：{data['summary']}"}
                }],
                'icon': {'type': 'emoji', 'emoji': '📋'},
                'color': 'blue_background'
            }
        })
        
        # 添加關鍵字
        keywords_text = '、'.join(data['keywords'])
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f'🏷️ 關鍵字：{keywords_text}'}
                }]
            }
        })
        
        blocks.append({
            'object': 'block',
            'type': 'divider',
            'divider': {}
        })
        
        # 添加主要內容
        for section in data['sections']:
            block = self._create_block(section)
            if block:
                blocks.append(block)
        
        return blocks


def main():
    """主程序"""
    if len(sys.argv) < 2:
        print('使用方式: python organize_and_upload.py <文檔路徑> [選項]')
        print('\n選項:')
        print('  --no-insights    不添加 AI 建議')
        print('  --mode=new       創建新頁面（預設）')
        print('  --mode=update    更新現有頁面，保留手動內容')
        print('\n範例:')
        print('  python organize_and_upload.py ../CHANGELOG.md')
        print('  python organize_and_upload.py ../CHANGELOG.md --mode=update')
        print('  python organize_and_upload.py ../README.md --no-insights --mode=update')
        sys.exit(1)
    
    file_path = sys.argv[1]
    add_insights = '--no-insights' not in sys.argv
    
    # 解析 mode 參數
    mode = 'new'  # 預設
    for arg in sys.argv:
        if arg.startswith('--mode='):
            mode = arg.split('=')[1]
            if mode not in ['new', 'update']:
                print(f'❌ 錯誤：mode 必須是 "new" 或 "update"')
                sys.exit(1)
    
    if not os.path.exists(file_path):
        print(f'❌ 文件不存在: {file_path}')
        sys.exit(1)
    
    organizer = NotionAIOrganizer()
    organizer.process_document(file_path, add_insights=add_insights, mode=mode)


if __name__ == '__main__':
    main()
