"""Unified Grading Agent - 一次LLM调用完成批改+反馈."""

import json
import logging
import re
from typing import Dict

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from app.core.config import settings
from app.agents.state import GradingState

logger = logging.getLogger(__name__)


class UnifiedGradingAgent:
    """统一批改Agent
    
    核心优化: 将批改和反馈生成合并到一次LLM调用中
    成本: ~$0.010 (vs 原设计的 $0.013)
    节省: 23%
    """
    
    def __init__(self):
        """初始化Agent"""
        # 使用OpenRouter API (成本更低)
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            openai_api_key=api_key,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        
        self.prompt_template = self._create_prompt_template()
        
        logger.info(f"UnifiedGradingAgent initialized with model: {settings.DEFAULT_MODEL}")
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """创建统一提示词模板"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的教师,正在批改学生作业。

请一次性完成以下所有任务:
1. 批改评分 - 找出错误,计算分数
2. 错误分析 - 详细说明每个错误
3. 总体反馈 - 优点、不足、改进建议
4. 知识点关联 - 相关知识点和学习建议

重要: 请严格按照JSON格式输出,不要添加任何额外的文字说明或markdown标记。"""),
            ("user", "{grading_prompt}")
        ])
    
    async def process(self, state: GradingState) -> GradingState:
        """执行统一批改
        
        Args:
            state: 当前批改状态
            
        Returns:
            更新后的批改状态
        """
        try:
            logger.info(f"UnifiedGradingAgent processing submission {state['submission_id']}")
            
            # 1. 构建提示词
            prompt = self._build_grading_prompt(state)
            
            # 2. 调用LLM (这是唯一的API调用)
            messages = self.prompt_template.format_messages(grading_prompt=prompt)
            response = await self.llm.ainvoke(messages)
            
            logger.debug(f"LLM response: {response.content[:200]}...")
            
            # 3. 解析结果
            result = self._parse_result(response.content)
            
            # 4. 更新状态
            state["score"] = result["score"]
            state["confidence"] = result["confidence"]
            state["errors"] = result["errors"]
            state["feedback_text"] = result["overall_comment"]
            state["suggestions"] = result["suggestions"]
            state["knowledge_points"] = result.get("knowledge_points", [])
            state["status"] = "completed"
            
            logger.info(
                f"Grading completed: score={result['score']}, "
                f"confidence={result['confidence']:.2f}, "
                f"errors={len(result['errors'])}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"UnifiedGradingAgent error: {str(e)}", exc_info=True)
            state["status"] = "failed"
            state["error_message"] = f"批改失败: {str(e)}"
            return state
    
    def _build_grading_prompt(self, state: GradingState) -> str:
        """构建批改提示词
        
        这个提示词设计为一次性完成所有任务,减少API调用次数
        """
        grading_standard = state["config"].get("grading_standard", {})
        strictness = state["config"].get("strictness", "standard")
        max_score = state["max_score"]
        
        # 严格程度说明
        strictness_desc = {
            "loose": "宽松 - 对小错误容忍度高",
            "standard": "标准 - 按照常规标准批改",
            "strict": "严格 - 对细节要求高"
        }.get(strictness, "标准")
        
        prompt = f"""
【批改任务】
请批改以下学生作业,并提供完整的反馈。

【批改标准】
{grading_standard.get('criteria', '请根据标准答案批改,找出学生答案中的错误')}

【标准答案】
{grading_standard.get('answer', '(未提供标准答案,请根据常识判断)')}

【学生答案】
{state['extracted_text']}

【批改要求】
- 满分: {max_score}分
- 严格程度: {strictness_desc}
- 请逐项对照标准答案,找出学生答案中的所有错误
- 对每个错误,请说明:
  * 错误类型 (概念错误/计算错误/表述错误/遗漏等)
  * 错误位置 (具体在哪一部分)
  * 错误原因和说明
  * 正确答案应该是什么
  * 严重程度 (high/medium/low)
  * 建议扣分
- 请给出总体评价,包括优点和不足
- 请提供3-5条具体的改进建议
- 请关联相关知识点并评估掌握程度

【输出格式】
请严格按照以下JSON格式输出,不要添加任何markdown标记或额外文字:

{{
    "score": 分数(0-{max_score}的数字),
    "confidence": 置信度(0-1之间的小数),
    "errors": [
        {{
            "type": "错误类型",
            "location": "错误位置描述",
            "description": "详细的错误说明",
            "correct_answer": "正确答案",
            "severity": "high或medium或low",
            "deduction": 扣分(数字)
        }}
    ],
    "overall_comment": "总体评价(100-200字)",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["改进建议1", "改进建议2", "改进建议3"],
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "mastery_level": 掌握程度(0-100的整数),
            "suggestion": "针对该知识点的学习建议"
        }}
    ]
}}
"""
        return prompt.strip()
    
    def _parse_result(self, content: str) -> Dict:
        """解析LLM返回结果
        
        Args:
            content: LLM返回的文本内容
            
        Returns:
            解析后的字典
            
        Raises:
            ValueError: 如果无法解析JSON
        """
        try:
            # 尝试直接解析JSON
            result = json.loads(content)
            return self._validate_result(result)
            
        except json.JSONDecodeError:
            # 如果解析失败,尝试提取JSON部分
            logger.warning("Failed to parse JSON directly, trying to extract...")
            
            # 移除可能的markdown标记
            content = content.replace("```json", "").replace("```", "")
            
            # 尝试找到JSON对象
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return self._validate_result(result)
                except json.JSONDecodeError:
                    pass
            
            # 如果还是失败,返回默认结果
            logger.error(f"Failed to parse LLM response: {content[:500]}")
            raise ValueError("无法解析LLM响应为有效的JSON格式")
    
    def _validate_result(self, result: Dict) -> Dict:
        """验证并补全结果
        
        确保所有必需字段都存在
        """
        # 必需字段
        required_fields = ["score", "confidence", "errors"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"缺少必需字段: {field}")
        
        # 可选字段的默认值
        result.setdefault("overall_comment", "批改完成")
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("suggestions", [])
        result.setdefault("knowledge_points", [])
        
        # 验证数据类型
        if not isinstance(result["score"], (int, float)):
            result["score"] = float(result["score"])
        
        if not isinstance(result["confidence"], (int, float)):
            result["confidence"] = float(result["confidence"])
        
        if not isinstance(result["errors"], list):
            result["errors"] = []
        
        return result

