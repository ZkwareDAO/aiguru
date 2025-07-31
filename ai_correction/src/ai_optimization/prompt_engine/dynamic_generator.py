"""
动态提示词生成器

基于内容特征智能选择模板并生成参数化提示词。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import math
from datetime import datetime

from ..models.prompt_models import PromptTemplate, GeneratedPrompt, PromptLayer
# TemplateManager will be imported when needed to avoid circular imports
from .prompt_engine import ContextAnalyzer
from ..config.config_manager import ConfigManager


class TemplateSelector:
    """模板选择器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def select_best_template(self, templates: List[PromptTemplate], 
                           features: Dict[str, Any], 
                           requirements: Dict[str, Any] = None) -> Tuple[PromptTemplate, float]:
        """选择最佳模板"""
        requirements = requirements or {}
        
        if not templates:
            raise ValueError("没有可用的模板")
        
        best_template = None
        best_score = -1
        
        for template in templates:
            score = self._calculate_template_score(template, features, requirements)
            
            self.logger.debug(f"模板 {template.name} 得分: {score:.3f}")
            
            if score > best_score:
                best_score = score
                best_template = template
        
        if best_template is None:
            # 如果没有找到合适的模板，返回第一个
            best_template = templates[0]
            best_score = 0.5
        
        self.logger.info(f"选择模板: {best_template.name}, 得分: {best_score:.3f}")
        return best_template, best_score
    
    def _calculate_template_score(self, template: PromptTemplate, 
                                features: Dict[str, Any], 
                                requirements: Dict[str, Any]) -> float:
        """计算模板匹配分数"""
        score = 0.0
        
        # 1. 类别匹配 (权重: 0.3)
        category_score = self._calculate_category_score(template, features)
        score += category_score * 0.3
        
        # 2. 标签匹配 (权重: 0.2)
        tag_score = self._calculate_tag_score(template, features)
        score += tag_score * 0.2
        
        # 3. 性能历史 (权重: 0.25)
        performance_score = self._calculate_performance_score(template)
        score += performance_score * 0.25
        
        # 4. 复杂度匹配 (权重: 0.15)
        complexity_score = self._calculate_complexity_score(template, features)
        score += complexity_score * 0.15
        
        # 5. 需求匹配 (权重: 0.1)
        requirement_score = self._calculate_requirement_score(template, requirements)
        score += requirement_score * 0.1
        
        return min(score, 1.0)  # 确保分数不超过1
    
    def _calculate_category_score(self, template: PromptTemplate, 
                                features: Dict[str, Any]) -> float:
        """计算类别匹配分数"""
        task_type = features.get("task_type", "unknown")
        domain = features.get("domain", "general")
        
        # 精确匹配
        if template.category == task_type:
            return 1.0
        
        # 领域匹配
        if template.category == domain:
            return 0.8
        
        # 通用匹配
        if template.category == "general":
            return 0.5
        
        return 0.0
    
    def _calculate_tag_score(self, template: PromptTemplate, 
                           features: Dict[str, Any]) -> float:
        """计算标签匹配分数"""
        if not template.tags:
            return 0.5  # 没有标签的模板给中等分数
        
        feature_tags = set()
        feature_tags.add(features.get("content_type", ""))
        feature_tags.add(features.get("language", ""))
        feature_tags.add(features.get("complexity", ""))
        feature_tags.add(features.get("domain", ""))
        
        template_tags = set(template.tags)
        
        # 计算交集比例
        intersection = feature_tags & template_tags
        union = feature_tags | template_tags
        
        if not union:
            return 0.5
        
        return len(intersection) / len(union)
    
    def _calculate_performance_score(self, template: PromptTemplate) -> float:
        """计算性能分数"""
        metrics = template.performance_metrics
        
        if metrics.usage_count == 0:
            return 0.5  # 新模板给中等分数
        
        # 综合考虑成功率和质量分数
        performance = (metrics.success_rate * 0.6 + metrics.quality_score * 0.4)
        
        # 考虑使用次数的影响（使用次数越多，可信度越高）
        confidence = min(metrics.usage_count / 100, 1.0)
        
        return performance * confidence + 0.5 * (1 - confidence)
    
    def _calculate_complexity_score(self, template: PromptTemplate, 
                                  features: Dict[str, Any]) -> float:
        """计算复杂度匹配分数"""
        content_complexity = features.get("complexity", "medium")
        
        # 估算模板复杂度
        template_complexity = self._estimate_template_complexity(template)
        
        complexity_map = {"low": 1, "medium": 2, "high": 3}
        content_level = complexity_map.get(content_complexity, 2)
        template_level = complexity_map.get(template_complexity, 2)
        
        # 复杂度差异越小，分数越高
        diff = abs(content_level - template_level)
        return max(0, 1 - diff * 0.3)
    
    def _estimate_template_complexity(self, template: PromptTemplate) -> str:
        """估算模板复杂度"""
        total_length = sum(len(content) for content in template.layers.values())
        param_count = len(template.parameters)
        
        if total_length > 2000 or param_count > 10:
            return "high"
        elif total_length > 500 or param_count > 5:
            return "medium"
        else:
            return "low"
    
    def _calculate_requirement_score(self, template: PromptTemplate, 
                                   requirements: Dict[str, Any]) -> float:
        """计算需求匹配分数"""
        if not requirements:
            return 1.0
        
        score = 1.0
        
        # 检查长度要求
        if "max_length" in requirements:
            template_length = sum(len(content) for content in template.layers.values())
            if template_length > requirements["max_length"]:
                score *= 0.5
        
        # 检查其他要求
        if requirements.get("detailed_analysis") and "detailed" not in template.tags:
            score *= 0.8
        
        if requirements.get("structured_output") and "structured" not in template.tags:
            score *= 0.8
        
        return score


class ParameterGenerator:
    """参数生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_parameters(self, template: PromptTemplate, 
                          features: Dict[str, Any], 
                          content_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成模板参数"""
        parameters = {}
        
        for param in template.parameters:
            value = self._generate_parameter_value(param, features, content_info)
            parameters[param.name] = value
        
        self.logger.debug(f"生成参数: {parameters}")
        return parameters
    
    def _generate_parameter_value(self, param, features: Dict[str, Any], 
                                content_info: Dict[str, Any]) -> Any:
        """生成单个参数值"""
        # 如果内容信息中已有该参数，直接使用
        if param.name in content_info:
            return content_info[param.name]
        
        # 根据参数名称和特征生成值
        if param.name == "language":
            return features.get("language", "zh")
        elif param.name == "complexity":
            return features.get("complexity", "medium")
        elif param.name == "domain":
            return features.get("domain", "general")
        elif param.name == "content_type":
            return features.get("content_type", "text")
        elif param.name == "task_type":
            return features.get("task_type", "grading")
        elif param.name == "student_level":
            return self._infer_student_level(features, content_info)
        elif param.name == "subject":
            return self._infer_subject(features, content_info)
        else:
            # 使用默认值
            return param.default_value
    
    def _infer_student_level(self, features: Dict[str, Any], 
                           content_info: Dict[str, Any]) -> str:
        """推断学生水平"""
        # 基于内容复杂度推断
        complexity = features.get("complexity", "medium")
        
        if complexity == "high":
            return "高级"
        elif complexity == "low":
            return "初级"
        else:
            return "中级"
    
    def _infer_subject(self, features: Dict[str, Any], 
                     content_info: Dict[str, Any]) -> str:
        """推断学科"""
        domain = features.get("domain", "general")
        
        domain_subject_map = {
            "math": "数学",
            "science": "科学",
            "language": "语文",
            "programming": "计算机科学",
            "general": "通用"
        }
        
        return domain_subject_map.get(domain, "通用")


class PromptOptimizer:
    """提示词优化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_prompt_length(self, prompt: str, max_length: int = None, 
                             target_complexity: str = None) -> str:
        """优化提示词长度和复杂度"""
        if max_length and len(prompt) <= max_length:
            return prompt
        
        # 分析提示词结构
        sections = self._parse_prompt_sections(prompt)
        
        # 按重要性排序
        prioritized_sections = self._prioritize_sections(sections)
        
        # 重新组装，控制长度
        optimized_prompt = self._reassemble_prompt(
            prioritized_sections, max_length, target_complexity
        )
        
        self.logger.info(f"提示词优化: {len(prompt)} -> {len(optimized_prompt)} 字符")
        return optimized_prompt
    
    def _parse_prompt_sections(self, prompt: str) -> List[Dict[str, Any]]:
        """解析提示词段落"""
        sections = []
        lines = prompt.split('\n')
        current_section = {"type": "unknown", "content": "", "importance": 1.0}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 识别段落类型
            section_type = self._identify_section_type(line)
            
            if section_type != current_section["type"] and current_section["content"]:
                sections.append(current_section)
                current_section = {"type": section_type, "content": line, "importance": 1.0}
            else:
                current_section["content"] += "\n" + line
                current_section["type"] = section_type
        
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def _identify_section_type(self, line: str) -> str:
        """识别段落类型"""
        if any(keyword in line for keyword in ["你是", "作为", "角色"]):
            return "role"
        elif any(keyword in line for keyword in ["任务", "目标", "要求"]):
            return "task"
        elif any(keyword in line for keyword in ["格式", "输出", "结构"]):
            return "format"
        elif any(keyword in line for keyword in ["注意", "重要", "必须"]):
            return "constraint"
        elif any(keyword in line for keyword in ["例如", "示例", "比如"]):
            return "example"
        else:
            return "content"
    
    def _prioritize_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按重要性排序段落"""
        importance_map = {
            "role": 1.0,
            "task": 0.9,
            "constraint": 0.8,
            "format": 0.7,
            "content": 0.6,
            "example": 0.5
        }
        
        for section in sections:
            section["importance"] = importance_map.get(section["type"], 0.5)
        
        return sorted(sections, key=lambda x: x["importance"], reverse=True)
    
    def _reassemble_prompt(self, sections: List[Dict[str, Any]], 
                          max_length: int = None, 
                          target_complexity: str = None) -> str:
        """重新组装提示词"""
        result_parts = []
        current_length = 0
        
        for section in sections:
            content = section["content"]
            
            # 如果有长度限制
            if max_length:
                remaining_length = max_length - current_length
                if len(content) > remaining_length:
                    if remaining_length > 100:  # 至少保留100字符
                        content = content[:remaining_length-3] + "..."
                    else:
                        break
            
            # 根据目标复杂度调整内容
            if target_complexity == "low":
                content = self._simplify_content(content)
            
            result_parts.append(content)
            current_length += len(content)
        
        return "\n\n".join(result_parts)
    
    def _simplify_content(self, content: str) -> str:
        """简化内容"""
        # 移除冗余修饰词
        simplified = content.replace("请仔细", "请")
        simplified = simplified.replace("详细地", "")
        simplified = simplified.replace("非常", "")
        simplified = simplified.replace("特别", "")
        
        return simplified


class DynamicPromptGenerator:
    """动态提示词生成器"""
    
    def __init__(self, template_manager = None, 
                 config_manager: ConfigManager = None):
        """初始化动态提示词生成器"""
        if template_manager is None:
            from .template_manager import TemplateManager
            self.template_manager = TemplateManager()
        else:
            self.template_manager = template_manager
        self.config_manager = config_manager or ConfigManager()
        self.context_analyzer = ContextAnalyzer()
        self.template_selector = TemplateSelector()
        self.parameter_generator = ParameterGenerator()
        self.prompt_optimizer = PromptOptimizer()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "enable_intelligent_selection": self.config_manager.get(
                "dynamic_generator.enable_intelligent_selection", True
            ),
            "enable_parameter_generation": self.config_manager.get(
                "dynamic_generator.enable_parameter_generation", True
            ),
            "enable_length_optimization": self.config_manager.get(
                "dynamic_generator.enable_length_optimization", True
            ),
            "max_prompt_length": self.config_manager.get(
                "dynamic_generator.max_prompt_length", 8000
            ),
            "selection_threshold": self.config_manager.get(
                "dynamic_generator.selection_threshold", 0.6
            )
        }
    
    def generate_optimized_prompt(self, task_type: str, content_info: Dict[str, Any],
                                requirements: Dict[str, Any] = None,
                                user_parameters: Dict[str, Any] = None) -> GeneratedPrompt:
        """生成优化的提示词"""
        requirements = requirements or {}
        user_parameters = user_parameters or {}
        
        try:
            # 1. 分析内容特征
            features = self.context_analyzer.analyze(content_info)
            features["task_type"] = task_type
            
            # 2. 获取候选模板
            candidate_templates = self.template_manager.get_templates_by_category(task_type)
            if not candidate_templates:
                candidate_templates = self.template_manager.get_templates_by_category("general")
            
            if not candidate_templates:
                raise ValueError(f"没有找到适合任务类型 '{task_type}' 的模板")
            
            # 3. 智能选择最佳模板
            best_template, selection_score = self.template_selector.select_best_template(
                candidate_templates, features, requirements
            )
            
            # 检查选择质量
            if selection_score < self.config["selection_threshold"]:
                self.logger.warning(f"模板选择质量较低: {selection_score:.3f}")
            
            # 4. 生成参数
            generated_parameters = {}
            if self.config["enable_parameter_generation"]:
                generated_parameters = self.parameter_generator.generate_parameters(
                    best_template, features, content_info
                )
            
            # 合并用户参数
            final_parameters = {**generated_parameters, **user_parameters}
            
            # 5. 生成基础提示词
            from .prompt_engine import PromptEngine
            prompt_engine = PromptEngine(self.config_manager)
            
            base_prompt = prompt_engine.generate_prompt(
                best_template, content_info, final_parameters, requirements
            )
            
            # 6. 长度和复杂度优化
            optimized_content = base_prompt.content
            if self.config["enable_length_optimization"]:
                target_complexity = features.get("complexity", "medium")
                optimized_content = self.prompt_optimizer.optimize_prompt_length(
                    base_prompt.content, 
                    self.config["max_prompt_length"],
                    target_complexity
                )
            
            # 7. 创建最终结果
            optimized_prompt = GeneratedPrompt(
                template_id=best_template.id,
                content=optimized_content,
                parameters=final_parameters
            )
            
            # 添加生成元数据
            optimized_prompt.usage_stats = {
                "template_selection_score": selection_score,
                "original_length": len(base_prompt.content),
                "optimized_length": len(optimized_content),
                "features": features,
                "generation_method": "dynamic"
            }
            
            self.logger.info(
                f"动态生成提示词完成 - 模板: {best_template.name}, "
                f"长度: {len(optimized_content)}, 选择分数: {selection_score:.3f}"
            )
            
            return optimized_prompt
            
        except Exception as e:
            self.logger.error(f"动态生成提示词失败: {str(e)}")
            raise
    
    def batch_generate_prompts(self, requests: List[Dict[str, Any]]) -> List[GeneratedPrompt]:
        """批量生成提示词"""
        results = []
        
        for i, request in enumerate(requests):
            try:
                prompt = self.generate_optimized_prompt(
                    task_type=request.get("task_type", "general"),
                    content_info=request.get("content_info", {}),
                    requirements=request.get("requirements", {}),
                    user_parameters=request.get("parameters", {})
                )
                results.append(prompt)
                
            except Exception as e:
                self.logger.error(f"批量生成第 {i+1} 个提示词失败: {str(e)}")
                # 创建错误占位符
                error_prompt = GeneratedPrompt(
                    template_id="error",
                    content=f"生成失败: {str(e)}",
                    parameters=request.get("parameters", {})
                )
                results.append(error_prompt)
        
        self.logger.info(f"批量生成完成: {len(results)} 个提示词")
        return results
    
    def analyze_generation_quality(self, prompt: GeneratedPrompt) -> Dict[str, Any]:
        """分析生成质量"""
        analysis = {
            "length_score": self._analyze_length_quality(prompt),
            "complexity_score": self._analyze_complexity_quality(prompt),
            "structure_score": self._analyze_structure_quality(prompt),
            "parameter_score": self._analyze_parameter_quality(prompt)
        }
        
        # 计算总体质量分数
        analysis["overall_score"] = sum(analysis.values()) / len(analysis)
        
        return analysis
    
    def _analyze_length_quality(self, prompt: GeneratedPrompt) -> float:
        """分析长度质量"""
        length = len(prompt.content)
        
        # 理想长度范围
        if 1000 <= length <= 3000:
            return 1.0
        elif 500 <= length <= 5000:
            return 0.8
        elif length <= 8000:
            return 0.6
        else:
            return 0.3
    
    def _analyze_complexity_quality(self, prompt: GeneratedPrompt) -> float:
        """分析复杂度质量"""
        content = prompt.content
        
        # 计算复杂度指标
        sentence_count = len([s for s in content.split('。') if s.strip()])
        avg_sentence_length = len(content) / max(sentence_count, 1)
        
        # 理想复杂度
        if 20 <= avg_sentence_length <= 50:
            return 1.0
        elif 10 <= avg_sentence_length <= 80:
            return 0.8
        else:
            return 0.6
    
    def _analyze_structure_quality(self, prompt: GeneratedPrompt) -> float:
        """分析结构质量"""
        content = prompt.content
        
        # 检查结构元素
        has_role = any(keyword in content for keyword in ["你是", "作为"])
        has_task = any(keyword in content for keyword in ["任务", "目标"])
        has_format = any(keyword in content for keyword in ["格式", "输出"])
        
        structure_score = sum([has_role, has_task, has_format]) / 3
        return structure_score
    
    def _analyze_parameter_quality(self, prompt: GeneratedPrompt) -> float:
        """分析参数质量"""
        # 检查参数是否被正确替换
        content = prompt.content
        unresolved_params = len([m for m in content if '{' in m and '}' in m])
        
        if unresolved_params == 0:
            return 1.0
        elif unresolved_params <= 2:
            return 0.7
        else:
            return 0.4