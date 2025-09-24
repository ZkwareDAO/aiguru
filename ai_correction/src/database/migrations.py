#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
用于扩展现有数据库表结构以支持班级作业批改功能
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DatabaseMigration:
    """数据库迁移管理器"""
    
    def __init__(self, db_path: str = "class_system.db"):
        self.db_path = Path(db_path)
        self.migration_history_table = "migration_history"
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_migration_history(self):
        """初始化迁移历史表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.migration_history_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rollback_sql TEXT,
                    description TEXT
                )
            ''')
            conn.commit()
        except Exception as e:
            print(f"初始化迁移历史表失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def is_migration_applied(self, migration_name: str) -> bool:
        """检查迁移是否已应用"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM {self.migration_history_table} 
                WHERE migration_name = ?
            ''', (migration_name,))
            result = cursor.fetchone()
            return result['count'] > 0
        except Exception:
            return False
        finally:
            conn.close()
    
    def record_migration(self, migration_name: str, rollback_sql: str = "", description: str = ""):
        """记录迁移历史"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
                INSERT INTO {self.migration_history_table} 
                (migration_name, rollback_sql, description)
                VALUES (?, ?, ?)
            ''', (migration_name, rollback_sql, description))
            conn.commit()
        except Exception as e:
            print(f"记录迁移历史失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def apply_migration(self, migration_name: str, migration_sql: str, 
                       rollback_sql: str = "", description: str = "") -> bool:
        """应用迁移"""
        if self.is_migration_applied(migration_name):
            print(f"迁移 {migration_name} 已经应用过，跳过")
            return True
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 执行迁移SQL
            for sql_statement in migration_sql.strip().split(';'):
                if sql_statement.strip():
                    cursor.execute(sql_statement.strip())
            
            conn.commit()
            
            # 记录迁移历史
            self.record_migration(migration_name, rollback_sql, description)
            
            print(f"迁移 {migration_name} 应用成功")
            return True
            
        except Exception as e:
            print(f"应用迁移 {migration_name} 失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def rollback_migration(self, migration_name: str) -> bool:
        """回滚迁移"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取回滚SQL
            cursor.execute(f'''
                SELECT rollback_sql FROM {self.migration_history_table} 
                WHERE migration_name = ?
            ''', (migration_name,))
            result = cursor.fetchone()
            
            if not result or not result['rollback_sql']:
                print(f"迁移 {migration_name} 没有回滚SQL")
                return False
            
            # 执行回滚SQL
            rollback_sql = result['rollback_sql']
            for sql_statement in rollback_sql.strip().split(';'):
                if sql_statement.strip():
                    cursor.execute(sql_statement.strip())
            
            # 删除迁移记录
            cursor.execute(f'''
                DELETE FROM {self.migration_history_table} 
                WHERE migration_name = ?
            ''', (migration_name,))
            
            conn.commit()
            print(f"迁移 {migration_name} 回滚成功")
            return True
            
        except Exception as e:
            print(f"回滚迁移 {migration_name} 失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_applied_migrations(self) -> List[Dict]:
        """获取已应用的迁移列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
                SELECT migration_name, applied_at, description 
                FROM {self.migration_history_table} 
                ORDER BY applied_at
            ''')
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()


def migrate_assignments_table():
    """迁移assignments表，添加新字段"""
    migration_name = "001_extend_assignments_table"
    
    migration_sql = '''
        ALTER TABLE assignments ADD COLUMN grading_config_id TEXT;
        ALTER TABLE assignments ADD COLUMN auto_grading_enabled BOOLEAN DEFAULT 1;
        ALTER TABLE assignments ADD COLUMN grading_template_id TEXT;
    '''
    
    rollback_sql = '''
        -- SQLite不支持DROP COLUMN，需要重建表
        CREATE TABLE assignments_backup AS SELECT 
            id, class_id, title, description, question_files, marking_files, 
            deadline, created_at, is_active 
        FROM assignments;
        
        DROP TABLE assignments;
        
        CREATE TABLE assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            question_files TEXT,
            marking_files TEXT,
            deadline TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        );
        
        INSERT INTO assignments SELECT * FROM assignments_backup;
        DROP TABLE assignments_backup;
    '''
    
    description = "扩展assignments表，添加grading_config_id、auto_grading_enabled、grading_template_id字段"
    
    return migration_name, migration_sql, rollback_sql, description


def migrate_submissions_table():
    """迁移submissions表，添加新字段"""
    migration_name = "002_extend_submissions_table"
    
    migration_sql = '''
        ALTER TABLE submissions ADD COLUMN task_id TEXT;
        ALTER TABLE submissions ADD COLUMN grading_details TEXT;
        ALTER TABLE submissions ADD COLUMN ai_confidence REAL;
        ALTER TABLE submissions ADD COLUMN manual_review_required BOOLEAN DEFAULT 0;
    '''
    
    rollback_sql = '''
        -- SQLite不支持DROP COLUMN，需要重建表
        CREATE TABLE submissions_backup AS SELECT 
            id, assignment_id, student_username, answer_files, ai_result, 
            teacher_feedback, status, score, submitted_at, graded_at, returned_at 
        FROM submissions;
        
        DROP TABLE submissions;
        
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_username TEXT NOT NULL,
            answer_files TEXT,
            ai_result TEXT,
            teacher_feedback TEXT,
            status TEXT DEFAULT 'submitted' CHECK (status IN ('submitted', 'ai_graded', 'teacher_reviewed', 'returned')),
            score REAL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            graded_at TIMESTAMP,
            returned_at TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES assignments (id),
            FOREIGN KEY (student_username) REFERENCES users (username),
            UNIQUE(assignment_id, student_username)
        );
        
        INSERT INTO submissions SELECT * FROM submissions_backup;
        DROP TABLE submissions_backup;
    '''
    
    description = "扩展submissions表，添加task_id、grading_details、ai_confidence、manual_review_required字段"
    
    return migration_name, migration_sql, rollback_sql, description


def create_grading_tasks_table():
    """创建grading_tasks表"""
    migration_name = "003_create_grading_tasks_table"
    
    migration_sql = '''
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
        );
        
        CREATE INDEX idx_grading_tasks_status ON grading_tasks(status);
        CREATE INDEX idx_grading_tasks_priority ON grading_tasks(priority, created_at);
        CREATE INDEX idx_grading_tasks_assignment ON grading_tasks(assignment_id);
        CREATE INDEX idx_grading_tasks_student ON grading_tasks(student_username);
    '''
    
    rollback_sql = '''
        DROP INDEX IF EXISTS idx_grading_tasks_status;
        DROP INDEX IF EXISTS idx_grading_tasks_priority;
        DROP INDEX IF EXISTS idx_grading_tasks_assignment;
        DROP INDEX IF EXISTS idx_grading_tasks_student;
        DROP TABLE IF EXISTS grading_tasks;
    '''
    
    description = "创建grading_tasks表用于跟踪批改任务状态"
    
    return migration_name, migration_sql, rollback_sql, description


def run_all_migrations(db_path: str = "class_system.db") -> bool:
    """运行所有迁移"""
    migrator = DatabaseMigration(db_path)
    
    # 初始化迁移历史表
    migrator.init_migration_history()
    
    # 定义所有迁移
    migrations = [
        migrate_assignments_table(),
        migrate_submissions_table(),
        create_grading_tasks_table()
    ]
    
    success_count = 0
    
    for migration_name, migration_sql, rollback_sql, description in migrations:
        if migrator.apply_migration(migration_name, migration_sql, rollback_sql, description):
            success_count += 1
        else:
            print(f"迁移失败，停止后续迁移")
            break
    
    print(f"成功应用 {success_count}/{len(migrations)} 个迁移")
    return success_count == len(migrations)


def rollback_all_migrations(db_path: str = "class_system.db") -> bool:
    """回滚所有迁移"""
    migrator = DatabaseMigration(db_path)
    
    # 获取已应用的迁移（按应用时间倒序）
    applied_migrations = migrator.get_applied_migrations()
    applied_migrations.reverse()
    
    success_count = 0
    
    for migration in applied_migrations:
        migration_name = migration['migration_name']
        if migrator.rollback_migration(migration_name):
            success_count += 1
        else:
            print(f"回滚迁移 {migration_name} 失败，停止后续回滚")
            break
    
    print(f"成功回滚 {success_count}/{len(applied_migrations)} 个迁移")
    return success_count == len(applied_migrations)


def check_migration_status(db_path: str = "class_system.db"):
    """检查迁移状态"""
    migrator = DatabaseMigration(db_path)
    
    try:
        applied_migrations = migrator.get_applied_migrations()
        
        if not applied_migrations:
            print("没有已应用的迁移")
            return
        
        print("已应用的迁移:")
        print("-" * 80)
        for migration in applied_migrations:
            print(f"名称: {migration['migration_name']}")
            print(f"应用时间: {migration['applied_at']}")
            print(f"描述: {migration['description']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"检查迁移状态失败: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python migrations.py [migrate|rollback|status] [db_path]")
        sys.exit(1)
    
    command = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "class_system.db"
    
    if command == "migrate":
        success = run_all_migrations(db_path)
        sys.exit(0 if success else 1)
    elif command == "rollback":
        success = rollback_all_migrations(db_path)
        sys.exit(0 if success else 1)
    elif command == "status":
        check_migration_status(db_path)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)