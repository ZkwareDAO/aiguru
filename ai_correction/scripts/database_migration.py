#!/usr/bin/env python3
"""
数据库迁移脚本
支持从现有系统平滑升级到班级作业批改系统
"""

import sqlite3
import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigration:
    def __init__(self, db_path: str = 'class_system.db'):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migrations = [
            self.migration_001_add_classroom_tables,
            self.migration_002_extend_assignments_table,
            self.migration_003_extend_submissions_table,
            self.migration_004_add_grading_tasks_table,
            self.migration_005_add_indexes,
            self.migration_006_add_audit_tables,
            self.migration_007_add_notification_tables,
        ]
    
    def backup_database(self) -> bool:
        """备份数据库"""
        try:
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, self.backup_path)
                logger.info(f"数据库已备份到: {self.backup_path}")
                return True
            else:
                logger.warning("数据库文件不存在，跳过备份")
                return True
        except Exception as e:
            logger.error(f"备份数据库失败: {e}")
            return False
    
    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查版本表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if cursor.fetchone():
                cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                result = cursor.fetchone()
                version = result[0] if result else 0
            else:
                # 创建版本表
                cursor.execute("""
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                conn.commit()
                version = 0
            
            conn.close()
            return version
        except Exception as e:
            logger.error(f"获取数据库版本失败: {e}")
            return 0
    
    def update_version(self, version: int, description: str):
        """更新数据库版本"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schema_version (version, description)
                VALUES (?, ?)
            """, (version, description))
            conn.commit()
            conn.close()
            logger.info(f"数据库版本更新到: {version}")
        except Exception as e:
            logger.error(f"更新数据库版本失败: {e}")
    
    def migration_001_add_classroom_tables(self):
        """迁移001: 添加班级相关表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建班级表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    class_code TEXT UNIQUE NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建班级成员表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS class_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    student_username TEXT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (class_id) REFERENCES classes (id),
                    UNIQUE(class_id, student_username)
                )
            """)
            
            conn.commit()
            logger.info("迁移001完成: 班级相关表已创建")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移001失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_002_extend_assignments_table(self):
        """迁移002: 扩展作业表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='assignments'
            """)
            
            if not cursor.fetchone():
                # 创建作业表
                cursor.execute("""
                    CREATE TABLE assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        class_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        question_files TEXT,  -- JSON格式存储文件列表
                        marking_files TEXT,   -- JSON格式存储批改标准文件
                        grading_config_id TEXT,
                        auto_grading_enabled BOOLEAN DEFAULT 1,
                        grading_template_id TEXT,
                        deadline TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (class_id) REFERENCES classes (id)
                    )
                """)
            else:
                # 添加新字段（如果不存在）
                new_columns = [
                    ('grading_config_id', 'TEXT'),
                    ('auto_grading_enabled', 'BOOLEAN DEFAULT 1'),
                    ('grading_template_id', 'TEXT'),
                    ('question_files', 'TEXT'),
                    ('marking_files', 'TEXT')
                ]
                
                for column_name, column_type in new_columns:
                    try:
                        cursor.execute(f"ALTER TABLE assignments ADD COLUMN {column_name} {column_type}")
                        logger.info(f"添加字段: assignments.{column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            logger.info(f"字段已存在: assignments.{column_name}")
                        else:
                            raise
            
            conn.commit()
            logger.info("迁移002完成: 作业表已扩展")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移002失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_003_extend_submissions_table(self):
        """迁移003: 扩展提交表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='submissions'
            """)
            
            if not cursor.fetchone():
                # 创建提交表
                cursor.execute("""
                    CREATE TABLE submissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        assignment_id INTEGER NOT NULL,
                        student_username TEXT NOT NULL,
                        answer_files TEXT,  -- JSON格式存储答案文件列表
                        ai_result TEXT,     -- JSON格式存储AI批改结果
                        teacher_feedback TEXT,
                        status TEXT DEFAULT 'submitted',
                        score REAL,
                        task_id TEXT,
                        grading_details TEXT,  -- JSON格式存储详细批改信息
                        ai_confidence REAL,
                        manual_review_required BOOLEAN DEFAULT 0,
                        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        graded_at TIMESTAMP,
                        returned_at TIMESTAMP,
                        FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                        UNIQUE(assignment_id, student_username)
                    )
                """)
            else:
                # 添加新字段
                new_columns = [
                    ('task_id', 'TEXT'),
                    ('grading_details', 'TEXT'),
                    ('ai_confidence', 'REAL'),
                    ('manual_review_required', 'BOOLEAN DEFAULT 0'),
                    ('answer_files', 'TEXT'),
                    ('ai_result', 'TEXT')
                ]
                
                for column_name, column_type in new_columns:
                    try:
                        cursor.execute(f"ALTER TABLE submissions ADD COLUMN {column_name} {column_type}")
                        logger.info(f"添加字段: submissions.{column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            logger.info(f"字段已存在: submissions.{column_name}")
                        else:
                            raise
            
            conn.commit()
            logger.info("迁移003完成: 提交表已扩展")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移003失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_004_add_grading_tasks_table(self):
        """迁移004: 添加批改任务表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grading_tasks (
                    id TEXT PRIMARY KEY,
                    submission_id INTEGER NOT NULL,
                    assignment_id INTEGER NOT NULL,
                    student_username TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 1,
                    grading_config TEXT,  -- JSON格式存储批改配置
                    progress INTEGER DEFAULT 0,
                    result TEXT,  -- JSON格式存储批改结果
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (submission_id) REFERENCES submissions (id),
                    FOREIGN KEY (assignment_id) REFERENCES assignments (id)
                )
            """)
            
            conn.commit()
            logger.info("迁移004完成: 批改任务表已创建")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移004失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_005_add_indexes(self):
        """迁移005: 添加索引优化查询性能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            indexes = [
                # 班级相关索引
                "CREATE INDEX IF NOT EXISTS idx_classes_teacher_id ON classes(teacher_id)",
                "CREATE INDEX IF NOT EXISTS idx_classes_code ON classes(class_code)",
                "CREATE INDEX IF NOT EXISTS idx_class_members_class_id ON class_members(class_id)",
                "CREATE INDEX IF NOT EXISTS idx_class_members_student ON class_members(student_username)",
                
                # 作业相关索引
                "CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id)",
                "CREATE INDEX IF NOT EXISTS idx_assignments_deadline ON assignments(deadline)",
                "CREATE INDEX IF NOT EXISTS idx_assignments_active ON assignments(is_active)",
                
                # 提交相关索引
                "CREATE INDEX IF NOT EXISTS idx_submissions_assignment_id ON submissions(assignment_id)",
                "CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_username)",
                "CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status)",
                "CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at)",
                
                # 批改任务索引
                "CREATE INDEX IF NOT EXISTS idx_grading_tasks_status ON grading_tasks(status)",
                "CREATE INDEX IF NOT EXISTS idx_grading_tasks_created_at ON grading_tasks(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_grading_tasks_assignment ON grading_tasks(assignment_id)",
                
                # 复合索引
                "CREATE INDEX IF NOT EXISTS idx_submissions_assignment_student ON submissions(assignment_id, student_username)",
                "CREATE INDEX IF NOT EXISTS idx_assignments_class_active ON assignments(class_id, is_active)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                logger.info(f"创建索引: {index_sql.split('ON')[1].split('(')[0].strip()}")
            
            conn.commit()
            logger.info("迁移005完成: 索引已创建")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移005失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_006_add_audit_tables(self):
        """迁移006: 添加审计日志表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,  -- JSON格式存储详细信息
                    success BOOLEAN DEFAULT 1
                )
            """)
            
            # 审计日志索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)")
            
            conn.commit()
            logger.info("迁移006完成: 审计日志表已创建")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移006失败: {e}")
            raise
        finally:
            conn.close()
    
    def migration_007_add_notification_tables(self):
        """迁移007: 添加通知表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,  -- JSON格式存储额外数据
                    is_read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP
                )
            """)
            
            # 通知索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)")
            
            conn.commit()
            logger.info("迁移007完成: 通知表已创建")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"迁移007失败: {e}")
            raise
        finally:
            conn.close()
    
    def run_migrations(self) -> bool:
        """运行所有待执行的迁移"""
        try:
            # 备份数据库
            if not self.backup_database():
                return False
            
            # 获取当前版本
            current_version = self.get_current_version()
            logger.info(f"当前数据库版本: {current_version}")
            
            # 执行迁移
            for i, migration in enumerate(self.migrations, 1):
                if i > current_version:
                    logger.info(f"执行迁移 {i:03d}: {migration.__name__}")
                    migration()
                    self.update_version(i, migration.__doc__ or migration.__name__)
                else:
                    logger.info(f"跳过迁移 {i:03d}: 已执行")
            
            logger.info("所有迁移执行完成")
            return True
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            logger.info(f"可以从备份恢复: {self.backup_path}")
            return False
    
    def rollback_to_version(self, target_version: int) -> bool:
        """回滚到指定版本（从备份恢复）"""
        try:
            if os.path.exists(self.backup_path):
                shutil.copy2(self.backup_path, self.db_path)
                logger.info(f"已从备份恢复数据库: {self.backup_path}")
                return True
            else:
                logger.error("备份文件不存在，无法回滚")
                return False
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """验证迁移结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查关键表是否存在
            required_tables = [
                'classes', 'class_members', 'assignments', 'submissions',
                'grading_tasks', 'audit_logs', 'notifications', 'schema_version'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = set(required_tables) - set(existing_tables)
            if missing_tables:
                logger.error(f"缺少表: {missing_tables}")
                return False
            
            # 检查关键字段
            cursor.execute("PRAGMA table_info(assignments)")
            assignment_columns = [row[1] for row in cursor.fetchall()]
            required_assignment_columns = ['grading_config_id', 'auto_grading_enabled']
            
            missing_columns = set(required_assignment_columns) - set(assignment_columns)
            if missing_columns:
                logger.error(f"assignments表缺少字段: {missing_columns}")
                return False
            
            conn.close()
            logger.info("迁移验证通过")
            return True
            
        except Exception as e:
            logger.error(f"迁移验证失败: {e}")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--db', default='class_system.db', help='数据库文件路径')
    parser.add_argument('--verify', action='store_true', help='仅验证迁移结果')
    parser.add_argument('--rollback', help='回滚到指定备份文件')
    
    args = parser.parse_args()
    
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    migration = DatabaseMigration(args.db)
    
    if args.rollback:
        # 回滚操作
        migration.backup_path = args.rollback
        if migration.rollback_to_version(0):
            logger.info("回滚成功")
        else:
            logger.error("回滚失败")
            exit(1)
    elif args.verify:
        # 验证操作
        if migration.verify_migration():
            logger.info("验证成功")
        else:
            logger.error("验证失败")
            exit(1)
    else:
        # 执行迁移
        if migration.run_migrations():
            if migration.verify_migration():
                logger.info("迁移和验证都成功完成")
            else:
                logger.error("迁移完成但验证失败")
                exit(1)
        else:
            logger.error("迁移失败")
            exit(1)

if __name__ == '__main__':
    main()