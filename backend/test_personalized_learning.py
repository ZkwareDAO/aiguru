"""Test personalized learning recommendation system."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.user import User, UserRole
from app.services.ai_agent_service import AIAgentService


async def test_personalized_study_plan():
    """Test personalized study plan generation."""
    print("Testing Personalized Study Plan Generation...")
    
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
            email="student@example.com",
            name="Alice Student",
            role=UserRole.STUDENT,
            password_hash="hashed"
        )
        
        mock_user_service = AsyncMock()
        mock_user_service.get_user_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service
        
        # Mock analytics service with realistic data
        mock_analytics_service = AsyncMock()
        mock_analytics_service.get_user_performance_data.return_value = {
            "total_submissions": 15,
            "average_score": 72.5,
            "submissions": [
                {"score": 85, "submitted_at": datetime.utcnow()},
                {"score": 60, "submitted_at": datetime.utcnow()},
                {"score": 78, "submitted_at": datetime.utcnow()}
            ]
        }
        mock_analytics_service.identify_weak_areas.return_value = [
            {
                "area": "Quadratic Equations",
                "subject": "mathematics",
                "severity": "high",
                "average_score": 0.55,
                "error_count": 8,
                "total_attempts": 12
            },
            {
                "area": "Geometry Proofs",
                "subject": "mathematics",
                "severity": "medium",
                "average_score": 0.68,
                "error_count": 5,
                "total_attempts": 10
            }
        ]
        mock_analytics_service.calculate_mastery_levels.return_value = {
            "Linear Equations": 0.85,
            "Quadratic Equations": 0.55,
            "Geometry Proofs": 0.68,
            "Trigonometry": 0.72
        }
        mock_analytics_service.analyze_learning_patterns.return_value = {
            "total_submissions": 15,
            "score_trend": "improving",
            "consistency": 0.65,
            "peak_performance_time": "morning",
            "study_frequency": 0.8,
            "strengths": ["Regular study habits", "Good at algebra"]
        }
        mock_analytics_service_class.return_value = mock_analytics_service
        
        # Create AI agent service
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Mock AI analysis
        ai_service._get_ai_analysis = AsyncMock(return_value="Focus on quadratic equations and maintain consistency")
        
        # Test personalized study plan generation
        print("  Testing enhanced study plan generation...")
        study_plan = await ai_service.generate_study_plan(
            user_id=mock_user.id,
            goals=["Improve math scores", "Master quadratic equations"],
            available_time_per_day=45,
            target_weeks=6,
            difficulty_level="intermediate"
        )
        
        # Verify study plan structure
        assert study_plan.user_id == mock_user.id
        assert "Alice Student" in study_plan.plan_name
        assert len(study_plan.goals) >= 2  # Should include user goals + weak area goals
        assert len(study_plan.weekly_tasks) == 6  # 6 weeks
        
        print("  ✅ Enhanced study plan generated successfully")
        
        # Test goal personalization
        print("  Testing goal personalization...")
        goals = study_plan.goals
        
        # Should have goals for weak areas
        weak_area_goals = [g for g in goals if "Quadratic Equations" in g.title or "Geometry Proofs" in g.title]
        assert len(weak_area_goals) > 0, "Should create goals for weak areas"
        
        # High severity weak areas should have high priority
        high_priority_goals = [g for g in goals if g.priority == "high"]
        assert len(high_priority_goals) > 0, "Should have high priority goals for severe weak areas"
        
        print("  ✅ Goals properly personalized based on weak areas")
        
        # Test task personalization
        print("  Testing task personalization...")
        week1_tasks = study_plan.weekly_tasks["week_1"]
        
        # Should have tasks focused on weak areas in early weeks
        quadratic_tasks = [t for t in week1_tasks if "Quadratic" in t.title or "Quadratic" in t.description]
        assert len(quadratic_tasks) > 0, "Should have tasks focused on weak areas"
        
        # Tasks should be appropriately timed
        for task in week1_tasks:
            assert 30 <= task.estimated_time_minutes <= 90, "Task time should be reasonable"
        
        print("  ✅ Tasks properly personalized and timed")


async def test_learning_resources_generation():
    """Test personalized learning resources generation."""
    print("\nTesting Learning Resources Generation...")
    
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
            "consistency": 0.4,  # Low consistency
            "peak_performance_time": "evening"
        }
        mock_analytics_service.calculate_mastery_levels.return_value = {
            "Quadratic Equations": 0.3  # Low mastery
        }
        mock_analytics_service_class.return_value = mock_analytics_service
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Test resource generation
        print("  Testing resource generation for Quadratic Equations...")
        resources = await ai_service.generate_learning_resources(
            user_id=uuid4(),
            topic="Quadratic Equations",
            difficulty_level="beginner"
        )
        
        # Verify resource structure
        assert isinstance(resources, dict)
        expected_categories = ["videos", "practice", "reading", "interactive"]
        for category in expected_categories:
            assert category in resources, f"Should have {category} resources"
            assert isinstance(resources[category], list), f"{category} should be a list"
            assert len(resources[category]) > 0, f"Should have {category} resources"
        
        print("  ✅ Basic resources generated correctly")
        
        # Test personalization features
        print("  Testing resource personalization...")
        
        # Should have study tips for low consistency
        if "study_tips" in resources:
            study_tips = resources["study_tips"]
            assert any("schedule" in tip.lower() or "routine" in tip.lower() for tip in study_tips), \
                "Should suggest schedule/routine for low consistency"
        
        # Should have foundation resources for low mastery
        if "foundation" in resources:
            foundation = resources["foundation"]
            assert any("basic" in item.lower() or "prerequisite" in item.lower() for item in foundation), \
                "Should suggest foundation work for low mastery"
        
        # Should have timing recommendations
        if "timing" in resources:
            timing = resources["timing"]
            assert any("evening" in item.lower() for item in timing), \
                "Should mention peak performance time"
        
        print("  ✅ Resources properly personalized")


async def test_adaptive_feedback():
    """Test adaptive feedback generation."""
    print("\nTesting Adaptive Feedback Generation...")
    
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
            "consistency": 0.8,
            "study_frequency": 0.9
        }
        mock_analytics_service.identify_weak_areas.return_value = [
            {"area": "Geometry Proofs", "severity": "medium"}
        ]
        mock_analytics_service_class.return_value = mock_analytics_service
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        
        # Test with improving performance
        print("  Testing feedback for improving performance...")
        recent_performance = [
            {"score": 70, "topic": "algebra"},
            {"score": 75, "topic": "algebra"},
            {"score": 80, "topic": "algebra"},
            {"score": 85, "topic": "algebra"}
        ]
        
        feedback = await ai_service.generate_adaptive_feedback(
            user_id=uuid4(),
            recent_performance=recent_performance
        )
        
        # Verify feedback structure
        assert "overall_message" in feedback
        assert "specific_feedback" in feedback
        assert "encouragement" in feedback
        assert "next_steps" in feedback
        assert "performance_summary" in feedback
        
        # Check performance summary
        summary = feedback["performance_summary"]
        assert summary["average_score"] == 77.5
        assert summary["trend"] == "improving"
        assert summary["total_attempts"] == 4
        
        print("  ✅ Feedback structure correct")
        
        # Test feedback content
        print("  Testing feedback content quality...")
        
        overall_msg = feedback["overall_message"]
        assert "improv" in overall_msg.lower() or "progress" in overall_msg.lower(), \
            "Should mention improvement for improving trend"
        
        encouragement = feedback["encouragement"]
        assert len(encouragement) > 0, "Should provide encouragement"
        
        next_steps = feedback["next_steps"]
        assert isinstance(next_steps, list) and len(next_steps) > 0, "Should provide next steps"
        
        print("  ✅ Feedback content appropriate")
        
        # Test with declining performance
        print("  Testing feedback for declining performance...")
        declining_performance = [
            {"score": 85, "topic": "algebra"},
            {"score": 80, "topic": "algebra"},
            {"score": 70, "topic": "algebra"},
            {"score": 65, "topic": "algebra"}
        ]
        
        declining_feedback = await ai_service.generate_adaptive_feedback(
            user_id=uuid4(),
            recent_performance=declining_performance
        )
        
        # Should recognize declining trend
        assert declining_feedback["performance_summary"]["trend"] == "declining"
        
        # Should provide appropriate guidance
        overall_msg = declining_feedback["overall_message"]
        print(f"    Declining feedback message: '{overall_msg}'")
        assert "improve" in overall_msg.lower() or "focus" in overall_msg.lower(), \
            f"Should suggest improvement for declining performance. Got: '{overall_msg}'"
        
        print("  ✅ Declining performance feedback appropriate")


async def test_recommendation_integration():
    """Test integration of all recommendation features."""
    print("\nTesting Recommendation System Integration...")
    
    with patch('app.services.ai_agent_service.get_settings') as mock_settings, \
         patch('app.services.ai_agent_service.ChatOpenAI'), \
         patch('app.services.ai_agent_service.UserService') as mock_user_service_class, \
         patch('app.services.ai_agent_service.AnalyticsService') as mock_analytics_service_class:
        
        settings = MagicMock()
        settings.OPENAI_API_KEY = "test-api-key"
        mock_settings.return_value = settings
        
        # Mock user
        mock_user = User(
            id=uuid4(),
            email="student@example.com",
            name="Test Student",
            role=UserRole.STUDENT,
            password_hash="hashed"
        )
        
        mock_user_service = AsyncMock()
        mock_user_service.get_user_by_id.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service
        
        # Mock comprehensive analytics
        mock_analytics_service = AsyncMock()
        mock_analytics_service.get_user_performance_data.return_value = {
            "total_submissions": 20,
            "average_score": 75.0
        }
        mock_analytics_service.identify_weak_areas.return_value = [
            {"area": "Quadratic Equations", "subject": "mathematics", "severity": "high"},
            {"area": "Geometry Proofs", "subject": "mathematics", "severity": "medium"}
        ]
        mock_analytics_service.calculate_mastery_levels.return_value = {
            "Linear Equations": 0.9,
            "Quadratic Equations": 0.4,
            "Geometry Proofs": 0.6
        }
        mock_analytics_service.analyze_learning_patterns.return_value = {
            "consistency": 0.7,
            "score_trend": "improving",
            "peak_performance_time": "morning",
            "strengths": ["Strong algebra foundation", "Regular study habits"]
        }
        mock_analytics_service.get_learning_trends.return_value = [
            {"date": datetime.utcnow(), "average_score": 75, "assignments_completed": 2}
        ]
        mock_analytics_service_class.return_value = mock_analytics_service
        
        mock_db = AsyncMock()
        ai_service = AIAgentService(mock_db)
        ai_service._get_ai_analysis = AsyncMock(return_value="Focus on quadratic equations")
        
        # Test comprehensive analysis
        print("  Testing comprehensive learning analysis...")
        analysis = await ai_service.analyze_learning_data(
            user_id=mock_user.id,
            analysis_type="comprehensive",
            include_recommendations=True
        )
        
        # Verify comprehensive analysis
        assert len(analysis.knowledge_points) > 0
        assert len(analysis.weak_areas) > 0
        assert len(analysis.recommendations) > 0
        assert len(analysis.strengths) > 0
        
        print("  ✅ Comprehensive analysis complete")
        
        # Test that recommendations are personalized
        print("  Testing recommendation personalization...")
        recommendations = analysis.recommendations
        
        # Should mention weak areas
        rec_text = " ".join(recommendations).lower()
        assert "quadratic" in rec_text or "geometry" in rec_text, \
            "Should mention weak areas in recommendations"
        
        # Should consider learning patterns
        if any("morning" in rec.lower() for rec in recommendations):
            print("    ✅ Peak time considered in recommendations")
        
        print("  ✅ Recommendations properly personalized")


async def main():
    """Run all personalized learning tests."""
    print("Running Personalized Learning System Tests...\n")
    
    await test_personalized_study_plan()
    await test_learning_resources_generation()
    await test_adaptive_feedback()
    await test_recommendation_integration()
    
    print("\n🎉 All personalized learning system tests passed!")


if __name__ == "__main__":
    asyncio.run(main())