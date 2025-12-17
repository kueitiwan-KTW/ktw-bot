"""
AI 對話處理器
處理一般諮詢、知識庫問答、天氣查詢等
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .base_handler import BaseHandler


class AIConversationHandler(BaseHandler):
    """
    AI 對話處理器
    
    處理:
    - 知識庫問答
    - 天氣查詢
    - 設施介紹
    - 一般諮詢
    
    特點:
    - 不維護複雜狀態
    - 純粹的問答模式
    - 使用 Gemini AI
    """
    
    def __init__(self, model, knowledge_base: Dict, weather_helper, logger):
        """
        初始化處理器
        
        Args:
            model: Gemini AI 模型
            knowledge_base: 知識庫資料
            weather_helper: 天氣查詢助手
            logger: 對話記錄器
        """
        super().__init__()
        self.model = model
        self.knowledge_base = knowledge_base
        self.weather_helper = weather_helper
        self.logger = logger
        self.chat_sessions: Dict[str, Any] = {}
    
    def is_active(self, user_id: str) -> bool:
        """AI 對話不維護持續狀態，總是返回 False"""
        return False
    
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """處理一般對話"""
        
        # 1. 檢查是否為天氣查詢
        if self._is_weather_query(message):
            return self._handle_weather_query(message)
        
        # 2. 使用 AI 對話
        return self._generate_ai_response(user_id, message, display_name)
    
    def _is_weather_query(self, message: str) -> bool:
        """檢查是否為天氣查詢"""
        weather_keywords = ['天氣', '氣溫', '下雨', '會不會雨', '溫度', '天氣預報']
        return any(kw in message for kw in weather_keywords)
    
    def _handle_weather_query(self, message: str) -> str:
        """處理天氣查詢"""
        try:
            # 判斷是查詢特定日期還是一週
            week_keywords = ['一週', '這週', '未來', '七天', '7天', '週末']
            
            if any(kw in message for kw in week_keywords):
                result = self.weather_helper.get_weekly_forecast()
            else:
                # 提取日期（如果有）
                date_str = self._extract_date_from_message(message)
                result = self.weather_helper.get_weather_forecast(date_str)
            
            if result:
                return result + "\n\n（資料來源：中央氣象署）"
            else:
                return "抱歉，目前無法取得天氣資訊，請稍後再試。"
        except Exception as e:
            print(f"❌ 天氣查詢失敗: {e}")
            return "抱歉，天氣查詢發生錯誤，請稍後再試。"
    
    def _extract_date_from_message(self, message: str) -> Optional[str]:
        """從訊息中提取日期"""
        import re
        
        # 今天/明天/後天
        if '今天' in message or '今日' in message:
            return 'today'
        elif '明天' in message or '明日' in message:
            return 'tomorrow'
        elif '後天' in message:
            return 'day_after_tomorrow'
        
        # 日期格式 (12/25, 12月25日)
        match = re.search(r'(\d{1,2})[/月](\d{1,2})', message)
        if match:
            month, day = match.groups()
            return f"{datetime.now().year}-{int(month):02d}-{int(day):02d}"
        
        return None
    
    def _generate_ai_response(self, user_id: str, message: str, display_name: str = None) -> str:
        """生成 AI 回覆"""
        try:
            # 取得或建立聊天 session
            chat = self._get_or_create_chat(user_id)
            
            # 加入系統時間資訊
            today_str = datetime.now().strftime("%Y-%m-%d")
            weekday_map = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
            weekday_str = weekday_map[datetime.now().weekday()]
            
            enhanced_message = message + f"\n(System Info: Current Date is {today_str} 星期{weekday_str})"
            
            # 發送訊息給 AI
            response = chat.send_message(enhanced_message)
            
            return response.text
            
        except Exception as e:
            print(f"❌ AI 回覆失敗: {e}")
            return "不好意思，我目前無法回答這個問題。請稍後再試，或直接聯繫櫃檯。"
    
    def _get_or_create_chat(self, user_id: str):
        """取得或建立聊天 session"""
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = self.model.start_chat(
                enable_automatic_function_calling=True
            )
        return self.chat_sessions[user_id]
    
    def reset_chat(self, user_id: str):
        """重置用戶的聊天 session"""
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]
            print(f"✅ 已重置用戶 {user_id} 的 AI 對話")
