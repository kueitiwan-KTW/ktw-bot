# L3_business/plugins/hotel 訂單查詢狀態機
# 建立日期：2025-12-24

"""
訂單查詢狀態機

處理流程：
客人說想查訂單 → 搜尋訂單 → 確認是否本人 → 收集補充資訊 → 完成確認
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, date


@dataclass
class OrderData:
    """訂單資料模型"""
    
    # 查詢結果
    order_id: str = ""
    guest_name: str = ""
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    room_type: str = ""
    room_count: int = 1
    nights: int = 1
    total_price: float = 0
    
    # 確認資訊
    phone: str = ""
    arrival_time: str = ""
    special_requests: str = ""
    
    # LINE 資訊
    line_user_id: str = ""
    line_display_name: str = ""
    
    # 元資料
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化為 dict"""
        return {
            'order_id': self.order_id,
            'guest_name': self.guest_name,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'room_type': self.room_type,
            'room_count': self.room_count,
            'nights': self.nights,
            'total_price': self.total_price,
            'phone': self.phone,
            'arrival_time': self.arrival_time,
            'special_requests': self.special_requests,
            'line_user_id': self.line_user_id,
            'line_display_name': self.line_display_name
        }


class SimpleOrderQueryMachine:
    """
    簡化版訂單查詢狀態機
    
    支援：
    - SessionManager 整合（持久化）
    - Event 格式（統一事件處理）
    """
    
    STATES = ['idle', 'searching', 'confirming', 'collecting_phone', 'collecting_arrival', 'completed', 'not_found']
    
    # 事件名稱常數
    EVENT_START = 'ORDER_QUERY_START'
    EVENT_CONFIRM = 'ORDER_QUERY_CONFIRM'
    EVENT_PHONE = 'ORDER_QUERY_PHONE'
    EVENT_ARRIVAL = 'ORDER_QUERY_ARRIVAL'
    EVENT_CANCEL = 'CANCEL'
    
    def __init__(self, model: OrderData = None, user_id: str = None, tenant_id: str = None, session_manager = None):
        self.model = model or OrderData()
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.current_state = 'idle'
        self.found_orders: List[OrderData] = []
        self.session_manager = session_manager
        
        # 如果有 SessionManager，從 session 恢復狀態
        if session_manager and user_id:
            session_state = session_manager.get_state(user_id)
            if session_state.startswith('order_query.'):
                self.current_state = session_state.replace('order_query.', '')
                data = session_manager.get_data(user_id)
                if data:
                    self._restore_from_session_data(data)
    
    def _restore_from_session_data(self, data: Dict[str, Any]):
        """從 session 資料恢復 model"""
        if data.get('order_id'):
            self.model.order_id = data.get('order_id', '')
            self.model.guest_name = data.get('guest_name', '')
            self.model.phone = data.get('phone', '')
            self.model.arrival_time = data.get('arrival_time', '')
    
    def _sync_to_session(self):
        """同步狀態到 SessionManager"""
        if self.session_manager and self.user_id:
            state = f'order_query.{self.current_state}' if self.current_state != 'idle' else 'idle'
            data = {
                'order_id': self.model.order_id,
                'guest_name': self.model.guest_name,
                'phone': self.model.phone,
                'arrival_time': self.model.arrival_time,
            }
            self.session_manager.set_state(self.user_id, state, data)
    
    def handle_event(self, event) -> str:
        """
        處理統一事件格式
        
        Args:
            event: Event 物件，包含 name, slots, raw_text 等
            
        Returns:
            回覆訊息
        """
        event_name = event.name if hasattr(event, 'name') else event.get('name', '')
        slots = event.slots if hasattr(event, 'slots') else event.get('slots', {})
        raw_text = event.raw_text if hasattr(event, 'raw_text') else event.get('raw_text', '')
        
        if event_name == self.EVENT_START:
            return self.start_query(raw_text)
        elif event_name == self.EVENT_CONFIRM:
            return self.confirm_order()
        elif event_name == self.EVENT_PHONE:
            phone = slots.get('phone', raw_text)
            return self.got_phone(phone)
        elif event_name == self.EVENT_ARRIVAL:
            time = slots.get('time', raw_text)
            return self.got_arrival(time)
        elif event_name == self.EVENT_CANCEL:
            return self.cancel()
        else:
            # 根據當前狀態處理
            if self.current_state == 'confirming':
                return self.confirm_order()
            elif self.current_state == 'collecting_phone':
                return self.got_phone(raw_text)
            elif self.current_state == 'collecting_arrival':
                return self.got_arrival(raw_text)
            else:
                return "我不太理解您的意思，請問您想做什麼？"

    def start_query(self, search_term: str) -> str:
        """開始查詢"""
        if self.current_state != 'idle':
            return "目前正在進行其他流程"
        
        self.current_state = 'searching'
        # TODO: 呼叫 PMS API 搜尋訂單
        # self.found_orders = self._search_orders(search_term)
        
        if not self.found_orders:
            self.current_state = 'not_found'
            return "抱歉，查不到符合的訂單。\n\n請確認：\n• 訂房大名\n• 入住日期\n• 或訂單編號"
        
        if len(self.found_orders) == 1:
            self.model = self.found_orders[0]
            self.current_state = 'confirming'
            return self._format_order_confirmation()
        
        # 多筆訂單
        return self._format_multiple_orders()
    
    def confirm_order(self) -> str:
        """確認訂單"""
        if self.current_state != 'confirming':
            return "請先查詢訂單"
        
        self.current_state = 'collecting_phone'
        return "請提供您的聯絡電話，以便我們在需要時聯繫您。"
    
    def got_phone(self, phone: str) -> str:
        """收到電話"""
        if self.current_state != 'collecting_phone':
            return "目前不在收集電話階段"
        
        if not phone or len(phone) < 8:
            return "電話格式不正確，請輸入正確的電話號碼"
        
        self.model.phone = phone
        self.current_state = 'collecting_arrival'
        return "請問您預計幾點抵達？"
    
    def got_arrival(self, time: str) -> str:
        """收到抵達時間"""
        if self.current_state != 'collecting_arrival':
            return "目前不在收集抵達時間階段"
        
        self.model.arrival_time = time
        self.current_state = 'completed'
        return self._format_confirmation_success()
    
    def cancel(self) -> str:
        """取消流程"""
        if self.current_state in ['idle', 'completed', 'not_found']:
            return "目前沒有進行中的流程"
        
        self.current_state = 'idle'
        return "好的，已結束查詢流程。有需要隨時再和我說！"
    
    def _format_order_confirmation(self) -> str:
        """格式化訂單確認訊息"""
        return f"""📋 查詢結果

👤 姓名：{self.model.guest_name}
📅 入住：{self.model.check_in_date}
📅 退房：{self.model.check_out_date}
🏠 房型：{self.model.room_type}
🔢 數量：{self.model.room_count} 間
🌙 晚數：{self.model.nights} 晚

請問這是您的訂單嗎？
（回覆「是」繼續確認資訊，或「不是」重新查詢）"""
    
    def _format_multiple_orders(self) -> str:
        """格式化多筆訂單列表"""
        lines = ["查到多筆訂單，請選擇：\n"]
        for i, order in enumerate(self.found_orders, 1):
            lines.append(f"{i}. {order.guest_name} - {order.check_in_date} ({order.room_type})")
        lines.append("\n請輸入編號選擇，或說「取消」結束")
        return "\n".join(lines)
    
    def _format_confirmation_success(self) -> str:
        """格式化確認成功訊息"""
        return f"""✅ 已為您完成預訂資訊確認！

📅 入住：{self.model.check_in_date}
📅 退房：{self.model.check_out_date}
🏠 房型：{self.model.room_type}
📞 電話：{self.model.phone}
🕐 抵達：{self.model.arrival_time}

如有任何問題，歡迎隨時詢問！
祝您旅途愉快！ 🎉"""
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            'current_state': self.current_state,
            'model_data': self.model.to_dict(),
            'user_id': self.user_id,
            'tenant_id': self.tenant_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimpleOrderQueryMachine':
        """反序列化"""
        model = OrderData()
        model_data = data.get('model_data', {})
        
        for key, value in model_data.items():
            if hasattr(model, key):
                if key in ['check_in_date', 'check_out_date'] and value:
                    setattr(model, key, date.fromisoformat(value))
                else:
                    setattr(model, key, value)
        
        machine = cls(
            model=model,
            user_id=data.get('user_id'),
            tenant_id=data.get('tenant_id')
        )
        machine.current_state = data.get('current_state', 'idle')
        
        return machine
