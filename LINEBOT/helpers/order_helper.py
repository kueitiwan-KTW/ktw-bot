"""
訂單處理共用輔助方法 (Order Helper)
實作 Single Source of Truth (SSOT) 邏輯，供 bot.py 與各 Handler 統一調用。
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List

# 房型對照表 (SSOT)
ROOM_TYPES = {
    'SD': {'zh': '標準雙人房', 'short': '雙人房'},
    'ST': {'zh': '標準三人房', 'short': '三人房'},
    'SQ': {'zh': '標準四人房', 'short': '四人房'},
    'CD': {'zh': '經典雙人房', 'short': '雙人房'},
    'CQ': {'zh': '經典四人房', 'short': '四人房'},
    'ED': {'zh': '行政雙人房', 'short': '雙人房'},
    'DD': {'zh': '豪華雙人房', 'short': '雙人房'},
    'WD': {'zh': '海景雙人房', 'short': '海景雙人房'},
    'WQ': {'zh': '海景四人房', 'short': '海景四人房'},
    'FM': {'zh': '親子家庭房', 'short': '家庭房'},
    'VD': {'zh': 'VIP 雙人房', 'short': 'VIP 雙人房'},
    'VQ': {'zh': 'VIP 四人房', 'short': 'VIP 四人房'},
    'AD': {'zh': '無障礙雙人房', 'short': '無障礙雙人房'},
    'AQ': {'zh': '無障礙四人房', 'short': '無障礙四人房'},
}

def normalize_phone(phone: Optional[str]) -> str:
    """
    標準化電話號碼
    - 策略：先找 09 開頭的手機號碼，否則提取所有數字並取最後 9 碼補 0
    - 支援處理 886886933912773 → 0933912773 格式
    """
    if not phone:
        return '未提供'
    
    # 移除空白、連字符、加號
    import re
    clean = re.sub(r'[\s\-\+]', '', phone)
    
    # 1. 直接尋找 09 開頭的手機號碼 (10碼)
    phone_match = re.search(r'(09\d{8})', clean)
    if phone_match:
        return phone_match.group(1)
    
    # 2. 提取所有數字，取最後 9 碼加上 0
    digits = re.sub(r'\D', '', clean)
    if len(digits) >= 9:
        return '0' + digits[-9:]
    
    return clean if clean else '未提供'

def clean_ota_id(ota_id: Optional[str]) -> str:
    """
    清理 OTA 編號，移除英文前綴 (RMAG, RMPGP, RM 等)
    """
    if not ota_id:
        return ''
    return re.sub(r'^[A-Z]+', '', ota_id)

def detect_booking_source(remarks: str = "", ota_id: str = "", subject: str = "") -> str:
    """
    偵測訂房來源
    """
    text = (remarks + ota_id + subject).lower()
    
    # 1. 優先從備註/標題關鍵字判斷
    if any(kw in text for kw in ['官網', '網路訂房', '線上訂購', 'rmpgp']):
        return "官網"
    if any(kw in text for kw in ['agoda', 'rmag']):
        return "Agoda"
    if any(kw in text for kw in ['booking.com', 'booking', 'rmbk']):
        return "Booking"
    if 'expedia' in text:
        return "Expedia"
    if 'trip.com' in text or 'ctrip' in text:
        return "Trip.com"
    
    return "其他"

def get_breakfast_info(remarks: str = "", rooms: List[Dict] = None) -> str:
    """
    判斷早餐資訊
    """
    remarks = remarks or ""
    rooms = rooms or []
    
    # 只要備註或任何一間房型提到「不含早」或「無早」，就判定為不含早餐
    if any(kw in remarks for kw in ['不含早', '無早']):
        return "不含早餐"
    
    for room in rooms:
        name = (room.get('room_type_name') or room.get('ROOM_TYPE_NAME') or "").lower()
        if any(kw in name for kw in ['不含早', '無早']):
            return "不含早餐"
            
    return "含早餐"


def format_order_display(order_data: Dict[str, Any]) -> str:
    """
    格式化訂單資訊 - 標準 8 欄位制式格式 (SSOT)
    
    此函數為單一真實來源 (Single Source of Truth)，
    供 LINE Bot、Payload CMS、Admin Dashboard 等系統共用。
    
    必須輸出的 8 個欄位（順序固定）：
    1. 訂單來源
    2. 預約編號
    3. 訂房人姓名
    4. 聯絡電話
    5. 入住日期
    6. 退房日期
    7. 房型
    8. 早餐
    
    Args:
        order_data: 訂單資料字典，需包含以下欄位：
            - ota_booking_id: OTA 訂單編號（可選）
            - order_id: PMS 訂單編號
            - guest_name: 訂房人姓名
            - phone / contact_phone: 聯絡電話
            - check_in: 入住日期
            - check_out: 退房日期
            - nights: 入住晚數（可選）
            - room_type: 房型名稱
            - remarks: 備註（用於判斷早餐）
    
    Returns:
        str: 格式化後的訂單資訊文字
    """
    lines = []
    
    # 1. 訂單來源 (必填)
    ota_id = order_data.get('ota_booking_id', '')
    booking_source = detect_booking_source(
        remarks=order_data.get('remarks', ''),
        ota_id=ota_id
    )
    lines.append(f"訂單來源: {booking_source}")
    
    # 2. 預約編號 (必填)
    pms_id = order_data.get('order_id', '未知')
    display_ota = clean_ota_id(ota_id)
    display_id = display_ota if display_ota else pms_id
    lines.append(f"預約編號: {display_id}")
    
    # 3. 訂房人姓名 (必填，無資料顯示 '未提供')
    guest_name = order_data.get('guest_name') or '未提供'
    lines.append(f"訂房人姓名: {guest_name}")
    
    # 4. 聯絡電話 (必填，無資料顯示 '未提供')
    phone = order_data.get('phone') or order_data.get('contact_phone') or '未提供'
    lines.append(f"聯絡電話: {phone}")
    
    # 5. 入住日期 (必填，無資料顯示 '未提供')
    check_in = order_data.get('check_in') or '未提供'
    lines.append(f"入住日期: {check_in}")
    
    # 6. 退房日期 (必填，無資料顯示 '未提供'，有資料則附加晚數)
    check_out = order_data.get('check_out') or '未提供'
    if check_out != '未提供' and order_data.get('nights'):
        nights = order_data.get('nights', 1)
        lines.append(f"退房日期: {check_out} (共 {nights} 晚)")
    else:
        lines.append(f"退房日期: {check_out}")
    
    # 7. 房型 (必填，無資料顯示 '未知')
    room_type = order_data.get('room_type') or '未知'
    lines.append(f"房型: {room_type}")
    
    # 8. 早餐 (必填，使用 get_breakfast_info 判斷)
    breakfast = get_breakfast_info(
        remarks=order_data.get('remarks', ''),
        rooms=order_data.get('rooms', [])
    )
    lines.append(f"早餐: {breakfast}")
    
    return '\n'.join(lines)


def get_resume_message(pending_intent: str) -> str:
    """
    取得中斷恢復的統一提示訊息
    """
    messages = {
        'same_day_booking': "━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「加訂需求」，現在立刻為您處理！\n\n請問您今天想再加訂什麼房型呢？",
        'order_query': "━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「查詢訂單」，現在可以為您處理囉！\n\n請提供您的訂單編號或訂房截圖。"
    }
    return messages.get(pending_intent, "")


def sync_order_details(order_id: str, data: Dict[str, Any], logger: Any, pms_client: Any, ota_id: str = None) -> bool:
    """
    統一同步訂單詳情到客訴資料庫 (JSON) 與 SQLite 擴充表。
    確保資訊紀錄的一致性 (SSOT)。
    
    🔧 方案 B：OTA ID 與 PMS ID 雙重儲存
    - 當兩個 ID 都存在時，同時存兩份資料
    - 無論用哪個 ID 查詢都能找到
    """
    # 收集所有需要儲存的 ID（去重）
    storage_keys = []
    if ota_id:
        storage_keys.append(ota_id)
        # 也儲存純數字版本
        clean_ota = re.sub(r'^[A-Z]+', '', ota_id)
        if clean_ota != ota_id:
            storage_keys.append(clean_ota)
    if order_id and order_id not in storage_keys:
        storage_keys.append(order_id)
    
    if not storage_keys:
        return False

    try:
        for key in storage_keys:
            # 1. 儲存到 guest_orders.json (透過 ChatLogger)
            if logger:
                full_order = {
                    'order_id': key,
                    'pms_id': order_id,  # 保留 PMS ID 參考
                    'ota_id': ota_id,    # 保留 OTA ID 參考
                    'guest_name': data.get('guest_name'),
                    'phone': data.get('phone'),
                    'arrival_time': data.get('arrival_time'),
                    'special_requests': data.get('special_requests', []),
                    'line_user_id': data.get('line_user_id'),
                    'line_display_name': data.get('display_name'),
                    'updated_at': datetime.now().isoformat()
                }
                for field in ['check_in', 'check_out', 'room_type', 'booking_source']:
                    if field in data:
                        full_order[field] = data[field]
                        
                logger.save_order(full_order)

            # 2. 同步到 SQLite (透過 PMSClient 調用後端 API)
            if pms_client:
                # 🔧 AI 提取需求加入時間戳 [MM/DD HH:MM]
                timestamp = datetime.now().strftime('%m/%d %H:%M')
                special_reqs = data.get('special_requests', [])
                if special_reqs:
                    ai_requests = "; ".join([f"[{timestamp}] {req}" for req in special_reqs])
                else:
                    ai_requests = None
                
                sync_payload = {
                    'confirmed_phone': data.get('phone'),
                    'arrival_time': data.get('arrival_time'),
                    'ai_extracted_requests': ai_requests,
                    'line_name': data.get('display_name')
                }
                pms_client.update_supplement(key, sync_payload)

        
        # 3. 🔧 方案 D：儲存用戶訂單關聯
        if pms_client and data.get('line_user_id') and order_id:
            try:
                pms_client.save_user_order_link(
                    line_user_id=data.get('line_user_id'),
                    pms_id=order_id,
                    ota_id=ota_id,
                    check_in_date=data.get('check_in')
                )
            except Exception as e:
                print(f"⚠️ [Sync] 儲存用戶訂單關聯失敗: {e}")
        
        print(f"✅ [Sync] Order synced to {len(storage_keys)} keys: {storage_keys}")
        return True
    except Exception as e:
        print(f"❌ [Sync] Failed to sync order: {e}")
        return False


# =====================
# 時間格式驗證相關方法
# =====================

# 中文數字對照表
CHINESE_NUMERALS = {
    '零': '0', '〇': '0', '一': '1', '二': '2', '兩': '2',
    '三': '3', '四': '4', '五': '5', '六': '6', '七': '7',
    '八': '8', '九': '9', '十': '10', '十一': '11', '十二': '12'
}

def convert_chinese_numerals(text: str) -> str:
    """
    將中文數字轉換為阿拉伯數字
    
    Examples:
        >>> convert_chinese_numerals("下午三點")
        "下午3點"
        
        >>> convert_chinese_numerals("晚上七點半")
        "晚上7點半"
        
        >>> convert_chinese_numerals("十二點")
        "12點"
    """
    result = text
    
    # 先處理 "十X" 格式（如 十一→11, 十二→12）
    for cn, ar in [('十二', '12'), ('十一', '11'), ('十', '10')]:
        result = result.replace(cn, ar)
    
    # 再處理單個中文數字
    for cn, ar in CHINESE_NUMERALS.items():
        if cn not in ['十', '十一', '十二']:  # 避免重複處理
            result = result.replace(cn, ar)
    
    return result

def is_valid_time_format(time_str: str) -> bool:
    """
    檢查是否為有效的時間格式
    
    支援格式：
    - 時間關鍵字：點、時、:、上午、下午、中午、晚上、傍晚、早上
    - 數字時間：14:00、15:30
    - 相對時間：等一下、馬上、待會
    
    不接受：
    - 純數字（可能是訂單編號）：250277285
    - 日期格式：12/25、2025-01-01
    
    Args:
        time_str: 用戶輸入的時間字串
        
    Returns:
        True 如果是有效的時間格式
    """
    # 清理輸入
    clean = time_str.strip()
    
    # 排除：純數字（8 位以上可能是訂單編號）
    digits_only = re.sub(r'\D', '', clean)
    if digits_only and len(digits_only) >= 8:
        return False
    
    # 排除：日期格式
    if re.search(r'\d{1,2}/\d{1,2}', clean) or re.search(r'\d{4}-\d{2}-\d{2}', clean):
        return False
    
    # 時間關鍵字白名單（先用原始訊息匹配，避免「等一下」變「等1下」）
    time_keywords = [
        '點', '時', ':', 
        '上午', '下午', '中午', '晚上', '傍晚', '早上', '凌晨',
        '等一下', '等下', '馬上', '待會', '稀候', '稍後', '現在',
        '左右', '前後', '大約', '約'
    ]
    
    # 先用原始訊息匹配
    if any(kw in clean for kw in time_keywords):
        return True
    
    # 再轉換中文數字後匹配（處理「三點」變「3點」）
    normalized = convert_chinese_numerals(clean)
    if any(kw in normalized for kw in time_keywords):
        return True
    
    # 檢查 24 小時格式：14:00、3:30
    if re.search(r'\d{1,2}:\d{2}', normalized):
        return True
    
    return False

def validate_arrival_time(time_str: str) -> Optional[str]:
    """
    驗證並標準化抵達時間
    
    流程：
    1. 檢查是否為訂單編號（誤判）→ 返回 None
    2. 檢查是否為有效時間格式 → 返回標準化的時間
    
    Args:
        time_str: 用戶輸入的時間字串
        
    Returns:
        標準化後的時間字串，None 表示無效（不是時間）
        
    Examples:
        >>> validate_arrival_time("下午三點")
        "下午3點"  # 中文轉阿拉伯數字
        
        >>> validate_arrival_time("250277285")
        None  # 這是訂單號，不是時間
        
        >>> validate_arrival_time("14:00")
        "14:00"
    """
    if not time_str:
        return None
    
    # 1. 檢查是否為有效時間格式
    if not is_valid_time_format(time_str):
        return None
    
    # 2. 標準化：轉換中文數字
    normalized = convert_chinese_numerals(time_str.strip())
    
    # 3. 清理多餘空白
    normalized = ' '.join(normalized.split())
    
    return normalized

def is_vague_time(time_str: str) -> bool:
    """
    檢查時間是否模糊（需要進一步確認具體時間）
    
    模糊時間範例：下午、晚上、傍晚（沒有具體幾點）
    具體時間範例：下午3點、晚上7點、14:00
    
    Args:
        time_str: 用戶輸入的時間字串
        
    Returns:
        True 如果時間模糊，需要追問具體時間
    """
    if not time_str:
        return True
    
    # 先標準化
    normalized = convert_chinese_numerals(time_str)
    
    # 模糊關鍵字（只有時段，沒有具體時間）
    vague_keywords = ['下午', '上午', '晚上', '傍晚', '早上', '中午', '凌晨']
    
    # 具體時間指標
    specific_indicators = ['點', '時', ':']
    
    # 如果有模糊關鍵字但沒有具體時間指標 → 模糊
    has_vague = any(kw in normalized for kw in vague_keywords)
    has_specific = any(ind in normalized for ind in specific_indicators)
    
    # 特殊情況：「等一下」「馬上」「待會」視為具體（表示很快到）
    soon_keywords = ['等一下', '馬上', '待會', '稍後', '現在', '快到']
    if any(kw in normalized for kw in soon_keywords):
        return False
    
    return has_vague and not has_specific
