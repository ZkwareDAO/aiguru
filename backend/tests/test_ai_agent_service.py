"""Tests for AI Agent service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.exceptions import AIServiceError, ValidationError
from app.models.ai import ChatMessage, MessageType
from app.models.user import User, UserRole
from app.schemas.ai_agent import ChatResponse, LearningAnalysis, StudyPlan
from app.services.ai_agent_service import AIAgentService


class TestAIAgentService:
    """Test cases for AI Agent service."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return User(
            id=uuid4(),
            email="test@example.com",
            name="Test User",
            role=UserRole.STUDENT,
            password_hash="hashed_password"
        )
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with OpenAI API key."""
        with patch('app.services.ai_agent_service.get_settings') as mock:
            settings = MagicMock()
            settings.OPENAI_API_KEY = "test-api-key"
            mock.return_value = settings
            yield settings
    
    @pytest.fixture
    def ai_agent_service(self, mock_db, mock_settings):
        """Create AI agent service instance for testing."""
        with patch('app.services.ai_agent_service.ChatOpenAI'), \
             patch('app.services.ai_agent_service.UserService'), \
             patch('app.services.ai_agent_service.AnalyticsService'):
            service = AIAgentService(mock_db)
            return service
    
    async def test_init_without_api_key(self, mock_db):
        """Test initialization fails without OpenAI API key."""
        with patch('app.services.ai_agent_service.get_settings') as mock_settings:
            settings = MagicMock()
            settings.OPENAI_API_KEY = None
            mock_settings.return_value = settings
            
            with pytest.raises(AIServiceError, match="OpenAI API key not configured"):
                AIAgentService(mock_db)
    
    async def test_process_chat_message_success(self, ai_agent_service, mock_user, mock_db):
        """Test successful chat message processing."""
        # Mock user service
        ai_agent_service.user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        # Mock agent execution
        ai_agent_service._run_agent_async = AsyncMock(return_value="Test response")
        
        # Mock save chat message
        ai_agent_service._save_chat_message = AsyncMock()
        
        # Test
        response = await ai_agent_service.process_chat_message(
            user_id=mock_user.id,
            message="Hello, can you help me?"
        )
        
        # Assertions
        assert isinstance(response, ChatResponse)
        assert response.message == "Test response"
        assert response.user_id == mock_user.id
        assert ai_agent_service._save_chat_message.call_count == 2  # User message + assistant response
    
    async def test_process_chat_message_user_not_found(self, ai_agent_service, mock_db):
        """Test chat message processing with non-existent user."""
        # Mock user service to return None
        ai_agent_service.user_service.get_user_by_id = AsyncMock(return_value=None)
        
        # Test
        with pytest.raises(ValidationError, match="User not found"):
            await ai_agent_service.process_chat_message(
                user_id=uuid4(),
                message="Hello"
            )
    
    async def test_save_chat_message(self, ai_agent_service, mock_user, mock_db):
        """Test saving chat message to database."""
        # Test
        message = await ai_agent_service._save_chat_message(
            user_id=mock_user.id,
            message_type=MessageType.USER,
            content="Test message"
        )
        
        # Assertions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_get_chat_history(self, ai_agent_service, mock_user, mock_db):
        """Test getting chat history."""
        # Mock database query
        mock_messages = [
            MagicMock(
                id=uuid4(),
                user_id=mock_user.id,
                message_type=MessageType.USER,
                content="Hello",
                created_at=datetime.utcnow()
            ),
            MagicMock(
                id=uuid4(),
                user_id=mock_user.id,
                message_type=MessageType.ASSISTANT,
                content="Hi there!",
                created_at=datetime.utcnow()
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result
        
        # Test
        messages = await ai_agent_service.get_chat_history(mock_user.id, limit=10)
        
        # Assertions
        assert len(messages) == 2
        mock_db.execute.assert_called_once()
    
    async def test_clear_chat_history(self, ai_agent_service, mock_user, mock_db):
        """Test clearing chat history."""
        # Test
        result = await ai_agent_service.clear_chat_history(mock_user.id)
        
        # Assertions
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_analyze_learning_data(self, ai_agent_service, mock_user):
        """Test learning data analysis."""
        # Mock user service
        ai_agent_service.user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        # Mock AI analysis
        ai_agent_service._get_ai_analysis = AsyncMock(return_value="Detailed analysis")
        
        # Test
        analysis = await ai_agent_service.analyze_learning_data(
            user_id=mock_user.id,
            analysis_type="comprehensive"
        )
        
        # Assertions
        assert isinstance(analysis, LearningAnalysis)
        assert analysis.user_id == mock_user.id
        assert len(analysis.knowledge_points) > 0
        assert len(analysis.recommendations) > 0
    
    async def test_generate_study_plan(self, ai_agent_service, mock_user):
        """Test study plan generation."""
        # Mock user service
        ai_agent_service.user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        # Mock AI analysis
        ai_agent_service._get_ai_analysis = AsyncMock(return_value="Study plan recommendations")
        
        # Test
        study_plan = await ai_agent_service.generate_study_plan(
            user_id=mock_user.id,
            goals=["Improve math scores", "Master algebra"],
            available_time_per_day=60,
            target_weeks=4
        )
        
        # Assertions
        assert isinstance(study_plan, StudyPlan)
        assert study_plan.user_id == mock_user.id
        assert len(study_plan.goals) == 2
        assert len(study_plan.weekly_tasks) == 4
        assert study_plan.estimated_total_hours > 0
    
    async def test_update_user_context(self, ai_agent_service, mock_user):
        """Test updating user context."""
        # Mock save chat message
        ai_agent_service._save_chat_message = AsyncMock()
        
        # Test
        context_data = {
            "learning_style": "visual",
            "preferred_subjects": ["mathematics", "science"]
        }
        
        result = await ai_agent_service.update_user_context(
            user_id=mock_user.id,
            context_data=context_data
        )
        
        # Assertions
        assert result is True
        ai_agent_service._save_chat_message.assert_called_once()
    
    async def test_get_ai_analysis(self, ai_agent_service):
        """Test AI analysis method."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "AI analysis result"
        ai_agent_service.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        # Test
        messages = []  # Mock messages
        result = await ai_agent_service._get_ai_analysis(messages)
        
        # Assertions
        assert result == "AI analysis result"
        ai_agent_service.llm.ainvoke.assert_called_once()
    
    async def test_get_ai_analysis_error(self, ai_agent_service):
        """Test AI analysis method with error."""
        # Mock LLM to raise exception
        ai_agent_service.llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
        
        # Test
        messages = []
        result = await ai_agent_service._get_ai_analysis(messages)
        
        # Assertions
        assert "Unable to generate AI analysis" in result


@pytest.mark.asyncio
class TestAIAgentServiceIntegration:
    """Integration tests for AI Agent service."""
    
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow."""
        # This would be an integration test with a real database
        # For now, we'll skip this as it requires more setup
        pass
    
    async def test_learning_analysis_with_real_data(self):
        """Test learning analysis with actual user data."""
        # This would test with real user performance data
        # For now, we'll skip this as it requires database setup
        pass