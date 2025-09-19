"""LangChain AI Agent service for intelligent conversations and learning analysis."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, ValidationError
from app.models.ai import ChatMessage, MessageType
from app.models.user import User
from app.schemas.ai_agent import (
    ChatRequest,
    ChatResponse,
    LearningAnalysis,
    StudyPlan,
    StudyGoal,
    StudyTask,
    ContextData
)
from app.services.user_service import UserService
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
settings = get_settings()


class AIAgentService:
    """LangChain-based AI Agent service for educational assistance."""
    
    def __init__(self, db: AsyncSession):
        """Initialize AI Agent service."""
        self.db = db
        self.user_service = UserService(db)
        self.analytics_service = AnalyticsService(db)
        
        # Initialize OpenAI LLM
        if not settings.OPENAI_API_KEY:
            raise AIServiceError("OpenAI API key not configured")
        
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Initialize memory for conversation context
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Keep last 10 messages
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize prompt templates
        self._setup_prompt_templates()
        
        # Initialize tools for the agent
        self._setup_agent_tools()
        
        # Create the agent
        self._create_agent()
    
    def _setup_prompt_templates(self) -> None:
        """Set up prompt templates for different conversation types."""
        
        # Main conversation prompt
        self.conversation_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的AI教育助手，专门帮助学生、教师和家长解决学习相关的问题。

你的主要职责包括：
1. 回答学习相关的问题
2. 分析学生的学习数据和成绩
3. 提供个性化的学习建议和计划
4. 帮助识别学习中的薄弱环节
5. 推荐适合的学习方法和资源

请始终保持：
- 专业且友好的语调
- 基于数据的客观分析
- 个性化的建议
- 鼓励性的反馈
- 清晰易懂的解释

当前用户信息：
- 用户ID: {user_id}
- 用户角色: {user_role}
- 用户姓名: {user_name}

请根据用户的具体情况提供针对性的帮助。"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Learning analysis prompt
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个学习数据分析专家，需要分析学生的学习情况并提供详细的分析报告。

请分析以下学习数据：
{learning_data}

分析要点：
1. 成绩趋势分析
2. 知识点掌握情况
3. 学习行为模式
4. 薄弱环节识别
5. 进步空间评估

请提供结构化的分析结果，包括具体的数据支撑和改进建议。"""),
            ("human", "请分析我的学习情况")
        ])
        
        # Study plan prompt
        self.study_plan_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个个性化学习计划制定专家，需要根据学生的学习情况制定详细的学习计划。

学生信息：
- 当前学习水平: {current_level}
- 薄弱环节: {weak_areas}
- 学习目标: {learning_goals}
- 可用时间: {available_time}

请制定一个详细的学习计划，包括：
1. 短期目标（1-2周）
2. 中期目标（1个月）
3. 长期目标（3个月）
4. 具体的学习任务和时间安排
5. 推荐的学习资源和方法
6. 进度检查点和评估标准"""),
            ("human", "{request}")
        ])
    
    def _setup_agent_tools(self) -> None:
        """Set up tools for the AI agent."""
        from langchain.tools import tool
        
        @tool
        def get_learning_data(user_id: str) -> str:
            """获取用户的学习数据，包括成绩、作业完成情况等"""
            try:
                # This would be implemented to fetch actual learning data
                return f"Learning data for user {user_id}"
            except Exception as e:
                return f"Error fetching learning data: {str(e)}"
        
        @tool
        def analyze_performance(user_id: str, analysis_type: str = "general") -> str:
            """分析学生的学习表现和成绩趋势"""
            try:
                # This would be implemented to perform actual analytics
                return f"Performance analysis for user {user_id}"
            except Exception as e:
                return f"Error analyzing performance: {str(e)}"
        
        self.tools = [get_learning_data, analyze_performance]
    
    def _create_agent(self) -> None:
        """Create the LangChain agent with tools."""
        try:
            self.agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.conversation_prompt
            )
            
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=self.memory,
                verbose=True,
                max_iterations=3,
                early_stopping_method="generate"
            )
            
            logger.info("AI Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to create AI agent: {str(e)}")
            raise AIServiceError(f"Failed to initialize AI agent: {str(e)}")
    
    async def process_chat_message(
        self,
        user_id: UUID,
        message: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """Process a chat message and return AI response."""
        try:
            # Get user information
            user = await self.user_service.get_user_by_id(user_id)
            if not user:
                raise ValidationError("User not found")
            
            # Prepare context for the agent
            agent_context = {
                "user_id": str(user_id),
                "user_role": user.role,
                "user_name": user.name,
                "input": message
            }
            
            # Add additional context if provided
            if context_data:
                agent_context.update(context_data)
            
            # Process message with agent
            start_time = datetime.utcnow()
            
            response = await self._run_agent_async(agent_context)
            
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Save user message
            await self._save_chat_message(
                user_id=user_id,
                message_type=MessageType.USER,
                content=message,
                context_data=context_data
            )
            
            # Save assistant response
            await self._save_chat_message(
                user_id=user_id,
                message_type=MessageType.ASSISTANT,
                content=response,
                context_data={"response_time_ms": response_time_ms},
                response_time_ms=response_time_ms
            )
            
            return ChatResponse(
                message=response,
                user_id=user_id,
                timestamp=end_time,
                context_data=context_data,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            raise AIServiceError(f"Failed to process chat message: {str(e)}")
    
    async def _run_agent_async(self, context: Dict[str, Any]) -> str:
        """Run the agent asynchronously."""
        try:
            # For now, we'll use a simple implementation
            # In a full implementation, this would use the actual agent executor
            result = self.agent_executor.invoke(context)
            return result.get("output", "I'm sorry, I couldn't process your request.")
            
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            return "I apologize, but I'm experiencing some technical difficulties. Please try again later."
    
    async def _save_chat_message(
        self,
        user_id: UUID,
        message_type: MessageType,
        content: str,
        context_data: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None
    ) -> ChatMessage:
        """Save chat message to database."""
        try:
            chat_message = ChatMessage(
                user_id=user_id,
                message_type=message_type,
                content=content,
                context_data=context_data,
                ai_model="gpt-4-turbo-preview" if message_type == MessageType.ASSISTANT else None,
                response_time_ms=response_time_ms
            )
            
            self.db.add(chat_message)
            await self.db.commit()
            await self.db.refresh(chat_message)
            
            return chat_message
            
        except Exception as e:
            logger.error(f"Error saving chat message: {str(e)}")
            await self.db.rollback()
            raise
    
    async def get_chat_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get chat history for a user."""
        try:
            from sqlalchemy import select
            
            query = (
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            # Return in chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error fetching chat history: {str(e)}")
            raise AIServiceError(f"Failed to fetch chat history: {str(e)}")
    
    async def clear_chat_history(self, user_id: UUID) -> bool:
        """Clear chat history for a user."""
        try:
            from sqlalchemy import delete
            
            query = delete(ChatMessage).where(ChatMessage.user_id == user_id)
            await self.db.execute(query)
            await self.db.commit()
            
            # Clear memory as well
            self.memory.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
            await self.db.rollback()
            raise AIServiceError(f"Failed to clear chat history: {str(e)}")
    
    async def update_user_context(
        self,
        user_id: UUID,
        context_data: Dict[str, Any]
    ) -> bool:
        """Update user context for better personalization."""
        try:
            # Save context as a system message
            await self._save_chat_message(
                user_id=user_id,
                message_type=MessageType.SYSTEM,
                content="Context update",
                context_data=context_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user context: {str(e)}")
            raise AIServiceError(f"Failed to update user context: {str(e)}")
    
    async def analyze_learning_data(
        self,
        user_id: UUID,
        analysis_type: str = "general",
        time_period: Optional[str] = "last_month",
        subjects: Optional[List[str]] = None,
        include_recommendations: bool = True
    ) -> LearningAnalysis:
        """Analyze user's learning data and provide insights."""
        try:
            from datetime import datetime
            from app.schemas.ai_agent import KnowledgePoint, LearningTrend, WeakArea
            
            # Get user information
            user = await self.user_service.get_user_by_id(user_id)
            if not user:
                raise ValidationError("User not found")
            
            # Get real analytics data
            performance_data = await self.analytics_service.get_user_performance_data(
                user_id, time_period, subjects
            )
            
            mastery_levels = await self.analytics_service.calculate_mastery_levels(
                user_id, subjects
            )
            
            weak_areas_data = await self.analytics_service.identify_weak_areas(user_id)
            
            learning_patterns = await self.analytics_service.analyze_learning_patterns(user_id)
            
            trends_data = await self.analytics_service.get_learning_trends(user_id)
            
            # Convert analytics data to schema objects
            knowledge_points = []
            for topic, mastery in mastery_levels.items():
                # Estimate practice count and errors based on performance data
                practice_count = max(1, performance_data.get("total_submissions", 0) // len(mastery_levels))
                error_count = max(0, int(practice_count * (1 - mastery)))
                
                knowledge_points.append(KnowledgePoint(
                    name=topic,
                    subject=subjects[0] if subjects else "mathematics",
                    mastery_level=mastery,
                    practice_count=practice_count,
                    error_count=error_count,
                    last_practiced=datetime.utcnow(),
                    difficulty_level=self._determine_difficulty_level(mastery)
                ))
            
            # Convert trends data
            learning_trends = []
            for trend in trends_data[:10]:  # Limit to recent trends
                learning_trends.append(LearningTrend(
                    date=trend["date"],
                    score=trend["average_score"],
                    subject=subjects[0] if subjects else "mathematics",
                    assignment_count=trend["assignments_completed"]
                ))
            
            # Convert weak areas
            weak_areas = []
            for weak_area in weak_areas_data:
                recommendations = self._generate_area_recommendations(weak_area["area"])
                
                weak_areas.append(WeakArea(
                    area=weak_area["area"],
                    subject=weak_area["subject"],
                    severity=weak_area.get("severity", "medium"),
                    error_rate=weak_area.get("error_count", 0) / max(weak_area.get("total_attempts", 1), 1),
                    recommendation=recommendations["main"],
                    practice_resources=recommendations["resources"]
                ))
            
            # Generate AI-powered analysis
            analysis_context = {
                "user_role": user.role,
                "performance_data": performance_data,
                "learning_patterns": learning_patterns,
                "mastery_levels": mastery_levels,
                "weak_areas": weak_areas_data
            }
            
            # Use LangChain to generate detailed analysis
            analysis_prompt_formatted = self.analysis_prompt.format_messages(
                learning_data=str(analysis_context)
            )
            
            # Get AI analysis
            ai_response = await self._get_ai_analysis(analysis_prompt_formatted)
            
            # Generate recommendations
            recommendations = []
            if include_recommendations:
                recommendations = await self._generate_personalized_recommendations(
                    user_id, learning_patterns, weak_areas_data, ai_response
                )
            
            return LearningAnalysis(
                user_id=user_id,
                analysis_date=datetime.utcnow(),
                overall_performance=performance_data.get("average_score", 0),
                knowledge_points=knowledge_points,
                learning_trends=learning_trends,
                weak_areas=weak_areas,
                strengths=learning_patterns.get("strengths", []),
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error analyzing learning data: {str(e)}")
            raise AIServiceError(f"Failed to analyze learning data: {str(e)}")
    
    def _determine_difficulty_level(self, mastery: float) -> str:
        """Determine difficulty level based on mastery."""
        if mastery >= 0.8:
            return "advanced"
        elif mastery >= 0.6:
            return "intermediate"
        else:
            return "beginner"
    
    def _generate_area_recommendations(self, area: str) -> Dict[str, Any]:
        """Generate recommendations for specific weak areas."""
        recommendations = {
            "Quadratic Equations": {
                "main": "Focus on factoring techniques and completing the square method",
                "resources": ["Khan Academy - Quadratics", "Practice Worksheet #5", "Quadratic Formula Drills"]
            },
            "Geometry Proofs": {
                "main": "Practice logical reasoning and proof structure",
                "resources": ["Geometry Proof Templates", "Logic Practice Problems", "Visual Proof Examples"]
            },
            "Linear Equations": {
                "main": "Review basic algebraic manipulation and graphing",
                "resources": ["Algebra Basics Review", "Graphing Practice", "Word Problem Examples"]
            },
            "Trigonometry": {
                "main": "Memorize unit circle and practice identity applications",
                "resources": ["Unit Circle Practice", "Trig Identity Cheat Sheet", "Real-world Applications"]
            }
        }
        
        return recommendations.get(area, {
            "main": f"Focus on practicing {area} fundamentals",
            "resources": ["Textbook exercises", "Online practice problems", "Study group sessions"]
        })
    
    async def _generate_personalized_recommendations(
        self,
        user_id: UUID,
        learning_patterns: Dict[str, Any],
        weak_areas: List[Dict[str, Any]],
        ai_analysis: str
    ) -> List[str]:
        """Generate personalized recommendations based on analysis."""
        recommendations = []
        
        # Based on learning patterns
        if learning_patterns.get("consistency", 0) < 0.7:
            recommendations.append("建立更规律的学习习惯，每天固定时间学习")
        
        if learning_patterns.get("score_trend") == "declining":
            recommendations.append("最近成绩有下降趋势，建议回顾基础知识")
        
        peak_time = learning_patterns.get("peak_performance_time")
        if peak_time:
            recommendations.append(f"你在{peak_time}时段表现最佳，建议在此时间安排重要学习任务")
        
        # Based on weak areas
        for weak_area in weak_areas[:2]:  # Top 2 weak areas
            area = weak_area["area"]
            severity = weak_area.get("severity", "medium")
            
            if severity == "high":
                recommendations.append(f"优先加强{area}的练习，这是当前最需要改进的领域")
            else:
                recommendations.append(f"适当增加{area}的练习时间")
        
        # Add AI-generated recommendations
        if ai_analysis and len(ai_analysis) > 50:
            # Extract key insights from AI analysis
            ai_recommendation = ai_analysis[:150] + "..." if len(ai_analysis) > 150 else ai_analysis
            recommendations.append(f"AI分析建议：{ai_recommendation}")
        
        # Ensure we have at least some recommendations
        if not recommendations:
            recommendations = [
                "继续保持良好的学习态度",
                "定期复习已学内容",
                "遇到困难及时寻求帮助"
            ]
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    async def generate_learning_resources(
        self,
        user_id: UUID,
        topic: str,
        difficulty_level: str = "intermediate"
    ) -> Dict[str, List[str]]:
        """Generate personalized learning resources for a specific topic."""
        try:
            # Get user's learning patterns to personalize resources
            learning_patterns = await self.analytics_service.analyze_learning_patterns(user_id)
            mastery_levels = await self.analytics_service.calculate_mastery_levels(user_id)
            
            # Base resources by topic
            resource_database = {
                "Quadratic Equations": {
                    "beginner": {
                        "videos": ["Khan Academy - Intro to Quadratics", "Professor Leonard - Quadratic Basics"],
                        "practice": ["Basic Quadratic Worksheets", "Simple Factoring Problems"],
                        "reading": ["Algebra Textbook Ch. 9", "Quadratic Equations Guide"],
                        "interactive": ["Desmos Graphing Calculator", "Quadratic Formula Tool"]
                    },
                    "intermediate": {
                        "videos": ["Khan Academy - Quadratic Formula", "PatrickJMT - Completing the Square"],
                        "practice": ["Mixed Quadratic Problems", "Word Problem Sets"],
                        "reading": ["Advanced Algebra Guide", "Quadratic Applications"],
                        "interactive": ["Quadratic Explorer", "Graphing Practice Tool"]
                    },
                    "advanced": {
                        "videos": ["MIT OpenCourseWare - Quadratics", "Advanced Quadratic Techniques"],
                        "practice": ["Competition Math Problems", "Complex Quadratics"],
                        "reading": ["College Algebra Textbook", "Mathematical Olympiad Problems"],
                        "interactive": ["Advanced Graphing Software", "Mathematical Modeling Tools"]
                    }
                },
                "Geometry Proofs": {
                    "beginner": {
                        "videos": ["Khan Academy - Intro to Proofs", "Geometry Basics"],
                        "practice": ["Simple Proof Templates", "Basic Theorem Applications"],
                        "reading": ["Geometry Fundamentals", "Proof Writing Guide"],
                        "interactive": ["GeoGebra Basic", "Proof Builder Tool"]
                    },
                    "intermediate": {
                        "videos": ["Khan Academy - Geometric Proofs", "Proof Techniques"],
                        "practice": ["Two-Column Proofs", "Paragraph Proofs"],
                        "reading": ["Geometry Textbook", "Proof Strategies Guide"],
                        "interactive": ["GeoGebra Advanced", "Interactive Proof Tool"]
                    },
                    "advanced": {
                        "videos": ["Advanced Geometric Proofs", "Competition Geometry"],
                        "practice": ["Olympiad Geometry Problems", "Complex Proofs"],
                        "reading": ["Advanced Geometry Texts", "Research Papers"],
                        "interactive": ["Professional Geometry Software", "3D Modeling Tools"]
                    }
                }
            }
            
            # Get resources for the topic and difficulty level
            topic_resources = resource_database.get(topic, {})
            level_resources = topic_resources.get(difficulty_level, {})
            
            # If no specific resources, create generic ones
            if not level_resources:
                level_resources = {
                    "videos": [f"{topic} Tutorial Videos", f"Online {topic} Lectures"],
                    "practice": [f"{topic} Practice Problems", f"{topic} Worksheets"],
                    "reading": [f"{topic} Study Guide", f"{topic} Reference Materials"],
                    "interactive": [f"{topic} Online Tools", f"Interactive {topic} Exercises"]
                }
            
            # Personalize based on learning patterns
            personalized_resources = self._personalize_resources(
                level_resources, learning_patterns, mastery_levels.get(topic, 0.5)
            )
            
            return personalized_resources
            
        except Exception as e:
            logger.error(f"Error generating learning resources: {str(e)}")
            raise AIServiceError(f"Failed to generate learning resources: {str(e)}")
    
    def _personalize_resources(
        self,
        base_resources: Dict[str, List[str]],
        learning_patterns: Dict[str, Any],
        mastery_level: float
    ) -> Dict[str, List[str]]:
        """Personalize resources based on learning patterns."""
        personalized = base_resources.copy()
        
        # Add recommendations based on consistency
        consistency = learning_patterns.get("consistency", 0.5)
        if consistency < 0.6:
            personalized["study_tips"] = [
                "Set up a regular study schedule",
                "Use a study planner or app",
                "Create daily study reminders"
            ]
        
        # Add resources based on mastery level
        if mastery_level < 0.4:
            personalized["foundation"] = [
                "Review prerequisite concepts",
                "Start with basic examples",
                "Focus on understanding before speed"
            ]
        elif mastery_level > 0.8:
            personalized["challenge"] = [
                "Try advanced problems",
                "Explore real-world applications",
                "Consider teaching others"
            ]
        
        # Add peak time recommendations
        peak_time = learning_patterns.get("peak_performance_time")
        if peak_time:
            personalized["timing"] = [
                f"Schedule difficult topics during your {peak_time} peak time",
                f"Use {peak_time} for new concept learning",
                f"Review and practice during other times"
            ]
        
        return personalized
    
    async def generate_adaptive_feedback(
        self,
        user_id: UUID,
        recent_performance: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate adaptive feedback based on recent performance."""
        try:
            # Analyze recent performance trends
            scores = [p.get("score", 0) for p in recent_performance if p.get("score") is not None]
            
            if not scores:
                return {"message": "No recent performance data available"}
            
            # Calculate performance metrics
            avg_score = sum(scores) / len(scores)
            trend = "improving" if self._is_improving_trend(scores) else "declining"
            consistency = self._calculate_consistency(scores)
            
            # Get user's learning patterns for context
            learning_patterns = await self.analytics_service.analyze_learning_patterns(user_id)
            weak_areas = await self.analytics_service.identify_weak_areas(user_id)
            
            # Generate adaptive feedback
            feedback = {
                "overall_message": self._generate_overall_feedback_message(avg_score, trend, consistency),
                "specific_feedback": self._generate_specific_feedback(scores, recent_performance),
                "encouragement": self._generate_encouragement(trend, consistency, avg_score),
                "next_steps": await self._generate_next_steps(user_id, weak_areas, learning_patterns),
                "performance_summary": {
                    "average_score": round(avg_score, 1),
                    "trend": trend,
                    "consistency": round(consistency, 2),
                    "total_attempts": len(scores)
                }
            }
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating adaptive feedback: {str(e)}")
            raise AIServiceError(f"Failed to generate adaptive feedback: {str(e)}")
    
    def _generate_overall_feedback_message(self, avg_score: float, trend: str, consistency: float) -> str:
        """Generate an overall feedback message."""
        # Prioritize trend over average score
        if trend == "declining":
            return "Your recent scores show a declining trend. Let's focus on identifying areas that need improvement and create a targeted study plan."
        elif avg_score >= 85 and trend == "improving" and consistency > 0.8:
            return "Excellent work! You're performing consistently at a high level and showing continuous improvement."
        elif avg_score >= 75 and trend == "improving":
            return "Great progress! Your scores are improving and you're on the right track."
        elif trend == "improving":
            return "Nice improvement! Keep up the good work and continue building on your progress."
        elif avg_score >= 75 and consistency > 0.7:
            return "Good consistent performance! You're maintaining steady progress."
        elif avg_score >= 70:
            return "You're doing well overall. Focus on consistency to reach the next level."
        else:
            return "There's room for improvement. Let's identify areas to focus on and create a plan."
    
    def _generate_specific_feedback(self, scores: List[float], performance_data: List[Dict[str, Any]]) -> List[str]:
        """Generate specific feedback based on performance patterns."""
        feedback = []
        
        # Analyze score patterns
        if len(scores) >= 3:
            recent_scores = scores[-3:]
            if all(s >= 80 for s in recent_scores):
                feedback.append("Your recent performance has been consistently strong")
            elif any(s < 60 for s in recent_scores):
                feedback.append("Some recent scores indicate areas that need attention")
        
        # Analyze score variance
        if len(scores) > 1:
            score_range = max(scores) - min(scores)
            if score_range > 30:
                feedback.append("Your scores vary significantly - focus on consistency")
            elif score_range < 10:
                feedback.append("Your performance is very consistent")
        
        # Analyze improvement areas
        if scores:
            lowest_score = min(scores)
            if lowest_score < 60:
                feedback.append("Pay special attention to topics where you scored below 60%")
        
        return feedback
    
    def _generate_encouragement(self, trend: str, consistency: float, avg_score: float) -> str:
        """Generate encouraging message."""
        if trend == "improving":
            return "You're making great progress! Keep up the momentum."
        elif consistency > 0.8:
            return "Your consistency is impressive! This steady approach will pay off."
        elif avg_score >= 70:
            return "You're doing well! Small improvements will make a big difference."
        else:
            return "Every expert was once a beginner. Keep practicing and you'll see improvement!"
    
    async def _generate_next_steps(
        self,
        user_id: UUID,
        weak_areas: List[Dict[str, Any]],
        learning_patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized next steps."""
        next_steps = []
        
        # Based on weak areas
        if weak_areas:
            top_weak_area = weak_areas[0]
            next_steps.append(f"Focus extra practice time on {top_weak_area['area']}")
        
        # Based on consistency
        consistency = learning_patterns.get("consistency", 0.5)
        if consistency < 0.6:
            next_steps.append("Establish a more regular study routine")
        
        # Based on study frequency
        study_frequency = learning_patterns.get("study_frequency", 0)
        if study_frequency < 0.5:  # Less than every other day
            next_steps.append("Increase study frequency to at least every other day")
        
        # General recommendations
        next_steps.extend([
            "Review mistakes from recent assignments",
            "Set specific goals for the next week",
            "Consider forming a study group or finding a study partner"
        ])
        
        return next_steps[:4]  # Limit to 4 next steps
    
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
    
    async def get_conversation_context(
        self,
        user_id: UUID,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get conversation context for better AI responses."""
        try:
            # Get recent chat history
            recent_messages = await self.get_chat_history(user_id, limit=limit)
            
            # Get user's learning context
            learning_patterns = await self.analytics_service.analyze_learning_patterns(user_id)
            weak_areas = await self.analytics_service.identify_weak_areas(user_id)
            mastery_levels = await self.analytics_service.calculate_mastery_levels(user_id)
            
            # Analyze conversation patterns
            conversation_analysis = self._analyze_conversation_patterns(recent_messages)
            
            # Build comprehensive context
            context = {
                "user_id": str(user_id),
                "conversation_id": conversation_id,
                "recent_messages": [
                    {
                        "type": msg.message_type,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                        "timestamp": msg.created_at,
                        "context_data": msg.context_data
                    }
                    for msg in recent_messages
                ],
                "learning_context": {
                    "weak_areas": [wa["area"] for wa in weak_areas[:3]],
                    "strong_areas": [topic for topic, level in mastery_levels.items() if level > 0.8],
                    "consistency": learning_patterns.get("consistency", 0.5),
                    "peak_time": learning_patterns.get("peak_performance_time"),
                    "recent_trend": learning_patterns.get("score_trend", "stable")
                },
                "conversation_patterns": conversation_analysis,
                "context_summary": self._generate_context_summary(
                    learning_patterns, weak_areas, conversation_analysis
                )
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            raise AIServiceError(f"Failed to get conversation context: {str(e)}")
    
    def _analyze_conversation_patterns(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze patterns in conversation history."""
        if not messages:
            return {"total_messages": 0, "topics": [], "engagement_level": "new"}
        
        # Analyze message content for topics
        topics = []
        question_count = 0
        help_requests = 0
        
        for msg in messages:
            if msg.is_user_message:
                content_lower = msg.content.lower()
                
                # Count questions
                if "?" in msg.content or any(word in content_lower for word in ["how", "what", "why", "when", "where"]):
                    question_count += 1
                
                # Count help requests
                if any(word in content_lower for word in ["help", "explain", "don't understand", "confused"]):
                    help_requests += 1
                
                # Extract topics (simple keyword matching)
                for topic in ["math", "algebra", "geometry", "calculus", "trigonometry", "statistics"]:
                    if topic in content_lower and topic not in topics:
                        topics.append(topic)
        
        # Determine engagement level
        user_messages = [msg for msg in messages if msg.is_user_message]
        if len(user_messages) >= 10:
            engagement_level = "high"
        elif len(user_messages) >= 5:
            engagement_level = "medium"
        else:
            engagement_level = "low"
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "topics": topics,
            "question_count": question_count,
            "help_requests": help_requests,
            "engagement_level": engagement_level,
            "avg_message_length": sum(len(msg.content) for msg in user_messages) / len(user_messages) if user_messages else 0
        }
    
    def _generate_context_summary(
        self,
        learning_patterns: Dict[str, Any],
        weak_areas: List[Dict[str, Any]],
        conversation_patterns: Dict[str, Any]
    ) -> str:
        """Generate a summary of the current context for AI processing."""
        summary_parts = []
        
        # Learning context
        consistency = learning_patterns.get("consistency", 0.5)
        if consistency > 0.8:
            summary_parts.append("Student shows high consistency in learning")
        elif consistency < 0.5:
            summary_parts.append("Student needs help with study consistency")
        
        # Weak areas
        if weak_areas:
            top_weak = weak_areas[0]["area"]
            summary_parts.append(f"Main challenge area: {top_weak}")
        
        # Conversation patterns
        engagement = conversation_patterns.get("engagement_level", "new")
        if engagement == "high":
            summary_parts.append("Highly engaged student with many questions")
        elif engagement == "low":
            summary_parts.append("New or less engaged student")
        
        help_requests = conversation_patterns.get("help_requests", 0)
        if help_requests > 2:
            summary_parts.append("Student frequently asks for help - provide detailed explanations")
        
        return "; ".join(summary_parts) if summary_parts else "New conversation with limited context"
    
    async def evaluate_conversation_quality(
        self,
        user_id: UUID,
        conversation_id: Optional[str] = None,
        recent_messages: Optional[List[ChatMessage]] = None
    ) -> Dict[str, Any]:
        """Evaluate the quality of recent conversations."""
        try:
            if not recent_messages:
                recent_messages = await self.get_chat_history(user_id, limit=20)
            
            if not recent_messages:
                return {"quality_score": 0, "feedback": "No conversation history available"}
            
            # Analyze conversation quality metrics
            quality_metrics = {
                "responsiveness": self._evaluate_responsiveness(recent_messages),
                "helpfulness": self._evaluate_helpfulness(recent_messages),
                "engagement": self._evaluate_engagement(recent_messages),
                "clarity": self._evaluate_clarity(recent_messages),
                "personalization": self._evaluate_personalization(recent_messages)
            }
            
            # Calculate overall quality score
            overall_score = sum(quality_metrics.values()) / len(quality_metrics)
            
            # Generate improvement suggestions
            suggestions = self._generate_quality_improvements(quality_metrics)
            
            return {
                "quality_score": round(overall_score, 2),
                "metrics": quality_metrics,
                "suggestions": suggestions,
                "conversation_length": len(recent_messages),
                "evaluation_date": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating conversation quality: {str(e)}")
            raise AIServiceError(f"Failed to evaluate conversation quality: {str(e)}")
    
    def _evaluate_responsiveness(self, messages: List[ChatMessage]) -> float:
        """Evaluate how responsive the AI has been to user queries."""
        if not messages:
            return 0.0
        
        user_messages = [msg for msg in messages if msg.is_user_message]
        assistant_messages = [msg for msg in messages if msg.is_assistant_message]
        
        if not user_messages:
            return 0.0
        
        # Check response rate
        response_rate = len(assistant_messages) / len(user_messages)
        
        # Check response times (if available)
        avg_response_time = 0
        response_times = [msg.response_time_ms for msg in assistant_messages if msg.response_time_ms]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            # Good response time is under 3 seconds (3000ms)
            time_score = max(0, 1 - (avg_response_time - 1000) / 5000)
        else:
            time_score = 0.8  # Default if no timing data
        
        return min(1.0, (response_rate * 0.7 + time_score * 0.3))
    
    def _evaluate_helpfulness(self, messages: List[ChatMessage]) -> float:
        """Evaluate how helpful the AI responses have been."""
        assistant_messages = [msg for msg in messages if msg.is_assistant_message]
        
        if not assistant_messages:
            return 0.0
        
        helpful_indicators = 0
        total_responses = len(assistant_messages)
        
        for msg in assistant_messages:
            content_lower = msg.content.lower()
            
            # Check for helpful patterns
            if any(indicator in content_lower for indicator in [
                "let me help", "here's how", "try this", "step by step",
                "example", "practice", "recommend", "suggest"
            ]):
                helpful_indicators += 1
            
            # Check for detailed responses (longer responses often more helpful)
            if len(msg.content) > 100:
                helpful_indicators += 0.5
        
        return min(1.0, helpful_indicators / total_responses)
    
    def _evaluate_engagement(self, messages: List[ChatMessage]) -> float:
        """Evaluate user engagement level."""
        user_messages = [msg for msg in messages if msg.is_user_message]
        
        if not user_messages:
            return 0.0
        
        # Factors that indicate engagement
        engagement_score = 0
        
        # Message frequency
        if len(user_messages) >= 10:
            engagement_score += 0.3
        elif len(user_messages) >= 5:
            engagement_score += 0.2
        
        # Question asking
        questions = sum(1 for msg in user_messages if "?" in msg.content)
        if questions >= 3:
            engagement_score += 0.3
        elif questions >= 1:
            engagement_score += 0.2
        
        # Message length (engaged users write more)
        avg_length = sum(len(msg.content) for msg in user_messages) / len(user_messages)
        if avg_length > 50:
            engagement_score += 0.2
        elif avg_length > 20:
            engagement_score += 0.1
        
        # Follow-up questions
        follow_ups = 0
        for i in range(1, len(user_messages)):
            if any(word in user_messages[i].content.lower() for word in ["also", "and", "what about", "how about"]):
                follow_ups += 1
        
        if follow_ups > 0:
            engagement_score += 0.2
        
        return min(1.0, engagement_score)
    
    def _evaluate_clarity(self, messages: List[ChatMessage]) -> float:
        """Evaluate clarity of AI responses."""
        assistant_messages = [msg for msg in messages if msg.is_assistant_message]
        
        if not assistant_messages:
            return 0.0
        
        clarity_score = 0
        total_responses = len(assistant_messages)
        
        for msg in assistant_messages:
            content = msg.content
            
            # Check for clear structure
            if any(indicator in content for indicator in ["1.", "2.", "First", "Second", "Step"]):
                clarity_score += 0.3
            
            # Check for examples
            if any(word in content.lower() for word in ["example", "for instance", "like this"]):
                clarity_score += 0.2
            
            # Check for explanations
            if any(word in content.lower() for word in ["because", "since", "this means", "in other words"]):
                clarity_score += 0.2
            
            # Avoid overly long responses
            if 50 <= len(content) <= 500:
                clarity_score += 0.3
            elif len(content) > 500:
                clarity_score += 0.1
        
        return min(1.0, clarity_score / total_responses)
    
    def _evaluate_personalization(self, messages: List[ChatMessage]) -> float:
        """Evaluate how personalized the responses are."""
        assistant_messages = [msg for msg in messages if msg.is_assistant_message]
        
        if not assistant_messages:
            return 0.0
        
        personalization_score = 0
        total_responses = len(assistant_messages)
        
        for msg in assistant_messages:
            content_lower = msg.content.lower()
            
            # Check for personal references
            if any(word in content_lower for word in ["you", "your", "based on your"]):
                personalization_score += 0.2
            
            # Check for context awareness
            if msg.context_data and len(msg.context_data) > 0:
                personalization_score += 0.3
            
            # Check for specific recommendations
            if any(word in content_lower for word in ["recommend", "suggest", "for you", "your case"]):
                personalization_score += 0.2
        
        return min(1.0, personalization_score / total_responses)
    
    def _generate_quality_improvements(self, metrics: Dict[str, float]) -> List[str]:
        """Generate suggestions for improving conversation quality."""
        suggestions = []
        
        if metrics["responsiveness"] < 0.7:
            suggestions.append("Improve response time and ensure all user questions are addressed")
        
        if metrics["helpfulness"] < 0.7:
            suggestions.append("Provide more detailed explanations and practical examples")
        
        if metrics["engagement"] < 0.5:
            suggestions.append("Ask more engaging questions to encourage user participation")
        
        if metrics["clarity"] < 0.7:
            suggestions.append("Structure responses more clearly with numbered steps or bullet points")
        
        if metrics["personalization"] < 0.6:
            suggestions.append("Use more personalized responses based on user's learning history")
        
        if not suggestions:
            suggestions.append("Conversation quality is good - maintain current approach")
        
        return suggestions
    
    async def manage_conversation_memory(
        self,
        user_id: UUID,
        action: str,
        conversation_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Manage conversation memory and context."""
        try:
            if action == "save_context":
                # Save important context for future conversations
                await self._save_chat_message(
                    user_id=user_id,
                    message_type=MessageType.SYSTEM,
                    content="Context saved",
                    context_data=context_data
                )
                return {"status": "success", "message": "Context saved successfully"}
            
            elif action == "load_context":
                # Load conversation context
                context = await self.get_conversation_context(user_id, conversation_id)
                return {"status": "success", "context": context}
            
            elif action == "clear_memory":
                # Clear conversation memory
                success = await self.clear_chat_history(user_id)
                self.memory.clear()
                return {"status": "success" if success else "error", "message": "Memory cleared"}
            
            elif action == "optimize_memory":
                # Optimize memory by keeping only important messages
                await self._optimize_conversation_memory(user_id)
                return {"status": "success", "message": "Memory optimized"}
            
            else:
                raise ValidationError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Error managing conversation memory: {str(e)}")
            raise AIServiceError(f"Failed to manage conversation memory: {str(e)}")
    
    async def _optimize_conversation_memory(self, user_id: UUID) -> None:
        """Optimize conversation memory by keeping only important messages."""
        try:
            # Get all messages
            all_messages = await self.get_chat_history(user_id, limit=100)
            
            if len(all_messages) <= 20:
                return  # No need to optimize
            
            # Identify important messages
            important_messages = []
            
            for msg in all_messages:
                # Keep system messages (context)
                if msg.is_system_message:
                    important_messages.append(msg)
                    continue
                
                # Keep messages with high engagement
                if msg.is_user_message and len(msg.content) > 50:
                    important_messages.append(msg)
                    continue
                
                # Keep AI responses with context data
                if msg.is_assistant_message and msg.context_data:
                    important_messages.append(msg)
                    continue
                
                # Keep recent messages (last 10)
                if msg in all_messages[-10:]:
                    important_messages.append(msg)
            
            # Update memory with important messages only
            self.memory.clear()
            for msg in important_messages[-10:]:  # Keep last 10 important messages
                if msg.is_user_message:
                    self.memory.chat_memory.add_user_message(msg.content)
                elif msg.is_assistant_message:
                    self.memory.chat_memory.add_ai_message(msg.content)
            
        except Exception as e:
            logger.error(f"Error optimizing conversation memory: {str(e)}")
            raise
    
    async def generate_study_plan(
        self,
        user_id: UUID,
        goals: List[str],
        available_time_per_day: int,
        target_weeks: int = 4,
        difficulty_level: str = "intermediate"
    ) -> StudyPlan:
        """Generate a personalized study plan."""
        try:
            from datetime import datetime, timedelta
            from app.schemas.ai_agent import StudyGoal, StudyTask
            
            # Get user information and learning data
            user = await self.user_service.get_user_by_id(user_id)
            if not user:
                raise ValidationError("User not found")
            
            # Get user's learning analytics for personalization
            performance_data = await self.analytics_service.get_user_performance_data(user_id)
            weak_areas = await self.analytics_service.identify_weak_areas(user_id)
            mastery_levels = await self.analytics_service.calculate_mastery_levels(user_id)
            learning_patterns = await self.analytics_service.analyze_learning_patterns(user_id)
            
            # Create personalized study goals
            study_goals = await self._create_personalized_goals(
                goals, weak_areas, mastery_levels, target_weeks
            )
            
            # Generate weekly tasks based on user's learning patterns and weak areas
            weekly_tasks = await self._generate_personalized_weekly_tasks(
                user_id, goals, weak_areas, mastery_levels, learning_patterns,
                available_time_per_day, target_weeks, difficulty_level
            )
            
            # Use AI to enhance and validate the study plan
            plan_context = {
                "user_role": user.role,
                "current_performance": performance_data.get("average_score", 0),
                "weak_areas": [wa["area"] for wa in weak_areas],
                "strong_areas": [topic for topic, level in mastery_levels.items() if level > 0.8],
                "learning_goals": goals,
                "available_time": f"{available_time_per_day} minutes per day",
                "consistency": learning_patterns.get("consistency", 0.5),
                "peak_time": learning_patterns.get("peak_performance_time", "morning")
            }
            
            study_plan_prompt_formatted = self.study_plan_prompt.format_messages(
                current_level=f"Average score: {plan_context['current_performance']:.1f}%",
                weak_areas=", ".join(plan_context["weak_areas"]),
                learning_goals=", ".join(goals),
                available_time=plan_context["available_time"],
                request=f"Create a personalized study plan for a {user.role} with {plan_context['consistency']:.1f} consistency"
            )
            
            # Get AI recommendations for the plan
            ai_recommendations = await self._get_ai_analysis(study_plan_prompt_formatted)
            
            # Calculate total estimated hours
            total_hours = 0
            for week_tasks in weekly_tasks.values():
                for task in week_tasks:
                    total_hours += task.estimated_time_minutes
            total_hours = int(total_hours / 60)
            
            return StudyPlan(
                user_id=user_id,
                plan_name=self._generate_plan_name(goals, user.name),
                created_date=datetime.utcnow(),
                target_completion_date=datetime.utcnow() + timedelta(weeks=target_weeks),
                goals=study_goals,
                weekly_tasks=weekly_tasks,
                estimated_total_hours=total_hours,
                difficulty_level=difficulty_level
            )
            
        except Exception as e:
            logger.error(f"Error generating study plan: {str(e)}")
            raise AIServiceError(f"Failed to generate study plan: {str(e)}")
    
    async def _create_personalized_goals(
        self,
        user_goals: List[str],
        weak_areas: List[Dict[str, Any]],
        mastery_levels: Dict[str, float],
        target_weeks: int
    ) -> List[StudyGoal]:
        """Create personalized study goals based on user data."""
        from datetime import datetime, timedelta
        from app.schemas.ai_agent import StudyGoal
        
        goals = []
        
        # Create goals from user input
        for i, goal in enumerate(user_goals):
            priority = "high" if i == 0 else "medium"
            
            # Make goals more specific based on weak areas
            if weak_areas and any(wa["area"].lower() in goal.lower() for wa in weak_areas):
                priority = "high"
                description = f"Focus on improving {goal} - identified as a weak area"
            else:
                description = f"Work towards achieving: {goal}"
            
            goals.append(StudyGoal(
                title=goal,
                description=description,
                target_date=datetime.utcnow() + timedelta(weeks=target_weeks),
                priority=priority,
                measurable_outcome=self._create_measurable_outcome(goal, weak_areas)
            ))
        
        # Add goals for top weak areas if not already covered
        for weak_area in weak_areas[:2]:  # Top 2 weak areas
            area_name = weak_area["area"]
            if not any(area_name.lower() in goal.lower() for goal in user_goals):
                goals.append(StudyGoal(
                    title=f"Improve {area_name}",
                    description=f"Address weakness in {area_name} (current performance: {weak_area.get('average_score', 0):.1%})",
                    target_date=datetime.utcnow() + timedelta(weeks=target_weeks),
                    priority="high" if weak_area.get("severity") == "high" else "medium",
                    measurable_outcome=f"Achieve 80%+ accuracy in {area_name} exercises"
                ))
        
        return goals
    
    def _create_measurable_outcome(self, goal: str, weak_areas: List[Dict[str, Any]]) -> str:
        """Create a measurable outcome for a goal."""
        goal_lower = goal.lower()
        
        if "score" in goal_lower or "grade" in goal_lower:
            return f"Achieve target score/grade in {goal}"
        elif "improve" in goal_lower:
            return f"Show measurable improvement in {goal}"
        elif any(wa["area"].lower() in goal_lower for wa in weak_areas):
            return f"Reach 80%+ proficiency in {goal}"
        else:
            return f"Complete all tasks related to {goal}"
    
    async def _generate_personalized_weekly_tasks(
        self,
        user_id: UUID,
        goals: List[str],
        weak_areas: List[Dict[str, Any]],
        mastery_levels: Dict[str, float],
        learning_patterns: Dict[str, Any],
        available_time_per_day: int,
        target_weeks: int,
        difficulty_level: str
    ) -> Dict[str, List[StudyTask]]:
        """Generate personalized weekly tasks."""
        from datetime import datetime, timedelta
        from app.schemas.ai_agent import StudyTask
        
        weekly_tasks = {}
        
        # Determine optimal study schedule based on patterns
        peak_time = learning_patterns.get("peak_performance_time", "morning")
        consistency = learning_patterns.get("consistency", 0.5)
        
        # Adjust task frequency based on consistency
        days_per_week = 5 if consistency > 0.7 else 4 if consistency > 0.5 else 3
        
        for week in range(1, target_weeks + 1):
            week_key = f"week_{week}"
            tasks = []
            
            # Distribute time across different focus areas
            focus_areas = self._determine_weekly_focus(week, target_weeks, weak_areas, goals)
            
            for day in range(1, days_per_week + 1):
                # Determine focus for this day
                day_focus = focus_areas[day % len(focus_areas)]
                
                # Adjust task time based on day and user patterns
                base_time = available_time_per_day
                if peak_time == "morning" and day <= 3:  # Front-load for morning people
                    task_time = min(base_time + 10, 90)
                elif peak_time == "evening" and day >= 3:  # Back-load for evening people
                    task_time = min(base_time + 10, 90)
                else:
                    task_time = base_time
                
                # Create task based on focus area
                task = self._create_focused_task(
                    day_focus, week, day, task_time, difficulty_level, weak_areas, mastery_levels
                )
                
                tasks.append(task)
            
            weekly_tasks[week_key] = tasks
        
        return weekly_tasks
    
    def _determine_weekly_focus(
        self,
        week: int,
        total_weeks: int,
        weak_areas: List[Dict[str, Any]],
        goals: List[str]
    ) -> List[str]:
        """Determine focus areas for each week."""
        focus_areas = []
        
        # Early weeks: focus on weak areas
        if week <= total_weeks // 2:
            focus_areas.extend([wa["area"] for wa in weak_areas[:2]])
        
        # Later weeks: focus on goals and review
        if week > total_weeks // 2:
            focus_areas.extend(goals[:2])
            focus_areas.append("Review and Practice")
        
        # Always include some variety
        if "Practice Problems" not in focus_areas:
            focus_areas.append("Practice Problems")
        
        return focus_areas if focus_areas else ["General Study"]
    
    def _create_focused_task(
        self,
        focus_area: str,
        week: int,
        day: int,
        time_minutes: int,
        difficulty_level: str,
        weak_areas: List[Dict[str, Any]],
        mastery_levels: Dict[str, float]
    ) -> StudyTask:
        """Create a task focused on a specific area."""
        from datetime import datetime, timedelta
        from app.schemas.ai_agent import StudyTask
        
        # Task templates based on focus area
        task_templates = {
            "Quadratic Equations": {
                "title": "Quadratic Equations Practice",
                "description": "Practice solving quadratic equations using various methods",
                "resources": ["Quadratic Formula Reference", "Factoring Guide", "Practice Problems Set"]
            },
            "Geometry Proofs": {
                "title": "Geometry Proof Practice",
                "description": "Work on geometric proof techniques and logical reasoning",
                "resources": ["Proof Templates", "Geometry Theorem List", "Practice Proofs"]
            },
            "Linear Equations": {
                "title": "Linear Equations Review",
                "description": "Review and practice linear equation solving techniques",
                "resources": ["Linear Algebra Basics", "Graphing Tools", "Word Problems"]
            },
            "Practice Problems": {
                "title": "Mixed Practice Session",
                "description": "Work on a variety of problems to reinforce learning",
                "resources": ["Problem Sets", "Previous Assignments", "Online Practice"]
            },
            "Review and Practice": {
                "title": "Review Session",
                "description": "Review previous topics and consolidate learning",
                "resources": ["Study Notes", "Summary Sheets", "Practice Tests"]
            }
        }
        
        # Get template or create generic one
        template = task_templates.get(focus_area, {
            "title": f"{focus_area} Study Session",
            "description": f"Focus on {focus_area} concepts and practice",
            "resources": ["Textbook", "Online Resources", "Practice Materials"]
        })
        
        # Adjust difficulty based on mastery level
        mastery = mastery_levels.get(focus_area, 0.5)
        if mastery > 0.8:
            adjusted_difficulty = "advanced"
            template["description"] += " - Advanced level exercises"
        elif mastery < 0.4:
            adjusted_difficulty = "beginner"
            template["description"] += " - Focus on fundamentals"
        else:
            adjusted_difficulty = difficulty_level
        
        return StudyTask(
            title=f"Week {week}, Day {day}: {template['title']}",
            description=template["description"],
            estimated_time_minutes=time_minutes,
            difficulty_level=adjusted_difficulty,
            resources=template["resources"],
            due_date=datetime.utcnow() + timedelta(weeks=week-1, days=day)
        )
    
    def _generate_plan_name(self, goals: List[str], user_name: str) -> str:
        """Generate a personalized plan name."""
        from datetime import datetime
        
        if goals:
            main_goal = goals[0][:20] + "..." if len(goals[0]) > 20 else goals[0]
            return f"{user_name}'s {main_goal} Plan - {datetime.utcnow().strftime('%B %Y')}"
        else:
            return f"{user_name}'s Study Plan - {datetime.utcnow().strftime('%B %Y')}"
    
    async def _get_ai_analysis(self, messages: List[BaseMessage]) -> str:
        """Get AI analysis using the LLM."""
        try:
            # Convert messages to the format expected by the LLM
            formatted_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    formatted_messages.append(msg)
            
            # Get response from LLM
            response = await self.llm.ainvoke(formatted_messages)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error(f"Error getting AI analysis: {str(e)}")
            return "Unable to generate AI analysis at this time."