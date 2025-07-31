"""
提示词模板管理器

实现提示词模板的创建、存储、检索和管理功能，支持模板继承、组合和版本控制。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import threading

from ..models.prompt_models import (
    PromptTemplate, PromptParameter, PerformanceMetrics, PromptLayer
)
from ..config.config_manager import ConfigManager


class TemplateStorage:
    """模板存储接口"""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "data/templates"
        self.logger = logging.getLogger(__name__)
        self._ensure_storage_path()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
    
    def save_template(self, template: PromptTemplate) -> bool:
        """保存模板"""
        try:
            file_path = os.path.join(self.storage_path, f"{template.id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"模板已保存: {template.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存模板失败: {str(e)}")
            return False
    
    def load_template(self, template_id: str) -> Optional[PromptTemplate]:
        """加载模板"""
        try:
            file_path = os.path.join(self.storage_path, f"{template_id}.json")
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return PromptTemplate.from_dict(data)
            
        except Exception as e:
            self.logger.error(f"加载模板失败: {str(e)}")
            return None
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            file_path = os.path.join(self.storage_path, f"{template_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"模板已删除: {template_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"删除模板失败: {str(e)}")
            return False
    
    def list_templates(self) -> List[str]:
        """列出所有模板ID"""
        try:
            template_ids = []
            for filename in os.listdir(self.storage_path):
                if filename.endswith('.json'):
                    template_ids.append(filename[:-5])  # 移除.json后缀
            return template_ids
            
        except Exception as e:
            self.logger.error(f"列出模板失败: {str(e)}")
            return []


class TemplateInheritance:
    """模板继承管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_inherited_template(self, parent_template: PromptTemplate,
                                child_name: str, 
                                overrides: Dict[str, Any] = None) -> PromptTemplate:
        """创建继承模板"""
        overrides = overrides or {}
        
        # 克隆父模板
        child_template = parent_template.clone(new_name=child_name)
        
        # 应用覆盖
        if "category" in overrides:
            child_template.category = overrides["category"]
        
        if "layers" in overrides:
            for layer_name, content in overrides["layers"].items():
                if layer_name in child_template.layers:
                    child_template.layers[layer_name] = content
        
        if "parameters" in overrides:
            # 合并参数
            param_dict = {p.name: p for p in child_template.parameters}
            for param_data in overrides["parameters"]:
                param = PromptParameter.from_dict(param_data)
                param_dict[param.name] = param
            child_template.parameters = list(param_dict.values())
        
        if "tags" in overrides:
            child_template.tags.extend(overrides["tags"])
            child_template.tags = list(set(child_template.tags))  # 去重
        
        self.logger.info(f"创建继承模板: {child_name} <- {parent_template.name}")
        return child_template
    
    def merge_templates(self, templates: List[PromptTemplate], 
                       merged_name: str) -> PromptTemplate:
        """合并多个模板"""
        if not templates:
            raise ValueError("至少需要一个模板进行合并")
        
        # 以第一个模板为基础
        base_template = templates[0]
        merged_template = base_template.clone(new_name=merged_name)
        
        # 合并其他模板的内容
        for template in templates[1:]:
            # 合并层内容
            for layer_name, content in template.layers.items():
                if layer_name in merged_template.layers:
                    # 如果层已存在，追加内容
                    merged_template.layers[layer_name] += f"\n\n{content}"
                else:
                    # 如果层不存在，直接添加
                    merged_template.layers[layer_name] = content
            
            # 合并参数
            existing_param_names = {p.name for p in merged_template.parameters}
            for param in template.parameters:
                if param.name not in existing_param_names:
                    merged_template.parameters.append(param)
            
            # 合并标签
            merged_template.tags.extend(template.tags)
        
        # 去重标签
        merged_template.tags = list(set(merged_template.tags))
        
        self.logger.info(f"合并模板完成: {merged_name} <- {[t.name for t in templates]}")
        return merged_template


class TemplateVersionControl:
    """模板版本控制"""
    
    def __init__(self, storage: TemplateStorage):
        self.storage = storage
        self.logger = logging.getLogger(__name__)
    
    def create_version(self, template: PromptTemplate, 
                      version_notes: str = "") -> PromptTemplate:
        """创建新版本"""
        # 解析当前版本号
        current_version = template.version
        version_parts = current_version.split('.')
        
        # 增加小版本号
        if len(version_parts) >= 3:
            version_parts[2] = str(int(version_parts[2]) + 1)
        else:
            version_parts.append("1")
        
        new_version = '.'.join(version_parts)
        
        # 创建新版本模板
        new_template = template.clone(new_version=new_version)
        new_template.id = f"{template.id}_v{new_version.replace('.', '_')}"
        
        # 保存版本信息
        if "version_history" not in new_template.usage_stats:
            new_template.usage_stats["version_history"] = []
        
        new_template.usage_stats["version_history"].append({
            "version": new_version,
            "created_at": datetime.now().isoformat(),
            "notes": version_notes,
            "parent_version": current_version
        })
        
        self.logger.info(f"创建模板版本: {template.name} v{new_version}")
        return new_template
    
    def get_version_history(self, template: PromptTemplate) -> List[Dict[str, Any]]:
        """获取版本历史"""
        return template.usage_stats.get("version_history", [])
    
    def rollback_to_version(self, template_id: str, target_version: str) -> Optional[PromptTemplate]:
        """回滚到指定版本"""
        # 构造版本化的模板ID
        version_id = f"{template_id}_v{target_version.replace('.', '_')}"
        
        # 加载目标版本
        target_template = self.storage.load_template(version_id)
        if not target_template:
            self.logger.error(f"未找到版本 {target_version} 的模板")
            return None
        
        # 创建新的当前版本
        current_template = target_template.clone()
        current_template.id = template_id  # 恢复原始ID
        
        self.logger.info(f"回滚模板到版本: {target_version}")
        return current_template


class TemplatePerformanceTracker:
    """模板性能跟踪器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._performance_cache = {}
        self._cache_lock = threading.Lock()
    
    def record_usage(self, template_id: str, response_time: float, 
                    success: bool, quality_score: float):
        """记录使用情况"""
        with self._cache_lock:
            if template_id not in self._performance_cache:
                self._performance_cache[template_id] = PerformanceMetrics()
            
            self._performance_cache[template_id].update(
                response_time, success, quality_score
            )
    
    def get_performance_metrics(self, template_id: str) -> Optional[PerformanceMetrics]:
        """获取性能指标"""
        with self._cache_lock:
            return self._performance_cache.get(template_id)
    
    def get_top_performing_templates(self, limit: int = 10) -> List[Tuple[str, PerformanceMetrics]]:
        """获取性能最佳的模板"""
        with self._cache_lock:
            # 按综合分数排序
            sorted_templates = sorted(
                self._performance_cache.items(),
                key=lambda x: x[1].quality_score * x[1].success_rate,
                reverse=True
            )
            
            return sorted_templates[:limit]
    
    def generate_performance_report(self, template_ids: List[str] = None) -> Dict[str, Any]:
        """生成性能报告"""
        with self._cache_lock:
            if template_ids is None:
                template_ids = list(self._performance_cache.keys())
            
            report = {
                "total_templates": len(template_ids),
                "templates": {},
                "summary": {
                    "avg_response_time": 0.0,
                    "avg_success_rate": 0.0,
                    "avg_quality_score": 0.0,
                    "total_usage": 0
                }
            }
            
            total_response_time = 0
            total_success_rate = 0
            total_quality_score = 0
            total_usage = 0
            
            for template_id in template_ids:
                if template_id in self._performance_cache:
                    metrics = self._performance_cache[template_id]
                    report["templates"][template_id] = metrics.to_dict()
                    
                    total_response_time += metrics.avg_response_time
                    total_success_rate += metrics.success_rate
                    total_quality_score += metrics.quality_score
                    total_usage += metrics.usage_count
            
            # 计算平均值
            count = len([tid for tid in template_ids if tid in self._performance_cache])
            if count > 0:
                report["summary"]["avg_response_time"] = total_response_time / count
                report["summary"]["avg_success_rate"] = total_success_rate / count
                report["summary"]["avg_quality_score"] = total_quality_score / count
            
            report["summary"]["total_usage"] = total_usage
            
            return report


class TemplateManager:
    """提示词模板管理器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """初始化模板管理器"""
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化组件
        self.storage = TemplateStorage(self.config["storage_path"])
        self.inheritance = TemplateInheritance()
        self.version_control = TemplateVersionControl(self.storage)
        self.performance_tracker = TemplatePerformanceTracker()
        
        # 模板缓存
        self._template_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_expiry = {}
        
        # 初始化基础模板
        self._initialize_base_templates()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "storage_path": self.config_manager.get(
                "template_manager.storage_path", "data/templates"
            ),
            "cache_enabled": self.config_manager.get(
                "template_manager.cache_enabled", True
            ),
            "cache_ttl": self.config_manager.get(
                "template_manager.cache_ttl", 3600
            ),
            "auto_create_base_templates": self.config_manager.get(
                "template_manager.auto_create_base_templates", True
            )
        }
    
    def _initialize_base_templates(self):
        """初始化基础模板"""
        if not self.config["auto_create_base_templates"]:
            return
        
        base_templates = self._create_base_templates()
        
        for template in base_templates:
            if not self.get_template(template.id):
                self.save_template(template)
                self.logger.info(f"创建基础模板: {template.name}")
    
    def _create_base_templates(self) -> List[PromptTemplate]:
        """创建基础模板"""
        templates = []
        
        # 1. 通用批改模板
        grading_template = PromptTemplate(
            id="base_grading",
            name="通用批改模板",
            category="grading",
            layers={
                PromptLayer.SYSTEM.value: """你是一位专业的教师和评估专家，具有丰富的教学经验和严谨的评分标准。
你的任务是对学生的作业进行客观、公正、准确的批改和评分。""",
                
                PromptLayer.TASK.value: """请根据提供的标准答案和评分标准，对学生的答案进行详细批改。
任务要求：
1. 仔细比较学生答案与标准答案
2. 根据评分标准给出准确分数
3. 指出答案中的错误和不足
4. 提供具体的改进建议""",
                
                PromptLayer.CONTEXT.value: """批改材料：
标准答案：{standard_answer}
学生答案：{student_answer}
评分标准：{grading_criteria}
总分：{total_score}""",
                
                PromptLayer.FORMAT.value: """请按以下格式输出批改结果：

**得分：** [具体分数]/[总分]

**详细分析：**
[对答案的详细分析，包括正确之处和错误之处]

**主要问题：**
1. [问题1]
2. [问题2]
...

**改进建议：**
1. [建议1]
2. [建议2]
...""",
                
                PromptLayer.QUALITY.value: """质量要求：
1. 评分必须严格按照标准，不得主观臆断
2. 分析要客观公正，有理有据
3. 建议要具体可行，有助于学生提高
4. 语言要专业准确，态度要鼓励支持"""
            },
            parameters=[
                PromptParameter("standard_answer", "str", "", "标准答案"),
                PromptParameter("student_answer", "str", "", "学生答案"),
                PromptParameter("grading_criteria", "str", "", "评分标准"),
                PromptParameter("total_score", "int", 100, "总分")
            ],
            tags=["grading", "general", "structured"]
        )
        templates.append(grading_template)
        
        # 2. 数学批改模板
        math_template = PromptTemplate(
            id="math_grading",
            name="数学批改模板",
            category="math",
            layers={
                PromptLayer.SYSTEM.value: """你是一位数学教师和专家，精通各个层次的数学知识，具有丰富的数学教学和评估经验。
你擅长分析数学解题过程，能够准确识别计算错误、逻辑错误和方法问题。""",
                
                PromptLayer.TASK.value: """请对学生的数学答案进行专业批改：
1. 检查计算过程的准确性
2. 评估解题方法的合理性
3. 分析逻辑推理的正确性
4. 评价答案的完整性和规范性
5. 根据评分标准给出准确分数""",
                
                PromptLayer.CONTEXT.value: """数学题目：{question}
标准解答：{standard_solution}
学生解答：{student_solution}
评分要点：{scoring_points}
总分：{total_score}""",
                
                PromptLayer.FORMAT.value: """请按以下格式输出批改结果：

**得分：** [具体分数]/[总分]

**解题过程分析：**
[分步骤分析学生的解题过程]

**计算检查：**
[检查计算的准确性]

**方法评价：**
[评价解题方法的优劣]

**主要错误：**
1. [错误类型] - [具体错误]
2. [错误类型] - [具体错误]

**改进建议：**
1. [针对性建议]
2. [学习方法建议]""",
                
                PromptLayer.QUALITY.value: """数学批改要求：
1. 计算检查要逐步进行，不能遗漏
2. 方法评价要考虑多种解法的可能性
3. 错误分类要准确（计算错误、概念错误、方法错误等）
4. 建议要有针对性，帮助学生理解数学概念"""
            },
            parameters=[
                PromptParameter("question", "str", "", "数学题目"),
                PromptParameter("standard_solution", "str", "", "标准解答"),
                PromptParameter("student_solution", "str", "", "学生解答"),
                PromptParameter("scoring_points", "str", "", "评分要点"),
                PromptParameter("total_score", "int", 100, "总分")
            ],
            tags=["math", "calculation", "logic", "detailed"]
        )
        templates.append(math_template)
        
        # 3. 语文批改模板
        language_template = PromptTemplate(
            id="language_grading",
            name="语文批改模板", 
            category="language",
            layers={
                PromptLayer.SYSTEM.value: """你是一位语文教师和文学专家，具有深厚的语言文字功底和丰富的语文教学经验。
你擅长分析文章的内容、结构、语言表达和文学手法。""",
                
                PromptLayer.TASK.value: """请对学生的语文作业进行全面批改：
1. 评价内容的准确性和深度
2. 分析结构的合理性和逻辑性
3. 检查语言表达的规范性和流畅性
4. 评估文学理解和表达能力
5. 根据评分标准给出综合分数""",
                
                PromptLayer.CONTEXT.value: """题目要求：{question_requirement}
参考答案：{reference_answer}
学生答案：{student_answer}
评分标准：{grading_standard}
总分：{total_score}""",
                
                PromptLayer.FORMAT.value: """请按以下格式输出批改结果：

**得分：** [具体分数]/[总分]

**内容分析：**
[分析答案内容的准确性和完整性]

**结构评价：**
[评价文章结构和逻辑]

**语言表达：**
[评价语言的规范性和表达效果]

**亮点总结：**
[指出答案中的优秀之处]

**改进建议：**
1. [内容方面的建议]
2. [表达方面的建议]
3. [结构方面的建议]""",
                
                PromptLayer.QUALITY.value: """语文批改要求：
1. 注重内容理解的准确性和深度
2. 关注语言表达的规范性和美感
3. 评价要兼顾知识性和文学性
4. 建议要有助于提高语文素养"""
            },
            parameters=[
                PromptParameter("question_requirement", "str", "", "题目要求"),
                PromptParameter("reference_answer", "str", "", "参考答案"),
                PromptParameter("student_answer", "str", "", "学生答案"),
                PromptParameter("grading_standard", "str", "", "评分标准"),
                PromptParameter("total_score", "int", 100, "总分")
            ],
            tags=["language", "literature", "expression", "comprehensive"]
        )
        templates.append(language_template)
        
        # 4. 简化批改模板（用于复杂度较低的内容）
        simple_template = PromptTemplate(
            id="simple_grading",
            name="简化批改模板",
            category="simple",
            layers={
                PromptLayer.SYSTEM.value: """你是一位教师，负责对学生作业进行批改。""",
                
                PromptLayer.TASK.value: """请对比学生答案和标准答案，给出分数和简要评价。""",
                
                PromptLayer.CONTEXT.value: """标准答案：{standard_answer}
学生答案：{student_answer}
总分：{total_score}""",
                
                PromptLayer.FORMAT.value: """**得分：** [分数]/[总分]
**评价：** [简要评价]
**建议：** [改进建议]""",
                
                PromptLayer.QUALITY.value: """要求简洁明了，重点突出。"""
            },
            parameters=[
                PromptParameter("standard_answer", "str", "", "标准答案"),
                PromptParameter("student_answer", "str", "", "学生答案"),
                PromptParameter("total_score", "int", 100, "总分")
            ],
            tags=["simple", "quick", "basic"]
        )
        templates.append(simple_template)
        
        return templates
    
    def save_template(self, template: PromptTemplate) -> bool:
        """保存模板"""
        try:
            # 保存到存储
            success = self.storage.save_template(template)
            
            if success:
                # 更新缓存
                with self._cache_lock:
                    self._template_cache[template.id] = template
                    self._cache_expiry[template.id] = datetime.now() + timedelta(
                        seconds=self.config["cache_ttl"]
                    )
                
                self.logger.info(f"模板已保存: {template.name} ({template.id})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"保存模板失败: {str(e)}")
            return False
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        # 检查缓存
        if self.config["cache_enabled"]:
            with self._cache_lock:
                if template_id in self._template_cache:
                    # 检查缓存是否过期
                    if datetime.now() < self._cache_expiry.get(template_id, datetime.min):
                        return self._template_cache[template_id]
                    else:
                        # 清除过期缓存
                        del self._template_cache[template_id]
                        if template_id in self._cache_expiry:
                            del self._cache_expiry[template_id]
        
        # 从存储加载
        template = self.storage.load_template(template_id)
        
        if template and self.config["cache_enabled"]:
            # 更新缓存
            with self._cache_lock:
                self._template_cache[template_id] = template
                self._cache_expiry[template_id] = datetime.now() + timedelta(
                    seconds=self.config["cache_ttl"]
                )
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            # 从存储删除
            success = self.storage.delete_template(template_id)
            
            if success:
                # 从缓存删除
                with self._cache_lock:
                    if template_id in self._template_cache:
                        del self._template_cache[template_id]
                    if template_id in self._cache_expiry:
                        del self._cache_expiry[template_id]
                
                self.logger.info(f"模板已删除: {template_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除模板失败: {str(e)}")
            return False
    
    def list_templates(self, category: str = None, 
                      active_only: bool = True) -> List[PromptTemplate]:
        """列出模板"""
        template_ids = self.storage.list_templates()
        templates = []
        
        for template_id in template_ids:
            template = self.get_template(template_id)
            if template:
                # 过滤条件
                if active_only and not template.is_active:
                    continue
                if category and template.category != category:
                    continue
                
                templates.append(template)
        
        # 按名称排序
        templates.sort(key=lambda t: t.name)
        return templates
    
    def get_templates_by_category(self, category: str) -> List[PromptTemplate]:
        """按类别获取模板"""
        return self.list_templates(category=category)
    
    def search_templates(self, query: str, 
                        search_fields: List[str] = None) -> List[PromptTemplate]:
        """搜索模板"""
        search_fields = search_fields or ["name", "category", "tags"]
        query = query.lower()
        
        all_templates = self.list_templates(active_only=False)
        matching_templates = []
        
        for template in all_templates:
            # 检查各个字段
            if "name" in search_fields and query in template.name.lower():
                matching_templates.append(template)
                continue
            
            if "category" in search_fields and query in template.category.lower():
                matching_templates.append(template)
                continue
            
            if "tags" in search_fields:
                for tag in template.tags:
                    if query in tag.lower():
                        matching_templates.append(template)
                        break
        
        return matching_templates
    
    def create_inherited_template(self, parent_id: str, child_name: str,
                                overrides: Dict[str, Any] = None) -> Optional[PromptTemplate]:
        """创建继承模板"""
        parent_template = self.get_template(parent_id)
        if not parent_template:
            self.logger.error(f"父模板不存在: {parent_id}")
            return None
        
        child_template = self.inheritance.create_inherited_template(
            parent_template, child_name, overrides
        )
        
        # 保存子模板
        if self.save_template(child_template):
            return child_template
        else:
            return None
    
    def merge_templates(self, template_ids: List[str], 
                       merged_name: str) -> Optional[PromptTemplate]:
        """合并模板"""
        templates = []
        for template_id in template_ids:
            template = self.get_template(template_id)
            if template:
                templates.append(template)
            else:
                self.logger.warning(f"模板不存在，跳过: {template_id}")
        
        if not templates:
            self.logger.error("没有有效的模板可以合并")
            return None
        
        merged_template = self.inheritance.merge_templates(templates, merged_name)
        
        # 保存合并后的模板
        if self.save_template(merged_template):
            return merged_template
        else:
            return None
    
    def create_template_version(self, template_id: str, 
                              version_notes: str = "") -> Optional[PromptTemplate]:
        """创建模板版本"""
        template = self.get_template(template_id)
        if not template:
            self.logger.error(f"模板不存在: {template_id}")
            return None
        
        new_version = self.version_control.create_version(template, version_notes)
        
        # 保存新版本
        if self.save_template(new_version):
            return new_version
        else:
            return None
    
    def record_template_usage(self, template_id: str, response_time: float,
                            success: bool, quality_score: float):
        """记录模板使用情况"""
        self.performance_tracker.record_usage(
            template_id, response_time, success, quality_score
        )
        
        # 更新模板的性能指标
        template = self.get_template(template_id)
        if template:
            template.performance_metrics.update(response_time, success, quality_score)
            self.save_template(template)
    
    def get_template_performance(self, template_id: str) -> Optional[PerformanceMetrics]:
        """获取模板性能指标"""
        return self.performance_tracker.get_performance_metrics(template_id)
    
    def get_performance_report(self, template_ids: List[str] = None) -> Dict[str, Any]:
        """获取性能报告"""
        return self.performance_tracker.generate_performance_report(template_ids)
    
    def get_optimization_suggestions(self, template_id: str) -> List[str]:
        """获取优化建议"""
        template = self.get_template(template_id)
        if not template:
            return ["模板不存在"]
        
        suggestions = []
        metrics = self.get_template_performance(template_id)
        
        if metrics:
            # 基于性能指标生成建议
            if metrics.success_rate < 0.8:
                suggestions.append("成功率较低，建议检查模板的参数设置和格式要求")
            
            if metrics.quality_score < 0.7:
                suggestions.append("质量分数较低，建议优化提示词内容和结构")
            
            if metrics.avg_response_time > 10:
                suggestions.append("响应时间较长，建议简化提示词或优化参数")
        
        # 基于模板内容生成建议
        total_length = sum(len(content) for content in template.layers.values())
        if total_length > 5000:
            suggestions.append("模板内容较长，建议精简不必要的描述")
        
        if len(template.parameters) > 15:
            suggestions.append("参数过多，建议合并相关参数或使用默认值")
        
        if not template.tags:
            suggestions.append("建议添加标签以便更好地分类和搜索")
        
        return suggestions if suggestions else ["模板表现良好，暂无优化建议"]
    
    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._template_cache.clear()
            self._cache_expiry.clear()
        
        self.logger.info("模板缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._cache_lock:
            return {
                "cached_templates": len(self._template_cache),
                "cache_enabled": self.config["cache_enabled"],
                "cache_ttl": self.config["cache_ttl"]
            }