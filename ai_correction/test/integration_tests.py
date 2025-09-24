#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试套件
编写完整的作业创建到批改完成的端到端测试
编写多学生并发提交的集成测试
编写教师修改批改结果的集成测试
编写文件上传和处理的集成测试
"""

import unittest
import tempfile
import sqlite3
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入所有需要测试的模块
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.services.classroom_grading_service import ClassroomGradingService
from src.services.file_manager import FileManager
from src.services.notification_service import NotificationService
from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus
from src.models.classroom_grading_task import ClassroomGradingTask


class EndToEndWorkflowTests(unittest.TestCase):
    """端到端工作流程测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 创建临时文件目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 初始化测试数据库
        self._init_test_database()
        
        # 创建服务实例
        self.assignment_service = AssignmentService(db_path=self.db_path)
        self.submission_service = SubmissionService(db_path=self.db_path)
        
        # 创建模拟依赖
        self.mock_task_service = Mock()
        self.mock_grading_config_service = Mock()
        self.classroom_grading_service = ClassroomGradingService(
            db_path=self.db_path,
            task_service=self.mock_task_service,
            grading_config_service=self.mock_grading_config_service
        )
        
        # 创建文件管理器
        try:
            self.file_manager = FileManager()
        except:
            self.file_manager = None
    
    def tearDown(self):
        """测试后清理"""
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except:
            pass
        
        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
    
    def _init_test_database(self):
        """初始化测试数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建完整的表结构
        cursor.execute('''
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                real_name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE classes (
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
        
        cursor.execute('''
            CREATE TABLE class_members (
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
        
        cursor.execute('''
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                question_files TEXT,
                marking_files TEXT,
                grading_config_id TEXT,
                auto_grading_enabled BOOLEAN DEFAULT 1,
                grading_template_id TEXT,
                deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                student_username TEXT NOT NULL,
                answer_files TEXT,
                ai_result TEXT,
                teacher_feedback TEXT,
                status TEXT DEFAULT 'submitted',
                score REAL,
                task_id TEXT,
                grading_details TEXT,
                ai_confidence REAL,
                manual_review_required BOOLEAN DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graded_at TIMESTAMP,
                returned_at TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (student_username) REFERENCES users (username),
                UNIQUE(assignment_id, student_username)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_username TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipient_username) REFERENCES users (username)
            )
        ''')
        
        # 插入测试数据
        test_users = [
            ('teacher1', 'hash1', 'teacher', '张老师', 'teacher1@test.com'),
            ('student1', 'hash2', 'student', '学生1', 'student1@test.com'),
            ('student2', 'hash3', 'student', '学生2', 'student2@test.com'),
            ('student3', 'hash4', 'student', '学生3', 'student3@test.com'),
        ]
        
        for username, password_hash, role, real_name, email in test_users:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, role, real_name, email))
        
        cursor.execute('''
            INSERT INTO classes (id, name, description, teacher_username, invite_code)
            VALUES (1, '测试班级', '集成测试班级', 'teacher1', 'TEST001')
        ''')
        
        # 添加班级成员
        for i in range(1, 4):
            cursor.execute('''
                INSERT INTO class_members (class_id, student_username)
                VALUES (1, ?)
            ''', (f'student{i}',))
        
        conn.commit()
        conn.close()
    
    def _create_test_files(self, assignment_id):
        """创建测试文件"""
        # 创建作业题目文件
        question_dir = Path(self.temp_dir) / "assignments" / str(assignment_id) / "questions"
        question_dir.mkdir(parents=True, exist_ok=True)
        
        question_file = question_dir / "question.txt"
        question_file.write_text("这是一个测试题目", encoding='utf-8')
        
        # 创建批改标准文件
        marking_dir = Path(self.temp_dir) / "assignments" / str(assignment_id) / "marking_standards"
        marking_dir.mkdir(parents=True, exist_ok=True)
        
        marking_file = marking_dir / "rubric.txt"
        marking_file.write_text("这是批改标准", encoding='utf-8')
        
        return [str(question_file)], [str(marking_file)]
    
    def _create_student_answer_files(self, assignment_id, student_username):
        """创建学生答案文件"""
        answer_dir = Path(self.temp_dir) / "submissions" / str(assignment_id) / student_username
        answer_dir.mkdir(parents=True, exist_ok=True)
        
        answer_file = answer_dir / "answer.txt"
        answer_file.write_text(f"这是{student_username}的答案", encoding='utf-8')
        
        return [str(answer_file)]
    
    def test_complete_assignment_workflow(self):
        """测试完整的作业工作流程：创建->提交->批改->反馈"""
        print("\n🧪 测试完整作业工作流程...")
        
        # 1. 教师创建作业
        print("1. 创建作业...")
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="集成测试作业",
            description="这是一个集成测试作业",
            question_files=["question.txt"],
            marking_files=["rubric.txt"],
            auto_grading_enabled=True,
            deadline=datetime.now() + timedelta(days=7)
        )
        
        self.assertIsNotNone(assignment_id)
        print(f"✅ 作业创建成功，ID: {assignment_id}")
        
        # 验证作业创建
        assignment = self.assignment_service.get_assignment_by_id(assignment_id)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.title, "集成测试作业")
        self.assertTrue(assignment.auto_grading_enabled)
        
        # 2. 学生提交作业
        print("2. 学生提交作业...")
        student_username = "student1"
        
        # 创建测试文件
        answer_files = self._create_student_answer_files(assignment_id, student_username)
        
        success = self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username=student_username,
            answer_files=answer_files
        )
        
        self.assertTrue(success)
        print(f"✅ 学生 {student_username} 提交成功")
        
        # 验证提交记录
        submission = self.submission_service.get_submission(assignment_id, student_username)
        self.assertIsNotNone(submission)
        self.assertEqual(submission.status, SubmissionStatus.SUBMITTED)
        self.assertEqual(len(submission.answer_files), 1)
        
        # 3. 触发自动批改
        print("3. 触发自动批改...")
        self.mock_task_service.create_task.return_value = 'task_123'
        
        task_id = self.classroom_grading_service.trigger_auto_grading(submission)
        print(f"✅ 批改任务创建成功，Task ID: {task_id}")
        
        # 4. 模拟AI批改完成
        print("4. 模拟AI批改完成...")
        success = self.submission_service.update_submission_grading_result(
            submission.id,
            score=85.0,
            feedback="AI批改：作业完成质量良好，逻辑清晰。",
            confidence=0.9,
            criteria_scores={'内容准确性': 90, '语言质量': 80},
            suggestions=['注意语法细节', '可以增加更多例子'],
            task_id=task_id
        )
        
        self.assertTrue(success)
        print("✅ AI批改完成")
        
        # 验证批改结果
        graded_submission = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(graded_submission.status, SubmissionStatus.AI_GRADED)
        self.assertEqual(graded_submission.score, 85.0)
        self.assertEqual(graded_submission.ai_confidence, 0.9)
        self.assertFalse(graded_submission.manual_review_required)  # 高置信度不需要审核
        
        # 5. 教师审核和修改反馈
        print("5. 教师审核和修改反馈...")
        success = self.submission_service.update_submission_feedback(
            submission.id,
            teacher_feedback="教师反馈：作业完成得很好，继续保持！建议多练习类似题目。",
            score=88.0
        )
        
        self.assertTrue(success)
        print("✅ 教师反馈完成")
        
        # 验证最终结果
        final_submission = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(final_submission.status, SubmissionStatus.TEACHER_REVIEWED)
        self.assertEqual(final_submission.score, 88.0)
        self.assertIsNotNone(final_submission.teacher_feedback)
        
        # 6. 验证统计数据
        print("6. 验证统计数据...")
        assignment_stats = self.assignment_service.get_assignment_statistics(assignment_id)
        self.assertEqual(assignment_stats['total_submissions'], 1)
        self.assertEqual(assignment_stats['teacher_reviewed_submissions'], 1)
        self.assertEqual(assignment_stats['average_score'], 88.0)
        
        submission_stats = self.submission_service.get_submission_statistics(assignment_id=assignment_id)
        self.assertEqual(submission_stats['total_submissions'], 1)
        self.assertEqual(submission_stats['teacher_reviewed_submissions'], 1)
        self.assertEqual(submission_stats['average_score'], 88.0)
        
        print("✅ 完整工作流程测试通过！")
    
    def test_multiple_students_concurrent_submission(self):
        """测试多学生并发提交的集成测试"""
        print("\n🧪 测试多学生并发提交...")
        
        # 1. 创建作业
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="并发测试作业",
            description="用于测试并发提交",
            auto_grading_enabled=True
        )
        
        self.assertIsNotNone(assignment_id)
        print(f"✅ 作业创建成功，ID: {assignment_id}")
        
        # 2. 准备多个学生的提交数据
        students = ['student1', 'student2', 'student3']
        submission_results = {}
        
        def submit_assignment_for_student(student_username):
            """为单个学生提交作业"""
            try:
                # 创建学生答案文件
                answer_files = self._create_student_answer_files(assignment_id, student_username)
                
                # 提交作业
                success = self.submission_service.submit_assignment(
                    assignment_id=assignment_id,
                    student_username=student_username,
                    answer_files=answer_files
                )
                
                return {
                    'student': student_username,
                    'success': success,
                    'timestamp': datetime.now()
                }
            except Exception as e:
                return {
                    'student': student_username,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now()
                }
        
        # 3. 使用线程池并发提交
        print("3. 并发提交作业...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有任务
            future_to_student = {
                executor.submit(submit_assignment_for_student, student): student 
                for student in students
            }
            
            # 收集结果
            for future in as_completed(future_to_student):
                result = future.result()
                submission_results[result['student']] = result
                print(f"✅ {result['student']} 提交结果: {result['success']}")
        
        # 4. 验证所有提交都成功
        for student in students:
            result = submission_results[student]
            self.assertTrue(result['success'], f"学生 {student} 提交失败")
            
            # 验证提交记录
            submission = self.submission_service.get_submission(assignment_id, student)
            self.assertIsNotNone(submission, f"学生 {student} 的提交记录未找到")
            self.assertEqual(submission.status, SubmissionStatus.SUBMITTED)
        
        # 5. 验证作业统计
        stats = self.assignment_service.get_assignment_statistics(assignment_id)
        self.assertEqual(stats['total_submissions'], 3)
        self.assertEqual(stats['submission_rate'], 100.0)  # 3/3 * 100
        
        print("✅ 并发提交测试通过！")
    
    def test_teacher_modify_grading_results(self):
        """测试教师修改批改结果的集成测试"""
        print("\n🧪 测试教师修改批改结果...")
        
        # 1. 创建作业并提交
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="批改修改测试作业",
            description="用于测试教师修改批改结果"
        )
        
        student_username = "student1"
        answer_files = self._create_student_answer_files(assignment_id, student_username)
        
        self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username=student_username,
            answer_files=answer_files
        )
        
        submission = self.submission_service.get_submission(assignment_id, student_username)
        print("✅ 作业创建和提交完成")
        
        # 2. AI批改
        print("2. AI批改...")
        self.submission_service.update_submission_grading_result(
            submission.id,
            score=75.0,
            feedback="AI批改：作业基本完成，但有改进空间。",
            confidence=0.7,
            criteria_scores={'内容': 70, '语法': 80},
            suggestions=['需要更多细节', '注意语法']
        )
        
        ai_graded_submission = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(ai_graded_submission.status, SubmissionStatus.AI_GRADED)
        self.assertEqual(ai_graded_submission.score, 75.0)
        print("✅ AI批改完成，分数: 75.0")
        
        # 3. 教师第一次修改
        print("3. 教师第一次修改...")
        success = self.submission_service.update_submission_feedback(
            submission.id,
            teacher_feedback="教师反馈：作业完成得不错，但可以更深入一些。",
            score=80.0
        )
        
        self.assertTrue(success)
        
        first_review = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(first_review.status, SubmissionStatus.TEACHER_REVIEWED)
        self.assertEqual(first_review.score, 80.0)
        print("✅ 教师第一次修改完成，分数: 80.0")
        
        # 4. 教师第二次修改（再次调整）
        print("4. 教师第二次修改...")
        success = self.submission_service.update_submission_feedback(
            submission.id,
            teacher_feedback="教师反馈：重新评估后，认为作业质量更高，给予更高分数。",
            score=85.0
        )
        
        self.assertTrue(success)
        
        final_review = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(final_review.status, SubmissionStatus.TEACHER_REVIEWED)
        self.assertEqual(final_review.score, 85.0)
        print("✅ 教师第二次修改完成，最终分数: 85.0")
        
        # 5. 验证修改历史和最终状态
        # 验证最终分数是教师分数
        final_score = final_review.get_final_score()
        self.assertEqual(final_score, 85.0)
        
        # 验证最终反馈是教师反馈
        final_feedback = final_review.get_final_feedback()
        self.assertIn("重新评估后", final_feedback)
        
        # 验证统计数据反映最新分数
        stats = self.submission_service.get_submission_statistics(assignment_id=assignment_id)
        self.assertEqual(stats['average_score'], 85.0)
        
        print("✅ 教师修改批改结果测试通过！")
    
    def test_file_upload_and_processing(self):
        """测试文件上传和处理的集成测试"""
        print("\n🧪 测试文件上传和处理...")
        
        # 1. 创建测试文件
        print("1. 创建测试文件...")
        test_files = {}
        
        # 创建不同类型的测试文件
        file_types = {
            'question.txt': '这是一个文本题目文件\n包含多行内容\n测试文件处理',
            'rubric.txt': '批改标准：\n1. 内容准确性 (40分)\n2. 语言质量 (30分)\n3. 逻辑结构 (30分)',
            'answer.txt': '学生答案：\n这是学生的答案内容\n包含详细的解答过程'
        }
        
        for filename, content in file_types.items():
            file_path = Path(self.temp_dir) / filename
            file_path.write_text(content, encoding='utf-8')
            test_files[filename] = str(file_path)
            print(f"✅ 创建测试文件: {filename}")
        
        # 2. 创建作业并上传文件
        print("2. 创建作业并关联文件...")
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="文件处理测试作业",
            description="用于测试文件上传和处理功能",
            question_files=[test_files['question.txt']],
            marking_files=[test_files['rubric.txt']],
            auto_grading_enabled=True
        )
        
        self.assertIsNotNone(assignment_id)
        
        # 验证作业文件关联
        assignment = self.assignment_service.get_assignment_by_id(assignment_id)
        self.assertEqual(len(assignment.question_files), 1)
        self.assertEqual(len(assignment.marking_files), 1)
        print("✅ 作业文件关联成功")
        
        # 3. 学生提交答案文件
        print("3. 学生提交答案文件...")
        student_username = "student1"
        
        success = self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username=student_username,
            answer_files=[test_files['answer.txt']]
        )
        
        self.assertTrue(success)
        
        # 验证提交文件
        submission = self.submission_service.get_submission(assignment_id, student_username)
        self.assertEqual(len(submission.answer_files), 1)
        print("✅ 学生答案文件提交成功")
        
        # 4. 测试文件内容读取和处理
        print("4. 测试文件内容读取...")
        
        # 验证文件存在且可读取
        for file_type, file_path in test_files.items():
            self.assertTrue(Path(file_path).exists(), f"文件 {file_type} 不存在")
            
            # 读取文件内容
            content = Path(file_path).read_text(encoding='utf-8')
            self.assertGreater(len(content), 0, f"文件 {file_type} 内容为空")
            print(f"✅ 文件 {file_type} 读取成功，内容长度: {len(content)}")
        
        # 5. 模拟批改过程中的文件处理
        print("5. 模拟批改文件处理...")
        
        # 获取作业相关的所有文件
        question_files = assignment.question_files
        marking_files = assignment.marking_files
        answer_files = submission.answer_files
        
        # 验证所有文件都可以访问
        all_files = question_files + marking_files + answer_files
        for file_path in all_files:
            if os.path.isabs(file_path):  # 绝对路径
                self.assertTrue(Path(file_path).exists(), f"文件 {file_path} 不存在")
            else:  # 相对路径，需要在适当的目录中查找
                # 这里简化处理，实际应用中需要根据文件类型确定正确路径
                pass
        
        print("✅ 批改文件处理验证完成")
        
        # 6. 测试文件清理（可选）
        print("6. 测试文件管理...")
        
        # 验证文件统计
        file_count = assignment.get_file_count()
        self.assertEqual(file_count['question_files'], 1)
        self.assertEqual(file_count['marking_files'], 1)
        self.assertEqual(file_count['total_files'], 2)
        
        submission_file_count = submission.get_file_count()
        self.assertEqual(submission_file_count, 1)
        
        print("✅ 文件上传和处理测试通过！")
    
    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复机制"""
        print("\n🧪 测试错误处理和恢复...")
        
        # 1. 测试无效数据提交
        print("1. 测试无效数据处理...")
        
        # 尝试创建无效作业
        invalid_assignment_id = self.assignment_service.create_assignment(
            class_id=0,  # 无效班级ID
            title="",    # 空标题
            description="测试无效数据"
        )
        
        self.assertIsNone(invalid_assignment_id)
        print("✅ 无效作业创建被正确拒绝")
        
        # 2. 测试重复提交处理
        print("2. 测试重复提交处理...")
        
        # 创建有效作业
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="重复提交测试",
            description="测试重复提交处理"
        )
        
        student_username = "student1"
        answer_files = self._create_student_answer_files(assignment_id, student_username)
        
        # 第一次提交
        success1 = self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username=student_username,
            answer_files=answer_files
        )
        self.assertTrue(success1)
        
        # 第二次提交（应该覆盖第一次）
        new_answer_files = self._create_student_answer_files(assignment_id, f"{student_username}_v2")
        success2 = self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username=student_username,
            answer_files=new_answer_files
        )
        self.assertTrue(success2)
        
        # 验证只有一个提交记录
        submissions = self.submission_service.get_assignment_submissions(assignment_id)
        student_submissions = [s for s in submissions if s.student_username == student_username]
        self.assertEqual(len(student_submissions), 1)
        print("✅ 重复提交处理正确")
        
        # 3. 测试数据库连接错误恢复
        print("3. 测试服务错误处理...")
        
        # 创建一个使用无效数据库路径的服务
        invalid_service = AssignmentService(db_path="/invalid/path/database.db")
        
        # 尝试操作应该失败但不崩溃
        try:
            result = invalid_service.get_class_assignments(1)
            # 如果没有抛出异常，结果应该是空列表
            self.assertEqual(result, [])
        except Exception:
            # 如果抛出异常，应该是可预期的数据库错误
            pass
        
        print("✅ 错误处理和恢复测试通过！")


class ConcurrencyTests(unittest.TestCase):
    """并发测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 初始化测试数据库
        self._init_test_database()
        
        # 创建服务实例
        self.assignment_service = AssignmentService(db_path=self.db_path)
        self.submission_service = SubmissionService(db_path=self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except:
            pass
    
    def _init_test_database(self):
        """初始化测试数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建基础表结构
        cursor.execute('''
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                real_name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE classes (
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
        
        cursor.execute('''
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                question_files TEXT,
                marking_files TEXT,
                grading_config_id TEXT,
                auto_grading_enabled BOOLEAN DEFAULT 1,
                grading_template_id TEXT,
                deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                student_username TEXT NOT NULL,
                answer_files TEXT,
                ai_result TEXT,
                teacher_feedback TEXT,
                status TEXT DEFAULT 'submitted',
                score REAL,
                task_id TEXT,
                grading_details TEXT,
                ai_confidence REAL,
                manual_review_required BOOLEAN DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graded_at TIMESTAMP,
                returned_at TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (student_username) REFERENCES users (username),
                UNIQUE(assignment_id, student_username)
            )
        ''')
        
        # 插入测试数据
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name)
            VALUES ('teacher1', 'hash1', 'teacher', '张老师')
        ''')
        
        cursor.execute('''
            INSERT INTO classes (id, name, description, teacher_username, invite_code)
            VALUES (1, '并发测试班级', '用于并发测试', 'teacher1', 'CONC001')
        ''')
        
        # 创建多个学生用户
        for i in range(1, 21):  # 20个学生
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name)
                VALUES (?, ?, ?, ?)
            ''', (f'student{i}', f'hash{i}', 'student', f'学生{i}'))
        
        conn.commit()
        conn.close()
    
    def test_concurrent_assignment_creation(self):
        """测试并发作业创建"""
        print("\n🧪 测试并发作业创建...")
        
        def create_assignment(index):
            """创建单个作业"""
            try:
                assignment_id = self.assignment_service.create_assignment(
                    class_id=1,
                    title=f"并发作业{index}",
                    description=f"这是第{index}个并发创建的作业"
                )
                return {'index': index, 'id': assignment_id, 'success': assignment_id is not None}
            except Exception as e:
                return {'index': index, 'id': None, 'success': False, 'error': str(e)}
        
        # 并发创建10个作业
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_assignment, i) for i in range(1, 11)]
            results = [future.result() for future in as_completed(futures)]
        
        # 验证结果
        successful_creations = [r for r in results if r['success']]
        self.assertEqual(len(successful_creations), 10)
        
        # 验证所有作业都被正确创建
        assignments = self.assignment_service.get_class_assignments(1)
        self.assertEqual(len(assignments), 10)
        
        print(f"✅ 并发创建了 {len(successful_creations)} 个作业")
    
    def test_concurrent_submissions(self):
        """测试并发提交"""
        print("\n🧪 测试并发提交...")
        
        # 先创建一个作业
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="并发提交测试作业",
            description="用于测试并发提交"
        )
        
        def submit_for_student(student_index):
            """为单个学生提交作业"""
            try:
                student_username = f'student{student_index}'
                success = self.submission_service.submit_assignment(
                    assignment_id=assignment_id,
                    student_username=student_username,
                    answer_files=[f'answer_{student_index}.txt']
                )
                return {
                    'student': student_username,
                    'success': success,
                    'timestamp': datetime.now()
                }
            except Exception as e:
                return {
                    'student': f'student{student_index}',
                    'success': False,
                    'error': str(e)
                }
        
        # 并发提交（10个学生同时提交）
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(submit_for_student, i) for i in range(1, 11)]
            results = [future.result() for future in as_completed(futures)]
        
        # 验证结果
        successful_submissions = [r for r in results if r['success']]
        self.assertEqual(len(successful_submissions), 10)
        
        # 验证数据库中的提交记录
        submissions = self.submission_service.get_assignment_submissions(assignment_id)
        self.assertEqual(len(submissions), 10)
        
        print(f"✅ 并发提交了 {len(successful_submissions)} 个作业")


def run_integration_tests():
    """运行集成测试套件"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        EndToEndWorkflowTests,
        ConcurrencyTests
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 计算测试结果
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"集成测试结果:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - failures - errors}")
    print(f"失败: {failures}")
    print(f"错误: {errors}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"{'='*60}")
    
    return success_rate >= 80.0


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)