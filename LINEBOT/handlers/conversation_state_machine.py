"""
統一對話狀態機 (Unified Conversation State Machine)

職責：
- 管理所有用戶的對話狀態
- 提供統一的狀態轉換 API
- 處理跨流程意圖跳轉 (pending_intent)
- 根據狀態決定應使用的 Handler
- 【新增】持久化到 SQLite (透過 ktw-backend API)

設計原則：
- Single Source of Truth (SSOT)
- 所有狀態儲存在此類別中
- Handler 只負責業務邏輯，不管理狀態
"""

from typing import Dict, Optional, Any
from datetime import datetime
import requests
import os


class ConversationStateMachine:
    """統一對話狀態機（含 SQLite 持久化）"""
    
    # 狀態定義
    STATE_IDLE = 'idle'
    
    # 訂單查詢流程狀態
    STATE_ORDER_QUERY_CONFIRMING = 'order_query.confirming'
    STATE_ORDER_QUERY_COLLECTING_PHONE = 'order_query.collecting_phone'
    STATE_ORDER_QUERY_COLLECTING_ARRIVAL = 'order_query.collecting_arrival'
    STATE_ORDER_QUERY_COLLECTING_SPECIAL = 'order_query.collecting_special'
    STATE_ORDER_QUERY_COMPLETED = 'order_query.completed'
    
    # 當日預訂流程狀態
    STATE_BOOKING_ASK_DATE = 'booking.ask_date'
    STATE_BOOKING_SHOW_ROOMS = 'booking.show_rooms'
    STATE_BOOKING_COLLECT_ROOM = 'booking.collect_room'
    STATE_BOOKING_COLLECT_COUNT = 'booking.collect_count'
    STATE_BOOKING_COLLECT_BED = 'booking.collect_bed'
    STATE_BOOKING_COLLECT_NAME = 'booking.collect_name'
    STATE_BOOKING_COLLECT_PHONE = 'booking.collect_phone'
    STATE_BOOKING_COLLECT_ARRIVAL = 'booking.collect_arrival'
    STATE_BOOKING_COLLECT_SPECIAL = 'booking.collect_special'
    STATE_BOOKING_COLLECT_REQUESTS = 'booking.collect_requests'
    STATE_BOOKING_CONFIRM = 'booking.confirm'
    STATE_BOOKING_COMPLETED = 'booking.completed'
    
    # ktw-backend API URL (本地，非 PMS 192.168.8.3)
    BACKEND_API_URL = os.getenv('KTW_BACKEND_URL', 'http://localhost:3000')
    
    def __init__(self):
        """初始化狀態機"""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._sync_enabled = True  # 可透過環境變數關閉同步
    
    # Session 超時時間（秒）：超過此時間未活動自動重置為 idle
    SESSION_TIMEOUT_SECONDS = 2 * 60 * 60  # 2 小時
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """
        取得或建立用戶 session
        
        包含超時檢查：超過 2 小時未活動的非 idle session 自動重置，
        避免客人隔天回覆時承接到舊流程。
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            用戶的 session dict
        """
        if user_id not in self.sessions:
            # 先嘗試從 SQLite 載入
            persisted = self._load_from_backend(user_id)
            if persisted:
                # 超時檢查：超過 2 小時未活動自動重置
                if self._is_session_expired(persisted):
                    print(f"⏰ Session 已超時，自動重置: {user_id} (上次: {persisted.get('updated_at')})")
                    self.reset_session(user_id)
                    self.sessions[user_id] = self._create_default_session()
                else:
                    self.sessions[user_id] = persisted
                    print(f"📥 Session 從 SQLite 載入: {user_id} → {persisted.get('state')}")
            else:
                self.sessions[user_id] = self._create_default_session()
        else:
            # 記憶體中的 session 也要檢查超時
            if self._is_session_expired(self.sessions[user_id]):
                print(f"⏰ 記憶體 Session 已超時，自動重置: {user_id}")
                self.reset_session(user_id)
                self.sessions[user_id] = self._create_default_session()
        return self.sessions[user_id]
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """
        檢查 session 是否已超時
        
        只檢查非 idle 狀態的 session，idle 狀態不需要超時。
        
        Args:
            session: session dict
            
        Returns:
            True 如果已超時（超過 SESSION_TIMEOUT_SECONDS 秒）
        """
        state = session.get('state', self.STATE_IDLE)
        if state == self.STATE_IDLE:
            return False
        
        updated_at_str = session.get('updated_at')
        if not updated_at_str:
            return False
        
        try:
            updated_at = datetime.fromisoformat(updated_at_str)
            elapsed = (datetime.now() - updated_at).total_seconds()
            return elapsed > self.SESSION_TIMEOUT_SECONDS
        except (ValueError, TypeError):
            return False
    
    def _create_default_session(self) -> Dict[str, Any]:
        """建立預設 session"""
        return {
            'state': self.STATE_IDLE,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'data': {},  # 流程相關資料
            'pending_intent': None,  # 待處理意圖
            'pending_intent_message': None,
        }
    
    def _load_from_backend(self, user_id: str) -> Optional[Dict[str, Any]]:
        """從 ktw-backend 載入 session"""
        if not self._sync_enabled:
            return None
        try:
            response = requests.get(
                f"{self.BACKEND_API_URL}/api/bot/sessions/{user_id}",
                timeout=2
            )
            if response.ok:
                result = response.json()
                if result.get('success') and result.get('data'):
                    db_session = result['data']
                    return {
                        'state': db_session.get('state', self.STATE_IDLE),
                        'created_at': db_session.get('created_at', datetime.now().isoformat()),
                        'updated_at': db_session.get('updated_at', datetime.now().isoformat()),
                        'data': db_session.get('data', {}),
                        'pending_intent': db_session.get('pending_intent'),
                        'pending_intent_message': db_session.get('pending_intent_message'),
                    }
        except Exception as e:
            print(f"⚠️ 載入 Session 失敗: {e}")
        return None
    
    def _sync_to_backend(self, user_id: str):
        """同步 session 到 ktw-backend"""
        if not self._sync_enabled:
            return
        try:
            session = self.sessions.get(user_id)
            if not session:
                return
            
            payload = {
                'handler_type': self.get_active_handler_type(user_id),
                'state': session.get('state'),
                'data': session.get('data', {}),
                'pending_intent': session.get('pending_intent'),
                'pending_intent_message': session.get('pending_intent_message'),
            }
            
            requests.put(
                f"{self.BACKEND_API_URL}/api/bot/sessions/{user_id}",
                json=payload,
                timeout=2
            )
        except Exception as e:
            print(f"⚠️ 同步 Session 失敗: {e}")
    
    def _delete_from_backend(self, user_id: str):
        """從 ktw-backend 刪除 session"""
        if not self._sync_enabled:
            return
        try:
            requests.delete(
                f"{self.BACKEND_API_URL}/api/bot/sessions/{user_id}",
                timeout=2
            )
        except Exception as e:
            print(f"⚠️ 刪除 Session 失敗: {e}")
    
    def get_state(self, user_id: str) -> str:
        """
        取得當前狀態
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            當前狀態字串
        """
        session = self.get_session(user_id)
        return session['state']
    
    def transition(self, user_id: str, target_state: str, data: Optional[Dict] = None):
        """
        狀態轉換
        
        Args:
            user_id: LINE 用戶 ID
            target_state: 目標狀態
            data: 可選的資料更新
        """
        session = self.get_session(user_id)
        old_state = session['state']
        session['state'] = target_state
        session['updated_at'] = datetime.now().isoformat()
        
        # 更新資料
        if data:
            session['data'].update(data)
        
        print(f"🔄 State Transition [{user_id}]: {old_state} → {target_state}")
        
        # 同步到 SQLite
        self._sync_to_backend(user_id)
    
    def get_data(self, user_id: str, key: str = None) -> Any:
        """
        取得 session 資料
        
        Args:
            user_id: LINE 用戶 ID
            key: 資料鍵名，None 表示取得整個 data dict
            
        Returns:
            資料值或整個 data dict
        """
        session = self.get_session(user_id)
        if key is None:
            return session['data']
        return session['data'].get(key)
    
    def set_data(self, user_id: str, key: str, value: Any):
        """
        設定 session 資料
        
        Args:
            user_id: LINE 用戶 ID
            key: 資料鍵名
            value: 資料值
        """
        session = self.get_session(user_id)
        session['data'][key] = value
        session['updated_at'] = datetime.now().isoformat()
        
        # 同步到 SQLite
        self._sync_to_backend(user_id)
    
    def get_active_handler_type(self, user_id: str) -> str:
        """
        根據狀態返回應使用的 Handler 類型
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            'order_query', 'same_day_booking', 或 'ai_conversation'
        """
        state = self.get_state(user_id)
        
        if state.startswith('order_query'):
            return 'order_query'
        elif state.startswith('booking'):
            return 'same_day_booking'
        else:
            return 'ai_conversation'
    
    def set_pending_intent(self, user_id: str, intent: str, message: Optional[str] = None):
        """
        設定待處理意圖 (跨流程跳轉)
        
        使用場景：
        - 用戶在「訂單查詢」中說「我要加訂」→ 設定 pending_intent='same_day_booking'
        - 用戶在「當日預訂」中說「我要查訂單」→ 設定 pending_intent='order_query'
        
        Args:
            user_id: LINE 用戶 ID
            intent: 意圖類型 ('same_day_booking' 或 'order_query')
            message: 可選的觸發訊息
        """
        session = self.get_session(user_id)
        session['pending_intent'] = intent
        if message:
            session['pending_intent_message'] = message
        session['updated_at'] = datetime.now().isoformat()
        print(f"📌 Pending Intent Set [{user_id}]: {intent}")
        
        # 同步到 SQLite
        self._sync_to_backend(user_id)
    
    def get_pending_intent(self, user_id: str) -> Optional[str]:
        """
        取得待處理意圖
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            pending_intent 字串，None 表示無待處理意圖
        """
        session = self.get_session(user_id)
        return session.get('pending_intent')
    
    def clear_pending_intent(self, user_id: str):
        """
        清除待處理意圖
        
        Args:
            user_id: LINE 用戶 ID
        """
        session = self.get_session(user_id)
        if 'pending_intent' in session:
            session['pending_intent'] = None
        if 'pending_intent_message' in session:
            session['pending_intent_message'] = None
        session['updated_at'] = datetime.now().isoformat()
        print(f"🧹 Pending Intent Cleared [{user_id}]")
        
        # 同步到 SQLite
        self._sync_to_backend(user_id)
    
    def execute_pending_intent(self, user_id: str) -> Optional[str]:
        """
        執行待處理意圖（流程完成後自動跳轉）
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            目標狀態字串，None 表示無待處理意圖
        """
        pending = self.get_pending_intent(user_id)
        if not pending:
            return None
        
        # 清除 pending_intent
        self.clear_pending_intent(user_id)
        
        # 根據意圖返回目標狀態
        intent_to_state = {
            'same_day_booking': self.STATE_BOOKING_ASK_DATE,
            'order_query': self.STATE_IDLE  # 需要用戶提供訂單號，所以回到 idle
        }
        
        target_state = intent_to_state.get(pending)
        print(f"🎯 Executing Pending Intent [{user_id}]: {pending} → {target_state}")
        return target_state
    
    def reset_session(self, user_id: str):
        """
        重置用戶 session
        
        Args:
            user_id: LINE 用戶 ID
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
        
        # 從 SQLite 刪除
        self._delete_from_backend(user_id)
        
        print(f"🔄 Session Reset [{user_id}]")
    
    def is_in_active_flow(self, user_id: str) -> bool:
        """
        檢查用戶是否在進行中的流程
        
        Args:
            user_id: LINE 用戶 ID
            
        Returns:
            True 如果在進行中流程，False 如果閒置
        """
        state = self.get_state(user_id)
        return state != self.STATE_IDLE

