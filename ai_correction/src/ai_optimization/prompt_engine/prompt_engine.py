"""
提示词引擎核心实现

实现分层提示词架构和智能提示词组装功能。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import hashlib

from ..models.prompt_models import (
    PromptTemplate, GeneratedPrompt, PromptLayer, PromptParameter
)
from ..config.config_manager import ConfigManager


class ContextAnalyzer:
    """上下文分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, content_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析内容特征"""
        features = {
            "content_type": self._detect_content_type(content_info),
            "content_size": self._calculate_content_size(content_info),
            "complexity": self._assess_complexity(content_info),
            "language": self._detect_language(content_info),
            "domain": self._detect_domain(content_info),
            "task_type": content_info.get("task_type", "unknown")
        }
        
        self.logger.debug(f"分析内容特征: {features}")
        return features
    
    def _detect_content_type(self, content_info: Dict[str, Any]) -> str:
        """检测内容类型"""
        if "files" in content_info:
            file_types = []
            for file_info in content_info["files"]:
                if file_info.get("type"):
                    file_types.append(file_info["type"])
            
            if "image" in file_types:
                return "multimodal" if len(set(file_types)) > 1 else "image"
            elif "pdf" in file_types:
                return "pdf"
            else:
                return "text"
        
        return content_info.get("content_type", "text")
    
    def _calculate_content_size(self, content_info: Dict[str, Any]) -> int:
        """计算内容大小"""
        total_size = 0
        
        if "content" in content_info:
            total_size += len(str(content_info["content"]))
        
        if "files" in content_info:
            for file_info in content_info["files"]:
                if "size" in file_info:
                    total_size += file_info["size"]
                elif "content" in file_info:
                    total_size += len(str(file_info["content"]))
        
        return total_size
    
    def _assess_complexity(self, content_info: Dict[str, Any]) -> str:
        """评估内容复杂度"""
        size = self._calculate_content_size(content_info)
        file_count = len(content_info.get("files", []))
        
        if size > 10000 or file_count > 5:
            return "high"
        elif size > 2000 or file_count > 2:
            return "medium"
        else:
            return "low"
    
    def _detect_language(self, content_info: Dict[str, Any]) -> str:
        """检测语言"""
        # 简单的语言检测逻辑
        content = str(content_info.get("content", ""))
        
        # 检测中文字符
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(content)
        
        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "zh"
        else:
            return "en"
    
    def _detect_domain(self, content_info: Dict[str, Any]) -> str:
        """检测领域"""
        # 基于关键词检测领域
        content = str(content_info.get("content", "")).lower()
        
        domain_keywords = {
            "math": ["数学", "计算", "公式", "方程", "math", "equation", "formula"],
            "science": ["物理", "化学", "生物", "science", "physics", "chemistry"],
            "language": ["语文", "英语", "文学", "language", "literature", "essay"],
            "programming": ["代码", "程序", "编程", "code", "program", "function"],
            "general": []
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in content for keyword in keywords):
                return domain
        
        return "general"


class PromptOptimizer:
    """提示词优化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_prompt(self, prompt: str, features: Dict[str, Any], 
                       constraints: Dict[str, Any] = None) -> str:
        """优化提示词"""
        constraints = constraints or {}
        
        # 长度优化
        if constraints.get("max_length"):
            prompt = self._optimize_length(prompt, constraints["max_length"])
        
        # 复杂度优化
        if features.get("complexity") == "low":
            prompt = self._simplify_prompt(prompt)
        
        # 语言优化
        if features.get("language") == "zh":
            prompt = self._optimize_for_chinese(prompt)
        
        self.logger.debug(f"优化后的提示词长度: {len(prompt)}")
        return prompt
    
    def _optimize_length(self, prompt: str, max_length: int) -> str:
        """优化提示词长度"""
        if len(prompt) <= max_length:
            return prompt
        
        # 简单的截断策略，保留重要部分
        lines = prompt.split('\n')
        optimized_lines = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) + 1 <= max_length:
                optimized_lines.append(line)
                current_length += len(line) + 1
            else:
                break
        
        return '\n'.join(optimized_lines)
    
    def _simplify_prompt(self, prompt: str) -> str:
        """简化提示词"""
        # 移除冗余的修饰词和复杂句式
        simplified = prompt.replace("请仔细", "请")
        simplified = simplified.replace("详细地", "")
        simplified = simplified.replace("非常", "")
        return simplified
    
    def _optimize_for_chinese(self, prompt: str) -> str:
        """为中文优化提示词"""
        # 确保中文标点符号正确
        optimized = prompt.replace(".", "。")
        optimized = optimized.replace(",", "，")
        optimized = optimized.replace("?", "？")
        optimized = optimized.replace("!", "！")
        return optimized


class PromptEngine:
    """提示词引擎核心类"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """初始化提示词引擎"""
        self.config_manager = config_manager or ConfigManager()
        self.context_analyzer = ContextAnalyzer()
        self.prompt_optimizer = PromptOptimizer()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化缓存
        self._prompt_cache = {}
        self._feature_cache = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "max_prompt_length": self.config_manager.get("prompt.max_length", 8000),
            "enable_optimization": self.config_manager.get("prompt.enable_optimization", True),
            "cache_enabled": self.config_manager.get("prompt.cache_enabled", True),
            "default_language": self.config_manager.get("prompt.default_language", "zh"),
            "quality_threshold": self.config_manager.get("prompt.quality_threshold", 0.8)
        }
    
    def generate_prompt(self, template: PromptTemplate, content_info: Dict[str, Any],
                       parameters: Dict[str, Any] = None, 
                       quality_requirements: Dict[str, Any] = None) -> GeneratedPrompt:
        """生成优化的提示词"""
        parameters = parameters or {}
        quality_requirements = quality_requirements or {}
        
        try:
            # 分析内容特征
            features = self._get_content_features(content_info)
            
            # 验证参数
            param_errors = template.validate_parameters(parameters)
            if param_errors:
                raise ValueError(f"参数验证失败: {param_errors}")
            
            # 组装提示词
            prompt_content = self._assemble_prompt(template, features, parameters, quality_requirements)
            
            # 优化提示词
            if self.config["enable_optimization"]:
                constraints = {
                    "max_length": self.config["max_prompt_length"],
                    **quality_requirements
                }
                prompt_content = self.prompt_optimizer.optimize_prompt(
                    prompt_content, features, constraints
                )
            
            # 创建生成的提示词对象
            generated_prompt = GeneratedPrompt(
                template_id=template.id,
                content=prompt_content,
                parameters=parameters
            )
            
            # 缓存结果
            if self.config["cache_enabled"]:
                self._cache_prompt(generated_prompt, features)
            
            self.logger.info(f"成功生成提示词，模板ID: {template.id}, 长度: {len(prompt_content)}")
            return generated_prompt
            
        except Exception as e:
            self.logger.error(f"生成提示词失败: {str(e)}")
            raise
    
    def _get_content_features(self, content_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取内容特征（带缓存）"""
        if not self.config["cache_enabled"]:
            return self.context_analyzer.analyze(content_info)
        
        # 生成特征缓存键
        cache_key = self._generate_feature_cache_key(content_info)
        
        if cache_key in self._feature_cache:
            self.logger.debug("使用缓存的内容特征")
            return self._feature_cache[cache_key]
        
        # 分析特征并缓存
        features = self.context_analyzer.analyze(content_info)
        self._feature_cache[cache_key] = features
        
        return features
    
    def _generate_feature_cache_key(self, content_info: Dict[str, Any]) -> str:
        """生成特征缓存键"""
        # 创建内容信息的哈希
        content_str = json.dumps(content_info, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _assemble_prompt(self, template: PromptTemplate, features: Dict[str, Any],
                        parameters: Dict[str, Any], quality_requirements: Dict[str, Any]) -> str:
        """组装分层提示词"""
        prompt_parts = []
        
        # 按层次组装提示词
        for layer in PromptLayer:
            layer_content = self._build_layer_content(
                template, layer, features, parameters, quality_requirements
            )
            if layer_content:
                prompt_parts.append(layer_content)
        
        return "\n\n".join(prompt_parts)
    
    def _build_layer_content(self, template: PromptTemplate, layer: PromptLayer,
                           features: Dict[str, Any], parameters: Dict[str, Any],
                           quality_requirements: Dict[str, Any]) -> str:
        """构建指定层的内容"""
        base_content = template.get_layer_content(layer)
        if not base_content:
            return ""
        
        # 根据层类型进行特殊处理
        if layer == PromptLayer.SYSTEM:
            return self._build_system_layer(base_content, features)
        elif layer == PromptLayer.TASK:
            return self._build_task_layer(base_content, features, parameters)
        elif layer == PromptLayer.CONTEXT:
            return self._build_context_layer(base_content, features, parameters)
        elif layer == PromptLayer.FORMAT:
            return self._build_format_layer(base_content, quality_requirements)
        elif layer == PromptLayer.QUALITY:
            return self._build_quality_layer(base_content, quality_requirements)
        else:
            return self._substitute_parameters(base_content, parameters)
    
    def _build_system_layer(self, base_content: str, features: Dict[str, Any]) -> str:
        """构建系统层内容"""
        # 根据内容特征调整系统角色定义
        content = base_content
        
        if features.get("domain") != "general":
            domain_expertise = {
                "math": "数学专家",
                "science": "科学专家", 
                "language": "语言专家",
                "programming": "编程专家"
            }
            expertise = domain_expertise.get(features["domain"], "专业评估师")
            content = content.replace("AI助手", expertise)
        
        return content
    
    def _build_task_layer(self, base_content: str, features: Dict[str, Any], 
                         parameters: Dict[str, Any]) -> str:
        """构建任务层内容"""
        content = self._substitute_parameters(base_content, parameters)
        
        # 根据复杂度调整任务描述
        if features.get("complexity") == "high":
            content += "\n请特别注意处理复杂内容，确保全面分析。"
        elif features.get("complexity") == "low":
            content += "\n请保持简洁明了的分析风格。"
        
        return content
    
    def _build_context_layer(self, base_content: str, features: Dict[str, Any],
                           parameters: Dict[str, Any]) -> str:
        """构建上下文层内容"""
        content = self._substitute_parameters(base_content, parameters)
        
        # 添加内容类型说明
        content_type_desc = {
            "text": "以下是文本内容",
            "image": "以下是图像内容",
            "pdf": "以下是PDF文档内容",
            "multimodal": "以下是多模态内容（包含文本和图像）"
        }
        
        content_type = features.get("content_type", "text")
        if content_type in content_type_desc:
            content = f"{content_type_desc[content_type]}：\n\n{content}"
        
        return content
    
    def _build_format_layer(self, base_content: str, quality_requirements: Dict[str, Any]) -> str:
        """构建格式层内容"""
        content = base_content
        
        # 根据质量要求调整输出格式
        if quality_requirements.get("detailed_analysis"):
            content += "\n请提供详细的分析过程和推理步骤。"
        
        if quality_requirements.get("structured_output"):
            content += "\n请使用结构化格式输出结果。"
        
        return content
    
    def _build_quality_layer(self, base_content: str, quality_requirements: Dict[str, Any]) -> str:
        """构建质量层内容"""
        content = base_content
        
        # 添加质量控制要求
        if quality_requirements.get("consistency_check"):
            content += "\n请确保评分标准的一致性。"
        
        if quality_requirements.get("accuracy_focus"):
            content += "\n请特别注重准确性，避免主观判断。"
        
        return content
    
    def _substitute_parameters(self, content: str, parameters: Dict[str, Any]) -> str:
        """替换参数占位符"""
        for key, value in parameters.items():
            placeholder = f"{{{key}}}"
            if placeholder in content:
                content = content.replace(placeholder, str(value))
        
        return content
    
    def _cache_prompt(self, prompt: GeneratedPrompt, features: Dict[str, Any]):
        """缓存提示词"""
        cache_key = f"{prompt.template_id}_{prompt.context_hash}"
        self._prompt_cache[cache_key] = {
            "prompt": prompt,
            "features": features,
            "timestamp": datetime.now()
        }
        
        # 限制缓存大小
        if len(self._prompt_cache) > 1000:
            # 移除最旧的缓存项
            oldest_key = min(self._prompt_cache.keys(), 
                           key=lambda k: self._prompt_cache[k]["timestamp"])
            del self._prompt_cache[oldest_key]
    
    def get_cached_prompt(self, template_id: str, content_info: Dict[str, Any],
                         parameters: Dict[str, Any] = None) -> Optional[GeneratedPrompt]:
        """获取缓存的提示词"""
        if not self.config["cache_enabled"]:
            return None
        
        parameters = parameters or {}
        
        # 生成上下文哈希
        context_str = json.dumps(parameters, sort_keys=True, ensure_ascii=False)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()
        
        cache_key = f"{template_id}_{context_hash}"
        
        if cache_key in self._prompt_cache:
            cached_item = self._prompt_cache[cache_key]
            
            # 检查缓存是否过期（1小时）
            age = (datetime.now() - cached_item["timestamp"]).total_seconds()
            if age < 3600:  # 1小时
                self.logger.debug(f"使用缓存的提示词: {cache_key}")
                return cached_item["prompt"]
            else:
                # 删除过期缓存
                del self._prompt_cache[cache_key]
        
        return None
    
    def clear_cache(self):
        """清空缓存"""
        self._prompt_cache.clear()
        self._feature_cache.clear()
        self.logger.info("提示词缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "prompt_cache_size": len(self._prompt_cache),
            "feature_cache_size": len(self._feature_cache),
            "cache_enabled": self.config["cache_enabled"]
        }