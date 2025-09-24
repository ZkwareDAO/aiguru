#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交服务
提供作业提交管理的核心业务逻辑
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from src.models.submission import Submission, SubmissionStatus, SubmissionGradingDetails
from src.infrastructure.logging import get_logger


class SubmissionService:
    """提交服务"""
    
    def __init__(self, db_path: str = "class_system.db"):
        self.db_path = Path(db_path)
        self.logger = get_logger(f"{__name__}.SubmissionService")
        
        # 确保数据库存在
        self._ensure_database()
        
        self.logger.info("提交服务已初始化")
    
    def _ensure_database(self):
        """确保数据库和表结构存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查submissions表是否存在扩展字段
            cursor.execute("PRAGMA table_info(submissions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 如果缺少扩展字段，添加它们
            if 'task_id' not in columns:
                cursor.execute('ALTER TABLE submissions ADD COLUMN task_id TEXT')
            if 'grading_details' not in columns:
                cursor.execute('ALTER TABLE submissions ADD COLUMN grading_details TEXT')
            if 'ai_confidence' not in columns:
                cursor.execute('ALTER TABLE submissions ADD COLUMN ai_confidence REAL')
            if 'manual_review_required' not in columns:
                cursor.execute('ALTER TABLE submissions ADD COLUMN manual_review_required BOOLEAN DEFAULT 0')
            
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
    
    def submit_assignment(self, assignment_id: int, student_username: str, 
                         answer_files: List[str]) -> bool:
        """提交作业"""
        try:
            # 创建提交对象并验证
            submission = Submission(
                assignment_id=assignment_id,
                student_username=student_username,
                answer_files=answer_files,
                status=SubmissionStatus.SUBMITTED
            )
            
            # 验证提交数据
            validation_errors = submission.validate()
            if validation_errors:
                self.logger.error(f"提交数据验证失败: {validation_errors}")
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # 检查作业是否存在且活跃
                cursor.execute('''
                    SELECT id, title, deadline FROM assignments 
                    WHERE id = ? AND is_active = 1
                ''', (assignment_id,))
                
                assignment = cursor.fetchone()
                if not assignment:
                    self.logger.error(f"作业不存在或已停用: {assignment_id}")
                    return False
                
                # 检查是否过期（允许过期提交但标记为迟交）
                is_late = False
                if assignment['deadline']:
                    deadline = datetime.fromisoformat(assignment['deadline'])
                    if datetime.now() > deadline:
                        is_late = True
                
                # 插入或更新提交记录
                cursor.execute('''
                    INSERT OR REPLACE INTO submissions (
                        assignment_id, student_username, answer_files, status, submitted_at
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    submission.assignment_id,
                    submission.student_username,
                    json.dumps(submission.answer_files, ensure_ascii=False),
                    submission.status.value,
                    submission.submitted_at.isoformat()
                ))
                
                submission_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"作业提交成功: {submission_id} - 学生: {student_username}, 作业: {assignment_id}")
                
                # 添加提交通知
                self._notify_submission(assignment_id, student_username, assignment['title'], is_late)
                
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"提交作业数据库操作失败: {e}")
                return False
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"提交作业失败: {e}")
            return False
    
    def get_submission(self, assignment_id: int, student_username: str) -> Optional[Submission]:
        """获取指定学生的作业提交"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, a.title as assignment_title, a.deadline as assignment_deadline
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                WHERE s.assignment_id = ? AND s.student_username = ?
            ''', (assignment_id, student_username))
            
            row = cursor.fetchone()
            if row:
                submission = Submission.from_db_row(dict(row))
                submission.assignment_title = row['assignment_title']
                submission.assignment_deadline = row['assignment_deadline']
                conn.close()
                return submission
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"获取提交记录失败: {e}")
            return None
    
    def get_assignment_submissions(self, assignment_id: int) -> List[Submission]:
        """获取作业的所有提交"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, u.real_name, a.title as assignment_title
                FROM submissions s
                JOIN users u ON s.student_username = u.username
                JOIN assignments a ON s.assignment_id = a.id
                WHERE s.assignment_id = ?
                ORDER BY s.submitted_at DESC
            ''', (assignment_id,))
            
            submissions = []
            for row in cursor.fetchall():
                submission = Submission.from_db_row(dict(row))
                submission.student_real_name = row['real_name']
                submission.assignment_title = row['assignment_title']
                submissions.append(submission)
            
            conn.close()
            return submissions
            
        except Exception as e:
            self.logger.error(f"获取作业提交列表失败: {e}")
            return []
    
    def update_submission_feedback(self, submission_id: int, teacher_feedback: str, 
                                  score: Optional[float] = None) -> bool:
        """更新提交反馈（教师修改）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取当前提交记录
            cursor.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,))
            row = cursor.fetchone()
            if not row:
                self.logger.error(f"提交记录不存在: {submission_id}")
                return False
            
            submission = Submission.from_db_row(dict(row))
            
            # 设置教师审核结果
            submission.set_teacher_review(score, teacher_feedback)
            
            try:
                # 更新数据库
                cursor.execute('''
                    UPDATE submissions 
                    SET teacher_feedback = ?, score = ?, status = ?, 
                        grading_details = ?, manual_review_required = ?, graded_at = ?
                    WHERE id = ?
                ''', (
                    submission.teacher_feedback,
                    submission.score,
                    submission.status.value,
                    json.dumps(submission.grading_details.to_dict(), ensure_ascii=False) if submission.grading_details else None,
                    submission.manual_review_required,
                    submission.graded_at.isoformat() if submission.graded_at else None,
                    submission_id
                ))
                
                conn.commit()
                
                self.logger.info(f"提交反馈更新成功: {submission_id}")
                
                # 通知学生反馈已更新
                self._notify_feedback_updated(submission.assignment_id, submission.student_username)
                
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"更新提交反馈数据库操作失败: {e}")
                return False
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"更新提交反馈失败: {e}")
            return False
    
    def get_submission_history(self, student_username: str, limit: int = 50) -> List[Submission]:
        """获取学生提交历史"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, a.title as assignment_title, c.name as class_name
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                WHERE s.student_username = ?
                ORDER BY s.submitted_at DESC
                LIMIT ?
            ''', (student_username, limit))
            
            submissions = []
            for row in cursor.fetchall():
                submission = Submission.from_db_row(dict(row))
                submission.assignment_title = row['assignment_title']
                submission.class_name = row['class_name']
                submissions.append(submission)
            
            conn.close()
            return submissions
            
        except Exception as e:
            self.logger.error(f"获取提交历史失败: {e}")
            return []
    
    def get_submissions_by_status(self, status: SubmissionStatus, 
                                 assignment_id: Optional[int] = None,
                                 class_id: Optional[int] = None) -> List[Submission]:
        """根据状态获取提交列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT s.*, a.title as assignment_title, c.name as class_name, u.real_name
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                JOIN users u ON s.student_username = u.username
                WHERE s.status = ?
            '''
            
            params = [status.value]
            
            if assignment_id:
                base_query += ' AND s.assignment_id = ?'
                params.append(assignment_id)
            
            if class_id:
                base_query += ' AND a.class_id = ?'
                params.append(class_id)
            
            base_query += ' ORDER BY s.submitted_at DESC'
            
            cursor.execute(base_query, params)
            
            submissions = []
            for row in cursor.fetchall():
                submission = Submission.from_db_row(dict(row))
                submission.assignment_title = row['assignment_title']
                submission.class_name = row['class_name']
                submission.student_real_name = row['real_name']
                submissions.append(submission)
            
            conn.close()
            return submissions
            
        except Exception as e:
            self.logger.error(f"根据状态获取提交失败: {e}")
            return []
    
    def get_pending_grading_submissions(self, teacher_username: Optional[str] = None) -> List[Submission]:
        """获取待批改的提交"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT s.*, a.title as assignment_title, c.name as class_name, u.real_name
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                JOIN users u ON s.student_username = u.username
                WHERE s.status = ?
            '''
            
            params = [SubmissionStatus.SUBMITTED.value]
            
            if teacher_username:
                base_query += ' AND c.teacher_username = ?'
                params.append(teacher_username)
            
            base_query += ' ORDER BY s.submitted_at ASC'  # 按提交时间正序，先提交先批改
            
            cursor.execute(base_query, params)
            
            submissions = []
            for row in cursor.fetchall():
                submission = Submission.from_db_row(dict(row))
                submission.assignment_title = row['assignment_title']
                submission.class_name = row['class_name']
                submission.student_real_name = row['real_name']
                submissions.append(submission)
            
            conn.close()
            return submissions
            
        except Exception as e:
            self.logger.error(f"获取待批改提交失败: {e}")
            return []
    
    def get_submissions_requiring_review(self, teacher_username: Optional[str] = None) -> List[Submission]:
        """获取需要人工审核的提交"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT s.*, a.title as assignment_title, c.name as class_name, u.real_name
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                JOIN users u ON s.student_username = u.username
                WHERE (s.manual_review_required = 1 OR s.status = ?)
            '''
            
            params = [SubmissionStatus.PENDING_REVIEW.value]
            
            if teacher_username:
                base_query += ' AND c.teacher_username = ?'
                params.append(teacher_username)
            
            base_query += ' ORDER BY s.submitted_at ASC'
            
            cursor.execute(base_query, params)
            
            submissions = []
            for row in cursor.fetchall():
                submission = Submission.from_db_row(dict(row))
                submission.assignment_title = row['assignment_title']
                submission.class_name = row['class_name']
                submission.student_real_name = row['real_name']
                submissions.append(submission)
            
            conn.close()
            return submissions
            
        except Exception as e:
            self.logger.error(f"获取需要审核的提交失败: {e}")
            return []
    
    def update_submission_grading_result(self, submission_id: int, score: float, 
                                       feedback: str, confidence: float = None,
                                       criteria_scores: Dict[str, float] = None,
                                       suggestions: List[str] = None,
                                       task_id: Optional[str] = None) -> bool:
        """更新提交的AI批改结果"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取当前提交记录
            cursor.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,))
            row = cursor.fetchone()
            if not row:
                self.logger.error(f"提交记录不存在: {submission_id}")
                return False
            
            submission = Submission.from_db_row(dict(row))
            
            # 设置AI批改结果
            submission.set_ai_grading_result(score, feedback, confidence, criteria_scores, suggestions)
            
            if task_id:
                submission.task_id = task_id
            
            try:
                # 更新数据库
                cursor.execute('''
                    UPDATE submissions 
                    SET ai_result = ?, score = ?, status = ?, task_id = ?,
                        grading_details = ?, ai_confidence = ?, manual_review_required = ?, graded_at = ?
                    WHERE id = ?
                ''', (
                    submission.ai_result,
                    submission.score,
                    submission.status.value,
                    submission.task_id,
                    json.dumps(submission.grading_details.to_dict(), ensure_ascii=False) if submission.grading_details else None,
                    submission.ai_confidence,
                    submission.manual_review_required,
                    submission.graded_at.isoformat() if submission.graded_at else None,
                    submission_id
                ))
                
                conn.commit()
                
                self.logger.info(f"AI批改结果更新成功: {submission_id}, 分数: {score}")
                
                # 通知学生批改完成
                self._notify_grading_completed(submission.assignment_id, submission.student_username)
                
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"更新AI批改结果数据库操作失败: {e}")
                return False
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"更新AI批改结果失败: {e}")
            return False
    
    def get_submission_statistics(self, assignment_id: Optional[int] = None,
                                class_id: Optional[int] = None,
                                student_username: Optional[str] = None) -> Dict[str, Any]:
        """获取提交统计数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT 
                    COUNT(*) as total_submissions,
                    COUNT(CASE WHEN s.status = 'submitted' THEN 1 END) as pending_submissions,
                    COUNT(CASE WHEN s.status = 'ai_graded' THEN 1 END) as ai_graded_submissions,
                    COUNT(CASE WHEN s.status = 'teacher_reviewed' THEN 1 END) as teacher_reviewed_submissions,
                    COUNT(CASE WHEN s.status = 'returned' THEN 1 END) as returned_submissions,
                    COUNT(CASE WHEN s.status = 'failed' THEN 1 END) as failed_submissions,
                    COUNT(CASE WHEN s.manual_review_required = 1 THEN 1 END) as review_required_submissions,
                    AVG(s.score) as average_score,
                    MIN(s.score) as min_score,
                    MAX(s.score) as max_score,
                    AVG(s.ai_confidence) as average_confidence
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                WHERE 1=1
            '''
            
            params = []
            
            if assignment_id:
                base_query += ' AND s.assignment_id = ?'
                params.append(assignment_id)
            
            if class_id:
                base_query += ' AND a.class_id = ?'
                params.append(class_id)
            
            if student_username:
                base_query += ' AND s.student_username = ?'
                params.append(student_username)
            
            cursor.execute(base_query, params)
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'total_submissions': row['total_submissions'] or 0,
                    'pending_submissions': row['pending_submissions'] or 0,
                    'ai_graded_submissions': row['ai_graded_submissions'] or 0,
                    'teacher_reviewed_submissions': row['teacher_reviewed_submissions'] or 0,
                    'returned_submissions': row['returned_submissions'] or 0,
                    'failed_submissions': row['failed_submissions'] or 0,
                    'review_required_submissions': row['review_required_submissions'] or 0,
                    'average_score': round(row['average_score'], 2) if row['average_score'] else None,
                    'min_score': row['min_score'],
                    'max_score': row['max_score'],
                    'average_confidence': round(row['average_confidence'], 3) if row['average_confidence'] else None,
                    'grading_completion_rate': round((row['ai_graded_submissions'] + row['teacher_reviewed_submissions'] + row['returned_submissions']) / row['total_submissions'] * 100, 2) if row['total_submissions'] > 0 else 0
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"获取提交统计失败: {e}")
            return {}
    
    def _notify_submission(self, assignment_id: int, student_username: str, 
                          assignment_title: str, is_late: bool):
        """通知作业提交"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取教师用户名
            cursor.execute('''
                SELECT c.teacher_username FROM classes c
                JOIN assignments a ON c.id = a.class_id
                WHERE a.id = ?
            ''', (assignment_id,))
            
            teacher_row = cursor.fetchone()
            if teacher_row:
                teacher_username = teacher_row['teacher_username']
                
                # 通知教师
                status_text = "（迟交）" if is_late else ""
                cursor.execute('''
                    INSERT INTO notifications (recipient_username, title, content, type)
                    VALUES (?, ?, ?, ?)
                ''', (
                    teacher_username,
                    "学生作业提交",
                    f"学生 {student_username} 提交了作业：{assignment_title}{status_text}",
                    "warning" if is_late else "info"
                ))
                
                # 通知学生
                cursor.execute('''
                    INSERT INTO notifications (recipient_username, title, content, type)
                    VALUES (?, ?, ?, ?)
                ''', (
                    student_username,
                    "作业提交成功",
                    f"您已成功提交作业：{assignment_title}{status_text}",
                    "warning" if is_late else "success"
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"发送提交通知失败: {e}")
    
    def _notify_grading_completed(self, assignment_id: int, student_username: str):
        """通知批改完成"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取作业标题
            cursor.execute('SELECT title FROM assignments WHERE id = ?', (assignment_id,))
            assignment_row = cursor.fetchone()
            
            if assignment_row:
                assignment_title = assignment_row['title']
                
                cursor.execute('''
                    INSERT INTO notifications (recipient_username, title, content, type)
                    VALUES (?, ?, ?, ?)
                ''', (
                    student_username,
                    "作业批改完成",
                    f"您的作业 '{assignment_title}' 已完成批改，请查看结果",
                    "success"
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"发送批改完成通知失败: {e}")
    
    def _notify_feedback_updated(self, assignment_id: int, student_username: str):
        """通知反馈已更新"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取作业标题
            cursor.execute('SELECT title FROM assignments WHERE id = ?', (assignment_id,))
            assignment_row = cursor.fetchone()
            
            if assignment_row:
                assignment_title = assignment_row['title']
                
                cursor.execute('''
                    INSERT INTO notifications (recipient_username, title, content, type)
                    VALUES (?, ?, ?, ?)
                ''', (
                    student_username,
                    "作业反馈已更新",
                    f"教师已更新您的作业 '{assignment_title}' 的反馈，请查看",
                    "info"
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"发送反馈更新通知失败: {e}")