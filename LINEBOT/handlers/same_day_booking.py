"""
當日預訂對話狀態機
處理 BOT 當日預訂的多輪對話流程
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os

# 引入共用 Helper
from helpers.intent_detector import IntentDetector
from helpers.order_helper import validate_arrival_time, is_vague_time


class SameDayBookingHandler:
    """
    當日預訂處理器
    
    注意：狀態管理已遷移至 ConversationStateMachine
    """
    
    # 房型對照表（固定顯示的房型，使用 2/3/4 作為編號）
    AVAILABLE_ROOMS = [
        {'code': 'SD', 'name': '標準雙人房', 'price': 2800, 'beds': ['一大床', '兩小床'], 'capacity': 2},
        {'code': 'ST', 'name': '標準三人房', 'price': 3600, 'beds': ['一大床+一小床', '三小床'], 'capacity': 3},
        {'code': 'SQ', 'name': '標準四人房', 'price': 4200, 'beds': ['兩大床', '四小床'], 'capacity': 4}
    ]
    
    # 可升等的房型（依容納人數分類，VIP/家庭房不可升等）
    UPGRADABLE_ROOMS = {
        2: ['SD', 'CD', 'DD', 'ED', 'WD', 'AD'],  # 雙人房可用
        3: ['ST', 'SQ', 'CQ', 'WQ', 'AQ'],         # 三人房可用三人/四人房
        4: ['SQ', 'CQ', 'WQ', 'AQ']                # 四人房可用
    }
    
    # 無障礙房型（需特別告知）
    ACCESSIBLE_ROOMS = ['AD', 'AQ']
    
    # 完整房型對照表
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
    
    def __init__(self, pms_client, state_machine):
        """
        初始化處理器
        
        Args:
            pms_client: PMSClient 實例
            state_machine: 統一對話狀態機
        """
        self.pms_client = pms_client
        self.state_machine = state_machine  # 注入狀態機
        self.user_sessions = {}  # 暫時保留，用於業務資料
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """取得或建立用戶對話 session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'state': 'idle',  # 使用字串常量而非 self.STATE_IDLE
                'available_rooms': [],
                'selected_room': None,
                'room_count': 0,
                'bed_type': None,
                'special_requests': None,
                'guest_name': None,
                'line_display_name': None,
                'guest_phone': None,
                'arrival_time': None,
                'multi_room_orders': [],
                'is_multi_room': False,
                'created_at': datetime.now().isoformat()
            }
        return self.user_sessions[user_id]
    
    def clear_session(self, user_id: str, save_interrupted: bool = False):
        """
        清除用戶 session
        
        Args:
            user_id: LINE 用戶 ID
            save_interrupted: 是否保存中斷資訊到 Dashboard
        """
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            
            # 如果已選擇房型但未完成預訂，保存為中斷狀態
            if save_interrupted and session.get('selected_room') and session.get('state') != self.STATE_IDLE:
                self._save_interrupted_booking(user_id, session)
            
            del self.user_sessions[user_id]
    
    def _save_interrupted_booking(self, user_id: str, session: Dict):
        """保存中斷的預訂資訊到 Dashboard"""
        try:
            # 建構中斷訂單資料
            today = datetime.now().strftime('%Y-%m-%d')
            room = session.get('selected_room') or {}
            
            booking_data = {
                'room_type_code': room.get('code', ''),
                'room_type_name': room.get('name', '未選定'),
                'room_count': session.get('room_count', 1),
                'bed_type': session.get('bed_type'),
                'nights': 1,
                'guest_name': session.get('guest_name', ''),
                'phone': session.get('phone', ''),
                'arrival_time': session.get('arrival_time', ''),
                'line_user_id': user_id,
                'line_display_name': session.get('line_display_name', ''),
                'status': 'interrupted'  # 中斷狀態
            }
            
            # 調用 API 保存中斷訂單
            self.pms_client.create_same_day_booking(booking_data)
            print(f"💔 已保存中斷預訂: {session.get('line_display_name', user_id)}")
            
        except Exception as e:
            print(f"⚠️ 保存中斷預訂失敗: {e}")
    
    def is_booking_intent(self, message: str) -> bool:
        """
        判斷是否為一般訂房意圖（包含當日和未來）
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是訂房意圖
        """
        # 排除：查詢訂單的關鍵字
        exclude_keywords = [
            '我有訂房', '我訂了', '已經訂',
            '確認訂單', '查訂單', '查詢訂單',
            '我的訂單', '訂單查詢'
        ]
        
        if any(kw in message.lower() for kw in exclude_keywords):
            return False
        
        booking_keywords = [
            '訂房', '預訂', '訂', '住', '入住', 
            '有房', '還有房', '空房', '房間',
            '想住', '要住', '可以住'
        ]
        
        message_lower = message.lower()
        return any(kw in message_lower for kw in booking_keywords)
    
    def is_same_day_intent(self, message: str) -> bool:
        """
        判斷是否為當日預訂意圖（已棄用，改用 is_booking_intent）
        
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
    
    def is_cancel_intent(self, message: str) -> bool:
        """
        判斷是否為取消訂單意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是取消意圖
        """
        cancel_keywords = [
            '取消訂單', '取消預訂', '不住了', '不要了',
            '不來了', '取消了', '我要取消', '幫我取消',
            '想取消', '需要取消'
        ]
        return any(kw in message for kw in cancel_keywords)
    
    def _is_interrupt_intent(self, message: str) -> bool:
        """
        判斷是否要中斷當前預訂流程
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果用戶想中斷
        """
        interrupt_keywords = [
            '不用了', '算了', '先不用', '我再想想',
            '下次', '改天', '等等', '稍後', '晚點',
            '謝謝', '謝謝你', '好的謝謝', '感謝',
            '不需要', '暫時不用', '先這樣'
        ]
        return any(kw in message for kw in interrupt_keywords)
    
    def is_within_booking_hours(self) -> bool:
        """
        檢查是否在可預訂時間內（22:00 前）
        
        Returns:
            True 如果在可預訂時間內
        """
        now = datetime.now()
        return now.hour < 22
    
    def _is_invalid_arrival_time(self, arrival_time: str) -> bool:
        """
        檢查抵達時間是否無效（超過晚上10點或已過的時間）
        
        Args:
            arrival_time: 客人輸入的抵達時間字串
            
        Returns:
            True 如果時間無效
        """
        import re
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        # 檢查是否包含隔日關鍵字
        tomorrow_keywords = ['明天', '明日', '隔天', '隔日', '凌晨']
        if any(kw in arrival_time for kw in tomorrow_keywords):
            return True
        
        # 特殊格式：馬上到、等等到、X分鐘後 都視為有效
        if any(kw in arrival_time for kw in ['馬上', '等等', '現在', '待會', '分鐘後']):
            # 但如果已經超過晚上10點，則無效
            if current_hour >= 22:
                return True
            return False
        
        # 嘗試解析小時
        hour_match = re.search(r'(\d{1,2})', arrival_time)
        if not hour_match:
            return False  # 無法解析，交給人工處理
        
        hour = int(hour_match.group(1))
        
        # 判斷上午/下午/晚上
        if '晚上' in arrival_time or '晚間' in arrival_time:
            # 晚上格式：晚上7點=19:00, 晚上10點=22:00
            if hour >= 10:  # 晚上10點以後無效
                return True
        elif '下午' in arrival_time or '傍晚' in arrival_time:
            # 下午轉為24小時制
            if hour < 12:
                hour += 12
            if hour >= 22:
                return True
        elif '上午' in arrival_time or '早上' in arrival_time:
            # 如果已經過了上午時間，則無效
            if hour < current_hour:
                return True
            return False
        elif '中午' in arrival_time:
            if current_hour > 13:  # 已經過了中午
                return True
            return False
        else:
            # 沒有前綴，根據當前時間智能判斷
            # 原則：客人說的時間一定是「未來的時間」
            
            # 24小時制：22-23 和 0-5 無效（太晚或凌晨）
            if hour >= 22 or hour == 0:
                return True
            if 1 <= hour <= 5:
                return True
            
            # 智能判斷：如果說的時間早於現在，可能是指下午/晚上
            # 例如：現在11點，客人說6點 -> 應該是下午6點(18:00)
            if hour < current_hour:
                # 檢查加12小時後是否有效（不超過22點）
                adjusted_hour = hour + 12
                if adjusted_hour >= 22:
                    return True  # 太晚了
                # 否則視為有效（會智能理解為下午）
                return False
            
            # 時間在當前時間之後，直接有效
        
        return False
    
    def _is_vague_arrival_time(self, arrival_time: str) -> bool:
        """
        檢查抵達時間是否模糊（只有時段沒有具體時間）
        
        Args:
            arrival_time: 客人輸入的抵達時間字串
            
        Returns:
            True 如果時間模糊需要再確認
        """
        import re
        
        # 如果只有時段詞，沒有具體數字，就是模糊的
        vague_only_keywords = ['傍晚', '中午', '下午', '晚上', '早上', '上午']
        
        # 檢查是否有數字
        has_number = bool(re.search(r'\d', arrival_time))
        
        if not has_number:
            # 沒有數字，只有時段詞，需要確認
            return any(kw in arrival_time for kw in vague_only_keywords)
        
        return False

    def _is_query_intent(self, message: str) -> bool:
        """偵測查詢意圖"""
        keywords = ['查訂單', '查詢訂單', '我有訂房', '確認訂單', '我的訂單', '我訂了', '已經訂']
        return any(kw in message for kw in keywords)
    
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
        
        # 偵測「跨流程」意圖 (例如在預訂中要查現有訂單)
        state = session['state']
        if state != self.STATE_IDLE and self._is_query_intent(message):
            session['pending_intent'] = 'query'
            return "好的，了解您想查詢現有訂單。為了確保您的預訂完整，請先讓我幫您完成這筆當日預訂的登記，稍後立刻為您查詢唷！"

        # 狀態機處理
        
        if state == self.STATE_IDLE:
            # 檢查是否為取消訂單意圖
            if self.is_cancel_intent(message):
                return self._start_cancel(user_id, session)
            # 檢查是否為訂房意圖（一般性）
            if self.is_booking_intent(message):
                #先檢查是否明確提到「今天」
                if self.is_same_day_intent(message):
                    # 直接進入當日預訂流程
                    return self._start_booking(user_id, session)
                else:
                    # 詢問入住日期
                    self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_ASK_DATE)
                    return """請問您想預訂哪一天入住？

您可以回覆：
• 今天 / 今日
• 明天 / 明日  
• 12/25
• 12月25日

或者告訴我具體的日期！"""
            return None  # 不是當日預訂，交給其他處理器
        
        elif state == self.STATE_ASK_DATE:
            # 處理日期輸入
            return self._handle_date_input(user_id, session, message)
        
        elif state == self.STATE_SHOW_ROOMS:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 等待用戶選擇房型
            return self._handle_room_selection(user_id, session, message)
        
        elif state == self.STATE_COLLECT_COUNT:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 收集房間數量
            return self._handle_count_collection(user_id, session, message)
        
        elif state == self.STATE_COLLECT_BED:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 收集床型
            return self._handle_bed_selection(user_id, session, message)
        
        elif state == self.STATE_MULTI_BED_SELECT:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 多房型逐一選擇床型
            return self._handle_multi_bed_select(user_id, session, message)
        
        elif state == self.STATE_COLLECT_REQUESTS:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 收集特殊需求
            return self._handle_requests_collection(user_id, session, message)
        
        elif state == self.STATE_COLLECT_INFO:
            # 檢查是否要中斷
            if self._is_interrupt_intent(message):
                self.clear_session(user_id, save_interrupted=True)
                return "好的，如有需要隨時再詢問！"
            # 收集客人資訊
            return self._handle_info_collection(user_id, session, message)
        
        elif state == self.STATE_CONFIRM:
            # 確認預訂
            return self._handle_confirmation(user_id, session, message)
        
        elif state == self.STATE_CANCEL_CONFIRM:
            # 確認取消
            return self._handle_cancel_confirmation(user_id, session, message)
        
        return None
    
    def _handle_date_input(self, user_id: str, session: Dict, message: str) -> str:
        """處理日期輸入"""
        import re
        from datetime import datetime, timedelta
        
        message_clean = message.strip()
        today = datetime.now().date()
        
        # 檢查是否為「今天」
        if any(kw in message_clean for kw in ['今天', '今日', '當日', '當天', '現在', '馬上', '立刻']):
            # 進入當日預訂流程
            return self._start_booking(user_id, session)
        
        # 檢查是否為「明天」或未來日期
        if any(kw in message_clean for kw in ['明天', '明日', '後天']):
            self.clear_session(user_id)
            return """感謝您的預訂！

由於您預訂的是未來日期，請透過我們的官網完成預訂：

🌐 線上訂房：https://ktwhotel.com/2cTrT

📋 預訂資訊：
• 入住/退房時間：15:00 入住 / 11:00 退房
• 付款方式：線上刷卡 / 現場付款
• 早餐：含自助式早餐
• 停車：提供免費停車位

如有任何問題，歡迎隨時詢問！"""
        
        # 嘗試解析具體日期（12/25, 12月25日等）
        date_patterns = [
            (r'(\d{1,2})/(\d{1,2})', '%m/%d'),           # 12/25
            (r'(\d{1,2})月(\d{1,2})日?', '%m/%d'),        # 12月25日
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', '%Y/%m/%d'), # 2025/12/25
        ]
        
        for pattern, date_format in date_patterns:
            match = re.search(pattern, message_clean)
            if match:
                try:
                    if len(match.groups()) == 2:
                        # 補上年份
                        month, day = map(int, match.groups())
                        year = today.year
                        # 如果日期已過，視為明年
                        check_date = datetime(year, month, day).date()
                        if check_date < today:
                            year += 1
                        target_date = datetime(year, month, day).date()
                    else:
                        # 完整日期
                        target_date = datetime.strptime(match.group(), date_format).date()
                    
                    # 判斷是否為今天
                    if target_date == today:
                        return self._start_booking(user_id, session)
                    else:
                        # 未來日期
                        self.clear_session(user_id)
                        return f"""感謝您的預訂！

您預訂的日期是：{target_date.strftime('%Y年%m月%d日')}

請透過我們的官網完成預訂：

🌐 線上訂房：https://ktwhotel.com/2cTrT

📋 預訂資訊：
• 入住/退房時間：15:00 入住 / 11:00 退房
• 付款方式：線上刷卡 / 現場付款
• 早餐：含自助式早餐
• 停車：提供免費停車位

如有任何問題，歡迎隨時詢問！"""
                except:
                    pass
        
        # 無法解析日期
        return """抱歉，我無法理解您的日期格式。

請用以下方式回覆：
• 今天 / 今日
• 明天 / 明日
• 12/25
• 12月25日

或者直接告訴我「今天想住」！"""
    
    def _start_booking(self, user_id: str, session: Dict) -> str:
        """開始預訂流程"""
        from datetime import datetime
        
        # 檢查時間
        if not self.is_within_booking_hours():
            self.clear_session(user_id)
            return """抱歉，當日預訂服務僅開放至晚上 8 點。

若您有住宿需求，歡迎透過官網預訂：
🌐 https://ktwhotel.com/2cTrT"""
        
        # 🆕 生成 order_id 並立刻暫存（漸進式暫存）
        order_id = f"WI{datetime.now().strftime('%m%d%H%M')}"
        session['order_id'] = order_id
        
        # 立刻暫存到 PMS（只有 LINE 資訊）
        try:
            self.pms_client.create_same_day_booking({
                'order_id': order_id,
                'line_user_id': user_id,
                'line_display_name': session.get('line_display_name', ''),
                'status': 'incomplete',
                'room_type_code': '',
                'room_count': 0,
                'guest_name': '',
                'phone': '',
                'arrival_time': ''
            })
            print(f"📝 漸進式暫存：已建立 {order_id}")
        except Exception as e:
            print(f"⚠️ 漸進式暫存失敗: {e}")
        
        # 從 API 獲取今日房價
        result = self.pms_client.get_today_availability()
        api_prices = {}
        if result and result.get('success'):
            for room in result.get('data', {}).get('available_room_types', []):
                api_prices[room.get('room_type_code')] = room.get('price', 0)
        
        self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_SHOW_ROOMS)
        
        # 顯示房型列表（使用 API 價格）
        room_list = []
        for room in self.AVAILABLE_ROOMS:
            capacity = room['capacity']
            # 優先使用 API 價格，否則用預設價格
            price = api_prices.get(room['code'], room['price'])
            session[f"price_{room['code']}"] = price  # 保存價格到 session
            room_list.append(f"{capacity}. {room['name']} - NT${price:,}/晚（含早餐）")
        
        return f"""📋 今日可預訂房型：

{chr(10).join(room_list)}

請輸入您想預訂的房型：
• 單一房型：直接輸入編號（如：2）
• 多種房型：輸入組合（如：1間雙人1間三人）"""
    
    def _handle_room_selection(self, user_id: str, session: Dict, message: str) -> str:
        """處理房型選擇（支援單一房型和多房型）"""
        import re
        message_clean = message.strip()
        
        # 嘗試解析多房型輸入（如：1間雙人1間三人、2間雙人房1間四人房）
        multi_room_result = self._parse_multi_room_input(message_clean)
        
        if multi_room_result:
            # 多房型模式
            total_rooms = sum(item['count'] for item in multi_room_result)
            
            # 檢查總數是否超過5間
            if total_rooms >= 5:
                self.clear_session(user_id)
                return """感謝您的訂房需求！

由於您預訂的房間數較多（5間以上），為確保您的權益並享有完整服務，請透過官網預訂：

🌐 https://ktwhotel.com/2cTrT

官網預訂可線上刷卡支付訂金，確保房間保留。感謝您的理解！"""
            
            # 保存多房型選擇
            session['multi_room_orders'] = multi_room_result
            session['is_multi_room'] = True
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
            
            # 直接進入收集資訊階段
            return self._check_multi_room_availability(user_id, session)
        
        # 單一房型模式（數字選擇 2/3/4）
        selected_room = None
        if message_clean.isdigit():
            capacity = int(message_clean)
            for room in self.AVAILABLE_ROOMS:
                if room['capacity'] == capacity:
                    selected_room = room
                    break
        
        if not selected_room:
            room_list = '\n'.join([f"{r['capacity']}. {r['name']}" for r in self.AVAILABLE_ROOMS])
            return f"""抱歉，請輸入正確的格式。

可選房型：
{room_list}

• 單一房型：直接輸入編號（如：2）
• 多種房型：輸入組合（如：1間雙人1間三人）"""
        
        # 單一房型：保存選擇
        session['selected_room'] = selected_room
        session['is_multi_room'] = False
        self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_COUNT)
        
        return f"""好的，您選擇了：{selected_room['name']}

請問需要幾間？（請輸入數字，1-4間）"""
    
    def _parse_multi_room_input(self, message: str) -> list:
        """
        解析多房型輸入
        支援格式：1間雙人1間三人、2間雙人房1間四人房、1雙人2三人、兩間雙人、一間四人
        
        Returns:
            list of {'room': room_dict, 'count': int} or None
        """
        import re
        
        # 中文數字對照
        chinese_numbers = {
            '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        # 房型關鍵字對照
        room_keywords = {
            '雙人': 2,
            '雙人房': 2,
            '兩人': 2,
            '2人': 2,
            '三人': 3,
            '三人房': 3,
            '3人': 3,
            '四人': 4,
            '四人房': 4,
            '4人': 4,
        }
        
        # 嘗試匹配 「數量+間+房型」 模式，支援阿拉伯數字和中文數字
        # 匹配：1間雙人、兩間雙人、2雙人房 等
        pattern = r'([一二兩三四五六七八九十\d]+)\s*間?\s*(雙人房?|兩人|2人|三人房?|3人|四人房?|4人)'
        matches = re.findall(pattern, message)
        
        if not matches:
            return None
        
        results = []
        for count_str, room_type in matches:
            # 解析數量（支援中文數字）
            if count_str in chinese_numbers:
                count = chinese_numbers[count_str]
            elif count_str.isdigit():
                count = int(count_str)
            else:
                continue
                
            if count <= 0:
                continue
                
            capacity = room_keywords.get(room_type)
            if not capacity:
                continue
            
            # 找到對應的房型
            for room in self.AVAILABLE_ROOMS:
                if room['capacity'] == capacity:
                    results.append({
                        'room': room,
                        'count': count
                    })
                    break
        
        return results if results else None
    
    def _check_multi_room_availability(self, user_id: str, session: Dict) -> str:
        """檢查多房型庫存"""
        orders = session.get('multi_room_orders', [])
        
        # 查詢 API 庫存
        result = self.pms_client.get_today_availability()
        
        if not result or not result.get('success'):
            self.clear_session(user_id)
            return """抱歉，目前無法查詢房況，請稍後再試。"""
        
        available_rooms = result.get('data', {}).get('available_room_types', [])
        
        # 建構可用庫存字典
        availability = {}
        for room in available_rooms:
            code = room.get('room_type_code')
            availability[code] = room.get('available_count', 0)
        
        # 檢查每個房型的庫存
        order_lines = []
        total_price = 0
        all_available = True
        
        for order in orders:
            room = order['room']
            count = order['count']
            room_code = room['code']
            price = session.get(f"price_{room_code}", room['price'])
            
            # 取得該房型可升等的總庫存
            capacity = room['capacity']
            upgradable_codes = self.UPGRADABLE_ROOMS.get(capacity, [room_code])
            total_available = sum(availability.get(code, 0) for code in upgradable_codes)
            
            if total_available < count:
                all_available = False
            
            subtotal = price * count
            total_price += subtotal
            order_lines.append(f"• {room['name']} x {count} 間 - NT${subtotal:,}")
        
        if not all_available:
            self.clear_session(user_id)
            return f"""抱歉，目前庫存不足，無法完成您的預訂。

建議您可以查看其他日期的空房：
🌐 https://ktwhotel.com/2cTrT"""
        
        # 庫存充足，顯示確認資訊並進入床型選擇
        session['total_price'] = total_price
        
        # 初始化床型選擇進度
        session['multi_bed_index'] = 0  # 當前要選擇床型的房型索引
        session['multi_bed_types'] = {}  # 儲存每個房型的床型選擇 {idx: bed_type}
        self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_BED)
        
        room_list = "\n".join(order_lines)
        
        # 取得第一個房型的床型選項
        first_order = orders[0]
        first_room = first_order['room']
        beds = first_room.get('beds', [])
        bed_options = "\n".join([f"{i+1}. {bed}" for i, bed in enumerate(beds)])
        
        return f"""好的，已確認您要預訂：

{room_list}
━━━━━━━━━━━━━━━
💰 總計：NT${total_price:,}（含早餐）

🛏️ 請選擇【{first_room['name']}】的床型：
{bed_options}

（請輸入數字選擇）"""
    
    def _handle_count_collection(self, user_id: str, session: Dict, message: str) -> str:
        """處理房間數量收集"""
        message_clean = message.strip()
        
        # 解析數量
        import re
        count_match = re.search(r'(\d+)', message_clean)
        if not count_match:
            return "請輸入數字，例如：1"
        
        room_count = int(count_match.group(1))
        if room_count <= 0:
            return "房間數量需大於 0，請重新輸入。"
        
        # 5間以上請走官網
        if room_count >= 5:
            self.clear_session(user_id)
            return """感謝您的訂房需求！

由於您預訂的房間數較多（5間以上），為確保您的權益並享有完整服務，請透過官網預訂：

🌐 https://ktwhotel.com/2cTrT

官網預訂可線上刷卡支付訂金，確保房間保留。感謝您的理解！"""
        
        session['room_count'] = room_count
        
        # 檢查該房型是否有床型選項
        selected_room = session['selected_room']
        if len(selected_room.get('beds', [])) > 1:
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_BED)
            bed_list = '\n'.join([f"{i+1}. {bed}" for i, bed in enumerate(selected_room['beds'])])
            return f"""請選擇床型：

{bed_list}

請輸入編號（例如：1）"""
        else:
            # 只有一種床型，直接進入下一步
            if selected_room.get('beds'):
                session['bed_type'] = selected_room['beds'][0]
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
            return self._check_availability_and_proceed(user_id, session)
    
    def _handle_bed_selection(self, user_id: str, session: Dict, message: str) -> str:
        """處理床型選擇"""
        message_clean = message.strip()
        selected_room = session['selected_room']
        beds = selected_room.get('beds', [])
        
        # 數字選擇
        if message_clean.isdigit():
            idx = int(message_clean) - 1
            if 0 <= idx < len(beds):
                session['bed_type'] = beds[idx]
                self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
                return self._check_availability_and_proceed(user_id, session)
        
        bed_list = '\n'.join([f"{i+1}. {bed}" for i, bed in enumerate(beds)])
        return f"""請輸入正確的編號。

可選床型：
{bed_list}"""
    
    def _check_availability_and_proceed(self, user_id: str, session: Dict) -> str:
        """檢查庫存並繼續流程"""
        selected_room = session['selected_room']
        room_count = session['room_count']
        capacity = selected_room['capacity']
        
        # 查詢 API 庫存
        result = self.pms_client.get_today_availability()
        
        if not result or not result.get('success'):
            self.clear_session(user_id)
            return """抱歉，目前無法查詢房況，請稍後再試。"""
        
        available_rooms = result.get('data', {}).get('available_room_types', [])
        
        # 取得可升等的房型列表
        upgradable_codes = self.UPGRADABLE_ROOMS.get(capacity, [])
        
        # 計算總可用數量（館內＋網路）
        total_available = 0
        accessible_only = True  # 是否只剩無障礙房
        available_types = []    # 可用的房型列表
        
        for room in available_rooms:
            room_code = room.get('room_type_code')
            if room_code in upgradable_codes:
                count = room.get('available_count', 0)
                if count > 0:
                    total_available += count
                    available_types.append(room_code)
                    if room_code not in self.ACCESSIBLE_ROOMS:
                        accessible_only = False
        
        # 檢查庫存
        if total_available >= room_count:
            # 庫存充足
            bed_info = f" - {session.get('bed_type')}" if session.get('bed_type') else ""
            
            # 如果只剩無障礙房，需要告知
            accessible_notice = ""
            if accessible_only and any(code in self.ACCESSIBLE_ROOMS for code in available_types):
                accessible_notice = "\n\n⚠️ 目前僅剩無障礙房型，此房型只有淋浴間為無障礙設計，其餘房內設施與一般房間相同。"
            
            # 進入特殊需求詢問狀態
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_REQUESTS)
            
            return f"""好的，已確認：
🏨 {selected_room['name']}{bed_info} x {room_count} 間{accessible_notice}

━━━━━━━━━━━━━━━
是否有其他特殊需求？

常見需求：
• 嬰兒床
• 嬰兒澡盆
• 消毒鍋
• 無障礙房

（沒有請輸入「無」或「沒有」，有需求請直接說明）"""
        else:
            # 庫存不足
            self.clear_session(user_id)
            return f"""抱歉，目前{selected_room['name']}已無空房。

建議您可以查看其他日期的空房：
🌐 https://ktwhotel.com/2cTrT"""
    
    def _handle_multi_bed_select(self, user_id: str, session: Dict, message: str) -> str:
        """處理多房型逐一選擇床型"""
        orders = session.get('multi_room_orders', [])
        current_idx = session.get('multi_bed_index', 0)
        
        if current_idx >= len(orders):
            # 所有床型已選擇完成，進入收集資訊階段
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
            return """所有床型已選擇完成！

請提供以下資訊以完成預訂：
1️⃣ 您的姓名
2️⃣ 聯絡電話
3️⃣ 預計抵達時間

（您可以一次提供，例如：王小明、0912345678、晚上7點）"""
        
        current_order = orders[current_idx]
        current_room = current_order['room']
        beds = current_room.get('beds', [])
        
        # 解析用戶選擇的床型
        message_clean = message.strip()
        
        selected_bed = None
        
        # 數字選擇 (1, 2, ...)
        if message_clean.isdigit():
            idx = int(message_clean) - 1
            if 0 <= idx < len(beds):
                selected_bed = beds[idx]
        
        # 也支援直接輸入床型名稱
        if not selected_bed:
            for bed in beds:
                if bed in message or message in bed:
                    selected_bed = bed
                    break
        
        if not selected_bed:
            bed_options = "\n".join([f"{i+1}. {bed}" for i, bed in enumerate(beds)])
            return f"""請選擇有效的床型：
{bed_options}

（請輸入數字選擇）"""
        
        # 儲存床型選擇
        session['multi_bed_types'][current_idx] = selected_bed
        
        # 更新到 orders 中（用於建立訂單時）
        orders[current_idx]['bed_type'] = selected_bed
        
        # 移到下一個房型
        next_idx = current_idx + 1
        session['multi_bed_index'] = next_idx
        
        if next_idx >= len(orders):
            # 所有床型已選擇完成，進入特殊需求詢問
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_REQUESTS)
            
            # 顯示選擇結果摘要
            summary_lines = []
            for i, order in enumerate(orders):
                room_name = order['room']['name']
                bed_type = session['multi_bed_types'].get(i, '預設')
                summary_lines.append(f"• {room_name}: {bed_type}")
            
            return f"""✅ 床型選擇完成！

{chr(10).join(summary_lines)}

━━━━━━━━━━━━━━━
是否有其他特殊需求？

常見需求：
• 嬰兒床
• 嬰兒澡盆
• 消毒鍋
• 無障礙房

（沒有請輸入「無」或「沒有」，有需求請直接說明）"""
        
        # 詢問下一個房型的床型
        next_order = orders[next_idx]
        next_room = next_order['room']
        next_beds = next_room.get('beds', [])
        bed_options = "\n".join([f"{i+1}. {bed}" for i, bed in enumerate(next_beds)])
        
        return f"""✅ {current_room['name']}：{selected_bed}

🛏️ 請選擇【{next_room['name']}】的床型：
{bed_options}

（請輸入數字選擇）"""
    
    def _handle_requests_collection(self, user_id: str, session: Dict, message: str) -> str:
        """收集客人特殊需求"""
        message_clean = message.strip()
        
        # 判斷是否沒有需求
        no_request_keywords = ['無', '沒有', '沒', '不用', '不需要', '無需', 'no', '否']
        has_no_request = any(kw in message_clean.lower() for kw in no_request_keywords)
        
        if has_no_request:
            # 沒有特殊需求
            session['special_requests'] = None
            self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
            return """好的，沒有特殊需求！

請提供以下資訊以完成預訂：
1️⃣ 您的姓名
2️⃣ 聯絡電話
3️⃣ 預計抵達時間

（您可以一次提供，例如：王小明、0912345678、晚上7點）"""
        
        # 有特殊需求，儲存需求內容
        session['special_requests'] = message_clean
        self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_COLLECT_NAME)
        
        return f"""✅ 已記錄您的特殊需求：{message_clean}

請提供以下資訊以完成預訂：
1️⃣ 您的姓名
2️⃣ 聯絡電話
3️⃣ 預計抵達時間

（您可以一次提供，例如：王小明、0912345678、晚上7點）"""
    
    def _handle_info_collection(self, user_id: str, session: Dict, message: str) -> str:
        """收集客人資訊"""
        import re
        
        # 清理訊息
        clean_message = message.replace('-', '').replace(' ', '')
        
        # 1. 嘗試解析電話
        # 先找所有數字開頭的疑似電話（至少 8 位數）
        all_digits_match = re.search(r'(0\d{7,14})', clean_message)
        if all_digits_match and not session.get('phone'):
            potential_phone = all_digits_match.group(1)
            
            # 檢查是否為標準台灣手機格式（09 開頭 10 位）
            if re.match(r'^09\d{8}$', potential_phone):
                # 正確格式
                session['phone'] = potential_phone
            elif potential_phone.startswith('09') and len(potential_phone) != 10:
                # 09 開頭但位數不對，需確認
                session['pending_phone'] = potential_phone
            elif len(potential_phone) >= 8:
                # 其他格式（市話或可能打錯），暫存等待確認
                session['pending_phone'] = potential_phone
        
        # 2. 嘗試解析抵達時間（更寬鬆的格式）
        if not session.get('arrival_time'):
            time_patterns = [
                r'(下午\d+點?半?)', r'(晚上\d+點?半?)', r'(傍晚\d+點?半?)', 
                r'(上午\d+點?半?)', r'(中午\d*點?半?)',
                r'(\d{1,2}[點:：時]\d{0,2})',  # 3點、15:00
                r'(\d{1,2}點半?)',  # 5點、5點半
                r'(\d+分鐘後[到來]?)',  # 10分鐘後到、5分鐘後
                r'(馬上[到來]?)', r'(等等[到來]?)', r'(現在)', r'(待會[兒]?[到來]?)',
            ]
            for pattern in time_patterns:
                time_match = re.search(pattern, message)
                if time_match:
                    session['arrival_time'] = time_match.group(1)
                    break
        
        # 3. 嘗試解析姓名
        if not session.get('guest_name'):
            remaining = message
            if all_digits_match:
                remaining = remaining.replace(all_digits_match.group(0), '')
            if session.get('arrival_time'):
                remaining = remaining.replace(session['arrival_time'], '')
            
            # 清理標點後提取姓名
            remaining = re.sub(r'[,，、。！？\s]', '', remaining)
            name_match = re.search(r'([一-龥A-Za-z]{2,10})', remaining)
            if name_match:
                potential_name = name_match.group(1)
                # 排除非姓名詞
                exclude_words = ['晚上', '下午', '傍晚', '上午', '中午', '點', '間', '房', '好了', '可以', '沒問題']
                if not any(word in potential_name for word in exclude_words):
                    session['guest_name'] = potential_name
        
        # 4. 檢查是否有待確認的電話
        if session.get('pending_phone') and not session.get('phone'):
            pending = session['pending_phone']
            # 檢查用戶是否正在回覆確認
            msg_lower = message.strip().lower()
            if msg_lower in ['是', '對', '正確', 'yes', 'y', '確認', '沒錯']:
                # 用戶確認電話正確
                session['phone'] = pending
                del session['pending_phone']
            elif msg_lower in ['否', '不對', '不是', 'no', 'n', '錯了', '打錯']:
                # 用戶說電話錯了
                del session['pending_phone']
                return "請重新提供您的聯絡電話（手機號碼）"
            else:
                # 還沒確認過，詢問用戶
                if len(pending) != 10:
                    return f"您輸入的電話 {pending} 似乎有 {len(pending)} 位數，台灣手機通常是 10 位數（09 開頭）。\n\n請問這個號碼正確嗎？\n• 正確請回覆「是」\n• 錯誤請回覆「否」並重新提供"
                else:
                    return f"請確認您的電話號碼：{pending}\n• 正確請回覆「是」\n• 錯誤請回覆「否」"
        
        # 5. 檢查缺少的必填資訊並給專業提示
        missing = []
        if not session.get('phone'):
            missing.append('電話')
        if not session.get('arrival_time'):
            missing.append('抵達時間')
        if not session.get('guest_name'):
            missing.append('姓名')
        
        if missing:
            if 'arrival_time' not in [k for k in session.keys() if session.get(k)] and '抵達時間' in missing:
                return "請提供您預計幾點抵達？（例如：下午3點、晚上7點）"
            elif 'phone' not in [k for k in session.keys() if session.get(k)] and '電話' in missing:
                return "請提供您的聯絡電話（手機號碼）"
            elif 'guest_name' not in [k for k in session.keys() if session.get(k)] and '姓名' in missing:
                return "請問您的大名是？"
            return f"請提供：{'、'.join(missing)}"
        
        # 5. 驗證抵達時間是否有效
        arrival_time = session.get('arrival_time', '')
        if self._is_invalid_arrival_time(arrival_time):
            self.clear_session(user_id)
            return """抱歉，當日預訂僅接受今日晚上 10 點前抵達的訂單。

如需隔日入住，請透過官網預訂：
🌐 https://ktwhotel.com/2cTrT"""
        
        # 6. 檢查時間是否模糊，需要再次確認
        if self._is_vague_arrival_time(arrival_time):
            # 標記為需要確認時間
            if not session.get('time_confirmed'):
                session['time_confirmed'] = False
                return f"您說{arrival_time}，請問大約是幾點呢？（例如：3點、下午5點）"
        
        # 資訊完整，進入確認階段
        self.state_machine.transition(user_id, self.state_machine.STATE_BOOKING_CONFIRM)
        
        # 🆕 漸進式更新暫存（資訊已完整，改為 pending）
        order_id = session.get('order_id')
        if order_id:
            try:
                # 取得房型資訊
                if session.get('is_multi_room'):
                    orders = session.get('multi_room_orders', [])
                    room_type_code = ','.join([o['room']['code'] for o in orders])
                    room_type_name = ','.join([o['room']['name'] for o in orders])
                    room_count = sum(o['count'] for o in orders)
                else:
                    room = session.get('selected_room', {})
                    room_type_code = room.get('code', '')
                    room_type_name = room.get('name', '')
                    room_count = session.get('room_count', 1)
                
                self.pms_client.create_same_day_booking({
                    'order_id': order_id,
                    'line_user_id': user_id,
                    'line_display_name': session.get('line_display_name', ''),
                    'status': 'pending',  # 資訊已完整
                    'room_type_code': room_type_code,
                    'room_type_name': room_type_name,
                    'room_count': room_count,
                    'guest_name': session.get('guest_name', ''),
                    'phone': session.get('phone', ''),
                    'arrival_time': session.get('arrival_time', ''),
                    'bed_type': session.get('bed_type', ''),
                    'special_requests': session.get('special_requests', '')
                })
                print(f"📝 漸進式暫存：已更新 {order_id} (pending)")
            except Exception as e:
                print(f"⚠️ 漸進式更新失敗: {e}")
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 根據是否為多房型生成不同的確認訊息
        if session.get('is_multi_room'):
            # 多房型模式
            orders = session.get('multi_room_orders', [])
            room_lines = []
            for order in orders:
                room = order['room']
                count = order['count']
                room_lines.append(f"• {room['name']} x {count} 間")
            
            total_price = session.get('total_price', 0)
            
            return f"""📋 請確認預訂資訊：

🏨 房型：
{chr(10).join(room_lines)}
💰 總計：NT${total_price:,}（含早餐）
📅 入住日期：{today}（今日）
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}
💬 LINE 姓名：{session.get('line_display_name', '未提供')}

請輸入：
1️⃣ 確認預訂
2️⃣ 取消預訂"""
        else:
            # 單一房型模式
            room = session['selected_room']
            room_name = room['name']
            bed_info = f" - {session.get('bed_type')}" if session.get('bed_type') else ""
            
            return f"""📋 請確認預訂資訊：

🏨 房型：{room_name}{bed_info} x {session['room_count']} 間
📅 入住日期：{today}（今日）
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}
💬 LINE 姓名：{session.get('line_display_name', '未提供')}

請輸入：
1️⃣ 確認預訂
2️⃣ 取消預訂"""
    
    def _handle_confirmation(self, user_id: str, session: Dict, message: str) -> str:
        """處理預訂確認"""
        message_clean = message.strip()
        
        # 數字選擇
        if message_clean == '2':
            self.clear_session(user_id)
            return "好的，已取消預訂。如有需要歡迎再次詢問！"
        
        if message_clean == '1':
            return self._create_booking(user_id, session)
        
        return """請輸入：
1️⃣ 確認預訂
2️⃣ 取消預訂"""
    
    def _create_booking(self, user_id: str, session: Dict) -> str:
        """建立預訂（支援單一房型和多房型）"""
        
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 判斷是多房型還是單一房型
        if session.get('is_multi_room'):
            return self._create_multi_room_booking(user_id, session, today, tomorrow)
        else:
            return self._create_single_room_booking(user_id, session, today, tomorrow)
    
    def _create_single_room_booking(self, user_id: str, session: Dict, today: str, tomorrow: str) -> str:
        """建立單一房型預訂"""
        room = session['selected_room']
        
        booking_data = {
            'room_type_code': room.get('code'),
            'room_type_name': room.get('name'),
            'room_count': session['room_count'],
            'bed_type': session.get('bed_type'),
            'nights': 1,
            'guest_name': session['guest_name'],
            'phone': session['phone'],
            'arrival_time': session['arrival_time'],
            'line_user_id': user_id,
            'line_display_name': session.get('line_display_name'),
            'needs_upgrade': session.get('needs_upgrade', False)
        }
        
        result = self.pms_client.create_same_day_booking(booking_data)
        
        if not result or not result.get('success'):
            error_msg = result.get('error', {}).get('message', '系統錯誤') if result else '連線失敗'
            self.clear_session(user_id)
            return f"""抱歉，預訂失敗：{error_msg}

請稍後再試。"""
        
        # 成功
        order_id = result.get('data', {}).get('temp_order_id', '未知')
        room_name = room.get('name')
        bed_info = f" - {session.get('bed_type')}" if session.get('bed_type') else ""
        
        # 寫入 guest_orders.json
        self._save_to_guest_orders(
            order_id=order_id,
            user_id=user_id,
            session=session,
            room=room,
            check_in=today,
            check_out=tomorrow
        )
        
        pending_intent = session.get('pending_intent')
        self.clear_session(user_id)
        
        response = f"""✅ 預訂成功！

📋 預訂資訊：
━━━━━━━━━━━━━━━
🏨 房型：{room_name}{bed_info} x {session['room_count']} 間  
📅 入住日期：{today}
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}
💬 LINE 姓名：{session.get('line_display_name', '未提供')}
━━━━━━━━━━━━━━━

⚠️ 當日預訂注意事項：
• 由於旅棧採預約訂金制，當日或即時預訂無收取訂金，館方保留臨時取消之權利
• 如需確保必能有房間，可採官網預訂線上刷卡支付訂金：https://ktwhotel.com/2cTrT
• 請務必於預定時間抵達飯店櫃檯辦理入住
• 如有更變需取消預訂，務必 LINE 告之

期待您的光臨！🌊"""

        if pending_intent == 'query':
            response += "\n\n━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「查詢現有訂單」，現在立刻為您處理！\n\n請問您的訂單編號是多少呢？"

        return response
    
    def _create_multi_room_booking(self, user_id: str, session: Dict, today: str, tomorrow: str) -> str:
        """建立多房型預訂"""
        orders = session.get('multi_room_orders', [])
        created_orders = []
        room_lines = []
        
        # 生成大訂單 ID（所有房型共用）- 格式：WI+月日時分
        from datetime import datetime
        now = datetime.now()
        order_id = f"WI{now.strftime('%m%d%H%M')}"
        
        for idx, order in enumerate(orders, start=1):
            room = order['room']
            count = order['count']
            
            # 生成小項目 ID（每個房型獨立）
            item_id = f"{order_id}-{idx}"
            
            # 取得床型：優先使用用戶選擇的，沒有則用預設（beds 陣列第一個）
            bed_type = order.get('bed_type') or room.get('beds', [None])[0]
            
            booking_data = {
                'order_id': order_id,           # 大訂單 ID（多房型共用）
                'item_id': item_id,             # 小項目 ID（每房型獨立）
                'room_type_code': room.get('code'),
                'room_type_name': room.get('name'),
                'room_count': count,
                'bed_type': bed_type,           # 用戶選擇或預設床型
                'nights': 1,
                'guest_name': session['guest_name'],
                'phone': session['phone'],
                'arrival_time': session['arrival_time'],
                'special_requests': session.get('special_requests'),  # 客人特殊需求
                'line_user_id': user_id,
                'line_display_name': session.get('line_display_name')
            }
            
            result = self.pms_client.create_same_day_booking(booking_data)
            
            if result and result.get('success'):
                order_id = result.get('data', {}).get('temp_order_id', '未知')
                created_orders.append(order_id)
                
                # 寫入 guest_orders.json
                self._save_to_guest_orders(
                    order_id=order_id,
                    user_id=user_id,
                    session=session,
                    room=room,
                    check_in=today,
                    check_out=tomorrow
                )
            
            room_lines.append(f"• {room['name']} x {count} 間")
        
        if not created_orders:
            self.clear_session(user_id)
            return """抱歉，預訂失敗，請稍後再試。"""
        
        pending_intent = session.get('pending_intent')
        self.clear_session(user_id)
        
        total_price = session.get('total_price', 0)
        
        response = f"""✅ 預訂成功！

📋 預訂資訊：
━━━━━━━━━━━━━━━
🏨 房型：
{chr(10).join(room_lines)}
💰 總計：NT${total_price:,}（含早餐）
📅 入住日期：{today}
👤 姓名：{session['guest_name']}
📞 電話：{session['phone']}
🕐 抵達時間：{session['arrival_time']}
💬 LINE 姓名：{session.get('line_display_name', '未提供')}
━━━━━━━━━━━━━━━

⚠️ 當日預訂注意事項：
• 由於旅棧採預約訂金制，當日或即時預訂無收取訂金，館方保留臨時取消之權利
• 如需確保必能有房間，可採官網預訂線上刷卡支付訂金：https://ktwhotel.com/2cTrT
• 請務必於預定時間抵達飯店櫃檯辦理入住
• 如有更變需取消預訂，務必 LINE 告之

期待您的光臨！🌊"""

        if pending_intent == 'query':
            response += "\n\n━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「查詢現有訂單」，現在立刻為您處理！\n\n請問您的訂單編號是多少呢？"

        return response
    
    def _save_to_guest_orders(self, order_id: str, user_id: str, session: Dict, 
                               room: Dict, check_in: str, check_out: str):
        """將當日預訂寫入 guest_orders.json"""
        try:
            # 檔案路徑（從 handlers/ 跳兩層到 LINEBOT/，再到 data/chat_logs/）
            orders_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'chat_logs', 'guest_orders.json')
            
            # 讀取現有資料
            orders = {}
            if os.path.exists(orders_file):
                with open(orders_file, 'r', encoding='utf-8') as f:
                    orders = json.load(f)
            
            # 建立訂單記錄
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            room_code = room.get('code', 'SD')
            room_name = room.get('name', '標準雙人房')
            bed_type = session.get('bed_type', '')
            
            order_data = {
                'order_id': order_id,
                'line_user_id': user_id,
                'line_display_name': session.get('line_display_name', ''),
                'check_in': check_in,
                'check_out': check_out,
                'room_type': f"{room_code}-{room_name}",
                'room_count': session.get('room_count', 1),
                'bed_type': bed_type,
                'guest_name': session.get('guest_name', ''),
                'phone': session.get('phone', ''),
                'arrival_time': session.get('arrival_time', ''),
                'booking_source': 'LINE當日預訂',
                'breakfast': True,  # 當日預訂含早餐
                'created_at': now,
                'updated_at': now,
                'special_requests': [
                    f"[{now}] 當日預訂",
                    f"[{now}] 床型: {bed_type}" if bed_type else None,
                    f"[{now}] arrival_time: {session.get('arrival_time', '')}"
                ]
            }
            
            # 清除 None 值
            order_data['special_requests'] = [r for r in order_data['special_requests'] if r]
            
            # 寫入
            orders[order_id] = order_data
            
            with open(orders_file, 'w', encoding='utf-8') as f:
                json.dump(orders, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已寫入 guest_orders.json: {order_id}")
            
        except Exception as e:
            print(f"⚠️ 寫入 guest_orders.json 失敗: {e}")
    
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
    
    def _start_cancel(self, user_id: str, session: Dict) -> str:
        """開始取消流程"""
        
        # 查詢該用戶的 pending 訂單
        result = self.pms_client.get_same_day_bookings()
        
        if not result or not result.get('success'):
            self.clear_session(user_id)
            return """抱歉，目前無法查詢訂單，請稍後再試。"""
        
        bookings = result.get('data', [])
        
        # 找出該用戶的 pending 或 interrupted 訂單
        user_bookings = [b for b in bookings 
                        if b.get('line_user_id') == user_id 
                        and b.get('status') in ['pending', 'interrupted']]
        
        if not user_bookings:
            self.clear_session(user_id)
            return """您目前沒有待處理的當日訂單。

如有其他問題，請隨時詢問！"""
        
        # 取第一筆（通常只會有一筆）
        booking = user_bookings[0]
        session['cancel_booking'] = booking
        self.state_machine.transition(user_id, self.state_machine.STATE_IDLE)
        
        room_name = booking.get('room_type_name', booking.get('room_type_code', '未知'))
        bed_info = f" - {booking.get('bed_type')}" if booking.get('bed_type') else ""
        status_text = "待入住" if booking.get('status') == 'pending' else "預約中斷"
        
        return f"""📋 您有一筆{status_text}的當日訂單：

🏨 房型：{room_name}{bed_info} x {booking.get('room_count', 1)} 間
👤 姓名：{booking.get('guest_name', '-')}
🕐 預計抵達：{booking.get('arrival_time', '-')}

請問確定要取消嗎？
1️⃣ 確認取消
2️⃣ 保留訂單"""
    
    def _handle_cancel_confirmation(self, user_id: str, session: Dict, message: str) -> str:
        """處理取消確認"""
        message_clean = message.strip()
        
        # 保留訂單
        if message_clean == '2':
            self.clear_session(user_id)
            return "好的，已為您保留訂單。期待您的光臨！🌊"
        
        # 確認取消
        if message_clean == '1':
            return self._execute_cancel(user_id, session)
        
        return """請輸入：
1️⃣ 確認取消
2️⃣ 保留訂單"""
    
    def _execute_cancel(self, user_id: str, session: Dict) -> str:
        """執行取消訂單"""
        booking = session.get('cancel_booking')
        
        if not booking:
            self.clear_session(user_id)
            return "訂單資料遺失，請重新操作。"
        
        order_id = booking.get('temp_order_id')
        
        # 調用取消 API
        result = self.pms_client.cancel_same_day_booking(order_id)
        
        if not result or not result.get('success'):
            error_msg = result.get('error', {}).get('message', '系統錯誤') if result else '連線失敗'
            self.clear_session(user_id)
            return f"""抱歉，取消失敗：{error_msg}

請稍後再試。"""
        
        self.clear_session(user_id)
        
        room_name = booking.get('room_type_name', booking.get('room_type_code'))
        
        return f"""✅ 已為您取消訂單！

📋 已取消的訂單資訊：
━━━━━━━━━━━━━━━
🏨 房型：{room_name}
👤 姓名：{booking.get('guest_name', '-')}
━━━━━━━━━━━━━━━

如有需要隨時歡迎再次預訂！"""
    
    # ============================================
    # AI Function Calling 專用方法 (Phase 3 新增)
    # ============================================
    
    def create_booking_for_ai(
        self,
        user_id: str,
        rooms: str,
        guest_name: str,
        phone: str,
        arrival_time: str,
        bed_type: str = None,
        special_requests: str = None,
        display_name: str = None,
        pending_order_id: str = None  # 沿用之前的 order_id
    ) -> Dict[str, Any]:
        """
        供 AI Function Calling 調用的當日預訂入口
        從 bot.py::create_same_day_booking 遷移而來
        
        Args:
            user_id: LINE 用戶 ID
            rooms: 房型和數量（如「2間雙人房」或「標準雙人房 x 2, 標準四人房 x 1」）
            guest_name: 客人姓名
            phone: 聯絡電話（台灣手機 09xxxxxxxx）
            arrival_time: 預計抵達時間
            bed_type: 床型偏好（可選）
            special_requests: 特殊需求（可選）
            display_name: LINE 顯示名稱
        
        Returns:
            Dict: 訂房結果
        """
        import re
        
        print(f"🔧 Handler: create_booking_for_ai(rooms={rooms}, name={guest_name})")
        
        # 1️⃣ 驗證電話格式
        phone_clean = re.sub(r'[-\s]', '', phone)
        if not re.match(r'^09\d{8}$', phone_clean):
            return {
                "success": False,
                "error": "電話號碼格式錯誤",
                "message": "請提供有效的台灣手機號碼（09 開頭 10 位數）。"
            }
        
        # 2️⃣ 解析房型
        parsed_rooms = self._parse_rooms_for_ai(rooms)
        if not parsed_rooms:
            return {
                "success": False,
                "error": "無法解析房型",
                "message": f"無法解析「{rooms}」。請使用格式如「2間雙人房」或「標準雙人房 x 2」。"
            }
        
        # 3️⃣ 檢查時間
        if not self.is_within_booking_hours():
            return {
                "success": False,
                "error": "已超過預訂時間",
                "message": "抱歉，當日預訂服務僅開放至晚上 10 點。"
            }
        
        # 4️⃣ 記錄訂單
        booking_data = {
            "order_id": pending_order_id,  # 沿用之前的 order_id（如果有）
            "guest_name": guest_name,
            "phone": phone_clean,
            "arrival_time": arrival_time,
            "rooms": parsed_rooms,
            "bed_type": bed_type,
            "special_requests": special_requests,
            "line_user_id": user_id,
            "line_display_name": display_name,
            "booking_time": datetime.now().isoformat()
        }
        
        # 調用 PMS API
        result = self._submit_booking_to_pms(booking_data)
        
        if result.get('success'):
            # 格式化成功訊息
            room_summary = ", ".join([f"{r['name']} x{r['count']}" for r in parsed_rooms])
            total_price = sum(r.get('price', 0) * r['count'] for r in parsed_rooms)
            
            return {
                "success": True,
                "message": f"✅ 預訂成功！",
                "booking_summary": {
                    "guest_name": guest_name,
                    "phone": phone_clean,
                    "rooms": room_summary,
                    "arrival_time": arrival_time,
                    "total_price": total_price
                }
            }
        else:
            return {
                "success": False,
                "error": result.get('error', '系統錯誤'),
                "message": result.get('message', '預訂失敗，請稍後再試。')
            }
    
    def _parse_rooms_for_ai(self, rooms: str) -> list:
        """解析 AI 傳入的房型字串"""
        import re
        
        result = []
        
        # 房型對照表
        room_mapping = {
            '雙人': {'code': 'SD', 'name': '標準雙人房', 'price': 2280},
            '三人': {'code': 'ST', 'name': '標準三人房', 'price': 2880},
            '四人': {'code': 'SQ', 'name': '標準四人房', 'price': 3680},
            '標準雙人': {'code': 'SD', 'name': '標準雙人房', 'price': 2280},
            '標準三人': {'code': 'ST', 'name': '標準三人房', 'price': 2880},
            '標準四人': {'code': 'SQ', 'name': '標準四人房', 'price': 3680},
        }
        
        # 解析格式：「2間雙人房」「雙人房 x 2」「1雙人1三人」
        patterns = [
            r'(\d+)\s*間?\s*(雙人|三人|四人|標準雙人|標準三人|標準四人)',  # 2間雙人
            r'(雙人|三人|四人|標準雙人|標準三人|標準四人)\s*[xX×]\s*(\d+)',  # 雙人 x 2
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, rooms)
            for match in matches:
                if len(match) == 2:
                    if match[0].isdigit():
                        count, room_type = int(match[0]), match[1]
                    else:
                        room_type, count = match[0], int(match[1])
                    
                    if room_type in room_mapping:
                        room_info = room_mapping[room_type].copy()
                        room_info['count'] = count
                        result.append(room_info)
        
        return result if result else None
    
    def _submit_booking_to_pms(self, booking_data: Dict) -> Dict:
        """提交訂單到 PMS（複用現有邏輯）"""
        try:
            # 使用現有的 PMS Client
            rooms = booking_data.get('rooms', [])
            
            for room in rooms:
                # 構建 API 期望的 booking_data 字典
                pms_booking_data = {
                    'room_type_code': room['code'],
                    'room_type_name': room['name'],
                    'room_count': room['count'],
                    'nights': 1,  # 當日預訂
                    'guest_name': booking_data['guest_name'],
                    'phone': booking_data['phone'],
                    'arrival_time': booking_data['arrival_time'],
                    'bed_type': booking_data.get('bed_type'),
                    'special_requests': booking_data.get('special_requests'),
                    'line_user_id': booking_data.get('line_user_id'),
                    'line_display_name': booking_data.get('line_display_name')
                }
                
                result = self.pms_client.create_same_day_booking(pms_booking_data)
                
                if not result or not result.get('success'):
                    return {
                        "success": False,
                        "error": result.get('error', '預訂失敗') if result else '連線失敗'
                    }
            
            return {"success": True}
            
        except Exception as e:
            print(f"❌ PMS 訂房錯誤: {e}")
            return {"success": False, "error": str(e)}

