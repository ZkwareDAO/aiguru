"""
内容优化器

实现智能内容压缩、大小控制、图像质量优化和文本摘要功能，
确保内容符合API调用的大小限制要求。
"""

import os
import io
import re
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image, ImageOps
import base64

from ..config.config_manager import ConfigManager
from ..models.api_models import ModelConfig, TaskType


logger = logging.getLogger(__name__)


@dataclass
class ContentItem:
    """内容项"""
    content_type: str  # text, image, pdf, mixed
    content: Union[str, bytes]
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    original_size: Optional[int] = None
    compression_ratio: float = 1.0
    
    def __post_init__(self):
        if self.original_size is None:
            self.original_size = self.size


@dataclass
class ProcessedContent:
    """处理后的内容"""
    items: List[ContentItem] = field(default_factory=list)
    total_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.total_size = sum(item.size for item in self.items)
    
    @property
    def text_items(self) -> List[ContentItem]:
        """获取文本内容项"""
        return [item for item in self.items if item.content_type == 'text']
    
    @property
    def image_items(self) -> List[ContentItem]:
        """获取图像内容项"""
        return [item for item in self.items if item.content_type == 'image']
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        total_original = sum(item.original_size or item.size for item in self.items)
        total_compressed = self.total_size
        
        return {
            'original_size': total_original,
            'compressed_size': total_compressed,
            'compression_ratio': total_compressed / total_original if total_original > 0 else 1.0,
            'space_saved': total_original - total_compressed,
            'items_count': len(self.items)
        }


@dataclass
class OptimizedContent:
    """优化后的内容"""
    processed_content: ProcessedContent
    optimization_applied: List[str] = field(default_factory=list)
    api_compatible: bool = True
    estimated_tokens: int = 0
    optimization_metadata: Dict[str, Any] = field(default_factory=dict)


class ContentOptimizer:
    """内容优化器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化内容优化器"""
        self.config_manager = config_manager or ConfigManager()
        self._load_config()
        
        # 初始化压缩器
        self.text_compressor = TextCompressor(self.config)
        self.image_compressor = ImageCompressor(self.config)
        self.size_controller = SizeController(self.config)
        
        logger.info("内容优化器初始化完成")
    
    def _load_config(self):
        """加载配置"""
        self.config = {
            'max_file_size': self.config_manager.get(
                'ai_optimization.content_processor.max_file_size', 20 * 1024 * 1024
            ),
            'max_image_size': self.config_manager.get(
                'ai_optimization.content_processor.max_image_size', 5 * 1024 * 1024
            ),
            'max_text_length': self.config_manager.get(
                'ai_optimization.content_processor.max_text_length', 50000
            ),
            'compression_quality': self.config_manager.get(
                'ai_optimization.content_processor.compression_quality', 85
            ),
            'text_summary_ratio': self.config_manager.get(
                'ai_optimization.content_processor.text_summary_ratio', 0.3
            ),
            'enable_aggressive_compression': self.config_manager.get(
                'ai_optimization.content_processor.enable_aggressive_compression', False
            )
        }
    
    def optimize_for_api(self, content: ProcessedContent, 
                        model_config: ModelConfig,
                        task_type: TaskType = TaskType.GRADING) -> OptimizedContent:
        """为API调用优化内容"""
        logger.info(f"开始为API优化内容，原始大小: {content.total_size} bytes")
        
        optimizations_applied = []
        optimization_metadata = {
            'original_size': content.total_size,
            'model_limits': {
                'max_content_size': model_config.max_content_size,
                'max_tokens': model_config.max_tokens
            },
            'task_type': task_type.value,
            'optimization_start_time': datetime.now().isoformat()
        }
        
        # 创建优化后的内容副本
        optimized_content = ProcessedContent(
            items=[self._copy_content_item(item) for item in content.items],
            metadata=content.metadata.copy()
        )
        
        # 1. 检查是否需要优化
        if not self._needs_optimization(optimized_content, model_config):
            logger.info("内容无需优化")
            return OptimizedContent(
                processed_content=optimized_content,
                optimization_applied=[],
                api_compatible=True,
                estimated_tokens=self._estimate_tokens(optimized_content),
                optimization_metadata=optimization_metadata
            )
        
        # 2. 应用大小控制
        if optimized_content.total_size > model_config.max_content_size:
            optimized_content = self.size_controller.control_size(
                optimized_content, model_config.max_content_size
            )
            optimizations_applied.append("size_control")
        
        # 3. 优化文本内容
        text_optimized = False
        for item in optimized_content.text_items:
            if len(item.content) > self.config['max_text_length']:
                original_length = len(item.content)
                item.content = self.text_compressor.compress_text(
                    item.content, self.config['max_text_length']
                )
                item.size = len(item.content.encode('utf-8'))
                item.compression_ratio = item.size / (item.original_size or item.size)
                text_optimized = True
                
                logger.info(f"文本压缩: {original_length} -> {len(item.content)} 字符")
        
        if text_optimized:
            optimizations_applied.append("text_compression")
        
        # 4. 优化图像内容
        image_optimized = False
        for item in optimized_content.image_items:
            if item.size > self.config['max_image_size']:
                original_size = item.size
                item.content = self.image_compressor.compress_image(
                    item.content, self.config['max_image_size']
                )
                item.size = len(item.content)
                item.compression_ratio = item.size / (item.original_size or item.size)
                image_optimized = True
                
                logger.info(f"图像压缩: {original_size} -> {item.size} bytes")
        
        if image_optimized:
            optimizations_applied.append("image_compression")
        
        # 5. 重新计算总大小
        optimized_content.total_size = sum(item.size for item in optimized_content.items)
        
        # 6. 估算token数量并进行token优化
        estimated_tokens = self._estimate_tokens(optimized_content)
        
        if estimated_tokens > model_config.max_tokens:
            optimized_content = self._optimize_for_tokens(
                optimized_content, model_config.max_tokens
            )
            estimated_tokens = self._estimate_tokens(optimized_content)
            optimizations_applied.append("token_optimization")
        
        # 7. 最终检查和激进优化
        if (optimized_content.total_size > model_config.max_content_size or 
            estimated_tokens > model_config.max_tokens):
            if self.config['enable_aggressive_compression']:
                optimized_content = self._apply_aggressive_optimization(
                    optimized_content, model_config
                )
                estimated_tokens = self._estimate_tokens(optimized_content)
                optimizations_applied.append("aggressive_compression")
            else:
                logger.warning(f"内容仍超过限制 - 大小: {optimized_content.total_size} > {model_config.max_content_size}, "
                             f"tokens: {estimated_tokens} > {model_config.max_tokens}")
        
        # 8. 更新优化元数据
        optimization_metadata.update({
            'optimized_size': optimized_content.total_size,
            'compression_stats': optimized_content.get_compression_stats(),
            'estimated_tokens': estimated_tokens,
            'optimization_end_time': datetime.now().isoformat(),
            'optimizations_applied': optimizations_applied
        })
        
        api_compatible = (
            optimized_content.total_size <= model_config.max_content_size and
            estimated_tokens <= model_config.max_tokens
        )
        
        logger.info(f"内容优化完成，最终大小: {optimized_content.total_size} bytes, "
                   f"API兼容: {api_compatible}")
        
        return OptimizedContent(
            processed_content=optimized_content,
            optimization_applied=optimizations_applied,
            api_compatible=api_compatible,
            estimated_tokens=estimated_tokens,
            optimization_metadata=optimization_metadata
        )
    
    def _needs_optimization(self, content: ProcessedContent, model_config: ModelConfig) -> bool:
        """检查是否需要优化"""
        # 检查总大小
        if content.total_size > model_config.max_content_size:
            return True
        
        # 检查文本长度
        for item in content.text_items:
            if len(item.content) > self.config['max_text_length']:
                return True
        
        # 检查图像大小
        for item in content.image_items:
            if item.size > self.config['max_image_size']:
                return True
        
        # 检查估算的token数量
        estimated_tokens = self._estimate_tokens(content)
        if estimated_tokens > model_config.max_tokens:
            return True
        
        return False
    
    def _copy_content_item(self, item: ContentItem) -> ContentItem:
        """复制内容项"""
        return ContentItem(
            content_type=item.content_type,
            content=item.content,
            size=item.size,
            metadata=item.metadata.copy(),
            original_size=item.original_size,
            compression_ratio=item.compression_ratio
        )
    
    def _apply_aggressive_optimization(self, content: ProcessedContent, 
                                     model_config: ModelConfig) -> ProcessedContent:
        """应用激进优化策略"""
        logger.info("应用激进优化策略")
        
        target_size = int(model_config.max_content_size * 0.8)  # 目标为限制的80%
        
        # 1. 进一步压缩文本
        for item in content.text_items:
            if content.total_size > target_size:
                reduction_ratio = min(0.5, target_size / content.total_size)
                target_length = int(len(item.content) * reduction_ratio)
                item.content = self.text_compressor.aggressive_compress(
                    item.content, target_length
                )
                item.size = len(item.content.encode('utf-8'))
        
        # 2. 进一步压缩图像
        for item in content.image_items:
            if content.total_size > target_size:
                target_image_size = int(item.size * 0.5)  # 压缩到50%
                item.content = self.image_compressor.aggressive_compress(
                    item.content, target_image_size
                )
                item.size = len(item.content)
        
        # 3. 重新计算总大小
        content.total_size = sum(item.size for item in content.items)
        
        return content
    
    def _optimize_for_tokens(self, content: ProcessedContent, max_tokens: int) -> ProcessedContent:
        """基于token限制优化内容"""
        logger.info(f"基于token限制优化内容，目标: {max_tokens} tokens")
        
        current_tokens = self._estimate_tokens(content)
        if current_tokens <= max_tokens:
            return content
        
        # 计算需要减少的token比例
        reduction_ratio = max_tokens / current_tokens
        
        # 优先压缩文本内容（因为文本token更容易控制）
        for item in content.text_items:
            if current_tokens > max_tokens:
                # 计算该文本项的token数
                item_tokens = self._estimate_text_tokens(item.content)
                target_tokens = int(item_tokens * reduction_ratio)
                
                # 根据token数量压缩文本
                target_length = self._estimate_length_from_tokens(target_tokens)
                item.content = self.text_compressor.compress_text(item.content, target_length)
                item.size = len(item.content.encode('utf-8'))
                
                # 重新计算当前token数
                current_tokens = self._estimate_tokens(content)
        
        # 如果还是超过限制，压缩图像
        for item in content.image_items:
            if current_tokens > max_tokens:
                # 图像压缩以减少token
                current_image_tokens = self._estimate_image_tokens(item.size)
                target_image_tokens = int(current_image_tokens * 0.7)  # 减少30%
                target_size = self._estimate_size_from_image_tokens(target_image_tokens)
                
                item.content = self.image_compressor.compress_image(item.content, target_size)
                item.size = len(item.content)
                
                # 重新计算当前token数
                current_tokens = self._estimate_tokens(content)
        
        # 重新计算总大小
        content.total_size = sum(item.size for item in content.items)
        
        return content
    
    def _estimate_text_tokens(self, text: str) -> int:
        """估算单个文本的token数量"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        numbers = len(re.findall(r'\d+', text))
        punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))
        
        tokens = int(
            chinese_chars * 1.0 + 
            english_words * 1.3 + 
            numbers * 0.5 + 
            punctuation * 0.3
        )
        
        return int(tokens * 1.1)  # 添加基础开销
    
    def _estimate_image_tokens(self, image_size: int) -> int:
        """估算单个图像的token数量"""
        size_kb = image_size / 1024
        
        if size_kb < 10:
            return int(100 + size_kb * 10)
        elif size_kb < 100:
            return int(200 + (size_kb - 10) * 3)
        else:
            return int(500 + min((size_kb - 100) * 2, 500))
    
    def _estimate_length_from_tokens(self, target_tokens: int) -> int:
        """根据目标token数估算文本长度"""
        # 假设平均每个token对应1.2个字符（中英文混合）
        return int(target_tokens * 1.2)
    
    def _estimate_size_from_image_tokens(self, target_tokens: int) -> int:
        """根据目标token数估算图像大小"""
        # 反向计算图像大小
        if target_tokens <= 200:
            size_kb = (target_tokens - 100) / 10
        elif target_tokens <= 470:
            size_kb = 10 + (target_tokens - 200) / 3
        else:
            size_kb = 100 + (target_tokens - 500) / 2
        
        return max(1024, int(size_kb * 1024))  # 至少1KB
    
    def _estimate_tokens(self, content: ProcessedContent) -> int:
        """估算token数量"""
        total_tokens = 0
        
        for item in content.items:
            if item.content_type == 'text':
                # 改进的文本token估算
                text = item.content
                
                # 计算中文字符数
                chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
                
                # 计算英文单词数
                english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
                
                # 计算数字和符号
                numbers = len(re.findall(r'\d+', text))
                punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))
                
                # 更精确的token估算
                # 中文字符：1个字符 ≈ 1个token
                # 英文单词：1个单词 ≈ 1.3个token（考虑子词分割）
                # 数字：1个数字 ≈ 0.5个token
                # 标点符号：1个符号 ≈ 0.3个token
                tokens = int(
                    chinese_chars * 1.0 + 
                    english_words * 1.3 + 
                    numbers * 0.5 + 
                    punctuation * 0.3
                )
                
                # 添加基础开销（格式化、结构等）
                tokens = int(tokens * 1.1)
                
                total_tokens += tokens
                
            elif item.content_type == 'image':
                # 改进的图像token估算
                # 基于图像大小和复杂度的更精确估算
                # 小图像（<10KB）：约100-200 tokens
                # 中等图像（10-100KB）：约200-500 tokens  
                # 大图像（>100KB）：约500-1000 tokens
                size_kb = item.size / 1024
                
                if size_kb < 10:
                    tokens = int(100 + size_kb * 10)
                elif size_kb < 100:
                    tokens = int(200 + (size_kb - 10) * 3)
                else:
                    tokens = int(500 + min((size_kb - 100) * 2, 500))
                
                total_tokens += tokens
        
        return total_tokens
    
    def get_optimization_stats(self, optimized_content: OptimizedContent) -> Dict[str, Any]:
        """获取优化统计信息"""
        stats = optimized_content.processed_content.get_compression_stats()
        stats.update({
            'optimizations_applied': optimized_content.optimization_applied,
            'api_compatible': optimized_content.api_compatible,
            'estimated_tokens': optimized_content.estimated_tokens,
            'optimization_metadata': optimized_content.optimization_metadata
        })
        return stats


class TextCompressor:
    """文本压缩器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.summary_ratio = config.get('text_summary_ratio', 0.3)
    
    def compress_text(self, text: str, max_length: int) -> str:
        """压缩文本到指定长度"""
        if len(text) <= max_length:
            return text
        
        logger.info(f"压缩文本: {len(text)} -> {max_length} 字符")
        
        # 1. 首先尝试移除多余的空白字符
        compressed = self._remove_excessive_whitespace(text)
        
        if len(compressed) <= max_length:
            return compressed
        
        # 2. 尝试智能摘要
        compressed = self._intelligent_summarize(compressed, max_length)
        
        if len(compressed) <= max_length:
            return compressed
        
        # 3. 最后截断
        return self._smart_truncate(compressed, max_length)
    
    def aggressive_compress(self, text: str, target_length: int) -> str:
        """激进压缩文本"""
        logger.info(f"激进压缩文本: {len(text)} -> {target_length} 字符")
        
        # 1. 移除所有多余内容
        compressed = self._remove_redundant_content(text)
        
        # 2. 提取关键信息
        compressed = self._extract_key_information(compressed, target_length)
        
        # 3. 确保不超过目标长度
        if len(compressed) > target_length:
            compressed = compressed[:target_length]
        
        return compressed
    
    def _remove_excessive_whitespace(self, text: str) -> str:
        """移除多余的空白字符"""
        # 移除多余的空行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # 移除行首行尾空白
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # 移除多余的空格
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _intelligent_summarize(self, text: str, max_length: int) -> str:
        """智能摘要"""
        # 简单的摘要策略：保留重要句子
        sentences = self._split_sentences(text)
        
        if not sentences:
            return text[:max_length]
        
        # 计算每个句子的重要性分数
        sentence_scores = self._calculate_sentence_scores(sentences)
        
        # 按分数排序并选择重要句子
        sorted_sentences = sorted(
            zip(sentences, sentence_scores), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 选择句子直到达到长度限制
        selected_sentences = []
        current_length = 0
        
        for sentence, score in sorted_sentences:
            if current_length + len(sentence) <= max_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        # 按原始顺序重新排列
        result_sentences = []
        for sentence in sentences:
            if sentence in selected_sentences:
                result_sentences.append(sentence)
        
        return ''.join(result_sentences)
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """智能截断"""
        if len(text) <= max_length:
            return text
        
        # 尝试在句子边界截断
        sentences = self._split_sentences(text)
        result = ""
        
        for sentence in sentences:
            if len(result + sentence) <= max_length:
                result += sentence
            else:
                break
        
        # 如果结果太短，直接截断
        if len(result) < max_length * 0.8:
            result = text[:max_length]
        
        return result
    
    def _remove_redundant_content(self, text: str) -> str:
        """移除冗余内容"""
        # 移除重复的句子
        sentences = self._split_sentences(text)
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            sentence_key = self._normalize_sentence(sentence)
            if sentence_key not in seen:
                unique_sentences.append(sentence)
                seen.add(sentence_key)
        
        return ''.join(unique_sentences)
    
    def _extract_key_information(self, text: str, target_length: int) -> str:
        """提取关键信息"""
        # 识别关键词和短语
        key_patterns = [
            r'分数[：:]\s*\d+',  # 分数
            r'得分[：:]\s*\d+',  # 得分
            r'错误[：:].*?[。\n]',  # 错误描述
            r'建议[：:].*?[。\n]',  # 建议
            r'优点[：:].*?[。\n]',  # 优点
            r'缺点[：:].*?[。\n]',  # 缺点
        ]
        
        key_content = []
        for pattern in key_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            key_content.extend(matches)
        
        # 组合关键内容
        result = ' '.join(key_content)
        
        # 如果关键内容不足，补充原文
        if len(result) < target_length * 0.5:
            remaining_length = target_length - len(result)
            additional_text = text[:remaining_length]
            result = result + ' ' + additional_text
        
        return result[:target_length]
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 简单的句子分割
        sentences = re.split(r'[。！？\n]', text)
        return [s.strip() + '。' for s in sentences if s.strip()]
    
    def _calculate_sentence_scores(self, sentences: List[str]) -> List[float]:
        """计算句子重要性分数"""
        scores = []
        
        # 重要关键词
        important_keywords = [
            '分数', '得分', '错误', '正确', '建议', '改进', 
            '优点', '缺点', '问题', '解答', '答案'
        ]
        
        for sentence in sentences:
            score = 0.0
            
            # 基于关键词的分数
            for keyword in important_keywords:
                if keyword in sentence:
                    score += 1.0
            
            # 基于长度的分数（适中长度的句子更重要）
            length_score = 1.0 - abs(len(sentence) - 50) / 100
            score += max(0, length_score)
            
            # 基于位置的分数（开头和结尾的句子更重要）
            # 这里简化处理，实际应用中可以根据句子在文本中的位置调整
            
            scores.append(score)
        
        return scores
    
    def _normalize_sentence(self, sentence: str) -> str:
        """标准化句子用于去重"""
        # 移除标点和空白，转换为小写
        normalized = re.sub(r'[^\w\s]', '', sentence.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized


class ImageCompressor:
    """图像压缩器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.quality = config.get('compression_quality', 85)
    
    def compress_image(self, image_data: bytes, max_size: int) -> bytes:
        """压缩图像到指定大小"""
        if len(image_data) <= max_size:
            return image_data
        
        logger.info(f"压缩图像: {len(image_data)} -> {max_size} bytes")
        
        try:
            # 解码图像
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式（如果需要）
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # 1. 首先尝试调整质量
            compressed = self._compress_by_quality(image, max_size)
            
            if len(compressed) <= max_size:
                return compressed
            
            # 2. 尝试调整尺寸
            compressed = self._compress_by_size(image, max_size)
            
            return compressed
            
        except Exception as e:
            logger.error(f"图像压缩失败: {e}")
            # 如果压缩失败，返回截断的原始数据
            return image_data[:max_size]
    
    def aggressive_compress(self, image_data: bytes, target_size: int) -> bytes:
        """激进压缩图像"""
        logger.info(f"激进压缩图像: {len(image_data)} -> {target_size} bytes")
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # 大幅降低质量和尺寸
            quality = 30  # 低质量
            scale_factor = 0.5  # 缩小到50%
            
            # 调整尺寸
            new_width = int(image.width * scale_factor)
            new_height = int(image.height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 压缩
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_data = output.getvalue()
            
            # 如果仍然太大，继续降低质量
            while len(compressed_data) > target_size and quality > 10:
                quality -= 5
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_data = output.getvalue()
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"激进图像压缩失败: {e}")
            return image_data[:target_size]
    
    def _compress_by_quality(self, image: Image.Image, max_size: int) -> bytes:
        """通过调整质量压缩图像"""
        quality = self.quality
        
        while quality > 10:
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_data = output.getvalue()
            
            if len(compressed_data) <= max_size:
                return compressed_data
            
            quality -= 10
        
        # 最低质量
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=10, optimize=True)
        return output.getvalue()
    
    def _compress_by_size(self, image: Image.Image, max_size: int) -> bytes:
        """通过调整尺寸压缩图像"""
        scale_factor = 0.9
        current_image = image.copy()
        
        while scale_factor > 0.1:
            new_width = int(image.width * scale_factor)
            new_height = int(image.height * scale_factor)
            
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            resized_image.save(output, format='JPEG', quality=self.quality, optimize=True)
            compressed_data = output.getvalue()
            
            if len(compressed_data) <= max_size:
                return compressed_data
            
            scale_factor -= 0.1
        
        # 最小尺寸
        min_width = max(50, int(image.width * 0.1))
        min_height = max(50, int(image.height * 0.1))
        
        resized_image = image.resize((min_width, min_height), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        resized_image.save(output, format='JPEG', quality=30, optimize=True)
        return output.getvalue()


class SizeController:
    """大小控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def control_size(self, content: ProcessedContent, max_size: int) -> ProcessedContent:
        """控制内容总大小"""
        if content.total_size <= max_size:
            return content
        
        logger.info(f"控制内容大小: {content.total_size} -> {max_size} bytes")
        
        # 计算压缩比例
        compression_ratio = max_size / content.total_size
        
        # 按优先级分配大小
        text_priority = 0.7  # 文本内容优先级更高
        image_priority = 0.3
        
        text_budget = int(max_size * text_priority)
        image_budget = int(max_size * image_priority)
        
        # 压缩文本内容
        text_items = content.text_items
        if text_items:
            total_text_size = sum(item.size for item in text_items)
            if total_text_size > text_budget:
                self._redistribute_text_size(text_items, text_budget)
        
        # 压缩图像内容
        image_items = content.image_items
        if image_items:
            total_image_size = sum(item.size for item in image_items)
            if total_image_size > image_budget:
                self._redistribute_image_size(image_items, image_budget)
        
        # 重新计算总大小
        content.total_size = sum(item.size for item in content.items)
        
        return content
    
    def _redistribute_text_size(self, text_items: List[ContentItem], budget: int):
        """重新分配文本大小"""
        if not text_items:
            return
        
        # 按重要性排序（这里简化为按大小排序）
        text_items.sort(key=lambda x: x.size, reverse=True)
        
        # 平均分配预算
        per_item_budget = budget // len(text_items)
        
        for item in text_items:
            if item.size > per_item_budget:
                # 截断文本
                text = item.content
                if isinstance(text, str):
                    # 按字符截断
                    char_ratio = per_item_budget / item.size
                    target_chars = int(len(text) * char_ratio)
                    item.content = text[:target_chars]
                    item.size = len(item.content.encode('utf-8'))
    
    def _redistribute_image_size(self, image_items: List[ContentItem], budget: int):
        """重新分配图像大小"""
        if not image_items:
            return
        
        # 平均分配预算
        per_item_budget = budget // len(image_items)
        
        for item in image_items:
            if item.size > per_item_budget:
                # 截断图像数据（简化处理）
                item.content = item.content[:per_item_budget]
                item.size = len(item.content)