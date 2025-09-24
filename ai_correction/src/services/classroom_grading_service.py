#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级批改服务
提供班级作业批改的核心业务逻辑
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from src.models.classroom_grading_task import ClassroomGradingTask, ClassroomTaskStatus
from src.models.submission import Submission, SubmissionStatus
from src.models.task import Task, TaskType, TaskPriority
from src.models.grading_config import GradingConfig
from src.services.task_service import TaskService, get_task_service
from src.services.grading_config_service import GradingConfigService
from src.infrastructure.logging import get_logger


class ClassroomGradingService:
    """班级批改服务"""
    
    def __init__(self, db_path: str = "class_system.db",
                 task_service: Optional[TaskService] = None,
                 grading_config_service: Optional[GradingConfigService] = None):
        self.db_path = Path(db_path)
        self.logger = get_logger(f"{__name__}.ClassroomGradingService")
        
        # 依赖服务
        self.task_service = task_service or get_task_service()
        self.grading_config_service = grading_config_service or GradingConfigService()
        
        # 确保数据库存在
        self._ensure_database()
        
        # 注册批改任务处理器
        self._register_grading_handler()
        
        self.logger.info("班级批改服务已初始化")
    
    def _ensure_database(self):
        """确保数据库和表结构存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查grading_tasks表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='grading_tasks'
            """)
            
            if not cursor.fetchone():
                # 创建grading_tasks表
                cursor.execute('''
                    CREATE TABLE grading_tasks (
                        id TEXT PRIMARY KEY,
                        submission_id INTEGER NOT NULL,
                        assignment_id INTEGER NOT NULL,
                        student_username TEXT NOT NULL,
                        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'retrying')),
                        priority INTEGER DEFAULT 2,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        result_score REAL,
                        result_feedback TEXT,
                        confidence_score REAL,
                        criteria_scores TEXT,
                        improvement_suggestions TEXT,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        max_retries INTEGER DEFAULT 3,
                        created_by TEXT,
                        processing_node TEXT,
                        estimated_duration INTEGER,
                        FOREIGN KEY (submission_id) REFERENCES submissions (id),
                        FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                        FOREIGN KEY (student_username) REFERENCES users (username)
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX idx_grading_tasks_status ON grading_tasks(status)')
                cursor.execute('CREATE INDEX idx_grading_tasks_priority ON grading_tasks(priority, created_at)')
                cursor.execute('CREATE INDEX idx_grading_tasks_assignment ON grading_tasks(assignment_id)')
                cursor.execute('CREATE INDEX idx_grading_tasks_student ON grading_tasks(student_username)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"确保数据库结构失败: {e}")
            raise
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _register_grading_handler(self):
        """注册批改任务处理器"""
        def classroom_grading_handler(task: Task) -> Dict[str, Any]:
            """班级批改任务处理器"""
            try:
                # 从任务数据中获取批改任务信息
                grading_task_data = task.input_data.get('grading_task')
                if not grading_task_data:
                    raise ValueError("缺少批改任务数据")
                
                grading_task = ClassroomGradingTask.from_dict(grading_task_data)
                
                # 执行批改逻辑
                result = self.process_grading_task(task)
                
                return result
                
            except Exception as e:
                self.logger.error(f"批改任务处理失败: {e}")
                raise
        
        # 注册处理器
        self.task_service.register_task_handler('classroom_grading', classroom_grading_handler)
    
    def trigger_auto_grading(self, submission: Submission) -> str:
        """触发自动批改"""
        try:
            # 获取作业信息
            assignment = self._get_assignment_info(submission.assignment_id)
            if not assignment:
                self.logger.error(f"作业不存在: {submission.assignment_id}")
                return None
            
            # 检查是否启用自动批改
            if not assignment.get('auto_grading_enabled', True):
                self.logger.info(f"作业 {submission.assignment_id} 未启用自动批改")
                return None
            
            # 获取批改配置
            grading_config = None
            if assignment.get('grading_config_id'):
                grading_config = self.grading_config_service.load_config(assignment['grading_config_id'])
            elif assignment.get('grading_template_id'):
                template = self.grading_config_service.load_template(assignment['grading_template_id'])
                if template:
                    grading_config = template.config
            
            # 创建批改任务
            grading_task = ClassroomGradingTask(
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                student_username=submission.student_username,
                answer_files=submission.answer_files,
                marking_files=json.loads(assignment.get('marking_files', '[]')),
                grading_config=grading_config,
                priority=TaskPriority.NORMAL,
                created_by='system'
            )
            
            # 验证任务数据
            validation_errors = grading_task.validate()
            if validation_errors:
                self.logger.error(f"批改任务验证失败: {validation_errors}")
                return None
            
            # 保存批改任务到数据库
            self._save_grading_task(grading_task)
            
            # 创建系统任务
            task_id = self.task_service.create_task(
                name=f"批改作业 - {assignment.get('title', '未知作业')}",
                task_type=TaskType.GRADING,
                input_data={
                    'grading_task': grading_task.to_dict(),
                    'submission_id': submission.id,
                    'assignment_id': submission.assignment_id,
                    'student_username': submission.student_username
                },
                description=f"为学生 {submission.student_username} 批改作业",
                priority=TaskPriority.NORMAL,
                created_by='system'
            )
            
            # 更新批改任务状态
            grading_task.start_processing()
            self._update_grading_task(grading_task)
            
            self.logger.info(f"自动批改任务已创建: {task_id} - 提交ID: {submission.id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"触发自动批改失败: {e}")
            return None
    
    def process_grading_task(self, task: Task) -> Dict[str, Any]:
        """处理批改任务执行逻辑"""
        try:
            grading_task_data = task.input_data.get('grading_task')
            grading_task = ClassroomGradingTask.from_dict(grading_task_data)
            
            # 更新任务进度
            task.update_progress(
                current_step="准备批改",
                completed_steps=0,
                total_steps=4,
                current_operation="加载批改配置和文件"
            )
            
            # 应用批改标准进行智能批改
            grading_result = self.apply_grading_standards(
                answer_files=grading_task.answer_files,
                marking_files=grading_task.marking_files,
                grading_config=grading_task.grading_config
            )
            
            # 更新任务进度
            task.update_progress(
                current_step="生成批改报告",
                completed_steps=3,
                total_steps=4,
                current_operation="整理批改结果"
            )
            
            # 生成批改报告
            report = self.generate_grading_report(grading_task, grading_result)
            
            # 完成批改任务
            grading_task.complete_with_result(
                score=grading_result['score'],
                feedback=grading_result['feedback'],
                confidence=grading_result.get('confidence'),
                criteria_scores=grading_result.get('criteria_scores'),
                suggestions=grading_result.get('suggestions')
            )
            
            # 更新数据库中的批改任务
            self._update_grading_task(grading_task)
            
            # 更新提交记录
            self._update_submission_with_result(grading_task)
            
            # 更新任务进度
            task.update_progress(
                current_step="批改完成",
                completed_steps=4,
                total_steps=4,
                current_operation="批改任务已完成"
            )
            
            return {
                'grading_task_id': grading_task.id,
                'submission_id': grading_task.submission_id,
                'score': grading_result['score'],
                'feedback': grading_result['feedback'],
                'confidence': grading_result.get('confidence'),
                'report': report,
                'processing_time': grading_task.get_duration()
            }
            
        except Exception as e:
            # 处理失败
            if 'grading_task' in locals():
                grading_task.fail_with_error(str(e))
                self._update_grading_task(grading_task)
            
            self.logger.error(f"处理批改任务失败: {e}")
            raise
    
    def apply_grading_standards(self, answer_files: List[str], marking_files: List[str],
                               grading_config: Optional[GradingConfig] = None) -> Dict[str, Any]:
        """应用批改标准进行智能批改"""
        try:
            # 模拟AI批改过程
            import time
            import random
            
            # 模拟处理时间
            time.sleep(2)
            
            # 基础分数计算
            base_score = random.uniform(70, 95)
            
            # 如果有批改配置，使用配置进行更精确的评分
            if grading_config:
                criteria_scores = {}
                total_weight = 0
                weighted_score = 0
                
                for rule in grading_config.scoring_rules:
                    # 模拟每个评分标准的得分
                    rule_score = random.uniform(0.7, 0.95) * rule.max_score
                    criteria_scores[rule.name] = rule_score
                    
                    # 计算加权分数
                    weight = rule.weight if rule.weight > 0 else 1
                    weighted_score += rule_score * weight
                    total_weight += weight
                
                if total_weight > 0:
                    base_score = weighted_score / total_weight
            else:
                # 使用默认评分标准
                criteria_scores = {
                    '内容准确性': random.uniform(70, 95),
                    '语言质量': random.uniform(75, 90),
                    '结构逻辑': random.uniform(80, 95)
                }
            
            # 生成反馈
            feedback_parts = []
            
            if base_score >= 90:
                feedback_parts.append("作业完成质量优秀，内容准确，表达清晰。")
            elif base_score >= 80:
                feedback_parts.append("作业完成质量良好，大部分内容正确。")
            elif base_score >= 70:
                feedback_parts.append("作业基本完成，但还有改进空间。")
            else:
                feedback_parts.append("作业需要进一步完善。")
            
            # 生成改进建议
            suggestions = []
            if base_score < 85:
                suggestions.append("建议加强对基础概念的理解")
            if base_score < 80:
                suggestions.append("注意语言表达的准确性")
            if base_score < 75:
                suggestions.append("完善答案的逻辑结构")
            
            # 计算置信度
            confidence = random.uniform(0.75, 0.95)
            if not marking_files:
                confidence *= 0.8  # 没有批改标准时降低置信度
            
            feedback = " ".join(feedback_parts)
            if suggestions:
                feedback += " 改进建议：" + "；".join(suggestions) + "。"
            
            return {
                'score': round(base_score, 1),
                'feedback': feedback,
                'confidence': round(confidence, 3),
                'criteria_scores': {k: round(v, 1) for k, v in criteria_scores.items()},
                'suggestions': suggestions,
                'processing_details': {
                    'answer_files_count': len(answer_files),
                    'marking_files_count': len(marking_files),
                    'has_grading_config': grading_config is not None,
                    'grading_method': 'ai_with_config' if grading_config else 'ai_default'
                }
            }
            
        except Exception as e:
            self.logger.error(f"应用批改标准失败: {e}")
            raise
    
    def generate_grading_report(self, grading_task: ClassroomGradingTask, 
                               grading_result: Dict[str, Any]) -> str:
        """生成详细的批改报告"""
        try:
            report_parts = []
            
            # 报告头部
            report_parts.append("=== 作业批改报告 ===")
            report_parts.append(f"学生：{grading_task.student_username}")
            report_parts.append(f"作业ID：{grading_task.assignment_id}")
            report_parts.append(f"批改时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_parts.append("")
            
            # 评分结果
            report_parts.append("=== 评分结果 ===")
            report_parts.append(f"总分：{grading_result['score']}")
            report_parts.append(f"AI置信度：{grading_result.get('confidence', 0):.1%}")
            report_parts.append("")
            
            # 分项得分
            if grading_result.get('criteria_scores'):
                report_parts.append("=== 分项得分 ===")
                for criterion, score in grading_result['criteria_scores'].items():
                    report_parts.append(f"{criterion}：{score}")
                report_parts.append("")
            
            # 详细反馈
            report_parts.append("=== 详细反馈 ===")
            report_parts.append(grading_result['feedback'])
            report_parts.append("")
            
            # 改进建议
            if grading_result.get('suggestions'):
                report_parts.append("=== 改进建议 ===")
                for i, suggestion in enumerate(grading_result['suggestions'], 1):
                    report_parts.append(f"{i}. {suggestion}")
                report_parts.append("")
            
            # 技术信息
            processing_details = grading_result.get('processing_details', {})
            report_parts.append("=== 批改信息 ===")
            report_parts.append(f"答案文件数：{processing_details.get('answer_files_count', 0)}")
            report_parts.append(f"批改标准文件数：{processing_details.get('marking_files_count', 0)}")
            report_parts.append(f"批改方法：{processing_details.get('grading_method', '未知')}")
            duration = grading_task.get_duration()
            report_parts.append(f"处理时长：{duration:.2f}秒" if duration else "处理时长：未知")
            
            return "\n".join(report_parts)
            
        except Exception as e:
            self.logger.error(f"生成批改报告失败: {e}")
            return f"批改报告生成失败: {str(e)}"
    
    def get_grading_task(self, task_id: str) -> Optional[ClassroomGradingTask]:
        """获取批改任务"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM grading_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = self._row_to_grading_task(dict(row))
                conn.close()
                return task
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"获取批改任务失败: {e}")
            return None
    
    def get_grading_tasks_by_status(self, status: ClassroomTaskStatus,
                                   assignment_id: Optional[int] = None,
                                   student_username: Optional[str] = None) -> List[ClassroomGradingTask]:
        """根据状态获取批改任务列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM grading_tasks WHERE status = ?'
            params = [status.value]
            
            if assignment_id:
                query += ' AND assignment_id = ?'
                params.append(assignment_id)
            
            if student_username:
                query += ' AND student_username = ?'
                params.append(student_username)
            
            query += ' ORDER BY priority DESC, created_at ASC'
            
            cursor.execute(query, params)
            
            tasks = []
            for row in cursor.fetchall():
                task = self._row_to_grading_task(dict(row))
                tasks.append(task)
            
            conn.close()
            return tasks
            
        except Exception as e:
            self.logger.error(f"根据状态获取批改任务失败: {e}")
            return []
    
    def get_pending_grading_tasks(self, limit: int = 50) -> List[ClassroomGradingTask]:
        """获取待处理的批改任务"""
        return self.get_grading_tasks_by_status(ClassroomTaskStatus.PENDING)[:limit]
    
    def get_failed_grading_tasks(self) -> List[ClassroomGradingTask]:
        """获取失败的批改任务"""
        return self.get_grading_tasks_by_status(ClassroomTaskStatus.FAILED)
    
    def retry_failed_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        try:
            grading_task = self.get_grading_task(task_id)
            if not grading_task or not grading_task.can_retry():
                return False
            
            # 重试任务
            grading_task.retry()
            self._update_grading_task(grading_task)
            
            # 重新创建系统任务
            assignment = self._get_assignment_info(grading_task.assignment_id)
            task_id = self.task_service.create_task(
                name=f"重试批改作业 - {assignment.get('title', '未知作业')}",
                task_type=TaskType.GRADING,
                input_data={
                    'grading_task': grading_task.to_dict(),
                    'submission_id': grading_task.submission_id,
                    'assignment_id': grading_task.assignment_id,
                    'student_username': grading_task.student_username
                },
                description=f"重试为学生 {grading_task.student_username} 批改作业",
                priority=TaskPriority.HIGH,  # 重试任务使用高优先级
                created_by='system'
            )
            
            self.logger.info(f"批改任务重试已创建: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"重试批改任务失败: {e}")
            return False
    
    def cancel_grading_task(self, task_id: str) -> bool:
        """取消批改任务"""
        try:
            grading_task = self.get_grading_task(task_id)
            if not grading_task:
                return False
            
            # 取消任务
            if grading_task.cancel():
                self._update_grading_task(grading_task)
                
                # 尝试取消系统任务
                self.task_service.cancel_task(task_id)
                
                self.logger.info(f"批改任务已取消: {task_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"取消批改任务失败: {e}")
            return False
    
    def get_grading_statistics(self, assignment_id: Optional[int] = None,
                              student_username: Optional[str] = None) -> Dict[str, Any]:
        """获取批改统计数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_tasks,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_tasks,
                    AVG(result_score) as average_score,
                    AVG(confidence_score) as average_confidence,
                    AVG(CASE WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400 END) as average_processing_time
                FROM grading_tasks
                WHERE 1=1
            '''
            
            params = []
            
            if assignment_id:
                base_query += ' AND assignment_id = ?'
                params.append(assignment_id)
            
            if student_username:
                base_query += ' AND student_username = ?'
                params.append(student_username)
            
            cursor.execute(base_query, params)
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                total_tasks = row['total_tasks'] or 0
                completed_tasks = row['completed_tasks'] or 0
                
                return {
                    'total_tasks': total_tasks,
                    'pending_tasks': row['pending_tasks'] or 0,
                    'processing_tasks': row['processing_tasks'] or 0,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': row['failed_tasks'] or 0,
                    'cancelled_tasks': row['cancelled_tasks'] or 0,
                    'completion_rate': round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0,
                    'average_score': round(row['average_score'], 2) if row['average_score'] else None,
                    'average_confidence': round(row['average_confidence'], 3) if row['average_confidence'] else None,
                    'average_processing_time': round(row['average_processing_time'], 2) if row['average_processing_time'] else None
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"获取批改统计失败: {e}")
            return {}
    
    def _get_assignment_info(self, assignment_id: int) -> Optional[Dict[str, Any]]:
        """获取作业信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM assignments WHERE id = ? AND is_active = 1
            ''', (assignment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            self.logger.error(f"获取作业信息失败: {e}")
            return None
    
    def _save_grading_task(self, grading_task: ClassroomGradingTask):
        """保存批改任务到数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO grading_tasks (
                    id, submission_id, assignment_id, student_username, status, priority,
                    created_at, started_at, completed_at, last_updated,
                    result_score, result_feedback, confidence_score, criteria_scores,
                    improvement_suggestions, error_message, retry_count, max_retries,
                    created_by, processing_node, estimated_duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                grading_task.id,
                grading_task.submission_id,
                grading_task.assignment_id,
                grading_task.student_username,
                grading_task.status.value,
                grading_task.priority.value,
                grading_task.created_at.isoformat(),
                grading_task.started_at.isoformat() if grading_task.started_at else None,
                grading_task.completed_at.isoformat() if grading_task.completed_at else None,
                grading_task.last_updated.isoformat(),
                grading_task.result_score,
                grading_task.result_feedback,
                grading_task.confidence_score,
                json.dumps(grading_task.criteria_scores, ensure_ascii=False),
                json.dumps(grading_task.improvement_suggestions, ensure_ascii=False),
                grading_task.error_message,
                grading_task.retry_count,
                grading_task.max_retries,
                grading_task.created_by,
                grading_task.processing_node,
                grading_task.estimated_duration
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存批改任务失败: {e}")
            raise
    
    def _update_grading_task(self, grading_task: ClassroomGradingTask):
        """更新批改任务"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE grading_tasks SET
                    status = ?, started_at = ?, completed_at = ?, last_updated = ?,
                    result_score = ?, result_feedback = ?, confidence_score = ?,
                    criteria_scores = ?, improvement_suggestions = ?, error_message = ?,
                    retry_count = ?, processing_node = ?
                WHERE id = ?
            ''', (
                grading_task.status.value,
                grading_task.started_at.isoformat() if grading_task.started_at else None,
                grading_task.completed_at.isoformat() if grading_task.completed_at else None,
                grading_task.last_updated.isoformat(),
                grading_task.result_score,
                grading_task.result_feedback,
                grading_task.confidence_score,
                json.dumps(grading_task.criteria_scores, ensure_ascii=False),
                json.dumps(grading_task.improvement_suggestions, ensure_ascii=False),
                grading_task.error_message,
                grading_task.retry_count,
                grading_task.processing_node,
                grading_task.id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"更新批改任务失败: {e}")
            raise
    
    def _update_submission_with_result(self, grading_task: ClassroomGradingTask):
        """用批改结果更新提交记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建详细批改信息
            grading_details = {
                'ai_score': grading_task.result_score,
                'ai_feedback': grading_task.result_feedback,
                'grading_criteria_scores': grading_task.criteria_scores,
                'improvement_suggestions': grading_task.improvement_suggestions,
                'grading_timestamp': grading_task.completed_at.isoformat() if grading_task.completed_at else None
            }
            
            cursor.execute('''
                UPDATE submissions SET
                    ai_result = ?, score = ?, status = ?, task_id = ?,
                    grading_details = ?, ai_confidence = ?, 
                    manual_review_required = ?, graded_at = ?
                WHERE id = ?
            ''', (
                grading_task.result_feedback,
                grading_task.result_score,
                SubmissionStatus.AI_GRADED.value,
                grading_task.id,
                json.dumps(grading_details, ensure_ascii=False),
                grading_task.confidence_score,
                grading_task.confidence_score < 0.7 if grading_task.confidence_score else False,
                grading_task.completed_at.isoformat() if grading_task.completed_at else None,
                grading_task.submission_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"更新提交记录失败: {e}")
            raise
    
    def _row_to_grading_task(self, row: Dict[str, Any]) -> ClassroomGradingTask:
        """将数据库行转换为批改任务对象"""
        return ClassroomGradingTask(
            id=row['id'],
            submission_id=row['submission_id'],
            assignment_id=row['assignment_id'],
            student_username=row['student_username'],
            status=ClassroomTaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            created_at=datetime.fromisoformat(row['created_at']),
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            last_updated=datetime.fromisoformat(row['last_updated']),
            result_score=row['result_score'],
            result_feedback=row['result_feedback'],
            confidence_score=row['confidence_score'],
            criteria_scores=json.loads(row['criteria_scores']) if row['criteria_scores'] else {},
            improvement_suggestions=json.loads(row['improvement_suggestions']) if row['improvement_suggestions'] else [],
            error_message=row['error_message'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            created_by=row['created_by'],
            processing_node=row['processing_node'],
            estimated_duration=row['estimated_duration']
        )