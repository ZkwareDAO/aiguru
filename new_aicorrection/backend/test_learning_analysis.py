"""Test enhanced learning analysis functionality."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.user import User, UserRole
from app.services.ai_agent_service import AIAgentService
from app.services.analytics_service import AnalyticsService


async def test_analytics_service():
    """Test analytics service functionality."""
    print("Testing Analytics Service...")
    
    mock_db = AsyncMock()
    analytics_service = AnalyticsService(mock_db)
    
    user_id = uuid4()
    
    # Test get_user_performance_data
    print("  Testing get_user_performance_data...")
    
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    performance_data = await analytics_service.get_user_performance_data(user_id)
    
    assert "total_submissions" in performance_data
    assert "average_score" in performance_data
    print("  ✅ Performance data retrieval works")
    
    # Test identify_weak_areas
    print("  Testing identify_weak_areas...")
    weak_areas = await analytics_service.identify_weak_areas(user_id)
    
    assert isinstance(weak_areas, list)
    if weak_areas:
        assert "area" in weak_areas[0]
        assert "subject" in weak_areas[0]
        assert "severity" in weak_areas[0]
    print("  ✅ Weak area identification works")
    
    # Test calculate_mastery_levels
    print("  Testing calculate_mastery_levels...")
    mastery_levels = await analytics_service.calculate_mastery_levels(user_id)
    
    assert isinstance(mastery_levels, dict)
    for topic, level in mastery_levels.items():
        assert 0 <= level <= 1
    print("  ✅ Mastery level calculation works")
    
    # Test analyze_learning_patterns
    print("  Testing analyze_learning_patterns...")
    patterns = await analytics_service.analyze_learning_patterns(user_id)
    
    assert "total_submissions" in patterns
    assert "score_trend" in patterns
    assert "consistency" in patterns
    print("  ✅ Learning pattern analysis works")


async def test_enhanced_ai_analysis():
    """Test enhanced AI learning analysis."""
    print("\nTesting Enhanced AI Analysis...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService') as mock_user_service_class, \
         patch('app.services.ai_agent_service.AnalyticsService') as mock_analytics_service_class:
        
        # Setup mocks
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        # Mock user
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            name="Test Student",
            role=UserRole.STUDENT,
            password_hash="hashed"
        )
        
        mock_user_service = AsyncMock()
        mock_user_service.get_user_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service
        
        # Mock analytics service
        mock_analytics_service = AsyncMock()
        mock_analytics_service.get_user_performance_data.return_value = {
            "total_submissions": 10,
            "average_score": 75.5,
            "submissions": [
                {"score": 80, "submitted_at": datetime.utcnow()},
                {"score": 70, "submitted_at": datetime.utcnow()}
            ]
        }
        mock_analytics_service.calculate_mastery_levels.return_value = {
            "Linear Equations": 0.85,
            "Quadratic Functions": 0.65
        }
        mock_analytics_service.identify_weak_areas.return_value = [
            {
                "area": "Geometry Proofs",
                "subject": "mathematics",
                "severity": "medium",
                "error_count": 5,
                "total_attempts": 10
            }
        ]
        mock_analytics_service.analyze_learning_patterns.return_value = {
            "total_submissions": 10,
            "score_trend": "improving",
            "consistency": 0.8,
            "strengths": ["Regular study habits", "Strong problem-solving"]
        }
        mock_analytics_service.get_learning_trends.return_value = [
            {
                "date": datetime.utcnow(),
                "average_score": 75,
                "assignments_completed": 2
            }
        ]
        mock_analytics_service_class.return_value = mock_analytics_service
        
        # Create AI agent service
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Mock AI analysis
        ai_service._get_ai_analysis = AsyncMock(return_value="Student shows good progress in algebra but needs work on geometry")
        
        # Test enhanced analysis
        print("  Testing enhanced learning analysis...")
        analysis = await ai_service.analyze_learning_data(
            user_id=mock_user.id,
            analysis_type="comprehensive",
            subjects=["mathematics"]
        )
        
        # Verify analysis results
        assert analysis.user_id == mock_user.id
        assert analysis.overall_performance == 75.5
        assert len(analysis.knowledge_points) > 0
        assert len(analysis.weak_areas) > 0
        assert len(analysis.strengths) > 0
        assert len(analysis.recommendations) > 0
        
        print("  ✅ Enhanced learning analysis works")
        
        # Test knowledge points
        kp = analysis.knowledge_points[0]
        assert hasattr(kp, 'name')
        assert hasattr(kp, 'mastery_level')
        assert 0 <= kp.mastery_level <= 1
        print("  ✅ Knowledge points properly structured")
        
        # Test weak areas
        if analysis.weak_areas:
            wa = analysis.weak_areas[0]
            assert hasattr(wa, 'area')
            assert hasattr(wa, 'severity')
            assert hasattr(wa, 'recommendation')
            print("  ✅ Weak areas properly identified")
        
        # Test recommendations
        assert isinstance(analysis.recommendations, list)
        assert len(analysis.recommendations) > 0
        print("  ✅ Personalized recommendations generated")


async def test_recommendation_generation():
    """Test recommendation generation logic."""
    print("\nTesting Recommendation Generation...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService'), \
         patch('app.services.ai_agent_service.AnalyticsService'):
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Test area recommendations
        print("  Testing area-specific recommendations...")
        quad_rec = ai_service._generate_area_recommendations("Quadratic Equations")
        assert "main" in quad_rec
        assert "resources" in quad_rec
        assert isinstance(quad_rec["resources"], list)
        print("  ✅ Area-specific recommendations work")
        
        # Test personalized recommendations
        print("  Testing personalized recommendations...")
        learning_patterns = {
            "consistency": 0.5,  # Low consistency
            "score_trend": "declining",
            "peak_performance_time": "morning"
        }
        weak_areas = [
            {"area": "Geometry Proofs", "severity": "high"}
        ]
        
        recommendations = await ai_service._generate_personalized_recommendations(
            uuid4(), learning_patterns, weak_areas, "Good analysis"
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        print("  ✅ Personalized recommendations generated")
        
        # Check that recommendations address the issues
        rec_text = " ".join(recommendations)
        assert "规律" in rec_text or "习惯" in rec_text  # Should mention habits due to low consistency
        print("  ✅ Recommendations address specific issues")


async def main():
    """Run all tests."""
    print("Running Enhanced Learning Analysis Tests...\n")
    
    await test_analytics_service()
    await test_enhanced_ai_analysis()
    await test_recommendation_generation()
    
    print("\n🎉 All enhanced learning analysis tests passed!")


if __name__ == "__main__":
    asyncio.run(main())