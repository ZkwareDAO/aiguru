#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计日志服务
实现操作审计日志记录和数据访问监控
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import hashlib
import sqlite3
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型"""
    # 用户操作
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    
    # 作业操作
    ASSIGNMENT_CREATE = "assignment_create"
    ASSIGNMENT_VIEW = "assignment_view"
    ASSIGNMENT_EDIT = "assignment_edit"
    ASSIGNMENT_DELETE = "assignment_delete"
    
    # 提交操作
    SUBMISSION_CREATE = "submission_create"
    SUBMISSION_VIEW = "submission_view"
    SUBMISSION_EDIT = "submission_edit"
    SUBMISSION_DELETE = "submission_delete"
    
    # 批改操作
    GRADING_START = "grading_start"
    GRADING_COMPLETE = "grading_complete"
    GRADING_MODIFY = "grading_modify"
    GRADING_VIEW = "grading_view"
    
    # 班级操作
    CLASS_CREATE = "class_create"
    CLASS_JOIN = "class_join"
    CLASS_LEAVE = "class_leave"
    CLASS_DELETE = "class_delete"
    
    # 文件操作
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    
    # 权限操作
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # 系统操作
    SYSTEM_ERROR = "system_error"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditLevel(Enum):
    """审计级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    id: Optional[int] = None
    event_type: AuditEventType = AuditEventType.USER_LOGIN
    level: AuditLevel = AuditLevel.INFO
    user_id: str = ""
    user_role: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str = ""
    description: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'level': self.level.value,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'additional_data': self.additional_data,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """从字典创建"""
        return cls(
            id=data.get('id'),
            event_type=AuditEventType(data.get('event_type', 'user_login')),
            level=AuditLevel(data.get('level', 'info')),
            user_id=data.get('user_id', ''),
            user_role=data.get('user_role', ''),
            resource_type=data.get('resource_type'),
            resource_id=data.get('resource_id'),
            action=data.get('action', ''),
            description=data.get('description', ''),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            session_id=data.get('session_id'),
            additional_data=data.get('additional_data', {}),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
        )


class DataAccessMonitor:
    """数据访问监控器"""
    
    def __init__(self):
        self.suspicious_patterns = {
            'rapid_access': {'threshold': 100, 'window': 60},  # 60秒内超过100次访问
            'unusual_hours': {'start': 2, 'end': 6},  # 凌晨2-6点访问
            'bulk_download': {'threshold': 50},  # 一次下载超过50个文件
            'failed_attempts': {'threshold': 10, 'window': 300},  # 5分钟内超过10次失败尝试
        }
    
    def detect_suspicious_activity(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        alerts = []
        
        # 检测快速访问
        alerts.extend(self._detect_rapid_access(events))
        
        # 检测异常时间访问
        alerts.extend(self._detect_unusual_hours(events))
        
        # 检测批量下载
        alerts.extend(self._detect_bulk_download(events))
        
        # 检测失败尝试
        alerts.extend(self._detect_failed_attempts(events))
        
        return alerts
    
    def _detect_rapid_access(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """检测快速访问"""
        alerts = []
        user_access_count = {}
        
        # 统计每个用户在时间窗口内的访问次数
        for event in events:
            if event.timestamp >= datetime.now() - timedelta(seconds=self.suspicious_patterns['rapid_access']['window']):
                user_id = event.user_id
                user_access_count[user_id] = user_access_count.get(user_id, 0) + 1
        
        # 检查是否超过阈值
        for user_id, count in user_access_count.items():
            if count > self.suspicious_patterns['rapid_access']['threshold']:
                alerts.append({
                    'type': 'rapid_access',
                    'user_id': user_id,
                    'count': count,
                    'threshold': self.suspicious_patterns['rapid_access']['threshold'],
                    'description': f"用户 {user_id} 在短时间内进行了 {count} 次访问"
                })
        
        return alerts
    
    def _detect_unusual_hours(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """检测异常时间访问"""
        alerts = []
        unusual_start = self.suspicious_patterns['unusual_hours']['start']
        unusual_end = self.suspicious_patterns['unusual_hours']['end']
        
        for event in events:
            hour = event.timestamp.hour
            if unusual_start <= hour <= unusual_end:
                alerts.append({
                    'type': 'unusual_hours',
                    'user_id': event.user_id,
                    'timestamp': event.timestamp.isoformat(),
                    'description': f"用户 {event.user_id} 在异常时间 {hour}:00 进行了访问"
                })
        
        return alerts
    
    def _detect_bulk_download(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """检测批量下载"""
        alerts = []
        download_events = [e for e in events if e.event_type == AuditEventType.FILE_DOWNLOAD]
        
        # 按用户和时间窗口统计下载次数
        user_downloads = {}
        for event in download_events:
            if event.timestamp >= datetime.now() - timedelta(minutes=10):  # 10分钟窗口
                user_id = event.user_id
                user_downloads[user_id] = user_downloads.get(user_id, 0) + 1
        
        for user_id, count in user_downloads.items():
            if count > self.suspicious_patterns['bulk_download']['threshold']:
                alerts.append({
                    'type': 'bulk_download',
                    'user_id': user_id,
                    'count': count,
                    'threshold': self.suspicious_patterns['bulk_download']['threshold'],
                    'description': f"用户 {user_id} 在短时间内下载了 {count} 个文件"
                })
        
        return alerts
    
    def _detect_failed_attempts(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """检测失败尝试"""
        alerts = []
        failed_events = [e for e in events if e.event_type == AuditEventType.PERMISSION_DENIED or 
                        e.event_type == AuditEventType.UNAUTHORIZED_ACCESS]
        
        # 按用户统计失败次数
        user_failures = {}
        for event in failed_events:
            if event.timestamp >= datetime.now() - timedelta(seconds=self.suspicious_patterns['failed_attempts']['window']):
                user_id = event.user_id
                user_failures[user_id] = user_failures.get(user_id, 0) + 1
        
        for user_id, count in user_failures.items():
            if count > self.suspicious_patterns['failed_attempts']['threshold']:
                alerts.append({
                    'type': 'failed_attempts',
                    'user_id': user_id,
                    'count': count,
                    'threshold': self.suspicious_patterns['failed_attempts']['threshold'],
                    'description': f"用户 {user_id} 在短时间内有 {count} 次失败尝试"
                })
        
        return alerts


class AuditService:
    """审计服务"""
    
    def __init__(self, db_path: str = "audit.db"):
        self.db_path = Path(db_path)
        self.monitor = DataAccessMonitor()
        self._init_database()
    
    def _init_database(self):
        """初始化审计数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_role TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    action TEXT,
                    description TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT,
                    additional_data TEXT,  -- JSON格式
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id)')
            
            conn.commit()
            logger.info("审计数据库初始化成功")
            
        except Exception as e:
            logger.error(f"审计数据库初始化失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def log_event(self, event: AuditEvent) -> bool:
        """记录审计事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_logs (
                    event_type, level, user_id, user_role, resource_type, resource_id,
                    action, description, ip_address, user_agent, session_id, additional_data, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_type.value,
                event.level.value,
                event.user_id,
                event.user_role,
                event.resource_type,
                event.resource_id,
                event.action,
                event.description,
                event.ip_address,
                event.user_agent,
                event.session_id,
                json.dumps(event.additional_data),
                event.timestamp.isoformat()
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"记录审计事件失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_events(self, user_id: Optional[str] = None, event_type: Optional[AuditEventType] = None,
                   start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                   limit: int = 100) -> List[AuditEvent]:
        """获取审计事件"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event_data = dict(row)
                event_data['additional_data'] = json.loads(event_data.get('additional_data', '{}'))
                events.append(AuditEvent.from_dict(event_data))
            
            return events
            
        except Exception as e:
            logger.error(f"获取审计事件失败: {e}")
            return []
        finally:
            conn.close()
    
    def log_user_login(self, user_id: str, user_role: str, ip_address: str = None, 
                      user_agent: str = None, session_id: str = None):
        """记录用户登录"""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGIN,
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            action="login",
            description=f"用户 {user_id} 登录系统",
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        self.log_event(event)
    
    def log_user_logout(self, user_id: str, user_role: str, session_id: str = None):
        """记录用户登出"""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGOUT,
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            action="logout",
            description=f"用户 {user_id} 登出系统",
            session_id=session_id
        )
        self.log_event(event)
    
    def log_assignment_operation(self, user_id: str, user_role: str, assignment_id: str, 
                                action: str, description: str = None):
        """记录作业操作"""
        event_type_map = {
            'create': AuditEventType.ASSIGNMENT_CREATE,
            'view': AuditEventType.ASSIGNMENT_VIEW,
            'edit': AuditEventType.ASSIGNMENT_EDIT,
            'delete': AuditEventType.ASSIGNMENT_DELETE
        }
        
        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.ASSIGNMENT_VIEW),
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            resource_type="assignment",
            resource_id=assignment_id,
            action=action,
            description=description or f"用户 {user_id} {action} 作业 {assignment_id}"
        )
        self.log_event(event)
    
    def log_submission_operation(self, user_id: str, user_role: str, submission_id: str, 
                                action: str, description: str = None):
        """记录提交操作"""
        event_type_map = {
            'create': AuditEventType.SUBMISSION_CREATE,
            'view': AuditEventType.SUBMISSION_VIEW,
            'edit': AuditEventType.SUBMISSION_EDIT,
            'delete': AuditEventType.SUBMISSION_DELETE
        }
        
        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.SUBMISSION_VIEW),
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            resource_type="submission",
            resource_id=submission_id,
            action=action,
            description=description or f"用户 {user_id} {action} 提交 {submission_id}"
        )
        self.log_event(event)
    
    def log_grading_operation(self, user_id: str, user_role: str, submission_id: str, 
                             action: str, description: str = None, additional_data: Dict = None):
        """记录批改操作"""
        event_type_map = {
            'start': AuditEventType.GRADING_START,
            'complete': AuditEventType.GRADING_COMPLETE,
            'modify': AuditEventType.GRADING_MODIFY,
            'view': AuditEventType.GRADING_VIEW
        }
        
        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.GRADING_VIEW),
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            resource_type="grading",
            resource_id=submission_id,
            action=action,
            description=description or f"用户 {user_id} {action} 批改 {submission_id}",
            additional_data=additional_data or {}
        )
        self.log_event(event)
    
    def log_permission_denied(self, user_id: str, user_role: str, resource_type: str, 
                             resource_id: str, action: str, reason: str = None):
        """记录权限拒绝"""
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_DENIED,
            level=AuditLevel.WARNING,
            user_id=user_id,
            user_role=user_role,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            description=f"用户 {user_id} 尝试 {action} {resource_type} {resource_id} 被拒绝: {reason or '权限不足'}"
        )
        self.log_event(event)
    
    def log_file_operation(self, user_id: str, user_role: str, file_path: str, 
                          action: str, file_size: int = None):
        """记录文件操作"""
        event_type_map = {
            'upload': AuditEventType.FILE_UPLOAD,
            'download': AuditEventType.FILE_DOWNLOAD,
            'delete': AuditEventType.FILE_DELETE
        }
        
        additional_data = {}
        if file_size is not None:
            additional_data['file_size'] = file_size
        
        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.FILE_UPLOAD),
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            resource_type="file",
            resource_id=file_path,
            action=action,
            description=f"用户 {user_id} {action} 文件 {file_path}",
            additional_data=additional_data
        )
        self.log_event(event)
    
    def log_system_error(self, error_message: str, user_id: str = None, 
                        additional_data: Dict = None):
        """记录系统错误"""
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_ERROR,
            level=AuditLevel.ERROR,
            user_id=user_id or "system",
            user_role="system",
            action="error",
            description=f"系统错误: {error_message}",
            additional_data=additional_data or {}
        )
        self.log_event(event)
    
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户活动摘要"""
        start_time = datetime.now() - timedelta(days=days)
        events = self.get_events(user_id=user_id, start_time=start_time, limit=1000)
        
        summary = {
            'total_events': len(events),
            'event_types': {},
            'daily_activity': {},
            'resource_access': {},
            'recent_activities': []
        }
        
        for event in events:
            # 统计事件类型
            event_type = event.event_type.value
            summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
            
            # 统计每日活动
            date_key = event.timestamp.date().isoformat()
            summary['daily_activity'][date_key] = summary['daily_activity'].get(date_key, 0) + 1
            
            # 统计资源访问
            if event.resource_type:
                resource_key = f"{event.resource_type}:{event.resource_id}"
                summary['resource_access'][resource_key] = summary['resource_access'].get(resource_key, 0) + 1
        
        # 最近活动（最多10条）
        summary['recent_activities'] = [event.to_dict() for event in events[:10]]
        
        return summary
    
    def detect_suspicious_activities(self, hours: int = 24) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        start_time = datetime.now() - timedelta(hours=hours)
        events = self.get_events(start_time=start_time, limit=10000)
        
        return self.monitor.detect_suspicious_activity(events)
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM audit_logs WHERE timestamp < ?', (cutoff_date.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"清理了 {deleted_count} 条旧审计日志")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()


# 全局审计服务实例
audit_service = AuditService()