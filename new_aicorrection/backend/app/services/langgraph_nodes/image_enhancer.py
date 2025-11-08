"""ImageEnhancer node for LangGraph grading workflow using CamScanner API."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from PIL import Image
import io

from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error

logger = logging.getLogger(__name__)


class ImageEnhancer:
    """
    Enhances images using CamScanner API.
    
    Responsibilities:
    - Check if CamScanner API key is configured
    - Skip enhancement if API key is not available
    - Call CamScanner API for image enhancement
    - Apply document scanning and enhancement
    - Save enhanced images
    
    Note: This node is OPTIONAL - it will be skipped if API key is not configured.
    """
    
    def __init__(self):
        """Initialize ImageEnhancer."""
        # Get CamScanner API key from environment
        self.api_key = os.getenv("CAMSCANNER_API_KEY")
        self.api_endpoint = os.getenv(
            "CAMSCANNER_API_ENDPOINT",
            "https://api.camscanner.com/v1/enhance"  # 示例端点，需要根据实际API调整
        )
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("CamScanner API key not configured - image enhancement will be skipped")
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute image enhancement.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        logger.info(f"ImageEnhancer processing task: {state.get('task_id', 'unknown')}")
        
        # Update progress
        state = update_state_progress(
            state,
            phase="image_enhancement",
            progress=10,
            message="开始图像增强处理"
        )
        
        try:
            # Check if enhancement is enabled
            if not self.enabled:
                logger.info("Image enhancement skipped - API key not configured")
                state = update_state_progress(
                    state,
                    phase="image_enhancement",
                    progress=15,
                    message="图像增强已跳过（未配置API密钥）"
                )
                return mark_node_complete(state, "image_enhancer", skip_reason="API key not configured")
            
            # Get files to enhance
            answer_files = state.get("answer_files", [])
            question_files = state.get("question_files", [])
            
            all_files = answer_files + question_files
            
            if not all_files:
                logger.warning("No files to enhance")
                return mark_node_complete(state, "image_enhancer", skip_reason="No files to process")
            
            # Enhance images
            enhanced_results = await self._enhance_images(state, all_files)
            
            # Update state with enhanced images
            state["enhanced_images"] = enhanced_results
            state["enhancement_applied"] = True
            
            # Update progress
            state = update_state_progress(
                state,
                phase="image_enhancement",
                progress=15,
                message=f"成功增强 {len(enhanced_results.get('enhanced_files', []))} 个图像"
            )
            
            return mark_node_complete(state, "image_enhancer")
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {str(e)}", exc_info=True)
            return mark_node_error(
                state,
                "image_enhancer",
                str(e),
                recoverable=True  # Enhancement failure is recoverable - can continue with original images
            )
    
    async def _enhance_images(self, state: GraphState, image_files: list) -> Dict[str, Any]:
        """
        Enhance images using CamScanner API.
        
        Args:
            state: Current graph state
            image_files: List of image file paths
            
        Returns:
            Dictionary containing enhanced image information
        """
        enhanced_results = {
            "enhanced_files": [],
            "original_files": [],
            "enhancement_metadata": []
        }
        
        for idx, image_path in enumerate(image_files):
            try:
                path = Path(image_path)
                
                # Check if it's an image file
                if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}:
                    logger.warning(f"Skipping non-image file: {path.name}")
                    continue
                
                logger.info(f"Enhancing image {idx + 1}/{len(image_files)}: {path.name}")
                
                # Call CamScanner API
                enhanced_image_data = await self._call_camscanner_api(image_path)
                
                if enhanced_image_data:
                    # Save enhanced image
                    enhanced_path = path.parent / f"enhanced_{path.name}"
                    
                    # Save the enhanced image
                    with open(enhanced_path, 'wb') as f:
                        f.write(enhanced_image_data)
                    
                    enhanced_results["enhanced_files"].append(str(enhanced_path))
                    enhanced_results["original_files"].append(str(image_path))
                    enhanced_results["enhancement_metadata"].append({
                        "original_file": str(image_path),
                        "enhanced_file": str(enhanced_path),
                        "enhancement_applied": True,
                        "api_used": "CamScanner"
                    })
                    
                    logger.info(f"Successfully enhanced: {path.name}")
                else:
                    # Enhancement failed, use original
                    logger.warning(f"Enhancement failed for {path.name}, using original")
                    enhanced_results["enhanced_files"].append(str(image_path))
                    enhanced_results["original_files"].append(str(image_path))
                    enhanced_results["enhancement_metadata"].append({
                        "original_file": str(image_path),
                        "enhanced_file": str(image_path),
                        "enhancement_applied": False,
                        "fallback_reason": "API call failed"
                    })
                
            except Exception as e:
                logger.error(f"Error enhancing {image_path}: {str(e)}")
                # Use original image on error
                enhanced_results["enhanced_files"].append(str(image_path))
                enhanced_results["original_files"].append(str(image_path))
                enhanced_results["enhancement_metadata"].append({
                    "original_file": str(image_path),
                    "enhanced_file": str(image_path),
                    "enhancement_applied": False,
                    "error": str(e)
                })
        
        return enhanced_results
    
    async def _call_camscanner_api(self, image_path: str) -> Optional[bytes]:
        """
        Call CamScanner API to enhance image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Enhanced image data as bytes, or None if failed
        """
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Prepare API request
            # Note: This is a placeholder implementation
            # You need to adjust according to actual CamScanner API documentation
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/octet-stream"
            }
            
            # Example API call structure - adjust based on actual API
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                data=image_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("CamScanner API call successful")
                return response.content
            else:
                logger.error(f"CamScanner API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("CamScanner API timeout")
            return None
        except Exception as e:
            logger.error(f"CamScanner API call failed: {str(e)}")
            return None
    
    async def _fallback_enhancement(self, image_path: str) -> Optional[bytes]:
        """
        Fallback image enhancement using local processing.
        
        This is used when CamScanner API is not available.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Enhanced image data as bytes
        """
        try:
            # Open image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Apply basic enhancements
            from PIL import ImageEnhance, ImageFilter
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Apply edge enhancement
            img = img.filter(ImageFilter.EDGE_ENHANCE)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Fallback enhancement failed: {str(e)}")
            return None


def create_image_enhancer_node() -> ImageEnhancer:
    """
    Factory function to create ImageEnhancer node.
    
    Returns:
        ImageEnhancer instance
    """
    return ImageEnhancer()

