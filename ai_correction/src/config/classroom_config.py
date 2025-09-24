#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级批改系统配置管理
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GradingTemplateType(Enum):
    """批改模板类型"""
    GENERAL = "general"
    MATH = "math"
    LANGUAGE = "language"
    SCIENCE = "science"
    ESSAY = "essay"
    CODE = "code"


@dataclass
class GradingTemplate:
    """批改模板配置"""
    id: str
    name: str
    type: GradingTemplateType
    description: str
    criteria: List[Dict[str, Any]]
    scoring_method: str = "weighted"
    max_score: float = 100.0
    ai_model: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 2000
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GradingTemplate':
        """从字典创建"""
        data['type'] = GradingTemplateType(data['type'])
        return cls(**data)


@dataclass
class FileStorageConfig:
    """文件存储配置"""
    base_path: str
    max_file_size_mb: int
    allowed_extensions: List[str]
    scan_enabled: bool
    retention_days: int
    backup_enabled: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileStorageConfig':
        """从字典创建"""
        return cls(**data)


@dataclass
class AIEngineConfig:
    """AI批改引擎配置"""
    default_model: str
    fallback_models: List[str]
    timeout_seconds: int
    max_retries: int
    confidence_threshold: float
    batch_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIEngineConfig':
        """从字典创建"""
        return cls(**data)


class ClassroomConfigManager:
    """班级批改配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.templates_file = self.config_dir / "grading_templates.json"
        self.storage_file = self.config_dir / "file_storage.yaml"
        self.ai_engine_file = self.config_dir / "ai_engine.yaml"
        
        # 缓存
        self._templates_cache: Optional[Dict[str, GradingTemplate]] = None
        self._storage_config_cache: Optional[FileStorageConfig] = None
        self._ai_engine_config_cache: Optional[AIEngineConfig] = None
        
        self.logger = logging.getLogger(f"{__name__}.ClassroomConfigManager")
        
        # 初始化默认配置
        self._ensure_default_configs()
    
    def _ensure_default_configs(self):
        """确保默认配置文件存在"""
        if not self.templates_file.exists():
            self._create_default_templates()
        
        if not self.storage_file.exists():
            self._create_default_storage_config()
        
        if not self.ai_engine_file.exists():
            self._create_default_ai_engine_config()
    
    def _create_default_templates(self):
        """创建默认批改模板"""
        default_templates = {
            "general": GradingTemplate(
                id="general",
                name="通用批改模板",
                type=GradingTemplateType.GENERAL,
                description="适用于大多数作业类型的通用批改模板",
                criteria=[
                    {
                        "name": "内容准确性",
                        "weight": 0.4,
                        "description": "答案内容的准确性和完整性"
                    },
                    {
                        "name": "逻辑清晰度",
                        "weight": 0.3,
                        "description": "思路逻辑的清晰度和条理性"
                    },
                    {
                        "name": "表达规范性",
                        "weight": 0.2,
                        "description": "语言表达的规范性和准确性"
                    },
                    {
                        "name": "创新性",
                        "weight": 0.1,
                        "description": "思路的创新性和独特性"
                    }
                ]
            ),
            "math": GradingTemplate(
                id="math",
                name="数学作业模板",
                type=GradingTemplateType.MATH,
                description="专门用于数学作业的批改模板",
                criteria=[
                    {
                        "name": "计算准确性",
                        "weight": 0.5,
                        "description": "计算过程和结果的准确性"
                    },
                    {
                        "name": "解题步骤",
                        "weight": 0.3,
                        "description": "解题步骤的完整性和逻辑性"
                    },
                    {
                        "name": "公式运用",
                        "weight": 0.2,
                        "description": "公式的正确运用和理解"
                    }
                ]
            ),
            "essay": GradingTemplate(
                id="essay",
                name="作文批改模板",
                type=GradingTemplateType.ESSAY,
                description="专门用于作文和写作类作业的批改模板",
                criteria=[
                    {
                        "name": "主题明确性",
                        "weight": 0.25,
                        "description": "主题是否明确，论点是否清晰"
                    },
                    {
                        "name": "结构完整性",
                        "weight": 0.25,
                        "description": "文章结构是否完整，层次是否清晰"
                    },
                    {
                        "name": "语言表达",
                        "weight": 0.25,
                        "description": "语言表达的准确性和流畅性"
                    },
                    {
                        "name": "创意和深度",
                        "weight": 0.25,
                        "description": "内容的创意性和思考深度"
                    }
                ]
            )
        }
        
        # 转换为字典格式并保存
        templates_dict = {
            template_id: template.to_dict() 
            for template_id, template in default_templates.items()
        }
        
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(templates_dict, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"已创建默认批改模板配置: {self.templates_file}")
    
    def _create_default_storage_config(self):
        """创建默认文件存储配置"""
        default_config = FileStorageConfig(
            base_path="uploads",
            max_file_size_mb=100,
            allowed_extensions=[
                ".pdf", ".doc", ".docx", ".txt", ".md",
                ".jpg", ".jpeg", ".png", ".gif", ".json"
            ],
            scan_enabled=True,
            retention_days=365,
            backup_enabled=True
        )
        
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"已创建默认文件存储配置: {self.storage_file}")
    
    def _create_default_ai_engine_config(self):
        """创建默认AI引擎配置"""
        default_config = AIEngineConfig(
            default_model="gpt-3.5-turbo",
            fallback_models=["gpt-4", "claude-3-sonnet"],
            timeout_seconds=120,
            max_retries=3,
            confidence_threshold=0.8,
            batch_size=5
        )
        
        with open(self.ai_engine_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"已创建默认AI引擎配置: {self.ai_engine_file}")
    
    def get_grading_templates(self) -> Dict[str, GradingTemplate]:
        """获取所有批改模板"""
        if self._templates_cache is None:
            self._load_grading_templates()
        return self._templates_cache
    
    def _load_grading_templates(self):
        """加载批改模板"""
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            self._templates_cache = {
                template_id: GradingTemplate.from_dict(template_data)
                for template_id, template_data in templates_data.items()
            }
            
            self.logger.info(f"已加载 {len(self._templates_cache)} 个批改模板")
            
        except Exception as e:
            self.logger.error(f"加载批改模板失败: {e}")
            self._templates_cache = {}
    
    def get_grading_template(self, template_id: str) -> Optional[GradingTemplate]:
        """获取指定的批改模板"""
        templates = self.get_grading_templates()
        return templates.get(template_id)
    
    def save_grading_template(self, template: GradingTemplate):
        """保存批改模板"""
        templates = self.get_grading_templates()
        templates[template.id] = template
        
        # 转换为字典格式并保存
        templates_dict = {
            template_id: template.to_dict() 
            for template_id, template in templates.items()
        }
        
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(templates_dict, f, ensure_ascii=False, indent=2)
        
        # 更新缓存
        self._templates_cache = templates
        
        self.logger.info(f"已保存批改模板: {template.id}")
    
    def delete_grading_template(self, template_id: str) -> bool:
        """删除批改模板"""
        templates = self.get_grading_templates()
        
        if template_id not in templates:
            return False
        
        del templates[template_id]
        
        # 保存更新后的模板
        templates_dict = {
            template_id: template.to_dict() 
            for template_id, template in templates.items()
        }
        
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(templates_dict, f, ensure_ascii=False, indent=2)
        
        # 更新缓存
        self._templates_cache = templates
        
        self.logger.info(f"已删除批改模板: {template_id}")
        return True
    
    def get_file_storage_config(self) -> FileStorageConfig:
        """获取文件存储配置"""
        if self._storage_config_cache is None:
            self._load_file_storage_config()
        return self._storage_config_cache
    
    def _load_file_storage_config(self):
        """加载文件存储配置"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self._storage_config_cache = FileStorageConfig.from_dict(config_data)
            self.logger.info("已加载文件存储配置")
            
        except Exception as e:
            self.logger.error(f"加载文件存储配置失败: {e}")
            self._storage_config_cache = FileStorageConfig(
                base_path="uploads",
                max_file_size_mb=100,
                allowed_extensions=[".pdf", ".doc", ".docx", ".txt"],
                scan_enabled=True,
                retention_days=365,
                backup_enabled=True
            )
    
    def save_file_storage_config(self, config: FileStorageConfig):
        """保存文件存储配置"""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        # 更新缓存
        self._storage_config_cache = config
        
        self.logger.info("已保存文件存储配置")
    
    def get_ai_engine_config(self) -> AIEngineConfig:
        """获取AI引擎配置"""
        if self._ai_engine_config_cache is None:
            self._load_ai_engine_config()
        return self._ai_engine_config_cache
    
    def _load_ai_engine_config(self):
        """加载AI引擎配置"""
        try:
            with open(self.ai_engine_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self._ai_engine_config_cache = AIEngineConfig.from_dict(config_data)
            self.logger.info("已加载AI引擎配置")
            
        except Exception as e:
            self.logger.error(f"加载AI引擎配置失败: {e}")
            self._ai_engine_config_cache = AIEngineConfig(
                default_model="gpt-3.5-turbo",
                fallback_models=["gpt-4"],
                timeout_seconds=120,
                max_retries=3,
                confidence_threshold=0.8,
                batch_size=5
            )
    
    def save_ai_engine_config(self, config: AIEngineConfig):
        """保存AI引擎配置"""
        with open(self.ai_engine_file, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        # 更新缓存
        self._ai_engine_config_cache = config
        
        self.logger.info("已保存AI引擎配置")
    
    def reload_all_configs(self):
        """重新加载所有配置"""
        self._templates_cache = None
        self._storage_config_cache = None
        self._ai_engine_config_cache = None
        
        self.logger.info("已清空配置缓存，将在下次访问时重新加载")
    
    def validate_config(self) -> Dict[str, List[str]]:
        """验证配置的有效性"""
        errors = {
            "templates": [],
            "storage": [],
            "ai_engine": []
        }
        
        # 验证批改模板
        try:
            templates = self.get_grading_templates()
            for template_id, template in templates.items():
                if not template.criteria:
                    errors["templates"].append(f"模板 {template_id} 缺少评分标准")
                
                total_weight = sum(criterion.get("weight", 0) for criterion in template.criteria)
                if abs(total_weight - 1.0) > 0.01:
                    errors["templates"].append(f"模板 {template_id} 权重总和不等于1.0: {total_weight}")
        
        except Exception as e:
            errors["templates"].append(f"加载模板时出错: {e}")
        
        # 验证文件存储配置
        try:
            storage_config = self.get_file_storage_config()
            if storage_config.max_file_size_mb <= 0:
                errors["storage"].append("文件大小限制必须大于0")
            
            if not storage_config.allowed_extensions:
                errors["storage"].append("必须指定允许的文件扩展名")
        
        except Exception as e:
            errors["storage"].append(f"加载存储配置时出错: {e}")
        
        # 验证AI引擎配置
        try:
            ai_config = self.get_ai_engine_config()
            if ai_config.timeout_seconds <= 0:
                errors["ai_engine"].append("超时时间必须大于0")
            
            if ai_config.confidence_threshold < 0 or ai_config.confidence_threshold > 1:
                errors["ai_engine"].append("置信度阈值必须在0-1之间")
        
        except Exception as e:
            errors["ai_engine"].append(f"加载AI引擎配置时出错: {e}")
        
        return errors


# 全局配置管理器实例
_config_manager: Optional[ClassroomConfigManager] = None


def get_classroom_config_manager() -> ClassroomConfigManager:
    """获取班级配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ClassroomConfigManager()
    return _config_manager


def reset_classroom_config_manager():
    """重置配置管理器（主要用于测试）"""
    global _config_manager
    _config_manager = None