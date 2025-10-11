"""Complexity Assessor - 任务复杂度评估."""

import logging
from typing import Dict

from app.agents.state import GradingState

logger = logging.getLogger(__name__)


class ComplexityAssessor:
    """任务复杂度评估器
    
    根据多个因素评估批改任务的复杂度,用于选择合适的Agent组合
    
    复杂度等级:
    - simple: 简单任务 (分数 < 30) - 使用快速模式
    - medium: 中等任务 (分数 30-70) - 使用标准模式
    - complex: 复杂任务 (分数 > 70) - 使用完整模式
    """
    
    def __init__(self):
        """初始化评估器"""
        logger.info("ComplexityAssessor initialized")
    
    def assess(self, state: GradingState) -> str:
        """评估任务复杂度
        
        Args:
            state: 当前批改状态
            
        Returns:
            复杂度等级: "simple" | "medium" | "complex"
        """
        try:
            # 提取复杂度因素
            factors = self._extract_factors(state)
            
            # 计算复杂度分数
            score = self._calculate_complexity_score(factors)
            
            # 确定复杂度等级
            if score < 30:
                complexity = "simple"
            elif score < 70:
                complexity = "medium"
            else:
                complexity = "complex"
            
            logger.info(
                f"Complexity assessed: {complexity} (score={score}, "
                f"files={factors['file_count']}, "
                f"length={factors['text_length']}, "
                f"questions={factors['question_count']})"
            )
            
            return complexity
            
        except Exception as e:
            logger.error(f"Failed to assess complexity: {e}")
            # 默认返回medium
            return "medium"
    
    def _extract_factors(self, state: GradingState) -> Dict:
        """提取复杂度因素
        
        Args:
            state: 当前批改状态
            
        Returns:
            复杂度因素字典
        """
        preprocessed_files = state.get("preprocessed_files", [])
        extracted_text = state.get("extracted_text", "")
        config = state.get("config", {})
        
        return {
            # 文件数量
            "file_count": len(preprocessed_files),
            
            # 文本长度
            "text_length": len(extracted_text),
            
            # 题目数量 (从配置中获取,或根据文本估算)
            "question_count": config.get("question_count", self._estimate_question_count(extracted_text)),
            
            # 是否包含图片
            "has_images": any(f.get("type") == "image" for f in preprocessed_files),
            
            # 学科
            "subject": config.get("subject", "").lower(),
            
            # 年级
            "grade_level": config.get("grade_level", ""),
            
            # 是否需要OCR
            "needs_ocr": any(f.get("needs_ocr", False) for f in preprocessed_files),
        }
    
    def _estimate_question_count(self, text: str) -> int:
        """估算题目数量
        
        Args:
            text: 文本内容
            
        Returns:
            估算的题目数量
        """
        # 简单的启发式方法
        # 查找常见的题目标记
        import re
        
        patterns = [
            r'第\s*[一二三四五六七八九十\d]+\s*题',
            r'\d+\s*[.、)]',
            r'[（(]\s*\d+\s*[）)]',
        ]
        
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            count = max(count, len(matches))
        
        # 如果没有找到明显的题目标记,根据长度估算
        if count == 0:
            # 假设每500字符一道题
            count = max(1, len(text) // 500)
        
        return count
    
    def _calculate_complexity_score(self, factors: Dict) -> int:
        """计算复杂度分数
        
        Args:
            factors: 复杂度因素
            
        Returns:
            复杂度分数 (0-100)
        """
        score = 0
        
        # 1. 文件数量 (0-20分)
        file_count = factors["file_count"]
        if file_count == 1:
            score += 0
        elif file_count <= 3:
            score += 10
        else:
            score += 20
        
        # 2. 文本长度 (0-30分)
        text_length = factors["text_length"]
        if text_length < 500:
            score += 0
        elif text_length < 2000:
            score += 15
        else:
            score += 30
        
        # 3. 题目数量 (0-20分)
        question_count = factors["question_count"]
        if question_count <= 3:
            score += 0
        elif question_count <= 10:
            score += 10
        else:
            score += 20
        
        # 4. 是否包含图片 (0-15分)
        if factors["has_images"]:
            score += 15
        
        # 5. 学科难度 (0-15分)
        difficult_subjects = [
            "数学", "math", "mathematics",
            "物理", "physics",
            "化学", "chemistry",
            "编程", "programming", "code",
        ]
        subject = factors["subject"]
        if any(s in subject for s in difficult_subjects):
            score += 15
        
        # 6. 是否需要OCR (0-10分)
        if factors["needs_ocr"]:
            score += 10
        
        # 确保分数在0-100范围内
        score = min(max(score, 0), 100)
        
        return score
    
    def get_recommended_mode(self, complexity: str) -> str:
        """根据复杂度推荐批改模式
        
        Args:
            complexity: 复杂度等级
            
        Returns:
            推荐的批改模式
        """
        mode_mapping = {
            "simple": "fast",
            "medium": "standard",
            "complex": "premium",
        }
        return mode_mapping.get(complexity, "standard")

