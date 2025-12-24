# L3_business/plugins/hotel 飯店訂房狀態機
# 建立日期：2025-12-24

"""
當日預訂狀態機

處理流程：
客人說想訂房 → 確認房型 → 收集電話 → 收集抵達時間 → 完成

使用 python-statemachine 實現（需安裝：pip install python-statemachine）
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, date

# 備註：正式使用時取消註解
# from statemachine import StateMachine, State


@dataclass
class BookingData:
    """當日預訂資料模型"""
    
    # 預訂資訊
    check_in_date: Optional[date] = None
    nights: int = 1
    room_type: str = ""
    room_count: int = 1
    guests: int = 2
    
    # 客人資訊
    guest_name: str = ""
    phone: str = ""
    arrival_time: str = ""
    special_requests: str = ""
    
    # LINE 資訊
    line_user_id: str = ""
    line_display_name: str = ""
    
    # 元資料
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化為 dict"""
        return {
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'nights': self.nights,
            'room_type': self.room_type,
            'room_count': self.room_count,
            'guests': self.guests,
            'guest_name': self.guest_name,
            'phone': self.phone,
            'arrival_time': self.arrival_time,
            'special_requests': self.special_requests,
            'line_user_id': self.line_user_id,
            'line_display_name': self.line_display_name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# 以下為 python-statemachine 實現範例
# 正式使用時取消註解並安裝套件

"""
class SameDayBookingMachine(StateMachine):
    '''當日預訂狀態機'''
    
    # 狀態定義
    idle = State(initial=True)
    confirming_room = State()       # 確認房型
    collecting_phone = State()      # 收集電話
    collecting_arrival = State()    # 收集抵達時間
    collecting_special = State()    # 收集特殊需求
    completed = State(final=True)
    cancelled = State(final=True)
    
    # 轉換定義
    start_booking = idle.to(confirming_room)
    confirm_room = confirming_room.to(collecting_phone)
    reject_room = confirming_room.to(idle)
    
    got_phone = collecting_phone.to(collecting_arrival)
    got_arrival = collecting_arrival.to(collecting_special)
    complete = collecting_special.to(completed)
    
    # 任何狀態都可以取消
    cancel = (
        confirming_room.to(cancelled) |
        collecting_phone.to(cancelled) |
        collecting_arrival.to(cancelled) |
        collecting_special.to(cancelled)
    )
    
    def __init__(self, model: BookingData = None, user_id: str = None, tenant_id: str = None):
        self.model = model or BookingData()
        self.user_id = user_id
        self.tenant_id = tenant_id
        super().__init__()
    
    # 進入狀態事件
    def on_enter_confirming_room(self):
        '''進入確認房型狀態'''
        return self._format_room_confirmation()
    
    def on_enter_collecting_phone(self):
        '''進入收集電話狀態'''
        return "請提供您的聯絡電話，以便我們在需要時聯繫您。"
    
    def on_enter_collecting_arrival(self):
        '''進入收集抵達時間狀態'''
        return "請問您預計幾點抵達？"
    
    def on_enter_collecting_special(self):
        '''進入收集特殊需求狀態'''
        return "請問有任何特殊需求嗎？（如：無障礙設施、嬰兒床等）\n\n沒有的話請直接說「沒有」或「確認」"
    
    def on_enter_completed(self):
        '''進入完成狀態'''
        # 儲存到資料庫
        return self._format_booking_success()
    
    def on_enter_cancelled(self):
        '''進入取消狀態'''
        return "好的，已為您取消預訂流程。有需要隨時再和我說！"
    
    # Guards（前置條件）
    def before_got_phone(self, phone: str):
        '''電話驗證'''
        if not phone or len(phone) < 8:
            raise ValueError("電話格式不正確，請輸入正確的電話號碼")
        self.model.phone = phone
        self.model.updated_at = datetime.now()
    
    def before_got_arrival(self, time: str):
        '''抵達時間驗證'''
        self.model.arrival_time = time
        self.model.updated_at = datetime.now()
    
    def before_complete(self, special: str = ""):
        '''特殊需求'''
        self.model.special_requests = special
        self.model.updated_at = datetime.now()
    
    # 格式化方法
    def _format_room_confirmation(self) -> str:
        '''格式化房型確認訊息'''
        return f'''
📋 預訂確認

日期：{self.model.check_in_date}
房型：{self.model.room_type}
數量：{self.model.room_count} 間
人數：{self.model.guests} 人

請確認以上資訊是否正確？
        '''.strip()
    
    def _format_booking_success(self) -> str:
        '''格式化預訂成功訊息'''
        return f'''
✅ 預訂完成！

📅 入住日期：{self.model.check_in_date}
🏠 房型：{self.model.room_type}
📞 聯絡電話：{self.model.phone}
🕐 預計抵達：{self.model.arrival_time}

⚠️ 提醒：當日預訂為「無押金」預訂，
若臨時有變動請提前告知，感謝您的配合！

祝您旅途愉快！ 🎉
        '''.strip()
"""


# 簡化版狀態機（不依賴 python-statemachine）
class SimpleSameDayBookingMachine:
    """
    簡化版當日預訂狀態機
    
    支援：
    - SessionManager 整合（持久化）
    - Event 格式（統一事件處理）
    """
    
    STATES = ['idle', 'confirming_room', 'collecting_phone', 'collecting_arrival', 'collecting_special', 'completed', 'cancelled']
    
    # 事件名稱常數
    EVENT_START = 'BOOKING_START'
    EVENT_CONFIRM = 'BOOKING_CONFIRM'
    EVENT_PHONE = 'BOOKING_PHONE'
    EVENT_ARRIVAL = 'BOOKING_ARRIVAL'
    EVENT_SPECIAL = 'BOOKING_SPECIAL'
    EVENT_CANCEL = 'CANCEL'
    
    def __init__(self, model: BookingData = None, user_id: str = None, tenant_id: str = None, session_manager = None):
        self.model = model or BookingData()
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.current_state = 'idle'
        self.session_manager = session_manager
        
        # 如果有 SessionManager，從 session 恢復狀態
        if session_manager and user_id:
            session_state = session_manager.get_state(user_id)
            if session_state.startswith('booking.'):
                self.current_state = session_state.replace('booking.', '')
                data = session_manager.get_data(user_id)
                if data:
                    self._restore_from_session_data(data)
    
    def _restore_from_session_data(self, data: Dict[str, Any]):
        """從 session 資料恢復 model"""
        self.model.room_type = data.get('room_type', '')
        self.model.room_count = data.get('room_count', 1)
        self.model.guests = data.get('guests', 2)
        self.model.guest_name = data.get('guest_name', '')
        self.model.phone = data.get('phone', '')
        self.model.arrival_time = data.get('arrival_time', '')
        self.model.special_requests = data.get('special_requests', '')
    
    def _sync_to_session(self):
        """同步狀態到 SessionManager"""
        if self.session_manager and self.user_id:
            state = f'booking.{self.current_state}' if self.current_state != 'idle' else 'idle'
            data = {
                'room_type': self.model.room_type,
                'room_count': self.model.room_count,
                'guests': self.model.guests,
                'guest_name': self.model.guest_name,
                'phone': self.model.phone,
                'arrival_time': self.model.arrival_time,
                'special_requests': self.model.special_requests,
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
            room_type = slots.get('room_type', '標準雙人房')
            room_count = slots.get('room_count', 1)
            guests = slots.get('guests', 2)
            return self.start_booking(room_type, room_count, guests)
        elif event_name == self.EVENT_CONFIRM:
            return self.confirm_room()
        elif event_name == self.EVENT_PHONE:
            phone = slots.get('phone', raw_text)
            return self.got_phone(phone)
        elif event_name == self.EVENT_ARRIVAL:
            time = slots.get('time', raw_text)
            return self.got_arrival(time)
        elif event_name == self.EVENT_SPECIAL:
            special = slots.get('special', raw_text)
            return self.complete(special)
        elif event_name == self.EVENT_CANCEL:
            return self.cancel()
        else:
            # 根據當前狀態處理
            if self.current_state == 'confirming_room':
                return self.confirm_room()
            elif self.current_state == 'collecting_phone':
                return self.got_phone(raw_text)
            elif self.current_state == 'collecting_arrival':
                return self.got_arrival(raw_text)
            elif self.current_state == 'collecting_special':
                return self.complete(raw_text)
            else:
                return "我不太理解您的意思，請問您想做什麼？"

    def start_booking(self, room_type: str, room_count: int = 1, guests: int = 2) -> str:
        """開始預訂流程"""
        if self.current_state != 'idle':
            return "目前正在進行其他流程"
        
        self.model.check_in_date = date.today()
        self.model.room_type = room_type
        self.model.room_count = room_count
        self.model.guests = guests
        self.model.line_user_id = self.user_id
        self.current_state = 'confirming_room'
        
        return self._format_room_confirmation()
    
    def confirm_room(self) -> str:
        """確認房型"""
        if self.current_state != 'confirming_room':
            return "請先開始預訂流程"
        
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
        self.current_state = 'collecting_special'
        return "請問有任何特殊需求嗎？（如：無障礙設施、嬰兒床等）\n\n沒有的話請直接說「沒有」或「確認」"
    
    def complete(self, special: str = "") -> str:
        """完成預訂"""
        if self.current_state != 'collecting_special':
            return "請先完成前面的步驟"
        
        self.model.special_requests = special
        self.current_state = 'completed'
        return self._format_booking_success()
    
    def cancel(self) -> str:
        """取消預訂"""
        if self.current_state in ['idle', 'completed', 'cancelled']:
            return "目前沒有進行中的預訂流程"
        
        self.current_state = 'cancelled'
        return "好的，已為您取消預訂流程。有需要隨時再和我說！"
    
    def _format_room_confirmation(self) -> str:
        """格式化房型確認訊息"""
        return f"""📋 預訂確認

📅 日期：{self.model.check_in_date}
🏠 房型：{self.model.room_type}
🔢 數量：{self.model.room_count} 間
👥 人數：{self.model.guests} 人

請確認以上資訊是否正確？
（回覆「確認」繼續，或「取消」結束）"""
    
    def _format_booking_success(self) -> str:
        """格式化預訂成功訊息"""
        return f"""✅ 預訂完成！

📅 入住日期：{self.model.check_in_date}
🏠 房型：{self.model.room_type}
📞 聯絡電話：{self.model.phone}
🕐 預計抵達：{self.model.arrival_time}

⚠️ 提醒：當日預訂為「無押金」預訂，
若臨時有變動請提前告知，感謝您的配合！

祝您旅途愉快！ 🎉"""
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化（用於 Session 持久化）"""
        return {
            'current_state': self.current_state,
            'model_data': self.model.to_dict(),
            'user_id': self.user_id,
            'tenant_id': self.tenant_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimpleSameDayBookingMachine':
        """反序列化"""
        model = BookingData()
        model_data = data.get('model_data', {})
        
        # 恢復模型資料
        for key, value in model_data.items():
            if hasattr(model, key):
                if key == 'check_in_date' and value:
                    setattr(model, key, date.fromisoformat(value))
                elif key in ['created_at', 'updated_at'] and value:
                    setattr(model, key, datetime.fromisoformat(value))
                else:
                    setattr(model, key, value)
        
        machine = cls(
            model=model,
            user_id=data.get('user_id'),
            tenant_id=data.get('tenant_id')
        )
        machine.current_state = data.get('current_state', 'idle')
        
        return machine
