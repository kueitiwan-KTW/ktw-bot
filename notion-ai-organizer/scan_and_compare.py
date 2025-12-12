"""
批量文檔掃描與同步工具

功能：
1. 掃描專案目錄下所有文檔檔案
2. 比對 Notion 中已有的頁面
3. 識別：新文件、已存在、需更新的文件
4. 批量上傳/更新到 Notion
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
import hashlib
from datetime import datetime

# 載入環境變數
load_dotenv(Path(__file__).parent.parent / '.env')

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
PARENT_PAGE_ID = os.getenv('NOTION_PARENT_PAGE_ID', '2c5c3f7d0f51809aadd0cad363f798a5')

notion = Client(auth=NOTION_TOKEN)


class DocumentScanner:
    """文檔掃描與比對工具"""
    
    # 支援的文件類型
    SUPPORTED_EXTENSIONS = [
        '.md',      # Markdown
        '.txt',     # 純文字
        '.json',    # JSON
        '.py',      # Python（可選）
        '.js',      # JavaScript（可選）
    ]
    
    # 排除的目錄
    EXCLUDE_DIRS = [
        'node_modules',
        '.git',
        '__pycache__',
        'venv',
        '.env',
        'chat_logs',
        'daemon',
        '.gemini'
    ]
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.notion_pages = {}  # 存儲 Notion 現有頁面
        self.local_files = {}   # 存儲本地文件
        self.current_branch = self._get_current_branch()
        self.is_main_branch = self.current_branch in ['main', 'master']
    
    def _get_current_branch(self):
        """獲取當前Git分支名稱"""
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else 'unknown'
        except:
            return 'unknown'
    
    def _get_all_branches(self):
        """獲取所有Git分支列表"""
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'branch', '-a'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                branches = []
                for line in result.stdout.strip().split('\n'):
                    branch = line.strip().replace('* ', '')
                    # 排除 remote tracking branches
                    if not branch.startswith('remotes/'):
                        branches.append(branch)
                return branches
            return []
        except:
            return []
    
    def get_branch_tag(self):
        """獲取分支標籤（如果不是main分支則標記[分支]）"""
        if self.is_main_branch:
            return ''
        return f' [分支: {self.current_branch}]'
    
    def scan_local_files(self, include_code=False):
        """掃描本地文件"""
        print('🔍 掃描本地文檔...\n')
        
        extensions = self.SUPPORTED_EXTENSIONS.copy()
        if not include_code:
            # 如果不包含代碼，只掃描文檔類型
            extensions = ['.md', '.txt', '.json']
        
        for root, dirs, files in os.walk(self.project_root):
            # 排除特定目錄
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                
                # 檢查副檔名
                if file_path.suffix in extensions:
                    rel_path = file_path.relative_to(self.project_root)
                    
                    # 計算文件哈希（用於比對）
                    file_hash = self._calculate_hash(file_path)
                    
                    # 獲取文件資訊
                    stats = file_path.stat()
                    
                    self.local_files[str(rel_path)] = {
                        'path': file_path,
                        'relative_path': str(rel_path),
                        'hash': file_hash,
                        'size': stats.st_size,
                        'modified': datetime.fromtimestamp(stats.st_mtime),
                        'type': file_path.suffix
                    }
        
        print(f'✅ 找到 {len(self.local_files)} 個文檔文件\n')
        return self.local_files
    
    def scan_notion_pages(self):
        """掃描 Notion 現有頁面"""
        print('🔍 掃描 Notion 現有頁面...\n')
        
        children = notion.blocks.children.list(block_id=PARENT_PAGE_ID)
        
        for block in children['results']:
            if block['type'] == 'child_page':
                page_id = block['id']
                page = notion.pages.retrieve(page_id=page_id)
                title = page['properties']['title']['title'][0]['plain_text'] if page['properties']['title']['title'] else 'Untitled'
                
                self.notion_pages[title] = {
                    'id': page_id,
                    'title': title,
                    'created': page['created_time'],
                    'last_edited': page['last_edited_time']
                }
        
        print(f'✅ 找到 {len(self.notion_pages)} 個 Notion 頁面\n')
        return self.notion_pages
    
    def compare_files(self):
        """比對本地文件與 Notion 頁面"""
        print('📊 比對分析...\n')
        
        results = {
            'new': [],       # 新文件（Notion 中不存在）
            'existing': [],  # 已存在（需要檢查是否更新）
            'orphaned': []   # Notion 中有但本地沒有
        }
        
        # 檢查本地文件
        for rel_path, file_info in self.local_files.items():
            # 簡化名稱用於匹配
            file_name = Path(rel_path).stem  # 去掉副檔名
            
            # 檢查是否在 Notion 中存在
            matched = False
            for title, page_info in self.notion_pages.items():
                if file_name.lower() in title.lower() or title.lower() in file_name.lower():
                    results['existing'].append({
                        'local': file_info,
                        'notion': page_info,
                        'match_type': 'fuzzy'
                    })
                    matched = True
                    break
            
            if not matched:
                results['new'].append(file_info)
        
        # 檢查 Notion 中的孤立頁面（本地沒有對應文件）
        for title, page_info in self.notion_pages.items():
            matched = False
            for rel_path in self.local_files.keys():
                file_name = Path(rel_path).stem
                if file_name.lower() in title.lower():
                    matched = True
                    break
            
            if not matched:
                results['orphaned'].append(page_info)
        
        return results
    
    def print_comparison_report(self, results):
        """打印比對報告"""
        print('=' * 80)
        print('📋 比對報告')
        print('=' * 80)
        
        print(f'\n🆕 新文件（需要上傳到 Notion）：{len(results["new"])} 個')
        for i, file_info in enumerate(results['new'][:10], 1):
            print(f'   {i:2d}. {file_info["relative_path"]:50s} ({file_info["size"]:,} bytes)')
        if len(results['new']) > 10:
            print(f'   ... 還有 {len(results["new"]) - 10} 個文件')
        
        print(f'\n✅ 已存在（可能需要更新）：{len(results["existing"])} 個')
        for i, match in enumerate(results['existing'][:10], 1):
            local = match['local']
            notion = match['notion']
            print(f'   {i:2d}. {local["relative_path"]:40s} ↔️ {notion["title"]}')
        if len(results['existing']) > 10:
            print(f'   ... 還有 {len(results["existing"]) - 10} 個匹配')
        
        print(f'\n🗑️ 孤立頁面（Notion 中有但本地沒有）：{len(results["orphaned"])} 個')
        for i, page_info in enumerate(results['orphaned'][:10], 1):
            print(f'   {i:2d}. {page_info["title"]}')
        if len(results['orphaned']) > 10:
            print(f'   ... 還有 {len(results["orphaned"]) - 10} 個頁面')
        
        print('\n' + '=' * 80)
        
        # 統計
        print(f'\n📊 統計：')
        print(f'   本地文檔：{len(self.local_files)} 個')
        print(f'   Notion 頁面：{len(self.notion_pages)} 個')
        print(f'   新增需求：{len(results["new"])} 個')
        print(f'   同步狀態：{len(results["existing"])} 個已同步')
        
        return results
    
    def _calculate_hash(self, file_path):
        """計算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
    
    def export_to_file(self, results, output_file='scan_results.txt'):
        """導出比對結果到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('文檔掃描與比對結果\n')
            f.write('=' * 80 + '\n\n')
            f.write(f'掃描時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            f.write(f'新文件（{len(results["new"])} 個）：\n')
            for file_info in results['new']:
                f.write(f'  - {file_info["relative_path"]}\n')
            
            f.write(f'\n已存在（{len(results["existing"])} 個）：\n')
            for match in results['existing']:
                f.write(f'  - {match["local"]["relative_path"]} ↔️ {match["notion"]["title"]}\n')
            
            f.write(f'\n孤立頁面（{len(results["orphaned"])} 個）：\n')
            for page in results['orphaned']:
                f.write(f'  - {page["title"]}\n')
        
        print(f'\n📄 結果已導出到：{output_file}')


def main():
    """主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description='掃描並比對專案文檔與 Notion 頁面')
    parser.add_argument('--project', default='/Users/ktw/KTW-bot', help='專案根目錄')
    parser.add_argument('--include-code', action='store_true', help='包含程式碼文件（.py, .js）')
    parser.add_argument('--export', default='scan_results.txt', help='導出結果文件名')
    
    args = parser.parse_args()
    
    scanner = DocumentScanner(args.project)
    
    # 掃描
    scanner.scan_local_files(include_code=args.include_code)
    scanner.scan_notion_pages()
    
    # 比對
    results = scanner.compare_files()
    
    # 顯示報告
    scanner.print_comparison_report(results)
    
    # 導出結果
    scanner.export_to_file(results, args.export)
    
    print('\n💡 下一步：')
    print('   - 使用 organize_and_upload.py 上傳新文件')
    print('   - 檢查是否需要更新已存在的頁面')
    print('   - 考慮清理孤立的 Notion 頁面')


if __name__ == '__main__':
    main()
