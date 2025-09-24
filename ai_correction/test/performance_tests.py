#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能和负载测试套件
编写批量批改性能测试，验证系统处理能力
编写并发用户访问负载测试
编写大文件上传和处理性能测试
编写数据库查询性能测试
"""

import unittest
import tempfile
import sqlite3
import json
import os
import sys
import time
import threading
import psutil
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入所有需要测试的模块
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.services.classroom_grading_service import ClassroomGradingService
from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus


class PerformanceTestBase(unittest.TestCase):
    """性能测试基类"""
    
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
        
        # 性能监控
        self.performance_metrics = {
            'start_time': None,
            'end_time': None,
            'memory_usage': [],
            'cpu_usage': [],
            'response_times': []
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
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX idx_assignments_class_id ON assignments(class_id)')
        cursor.execute('CREATE INDEX idx_submissions_assignment_id ON submissions(assignment_id)')
        cursor.execute('CREATE INDEX idx_submissions_student ON submissions(student_username)')
        cursor.execute('CREATE INDEX idx_submissions_status ON submissions(status)')
        cursor.execute('CREATE INDEX idx_notifications_recipient ON notifications(recipient_username)')
        
        # 插入测试数据
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name)
            VALUES ('teacher1', 'hash1', 'teacher', '张老师')
        ''')
        
        cursor.execute('''
            INSERT INTO classes (id, name, description, teacher_username, invite_code)
            VALUES (1, '性能测试班级', '用于性能测试', 'teacher1', 'PERF001')
        ''')
        
        conn.commit()
        conn.close()
    
    def start_performance_monitoring(self):
        """开始性能监控"""
        self.performance_metrics['start_time'] = time.time()
        self.performance_metrics['memory_usage'] = []
        self.performance_metrics['cpu_usage'] = []
        self.performance_metrics['response_times'] = []
    
    def record_performance_metric(self, operation_time=None):
        """记录性能指标"""
        # 记录内存使用
        memory_info = psutil.virtual_memory()
        self.performance_metrics['memory_usage'].append(memory_info.percent)
        
        # 记录CPU使用
        cpu_percent = psutil.cpu_percent()
        self.performance_metrics['cpu_usage'].append(cpu_percent)
        
        # 记录响应时间
        if operation_time is not None:
            self.performance_metrics['response_times'].append(operation_time)
    
    def stop_performance_monitoring(self):
        """停止性能监控"""
        self.performance_metrics['end_time'] = time.time()
        
        # 计算总体性能指标
        total_time = self.performance_metrics['end_time'] - self.performance_metrics['start_time']
        
        metrics_summary = {
            'total_time': total_time,
            'avg_memory_usage': statistics.mean(self.performance_metrics['memory_usage']) if self.performance_metrics['memory_usage'] else 0,
            'max_memory_usage': max(self.performance_metrics['memory_usage']) if self.performance_metrics['memory_usage'] else 0,
            'avg_cpu_usage': statistics.mean(self.performance_metrics['cpu_usage']) if self.performance_metrics['cpu_usage'] else 0,
            'max_cpu_usage': max(self.performance_metrics['cpu_usage']) if self.performance_metrics['cpu_usage'] else 0,
            'avg_response_time': statistics.mean(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0,
            'max_response_time': max(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0,
            'min_response_time': min(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0
        }
        
        return metrics_summary
    
    def generate_random_string(self, length=100):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))
    
    def create_large_test_file(self, size_mb=1):
        """创建大测试文件"""
        file_path = Path(self.temp_dir) / f"large_file_{size_mb}mb.txt"
        
        # 生成指定大小的文件内容
        content_size = size_mb * 1024 * 1024  # 转换为字节
        chunk_size = 1024  # 每次写入1KB
        
        with open(file_path, 'w', encoding='utf-8') as f:
            written = 0
            while written < content_size:
                chunk = self.generate_random_string(min(chunk_size, content_size - written))
                f.write(chunk)
                written += len(chunk.encode('utf-8'))
        
        return str(file_path)


class BatchGradingPerformanceTests(PerformanceTestBase):
    """批量批改性能测试"""
    
    def test_batch_grading_performance(self):
        """测试批量批改性能"""
        print("\n🧪 测试批量批改性能...")
        
        # 创建大量学生用户
        num_students = 100
        print(f"1. 创建 {num_students} 个学生用户...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i in range(1, num_students + 1):
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name)
                VALUES (?, ?, ?, ?)
            ''', (f'student{i}', f'hash{i}', 'student', f'学生{i}'))
            
            cursor.execute('''
                INSERT INTO class_members (class_id, student_username)
                VALUES (1, ?)
            ''', (f'student{i}',))
        
        conn.commit()
        conn.close()
        
        # 创建作业
        print("2. 创建测试作业...")
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="批量批改性能测试作业",
            description="用于测试批量批改性能",
            auto_grading_enabled=True
        )
        
        # 批量提交作业
        print(f"3. 批量提交 {num_students} 个作业...")
        self.start_performance_monitoring()
        
        submission_times = []
        for i in range(1, num_students + 1):
            start_time = time.time()
            
            success = self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username=f'student{i}',
                answer_files=[f'answer_{i}.txt']
            )
            
            end_time = time.time()
            submission_time = end_time - start_time
            submission_times.append(submission_time)
            
            self.assertTrue(success)
            self.record_performance_metric(submission_time)
        
        # 批量AI批改
        print(f"4. 批量AI批改 {num_students} 个提交...")
        grading_times = []
        
        for i in range(1, num_students + 1):
            submission = self.submission_service.get_submission(assignment_id, f'student{i}')
            
            start_time = time.time()
            
            success = self.submission_service.update_submission_grading_result(
                submission.id,
                score=random.uniform(70, 95),
                feedback=f"AI批改：学生{i}的作业完成质量良好。",
                confidence=random.uniform(0.8, 0.95),
                criteria_scores={'内容': random.uniform(80, 95), '语法': random.uniform(75, 90)},
                suggestions=['继续保持', '注意细节'],
                task_id=f'task_{i}'
            )
            
            end_time = time.time()
            grading_time = end_time - start_time
            grading_times.append(grading_time)
            
            self.assertTrue(success)
            self.record_performance_metric(grading_time)
        
        # 停止监控并分析结果
        metrics = self.stop_performance_monitoring()
        
        print(f"\n📊 批量批改性能测试结果:")
        print(f"- 总处理时间: {metrics['total_time']:.2f} 秒")
        print(f"- 平均提交时间: {statistics.mean(submission_times):.4f} 秒")
        print(f"- 平均批改时间: {statistics.mean(grading_times):.4f} 秒")
        print(f"- 最大响应时间: {metrics['max_response_time']:.4f} 秒")
        print(f"- 平均内存使用: {metrics['avg_memory_usage']:.2f}%")
        print(f"- 最大内存使用: {metrics['max_memory_usage']:.2f}%")
        print(f"- 平均CPU使用: {metrics['avg_cpu_usage']:.2f}%")
        
        # 性能断言
        self.assertLess(statistics.mean(submission_times), 0.1, "平均提交时间应小于100ms")
        self.assertLess(statistics.mean(grading_times), 0.2, "平均批改时间应小于200ms")
        self.assertLess(metrics['max_memory_usage'], 80, "最大内存使用应小于80%")
        
        print("✅ 批量批改性能测试通过！")
    
    def test_concurrent_grading_performance(self):
        """测试并发批改性能"""
        print("\n🧪 测试并发批改性能...")
        
        # 创建测试数据
        num_students = 50
        num_threads = 10
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i in range(1, num_students + 1):
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name)
                VALUES (?, ?, ?, ?)
            ''', (f'concurrent_student{i}', f'hash{i}', 'student', f'并发学生{i}'))
        
        conn.commit()
        conn.close()
        
        # 创建作业
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="并发批改性能测试作业",
            description="用于测试并发批改性能"
        )
        
        # 先提交所有作业
        for i in range(1, num_students + 1):
            self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username=f'concurrent_student{i}',
                answer_files=[f'concurrent_answer_{i}.txt']
            )
        
        # 并发批改函数
        def grade_submission(student_index):
            try:
                start_time = time.time()
                
                submission = self.submission_service.get_submission(
                    assignment_id, f'concurrent_student{student_index}'
                )
                
                success = self.submission_service.update_submission_grading_result(
                    submission.id,
                    score=random.uniform(70, 95),
                    feedback=f"并发批改：学生{student_index}的作业。",
                    confidence=random.uniform(0.8, 0.95)
                )
                
                end_time = time.time()
                return {
                    'student_index': student_index,
                    'success': success,
                    'time': end_time - start_time
                }
            except Exception as e:
                return {
                    'student_index': student_index,
                    'success': False,
                    'error': str(e),
                    'time': 0
                }
        
        # 开始并发批改
        print(f"开始并发批改 {num_students} 个提交，使用 {num_threads} 个线程...")
        self.start_performance_monitoring()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(grade_submission, i) 
                for i in range(1, num_students + 1)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                self.record_performance_metric(result['time'])
        
        metrics = self.stop_performance_monitoring()
        
        # 分析结果
        successful_gradings = [r for r in results if r['success']]
        failed_gradings = [r for r in results if not r['success']]
        grading_times = [r['time'] for r in successful_gradings]
        
        print(f"\n📊 并发批改性能测试结果:")
        print(f"- 成功批改: {len(successful_gradings)}/{num_students}")
        print(f"- 失败批改: {len(failed_gradings)}")
        print(f"- 总处理时间: {metrics['total_time']:.2f} 秒")
        print(f"- 平均批改时间: {statistics.mean(grading_times):.4f} 秒")
        print(f"- 吞吐量: {len(successful_gradings) / metrics['total_time']:.2f} 批改/秒")
        print(f"- 最大内存使用: {metrics['max_memory_usage']:.2f}%")
        
        # 性能断言
        self.assertGreaterEqual(len(successful_gradings), num_students * 0.95, "成功率应大于95%")
        self.assertLess(metrics['total_time'], 30, "总处理时间应小于30秒")
        
        print("✅ 并发批改性能测试通过！")


class LoadTests(PerformanceTestBase):
    """负载测试"""
    
    def test_concurrent_user_access_load(self):
        """测试并发用户访问负载"""
        print("\n🧪 测试并发用户访问负载...")
        
        # 创建大量用户和作业
        num_users = 200
        num_assignments = 20
        
        print(f"1. 创建 {num_users} 个用户...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i in range(1, num_users + 1):
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name)
                VALUES (?, ?, ?, ?)
            ''', (f'load_user{i}', f'hash{i}', 'student', f'负载用户{i}'))
        
        conn.commit()
        conn.close()
        
        print(f"2. 创建 {num_assignments} 个作业...")
        assignment_ids = []
        for i in range(1, num_assignments + 1):
            assignment_id = self.assignment_service.create_assignment(
                class_id=1,
                title=f"负载测试作业{i}",
                description=f"第{i}个负载测试作业"
            )
            assignment_ids.append(assignment_id)
        
        # 模拟用户操作
        def simulate_user_operations(user_index):
            """模拟单个用户的操作"""
            operations = []
            
            try:
                # 1. 获取作业列表
                start_time = time.time()
                assignments = self.assignment_service.get_student_assignments(f'load_user{user_index}')
                operations.append(('get_assignments', time.time() - start_time))
                
                # 2. 随机选择几个作业进行操作
                selected_assignments = random.sample(assignment_ids, min(5, len(assignment_ids)))
                
                for assignment_id in selected_assignments:
                    # 获取作业详情
                    start_time = time.time()
                    assignment = self.assignment_service.get_assignment_by_id(assignment_id)
                    operations.append(('get_assignment_detail', time.time() - start_time))
                    
                    # 提交作业
                    start_time = time.time()
                    success = self.submission_service.submit_assignment(
                        assignment_id=assignment_id,
                        student_username=f'load_user{user_index}',
                        answer_files=[f'load_answer_{user_index}_{assignment_id}.txt']
                    )
                    operations.append(('submit_assignment', time.time() - start_time))
                    
                    if success:
                        # 查看提交状态
                        start_time = time.time()
                        submission = self.submission_service.get_submission(
                            assignment_id, f'load_user{user_index}'
                        )
                        operations.append(('get_submission', time.time() - start_time))
                
                return {
                    'user_index': user_index,
                    'success': True,
                    'operations': operations
                }
                
            except Exception as e:
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e),
                    'operations': operations
                }
        
        # 开始负载测试
        print(f"3. 开始 {num_users} 个用户的并发访问...")
        self.start_performance_monitoring()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(simulate_user_operations, i) 
                for i in range(1, num_users + 1)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # 记录所有操作的响应时间
                for operation_name, operation_time in result.get('operations', []):
                    self.record_performance_metric(operation_time)
        
        metrics = self.stop_performance_monitoring()
        
        # 分析结果
        successful_users = [r for r in results if r['success']]
        failed_users = [r for r in results if not r['success']]
        
        all_operations = []
        for result in successful_users:
            all_operations.extend(result['operations'])
        
        operation_times = [op[1] for op in all_operations]
        
        print(f"\n📊 并发用户访问负载测试结果:")
        print(f"- 成功用户: {len(successful_users)}/{num_users}")
        print(f"- 失败用户: {len(failed_users)}")
        print(f"- 总操作数: {len(all_operations)}")
        print(f"- 总处理时间: {metrics['total_time']:.2f} 秒")
        print(f"- 平均操作时间: {statistics.mean(operation_times):.4f} 秒")
        print(f"- 操作吞吐量: {len(all_operations) / metrics['total_time']:.2f} 操作/秒")
        print(f"- 最大内存使用: {metrics['max_memory_usage']:.2f}%")
        print(f"- 最大CPU使用: {metrics['max_cpu_usage']:.2f}%")
        
        # 性能断言
        self.assertGreaterEqual(len(successful_users), num_users * 0.9, "成功率应大于90%")
        self.assertLess(statistics.mean(operation_times), 1.0, "平均操作时间应小于1秒")
        
        print("✅ 并发用户访问负载测试通过！")


class LargeFileProcessingTests(PerformanceTestBase):
    """大文件处理性能测试"""
    
    def test_large_file_upload_performance(self):
        """测试大文件上传性能"""
        print("\n🧪 测试大文件上传性能...")
        
        # 创建不同大小的测试文件
        file_sizes = [1, 5, 10, 20]  # MB
        test_files = {}
        
        print("1. 创建测试文件...")
        for size in file_sizes:
            file_path = self.create_large_test_file(size)
            test_files[size] = file_path
            print(f"✅ 创建 {size}MB 测试文件")
        
        # 创建作业
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="大文件上传测试作业",
            description="用于测试大文件上传性能"
        )
        
        # 创建测试用户
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name)
            VALUES ('file_test_user', 'hash', 'student', '文件测试用户')
        ''')
        conn.commit()
        conn.close()
        
        # 测试不同大小文件的上传性能
        upload_results = {}
        
        print("2. 测试文件上传性能...")
        for size, file_path in test_files.items():
            print(f"测试 {size}MB 文件上传...")
            
            self.start_performance_monitoring()
            start_time = time.time()
            
            # 模拟文件上传（实际上是文件路径关联）
            success = self.submission_service.submit_assignment(
                assignment_id=assignment_id,
                student_username='file_test_user',
                answer_files=[file_path]
            )
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            metrics = self.stop_performance_monitoring()
            
            upload_results[size] = {
                'success': success,
                'upload_time': upload_time,
                'file_size_mb': size,
                'upload_speed_mbps': size / upload_time if upload_time > 0 else 0,
                'memory_usage': metrics['max_memory_usage']
            }
            
            print(f"✅ {size}MB 文件上传完成，耗时: {upload_time:.2f}秒")
            
            # 清理提交记录以便下次测试
            submission = self.submission_service.get_submission(assignment_id, 'file_test_user')
            if submission:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM submissions WHERE id = ?', (submission.id,))
                conn.commit()
                conn.close()
        
        # 分析结果
        print(f"\n📊 大文件上传性能测试结果:")
        for size, result in upload_results.items():
            print(f"- {size}MB 文件:")
            print(f"  上传时间: {result['upload_time']:.2f} 秒")
            print(f"  上传速度: {result['upload_speed_mbps']:.2f} MB/秒")
            print(f"  内存使用: {result['memory_usage']:.2f}%")
        
        # 性能断言
        for size, result in upload_results.items():
            self.assertTrue(result['success'], f"{size}MB文件上传应该成功")
            self.assertLess(result['upload_time'], size * 2, f"{size}MB文件上传时间应小于{size * 2}秒")
        
        print("✅ 大文件上传性能测试通过！")
    
    def test_large_file_processing_performance(self):
        """测试大文件处理性能"""
        print("\n🧪 测试大文件处理性能...")
        
        # 创建大文件
        large_file = self.create_large_test_file(10)  # 10MB文件
        
        # 创建作业和提交
        assignment_id = self.assignment_service.create_assignment(
            class_id=1,
            title="大文件处理测试",
            description="测试大文件处理性能",
            question_files=[large_file],
            marking_files=[large_file]
        )
        
        # 创建用户
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name)
            VALUES ('processing_user', 'hash', 'student', '处理测试用户')
        ''')
        conn.commit()
        conn.close()
        
        # 提交大文件
        self.submission_service.submit_assignment(
            assignment_id=assignment_id,
            student_username='processing_user',
            answer_files=[large_file]
        )
        
        submission = self.submission_service.get_submission(assignment_id, 'processing_user')
        
        # 测试批改处理性能
        print("开始大文件批改处理...")
        self.start_performance_monitoring()
        
        start_time = time.time()
        
        # 模拟批改处理
        result = self.classroom_grading_service.apply_grading_standards(
            answer_files=[large_file],
            marking_files=[large_file],
            grading_config=None
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        metrics = self.stop_performance_monitoring()
        
        print(f"\n📊 大文件处理性能测试结果:")
        print(f"- 文件大小: 10MB")
        print(f"- 处理时间: {processing_time:.2f} 秒")
        print(f"- 处理速度: {10 / processing_time:.2f} MB/秒")
        print(f"- 最大内存使用: {metrics['max_memory_usage']:.2f}%")
        print(f"- 最大CPU使用: {metrics['max_cpu_usage']:.2f}%")
        
        # 性能断言
        self.assertIsNotNone(result)
        self.assertIn('score', result)
        self.assertLess(processing_time, 30, "10MB文件处理时间应小于30秒")
        self.assertLess(metrics['max_memory_usage'], 90, "内存使用应小于90%")
        
        print("✅ 大文件处理性能测试通过！")


class DatabasePerformanceTests(PerformanceTestBase):
    """数据库查询性能测试"""
    
    def test_database_query_performance(self):
        """测试数据库查询性能"""
        print("\n🧪 测试数据库查询性能...")
        
        # 创建大量测试数据
        num_users = 1000
        num_assignments = 100
        num_submissions = 5000
        
        print(f"1. 创建 {num_users} 个用户...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 批量插入用户
        users_data = [
            (f'perf_user{i}', f'hash{i}', 'student', f'性能用户{i}')
            for i in range(1, num_users + 1)
        ]
        cursor.executemany('''
            INSERT INTO users (username, password_hash, role, real_name)
            VALUES (?, ?, ?, ?)
        ''', users_data)
        
        print(f"2. 创建 {num_assignments} 个作业...")
        # 批量插入作业
        assignments_data = [
            (1, f'性能测试作业{i}', f'第{i}个性能测试作业', '[]', '[]', 1)
            for i in range(1, num_assignments + 1)
        ]
        cursor.executemany('''
            INSERT INTO assignments (class_id, title, description, question_files, marking_files, auto_grading_enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', assignments_data)
        
        print(f"3. 创建 {num_submissions} 个提交...")
        # 批量插入提交
        submissions_data = []
        for i in range(1, num_submissions + 1):
            assignment_id = random.randint(1, num_assignments)
            user_id = random.randint(1, num_users)
            status = random.choice(['submitted', 'ai_graded', 'teacher_reviewed'])
            score = random.uniform(60, 100) if status != 'submitted' else None
            
            submissions_data.append((
                assignment_id, f'perf_user{user_id}', '["answer.txt"]',
                f'AI批改结果{i}' if status != 'submitted' else None,
                f'教师反馈{i}' if status == 'teacher_reviewed' else None,
                status, score
            ))
        
        cursor.executemany('''
            INSERT INTO submissions (assignment_id, student_username, answer_files, ai_result, teacher_feedback, status, score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', submissions_data)
        
        conn.commit()
        conn.close()
        
        print("4. 测试各种查询性能...")
        
        # 测试不同类型的查询
        query_tests = [
            {
                'name': '获取班级作业列表',
                'method': lambda: self.assignment_service.get_class_assignments(1),
                'expected_min_count': 1
            },
            {
                'name': '获取学生作业列表',
                'method': lambda: self.assignment_service.get_student_assignments('perf_user1'),
                'expected_min_count': 0
            },
            {
                'name': '获取作业统计',
                'method': lambda: self.assignment_service.get_assignment_statistics(1),
                'expected_keys': ['total_submissions', 'average_score']
            },
            {
                'name': '获取作业所有提交',
                'method': lambda: self.submission_service.get_assignment_submissions(1),
                'expected_min_count': 0
            },
            {
                'name': '获取学生提交历史',
                'method': lambda: self.submission_service.get_submission_history('perf_user1'),
                'expected_min_count': 0
            },
            {
                'name': '搜索作业',
                'method': lambda: self.assignment_service.search_assignments(keyword='性能'),
                'expected_min_count': 1
            }
        ]
        
        query_results = {}
        
        for test in query_tests:
            print(f"测试查询: {test['name']}")
            
            # 预热查询
            test['method']()
            
            # 正式测试
            query_times = []
            for _ in range(10):  # 每个查询测试10次
                start_time = time.time()
                result = test['method']()
                end_time = time.time()
                query_times.append(end_time - start_time)
                
                # 验证结果
                if 'expected_min_count' in test:
                    self.assertGreaterEqual(len(result), test['expected_min_count'])
                elif 'expected_keys' in test:
                    for key in test['expected_keys']:
                        self.assertIn(key, result)
            
            query_results[test['name']] = {
                'avg_time': statistics.mean(query_times),
                'max_time': max(query_times),
                'min_time': min(query_times),
                'times': query_times
            }
        
        # 分析结果
        print(f"\n📊 数据库查询性能测试结果:")
        for query_name, result in query_results.items():
            print(f"- {query_name}:")
            print(f"  平均时间: {result['avg_time']:.4f} 秒")
            print(f"  最大时间: {result['max_time']:.4f} 秒")
            print(f"  最小时间: {result['min_time']:.4f} 秒")
        
        # 性能断言
        for query_name, result in query_results.items():
            self.assertLess(result['avg_time'], 1.0, f"{query_name}平均查询时间应小于1秒")
            self.assertLess(result['max_time'], 2.0, f"{query_name}最大查询时间应小于2秒")
        
        print("✅ 数据库查询性能测试通过！")
    
    def test_database_concurrent_access_performance(self):
        """测试数据库并发访问性能"""
        print("\n🧪 测试数据库并发访问性能...")
        
        # 创建基础测试数据
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建一些基础数据
        for i in range(1, 101):
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, real_name)
                VALUES (?, ?, ?, ?)
            ''', (f'concurrent_user{i}', f'hash{i}', 'student', f'并发用户{i}'))
        
        for i in range(1, 21):
            cursor.execute('''
                INSERT INTO assignments (class_id, title, description, question_files, marking_files, auto_grading_enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (1, f'并发测试作业{i}', f'第{i}个并发测试作业', '[]', '[]', 1))
        
        conn.commit()
        conn.close()
        
        # 并发访问函数
        def concurrent_database_operations(thread_id):
            """并发数据库操作"""
            operations = []
            
            try:
                for i in range(10):  # 每个线程执行10次操作
                    # 随机选择操作类型
                    operation_type = random.choice([
                        'get_assignments',
                        'get_assignment_detail',
                        'submit_assignment',
                        'get_submission'
                    ])
                    
                    start_time = time.time()
                    
                    if operation_type == 'get_assignments':
                        result = self.assignment_service.get_class_assignments(1)
                    elif operation_type == 'get_assignment_detail':
                        assignment_id = random.randint(1, 20)
                        result = self.assignment_service.get_assignment_by_id(assignment_id)
                    elif operation_type == 'submit_assignment':
                        assignment_id = random.randint(1, 20)
                        username = f'concurrent_user{random.randint(1, 100)}'
                        result = self.submission_service.submit_assignment(
                            assignment_id, username, [f'answer_{thread_id}_{i}.txt']
                        )
                    elif operation_type == 'get_submission':
                        assignment_id = random.randint(1, 20)
                        username = f'concurrent_user{random.randint(1, 100)}'
                        result = self.submission_service.get_submission(assignment_id, username)
                    
                    end_time = time.time()
                    operations.append({
                        'type': operation_type,
                        'time': end_time - start_time,
                        'success': result is not None
                    })
                
                return {
                    'thread_id': thread_id,
                    'success': True,
                    'operations': operations
                }
                
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'success': False,
                    'error': str(e),
                    'operations': operations
                }
        
        # 开始并发测试
        num_threads = 20
        print(f"开始 {num_threads} 个线程的并发数据库访问...")
        
        self.start_performance_monitoring()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(concurrent_database_operations, i) 
                for i in range(1, num_threads + 1)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # 记录操作时间
                for op in result.get('operations', []):
                    self.record_performance_metric(op['time'])
        
        metrics = self.stop_performance_monitoring()
        
        # 分析结果
        successful_threads = [r for r in results if r['success']]
        all_operations = []
        for result in successful_threads:
            all_operations.extend(result['operations'])
        
        operation_times = [op['time'] for op in all_operations]
        successful_operations = [op for op in all_operations if op['success']]
        
        print(f"\n📊 数据库并发访问性能测试结果:")
        print(f"- 成功线程: {len(successful_threads)}/{num_threads}")
        print(f"- 总操作数: {len(all_operations)}")
        print(f"- 成功操作: {len(successful_operations)}")
        print(f"- 成功率: {len(successful_operations) / len(all_operations) * 100:.2f}%")
        print(f"- 总处理时间: {metrics['total_time']:.2f} 秒")
        print(f"- 平均操作时间: {statistics.mean(operation_times):.4f} 秒")
        print(f"- 操作吞吐量: {len(all_operations) / metrics['total_time']:.2f} 操作/秒")
        print(f"- 最大内存使用: {metrics['max_memory_usage']:.2f}%")
        
        # 性能断言
        self.assertGreaterEqual(len(successful_threads), num_threads * 0.9, "成功线程应大于90%")
        self.assertGreaterEqual(len(successful_operations) / len(all_operations), 0.95, "操作成功率应大于95%")
        self.assertLess(statistics.mean(operation_times), 0.5, "平均操作时间应小于0.5秒")
        
        print("✅ 数据库并发访问性能测试通过！")


def run_performance_tests():
    """运行性能测试套件"""
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        BatchGradingPerformanceTests,
        LoadTests,
        LargeFileProcessingTests,
        DatabasePerformanceTests
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
    print(f"性能和负载测试结果:")
    print(f"总测试数: {total_tests}")
    print(f"成功: {total_tests - failures - errors}")
    print(f"失败: {failures}")
    print(f"错误: {errors}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"{'='*60}")
    
    return success_rate >= 70.0


if __name__ == '__main__':
    success = run_performance_tests()
    sys.exit(0 if success else 1)