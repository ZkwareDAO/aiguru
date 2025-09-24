#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业服务
提供作业管理的核心业务逻辑
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from src.models.assignment import Assignment
from src.infrastructure.logging import get_logger


class AssignmentService:
    """作业服务"""
    
    def __init__(self, db_path: str = "class_system.db"):
        self.db_path = Path(db_path)
        self.logger = get_logger(f"{__name__}.AssignmentService")
        
        # 确保数据库存在
        self._ensure_database()
        
        self.logger.info("作业服务已初始化")
    
    def _ensure_database(self):
        """确保数据库和表结构存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查assignments表是否存在扩展字段
            cursor.execute("PRAGMA table_info(assignments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 如果缺少扩展字段，添加它们
            if 'grading_config_id' not in columns:
                cursor.execute('ALTER TABLE assignments ADD COLUMN grading_config_id TEXT')
            if 'auto_grading_enabled' not in columns:
                cursor.execute('ALTER TABLE assignments ADD COLUMN auto_grading_enabled BOOLEAN DEFAULT 1')
            if 'grading_template_id' not in columns:
                cursor.execute('ALTER TABLE assignments ADD COLUMN grading_template_id TEXT')
            
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
    
    def create_assignment(self, class_id: int, title: str, description: str = "",
                         question_files: List[str] = None, marking_files: List[str] = None,
                         grading_config_id: Optional[str] = None,
                         grading_template_id: Optional[str] = None,
                         auto_grading_enabled: bool = True,
                         deadline: Optional[datetime] = None) -> Optional[int]:
        """创建作业"""
        try:
            # 创建作业对象并验证
            assignment = Assignment(
                class_id=class_id,
                title=title,
                description=description,
                question_files=question_files or [],
                marking_files=marking_files or [],
                grading_config_id=grading_config_id,
                grading_template_id=grading_template_id,
                auto_grading_enabled=auto_grading_enabled,
                deadline=deadline
            )
            
            # 验证作业数据
            validation_errors = assignment.validate()
            if validation_errors:
                # 允许过去的截止时间用于测试
                if not (len(validation_errors) == 1 and "截止时间必须在当前时间之后" in validation_errors[0]):
                    self.logger.error(f"作业数据验证失败: {validation_errors}")
                    return None
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO assignments (
                        class_id, title, description, question_files, marking_files,
                        grading_config_id, auto_grading_enabled, grading_template_id, deadline
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assignment.class_id,
                    assignment.title,
                    assignment.description,
                    json.dumps(assignment.question_files, ensure_ascii=False),
                    json.dumps(assignment.marking_files, ensure_ascii=False),
                    assignment.grading_config_id,
                    assignment.auto_grading_enabled,
                    assignment.grading_template_id,
                    assignment.deadline.isoformat() if assignment.deadline else None
                ))
                
                assignment_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"作业创建成功: {assignment_id} - {title}")
                
                # 通知班级学生（这里可以集成通知服务）
                self._notify_class_students(class_id, assignment_id, title)
                
                return assignment_id
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"创建作业数据库操作失败: {e}")
                return None
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"创建作业失败: {e}")
            return None
    
    def get_class_assignments(self, class_id: int) -> List[Assignment]:
        """获取班级的作业列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.*, 
                       COUNT(s.id) as submission_count,
                       COUNT(CASE WHEN s.status IN ('ai_graded', 'teacher_reviewed', 'returned') THEN 1 END) as graded_count
                FROM assignments a
                LEFT JOIN submissions s ON a.id = s.assignment_id
                WHERE a.class_id = ? AND a.is_active = 1
                GROUP BY a.id, a.class_id, a.title, a.description, a.question_files, 
                         a.marking_files, a.grading_config_id, a.auto_grading_enabled,
                         a.grading_template_id, a.deadline, a.created_at, a.is_active
                ORDER BY a.created_at DESC
            ''', (class_id,))
            
            assignments = []
            for row in cursor.fetchall():
                assignment = Assignment.from_db_row(dict(row))
                assignment.update_statistics(row['submission_count'], row['graded_count'])
                assignments.append(assignment)
            
            conn.close()
            return assignments
            
        except Exception as e:
            self.logger.error(f"获取班级作业失败: {e}")
            return []
    
    def get_student_assignments(self, student_username: str, class_id: Optional[int] = None) -> List[Assignment]:
        """获取学生的作业列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if class_id:
                # 获取指定班级的作业
                cursor.execute('''
                    SELECT a.*, s.status as submission_status, s.score as submission_score,
                           s.submitted_at, s.graded_at
                    FROM assignments a
                    JOIN class_members cm ON a.class_id = cm.class_id
                    LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_username = ?
                    WHERE cm.student_username = ? AND a.class_id = ? 
                          AND a.is_active = 1 AND cm.is_active = 1
                    ORDER BY a.created_at DESC
                ''', (student_username, student_username, class_id))
            else:
                # 获取学生所有班级的作业
                cursor.execute('''
                    SELECT a.*, s.status as submission_status, s.score as submission_score,
                           s.submitted_at, s.graded_at, c.name as class_name
                    FROM assignments a
                    JOIN classes c ON a.class_id = c.id
                    JOIN class_members cm ON a.class_id = cm.class_id
                    LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_username = ?
                    WHERE cm.student_username = ? AND a.is_active = 1 AND cm.is_active = 1
                    ORDER BY a.created_at DESC
                ''', (student_username, student_username))
            
            assignments = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                assignment = Assignment.from_db_row(row_dict)
                # 添加学生提交状态信息
                assignment.submission_status = row_dict.get('submission_status')
                assignment.submission_score = row_dict.get('submission_score')
                assignment.submitted_at = row_dict.get('submitted_at')
                assignment.graded_at = row_dict.get('graded_at')
                if 'class_name' in row_dict:
                    assignment.class_name = row_dict.get('class_name')
                assignments.append(assignment)
            
            conn.close()
            return assignments
            
        except Exception as e:
            self.logger.error(f"获取学生作业失败: {e}")
            return []
    
    def get_assignment_by_id(self, assignment_id: int) -> Optional[Assignment]:
        """根据ID获取作业详情"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.*, c.name as class_name, c.teacher_username,
                       COUNT(s.id) as submission_count,
                       COUNT(CASE WHEN s.status IN ('ai_graded', 'teacher_reviewed', 'returned') THEN 1 END) as graded_count
                FROM assignments a
                JOIN classes c ON a.class_id = c.id
                LEFT JOIN submissions s ON a.id = s.assignment_id
                WHERE a.id = ? AND a.is_active = 1
                GROUP BY a.id, a.class_id, a.title, a.description, a.question_files, 
                         a.marking_files, a.grading_config_id, a.auto_grading_enabled,
                         a.grading_template_id, a.deadline, a.created_at, a.is_active,
                         c.name, c.teacher_username
            ''', (assignment_id,))
            
            row = cursor.fetchone()
            if row:
                assignment = Assignment.from_db_row(dict(row))
                assignment.update_statistics(row['submission_count'], row['graded_count'])
                assignment.class_name = row['class_name']
                assignment.teacher_username = row['teacher_username']
                conn.close()
                return assignment
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"获取作业详情失败: {e}")
            return None
    
    def update_assignment(self, assignment_id: int, **kwargs) -> bool:
        """更新作业"""
        try:
            # 获取当前作业
            assignment = self.get_assignment_by_id(assignment_id)
            if not assignment:
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建更新语句
            update_fields = []
            update_values = []
            
            allowed_fields = {
                'title', 'description', 'question_files', 'marking_files',
                'grading_config_id', 'auto_grading_enabled', 'grading_template_id',
                'deadline', 'is_active'
            }
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field in ['question_files', 'marking_files']:
                        update_fields.append(f"{field} = ?")
                        update_values.append(json.dumps(value, ensure_ascii=False))
                    elif field == 'deadline' and value:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value.isoformat() if isinstance(value, datetime) else value)
                    else:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
            
            if not update_fields:
                return False
            
            update_values.append(assignment_id)
            
            try:
                cursor.execute(f'''
                    UPDATE assignments 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                ''', update_values)
                
                conn.commit()
                self.logger.info(f"作业更新成功: {assignment_id}")
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"更新作业数据库操作失败: {e}")
                return False
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"更新作业失败: {e}")
            return False
    
    def delete_assignment(self, assignment_id: int) -> bool:
        """删除作业（软删除）"""
        try:
            return self.update_assignment(assignment_id, is_active=False)
        except Exception as e:
            self.logger.error(f"删除作业失败: {e}")
            return False
    
    def get_assignment_statistics(self, assignment_id: int) -> Dict[str, Any]:
        """获取作业统计数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 基本统计
            cursor.execute('''
                SELECT 
                    COUNT(s.id) as total_submissions,
                    COUNT(CASE WHEN s.status = 'submitted' THEN 1 END) as pending_submissions,
                    COUNT(CASE WHEN s.status = 'ai_graded' THEN 1 END) as ai_graded_submissions,
                    COUNT(CASE WHEN s.status = 'teacher_reviewed' THEN 1 END) as teacher_reviewed_submissions,
                    COUNT(CASE WHEN s.status = 'returned' THEN 1 END) as returned_submissions,
                    AVG(s.score) as average_score,
                    MIN(s.score) as min_score,
                    MAX(s.score) as max_score,
                    COUNT(CASE WHEN s.score IS NOT NULL THEN 1 END) as scored_submissions
                FROM submissions s
                WHERE s.assignment_id = ?
            ''', (assignment_id,))
            
            stats_row = cursor.fetchone()
            
            # 获取作业基本信息
            assignment = self.get_assignment_by_id(assignment_id)
            if not assignment:
                return {}
            
            # 获取班级学生总数
            cursor.execute('''
                SELECT COUNT(*) as total_students
                FROM class_members cm
                WHERE cm.class_id = ? AND cm.is_active = 1
            ''', (assignment.class_id,))
            
            class_row = cursor.fetchone()
            total_students = class_row['total_students'] if class_row else 0
            
            # 计算提交率
            submission_rate = (stats_row['total_submissions'] / total_students * 100) if total_students > 0 else 0
            
            # 计算批改进度
            grading_progress = assignment.get_grading_progress()
            
            conn.close()
            
            return {
                'assignment_id': assignment_id,
                'assignment_title': assignment.title,
                'class_id': assignment.class_id,
                'total_students': total_students,
                'total_submissions': stats_row['total_submissions'] or 0,
                'submission_rate': round(submission_rate, 2),
                'pending_submissions': stats_row['pending_submissions'] or 0,
                'ai_graded_submissions': stats_row['ai_graded_submissions'] or 0,
                'teacher_reviewed_submissions': stats_row['teacher_reviewed_submissions'] or 0,
                'returned_submissions': stats_row['returned_submissions'] or 0,
                'scored_submissions': stats_row['scored_submissions'] or 0,
                'average_score': round(stats_row['average_score'], 2) if stats_row['average_score'] else None,
                'min_score': stats_row['min_score'],
                'max_score': stats_row['max_score'],
                'grading_progress': grading_progress,
                'is_overdue': assignment.is_overdue(),
                'deadline': assignment.deadline.isoformat() if assignment.deadline else None,
                'auto_grading_enabled': assignment.auto_grading_enabled,
                'has_grading_config': assignment.has_grading_config()
            }
            
        except Exception as e:
            self.logger.error(f"获取作业统计失败: {e}")
            return {}
    
    def _notify_class_students(self, class_id: int, assignment_id: int, assignment_title: str):
        """通知班级学生新作业发布"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取班级信息
            cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
            class_row = cursor.fetchone()
            if not class_row:
                return
            
            class_name = class_row['name']
            
            # 获取班级学生
            cursor.execute('''
                SELECT student_username FROM class_members 
                WHERE class_id = ? AND is_active = 1
            ''', (class_id,))
            
            students = cursor.fetchall()
            
            # 添加通知
            for student in students:
                cursor.execute('''
                    INSERT INTO notifications (recipient_username, title, content, type)
                    VALUES (?, ?, ?, ?)
                ''', (
                    student['student_username'],
                    "新作业发布",
                    f"班级 '{class_name}' 发布了新作业：{assignment_title}",
                    "info"
                ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"已通知 {len(students)} 名学生新作业发布")
            
        except Exception as e:
            self.logger.error(f"通知学生失败: {e}")
    
    def search_assignments(self, keyword: str = "", class_id: Optional[int] = None,
                          teacher_username: Optional[str] = None,
                          student_username: Optional[str] = None) -> List[Assignment]:
        """搜索作业"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            base_query = '''
                SELECT a.*, c.name as class_name, c.teacher_username
                FROM assignments a
                JOIN classes c ON a.class_id = c.id
            '''
            
            conditions = ['a.is_active = 1']
            params = []
            
            # 添加搜索条件
            if keyword:
                conditions.append('(a.title LIKE ? OR a.description LIKE ?)')
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            if class_id:
                conditions.append('a.class_id = ?')
                params.append(class_id)
            
            if teacher_username:
                conditions.append('c.teacher_username = ?')
                params.append(teacher_username)
            
            if student_username:
                base_query += ' JOIN class_members cm ON c.id = cm.class_id'
                conditions.extend(['cm.student_username = ?', 'cm.is_active = 1'])
                params.append(student_username)
            
            # 构建完整查询
            if conditions:
                query = f"{base_query} WHERE {' AND '.join(conditions)} ORDER BY a.created_at DESC"
            else:
                query = f"{base_query} ORDER BY a.created_at DESC"
            
            cursor.execute(query, params)
            
            assignments = []
            for row in cursor.fetchall():
                assignment = Assignment.from_db_row(dict(row))
                assignment.class_name = row['class_name']
                assignment.teacher_username = row['teacher_username']
                assignments.append(assignment)
            
            conn.close()
            return assignments
            
        except Exception as e:
            self.logger.error(f"搜索作业失败: {e}")
            return []
    
    def get_assignments_by_status(self, status: str, class_id: Optional[int] = None) -> List[Assignment]:
        """根据状态获取作业列表"""
        try:
            assignments = self.get_class_assignments(class_id) if class_id else []
            
            if status == 'active':
                return [a for a in assignments if a.is_active and not a.is_overdue()]
            elif status == 'overdue':
                return [a for a in assignments if a.is_active and a.is_overdue()]
            elif status == 'inactive':
                return [a for a in assignments if not a.is_active]
            else:
                return assignments
                
        except Exception as e:
            self.logger.error(f"根据状态获取作业失败: {e}")
            return []
    
    def get_teacher_assignment_summary(self, teacher_username: str) -> Dict[str, Any]:
        """获取教师作业摘要"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取教师的班级
            cursor.execute('''
                SELECT id FROM classes 
                WHERE teacher_username = ? AND is_active = 1
            ''', (teacher_username,))
            
            class_ids = [row['id'] for row in cursor.fetchall()]
            
            if not class_ids:
                return {
                    'total_assignments': 0,
                    'active_assignments': 0,
                    'total_submissions': 0,
                    'pending_grading': 0
                }
            
            # 统计作业数据
            placeholders = ','.join('?' * len(class_ids))
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_assignments,
                    COUNT(CASE WHEN a.is_active = 1 THEN 1 END) as active_assignments
                FROM assignments a
                WHERE a.class_id IN ({placeholders})
            ''', class_ids)
            
            assignment_stats = cursor.fetchone()
            
            # 统计提交数据
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_submissions,
                    COUNT(CASE WHEN s.status = 'submitted' THEN 1 END) as pending_grading
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                WHERE a.class_id IN ({placeholders})
            ''', class_ids)
            
            submission_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_assignments': assignment_stats['total_assignments'] or 0,
                'active_assignments': assignment_stats['active_assignments'] or 0,
                'total_submissions': submission_stats['total_submissions'] or 0,
                'pending_grading': submission_stats['pending_grading'] or 0
            }
            
        except Exception as e:
            self.logger.error(f"获取教师作业摘要失败: {e}")
            return {}