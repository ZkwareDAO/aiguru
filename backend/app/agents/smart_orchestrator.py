"""Smart Orchestrator - 智能编排器 (Phase 2 Enhanced)."""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from uuid import UUID

from langgraph.graph import StateGraph, END

from app.agents.state import GradingState
from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.preprocess_agent import PreprocessAgent
from app.agents.question_segmentation_agent import QuestionSegmentationAgent
from app.agents.location_annotation_agent import LocationAnnotationAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class SmartOrchestrator:
    """智能编排器 (Phase 2 Enhanced)

    核心功能:
    - Phase 2 Multi-Agent协作流程
    - 题目分段识别 (QuestionSegmentationAgent)
    - 批改识别 (UnifiedGradingAgent)
    - 精确位置标注 (LocationAnnotationAgent)
    - 集成智能缓存
    - 实时进度回调

    工作流:
    用户上传作业
      ↓
    [Agent 1] QuestionSegmentationAgent - 题目分段
      ↓
    [Agent 2] UnifiedGradingAgent - 批改识别
      ↓
    [Agent 3] LocationAnnotationAgent - 精确位置标注
      ↓
    返回完整批改结果

    成本优化:
    - 题目分段: 免费 (Mock OCR) 或 $0.001/页
    - 批改识别: $0.000043/题
    - 位置标注: $0.000001/题
    - 总成本: ~$0.010660 (10页15题)
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """初始化编排器

        Args:
            progress_callback: 进度回调函数 (可选)
        """
        self.unified_agent = UnifiedGradingAgent()
        self.preprocess_agent = PreprocessAgent()
        self.segmentation_agent = QuestionSegmentationAgent(use_paddle_ocr=False)
        self.location_agent = LocationAnnotationAgent()
        self.complexity_assessor = ComplexityAssessor()
        self.cache_service = CacheService()
        self.progress_callback = progress_callback

        self.workflow = self._build_workflow()

        logger.info("SmartOrchestrator (Phase 2) initialized")
    
    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流 (Phase 2)

        工作流:
        check_cache → preprocess → segment_questions → grade_questions → annotate_locations → finalize
        """
        workflow = StateGraph(GradingState)

        # 添加节点
        workflow.add_node("check_cache", self._check_cache)
        workflow.add_node("preprocess", self._preprocess_step)
        workflow.add_node("segment_questions", self._segment_questions_step)
        workflow.add_node("assess_complexity", self._assess_complexity_step)
        workflow.add_node("grade_questions", self._grade_questions_step)
        workflow.add_node("annotate_locations", self._annotate_locations_step)
        workflow.add_node("finalize", self._finalize_step)

        # 定义流程
        workflow.set_entry_point("check_cache")

        # 缓存检查后的条件分支
        workflow.add_conditional_edges(
            "check_cache",
            self._should_use_cache,
            {
                "use_cache": "finalize",  # 缓存命中,直接完成
                "process": "preprocess"    # 缓存未命中,继续处理
            }
        )

        # Phase 2 工作流:
        # preprocess → segment_questions → assess_complexity → grade_questions → annotate_locations → finalize
        workflow.add_edge("preprocess", "segment_questions")
        workflow.add_edge("segment_questions", "assess_complexity")
        workflow.add_edge("assess_complexity", "grade_questions")
        workflow.add_edge("grade_questions", "annotate_locations")
        workflow.add_edge("annotate_locations", "finalize")

        # 完成后结束
        workflow.add_edge("finalize", END)

        return workflow.compile()
    
    async def execute(self, input_data: Dict) -> Dict:
        """执行批改流程
        
        Args:
            input_data: 输入数据,包含:
                - submission_id: 提交ID
                - assignment_id: 作业ID
                - mode: 批改模式 (可选)
                - config: 配置信息
                
        Returns:
            批改结果
        """
        try:
            logger.info(f"SmartOrchestrator executing for submission {input_data.get('submission_id')}")
            
            # 初始化状态
            initial_state = self._create_initial_state(input_data)
            
            # 执行工作流
            result = await self.workflow.ainvoke(initial_state)
            
            # 转换为输出格式
            output = self._format_output(result)
            
            logger.info(
                f"Execution completed: status={result['status']}, "
                f"score={result.get('score')}, "
                f"from_cache={result.get('from_cache', False)}, "
                f"time={result.get('processing_time_ms')}ms"
            )
            
            return output
            
        except Exception as e:
            logger.error(f"SmartOrchestrator execution failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "submission_id": input_data.get("submission_id"),
            }
    
    def _create_initial_state(self, input_data: Dict) -> GradingState:
        """创建初始状态"""
        return GradingState(
            submission_id=input_data["submission_id"],
            assignment_id=input_data["assignment_id"],
            status="pending",
            grading_mode=input_data.get("mode", "fast"),
            config=input_data.get("config", {}),
            max_score=input_data.get("max_score", 100.0),
            preprocessed_files=[],
            extracted_text="",
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=datetime.utcnow(),
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )
    
    async def _check_cache(self, state: GradingState) -> GradingState:
        """检查缓存"""
        try:
            # 如果已经有提取的文本,检查缓存
            if state.get("extracted_text"):
                cached_result = await self.cache_service.get_similar(
                    state["extracted_text"]
                )
                
                if cached_result:
                    logger.info("Cache hit!")
                    # 更新状态
                    state.update(cached_result)
                    state["from_cache"] = True
                    state["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            # 缓存失败不影响主流程
        
        return state
    
    def _should_use_cache(self, state: GradingState) -> str:
        """判断是否使用缓存"""
        return "use_cache" if state.get("from_cache") else "process"
    
    async def _preprocess_step(self, state: GradingState) -> GradingState:
        """预处理步骤"""
        await self._report_progress(state, "preprocessing", 10)
        return await self.preprocess_agent.process(state)

    async def _segment_questions_step(self, state: GradingState) -> GradingState:
        """题目分段步骤 (Phase 2 Agent 1)"""
        try:
            await self._report_progress(state, "segmenting_questions", 30)
            logger.info(f"Segmenting questions for submission {state['submission_id']}")

            # 获取图片URL列表
            images = self._extract_image_urls(state)

            if not images:
                logger.warning("No images found, skipping segmentation")
                state["question_segments"] = []
                return state

            # 调用QuestionSegmentationAgent
            state["images"] = images
            segments = await self.segmentation_agent.segment_questions(images)
            state["question_segments"] = segments

            logger.info(f"Segmentation completed: {len(segments)} questions found")

            return state

        except Exception as e:
            logger.error(f"Question segmentation failed: {e}", exc_info=True)
            # 兜底: 创建单个分段
            state["question_segments"] = []
            return state
    
    async def _assess_complexity_step(self, state: GradingState) -> GradingState:
        """评估复杂度"""
        try:
            complexity = self.complexity_assessor.assess(state)
            state["config"]["complexity"] = complexity
            
            # 如果用户没有指定模式,使用推荐模式
            if not state.get("grading_mode") or state["grading_mode"] == "auto":
                recommended_mode = self.complexity_assessor.get_recommended_mode(complexity)
                state["grading_mode"] = recommended_mode
                logger.info(f"Using recommended mode: {recommended_mode} for complexity: {complexity}")
            
        except Exception as e:
            logger.error(f"Complexity assessment failed: {e}")
            # 失败时使用默认模式
            state["config"]["complexity"] = "medium"
        
        return state
    
    async def _grade_questions_step(self, state: GradingState) -> GradingState:
        """批改题目步骤 (Phase 2 Agent 2)"""
        try:
            await self._report_progress(state, "grading_questions", 50)
            logger.info(f"Grading questions for submission {state['submission_id']}")

            question_segments = state.get("question_segments", [])

            if not question_segments:
                # 兜底: 使用原有的unified grading
                logger.warning("No question segments, using unified grading")
                return await self.unified_agent.process(state)

            # 批改每个题目
            grading_results = []

            for i, segment in enumerate(question_segments):
                try:
                    # 为每个题目创建临时状态
                    question_state = self._create_question_state(state, segment)

                    # 调用UnifiedGradingAgent
                    graded_state = await self.unified_agent.process(question_state)

                    # 提取批改结果
                    result = self._extract_grading_result(graded_state, segment)
                    grading_results.append(result)

                    # 报告进度
                    progress = 50 + int((i + 1) / len(question_segments) * 20)
                    await self._report_progress(state, f"grading_question_{i+1}", progress)

                except Exception as e:
                    logger.error(f"Failed to grade question {i}: {e}")
                    # 添加错误结果
                    grading_results.append(self._create_error_result(segment, str(e)))

            state["grading_results"] = grading_results

            # 计算总分
            total_score = sum(r["score"] for r in grading_results)
            state["score"] = total_score

            logger.info(f"Grading completed: {len(grading_results)} questions, score={total_score}")

            return state

        except Exception as e:
            logger.error(f"Question grading failed: {e}", exc_info=True)
            state["status"] = "failed"
            state["error_message"] = f"批改失败: {str(e)}"
            return state

    async def _annotate_locations_step(self, state: GradingState) -> GradingState:
        """位置标注步骤 (Phase 2 Agent 3)"""
        try:
            await self._report_progress(state, "annotating_locations", 70)
            logger.info(f"Annotating locations for submission {state['submission_id']}")

            grading_results = state.get("grading_results", [])
            images = state.get("images", [])

            if not grading_results or not images:
                logger.warning("No grading results or images, skipping annotation")
                state["annotated_results"] = grading_results
                return state

            # 为每个题目的错误标注位置
            annotated_results = []

            for i, result in enumerate(grading_results):
                try:
                    # 获取题目对应的图片
                    page_index = result.get("page_index", 0)
                    if page_index >= len(images):
                        logger.warning(f"Page index {page_index} out of range")
                        annotated_results.append(result)
                        continue

                    image_url = images[page_index]

                    # 标注每个错误的位置
                    errors = result.get("errors", [])
                    if errors:
                        annotated_errors = await self._annotate_errors(
                            image_url,
                            result["bbox"],
                            errors
                        )
                        result["errors"] = annotated_errors

                    annotated_results.append(result)

                    # 报告进度
                    progress = 70 + int((i + 1) / len(grading_results) * 20)
                    await self._report_progress(state, f"annotating_question_{i+1}", progress)

                except Exception as e:
                    logger.error(f"Failed to annotate question {i}: {e}")
                    annotated_results.append(result)

            state["annotated_results"] = annotated_results
            state["status"] = "completed"

            logger.info(f"Annotation completed: {len(annotated_results)} questions")

            return state

        except Exception as e:
            logger.error(f"Location annotation failed: {e}", exc_info=True)
            # 不影响主流程,使用未标注的结果
            state["annotated_results"] = state.get("grading_results", [])
            state["status"] = "completed"
            return state
    
    async def _finalize_step(self, state: GradingState) -> GradingState:
        """完成步骤"""
        try:
            # 记录结束时间
            state["processing_end_time"] = datetime.utcnow()
            
            # 计算处理时间
            if state["processing_start_time"] and state["processing_end_time"]:
                processing_time = (
                    state["processing_end_time"] - state["processing_start_time"]
                ).total_seconds() * 1000
                state["processing_time_ms"] = int(processing_time)
            
            # 如果不是从缓存获取的,存储到缓存
            if not state.get("from_cache") and state["status"] == "completed":
                await self.cache_service.store(state)
            
            logger.info(f"Finalized: time={state.get('processing_time_ms')}ms")
            
        except Exception as e:
            logger.error(f"Finalization failed: {e}")
        
        return state
    
    def _format_output(self, state: GradingState) -> Dict:
        """格式化输出 (Phase 2)"""
        return {
            "submission_id": str(state["submission_id"]),
            "assignment_id": str(state["assignment_id"]),
            "status": state["status"],
            "score": state.get("score"),
            "max_score": state["max_score"],
            "confidence": state.get("confidence"),

            # Phase 2: 题目级别的结果
            "question_segments": state.get("question_segments", []),
            "grading_results": state.get("grading_results", []),
            "annotated_results": state.get("annotated_results", []),

            # 兼容旧格式
            "errors": state.get("errors", []),
            "annotations": state.get("annotations", []),
            "feedback_text": state.get("feedback_text", ""),
            "suggestions": state.get("suggestions", []),
            "knowledge_points": state.get("knowledge_points", []),

            "grading_mode": state["grading_mode"],
            "complexity": state["config"].get("complexity"),
            "processing_time_ms": state.get("processing_time_ms"),
            "from_cache": state.get("from_cache", False),
            "error_message": state.get("error_message"),
        }

    # ========== Phase 2 辅助方法 ==========

    def _extract_image_urls(self, state: GradingState) -> list[str]:
        """从状态中提取图片URL列表"""
        images = []

        for file in state.get("preprocessed_files", []):
            if file.get("type") == "image":
                # 假设file_path就是URL或可以转换为URL
                images.append(file.get("file_path", ""))

        return images

    def _create_question_state(self, state: GradingState, segment: Dict) -> GradingState:
        """为单个题目创建临时状态"""
        question_state = GradingState(
            submission_id=state["submission_id"],
            assignment_id=state["assignment_id"],
            status="grading",
            grading_mode=state["grading_mode"],
            config=state["config"],
            max_score=segment.get("max_score", 10.0),  # 默认10分
            preprocessed_files=[],
            extracted_text=segment.get("ocr_text", ""),
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=state["processing_start_time"],
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )

        return question_state

    def _extract_grading_result(self, graded_state: GradingState, segment: Dict) -> Dict:
        """从批改状态中提取结果"""
        from app.agents.state import QuestionGrading

        return QuestionGrading(
            question_index=segment["question_index"],
            question_number=segment["question_number"],
            page_index=segment["page_index"],
            bbox=segment["bbox"],
            score=graded_state.get("score", 0.0),
            max_score=graded_state["max_score"],
            status=self._determine_status(graded_state),
            errors=graded_state.get("errors", []),
            correct_parts=graded_state.get("annotations", []),
            warnings=[],
            feedback=graded_state.get("feedback_text", "")
        )

    def _determine_status(self, state: GradingState) -> str:
        """判断题目状态"""
        score = state.get("score", 0.0)
        max_score = state["max_score"]

        if score >= max_score * 0.9:
            return "correct"
        elif score >= max_score * 0.5:
            return "warning"
        else:
            return "error"

    def _create_error_result(self, segment: Dict, error_message: str) -> Dict:
        """创建错误结果"""
        from app.agents.state import QuestionGrading

        return QuestionGrading(
            question_index=segment["question_index"],
            question_number=segment["question_number"],
            page_index=segment["page_index"],
            bbox=segment["bbox"],
            score=0.0,
            max_score=10.0,
            status="error",
            errors=[{"type": "系统错误", "description": error_message}],
            correct_parts=[],
            warnings=[],
            feedback=f"批改失败: {error_message}"
        )

    async def _annotate_errors(
        self,
        image_url: str,
        question_bbox: Dict,
        errors: list[Dict]
    ) -> list[Dict]:
        """为错误列表标注位置"""
        annotated_errors = []

        # 假设图片尺寸 (实际应该从图片获取)
        image_width = 800
        image_height = 1200

        for error in errors:
            try:
                # 调用LocationAnnotationAgent
                location = await self.location_agent.annotate(
                    image_url=image_url,
                    image_width=image_width,
                    image_height=image_height,
                    question_bbox=question_bbox,
                    error=error
                )

                # 添加位置信息到错误
                error["location"] = location
                annotated_errors.append(error)

            except Exception as e:
                logger.error(f"Failed to annotate error: {e}")
                # 不添加位置信息
                annotated_errors.append(error)

        return annotated_errors

    async def _report_progress(self, state: GradingState, step: str, progress: int):
        """报告进度"""
        if self.progress_callback:
            try:
                await self.progress_callback({
                    "submission_id": str(state["submission_id"]),
                    "step": step,
                    "progress": progress,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")

