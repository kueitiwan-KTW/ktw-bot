"""
當日預訂對話狀態機
處理 BOT 當日預訂的多輪對話流程
"""

from datetime import datetime
from typing import Optional, Dict, Any


class SameDayBookingHandler:
    """當日預訂處理器"""
    
    # 對話狀態常量
    STATE_IDLE = 'idle'                     # 初始狀態
    STATE_SHOW_ROOMS = 'show_rooms'         # 顯示可用房型
    STATE_COLLECT_ROOM = 'collect_room'     # 收集房型選擇
    STATE_COLLECT_INFO = 'collect_info'     # 收集客人資訊
    STATE_CONFIRM = 'confirm'               # 確認預訂
    STATE_COMPLETE = 'complete'             # 完成
    
    # 房型對照表
    ROOM_TYPE_MAP = {
        'SD': '標準雙人房',
        'ST': '標準三人房', 
        'SQ': '標準四人房',
        'CD': '經典雙人房',
        'CQ': '經典四人房',
        'DD': '豪華雙人房',
        'ED': '行政雙人房',
        'WD': '海景雙人房',
        'WQ': '海景四人房',
        'VD': 'VIP雙人房',
        'VQ': 'VIP四人房',
        'FM': '親子家庭房',
        'AD': '無障礙雙人房',
        'AQ': '無障礙四人房'
    }
    
    def __init__(self, pms_client):
        """
        初始化處理器
        
        Args:
            pms_client: PMSClient 實例
        """
        self.pms_client = pms_client
        self.user_sessions = {}  # 用戶對話狀態 {user_id: session_data}
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """取得或建立用戶對話 session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'state': self.STATE_IDLE,
                'available_rooms': [],
                'selected_room': None,
                'room_count': 1,
                'guest_name': None,
                'phone': None,
                'arrival_time': None,
                'line_display_name': None,
                'created_at': datetime.now().isoformat()
            }
        return self.user_sessions[user_id]
    
    def clear_session(self, user_id: str):
        """清除用戶 session"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    def is_same_day_intent(self, message: str) -> bool:
        """
        判斷是否為當日預訂意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是當日預訂意圖
        """
        keywords = [
            '今天', '今日', '當天', '當日',
            '現在', '馬上', '立刻', '等下', '等一下',
            '晚上', '今晚', '下午', '傍晚'
        ]
        booking_keywords = ['訂房', '預訂', '訂', '住', '入住', '有房', '還有房']
        
        message_lower = message.lower()
        
        # 檢查是否包含時間關鍵字 + 預訂關鍵字
        has_time = any(kw in message_lower for kw in keywords)
        has_booking = any(kw in message_lower for kw in booking_keywords)
        
        return has_time and has_booking
    
    def is_within_booking_hours(self) -> bool:
        """
        檢查是否在可預訂時間內（22:00 前）
        
        Returns:
            True 如果在可預訂時間內
        """
        now = datetime.now()
        return now.hour < 22
    
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """
        處理用戶訊息
        
        Args:
            user_id: LINE 用戶 ID
            message: 用戶訊息
            display_name: LINE 顯示名稱
            
        Returns:
            回覆訊息，None 表示不是當日預訂流程
        """
        session = self.get_session(user_id)
        
        # 保存 display_name
        if display_name:
            session['line_display_name'] = display_name
        
        # 狀態機處理
        state = session['state']
        
        if state == self.STATE_IDLE:
            # 檢查是否為當日預訂意圖
            if self.is_same_day_intent(message):
                return self._start_booking(user_id, session)
            return None  # 不是當日預訂，交給其他處理器
        
        elif state == self.STATE_SHOW_ROOMS:
            # 等待用戶選擇房型
            return self._handle_room_selection(user_id, session, message)
        
        elif state == self.STATE_COLLECT_INFO:
            # 收集客人資訊
            return self._handle_info_collection(user_id, session, message)
        
        elif state == self.STATE_CONFIRM:
            # 確認預訂
            return self._handle_confirmation(user_id, session, message)
        
        return None
    
    def _start_booking(self, user_id: str, session: Dict) -> str:
        """開始預訂流程"""
        
        # 檢查時間
        if not self.is_within_booking_hours():
            self.clear_session(user_id)
            return """抱歉，當日預訂服務僅開放至晚上 10 點。

若您有住宿需求，歡迎透過以下方式預訂：
🌐 官網：https://www.tortugabay.com.tw
📞 電話：(08) 882-5631"""
        
        # 查詢今日可用房型
        result = self.pms_client.get_today_availability()
        
        if not result or not result.get('success'):
            self.clear_session(user_id)
            return """抱歉，目前無法查詢房況，請稍後再試。

如有急需，請直接聯繫：
📞 櫃檯電話：(08) 882-5631"""
        
        available_rooms = result.get('data', {}).get('available_room_types', [])
        
        if not available_rooms:
            self.clear_session(user_id)
            return """抱歉，今日房間已全數客滿。

建議您可以：
1. 查看明日或其他日期的空房
2. 透過官網預訂：https://www.tortugabay.com.tw
3. 致電櫃檯確認：(08) 882-5631"""
        
        # 保存可用房型
        session['available_rooms'] = available_rooms
        session['state'] = self.STATE_SHOW_ROOMS
        
        # 格式化房型列表
        room_list = []
        for i, room in enumerate(available_rooms, 1):
            name = room.get('room_type_name', room.get('room_type_code', '未知'))
            available = room.get('available_count', 0)
            price = room.get('price', 0)
            room_list.append(f"{i}. {name} - 剩 {available} 間")
            if price:
                room_list[-1] += f"（NT${price:,}/晚）"
        
        return f"""📋 今日可預訂房型：

{chr(10).join(room_list)}

請告訴我您想預訂哪種房型？
（直接輸入房型名稱或編號即可）"""
    
    def _handle_room_selection(self, user_id: str, session: Dict, message: str) -> str:
        """處理房型選擇"""
        available_rooms = session.get('available_rooms', [])
        selected_room = None
        room_count = 1
        
        # 嘗試解析房型選擇
        message_clean = message.strip()
        
        # 解析間數（如 "2間"）
        import re
        count_match = re.search(r'(\d+)\s*間', message)
        if count_match:
            room_count = int(count_match.group(1))
        
        # 方法1: 數字選擇
        if message_clean.isdigit():
            idx = int(message_clean) - 1
            if 0 <= idx < len(available_rooms):
                selected_room = available_rooms[idx]
        
        # 方法2: 房型名稱匹配
        if not selected_room:
            for room in available_rooms:
                name = room.get('room_type_name', '')
                code = room.get('room_type_code', '')
                if name in message or code in message:
                    selected_room = room
                    break
                # 模糊匹配
                if '雙人' in message and '雙人' in name:
                    selected_room = room
                    break
                if '四人' in message and '四人' in name:
                    selected_room = room
                    break
        
        if not selected_room:
            return """抱歉，我沒有找到您選擇的房型。

請從以下房型中選擇：
""" + '\n'.join([f"{i+1}. {r.get('room_type_name', r.get('room_type_code'))}" 
                 for i, r in enumerate(available_rooms)])
        
        # 檢查數量
        available_count = selected_room.get('available_count', 0)
        if room_count > available_count:
            return f"抱歉，{selected_room.get('room_type_name')} 只剩 {available_count} 間，請調整數量。"
        
        # 保存選擇
        session['selected_room'] = selected_room
        session['room_count'] = room_count
        session['state'] = self.STATE_COLLECT_INFO
        
        room_name = selected_room.get('room_type_name', selected_room.get('room_type_code'))
        
        return f"""好的，您選擇了：
🏨 {room_name} x {room_count} 間

請提供以下資訊以完成預訂：
1️⃣ 您的姓名
2️⃣ 聯絡電話
3️⃣ 預計抵達時間

（您可以一次提供，例如：王小明、0912345678、晚上7點）"""
    
    def _handle_info_collection(self, user_id: str, session: Dict, message: str) -> str:
        """收集客人資訊"""
        import re
        
        # 嘗試解析姓名、電話、時間
        # 電話格式：09xxxxxxxx
        phone_match = re.search(r'(09\d{8})', message.replace('-', '').replace(' ', ''))
        if phone_match:
            session['phone'] = phone_match.group(1)
        
        # 時間格式：各種表達方式
        time_patterns = [
            r'(下午\d+點)', r'(晚上\d+點)', r'(傍晚\d+點)', r'(上午\d+點)',
            r'(\d{1,2}[點:：]\d{0,2})', r'(\d{1,2}點)',
            r'(大約\S+)', r'(約\S+點)',
        ]
        for pattern in time_patterns:
            time_match = re.search(pattern, message)
            if time_match:
                session['arrival_time'] = time_match.group(1)
                break
        
        # 姓名：排除電話和時間後的中文/英文
        remaining = message
        if phone_match:
            remaining = remaining.replace(phone_match.group(1), '')
        if session.get('arrival_time'):
            remaining = remaining.replace(session['arrival_time'], '')
        
        # 嘗試提取姓名
        name_match = re.search(r'([一-龥A-Za-z]{2,10})', remaining.replace(',', '').replace('，', '').strip())
        if name_match and not session.get('guest_name'):
            potential_name = name_match.group(1)
            # 排除常見非姓名詞
            exclude_words = ['晚上', '下午', '傍晚', '上午', '點', '間', '房']
            if not any(word in potential_name for word in exclude_words):
                session['guest_name'] = potential_name
        
        # 檢查是否收集完整
        missing = []
        if not session.get('guest_name'):
            missing.append('姓名')
        if not session.get('phone'):
            missing.append('聯絡電話')
        if not session.get('arrival_time'):
            missing.append('預計抵達時間')
        
        if missing:
            return f"請再提供：{'、'.join(missing)}"
        
        # 資訊完整，進入確認階段
        session['state'] = self.STATE_CONFIRM
        
        room = session['selected_room']
        room_name = room.get('room_type_name', room.get('room_type_code'))
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        return f"""📋 請確認預訂資訊：

🏨 房型：{room_name} x {session['room_count']} 間
📅 入住日期：{today}（今日）
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}

請回覆「確認」完成預訂，或「取消」放棄預訂。"""
    
    def _handle_confirmation(self, user_id: str, session: Dict, message: str) -> str:
        """處理預訂確認"""
        message_clean = message.strip().lower()
        
        # 取消
        if any(word in message_clean for word in ['取消', '不要', '算了', '放棄']):
            self.clear_session(user_id)
            return "好的，已取消預訂。如有需要歡迎再次詢問！"
        
        # 確認
        if any(word in message_clean for word in ['確認', '確定', '好', 'ok', '是', '對']):
            return self._create_booking(user_id, session)
        
        return "請回覆「確認」完成預訂，或「取消」放棄預訂。"
    
    def _create_booking(self, user_id: str, session: Dict) -> str:
        """建立預訂"""
        room = session['selected_room']
        
        booking_data = {
            'room_type_code': room.get('room_type_code'),
            'room_type_name': room.get('room_type_name'),
            'room_count': session['room_count'],
            'nights': 1,
            'guest_name': session['guest_name'],
            'phone': session['phone'],
            'arrival_time': session['arrival_time'],
            'line_user_id': user_id,
            'line_display_name': session.get('line_display_name')
        }
        
        result = self.pms_client.create_same_day_booking(booking_data)
        
        if not result or not result.get('success'):
            error_msg = result.get('error', {}).get('message', '系統錯誤') if result else '連線失敗'
            self.clear_session(user_id)
            return f"""抱歉，預訂失敗：{error_msg}

請直接聯繫櫃檯：(08) 882-5631"""
        
        # 成功
        order_id = result.get('data', {}).get('temp_order_id', '未知')
        self.clear_session(user_id)
        
        today = datetime.now().strftime('%Y-%m-%d')
        room_name = room.get('room_type_name', room.get('room_type_code'))
        
        return f"""✅ 預訂成功！

📋 預訂資訊：
━━━━━━━━━━━━━━━
🔢 訂單編號：{order_id}
🏨 房型：{room_name} x {session['room_count']} 間  
📅 入住日期：{today}
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}
━━━━━━━━━━━━━━━

⚠️ 當日預訂注意事項：
• 由於為當日預訂，恕不收取訂金
• 館方保留臨時取消之權利
• 請務必於預定時間抵達飯店櫃檯辦理入住
• 如有任何疑問或行程變動，請告知龜地灣旅棧 LINE 官方帳號

期待您的光臨！🌊"""
    
    def is_in_booking_flow(self, user_id: str) -> bool:
        """
        檢查用戶是否在預訂流程中
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            True 如果用戶正在進行當日預訂
        """
        session = self.user_sessions.get(user_id)
        if not session:
            return False
        return session.get('state', self.STATE_IDLE) != self.STATE_IDLE
