#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件存储结构管理模块
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StoragePolicy(Enum):
    """存储策略"""
    IMMEDIATE = "immediate"      # 立即存储
    SCHEDULED = "scheduled"      # 定时存储
    ON_DEMAND = "on_demand"      # 按需存储


class ArchivePolicy(Enum):
    """归档策略"""
    NEVER = "never"              # 永不归档
    TIME_BASED = "time_based"    # 基于时间归档
    SIZE_BASED = "size_based"    # 基于大小归档
    MANUAL = "manual"            # 手动归档


class FileStorageManager:
    """文件存储结构管理器"""
    
    def __init__(self, base_storage_dir: str = "uploads"):
        """初始化存储管理器"""
        self.base_storage_dir = Path(base_storage_dir)
        self.config_file = self.base_storage_dir / "storage_config.json"
        self.archive_dir = self.base_storage_dir / "archive"
        self.temp_dir = self.base_storage_dir / "temp"
        
        # 默认配置
        self.config = {
            'storage_policy': StoragePolicy.IMMEDIATE.value,
            'archive_policy': ArchivePolicy.TIME_BASED.value,
            'archive_after_days': 365,
            'max_storage_size_gb': 100,
            'cleanup_temp_after_hours': 24,
            'directory_structure': {
                'assignments': 'assignments/{assignment_id}',
                'submissions': 'submissions/{assignment_id}/{student_username}',
                'grading_results': 'grading_results/{assignment_id}',
                'archive': 'archive/{year}/{month}',
                'temp': 'temp'
            }
        }
        
        # 初始化存储结构
        self._initialize_storage_structure()
        self._load_config()
    
    def _initialize_storage_structure(self):
        """初始化标准化的文件存储目录结构"""
        try:
            # 创建基础目录
            directories = [
                self.base_storage_dir / "assignments",
                self.base_storage_dir / "submissions",
                self.base_storage_dir / "grading_results",
                self.archive_dir,
                self.temp_dir,
                self.base_storage_dir / "logs"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            # 创建README文件说明目录结构
            readme_content = """# 文件存储目录结构

## 目录说明

- `assignments/`: 作业相关文件
  - `{assignment_id}/questions/`: 作业题目文件
  - `{assignment_id}/marking_standards/`: 批改标准文件

- `submissions/`: 学生提交文件
  - `{assignment_id}/{student_username}/`: 学生答案文件

- `grading_results/`: 批改结果文件
  - `{assignment_id}/`: 批改结果和报告

- `archive/`: 归档文件
  - `{year}/{month}/`: 按时间归档的文件

- `temp/`: 临时文件
  - 用于临时存储上传中的文件

- `logs/`: 存储操作日志
"""
            
            readme_file = self.base_storage_dir / "README.md"
            if not readme_file.exists():
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
            
            logger.info(f"文件存储结构已初始化: {self.base_storage_dir}")
            
        except Exception as e:
            logger.error(f"初始化存储结构失败: {e}")
            raise
    
    def _load_config(self):
        """加载存储配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info("存储配置已加载")
            else:
                self._save_config()
                logger.info("使用默认存储配置")
        except Exception as e:
            logger.error(f"加载存储配置失败: {e}")
    
    def _save_config(self):
        """保存存储配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存存储配置失败: {e}")
    
    def generate_file_path(self, path_type: str, **kwargs) -> str:
        """生成文件路径"""
        try:
            template = self.config['directory_structure'].get(path_type)
            if not template:
                raise ValueError(f"未知的路径类型: {path_type}")
            
            # 添加时间戳用于归档路径
            if path_type == 'archive':
                now = datetime.now()
                kwargs.setdefault('year', now.year)
                kwargs.setdefault('month', f"{now.month:02d}")
            
            # 格式化路径
            formatted_path = template.format(**kwargs)
            full_path = self.base_storage_dir / formatted_path
            
            # 创建目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            return str(full_path)
            
        except Exception as e:
            logger.error(f"生成文件路径失败: {e}")
            raise
    
    def get_assignment_directory(self, assignment_id: int) -> str:
        """获取作业目录路径"""
        return self.generate_file_path('assignments', assignment_id=assignment_id)
    
    def get_submission_directory(self, assignment_id: int, student_username: str) -> str:
        """获取提交目录路径"""
        return self.generate_file_path('submissions', 
                                     assignment_id=assignment_id, 
                                     student_username=student_username)
    
    def get_grading_results_directory(self, assignment_id: int) -> str:
        """获取批改结果目录路径"""
        return self.generate_file_path('grading_results', assignment_id=assignment_id)
    
    def get_archive_directory(self, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """获取归档目录路径"""
        kwargs = {}
        if year:
            kwargs['year'] = year
        if month:
            kwargs['month'] = f"{month:02d}"
        return self.generate_file_path('archive', **kwargs)
    
    def get_temp_directory(self) -> str:
        """获取临时目录路径"""
        return str(self.temp_dir)
    
    def organize_files_by_assignment(self, assignment_id: int) -> Dict[str, List[str]]:
        """按作业组织文件"""
        try:
            assignment_dir = Path(self.get_assignment_directory(assignment_id))
            submission_base = self.base_storage_dir / "submissions" / str(assignment_id)
            results_dir = Path(self.get_grading_results_directory(assignment_id))
            
            organized_files = {
                'questions': [],
                'marking_standards': [],
                'submissions': {},
                'results': []
            }
            
            # 收集题目文件
            questions_dir = assignment_dir / "questions"
            if questions_dir.exists():
                organized_files['questions'] = [
                    str(f) for f in questions_dir.rglob("*") if f.is_file()
                ]
            
            # 收集批改标准文件
            marking_dir = assignment_dir / "marking_standards"
            if marking_dir.exists():
                organized_files['marking_standards'] = [
                    str(f) for f in marking_dir.rglob("*") if f.is_file()
                ]
            
            # 收集学生提交文件
            if submission_base.exists():
                for student_dir in submission_base.iterdir():
                    if student_dir.is_dir():
                        student_username = student_dir.name
                        organized_files['submissions'][student_username] = [
                            str(f) for f in student_dir.rglob("*") if f.is_file()
                        ]
            
            # 收集批改结果文件
            if results_dir.exists():
                organized_files['results'] = [
                    str(f) for f in results_dir.rglob("*") if f.is_file()
                ]
            
            return organized_files
            
        except Exception as e:
            logger.error(f"组织作业文件失败: {e}")
            return {}
    
    def cleanup_temp_files(self, max_age_hours: Optional[int] = None) -> Tuple[int, List[str]]:
        """清理临时文件"""
        try:
            max_age = max_age_hours or self.config['cleanup_temp_after_hours']
            cutoff_time = datetime.now() - timedelta(hours=max_age)
            
            cleaned_files = []
            cleaned_count = 0
            
            if not self.temp_dir.exists():
                return 0, []
            
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            cleaned_files.append(str(file_path))
                            cleaned_count += 1
                            logger.info(f"清理临时文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"无法删除临时文件 {file_path}: {e}")
            
            # 清理空目录
            self._cleanup_empty_directories(self.temp_dir)
            
            return cleaned_count, cleaned_files
            
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0, []
    
    def archive_old_files(self, days_old: Optional[int] = None) -> Tuple[int, List[str]]:
        """归档旧文件"""
        try:
            if self.config['archive_policy'] == ArchivePolicy.NEVER.value:
                return 0, []
            
            days_threshold = days_old or self.config['archive_after_days']
            cutoff_time = datetime.now() - timedelta(days=days_threshold)
            
            archived_files = []
            archived_count = 0
            
            # 归档作业文件
            assignments_dir = self.base_storage_dir / "assignments"
            if assignments_dir.exists():
                for assignment_dir in assignments_dir.iterdir():
                    if assignment_dir.is_dir():
                        dir_mtime = datetime.fromtimestamp(assignment_dir.stat().st_mtime)
                        if dir_mtime < cutoff_time:
                            archive_path = self._archive_directory(assignment_dir, "assignments")
                            if archive_path:
                                archived_files.append(archive_path)
                                archived_count += 1
            
            # 归档提交文件
            submissions_dir = self.base_storage_dir / "submissions"
            if submissions_dir.exists():
                for assignment_dir in submissions_dir.iterdir():
                    if assignment_dir.is_dir():
                        dir_mtime = datetime.fromtimestamp(assignment_dir.stat().st_mtime)
                        if dir_mtime < cutoff_time:
                            archive_path = self._archive_directory(assignment_dir, "submissions")
                            if archive_path:
                                archived_files.append(archive_path)
                                archived_count += 1
            
            return archived_count, archived_files
            
        except Exception as e:
            logger.error(f"归档旧文件失败: {e}")
            return 0, []
    
    def _archive_directory(self, source_dir: Path, category: str) -> Optional[str]:
        """归档目录"""
        try:
            # 生成归档路径
            now = datetime.now()
            archive_subdir = self.archive_dir / str(now.year) / f"{now.month:02d}" / category
            archive_subdir.mkdir(parents=True, exist_ok=True)
            
            # 创建压缩文件
            import zipfile
            archive_name = f"{source_dir.name}_{now.strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = archive_subdir / archive_name
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zipf.write(file_path, arcname)
            
            # 删除原目录
            shutil.rmtree(source_dir)
            
            logger.info(f"目录已归档: {source_dir} -> {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            logger.error(f"归档目录失败 {source_dir}: {e}")
            return None
    
    def _cleanup_empty_directories(self, root_dir: Path):
        """清理空目录"""
        try:
            for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
                dir_path = Path(dirpath)
                if dir_path != root_dir and not filenames and not dirnames:
                    try:
                        dir_path.rmdir()
                        logger.info(f"清理空目录: {dir_path}")
                    except OSError:
                        pass  # 目录不为空或无法删除
        except Exception as e:
            logger.warning(f"清理空目录失败: {e}")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            stats = {
                'total_size_bytes': 0,
                'total_files': 0,
                'directories': {},
                'file_types': {},
                'last_updated': datetime.now().isoformat()
            }
            
            # 统计各目录
            for dir_name in ['assignments', 'submissions', 'grading_results', 'archive', 'temp']:
                dir_path = self.base_storage_dir / dir_name
                if dir_path.exists():
                    dir_stats = self._get_directory_stats(dir_path)
                    stats['directories'][dir_name] = dir_stats
                    stats['total_size_bytes'] += dir_stats['size_bytes']
                    stats['total_files'] += dir_stats['file_count']
                    
                    # 合并文件类型统计
                    for ext, count in dir_stats['file_types'].items():
                        stats['file_types'][ext] = stats['file_types'].get(ext, 0) + count
            
            # 转换大小单位
            stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
            stats['total_size_gb'] = stats['total_size_mb'] / 1024
            
            return stats
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}
    
    def _get_directory_stats(self, directory: Path) -> Dict[str, Any]:
        """获取目录统计信息"""
        stats = {
            'size_bytes': 0,
            'file_count': 0,
            'file_types': {},
            'subdirectories': 0
        }
        
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    stats['file_count'] += 1
                    stats['size_bytes'] += item.stat().st_size
                    
                    # 统计文件类型
                    ext = item.suffix.lower() or 'no_extension'
                    stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                    
                elif item.is_dir() and item != directory:
                    stats['subdirectories'] += 1
                    
        except Exception as e:
            logger.warning(f"获取目录统计失败 {directory}: {e}")
        
        return stats
    
    def check_storage_health(self) -> Dict[str, Any]:
        """检查存储健康状况"""
        try:
            health_report = {
                'status': 'healthy',
                'issues': [],
                'warnings': [],
                'recommendations': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # 检查存储空间
            stats = self.get_storage_statistics()
            max_size_gb = self.config['max_storage_size_gb']
            
            if stats.get('total_size_gb', 0) > max_size_gb * 0.9:
                health_report['warnings'].append(f"存储空间使用率超过90%: {stats['total_size_gb']:.1f}GB / {max_size_gb}GB")
                health_report['recommendations'].append("考虑清理旧文件或增加存储空间")
            
            if stats.get('total_size_gb', 0) > max_size_gb:
                health_report['issues'].append(f"存储空间已满: {stats['total_size_gb']:.1f}GB / {max_size_gb}GB")
                health_report['status'] = 'critical'
            
            # 检查目录结构
            required_dirs = ['assignments', 'submissions', 'grading_results', 'temp']
            for dir_name in required_dirs:
                dir_path = self.base_storage_dir / dir_name
                if not dir_path.exists():
                    health_report['issues'].append(f"缺少必需目录: {dir_name}")
                    health_report['status'] = 'unhealthy'
            
            # 检查临时文件
            temp_stats = stats.get('directories', {}).get('temp', {})
            if temp_stats.get('file_count', 0) > 1000:
                health_report['warnings'].append(f"临时文件过多: {temp_stats['file_count']} 个文件")
                health_report['recommendations'].append("运行临时文件清理")
            
            # 检查配置文件
            if not self.config_file.exists():
                health_report['warnings'].append("存储配置文件不存在")
                health_report['recommendations'].append("重新生成配置文件")
            
            return health_report
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def optimize_storage(self) -> Dict[str, Any]:
        """优化存储"""
        try:
            optimization_report = {
                'actions_taken': [],
                'space_freed_mb': 0,
                'files_processed': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # 清理临时文件
            cleaned_count, cleaned_files = self.cleanup_temp_files()
            if cleaned_count > 0:
                optimization_report['actions_taken'].append(f"清理了 {cleaned_count} 个临时文件")
                optimization_report['files_processed'] += cleaned_count
            
            # 归档旧文件
            archived_count, archived_files = self.archive_old_files()
            if archived_count > 0:
                optimization_report['actions_taken'].append(f"归档了 {archived_count} 个目录")
                optimization_report['files_processed'] += archived_count
            
            # 清理空目录
            self._cleanup_empty_directories(self.base_storage_dir)
            optimization_report['actions_taken'].append("清理了空目录")
            
            # 计算释放的空间（简化计算）
            if optimization_report['files_processed'] > 0:
                # 估算每个文件平均1MB
                optimization_report['space_freed_mb'] = optimization_report['files_processed'] * 1
            
            return optimization_report
            
        except Exception as e:
            logger.error(f"存储优化失败: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """更新存储配置"""
        try:
            # 验证配置
            valid_keys = set(self.config.keys())
            for key in new_config:
                if key not in valid_keys:
                    raise ValueError(f"无效的配置项: {key}")
            
            # 更新配置
            self.config.update(new_config)
            self._save_config()
            
            logger.info("存储配置已更新")
            return True
            
        except Exception as e:
            logger.error(f"更新存储配置失败: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前存储配置"""
        return self.config.copy()
    
    def backup_storage_structure(self, backup_path: str) -> bool:
        """备份存储结构"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份配置文件
            if self.config_file.exists():
                shutil.copy2(self.config_file, backup_dir / "storage_config.json")
            
            # 备份目录结构信息
            structure_info = {
                'directories': list(self.config['directory_structure'].keys()),
                'statistics': self.get_storage_statistics(),
                'health_report': self.check_storage_health(),
                'backup_timestamp': datetime.now().isoformat()
            }
            
            with open(backup_dir / "structure_info.json", 'w', encoding='utf-8') as f:
                json.dump(structure_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"存储结构已备份到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"备份存储结构失败: {e}")
            return False
    
    def restore_storage_structure(self, backup_path: str) -> bool:
        """恢复存储结构"""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                raise FileNotFoundError(f"备份目录不存在: {backup_path}")
            
            # 恢复配置文件
            backup_config = backup_dir / "storage_config.json"
            if backup_config.exists():
                shutil.copy2(backup_config, self.config_file)
                self._load_config()
            
            # 重新初始化存储结构
            self._initialize_storage_structure()
            
            logger.info(f"存储结构已从备份恢复: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"恢复存储结构失败: {e}")
            return False