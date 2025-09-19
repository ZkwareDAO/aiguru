"""Tests for AI grading API integration."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AIServiceError, ExternalServiceError
from app.schemas.grading import GradingRequest, GradingResult
from app.services.ai_grading_api import (
    AIGradingAPIClient,
    MockAIGradingAPIClient,
    get_ai_grading_client,
    GradingAPIRequest,
    GradingAPIResponse
)


class TestAIGradingAPIClient:
    """Test AI grading API client."""
    
    @pytest.fixture
    def grading_request(self):
        """Create test grading request."""
        return GradingRequest(
            submission_id="123e4567-e89b-12d3-a456-426614174000",
            assignment_title="Math Assignment",
            assignment_description="Solve the following problems",
            assignment_instructions="Show your work",
            student_answer="2 + 2 = 4 because addition is commutative",
            max_score=100
        )
    
    @pytest.fixture
    def mock_api_response(self):
        """Create mock API response."""
        return {
            "success": True,
            "score": 85,
            "max_score": 100,
            "percentage": 85.0,
            "feedback": "Good work! Your answer is correct and well explained.",
            "suggestions": "Consider providing more examples.",
            "strengths": ["Clear reasoning", "Correct answer"],
            "weaknesses": ["Could use more detail"],
            "confidence": 0.9,
            "processing_time_ms": 1500
        }
    
    async def test_mock_client_grade_submission(self, grading_request):
        """Test mock client grading functionality."""
        client = MockAIGradingAPIClient()
        
        result = await client.grade_submission(grading_request)
        
        assert isinstance(result, GradingResult)
        assert result.score >= 0
        assert result.max_score == grading_request.max_score
        assert result.percentage >= 0
        assert result.feedback is not None
        assert result.confidence is not None
    
    async def test_mock_client_batch_grading(self, grading_request):
        """Test mock client batch grading."""
        client = MockAIGradingAPIClient()
        
        requests = [grading_request, grading_request]
        results = await client.batch_grade_submissions(requests)
        
        assert len(results) == 2
        assert all(isinstance(r, GradingResult) for r in results)
    
    async def test_mock_client_health_check(self):
        """Test mock client health check."""
        client = MockAIGradingAPIClient()
        
        health = await client.check_api_health()
        
        assert health["status"] == "healthy"
        assert "timestamp" in health
    
    async def test_mock_client_supported_models(self):
        """Test mock client supported models."""
        client = MockAIGradingAPIClient()
        
        models = await client.get_supported_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "mock-grader-v1" in models
    
    @patch('httpx.AsyncClient')
    async def test_real_client_successful_grading(
        self,
        mock_client_class,
        grading_request,
        mock_api_response
    ):
        """Test real client successful grading."""
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Create client with mock settings
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            mock_settings.return_value.AI_GRADING_API_KEY = "test-key"
            
            client = AIGradingAPIClient()
            result = await client.grade_submission(grading_request)
        
        assert isinstance(result, GradingResult)
        assert result.score == 85
        assert result.max_score == 100
        assert result.percentage == 85.0
        assert result.feedback == "Good work! Your answer is correct and well explained."
    
    @patch('httpx.AsyncClient')
    async def test_real_client_api_error(
        self,
        mock_client_class,
        grading_request
    ):
        """Test real client API error handling."""
        # Mock HTTP client to raise error
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            mock_settings.return_value.AI_GRADING_API_KEY = "test-key"
            
            client = AIGradingAPIClient()
            
            with pytest.raises(AIServiceError):
                await client.grade_submission(grading_request)
    
    async def test_client_no_api_url_configured(self, grading_request):
        """Test client behavior when API URL is not configured."""
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.AI_GRADING_API_URL = None
            
            client = AIGradingAPIClient()
            
            with pytest.raises(Exception):  # Should raise configuration error
                await client.grade_submission(grading_request)
    
    @patch('httpx.AsyncClient')
    async def test_real_client_retry_logic(
        self,
        mock_client_class,
        grading_request,
        mock_api_response
    ):
        """Test real client retry logic."""
        # Mock HTTP client to fail first two times, succeed on third
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status.return_value = None
        
        # First two calls fail, third succeeds
        mock_client.post.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            mock_response
        ]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            mock_settings.return_value.AI_GRADING_API_KEY = "test-key"
            
            client = AIGradingAPIClient()
            result = await client.grade_submission(grading_request)
        
        # Should succeed after retries
        assert isinstance(result, GradingResult)
        assert result.score == 85
        
        # Should have made 3 calls (2 failures + 1 success)
        assert mock_client.post.call_count == 3
    
    @patch('httpx.AsyncClient')
    async def test_real_client_max_retries_exceeded(
        self,
        mock_client_class,
        grading_request
    ):
        """Test real client when max retries are exceeded."""
        # Mock HTTP client to always fail
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            mock_settings.return_value.AI_GRADING_API_KEY = "test-key"
            
            client = AIGradingAPIClient()
            
            with pytest.raises(Exception):
                await client.grade_submission(grading_request)
        
        # Should have made max_retries calls
        assert mock_client.post.call_count == client.max_retries
    
    def test_grading_api_request_validation(self):
        """Test grading API request validation."""
        # Valid request
        request = GradingAPIRequest(
            assignment_title="Test Assignment",
            student_answer="Test answer",
            max_score=100
        )
        assert request.assignment_title == "Test Assignment"
        assert request.max_score == 100
        
        # Test with all fields
        full_request = GradingAPIRequest(
            assignment_title="Math Test",
            assignment_description="Algebra problems",
            assignment_instructions="Show work",
            student_answer="x = 5",
            rubric={"accuracy": 50, "method": 50},
            grading_criteria=["Correct answer", "Clear work"],
            max_score=100,
            ai_model="gpt-4"
        )
        assert full_request.rubric == {"accuracy": 50, "method": 50}
        assert len(full_request.grading_criteria) == 2
    
    def test_grading_api_response_parsing(self):
        """Test grading API response parsing."""
        # Successful response
        response_data = {
            "success": True,
            "score": 90,
            "max_score": 100,
            "percentage": 90.0,
            "feedback": "Excellent work!",
            "confidence": 0.95
        }
        
        response = GradingAPIResponse(**response_data)
        assert response.success is True
        assert response.score == 90
        assert response.confidence == 0.95
        
        # Failed response
        failed_response_data = {
            "success": False,
            "error_message": "Invalid input",
            "error_code": "INVALID_INPUT"
        }
        
        failed_response = GradingAPIResponse(**failed_response_data)
        assert failed_response.success is False
        assert failed_response.error_message == "Invalid input"
    
    def test_get_ai_grading_client_factory(self):
        """Test AI grading client factory function."""
        # Test development environment (should return mock)
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.is_development = True
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            
            client = get_ai_grading_client()
            assert isinstance(client, MockAIGradingAPIClient)
        
        # Test production environment with API URL (should return real client)
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.is_development = False
            mock_settings.return_value.is_testing = False
            mock_settings.return_value.AI_GRADING_API_URL = "https://api.example.com"
            
            client = get_ai_grading_client()
            assert isinstance(client, AIGradingAPIClient)
            assert not isinstance(client, MockAIGradingAPIClient)
        
        # Test production environment without API URL (should return mock)
        with patch('app.services.ai_grading_api.get_settings') as mock_settings:
            mock_settings.return_value.is_development = False
            mock_settings.return_value.is_testing = False
            mock_settings.return_value.AI_GRADING_API_URL = None
            
            client = get_ai_grading_client()
            assert isinstance(client, MockAIGradingAPIClient)
    
    async def test_mock_grading_scoring_logic(self):
        """Test mock grading scoring logic."""
        client = MockAIGradingAPIClient()
        
        # Test short answer
        short_request = GradingRequest(
            submission_id="123e4567-e89b-12d3-a456-426614174000",
            assignment_title="Test",
            student_answer="Yes",
            max_score=100
        )
        short_result = await client.grade_submission(short_request)
        
        # Test long answer with good keywords
        long_request = GradingRequest(
            submission_id="123e4567-e89b-12d3-a456-426614174000",
            assignment_title="Test",
            student_answer="This is a detailed analysis because the evidence shows that therefore we can conclude",
            max_score=100
        )
        long_result = await client.grade_submission(long_request)
        
        # Long answer with keywords should score higher
        assert long_result.score >= short_result.score
        assert "Good use of reasoning" in long_result.feedback
    
    async def test_convert_to_grading_result(self):
        """Test conversion from API response to GradingResult."""
        client = AIGradingAPIClient()
        
        api_response = GradingAPIResponse(
            success=True,
            score=85,
            max_score=100,
            percentage=None,  # Should be calculated
            feedback="Good work",
            suggestions="Add more detail",
            confidence=0.9
        )
        
        result = client._convert_to_grading_result(api_response)
        
        assert result.score == 85
        assert result.max_score == 100
        assert result.percentage == 85.0  # Should be calculated
        assert result.feedback == "Good work"
        assert result.suggestions == "Add more detail"
        assert result.confidence == 0.9