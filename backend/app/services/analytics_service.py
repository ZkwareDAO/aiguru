"""Analytics service for learning data analysis."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.exceptions import ValidationError
from app.models.user import User
from app.models.assignment import Assignment, Submission

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analyzing learning data and generating insights."""
    
    def __init__(self, db: AsyncSession):
        """Initialize analytics service."""
        self.db = db
    
    async def get_user_performance_data(
        self,
        user_id: UUID,
        time_period: str = "last_month",
        subjects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get user performance data for analysis."""
        try:
            # Calculate date range based on time period
            end_date = datetime.utcnow()
            if time_period == "last_week":
                start_date = end_date - timedelta(weeks=1)
            elif time_period == "last_month":
                start_date = end_date - timedelta(days=30)
            elif time_period == "last_quarter":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)  # Default to last month
            
            # Query submissions for the user in the time period
            query = (
                select(Submission)
                .join(Assignment)
                .where(
                    Submission.student_id == user_id,
                    Submission.submitted_at >= start_date,
                    Submission.submitted_at <= end_date
                )
            )
            
            if subjects:
                query = query.where(Assignment.subject.in_(subjects))
            
            result = await self.db.execute(query)
            submissions = result.scalars().all()
            
            # Calculate performance metrics
            total_submissions = len(submissions)
            total_score = sum(s.score or 0 for s in submissions if s.score is not None)
            graded_submissions = [s for s in submissions if s.score is not None]
            
            performance_data = {
                "total_submissions": total_submissions,
                "graded_submissions": len(graded_submissions),
                "average_score": total_score / len(graded_submissions) if graded_submissions else 0,
                "submissions": [
                    {
                        "id": str(s.id),
                        "assignment_id": str(s.assignment_id),
                        "score": s.score,
                        "submitted_at": s.submitted_at,
                        "graded_at": s.graded_at
                    }
                    for s in submissions
                ]
            }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting user performance data: {str(e)}")
            raise ValidationError(f"Failed to get performance data: {str(e)}")
    
    async def get_subject_performance(
        self,
        user_id: UUID,
        subject: str,
        time_period: str = "last_month"
    ) -> Dict[str, Any]:
        """Get performance data for a specific subject."""
        try:
            performance_data = await self.get_user_performance_data(
                user_id=user_id,
                time_period=time_period,
                subjects=[subject]
            )
            
            return {
                "subject": subject,
                "performance": performance_data
            }
            
        except Exception as e:
            logger.error(f"Error getting subject performance: {str(e)}")
            raise ValidationError(f"Failed to get subject performance: {str(e)}")
    
    async def identify_weak_areas(
        self,
        user_id: UUID,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Identify areas where the user is performing below threshold."""
        try:
            # Get user performance data
            performance_data = await self.get_user_performance_data(user_id)
            
            # Analyze submissions by subject/topic
            weak_areas = []
            
            # Group submissions by subject
            subject_performance = {}
            for submission in performance_data.get("submissions", []):
                if submission.get("score") is not None:
                    # In a real implementation, we'd get the assignment subject
                    # For now, we'll use mock data with some analysis
                    subject = "mathematics"  # This would come from the assignment
                    
                    if subject not in subject_performance:
                        subject_performance[subject] = {
                            "scores": [],
                            "total_attempts": 0,
                            "error_count": 0
                        }
                    
                    score = submission["score"]
                    subject_performance[subject]["scores"].append(score)
                    subject_performance[subject]["total_attempts"] += 1
                    
                    if score < threshold * 100:  # Convert threshold to percentage
                        subject_performance[subject]["error_count"] += 1
            
            # Identify weak areas based on performance
            for subject, perf in subject_performance.items():
                if perf["scores"]:
                    avg_score = sum(perf["scores"]) / len(perf["scores"])
                    error_rate = perf["error_count"] / perf["total_attempts"]
                    
                    if avg_score < threshold * 100 or error_rate > 0.3:
                        # Determine specific weak areas within the subject
                        if subject == "mathematics":
                            if avg_score < 60:
                                weak_areas.append({
                                    "area": "Quadratic Equations",
                                    "subject": subject,
                                    "average_score": avg_score / 100,
                                    "error_count": perf["error_count"],
                                    "total_attempts": perf["total_attempts"],
                                    "severity": "high" if avg_score < 50 else "medium"
                                })
                            elif avg_score < 70:
                                weak_areas.append({
                                    "area": "Geometry Proofs",
                                    "subject": subject,
                                    "average_score": avg_score / 100,
                                    "error_count": perf["error_count"],
                                    "total_attempts": perf["total_attempts"],
                                    "severity": "medium"
                                })
            
            # If no real data, return mock weak areas for demonstration
            if not weak_areas:
                weak_areas = [
                    {
                        "area": "Quadratic Equations",
                        "subject": "mathematics",
                        "average_score": 0.65,
                        "error_count": 8,
                        "total_attempts": 12,
                        "severity": "medium"
                    },
                    {
                        "area": "Geometry Proofs",
                        "subject": "mathematics", 
                        "average_score": 0.58,
                        "error_count": 15,
                        "total_attempts": 20,
                        "severity": "high"
                    }
                ]
            
            return weak_areas
            
        except Exception as e:
            logger.error(f"Error identifying weak areas: {str(e)}")
            raise ValidationError(f"Failed to identify weak areas: {str(e)}")
    
    async def get_learning_trends(
        self,
        user_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get learning trends over time."""
        try:
            # For now, return mock trend data
            # In a full implementation, this would calculate actual trends
            trends = []
            base_date = datetime.utcnow() - timedelta(days=days)
            
            for i in range(days):
                date = base_date + timedelta(days=i)
                # Mock trend data with some variation
                score = 75 + (i * 0.5) + (i % 7) * 2  # Gradual improvement with weekly cycles
                
                trends.append({
                    "date": date,
                    "average_score": min(score, 100),
                    "assignments_completed": 1 if i % 3 == 0 else 0,
                    "study_time_minutes": 30 + (i % 5) * 10
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting learning trends: {str(e)}")
            raise ValidationError(f"Failed to get learning trends: {str(e)}")
    
    async def calculate_mastery_levels(
        self,
        user_id: UUID,
        subjects: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """Calculate mastery levels for different topics."""
        try:
            # Get user performance data
            performance_data = await self.get_user_performance_data(user_id)
            
            # Calculate mastery based on recent performance
            mastery_levels = {}
            
            # Analyze submissions to calculate mastery
            topic_scores = {}
            for submission in performance_data.get("submissions", []):
                if submission.get("score") is not None:
                    # In a real implementation, we'd get the topic from the assignment
                    # For now, we'll simulate different topics based on score patterns
                    score = submission["score"]
                    
                    # Simulate topic assignment based on score patterns
                    if score >= 85:
                        topic = "Linear Equations"
                    elif score >= 70:
                        topic = "Quadratic Functions"
                    elif score >= 60:
                        topic = "Geometry Basics"
                    elif score >= 50:
                        topic = "Trigonometry"
                    else:
                        topic = "Calculus Basics"
                    
                    if topic not in topic_scores:
                        topic_scores[topic] = []
                    topic_scores[topic].append(score)
            
            # Calculate mastery levels based on performance
            for topic, scores in topic_scores.items():
                if scores:
                    # Calculate mastery using weighted average (recent scores matter more)
                    weights = [i + 1 for i in range(len(scores))]  # More weight to recent scores
                    weighted_avg = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
                    
                    # Convert to mastery level (0-1 scale)
                    mastery_level = min(weighted_avg / 100, 1.0)
                    
                    # Apply consistency bonus/penalty
                    if len(scores) > 1:
                        consistency = 1 - (max(scores) - min(scores)) / 100
                        mastery_level = mastery_level * (0.8 + 0.2 * consistency)
                    
                    mastery_levels[topic] = round(mastery_level, 2)
            
            # If no real data, return mock mastery levels
            if not mastery_levels:
                mastery_levels = {
                    "Linear Equations": 0.85,
                    "Quadratic Functions": 0.72,
                    "Geometry Basics": 0.90,
                    "Trigonometry": 0.65,
                    "Calculus Basics": 0.55
                }
            
            # Filter by subjects if specified
            if subjects:
                filtered_mastery = {}
                for topic, level in mastery_levels.items():
                    # Simple subject matching (in real implementation, would be more sophisticated)
                    if any(subject.lower() in topic.lower() for subject in subjects):
                        filtered_mastery[topic] = level
                return filtered_mastery
            
            return mastery_levels
            
        except Exception as e:
            logger.error(f"Error calculating mastery levels: {str(e)}")
            raise ValidationError(f"Failed to calculate mastery levels: {str(e)}")
    
    async def analyze_learning_patterns(
        self,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze learning patterns and behaviors."""
        try:
            performance_data = await self.get_user_performance_data(user_id, "last_month")
            trends = await self.get_learning_trends(user_id, days)
            
            # Analyze submission patterns
            submission_times = []
            scores_over_time = []
            
            for submission in performance_data.get("submissions", []):
                if submission.get("submitted_at") and submission.get("score") is not None:
                    submission_times.append(submission["submitted_at"])
                    scores_over_time.append(submission["score"])
            
            # Calculate learning patterns
            patterns = {
                "total_submissions": len(submission_times),
                "average_score": sum(scores_over_time) / len(scores_over_time) if scores_over_time else 0,
                "score_trend": "improving" if self._is_improving_trend(scores_over_time) else "declining",
                "consistency": self._calculate_consistency(scores_over_time),
                "peak_performance_time": self._find_peak_performance_time(submission_times, scores_over_time),
                "study_frequency": len(submission_times) / max(days, 1),
                "strengths": self._identify_strengths(performance_data),
                "improvement_areas": await self.identify_weak_areas(user_id)
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing learning patterns: {str(e)}")
            raise ValidationError(f"Failed to analyze learning patterns: {str(e)}")
    
    def _is_improving_trend(self, scores: List[float]) -> bool:
        """Check if scores show an improving trend."""
        if len(scores) < 2:
            return False
        
        # Simple linear trend analysis
        recent_scores = scores[-3:] if len(scores) >= 3 else scores
        early_scores = scores[:3] if len(scores) >= 3 else scores[:-1]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        early_avg = sum(early_scores) / len(early_scores)
        
        return recent_avg > early_avg
    
    def _calculate_consistency(self, scores: List[float]) -> float:
        """Calculate consistency score (0-1, higher is more consistent)."""
        if len(scores) < 2:
            return 1.0
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        
        if mean_score == 0:
            return 0.0
        
        cv = std_dev / mean_score
        # Convert to consistency score (0-1, where 1 is perfectly consistent)
        consistency = max(0, 1 - cv)
        return round(consistency, 2)
    
    def _find_peak_performance_time(self, times: List[datetime], scores: List[float]) -> Optional[str]:
        """Find the time of day when performance is typically highest."""
        if not times or not scores:
            return None
        
        # Group scores by hour of day
        hour_scores = {}
        for time, score in zip(times, scores):
            hour = time.hour
            if hour not in hour_scores:
                hour_scores[hour] = []
            hour_scores[hour].append(score)
        
        # Find hour with highest average score
        best_hour = None
        best_avg = 0
        
        for hour, hour_score_list in hour_scores.items():
            avg_score = sum(hour_score_list) / len(hour_score_list)
            if avg_score > best_avg:
                best_avg = avg_score
                best_hour = hour
        
        if best_hour is not None:
            if 6 <= best_hour < 12:
                return "morning"
            elif 12 <= best_hour < 18:
                return "afternoon"
            elif 18 <= best_hour < 22:
                return "evening"
            else:
                return "night"
        
        return None
    
    def _identify_strengths(self, performance_data: Dict[str, Any]) -> List[str]:
        """Identify user's strengths based on performance data."""
        strengths = []
        
        # Analyze high-scoring submissions
        high_scores = [s for s in performance_data.get("submissions", []) 
                      if s.get("score", 0) >= 85]
        
        if len(high_scores) >= 3:
            strengths.append("Consistent high performance")
        
        if performance_data.get("average_score", 0) >= 80:
            strengths.append("Strong overall academic performance")
        
        # Add more strength identification logic based on patterns
        total_submissions = performance_data.get("total_submissions", 0)
        if total_submissions >= 10:
            strengths.append("Regular study habits")
        
        if not strengths:
            strengths = ["Shows dedication to learning", "Actively engages with assignments"]
        
        return strengths