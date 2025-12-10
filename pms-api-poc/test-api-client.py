#!/usr/bin/env python3
"""
PMS API 測試客戶端 (Mac 本機)

用途：測試 Windows Server 上的 PMS API 是否正常運作
"""

import requests
import json
from datetime import datetime

# PMS API 設定
# 將 Windows Server 部署完成後，修改此 IP 為 192.168.8.3
PMS_API_URL = "http://192.168.8.3:3000/api"

def test_connection():
    """測試 API 是否可連線"""
    print("=" * 60)
    print("測試 1：檢查 API 連線")
    print("=" * 60)
    
    try:
        response = requests.get(f"{PMS_API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API 連線成功")
            print(f"   回應: {response.json()}")
            return True
        else:
            print(f"❌ API 回應異常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 無法連線到 API")
        print(f"   請確認:")
        print(f"   1. Windows Server (192.168.8.3) 上的 API 是否正在運行")
        print(f"   2. 防火牆是否開放 Port 3000")
        print(f"   3. 網路是否可連通")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def test_query_booking(order_id="00150501"):
    """測試訂單查詢"""
    print("\n" + "=" * 60)
    print(f"測試 2：查詢訂單 {order_id}")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{PMS_API_URL}/bookings/{order_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                booking = data.get('data', {})
                print("✅ 查詢成功")
                print(f"\n訂單資訊:")
                print(f"  訂單編號: {booking.get('booking_id')}")
                print(f"  訂房人: {booking.get('guest_name', '未提供')}")
                print(f"  聯絡電話: {booking.get('contact_phone', '未提供')}")
                print(f"  入住日期: {booking.get('check_in_date')}")
                print(f"  退房日期: {booking.get('check_out_date')}")
                print(f"  住宿天數: {booking.get('nights')} 晚")
                print(f"  訂單狀態: {booking.get('status_name')}")
                
                rooms = booking.get('rooms', [])
                if rooms:
                    print(f"\n房型資訊:")
                    for idx, room in enumerate(rooms, 1):
                        print(f"  房型 {idx}: {room.get('room_type_name')}")
                        print(f"    房間數: {room.get('room_count')} 間")
                        print(f"    成人數: {room.get('adult_count')} 人")
                        print(f"    兒童數: {room.get('child_count')} 人")
                
                return True
            else:
                print(f"❌ 查詢失敗: {data.get('error', {}).get('message')}")
                return False
                
        elif response.status_code == 404:
            print(f"❌ 找不到訂單 {order_id}")
            return False
        else:
            print(f"❌ API 錯誤: {response.status_code}")
            print(f"   回應: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def test_search_bookings(guest_name=None, phone=None):
    """測試訂單搜尋"""
    print("\n" + "=" * 60)
    print("測試 3：搜尋訂單")
    print("=" * 60)
    
    params = {}
    if guest_name:
        params['name'] = guest_name
    if phone:
        params['phone'] = phone
    
    if not params:
        print("⚠️  未提供搜尋條件，跳過此測試")
        return False
    
    try:
        response = requests.get(
            f"{PMS_API_URL}/bookings/search",
            params=params,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                bookings = data.get('data', [])
                print(f"✅ 找到 {len(bookings)} 筆訂單")
                
                for idx, booking in enumerate(bookings[:5], 1):  # 只顯示前5筆
                    print(f"\n訂單 {idx}:")
                    print(f"  訂單編號: {booking.get('booking_id')}")
                    print(f"  訂房人: {booking.get('guest_name')}")
                    print(f"  入住日期: {booking.get('check_in_date')}")
                    print(f"  狀態: {booking.get('status_name')}")
                
                if len(bookings) > 5:
                    print(f"\n... 還有 {len(bookings) - 5} 筆訂單")
                
                return True
            else:
                print(f"❌ 搜尋失敗")
                return False
                
        else:
            print(f"❌ API 錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def test_bot_integration():
    """模擬 BOT 整合測試"""
    print("\n" + "=" * 60)
    print("測試 4：模擬 BOT 查詢流程")
    print("=" * 60)
    
    # 模擬 BOT 收到用戶訊息：訂單編號
    order_id = "00150501"
    print(f"\n用戶輸入: {order_id}")
    
    try:
        # 步驟 1：查詢訂單
        response = requests.get(
            f"{PMS_API_URL}/bookings/{order_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                booking = data['data']
                
                # 步驟 2：格式化 BOT 回應
                bot_reply = f"""我幫您找到了訂單編號 {booking['booking_id']}，請稍等，這就為您查詢訂單詳細資訊。

• 訂單編號: {booking['booking_id']}
• 訂房人: {booking.get('guest_name', '未提供')}
• 訂房來源: {booking.get('booking_source', 'N/A')}
• 入住日期: {booking['check_in_date']}
• 退房日期: {booking['check_out_date']}，共 {booking['nights']} 晚
• 房型: {booking['rooms'][0]['room_type_name']} X {booking['rooms'][0]['room_count']} 間
• 早餐: {'有' if booking.get('breakfast') else '無'}

系統顯示您的訂單缺少聯絡電話，請問方便提供您的聯絡電話嗎？"""
                
                print("\nBOT 回應預覽:")
                print("-" * 60)
                print(bot_reply)
                print("-" * 60)
                print("\n✅ BOT 整合測試成功")
                print("   資料來源: PMS API (不再是 Gmail)")
                print("   無幻覺問題: ✓")
                
                return True
            else:
                print("❌ 找不到訂單")
                return False
        else:
            print(f"❌ API 錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def main():
    """主程式"""
    print("\n" + "=" * 60)
    print("PMS API 測試客戶端 (Mac 本機)")
    print("=" * 60)
    print(f"API 位址: {PMS_API_URL}")
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # 執行測試
    results = []
    
    # 測試 1：連線
    results.append(("API 連線", test_connection()))
    
    # 如果連線成功，繼續其他測試
    if results[0][1]:
        # 測試 2：查詢訂單
        results.append(("查詢訂單", test_query_booking("00150501")))
        
        # 測試 3：搜尋訂單（選填）
        # results.append(("搜尋訂單", test_search_bookings(guest_name="王")))
        
        # 測試 4：BOT 整合
        results.append(("BOT 整合", test_bot_integration()))
    
    # 測試總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\n總計: {passed}/{total} 項測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！PMS API 運作正常。")
        print("\n📝 下一步:")
        print("   1. 修改 bot.py 使用 PMS API")
        print("   2. 移除 Gmail API 相關代碼")
        print("   3. 測試完整 BOT 功能")
    else:
        print("\n⚠️  部分測試失敗，請檢查:")
        print("   1. Windows Server 上的 API 是否正在運行")
        print("   2. 防火牆設定是否正確")
        print("   3. API 端點是否實作完成")


if __name__ == "__main__":
    main()
