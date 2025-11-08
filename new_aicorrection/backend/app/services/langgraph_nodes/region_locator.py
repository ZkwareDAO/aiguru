"""RegionLocator node for LangGraph grading workflow."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import base64
import json

from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error
from app.core.ai_grading_engine import call_openrouter_api, call_gemini_api

logger = logging.getLogger(__name__)


class RegionLocator:
    """
    Locates key regions in answer sheets using AI vision models.
    
    Responsibilities:
    - Detect answer regions in student submissions
    - Identify question areas
    - Locate marking/grading areas
    - Extract region coordinates and metadata
    - Support multiple detection strategies
    
    Uses AI vision models (GPT-4V, Gemini Vision) to analyze document layout.
    """
    
    def __init__(self):
        """Initialize RegionLocator."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Determine which AI service to use
        self.ai_service = self._determine_ai_service()
        
        if not self.ai_service:
            logger.warning("No AI API keys configured for region location")
    
    def _determine_ai_service(self) -> Optional[str]:
        """Determine which AI service to use based on available API keys."""
        if self.gemini_api_key:
            return "gemini"
        elif self.openrouter_api_key:
            return "openrouter"
        elif self.openai_api_key:
            return "openai"
        return None
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute region location.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        logger.info(f"RegionLocator processing task: {state.get('task_id', 'unknown')}")
        
        # Update progress
        state = update_state_progress(
            state,
            phase="region_location",
            progress=20,
            message="开始定位答题区域"
        )
        
        try:
            # Get images to analyze (use enhanced if available, otherwise original)
            enhanced_images = state.get("enhanced_images", {})
            if enhanced_images and enhanced_images.get("enhanced_files"):
                images_to_analyze = enhanced_images["enhanced_files"]
                logger.info("Using enhanced images for region location")
            else:
                # Use original images
                answer_files = state.get("answer_files", [])
                question_files = state.get("question_files", [])
                images_to_analyze = answer_files + question_files
                logger.info("Using original images for region location")
            
            if not images_to_analyze:
                logger.warning("No images to analyze for region location")
                return mark_node_complete(state, "region_locator", skip_reason="No images to analyze")
            
            # Locate regions in images
            region_results = await self._locate_regions(state, images_to_analyze)
            
            # Update state with region information
            state["detected_regions"] = region_results
            
            # Update progress
            state = update_state_progress(
                state,
                phase="region_location",
                progress=25,
                message=f"成功定位 {len(region_results.get('regions', []))} 个区域"
            )
            
            return mark_node_complete(state, "region_locator")
            
        except Exception as e:
            logger.error(f"Region location failed: {str(e)}", exc_info=True)
            return mark_node_error(
                state,
                "region_locator",
                str(e),
                recoverable=True  # Can continue without region information
            )
    
    async def _locate_regions(self, state: GraphState, image_files: List[str]) -> Dict[str, Any]:
        """
        Locate regions in images using AI vision models.
        
        Args:
            state: Current graph state
            image_files: List of image file paths
            
        Returns:
            Dictionary containing region information
        """
        region_results = {
            "regions": [],
            "metadata": {
                "total_images": len(image_files),
                "detection_method": self.ai_service or "none",
                "regions_detected": 0
            }
        }
        
        for idx, image_path in enumerate(image_files):
            try:
                logger.info(f"Analyzing image {idx + 1}/{len(image_files)}: {Path(image_path).name}")
                
                # Detect regions using AI
                regions = await self._detect_regions_with_ai(image_path, state)
                
                if regions:
                    region_results["regions"].extend(regions)
                    region_results["metadata"]["regions_detected"] += len(regions)
                    logger.info(f"Detected {len(regions)} regions in {Path(image_path).name}")
                else:
                    logger.warning(f"No regions detected in {Path(image_path).name}")
                
            except Exception as e:
                logger.error(f"Error analyzing {image_path}: {str(e)}")
                continue
        
        return region_results
    
    async def _detect_regions_with_ai(
        self,
        image_path: str,
        state: GraphState
    ) -> List[Dict[str, Any]]:
        """
        Detect regions using AI vision models.
        
        Args:
            image_path: Path to the image file
            state: Current graph state
            
        Returns:
            List of detected regions with coordinates and metadata
        """
        if not self.ai_service:
            logger.warning("No AI service available for region detection")
            return []
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare prompt for region detection
            prompt = self._create_region_detection_prompt(state)
            
            # Call AI API
            if self.ai_service == "gemini":
                response = await self._call_gemini_for_regions(image_base64, prompt)
            elif self.ai_service == "openrouter":
                response = await self._call_openrouter_for_regions(image_base64, prompt)
            else:
                response = await self._call_openai_for_regions(image_base64, prompt)
            
            # Parse response
            regions = self._parse_region_response(response, image_path)
            
            return regions
            
        except Exception as e:
            logger.error(f"AI region detection failed: {str(e)}")
            return []
    
    def _create_region_detection_prompt(self, state: GraphState) -> str:
        """Create prompt for region detection."""
        task_type = state.get("task_type", "auto")
        language = state.get("language", "zh")
        
        if language == "zh":
            prompt = """请分析这张答题卡/作业图片，识别并定位以下区域：

1. **题目区域**: 包含问题/题目的区域
2. **答案区域**: 学生作答的区域
3. **评分区域**: 用于批改和评分的区域（如果有）
4. **其他重要区域**: 如学生信息、日期等

对于每个区域，请提供：
- region_type: 区域类型（question/answer/grading/other）
- coordinates: 边界框坐标 [x1, y1, x2, y2]（归一化到0-1）
- confidence: 置信度（0-1）
- description: 区域描述

请以JSON格式返回结果：
{
  "regions": [
    {
      "region_type": "answer",
      "coordinates": [0.1, 0.2, 0.9, 0.8],
      "confidence": 0.95,
      "description": "学生答题区域"
    }
  ]
}"""
        else:
            prompt = """Please analyze this answer sheet/homework image and identify the following regions:

1. **Question regions**: Areas containing questions/problems
2. **Answer regions**: Areas where students wrote their answers
3. **Grading regions**: Areas for marking/grading (if any)
4. **Other important regions**: Such as student info, date, etc.

For each region, provide:
- region_type: Type of region (question/answer/grading/other)
- coordinates: Bounding box [x1, y1, x2, y2] (normalized to 0-1)
- confidence: Confidence score (0-1)
- description: Region description

Return results in JSON format:
{
  "regions": [
    {
      "region_type": "answer",
      "coordinates": [0.1, 0.2, 0.9, 0.8],
      "confidence": 0.95,
      "description": "Student answer area"
    }
  ]
}"""
        
        return prompt
    
    async def _call_gemini_for_regions(
        self,
        image_base64: str,
        prompt: str
    ) -> str:
        """Call Gemini API for region detection."""
        try:
            # Use the existing Gemini API function
            response = call_gemini_api(
                prompt=prompt,
                image_base64=image_base64,
                api_key=self.gemini_api_key
            )
            return response
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise
    
    async def _call_openrouter_for_regions(
        self,
        image_base64: str,
        prompt: str
    ) -> str:
        """Call OpenRouter API for region detection."""
        try:
            # Use the existing OpenRouter API function
            response = call_openrouter_api(
                prompt=prompt,
                image_base64=image_base64,
                api_key=self.openrouter_api_key,
                model="google/gemini-2.0-flash-exp:free"
            )
            return response
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {str(e)}")
            raise
    
    async def _call_openai_for_regions(
        self,
        image_base64: str,
        prompt: str
    ) -> str:
        """Call OpenAI API for region detection."""
        # Placeholder - implement if needed
        raise NotImplementedError("OpenAI vision API not yet implemented")
    
    def _parse_region_response(
        self,
        response: str,
        image_path: str
    ) -> List[Dict[str, Any]]:
        """
        Parse AI response to extract region information.
        
        Args:
            response: AI API response
            image_path: Path to the source image
            
        Returns:
            List of region dictionaries
        """
        try:
            # Try to extract JSON from response
            import re
            
            # Find JSON block in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                regions = data.get("regions", [])
                
                # Add source image to each region
                for region in regions:
                    region["source_image"] = image_path
                
                return regions
            else:
                logger.warning("No JSON found in AI response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing region response: {str(e)}")
            return []


def create_region_locator_node() -> RegionLocator:
    """
    Factory function to create RegionLocator node.
    
    Returns:
        RegionLocator instance
    """
    return RegionLocator()

