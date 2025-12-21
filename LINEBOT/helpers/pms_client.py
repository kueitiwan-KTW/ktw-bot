"""
PMS API Client
用于与 PMS REST API 进行交互，获取订单资料
"""

import os
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# 引入 API Logger
try:
    from helpers.api_logger import get_api_logger
except ImportError:
    from .api_logger import get_api_logger


class PMSClient:
    """PMS REST API 客户端"""
    
    def __init__(self):
        """初始化 PMS 客户端"""
        self.base_url = os.getenv('PMS_API_BASE_URL', 'http://192.168.8.3:3000/api')
        self.timeout = int(os.getenv('PMS_API_TIMEOUT', '5'))
        self.enabled = os.getenv('PMS_API_ENABLED', 'True').lower() == 'true'
        self.api_logger = get_api_logger()
        
        print(f"🔷 PMS Client initialized: base_url={self.base_url}, timeout={self.timeout}s, enabled={self.enabled}")
    
    def get_booking_details(self, booking_id: str, guest_name: Optional[str] = None, 
                            phone: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        獲取訂單詳細資料 (支援組合式驗證)
        
        Args:
            booking_id: 訂單編號
            guest_name: (選填) 訂房人姓名，用於交叉核對
            phone: (選填) 聯絡電話，用於交叉核對
            user_id: (選填) LINE 用戶 ID，用於日誌記錄
            
        Returns:
            訂單資料字典，失敗或資料不匹配返回 None
        """
        import re
        start_time = time.time()
        
        # 記錄查詢開始
        self.api_logger.log_query_start(user_id or "unknown", booking_id, guest_name, phone)
        
        if not self.enabled:
            print("⚠️ PMS API is disabled")
            self.api_logger.log_pms_error("DISABLED", booking_id, 0, "PMS API is disabled")
            return None
        
        try:
            # 清理訂單號
            clean_id = booking_id.strip()
            clean_id = re.sub(r'^[A-Z]+', '', clean_id)
            
            url = f"{self.base_url}/bookings/{clean_id}"
            print(f"📡 PMS API Request: GET {url}")
            self.api_logger.log_pms_request(url)
            
            response = requests.get(url, timeout=self.timeout)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    order_data = data['data']
                    pms_id = order_data.get('booking_id')
                    ota_id = order_data.get('ota_booking_id')
                    
                    # 記錄成功回應
                    self.api_logger.log_pms_response(200, elapsed, True, pms_id, ota_id)
                    
                    # 執行交叉核對 (如果提供了姓名或電話)
                    if guest_name or phone:
                        is_match = True
                        pms_name = order_data.get('guest_name', '')
                        pms_phone = order_data.get('contact_phone', '')
                        
                        if guest_name and guest_name not in pms_name:
                            print(f"❌ Privacy Check Failed: Name mismatch ('{guest_name}' not in '{pms_name}')")
                            self.api_logger.log_pms_error("PRIVACY_NAME", booking_id, elapsed, 
                                f"Name mismatch: '{guest_name}' not in '{pms_name}'")
                            is_match = False
                        
                        if phone:
                            clean_input_phone = re.sub(r'\D', '', phone)
                            clean_pms_phone = re.sub(r'\D', '', pms_phone)
                            if clean_input_phone and clean_input_phone not in clean_pms_phone:
                                print(f"❌ Privacy Check Failed: Phone mismatch ('{clean_input_phone}' not in '{clean_pms_phone}')")
                                self.api_logger.log_pms_error("PRIVACY_PHONE", booking_id, elapsed,
                                    f"Phone mismatch: '{clean_input_phone}' not in '{clean_pms_phone}'")
                                is_match = False
                        
                        if not is_match:
                            return None
                            
                    print(f"✅ PMS API Success: booking_id={pms_id}")
                    self.api_logger.log_query_result(booking_id, "pms", True, pms_id)
                    return data
                else:
                    print(f"⚠️ PMS API returned success=false")
                    self.api_logger.log_pms_response(200, elapsed, False)
                    self.api_logger.log_pms_error("API_FAIL", booking_id, elapsed, "API returned success=false")
                    return None
                    
            elif response.status_code == 404:
                print(f"📭 PMS API: Booking {clean_id} not found")
                self.api_logger.log_pms_response(404, elapsed, False)
                return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                self.api_logger.log_pms_response(response.status_code, elapsed, False)
                self.api_logger.log_pms_error("HTTP_ERROR", booking_id, elapsed, f"HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"⏱️ PMS API Timeout after {self.timeout}s")
            self.api_logger.log_pms_error("TIMEOUT", booking_id, elapsed, f"Request timeout after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"🔌 PMS API Connection Error (is server running?)")
            self.api_logger.log_pms_error("CONNECTION", booking_id, elapsed, f"Connection error: {str(e)[:100]}")
            return None
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ PMS API Unexpected Error: {e}")
            self.api_logger.log_pms_error("UNEXPECTED", booking_id, elapsed, f"Unexpected: {str(e)[:100]}")
            return None
    
    def search_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        通过姓名搜索订单
        
        Args:
            name: 订房人姓名
            
        Returns:
            订单列表字典，失败返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/bookings/search"
            params = {'name': name}
            print(f"📡 PMS API Request: GET {url}?name={name}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    count = data.get('count', 0)
                    print(f"✅ PMS API Success: found {count} bookings")
                    return data
                else:
                    return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ PMS API Error: {e}")
            return None
    
    def search_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        通过电话搜索订单
        
        Args:
            phone: 联络电话
            
        Returns:
            订单列表字典，失败返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/bookings/search"
            params = {'phone': phone}
            print(f"📡 PMS API Request: GET {url}?phone={phone}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    count = data.get('count', 0)
                    print(f"✅ PMS API Success: found {count} bookings")
                    return data
                else:
                    return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ PMS API Error: {e}")
            return None
    
    def check_health(self) -> bool:
        """
        检查 PMS API 健康状态
        
        Returns:
            True 表示服务正常，False 表示异常
        """
        if not self.enabled:
            return False
        
        try:
            # 使用基础 URL 而非 v1 路徑
            # 如果 base_url 以 /api 結尾，health 應該在 /api/health
            # 如果 base_url 以 /api/v1 結尾，health 仍應在 /api/health
            if '/api/v1' in self.base_url:
                url = self.base_url.replace('/api/v1', '/api/health')
            elif self.base_url.endswith('/api'):
                url = f"{self.base_url}/health"
            else:
                url = f"{self.base_url}/api/health"
            
            print(f"🏥 Health Check: {url}")
            
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                # 兼容不同 API 的健康檢查回傳格式
                if data.get('status') == 'ok' or data.get('success'):
                    print(f"✅ PMS API is healthy")
                    return True
            
            print(f"⚠️ PMS API health check failed")
            return False
            
        except Exception as e:
            print(f"❌ PMS API health check error: {e}")
            return False

    # ============================================
    # 當日預訂相關方法
    # ============================================
    
    def get_today_availability(self) -> Optional[Dict[str, Any]]:
        """
        查詢今日可用房型
        
        Returns:
            包含可用房型列表的字典，失敗返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/rooms/today-availability"
            print(f"📡 PMS API Request: GET {url}")
            
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    room_types = data.get('data', {}).get('available_room_types', [])
                    print(f"✅ 今日可用房型: {len(room_types)} 種")
                    return data
                else:
                    print(f"⚠️ API 回傳 success=false")
                    return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 查詢今日房型失敗: {e}")
            return None
    
    def create_same_day_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        建立當日預訂（暫存）
        
        Args:
            booking_data: 包含以下欄位的字典
                - room_type_code: 房型代碼 (如 'SD', 'VD')
                - room_type_name: 房型名稱 (如 '經典雙人房')
                - room_count: 間數
                - nights: 晚數（當日預訂通常為 1）
                - guest_name: 客人姓名
                - phone: 聯絡電話
                - arrival_time: 預計抵達時間
                - line_user_id: LINE 用戶 ID（可選）
                - line_display_name: LINE 顯示名稱（可選）
        
        Returns:
            訂單資訊字典，失敗返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/bookings/same-day"
            print(f"📡 PMS API Request: POST {url}")
            print(f"   Body: {booking_data}")
            
            response = requests.post(url, json=booking_data, timeout=self.timeout)
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                if data.get('success'):
                    order_id = data.get('data', {}).get('temp_order_id')
                    print(f"✅ 當日預訂成功: {order_id}")
                    return data
                else:
                    error_msg = data.get('error', {}).get('message', '未知錯誤')
                    print(f"⚠️ 建立預訂失敗: {error_msg}")
                    return None
            elif response.status_code == 400:
                data = response.json()
                error_msg = data.get('error', {}).get('message', '參數錯誤')
                print(f"⚠️ 參數錯誤: {error_msg}")
                return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 建立當日預訂失敗: {e}")
            return None
    
    def get_same_day_bookings(self) -> Optional[Dict[str, Any]]:
        """
        查詢當日預訂列表
        
        Returns:
            包含訂單列表的字典，失敗返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/bookings/same-day-list"
            print(f"📡 PMS API Request: GET {url}")
            
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    bookings = data.get('data', [])
                    print(f"✅ 當日預訂列表: {len(bookings)} 筆")
                    return data
                else:
                    print(f"⚠️ API 回傳 success=false")
                    return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 查詢當日預訂列表失敗: {e}")
            return None
    
    
    def cancel_same_day_booking(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        取消當日預訂
        
        Args:
            order_id: 暫存訂單編號（如 TEMP-20251216001）
        
        Returns:
            取消結果，失敗返回 None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/bookings/same-day/{order_id}/cancel"
            print(f"📡 PMS API Request: PATCH {url}")
            
            response = requests.patch(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ 訂單已取消: {order_id}")
                    return data
                else:
                    error_msg = data.get('error', {}).get('message', '未知錯誤')
                    print(f"⚠️ 取消失敗: {error_msg}")
                    return data
            elif response.status_code == 404:
                print(f"⚠️ 找不到訂單: {order_id}")
                return {'success': False, 'error': {'message': '找不到訂單'}}
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 取消訂單失敗: {e}")
            return None

    def update_supplement(self, booking_id: str, data: Dict[str, Any]) -> bool:
        """
        更新訂單擴充資料（電話、抵達時間、特殊需求）
        
        Args:
            booking_id: 訂單編號
            data: 要更新的資料字典 (如 {'confirmed_phone': '...', 'arrival_time': '...'})
            
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
            
        try:
            # 清理訂單號
            import re
            clean_id = booking_id.strip()
            clean_id = re.sub(r'^[A-Z]+', '', clean_id)
            
            url = f"{self.base_url}/pms/supplements/{clean_id}"
            print(f"📡 API Sync Request: PATCH {url}")
            
            response = requests.patch(url, json=data, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"✅ 擴充資料同步成功: {clean_id}")
                return True
            else:
                print(f"⚠️ 同步失敗: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 同步擴充資料失敗: {e}")
            return False

    def save_user_order_link(self, line_user_id: str, pms_id: str, 
                             ota_id: str = None, check_in_date: str = None) -> bool:
        """
        🔧 方案 D：儲存用戶訂單關聯
        
        Args:
            line_user_id: LINE 用戶 ID
            pms_id: PMS 訂單 ID
            ota_id: OTA 訂單 ID（可選）
            check_in_date: 入住日期（可選）
            
        Returns:
            是否成功
        """
        if not self.enabled or not line_user_id or not pms_id:
            return False
            
        try:
            # 使用本地後端 API
            local_url = "http://localhost:3000/api/user-orders"
            
            payload = {
                'line_user_id': line_user_id,
                'pms_id': pms_id,
                'ota_id': ota_id,
                'check_in_date': check_in_date
            }
            
            print(f"📡 User Order Link: POST {local_url}")
            
            response = requests.post(local_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ 用戶訂單關聯已儲存: {line_user_id} → {pms_id}")
                return True
            else:
                print(f"⚠️ 儲存用戶訂單關聯失敗: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 儲存用戶訂單關聯失敗: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    print("Testing PMS Client...")
    
    # 需要先设置环境变量或创建 .env 文件
    from dotenv import load_dotenv
    load_dotenv()
    
    client = PMSClient()
    
    # 测试健康检查
    print("\n=== Health Check ===")
    is_healthy = client.check_health()
    print(f"Health: {is_healthy}")
    
    # 测试获取订单详情
    print("\n=== Get Booking Details ===")
    result = client.get_booking_details("00605101")
    if result:
        print(f"Success: {result['data']['guest_name']}")
    else:
        print("Failed")
    
    # 测试姓名搜索
    print("\n=== Search by Name ===")
    result = client.search_by_name("booking")
    if result:
        print(f"Found {result['count']} bookings")
    else:
        print("Failed")
