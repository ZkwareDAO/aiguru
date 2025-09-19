"""Test conversation history and context management."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.ai import ChatMessage, MessageType
from app.models.user import User, UserRole
from app.services.ai_agent_service import AIAgentService


async def test_conversation_context():
    """Test conversation context retrieval and analysis."""
    print("Testing Conversation Context Management...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService') as mock_analytics_service_class:
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        # Mock analytics service
        mock_analytics_service = AsyncMock()
        mock_analytics_service.analyze_learning_patterns.return_value = {
            "consistency": 0.75,
            "score_trend": "improving",
            "peak_performance_time": "morning"
        }
        mock_analytics_service.identify_weak_areas.return_value = [
            {"area": "Quadratic Equations", "subject": "mathematics", "severity": "medium"}
        ]
        mock_analytics_service.calculate_mastery_levels.return_value = {
            "Linear Equations": 0.9,
            "Algebra Basics": 0.85
        }
        mock_analytics_service_class.return_value = mock_analytics_service
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Mock chat history
        mock_messages = [
            MagicMock(
                message_type=MessageType.USER,
                content="How do I solve quadratic equations?",
                created_at=datetime.utcnow(),
                context_data=None,
                is_user_message=True,
                is_assistant_message=False,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.ASSISTANT,
                content="To solve quadratic equations, you can use several methods...",
                created_at=datetime.utcnow(),
                context_data={"topic": "quadratic_equations"},
                response_time_ms=1500,
                is_user_message=False,
                is_assistant_message=True,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="Can you give me an example?",
                created_at=datetime.utcnow(),
                context_data=None,
                is_user_message=True,
                is_assistant_message=False,
                is_system_message=False
            )
        ]
        
        ai_service.get_chat_history = AsyncMock(return_value=mock_messages)
        
        # Test context retrieval
        print("  Testing context retrieval...")
        user_id = uuid4()
        context = await ai_service.get_conversation_context(
            user_id=user_id,
            conversation_id="test_conv_123",
            limit=10
        )
        
        # Verify context structure
        assert "user_id" in context
        assert "conversation_id" in context
        assert "recent_messages" in context
        assert "learning_context" in context
        assert "conversation_patterns" in context
        assert "context_summary" in context
        
        print("  ✅ Context structure correct")
        
        # Test learning context
        learning_ctx = context["learning_context"]
        assert "weak_areas" in learning_ctx
        assert "strong_areas" in learning_ctx
        assert "consistency" in learning_ctx
        assert learning_ctx["consistency"] == 0.75
        
        print("  ✅ Learning context properly integrated")
        
        # Test conversation patterns
        patterns = context["conversation_patterns"]
        assert "total_messages" in patterns
        assert "engagement_level" in patterns
        assert "topics" in patterns
        assert patterns["total_messages"] == 3
        
        print("  ✅ Conversation patterns analyzed")


async def test_conversation_quality_evaluation():
    """Test conversation quality evaluation."""
    print("\nTesting Conversation Quality Evaluation...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Create mock messages with different quality characteristics
        high_quality_messages = [
            MagicMock(
                message_type=MessageType.USER,
                content="How do I solve this quadratic equation: x² + 5x + 6 = 0?",
                is_user_message=True,
                is_assistant_message=False,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.ASSISTANT,
                content="Let me help you solve this step by step. First, we can try factoring. We need two numbers that multiply to 6 and add to 5. Those numbers are 2 and 3. So we can factor as (x + 2)(x + 3) = 0.",
                response_time_ms=2000,
                context_data={"method": "factoring", "topic": "quadratic"},
                is_user_message=False,
                is_assistant_message=True,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="That makes sense! Can you show me another example?",
                is_user_message=True,
                is_assistant_message=False,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.ASSISTANT,
                content="Of course! Let's try x² - 7x + 12 = 0. For this one, we need two numbers that multiply to 12 and add to -7. Those are -3 and -4. So we get (x - 3)(x - 4) = 0, which gives us x = 3 or x = 4.",
                response_time_ms=1800,
                context_data={"method": "factoring", "example": "second"},
                is_user_message=False,
                is_assistant_message=True,
                is_system_message=False
            )
        ]
        
        # Test quality evaluation
        print("  Testing quality evaluation with high-quality conversation...")
        quality_eval = await ai_service.evaluate_conversation_quality(
            user_id=uuid4(),
            recent_messages=high_quality_messages
        )
        
        # Verify evaluation structure
        assert "quality_score" in quality_eval
        assert "metrics" in quality_eval
        assert "suggestions" in quality_eval
        assert "conversation_length" in quality_eval
        
        print("  ✅ Quality evaluation structure correct")
        
        # Test individual metrics
        metrics = quality_eval["metrics"]
        expected_metrics = ["responsiveness", "helpfulness", "engagement", "clarity", "personalization"]
        
        for metric in expected_metrics:
            assert metric in metrics
            assert 0 <= metrics[metric] <= 1
        
        print("  ✅ All quality metrics calculated")
        
        # Test that high-quality conversation gets good scores
        assert quality_eval["quality_score"] > 0.5, "High-quality conversation should score well"
        print(f"    Quality score: {quality_eval['quality_score']:.2f}")
        
        # Test with low-quality conversation
        print("  Testing with low-quality conversation...")
        low_quality_messages = [
            MagicMock(
                message_type=MessageType.USER,
                content="help",
                is_user_message=True,
                is_assistant_message=False,
                is_system_message=False
            ),
            MagicMock(
                message_type=MessageType.ASSISTANT,
                content="ok",
                response_time_ms=5000,  # Slow response
                context_data=None,
                is_user_message=False,
                is_assistant_message=True,
                is_system_message=False
            )
        ]
        
        low_quality_eval = await ai_service.evaluate_conversation_quality(
            user_id=uuid4(),
            recent_messages=low_quality_messages
        )
        
        # Low quality should score lower
        assert low_quality_eval["quality_score"] < quality_eval["quality_score"], \
            "Low-quality conversation should score lower"
        
        print("  ✅ Quality evaluation correctly distinguishes conversation quality")


async def test_conversation_patterns_analysis():
    """Test conversation pattern analysis."""
    print("\nTesting Conversation Pattern Analysis...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Test with engaged conversation
        print("  Testing engaged conversation pattern...")
        engaged_messages = [
            MagicMock(
                message_type=MessageType.USER,
                content="How do I approach algebra problems?",
                is_user_message=True,
                is_assistant_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="What about quadratic equations specifically?",
                is_user_message=True,
                is_assistant_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="I don't understand the discriminant. Can you help explain it?",
                is_user_message=True,
                is_assistant_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="Can you give me more examples to practice with?",
                is_user_message=True,
                is_assistant_message=False
            )
        ]
        
        patterns = ai_service._analyze_conversation_patterns(engaged_messages)
        
        # Verify pattern analysis
        assert patterns["total_messages"] == 4
        assert patterns["user_messages"] == 4
        assert patterns["question_count"] >= 2  # Should detect questions
        assert patterns["help_requests"] >= 1  # Should detect help request
        assert patterns["engagement_level"] in ["low", "medium", "high"]
        
        print("  ✅ Conversation patterns correctly analyzed")
        
        # Test topic extraction
        print("  Testing topic extraction...")
        math_messages = [
            MagicMock(
                message_type=MessageType.USER,
                content="I need help with algebra and geometry",
                is_user_message=True,
                is_assistant_message=False
            ),
            MagicMock(
                message_type=MessageType.USER,
                content="What about calculus derivatives?",
                is_user_message=True,
                is_assistant_message=False
            )
        ]
        
        math_patterns = ai_service._analyze_conversation_patterns(math_messages)
        topics = math_patterns["topics"]
        
        # Should extract math topics
        expected_topics = ["algebra", "geometry", "calculus"]
        found_topics = [topic for topic in expected_topics if topic in topics]
        assert len(found_topics) > 0, "Should extract math topics from conversation"
        
        print("  ✅ Topic extraction working")


async def test_memory_management():
    """Test conversation memory management."""
    print("\nTesting Memory Management...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Mock save chat message
        ai_service._save_chat_message = AsyncMock()
        ai_service.clear_chat_history = AsyncMock(return_value=True)
        ai_service.get_conversation_context = AsyncMock(return_value={"test": "context"})
        
        user_id = uuid4()
        
        # Test save context
        print("  Testing save context...")
        result = await ai_service.manage_conversation_memory(
            user_id=user_id,
            action="save_context",
            context_data={"important_topic": "quadratic_equations", "difficulty": "medium"}
        )
        
        assert result["status"] == "success"
        ai_service._save_chat_message.assert_called_once()
        print("  ✅ Context saving works")
        
        # Test load context
        print("  Testing load context...")
        result = await ai_service.manage_conversation_memory(
            user_id=user_id,
            action="load_context",
            conversation_id="test_conv"
        )
        
        assert result["status"] == "success"
        assert "context" in result
        print("  ✅ Context loading works")
        
        # Test clear memory
        print("  Testing clear memory...")
        result = await ai_service.manage_conversation_memory(
            user_id=user_id,
            action="clear_memory"
        )
        
        assert result["status"] == "success"
        ai_service.clear_chat_history.assert_called_once()
        print("  ✅ Memory clearing works")
        
        # Test invalid action
        print("  Testing invalid action handling...")
        try:
            await ai_service.manage_conversation_memory(
                user_id=user_id,
                action="invalid_action"
            )
            assert False, "Should raise ValidationError"
        except Exception as e:
            assert "Unknown action" in str(e)
        
        print("  ✅ Invalid action properly handled")


async def test_context_summary_generation():
    """Test context summary generation."""
    print("\nTesting Context Summary Generation...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Test with various learning patterns
        print("  Testing context summary with different patterns...")
        
        # High consistency student
        learning_patterns = {"consistency": 0.9, "score_trend": "improving"}
        weak_areas = [{"area": "Geometry Proofs", "severity": "medium"}]
        conversation_patterns = {"engagement_level": "high", "help_requests": 1}
        
        summary = ai_service._generate_context_summary(
            learning_patterns, weak_areas, conversation_patterns
        )
        
        assert "high consistency" in summary.lower()
        assert "geometry proofs" in summary.lower()
        assert "highly engaged" in summary.lower()
        
        print("  ✅ High-performing student summary correct")
        
        # Struggling student
        learning_patterns = {"consistency": 0.3, "score_trend": "declining"}
        weak_areas = [{"area": "Algebra Basics", "severity": "high"}]
        conversation_patterns = {"engagement_level": "low", "help_requests": 5}
        
        summary = ai_service._generate_context_summary(
            learning_patterns, weak_areas, conversation_patterns
        )
        
        assert "consistency" in summary.lower()
        assert "algebra basics" in summary.lower()
        assert "help" in summary.lower()
        
        print("  ✅ Struggling student summary correct")
        
        # New student
        learning_patterns = {}
        weak_areas = []
        conversation_patterns = {"engagement_level": "new", "help_requests": 0}
        
        summary = ai_service._generate_context_summary(
            learning_patterns, weak_areas, conversation_patterns
        )
        
        assert "new conversation" in summary.lower() or "limited context" in summary.lower()
        
        print("  ✅ New student summary correct")


async def main():
    """Run all conversation management tests."""
    print("Running Conversation Management Tests...\n")
    
    await test_conversation_context()
    await test_conversation_quality_evaluation()
    await test_conversation_patterns_analysis()
    await test_memory_management()
    await test_context_summary_generation()
    
    print("\n🎉 All conversation management tests passed!")


if __name__ == "__main__":
    asyncio.run(main())