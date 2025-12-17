"""
處理器基礎類別
定義所有處理器的共用介面
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseHandler(ABC):
    """處理器抽象基礎類別"""
    
    def __init__(self):
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self._next_handler: Optional[str] = None
    
    @abstractmethod
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """
        處理用戶訊息
        
        Args:
            user_id: LINE 用戶 ID
            message: 用戶訊息
            display_name: LINE 顯示名稱
        
        Returns:
            回覆訊息，None 表示不處理
        """
        pass
    
    @abstractmethod
    def is_active(self, user_id: str) -> bool:
        """
        檢查用戶是否在此處理器的流程中
        
        Args:
            user_id: LINE 用戶 ID
        
        Returns:
            True 表示用戶正在此處理器的流程中
        """
        pass
    
    def is_completed(self, user_id: str) -> bool:
        """
        檢查用戶是否已完成此處理器的流程
        
        Args:
            user_id: LINE 用戶 ID
        
        Returns:
            True 表示流程已完成
        """
        return False
    
    def should_switch_to(self) -> Optional[str]:
        """
        檢查是否需要切換到其他處理器
        
        Returns:
            處理器名稱 ('ORDER_QUERY', 'SAME_DAY_BOOKING', 'AI_CONVERSATION')
            None 表示不需要切換
        """
        next_handler = self._next_handler
        self._next_handler = None  # 重置
        return next_handler
    
    def request_switch(self, handler_name: str):
        """
        請求切換到其他處理器
        
        Args:
            handler_name: 目標處理器名稱
        """
        self._next_handler = handler_name
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """取得或建立用戶 session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = self._create_default_session()
        return self.user_sessions[user_id]
    
    def clear_session(self, user_id: str):
        """清除用戶 session"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    def _create_default_session(self) -> Dict[str, Any]:
        """建立預設 session（子類別可覆寫）"""
        return {'state': 'idle'}


class HandlerRouter:
    """處理器路由器"""
    
    # 處理器類型常量
    ORDER_QUERY = 'ORDER_QUERY'
    SAME_DAY_BOOKING = 'SAME_DAY_BOOKING'
    AI_CONVERSATION = 'AI_CONVERSATION'
    
    def __init__(self):
        self.handlers: Dict[str, BaseHandler] = {}
        self.active_handler: Dict[str, str] = {}  # {user_id: handler_type}
    
    def register_handler(self, handler_type: str, handler: BaseHandler):
        """註冊處理器"""
        self.handlers[handler_type] = handler
    
    def get_active_handler(self, user_id: str) -> Optional[BaseHandler]:
        """取得用戶當前活躍的處理器"""
        handler_type = self.active_handler.get(user_id)
        if handler_type:
            handler = self.handlers.get(handler_type)
            if handler and handler.is_active(user_id):
                return handler
            else:
                # 清除無效的活躍狀態
                del self.active_handler[user_id]
        return None
    
    def set_active_handler(self, user_id: str, handler_type: str):
        """設定用戶當前的處理器"""
        self.active_handler[user_id] = handler_type
    
    def clear_active_handler(self, user_id: str):
        """清除用戶的處理器狀態"""
        if user_id in self.active_handler:
            del self.active_handler[user_id]
    
    def route(self, user_id: str, message: str) -> str:
        """
        路由判斷 - 決定使用哪個處理器
        
        Args:
            user_id: LINE 用戶 ID
            message: 用戶訊息
        
        Returns:
            處理器類型
        """
        import re
        
        # 優先順序 1: 檢查是否包含訂單編號 (5位數以上)
        if re.search(r'\b\d{5,}\b', message):
            return self.ORDER_QUERY
        
        # 優先順序 2: 檢查是否為訂房意圖
        booking_keywords = [
            '訂房', '預訂', '今天住', '今日住', '有房', '還有房',
            '空房', '房間', '想住', '要住', '可以住', '訂'
        ]
        
        # 排除查詢訂單相關
        exclude_keywords = ['我有訂', '已經訂', '查訂單', '我的訂單']
        
        message_lower = message.lower()
        has_booking_intent = any(kw in message_lower for kw in booking_keywords)
        has_exclude = any(kw in message_lower for kw in exclude_keywords)
        
        if has_booking_intent and not has_exclude:
            return self.SAME_DAY_BOOKING
        
        # 優先順序 3: 一般對話
        return self.AI_CONVERSATION
