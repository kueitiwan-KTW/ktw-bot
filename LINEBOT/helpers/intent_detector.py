"""
意圖偵測器 (Intent Detector)

職責：
- 統一所有意圖偵測邏輯
- 避免各 Handler 重複實作
- 提供可測試、可維護的意圖識別

設計原則：
- 使用靜態方法 (Stateless)
- 關鍵字匹配為主，未來可擴充為 AI 判斷
"""

import re
from typing import List


class IntentDetector:
    """統一意圖偵測器"""
    
    @staticmethod
    def has_order_number(message: str) -> bool:
        """
        檢測訂單編號（排除電話號碼）
        
        邏輯：
        1. 排除 09 開頭的 10 位數字（電話號碼）
        2. 檢測不以 0 開頭的 5-10 位數字（訂單編號）
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果包含訂單編號
        """
        # 排除電話號碼（09 開頭的 10 位數）
        if re.search(r'09\d{8}', message):
            return False
        
        # 訂單編號：不以 0 開頭的 5-10 位數字
        return bool(re.search(r'\b[1-9]\d{4,9}\b', message))
    
    @staticmethod
    def is_possible_order_number(message: str) -> bool:
        """
        判斷訊息是否「可能是訂單編號」
        
        核心邏輯：只要不是 0 開頭的數字串，都可能是訂單
        
        原因：
        - 電話都是 0 開頭（09手機、02市話...）
        - 訂單通常不是 0 開頭（如 250277285、1671721966）
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果訊息可能是訂單編號
            
        Examples:
            >>> is_possible_order_number("250277285")
            True  # 不是 0 開頭 → 可能是訂單
            
            >>> is_possible_order_number("0912345678")
            False  # 0 開頭 → 可能是電話
            
            >>> is_possible_order_number("1671721966")
            True  # 不是 0 開頭 → 可能是訂單
        """
        # 清理訊息
        clean = message.strip().replace(' ', '').replace('-', '')
        
        # 只檢查純數字訊息
        if not clean.isdigit():
            return False
        
        # 核心判斷：不是 0 開頭 + 至少 5 位數 = 可能是訂單
        if len(clean) >= 5 and not clean.startswith('0'):
            return True
        
        return False
    
    @staticmethod
    def extract_order_number(message: str) -> str:
        """
        提取訂單編號
        
        Args:
            message: 用戶訊息
            
        Returns:
            訂單編號字串，None 表示未找到
        """
        # 排除電話號碼
        if re.search(r'09\d{8}', message):
            # 嘗試找到非電話的數字
            numbers = re.findall(r'\b[1-9]\d{4,9}\b', message)
            if numbers:
                return numbers[0]
            return None
        
        # 提取訂單編號
        match = re.search(r'\b[1-9]\d{4,9}\b', message)
        return match.group(0) if match else None
    
    @staticmethod
    def is_new_order_query(message: str, current_order_id: str = None) -> bool:
        """
        檢測是否為「新訂單查詢」意圖
        
        用於判斷：當用戶正在一個訂單流程中，是否提到了不同的訂單編號。
        這可能代表用戶想切換到另一筆訂單。
        
        Args:
            message: 用戶訊息
            current_order_id: 目前正在處理的訂單編號（可能包含前綴如 RMPGP）
        
        Returns:
            True 如果偵測到「新的」訂單編號（與 current_order_id 不同）
        
        Examples:
            >>> is_new_order_query("250277285", "250305361")
            True  # 不同的訂單號
            
            >>> is_new_order_query("250305361", "RMPGP250305361")
            False  # 相同訂單（清理後比對）
            
            >>> is_new_order_query("250277285", None)
            True  # 有訂單號，無當前訂單
        """
        # 從訊息中提取訂單編號
        new_order = IntentDetector.extract_order_number(message)
        
        if not new_order:
            return False
        
        # 如果沒有當前訂單，只要有新訂單號就算
        if not current_order_id:
            return True
        
        # 清理並比對：移除常見前綴（RMPGP, RMAG, RMBK...）
        def clean_order_id(order_id: str) -> str:
            """移除 OTA 前綴，只保留數字"""
            if not order_id:
                return ""
            # 移除常見前綴
            import re
            cleaned = re.sub(r'^(RMPGP|RMAG|RMBK|RM[A-Z]{2})', '', order_id)
            # 只保留數字
            return re.sub(r'\D', '', cleaned)
        
        clean_current = clean_order_id(current_order_id)
        clean_new = clean_order_id(new_order)
        
        # 比對：如果清理後的數字不同，則為新訂單
        return clean_new != clean_current
    
    @staticmethod
    def is_booking_intent(message: str) -> bool:
        """
        檢測訂房意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是訂房意圖
        """
        keywords = [
            '訂房', '預訂', '今天住', '今日住', '有房', '還有房',
            '空房', '想住', '要住', '可以住', '今天訂', '今日訂',
            '今天', '今日', '明天', '明日',
            '加訂', '加定', '多訂', '再訂', '多一間', '再一間'
        ]
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def is_same_day_booking_intent(message: str) -> bool:
        """
        檢測當日訂房意圖（強調「今天」）
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果明確提到今天
        """
        keywords = ['今天', '今日', '今晚', '現在']
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def is_query_intent(message: str) -> bool:
        """
        檢測查詢訂單意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是查詢意圖
        """
        keywords = [
            '查訂單', '查詢訂單', '我有訂', '確認訂單', '我的訂單',
            '我訂了', '已經訂', '訂單狀態', '訂單資訊'
        ]
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def is_cancel_intent(message: str) -> bool:
        """
        檢測取消意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是取消意圖
        """
        keywords = [
            '取消', '不要', '算了', '放棄', '不訂', '不定',
            '退訂', '退房', '取消訂房', '取消預訂'
        ]
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def is_interrupt_intent(message: str) -> bool:
        """
        檢測中斷流程意圖
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果用戶想中斷當前流程
        """
        keywords = [
            '不要', '算了', '取消', '停止', '退出',
            '重新開始', '重來', 'reset', 'restart'
        ]
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def is_confirmation(message: str) -> bool:
        """
        檢測確認意圖（是/對/沒錯）
        
        排除禮貌用語（謝謝、感謝等），避免客人道謝被誤判為確認。
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是確認
        """
        # 排除禮貌用語（不應視為確認）
        polite_words = ['謝謝', '感謝', '謝了', '辛苦', '麻煩', '拜託', '多謝', '3q', 'thanks', 'thank']
        message_lower = message.lower().strip()
        if any(pw in message_lower for pw in polite_words):
            return False
        
        keywords = [
            '是', '對', '沒錯', '正確', '確認', 'yes', '好', 'ok', 'OK', 'Yes'
        ]
        # 完全匹配或包含在短訊息中
        return message_lower in keywords or any(kw in message and len(message) <= 10 for kw in keywords)
    
    @staticmethod
    def is_rejection(message: str) -> bool:
        """
        檢測否定意圖（不是/錯了）
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果是否定
        """
        keywords = [
            '不是', '錯', '不對', '不正確', 'no', 'No', 'NO'
        ]
        message_lower = message.lower().strip()
        return message_lower in keywords or any(kw in message and len(message) <= 10 for kw in keywords)
    
    @staticmethod
    def extract_phone_number(message: str, strict: bool = True) -> str:
        """
        提取電話號碼（強化版）
        
        Args:
            message: 用戶訊息
            strict: True = 嚴格模式（只接受台灣電話格式）
                    False = 寬鬆模式（8 位以上數字，向後兼容）
        
        Returns:
            電話號碼字串，None 表示未找到
        """
        # 清理訊息：移除空白、連字符、加號
        clean = message.replace(' ', '').replace('-', '').replace('+', '')
        
        if strict:
            # 嚴格模式：只接受台灣電話格式
            
            # 1. 台灣手機：09 開頭 10 位
            mobile_match = re.search(r'(09\d{8})', clean)
            if mobile_match:
                return mobile_match.group(1)
            
            # 2. 台灣市話：0 開頭 9-10 位（排除 09 手機）
            # 格式：02-xxxxxxxx (台北)、03-xxxxxxx (桃園/新竹)...
            landline_match = re.search(r'(0[2-8]\d{7,8})', clean)
            if landline_match:
                return landline_match.group(1)
            
            # 嚴格模式下，不符合台灣電話格式則返回 None
            return None
        else:
            # 寬鬆模式：8 位以上數字（向後兼容舊邏輯）
            
            # 1. 優先找 09 開頭手機
            mobile_match = re.search(r'(09\d{8})', clean)
            if mobile_match:
                return mobile_match.group(1)
            
            # 2. 其他 8 位以上數字
            match = re.search(r'(\d{8,})', clean)
            return match.group(1) if match else None
    
    @staticmethod
    def is_phone_number(message: str) -> bool:
        """
        判斷訊息是否為有效的電話號碼
        
        使用嚴格模式判斷，只接受台灣電話格式：
        - 手機：09 開頭 10 位數
        - 市話：0X 開頭 9-10 位數
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果訊息包含有效的台灣電話號碼
        """
        return IntentDetector.extract_phone_number(message, strict=True) is not None
    
    @staticmethod
    def is_special_request(message: str) -> bool:
        """
        檢測是否為特殊需求意圖
        
        識別客人提出的特殊要求，如設施需求、房間偏好等。
        
        Args:
            message: 用戶訊息
            
        Returns:
            True 如果訊息包含特殊需求關鍵字
            
        Examples:
            >>> is_special_request("需要嬰兒床")
            True
            
            >>> is_special_request("兩筆訂單能安排鄰近嗎")
            True
            
            >>> is_special_request("好")
            False
        """
        keywords = [
            # 設施需求
            '嬰兒床', '嬰兒澡盆', '消毒鍋', '奶瓶消毒', '澡盆',
            '嬰兒', '寶寶', '小孩',
            # 房間偏好
            '高樓層', '低樓層', '安靜', '禁菸', '禁煙', '吸菸', '吸煙',
            '靠近', '鄰近', '同樓層', '隔壁', '附近', '旁邊',
            '相鄰', '連通', '面海', '海景', '窗戶',
            # 床型需求
            '大床', '小床', '雙人床', '單人床', '加床', '併床',
            '兩張床', '一張床', '床型',
            # 停車相關
            '停車', '車位', '停車場',
            # 寵物相關
            '寵物', '狗', '貓', '毛小孩',
            # 其他服務
            '提前', '提早', '晚退', '延遲退房', 'late checkout',
            '需要', '希望', '能否', '可以嗎', '可不可以', '幫忙', '安排'
        ]
        return any(kw in message for kw in keywords)
    
    @staticmethod
    def extract_special_request(message: str) -> str:
        """
        提取特殊需求內容
        
        從訊息中提取特殊需求的描述，移除可能混入的訂單編號。
        
        Args:
            message: 用戶訊息
            
        Returns:
            清理後的需求內容，None 如果不是特殊需求
            
        Examples:
            >>> extract_special_request("250277285 能安排鄰近嗎")
            "能安排鄰近嗎"
            
            >>> extract_special_request("需要嬰兒床")
            "需要嬰兒床"
        """
        if not IntentDetector.is_special_request(message):
            return None
        
        # 移除訂單編號（避免汙染需求內容）
        clean_message = re.sub(r'\b[1-9]\d{4,9}\b', '', message)
        
        # 移除多餘的標點和空白
        clean_message = re.sub(r'^[\s,，、]+|[\s,，、]+$', '', clean_message)
        
        return clean_message.strip() if clean_message.strip() else message

