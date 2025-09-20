"""Grading result processing service for analysis and feedback generation."""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import GradingError, NotFoundError
from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission
from app.models.user import User
from app.schemas.grading import GradingResult

logger = logging.getLogger(__name__)


class GradingResultAnalyzer:
    """Analyzer for grading results and feedback generation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_grading_result(
        self,
        task_id: UUID,
        grading_result: GradingResult
    ) -> Dict:
        """Analyze a grading result and generate insights."""
        try:
            # Get task and submission details
            task = await self._get_grading_task_with_details(task_id)
            submission = task.submission
            assignment = submission.assignment
            
            # Perform various analyses
            analysis = {
                "task_id": str(task_id),
                "submission_id": str(submission.id),
                "assignment_id": str(assignment.id),
                "student_id": str(submission.student_id),
                "analyzed_at": datetime.utcnow().isoformat(),
                "score_analysis": await self._analyze_score(grading_result, assignment),
                "feedback_analysis": await self._analyze_feedback(grading_result),
                "comparative_analysis": await self._analyze_comparative_performance(
                    submission, grading_result
                ),
                "quality_metrics": await self._calculate_quality_metrics(grading_result),
                "improvement_suggestions": await self._generate_improvement_suggestions(
                    grading_result, submission, assignment
                ),
                "confidence_assessment": await self._assess_confidence(grading_result)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze grading result for task {task_id}: {str(e)}")
            raise GradingError(f"Result analysis failed: {str(e)}")
    
    async def generate_enhanced_feedback(
        self,
        grading_result: GradingResult,
        submission: Submission,
        assignment: Assignment
    ) -> str:
        """Generate enhanced feedback based on grading result and context."""
        try:
            feedback_parts = []
            
            # Start with AI feedback
            if grading_result.feedback:
                feedback_parts.append("AI Analysis:")
                feedback_parts.append(grading_result.feedback)
            
            # Add score context
            score_context = await self._generate_score_context(
                grading_result, assignment
            )
            if score_context:
                feedback_parts.append("\nScore Analysis:")
                feedback_parts.append(score_context)
            
            # Add strengths and weaknesses
            if grading_result.strengths:
                feedback_parts.append("\nStrengths:")
                for strength in grading_result.strengths:
                    feedback_parts.append(f"• {strength}")
            
            if grading_result.weaknesses:
                feedback_parts.append("\nAreas for Improvement:")
                for weakness in grading_result.weaknesses:
                    feedback_parts.append(f"• {weakness}")
            
            # Add suggestions
            if grading_result.suggestions:
                feedback_parts.append("\nSuggestions:")
                feedback_parts.append(grading_result.suggestions)
            
            # Add comparative context
            comparative_context = await self._generate_comparative_context(
                submission, grading_result
            )
            if comparative_context:
                feedback_parts.append("\nClass Performance Context:")
                feedback_parts.append(comparative_context)
            
            return "\n".join(feedback_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate enhanced feedback: {str(e)}")
            return grading_result.feedback or "Feedback generation failed."
    
    async def assess_grading_quality(
        self,
        task_id: UUID,
        grading_result: GradingResult
    ) -> Dict:
        """Assess the quality of AI grading result."""
        try:
            task = await self._get_grading_task_with_details(task_id)
            
            quality_assessment = {
                "overall_quality": "unknown",
                "confidence_level": "low",
                "reliability_score": 0.0,
                "consistency_score": 0.0,
                "feedback_quality": "poor",
                "recommendations": [],
                "flags": []
            }
            
            # Assess confidence
            if grading_result.confidence:
                if grading_result.confidence >= 0.9:
                    quality_assessment["confidence_level"] = "high"
                elif grading_result.confidence >= 0.7:
                    quality_assessment["confidence_level"] = "medium"
                else:
                    quality_assessment["confidence_level"] = "low"
                    quality_assessment["flags"].append("Low AI confidence")
            
            # Assess score reasonableness
            score_assessment = await self._assess_score_reasonableness(
                grading_result, task.submission
            )
            quality_assessment.update(score_assessment)
            
            # Assess feedback quality
            feedback_quality = await self._assess_feedback_quality(grading_result)
            quality_assessment["feedback_quality"] = feedback_quality
            
            # Calculate overall quality
            quality_assessment["overall_quality"] = await self._calculate_overall_quality(
                quality_assessment
            )
            
            # Generate recommendations
            quality_assessment["recommendations"] = await self._generate_quality_recommendations(
                quality_assessment, grading_result
            )
            
            return quality_assessment
            
        except Exception as e:
            logger.error(f"Failed to assess grading quality for task {task_id}: {str(e)}")
            raise GradingError(f"Quality assessment failed: {str(e)}")
    
    async def detect_grading_anomalies(
        self,
        assignment_id: UUID,
        threshold_std_dev: float = 2.0
    ) -> List[Dict]:
        """Detect anomalies in grading results for an assignment."""
        try:
            # Get all graded submissions for the assignment
            query = select(Submission).options(
                selectinload(Submission.grading_tasks),
                selectinload(Submission.student)
            ).where(
                and_(
                    Submission.assignment_id == assignment_id,
                    Submission.score.isnot(None)
                )
            )
            
            result = await self.db.execute(query)
            submissions = result.scalars().all()
            
            if len(submissions) < 3:  # Need at least 3 submissions for anomaly detection
                return []
            
            # Calculate statistics
            scores = [s.score for s in submissions if s.score is not None]
            mean_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
            
            anomalies = []
            
            for submission in submissions:
                if submission.score is None:
                    continue
                
                # Check for score anomalies
                z_score = abs(submission.score - mean_score) / std_dev if std_dev > 0 else 0
                
                if z_score > threshold_std_dev:
                    anomaly = {
                        "submission_id": str(submission.id),
                        "student_id": str(submission.student_id),
                        "student_name": submission.student.name,
                        "score": submission.score,
                        "mean_score": mean_score,
                        "z_score": z_score,
                        "anomaly_type": "outlier_score",
                        "severity": "high" if z_score > 3.0 else "medium",
                        "detected_at": datetime.utcnow().isoformat()
                    }
                    
                    # Add grading task info if available
                    if submission.grading_tasks:
                        latest_task = max(
                            submission.grading_tasks,
                            key=lambda t: t.created_at
                        )
                        anomaly["grading_task_id"] = str(latest_task.id)
                        anomaly["ai_confidence"] = latest_task.result.get("confidence") if latest_task.result else None
                    
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect grading anomalies: {str(e)}")
            raise GradingError(f"Anomaly detection failed: {str(e)}")
    
    async def generate_grading_insights(
        self,
        assignment_id: UUID,
        time_period_days: int = 30
    ) -> Dict:
        """Generate insights about grading patterns and trends."""
        try:
            # Get grading tasks for the assignment within time period
            cutoff_date = datetime.utcnow() - timedelta(days=time_period_days)
            
            query = select(GradingTask).options(
                selectinload(GradingTask.submission).selectinload(Submission.assignment),
                selectinload(GradingTask.submission).selectinload(Submission.student)
            ).join(Submission).where(
                and_(
                    Submission.assignment_id == assignment_id,
                    GradingTask.created_at >= cutoff_date,
                    GradingTask.status == GradingTaskStatus.COMPLETED
                )
            )
            
            result = await self.db.execute(query)
            tasks = result.scalars().all()
            
            if not tasks:
                return {"message": "No grading data available for analysis"}
            
            insights = {
                "assignment_id": str(assignment_id),
                "analysis_period_days": time_period_days,
                "total_graded_submissions": len(tasks),
                "grading_statistics": await self._calculate_grading_statistics(tasks),
                "performance_trends": await self._analyze_performance_trends(tasks),
                "feedback_patterns": await self._analyze_feedback_patterns(tasks),
                "quality_metrics": await self._analyze_quality_metrics(tasks),
                "recommendations": await self._generate_assignment_recommendations(tasks),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate grading insights: {str(e)}")
            raise GradingError(f"Insights generation failed: {str(e)}")
    
    # Private helper methods
    
    async def _get_grading_task_with_details(self, task_id: UUID) -> GradingTask:
        """Get grading task with all related details."""
        query = select(GradingTask).options(
            selectinload(GradingTask.submission).selectinload(Submission.assignment),
            selectinload(GradingTask.submission).selectinload(Submission.student)
        ).where(GradingTask.id == task_id)
        
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundError(f"Grading task {task_id} not found")
        
        return task
    
    async def _analyze_score(
        self,
        grading_result: GradingResult,
        assignment: Assignment
    ) -> Dict:
        """Analyze the score component of grading result."""
        score_analysis = {
            "raw_score": grading_result.score,
            "max_score": grading_result.max_score,
            "percentage": grading_result.percentage,
            "grade_level": "unknown",
            "score_distribution": "unknown"
        }
        
        # Determine grade level
        if grading_result.percentage >= 90:
            score_analysis["grade_level"] = "excellent"
        elif grading_result.percentage >= 80:
            score_analysis["grade_level"] = "good"
        elif grading_result.percentage >= 70:
            score_analysis["grade_level"] = "satisfactory"
        elif grading_result.percentage >= 60:
            score_analysis["grade_level"] = "needs_improvement"
        else:
            score_analysis["grade_level"] = "unsatisfactory"
        
        return score_analysis
    
    async def _analyze_feedback(self, grading_result: GradingResult) -> Dict:
        """Analyze the feedback quality and content."""
        feedback_analysis = {
            "feedback_length": len(grading_result.feedback) if grading_result.feedback else 0,
            "has_suggestions": bool(grading_result.suggestions),
            "has_strengths": bool(grading_result.strengths),
            "has_weaknesses": bool(grading_result.weaknesses),
            "feedback_completeness": "unknown"
        }
        
        # Assess completeness
        completeness_score = 0
        if grading_result.feedback and len(grading_result.feedback) > 50:
            completeness_score += 1
        if grading_result.suggestions:
            completeness_score += 1
        if grading_result.strengths:
            completeness_score += 1
        if grading_result.weaknesses:
            completeness_score += 1
        
        if completeness_score >= 3:
            feedback_analysis["feedback_completeness"] = "comprehensive"
        elif completeness_score >= 2:
            feedback_analysis["feedback_completeness"] = "adequate"
        else:
            feedback_analysis["feedback_completeness"] = "minimal"
        
        return feedback_analysis
    
    async def _analyze_comparative_performance(
        self,
        submission: Submission,
        grading_result: GradingResult
    ) -> Dict:
        """Analyze performance compared to class average."""
        try:
            # Get class average for the assignment
            query = select(func.avg(Submission.score)).where(
                and_(
                    Submission.assignment_id == submission.assignment_id,
                    Submission.score.isnot(None)
                )
            )
            
            result = await self.db.execute(query)
            class_average = result.scalar()
            
            if class_average is None:
                return {"status": "insufficient_data"}
            
            performance_diff = grading_result.score - class_average
            performance_percentile = await self._calculate_percentile(
                submission.assignment_id, grading_result.score
            )
            
            return {
                "class_average": round(class_average, 2),
                "student_score": grading_result.score,
                "performance_difference": round(performance_diff, 2),
                "performance_percentile": performance_percentile,
                "relative_performance": (
                    "above_average" if performance_diff > 5 else
                    "below_average" if performance_diff < -5 else
                    "average"
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze comparative performance: {str(e)}")
            return {"status": "analysis_failed", "error": str(e)}
    
    async def _calculate_quality_metrics(self, grading_result: GradingResult) -> Dict:
        """Calculate quality metrics for the grading result."""
        metrics = {
            "confidence_score": grading_result.confidence or 0.0,
            "feedback_richness": 0.0,
            "consistency_indicator": 0.0,
            "completeness_score": 0.0
        }
        
        # Calculate feedback richness
        if grading_result.feedback:
            word_count = len(grading_result.feedback.split())
            metrics["feedback_richness"] = min(word_count / 50.0, 1.0)  # Normalize to 0-1
        
        # Calculate completeness score
        completeness_factors = [
            bool(grading_result.feedback),
            bool(grading_result.suggestions),
            bool(grading_result.strengths),
            bool(grading_result.weaknesses),
            grading_result.confidence is not None
        ]
        metrics["completeness_score"] = sum(completeness_factors) / len(completeness_factors)
        
        return metrics
    
    async def _generate_improvement_suggestions(
        self,
        grading_result: GradingResult,
        submission: Submission,
        assignment: Assignment
    ) -> List[str]:
        """Generate improvement suggestions based on grading result."""
        suggestions = []
        
        # Score-based suggestions
        if grading_result.percentage < 70:
            suggestions.append("Consider reviewing the assignment requirements and instructions")
            suggestions.append("Seek additional help or resources for this topic")
        
        # Feedback-based suggestions
        if grading_result.weaknesses:
            suggestions.append("Focus on addressing the identified weaknesses in future work")
        
        if grading_result.suggestions:
            suggestions.append("Follow the specific suggestions provided in the feedback")
        
        # Confidence-based suggestions
        if grading_result.confidence and grading_result.confidence < 0.7:
            suggestions.append("Consider having this work reviewed by the instructor")
            suggestions.append("The AI grading confidence is low - manual review recommended")
        
        return suggestions
    
    async def _assess_confidence(self, grading_result: GradingResult) -> Dict:
        """Assess the confidence level of the grading result."""
        confidence_assessment = {
            "confidence_value": grading_result.confidence,
            "confidence_level": "unknown",
            "reliability": "unknown",
            "recommendations": []
        }
        
        if grading_result.confidence is not None:
            if grading_result.confidence >= 0.9:
                confidence_assessment["confidence_level"] = "very_high"
                confidence_assessment["reliability"] = "excellent"
            elif grading_result.confidence >= 0.8:
                confidence_assessment["confidence_level"] = "high"
                confidence_assessment["reliability"] = "good"
            elif grading_result.confidence >= 0.7:
                confidence_assessment["confidence_level"] = "medium"
                confidence_assessment["reliability"] = "fair"
                confidence_assessment["recommendations"].append("Consider manual review")
            else:
                confidence_assessment["confidence_level"] = "low"
                confidence_assessment["reliability"] = "poor"
                confidence_assessment["recommendations"].append("Manual review strongly recommended")
        
        return confidence_assessment
    
    async def _generate_score_context(
        self,
        grading_result: GradingResult,
        assignment: Assignment
    ) -> Optional[str]:
        """Generate contextual information about the score."""
        if grading_result.percentage >= 90:
            return "Excellent performance! This score demonstrates strong mastery of the material."
        elif grading_result.percentage >= 80:
            return "Good work! This score shows solid understanding with room for minor improvements."
        elif grading_result.percentage >= 70:
            return "Satisfactory performance. Consider reviewing areas for improvement."
        elif grading_result.percentage >= 60:
            return "This score indicates some understanding but significant improvement is needed."
        else:
            return "This score suggests fundamental concepts need to be reviewed and reinforced."
    
    async def _generate_comparative_context(
        self,
        submission: Submission,
        grading_result: GradingResult
    ) -> Optional[str]:
        """Generate comparative context with class performance."""
        try:
            comparative_analysis = await self._analyze_comparative_performance(
                submission, grading_result
            )
            
            if comparative_analysis.get("status") != "insufficient_data":
                class_avg = comparative_analysis.get("class_average")
                percentile = comparative_analysis.get("performance_percentile")
                
                if class_avg and percentile:
                    return (
                        f"Class average: {class_avg}%. "
                        f"Your performance is in the {percentile}th percentile."
                    )
            
            return None
            
        except Exception:
            return None
    
    async def _calculate_percentile(self, assignment_id: UUID, score: int) -> Optional[int]:
        """Calculate percentile rank for a score within an assignment."""
        try:
            # Get all scores for the assignment
            query = select(Submission.score).where(
                and_(
                    Submission.assignment_id == assignment_id,
                    Submission.score.isnot(None)
                )
            )
            
            result = await self.db.execute(query)
            all_scores = [row[0] for row in result.fetchall()]
            
            if len(all_scores) < 2:
                return None
            
            # Calculate percentile
            scores_below = sum(1 for s in all_scores if s < score)
            percentile = int((scores_below / len(all_scores)) * 100)
            
            return percentile
            
        except Exception:
            return None
    
    async def _assess_score_reasonableness(
        self,
        grading_result: GradingResult,
        submission: Submission
    ) -> Dict:
        """Assess if the score seems reasonable."""
        assessment = {
            "score_reasonable": True,
            "reliability_score": 1.0,
            "flags": []
        }
        
        # Check for extreme scores
        if grading_result.percentage == 0:
            assessment["flags"].append("Zero score - may indicate grading error")
            assessment["reliability_score"] *= 0.5
        elif grading_result.percentage == 100:
            assessment["flags"].append("Perfect score - verify completeness")
            assessment["reliability_score"] *= 0.9
        
        # Check confidence vs score consistency
        if (grading_result.confidence and 
            grading_result.confidence < 0.7 and 
            grading_result.percentage > 80):
            assessment["flags"].append("High score with low confidence")
            assessment["reliability_score"] *= 0.7
        
        assessment["score_reasonable"] = assessment["reliability_score"] > 0.6
        
        return assessment
    
    async def _assess_feedback_quality(self, grading_result: GradingResult) -> str:
        """Assess the quality of feedback provided."""
        if not grading_result.feedback:
            return "poor"
        
        feedback_length = len(grading_result.feedback)
        has_suggestions = bool(grading_result.suggestions)
        has_strengths = bool(grading_result.strengths)
        has_weaknesses = bool(grading_result.weaknesses)
        
        quality_score = 0
        
        if feedback_length > 100:
            quality_score += 2
        elif feedback_length > 50:
            quality_score += 1
        
        if has_suggestions:
            quality_score += 1
        if has_strengths:
            quality_score += 1
        if has_weaknesses:
            quality_score += 1
        
        if quality_score >= 4:
            return "excellent"
        elif quality_score >= 3:
            return "good"
        elif quality_score >= 2:
            return "fair"
        else:
            return "poor"
    
    async def _calculate_overall_quality(self, quality_assessment: Dict) -> str:
        """Calculate overall quality rating."""
        confidence_level = quality_assessment.get("confidence_level", "low")
        feedback_quality = quality_assessment.get("feedback_quality", "poor")
        reliability_score = quality_assessment.get("reliability_score", 0.0)
        
        # Simple scoring system
        score = 0
        
        if confidence_level in ["high", "very_high"]:
            score += 2
        elif confidence_level == "medium":
            score += 1
        
        if feedback_quality in ["excellent", "good"]:
            score += 2
        elif feedback_quality == "fair":
            score += 1
        
        if reliability_score > 0.8:
            score += 1
        
        if score >= 4:
            return "excellent"
        elif score >= 3:
            return "good"
        elif score >= 2:
            return "fair"
        else:
            return "poor"
    
    async def _generate_quality_recommendations(
        self,
        quality_assessment: Dict,
        grading_result: GradingResult
    ) -> List[str]:
        """Generate recommendations based on quality assessment."""
        recommendations = []
        
        if quality_assessment.get("confidence_level") == "low":
            recommendations.append("Manual review recommended due to low AI confidence")
        
        if quality_assessment.get("feedback_quality") == "poor":
            recommendations.append("Consider requesting more detailed feedback")
        
        if quality_assessment.get("reliability_score", 0) < 0.7:
            recommendations.append("Grading reliability is questionable - verify results")
        
        if quality_assessment.get("flags"):
            recommendations.append("Review flagged issues before finalizing grade")
        
        return recommendations
    
    async def _calculate_grading_statistics(self, tasks: List[GradingTask]) -> Dict:
        """Calculate statistics from grading tasks."""
        scores = []
        confidences = []
        processing_times = []
        
        for task in tasks:
            if task.result:
                if "score" in task.result:
                    scores.append(task.result["score"])
                if "confidence" in task.result:
                    confidences.append(task.result["confidence"])
                if "processing_time_ms" in task.result:
                    processing_times.append(task.result["processing_time_ms"])
        
        stats = {}
        
        if scores:
            stats["score_statistics"] = {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                "min": min(scores),
                "max": max(scores)
            }
        
        if confidences:
            stats["confidence_statistics"] = {
                "mean": statistics.mean(confidences),
                "median": statistics.median(confidences),
                "min": min(confidences),
                "max": max(confidences)
            }
        
        if processing_times:
            stats["processing_time_statistics"] = {
                "mean_ms": statistics.mean(processing_times),
                "median_ms": statistics.median(processing_times),
                "min_ms": min(processing_times),
                "max_ms": max(processing_times)
            }
        
        return stats
    
    async def _analyze_performance_trends(self, tasks: List[GradingTask]) -> Dict:
        """Analyze performance trends from grading tasks."""
        # Sort tasks by creation date
        sorted_tasks = sorted(tasks, key=lambda t: t.created_at)
        
        # Extract scores over time
        scores_over_time = []
        for task in sorted_tasks:
            if task.result and "score" in task.result:
                scores_over_time.append({
                    "date": task.created_at.isoformat(),
                    "score": task.result["score"]
                })
        
        trend_analysis = {
            "scores_over_time": scores_over_time,
            "trend_direction": "stable"
        }
        
        # Simple trend analysis
        if len(scores_over_time) >= 3:
            recent_scores = [s["score"] for s in scores_over_time[-3:]]
            early_scores = [s["score"] for s in scores_over_time[:3]]
            
            recent_avg = statistics.mean(recent_scores)
            early_avg = statistics.mean(early_scores)
            
            if recent_avg > early_avg + 5:
                trend_analysis["trend_direction"] = "improving"
            elif recent_avg < early_avg - 5:
                trend_analysis["trend_direction"] = "declining"
        
        return trend_analysis
    
    async def _analyze_feedback_patterns(self, tasks: List[GradingTask]) -> Dict:
        """Analyze patterns in feedback."""
        feedback_lengths = []
        common_strengths = {}
        common_weaknesses = {}
        
        for task in tasks:
            if task.result:
                if "feedback" in task.result and task.result["feedback"]:
                    feedback_lengths.append(len(task.result["feedback"]))
                
                if "strengths" in task.result and task.result["strengths"]:
                    for strength in task.result["strengths"]:
                        common_strengths[strength] = common_strengths.get(strength, 0) + 1
                
                if "weaknesses" in task.result and task.result["weaknesses"]:
                    for weakness in task.result["weaknesses"]:
                        common_weaknesses[weakness] = common_weaknesses.get(weakness, 0) + 1
        
        patterns = {}
        
        if feedback_lengths:
            patterns["feedback_length_stats"] = {
                "mean": statistics.mean(feedback_lengths),
                "median": statistics.median(feedback_lengths),
                "min": min(feedback_lengths),
                "max": max(feedback_lengths)
            }
        
        # Get top 3 most common strengths and weaknesses
        patterns["common_strengths"] = sorted(
            common_strengths.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        patterns["common_weaknesses"] = sorted(
            common_weaknesses.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return patterns
    
    async def _analyze_quality_metrics(self, tasks: List[GradingTask]) -> Dict:
        """Analyze quality metrics across tasks."""
        high_confidence_count = 0
        low_confidence_count = 0
        total_with_confidence = 0
        
        for task in tasks:
            if task.result and "confidence" in task.result:
                confidence = task.result["confidence"]
                total_with_confidence += 1
                
                if confidence >= 0.8:
                    high_confidence_count += 1
                elif confidence < 0.6:
                    low_confidence_count += 1
        
        quality_metrics = {
            "total_tasks": len(tasks),
            "tasks_with_confidence": total_with_confidence
        }
        
        if total_with_confidence > 0:
            quality_metrics.update({
                "high_confidence_rate": high_confidence_count / total_with_confidence,
                "low_confidence_rate": low_confidence_count / total_with_confidence,
                "overall_confidence_quality": (
                    "excellent" if high_confidence_count / total_with_confidence > 0.8 else
                    "good" if high_confidence_count / total_with_confidence > 0.6 else
                    "fair" if high_confidence_count / total_with_confidence > 0.4 else
                    "poor"
                )
            })
        
        return quality_metrics
    
    async def _generate_assignment_recommendations(self, tasks: List[GradingTask]) -> List[str]:
        """Generate recommendations for the assignment based on grading patterns."""
        recommendations = []
        
        # Analyze scores
        scores = [
            task.result["score"] for task in tasks
            if task.result and "score" in task.result
        ]
        
        if scores:
            avg_score = statistics.mean(scores)
            
            if avg_score < 60:
                recommendations.append(
                    "Consider reviewing assignment difficulty - class average is low"
                )
            elif avg_score > 90:
                recommendations.append(
                    "Assignment may be too easy - consider increasing difficulty"
                )
        
        # Analyze confidence levels
        low_confidence_tasks = [
            task for task in tasks
            if (task.result and 
                "confidence" in task.result and 
                task.result["confidence"] < 0.7)
        ]
        
        if len(low_confidence_tasks) > len(tasks) * 0.3:
            recommendations.append(
                "High number of low-confidence gradings - consider manual review"
            )
        
        return recommendations


# Service factory function
async def get_grading_result_analyzer() -> GradingResultAnalyzer:
    """Get grading result analyzer instance."""
    async with get_db_session() as db:
        return GradingResultAnalyzer(db)