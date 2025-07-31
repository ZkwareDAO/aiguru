#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置设置
"""

import os
from dataclasses import dataclass
from typing import Optional
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
    logging: LoggingSettings = None
    
    def __post_init__(self):
        if self.ai is None:
            self.ai = AISettings()
        if self.task is None:
            self.task = TaskSettings()
        if self.logging is None:
            self.logging = LoggingSettings()
        
        # 从环境变量加载配置
        self.ai.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # 任务系统配置
        self.task.max_workers = int(os.getenv("TASK_MAX_WORKERS", "4"))
        self.task.db_path = os.getenv("TASK_DB_PATH", "tasks.db")
        
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