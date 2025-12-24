# L5_storage/database/session_manager.py
# 建立日期：2025-12-24
# 複製自：LINEBOT/handlers/conversation_state_machine.py

"""
Session 管理器

職責：
- 管理所有用戶的對話狀態
- 提供 Snapshot 支援（保存/恢復）
- 持久化到 SQLite（透過 Backend API）
- 支援 schema versioning

設計原則：
- Single Source of Truth (SSOT)
- 與 Machine 解耦，只管資料不管業務
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
import requests
import os
import json


# Schema 版本，修改欄位時必須升版
SCHEMA_VERSION = "1.0.0"


@dataclass
class SessionSnapshot:
    """
    Session 快照
    
    用於保存和恢復 Session 狀態。
    """
    schema_version: str
    user_id: str
    state: str
    data: Dict[str, Any]
    pending_intent: Optional[str] = None
    pending_intent_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化為 dict"""
        return {
            'schema_version': self.schema_version,
            'user_id': self.user_id,
            'state': self.state,
            'data': self.data,
            'pending_intent': self.pending_intent,
            'pending_intent_message': self.pending_intent_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'SessionSnapshot':
        """從 dict 反序列化"""
        return cls(
            schema_version=d.get('schema_version', '1.0.0'),
            user_id=d.get('user_id', ''),
            state=d.get('state', 'idle'),
            data=d.get('data', {}),
            pending_intent=d.get('pending_intent'),
            pending_intent_message=d.get('pending_intent_message'),
            created_at=d.get('created_at', ''),
            updated_at=d.get('updated_at', '')
        )


class SessionManager:
    """
    Session 管理器（含 SQLite 持久化）
    
    功能：
    - get/set session 資料
    - snapshot/restore 快照
    - 自動同步到 Backend API
    """
    
    STATE_IDLE = 'idle'
    
    # KTW-backend API URL
    BACKEND_API_URL = os.getenv('KTW_BACKEND_URL', 'http://localhost:3000')
    
    def __init__(self, tenant_id: str = None):
        """初始化"""
        self.tenant_id = tenant_id
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._sync_enabled = True
    
    # === Session 管理 ===
    
    def get_session(self, user_id: str) -> Dict[str, Any]:
        """
        取得或建立用戶 session
        
        會先嘗試從 SQLite 載入，若無則建立新的。
        """
        if user_id not in self.sessions:
            # 先嘗試從 SQLite 載入
            persisted = self._load_from_backend(user_id)
            if persisted:
                self.sessions[user_id] = persisted
                print(f"📥 Session 從 SQLite 載入: {user_id} → {persisted.get('state')}")
            else:
                self.sessions[user_id] = self._create_default_session(user_id)
        return self.sessions[user_id]
    
    def _create_default_session(self, user_id: str) -> Dict[str, Any]:
        """建立預設 session"""
        now = datetime.now().isoformat()
        return {
            'schema_version': SCHEMA_VERSION,
            'user_id': user_id,
            'state': self.STATE_IDLE,
            'created_at': now,
            'updated_at': now,
            'data': {},
            'pending_intent': None,
            'pending_intent_message': None,
        }
    
    def get_state(self, user_id: str) -> str:
        """取得當前狀態"""
        session = self.get_session(user_id)
        return session['state']
    
    def set_state(self, user_id: str, state: str, data: Optional[Dict] = None):
        """設定狀態（並同步到 Backend）"""
        session = self.get_session(user_id)
        old_state = session['state']
        session['state'] = state
        session['updated_at'] = datetime.now().isoformat()
        
        if data:
            session['data'].update(data)
        
        print(f"🔄 State: {old_state} → {state}")
        self._sync_to_backend(user_id)
    
    def get_data(self, user_id: str, key: str = None) -> Any:
        """取得 session 資料"""
        session = self.get_session(user_id)
        if key is None:
            return session['data']
        return session['data'].get(key)
    
    def set_data(self, user_id: str, key: str, value: Any):
        """設定 session 資料"""
        session = self.get_session(user_id)
        session['data'][key] = value
        session['updated_at'] = datetime.now().isoformat()
        self._sync_to_backend(user_id)
    
    def reset_session(self, user_id: str):
        """重置用戶 session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        self._delete_from_backend(user_id)
        print(f"🔄 Session Reset [{user_id}]")
    
    # === Snapshot 支援 ===
    
    def snapshot(self, user_id: str) -> SessionSnapshot:
        """
        建立快照
        
        用於保存當前狀態，以便稍後恢復。
        """
        session = self.get_session(user_id)
        return SessionSnapshot(
            schema_version=session.get('schema_version', SCHEMA_VERSION),
            user_id=user_id,
            state=session['state'],
            data=session.get('data', {}).copy(),
            pending_intent=session.get('pending_intent'),
            pending_intent_message=session.get('pending_intent_message'),
            created_at=session.get('created_at', ''),
            updated_at=session.get('updated_at', '')
        )
    
    def restore(self, snapshot: SessionSnapshot):
        """
        從快照恢復
        
        注意：會覆蓋現有 session。
        """
        user_id = snapshot.user_id
        
        # 檢查 schema 版本
        if snapshot.schema_version != SCHEMA_VERSION:
            print(f"⚠️ Schema 版本不一致: {snapshot.schema_version} vs {SCHEMA_VERSION}")
            # TODO: 實作版本遷移邏輯
        
        self.sessions[user_id] = {
            'schema_version': SCHEMA_VERSION,
            'user_id': user_id,
            'state': snapshot.state,
            'data': snapshot.data.copy(),
            'pending_intent': snapshot.pending_intent,
            'pending_intent_message': snapshot.pending_intent_message,
            'created_at': snapshot.created_at,
            'updated_at': datetime.now().isoformat()
        }
        
        print(f"📥 Session 從快照恢復: {user_id} → {snapshot.state}")
        self._sync_to_backend(user_id)
    
    # === Pending Intent ===
    
    def set_pending_intent(self, user_id: str, intent: str, message: Optional[str] = None):
        """設定待處理意圖"""
        session = self.get_session(user_id)
        session['pending_intent'] = intent
        if message:
            session['pending_intent_message'] = message
        session['updated_at'] = datetime.now().isoformat()
        print(f"📌 Pending Intent: {intent}")
        self._sync_to_backend(user_id)
    
    def get_pending_intent(self, user_id: str) -> Optional[str]:
        """取得待處理意圖"""
        session = self.get_session(user_id)
        return session.get('pending_intent')
    
    def clear_pending_intent(self, user_id: str):
        """清除待處理意圖"""
        session = self.get_session(user_id)
        session['pending_intent'] = None
        session['pending_intent_message'] = None
        session['updated_at'] = datetime.now().isoformat()
        print(f"🧹 Pending Intent Cleared")
        self._sync_to_backend(user_id)
    
    # === Backend API 同步 ===
    
    def _load_from_backend(self, user_id: str) -> Optional[Dict[str, Any]]:
        """從 Backend 載入 session"""
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
                        'schema_version': db_session.get('schema_version', SCHEMA_VERSION),
                        'user_id': user_id,
                        'state': db_session.get('state', self.STATE_IDLE),
                        'created_at': db_session.get('created_at', ''),
                        'updated_at': db_session.get('updated_at', ''),
                        'data': db_session.get('data', {}),
                        'pending_intent': db_session.get('pending_intent'),
                        'pending_intent_message': db_session.get('pending_intent_message'),
                    }
        except Exception as e:
            print(f"⚠️ 載入 Session 失敗: {e}")
        return None
    
    def _sync_to_backend(self, user_id: str):
        """同步 session 到 Backend"""
        if not self._sync_enabled:
            return
        try:
            session = self.sessions.get(user_id)
            if not session:
                return
            
            payload = {
                'schema_version': session.get('schema_version', SCHEMA_VERSION),
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
        """從 Backend 刪除 session"""
        if not self._sync_enabled:
            return
        try:
            requests.delete(
                f"{self.BACKEND_API_URL}/api/bot/sessions/{user_id}",
                timeout=2
            )
        except Exception as e:
            print(f"⚠️ 刪除 Session 失敗: {e}")
