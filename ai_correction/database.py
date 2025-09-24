#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级系统数据库模块
提供用户管理、班级管理、作业管理、提交管理等功能
"""

import sqlite3
import json
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 数据库路径
DB_PATH = Path("class_system.db")

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使查询结果可以像字典一样访问
    return conn

def init_database():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 用户表 - 扩展原有用户系统
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
                real_name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # 班级表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                teacher_username TEXT NOT NULL,
                invite_code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (teacher_username) REFERENCES users (username)
            )
        ''')
        
        # 班级成员表（学生加入班级的关联表）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS class_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                student_username TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (class_id) REFERENCES classes (id),
                FOREIGN KEY (student_username) REFERENCES users (username),
                UNIQUE(class_id, student_username)
            )
        ''')
        
        # 作业表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                question_files TEXT,  -- JSON格式存储文件路径列表
                marking_files TEXT,   -- JSON格式存储批改标准文件路径列表
                deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        ''')
        
        # 作业提交表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                student_username TEXT NOT NULL,
                answer_files TEXT,    -- JSON格式存储学生答案文件路径列表
                ai_result TEXT,       -- AI批改原始结果
                teacher_feedback TEXT, -- 老师修改后的反馈
                status TEXT DEFAULT 'submitted' CHECK (status IN ('submitted', 'ai_graded', 'teacher_reviewed', 'returned')),
                score REAL,           -- 最终得分
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graded_at TIMESTAMP,
                returned_at TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (student_username) REFERENCES users (username),
                UNIQUE(assignment_id, student_username)
            )
        ''')
        
        # 通知表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_username TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'info' CHECK (type IN ('info', 'success', 'warning', 'error')),
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipient_username) REFERENCES users (username)
            )
        ''')
        
        conn.commit()
        print("数据库初始化成功")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        conn.rollback()
    finally:
        conn.close()

# ===================== 用户管理 =====================

def register_user(username: str, password: str, role: str, real_name: str = "", email: str = "") -> bool:
    """注册用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查用户名是否已存在
        cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return False
        
        # 密码哈希
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, role, real_name, email))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"注册失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """验证用户登录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            SELECT username, role, real_name, email, created_at, last_login
            FROM users 
            WHERE username = ? AND password_hash = ? AND is_active = 1
        ''', (username, password_hash))
        
        user = cursor.fetchone()
        if user:
            # 更新最后登录时间
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (username,))
            conn.commit()
            return dict(user)
        
        return None
        
    except Exception as e:
        print(f"登录验证失败: {e}")
        return None
    finally:
        conn.close()

def get_user_info(username: str) -> Optional[Dict]:
    """获取用户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT username, role, real_name, email, created_at, last_login
            FROM users 
            WHERE username = ? AND is_active = 1
        ''', (username,))
        
        user = cursor.fetchone()
        return dict(user) if user else None
        
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return None
    finally:
        conn.close()

# ===================== 班级管理 =====================

def generate_invite_code() -> str:
    """生成班级邀请码"""
    return secrets.token_hex(4).upper()  # 8位大写邀请码

def create_class(teacher_username: str, class_name: str, description: str = "") -> Optional[str]:
    """创建班级"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        invite_code = generate_invite_code()
        
        # 确保邀请码唯一
        while True:
            cursor.execute('SELECT id FROM classes WHERE invite_code = ?', (invite_code,))
            if not cursor.fetchone():
                break
            invite_code = generate_invite_code()
        
        cursor.execute('''
            INSERT INTO classes (name, description, teacher_username, invite_code)
            VALUES (?, ?, ?, ?)
        ''', (class_name, description, teacher_username, invite_code))
        
        conn.commit()
        
        # 添加成功通知
        add_notification(teacher_username, "班级创建成功", 
                        f"班级 '{class_name}' 创建成功！邀请码：{invite_code}", "success")
        
        return invite_code
        
    except Exception as e:
        print(f"创建班级失败: {e}")
        return None
    finally:
        conn.close()

def join_class(student_username: str, invite_code: str) -> bool:
    """学生加入班级"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查找班级
        cursor.execute('''
            SELECT id, name, teacher_username 
            FROM classes 
            WHERE invite_code = ? AND is_active = 1
        ''', (invite_code,))
        
        class_info = cursor.fetchone()
        if not class_info:
            return False
        
        # 检查是否已经加入
        cursor.execute('''
            SELECT id FROM class_members 
            WHERE class_id = ? AND student_username = ? AND is_active = 1
        ''', (class_info['id'], student_username))
        
        if cursor.fetchone():
            return False  # 已经加入过
        
        # 加入班级
        cursor.execute('''
            INSERT INTO class_members (class_id, student_username)
            VALUES (?, ?)
        ''', (class_info['id'], student_username))
        
        conn.commit()
        
        # 添加通知
        add_notification(student_username, "成功加入班级", 
                        f"您已成功加入班级 '{class_info['name']}'", "success")
        add_notification(class_info['teacher_username'], "新学生加入", 
                        f"学生 {student_username} 加入了班级 '{class_info['name']}'", "info")
        
        return True
        
    except Exception as e:
        print(f"加入班级失败: {e}")
        return False
    finally:
        conn.close()

def get_teacher_classes(teacher_username: str) -> List[Dict]:
    """获取老师的班级列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.invite_code, c.created_at,
                   COUNT(cm.student_username) as student_count
            FROM classes c
            LEFT JOIN class_members cm ON c.id = cm.class_id AND cm.is_active = 1
            WHERE c.teacher_username = ? AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.invite_code, c.created_at
            ORDER BY c.created_at DESC
        ''', (teacher_username,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"获取老师班级失败: {e}")
        return []
    finally:
        conn.close()

def get_student_classes(student_username: str) -> List[Dict]:
    """获取学生的班级列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.teacher_username,
                   u.real_name as teacher_name, cm.joined_at,
                   COUNT(cm2.student_username) as student_count
            FROM class_members cm
            JOIN classes c ON cm.class_id = c.id
            LEFT JOIN users u ON c.teacher_username = u.username
            LEFT JOIN class_members cm2 ON c.id = cm2.class_id AND cm2.is_active = 1
            WHERE cm.student_username = ? AND cm.is_active = 1 AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.teacher_username, u.real_name, cm.joined_at
            ORDER BY cm.joined_at DESC
        ''', (student_username,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"获取学生班级失败: {e}")
        return []
    finally:
        conn.close()

def get_class_students(class_id: int) -> List[Dict]:
    """获取班级的学生列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT u.username, u.real_name, u.email, cm.joined_at
            FROM class_members cm
            JOIN users u ON cm.student_username = u.username
            WHERE cm.class_id = ? AND cm.is_active = 1 AND u.is_active = 1
            ORDER BY cm.joined_at ASC
        ''', (class_id,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"获取班级学生失败: {e}")
        return []
    finally:
        conn.close()

# ===================== 作业管理 =====================

def create_assignment(class_id: int, title: str, description: str = "", 
                     question_files: List[str] = None, marking_files: List[str] = None,
                     deadline: Optional[datetime] = None) -> Optional[int]:
    """创建作业"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO assignments (class_id, title, description, question_files, marking_files, deadline)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            class_id, 
            title, 
            description, 
            json.dumps(question_files or []), 
            json.dumps(marking_files or []),
            deadline
        ))
        
        assignment_id = cursor.lastrowid
        conn.commit()
        
        # 获取班级信息用于通知
        cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
        class_info = cursor.fetchone()
        if class_info:
            # 通知班级所有学生
            students = get_class_students(class_id)
            for student in students:
                add_notification(
                    student['username'], 
                    "新作业发布", 
                    f"班级 '{class_info['name']}' 发布了新作业：{title}", 
                    "info"
                )
        
        return assignment_id
        
    except Exception as e:
        print(f"创建作业失败: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_class_assignments(class_id: int) -> List[Dict]:
    """获取班级的作业列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.*, 
                   COUNT(s.id) as submission_count,
                   COUNT(CASE WHEN s.status = 'graded' THEN 1 END) as graded_count
            FROM assignments a
            LEFT JOIN submissions s ON a.id = s.assignment_id
            WHERE a.class_id = ? AND a.is_active = 1
            GROUP BY a.id, a.title, a.description, a.question_files, a.marking_files, 
                     a.deadline, a.created_at
            ORDER BY a.created_at DESC
        ''', (class_id,))
        
        assignments = []
        for row in cursor.fetchall():
            assignment = dict(row)
            assignment['question_files'] = json.loads(assignment['question_files'] or '[]')
            assignment['marking_files'] = json.loads(assignment['marking_files'] or '[]')
            assignments.append(assignment)
        
        return assignments
        
    except Exception as e:
        print(f"获取班级作业失败: {e}")
        return []
    finally:
        conn.close()

def get_assignment_by_id(assignment_id: int) -> Optional[Dict]:
    """根据ID获取作业详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.*, c.name as class_name, c.teacher_username
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.id = ? AND a.is_active = 1
        ''', (assignment_id,))
        
        row = cursor.fetchone()
        if row:
            assignment = dict(row)
            assignment['question_files'] = json.loads(assignment['question_files'] or '[]')
            assignment['marking_files'] = json.loads(assignment['marking_files'] or '[]')
            return assignment
        
        return None
        
    except Exception as e:
        print(f"获取作业详情失败: {e}")
        return None
    finally:
        conn.close()

def get_student_submissions_in_class(student_username: str, class_id: int) -> List[Dict]:
    """获取学生在班级中的所有提交记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT s.*, a.title as assignment_title, a.created_at as assignment_created
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.student_username = ? AND a.class_id = ?
            ORDER BY s.submitted_at DESC
        ''', (student_username, class_id))
        
        submissions = []
        for row in cursor.fetchall():
            submission = dict(row)
            submission['answer_files'] = json.loads(submission['answer_files'] or '[]')
            # 为了向后兼容，添加files字段映射
            submission['files'] = submission['answer_files']
            submissions.append(submission)
        
        return submissions
        
    except Exception as e:
        print(f"获取学生提交记录失败: {e}")
        return []
    finally:
        conn.close()

# ===================== 提交管理 =====================

def submit_assignment(assignment_id: int, student_username: str, answer_files: List[str]) -> bool:
    """提交作业"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO submissions (assignment_id, student_username, answer_files, submitted_at)
            VALUES (?, ?, ?, ?)
        ''', (assignment_id, student_username, json.dumps(answer_files), datetime.now().isoformat()))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"提交作业失败: {e}")
        return False
    finally:
        conn.close()

def save_grading_result(assignment_id: int, student_username: str, grading_result: str) -> bool:
    """保存批改结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 更新提交记录，添加批改结果
        cursor.execute('''
            UPDATE submissions 
            SET ai_result = ?, graded_at = ?, status = 'graded'
            WHERE assignment_id = ? AND student_username = ?
        ''', (grading_result, datetime.now().isoformat(), assignment_id, student_username))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"保存批改结果失败: {e}")
        return False
    finally:
        conn.close()

def get_grading_result(assignment_id: int, student_username: str) -> Optional[str]:
    """获取批改结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT ai_result FROM submissions 
            WHERE assignment_id = ? AND student_username = ?
        ''', (assignment_id, student_username))
        
        result = cursor.fetchone()
        return result['ai_result'] if result else None
        
    except Exception as e:
        print(f"获取批改结果失败: {e}")
        return None
    finally:
        conn.close()

def get_assignment_submissions(assignment_id: int) -> List[Dict]:
    """获取作业的所有提交"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT s.*, u.real_name
            FROM submissions s
            JOIN users u ON s.student_username = u.username
            WHERE s.assignment_id = ?
            ORDER BY s.submitted_at DESC
        ''', (assignment_id,))
        
        submissions = []
        for row in cursor.fetchall():
            submission = dict(row)
            submission['answer_files'] = json.loads(submission['answer_files'] or '[]')
            # 为了向后兼容，添加files字段映射
            submission['files'] = submission['answer_files']
            submissions.append(submission)
        
        return submissions
        
    except Exception as e:
        print(f"获取作业提交失败: {e}")
        return []
    finally:
        conn.close()

# ===================== 通知管理 =====================

def add_notification(username: str, title: str, content: str, type: str = "info") -> bool:
    """添加通知"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO notifications (recipient_username, title, content, type)
            VALUES (?, ?, ?, ?)
        ''', (username, title, content, type))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"添加通知失败: {e}")
        return False
    finally:
        conn.close()

def get_user_notifications(username: str, limit: int = 50) -> List[Dict]:
    """获取用户通知"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM notifications
            WHERE recipient_username = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (username, limit))
        
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"获取通知失败: {e}")
        return []
    finally:
        conn.close()

# ===================== 兼容性函数 =====================

def create_user(username: str, password: str, role: str, real_name: str = "", email: str = "") -> bool:
    """创建用户（兼容性函数）"""
    return register_user(username, password, role, real_name, email)

def verify_user(username: str, password: str) -> Optional[Dict]:
    """验证用户（兼容性函数）"""
    return authenticate_user(username, password)

def join_class_by_code(student_username: str, invite_code: str) -> bool:
    """通过邀请码加入班级（兼容性函数）"""
    return join_class(student_username, invite_code)

def get_user_classes(username: str, user_role: str = None) -> List[Dict]:
    """获取用户班级（兼容性函数）"""
    user_info = get_user_info(username)
    if not user_info:
        return []
    
    # 使用传入的角色或从用户信息中获取角色
    role = user_role if user_role else user_info['role']
    
    if role == 'teacher':
        return get_teacher_classes(username)
    else:
        return get_student_classes(username)

# ===================== 数据分析函数 =====================

def get_assignment_center_data(username: str, user_role: str = None, class_filter: str = None) -> Dict:
    """获取作业中心数据"""
    user_info = get_user_info(username)
    if not user_info:
        return {}
    
    # 使用传入的角色或从用户信息中获取角色
    role = user_role if user_role else user_info['role']
    
    if role == 'teacher':
        classes = get_teacher_classes(username)
        total_assignments = 0
        total_submissions = 0
        
        for class_info in classes:
            assignments = get_class_assignments(class_info['id'])
            total_assignments += len(assignments)
            for assignment in assignments:
                submissions = get_assignment_submissions(assignment['id'])
                total_submissions += len(submissions)
        
        return {
            'total_classes': len(classes),
            'total_assignments': total_assignments,
            'total_submissions': total_submissions
        }
    else:
        classes = get_student_classes(username)
        total_assignments = 0
        completed_assignments = 0
        
        for class_info in classes:
            assignments = get_class_assignments(class_info['id'])
            total_assignments += len(assignments)
            submissions = get_student_submissions_in_class(username, class_info['id'])
            completed_assignments += len(submissions)
        
        return {
            'total_classes': len(classes),
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments
        }

def get_user_assignment_summary(username: str, user_role: str = None) -> Dict:
    """获取用户作业摘要"""
    return get_assignment_center_data(username, user_role)

def search_assignments(username: str, keyword: str = "") -> List[Dict]:
    """搜索作业"""
    user_info = get_user_info(username)
    if not user_info:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if user_info['role'] == 'teacher':
            cursor.execute('''
                SELECT a.*, c.name as class_name
                FROM assignments a
                JOIN classes c ON a.class_id = c.id
                WHERE c.teacher_username = ? AND a.is_active = 1
                AND (a.title LIKE ? OR a.description LIKE ?)
                ORDER BY a.created_at DESC
            ''', (username, f'%{keyword}%', f'%{keyword}%'))
        else:
            cursor.execute('''
                SELECT a.*, c.name as class_name
                FROM assignments a
                JOIN classes c ON a.class_id = c.id
                JOIN class_members cm ON c.id = cm.class_id
                WHERE cm.student_username = ? AND a.is_active = 1 AND cm.is_active = 1
                AND (a.title LIKE ? OR a.description LIKE ?)
                ORDER BY a.created_at DESC
            ''', (username, f'%{keyword}%', f'%{keyword}%'))
        
        assignments = []
        for row in cursor.fetchall():
            assignment = dict(row)
            assignment['question_files'] = json.loads(assignment['question_files'] or '[]')
            assignment['marking_files'] = json.loads(assignment['marking_files'] or '[]')
            assignments.append(assignment)
        
        return assignments
        
    except Exception as e:
        print(f"搜索作业失败: {e}")
        return []
    finally:
        conn.close()

def delete_class(class_id: int, teacher_username: str) -> bool:
    """删除班级（仅班级创建者可删除）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证是否为班级创建者
        cursor.execute('''
            SELECT id, name FROM classes 
            WHERE id = ? AND teacher_username = ? AND is_active = 1
        ''', (class_id, teacher_username))
        
        class_info = cursor.fetchone()
        if not class_info:
            return False
        
        class_name = class_info['name']
        
        # 软删除班级（设置is_active为0）
        cursor.execute('''
            UPDATE classes SET is_active = 0 
            WHERE id = ? AND teacher_username = ?
        ''', (class_id, teacher_username))
        
        # 移除所有班级成员
        cursor.execute('''
            UPDATE class_members SET is_active = 0 
            WHERE class_id = ?
        ''', (class_id,))
        
        # 软删除班级相关的作业
        cursor.execute('''
            UPDATE assignments SET is_active = 0 
            WHERE class_id = ?
        ''', (class_id,))
        
        conn.commit()
        
        # 通知班级成员
        cursor.execute('''
            SELECT DISTINCT student_username FROM class_members 
            WHERE class_id = ?
        ''', (class_id,))
        
        students = cursor.fetchall()
        for student in students:
            add_notification(
                student['student_username'],
                "班级已解散",
                f"班级 '{class_name}' 已被解散",
                "warning"
            )
        
        # 通知创建者
        add_notification(
            teacher_username,
            "班级删除成功",
            f"班级 '{class_name}' 已成功删除",
            "success"
        )
        
        return True
        
    except Exception as e:
        print(f"删除班级失败: {e}")
        return False
    finally:
        conn.close()

def leave_class(class_id: int, student_username: str) -> bool:
    """学生退出班级"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取班级信息
        cursor.execute('''
            SELECT c.name, c.teacher_username 
            FROM classes c
            JOIN class_members cm ON c.id = cm.class_id
            WHERE c.id = ? AND cm.student_username = ? AND cm.is_active = 1 AND c.is_active = 1
        ''', (class_id, student_username))
        
        class_info = cursor.fetchone()
        if not class_info:
            return False
        
        class_name = class_info['name']
        teacher_username = class_info['teacher_username']
        
        # 移除班级成员关系
        cursor.execute('''
            UPDATE class_members SET is_active = 0 
            WHERE class_id = ? AND student_username = ?
        ''', (class_id, student_username))
        
        conn.commit()
        
        # 通知学生
        add_notification(
            student_username,
            "已退出班级",
            f"您已成功退出班级 '{class_name}'",
            "info"
        )
        
        # 通知教师
        add_notification(
            teacher_username,
            "学生退出班级",
            f"学生 {student_username} 已退出班级 '{class_name}'",
            "info"
        )
        
        return True
        
    except Exception as e:
        print(f"退出班级失败: {e}")
        return False
    finally:
        conn.close()

def get_assignment_status(assignment_id: int, username: str) -> str:
    """获取作业状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT status FROM submissions
            WHERE assignment_id = ? AND student_username = ?
        ''', (assignment_id, username))
        
        result = cursor.fetchone()
        return result['status'] if result else 'not_submitted'
        
    except Exception as e:
        print(f"获取作业状态失败: {e}")
        return 'unknown'
    finally:
        conn.close()

def get_user_submission_status(username: str) -> Dict:
    """获取用户提交状态统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM submissions
            WHERE student_username = ?
            GROUP BY status
        ''', (username,))
        
        status_counts = {}
        for row in cursor.fetchall():
            status_counts[row['status']] = row['count']
        
        return status_counts
        
    except Exception as e:
        print(f"获取提交状态失败: {e}")
        return {}
    finally:
        conn.close()

def get_assignment_analytics_data(assignment_id: int) -> Dict:
    """获取作业分析数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                COUNT(*) as total_submissions,
                AVG(score) as avg_score,
                MIN(score) as min_score,
                MAX(score) as max_score
            FROM submissions
            WHERE assignment_id = ? AND score IS NOT NULL
        ''', (assignment_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else {}
        
    except Exception as e:
        print(f"获取作业分析数据失败: {e}")
        return {}
    finally:
        conn.close()

def update_last_login(username: str) -> bool:
    """更新用户最后登录时间"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP 
            WHERE username = ?
        ''', (username,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"更新登录时间失败: {e}")
        return False
    finally:
        conn.close()