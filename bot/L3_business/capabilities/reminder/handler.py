# L3_business/capabilities/reminder/handler.py
# 建立日期：2025-12-24

"""
提醒能力 Handler

職責：
- 接收 Scheduler 的 Job
- 調用 LINE API 發送訊息
- 回報結果

這是 How SSOT（能力框架），不包含產業業務規則。
"""

from typing import Dict, Any
import os


class ReminderHandler:
    """
    提醒 Handler
    
    處理 Scheduler 派發的提醒任務。
    """
    
    def __init__(self, line_api_client=None):
        """
        初始化
        
        Args:
            line_api_client: LINE API 客戶端（可選，用於發送訊息）
        """
        self.line_api_client = line_api_client
    
    def handle(self, job) -> bool:
        """
        處理提醒任務
        
        Args:
            job: Job 物件，包含 job_type, tenant_id, payload
            
        Returns:
            True 成功，False 失敗
        """
        payload = job.payload
        user_id = payload.get('user_id')
        message = payload.get('message')
        reminder_type = payload.get('reminder_type', 'general')
        
        if not user_id or not message:
            print(f"❌ 缺少必要參數: user_id={user_id}, message={message[:20] if message else None}")
            return False
        
        # 發送訊息
        success = self._send_message(user_id, message, job.tenant_id)
        
        if success:
            print(f"✅ 提醒已發送: {user_id} ({reminder_type})")
        else:
            print(f"❌ 提醒發送失敗: {user_id}")
        
        return success
    
    def _send_message(self, user_id: str, message: str, tenant_id: str) -> bool:
        """
        發送訊息
        
        TODO: 整合 LINE Messaging API
        """
        if self.line_api_client:
            try:
                self.line_api_client.push_message(user_id, message)
                return True
            except Exception as e:
                print(f"❌ LINE API 錯誤: {e}")
                return False
        else:
            # 模擬發送（測試用）
            print(f"📤 [模擬發送] to={user_id}")
            print(f"📝 訊息:\n{message[:100]}...")
            return True


# 全域 Handler 實例
reminder_handler = ReminderHandler()


def get_reminder_handler():
    """取得 Handler 實例"""
    return reminder_handler
