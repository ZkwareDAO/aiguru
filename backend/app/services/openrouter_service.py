"""OpenRouter AI service for Gemini 2.5 Flash Lite integration."""

import asyncio
import base64
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from PIL import Image
import io

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, ExternalServiceError
from app.schemas.grading import GradingRequest, GradingResult

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenRouterService:
    """OpenRouter API service for AI grading with Gemini 2.5 Flash Lite."""
    
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-2.5-flash-lite"
        self.api_key = settings.OPENAI_API_KEY  # Will use this for OpenRouter key
        
    async def grade_submission_with_coordinates(
        self,
        image_data: bytes,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None
    ) -> Dict[str, Any]:
        """
        Grade submission and return coordinates for error marking.
        
        Returns:
            Dict containing score, feedback, and error coordinates in format:
            {
                "score": 85,
                "max_score": 100,
                "feedback": "整体表现良好",
                "errors": [
                    {
                        "coordinates": {"x": 100, "y": 200, "w": 50, "h": 30},
                        "error_type": "calculation_error",
                        "description": "移项符号错误",
                        "correct_answer": "x=3",
                        "knowledge_points": ["一元一次方程"]
                    }
                ]
            }
        """
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Construct prompt for coordinate-based grading
            prompt = self._build_coordinate_grading_prompt(
                question_text, answer_standard, grading_instructions
            )
            
            # Make API request
            response = await self._make_api_request(prompt, image_b64)
            
            # Parse response to extract coordinates and grading info
            result = self._parse_coordinate_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in coordinate grading: {str(e)}")
            raise AIServiceError(f"Coordinate grading failed: {str(e)}")
    
    async def grade_submission_with_cropped_regions(
        self,
        image_data: bytes,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None
    ) -> Tuple[Dict[str, Any], List[Tuple[Dict, bytes]]]:
        """
        Grade submission and return cropped error regions.
        
        Returns:
            Tuple of (grading_result, list of (error_info, cropped_image_bytes))
        """
        try:
            # First get coordinates
            coordinate_result = await self.grade_submission_with_coordinates(
                image_data, question_text, answer_standard, grading_instructions
            )
            
            # Crop regions based on coordinates
            cropped_regions = []
            if "errors" in coordinate_result:
                for error in coordinate_result["errors"]:
                    if "coordinates" in error:
                        cropped_bytes = self._crop_image_region(
                            image_data, error["coordinates"]
                        )
                        cropped_regions.append((error, cropped_bytes))
            
            return coordinate_result, cropped_regions
            
        except Exception as e:
            logger.error(f"Error in region grading: {str(e)}")
            raise AIServiceError(f"Region grading failed: {str(e)}")
    
    def _build_coordinate_grading_prompt(
        self,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None
    ) -> str:
        """Build prompt for coordinate-based grading."""
        base_prompt = f"""
你是一个专业的作业批改AI助手。请根据以下标准批改学生的答题：

题目：{question_text}

标准答案：{answer_standard}

{f"批改要求：{grading_instructions}" if grading_instructions else ""}

请分析图片中的学生答案，并返回JSON格式的批改结果，包含：

1. 总体评分信息
2. 错误位置的精确坐标 (x, y, width, height)
3. 每个错误的详细说明

返回格式示例：
{{
    "score": 85,
    "max_score": 100,
    "feedback": "整体表现良好，但存在几个计算错误",
    "errors": [
        {{
            "coordinates": {{"x": 150, "y": 200, "w": 80, "h": 25}},
            "error_type": "calculation_error",
            "description": "在解方程时，移项符号处理错误",
            "correct_answer": "应该是 2x = 6，所以 x = 3",
            "knowledge_points": ["一元一次方程", "移项法则"],
            "severity": "major"
        }}
    ],
    "strengths": ["解题思路清晰", "步骤完整"],
    "suggestions": ["注意移项时符号变化", "建议多练习基础计算"]
}}

重要：
- 坐标以像素为单位，(0,0)为图片左上角
- 确保坐标准确定位到错误位置
- 错误类型包括：calculation_error、concept_error、format_error、missing_step等
- 知识点要具体明确
"""
        return base_prompt
    
    async def _make_api_request(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Make API request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise ExternalServiceError(f"OpenRouter API error: {response.status_code}")
            
            return response.json()
    
    def _parse_coordinate_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenRouter API response to extract grading data."""
        try:
            # Extract content from API response
            content = api_response["choices"][0]["message"]["content"]
            
            # Try to parse JSON from content
            # Sometimes the model might include extra text, so we need to extract JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
                return result
            else:
                # Fallback: create basic response
                return {
                    "score": 0,
                    "max_score": 100,
                    "feedback": "无法解析AI回复，请重试",
                    "errors": []
                }
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error parsing coordinate response: {str(e)}")
            return {
                "score": 0,
                "max_score": 100,
                "feedback": "AI回复解析失败，请重试",
                "errors": []
            }
    
    def _crop_image_region(self, image_data: bytes, coordinates: Dict[str, int]) -> bytes:
        """Crop image region based on coordinates."""
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Extract coordinates
            x = coordinates.get("x", 0)
            y = coordinates.get("y", 0)
            w = coordinates.get("w", 100)
            h = coordinates.get("h", 100)
            
            # Ensure coordinates are within image bounds
            img_width, img_height = image.size
            x = max(0, min(x, img_width - 1))
            y = max(0, min(y, img_height - 1))
            w = min(w, img_width - x)
            h = min(h, img_height - y)
            
            # Crop the region
            cropped = image.crop((x, y, x + w, y + h))
            
            # Convert back to bytes
            output = io.BytesIO()
            cropped.save(output, format='JPEG', quality=90)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error cropping image: {str(e)}")
            # Return a placeholder or the original image
            return image_data
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check OpenRouter API health."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Simple test request
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "model": self.model,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model,
                "timestamp": "2024-01-01T00:00:00Z"
            }


# Factory function
def get_openrouter_service() -> OpenRouterService:
    """Get OpenRouter service instance."""
    return OpenRouterService()