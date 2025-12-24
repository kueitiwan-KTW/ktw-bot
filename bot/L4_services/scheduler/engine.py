# L4_services/scheduler/engine.py
# 建立日期：2025-12-24

"""
Scheduler Engine（排程引擎）

職責：
- 唯一能「建立/取消/查詢 job」的地方
- 管理 job queue
- Worker 執行任務
- 重試與節流

設計原則：
- L4 是引擎層，只負責「怎麼排」
- plugins 的 trigger specs 負責「排什麼」
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
import uuid


class JobStatus(Enum):
    """Job 狀態"""
    PENDING = "pending"       # 等待執行
    RUNNING = "running"       # 執行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失敗
    CANCELLED = "cancelled"   # 已取消


@dataclass
class Job:
    """排程任務"""
    job_id: str
    job_type: str              # reminder, review_check, publish
    tenant_id: str
    
    # 排程設定
    run_at: datetime           # 執行時間
    
    # 任務內容
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # 狀態
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    
    # 重試設定
    max_retries: int = 3
    retry_count: int = 0
    retry_delay_seconds: int = 60
    
    # 防重複
    idempotency_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'tenant_id': self.tenant_id,
            'run_at': self.run_at.isoformat(),
            'payload': self.payload,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'retry_count': self.retry_count,
        }


class SchedulerEngine:
    """
    排程引擎
    
    功能：
    - 新增/取消/查詢 job
    - Worker 執行任務
    - 重試機制
    """
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.handlers: Dict[str, Callable] = {}
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    # === Job 管理 ===
    
    def schedule(
        self,
        job_type: str,
        tenant_id: str,
        run_at: datetime,
        payload: Dict[str, Any] = None,
        idempotency_key: str = None,
        max_retries: int = 3
    ) -> str:
        """
        新增排程任務
        
        Args:
            job_type: 任務類型（如 check_in_reminder）
            tenant_id: 租戶 ID
            run_at: 執行時間
            payload: 任務資料
            idempotency_key: 防重複 key
            max_retries: 最大重試次數
            
        Returns:
            job_id
        """
        # 檢查 idempotency_key 防重複
        if idempotency_key:
            for job in self.jobs.values():
                if job.idempotency_key == idempotency_key and job.status == JobStatus.PENDING:
                    print(f"⚠️ Job 已存在（idempotency_key={idempotency_key}）")
                    return job.job_id
        
        job_id = str(uuid.uuid4())[:8]
        
        job = Job(
            job_id=job_id,
            job_type=job_type,
            tenant_id=tenant_id,
            run_at=run_at,
            payload=payload or {},
            idempotency_key=idempotency_key,
            max_retries=max_retries
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        print(f"📅 Job 已排程: {job_id} ({job_type}) @ {run_at}")
        return job_id
    
    def cancel(self, job_id: str) -> bool:
        """取消任務"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED
                    print(f"🚫 Job 已取消: {job_id}")
                    return True
        return False
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """查詢任務"""
        return self.jobs.get(job_id)
    
    def get_pending_jobs(self, job_type: str = None, tenant_id: str = None) -> List[Job]:
        """查詢等待中的任務"""
        result = []
        for job in self.jobs.values():
            if job.status != JobStatus.PENDING:
                continue
            if job_type and job.job_type != job_type:
                continue
            if tenant_id and job.tenant_id != tenant_id:
                continue
            result.append(job)
        return result
    
    # === Handler 註冊 ===
    
    def register_handler(self, job_type: str, handler: Callable):
        """
        註冊任務處理器
        
        Args:
            job_type: 任務類型
            handler: 處理函數，接收 (job: Job) -> bool
        """
        self.handlers[job_type] = handler
        print(f"📌 Handler 已註冊: {job_type}")
    
    # === Worker ===
    
    def start(self):
        """啟動 Worker"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        print("🚀 Scheduler Engine 已啟動")
    
    def stop(self):
        """停止 Worker"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        print("⏹️ Scheduler Engine 已停止")
    
    def _worker_loop(self):
        """Worker 主迴圈"""
        while self._running:
            now = datetime.now()
            
            # 找出到期的 jobs
            due_jobs = []
            with self._lock:
                for job in self.jobs.values():
                    if job.status == JobStatus.PENDING and job.run_at <= now:
                        due_jobs.append(job)
            
            # 執行到期的 jobs
            for job in due_jobs:
                self._execute_job(job)
            
            # 每秒檢查一次
            time.sleep(1)
    
    def _execute_job(self, job: Job):
        """執行任務"""
        handler = self.handlers.get(job.job_type)
        
        if not handler:
            print(f"⚠️ 找不到 Handler: {job.job_type}")
            job.status = JobStatus.FAILED
            return
        
        job.status = JobStatus.RUNNING
        job.executed_at = datetime.now()
        
        try:
            print(f"▶️ 執行 Job: {job.job_id} ({job.job_type})")
            success = handler(job)
            
            if success:
                job.status = JobStatus.COMPLETED
                print(f"✅ Job 完成: {job.job_id}")
            else:
                raise Exception("Handler 回傳 False")
                
        except Exception as e:
            print(f"❌ Job 失敗: {job.job_id} - {e}")
            job.retry_count += 1
            
            if job.retry_count < job.max_retries:
                # 重試
                job.status = JobStatus.PENDING
                job.run_at = datetime.now() + timedelta(seconds=job.retry_delay_seconds)
                print(f"🔄 Job 重試 ({job.retry_count}/{job.max_retries}): {job.job_id}")
            else:
                job.status = JobStatus.FAILED
                print(f"💀 Job 最終失敗: {job.job_id}")
    
    # === 便利方法 ===
    
    def schedule_reminder(
        self,
        tenant_id: str,
        user_id: str,
        message: str,
        run_at: datetime,
        reminder_type: str = "check_in"
    ) -> str:
        """
        快速排程提醒
        
        Args:
            tenant_id: 租戶 ID
            user_id: 用戶 ID
            message: 提醒訊息
            run_at: 發送時間
            reminder_type: 提醒類型
            
        Returns:
            job_id
        """
        return self.schedule(
            job_type="reminder",
            tenant_id=tenant_id,
            run_at=run_at,
            payload={
                "user_id": user_id,
                "message": message,
                "reminder_type": reminder_type
            },
            idempotency_key=f"{tenant_id}:{user_id}:{reminder_type}:{run_at.date()}"
        )


# 全域 Scheduler 實例
scheduler = SchedulerEngine()
