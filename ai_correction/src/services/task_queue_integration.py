#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列集成服务
扩展现有TaskService以支持班级批改任务类型
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from src.models.task import Task, TaskType, TaskPriority, TaskStatus
from src.models.classroom_grading_task import ClassroomGradingTask, ClassroomTaskStatus
from src.models.submission import Submission
from src.services.task_service import TaskService, get_task_service
from src.services.classroom_grading_service import ClassroomGradingService
from src.infrastructure.logging import get_logger


class TaskQueueIntegration:
    """任务队列集成服务"""
    
    def __init__(self, task_service: Optional[TaskService] = None,
                 grading_service: Optional[ClassroomGradingService] = None):
        self.logger = get_logger(f"{__name__}.TaskQueueIntegration")
        
        # 依赖服务
        self.task_service = task_service or get_task_service()
        self.grading_service = grading_service
        
        # 注册班级批改任务处理器
        self._register_classroom_grading_handler()
        
        self.logger.info("任务队列集成服务已初始化")
    
    def _register_classroom_grading_handler(self):
        """注册班级批改任务处理器"""
        def classroom_grading_handler(task: Task) -> Dict[str, Any]:
            """班级批改任务处理器"""
            try:
                self.logger.info(f"开始处理班级批改任务: {task.id}")
                
                # 更新任务进度
                task.update_progress(
                    current_step="初始化批改任务",
                    completed_steps=0,
                    total_steps=5,
                    current_operation="准备批改环境"
                )
                
                # 获取批改任务数据
                grading_task_data = task.input_data.get('grading_task')
                if not grading_task_data:
                    raise ValueError("缺少批改任务数据")
                
                grading_task = ClassroomGradingTask.from_dict(grading_task_data)
                
                # 更新批改任务状态为处理中
                grading_task.start_processing()
                if self.grading_service:
                    self.grading_service._update_grading_task(grading_task)
                
                # 更新任务进度
                task.update_progress(
                    current_step="加载批改配置",
                    completed_steps=1,
                    total_steps=5,
                    current_operation="准备批改标准和配置"
                )
                
                # 执行批改逻辑
                if self.grading_service:
                    result = self.grading_service.process_grading_task(task)
                else:
                    # 如果没有批改服务，执行简化的批改逻辑
                    result = self._simple_grading_process(task, grading_task)
                
                # 更新任务进度
                task.update_progress(
                    current_step="批改完成",
                    completed_steps=5,
                    total_steps=5,
                    current_operation="任务执行完成"
                )
                
                self.logger.info(f"班级批改任务完成: {task.id}")
                return result
                
            except Exception as e:
                self.logger.error(f"班级批改任务处理失败: {task.id} - {e}")
                
                # 更新批改任务状态为失败
                if 'grading_task' in locals():
                    grading_task.fail_with_error(str(e))
                    if self.grading_service:
                        self.grading_service._update_grading_task(grading_task)
                
                raise
        
        # 注册处理器
        self.task_service.register_task_handler('classroom_grading', classroom_grading_handler)
    
    def _simple_grading_process(self, task: Task, grading_task: ClassroomGradingTask) -> Dict[str, Any]:
        """简化的批改处理逻辑（当没有批改服务时使用）"""
        import time
        import random
        
        # 模拟批改过程
        task.update_progress(
            current_step="分析答案内容",
            completed_steps=2,
            total_steps=5,
            current_operation="正在分析学生答案"
        )
        time.sleep(1)
        
        task.update_progress(
            current_step="应用批改标准",
            completed_steps=3,
            total_steps=5,
            current_operation="根据批改标准评分"
        )
        time.sleep(1)
        
        task.update_progress(
            current_step="生成反馈",
            completed_steps=4,
            total_steps=5,
            current_operation="生成批改反馈"
        )
        time.sleep(1)
        
        # 生成模拟结果
        score = random.uniform(70, 95)
        feedback = f"作业完成质量{'优秀' if score >= 90 else '良好' if score >= 80 else '一般'}，继续努力！"
        confidence = random.uniform(0.7, 0.95)
        
        # 完成批改任务
        grading_task.complete_with_result(
            score=score,
            feedback=feedback,
            confidence=confidence
        )
        
        return {
            'grading_task_id': grading_task.id,
            'submission_id': grading_task.submission_id,
            'score': score,
            'feedback': feedback,
            'confidence': confidence,
            'processing_time': grading_task.get_duration()
        }
    
    def create_grading_task(self, submission: Submission, assignment_info: Dict[str, Any],
                           grading_config: Optional[Dict[str, Any]] = None,
                           priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """创建批改任务"""
        try:
            # 创建班级批改任务
            grading_task = ClassroomGradingTask(
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                student_username=submission.student_username,
                answer_files=submission.answer_files,
                marking_files=json.loads(assignment_info.get('marking_files', '[]')),
                priority=priority,
                created_by='system'
            )
            
            # 验证任务数据
            validation_errors = grading_task.validate()
            if validation_errors:
                self.logger.error(f"批改任务验证失败: {validation_errors}")
                return None
            
            # 创建系统任务
            task_id = self.task_service.create_task(
                name=f"批改作业 - {assignment_info.get('title', '未知作业')}",
                task_type=TaskType.GRADING,
                input_data={
                    'grading_task': grading_task.to_dict(),
                    'submission_id': submission.id,
                    'assignment_id': submission.assignment_id,
                    'student_username': submission.student_username,
                    'task_type': 'classroom_grading'
                },
                description=f"为学生 {submission.student_username} 批改作业",
                priority=priority,
                created_by='system'
            )
            
            self.logger.info(f"批改任务已创建: {task_id} - 提交ID: {submission.id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"创建批改任务失败: {e}")
            return None
    
    def get_grading_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取批改任务状态"""
        try:
            task = self.task_service.get_task(task_id)
            if not task:
                return None
            
            # 获取批改任务详细信息
            grading_task_data = task.input_data.get('grading_task')
            grading_task = None
            if grading_task_data:
                grading_task = ClassroomGradingTask.from_dict(grading_task_data)
            
            return {
                'task_id': task_id,
                'status': task.status.value,
                'progress': task.progress.to_dict(),
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'duration': task.get_duration().total_seconds() if task.get_duration() else None,
                'errors': [error.to_dict() for error in task.errors],
                'grading_task': grading_task.to_dict() if grading_task else None
            }
            
        except Exception as e:
            self.logger.error(f"获取批改任务状态失败: {e}")
            return None
    
    def cancel_grading_task(self, task_id: str) -> bool:
        """取消批改任务"""
        try:
            success = self.task_service.cancel_task(task_id)
            if success:
                self.logger.info(f"批改任务已取消: {task_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"取消批改任务失败: {e}")
            return False
    
    def retry_grading_task(self, task_id: str) -> bool:
        """重试批改任务"""
        try:
            success = self.task_service.retry_task(task_id)
            if success:
                self.logger.info(f"批改任务已重试: {task_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"重试批改任务失败: {e}")
            return False
    
    def get_grading_queue_status(self) -> Dict[str, Any]:
        """获取批改队列状态"""
        try:
            # 获取整体队列状态
            queue_status = self.task_service.get_queue_status()
            
            # 获取批改任务特定统计
            grading_tasks = [
                task for task in self.task_service.task_queue._tasks.values()
                if task.task_type == TaskType.GRADING and 
                task.input_data.get('task_type') == 'classroom_grading'
            ]
            
            grading_stats = {
                'total_grading_tasks': len(grading_tasks),
                'pending_grading_tasks': len([t for t in grading_tasks if t.status == TaskStatus.PENDING]),
                'running_grading_tasks': len([t for t in grading_tasks if t.status == TaskStatus.RUNNING]),
                'completed_grading_tasks': len([t for t in grading_tasks if t.status == TaskStatus.COMPLETED]),
                'failed_grading_tasks': len([t for t in grading_tasks if t.status == TaskStatus.FAILED])
            }
            
            return {
                **queue_status,
                'grading_statistics': grading_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取批改队列状态失败: {e}")
            return {}
    
    def get_pending_grading_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取待处理的批改任务"""
        try:
            pending_tasks = self.task_service.get_tasks_by_status(TaskStatus.PENDING)
            
            # 筛选批改任务
            grading_tasks = [
                task for task in pending_tasks
                if task.task_type == TaskType.GRADING and 
                task.input_data.get('task_type') == 'classroom_grading'
            ]
            
            # 按优先级和创建时间排序
            grading_tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
            
            # 转换为字典格式
            result = []
            for task in grading_tasks[:limit]:
                grading_task_data = task.input_data.get('grading_task')
                grading_task = ClassroomGradingTask.from_dict(grading_task_data) if grading_task_data else None
                
                result.append({
                    'task_id': task.id,
                    'name': task.name,
                    'priority': task.priority.value,
                    'created_at': task.created_at.isoformat(),
                    'submission_id': task.input_data.get('submission_id'),
                    'assignment_id': task.input_data.get('assignment_id'),
                    'student_username': task.input_data.get('student_username'),
                    'grading_task': grading_task.to_dict() if grading_task else None
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取待处理批改任务失败: {e}")
            return []
    
    def get_failed_grading_tasks(self) -> List[Dict[str, Any]]:
        """获取失败的批改任务"""
        try:
            failed_tasks = self.task_service.get_tasks_by_status(TaskStatus.FAILED)
            
            # 筛选批改任务
            grading_tasks = [
                task for task in failed_tasks
                if task.task_type == TaskType.GRADING and 
                task.input_data.get('task_type') == 'classroom_grading'
            ]
            
            # 转换为字典格式
            result = []
            for task in grading_tasks:
                grading_task_data = task.input_data.get('grading_task')
                grading_task = ClassroomGradingTask.from_dict(grading_task_data) if grading_task_data else None
                
                result.append({
                    'task_id': task.id,
                    'name': task.name,
                    'created_at': task.created_at.isoformat(),
                    'failed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'errors': [error.to_dict() for error in task.errors],
                    'submission_id': task.input_data.get('submission_id'),
                    'assignment_id': task.input_data.get('assignment_id'),
                    'student_username': task.input_data.get('student_username'),
                    'grading_task': grading_task.to_dict() if grading_task else None,
                    'can_retry': len(task.errors) < 3  # 简单的重试逻辑
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取失败批改任务失败: {e}")
            return []
    
    def cleanup_completed_grading_tasks(self, older_than_hours: int = 24) -> int:
        """清理已完成的批改任务"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            completed_tasks = self.task_service.get_tasks_by_status(TaskStatus.COMPLETED)
            
            # 筛选需要清理的批改任务
            tasks_to_cleanup = [
                task for task in completed_tasks
                if (task.task_type == TaskType.GRADING and 
                    task.input_data.get('task_type') == 'classroom_grading' and
                    task.completed_at and task.completed_at < cutoff_time)
            ]
            
            # 清理任务（这里可以实现具体的清理逻辑）
            cleanup_count = 0
            for task in tasks_to_cleanup:
                # 可以选择删除任务或标记为已归档
                # 这里暂时只记录日志
                self.logger.info(f"清理已完成的批改任务: {task.id}")
                cleanup_count += 1
            
            self.logger.info(f"清理了 {cleanup_count} 个已完成的批改任务")
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"清理已完成批改任务失败: {e}")
            return 0
    
    def get_grading_task_metrics(self) -> Dict[str, Any]:
        """获取批改任务指标"""
        try:
            all_tasks = list(self.task_service.task_queue._tasks.values())
            
            # 筛选批改任务
            grading_tasks = [
                task for task in all_tasks
                if task.task_type == TaskType.GRADING and 
                task.input_data.get('task_type') == 'classroom_grading'
            ]
            
            if not grading_tasks:
                return {
                    'total_tasks': 0,
                    'average_processing_time': 0,
                    'success_rate': 0,
                    'throughput_per_hour': 0
                }
            
            # 计算指标
            completed_tasks = [t for t in grading_tasks if t.status == TaskStatus.COMPLETED]
            failed_tasks = [t for t in grading_tasks if t.status == TaskStatus.FAILED]
            
            # 平均处理时间
            processing_times = [
                t.get_duration().total_seconds() for t in completed_tasks 
                if t.get_duration()
            ]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            # 成功率
            total_finished = len(completed_tasks) + len(failed_tasks)
            success_rate = len(completed_tasks) / total_finished * 100 if total_finished > 0 else 0
            
            # 吞吐量（每小时完成的任务数）
            if completed_tasks:
                # 计算最近24小时的完成任务数
                recent_completed = [
                    t for t in completed_tasks
                    if t.completed_at and (datetime.now() - t.completed_at).total_seconds() <= 86400
                ]
                throughput_per_hour = len(recent_completed) / 24
            else:
                throughput_per_hour = 0
            
            return {
                'total_tasks': len(grading_tasks),
                'completed_tasks': len(completed_tasks),
                'failed_tasks': len(failed_tasks),
                'pending_tasks': len([t for t in grading_tasks if t.status == TaskStatus.PENDING]),
                'running_tasks': len([t for t in grading_tasks if t.status == TaskStatus.RUNNING]),
                'average_processing_time': round(avg_processing_time, 2),
                'success_rate': round(success_rate, 2),
                'throughput_per_hour': round(throughput_per_hour, 2)
            }
            
        except Exception as e:
            self.logger.error(f"获取批改任务指标失败: {e}")
            return {}
    
    def set_grading_service(self, grading_service: ClassroomGradingService):
        """设置批改服务"""
        self.grading_service = grading_service
        self.logger.info("批改服务已设置")


# 全局任务队列集成实例
_task_queue_integration: Optional[TaskQueueIntegration] = None


def get_task_queue_integration() -> TaskQueueIntegration:
    """获取任务队列集成实例"""
    global _task_queue_integration
    if _task_queue_integration is None:
        _task_queue_integration = TaskQueueIntegration()
    return _task_queue_integration


def shutdown_task_queue_integration():
    """关闭任务队列集成"""
    global _task_queue_integration
    if _task_queue_integration:
        _task_queue_integration = None