"""Tests for grading result processor."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission, SubmissionStatus, AssignmentStatus
from app.models.class_model import Class
from app.models.user import User, UserRole
from app.schemas.grading import GradingResult
from app.services.grading_result_processor import GradingResultAnalyzer


@pytest.fixture
async def analyzer(db_session: AsyncSession):
    """Create grading result analyzer."""
    return GradingResultAnalyzer(db_session)


@pytest.fixture
async def test_teacher(db_session: AsyncSession):
    """Create test teacher."""
    teacher = User(
        email="teacher@test.com",
        password_hash="hashed_password",
        name="Test Teacher",
        role=UserRole.TEACHER
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


@pytest.fixture
async def test_students(db_session: AsyncSession):
    """Create test students."""
    students = []
    for i in range(5):
        student = User(
            email=f"student{i}@test.com",
            password_hash="hashed_password",
            name=f"Test Student {i}",
            role=UserRole.STUDENT
        )
        db_session.add(student)
        students.append(student)
    
    await db_session.commit()
    for student in students:
        await db_session.refresh(student)
    return students


@pytest.fixture
async def test_class(db_session: AsyncSession, test_teacher: User):
    """Create test class."""
    test_class = Class(
        name="Test Class",
        teacher_id=test_teacher.id,
        class_code="TEST123",
        subject="Math"
    )
    db_session.add(test_class)
    await db_session.commit()
    await db_session.refresh(test_class)
    return test_class


@pytest.fixture
async def test_assignment(db_session: AsyncSession, test_teacher: User, test_class: Class):
    """Create test assignment."""
    assignment = Assignment(
        title="Test Assignment",
        description="Test assignment description",
        instructions="Show your work clearly",
        teacher_id=test_teacher.id,
        class_id=test_class.id,
        status=AssignmentStatus.ACTIVE,
        total_points=100
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


@pytest.fixture
async def test_submissions_with_tasks(
    db_session: AsyncSession,
    test_assignment: Assignment,
    test_students: List[User]
):
    """Create test submissions with grading tasks."""
    submissions_and_tasks = []
    
    # Create submissions with varying scores
    scores = [95, 85, 75, 65, 45]  # Different performance levels
    
    for i, (student, score) in enumerate(zip(test_students, scores)):
        # Create submission
        submission = Submission(
            assignment_id=test_assignment.id,
            student_id=student.id,
            content=f"Student {i} answer with detailed explanation",
            status=SubmissionStatus.GRADED,
            score=score,
            max_score=100
        )
        db_session.add(submission)
        await db_session.flush()
        
        # Create grading task
        grading_result = {
            "score": score,
            "max_score": 100,
            "percentage": score,
            "feedback": f"Good work on assignment. Score: {score}%",
            "suggestions": "Keep up the good work" if score > 80 else "Need more practice",
            "strengths": ["Clear writing"] if score > 70 else None,
            "weaknesses": ["Needs more detail"] if score < 80 else None,
            "confidence": 0.9 if score > 80 else 0.7,
            "processing_time_ms": 2000
        }
        
        task = GradingTask(
            submission_id=submission.id,
            task_type="auto_grade",
            status=GradingTaskStatus.COMPLETED,
            result=grading_result,
            score=score,
            feedback=grading_result["feedback"],
            completed_at=datetime.utcnow()
        )
        db_session.add(task)
        
        submissions_and_tasks.append((submission, task))
    
    await db_session.commit()
    
    for submission, task in submissions_and_tasks:
        await db_session.refresh(submission)
        await db_session.refresh(task)
    
    return submissions_and_tasks


@pytest.fixture
def sample_grading_result():
    """Create sample grading result."""
    return GradingResult(
        score=85,
        max_score=100,
        percentage=85.0,
        feedback="Good work! Your answer demonstrates understanding of the concepts.",
        suggestions="Consider providing more specific examples in future work.",
        strengths=["Clear reasoning", "Correct methodology"],
        weaknesses=["Could use more detail", "Minor calculation errors"],
        confidence=0.85,
        processing_time_ms=2500
    )


class TestGradingResultAnalyzer:
    """Test grading result analyzer functionality."""
    
    async def test_analyze_grading_result(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks,
        sample_grading_result: GradingResult
    ):
        """Test analyzing a grading result."""
        submission, task = test_submissions_with_tasks[0]  # Get first submission/task
        
        analysis = await analyzer.analyze_grading_result(task.id, sample_grading_result)
        
        assert "task_id" in analysis
        assert "submission_id" in analysis
        assert "assignment_id" in analysis
        assert "student_id" in analysis
        assert "score_analysis" in analysis
        assert "feedback_analysis" in analysis
        assert "comparative_analysis" in analysis
        assert "quality_metrics" in analysis
        assert "improvement_suggestions" in analysis
        assert "confidence_assessment" in analysis
        
        # Check score analysis
        score_analysis = analysis["score_analysis"]
        assert score_analysis["raw_score"] == 85
        assert score_analysis["percentage"] == 85.0
        assert score_analysis["grade_level"] == "good"
        
        # Check feedback analysis
        feedback_analysis = analysis["feedback_analysis"]
        assert feedback_analysis["has_suggestions"] is True
        assert feedback_analysis["has_strengths"] is True
        assert feedback_analysis["has_weaknesses"] is True
    
    async def test_generate_enhanced_feedback(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks,
        sample_grading_result: GradingResult
    ):
        """Test generating enhanced feedback."""
        submission, task = test_submissions_with_tasks[0]
        assignment = submission.assignment
        
        enhanced_feedback = await analyzer.generate_enhanced_feedback(
            sample_grading_result, submission, assignment
        )
        
        assert isinstance(enhanced_feedback, str)
        assert len(enhanced_feedback) > len(sample_grading_result.feedback)
        assert "AI Analysis:" in enhanced_feedback
        assert "Score Analysis:" in enhanced_feedback
        assert "Strengths:" in enhanced_feedback
        assert "Areas for Improvement:" in enhanced_feedback
        assert "Suggestions:" in enhanced_feedback
    
    async def test_assess_grading_quality(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks,
        sample_grading_result: GradingResult
    ):
        """Test assessing grading quality."""
        submission, task = test_submissions_with_tasks[0]
        
        quality_assessment = await analyzer.assess_grading_quality(
            task.id, sample_grading_result
        )
        
        assert "overall_quality" in quality_assessment
        assert "confidence_level" in quality_assessment
        assert "reliability_score" in quality_assessment
        assert "consistency_score" in quality_assessment
        assert "feedback_quality" in quality_assessment
        assert "recommendations" in quality_assessment
        assert "flags" in quality_assessment
        
        # Check confidence assessment
        assert quality_assessment["confidence_level"] in ["low", "medium", "high", "very_high"]
        
        # Check that recommendations is a list
        assert isinstance(quality_assessment["recommendations"], list)
        assert isinstance(quality_assessment["flags"], list)
    
    async def test_detect_grading_anomalies(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks,
        test_assignment: Assignment
    ):
        """Test detecting grading anomalies."""
        anomalies = await analyzer.detect_grading_anomalies(test_assignment.id)
        
        # Should detect anomalies since we have scores ranging from 45 to 95
        assert isinstance(anomalies, list)
        
        # Check anomaly structure if any found
        if anomalies:
            anomaly = anomalies[0]
            assert "submission_id" in anomaly
            assert "student_id" in anomaly
            assert "student_name" in anomaly
            assert "score" in anomaly
            assert "mean_score" in anomaly
            assert "z_score" in anomaly
            assert "anomaly_type" in anomaly
            assert "severity" in anomaly
            assert "detected_at" in anomaly
    
    async def test_detect_grading_anomalies_insufficient_data(
        self,
        analyzer: GradingResultAnalyzer,
        db_session: AsyncSession,
        test_teacher: User,
        test_class: Class
    ):
        """Test anomaly detection with insufficient data."""
        # Create assignment with no submissions
        assignment = Assignment(
            title="Empty Assignment",
            teacher_id=test_teacher.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE,
            total_points=100
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        anomalies = await analyzer.detect_grading_anomalies(assignment.id)
        
        # Should return empty list for insufficient data
        assert anomalies == []
    
    async def test_generate_grading_insights(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks,
        test_assignment: Assignment
    ):
        """Test generating grading insights."""
        insights = await analyzer.generate_grading_insights(test_assignment.id)
        
        assert "assignment_id" in insights
        assert "analysis_period_days" in insights
        assert "total_graded_submissions" in insights
        assert "grading_statistics" in insights
        assert "performance_trends" in insights
        assert "feedback_patterns" in insights
        assert "quality_metrics" in insights
        assert "recommendations" in insights
        assert "generated_at" in insights
        
        # Check statistics
        stats = insights["grading_statistics"]
        if "score_statistics" in stats:
            score_stats = stats["score_statistics"]
            assert "mean" in score_stats
            assert "median" in score_stats
            assert "std_dev" in score_stats
            assert "min" in score_stats
            assert "max" in score_stats
        
        # Check quality metrics
        quality_metrics = insights["quality_metrics"]
        assert "total_tasks" in quality_metrics
        assert quality_metrics["total_tasks"] > 0
    
    async def test_generate_grading_insights_no_data(
        self,
        analyzer: GradingResultAnalyzer,
        db_session: AsyncSession,
        test_teacher: User,
        test_class: Class
    ):
        """Test generating insights with no grading data."""
        # Create assignment with no grading tasks
        assignment = Assignment(
            title="No Grading Assignment",
            teacher_id=test_teacher.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE,
            total_points=100
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        insights = await analyzer.generate_grading_insights(assignment.id)
        
        assert "message" in insights
        assert "No grading data available" in insights["message"]
    
    async def test_score_analysis_grade_levels(
        self,
        analyzer: GradingResultAnalyzer
    ):
        """Test score analysis grade level determination."""
        # Test different score levels
        test_cases = [
            (95, "excellent"),
            (85, "good"),
            (75, "satisfactory"),
            (65, "needs_improvement"),
            (45, "unsatisfactory")
        ]
        
        for score, expected_level in test_cases:
            grading_result = GradingResult(
                score=score,
                max_score=100,
                percentage=score,
                feedback="Test feedback"
            )
            
            # Create a mock assignment for the analysis
            from app.models.assignment import Assignment
            assignment = Assignment(total_points=100)
            
            score_analysis = await analyzer._analyze_score(grading_result, assignment)
            assert score_analysis["grade_level"] == expected_level
    
    async def test_feedback_analysis_completeness(
        self,
        analyzer: GradingResultAnalyzer
    ):
        """Test feedback analysis completeness assessment."""
        # Comprehensive feedback
        comprehensive_result = GradingResult(
            score=85,
            max_score=100,
            percentage=85.0,
            feedback="This is a detailed feedback with more than fifty characters to test completeness",
            suggestions="Specific suggestions for improvement",
            strengths=["Good analysis", "Clear writing"],
            weaknesses=["Minor errors", "Could be more detailed"]
        )
        
        feedback_analysis = await analyzer._analyze_feedback(comprehensive_result)
        assert feedback_analysis["feedback_completeness"] == "comprehensive"
        
        # Minimal feedback
        minimal_result = GradingResult(
            score=85,
            max_score=100,
            percentage=85.0,
            feedback="Short feedback"
        )
        
        feedback_analysis = await analyzer._analyze_feedback(minimal_result)
        assert feedback_analysis["feedback_completeness"] == "minimal"
    
    async def test_quality_metrics_calculation(
        self,
        analyzer: GradingResultAnalyzer
    ):
        """Test quality metrics calculation."""
        grading_result = GradingResult(
            score=85,
            max_score=100,
            percentage=85.0,
            feedback="This is a detailed feedback with sufficient length for quality assessment",
            suggestions="Improvement suggestions",
            strengths=["Good work"],
            weaknesses=["Minor issues"],
            confidence=0.9
        )
        
        metrics = await analyzer._calculate_quality_metrics(grading_result)
        
        assert "confidence_score" in metrics
        assert "feedback_richness" in metrics
        assert "consistency_indicator" in metrics
        assert "completeness_score" in metrics
        
        assert metrics["confidence_score"] == 0.9
        assert metrics["completeness_score"] > 0.8  # Should be high due to complete data
        assert metrics["feedback_richness"] > 0  # Should be positive due to feedback length
    
    async def test_improvement_suggestions_generation(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks
    ):
        """Test improvement suggestions generation."""
        submission, task = test_submissions_with_tasks[-1]  # Get lowest scoring submission
        assignment = submission.assignment
        
        # Low score result
        low_score_result = GradingResult(
            score=45,
            max_score=100,
            percentage=45.0,
            feedback="Needs significant improvement",
            weaknesses=["Incomplete analysis", "Calculation errors"],
            confidence=0.6
        )
        
        suggestions = await analyzer._generate_improvement_suggestions(
            low_score_result, submission, assignment
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Should include suggestions for low score
        suggestion_text = " ".join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in [
            "review", "help", "requirements", "weaknesses", "confidence"
        ])
    
    async def test_confidence_assessment(
        self,
        analyzer: GradingResultAnalyzer
    ):
        """Test confidence assessment."""
        # High confidence
        high_confidence_result = GradingResult(
            score=85,
            max_score=100,
            percentage=85.0,
            feedback="Good work",
            confidence=0.95
        )
        
        assessment = await analyzer._assess_confidence(high_confidence_result)
        assert assessment["confidence_level"] == "very_high"
        assert assessment["reliability"] == "excellent"
        
        # Low confidence
        low_confidence_result = GradingResult(
            score=85,
            max_score=100,
            percentage=85.0,
            feedback="Good work",
            confidence=0.5
        )
        
        assessment = await analyzer._assess_confidence(low_confidence_result)
        assert assessment["confidence_level"] == "low"
        assert assessment["reliability"] == "poor"
        assert len(assessment["recommendations"]) > 0
    
    async def test_comparative_analysis_with_class_data(
        self,
        analyzer: GradingResultAnalyzer,
        test_submissions_with_tasks
    ):
        """Test comparative analysis with class data."""
        submission, task = test_submissions_with_tasks[0]  # Get first submission (score 95)
        
        grading_result = GradingResult(
            score=95,
            max_score=100,
            percentage=95.0,
            feedback="Excellent work"
        )
        
        comparative_analysis = await analyzer._analyze_comparative_performance(
            submission, grading_result
        )
        
        # Should have class data since we created multiple submissions
        if comparative_analysis.get("status") != "insufficient_data":
            assert "class_average" in comparative_analysis
            assert "student_score" in comparative_analysis
            assert "performance_difference" in comparative_analysis
            assert "relative_performance" in comparative_analysis
            
            # High scoring student should be above average
            assert comparative_analysis["relative_performance"] in ["above_average", "average"]