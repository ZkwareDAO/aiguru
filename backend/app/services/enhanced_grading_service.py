"""Enhanced AI grading service with coordinate annotation and image cropping."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, ValidationError
from app.models.grading import GradingTask, GradingTaskStatus
from app.schemas.grading import GradingRequest, GradingResult
from app.services.openrouter_service import get_openrouter_service
from app.services.file_service import FileService

logger = logging.getLogger(__name__)
settings = get_settings()


class EnhancedGradingService:
    """Enhanced AI grading service with coordinate annotation support."""
    
    def __init__(self, file_service: Optional[FileService] = None):
        self.openrouter_service = get_openrouter_service()
        self.file_service = file_service or FileService()
    
    async def grade_submission_with_annotations(
        self,
        submission_id: UUID,
        image_file_id: UUID,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None,
        display_mode: str = "coordinates"  # "coordinates" or "cropped_regions"
    ) -> Dict[str, Any]:
        """
        Grade submission with visual annotations.
        
        Args:
            submission_id: ID of the submission
            image_file_id: ID of the uploaded image file
            question_text: The question/problem text
            answer_standard: Standard answer for comparison
            grading_instructions: Specific grading instructions
            display_mode: "coordinates" for coordinate overlay, "cropped_regions" for local crops
            
        Returns:
            Dict with grading results and annotation data
        """
        try:
            # Get image data
            image_data = await self.file_service.get_file_content(image_file_id)
            
            if display_mode == "coordinates":
                return await self._grade_with_coordinates(
                    submission_id, image_data, question_text, answer_standard, grading_instructions
                )
            elif display_mode == "cropped_regions":
                return await self._grade_with_cropped_regions(
                    submission_id, image_data, question_text, answer_standard, grading_instructions
                )
            else:
                raise ValidationError(f"Invalid display mode: {display_mode}")
                
        except Exception as e:
            logger.error(f"Error in enhanced grading: {str(e)}")
            raise AIServiceError(f"Enhanced grading failed: {str(e)}")
    
    async def _grade_with_coordinates(
        self,
        submission_id: UUID,
        image_data: bytes,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None
    ) -> Dict[str, Any]:
        """Grade with coordinate-based annotations."""
        try:
            # Call OpenRouter service for coordinate grading
            grading_result = await self.openrouter_service.grade_submission_with_coordinates(
                image_data, question_text, answer_standard, grading_instructions
            )
            
            # Enhanced result format for frontend coordinate display
            enhanced_result = {
                "submission_id": str(submission_id),
                "display_mode": "coordinates",
                "grading_summary": {
                    "score": grading_result.get("score", 0),
                    "max_score": grading_result.get("max_score", 100),
                    "percentage": (grading_result.get("score", 0) / grading_result.get("max_score", 100)) * 100,
                    "feedback": grading_result.get("feedback", ""),
                    "strengths": grading_result.get("strengths", []),
                    "suggestions": grading_result.get("suggestions", [])
                },
                "coordinate_annotations": [],
                "knowledge_point_summary": {},
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            # Process error coordinates for frontend display
            errors = grading_result.get("errors", [])
            knowledge_points = set()
            
            for i, error in enumerate(errors):
                annotation = {
                    "annotation_id": f"error_{i+1}",
                    "coordinates": error.get("coordinates", {}),
                    "error_details": {
                        "type": error.get("error_type", "unknown"),
                        "description": error.get("description", ""),
                        "correct_answer": error.get("correct_answer", ""),
                        "severity": error.get("severity", "medium")
                    },
                    "knowledge_points": error.get("knowledge_points", []),
                    "popup_content": {
                        "title": error.get("error_type", "错误").replace("_", " ").title(),
                        "description": error.get("description", ""),
                        "correct_solution": error.get("correct_answer", ""),
                        "knowledge_links": error.get("knowledge_points", [])
                    }
                }
                enhanced_result["coordinate_annotations"].append(annotation)
                knowledge_points.update(error.get("knowledge_points", []))
            
            # Summarize knowledge points
            enhanced_result["knowledge_point_summary"] = {
                "total_points": len(knowledge_points),
                "points": list(knowledge_points),
                "mastery_analysis": self._analyze_knowledge_mastery(errors)
            }
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in coordinate grading: {str(e)}")
            raise AIServiceError(f"Coordinate grading failed: {str(e)}")
    
    async def _grade_with_cropped_regions(
        self,
        submission_id: UUID,
        image_data: bytes,
        question_text: str,
        answer_standard: str,
        grading_instructions: str = None
    ) -> Dict[str, Any]:
        """Grade with cropped region cards."""
        try:
            # Call OpenRouter service for region grading
            grading_result, cropped_regions = await self.openrouter_service.grade_submission_with_cropped_regions(
                image_data, question_text, answer_standard, grading_instructions
            )
            
            # Enhanced result format for frontend card display
            enhanced_result = {
                "submission_id": str(submission_id),
                "display_mode": "cropped_regions",
                "grading_summary": {
                    "score": grading_result.get("score", 0),
                    "max_score": grading_result.get("max_score", 100),
                    "percentage": (grading_result.get("score", 0) / grading_result.get("max_score", 100)) * 100,
                    "feedback": grading_result.get("feedback", ""),
                    "strengths": grading_result.get("strengths", []),
                    "suggestions": grading_result.get("suggestions", [])
                },
                "error_cards": [],
                "original_image_url": None,  # Will be set by file service
                "knowledge_point_summary": {},
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            # Process cropped regions for card display
            knowledge_points = set()
            
            for i, (error_info, cropped_bytes) in enumerate(cropped_regions):
                # Save cropped image
                cropped_file_id = await self.file_service.save_file(
                    filename=f"cropped_error_{submission_id}_{i+1}.jpg",
                    content=cropped_bytes,
                    content_type="image/jpeg"
                )
                
                error_card = {
                    "card_id": f"error_{i+1}",
                    "error_details": {
                        "type": error_info.get("error_type", "unknown"),
                        "description": error_info.get("description", ""),
                        "correct_answer": error_info.get("correct_answer", ""),
                        "severity": error_info.get("severity", "medium")
                    },
                    "cropped_image": {
                        "file_id": str(cropped_file_id),
                        "url": f"/api/files/{cropped_file_id}",
                        "coordinates": error_info.get("coordinates", {})
                    },
                    "knowledge_points": error_info.get("knowledge_points", []),
                    "actions": {
                        "locate_in_original": {
                            "coordinates": error_info.get("coordinates", {}),
                            "description": "定位到原图中的错误位置"
                        },
                        "view_explanation": {
                            "detailed_analysis": error_info.get("description", ""),
                            "solution_steps": error_info.get("correct_answer", "")
                        },
                        "related_practice": {
                            "knowledge_points": error_info.get("knowledge_points", []),
                            "difficulty_level": error_info.get("severity", "medium")
                        }
                    }
                }
                
                enhanced_result["error_cards"].append(error_card)
                knowledge_points.update(error_info.get("knowledge_points", []))
            
            # Summarize knowledge points
            enhanced_result["knowledge_point_summary"] = {
                "total_points": len(knowledge_points),
                "points": list(knowledge_points),
                "mastery_analysis": self._analyze_knowledge_mastery(grading_result.get("errors", []))
            }
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in cropped region grading: {str(e)}")
            raise AIServiceError(f"Cropped region grading failed: {str(e)}")
    
    def _analyze_knowledge_mastery(self, errors: List[Dict]) -> Dict[str, Any]:
        """Analyze knowledge point mastery based on errors."""
        mastery_analysis = {
            "weak_areas": [],
            "strong_areas": [],
            "recommendations": []
        }
        
        # Count errors by knowledge point
        knowledge_errors = {}
        for error in errors:
            for point in error.get("knowledge_points", []):
                knowledge_errors[point] = knowledge_errors.get(point, 0) + 1
        
        # Classify based on error frequency
        for point, error_count in knowledge_errors.items():
            if error_count >= 2:
                mastery_analysis["weak_areas"].append({
                    "knowledge_point": point,
                    "error_count": error_count,
                    "severity": "high" if error_count >= 3 else "medium"
                })
            elif error_count == 1:
                mastery_analysis["weak_areas"].append({
                    "knowledge_point": point,
                    "error_count": error_count,
                    "severity": "low"
                })
        
        # Generate recommendations
        if mastery_analysis["weak_areas"]:
            high_priority = [area for area in mastery_analysis["weak_areas"] if area["severity"] == "high"]
            if high_priority:
                mastery_analysis["recommendations"].append(
                    f"重点复习：{', '.join([area['knowledge_point'] for area in high_priority])}"
                )
            
            medium_priority = [area for area in mastery_analysis["weak_areas"] if area["severity"] == "medium"]
            if medium_priority:
                mastery_analysis["recommendations"].append(
                    f"加强练习：{', '.join([area['knowledge_point'] for area in medium_priority])}"
                )
        
        return mastery_analysis
    
    async def batch_grade_with_annotations(
        self,
        submissions: List[Dict[str, Any]],
        display_mode: str = "coordinates"
    ) -> List[Dict[str, Any]]:
        """Batch grade multiple submissions with annotations."""
        results = []
        
        for submission in submissions:
            try:
                result = await self.grade_submission_with_annotations(
                    submission_id=submission["submission_id"],
                    image_file_id=submission["image_file_id"],
                    question_text=submission["question_text"],
                    answer_standard=submission["answer_standard"],
                    grading_instructions=submission.get("grading_instructions"),
                    display_mode=display_mode
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error grading submission {submission.get('submission_id')}: {str(e)}")
                # Add error result
                results.append({
                    "submission_id": str(submission.get("submission_id", "")),
                    "display_mode": display_mode,
                    "error": str(e),
                    "processing_timestamp": datetime.utcnow().isoformat()
                })
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            openrouter_health = await self.openrouter_service.check_api_health()
            
            return {
                "service": "enhanced_grading",
                "status": "healthy",
                "openrouter_status": openrouter_health.get("status", "unknown"),
                "features": {
                    "coordinate_annotation": True,
                    "cropped_regions": True,
                    "batch_processing": True,
                    "knowledge_analysis": True
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "service": "enhanced_grading",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Factory function
def get_enhanced_grading_service(file_service: Optional[FileService] = None) -> EnhancedGradingService:
    """Get enhanced grading service instance."""
    return EnhancedGradingService(file_service)