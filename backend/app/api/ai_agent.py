"""AI Agent API endpoints for intelligent conversations and learning analysis."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import AIServiceError, ValidationError
from app.models.user import User
from app.schemas.ai_agent import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    LearningAnalysisRequest,
    LearningAnalysis,
    StudyPlan,
    ContextData,
    AgentStatus
)
from app.services.ai_agent_service import AIAgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-agent", tags=["AI Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Send a message to the AI agent and get a response.
    
    This endpoint allows users to have conversations with the AI agent,
    which can help with learning questions, analysis, and recommendations.
    """
    try:
        agent_service = AIAgentService(db)
        
        response = await agent_service.process_chat_message(
            user_id=current_user.id,
            message=request.message,
            context_data=request.context_data
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error in chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        logger.error(f"AI service error in chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = Query(50, ge=1, le=100, description="Number of messages to retrieve"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ChatHistoryResponse:
    """
    Get chat history for the current user.
    
    Returns a paginated list of chat messages between the user and the AI agent.
    """
    try:
        agent_service = AIAgentService(db)
        
        messages = await agent_service.get_chat_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        # Convert messages to dict format
        message_dicts = []
        for msg in messages:
            message_dicts.append({
                "id": str(msg.id),
                "message_type": msg.message_type,
                "content": msg.content,
                "context_data": msg.context_data,
                "created_at": msg.created_at,
                "response_time_ms": msg.response_time_ms
            })
        
        # Check if there are more messages
        has_more = len(messages) == limit
        
        return ChatHistoryResponse(
            messages=message_dicts,
            total_count=len(messages) + offset,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )


@router.delete("/chat/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Clear chat history for the current user.
    
    This will permanently delete all chat messages for the user.
    """
    try:
        agent_service = AIAgentService(db)
        
        success = await agent_service.clear_chat_history(current_user.id)
        
        if success:
            return {"message": "Chat history cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear chat history"
            )
            
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )


@router.post("/analyze/learning", response_model=LearningAnalysis)
async def analyze_learning_data(
    request: LearningAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LearningAnalysis:
    """
    Analyze user's learning data and provide insights.
    
    This endpoint uses AI to analyze the user's learning performance,
    identify strengths and weaknesses, and provide recommendations.
    """
    try:
        agent_service = AIAgentService(db)
        
        analysis = await agent_service.analyze_learning_data(
            user_id=current_user.id,
            analysis_type=request.analysis_type,
            time_period=request.time_period,
            subjects=request.subjects,
            include_recommendations=request.include_recommendations
        )
        
        return analysis
        
    except ValidationError as e:
        logger.warning(f"Validation error in learning analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        logger.error(f"AI service error in learning analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in learning analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during analysis"
        )


@router.post("/study-plan/generate", response_model=StudyPlan)
async def generate_study_plan(
    goals: List[str],
    available_time_per_day: int = Query(..., ge=15, le=480, description="Available study time per day in minutes"),
    target_weeks: int = Query(4, ge=1, le=12, description="Number of weeks for the study plan"),
    difficulty_level: str = Query("intermediate", description="Preferred difficulty level"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StudyPlan:
    """
    Generate a personalized study plan based on user goals and constraints.
    
    This endpoint creates a detailed study plan with weekly tasks,
    goals, and recommendations based on the user's learning data.
    """
    try:
        agent_service = AIAgentService(db)
        
        study_plan = await agent_service.generate_study_plan(
            user_id=current_user.id,
            goals=goals,
            available_time_per_day=available_time_per_day,
            target_weeks=target_weeks,
            difficulty_level=difficulty_level
        )
        
        return study_plan
        
    except ValidationError as e:
        logger.warning(f"Validation error in study plan generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        logger.error(f"AI service error in study plan generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Study plan generation service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in study plan generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during study plan generation"
        )


@router.put("/context")
async def update_user_context(
    context: ContextData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Update user context for better AI personalization.
    
    This endpoint allows users to update their learning preferences,
    goals, and other context information to improve AI responses.
    """
    try:
        agent_service = AIAgentService(db)
        
        success = await agent_service.update_user_context(
            user_id=current_user.id,
            context_data=context.dict(exclude_none=True)
        )
        
        if success:
            return {"message": "User context updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user context"
            )
            
    except Exception as e:
        logger.error(f"Error updating user context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user context"
        )


@router.get("/status", response_model=AgentStatus)
async def get_agent_status(
    db: AsyncSession = Depends(get_db)
) -> AgentStatus:
    """
    Get the current status of the AI agent service.
    
    This endpoint provides information about the AI agent's availability,
    current load, and performance metrics.
    """
    try:
        from datetime import datetime
        
        # For now, return a mock status
        # In a full implementation, this would check actual service health
        return AgentStatus(
            is_available=True,
            current_load=0,
            average_response_time_ms=1200,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )


@router.get("/resources/{topic}")
async def get_learning_resources(
    topic: str,
    difficulty_level: str = Query("intermediate", description="Difficulty level for resources"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized learning resources for a specific topic.
    
    This endpoint provides curated learning resources based on the user's
    learning patterns and current mastery level.
    """
    try:
        agent_service = AIAgentService(db)
        
        resources = await agent_service.generate_learning_resources(
            user_id=current_user.id,
            topic=topic,
            difficulty_level=difficulty_level
        )
        
        return {
            "topic": topic,
            "difficulty_level": difficulty_level,
            "resources": resources,
            "generated_at": datetime.utcnow()
        }
        
    except ValidationError as e:
        logger.warning(f"Validation error in resource generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        logger.error(f"AI service error in resource generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resource generation service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in resource generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/feedback/adaptive")
async def get_adaptive_feedback(
    recent_performance: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get adaptive feedback based on recent performance.
    
    This endpoint analyzes recent performance data and provides
    personalized feedback and recommendations.
    """
    try:
        agent_service = AIAgentService(db)
        
        feedback = await agent_service.generate_adaptive_feedback(
            user_id=current_user.id,
            recent_performance=recent_performance
        )
        
        return feedback
        
    except ValidationError as e:
        logger.warning(f"Validation error in adaptive feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        logger.error(f"AI service error in adaptive feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Adaptive feedback service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in adaptive feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/recommendations/personalized")
async def get_personalized_recommendations(
    limit: int = Query(5, ge=1, le=10, description="Number of recommendations to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized learning recommendations.
    
    This endpoint provides AI-generated recommendations based on the user's
    complete learning profile and recent activity.
    """
    try:
        agent_service = AIAgentService(db)
        
        # Get comprehensive learning analysis
        analysis = await agent_service.analyze_learning_data(
            user_id=current_user.id,
            analysis_type="comprehensive",
            include_recommendations=True
        )
        
        # Get additional personalized recommendations
        learning_patterns = await agent_service.analytics_service.analyze_learning_patterns(current_user.id)
        weak_areas = await agent_service.analytics_service.identify_weak_areas(current_user.id)
        
        additional_recommendations = await agent_service._generate_personalized_recommendations(
            current_user.id, learning_patterns, weak_areas, "Comprehensive analysis"
        )
        
        # Combine and limit recommendations
        all_recommendations = analysis.recommendations + additional_recommendations
        unique_recommendations = list(dict.fromkeys(all_recommendations))[:limit]
        
        return {
            "recommendations": unique_recommendations,
            "based_on": {
                "learning_patterns": learning_patterns,
                "weak_areas": [wa["area"] for wa in weak_areas],
                "overall_performance": analysis.overall_performance
            },
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get personalized recommendations"
        )


@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    feedback: Optional[str] = Query(None, description="Optional feedback text"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Submit feedback for an AI agent response.
    
    This endpoint allows users to rate and provide feedback on AI responses
    to help improve the service quality.
    """
    try:
        # For now, just log the feedback
        # In a full implementation, this would store feedback in the database
        logger.info(f"User {current_user.id} rated message {message_id} with {rating}/5")
        if feedback:
            logger.info(f"Feedback: {feedback}")
        
        return {"message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/conversation/context")
async def get_conversation_context(
    conversation_id: Optional[str] = Query(None, description="Conversation ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of recent messages to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get conversation context for better AI responses.
    
    This endpoint provides comprehensive context including recent messages,
    learning patterns, and conversation analysis.
    """
    try:
        agent_service = AIAgentService(db)
        
        context = await agent_service.get_conversation_context(
            user_id=current_user.id,
            conversation_id=conversation_id,
            limit=limit
        )
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation context"
        )


@router.get("/conversation/quality")
async def evaluate_conversation_quality(
    conversation_id: Optional[str] = Query(None, description="Conversation ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Evaluate the quality of recent conversations.
    
    This endpoint analyzes conversation patterns and provides quality metrics
    and suggestions for improvement.
    """
    try:
        agent_service = AIAgentService(db)
        
        quality_evaluation = await agent_service.evaluate_conversation_quality(
            user_id=current_user.id,
            conversation_id=conversation_id
        )
        
        return quality_evaluation
        
    except Exception as e:
        logger.error(f"Error evaluating conversation quality: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate conversation quality"
        )


@router.post("/conversation/memory")
async def manage_conversation_memory(
    action: str = Query(..., description="Action to perform: save_context, load_context, clear_memory, optimize_memory"),
    conversation_id: Optional[str] = Query(None, description="Conversation ID"),
    context_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manage conversation memory and context.
    
    This endpoint allows saving, loading, clearing, and optimizing
    conversation memory for better AI performance.
    """
    try:
        agent_service = AIAgentService(db)
        
        result = await agent_service.manage_conversation_memory(
            user_id=current_user.id,
            action=action,
            conversation_id=conversation_id,
            context_data=context_data
        )
        
        return result
        
    except ValidationError as e:
        logger.warning(f"Validation error in memory management: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error managing conversation memory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to manage conversation memory"
        )