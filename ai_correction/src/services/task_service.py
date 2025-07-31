#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理服务
提供任务创建、管理和监控的高级接口
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import logging

from src.models.task import Task, TaskStatus, TaskType, TaskPriority, TaskHistory, TaskConfig
from src.services.task_queue import TaskQueue
from src.infrastructure.logging import get_logger


class TaskService:
    """任务管理服务"""
    
    def __init__(self, db_path: str = "tasks.db", max_workers: int = 4):
        self.db_path = Path(db_path)
        self.logger = get_logger(f"{__name__}.TaskService")
        
        # 初始化任务队列
        self.task_queue = TaskQueue(max_workers=max_workers)
        
        # 初始化数据库
        self._init_database()
        
        # 加载持久化任务
        self._load_tasks_from_db()
        
        # 注册默认任务处理器
        self._register_default_handlers()
        
        # 启动任务队列
        self.task_queue.start()
        
        self.logger.info("任务管理服务已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建任务表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建任务历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_history (
                        id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        details TEXT,
                        user_id TEXT,
                        FOREIGN KEY (task_id) REFERENCES tasks (id)
                    )
                ''')
                
                # 创建索引（简化版本，不使用json_extract）
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_task_id ON task_history (task_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks (updated_at)')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"初始化数据库失败: {e}")
            raise
    
    def _load_tasks_from_db(self):
        """从数据库加载任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT data FROM tasks')
                
                for (data_json,) in cursor.fetchall():
                    try:
                        task_data = json.loads(data_json)
                        task = Task.from_dict(task_data)
                        
                        # 重置运行中的任务状态
                        if task.status == TaskStatus.RUNNING:
                            task.status = TaskStatus.FAILED
                            task.add_error("system_restart", "系统重启导致任务中断")
                        
                        # 将任务添加到队列（但不自动启动）
                        self.task_queue._tasks[task.id] = task
                        
                        # 如果是等待或重试状态，重新加入队列
                        if task.status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
                            self.task_queue._pending_queue.append(task.id)
                        elif task.status == TaskStatus.PAUSED:
                            self.task_queue._paused_tasks[task.id] = task
                        
                    except Exception as e:
                        self.logger.error(f"加载任务失败: {e}")
                
                # 加载任务历史
                cursor.execute('SELECT task_id, action, timestamp, details, user_id FROM task_history ORDER BY timestamp')
                for task_id, action, timestamp, details_json, user_id in cursor.fetchall():
                    try:
                        history = TaskHistory(
                            task_id=task_id,
                            action=action,
                            timestamp=datetime.fromisoformat(timestamp),
                            details=json.loads(details_json) if details_json else {},
                            user_id=user_id
                        )
                        
                        if task_id not in self.task_queue._task_history:
                            self.task_queue._task_history[task_id] = []
                        self.task_queue._task_history[task_id].append(history)
                        
                    except Exception as e:
                        self.logger.error(f"加载任务历史失败: {e}")
                
                self.logger.info(f"从数据库加载了 {len(self.task_queue._tasks)} 个任务")
                
        except Exception as e:
            self.logger.error(f"从数据库加载任务失败: {e}")
    
    def _register_default_handlers(self):
        """注册默认任务处理器"""
        
        def grading_handler(task: Task) -> Dict[str, Any]:
            """批改任务处理器"""
            # 模拟批改过程
            import time
            
            files = task.input_data.get('files', [])
            total_files = len(files)
            
            results = []
            for i, file_info in enumerate(files):
                # 更新进度
                task.update_progress(
                    current_step=f"批改文件 {i+1}/{total_files}",
                    completed_steps=i,
                    total_steps=total_files,
                    current_operation=f"正在批改: {file_info.get('name', 'unknown')}"
                )
                
                # 模拟处理时间
                time.sleep(1)
                
                # 模拟批改结果
                result = {
                    'file_id': file_info.get('id'),
                    'file_name': file_info.get('name'),
                    'score': 85.5,
                    'feedback': '作业完成质量良好，建议在细节方面进一步完善。',
                    'graded_at': datetime.now().isoformat()
                }
                results.append(result)
            
            return {
                'total_files': total_files,
                'completed_files': len(results),
                'results': results,
                'summary': {
                    'average_score': sum(r['score'] for r in results) / len(results) if results else 0,
                    'total_time': task.get_duration().total_seconds() if task.get_duration() else 0
                }
            }
        
        def file_processing_handler(task: Task) -> Dict[str, Any]:
            """文件处理任务处理器"""
            import time
            
            files = task.input_data.get('files', [])
            operation = task.input_data.get('operation', 'process')
            
            processed_files = []
            for i, file_info in enumerate(files):
                task.update_progress(
                    current_step=f"处理文件 {i+1}/{len(files)}",
                    completed_steps=i,
                    total_steps=len(files),
                    current_operation=f"正在{operation}: {file_info.get('name', 'unknown')}"
                )
                
                time.sleep(0.5)  # 模拟处理时间
                
                processed_files.append({
                    'original': file_info,
                    'processed_at': datetime.now().isoformat(),
                    'status': 'success'
                })
            
            return {
                'operation': operation,
                'processed_files': processed_files,
                'total_processed': len(processed_files)
            }
        
        def report_generation_handler(task: Task) -> Dict[str, Any]:
            """报告生成任务处理器"""
            import time
            
            report_type = task.input_data.get('report_type', 'summary')
            data_source = task.input_data.get('data_source', {})
            
            # 模拟报告生成步骤
            steps = ['数据收集', '数据分析', '图表生成', '报告编写', '格式化输出']
            
            for i, step in enumerate(steps):
                task.update_progress(
                    current_step=step,
                    completed_steps=i,
                    total_steps=len(steps),
                    current_operation=f"正在执行: {step}"
                )
                time.sleep(1)
            
            return {
                'report_type': report_type,
                'generated_at': datetime.now().isoformat(),
                'file_path': f'/reports/{task.id}_{report_type}.pdf',
                'pages': 15,
                'charts': 8
            }
        
        # 注册处理器
        self.task_queue.register_handler(TaskType.GRADING.value, grading_handler)
        self.task_queue.register_handler(TaskType.FILE_PROCESSING.value, file_processing_handler)
        self.task_queue.register_handler(TaskType.REPORT_GENERATION.value, report_generation_handler)
    
    def create_task(self, name: str, task_type: TaskType, input_data: Dict[str, Any],
                   description: str = "", priority: TaskPriority = TaskPriority.NORMAL,
                   config: Optional[TaskConfig] = None, created_by: Optional[str] = None,
                   depends_on: List[str] = None) -> str:
        """创建新任务"""
        
        task = Task(
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            input_data=input_data,
            config=config or TaskConfig(),
            created_by=created_by,
            depends_on=depends_on or []
        )
        
        # 保存到数据库
        self._save_task_to_db(task)
        
        # 提交到队列
        task_id = self.task_queue.submit_task(task)
        
        self.logger.info(f"创建任务: {task_id} - {name}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.task_queue.get_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.get_task(task_id)
        return task.status if task else None
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务进度"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        return {
            'task_id': task_id,
            'status': task.status.value,
            'progress': task.progress.to_dict(),
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'duration': task.get_duration().total_seconds() if task.get_duration() else None,
            'errors': [error.to_dict() for error in task.errors]
        }
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        result = self.task_queue.pause_task(task_id)
        if result:
            self._update_task_in_db(task_id)
        return result
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        result = self.task_queue.resume_task(task_id)
        if result:
            self._update_task_in_db(task_id)
        return result
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        result = self.task_queue.cancel_task(task_id)
        if result:
            self._update_task_in_db(task_id)
        return result
    
    def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        result = self.task_queue.retry_task(task_id)
        if result:
            self._update_task_in_db(task_id)
        return result
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """根据状态获取任务列表"""
        return self.task_queue.get_tasks_by_status(status)
    
    def get_tasks_by_user(self, user_id: str) -> List[Task]:
        """获取用户的任务列表"""
        return [task for task in self.task_queue._tasks.values() if task.created_by == user_id]
    
    def get_task_history(self, task_id: str) -> List[TaskHistory]:
        """获取任务历史"""
        return self.task_queue.get_task_history(task_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return self.task_queue.get_queue_status()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        queue_status = self.get_queue_status()
        
        # 计算平均执行时间
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)
        avg_duration = 0
        if completed_tasks:
            durations = [task.get_duration().total_seconds() for task in completed_tasks if task.get_duration()]
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 计算成功率
        total_finished = len(completed_tasks) + len(self.get_tasks_by_status(TaskStatus.FAILED))
        success_rate = len(completed_tasks) / total_finished * 100 if total_finished > 0 else 0
        
        return {
            **queue_status,
            'average_duration': avg_duration,
            'success_rate': success_rate,
            'uptime': (datetime.now() - self._start_time).total_seconds() if hasattr(self, '_start_time') else 0
        }
    
    def register_task_handler(self, task_type: str, handler: Callable[[Task], Any]):
        """注册自定义任务处理器"""
        self.task_queue.register_handler(task_type, handler)
    
    def cleanup_expired_tasks(self) -> int:
        """清理过期任务"""
        count = self.task_queue.cleanup_expired_tasks()
        
        # 从数据库中删除过期任务（简化版本，不使用json_extract）
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有任务ID，然后在Python中过滤
                cursor.execute('SELECT id, data FROM tasks')
                expired_task_ids = []
                
                for task_id, data_json in cursor.fetchall():
                    try:
                        task_data = json.loads(data_json)
                        task = Task.from_dict(task_data)
                        if task.is_expired():
                            expired_task_ids.append(task_id)
                    except Exception:
                        # 如果任务数据损坏，也删除
                        expired_task_ids.append(task_id)
                
                # 删除过期任务
                if expired_task_ids:
                    placeholders = ','.join('?' * len(expired_task_ids))
                    cursor.execute(f'DELETE FROM tasks WHERE id IN ({placeholders})', expired_task_ids)
                    cursor.execute(f'DELETE FROM task_history WHERE task_id IN ({placeholders})', expired_task_ids)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"清理数据库中的过期任务失败: {e}")
        
        return count
    
    def shutdown(self):
        """关闭服务"""
        self.logger.info("正在关闭任务管理服务...")
        self.task_queue.stop()
        self.logger.info("任务管理服务已关闭")
    
    def _save_task_to_db(self, task: Task):
        """保存任务到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO tasks (id, data, updated_at) VALUES (?, ?, ?)',
                    (task.id, json.dumps(task.to_dict(), ensure_ascii=False), datetime.now())
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"保存任务到数据库失败: {e}")
    
    def _update_task_in_db(self, task_id: str):
        """更新数据库中的任务"""
        task = self.get_task(task_id)
        if task:
            self._save_task_to_db(task)
    
    def __enter__(self):
        self._start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# 全局任务服务实例
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """获取任务服务实例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service


def shutdown_task_service():
    """关闭任务服务"""
    global _task_service
    if _task_service:
        _task_service.shutdown()
        _task_service = None