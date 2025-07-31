#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批改配置服务
负责批改配置的管理、模板操作和智能推荐
"""

import json
import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from src.models.grading_config import (
    GradingConfig, GradingTemplate, ScoringRule, WeightConfig,
    SubjectType, GradeLevel, DEFAULT_TEMPLATES
)


class GradingConfigService:
    """批改配置服务"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.configs_file = os.path.join(data_dir, "grading_configs.json")
        self.templates_file = os.path.join(data_dir, "grading_templates.json")
        self.logger = logging.getLogger(__name__)
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 初始化数据文件
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """初始化数据文件"""
        # 初始化配置文件
        if not os.path.exists(self.configs_file):
            with open(self.configs_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        # 初始化模板文件
        if not os.path.exists(self.templates_file):
            templates_data = [template.to_dict() for template in DEFAULT_TEMPLATES]
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, ensure_ascii=False, indent=2)
    
    def save_config(self, config: GradingConfig) -> bool:
        """保存批改配置"""
        try:
            configs = self.load_all_configs()
            
            # 更新时间戳
            config.updated_at = datetime.now()
            
            # 查找是否已存在
            existing_index = -1
            for i, existing_config in enumerate(configs):
                if existing_config.id == config.id:
                    existing_index = i
                    break
            
            if existing_index >= 0:
                configs[existing_index] = config
            else:
                configs.append(config)
            
            # 保存到文件
            configs_data = [config.to_dict() for config in configs]
            with open(self.configs_file, 'w', encoding='utf-8') as f:
                json.dump(configs_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"批改配置已保存: {config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存批改配置失败: {e}")
            return False
    
    def load_config(self, config_id: str) -> Optional[GradingConfig]:
        """加载指定的批改配置"""
        try:
            configs = self.load_all_configs()
            for config in configs:
                if config.id == config_id:
                    return config
            return None
            
        except Exception as e:
            self.logger.error(f"加载批改配置失败: {e}")
            return None
    
    def load_all_configs(self) -> List[GradingConfig]:
        """加载所有批改配置"""
        try:
            if not os.path.exists(self.configs_file):
                return []
            
            with open(self.configs_file, 'r', encoding='utf-8') as f:
                configs_data = json.load(f)
            
            return [GradingConfig.from_dict(data) for data in configs_data]
            
        except Exception as e:
            self.logger.error(f"加载批改配置失败: {e}")
            return []
    
    def delete_config(self, config_id: str) -> bool:
        """删除批改配置"""
        try:
            configs = self.load_all_configs()
            configs = [config for config in configs if config.id != config_id]
            
            configs_data = [config.to_dict() for config in configs]
            with open(self.configs_file, 'w', encoding='utf-8') as f:
                json.dump(configs_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"批改配置已删除: {config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除批改配置失败: {e}")
            return False
    
    def save_template(self, template: GradingTemplate) -> bool:
        """保存批改模板"""
        try:
            templates = self.load_all_templates()
            
            # 查找是否已存在
            existing_index = -1
            for i, existing_template in enumerate(templates):
                if existing_template.id == template.id:
                    existing_index = i
                    break
            
            if existing_index >= 0:
                templates[existing_index] = template
            else:
                templates.append(template)
            
            # 保存到文件
            templates_data = [template.to_dict() for template in templates]
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"批改模板已保存: {template.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存批改模板失败: {e}")
            return False
    
    def load_template(self, template_id: str) -> Optional[GradingTemplate]:
        """加载指定的批改模板"""
        try:
            templates = self.load_all_templates()
            for template in templates:
                if template.id == template_id:
                    return template
            return None
            
        except Exception as e:
            self.logger.error(f"加载批改模板失败: {e}")
            return None
    
    def load_all_templates(self) -> List[GradingTemplate]:
        """加载所有批改模板"""
        try:
            if not os.path.exists(self.templates_file):
                return DEFAULT_TEMPLATES.copy()
            
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            return [GradingTemplate.from_dict(data) for data in templates_data]
            
        except Exception as e:
            self.logger.error(f"加载批改模板失败: {e}")
            return DEFAULT_TEMPLATES.copy()
    
    def get_templates_by_subject(self, subject: SubjectType) -> List[GradingTemplate]:
        """根据学科获取模板"""
        templates = self.load_all_templates()
        return [template for template in templates if template.subject == subject]
    
    def get_templates_by_grade_level(self, grade_level: GradeLevel) -> List[GradingTemplate]:
        """根据年级获取模板"""
        templates = self.load_all_templates()
        return [template for template in templates if template.grade_level == grade_level]
    
    def get_recommended_templates(self, subject: SubjectType, grade_level: GradeLevel, 
                                user_id: Optional[str] = None) -> List[GradingTemplate]:
        """获取推荐模板"""
        templates = self.load_all_templates()
        
        # 按匹配度排序
        scored_templates = []
        for template in templates:
            score = 0
            
            # 学科匹配
            if template.subject == subject:
                score += 10
            
            # 年级匹配
            if template.grade_level == grade_level:
                score += 8
            
            # 使用频率
            score += min(template.usage_count * 0.1, 5)
            
            # 公开模板优先
            if template.is_public:
                score += 2
            
            scored_templates.append((template, score))
        
        # 按分数排序并返回前5个
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        return [template for template, score in scored_templates[:5]]
    
    def create_config_from_template(self, template_id: str, config_name: str) -> Optional[GradingConfig]:
        """从模板创建配置"""
        template = self.load_template(template_id)
        if not template:
            return None
        
        # 复制模板配置
        config = GradingConfig(
            name=config_name,
            subject=template.config.subject,
            grade_level=template.config.grade_level,
            scoring_rules=[
                ScoringRule(
                    name=rule.name,
                    description=rule.description,
                    max_score=rule.max_score,
                    criteria=rule.criteria.copy(),
                    auto_grading=rule.auto_grading,
                    weight=rule.weight
                ) for rule in template.config.scoring_rules
            ],
            weight_distribution=WeightConfig(
                content_accuracy=template.config.weight_distribution.content_accuracy,
                language_quality=template.config.weight_distribution.language_quality,
                structure_logic=template.config.weight_distribution.structure_logic,
                creativity=template.config.weight_distribution.creativity
            ),
            custom_prompts=template.config.custom_prompts.copy(),
            is_template=False
        )
        
        # 增加模板使用次数
        template.usage_count += 1
        self.save_template(template)
        
        return config
    
    def validate_config(self, config: GradingConfig) -> List[str]:
        """验证配置"""
        return config.validate()
    
    def get_config_preview(self, config: GradingConfig) -> Dict[str, Any]:
        """获取配置预览信息"""
        return {
            'name': config.name,
            'subject': config.subject.value,
            'grade_level': config.grade_level.value,
            'total_score': config.get_total_score(),
            'rules_count': len(config.scoring_rules),
            'weight_distribution': config.weight_distribution.to_dict(),
            'has_custom_prompts': len(config.custom_prompts) > 0,
            'validation_errors': config.validate()
        }
    
    def export_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """导出配置"""
        config = self.load_config(config_id)
        if not config:
            return None
        
        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'config': config.to_dict()
        }
    
    def import_config(self, config_data: Dict[str, Any]) -> Optional[GradingConfig]:
        """导入配置"""
        try:
            if 'config' in config_data:
                config = GradingConfig.from_dict(config_data['config'])
                # 生成新的ID避免冲突
                config.id = str(uuid.uuid4())
                config.created_at = datetime.now()
                config.updated_at = datetime.now()
                return config
            else:
                return GradingConfig.from_dict(config_data)
                
        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return None
    
    def get_user_configs(self, user_id: str) -> List[GradingConfig]:
        """获取用户的配置"""
        configs = self.load_all_configs()
        return [config for config in configs if config.created_by == user_id]
    
    def get_recent_configs(self, user_id: Optional[str] = None, limit: int = 10) -> List[GradingConfig]:
        """获取最近使用的配置"""
        configs = self.load_all_configs()
        
        if user_id:
            configs = [config for config in configs if config.created_by == user_id]
        
        # 按更新时间排序
        configs.sort(key=lambda x: x.updated_at, reverse=True)
        
        return configs[:limit]