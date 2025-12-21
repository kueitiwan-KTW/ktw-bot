"""
API Logger - PMS API 調用日誌記錄器

記錄所有 PMS API 查詢過程，方便問題追蹤與診斷。
"""

import os
import logging
from datetime import datetime
from typing import Optional

class APILogger:
    """
    專門記錄 API 調用的 Logger
    
    日誌格式：
    2025-12-21 09:50:12 | INFO | PMS_QUERY | user=U45320f6... | order_id=1671721966
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化 API Logger
        
        Args:
            log_dir: 日誌目錄，預設為 data/api_logs
        """
        if log_dir is None:
            # 找到專案根目錄
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            log_dir = os.path.join(project_root, "data", "api_logs")
        
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 設定 logger
        self.logger = logging.getLogger("APILogger")
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重複添加 handler
        if not self.logger.handlers:
            # Console Handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
        
        # 更新每日檔案 handler
        self._update_file_handler()
    
    def _update_file_handler(self):
        """更新每日日誌檔案 handler"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"pms_api_{today}.log")
        
        # 移除舊的 FileHandler
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        
        # 添加新的 FileHandler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                                         datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        self.current_date = today
    
    def _check_date(self):
        """檢查日期是否變更，需要輪換日誌檔案"""
        today = datetime.now().strftime("%Y-%m-%d")
        if not hasattr(self, 'current_date') or self.current_date != today:
            self._update_file_handler()
    
    def log_query_start(self, user_id: str, order_id: str, 
                        guest_name: Optional[str] = None, 
                        phone: Optional[str] = None):
        """記錄查詢開始"""
        self._check_date()
        user_short = user_id[:12] + "..." if len(user_id) > 12 else user_id
        extra_info = []
        if guest_name:
            extra_info.append(f"name={guest_name}")
        if phone:
            extra_info.append(f"phone={phone}")
        extra_str = " | " + " | ".join(extra_info) if extra_info else ""
        
        self.logger.info(f"PMS_QUERY_START | user={user_short} | order_id={order_id}{extra_str}")
    
    def log_pms_request(self, url: str, method: str = "GET"):
        """記錄 PMS API 請求"""
        self._check_date()
        self.logger.debug(f"PMS_REQUEST | method={method} | url={url}")
    
    def log_pms_response(self, status_code: int, elapsed_seconds: float, 
                         found: bool, pms_id: Optional[str] = None,
                         ota_id: Optional[str] = None):
        """記錄 PMS API 回應"""
        self._check_date()
        result = "found" if found else "not_found"
        id_info = f" | pms_id={pms_id}" if pms_id else ""
        ota_info = f" | ota_id={ota_id}" if ota_id else ""
        
        self.logger.info(f"PMS_RESPONSE | status={status_code} | elapsed={elapsed_seconds:.2f}s | result={result}{id_info}{ota_info}")
    
    def log_pms_error(self, error_type: str, order_id: str, 
                      elapsed_seconds: float, error_msg: str):
        """記錄 PMS API 錯誤"""
        self._check_date()
        self.logger.error(f"PMS_ERROR | type={error_type} | order_id={order_id} | elapsed={elapsed_seconds:.2f}s | error={error_msg}")
    
    def log_fallback(self, source: str, order_id: str, 
                     triggered: bool, reason: Optional[str] = None):
        """記錄備援查詢"""
        self._check_date()
        reason_str = f" | reason={reason}" if reason else ""
        self.logger.info(f"FALLBACK | source={source} | order_id={order_id} | triggered={triggered}{reason_str}")
    
    def log_query_result(self, order_id: str, source: str, 
                         success: bool, pms_id: Optional[str] = None):
        """記錄查詢最終結果"""
        self._check_date()
        level = logging.INFO if success else logging.WARNING
        result = "success" if success else "not_found"
        id_info = f" | pms_id={pms_id}" if pms_id else ""
        
        self.logger.log(level, f"QUERY_RESULT | order_id={order_id} | source={source} | result={result}{id_info}")


# 單例模式
_api_logger_instance = None

def get_api_logger() -> APILogger:
    """取得 API Logger 單例"""
    global _api_logger_instance
    if _api_logger_instance is None:
        _api_logger_instance = APILogger()
    return _api_logger_instance
