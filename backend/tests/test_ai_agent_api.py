"""Tests for AI Agent API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.schemas.ai_agent import ChatResponse, LearningAnalysis, StudyPlan


class TestAIAgentAPI:
    """Test cases for AI Agent API endpoints."""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            name="Test User",
            role=UserRole.STUDENT,
            password_hash="hashed_password"
        )
    
    @pytest.fixture
    def mock_chat_response(self, mock_user):
        """Mock chat response."""
        return ChatResponse(
            message="Hello! I'm here to help you with your studies.",
            user_id=mock_user.id,
            timestamp=datetime.utcnow(),
            response_time_ms=1200
        )
    
    @pytest.fixture
    def mock_learning_analysis(self, mock_user):
        """Mock learning analysis."""
        return LearningAnalysis(
            user_id=mock_user.id,
            analysis_date=datetime.utcnow(),
            overall_performance=78.5,
            knowledge_points=[],
            learning_trends=[],
            weak_areas=[],
            strengths=["Strong in algebra"],
            recommendations=["Practice geometry"]
        )
    
    @pytest.fixture
    def mock_study_plan(self, mock_user):
        """Mock study plan."""
        return StudyPlan(
            user_id=mock_user.id,
            plan_name="Test Study Plan",
            created_date=datetime.utcnow(),
            target_completion_date=datetime.utcnow(),
            goals=[],
            weekly_tasks={},
            estimated_total_hours=20,
            difficulty_level="intermediate"
        )
    
    async def test_chat_with_agent_success(self, client: AsyncClient, mock_user, mock_chat_response):
        """Test successful chat with AI agent."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.process_chat_message.return_value = mock_chat_response
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.post(
                "/ai-agent/chat",
                json={
                    "message": "Hello, can you help me with math?",
                    "context_data": {"subject": "mathematics"}
                }
            )
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == mock_chat_response.message
            assert data["user_id"] == str(mock_user.id)
            mock_service.process_chat_message.assert_called_once()
    
    async def test_chat_with_agent_validation_error(self, client: AsyncClient, mock_user):
        """Test chat with validation error."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service to raise validation error
            mock_service = AsyncMock()
            mock_service.process_chat_message.side_effect = Exception("Validation error")
            mock_service_class.return_value = mock_service
            
            # Test request with invalid data
            response = await client.post(
                "/ai-agent/chat",
                json={"message": ""}  # Empty message
            )
            
            # Assertions
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_chat_with_agent_ai_service_error(self, client: AsyncClient, mock_user):
        """Test chat with AI service error."""
        from app.core.exceptions import AIServiceError
        
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service to raise AI service error
            mock_service = AsyncMock()
            mock_service.process_chat_message.side_effect = AIServiceError("AI service unavailable")
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.post(
                "/ai-agent/chat",
                json={"message": "Hello"}
            )
            
            # Assertions
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    async def test_get_chat_history_success(self, client: AsyncClient, mock_user):
        """Test successful chat history retrieval."""
        mock_messages = [
            {
                "id": str(uuid4()),
                "message_type": "user",
                "content": "Hello",
                "created_at": datetime.utcnow().isoformat(),
                "context_data": None,
                "response_time_ms": None
            },
            {
                "id": str(uuid4()),
                "message_type": "assistant",
                "content": "Hi there!",
                "created_at": datetime.utcnow().isoformat(),
                "context_data": None,
                "response_time_ms": 1200
            }
        ]
        
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.get_chat_history.return_value = [MagicMock(**msg) for msg in mock_messages]
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.get("/ai-agent/chat/history?limit=10&offset=0")
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["messages"]) == 2
            assert data["total_count"] == 2
            mock_service.get_chat_history.assert_called_once()
    
    async def test_clear_chat_history_success(self, client: AsyncClient, mock_user):
        """Test successful chat history clearing."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.clear_chat_history.return_value = True
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.delete("/ai-agent/chat/history")
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Chat history cleared successfully"
            mock_service.clear_chat_history.assert_called_once()
    
    async def test_analyze_learning_data_success(self, client: AsyncClient, mock_user, mock_learning_analysis):
        """Test successful learning data analysis."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.analyze_learning_data.return_value = mock_learning_analysis
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.post(
                "/ai-agent/analyze/learning",
                json={
                    "analysis_type": "comprehensive",
                    "time_period": "last_month",
                    "subjects": ["mathematics"],
                    "include_recommendations": True
                }
            )
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == str(mock_user.id)
            assert data["overall_performance"] == 78.5
            mock_service.analyze_learning_data.assert_called_once()
    
    async def test_generate_study_plan_success(self, client: AsyncClient, mock_user, mock_study_plan):
        """Test successful study plan generation."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.generate_study_plan.return_value = mock_study_plan
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.post(
                "/ai-agent/study-plan/generate?available_time_per_day=60&target_weeks=4&difficulty_level=intermediate",
                json=["Improve math scores", "Master algebra"]
            )
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == str(mock_user.id)
            assert data["plan_name"] == "Test Study Plan"
            mock_service.generate_study_plan.assert_called_once()
    
    async def test_update_user_context_success(self, client: AsyncClient, mock_user):
        """Test successful user context update."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user), \
             patch('app.api.ai_agent.AIAgentService') as mock_service_class:
            
            # Mock service
            mock_service = AsyncMock()
            mock_service.update_user_context.return_value = True
            mock_service_class.return_value = mock_service
            
            # Test request
            response = await client.put(
                "/ai-agent/context",
                json={
                    "current_subject": "mathematics",
                    "learning_style": "visual",
                    "available_study_time": 60
                }
            )
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "User context updated successfully"
            mock_service.update_user_context.assert_called_once()
    
    async def test_get_agent_status(self, client: AsyncClient):
        """Test getting agent status."""
        # Test request (no authentication required for status)
        response = await client.get("/ai-agent/status")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_available" in data
        assert "current_load" in data
        assert "average_response_time_ms" in data
    
    async def test_submit_feedback_success(self, client: AsyncClient, mock_user):
        """Test successful feedback submission."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user):
            
            # Test request
            response = await client.post(
                "/ai-agent/feedback?message_id=test_msg_123&rating=5&feedback=Great response!"
            )
            
            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Feedback submitted successfully"
    
    async def test_chat_message_too_long(self, client: AsyncClient, mock_user):
        """Test chat with message that's too long."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user):
            
            # Test request with very long message
            long_message = "x" * 2001  # Exceeds 2000 character limit
            response = await client.post(
                "/ai-agent/chat",
                json={"message": long_message}
            )
            
            # Assertions
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_invalid_study_plan_parameters(self, client: AsyncClient, mock_user):
        """Test study plan generation with invalid parameters."""
        with patch('app.api.ai_agent.get_current_user', return_value=mock_user):
            
            # Test request with invalid time parameter
            response = await client.post(
                "/ai-agent/study-plan/generate?available_time_per_day=0&target_weeks=4",
                json=["Improve math"]
            )
            
            # Assertions
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestAIAgentAPIIntegration:
    """Integration tests for AI Agent API."""
    
    async def test_full_conversation_api_flow(self):
        """Test complete conversation flow through API."""
        # This would be a full integration test
        # For now, we'll skip this as it requires more setup
        pass