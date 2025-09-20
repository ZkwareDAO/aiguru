"""Schemas for AI Agent service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat messages."""
    
    message: str = Field(..., min_length=1, max_length=2000, description="Chat message content")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Can you help me understand my math performance?",
                "context_data": {"subject": "mathematics", "grade": "10"},
                "session_id": "session_123"
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat messages."""
    
    message: str = Field(..., description="AI assistant response")
    user_id: UUID = Field(..., description="User ID")
    timestamp: datetime = Field(..., description="Response timestamp")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Response context data")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Response confidence score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Based on your recent assignments, I can see that you're doing well in algebra but might need some help with geometry...",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2024-01-15T10:30:00Z",
                "context_data": {"analysis_type": "performance_review"},
                "response_time_ms": 1500,
                "confidence_score": 0.85
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""
    
    messages: List[Dict[str, Any]] = Field(..., description="List of chat messages")
    total_count: int = Field(..., description="Total number of messages")
    has_more: bool = Field(..., description="Whether there are more messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "msg_123",
                        "message_type": "user",
                        "content": "How am I doing in math?",
                        "created_at": "2024-01-15T10:00:00Z"
                    },
                    {
                        "id": "msg_124",
                        "message_type": "assistant",
                        "content": "You're making good progress in math...",
                        "created_at": "2024-01-15T10:00:30Z"
                    }
                ],
                "total_count": 25,
                "has_more": True
            }
        }


class LearningAnalysisRequest(BaseModel):
    """Request schema for learning analysis."""
    
    analysis_type: str = Field(..., description="Type of analysis to perform")
    time_period: Optional[str] = Field("last_month", description="Time period for analysis")
    subjects: Optional[List[str]] = Field(None, description="Specific subjects to analyze")
    include_recommendations: bool = Field(True, description="Whether to include recommendations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_type": "comprehensive",
                "time_period": "last_month",
                "subjects": ["mathematics", "science"],
                "include_recommendations": True
            }
        }


class KnowledgePoint(BaseModel):
    """Schema for knowledge point analysis."""
    
    name: str = Field(..., description="Knowledge point name")
    subject: str = Field(..., description="Subject area")
    mastery_level: float = Field(..., ge=0.0, le=1.0, description="Mastery level (0-1)")
    practice_count: int = Field(..., ge=0, description="Number of practice attempts")
    error_count: int = Field(..., ge=0, description="Number of errors")
    last_practiced: Optional[datetime] = Field(None, description="Last practice date")
    difficulty_level: str = Field(..., description="Difficulty level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Linear Equations",
                "subject": "mathematics",
                "mastery_level": 0.75,
                "practice_count": 15,
                "error_count": 3,
                "last_practiced": "2024-01-15T10:00:00Z",
                "difficulty_level": "intermediate"
            }
        }


class LearningTrend(BaseModel):
    """Schema for learning trend data."""
    
    date: datetime = Field(..., description="Date of the data point")
    score: float = Field(..., ge=0.0, le=100.0, description="Score for the date")
    subject: str = Field(..., description="Subject area")
    assignment_count: int = Field(..., ge=0, description="Number of assignments")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15T00:00:00Z",
                "score": 85.5,
                "subject": "mathematics",
                "assignment_count": 3
            }
        }


class WeakArea(BaseModel):
    """Schema for weak area identification."""
    
    area: str = Field(..., description="Weak area name")
    subject: str = Field(..., description="Subject area")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate (0-1)")
    recommendation: str = Field(..., description="Improvement recommendation")
    practice_resources: List[str] = Field(default_factory=list, description="Recommended practice resources")
    
    class Config:
        json_schema_extra = {
            "example": {
                "area": "Quadratic Equations",
                "subject": "mathematics",
                "severity": "medium",
                "error_rate": 0.35,
                "recommendation": "Focus on factoring techniques and completing the square method",
                "practice_resources": ["Khan Academy - Quadratics", "Practice Worksheet #5"]
            }
        }


class LearningAnalysis(BaseModel):
    """Schema for comprehensive learning analysis."""
    
    user_id: UUID = Field(..., description="User ID")
    analysis_date: datetime = Field(..., description="Analysis date")
    overall_performance: float = Field(..., ge=0.0, le=100.0, description="Overall performance score")
    knowledge_points: List[KnowledgePoint] = Field(..., description="Knowledge point analysis")
    learning_trends: List[LearningTrend] = Field(..., description="Learning trend data")
    weak_areas: List[WeakArea] = Field(..., description="Identified weak areas")
    strengths: List[str] = Field(..., description="Identified strengths")
    recommendations: List[str] = Field(..., description="General recommendations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "analysis_date": "2024-01-15T10:00:00Z",
                "overall_performance": 78.5,
                "knowledge_points": [],
                "learning_trends": [],
                "weak_areas": [],
                "strengths": ["Strong in basic algebra", "Good problem-solving skills"],
                "recommendations": ["Practice more geometry problems", "Review trigonometry basics"]
            }
        }


class StudyGoal(BaseModel):
    """Schema for study goals."""
    
    title: str = Field(..., description="Goal title")
    description: str = Field(..., description="Goal description")
    target_date: datetime = Field(..., description="Target completion date")
    priority: str = Field(..., description="Priority level (low, medium, high)")
    measurable_outcome: str = Field(..., description="Measurable outcome")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Improve Geometry Score",
                "description": "Increase geometry test scores to above 85%",
                "target_date": "2024-02-15T00:00:00Z",
                "priority": "high",
                "measurable_outcome": "Score 85% or higher on next geometry test"
            }
        }


class StudyTask(BaseModel):
    """Schema for study tasks."""
    
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    estimated_time_minutes: int = Field(..., ge=1, description="Estimated time in minutes")
    difficulty_level: str = Field(..., description="Difficulty level")
    resources: List[str] = Field(default_factory=list, description="Required resources")
    due_date: Optional[datetime] = Field(None, description="Due date")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Practice Linear Equations",
                "description": "Complete 10 linear equation problems from chapter 5",
                "estimated_time_minutes": 30,
                "difficulty_level": "intermediate",
                "resources": ["Textbook Chapter 5", "Calculator"],
                "due_date": "2024-01-16T18:00:00Z"
            }
        }


class StudyPlan(BaseModel):
    """Schema for personalized study plans."""
    
    user_id: UUID = Field(..., description="User ID")
    plan_name: str = Field(..., description="Study plan name")
    created_date: datetime = Field(..., description="Plan creation date")
    target_completion_date: datetime = Field(..., description="Target completion date")
    goals: List[StudyGoal] = Field(..., description="Study goals")
    weekly_tasks: Dict[str, List[StudyTask]] = Field(..., description="Weekly task breakdown")
    estimated_total_hours: int = Field(..., ge=0, description="Estimated total study hours")
    difficulty_level: str = Field(..., description="Overall difficulty level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "plan_name": "Mathematics Improvement Plan",
                "created_date": "2024-01-15T10:00:00Z",
                "target_completion_date": "2024-03-15T00:00:00Z",
                "goals": [],
                "weekly_tasks": {
                    "week_1": [],
                    "week_2": []
                },
                "estimated_total_hours": 40,
                "difficulty_level": "intermediate"
            }
        }


class ContextData(BaseModel):
    """Schema for user context data."""
    
    current_subject: Optional[str] = Field(None, description="Current subject being studied")
    learning_style: Optional[str] = Field(None, description="Preferred learning style")
    difficulty_preference: Optional[str] = Field(None, description="Difficulty preference")
    available_study_time: Optional[int] = Field(None, description="Available study time per day (minutes)")
    goals: Optional[List[str]] = Field(None, description="Learning goals")
    interests: Optional[List[str]] = Field(None, description="Subject interests")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_subject": "mathematics",
                "learning_style": "visual",
                "difficulty_preference": "gradual",
                "available_study_time": 60,
                "goals": ["improve test scores", "understand concepts better"],
                "interests": ["algebra", "geometry"]
            }
        }


class AgentStatus(BaseModel):
    """Schema for AI agent status."""
    
    is_available: bool = Field(..., description="Whether the agent is available")
    current_load: int = Field(..., ge=0, description="Current processing load")
    average_response_time_ms: int = Field(..., ge=0, description="Average response time")
    last_updated: datetime = Field(..., description="Last status update")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_available": True,
                "current_load": 5,
                "average_response_time_ms": 1200,
                "last_updated": "2024-01-15T10:00:00Z"
            }
        }