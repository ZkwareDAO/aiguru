#!/usr/bin/env python3
"""
创建管理员账号脚本
用于初始化系统管理员账号
"""

import os
import sys
import sqlite3
import hashlib
import argparse
import getpass
from datetime import datetime

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user(db_path: str, username: str, password: str, email: str, full_name: str = None):
    """创建管理员用户"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查用户表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if not cursor.fetchone():
            # 创建用户表
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT UNIQUE,
                    full_name TEXT,
                    role TEXT DEFAULT 'student',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            print("用户表已创建")
        
        # 检查用户是否已存在
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"用户 {username} 已存在")
            return False
        
        # 创建管理员用户
        password_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role)
            VALUES (?, ?, ?, ?, 'admin')
        """, (username, password_hash, email, full_name or username))
        
        conn.commit()
        conn.close()
        
        print(f"管理员用户 {username} 创建成功")
        return True
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='创建系统管理员账号')
    parser.add_argument('--db', default='class_system.db', help='数据库文件路径')
    parser.add_argument('--username', help='管理员用户名')
    parser.add_argument('--password', help='管理员密码')
    parser.add_argument('--email', help='管理员邮箱')
    parser.add_argument('--full-name', help='管理员姓名')
    parser.add_argument('--interactive', action='store_true', help='交互式输入')
    
    args = parser.parse_args()
    
    # 交互式输入
    if args.interactive or not all([args.username, args.password, args.email]):
        print("创建系统管理员账号")
        print("=" * 30)
        
        username = args.username or input("用户名: ")
        email = args.email or input("邮箱: ")
        full_name = args.full_name or input("姓名 (可选): ") or None
        
        if args.password:
            password = args.password
        else:
            password = getpass.getpass("密码: ")
            password_confirm = getpass.getpass("确认密码: ")
            
            if password != password_confirm:
                print("密码不匹配")
                return
    else:
        username = args.username
        password = args.password
        email = args.email
        full_name = args.full_name
    
    # 验证输入
    if not username or not password or not email:
        print("用户名、密码和邮箱不能为空")
        return
    
    if len(password) < 6:
        print("密码长度至少6位")
        return
    
    # 创建管理员用户
    success = create_admin_user(args.db, username, password, email, full_name)
    
    if success:
        print("\n管理员账号信息:")
        print(f"用户名: {username}")
        print(f"邮箱: {email}")
        print(f"角色: 管理员")
        print("\n请妥善保管账号信息！")

if __name__ == '__main__':
    main()