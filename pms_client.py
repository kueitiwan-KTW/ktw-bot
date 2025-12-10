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
        self.base_url = os.getenv('PMS_API_BASE_URL', 'http://192.168.8.3:3000/api/v1')
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
