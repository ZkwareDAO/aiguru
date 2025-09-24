#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全配置管理
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PermissionConfig:
    """权限配置"""
    enable_role_based_access: bool = True
    enable_resource_level_permissions: bool = True
    default_session_timeout: int = 3600  # 秒
    max_failed_login_attempts: int = 5
    account_lockout_duration: int = 1800  # 秒
    require_password_change_days: int = 90
    min_password_length: int = 8
    require_strong_password: bool = True


@dataclass
class AuditConfig:
    """审计配置"""
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 90
    enable_real_time_monitoring: bool = True
    suspicious_activity_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        'rapid_access': {'threshold': 100, 'window_seconds': 60},
        'unusual_hours': {'start_hour': 2, 'end_hour': 6},
        'bulk_download': {'threshold': 50, 'window_minutes': 10},
        'failed_attempts': {'threshold': 10, 'window_seconds': 300}
    })
    alert_email_recipients: List[str] = field(default_factory=list)
    enable_security_alerts: bool = True


@dataclass
class EncryptionConfig:
    """加密配置"""
    enable_data_encryption: bool = True
    encryption_algorithm: str = "AES-256"
    key_rotation_days: int = 365
    encrypt_sensitive_fields: bool = True
    enable_file_encryption: bool = False
    hash_algorithm: str = "SHA-256"
    password_hash_iterations: int = 100000


@dataclass
class SecurityConfig:
    """安全配置"""
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    permission_config: PermissionConfig = field(default_factory=PermissionConfig)
    audit_config: AuditConfig = field(default_factory=AuditConfig)
    encryption_config: EncryptionConfig = field(default_factory=EncryptionConfig)
    
    # 文件上传安全配置
    max_file_size_mb: int = 50
    allowed_file_extensions: List[str] = field(default_factory=lambda: [
        '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif'
    ])
    enable_virus_scanning: bool = False
    quarantine_suspicious_files: bool = True
    
    # 网络安全配置
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 60
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    enable_csrf_protection: bool = True
    enable_xss_protection: bool = True
    
    # 数据保护配置
    enable_data_anonymization: bool = False
    data_retention_days: int = 2555  # 7年
    enable_gdpr_compliance: bool = True
    enable_data_backup_encryption: bool = True
    
    @classmethod
    def from_environment(cls) -> 'SecurityConfig':
        """从环境变量创建配置"""
        config = cls()
        
        # 安全级别
        security_level = os.getenv('SECURITY_LEVEL', 'medium').lower()
        if security_level in [level.value for level in SecurityLevel]:
            config.security_level = SecurityLevel(security_level)
        
        # 权限配置
        config.permission_config.enable_role_based_access = _get_bool_env(
            'ENABLE_ROLE_BASED_ACCESS', True
        )
        config.permission_config.default_session_timeout = _get_int_env(
            'SESSION_TIMEOUT', 3600
        )
        config.permission_config.max_failed_login_attempts = _get_int_env(
            'MAX_FAILED_LOGIN_ATTEMPTS', 5
        )
        config.permission_config.min_password_length = _get_int_env(
            'MIN_PASSWORD_LENGTH', 8
        )
        
        # 审计配置
        config.audit_config.enable_audit_logging = _get_bool_env(
            'ENABLE_AUDIT_LOGGING', True
        )
        config.audit_config.audit_log_retention_days = _get_int_env(
            'AUDIT_LOG_RETENTION_DAYS', 90
        )
        config.audit_config.enable_security_alerts = _get_bool_env(
            'ENABLE_SECURITY_ALERTS', True
        )
        
        # 加密配置
        config.encryption_config.enable_data_encryption = _get_bool_env(
            'ENABLE_DATA_ENCRYPTION', True
        )
        config.encryption_config.key_rotation_days = _get_int_env(
            'KEY_ROTATION_DAYS', 365
        )
        
        # 文件上传配置
        config.max_file_size_mb = _get_int_env('MAX_FILE_SIZE_MB', 50)
        config.enable_virus_scanning = _get_bool_env('ENABLE_VIRUS_SCANNING', False)
        
        # 网络安全配置
        config.enable_rate_limiting = _get_bool_env('ENABLE_RATE_LIMITING', True)
        config.rate_limit_requests_per_minute = _get_int_env(
            'RATE_LIMIT_REQUESTS_PER_MINUTE', 60
        )
        
        return config
    
    def apply_security_level(self):
        """根据安全级别调整配置"""
        if self.security_level == SecurityLevel.LOW:
            self._apply_low_security()
        elif self.security_level == SecurityLevel.MEDIUM:
            self._apply_medium_security()
        elif self.security_level == SecurityLevel.HIGH:
            self._apply_high_security()
        elif self.security_level == SecurityLevel.CRITICAL:
            self._apply_critical_security()
    
    def _apply_low_security(self):
        """应用低安全级别配置"""
        self.permission_config.max_failed_login_attempts = 10
        self.permission_config.min_password_length = 6
        self.permission_config.require_strong_password = False
        self.audit_config.enable_real_time_monitoring = False
        self.audit_config.suspicious_activity_thresholds['rapid_access']['threshold'] = 200
        self.enable_rate_limiting = False
    
    def _apply_medium_security(self):
        """应用中等安全级别配置"""
        # 使用默认配置
        pass
    
    def _apply_high_security(self):
        """应用高安全级别配置"""
        self.permission_config.max_failed_login_attempts = 3
        self.permission_config.min_password_length = 12
        self.permission_config.default_session_timeout = 1800  # 30分钟
        self.permission_config.require_password_change_days = 30
        self.audit_config.suspicious_activity_thresholds['rapid_access']['threshold'] = 50
        self.audit_config.suspicious_activity_thresholds['failed_attempts']['threshold'] = 5
        self.enable_virus_scanning = True
        self.rate_limit_requests_per_minute = 30
    
    def _apply_critical_security(self):
        """应用关键安全级别配置"""
        self.permission_config.max_failed_login_attempts = 2
        self.permission_config.min_password_length = 16
        self.permission_config.default_session_timeout = 900  # 15分钟
        self.permission_config.require_password_change_days = 15
        self.audit_config.suspicious_activity_thresholds['rapid_access']['threshold'] = 25
        self.audit_config.suspicious_activity_thresholds['failed_attempts']['threshold'] = 3
        self.encryption_config.enable_file_encryption = True
        self.encryption_config.key_rotation_days = 90
        self.enable_virus_scanning = True
        self.quarantine_suspicious_files = True
        self.enable_ip_whitelist = True
        self.rate_limit_requests_per_minute = 15
        self.enable_data_backup_encryption = True
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证权限配置
        if self.permission_config.min_password_length < 4:
            errors.append("最小密码长度不能少于4位")
        
        if self.permission_config.default_session_timeout < 300:
            errors.append("会话超时时间不能少于5分钟")
        
        if self.permission_config.max_failed_login_attempts < 1:
            errors.append("最大失败登录尝试次数必须大于0")
        
        # 验证审计配置
        if self.audit_config.audit_log_retention_days < 1:
            errors.append("审计日志保留天数必须大于0")
        
        # 验证文件上传配置
        if self.max_file_size_mb < 1:
            errors.append("最大文件大小必须大于1MB")
        
        if not self.allowed_file_extensions:
            errors.append("必须指定允许的文件扩展名")
        
        # 验证网络安全配置
        if self.rate_limit_requests_per_minute < 1:
            errors.append("速率限制必须大于每分钟1次请求")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'security_level': self.security_level.value,
            'permission_config': {
                'enable_role_based_access': self.permission_config.enable_role_based_access,
                'enable_resource_level_permissions': self.permission_config.enable_resource_level_permissions,
                'default_session_timeout': self.permission_config.default_session_timeout,
                'max_failed_login_attempts': self.permission_config.max_failed_login_attempts,
                'account_lockout_duration': self.permission_config.account_lockout_duration,
                'require_password_change_days': self.permission_config.require_password_change_days,
                'min_password_length': self.permission_config.min_password_length,
                'require_strong_password': self.permission_config.require_strong_password
            },
            'audit_config': {
                'enable_audit_logging': self.audit_config.enable_audit_logging,
                'audit_log_retention_days': self.audit_config.audit_log_retention_days,
                'enable_real_time_monitoring': self.audit_config.enable_real_time_monitoring,
                'suspicious_activity_thresholds': self.audit_config.suspicious_activity_thresholds,
                'alert_email_recipients': self.audit_config.alert_email_recipients,
                'enable_security_alerts': self.audit_config.enable_security_alerts
            },
            'encryption_config': {
                'enable_data_encryption': self.encryption_config.enable_data_encryption,
                'encryption_algorithm': self.encryption_config.encryption_algorithm,
                'key_rotation_days': self.encryption_config.key_rotation_days,
                'encrypt_sensitive_fields': self.encryption_config.encrypt_sensitive_fields,
                'enable_file_encryption': self.encryption_config.enable_file_encryption,
                'hash_algorithm': self.encryption_config.hash_algorithm,
                'password_hash_iterations': self.encryption_config.password_hash_iterations
            },
            'file_security': {
                'max_file_size_mb': self.max_file_size_mb,
                'allowed_file_extensions': self.allowed_file_extensions,
                'enable_virus_scanning': self.enable_virus_scanning,
                'quarantine_suspicious_files': self.quarantine_suspicious_files
            },
            'network_security': {
                'enable_rate_limiting': self.enable_rate_limiting,
                'rate_limit_requests_per_minute': self.rate_limit_requests_per_minute,
                'enable_ip_whitelist': self.enable_ip_whitelist,
                'ip_whitelist': self.ip_whitelist,
                'enable_csrf_protection': self.enable_csrf_protection,
                'enable_xss_protection': self.enable_xss_protection
            },
            'data_protection': {
                'enable_data_anonymization': self.enable_data_anonymization,
                'data_retention_days': self.data_retention_days,
                'enable_gdpr_compliance': self.enable_gdpr_compliance,
                'enable_data_backup_encryption': self.enable_data_backup_encryption
            }
        }


def _get_bool_env(key: str, default: bool) -> bool:
    """从环境变量获取布尔值"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def _get_int_env(key: str, default: int) -> int:
    """从环境变量获取整数值"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_list_env(key: str, default: List[str], separator: str = ',') -> List[str]:
    """从环境变量获取列表值"""
    value = os.getenv(key)
    if value:
        return [item.strip() for item in value.split(separator) if item.strip()]
    return default


class SecurityConfigManager:
    """安全配置管理器"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self._config = None
    
    def load_config(self) -> SecurityConfig:
        """加载配置"""
        if self._config is None:
            if self.config_file and os.path.exists(self.config_file):
                self._config = self._load_from_file()
            else:
                self._config = SecurityConfig.from_environment()
            
            # 应用安全级别配置
            self._config.apply_security_level()
            
            # 验证配置
            errors = self._config.validate()
            if errors:
                raise ValueError(f"安全配置验证失败: {'; '.join(errors)}")
        
        return self._config
    
    def _load_from_file(self) -> SecurityConfig:
        """从文件加载配置"""
        import json
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 这里可以实现从JSON配置文件创建SecurityConfig的逻辑
            # 为简化，暂时返回默认配置
            return SecurityConfig.from_environment()
            
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
    
    def save_config(self, config: SecurityConfig):
        """保存配置"""
        if not self.config_file:
            raise ValueError("未指定配置文件路径")
        
        import json
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._config = config
            
        except Exception as e:
            raise ValueError(f"保存配置文件失败: {e}")
    
    def get_config(self) -> SecurityConfig:
        """获取当前配置"""
        return self.load_config()
    
    def update_security_level(self, level: SecurityLevel):
        """更新安全级别"""
        config = self.load_config()
        config.security_level = level
        config.apply_security_level()
        
        if self.config_file:
            self.save_config(config)
        
        self._config = config
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        config = self.load_config()
        
        feature_map = {
            'role_based_access': config.permission_config.enable_role_based_access,
            'audit_logging': config.audit_config.enable_audit_logging,
            'data_encryption': config.encryption_config.enable_data_encryption,
            'real_time_monitoring': config.audit_config.enable_real_time_monitoring,
            'rate_limiting': config.enable_rate_limiting,
            'virus_scanning': config.enable_virus_scanning,
            'csrf_protection': config.enable_csrf_protection,
            'xss_protection': config.enable_xss_protection,
            'gdpr_compliance': config.enable_gdpr_compliance
        }
        
        return feature_map.get(feature, False)


# 全局配置管理器实例
security_config_manager = SecurityConfigManager()

# 便捷函数
def get_security_config() -> SecurityConfig:
    """获取安全配置"""
    return security_config_manager.get_config()

def is_security_feature_enabled(feature: str) -> bool:
    """检查安全功能是否启用"""
    return security_config_manager.is_feature_enabled(feature)