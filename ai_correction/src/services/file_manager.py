#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理器 - 处理作业文件和批改标准的上传、存储和管理
"""

import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class FileType(Enum):
    """文件类型"""
    QUESTION = "question"      # 作业题目文件
    MARKING = "marking"        # 批改标准文件
    ANSWER = "answer"          # 学生答案文件
    RESULT = "result"          # 批改结果文件


class FileAccessLevel(Enum):
    """文件访问级别"""
    PUBLIC = "public"          # 公开访问
    CLASS_ONLY = "class_only"  # 仅班级成员
    TEACHER_ONLY = "teacher_only"  # 仅教师
    OWNER_ONLY = "owner_only"  # 仅所有者


class FileMetadata:
    """文件元数据"""
    def __init__(self, file_path: str, file_type: FileType, 
                 owner: str, access_level: FileAccessLevel = FileAccessLevel.CLASS_ONLY,
                 assignment_id: Optional[int] = None, class_id: Optional[int] = None):
        self.file_path = file_path
        self.file_type = file_type
        self.owner = owner
        self.access_level = access_level
        self.assignment_id = assignment_id
        self.class_id = class_id
        self.created_at = datetime.now()
        self.file_size = 0
        self.mime_type = ""
        self.checksum = ""
        
        if os.path.exists(file_path):
            self.file_size = os.path.getsize(file_path)
            self.mime_type = mimetypes.guess_type(file_path)[0] or ""
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """计算文件校验和"""
        try:
            with open(self.file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"无法计算文件校验和 {self.file_path}: {e}")
            return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'file_path': self.file_path,
            'file_type': self.file_type.value,
            'owner': self.owner,
            'access_level': self.access_level.value,
            'assignment_id': self.assignment_id,
            'class_id': self.class_id,
            'created_at': self.created_at.isoformat(),
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """从字典创建"""
        metadata = cls(
            file_path=data['file_path'],
            file_type=FileType(data['file_type']),
            owner=data['owner'],
            access_level=FileAccessLevel(data.get('access_level', 'class_only')),
            assignment_id=data.get('assignment_id'),
            class_id=data.get('class_id')
        )
        metadata.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        metadata.file_size = data.get('file_size', 0)
        metadata.mime_type = data.get('mime_type', '')
        metadata.checksum = data.get('checksum', '')
        return metadata


class FileManager:
    """文件管理器"""
    
    # 支持的文件类型
    ALLOWED_EXTENSIONS = {
        FileType.QUESTION: {'.pdf', '.doc', '.docx', '.txt', '.md'},
        FileType.MARKING: {'.pdf', '.doc', '.docx', '.txt', '.md', '.json'},
        FileType.ANSWER: {'.pdf', '.doc', '.docx', '.txt', '.md', '.jpg', '.jpeg', '.png'},
        FileType.RESULT: {'.pdf', '.json', '.txt', '.html'}
    }
    
    # 文件大小限制 (MB)
    MAX_FILE_SIZE = {
        FileType.QUESTION: 50,
        FileType.MARKING: 20,
        FileType.ANSWER: 100,
        FileType.RESULT: 10
    }
    
    def __init__(self, base_upload_dir: str = "uploads"):
        """初始化文件管理器"""
        self.base_upload_dir = Path(base_upload_dir)
        self.metadata_file = self.base_upload_dir / "file_metadata.json"
        self._metadata_cache: Dict[str, FileMetadata] = {}
        
        # 创建基础目录结构
        self._create_directory_structure()
        
        # 加载文件元数据
        self._load_metadata()
    
    def _create_directory_structure(self):
        """创建标准化的文件存储目录结构"""
        directories = [
            self.base_upload_dir / "assignments",
            self.base_upload_dir / "submissions", 
            self.base_upload_dir / "grading_results",
            self.base_upload_dir / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"文件存储目录结构已创建: {self.base_upload_dir}")
    
    def _load_metadata(self):
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for file_path, metadata_dict in data.items():
                        self._metadata_cache[file_path] = FileMetadata.from_dict(metadata_dict)
                logger.info(f"已加载 {len(self._metadata_cache)} 个文件元数据")
            except Exception as e:
                logger.error(f"加载文件元数据失败: {e}")
                self._metadata_cache = {}
    
    def _save_metadata(self):
        """保存文件元数据"""
        try:
            data = {path: metadata.to_dict() for path, metadata in self._metadata_cache.items()}
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存文件元数据失败: {e}")
    
    def _validate_file(self, file_path: str, file_type: FileType) -> List[str]:
        """验证文件"""
        errors = []
        
        if not os.path.exists(file_path):
            errors.append("文件不存在")
            return errors
        
        # 检查文件扩展名
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS.get(file_type, set()):
            allowed = ', '.join(self.ALLOWED_EXTENSIONS.get(file_type, set()))
            errors.append(f"不支持的文件类型 {file_ext}，支持的类型: {allowed}")
        
        # 检查文件大小
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        max_size = self.MAX_FILE_SIZE.get(file_type, 10)
        if file_size_mb > max_size:
            errors.append(f"文件大小 {file_size_mb:.1f}MB 超过限制 {max_size}MB")
        
        # 检查文件完整性
        try:
            with open(file_path, 'rb') as f:
                f.read(1024)  # 尝试读取文件开头
        except Exception as e:
            errors.append(f"文件损坏或无法读取: {e}")
        
        return errors
    
    def _generate_file_path(self, file_type: FileType, assignment_id: Optional[int] = None,
                           student_username: Optional[str] = None, 
                           original_filename: str = "") -> str:
        """生成文件存储路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if file_type in [FileType.QUESTION, FileType.MARKING]:
            # 作业相关文件
            if assignment_id is None:
                raise ValueError("assignment_id is required for question and marking files")
            subdir = "questions" if file_type == FileType.QUESTION else "marking_standards"
            return str(self.base_upload_dir / "assignments" / str(assignment_id) / subdir / f"{timestamp}_{original_filename}")
        
        elif file_type == FileType.ANSWER:
            # 学生答案文件
            if assignment_id is None or student_username is None:
                raise ValueError("assignment_id and student_username are required for answer files")
            return str(self.base_upload_dir / "submissions" / str(assignment_id) / student_username / f"{timestamp}_{original_filename}")
        
        elif file_type == FileType.RESULT:
            # 批改结果文件
            if assignment_id is None or student_username is None:
                raise ValueError("assignment_id and student_username are required for result files")
            return str(self.base_upload_dir / "grading_results" / str(assignment_id) / student_username / f"{timestamp}_{original_filename}")
        
        else:
            # 临时文件
            return str(self.base_upload_dir / "temp" / f"{timestamp}_{original_filename}")
    
    def upload_file(self, source_path: str, file_type: FileType, owner: str,
                   assignment_id: Optional[int] = None, student_username: Optional[str] = None,
                   class_id: Optional[int] = None, 
                   access_level: FileAccessLevel = FileAccessLevel.CLASS_ONLY) -> Tuple[bool, str, Optional[str]]:
        """
        上传文件
        
        Args:
            source_path: 源文件路径
            file_type: 文件类型
            owner: 文件所有者
            assignment_id: 作业ID
            student_username: 学生用户名（用于答案文件）
            class_id: 班级ID
            access_level: 访问级别
        
        Returns:
            (成功标志, 错误信息, 目标文件路径)
        """
        try:
            # 验证文件
            errors = self._validate_file(source_path, file_type)
            if errors:
                return False, "; ".join(errors), None
            
            # 生成目标路径
            original_filename = Path(source_path).name
            target_path = self._generate_file_path(file_type, assignment_id, student_username, original_filename)
            
            # 创建目标目录
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 创建文件元数据
            metadata = FileMetadata(
                file_path=target_path,
                file_type=file_type,
                owner=owner,
                access_level=access_level,
                assignment_id=assignment_id,
                class_id=class_id
            )
            
            # 保存元数据
            self._metadata_cache[target_path] = metadata
            self._save_metadata()
            
            logger.info(f"文件上传成功: {source_path} -> {target_path}")
            return True, "", target_path
            
        except Exception as e:
            error_msg = f"文件上传失败: {e}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def upload_question_files(self, file_paths: List[str], assignment_id: int, 
                             teacher_username: str, class_id: int) -> Tuple[bool, str, List[str]]:
        """上传作业题目文件"""
        uploaded_files = []
        errors = []
        
        for file_path in file_paths:
            success, error, target_path = self.upload_file(
                source_path=file_path,
                file_type=FileType.QUESTION,
                owner=teacher_username,
                assignment_id=assignment_id,
                class_id=class_id,
                access_level=FileAccessLevel.CLASS_ONLY
            )
            
            if success and target_path:
                uploaded_files.append(target_path)
            else:
                errors.append(f"{Path(file_path).name}: {error}")
        
        if errors:
            return False, "; ".join(errors), uploaded_files
        
        return True, "", uploaded_files
    
    def upload_marking_files(self, file_paths: List[str], assignment_id: int,
                            teacher_username: str, class_id: int) -> Tuple[bool, str, List[str]]:
        """上传批改标准文件"""
        uploaded_files = []
        errors = []
        
        for file_path in file_paths:
            success, error, target_path = self.upload_file(
                source_path=file_path,
                file_type=FileType.MARKING,
                owner=teacher_username,
                assignment_id=assignment_id,
                class_id=class_id,
                access_level=FileAccessLevel.TEACHER_ONLY
            )
            
            if success and target_path:
                uploaded_files.append(target_path)
            else:
                errors.append(f"{Path(file_path).name}: {error}")
        
        if errors:
            return False, "; ".join(errors), uploaded_files
        
        return True, "", uploaded_files
    
    def upload_answer_files(self, file_paths: List[str], assignment_id: int,
                           student_username: str, class_id: int) -> Tuple[bool, str, List[str]]:
        """上传学生答案文件"""
        uploaded_files = []
        errors = []
        
        for file_path in file_paths:
            success, error, target_path = self.upload_file(
                source_path=file_path,
                file_type=FileType.ANSWER,
                owner=student_username,
                assignment_id=assignment_id,
                student_username=student_username,
                class_id=class_id,
                access_level=FileAccessLevel.OWNER_ONLY
            )
            
            if success and target_path:
                uploaded_files.append(target_path)
            else:
                errors.append(f"{Path(file_path).name}: {error}")
        
        if errors:
            return False, "; ".join(errors), uploaded_files
        
        return True, "", uploaded_files 
   
    def check_file_access(self, file_path: str, user: str, user_role: str = "student",
                         class_id: Optional[int] = None) -> bool:
        """检查文件访问权限"""
        metadata = self._metadata_cache.get(file_path)
        if not metadata:
            return False
        
        # 文件所有者总是可以访问
        if metadata.owner == user:
            return True
        
        # 根据访问级别检查权限
        if metadata.access_level == FileAccessLevel.PUBLIC:
            return True
        
        elif metadata.access_level == FileAccessLevel.CLASS_ONLY:
            # 需要在同一班级
            return class_id is not None and metadata.class_id == class_id
        
        elif metadata.access_level == FileAccessLevel.TEACHER_ONLY:
            # 只有教师可以访问
            return user_role == "teacher"
        
        elif metadata.access_level == FileAccessLevel.OWNER_ONLY:
            # 只有所有者可以访问
            return metadata.owner == user
        
        return False
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        return self._metadata_cache.get(file_path)
    
    def get_assignment_files(self, assignment_id: int, file_type: Optional[FileType] = None) -> List[str]:
        """获取作业相关文件列表"""
        files = []
        for path, metadata in self._metadata_cache.items():
            if metadata.assignment_id == assignment_id:
                if file_type is None or metadata.file_type == file_type:
                    if os.path.exists(path):
                        files.append(path)
        return files
    
    def get_student_files(self, assignment_id: int, student_username: str) -> List[str]:
        """获取学生提交的文件列表"""
        files = []
        for path, metadata in self._metadata_cache.items():
            if (metadata.assignment_id == assignment_id and 
                metadata.owner == student_username and 
                metadata.file_type == FileType.ANSWER):
                if os.path.exists(path):
                    files.append(path)
        return files
    
    def delete_file(self, file_path: str, user: str, user_role: str = "student") -> Tuple[bool, str]:
        """删除文件"""
        try:
            # 检查权限
            metadata = self._metadata_cache.get(file_path)
            if not metadata:
                return False, "文件不存在"
            
            # 只有文件所有者或教师可以删除文件
            if metadata.owner != user and user_role != "teacher":
                return False, "没有删除权限"
            
            # 删除物理文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 删除元数据
            if file_path in self._metadata_cache:
                del self._metadata_cache[file_path]
                self._save_metadata()
            
            logger.info(f"文件删除成功: {file_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"文件删除失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def move_file(self, source_path: str, target_path: str, user: str, user_role: str = "student") -> Tuple[bool, str]:
        """移动文件"""
        try:
            # 检查权限
            metadata = self._metadata_cache.get(source_path)
            if not metadata:
                return False, "源文件不存在"
            
            if metadata.owner != user and user_role != "teacher":
                return False, "没有移动权限"
            
            # 创建目标目录
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(source_path, target_path)
            
            # 更新元数据
            metadata.file_path = target_path
            del self._metadata_cache[source_path]
            self._metadata_cache[target_path] = metadata
            self._save_metadata()
            
            logger.info(f"文件移动成功: {source_path} -> {target_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"文件移动失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def copy_file(self, source_path: str, target_path: str, new_owner: str,
                 new_access_level: FileAccessLevel = FileAccessLevel.CLASS_ONLY) -> Tuple[bool, str]:
        """复制文件"""
        try:
            if not os.path.exists(source_path):
                return False, "源文件不存在"
            
            # 创建目标目录
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 创建新的元数据
            source_metadata = self._metadata_cache.get(source_path)
            if source_metadata:
                new_metadata = FileMetadata(
                    file_path=target_path,
                    file_type=source_metadata.file_type,
                    owner=new_owner,
                    access_level=new_access_level,
                    assignment_id=source_metadata.assignment_id,
                    class_id=source_metadata.class_id
                )
                self._metadata_cache[target_path] = new_metadata
                self._save_metadata()
            
            logger.info(f"文件复制成功: {source_path} -> {target_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"文件复制失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        if not os.path.exists(file_path):
            return None
        
        metadata = self._metadata_cache.get(file_path)
        
        file_info = {
            'path': file_path,
            'name': Path(file_path).name,
            'size': os.path.getsize(file_path),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'mime_type': mimetypes.guess_type(file_path)[0] or ""
        }
        
        if metadata:
            file_info.update({
                'type': metadata.file_type.value,
                'owner': metadata.owner,
                'access_level': metadata.access_level.value,
                'assignment_id': metadata.assignment_id,
                'class_id': metadata.class_id,
                'created_at': metadata.created_at.isoformat(),
                'checksum': metadata.checksum
            })
        
        return file_info
    
    def cleanup_orphaned_files(self) -> Tuple[int, List[str]]:
        """清理孤立文件（没有元数据记录的文件）"""
        orphaned_files = []
        cleaned_count = 0
        
        try:
            # 扫描所有文件
            for root, dirs, files in os.walk(self.base_upload_dir):
                for file in files:
                    if file == "file_metadata.json":
                        continue
                    
                    file_path = os.path.join(root, file)
                    if file_path not in self._metadata_cache:
                        orphaned_files.append(file_path)
                        
                        # 删除孤立文件
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.info(f"清理孤立文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"无法删除孤立文件 {file_path}: {e}")
            
            # 清理空目录
            self._cleanup_empty_directories()
            
        except Exception as e:
            logger.error(f"清理孤立文件失败: {e}")
        
        return cleaned_count, orphaned_files
    
    def cleanup_missing_files(self) -> Tuple[int, List[str]]:
        """清理元数据中记录但实际不存在的文件"""
        missing_files = []
        cleaned_count = 0
        
        try:
            paths_to_remove = []
            
            for file_path, metadata in self._metadata_cache.items():
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
                    paths_to_remove.append(file_path)
            
            # 从元数据中移除
            for path in paths_to_remove:
                del self._metadata_cache[path]
                cleaned_count += 1
                logger.info(f"清理缺失文件元数据: {path}")
            
            if paths_to_remove:
                self._save_metadata()
            
        except Exception as e:
            logger.error(f"清理缺失文件失败: {e}")
        
        return cleaned_count, missing_files
    
    def _cleanup_empty_directories(self):
        """清理空目录"""
        try:
            for root, dirs, files in os.walk(self.base_upload_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # 目录为空
                            os.rmdir(dir_path)
                            logger.info(f"清理空目录: {dir_path}")
                    except OSError:
                        pass  # 目录不为空或无法删除
        except Exception as e:
            logger.warning(f"清理空目录失败: {e}")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'file_types': {},
            'access_levels': {},
            'owners': {},
            'assignments': {}
        }
        
        try:
            for file_path, metadata in self._metadata_cache.items():
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    
                    stats['total_files'] += 1
                    stats['total_size'] += file_size
                    
                    # 按文件类型统计
                    file_type = metadata.file_type.value
                    if file_type not in stats['file_types']:
                        stats['file_types'][file_type] = {'count': 0, 'size': 0}
                    stats['file_types'][file_type]['count'] += 1
                    stats['file_types'][file_type]['size'] += file_size
                    
                    # 按访问级别统计
                    access_level = metadata.access_level.value
                    if access_level not in stats['access_levels']:
                        stats['access_levels'][access_level] = {'count': 0, 'size': 0}
                    stats['access_levels'][access_level]['count'] += 1
                    stats['access_levels'][access_level]['size'] += file_size
                    
                    # 按所有者统计
                    owner = metadata.owner
                    if owner not in stats['owners']:
                        stats['owners'][owner] = {'count': 0, 'size': 0}
                    stats['owners'][owner]['count'] += 1
                    stats['owners'][owner]['size'] += file_size
                    
                    # 按作业统计
                    if metadata.assignment_id:
                        assignment_id = str(metadata.assignment_id)
                        if assignment_id not in stats['assignments']:
                            stats['assignments'][assignment_id] = {'count': 0, 'size': 0}
                        stats['assignments'][assignment_id]['count'] += 1
                        stats['assignments'][assignment_id]['size'] += file_size
            
            # 转换大小为MB
            stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
        
        return stats
    
    def archive_assignment_files(self, assignment_id: int, archive_path: str) -> Tuple[bool, str]:
        """归档作业相关文件"""
        try:
            import zipfile
            
            assignment_files = self.get_assignment_files(assignment_id)
            if not assignment_files:
                return False, "没有找到相关文件"
            
            # 创建归档目录
            Path(archive_path).parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in assignment_files:
                    if os.path.exists(file_path):
                        # 使用相对路径作为归档内的路径
                        arcname = os.path.relpath(file_path, self.base_upload_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"作业文件归档成功: {assignment_id} -> {archive_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"文件归档失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_file_integrity(self, file_path: str) -> Tuple[bool, str]:
        """验证文件完整性"""
        try:
            metadata = self._metadata_cache.get(file_path)
            if not metadata:
                return False, "文件元数据不存在"
            
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 检查文件大小
            current_size = os.path.getsize(file_path)
            if current_size != metadata.file_size:
                return False, f"文件大小不匹配: 期望 {metadata.file_size}, 实际 {current_size}"
            
            # 检查校验和
            if metadata.checksum:
                current_checksum = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        current_checksum.update(chunk)
                
                if current_checksum.hexdigest() != metadata.checksum:
                    return False, "文件校验和不匹配"
            
            return True, ""
            
        except Exception as e:
            return False, f"验证失败: {e}"