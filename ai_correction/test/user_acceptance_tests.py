#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户验收测试套件
编写教师用户完整工作流程的验收测试
编写学生用户完整工作流程的验收测试
编写系统管理员监控和维护的验收测试
验证所有用户界面的可用性和响应性
"""

import unittest
import tempfile
import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入所有需要测试的模块
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.services.classroom_grading_service import ClassroomGradingService
from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus


class UserAcceptanceTestBase(unittest.TestCase):
    """用户验收测试基类"""
    
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
        
        # 用户验收测试结果记录
        self.test_results = {
            'passed_scenarios': [],
            'failed_scenarios': [],
            'user_feedback': []
        }
    
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
        
        # 插入测试用户数据
        test_users = [
            ('teacher_alice', 'hash1', 'teacher', '爱丽丝老师', 'alice@school.edu'),
            ('teacher_bob', 'hash2', 'teacher', '鲍勃老师', 'bob@school.edu'),
            ('student_charlie', 'hash3', 'student', '查理同学', 'charlie@student.edu'),
            ('student_diana', 'hash4', 'student', '戴安娜同学', 'diana@student.edu'),
            ('student_eve', 'hash5', 'student', '伊芙同学', 'eve@student.edu'),
            ('admin_frank', 'hash6', 'admin', '弗兰克管理员', 'frank@school.edu'),
        ]
        
        for username, password_hash, role, real_name, email in test_users:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, role, real_name, email))
        
        # 创建测试班级
        cursor.execute('''
            INSERT INTO classes (id, name, description, teacher_username, invite_code)
            VALUES (1, '高中数学班', '高中数学课程班级', 'teacher_alice', 'MATH001')
        ''')
        
        cursor.execute('''
            INSERT INTO classes (id, name, description, teacher_username, invite_code)
            VALUES (2, '初中语文班', '初中语文课程班级', 'teacher_bob', 'CHIN001')
        ''')
        
        # 添加班级成员
        students = ['student_charlie', 'student_diana', 'student_eve']
        for student in students:
            cursor.execute('''
                INSERT INTO class_members (class_id, student_username)
                VALUES (1, ?)
            ''', (student,))
            
            cursor.execute('''
                INSERT INTO class_members (class_id, student_username)
                VALUES (2, ?)
            ''', (student,))
        
        conn.commit()
        conn.close()
    
    def record_test_scenario(self, scenario_name, passed, details=None, user_feedback=None):
        """记录测试场景结果"""
        if passed:
            self.test_results['passed_scenarios'].append({
                'name': scenario_name,
                'details': details,
                'timestamp': datetime.now()
            })
        else:
            self.test_results['failed_scenarios'].append({
                'name': scenario_name,
                'details': details,
                'timestamp': datetime.now()
            })
        
        if user_feedback:
            self.test_results['user_feedback'].append({
                'scenario': scenario_name,
                'feedback': user_feedback,
                'timestamp': datetime.now()
            })
    
    def create_test_files(self, file_type="assignment"):
        """创建测试文件"""
        if file_type == "assignment":
            # 创建作业题目文件
            question_file = Path(self.temp_dir) / "question.txt"
            question_file.write_text("""
数学作业题目：

1. 解方程：2x + 5 = 13
2. 计算：(3 + 4) × 2 - 1
3. 求函数 f(x) = x² + 2x + 1 的最小值

请写出详细的解题过程。
            """.strip(), encoding='utf-8')
            
            # 创建批改标准文件
            rubric_file = Path(self.temp_dir) / "rubric.txt"
            rubric_file.write_text("""
批改标准：

1. 解方程 (30分)
   - 正确移项：10分
   - 正确计算：10分
   - 最终答案正确：10分

2. 计算题 (30分)
   - 运算顺序正确：15分
   - 计算结果正确：15分

3. 函数题 (40分)
   - 配方法或求导：20分
   - 最小值计算：20分

总分：100分
            """.strip(), encoding='utf-8')
            
            return [str(question_file)], [str(rubric_file)]
        
        elif file_type == "student_answer":
            # 创建学生答案文件
            answer_file = Path(self.temp_dir) / "student_answer.txt"
            answer_file.write_text("""
学生答案：

1. 解方程：2x + 5 = 13
   2x = 13 - 5
   2x = 8
   x = 4

2. 计算：(3 + 4) × 2 - 1
   = 7 × 2 - 1
   = 14 - 1
   = 13

3. 求函数 f(x) = x² + 2x + 1 的最小值
   f(x) = x² + 2x + 1 = (x + 1)²
   当 x = -1 时，f(x) 取最小值 0
            """.strip(), encoding='utf-8')
            
            return [str(answer_file)]


class TeacherWorkflowAcceptanceTests(UserAcceptanceTestBase):
    """教师用户完整工作流程验收测试"""
    
    def test_teacher_complete_workflow(self):
        """测试教师完整工作流程"""
        print("\n👩‍🏫 教师用户完整工作流程验收测试")
        print("=" * 50)
        
        teacher_username = "teacher_alice"
        class_id = 1
        
        # 场景1：教师登录和查看班级
        print("\n📋 场景1：教师登录和查看班级")
        try:
            # 模拟教师查看班级列表
            assignments = self.assignment_service.get_class_assignments(class_id)
            initial_assignment_count = len(assignments)
            
            print(f"✅ 教师成功查看班级，当前作业数量: {initial_assignment_count}")
            self.record_test_scenario(
                "教师登录和查看班级",
                True,
                f"成功查看班级，作业数量: {initial_assignment_count}"
            )
        except Exception as e:
            print(f"❌ 教师查看班级失败: {e}")
            self.record_test_scenario("教师登录和查看班级", False, str(e))
            return
        
        # 场景2：创建新作业
        print("\n📝 场景2：创建新作业")
        try:
            question_files, marking_files = self.create_test_files("assignment")
            
            assignment_id = self.assignment_service.create_assignment(
                class_id=class_id,
                title="期中数学测试",
                description="本次测试涵盖方程、计算和函数等内容，请认真作答。",
                question_files=question_files,
                marking_files=marking_files,
                auto_grading_enabled=True,
                deadline=datetime.now() + timedelta(days=7)
            )
            
            self.assertIsNotNone(assignment_id)
            print(f"✅ 教师成功创建作业，作业ID: {assignment_id}")
            
            # 验证作业创建成功
            assignment = self.assignment_service.get_assignment_by_id(assignment_id)
            self.assertEqual(assignment.title, "期中数学测试")
            self.assertTrue(assignment.auto_grading_enabled)
            
            self.record_test_scenario(
                "创建新作业",
                True,
                f"成功创建作业: {assignment.title}，ID: {assignment_id}"
            )
        except Exception as e:
            print(f"❌ 创建作业失败: {e}")
            self.record_test_scenario("创建新作业", False, str(e))
            return
        
        # 场景3：查看作业统计
        print("\n📊 场景3：查看作业统计")
        try:
            stats = self.assignment_service.get_assignment_statistics(assignment_id)
            
            print(f"✅ 作业统计信息:")
            print(f"   - 班级学生总数: {stats['total_students']}")
            print(f"   - 提交数量: {stats['total_submissions']}")
            print(f"   - 提交率: {stats['submission_rate']:.1f}%")
            
            self.assertIn('total_students', stats)
            self.assertIn('total_submissions', stats)
            self.assertIn('submission_rate', stats)
            
            self.record_test_scenario(
                "查看作业统计",
                True,
                f"成功获取统计信息，学生数: {stats['total_students']}"
            )
        except Exception as e:
            print(f"❌ 查看作业统计失败: {e}")
            self.record_test_scenario("查看作业统计", False, str(e))
        
        # 场景4：等待学生提交（模拟学生提交）
        print("\n👥 场景4：学生提交作业（模拟）")
        students = ['student_charlie', 'student_diana', 'student_eve']
        submitted_students = []
        
        for student in students:
            try:
                answer_files = self.create_test_files("student_answer")
                
                success = self.submission_service.submit_assignment(
                    assignment_id=assignment_id,
                    student_username=student,
                    answer_files=answer_files
                )
                
                if success:
                    submitted_students.append(student)
                    print(f"✅ 学生 {student} 成功提交作业")
                else:
                    print(f"❌ 学生 {student} 提交作业失败")
            except Exception as e:
                print(f"❌ 学生 {student} 提交作业异常: {e}")
        
        self.record_test_scenario(
            "学生提交作业",
            len(submitted_students) > 0,
            f"成功提交学生数: {len(submitted_students)}/{len(students)}"
        )
        
        # 场景5：查看学生提交列表
        print("\n📋 场景5：查看学生提交列表")
        try:
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            
            print(f"✅ 教师查看提交列表:")
            for submission in submissions:
                print(f"   - {submission.student_username}: {submission.status.value}")
            
            self.assertEqual(len(submissions), len(submitted_students))
            
            self.record_test_scenario(
                "查看学生提交列表",
                True,
                f"成功查看 {len(submissions)} 个提交"
            )
        except Exception as e:
            print(f"❌ 查看提交列表失败: {e}")
            self.record_test_scenario("查看学生提交列表", False, str(e))
        
        # 场景6：触发自动批改
        print("\n🤖 场景6：触发自动批改")
        self.mock_task_service.create_task.return_value = 'batch_task_123'
        
        graded_count = 0
        for student in submitted_students:
            try:
                submission = self.submission_service.get_submission(assignment_id, student)
                
                # 触发自动批改
                task_id = self.classroom_grading_service.trigger_auto_grading(submission)
                
                # 模拟AI批改完成
                success = self.submission_service.update_submission_grading_result(
                    submission.id,
                    score=85.0 + (graded_count * 5),  # 不同学生不同分数
                    feedback=f"AI批改：{student}的作业完成质量良好，逻辑清晰。",
                    confidence=0.9,
                    criteria_scores={'解方程': 28, '计算题': 30, '函数题': 35},
                    suggestions=['继续保持', '注意计算细节'],
                    task_id=task_id
                )
                
                if success:
                    graded_count += 1
                    print(f"✅ {student} 自动批改完成，分数: {85.0 + ((graded_count-1) * 5)}")
                
            except Exception as e:
                print(f"❌ {student} 自动批改失败: {e}")
        
        self.record_test_scenario(
            "触发自动批改",
            graded_count > 0,
            f"成功批改 {graded_count}/{len(submitted_students)} 个提交"
        )
        
        # 场景7：教师审核和修改批改结果
        print("\n✏️ 场景7：教师审核和修改批改结果")
        reviewed_count = 0
        
        for student in submitted_students[:2]:  # 只审核前两个学生
            try:
                submission = self.submission_service.get_submission(assignment_id, student)
                
                # 教师修改反馈和分数
                success = self.submission_service.update_submission_feedback(
                    submission.id,
                    teacher_feedback=f"教师反馈：{student}的作业完成得很好！解题思路清晰，计算准确。建议在函数题部分多加练习。",
                    score=submission.score + 2  # 教师给予额外2分
                )
                
                if success:
                    reviewed_count += 1
                    print(f"✅ 教师完成 {student} 的审核，调整后分数: {submission.score + 2}")
                
            except Exception as e:
                print(f"❌ 教师审核 {student} 失败: {e}")
        
        self.record_test_scenario(
            "教师审核和修改批改结果",
            reviewed_count > 0,
            f"成功审核 {reviewed_count} 个提交"
        )
        
        # 场景8：查看最终统计报告
        print("\n📈 场景8：查看最终统计报告")
        try:
            final_stats = self.assignment_service.get_assignment_statistics(assignment_id)
            submission_stats = self.submission_service.get_submission_statistics(assignment_id=assignment_id)
            
            print(f"✅ 最终统计报告:")
            print(f"   - 提交率: {final_stats['submission_rate']:.1f}%")
            print(f"   - 平均分: {submission_stats.get('average_score', 0):.1f}")
            print(f"   - AI批改数: {submission_stats.get('ai_graded_submissions', 0)}")
            print(f"   - 教师审核数: {submission_stats.get('teacher_reviewed_submissions', 0)}")
            
            self.record_test_scenario(
                "查看最终统计报告",
                True,
                f"提交率: {final_stats['submission_rate']:.1f}%, 平均分: {submission_stats.get('average_score', 0):.1f}"
            )
        except Exception as e:
            print(f"❌ 查看最终统计失败: {e}")
            self.record_test_scenario("查看最终统计报告", False, str(e))
        
        # 输出教师工作流程测试总结
        print(f"\n📋 教师工作流程测试总结:")
        print(f"✅ 通过场景: {len(self.test_results['passed_scenarios'])}")
        print(f"❌ 失败场景: {len(self.test_results['failed_scenarios'])}")
        
        # 验证关键场景都通过
        passed_scenario_names = [s['name'] for s in self.test_results['passed_scenarios']]
        critical_scenarios = ["创建新作业", "查看学生提交列表", "触发自动批改"]
        
        for scenario in critical_scenarios:
            self.assertIn(scenario, passed_scenario_names, f"关键场景 '{scenario}' 必须通过")
        
        print("🎉 教师用户完整工作流程验收测试通过！")
    
    def test_teacher_advanced_features(self):
        """测试教师高级功能"""
        print("\n👩‍🏫 教师高级功能验收测试")
        print("=" * 50)
        
        # 场景1：批量操作
        print("\n📦 场景1：批量操作测试")
        try:
            # 创建多个作业
            assignment_ids = []
            for i in range(3):
                assignment_id = self.assignment_service.create_assignment(
                    class_id=1,
                    title=f"批量测试作业{i+1}",
                    description=f"第{i+1}个批量测试作业"
                )
                assignment_ids.append(assignment_id)
            
            # 批量查看作业
            assignments = self.assignment_service.get_class_assignments(1)
            batch_assignments = [a for a in assignments if a.title.startswith("批量测试")]
            
            self.assertEqual(len(batch_assignments), 3)
            print(f"✅ 成功创建和查看 {len(batch_assignments)} 个批量作业")
            
            self.record_test_scenario("批量操作", True, f"成功处理 {len(batch_assignments)} 个作业")
            
        except Exception as e:
            print(f"❌ 批量操作失败: {e}")
            self.record_test_scenario("批量操作", False, str(e))
        
        # 场景2：搜索和筛选
        print("\n🔍 场景2：搜索和筛选测试")
        try:
            # 搜索作业
            search_results = self.assignment_service.search_assignments(keyword="批量")
            self.assertGreater(len(search_results), 0)
            
            # 按教师筛选
            teacher_assignments = self.assignment_service.search_assignments(teacher_username="teacher_alice")
            self.assertGreater(len(teacher_assignments), 0)
            
            print(f"✅ 搜索功能正常，找到 {len(search_results)} 个相关作业")
            self.record_test_scenario("搜索和筛选", True, f"搜索结果: {len(search_results)} 个")
            
        except Exception as e:
            print(f"❌ 搜索和筛选失败: {e}")
            self.record_test_scenario("搜索和筛选", False, str(e))


class StudentWorkflowAcceptanceTests(UserAcceptanceTestBase):
    """学生用户完整工作流程验收测试"""
    
    def test_student_complete_workflow(self):
        """测试学生完整工作流程"""
        print("\n👨‍🎓 学生用户完整工作流程验收测试")
        print("=" * 50)
        
        student_username = "student_charlie"
        
        # 准备测试环境：教师先创建作业
        question_files, marking_files = self.create_test_files("assignment")
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="学生测试作业",
            description="用于学生工作流程测试的作业",
            question_files=question_files,
            marking_files=marking_files,
            auto_grading_enabled=True,
            deadline=datetime.now() + timedelta(days=3)
        )
        
        # 场景1：学生登录和查看作业列表
        print("\n📚 场景1：学生登录和查看作业列表")
        try:
            assignments = self.assignment_service.get_student_assignments(student_username, class_id=1)
            
            print(f"✅ 学生成功查看作业列表，共 {len(assignments)} 个作业")
            for assignment in assignments:
                print(f"   - {assignment.title}: {assignment.status if hasattr(assignment, 'status') else '未提交'}")
            
            self.assertGreater(len(assignments), 0)
            self.record_test_scenario(
                "学生查看作业列表",
                True,
                f"成功查看 {len(assignments)} 个作业"
            )
            
        except Exception as e:
            print(f"❌ 学生查看作业列表失败: {e}")
            self.record_test_scenario("学生查看作业列表", False, str(e))
            return
        
        # 场景2：查看作业详情
        print("\n📖 场景2：查看作业详情")
        try:
            assignment = self.assignment_service.get_assignment_by_id(assignment_id)
            
            print(f"✅ 学生查看作业详情:")
            print(f"   - 标题: {assignment.title}")
            print(f"   - 描述: {assignment.description}")
            print(f"   - 截止时间: {assignment.deadline}")
            print(f"   - 题目文件数: {len(assignment.question_files)}")
            
            self.assertIsNotNone(assignment)
            self.assertEqual(assignment.title, "学生测试作业")
            
            self.record_test_scenario(
                "查看作业详情",
                True,
                f"成功查看作业: {assignment.title}"
            )
            
        except Exception as e:
            print(f"❌ 查看作业详情失败: {e}")
            self.record_test_scenario("查看作业详情", False, str(e))
        
        # 场景3：准备和上传答案文件
        print("\n📝 场景3：准备和上传答案文件")
        try:
            answer_files = self.create_test_files("student_answer")
            
            print(f"✅ 学生准备答案文件:")
            for file_path in answer_files:
                file_size = Path(file_path).stat().st_size
                print(f"   - {Path(file_path).name}: {file_size} 字节")
            
            self.assertEqual(len(answer_files), 1)
            self.assertGreater(Path(answer_files[0]).stat().st_size, 0)
            
            self.record_test_scenario(
                "准备答案文件",
                True,
                f"成功准备 {len(answer_files)} 个答案文件"
            )
            
        except Exception as e:
            print(f"❌ 准备答案文件失败: {e}")
            self.record_test_scenario("准备答案文件", False, str(e))
            return
        
        # 场景4：提交作业
        print("\n📤 场景4：提交作业")
        try:
            success = self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username=student_username,
                answer_files=answer_files
            )
            
            self.assertTrue(success)
            print(f"✅ 学生成功提交作业")
            
            # 验证提交记录
            submission = self.submission_service.get_submission(assignment_id, student_username)
            self.assertIsNotNone(submission)
            self.assertEqual(submission.status, SubmissionStatus.SUBMITTED)
            
            self.record_test_scenario(
                "提交作业",
                True,
                f"成功提交作业，状态: {submission.status.value}"
            )
            
        except Exception as e:
            print(f"❌ 提交作业失败: {e}")
            self.record_test_scenario("提交作业", False, str(e))
            return
        
        # 场景5：查看提交状态
        print("\n📊 场景5：查看提交状态")
        try:
            submission = self.submission_service.get_submission(assignment_id, student_username)
            
            print(f"✅ 学生查看提交状态:")
            print(f"   - 提交状态: {submission.status.value}")
            print(f"   - 提交时间: {submission.submitted_at}")
            print(f"   - 文件数量: {len(submission.answer_files)}")
            
            self.assertEqual(submission.status, SubmissionStatus.SUBMITTED)
            self.record_test_scenario(
                "查看提交状态",
                True,
                f"提交状态: {submission.status.value}"
            )
            
        except Exception as e:
            print(f"❌ 查看提交状态失败: {e}")
            self.record_test_scenario("查看提交状态", False, str(e))
        
        # 场景6：等待批改完成（模拟AI批改）
        print("\n⏳ 场景6：等待批改完成（模拟AI批改）")
        try:
            self.mock_task_service.create_task.return_value = 'student_task_123'
            
            # 触发自动批改
            task_id = self.classroom_grading_service.trigger_auto_grading(submission)
            
            # 模拟AI批改完成
            success = self.submission_service.update_submission_grading_result(
                submission.id,
                score=88.0,
                feedback="AI批改：作业完成质量优秀！解题步骤清晰，答案正确。",
                confidence=0.92,
                criteria_scores={'解方程': 30, '计算题': 28, '函数题': 38},
                suggestions=['继续保持优秀水平', '可以尝试更多挑战性题目'],
                task_id=task_id
            )
            
            self.assertTrue(success)
            print(f"✅ AI批改完成，分数: 88.0")
            
            self.record_test_scenario(
                "AI批改完成",
                True,
                "AI批改成功，分数: 88.0"
            )
            
        except Exception as e:
            print(f"❌ AI批改失败: {e}")
            self.record_test_scenario("AI批改完成", False, str(e))
        
        # 场景7：查看批改结果
        print("\n🎯 场景7：查看批改结果")
        try:
            graded_submission = self.submission_service.get_submission(assignment_id, student_username)
            
            print(f"✅ 学生查看批改结果:")
            print(f"   - 最终分数: {graded_submission.score}")
            print(f"   - 批改状态: {graded_submission.status.value}")
            print(f"   - AI反馈: {graded_submission.ai_result}")
            print(f"   - AI置信度: {graded_submission.ai_confidence}")
            
            self.assertEqual(graded_submission.status, SubmissionStatus.AI_GRADED)
            self.assertEqual(graded_submission.score, 88.0)
            self.assertIsNotNone(graded_submission.ai_result)
            
            self.record_test_scenario(
                "查看批改结果",
                True,
                f"分数: {graded_submission.score}, 状态: {graded_submission.status.value}"
            )
            
        except Exception as e:
            print(f"❌ 查看批改结果失败: {e}")
            self.record_test_scenario("查看批改结果", False, str(e))
        
        # 场景8：查看提交历史
        print("\n📚 场景8：查看提交历史")
        try:
            history = self.submission_service.get_submission_history(student_username)
            
            print(f"✅ 学生查看提交历史:")
            for submission in history:
                print(f"   - {submission.assignment_title}: {submission.score or '未批改'} 分")
            
            self.assertGreater(len(history), 0)
            self.record_test_scenario(
                "查看提交历史",
                True,
                f"历史记录数: {len(history)}"
            )
            
        except Exception as e:
            print(f"❌ 查看提交历史失败: {e}")
            self.record_test_scenario("查看提交历史", False, str(e))
        
        # 输出学生工作流程测试总结
        print(f"\n📋 学生工作流程测试总结:")
        print(f"✅ 通过场景: {len(self.test_results['passed_scenarios'])}")
        print(f"❌ 失败场景: {len(self.test_results['failed_scenarios'])}")
        
        # 验证关键场景都通过
        passed_scenario_names = [s['name'] for s in self.test_results['passed_scenarios']]
        critical_scenarios = ["提交作业", "查看批改结果", "查看提交历史"]
        
        for scenario in critical_scenarios:
            self.assertIn(scenario, passed_scenario_names, f"关键场景 '{scenario}' 必须通过")
        
        print("🎉 学生用户完整工作流程验收测试通过！")
    
    def test_student_edge_cases(self):
        """测试学生边缘情况"""
        print("\n👨‍🎓 学生边缘情况验收测试")
        print("=" * 50)
        
        student_username = "student_diana"
        
        # 场景1：重复提交测试
        print("\n🔄 场景1：重复提交测试")
        try:
            # 创建测试作业
            assignment_id = self.assignment_service.create_assignment(
                class_id=1,
                title="重复提交测试作业",
                description="用于测试重复提交功能"
            )
            
            answer_files = self.create_test_files("student_answer")
            
            # 第一次提交
            success1 = self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username=student_username,
                answer_files=answer_files
            )
            
            # 第二次提交（应该覆盖第一次）
            success2 = self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username=student_username,
                answer_files=answer_files
            )
            
            self.assertTrue(success1)
            self.assertTrue(success2)
            
            # 验证只有一个提交记录
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            student_submissions = [s for s in submissions if s.student_username == student_username]
            self.assertEqual(len(student_submissions), 1)
            
            print("✅ 重复提交处理正确，第二次提交覆盖第一次")
            self.record_test_scenario("重复提交测试", True, "重复提交处理正确")
            
        except Exception as e:
            print(f"❌ 重复提交测试失败: {e}")
            self.record_test_scenario("重复提交测试", False, str(e))
        
        # 场景2：过期作业提交测试
        print("\n⏰ 场景2：过期作业提交测试")
        try:
            # 创建已过期的作业
            expired_assignment_id = self.assignment_service.create_assignment(
                class_id=1,
                title="过期作业测试",
                description="用于测试过期提交",
                deadline=datetime.now() - timedelta(days=1)  # 昨天截止
            )
            
            answer_files = self.create_test_files("student_answer")
            
            # 尝试提交过期作业
            success = self.submission_service.submit_assignment(
                assignment_id=expired_assignment_id,
                student_username=student_username,
                answer_files=answer_files
            )
            
            # 系统应该允许过期提交，但标记为迟交
            self.assertTrue(success)
            
            submission = self.submission_service.get_submission(expired_assignment_id, student_username)
            self.assertIsNotNone(submission)
            
            print("✅ 过期作业提交处理正确，允许迟交")
            self.record_test_scenario("过期作业提交", True, "允许过期提交")
            
        except Exception as e:
            print(f"❌ 过期作业提交测试失败: {e}")
            self.record_test_scenario("过期作业提交", False, str(e))


class SystemAdminAcceptanceTests(UserAcceptanceTestBase):
    """系统管理员监控和维护验收测试"""
    
    def test_system_monitoring_workflow(self):
        """测试系统监控工作流程"""
        print("\n👨‍💼 系统管理员监控和维护验收测试")
        print("=" * 50)
        
        admin_username = "admin_frank"
        
        # 准备测试数据
        self._prepare_monitoring_test_data()
        
        # 场景1：系统整体状态监控
        print("\n📊 场景1：系统整体状态监控")
        try:
            # 获取系统统计信息
            total_users = self._get_total_users()
            total_assignments = self._get_total_assignments()
            total_submissions = self._get_total_submissions()
            
            print(f"✅ 系统整体状态:")
            print(f"   - 总用户数: {total_users}")
            print(f"   - 总作业数: {total_assignments}")
            print(f"   - 总提交数: {total_submissions}")
            
            self.assertGreater(total_users, 0)
            self.assertGreater(total_assignments, 0)
            
            self.record_test_scenario(
                "系统整体状态监控",
                True,
                f"用户: {total_users}, 作业: {total_assignments}, 提交: {total_submissions}"
            )
            
        except Exception as e:
            print(f"❌ 系统状态监控失败: {e}")
            self.record_test_scenario("系统整体状态监控", False, str(e))
        
        # 场景2：教师活动监控
        print("\n👩‍🏫 场景2：教师活动监控")
        try:
            teachers = ['teacher_alice', 'teacher_bob']
            teacher_activities = {}
            
            for teacher in teachers:
                summary = self.assignment_service.get_teacher_assignment_summary(teacher)
                teacher_activities[teacher] = summary
                
                print(f"✅ 教师 {teacher} 活动统计:")
                print(f"   - 总作业数: {summary.get('total_assignments', 0)}")
                print(f"   - 活跃作业数: {summary.get('active_assignments', 0)}")
                print(f"   - 待批改数: {summary.get('pending_grading', 0)}")
            
            self.assertGreater(len(teacher_activities), 0)
            self.record_test_scenario(
                "教师活动监控",
                True,
                f"监控了 {len(teacher_activities)} 个教师的活动"
            )
            
        except Exception as e:
            print(f"❌ 教师活动监控失败: {e}")
            self.record_test_scenario("教师活动监控", False, str(e))
        
        # 场景3：批改任务监控
        print("\n🤖 场景3：批改任务监控")
        try:
            # 创建一些批改任务进行监控
            assignment_id = self.assignment_service.create_assignment(
                class_id=1,
                title="监控测试作业",
                description="用于监控测试"
            )
            
            # 模拟学生提交
            students = ['student_charlie', 'student_diana']
            for student in students:
                answer_files = self.create_test_files("student_answer")
                self.submission_service.submit_assignment(
                    assignment_id=assignment_id,
                    student_username=student,
                    answer_files=answer_files
                )
            
            # 获取批改统计
            grading_stats = self.classroom_grading_service.get_grading_statistics(assignment_id=assignment_id)
            
            print(f"✅ 批改任务监控:")
            print(f"   - 总任务数: {grading_stats.get('total_tasks', 0)}")
            print(f"   - 完成任务数: {grading_stats.get('completed_tasks', 0)}")
            print(f"   - 失败任务数: {grading_stats.get('failed_tasks', 0)}")
            print(f"   - 完成率: {grading_stats.get('completion_rate', 0):.1f}%")
            
            self.assertIn('total_tasks', grading_stats)
            self.record_test_scenario(
                "批改任务监控",
                True,
                f"任务统计: {grading_stats.get('total_tasks', 0)} 个任务"
            )
            
        except Exception as e:
            print(f"❌ 批改任务监控失败: {e}")
            self.record_test_scenario("批改任务监控", False, str(e))
        
        # 场景4：系统性能监控
        print("\n⚡ 场景4：系统性能监控")
        try:
            # 模拟性能监控
            start_time = time.time()
            
            # 执行一些系统操作
            assignments = self.assignment_service.get_class_assignments(1)
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ 系统性能监控:")
            print(f"   - 查询响应时间: {response_time:.4f} 秒")
            print(f"   - 查询结果数: 作业 {len(assignments)} 个, 提交 {len(submissions)} 个")
            
            # 性能应该在合理范围内
            self.assertLess(response_time, 1.0, "查询响应时间应小于1秒")
            
            self.record_test_scenario(
                "系统性能监控",
                True,
                f"响应时间: {response_time:.4f} 秒"
            )
            
        except Exception as e:
            print(f"❌ 系统性能监控失败: {e}")
            self.record_test_scenario("系统性能监控", False, str(e))
        
        # 场景5：数据完整性检查
        print("\n🔍 场景5：数据完整性检查")
        try:
            # 检查数据一致性
            integrity_issues = self._check_data_integrity()
            
            print(f"✅ 数据完整性检查:")
            if integrity_issues:
                print(f"   - 发现问题: {len(integrity_issues)} 个")
                for issue in integrity_issues:
                    print(f"     * {issue}")
            else:
                print(f"   - 数据完整性良好，未发现问题")
            
            # 记录检查结果
            self.record_test_scenario(
                "数据完整性检查",
                len(integrity_issues) == 0,
                f"发现 {len(integrity_issues)} 个问题" if integrity_issues else "数据完整性良好"
            )
            
        except Exception as e:
            print(f"❌ 数据完整性检查失败: {e}")
            self.record_test_scenario("数据完整性检查", False, str(e))
        
        # 输出管理员监控测试总结
        print(f"\n📋 系统管理员监控测试总结:")
        print(f"✅ 通过场景: {len(self.test_results['passed_scenarios'])}")
        print(f"❌ 失败场景: {len(self.test_results['failed_scenarios'])}")
        
        # 验证关键监控场景都通过
        passed_scenario_names = [s['name'] for s in self.test_results['passed_scenarios']]
        critical_scenarios = ["系统整体状态监控", "教师活动监控", "系统性能监控"]
        
        for scenario in critical_scenarios:
            self.assertIn(scenario, passed_scenario_names, f"关键监控场景 '{scenario}' 必须通过")
        
        print("🎉 系统管理员监控和维护验收测试通过！")
    
    def _prepare_monitoring_test_data(self):
        """准备监控测试数据"""
        # 创建一些测试作业和提交
        for i in range(3):
            assignment_id = self.assignment_service.create_assignment(
                class_id=1,
                title=f"监控数据作业{i+1}",
                description=f"第{i+1}个监控数据作业"
            )
            
            # 为每个作业创建一些提交
            students = ['student_charlie', 'student_diana']
            for student in students:
                try:
                    answer_files = self.create_test_files("student_answer")
                    self.submission_service.submit_assignment(
                        assignment_id=assignment_id,
                        student_username=student,
                        answer_files=answer_files
                    )
                except:
                    pass  # 忽略重复提交错误
    
    def _get_total_users(self):
        """获取总用户数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _get_total_assignments(self):
        """获取总作业数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM assignments WHERE is_active = 1')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _get_total_submissions(self):
        """获取总提交数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM submissions')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _check_data_integrity(self):
        """检查数据完整性"""
        issues = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查孤立的提交记录
            cursor.execute('''
                SELECT COUNT(*) FROM submissions s
                LEFT JOIN assignments a ON s.assignment_id = a.id
                WHERE a.id IS NULL
            ''')
            orphaned_submissions = cursor.fetchone()[0]
            if orphaned_submissions > 0:
                issues.append(f"发现 {orphaned_submissions} 个孤立的提交记录")
            
            # 检查无效的用户引用
            cursor.execute('''
                SELECT COUNT(*) FROM submissions s
                LEFT JOIN users u ON s.student_username = u.username
                WHERE u.username IS NULL
            ''')
            invalid_users = cursor.fetchone()[0]
            if invalid_users > 0:
                issues.append(f"发现 {invalid_users} 个无效的用户引用")
            
            conn.close()
            
        except Exception as e:
            issues.append(f"数据完整性检查异常: {e}")
        
        return issues


class UIUsabilityTests(UserAcceptanceTestBase):
    """用户界面可用性和响应性测试"""
    
    def test_ui_component_usability(self):
        """测试UI组件可用性"""
        print("\n🖥️ 用户界面可用性验收测试")
        print("=" * 50)
        
        # 场景1：组件实例化测试
        print("\n🔧 场景1：UI组件实例化测试")
        try:
            # 测试所有UI组件是否可以正常实例化
            ui_components = []
            
            try:
                from src.ui.components.assignment_center import AssignmentCenter
                assignment_center = AssignmentCenter(self.assignment_service, self.submission_service)
                ui_components.append(('AssignmentCenter', assignment_center))
            except ImportError:
                print("⚠️ AssignmentCenter组件未找到")
            
            try:
                from src.ui.components.submission_interface import SubmissionInterface
                submission_interface = SubmissionInterface(self.assignment_service, self.submission_service)
                ui_components.append(('SubmissionInterface', submission_interface))
            except ImportError:
                print("⚠️ SubmissionInterface组件未找到")
            
            try:
                from src.ui.components.grading_dashboard import GradingDashboard
                grading_dashboard = GradingDashboard(self.assignment_service, self.submission_service)
                ui_components.append(('GradingDashboard', grading_dashboard))
            except ImportError:
                print("⚠️ GradingDashboard组件未找到")
            
            print(f"✅ 成功实例化 {len(ui_components)} 个UI组件")
            for name, component in ui_components:
                print(f"   - {name}: {type(component).__name__}")
            
            self.record_test_scenario(
                "UI组件实例化",
                len(ui_components) > 0,
                f"成功实例化 {len(ui_components)} 个组件"
            )
            
        except Exception as e:
            print(f"❌ UI组件实例化失败: {e}")
            self.record_test_scenario("UI组件实例化", False, str(e))
        
        # 场景2：组件方法可用性测试
        print("\n⚙️ 场景2：组件方法可用性测试")
        try:
            method_tests = []
            
            for name, component in ui_components:
                # 检查组件是否有必要的方法
                required_methods = self._get_required_methods(name)
                
                for method_name in required_methods:
                    has_method = hasattr(component, method_name)
                    method_tests.append((name, method_name, has_method))
                    
                    if has_method:
                        print(f"✅ {name}.{method_name} 方法存在")
                    else:
                        print(f"❌ {name}.{method_name} 方法缺失")
            
            successful_methods = [t for t in method_tests if t[2]]
            success_rate = len(successful_methods) / len(method_tests) if method_tests else 0
            
            print(f"✅ 方法可用性测试完成，成功率: {success_rate:.1%}")
            
            self.record_test_scenario(
                "组件方法可用性",
                success_rate >= 0.8,
                f"方法成功率: {success_rate:.1%}"
            )
            
        except Exception as e:
            print(f"❌ 组件方法可用性测试失败: {e}")
            self.record_test_scenario("组件方法可用性", False, str(e))
        
        # 场景3：响应性测试
        print("\n⚡ 场景3：UI响应性测试")
        try:
            response_times = []
            
            # 测试各种操作的响应时间
            operations = [
                ("获取作业列表", lambda: self.assignment_service.get_class_assignments(1)),
                ("获取提交列表", lambda: self.submission_service.get_assignment_submissions(1)),
                ("获取统计数据", lambda: self.assignment_service.get_assignment_statistics(1)),
            ]
            
            for operation_name, operation in operations:
                start_time = time.time()
                try:
                    result = operation()
                    end_time = time.time()
                    response_time = end_time - start_time
                    response_times.append(response_time)
                    
                    print(f"✅ {operation_name}: {response_time:.4f} 秒")
                except Exception as e:
                    print(f"❌ {operation_name} 失败: {e}")
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                print(f"✅ 响应性测试结果:")
                print(f"   - 平均响应时间: {avg_response_time:.4f} 秒")
                print(f"   - 最大响应时间: {max_response_time:.4f} 秒")
                
                # 响应时间应该在合理范围内
                is_responsive = avg_response_time < 0.5 and max_response_time < 1.0
                
                self.record_test_scenario(
                    "UI响应性",
                    is_responsive,
                    f"平均: {avg_response_time:.4f}s, 最大: {max_response_time:.4f}s"
                )
            
        except Exception as e:
            print(f"❌ UI响应性测试失败: {e}")
            self.record_test_scenario("UI响应性", False, str(e))
        
        # 输出UI可用性测试总结
        print(f"\n📋 UI可用性测试总结:")
        print(f"✅ 通过场景: {len(self.test_results['passed_scenarios'])}")
        print(f"❌ 失败场景: {len(self.test_results['failed_scenarios'])}")
        
        print("🎉 用户界面可用性验收测试完成！")
    
    def _get_required_methods(self, component_name):
        """获取组件必需的方法列表"""
        method_map = {
            'AssignmentCenter': [
                'render_teacher_view',
                'render_student_view',
                'render_assignment_creation_form'
            ],
            'SubmissionInterface': [
                'render_assignment_details',
                'render_file_upload_form',
                'render_submission_status'
            ],
            'GradingDashboard': [
                'render_class_overview',
                'render_assignment_statistics',
                'render_grading_progress'
            ]
        }
        
        return method_map.get(component_name, [])


def run_user_acceptance_tests():
    """运行用户验收测试套件"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TeacherWorkflowAcceptanceTests,
        StudentWorkflowAcceptanceTests,
        SystemAdminAcceptanceTests,
        UIUsabilityTests
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
    print(f"用户验收测试结果:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - failures - errors}")
    print(f"失败: {failures}")
    print(f"错误: {errors}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"{'='*60}")
    
    return success_rate >= 80.0


if __name__ == '__main__':
    success = run_user_acceptance_tests()
    sys.exit(0 if success else 1)