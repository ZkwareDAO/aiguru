"""RubricInterpreter node for LangGraph grading workflow."""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error
from app.core.ai_grading_engine import call_ai_api_async, process_file_content

logger = logging.getLogger(__name__)


class RubricInterpreter:
    """
    Interprets marking schemes and creates structured rubrics.
    
    Responsibilities:
    - Parse marking scheme files
    - Extract grading criteria
    - Create structured rubric schema
    - Generate evaluation guidelines
    """
    
    def __init__(self):
        """Initialize RubricInterpreter."""
        pass
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute rubric interpretation.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Starting rubric interpretation for task {state['task_id']}")
            
            # Update progress
            state = update_state_progress(
                state,
                phase="rubric_interpretation",
                progress=35,
                message="开始解析评分标准..."
            )
            
            marking_scheme_files = state.get("marking_scheme_files", [])
            
            if marking_scheme_files:
                # Parse marking scheme files
                rubric = await self._parse_marking_scheme(state, marking_scheme_files)
                state["rubric"] = rubric
                state["grading_criteria"] = rubric.get("criteria", [])
                
                message = "评分标准解析完成"
            else:
                # Generate default rubric based on question files
                rubric = await self._generate_default_rubric(state)
                state["rubric"] = rubric
                state["grading_criteria"] = rubric.get("criteria", [])
                
                message = "已生成默认评分标准"
            
            # Update progress
            state = update_state_progress(
                state,
                phase="rubric_interpretation",
                progress=40,
                message=message
            )
            
            # Mark node as complete
            state = mark_node_complete(
                state,
                "rubric_interpreter",
                {
                    "criteria_count": len(state.get("grading_criteria", [])),
                    "max_score": state.get("max_score", 100),
                    "has_custom_rubric": bool(marking_scheme_files)
                }
            )
            
            logger.info(f"Rubric interpretation completed for task {state['task_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Rubric interpretation error: {str(e)}", exc_info=True)
            return mark_node_error(state, "rubric_interpreter", f"评分标准解析失败: {str(e)}")
    
    async def _parse_marking_scheme(
        self,
        state: GraphState,
        marking_scheme_files: List[str]
    ) -> Dict[str, Any]:
        """
        Parse marking scheme files into structured rubric.
        
        Args:
            state: Current graph state
            marking_scheme_files: List of marking scheme file paths
            
        Returns:
            Structured rubric dictionary
        """
        try:
            # Read marking scheme content
            marking_content = ""
            for file_path in marking_scheme_files:
                content = process_file_content(file_path)
                marking_content += f"\n\n=== {Path(file_path).name} ===\n{content}"
            
            state["rubric_text"] = marking_content
            
            # Use AI to structure the rubric
            prompt = f"""请分析以下评分标准，并将其转换为结构化的评分规则。

评分标准内容：
{marking_content}

请以JSON格式输出，包含以下字段：
1. criteria: 评分标准列表，每项包含：
   - name: 标准名称
   - description: 详细描述
   - points: 分值
   - levels: 评分等级（如优秀、良好、及格、不及格）
2. total_points: 总分
3. grading_guidelines: 评分指导原则
4. key_points: 关键评分点

请确保输出是有效的JSON格式。"""
            
            # Call AI API to structure rubric
            response = await call_ai_api_async(
                prompt=prompt,
                system_message="你是一个专业的评分标准分析专家，擅长将文本评分标准转换为结构化数据。",
                files=marking_scheme_files
            )
            
            # Try to parse JSON from response
            try:
                # Extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    rubric = json.loads(json_str)
                else:
                    # Fallback to simple structure
                    rubric = self._create_simple_rubric(marking_content, state.get("max_score", 100))
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON, using simple rubric")
                rubric = self._create_simple_rubric(marking_content, state.get("max_score", 100))
            
            return rubric
            
        except Exception as e:
            logger.error(f"Failed to parse marking scheme: {str(e)}", exc_info=True)
            # Return simple rubric as fallback
            return self._create_simple_rubric("", state.get("max_score", 100))
    
    async def _generate_default_rubric(self, state: GraphState) -> Dict[str, Any]:
        """
        Generate default rubric when no marking scheme is provided.
        
        Args:
            state: Current graph state
            
        Returns:
            Default rubric dictionary
        """
        max_score = state.get("max_score", 100)
        subject = state.get("subject", "通用")
        
        # Create default rubric based on subject
        rubric = {
            "criteria": [
                {
                    "name": "内容准确性",
                    "description": "答案内容的准确性和完整性",
                    "points": int(max_score * 0.4),
                    "levels": [
                        {"level": "优秀", "description": "完全正确，内容完整", "score_range": [0.9, 1.0]},
                        {"level": "良好", "description": "基本正确，略有遗漏", "score_range": [0.7, 0.9]},
                        {"level": "及格", "description": "部分正确，有明显错误", "score_range": [0.6, 0.7]},
                        {"level": "不及格", "description": "大部分错误或未作答", "score_range": [0.0, 0.6]}
                    ]
                },
                {
                    "name": "解题思路",
                    "description": "解题方法和思路的正确性",
                    "points": int(max_score * 0.3),
                    "levels": [
                        {"level": "优秀", "description": "思路清晰，方法正确", "score_range": [0.9, 1.0]},
                        {"level": "良好", "description": "思路基本正确", "score_range": [0.7, 0.9]},
                        {"level": "及格", "description": "思路有缺陷", "score_range": [0.6, 0.7]},
                        {"level": "不及格", "description": "思路错误", "score_range": [0.0, 0.6]}
                    ]
                },
                {
                    "name": "表达规范",
                    "description": "答案表达的规范性和完整性",
                    "points": int(max_score * 0.2),
                    "levels": [
                        {"level": "优秀", "description": "表达规范，格式正确", "score_range": [0.9, 1.0]},
                        {"level": "良好", "description": "表达基本规范", "score_range": [0.7, 0.9]},
                        {"level": "及格", "description": "表达欠规范", "score_range": [0.6, 0.7]},
                        {"level": "不及格", "description": "表达混乱", "score_range": [0.0, 0.6]}
                    ]
                },
                {
                    "name": "创新性",
                    "description": "解题方法的创新性和独特性",
                    "points": int(max_score * 0.1),
                    "levels": [
                        {"level": "优秀", "description": "有创新思路", "score_range": [0.9, 1.0]},
                        {"level": "良好", "description": "方法常规但有效", "score_range": [0.7, 0.9]},
                        {"level": "及格", "description": "方法一般", "score_range": [0.6, 0.7]},
                        {"level": "不及格", "description": "无创新", "score_range": [0.0, 0.6]}
                    ]
                }
            ],
            "total_points": max_score,
            "grading_guidelines": [
                "严格按照评分标准评分",
                "注重答案的准确性和完整性",
                "考虑学生的解题思路和方法",
                "给予建设性的反馈和建议"
            ],
            "key_points": [
                "答案准确性",
                "解题方法",
                "表达规范",
                "创新思维"
            ]
        }
        
        return rubric
    
    def _create_simple_rubric(self, marking_text: str, max_score: int) -> Dict[str, Any]:
        """
        Create simple rubric from marking text.
        
        Args:
            marking_text: Marking scheme text
            max_score: Maximum score
            
        Returns:
            Simple rubric dictionary
        """
        return {
            "criteria": [
                {
                    "name": "整体评分",
                    "description": marking_text if marking_text else "根据答案质量综合评分",
                    "points": max_score,
                    "levels": [
                        {"level": "优秀", "score_range": [0.9, 1.0]},
                        {"level": "良好", "score_range": [0.7, 0.9]},
                        {"level": "及格", "score_range": [0.6, 0.7]},
                        {"level": "不及格", "score_range": [0.0, 0.6]}
                    ]
                }
            ],
            "total_points": max_score,
            "grading_guidelines": ["根据评分标准综合评分"],
            "key_points": ["答案质量"]
        }


def create_rubric_interpreter_node():
    """
    Factory function to create RubricInterpreter node.
    
    Returns:
        RubricInterpreter instance
    """
    return RubricInterpreter()

