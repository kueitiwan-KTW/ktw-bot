"""
VIP 服務處理器
處理內部 VIP 和客人 VIP 的專屬功能

功能：
- 內部 VIP：PMS 查詢、網路搜尋、無限制 AI 對話、圖片分析
- 客人 VIP：（未來）專屬優惠、優先服務

特色：
- 支援上下文記憶（任務記憶）
- 統一入口管理所有 VIP 功能
"""

import os
import re
from typing import Optional, Dict, Any
from PIL import Image
import io

from .base_handler import BaseHandler
from .vip_manager import vip_manager
from .internal_query import internal_query
from .web_search import web_search


class VIPServiceHandler(BaseHandler):
    """
    VIP 服務處理器
    
    狀態：
    - vip_idle: 閒置
    - vip_waiting_image: 等待圖片（記住任務）
    """
    
    # 狀態常數
    STATE_VIP_IDLE = 'vip_idle'
    STATE_VIP_WAITING_IMAGE = 'vip_waiting_image'
    
    # 角色稱謂對照表
    ROLE_TITLES = {
        'chairman': '董事長',
        'manager': '經理',
        'staff': '同事',
        'super_vip': '長官'
    }
    
    def __init__(self, state_machine, logger, vision_model=None):
        """
        初始化 VIP 服務處理器
        
        Args:
            state_machine: 統一對話狀態機
            logger: 對話記錄器
            vision_model: Gemini Vision 模型（用於圖片辨識）
        """
        super().__init__()
        self.state_machine = state_machine
        self.logger = logger
        self.vision_model = vision_model
    
    def is_vip(self, user_id: str) -> bool:
        """檢查用戶是否為任何類型的 VIP"""
        return vip_manager.is_vip(user_id)
    
    def is_internal(self, user_id: str) -> bool:
        """檢查用戶是否為內部 VIP"""
        return vip_manager.is_internal(user_id)
    
    def is_active(self, user_id: str) -> bool:
        """檢查用戶是否在 VIP 服務流程中（有待處理任務）"""
        state = self.state_machine.get_state(user_id)
        return state.startswith('vip_')
    
    def get_role_title(self, user_id: str) -> str:
        """取得 VIP 角色稱謂"""
        vip_info = vip_manager.get_vip_info(user_id)
        role = vip_info.get('role') if vip_info else None
        return self.ROLE_TITLES.get(role, '長官')
    
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """
        處理 VIP 用戶的文字訊息
        
        Args:
            user_id: LINE 用戶 ID
            message: 用戶訊息
            display_name: 用戶顯示名稱
            
        Returns:
            Optional[str]: 回覆訊息，若無法處理則返回 None
        """
        # 只處理內部 VIP
        if not self.is_internal(user_id):
            return None
        
        role_title = self.get_role_title(user_id)
        message_lower = message.lower()
        
        # 1. 檢查是否在等待圖片狀態
        state = self.state_machine.get_state(user_id)
        if state == self.STATE_VIP_WAITING_IMAGE:
            # 用戶傳了文字而非圖片
            pending_task = self.state_machine.get_data(user_id, 'pending_task')
            if pending_task:
                return f"{role_title}，請傳送您要{pending_task.get('description', '處理')}的圖片。"
        
        # 2. 偵測是否需要圖片的任務
        image_task = self._detect_image_task(message)
        if image_task:
            self.state_machine.transition(user_id, self.STATE_VIP_WAITING_IMAGE)
            self.state_machine.set_data(user_id, 'pending_task', image_task)
            return f"{role_title}，好的，請傳送您要{image_task['description']}的圖片。"
        
        # 3. 週報查詢（本週/週末）- 必須放在今日房況之前
        week_keywords = ['這禮拜', '這星期', '本週', '這周']
        weekend_keywords = ['這週末', '週末', '這個週末', '本週末']
        month_keywords = ['本月', '這個月', '這月']
        
        if any(kw in message for kw in weekend_keywords):
            result = internal_query.query_week_forecast(scope='weekend')
            return f"{role_title}，{result.get('message')}"
        
        if any(kw in message for kw in month_keywords):
            result = internal_query.query_month_forecast()
            return f"{role_title}，{result.get('message')}"
        
        if any(kw in message for kw in week_keywords):
            result = internal_query.query_week_forecast(scope='week')
            return f"{role_title}，{result.get('message')}"
        
        # 4. 今日房況查詢（擴充口語用法）
        room_status_keywords = [
            '房況', '今天房況', '住房率', '空房',
            '多少人住', '幾間房', '幾個人住', '住幾間',
            '今天住', '住房狀況', '房間狀況', '入住率'
        ]
        if any(kw in message for kw in room_status_keywords):
            result = internal_query.query_today_status()
            return f"{role_title}，{result.get('message')}"
        
        # 4. 入住名單
        if any(kw in message for kw in ['入住名單', '今日入住', '誰入住', '今天誰']):
            result = internal_query.query_today_checkin_list()
            return f"{role_title}，{result.get('message')}"
        
        # 5. 清潔/停用狀態
        if any(kw in message for kw in ['房間狀態', '待清潔', '待打掃', '清潔狀態', '客房狀態', '停用']):
            result = internal_query.query_room_status()
            return f"{role_title}，{result.get('message')}"
        
        # 6. 臨時訂單/當日訂單
        if any(kw in message for kw in ['臨時訂單', '現場訂', 'LINE訂單', '今日訂單']):
            result = internal_query.query_same_day_bookings()
            return f"{role_title}，{result.get('message')}"
        
        # 7. 姓名查詢
        name_match = re.search(r'(?:查|找|搜尋)(.+?)(?:的)?(?:訂單|訂房|預訂|資料)?$', message)
        if name_match:
            name = name_match.group(1).strip()
            if name and name not in ['今天', '今日', '明天', '昨天', '誰', '什麼']:
                result = internal_query.query_booking_by_name(name)
                return f"{role_title}，{result.get('message')}"
        
        # 8. 網路搜尋
        search_match = re.search(r'(?:幫我查一下|幫我查|搜尋一下|搜尋|查一下|上網查|幫我搜尋|幫查)(.+)', message)
        if search_match:
            query = search_match.group(1).strip()
            if query:
                result = web_search.search(query, role_title)
                return result.get('message')
        
        # 9. 無限制 AI 對話（任何其他訊息）
        return self._free_chat(message, role_title)
    
    def handle_image(self, user_id: str, image_data: bytes, display_name: str = None) -> Optional[str]:
        """
        處理 VIP 用戶的圖片
        
        Args:
            user_id: LINE 用戶 ID
            image_data: 圖片二進位資料
            display_name: 用戶顯示名稱
            
        Returns:
            Optional[str]: 回覆訊息，若無法處理則返回 None
        """
        # 只處理內部 VIP
        if not self.is_internal(user_id):
            return None
        
        if not self.vision_model:
            return "【系統錯誤】Vision 模型未初始化。"
        
        role_title = self.get_role_title(user_id)
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 檢查是否有待處理任務
            pending_task = self.state_machine.get_data(user_id, 'pending_task')
            
            if pending_task:
                # 有指定任務，按任務處理
                prompt = self._build_task_prompt(pending_task, role_title)
                # 清除任務狀態
                self.state_machine.transition(user_id, 'idle')
                self.state_machine.set_data(user_id, 'pending_task', None)
            else:
                # 無指定任務，通用分析
                prompt = f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）分析圖片。

【重要】這是內部 VIP，你可以做任何任務（翻譯、分析、辨識等），請：
1. 詳細描述圖片內容
2. 如果圖片中有文字，完整辨識出來（保持原始語言）
3. 如果是對話截圖，整理出對話內容
4. 開頭稱呼「{role_title}」
5. 辨識完後詢問「您需要我幫您做什麼處理嗎？（翻譯、整理、分析等）」

【語言規則】用對方使用的語言回覆。如果對方用中文問就用中文答，英文問就英文答。只有在對方明確要求翻譯時才翻譯。"""
            
            response = self.vision_model.generate_content([prompt, image])
            text = response.text.strip()
            
            # 記錄對話
            if self.logger:
                self.logger.log(user_id, "User", "[傳送了一張圖片]")
                self.logger.log(user_id, "Bot (VIP Vision)", text)
            
            return text
            
        except Exception as e:
            print(f"❌ VIP 圖片處理錯誤: {e}")
            return f"{role_title}，圖片處理發生錯誤，請稍後再試。"
    
    def _detect_image_task(self, message: str) -> Optional[Dict]:
        """
        偵測是否為需要圖片的任務
        
        Args:
            message: 用戶訊息
            
        Returns:
            Optional[Dict]: 任務資訊，包含 description 和 target_language 等
        """
        # 翻譯任務
        translate_patterns = [
            (r'翻譯.*(圖片|照片|截圖).*(?:成|為|到)?\s*(中文|印尼文|英文|日文|韓文|印尼語|英語|日語|韓語)?', 'translate'),
            (r'(?:圖片|照片|截圖).*翻譯.*(?:成|為|到)?\s*(中文|印尼文|英文|日文|韓文|印尼語|英語|日語|韓語)?', 'translate'),
            (r'幫我翻譯.*(圖|照片)', 'translate'),
            (r'translate.*(image|photo|picture)', 'translate'),
            (r'terjemahkan.*(foto|gambar)', 'translate'),  # 印尼語
        ]
        
        for pattern, task_type in translate_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # 嘗試提取目標語言
                target_lang = None
                if match.lastindex and match.lastindex >= 1:
                    target_lang = match.group(match.lastindex)
                
                # 從完整訊息中偵測語言
                if not target_lang:
                    if '印尼' in message or 'indonesia' in message.lower():
                        target_lang = '印尼語'
                    elif '英' in message or 'english' in message.lower():
                        target_lang = '英語'
                    elif '日' in message:
                        target_lang = '日語'
                    elif '韓' in message:
                        target_lang = '韓語'
                    elif '中' in message:
                        target_lang = '繁體中文'
                
                return {
                    'type': 'translate',
                    'description': f'翻譯成{target_lang}' if target_lang else '翻譯',
                    'target_language': target_lang
                }
        
        # 辨識任務
        if re.search(r'辨識.*(圖片|照片|文字|內容)', message):
            return {
                'type': 'ocr',
                'description': '辨識文字'
            }
        
        return None
    
    def _build_task_prompt(self, task: Dict, role_title: str) -> str:
        """
        根據任務建立 prompt
        
        Args:
            task: 任務資訊
            role_title: 角色稱謂
            
        Returns:
            str: Vision prompt
        """
        task_type = task.get('type', 'general')
        
        if task_type == 'translate':
            target_lang = task.get('target_language', '繁體中文')
            return f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）處理圖片。

【任務】將圖片中的所有文字翻譯成 {target_lang}

【要求】
1. 開頭稱呼「{role_title}」
2. 先完整辨識圖片中的所有文字（原文）
3. 然後翻譯成 {target_lang}
4. 如果是對話截圖，保持對話格式
5. 結尾問「還有其他需要幫忙的嗎？」"""
        
        elif task_type == 'ocr':
            return f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）處理圖片。

【任務】辨識圖片中的所有文字

【要求】
1. 開頭稱呼「{role_title}」
2. 完整辨識並列出圖片中的所有文字
3. 保持原始語言和格式
4. 結尾問「需要我幫您翻譯或做其他處理嗎？」"""
        
        else:
            return f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）分析圖片。

請完整分析這張圖片，開頭稱呼「{role_title}」。"""
    
    def _free_chat(self, message: str, role_title: str) -> str:
        """
        無限制 AI 對話（不受客服 persona 限制）
        
        Args:
            message: 用戶訊息
            role_title: 角色稱謂
            
        Returns:
            str: AI 回覆
        """
        try:
            # 嘗試使用新版 SDK
            try:
                from google import genai
                
                api_key = os.getenv('GOOGLE_API_KEY')
                client = genai.Client(api_key=api_key)
                
                system_prompt = f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）服務。

【重要】這是內部 VIP 對話，不受一般客服限制：
- 可以回答任何問題（翻譯、寫作、分析、建議等）
- 不需要詢問訂單編號
- 回覆要有禮貌，開頭稱呼「{role_title}」
- 盡力滿足所有合理需求

【語言規則】用對方使用的語言回覆。對方用中文問就用中文答，用英文問就用英文答，用印尼語問就用印尼語答。只有在對方明確要求翻譯時才做翻譯。

請直接回應以下訊息："""
                
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=f"{system_prompt}\n\n{message}"
                )
                
                if response and response.text:
                    return response.text
                    
            except ImportError:
                # Fallback 到舊版 SDK
                import google.generativeai as genai_old
                genai_old.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                model = genai_old.GenerativeModel('gemini-3-flash-preview')
                
                prompt = f"""你是龜地灣旅館的 AI 助理，正在為內部管理層人員（{role_title}）服務。
這是內部 VIP 對話，不受一般客服限制，可以回答任何問題。
用對方使用的語言回覆（中文問中文答、英文問英文答、印尼語問印尼語答）。
開頭稱呼「{role_title}」。

用戶訊息：{message}"""
                
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
                    
            return f"{role_title}，不好意思，系統暫時無法處理您的請求，請稍後再試。"
            
        except Exception as e:
            print(f"❌ VIP 對話錯誤: {e}")
            return f"{role_title}，系統發生錯誤：{str(e)}"


# 全域實例（延遲初始化，需在 bot.py 中設定 state_machine 和 logger）
vip_service = None

def init_vip_service(state_machine, logger, vision_model=None):
    """初始化 VIP 服務"""
    global vip_service
    vip_service = VIPServiceHandler(state_machine, logger, vision_model)
    return vip_service
