"""ScoringAgent node for LangGraph grading workflow."""

import logging
import json
from typing import Dict, Any, List, Optional

from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error
from app.core.ai_grading_engine import call_ai_api_async
from app.core.grading_prompts import get_core_grading_prompt, ULTIMATE_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)


class ScoringAgent:
    """
    Performs AI-powered grading using LLM.
    
    Responsibilities:
    - Call Gemini/GPT for grading
    - Apply rubric criteria
    - Generate scores and feedback
    - Provide detailed explanations
    """
    
    def __init__(self):
        """Initialize ScoringAgent."""
        pass
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute scoring.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Starting scoring for task {state['task_id']}")
            
            # Update progress
            state = update_state_progress(
                state,
                phase="scoring",
                progress=45,
                message="开始AI智能评分..."
            )
            
            # Perform grading
            grading_result = await self._perform_grading(state)
            
            # Update state with results
            state["scores"] = grading_result.get("scores", {})
            state["total_score"] = grading_result.get("total_score", 0)
            state["percentage"] = grading_result.get("percentage", 0.0)
            state["grade_level"] = grading_result.get("grade_level", "")
            state["result_text"] = grading_result.get("detailed_feedback", "")
            
            # Update progress
            state = update_state_progress(
                state,
                phase="scoring",
                progress=60,
                message=f"评分完成，总分: {state['total_score']}/{state['max_score']}"
            )
            
            # Mark node as complete
            state = mark_node_complete(
                state,
                "scoring_agent",
                {
                    "total_score": state["total_score"],
                    "max_score": state["max_score"],
                    "percentage": state["percentage"],
                    "grade_level": state["grade_level"]
                }
            )
            
            logger.info(f"Scoring completed for task {state['task_id']}: {state['total_score']}/{state['max_score']}")
            return state
            
        except Exception as e:
            logger.error(f"Scoring error: {str(e)}", exc_info=True)
            return mark_node_error(state, "scoring_agent", f"评分失败: {str(e)}")
    
    async def _perform_grading(self, state: GraphState) -> Dict[str, Any]:
        """
        Perform AI grading.
        
        Args:
            state: Current graph state
            
        Returns:
            Grading result dictionary
        """
        try:
            # Prepare grading prompt
            prompt = self._build_grading_prompt(state)
            
            # Get all files for grading
            all_files = []
            all_files.extend(state.get("question_files", []))
            all_files.extend(state.get("answer_files", []))
            if state.get("marking_scheme_files"):
                all_files.extend(state.get("marking_scheme_files", []))
            
            # Call AI API
            logger.info(f"Calling AI API for grading with {len(all_files)} files")
            response = await call_ai_api_async(
                prompt=prompt,
                system_message=ULTIMATE_SYSTEM_MESSAGE,
                files=all_files
            )
            
            # Parse grading result
            grading_result = self._parse_grading_response(response, state)
            
            return grading_result
            
        except Exception as e:
            logger.error(f"Grading execution error: {str(e)}", exc_info=True)
            raise
    
    def _build_grading_prompt(self, state: GraphState) -> str:
        """
        Build grading prompt based on state.
        
        Args:
            state: Current graph state
            
        Returns:
            Grading prompt string
        """
        # Get base prompt
        rubric = state.get("rubric", {})
        prompt = get_core_grading_prompt(rubric, {})
        
        # Add strictness level
        strictness = state.get("strictness_level", "中等")
        strictness_instructions = {
            "宽松": "评分时应该更加宽容，对于部分正确的答案给予较高分数，鼓励学生的努力。",
            "中等": "评分时应该公平公正，严格按照评分标准，但也要考虑学生的实际情况。",
            "严格": "评分时应该非常严格，只有完全正确的答案才能获得满分，对细节要求很高。"
        }
        prompt += f"\n\n**评分严格程度**: {strictness}\n{strictness_instructions.get(strictness, '')}\n"
        
        # Add rubric information
        if rubric:
            prompt += "\n\n**评分标准**:\n"
            criteria = rubric.get("criteria", [])
            for i, criterion in enumerate(criteria, 1):
                prompt += f"{i}. {criterion.get('name', '')}: {criterion.get('description', '')} ({criterion.get('points', 0)}分)\n"
            
            prompt += f"\n**总分**: {rubric.get('total_points', state.get('max_score', 100))}分\n"
            
            guidelines = rubric.get("grading_guidelines", [])
            if guidelines:
                prompt += "\n**评分指导原则**:\n"
                for guideline in guidelines:
                    prompt += f"- {guideline}\n"
        
        # Add OCR text if available
        ocr_output = state.get("ocr_output", {})
        if ocr_output and ocr_output.get("full_text"):
            prompt += f"\n\n**OCR识别的文本内容**:\n{ocr_output['full_text']}\n"
        
        # Add output format requirements
        prompt += """

**输出格式要求**:
请以以下JSON格式输出评分结果：

```json
{
  "scores": {
    "criterion_1": {
      "name": "标准名称",
      "score": 得分,
      "max_score": 满分,
      "feedback": "详细反馈"
    },
    ...
  },
  "total_score": 总分,
  "max_score": 满分,
  "percentage": 得分百分比,
  "grade_level": "等级(A/B/C/D/F)",
  "strengths": ["优点1", "优点2", ...],
  "weaknesses": ["问题1", "问题2", ...],
  "suggestions": ["建议1", "建议2", ...],
  "detailed_feedback": "详细的批改反馈文本"
}
```

请确保输出是有效的JSON格式，并包含详细的反馈和建议。
"""
        
        return prompt
    
    def _parse_grading_response(self, response: str, state: GraphState) -> Dict[str, Any]:
        """
        Parse AI grading response.
        
        Args:
            response: AI response text
            state: Current graph state
            
        Returns:
            Parsed grading result
        """
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate and normalize result
                if "total_score" not in result:
                    result["total_score"] = self._calculate_total_score(result.get("scores", {}))
                
                if "max_score" not in result:
                    result["max_score"] = state.get("max_score", 100)
                
                if "percentage" not in result:
                    result["percentage"] = (result["total_score"] / result["max_score"] * 100) if result["max_score"] > 0 else 0
                
                if "grade_level" not in result:
                    result["grade_level"] = self._calculate_grade_level(result["percentage"])
                
                if "detailed_feedback" not in result:
                    result["detailed_feedback"] = response
                
                return result
            else:
                # Fallback: create result from text
                logger.warning("Could not parse JSON from response, creating fallback result")
                return self._create_fallback_result(response, state)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            return self._create_fallback_result(response, state)
        except Exception as e:
            logger.error(f"Response parsing error: {str(e)}", exc_info=True)
            return self._create_fallback_result(response, state)
    
    def _calculate_total_score(self, scores: Dict[str, Any]) -> int:
        """Calculate total score from criterion scores."""
        total = 0
        for criterion_data in scores.values():
            if isinstance(criterion_data, dict):
                total += criterion_data.get("score", 0)
        return int(total)
    
    def _calculate_grade_level(self, percentage: float) -> str:
        """Calculate grade level from percentage."""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    
    def _create_fallback_result(self, response: str, state: GraphState) -> Dict[str, Any]:
        """
        Create fallback result when JSON parsing fails.
        
        Args:
            response: AI response text
            state: Current graph state
            
        Returns:
            Fallback grading result
        """
        max_score = state.get("max_score", 100)
        
        # Try to extract score from text
        import re
        score_match = re.search(r'(\d+)\s*/\s*(\d+)', response)
        if score_match:
            total_score = int(score_match.group(1))
            max_score = int(score_match.group(2))
        else:
            # Default to 70% if can't parse
            total_score = int(max_score * 0.7)
        
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        return {
            "scores": {
                "overall": {
                    "name": "整体评分",
                    "score": total_score,
                    "max_score": max_score,
                    "feedback": response
                }
            },
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage,
            "grade_level": self._calculate_grade_level(percentage),
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "detailed_feedback": response
        }


def create_scoring_agent_node():
    """
    Factory function to create ScoringAgent node.
    
    Returns:
        ScoringAgent instance
    """
    return ScoringAgent()

