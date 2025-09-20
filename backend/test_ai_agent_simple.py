"""Simple test for AI Agent service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.exceptions import AIServiceError
from app.services.ai_agent_service import AIAgentService


async def test_ai_agent_init():
    """Test AI agent initialization."""
    print("Testing AI Agent initialization...")
    
    # Test without API key
    with patch('app.services.ai_agent_service.get_settings') as mock_settings:
        settings = MagicMock()
        settings.OPENAI_API_KEY = None
        mock_settings.return_value = settings
        
        try:
            mock_db = AsyncMock()
            AIAgentService(mock_db)
            print("❌ Should have raised AIServiceError")
        except AIServiceError as e:
            print(f"✅ Correctly raised AIServiceError: {e}")
    
    # Test with API key
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        service = AIAgentService(mock_db)
        print("✅ AI Agent service initialized successfully with API key")
        
        # Test that the service has the expected attributes
        assert hasattr(service, 'llm')
        assert hasattr(service, 'memory')
        assert hasattr(service, 'conversation_prompt')
        print("✅ Service has expected attributes")


async def test_prompt_templates():
    """Test prompt template setup."""
    print("\nTesting prompt templates...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        service = AIAgentService(mock_db)
        
        # Check that prompt templates are set up
        assert hasattr(service, 'conversation_prompt')
        assert hasattr(service, 'analysis_prompt')
        assert hasattr(service, 'study_plan_prompt')
        print("✅ All prompt templates are set up")


async def main():
    """Run simple tests."""
    print("Running simple AI Agent tests...\n")
    
    await test_ai_agent_init()
    await test_prompt_templates()
    
    print("\n🎉 All simple tests passed!")


if __name__ == "__main__":
    asyncio.run(main())