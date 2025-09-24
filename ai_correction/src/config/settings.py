#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置设置
"""

import os
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


@dataclass
class AISettings:
    """AI服务配置"""
    openrouter_api_key: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7


@dataclass
class TaskSettings:
    """任务系统配置"""
    max_workers: int = 4
    db_path: str = "tasks.db"
    max_retries: int = 3
    retry_delay_seconds: int = 30
    cleanup_interval_hours: int = 24
    task_timeout_hours: int = 2
    auto_cleanup_days: int = 7


@dataclass
class ClassroomSettings:
    """班级批改系统配置"""
    # 数据库配置
    db_path: str = "class_system.db"
    
    # 文件存储配置
    upload_base_dir: str = "uploads"
    max_file_size_mb: int = 100
    allowed_file_extensions: List[str] = None
    
    # 批改配置
    auto_grading_enabled: bool = True
    default_grading_template: str = "general"
    grading_timeout_minutes: int = 30
    ai_confidence_threshold: float = 0.8
    
    # 通知配置
    notification_enabled: bool = True
    email_notifications: bool = False
    websocket_notifications: bool = True
    
    # 安全配置
    file_scan_enabled: bool = True
    access_control_enabled: bool = True
    audit_logging_enabled: bool = True
    
    def __post_init__(self):
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = [
                '.pdf', '.doc', '.docx', '.txt', '.md', 
                '.jpg', '.jpeg', '.png', '.gif', '.json'
            ]


@dataclass
class LoggingSettings:
    """日志配置"""
    level: str = "INFO"
    file_path: Optional[Path] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    def __post_init__(self):
        if self.file_path is None:
            self.file_path = Path("logs") / "app.log"


@dataclass
class AppSettings:
    """应用设置"""
    app_name: str = "AI智能批改系统"
    app_version: str = "2.0.0"
    environment: str = "development"
    debug: bool = True
    
    # 子配置
    ai: AISettings = None
    task: TaskSettings = None
    classroom: ClassroomSettings = None
    logging: LoggingSettings = None
    
    def __post_init__(self):
        if self.ai is None:
            self.ai = AISettings()
        if self.task is None:
            self.task = TaskSettings()
        if self.classroom is None:
            self.classroom = ClassroomSettings()
        if self.logging is None:
            self.logging = LoggingSettings()
        
        # 从环境变量加载配置
        self.ai.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # 任务系统配置
        self.task.max_workers = int(os.getenv("TASK_MAX_WORKERS", "4"))
        self.task.db_path = os.getenv("TASK_DB_PATH", "tasks.db")
        
        # 班级批改系统配置
        self.classroom.db_path = os.getenv("CLASSROOM_DB_PATH", "class_system.db")
        self.classroom.upload_base_dir = os.getenv("UPLOAD_BASE_DIR", "uploads")
        self.classroom.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        self.classroom.auto_grading_enabled = os.getenv("AUTO_GRADING_ENABLED", "true").lower() == "true"
        self.classroom.default_grading_template = os.getenv("DEFAULT_GRADING_TEMPLATE", "general")
        self.classroom.grading_timeout_minutes = int(os.getenv("GRADING_TIMEOUT_MINUTES", "30"))
        self.classroom.ai_confidence_threshold = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.8"))
        self.classroom.notification_enabled = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"
        self.classroom.email_notifications = os.getenv("EMAIL_NOTIFICATIONS", "false").lower() == "true"
        self.classroom.websocket_notifications = os.getenv("WEBSOCKET_NOTIFICATIONS", "true").lower() == "true"
        self.classroom.file_scan_enabled = os.getenv("FILE_SCAN_ENABLED", "true").lower() == "true"
        self.classroom.access_control_enabled = os.getenv("ACCESS_CONTROL_ENABLED", "true").lower() == "true"
        self.classroom.audit_logging_enabled = os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true"
        
        # 日志配置
        self.logging.level = os.getenv("LOG_LEVEL", "INFO")
        if os.getenv("LOG_FILE"):
            self.logging.file_path = Path(os.getenv("LOG_FILE"))


# 全局设置实例
_settings = None


def get_settings() -> AppSettings:
    """获取应用设置"""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings