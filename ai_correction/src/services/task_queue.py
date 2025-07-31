#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理服务
实现异步任务队列和状态管理
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import deque
import logging
from concurrent.futures import ThreadPoolExecutor, Future

from src.models.task import Task, TaskStatus, TaskPriority, TaskHistory, TaskError
from src.infrastructure.logging import get_logger, get_performance_logger


class TaskQueue:
    """任务队列"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.logger = get_logger(f"{__name__}.TaskQueue")
        self.perf_logger = get_performance_logger(f"{__name__}.TaskQueue")
        
        # 任务存储
        self._tasks: Dict[str, Task] = {}
        self._task_history: Dict[str, List[TaskHistory]] = {}
        
        # 队列管理
        self._pending_queue = deque()  # 等待队列
        self._running_tasks: Dict[str, Future] = {}  # 运行中的任务
        self._paused_tasks: Dict[str, Task] = {}  # 暂停的任务
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 任务处理器注册
        self._task_handlers: Dict[str, Callable] = {}
        
        # 控制标志
        self._running = False
        self._shutdown = False
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 锁
        self._lock = threading.RLock()
    
    def register_handler(self, task_type: str, handler: Callable[[Task], Any]):
        """注册任务处理器"""
        with self._lock:
            self._task_handlers[task_type] = handler
            self.logger.info(f"注册任务处理器: {task_type}")
    
    def submit_task(self, task: Task) -> str:
        """提交任务到队列"""
        with self._lock:
            # 检查依赖任务
            if task.depends_on:
                for dep_id in task.depends_on:
                    if dep_id not in self._tasks:
                        raise ValueError(f"依赖任务不存在: {dep_id}")
                    dep_task = self._tasks[dep_id]
                    if dep_task.status != TaskStatus.COMPLETED:
                        raise ValueError(f"依赖任务未完成: {dep_id}")
            
            # 添加到任务存储
            self._tasks[task.id] = task
            self._task_history[task.id] = []
            
            # 添加到等待队列
            self._pending_queue.append(task.id)
            
            # 记录历史
            self._add_history(task.id, "created", {"priority": task.priority.value})
            
            self.logger.info(f"任务已提交: {task.id} - {task.name}")
            return task.id
    
    def start(self):
        """启动任务队列处理"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._shutdown = False
            
            # 启动监控线程
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            
            self.logger.info("任务队列已启动")
    
    def stop(self, wait: bool = True):
        """停止任务队列处理"""
        with self._lock:
            if not self._running:
                return
            
            self._shutdown = True
            self._running = False
            
            # 取消所有运行中的任务
            for task_id, future in self._running_tasks.items():
                future.cancel()
                task = self._tasks.get(task_id)
                if task:
                    task.status = TaskStatus.CANCELLED
                    self._add_history(task_id, "cancelled", {"reason": "system_shutdown"})
            
            # 等待监控线程结束
            if wait and self._monitor_thread:
                self._monitor_thread.join(timeout=5)
            
            # 关闭线程池
            self._executor.shutdown(wait=wait)
            
            self.logger.info("任务队列已停止")
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.RUNNING:
                # 取消正在运行的任务
                future = self._running_tasks.get(task_id)
                if future:
                    future.cancel()
                    del self._running_tasks[task_id]
                
                # 移动到暂停队列
                task.status = TaskStatus.PAUSED
                self._paused_tasks[task_id] = task
                
                self._add_history(task_id, "paused")
                self.logger.info(f"任务已暂停: {task_id}")
                return True
            
            elif task.status == TaskStatus.PENDING:
                # 从等待队列中移除
                try:
                    self._pending_queue.remove(task_id)
                    task.status = TaskStatus.PAUSED
                    self._paused_tasks[task_id] = task
                    
                    self._add_history(task_id, "paused")
                    self.logger.info(f"等待任务已暂停: {task_id}")
                    return True
                except ValueError:
                    pass
            
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            task = self._paused_tasks.get(task_id)
            if not task or task.status != TaskStatus.PAUSED:
                return False
            
            # 从暂停队列移除
            del self._paused_tasks[task_id]
            
            # 重新加入等待队列
            task.status = TaskStatus.PENDING
            self._pending_queue.append(task_id)
            
            self._add_history(task_id, "resumed")
            self.logger.info(f"任务已恢复: {task_id}")
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.RUNNING:
                # 取消正在运行的任务
                future = self._running_tasks.get(task_id)
                if future:
                    future.cancel()
                    del self._running_tasks[task_id]
            
            elif task.status == TaskStatus.PENDING:
                # 从等待队列中移除
                try:
                    self._pending_queue.remove(task_id)
                except ValueError:
                    pass
            
            elif task.status == TaskStatus.PAUSED:
                # 从暂停队列中移除
                self._paused_tasks.pop(task_id, None)
            
            # 更新状态
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.add_error("user_cancelled", "任务被用户取消")
            
            self._add_history(task_id, "cancelled", {"reason": "user_request"})
            self.logger.info(f"任务已取消: {task_id}")
            return True
    
    def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or not task.can_retry():
                return False
            
            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.progress = task.progress.__class__()  # 重置进度
            
            # 重新加入等待队列
            self._pending_queue.append(task_id)
            
            self._add_history(task_id, "retried", {"retry_count": len(task.errors)})
            self.logger.info(f"任务已重试: {task_id}")
            return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_task_history(self, task_id: str) -> List[TaskHistory]:
        """获取任务历史"""
        return self._task_history.get(task_id, [])
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """根据状态获取任务列表"""
        return [task for task in self._tasks.values() if task.status == status]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self._lock:
            return {
                "total_tasks": len(self._tasks),
                "pending": len(self._pending_queue),
                "running": len(self._running_tasks),
                "paused": len(self._paused_tasks),
                "completed": len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED]),
                "cancelled": len([t for t in self._tasks.values() if t.status == TaskStatus.CANCELLED]),
                "max_workers": self.max_workers,
                "is_running": self._running
            }
    
    def cleanup_expired_tasks(self):
        """清理过期任务"""
        with self._lock:
            expired_tasks = []
            for task_id, task in self._tasks.items():
                if task.is_expired():
                    expired_tasks.append(task_id)
            
            for task_id in expired_tasks:
                del self._tasks[task_id]
                self._task_history.pop(task_id, None)
                self.logger.info(f"清理过期任务: {task_id}")
            
            return len(expired_tasks)
    
    def _monitor_loop(self):
        """监控循环"""
        self.logger.info("任务监控循环已启动")
        
        while not self._shutdown:
            try:
                # 处理等待队列
                self._process_pending_queue()
                
                # 检查运行中的任务
                self._check_running_tasks()
                
                # 定期清理过期任务
                if int(time.time()) % 300 == 0:  # 每5分钟清理一次
                    self.cleanup_expired_tasks()
                
                time.sleep(1)  # 1秒检查一次
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}", exc_info=True)
                time.sleep(5)  # 异常时等待5秒
        
        self.logger.info("任务监控循环已结束")
    
    def _process_pending_queue(self):
        """处理等待队列"""
        with self._lock:
            # 检查是否有可用的工作线程
            if len(self._running_tasks) >= self.max_workers:
                return
            
            # 按优先级排序等待队列
            pending_tasks = []
            while self._pending_queue:
                task_id = self._pending_queue.popleft()
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    pending_tasks.append(task)
            
            # 按优先级排序
            pending_tasks.sort(key=lambda t: t.priority.value, reverse=True)
            
            # 重新加入队列
            for task in pending_tasks:
                self._pending_queue.append(task.id)
            
            # 启动任务
            while self._pending_queue and len(self._running_tasks) < self.max_workers:
                task_id = self._pending_queue.popleft()
                task = self._tasks.get(task_id)
                if task:
                    self._start_task(task)
    
    def _start_task(self, task: Task):
        """启动任务"""
        try:
            # 检查是否有处理器
            handler = self._task_handlers.get(task.task_type.value)
            if not handler:
                task.status = TaskStatus.FAILED
                task.add_error("no_handler", f"没有找到任务类型的处理器: {task.task_type.value}")
                self._add_history(task.id, "failed", {"reason": "no_handler"})
                return
            
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # 提交到线程池
            future = self._executor.submit(self._execute_task, task, handler)
            self._running_tasks[task.id] = future
            
            self._add_history(task.id, "started")
            self.logger.info(f"任务已启动: {task.id} - {task.name}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.add_error("start_error", str(e))
            self._add_history(task.id, "failed", {"reason": "start_error", "error": str(e)})
            self.logger.error(f"启动任务失败: {task.id} - {e}")
    
    def _execute_task(self, task: Task, handler: Callable):
        """执行任务"""
        start_time = time.time()
        
        try:
            self.perf_logger.log_operation_start(
                f"task_execution_{task.task_type.value}",
                task_id=task.id,
                task_name=task.name
            )
            
            # 执行任务处理器
            result = handler(task)
            
            # 更新任务状态
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.output_data = result if isinstance(result, dict) else {"result": result}
                
                self._add_history(task.id, "completed", {"duration": time.time() - start_time})
            
            duration = time.time() - start_time
            self.perf_logger.log_operation_complete(
                f"task_execution_{task.task_type.value}",
                duration,
                True,
                task_id=task.id,
                task_name=task.name
            )
            
            self.logger.info(f"任务执行完成: {task.id} - {task.name} (耗时: {duration:.2f}秒)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            with self._lock:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.add_error("execution_error", str(e))
                
                self._add_history(task.id, "failed", {
                    "reason": "execution_error",
                    "error": str(e),
                    "duration": duration
                })
            
            self.perf_logger.log_operation_complete(
                f"task_execution_{task.task_type.value}",
                duration,
                False,
                task_id=task.id,
                task_name=task.name,
                error=str(e)
            )
            
            self.logger.error(f"任务执行失败: {task.id} - {e}", exc_info=True)
            
            # 检查是否需要自动重试
            if task.can_retry():
                self.logger.info(f"任务可以重试: {task.id}, 当前错误数: {len(task.errors)}, 最大重试数: {task.config.max_retries}")
                self._schedule_retry(task)
            else:
                self.logger.info(f"任务不能重试: {task.id}, 状态: {task.status}, 错误数: {len(task.errors)}, 最大重试数: {task.config.max_retries}")
        
        finally:
            # 从运行队列中移除
            with self._lock:
                self._running_tasks.pop(task.id, None)
    
    def _schedule_retry(self, task: Task):
        """安排重试"""
        def retry_after_delay():
            time.sleep(task.config.retry_delay.total_seconds())
            with self._lock:
                if task.status == TaskStatus.FAILED and task.can_retry():
                    # 重置任务状态以便重试
                    task.status = TaskStatus.PENDING
                    task.started_at = None
                    # 不重置completed_at，保留失败时间
                    self._pending_queue.append(task.id)
                    self._add_history(task.id, "retry_scheduled")
        
        # 在后台线程中延迟重试
        retry_thread = threading.Thread(target=retry_after_delay, daemon=True)
        retry_thread.start()
        
        self.logger.info(f"任务已安排重试: {task.id} (延迟: {task.config.retry_delay})")
    
    def _check_running_tasks(self):
        """检查运行中的任务"""
        with self._lock:
            completed_tasks = []
            
            for task_id, future in self._running_tasks.items():
                if future.done():
                    completed_tasks.append(task_id)
            
            # 清理已完成的任务
            for task_id in completed_tasks:
                del self._running_tasks[task_id]
    
    def _add_history(self, task_id: str, action: str, details: Dict[str, Any] = None):
        """添加历史记录"""
        history = TaskHistory(
            task_id=task_id,
            action=action,
            details=details or {}
        )
        
        if task_id not in self._task_history:
            self._task_history[task_id] = []
        
        self._task_history[task_id].append(history)