"""LangGraph-based AI grading workflow."""

import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from uuid import uuid4

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.langgraph_state import (
    GraphState,
    create_initial_state,
    update_state_progress,
    GradingEvent
)
from app.services.langgraph_nodes import (
    create_upload_validator_node,
    create_document_ingestor_node,
    create_rubric_interpreter_node,
    create_scoring_agent_node
)
from app.services.langgraph_nodes.result_assembler import create_result_assembler_node

logger = logging.getLogger(__name__)


class LangGraphGradingWorkflow:
    """
    LangGraph-based grading workflow orchestrator.
    
    This class manages the complete AI grading pipeline using LangGraph,
    coordinating multiple specialized agents/nodes.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize LangGraph grading workflow.
        
        Args:
            db: Database session
        """
        self.db = db
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph state graph."""
        try:
            # Create state graph
            workflow = StateGraph(GraphState)
            
            # Create nodes
            upload_validator = create_upload_validator_node(self.db)
            document_ingestor = create_document_ingestor_node()
            rubric_interpreter = create_rubric_interpreter_node()
            scoring_agent = create_scoring_agent_node()
            result_assembler = create_result_assembler_node(self.db)
            
            # Add nodes to graph
            workflow.add_node("upload_validator", upload_validator)
            workflow.add_node("document_ingestor", document_ingestor)
            workflow.add_node("rubric_interpreter", rubric_interpreter)
            workflow.add_node("scoring_agent", scoring_agent)
            workflow.add_node("result_assembler", result_assembler)
            
            # Define edges (workflow sequence)
            workflow.set_entry_point("upload_validator")
            workflow.add_edge("upload_validator", "document_ingestor")
            workflow.add_edge("document_ingestor", "rubric_interpreter")
            workflow.add_edge("rubric_interpreter", "scoring_agent")
            workflow.add_edge("scoring_agent", "result_assembler")
            workflow.add_edge("result_assembler", END)
            
            # Compile graph with checkpointer
            self.graph = workflow.compile(checkpointer=self.checkpointer)
            
            logger.info("LangGraph workflow built successfully")
            
        except Exception as e:
            logger.error(f"Failed to build LangGraph workflow: {str(e)}", exc_info=True)
            raise
    
    async def execute(
        self,
        question_files: List[str],
        answer_files: List[str],
        marking_scheme_files: Optional[List[str]] = None,
        task_type: str = "auto",
        strictness_level: str = "中等",
        language: str = "zh",
        submission_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_score: int = 100
    ) -> Dict[str, Any]:
        """
        Execute grading workflow.
        
        Args:
            question_files: List of question file paths
            answer_files: List of answer file paths
            marking_scheme_files: Optional marking scheme file paths
            task_type: Type of grading task
            strictness_level: Grading strictness
            language: Language for grading
            submission_id: Optional submission ID
            assignment_id: Optional assignment ID
            user_id: Optional user ID
            subject: Optional subject
            difficulty: Optional difficulty level
            max_score: Maximum possible score
            
        Returns:
            Final grading result
        """
        try:
            # Generate task ID
            task_id = str(uuid4())
            
            logger.info(f"Starting LangGraph grading workflow for task {task_id}")
            
            # Create initial state
            initial_state = create_initial_state(
                task_id=task_id,
                question_files=question_files,
                answer_files=answer_files,
                marking_scheme_files=marking_scheme_files or [],
                task_type=task_type,
                strictness_level=strictness_level,
                language=language,
                submission_id=submission_id,
                assignment_id=assignment_id,
                user_id=user_id,
                subject=subject,
                difficulty=difficulty,
                max_score=max_score
            )
            
            # Execute graph
            config = {"configurable": {"thread_id": task_id}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            logger.info(f"LangGraph workflow completed for task {task_id}")
            
            return final_state.get("result", {})
            
        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}", exc_info=True)
            raise
    
    async def execute_stream(
        self,
        question_files: List[str],
        answer_files: List[str],
        marking_scheme_files: Optional[List[str]] = None,
        task_type: str = "auto",
        strictness_level: str = "中等",
        language: str = "zh",
        submission_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_score: int = 100
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute grading workflow with streaming events.
        
        Args:
            Same as execute()
            
        Yields:
            Progress events and final result
        """
        try:
            # Generate task ID
            task_id = str(uuid4())
            
            logger.info(f"Starting streaming LangGraph workflow for task {task_id}")
            
            # Create initial state
            initial_state = create_initial_state(
                task_id=task_id,
                question_files=question_files,
                answer_files=answer_files,
                marking_scheme_files=marking_scheme_files or [],
                task_type=task_type,
                strictness_level=strictness_level,
                language=language,
                submission_id=submission_id,
                assignment_id=assignment_id,
                user_id=user_id,
                subject=subject,
                difficulty=difficulty,
                max_score=max_score
            )
            
            # Execute graph with streaming
            config = {"configurable": {"thread_id": task_id}}
            
            async for event in self.graph.astream(initial_state, config):
                # Extract state from event
                if isinstance(event, dict):
                    for node_name, node_state in event.items():
                        if isinstance(node_state, dict):
                            # Yield progress event
                            yield {
                                "type": "progress",
                                "task_id": task_id,
                                "node": node_name,
                                "phase": node_state.get("current_phase", ""),
                                "progress": node_state.get("progress", 0),
                                "status": node_state.get("status", "processing"),
                                "message": f"Processing {node_name}..."
                            }
            
            # Get final state
            final_state = await self.graph.aget_state(config)
            
            # Yield final result
            yield {
                "type": "complete",
                "task_id": task_id,
                "result": final_state.values.get("result", {}),
                "status": "completed"
            }
            
            logger.info(f"Streaming workflow completed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Streaming workflow error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "task_id": task_id if 'task_id' in locals() else "unknown",
                "error": str(e),
                "status": "failed"
            }
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status information or None if not found
        """
        try:
            config = {"configurable": {"thread_id": task_id}}
            state = await self.graph.aget_state(config)
            
            if state and state.values:
                return {
                    "task_id": task_id,
                    "status": state.values.get("status", "unknown"),
                    "phase": state.values.get("current_phase", ""),
                    "progress": state.values.get("progress", 0),
                    "result": state.values.get("result"),
                    "error": state.values.get("error_message")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}", exc_info=True)
            return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            # Note: LangGraph doesn't have built-in cancellation
            # This would need to be implemented with custom logic
            logger.warning(f"Task cancellation not fully implemented for {task_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel task: {str(e)}", exc_info=True)
            return False


# Global workflow instance
_workflow_instance: Optional[LangGraphGradingWorkflow] = None


def get_langgraph_workflow(db: AsyncSession) -> LangGraphGradingWorkflow:
    """
    Get or create LangGraph workflow instance.
    
    Args:
        db: Database session
        
    Returns:
        LangGraphGradingWorkflow instance
    """
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = LangGraphGradingWorkflow(db)
    return _workflow_instance

