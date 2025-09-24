#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据加密服务
实现敏感数据加密存储和解密
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

# 配置日志
logger = logging.getLogger(__name__)


class EncryptionService:
    """数据加密服务"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密服务
        
        Args:
            master_key: 主密钥，如果不提供则从环境变量获取或生成
        """
        self._master_key = master_key or self._get_or_create_master_key()
        self._fernet = self._create_fernet_cipher()
    
    def _get_or_create_master_key(self) -> str:
        """获取或创建主密钥"""
        # 首先尝试从环境变量获取
        master_key = os.getenv('ENCRYPTION_MASTER_KEY')
        if master_key:
            return master_key
        
        # 尝试从文件获取
        key_file = '.encryption_key'
        if os.path.exists(key_file):
            try:
                with open(key_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"读取密钥文件失败: {e}")
        
        # 生成新的主密钥
        master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        # 保存到文件
        try:
            with open(key_file, 'w') as f:
                f.write(master_key)
            os.chmod(key_file, 0o600)  # 设置文件权限为仅所有者可读写
            logger.info("生成新的主密钥并保存到文件")
        except Exception as e:
            logger.error(f"保存密钥文件失败: {e}")
        
        return master_key
    
    def _create_fernet_cipher(self) -> Fernet:
        """创建Fernet加密器"""
        # 使用PBKDF2从主密钥派生加密密钥
        salt = b'classroom_grading_salt'  # 固定盐值，实际应用中应该使用随机盐值
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        加密字符串数据
        
        Args:
            data: 要加密的字符串
            
        Returns:
            加密后的base64编码字符串
        """
        try:
            if not data:
                return ""
            
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密字符串数据
        
        Args:
            encrypted_data: 加密的base64编码字符串
            
        Returns:
            解密后的原始字符串
        """
        try:
            if not encrypted_data:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        加密字典中的指定字段
        
        Args:
            data: 要加密的字典
            fields_to_encrypt: 需要加密的字段列表
            
        Returns:
            加密后的字典
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
                    encrypted_data[f"{field}_encrypted"] = True  # 标记字段已加密
                except Exception as e:
                    logger.error(f"加密字段 {field} 失败: {e}")
        
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        解密字典中的指定字段
        
        Args:
            data: 要解密的字典
            fields_to_decrypt: 需要解密的字段列表
            
        Returns:
            解密后的字典
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                # 检查字段是否已加密
                if decrypted_data.get(f"{field}_encrypted", False):
                    try:
                        decrypted_data[field] = self.decrypt(decrypted_data[field])
                        decrypted_data.pop(f"{field}_encrypted", None)  # 移除加密标记
                    except Exception as e:
                        logger.error(f"解密字段 {field} 失败: {e}")
        
        return decrypted_data
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """
        哈希密码
        
        Args:
            password: 原始密码
            salt: 盐值，如果不提供则生成随机盐值
            
        Returns:
            (哈希值, 盐值) 元组
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        
        password_hash = base64.urlsafe_b64encode(kdf.derive(password.encode())).decode()
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 原始密码
            password_hash: 存储的密码哈希
            salt: 盐值
            
        Returns:
            密码是否匹配
        """
        try:
            computed_hash, _ = self.hash_password(password, salt)
            return computed_hash == password_hash
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        生成安全令牌
        
        Args:
            length: 令牌长度（字节）
            
        Returns:
            base64编码的安全令牌
        """
        token = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(token).decode()
    
    def hash_data(self, data: str, algorithm: str = 'sha256') -> str:
        """
        哈希数据
        
        Args:
            data: 要哈希的数据
            algorithm: 哈希算法 ('sha256', 'sha512', 'md5')
            
        Returns:
            十六进制哈希值
        """
        if algorithm == 'sha256':
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data.encode()).hexdigest()
        elif algorithm == 'md5':
            return hashlib.md5(data.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
    
    def encrypt_file_content(self, file_content: bytes) -> bytes:
        """
        加密文件内容
        
        Args:
            file_content: 文件内容字节
            
        Returns:
            加密后的文件内容字节
        """
        try:
            return self._fernet.encrypt(file_content)
        except Exception as e:
            logger.error(f"文件内容加密失败: {e}")
            raise
    
    def decrypt_file_content(self, encrypted_content: bytes) -> bytes:
        """
        解密文件内容
        
        Args:
            encrypted_content: 加密的文件内容字节
            
        Returns:
            解密后的文件内容字节
        """
        try:
            return self._fernet.decrypt(encrypted_content)
        except Exception as e:
            logger.error(f"文件内容解密失败: {e}")
            raise
    
    def create_data_signature(self, data: str) -> str:
        """
        创建数据签名用于完整性验证
        
        Args:
            data: 要签名的数据
            
        Returns:
            数据签名
        """
        # 使用HMAC创建签名
        import hmac
        signature = hmac.new(
            self._master_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_data_signature(self, data: str, signature: str) -> bool:
        """
        验证数据签名
        
        Args:
            data: 原始数据
            signature: 数据签名
            
        Returns:
            签名是否有效
        """
        try:
            expected_signature = self.create_data_signature(data)
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False


class SensitiveDataManager:
    """敏感数据管理器"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption_service = encryption_service
        
        # 定义需要加密的敏感字段
        self.sensitive_fields = {
            'user': ['email', 'real_name', 'phone'],
            'submission': ['ai_result', 'teacher_feedback'],
            'assignment': ['description'],
            'grading': ['feedback', 'comments']
        }
    
    def encrypt_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """加密用户敏感数据"""
        return self.encryption_service.encrypt_dict(
            user_data, 
            self.sensitive_fields.get('user', [])
        )
    
    def decrypt_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """解密用户敏感数据"""
        return self.encryption_service.decrypt_dict(
            user_data, 
            self.sensitive_fields.get('user', [])
        )
    
    def encrypt_submission_data(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """加密提交敏感数据"""
        return self.encryption_service.encrypt_dict(
            submission_data, 
            self.sensitive_fields.get('submission', [])
        )
    
    def decrypt_submission_data(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """解密提交敏感数据"""
        return self.encryption_service.decrypt_dict(
            submission_data, 
            self.sensitive_fields.get('submission', [])
        )
    
    def encrypt_assignment_data(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """加密作业敏感数据"""
        return self.encryption_service.encrypt_dict(
            assignment_data, 
            self.sensitive_fields.get('assignment', [])
        )
    
    def decrypt_assignment_data(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """解密作业敏感数据"""
        return self.encryption_service.decrypt_dict(
            assignment_data, 
            self.sensitive_fields.get('assignment', [])
        )
    
    def secure_delete_data(self, data_type: str, data_id: str) -> bool:
        """安全删除敏感数据"""
        try:
            # 这里应该实现安全删除逻辑
            # 例如多次覆写数据区域
            logger.info(f"安全删除 {data_type} 数据: {data_id}")
            return True
        except Exception as e:
            logger.error(f"安全删除数据失败: {e}")
            return False


# 全局加密服务实例
encryption_service = EncryptionService()
sensitive_data_manager = SensitiveDataManager(encryption_service)