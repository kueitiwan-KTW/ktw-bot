# L3_business/plugins/hotel/triggers/check_in_reminder.py
# 建立日期：2025-12-24

"""
入住提醒 Trigger Spec

職責：
- 定義「什麼時候」發送入住提醒
- 定義「訊息內容」模板
- 定義「變數」映射

這是 What SSOT（產業規格），不包含排程實作。
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime, date, timedelta


@dataclass
class CheckInReminderSpec:
    """
    入住提醒規格
    
    定義「入住前 1 天提醒」的規則。
    """
    
    # 觸發條件
    trigger_id: str = "check_in_reminder"
    trigger_time: str = "1_day_before"  # 入住前 1 天
    trigger_hour: int = 14              # 下午 2 點發送
    
    # 訊息模板
    message_template: str = """🏨 入住提醒

親愛的 {guest_name}，

明天就要入住啦！🎉

📅 入住日期：{check_in_date}
📅 退房日期：{check_out_date}
🏠 房型：{room_type}
🔢 數量：{room_count} 間

請問您預計幾點抵達呢？
可以直接在這裡回覆，我幫您記錄！

若有任何問題，歡迎隨時詢問 💬"""
    
    # 可用變數
    available_variables: List[str] = None
    
    def __post_init__(self):
        self.available_variables = [
            "guest_name",
            "check_in_date",
            "check_out_date",
            "room_type",
            "room_count"
        ]
    
    def calculate_send_time(self, check_in_date: date) -> datetime:
        """
        計算發送時間
        
        Args:
            check_in_date: 入住日期
            
        Returns:
            發送時間（入住前 1 天 14:00）
        """
        send_date = check_in_date - timedelta(days=1)
        return datetime(send_date.year, send_date.month, send_date.day, self.trigger_hour, 0, 0)
    
    def format_message(self, booking_data: Dict[str, Any]) -> str:
        """
        格式化訊息
        
        Args:
            booking_data: 訂房資料
            
        Returns:
            格式化後的訊息
        """
        return self.message_template.format(
            guest_name=booking_data.get('guest_name', '貴賓'),
            check_in_date=booking_data.get('check_in_date', ''),
            check_out_date=booking_data.get('check_out_date', ''),
            room_type=booking_data.get('room_type', ''),
            room_count=booking_data.get('room_count', 1)
        )


@dataclass
class CheckOutReminderSpec:
    """
    退房提醒規格
    """
    
    trigger_id: str = "check_out_reminder"
    trigger_time: str = "1_day_before"
    trigger_hour: int = 18  # 下午 6 點發送
    
    message_template: str = """🏨 退房提醒

親愛的 {guest_name}，

明天 11:00 前退房喔！

如需延遲退房請提前告知 💬

感謝您的入住，祝旅途愉快！🎉"""
    
    def calculate_send_time(self, check_out_date: date) -> datetime:
        """計算發送時間"""
        send_date = check_out_date - timedelta(days=1)
        return datetime(send_date.year, send_date.month, send_date.day, self.trigger_hour, 0, 0)
    
    def format_message(self, booking_data: Dict[str, Any]) -> str:
        """格式化訊息"""
        return self.message_template.format(
            guest_name=booking_data.get('guest_name', '貴賓')
        )


@dataclass
class ReviewRequestSpec:
    """
    邀請評價規格
    """
    
    trigger_id: str = "review_request"
    trigger_time: str = "1_day_after"  # 退房後 1 天
    trigger_hour: int = 10  # 上午 10 點發送
    
    message_template: str = """⭐ 感謝入住！

親愛的 {guest_name}，

感謝您選擇我們的飯店！

希望您度過了愉快的時光 🎉

如果方便的話，請給我們一個評價
讓我們更進步！

👉 Google 評論：{review_link}

感謝您的支持！💕"""
    
    def calculate_send_time(self, check_out_date: date) -> datetime:
        """計算發送時間"""
        send_date = check_out_date + timedelta(days=1)
        return datetime(send_date.year, send_date.month, send_date.day, self.trigger_hour, 0, 0)


# === 便利函數 ===

def get_all_reminder_specs() -> List:
    """取得所有提醒規格"""
    return [
        CheckInReminderSpec(),
        CheckOutReminderSpec(),
        ReviewRequestSpec()
    ]


def get_spec_by_id(trigger_id: str):
    """根據 ID 取得規格"""
    specs = {
        "check_in_reminder": CheckInReminderSpec(),
        "check_out_reminder": CheckOutReminderSpec(),
        "review_request": ReviewRequestSpec()
    }
    return specs.get(trigger_id)
