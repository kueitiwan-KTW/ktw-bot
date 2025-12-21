"""
Pending Guest Manager - 暫存客人資料管理器

當訂單查不到時，先暫存客人提供的資料（電話、抵達時間等），
之後訂單成功查詢時再自動匹配並合併。

暫存期限：7 天
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class PendingGuestManager:
    """暫存客人資料管理器"""
    
    # 暫存期限（天）
    EXPIRY_DAYS = 7
    
    def __init__(self, data_dir: Optional[str] = None):
        """初始化"""
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            data_dir = os.path.join(project_root, "data")
        
        self.data_file = os.path.join(data_dir, "pending_guests.json")
        self._ensure_file_exists()
        
        # 啟動時清理過期資料
        self._cleanup_expired()
    
    def _ensure_file_exists(self):
        """確保暫存檔案存在"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_data(self) -> Dict:
        """載入暫存資料"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_data(self, data: Dict):
        """儲存暫存資料"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _cleanup_expired(self):
        """清理過期的暫存資料"""
        data = self._load_data()
        now = datetime.now()
        cutoff = now - timedelta(days=self.EXPIRY_DAYS)
        
        expired_keys = []
        for key, value in data.items():
            created_at = datetime.strptime(value.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            if created_at < cutoff:
                expired_keys.append(key)
        
        if expired_keys:
            for key in expired_keys:
                del data[key]
            self._save_data(data)
            print(f"🗑️ 已清理 {len(expired_keys)} 筆過期的暫存資料")
    
    def save_pending(self, user_id: str, order_id: str, guest_name: str = "",
                     phone: str = "", arrival_time: str = "", 
                     special_requests: str = "") -> bool:
        """
        儲存暫存資料
        
        Args:
            user_id: LINE 用戶 ID
            order_id: 客人提供的訂單號
            guest_name: 客人姓名
            phone: 聯絡電話
            arrival_time: 預計抵達時間
            special_requests: 特殊需求
        
        Returns:
            儲存成功返回 True
        """
        data = self._load_data()
        
        key = f"{user_id}:{order_id}"
        
        # 如果已存在，合併資料（保留非空值）
        existing = data.get(key, {})
        
        data[key] = {
            "user_id": user_id,
            "provided_order_id": order_id,
            "guest_name": guest_name or existing.get('guest_name', ''),
            "phone": phone or existing.get('phone', ''),
            "arrival_time": arrival_time or existing.get('arrival_time', ''),
            "special_requests": special_requests or existing.get('special_requests', ''),
            "created_at": existing.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "status": "pending"
        }
        
        self._save_data(data)
        print(f"📝 已暫存客人資料: user={user_id[:12]}..., order={order_id}")
        return True
    
    def find_pending(self, user_id: str, ota_booking_id: str) -> Optional[Dict]:
        """
        尋找匹配的暫存資料
        
        匹配條件：
        1. 同一 user_id
        2. ota_booking_id 包含 provided_order_id
        
        Args:
            user_id: LINE 用戶 ID
            ota_booking_id: PMS 返回的 OTA 訂單號（如 RMAG1671721966）
        
        Returns:
            匹配的暫存資料，無則返回 None
        """
        data = self._load_data()
        
        for key, value in data.items():
            if value.get('status') != 'pending':
                continue
            if value.get('user_id') != user_id:
                continue
            
            provided_id = value.get('provided_order_id', '')
            # 檢查 OTA ID 是否包含客人提供的 ID
            if provided_id and provided_id in (ota_booking_id or ''):
                return value
        
        return None
    
    def mark_matched(self, user_id: str, order_id: str):
        """標記為已匹配"""
        data = self._load_data()
        key = f"{user_id}:{order_id}"
        
        if key in data:
            data[key]['status'] = 'matched'
            data[key]['matched_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_data(data)
            print(f"✅ 已標記暫存資料為已匹配: {key}")
    
    def get_pending_by_user(self, user_id: str) -> Optional[Dict]:
        """取得用戶最新的未匹配暫存資料"""
        data = self._load_data()
        
        pending_list = []
        for key, value in data.items():
            if value.get('user_id') == user_id and value.get('status') == 'pending':
                pending_list.append(value)
        
        if not pending_list:
            return None
        
        # 返回最新的
        return sorted(pending_list, key=lambda x: x.get('updated_at', ''), reverse=True)[0]


# 單例模式
_pending_guest_manager = None

def get_pending_guest_manager() -> PendingGuestManager:
    """取得 PendingGuestManager 單例"""
    global _pending_guest_manager
    if _pending_guest_manager is None:
        _pending_guest_manager = PendingGuestManager()
    return _pending_guest_manager


def retry_pending_matches(pms_client, logger) -> int:
    """
    🔧 方案 C：延遲重試機制
    
    定期重新嘗試匹配暫存資料與 PMS API。
    當之前查無訂單的資料，現在 PMS 已同步時，自動完成關聯。
    
    Args:
        pms_client: PMS API 客戶端
        logger: ChatLogger 實例
    
    Returns:
        成功匹配的數量
    """
    from helpers.order_helper import sync_order_details
    
    manager = get_pending_guest_manager()
    data = manager._load_data()
    
    matched_count = 0
    
    for key, value in list(data.items()):
        if value.get('status') != 'pending':
            continue
        
        order_id = value.get('provided_order_id')
        user_id = value.get('user_id')
        
        if not order_id:
            continue
        
        # 嘗試查詢 PMS
        try:
            result = pms_client.get_booking_details(order_id)
            
            if result and result.get('success'):
                pms_data = result.get('data', {})
                pms_id = pms_data.get('booking_id')
                ota_id = pms_data.get('ota_booking_id', order_id)
                
                print(f"🔄 [Retry] 找到匹配: {order_id} → PMS:{pms_id}")
                
                # 同步資料
                sync_order_details(
                    order_id=pms_id,
                    data={
                        "guest_name": value.get('guest_name'),
                        "phone": value.get('phone'),
                        "arrival_time": value.get('arrival_time'),
                        "line_user_id": user_id,
                        "display_name": value.get('line_display_name'),
                        "special_requests": value.get('special_requests', '').split('; ') if value.get('special_requests') else []
                    },
                    logger=logger,
                    pms_client=pms_client,
                    ota_id=ota_id
                )
                
                # 標記為已匹配
                manager.mark_matched(user_id, order_id)
                matched_count += 1
                
        except Exception as e:
            print(f"⚠️ [Retry] 查詢失敗 {order_id}: {e}")
            continue
    
    if matched_count > 0:
        print(f"✅ [Retry] 本次重試成功匹配 {matched_count} 筆資料")
    
    return matched_count
