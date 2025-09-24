#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件安全和验证模块
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

# 尝试导入python-magic，如果不可用则使用基本检测
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FileSecurityValidator:
    """文件安全验证器"""
    
    # 允许的MIME类型
    ALLOWED_MIME_TYPES = {
        # 文档类型
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'application/json',
        
        # 图片类型
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/webp',
        
        # 压缩文件
        'application/zip',
        'application/x-rar-compressed',
        'application/x-7z-compressed'
    }
    
    # 危险的文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.app', '.deb', '.pkg', '.dmg', '.msi', '.run', '.sh', '.ps1', '.php',
        '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl', '.cgi'
    }
    
    # 文件大小限制 (MB)
    DEFAULT_MAX_SIZE = {
        'document': 50,
        'image': 20,
        'archive': 100
    }
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """初始化文件安全验证器"""
        self.security_level = security_level
        self.max_file_sizes = self.DEFAULT_MAX_SIZE.copy()
        
        # 根据安全级别调整限制
        if security_level == SecurityLevel.HIGH:
            self.max_file_sizes = {k: v // 2 for k, v in self.max_file_sizes.items()}
        elif security_level == SecurityLevel.LOW:
            self.max_file_sizes = {k: v * 2 for k, v in self.max_file_sizes.items()}
    
    def validate_file_type(self, file_path: str) -> Tuple[bool, str]:
        """验证文件类型"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()
            if file_ext in self.DANGEROUS_EXTENSIONS:
                return False, f"危险的文件类型: {file_ext}"
            
            # 检查MIME类型
            mime_type = mimetypes.guess_type(file_path)[0]
            if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
                return False, f"不支持的MIME类型: {mime_type}"
            
            # 使用python-magic进行更深入的文件类型检测（如果可用）
            if HAS_MAGIC:
                try:
                    detected_mime = magic.from_file(file_path, mime=True)
                    if detected_mime not in self.ALLOWED_MIME_TYPES:
                        return False, f"检测到不支持的文件类型: {detected_mime}"
                except Exception as e:
                    logger.warning(f"无法使用magic检测文件类型 {file_path}: {e}")
                    # 如果magic检测失败，继续使用基本验证
            
            return True, ""
            
        except Exception as e:
            return False, f"文件类型验证失败: {e}"
    
    def validate_file_size(self, file_path: str, file_category: str = 'document') -> Tuple[bool, str]:
        """验证文件大小"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            max_size = self.max_file_sizes.get(file_category, self.max_file_sizes['document'])
            
            if file_size_mb > max_size:
                return False, f"文件大小 {file_size_mb:.1f}MB 超过限制 {max_size}MB"
            
            return True, ""
            
        except Exception as e:
            return False, f"文件大小验证失败: {e}"
    
    def scan_for_malware(self, file_path: str) -> Tuple[bool, str]:
        """扫描恶意软件（简化版本）"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 检查文件头部是否包含可疑内容
            suspicious_patterns = [
                b'<script',
                b'javascript:',
                b'vbscript:',
                b'onload=',
                b'onerror=',
                b'eval(',
                b'exec(',
                b'system(',
                b'shell_exec'
            ]
            
            try:
                with open(file_path, 'rb') as f:
                    # 读取文件前1KB进行检查
                    content = f.read(1024)
                    content_lower = content.lower()
                    
                    for pattern in suspicious_patterns:
                        if pattern in content_lower:
                            return False, f"检测到可疑内容: {pattern.decode('utf-8', errors='ignore')}"
            
            except Exception as e:
                logger.warning(f"无法读取文件进行恶意软件扫描 {file_path}: {e}")
            
            # 检查文件名是否包含可疑字符
            filename = Path(file_path).name
            suspicious_chars = ['<', '>', '|', '&', ';', '$', '`']
            for char in suspicious_chars:
                if char in filename:
                    return False, f"文件名包含可疑字符: {char}"
            
            return True, ""
            
        except Exception as e:
            return False, f"恶意软件扫描失败: {e}"
    
    def check_file_integrity(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """检查文件完整性"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在", None
            
            # 计算文件校验和
            checksum = self._calculate_checksum(file_path)
            if not checksum:
                return False, "无法计算文件校验和", None
            
            # 尝试读取文件以检查是否损坏
            try:
                with open(file_path, 'rb') as f:
                    # 读取整个文件以检查完整性
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
            except Exception as e:
                return False, f"文件损坏或无法读取: {e}", None
            
            return True, "", checksum
            
        except Exception as e:
            return False, f"文件完整性检查失败: {e}", None
    
    def _calculate_checksum(self, file_path: str) -> Optional[str]:
        """计算文件校验和"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件校验和失败 {file_path}: {e}")
            return None
    
    def validate_filename(self, filename: str) -> Tuple[bool, str]:
        """验证文件名"""
        try:
            # 检查文件名长度
            if len(filename) > 255:
                return False, "文件名过长"
            
            if len(filename) == 0:
                return False, "文件名不能为空"
            
            # 检查非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
            for char in illegal_chars:
                if char in filename:
                    return False, f"文件名包含非法字符: {char}"
            
            # 检查保留名称（Windows）
            reserved_names = [
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            ]
            
            name_without_ext = Path(filename).stem.upper()
            if name_without_ext in reserved_names:
                return False, f"文件名使用了保留名称: {name_without_ext}"
            
            # 检查是否以点开头或结尾
            if filename.startswith('.') or filename.endswith('.'):
                return False, "文件名不能以点开头或结尾"
            
            return True, ""
            
        except Exception as e:
            return False, f"文件名验证失败: {e}"
    
    def comprehensive_validation(self, file_path: str, file_category: str = 'document') -> Tuple[bool, List[str], Optional[str]]:
        """综合文件验证"""
        errors = []
        checksum = None
        
        try:
            # 验证文件名
            filename = Path(file_path).name
            is_valid, error = self.validate_filename(filename)
            if not is_valid:
                errors.append(f"文件名验证失败: {error}")
            
            # 验证文件类型
            is_valid, error = self.validate_file_type(file_path)
            if not is_valid:
                errors.append(f"文件类型验证失败: {error}")
            
            # 验证文件大小
            is_valid, error = self.validate_file_size(file_path, file_category)
            if not is_valid:
                errors.append(f"文件大小验证失败: {error}")
            
            # 恶意软件扫描
            if self.security_level in [SecurityLevel.MEDIUM, SecurityLevel.HIGH]:
                is_valid, error = self.scan_for_malware(file_path)
                if not is_valid:
                    errors.append(f"安全扫描失败: {error}")
            
            # 文件完整性检查
            is_valid, error, file_checksum = self.check_file_integrity(file_path)
            if not is_valid:
                errors.append(f"完整性检查失败: {error}")
            else:
                checksum = file_checksum
            
            return len(errors) == 0, errors, checksum
            
        except Exception as e:
            errors.append(f"综合验证失败: {e}")
            return False, errors, None
    
    def get_file_category(self, file_path: str) -> str:
        """根据文件类型确定分类"""
        try:
            mime_type = mimetypes.guess_type(file_path)[0] or ""
            
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
                return 'archive'
            else:
                return 'document'
                
        except Exception:
            return 'document'
    
    def set_max_file_size(self, category: str, size_mb: int):
        """设置文件大小限制"""
        self.max_file_sizes[category] = size_mb
    
    def get_security_report(self, file_path: str) -> Dict[str, Any]:
        """生成文件安全报告"""
        report = {
            'file_path': file_path,
            'filename': Path(file_path).name,
            'security_level': self.security_level.value,
            'timestamp': os.path.getctime(file_path) if os.path.exists(file_path) else None,
            'validations': {}
        }
        
        try:
            file_category = self.get_file_category(file_path)
            
            # 文件名验证
            is_valid, error = self.validate_filename(Path(file_path).name)
            report['validations']['filename'] = {'valid': is_valid, 'error': error}
            
            # 文件类型验证
            is_valid, error = self.validate_file_type(file_path)
            report['validations']['file_type'] = {'valid': is_valid, 'error': error}
            
            # 文件大小验证
            is_valid, error = self.validate_file_size(file_path, file_category)
            report['validations']['file_size'] = {'valid': is_valid, 'error': error}
            
            # 恶意软件扫描
            is_valid, error = self.scan_for_malware(file_path)
            report['validations']['malware_scan'] = {'valid': is_valid, 'error': error}
            
            # 完整性检查
            is_valid, error, checksum = self.check_file_integrity(file_path)
            report['validations']['integrity'] = {'valid': is_valid, 'error': error, 'checksum': checksum}
            
            # 总体结果
            all_valid = all(v['valid'] for v in report['validations'].values())
            report['overall_valid'] = all_valid
            
        except Exception as e:
            report['error'] = str(e)
            report['overall_valid'] = False
        
        return report


class FileQuarantineManager:
    """文件隔离管理器"""
    
    def __init__(self, quarantine_dir: str = "quarantine"):
        """初始化隔离管理器"""
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_log = self.quarantine_dir / "quarantine.log"
    
    def quarantine_file(self, file_path: str, reason: str) -> Tuple[bool, str]:
        """隔离文件"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 生成隔离文件名
            original_name = Path(file_path).name
            timestamp = int(os.path.getctime(file_path))
            quarantine_name = f"{timestamp}_{original_name}.quarantined"
            quarantine_path = self.quarantine_dir / quarantine_name
            
            # 移动文件到隔离区
            import shutil
            shutil.move(file_path, quarantine_path)
            
            # 记录隔离日志
            self._log_quarantine(file_path, str(quarantine_path), reason)
            
            logger.warning(f"文件已隔离: {file_path} -> {quarantine_path}, 原因: {reason}")
            return True, str(quarantine_path)
            
        except Exception as e:
            error_msg = f"文件隔离失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _log_quarantine(self, original_path: str, quarantine_path: str, reason: str):
        """记录隔离日志"""
        try:
            import datetime
            log_entry = f"{datetime.datetime.now().isoformat()} | {original_path} | {quarantine_path} | {reason}\n"
            
            with open(self.quarantine_log, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"记录隔离日志失败: {e}")
    
    def list_quarantined_files(self) -> List[Dict[str, Any]]:
        """列出隔离的文件"""
        quarantined_files = []
        
        try:
            for file_path in self.quarantine_dir.glob("*.quarantined"):
                file_info = {
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'quarantine_time': file_path.stat().st_ctime
                }
                quarantined_files.append(file_info)
                
        except Exception as e:
            logger.error(f"列出隔离文件失败: {e}")
        
        return quarantined_files
    
    def restore_file(self, quarantine_path: str, restore_path: str) -> Tuple[bool, str]:
        """恢复隔离的文件"""
        try:
            if not os.path.exists(quarantine_path):
                return False, "隔离文件不存在"
            
            # 创建恢复目录
            Path(restore_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件回原位置
            import shutil
            shutil.move(quarantine_path, restore_path)
            
            logger.info(f"文件已恢复: {quarantine_path} -> {restore_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"文件恢复失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_quarantined_file(self, quarantine_path: str) -> Tuple[bool, str]:
        """永久删除隔离的文件"""
        try:
            if not os.path.exists(quarantine_path):
                return False, "隔离文件不存在"
            
            os.remove(quarantine_path)
            logger.info(f"隔离文件已永久删除: {quarantine_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"删除隔离文件失败: {e}"
            logger.error(error_msg)
            return False, error_msg