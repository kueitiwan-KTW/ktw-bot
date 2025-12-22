"""
訂單查詢處理器
處理有訂單編號的查詢和客人資料收集
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from .base_handler import BaseHandler
from helpers.order_helper import (
    ROOM_TYPES, normalize_phone, clean_ota_id, 
    detect_booking_source, get_breakfast_info, get_resume_message,
    sync_order_details, validate_arrival_time, is_vague_time
)
from helpers.intent_detector import IntentDetector


class OrderQueryHandler(BaseHandler):
    """
    訂單查詢處理器
    
    處理流程:
    1. 用戶提供訂單編號
    2. 查詢 PMS API / Gmail API
    3. 確認訂單資訊
    4. 收集客人資料（電話、抵達時間、特殊需求）
    5. 寫入 guest_orders.json
    
    注意：狀態管理已遷移至 ConversationStateMachine
    """
    
    def __init__(self, pms_client, gmail_helper, logger, state_machine):
        """
        初始化處理器
        
        Args:
            pms_client: PMS API 客戶端
            gmail_helper: Gmail 查詢助手
            logger: 對話記錄器
            state_machine: 統一對話狀態機
        """
        super().__init__()
        self.pms_client = pms_client
        self.gmail_helper = gmail_helper
        self.logger = logger
        self.state_machine = state_machine  # 新增：注入狀態機
        
        # 房型對照表 (已遷移至 order_helper.ROOM_TYPES)
        self.room_types = ROOM_TYPES 
    
    def is_active(self, user_id: str) -> bool:
        """檢查用戶是否在訂單查詢流程中"""
        state = self.state_machine.get_state(user_id)
        return state.startswith('order_query')
    
    def is_completed(self, user_id: str) -> bool:
        """檢查是否完成流程"""
        state = self.state_machine.get_state(user_id)
        return state == self.state_machine.STATE_ORDER_QUERY_COMPLETED
    
    
    def handle_message(self, user_id: str, message: str, display_name: str = None) -> Optional[str]:
        """處理訊息"""
        session = self.get_session(user_id)
        state = self.state_machine.get_state(user_id)
        
        # 儲存 display_name
        if display_name:
            session['display_name'] = display_name
            print(f"📝 已儲存 display_name: {display_name}")
        
        # 偵測「跨流程」意圖 (例如在查詢中要加訂)
        if state != 'idle' and self._is_booking_intent(message):
            self.state_machine.set_pending_intent(user_id, 'same_day_booking', message)
            return "好的，了解您有加訂需求。為了確保權益，請先讓我幫您核對完這筆現有訂單的資訊，稍後立刻為您辦理加訂手續唷！"

        if state == 'idle':
            # 提取訂單編號並查詢
            order_id = self._extract_order_number(message)
            if order_id:
                return self._query_order(user_id, order_id)
            return None
        
        elif state == self.state_machine.STATE_ORDER_QUERY_CONFIRMING:
            return self._handle_order_confirmation(user_id, message)
        
        elif state == self.state_machine.STATE_ORDER_QUERY_COLLECTING_PHONE:
            return self._handle_phone_collection(user_id, message)
        
        elif state == self.state_machine.STATE_ORDER_QUERY_COLLECTING_ARRIVAL:
            return self._handle_arrival_collection(user_id, message)
        
        elif state == self.state_machine.STATE_ORDER_QUERY_COLLECTING_SPECIAL:
            return self._handle_special_requests(user_id, message)
        
        return None

    def _normalize_phone(self, phone: str) -> str:
        """標準化電話號碼 (移至 order_helper)"""
        return normalize_phone(phone)

    def _is_booking_intent(self, message: str) -> bool:
        """偵測加訂意圖"""
        keywords = ['加訂', '加定', '多訂', '再訂', '多一間', '再一間']
        return any(kw in message for kw in keywords)
    
    def _extract_order_number(self, message: str) -> Optional[str]:
        """從訊息中提取訂單編號 (已套用 OTA 清理)"""
        # 1. 清理並提取數字
        clean_message = message.replace('-', '').replace(' ', '')
        
        # 2. 移除可能的前綴 (套用共用輔助方法)
        clean_message = clean_ota_id(clean_message)
        
        # 3. 找 5 位數以上的數字
        match = re.search(r'(\d{5,})', clean_message)
        if match:
            return match.group(1)
        return None
    
    def _query_order(self, user_id: str, order_id: str) -> str:
        """查詢訂單"""
        session = self.get_session(user_id)
        session['order_id'] = order_id
        self.state_machine.transition(user_id, self.state_machine.STATE_ORDER_QUERY_CONFIRMING, {'order_id': order_id})
        
        # 1. 嘗試 PMS API
        result = self._query_pms(order_id)
        
        # 2. 若 PMS 找不到，嘗試 Gmail
        if not result:
            result = self._query_gmail(order_id)
        
        if result:
            session['order_data'] = result
            self.state_machine.set_data(user_id, 'order_data', result)
            
            # 格式化訂單資訊
            details = self._format_order_details(result)
            return f"""📋 我幫您找到了這筆訂單：

{details}

請問是這筆訂單嗎？"""
        
        else:
            # 找不到訂單
            # ✨ [修正] 即使找不到訂單，也嘗試從暫存區同步資料到 SQLite/JSON
            # 這是為了讓管理後台能透過 OTA ID 看到 LINE 姓名與需求
            try:
                from helpers.pending_guest import get_pending_guest_manager
                pending_manager = get_pending_guest_manager()
                pending_data = pending_manager.find_pending(user_id, order_id)
                
                if pending_data:
                    print(f"🔗 [Force Sync] 查無訂單但找到暫存資料，正在強制同步: {order_id}")
                    sync_order_details(
                        order_id=order_id,
                        data={
                            "guest_name": pending_data.get('guest_name'),
                            "phone": pending_data.get('phone'),
                            "arrival_time": pending_data.get('arrival_time'),
                            "line_user_id": user_id,
                            "display_name": pending_data.get('line_display_name') or getattr(self, 'current_display_name', None),
                            "special_requests": pending_data.get('special_requests', [])
                        },
                        logger=self.logger,
                        pms_client=self.pms_client,
                        ota_id=order_id  # 🔧 查無訂單時，order_id 本身就是 OTA ID
                    )

            except Exception as e:
                print(f"⚠️ [Force Sync] 執行失敗: {e}")

            self.clear_session(user_id)
            return f"""抱歉，找不到訂單編號 {order_id}。

請確認是否輸入正確？您可以再提供一次訂單編號，或傳送訂單截圖讓我幫您查詢。"""
    
    def _query_pms(self, order_id: str) -> Optional[Dict]:
        """查詢 PMS API"""
        try:
            result = self.pms_client.get_booking_details(order_id)
            if result and result.get('success'):
                # 標準化鍵名：將 PMS 的大寫鍵轉換為處理器使用的格式
                data = result.get('data', {})
                
                # 獲取 OTA 訂單編號（優先使用）
                ota_id = data.get('ota_booking_id') or ''
                pms_id = str(data.get('booking_id') or data.get('BOOKING_ID') or order_id)
                
                # 處理房型：從 rooms 陣列提取房型代碼並轉換，相同房型合併統計
                rooms = data.get('rooms', [])
                room_count_dict = {}  # 用字典統計：{房型中文名: 總數量}
                
                for room in rooms:
                    room_code = (room.get('room_type_code') or room.get('ROOM_TYPE_CODE') or '').strip()
                    room_count = room.get('room_count') or room.get('ROOM_COUNT') or 1
                    
                    # 獲取中文名稱 (從 SSOT 常數獲取)
                    room_meta = self.room_types.get(room_code, {})
                    room_name_zh = room_meta.get('zh', room_code)
                    
                    # 累加相同房型的數量
                    if room_name_zh in room_count_dict:
                        room_count_dict[room_name_zh] += room_count
                    else:
                        room_count_dict[room_name_zh] = room_count
                
                # 格式化為「房型 x數量」列表
                room_types_zh = [f"{name} x{count}" for name, count in room_count_dict.items()]
                
                # 組合姓名：優先使用 Last Name + First Name
                last_name = (data.get('guest_last_name') or data.get('GUEST_LAST_NAME') or '').strip()
                first_name = (data.get('guest_first_name') or data.get('GUEST_FIRST_NAME') or '').strip()
                
                if last_name and first_name:
                    guest_name = f"{last_name}{first_name}"
                else:
                    guest_name = data.get('guest_name') or data.get('GUEST_NAME')
                
                # 兼容性轉換
                return {
                    'order_id': pms_id,  # 內部 ID
                    'ota_booking_id': ota_id,  # OTA 外部編號
                    'guest_name': guest_name,
                    'check_in': data.get('check_in_date') or data.get('CHECK_IN_DATE'),
                    'check_out': data.get('check_out_date') or data.get('CHECK_OUT_DATE'),
                    'nights': data.get('nights') or data.get('NIGHTS') or 1,  # 晚數
                    'phone': self._normalize_phone(data.get('phone') or data.get('PHONE') or data.get('contact_phone') or ''),
                    'room_type': ', '.join(room_types_zh) if room_types_zh else '未知',
                    'remarks': data.get('remarks') or data.get('REMARKS') or '',  # 備註（用於判斷早餐）
                    'booking_source': data.get('booking_source') or data.get('BOOKING_SOURCE'),
                    'source': 'pms'
                }
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
        """格式化訂單資訊（複用 bot.py 邏輯）"""
        
        # 檢查訂單狀態：如果已取消，返回簡化訊息
        status_code = order_data.get('status_code', '').strip()
        status_name = order_data.get('status_name', '')
        
        if status_code == 'D' or '取消' in status_name:
            return """⚠️ 訂單狀態：已取消

此訂單已經取消，無法辦理入住。
如有疑問，請聯繫櫃檯：(03) 832-5700"""
        
        # 正常訂單處理
        lines = []
        
        # OTA 訂單號 (套用清理邏輯)
        ota_id = order_data.get('ota_booking_id', '')
        pms_id = order_data.get('order_id', '未知')
        
        display_ota = clean_ota_id(ota_id)
        display_id = display_ota if display_ota else pms_id
        
        # 訂房來源 (套用共用辨識邏輯)
        booking_source = detect_booking_source(
            remarks=order_data.get('remarks', ''),
            ota_id=ota_id
        )
        
        lines.append(f"訂單來源: {booking_source}")
        lines.append(f"預約編號: {display_id}")
        
        # 訂房人姓名
        if order_data.get('guest_name'):
            lines.append(f"訂房人姓名: {order_data['guest_name']}")
        
        # 聯絡電話
        phone = order_data.get('phone') or order_data.get('contact_phone') or '未提供'
        lines.append(f"聯絡電話: {phone}")
        
        # 日期與晚數
        if order_data.get('check_in'):
            lines.append(f"入住日期: {order_data['check_in']}")
            if order_data.get('check_out'):
                nights = order_data.get('nights', 1)
                lines.append(f"退房日期: {order_data['check_out']} (共 {nights} 晚)")
        
        # 房型（已經在 _query_pms 轉換為中文）
        room_type = order_data.get('room_type', '未知')
        lines.append(f"房型: {room_type}")
        
        # 早餐（從 remarks 判斷）
        remarks = order_data.get('remarks', '') or ''
        breakfast = "含早餐"
        if '不含早' in remarks or '無早' in remarks:
            breakfast = "不含早餐"
        lines.append(f"早餐: {breakfast}")
        
        return '\n'.join(lines)
    
    def _handle_order_confirmation(self, user_id: str, message: str) -> str:
        """處理訂單確認（增強版：加入特殊需求偵測）"""
        session = self.get_session(user_id)
        message_lower = message.lower().strip()
        
        # 1. 確認關鍵字
        if IntentDetector.is_confirmation(message):
            return self._start_collecting_info(user_id)
        
        # 2. 否定關鍵字
        if IntentDetector.is_rejection(message):
            self.clear_session(user_id)
            return "好的，請重新提供正確的訂單編號。"
        
        # 3. ✨ 特殊需求偵測（新增）
        if IntentDetector.is_special_request(message):
            special_req = IntentDetector.extract_special_request(message)
            if special_req:
                # 儲存需求
                if 'special_requests' not in session:
                    session['special_requests'] = []
                session['special_requests'].append(special_req)
                self._save_guest_info(user_id, 'special_need', special_req)
                return f"""好的，已為您記錄：{special_req}

請問這是您的訂單嗎？請回覆「是」或「不是」。"""
        
        # 4. 新訂單編號偵測
        new_order_id = self._extract_order_number(message)
        if new_order_id:
            return self._query_order(user_id, new_order_id)
        
        return "請問是這筆訂單嗎？請回覆「是」或「不是」。"
    
    def _start_collecting_info(self, user_id: str) -> str:
        """開始收集客人資訊 (強制電話確認)"""
        session = self.get_session(user_id)
        order_data = session.get('order_data', {})
        
        # 檢查訂單中是否已有電話
        existing_phone = order_data.get('phone') or order_data.get('contact_phone')
        
        self.state_machine.transition(user_id, self.state_machine.STATE_ORDER_QUERY_COLLECTING_PHONE)
        
        if existing_phone:
            session['phone'] = existing_phone
            return f"""好的！系統顯示您的聯絡電話為 {existing_phone}。

請問這是否為您的正確聯絡電話？如果您想更換，請直接輸入新的電話號碼。"""
        else:
            return """好的！系統顯示您的訂單缺少聯絡電話。

請問方便提供您的聯絡電話嗎？"""
    
    def _handle_phone_collection(self, user_id: str, message: str) -> str:
        """處理電話收集（增強版：AI + Helper 雙層驗證）"""
        session = self.get_session(user_id)
        current_order = session.get('order_id')
        
        # 1️⃣ 先檢查是否為新訂單意圖（優先級更高）
        if IntentDetector.is_new_order_query(message, current_order):
            new_order = IntentDetector.extract_order_number(message)
            # 設定延遲跳轉意圖
            self.state_machine.set_pending_intent(user_id, 'order_query', new_order)
            return f"""偵測到另一筆訂單（{new_order}），稍後為您查詢。

請先提供本筆訂單的聯絡電話。"""
        
        # 2️⃣ 檢查是否為可能的訂單編號（純數字但非 0 開頭）
        if IntentDetector.is_possible_order_number(message):
            # 主動確認意圖
            return f"""請問「{message}」是您的電話號碼，還是另一筆訂單編號呢？

如果是電話，請確認後重新輸入。
如果是訂單編號，請回覆「訂單」。"""
        
        # 3️⃣ 提取電話號碼（使用嚴格模式）
        phone = IntentDetector.extract_phone_number(message, strict=True)
        
        if phone:
            session['phone'] = phone
            self.state_machine.transition(user_id, self.state_machine.STATE_ORDER_QUERY_COLLECTING_ARRIVAL, {'phone': phone})
            self._save_guest_info(user_id, 'phone', phone)
            
            return f"""好的，已記錄您的電話: {phone}

請問您預計幾點抵達呢？（例如：下午3點、晚上7點）"""
        else:
            return "請提供有效的手機號碼（例如：0912345678）"
    
    def _handle_arrival_collection(self, user_id: str, message: str) -> str:
        """處理抵達時間收集（增強版：加入格式驗證與新訂單偵測）"""
        session = self.get_session(user_id)
        current_order = session.get('order_id')
        
        # 1️⃣ 檢查是否為新訂單意圖
        if IntentDetector.is_new_order_query(message, current_order):
            new_order = IntentDetector.extract_order_number(message)
            self.state_machine.set_pending_intent(user_id, 'order_query', new_order)
            return f"""偵測到另一筆訂單（{new_order}），稍後為您查詢。

請先告訴我本筆訂單的抵達時間。"""
        
        # 2️⃣ 驗證時間格式（使用新的 Helper）
        validated_time = validate_arrival_time(message)
        
        if validated_time:
            session['arrival_time'] = validated_time
            self._save_guest_info(user_id, 'arrival_time', validated_time)
            
            # 檢查時間是否模糊（使用新的 Helper）
            if is_vague_time(validated_time):
                return f"""好的，了解您大約{validated_time}會抵達。

為了更準確安排，請問大約是幾點呢？（例如：下午2點、3點左右）"""
            
            self.state_machine.transition(user_id, self.state_machine.STATE_ORDER_QUERY_COLLECTING_SPECIAL, {'arrival_time': validated_time})
            return """好的，已記錄您的抵達時間！

請問有什麼特殊需求嗎？（例如：嬰兒床、消毒鍋、嬰兒澡盆、高樓層、禁菸房等）

如果沒有特殊需求，請回覆「沒有」。"""
        else:
            # 時間格式無效（可能是訂單編號被誤輸入）
            return "請提供有效的抵達時間（例如：下午3點、晚上7點）"
    
    def _handle_special_requests(self, user_id: str, message: str) -> str:
        """處理特殊需求"""
        session = self.get_session(user_id)
        message_lower = message.lower().strip()
        
        # 無特殊需求
        no_request_keywords = ['沒有', '無', '不用', '沒', '不需要', 'no']
        if any(kw in message_lower for kw in no_request_keywords):
            return self._complete_collection(user_id)
        
        # 有特殊需求，儲存
        if 'special_requests' not in session:
            session['special_requests'] = []
        session['special_requests'].append(message)
        self._save_guest_info(user_id, 'special_need', message)
        
        return """好的，已為您記錄！

還有其他需求嗎？如果沒有，請回覆「沒有」。"""
    
    def _complete_collection(self, user_id: str) -> str:
        """完成資料收集 (帶有延遲跳轉處理)"""
        session = self.get_session(user_id)
        self.state_machine.transition(user_id, self.state_machine.STATE_ORDER_QUERY_COMPLETED)
        
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

        # 處理延遲跳轉引導 (套用共用訊息)
        pending_intent = self.state_machine.get_pending_intent(user_id)
        if pending_intent:
            resume_msg = get_resume_message(pending_intent)
            # 執行跳轉
            next_state = self.state_machine.execute_pending_intent(user_id)
            if next_state:
                self.state_machine.transition(user_id, next_state)
                if resume_msg:
                    response += f"\n\n{resume_msg}"
        
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
                self.logger.update_guest_request(
                    order_id=order_id,
                    request_type=info_type,
                    content=content
                )
                print(f"✅ 已儲存 {info_type}: {content}")
            except Exception as e:
                print(f"❌ 儲存失敗: {e}")
    
    def _save_to_guest_orders(self, user_id: str, session: Dict):
        """儲存到客訴資料庫 (JSON) 與 SQLite (套用 SSOT 函數)"""
        order_id = session.get('order_id')
        if not order_id:
            return
            
        # 準備資料
        order_data = session.get('order_data', {})
        sync_data = {
            'guest_name': order_data.get('guest_name'),
            'check_in': order_data.get('check_in'),
            'check_out': order_data.get('check_out'),
            'room_type': order_data.get('room_type'),
            'booking_source': order_data.get('booking_source'),
            'phone': session.get('phone'),
            'arrival_time': session.get('arrival_time'),
            'special_requests': session.get('special_requests', []),
            'line_user_id': user_id,
            'display_name': session.get('display_name')
        }
        
        # 使用統一 SSOT 函數同步
        sync_order_details(
            order_id=order_id,
            data=sync_data,
            logger=self.logger,
            pms_client=self.pms_client,
            ota_id=order_data.get('ota_booking_id')  # 🔧 方案 B：雙重儲存
        )

    
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
        """偵測訂房來源 (套用共用邏輯)"""
        return detect_booking_source(subject=subject, remarks=body)
    
    # ============================================
    # AI Function Calling 專用方法 (Phase 2 新增)
    # ============================================
    
    def query_for_ai(
        self, 
        user_id: str,
        order_id: str, 
        guest_name: str = "",
        phone: str = "",
        user_confirmed: bool = False,
        display_name: str = None
    ) -> Dict[str, Any]:
        """
        供 AI Function Calling 調用的訂單查詢入口
        從 bot.py::check_order_status 遷移而來
        
        Args:
            user_id: LINE 用戶 ID
            order_id: 訂單編號
            guest_name: 客人姓名（可選）
            phone: 電話號碼（可選）
            user_confirmed: 是否已確認訂單
            display_name: LINE 顯示名稱
        
        Returns:
            Dict: 符合 AI 工具規格的回傳格式
            - status: "found", "not_found", "privacy_blocked", "confirmation_needed"
            - formatted_display: 格式化的訂單文字
            - order_data: 訂單原始資料
        """
        print(f"🔧 Handler: query_for_ai(order_id={order_id}, confirmed={user_confirmed})")
        
        # 清理輸入
        order_id = order_id.strip()
        
        # 1️⃣ 隱私攔截
        privacy_result = self._check_privacy(order_id)
        if privacy_result:
            return privacy_result
        
        # 2️⃣ 查詢訂單（PMS 優先，Gmail 備援）
        order_data = self._query_pms(order_id)
        data_source = 'pms' if order_data else None
        
        if not order_data and (len(order_id) >= 10 or not order_id.isdigit()):
            print(f"📧 Falling back to Gmail search...")
            order_data = self._query_gmail(order_id)
            data_source = 'gmail' if order_data else None
        
        # 3️⃣ 找不到訂單
        if not order_data:
            self._handle_not_found_for_ai(user_id, order_id, guest_name, phone)
            return {"status": "not_found", "order_id": order_id}
        
        # 4️⃣ 處理暫存資料匹配
        pending_matched = self._match_pending_data(user_id, order_data, display_name)
        
        # 5️⃣ 確定顯示用的訂單 ID
        pms_id = str(order_data.get('order_id', order_id))
        ota_id = order_data.get('ota_booking_id', '')
        found_id = ota_id if ota_id and (order_id in ota_id or ota_id in order_id) else pms_id
        
        # 6️⃣ 需要確認
        if not user_confirmed:
            result = {
                "status": "confirmation_needed",
                "found_order_id": found_id,
                "message": f"找到訂單 {found_id}，請確認是否正確。"
            }
            if pending_matched:
                result['pending_matched'] = pending_matched
            return result
        
        # 7️⃣ 已確認，回傳完整資訊
        formatted = self._format_order_details(order_data)
        
        # 同步客人資料到 Backend（LINE 姓名、user_id 關聯）
        try:
            sync_order_details(
                order_id=pms_id,
                data={
                    "line_user_id": user_id,
                    "line_display_name": display_name
                },
                logger=self.logger,
                pms_client=self.pms_client,
                ota_id=ota_id
            )
            print(f"✅ [Sync] 用戶 {user_id} 關聯至訂單 {pms_id}")
        except Exception as e:
            print(f"⚠️ [Sync] 同步失敗: {e}")
        
        # 記錄用戶訂單關聯
        if self.logger:
            self.logger.link_order_to_user(found_id, user_id)
        
        return {
            "status": "found",
            "order_id": found_id,
            "formatted_display": formatted,
            "order_data": order_data,
            "data_source": data_source
        }
    
    def _check_privacy(self, order_id: str) -> Optional[Dict]:
        """
        隱私攔截檢查
        攔截日期格式、過短編號等不合法輸入
        """
        # 攔截日期格式
        if re.search(r'\d{1,2}/\d{1,2}', order_id) or re.search(r'\d{4}-\d{2}-\d{2}', order_id):
            print(f"🚫 Privacy Block: Date as ID: {order_id}")
            return {"status": "privacy_blocked", "message": "請提供訂單編號而非日期。"}
        
        # 攔截過短編號
        clean_numeric = re.sub(r'\D', '', order_id)
        if not clean_numeric or len(clean_numeric) < 5:
            print(f"🚫 Privacy Block: Vague ID: {order_id}")
            return {"status": "privacy_blocked", "message": "訂單編號過短或格式不正確。"}
        
        return None
    
    def _handle_not_found_for_ai(self, user_id: str, order_id: str, guest_name: str, phone: str):
        """處理找不到訂單的情況（供 AI 調用）"""
        try:
            from helpers.pending_guest import get_pending_guest_manager
            pending_manager = get_pending_guest_manager()
            pending_manager.save_pending(
                user_id=user_id,
                order_id=order_id,
                guest_name=guest_name,
                phone=phone
            )
        except Exception as e:
            print(f"⚠️ 暫存失敗: {e}")
    
    def _match_pending_data(self, user_id: str, order_data: Dict, display_name: str = None) -> Optional[Dict]:
        """匹配暫存資料並同步"""
        try:
            from helpers.pending_guest import get_pending_guest_manager
            pending_manager = get_pending_guest_manager()
            
            ota_id = order_data.get('ota_booking_id', '')
            pms_id = str(order_data.get('order_id', ''))
            
            pending_data = pending_manager.find_pending(user_id, ota_id or pms_id)
            
            if pending_data:
                print(f"🔗 找到暫存資料: {pending_data}")
                
                # 同步資料
                sync_order_details(
                    order_id=pms_id,
                    data={
                        "guest_name": pending_data.get('guest_name'),
                        "phone": pending_data.get('phone'),
                        "arrival_time": pending_data.get('arrival_time'),
                        "line_user_id": user_id,
                        "line_display_name": pending_data.get('line_display_name') or display_name
                    },
                    logger=self.logger,
                    pms_client=self.pms_client,
                    ota_id=ota_id
                )
                
                pending_manager.mark_matched(user_id, pending_data['provided_order_id'])
                
                return {
                    "phone": pending_data.get('phone', ''),
                    "arrival_time": pending_data.get('arrival_time', ''),
                    "special_requests": pending_data.get('special_requests', ''),
                    "note": f"已自動帶入您之前提供的資料"
                }
        except Exception as e:
            print(f"⚠️ 暫存匹配失敗: {e}")
        
        return None
