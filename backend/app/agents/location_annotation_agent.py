"""Location Annotation Agent - 精确位置标注

使用Gemini 2.5 Flash Lite进行像素级精确定位
成本: $0.000001/题 (几乎免费!)
"""

import logging
import json
import re
import os
from typing import Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agents.state import BoundingBox, ErrorLocation

logger = logging.getLogger(__name__)


class LocationAnnotationAgent:
    """位置标注Agent
    
    职责:
    - 在图片中精确定位错误位置
    - 返回像素级坐标
    - 提供置信度评分
    - 兜底方案处理
    
    技术: Gemini 2.5 Flash Lite (视觉模型)
    成本: $0.000001/题
    """
    
    LOCATION_PROMPT_TEMPLATE = """
你是一个专业的位置标注专家。你的任务是在学生作业图片中精确定位错误位置。

## 图片信息
- 图片尺寸: {width}px × {height}px
- 题目区域: x={bbox_x}, y={bbox_y}, width={bbox_width}, height={bbox_height}

## 错误信息
- 错误类型: {error_type}
- 错误描述: {error_description}
- 相关文字: {related_text}

## 任务要求
请仔细观察图片，找到错误所在的位置，并返回JSON格式:

{{
  "bbox": {{
    "x": 150,
    "y": 200,
    "width": 200,
    "height": 50
  }},
  "type": "area",
  "confidence": 0.95,
  "reasoning": "错误位于第二行的计算结果部分"
}}

## 定位要求
1. 坐标必须是相对于整张图片的绝对像素坐标
2. bbox应该紧密包围错误内容，不要过大或过小
3. 如果无法准确定位，confidence设为0.5以下
4. reasoning必须详细说明定位依据

## 标注类型
- point: 单个点（如错误的数字）
- line: 一行内容（如错误的公式）
- area: 一个区域（如错误的解题步骤）

只返回JSON，不要有其他文字。
"""
    
    def __init__(self):
        """初始化Agent"""
        self.llm = ChatOpenAI(
            model="google/gemini-2.0-flash-exp:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.1,  # 低温度，提高准确性
        )
        logger.info("LocationAnnotationAgent initialized with Gemini 2.5 Flash Lite")
    
    async def annotate(
        self,
        image_url: str,
        image_width: int,
        image_height: int,
        question_bbox: BoundingBox,
        error: Dict
    ) -> ErrorLocation:
        """精确位置标注
        
        Args:
            image_url: 图片URL
            image_width: 图片宽度
            image_height: 图片高度
            question_bbox: 题目边界框
            error: 错误信息
            
        Returns:
            位置标注结果
        """
        try:
            logger.info(f"Annotating error: {error.get('type')} in image {image_url}")
            
            # 1. 构建Prompt
            prompt = self._build_prompt(
                image_width,
                image_height,
                question_bbox,
                error
            )
            
            # 2. 调用LLM
            response = await self.llm.ainvoke([
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ])
            ])
            
            # 3. 解析响应
            result = self._parse_response(response.content)
            
            # 4. 验证结果
            validated_result = self._validate_result(
                result,
                image_width,
                image_height,
                question_bbox
            )
            
            # 5. 兜底处理
            if validated_result["confidence"] < 0.5:
                logger.warning(
                    f"Low confidence ({validated_result['confidence']}), "
                    f"using fallback location"
                )
                validated_result = self._get_fallback_location(question_bbox)
            
            logger.info(
                f"Location annotated: confidence={validated_result['confidence']:.2f}, "
                f"type={validated_result['type']}"
            )
            
            return validated_result
            
        except Exception as e:
            logger.error(f"Location annotation failed: {e}", exc_info=True)
            # 返回兜底位置
            return self._get_fallback_location(question_bbox)
    
    def _build_prompt(
        self,
        image_width: int,
        image_height: int,
        question_bbox: BoundingBox,
        error: Dict
    ) -> str:
        """构建Prompt"""
        return self.LOCATION_PROMPT_TEMPLATE.format(
            width=image_width,
            height=image_height,
            bbox_x=question_bbox["x"],
            bbox_y=question_bbox["y"],
            bbox_width=question_bbox["width"],
            bbox_height=question_bbox["height"],
            error_type=error.get("type", "未知错误"),
            error_description=error.get("description", ""),
            related_text=error.get("related_text", "无")
        )
    
    def _parse_response(self, content: str) -> ErrorLocation:
        """解析LLM响应
        
        Args:
            content: LLM响应内容
            
        Returns:
            位置标注结果
        """
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("未找到JSON")
            
            data = json.loads(json_match.group())
            
            return ErrorLocation(
                bbox=BoundingBox(
                    x=int(data["bbox"]["x"]),
                    y=int(data["bbox"]["y"]),
                    width=int(data["bbox"]["width"]),
                    height=int(data["bbox"]["height"])
                ),
                type=data["type"],
                confidence=float(data["confidence"]),
                reasoning=data["reasoning"]
            )
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.debug(f"Response content: {content}")
            raise
    
    def _validate_result(
        self,
        result: ErrorLocation,
        image_width: int,
        image_height: int,
        question_bbox: BoundingBox
    ) -> ErrorLocation:
        """验证结果
        
        Args:
            result: 位置标注结果
            image_width: 图片宽度
            image_height: 图片高度
            question_bbox: 题目边界框
            
        Returns:
            验证后的结果
        """
        bbox = result["bbox"]
        confidence = result["confidence"]
        
        # 1. 检查坐标是否在图片范围内
        if (bbox["x"] < 0 or
            bbox["y"] < 0 or
            bbox["x"] + bbox["width"] > image_width or
            bbox["y"] + bbox["height"] > image_height):
            logger.warning("坐标超出图片范围，降低置信度")
            confidence *= 0.5
        
        # 2. 检查是否在题目区域附近
        question_center_y = question_bbox["y"] + question_bbox["height"] / 2
        result_center_y = bbox["y"] + bbox["height"] / 2
        
        distance = abs(result_center_y - question_center_y)
        if distance > question_bbox["height"]:
            logger.warning("位置距离题目区域较远，降低置信度")
            confidence *= 0.7
        
        # 3. 检查bbox大小是否合理
        if bbox["width"] < 10 or bbox["height"] < 10:
            logger.warning("bbox过小，降低置信度")
            confidence *= 0.8
        
        if bbox["width"] > image_width * 0.8 or bbox["height"] > image_height * 0.8:
            logger.warning("bbox过大，降低置信度")
            confidence *= 0.8
        
        # 更新置信度
        result["confidence"] = max(0.0, min(1.0, confidence))
        
        return result
    
    def _get_fallback_location(
        self,
        question_bbox: BoundingBox
    ) -> ErrorLocation:
        """兜底方案: 返回题目中心位置
        
        Args:
            question_bbox: 题目边界框
            
        Returns:
            兜底位置
        """
        center_x = question_bbox["x"] + question_bbox["width"] / 2
        center_y = question_bbox["y"] + question_bbox["height"] / 2
        
        return ErrorLocation(
            bbox=BoundingBox(
                x=int(center_x - 50),
                y=int(center_y - 25),
                width=100,
                height=50
            ),
            type="area",
            confidence=0.3,
            reasoning="无法准确定位，返回题目中心位置"
        )
    
    async def batch_annotate(
        self,
        image_url: str,
        image_width: int,
        image_height: int,
        question_bbox: BoundingBox,
        errors: list[Dict]
    ) -> list[ErrorLocation]:
        """批量标注多个错误
        
        Args:
            image_url: 图片URL
            image_width: 图片宽度
            image_height: 图片高度
            question_bbox: 题目边界框
            errors: 错误列表
            
        Returns:
            位置标注结果列表
        """
        results = []
        for error in errors:
            result = await self.annotate(
                image_url,
                image_width,
                image_height,
                question_bbox,
                error
            )
            results.append(result)
        
        return results

