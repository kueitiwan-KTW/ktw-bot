"""
訂單查詢處理器
處理有訂單編號的查詢和客人資料收集
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any

from .base_handler import BaseHandler


class OrderQueryHandler(BaseHandler):
    """
    訂單查詢處理器
    
    處理流程:
    1. 用戶提供訂單編號
    2. 查詢 PMS API / Gmail API
    3. 確認訂單資訊
    4. 收集客人資料（電話、抵達時間、特殊需求）
    5. 寫入 guest_orders.json
    """
    
    # 狀態常量
    STATE_IDLE = 'idle'                          # 初始狀態
    STATE_QUERYING = 'querying'                  # 正在查詢
    STATE_CONFIRMING_ORDER = 'confirming_order'  # 確認訂單是否正確
    STATE_COLLECTING_PHONE = 'collecting_phone'  # 收集電話
    STATE_COLLECTING_ARRIVAL = 'collecting_arrival'  # 收集抵達時間
    STATE_COLLECTING_SPECIAL = 'collecting_special'  # 收集特殊需求
    STATE_COMPLETED = 'completed'                # 完成
    
    def __init__(self, pms_client, gmail_helper, logger):
        """
        初始化處理器
        
        Args:
            pms_client: PMS API 客戶端
            gmail_helper: Gmail 查詢助手
            logger: 對話記錄器
        """
        super().__init__()
        self.pms_client = pms_client
        self.gmail_helper = gmail_helper
        self.logger = logger
    
    def is_active(self, user_id: str) -> bool:
        """檢查用戶是否在訂單查詢流程中"""
        session = self.user_sessions.get(user_id)
        if not session:
            return False
        return session.get('state', self.STATE_IDLE) != self.STATE_IDLE
    
    def is_completed(self, user_id: str) -> bool:
        """檢查是否完成流程"""
        session = self.user_sessions.get(user_id)
        if not session:
            return False
        return session.get('state') == self.STATE_COMPLETED
    
    def _create_default_session(self) -> Dict[str, Any]:
        """建立預設 session"""
        return {
            'state': self.STATE_IDLE,
            'order_id': None,
            'order_data': None,
            'phone': None,
            'arrival_time': None,
            'special_requests': [],
            'created_at': datetime.now().isoformat()
        }
    
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """處理訊息"""
        session = self.get_session(user_id)
        state = session['state']
        
        # 儲存 display_name
        if display_name:
            session['display_name'] = display_name
        
        if state == self.STATE_IDLE:
            # 提取訂單編號並查詢
            order_id = self._extract_order_number(message)
            if order_id:
                return self._query_order(user_id, order_id)
            return None
        
        elif state == self.STATE_CONFIRMING_ORDER:
            return self._handle_order_confirmation(user_id, message)
        
        elif state == self.STATE_COLLECTING_PHONE:
            return self._handle_phone_collection(user_id, message)
        
        elif state == self.STATE_COLLECTING_ARRIVAL:
            return self._handle_arrival_collection(user_id, message)
        
        elif state == self.STATE_COLLECTING_SPECIAL:
            return self._handle_special_requests(user_id, message)
        
        return None
    
    def _extract_order_number(self, message: str) -> Optional[str]:
        """從訊息中提取訂單編號"""
        # 清理並提取數字
        clean_message = message.replace('-', '').replace(' ', '')
        
        # 移除可能的前綴 (RMAG, RMPGP 等)
        clean_message = re.sub(r'^[A-Z]+', '', clean_message)
        
        # 找 5 位數以上的數字
        match = re.search(r'\b(\d{5,})\b', clean_message)
        if match:
            return match.group(1)
        return None
    
    def _query_order(self, user_id: str, order_id: str) -> str:
        """查詢訂單"""
        session = self.get_session(user_id)
        session['order_id'] = order_id
        session['state'] = self.STATE_QUERYING
        
        # 1. 嘗試 PMS API
        result = self._query_pms(order_id)
        
        # 2. 若 PMS 找不到，嘗試 Gmail
        if not result:
            result = self._query_gmail(order_id)
        
        if result:
            session['order_data'] = result
            session['state'] = self.STATE_CONFIRMING_ORDER
            
            # 格式化訂單資訊
            details = self._format_order_details(result)
            return f"""📋 我幫您找到了這筆訂單：

{details}

請問是這筆訂單嗎？"""
        
        else:
            # 找不到訂單
            self.clear_session(user_id)
            return f"""抱歉，找不到訂單編號 {order_id}。

請確認是否輸入正確？您可以再提供一次訂單編號，或傳送訂單截圖讓我幫您查詢。"""
    
    def _query_pms(self, order_id: str) -> Optional[Dict]:
        """查詢 PMS API"""
        try:
            result = self.pms_client.get_booking_details(order_id)
            if result and result.get('success'):
                return result.get('data')
        except Exception as e:
            print(f"❌ PMS API 查詢失敗: {e}")
        return None
    
    def _query_gmail(self, order_id: str) -> Optional[Dict]:
        """查詢 Gmail API"""
        try:
            result = self.gmail_helper.search_order(order_id)
            if result:
                # 轉換為標準格式
                return self._parse_gmail_result(result, order_id)
        except Exception as e:
            print(f"❌ Gmail API 查詢失敗: {e}")
        return None
    
    def _parse_gmail_result(self, email_data: Dict, order_id: str) -> Dict:
        """解析 Gmail 結果為標準格式"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        # 從郵件內容提取資訊
        guest_name = self._extract_guest_name(body)
        check_in = self._extract_date(body, 'Check-in|入住')
        check_out = self._extract_date(body, 'Check-out|退房')
        room_type = self._extract_room_type(body)
        booking_source = self._detect_booking_source(subject, body)
        
        return {
            'order_id': order_id,
            'guest_name': guest_name,
            'check_in': check_in,
            'check_out': check_out,
            'room_type': room_type,
            'booking_source': booking_source,
            'source': 'gmail'
        }
    
    def _format_order_details(self, order_data: Dict) -> str:
        """格式化訂單資訊"""
        lines = []
        
        if order_data.get('order_id'):
            lines.append(f"📌 訂單編號: {order_data['order_id']}")
        
        if order_data.get('guest_name'):
            lines.append(f"👤 訂房人姓名: {order_data['guest_name']}")
        
        if order_data.get('check_in'):
            check_in = order_data['check_in']
            check_out = order_data.get('check_out', '')
            lines.append(f"📅 入住日期: {check_in}")
            if check_out:
                lines.append(f"📅 退房日期: {check_out}")
        
        if order_data.get('room_type'):
            lines.append(f"🏨 房型: {order_data['room_type']}")
        
        if order_data.get('room_count'):
            lines.append(f"🔢 數量: {order_data['room_count']} 間")
        
        if order_data.get('booking_source'):
            lines.append(f"📱 訂房來源: {order_data['booking_source']}")
        
        return '\n'.join(lines)
    
    def _handle_order_confirmation(self, user_id: str, message: str) -> str:
        """處理訂單確認"""
        session = self.get_session(user_id)
        message_lower = message.lower().strip()
        
        # 確認關鍵字
        confirm_keywords = ['是', '對', '正確', 'yes', '沒錯', '對的', '確認']
        deny_keywords = ['不是', '不對', '錯', 'no', '否', '重新', '再查']
        
        if any(kw in message_lower for kw in confirm_keywords):
            # 確認正確，開始收集資訊
            return self._start_collecting_info(user_id)
        
        elif any(kw in message_lower for kw in deny_keywords):
            # 不是這筆訂單
            self.clear_session(user_id)
            return "好的，請重新提供正確的訂單編號。"
        
        # 如果收到新的訂單編號
        new_order_id = self._extract_order_number(message)
        if new_order_id:
            return self._query_order(user_id, new_order_id)
        
        return "請問是這筆訂單嗎？請回覆「是」或「不是」。"
    
    def _start_collecting_info(self, user_id: str) -> str:
        """開始收集客人資訊"""
        session = self.get_session(user_id)
        order_data = session.get('order_data', {})
        
        # 檢查訂單中是否已有電話
        existing_phone = order_data.get('phone') or order_data.get('contact_phone')
        
        if existing_phone:
            session['phone'] = existing_phone
            session['state'] = self.STATE_COLLECTING_ARRIVAL
            return f"""好的！系統顯示您的聯絡電話為 {existing_phone}。

請問您預計幾點抵達呢？（例如：下午3點、晚上7點）"""
        else:
            session['state'] = self.STATE_COLLECTING_PHONE
            return """好的！系統顯示您的訂單缺少聯絡電話。

請問方便提供您的聯絡電話嗎？"""
    
    def _handle_phone_collection(self, user_id: str, message: str) -> str:
        """處理電話收集"""
        session = self.get_session(user_id)
        
        # 提取電話號碼
        phone = self._extract_phone(message)
        
        if phone:
            session['phone'] = phone
            session['state'] = self.STATE_COLLECTING_ARRIVAL
            
            # 儲存到資料庫
            self._save_guest_info(user_id, 'phone', phone)
            
            return f"""好的，已記錄您的電話: {phone}

請問您預計幾點抵達呢？（例如：下午3點、晚上7點）"""
        else:
            return "請提供有效的手機號碼（例如：0912345678）"
    
    def _handle_arrival_collection(self, user_id: str, message: str) -> str:
        """處理抵達時間收集"""
        session = self.get_session(user_id)
        
        # 儲存抵達時間
        session['arrival_time'] = message
        self._save_guest_info(user_id, 'arrival_time', message)
        
        # 檢查時間是否明確
        if self._is_vague_time(message):
            return f"""好的，了解您大約{message}會抵達。

為了更準確安排，請問大約是幾點呢？（例如：下午2點、3點左右）"""
        
        session['state'] = self.STATE_COLLECTING_SPECIAL
        return """好的，已記錄您的抵達時間！

請問有什麼特殊需求嗎？（例如：嬰兒床、消毒鍋、嬰兒澡盆、高樓層、禁菸房等）

如果沒有特殊需求，請回覆「沒有」。"""
    
    def _handle_special_requests(self, user_id: str, message: str) -> str:
        """處理特殊需求"""
        session = self.get_session(user_id)
        message_lower = message.lower().strip()
        
        # 無特殊需求
        no_request_keywords = ['沒有', '無', '不用', '沒', '不需要', 'no']
        if any(kw in message_lower for kw in no_request_keywords):
            return self._complete_collection(user_id)
        
        # 有特殊需求，儲存
        session['special_requests'].append(message)
        self._save_guest_info(user_id, 'special_need', message)
        
        return """好的，已為您記錄！

還有其他需求嗎？如果沒有，請回覆「沒有」。"""
    
    def _complete_collection(self, user_id: str) -> str:
        """完成資料收集"""
        session = self.get_session(user_id)
        session['state'] = self.STATE_COMPLETED
        
        # 儲存到 guest_orders.json
        self._save_to_guest_orders(user_id, session)
        
        order_data = session.get('order_data', {})
        arrival_time = session.get('arrival_time', '未提供')
        phone = session.get('phone', '未提供')
        special = '、'.join(session.get('special_requests', [])) or '無'
        
        response = f"""✅ 已為您完成預訂資訊確認！

📋 預訂摘要：
• 訂單編號: {order_data.get('order_id', '未知')}
• 入住日期: {order_data.get('check_in', '未知')}
• 聯絡電話: {phone}
• 預計抵達: {arrival_time}
• 特殊需求: {special}

📌 環保政策提醒:
配合減塑／環保政策，我們旅館目前不提供任何一次性備品（如小包裝牙刷、牙膏、刮鬍刀、拖鞋等）。

房內仍提供可重複使用的洗沐用品（大瓶裝或壁掛式洗髮乳、沐浴乳）與毛巾等基本用品。

若您習慣使用自己的盥洗用品，建議旅途前記得自備。

謝謝您的理解與配合，一起為環保盡一份心力 🌱

🅿️ 停車流程提醒:
為了讓您的入住流程更順暢，請於抵達當日先至櫃檯辦理入住登記，之後我們的櫃檯人員將會協助引導您前往停車位置 🅿️

感謝您的配合，我們期待為您提供舒適的入住體驗。"""
        
        # 清除 session（但保留訂單資訊供後續使用）
        self.clear_session(user_id)
        
        return response
    
    def _extract_phone(self, message: str) -> Optional[str]:
        """提取電話號碼"""
        # 移除空白和連字符
        clean = message.replace(' ', '').replace('-', '')
        
        # 台灣手機號碼 (09開頭10位)
        match = re.search(r'(09\d{8})', clean)
        if match:
            return match.group(1)
        
        # 其他數字（至少8位）
        match = re.search(r'(\d{8,})', clean)
        if match:
            return match.group(1)
        
        return None
    
    def _is_vague_time(self, time_str: str) -> bool:
        """檢查時間是否模糊"""
        vague_keywords = ['下午', '晚上', '傍晚', '中午', '早上', '上午']
        specific_patterns = [r'\d{1,2}[點:：時]', r'\d{1,2}pm', r'\d{1,2}am']
        
        # 如果有具體數字時間，不是模糊的
        if any(re.search(p, time_str) for p in specific_patterns):
            return False
        
        # 如果只有時段關鍵字，是模糊的
        return any(kw in time_str for kw in vague_keywords)
    
    def _save_guest_info(self, user_id: str, info_type: str, content: str):
        """儲存客人資訊到資料庫"""
        session = self.get_session(user_id)
        order_id = session.get('order_id')
        
        if order_id and self.logger:
            try:
                self.logger.update_order_info(
                    order_id=order_id,
                    info_type=info_type,
                    content=content,
                    line_user_id=user_id
                )
                print(f"✅ 已儲存 {info_type}: {content}")
            except Exception as e:
                print(f"❌ 儲存失敗: {e}")
    
    def _save_to_guest_orders(self, user_id: str, session: Dict):
        """儲存到 guest_orders.json"""
        if not self.logger:
            return
        
        order_data = session.get('order_data', {})
        order_id = session.get('order_id')
        
        if not order_id:
            return
        
        try:
            # 完整的訂單資訊
            full_order = {
                'order_id': order_id,
                'guest_name': order_data.get('guest_name'),
                'check_in': order_data.get('check_in'),
                'check_out': order_data.get('check_out'),
                'room_type': order_data.get('room_type'),
                'booking_source': order_data.get('booking_source'),
                'phone': session.get('phone'),
                'arrival_time': session.get('arrival_time'),
                'special_requests': session.get('special_requests', []),
                'line_user_id': user_id,
                'line_display_name': session.get('display_name'),
                'updated_at': datetime.now().isoformat()
            }
            
            self.logger.save_order(order_id, full_order)
            print(f"✅ 已儲存訂單 {order_id} 到 guest_orders.json")
        except Exception as e:
            print(f"❌ 儲存訂單失敗: {e}")
    
    # ============================================
    # 輔助方法 - 從郵件提取資訊
    # ============================================
    
    def _extract_guest_name(self, body: str) -> str:
        """從郵件內容提取客人姓名"""
        patterns = [
            r'Customer (?:First )?Name[^:]*[:：]\s*([A-Za-z\s]+)',
            r'顧客(?:名)?[^:]*[:：]\s*([A-Za-z\s\u4e00-\u9fff]+)',
            r'Guest[^:]*[:：]\s*([A-Za-z\s]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return '未知'
    
    def _extract_date(self, body: str, keyword: str) -> str:
        """從郵件內容提取日期"""
        pattern = rf'{keyword}[^:]*[:：]?\s*(\d{{1,2}}[-/]\w{{3,}}[-/]\d{{2,4}}|\d{{4}}[-/]\d{{1,2}}[-/]\d{{1,2}})'
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)
        return ''
    
    def _extract_room_type(self, body: str) -> str:
        """從郵件內容提取房型"""
        patterns = [
            r'Room Type[^:]*[:：]\s*([^\n]+)',
            r'房型[^:]*[:：]\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return '未知'
    
    def _detect_booking_source(self, subject: str, body: str) -> str:
        """偵測訂房來源"""
        text = (subject + body).lower()
        
        if 'agoda' in text:
            return 'Agoda'
        elif 'booking.com' in text:
            return 'Booking.com'
        elif 'expedia' in text:
            return 'Expedia'
        elif 'hotels.com' in text:
            return 'Hotels.com'
        elif 'trip.com' in text or 'ctrip' in text:
            return 'Trip.com'
        elif '官網' in text:
            return '官網'
        
        # 從訂單編號前綴判斷
        if 'rmag' in text:
            return 'Agoda'
        elif 'rmpgp' in text:
            return 'Booking.com'
        
        return '其他'
