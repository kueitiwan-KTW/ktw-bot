"""
PMS API Client
用于与 PMS REST API 进行交互，获取订单资料
"""

import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class PMSClient:
    """PMS REST API 客户端"""
    
    def __init__(self):
        """初始化 PMS 客户端"""
        self.base_url = os.getenv('PMS_API_BASE_URL', 'http://192.168.8.3:3000/api')
        self.timeout = int(os.getenv('PMS_API_TIMEOUT', '5'))
        self.enabled = os.getenv('PMS_API_ENABLED', 'True').lower() == 'true'
        
        print(f"🔷 PMS Client initialized: base_url={self.base_url}, timeout={self.timeout}s, enabled={self.enabled}")
    
    def get_booking_details(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单详细资料
        
        Args:
            booking_id: 订单编号
            
        Returns:
            订单资料字典，失败返回 None
        """
        if not self.enabled:
            print("⚠️ PMS API is disabled")
            return None
        
        try:
            # 清理订单号（移除前缀和空格）
            clean_id = booking_id.strip()
            # 移除可能的前缀（RMAG, RMPGP 等）
            import re
            clean_id = re.sub(r'^[A-Z]+', '', clean_id)
            
            url = f"{self.base_url}/bookings/{clean_id}"
            print(f"📡 PMS API Request: GET {url}")
            
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ PMS API Success: booking_id={data['data']['booking_id']}")
                    return data
                else:
                    print(f"⚠️ PMS API returned success=false")
                    return None
            elif response.status_code == 404:
                print(f"📭 PMS API: Booking {clean_id} not found")
                return None
            else:
                print(f"⚠️ PMS API Error: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏱️ PMS API Timeout after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 PMS API Connection Error (is server running?)")
            return None
        except Exception as e:
            print(f"❌ PMS API Unexpected Error: {e}")
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
            # 使用基础 URL 而非 v1
            base = self.base_url.replace('/api/v1', '')
            url = f"{base}/api/health"
            print(f"🏥 Health Check: {url}")
            
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
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
