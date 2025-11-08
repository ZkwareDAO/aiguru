"""AI grading API integration service."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, ExternalServiceError
from app.schemas.grading import GradingRequest, GradingResult

logger = logging.getLogger(__name__)


class AIGradingAPIError(Exception):
    """Exception raised when AI grading API encounters an error."""
    pass


class GradingAPIRequest(BaseModel):
    """Request format for AI grading API."""
    
    assignment_title: str = Field(..., description="Title of the assignment")
    assignment_description: Optional[str] = Field(None, description="Assignment description")
    assignment_instructions: Optional[str] = Field(None, description="Grading instructions")
    student_answer: str = Field(..., description="Student's answer/submission")
    rubric: Optional[Dict[str, Any]] = Field(None, description="Grading rubric")
    grading_criteria: Optional[List[str]] = Field(None, description="Specific grading criteria")
    max_score: int = Field(default=100, description="Maximum possible score")
    ai_model: Optional[str] = Field(None, description="Preferred AI model")
    
    class Config:
        json_encoders = {
            UUID: str
        }


class GradingAPIResponse(BaseModel):
    """Response format from AI grading API."""
    
    success: bool = Field(..., description="Whether grading was successful")
    score: Optional[int] = Field(None, description="Numerical score")
    max_score: Optional[int] = Field(None, description="Maximum possible score")
    percentage: Optional[float] = Field(None, description="Score as percentage")
    feedback: Optional[str] = Field(None, description="Detailed feedback")
    suggestions: Optional[str] = Field(None, description="Improvement suggestions")
    strengths: Optional[List[str]] = Field(None, description="Identified strengths")
    weaknesses: Optional[List[str]] = Field(None, description="Areas for improvement")
    rubric_scores: Optional[Dict[str, int]] = Field(None, description="Scores by rubric criteria")
    confidence: Optional[float] = Field(None, description="AI confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code if failed")


class AIGradingAPIClient:
    """Client for AI grading API integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.AI_GRADING_API_URL
        self.api_key = self.settings.AI_GRADING_API_KEY
        self.timeout = 300  # 5 minutes timeout for grading
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(self.timeout),
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "AI-Education-Backend/1.0"
            }
        }
        
        if self.api_key:
            self.client_config["headers"]["Authorization"] = f"Bearer {self.api_key}"
    
    async def grade_submission(
        self,
        grading_request: GradingRequest,
        ai_model: Optional[str] = None
    ) -> GradingResult:
        """Grade a submission using the AI grading API."""
        if not self.base_url:
            raise AIGradingAPIError("AI grading API URL not configured")
        
        try:
            # Prepare API request
            api_request = GradingAPIRequest(
                assignment_title=grading_request.assignment_title,
                assignment_description=grading_request.assignment_description,
                assignment_instructions=grading_request.assignment_instructions,
                student_answer=grading_request.student_answer,
                rubric=grading_request.rubric,
                grading_criteria=grading_request.grading_criteria,
                max_score=grading_request.max_score,
                ai_model=ai_model
            )
            
            # Make API call with retries
            response = await self._make_api_call_with_retry(
                "POST",
                f"{self.base_url}/grade",
                api_request.dict()
            )
            
            # Parse response
            api_response = GradingAPIResponse(**response)
            
            if not api_response.success:
                raise AIGradingAPIError(
                    f"Grading failed: {api_response.error_message or 'Unknown error'}"
                )
            
            # Convert to internal format
            return self._convert_to_grading_result(api_response)
            
        except httpx.RequestError as e:
            logger.error(f"Network error during grading API call: {str(e)}")
            raise ExternalServiceError(f"Network error: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during grading API call: {e.response.status_code}")
            raise ExternalServiceError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error during grading: {str(e)}")
            raise AIServiceError(f"Grading failed: {str(e)}")
    
    async def batch_grade_submissions(
        self,
        grading_requests: List[GradingRequest],
        ai_model: Optional[str] = None
    ) -> List[GradingResult]:
        """Grade multiple submissions in batch."""
        if not self.base_url:
            raise AIGradingAPIError("AI grading API URL not configured")
        
        try:
            # Prepare batch request
            batch_request = {
                "submissions": [
                    GradingAPIRequest(
                        assignment_title=req.assignment_title,
                        assignment_description=req.assignment_description,
                        assignment_instructions=req.assignment_instructions,
                        student_answer=req.student_answer,
                        rubric=req.rubric,
                        grading_criteria=req.grading_criteria,
                        max_score=req.max_score,
                        ai_model=ai_model
                    ).dict()
                    for req in grading_requests
                ]
            }
            
            # Make batch API call
            response = await self._make_api_call_with_retry(
                "POST",
                f"{self.base_url}/grade/batch",
                batch_request
            )
            
            # Parse batch response
            results = []
            for item in response.get("results", []):
                api_response = GradingAPIResponse(**item)
                if api_response.success:
                    results.append(self._convert_to_grading_result(api_response))
                else:
                    # Create error result
                    results.append(GradingResult(
                        score=0,
                        max_score=100,
                        percentage=0.0,
                        feedback=f"Grading failed: {api_response.error_message}",
                        suggestions="Please review the submission manually."
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Batch grading failed: {str(e)}")
            raise AIServiceError(f"Batch grading failed: {str(e)}")
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check the health of the AI grading API."""
        if not self.base_url:
            return {"status": "unavailable", "message": "API URL not configured"}
        
        try:
            response = await self._make_api_call_with_retry(
                "GET",
                f"{self.base_url}/health",
                timeout=10
            )
            
            return {
                "status": "healthy",
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"AI grading API health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_supported_models(self) -> List[str]:
        """Get list of supported AI models."""
        if not self.base_url:
            return []
        
        try:
            response = await self._make_api_call_with_retry(
                "GET",
                f"{self.base_url}/models"
            )
            
            return response.get("models", [])
            
        except Exception as e:
            logger.warning(f"Failed to get supported models: {str(e)}")
            return []
    
    async def _make_api_call_with_retry(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make API call with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(**self.client_config) as client:
                    if method.upper() == "GET":
                        response = await client.get(url)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    response.raise_for_status()
                    return response.json()
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"API call failed after {self.max_retries} attempts: {str(e)}")
        
        # If we get here, all retries failed
        raise last_exception
    
    def _convert_to_grading_result(self, api_response: GradingAPIResponse) -> GradingResult:
        """Convert API response to internal GradingResult format."""
        # Calculate percentage if not provided
        percentage = api_response.percentage
        if percentage is None and api_response.score is not None and api_response.max_score:
            percentage = (api_response.score / api_response.max_score) * 100
        
        return GradingResult(
            score=api_response.score or 0,
            max_score=api_response.max_score or 100,
            percentage=percentage or 0.0,
            feedback=api_response.feedback or "No feedback provided",
            suggestions=api_response.suggestions,
            strengths=api_response.strengths,
            weaknesses=api_response.weaknesses,
            rubric_scores=api_response.rubric_scores,
            confidence=api_response.confidence,
            processing_time_ms=api_response.processing_time_ms
        )


class MockAIGradingAPIClient(AIGradingAPIClient):
    """Mock AI grading API client for testing and development."""
    
    def __init__(self):
        super().__init__()
        self.mock_delay = 2.0  # Simulate API processing time
    
    async def grade_submission(
        self,
        grading_request: GradingRequest,
        ai_model: Optional[str] = None
    ) -> GradingResult:
        """Mock grading implementation."""
        # Simulate processing time
        await asyncio.sleep(self.mock_delay)
        
        # Generate mock score based on content length and keywords
        content = grading_request.student_answer.lower()
        base_score = min(len(content) // 10, grading_request.max_score)
        
        # Bonus points for good keywords
        good_keywords = ["because", "therefore", "analysis", "conclusion", "evidence"]
        bonus = sum(5 for keyword in good_keywords if keyword in content)
        
        final_score = min(base_score + bonus, grading_request.max_score)
        percentage = (final_score / grading_request.max_score) * 100
        
        # Generate mock feedback
        feedback_parts = []
        if final_score >= grading_request.max_score * 0.8:
            feedback_parts.append("Excellent work! Your answer demonstrates strong understanding.")
        elif final_score >= grading_request.max_score * 0.6:
            feedback_parts.append("Good effort. Your answer shows understanding but could be improved.")
        else:
            feedback_parts.append("Your answer needs improvement. Consider providing more detail.")
        
        if "because" in content:
            feedback_parts.append("Good use of reasoning and explanation.")
        
        if len(content) < 50:
            feedback_parts.append("Consider providing more detailed explanations.")
        
        return GradingResult(
            score=final_score,
            max_score=grading_request.max_score,
            percentage=percentage,
            feedback=" ".join(feedback_parts),
            suggestions="Try to provide more specific examples and detailed explanations.",
            strengths=["Clear writing", "Relevant content"] if final_score > 50 else None,
            weaknesses=["Needs more detail", "Could use more examples"] if final_score < 80 else None,
            confidence=0.85,
            processing_time_ms=int(self.mock_delay * 1000)
        )
    
    async def batch_grade_submissions(
        self,
        grading_requests: List[GradingRequest],
        ai_model: Optional[str] = None
    ) -> List[GradingResult]:
        """Mock batch grading implementation."""
        results = []
        for request in grading_requests:
            result = await self.grade_submission(request, ai_model)
            results.append(result)
        return results
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "message": "Mock AI grading API is running",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_supported_models(self) -> List[str]:
        """Mock supported models."""
        return ["gpt-4", "gpt-3.5-turbo", "claude-3", "mock-grader-v1"]


# Factory function to get the appropriate client
def get_ai_grading_client() -> AIGradingAPIClient:
    """Get AI grading client (real or mock based on configuration)."""
    settings = get_settings()
    
    # Use mock client in development/testing or when API URL is not configured
    if (settings.is_development or 
        settings.is_testing or 
        not settings.AI_GRADING_API_URL):
        logger.info("Using mock AI grading client")
        return MockAIGradingAPIClient()
    else:
        logger.info("Using real AI grading client")
        return AIGradingAPIClient()


# Global client instance
_ai_grading_client: Optional[AIGradingAPIClient] = None


async def get_ai_grading_api_client() -> AIGradingAPIClient:
    """Get singleton AI grading API client."""
    global _ai_grading_client
    if _ai_grading_client is None:
        _ai_grading_client = get_ai_grading_client()
    return _ai_grading_client