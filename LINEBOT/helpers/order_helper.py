"""
訂單處理共用輔助方法 (Order Helper)
實作 Single Source of Truth (SSOT) 邏輯，供 bot.py 與各 Handler 統一調用。
"""

import re
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

def get_resume_message(pending_intent: str) -> str:
    """
    取得中斷恢復的統一提示訊息
    """
    messages = {
        'same_day_booking': "━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「加訂需求」，現在立刻為您處理！\n\n請問您今天想再加訂什麼房型呢？",
        'order_query': "━━━━━━━━━━━━━━━\n🔔 您剛剛提到的「查詢訂單」，現在可以為您處理囉！\n\n請提供您的訂單編號或訂房截圖。"
    }
    return messages.get(pending_intent, "")

def sync_order_details(order_id: str, data: Dict[str, Any], logger: Any, pms_client: Any) -> bool:
    """
    統一同步訂單詳情到客訴資料庫 (JSON) 與 SQLite 擴充表。
    確保資訊紀錄的一致性 (SSOT)。
    """
    if not order_id:
        return False
        
    try:
        # 1. 儲存到 guest_orders.json (透過 ChatLogger)
        if logger:
            full_order = {
                'order_id': order_id,
                'guest_name': data.get('guest_name'),
                'phone': data.get('phone'),
                'arrival_time': data.get('arrival_time'),
                'special_requests': data.get('special_requests', []),
                'line_user_id': data.get('line_user_id'),
                'line_display_name': data.get('display_name'),
                'updated_at': datetime.now().isoformat()
            }
            # 保留原有 JSON 中的其他欄位（若有提供）
            for field in ['check_in', 'check_out', 'room_type', 'booking_source']:
                if field in data:
                    full_order[field] = data[field]
                    
            logger.save_order(full_order)
            print(f"✅ [Sync] Order {order_id} saved to JSON")

        # 2. 同步到 SQLite (透過 PMSClient 調用後端 API)
        if pms_client:
            sync_payload = {
                'confirmed_phone': data.get('phone'),
                'arrival_time': data.get('arrival_time'),
                'ai_extracted_requests': "; ".join(data.get('special_requests', [])) if data.get('special_requests') else None,
                'line_name': data.get('display_name')
            }
            pms_client.update_supplement(order_id, sync_payload)
            print(f"✅ [Sync] Order {order_id} synced to SQLite")
            
        return True
    except Exception as e:
        print(f"❌ [Sync] Failed to sync order {order_id}: {e}")
        return False
