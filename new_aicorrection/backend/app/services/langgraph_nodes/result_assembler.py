"""ResultAssembler node for LangGraph grading workflow."""

import logging
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error
from app.models.ai import GradingTask, GradingTaskStatus

logger = logging.getLogger(__name__)


class ResultAssembler:
    """
    Assembles final grading results and stores them.
    
    Responsibilities:
    - Compile all grading data
    - Generate result JSON
    - Store results in database
    - Upload to object storage (optional)
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ResultAssembler.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute result assembly.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Starting result assembly for task {state['task_id']}")
            
            # Update progress
            state = update_state_progress(
                state,
                phase="result_assembly",
                progress=80,
                message="正在汇总批改结果..."
            )
            
            # Assemble complete result
            complete_result = self._assemble_result(state)
            state["result"] = complete_result
            
            # Save to database
            await self._save_to_database(state, complete_result)
            
            # Update progress
            state = update_state_progress(
                state,
                phase="result_assembly",
                progress=90,
                message="批改结果已保存"
            )
            
            # Mark as complete
            state["status"] = "completed"
            state["completed_at"] = datetime.now()
            
            # Mark node as complete
            state = mark_node_complete(
                state,
                "result_assembler",
                {
                    "result_size": len(json.dumps(complete_result)),
                    "total_score": state.get("total_score", 0),
                    "saved_to_db": True
                }
            )
            
            logger.info(f"Result assembly completed for task {state['task_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Result assembly error: {str(e)}", exc_info=True)
            return mark_node_error(state, "result_assembler", f"结果汇总失败: {str(e)}")
    
    def _assemble_result(self, state: GraphState) -> Dict[str, Any]:
        """
        Assemble complete grading result.
        
        Args:
            state: Current graph state
            
        Returns:
            Complete result dictionary
        """
        result = {
            "task_id": state["task_id"],
            "submission_id": state.get("submission_id"),
            "assignment_id": state.get("assignment_id"),
            "user_id": state.get("user_id"),
            
            # Grading results
            "scores": state.get("scores", {}),
            "total_score": state.get("total_score", 0),
            "max_score": state.get("max_score", 100),
            "percentage": state.get("percentage", 0.0),
            "grade_level": state.get("grade_level", ""),
            
            # Feedback
            "detailed_feedback": state.get("result_text", ""),
            "strengths": state.get("strengths", []),
            "suggestions": state.get("suggestions", []),
            
            # Knowledge analysis
            "knowledge_points": state.get("knowledge_points", []),
            "weak_areas": state.get("weak_areas", []),
            "learning_insights": state.get("learning_insights", {}),
            
            # Annotations
            "annotations": state.get("annotations", []),
            "cropped_regions": state.get("cropped_regions", []),
            
            # Metadata
            "rubric": state.get("rubric", {}),
            "grading_criteria": state.get("grading_criteria", []),
            "strictness_level": state.get("strictness_level", "中等"),
            "language": state.get("language", "zh"),
            
            # Timestamps
            "created_at": state.get("created_at").isoformat() if state.get("created_at") else None,
            "started_at": state.get("started_at").isoformat() if state.get("started_at") else None,
            "completed_at": datetime.now().isoformat(),
            
            # Processing info
            "events": state.get("events", []),
            "processing_phases": [
                event.get("node_name") for event in state.get("events", [])
                if event.get("event_type") == "node_complete"
            ]
        }
        
        return result
    
    async def _save_to_database(self, state: GraphState, result: Dict[str, Any]):
        """
        Save result to database.
        
        Args:
            state: Current graph state
            result: Complete result dictionary
        """
        try:
            from sqlalchemy import select
            
            # Get grading task
            task_result = await self.db.execute(
                select(GradingTask).where(GradingTask.id == state["task_id"])
            )
            grading_task = task_result.scalar_one_or_none()
            
            if grading_task:
                # Update grading task
                grading_task.status = GradingTaskStatus.COMPLETED
                grading_task.progress = 100
                grading_task.result = result
                grading_task.score = state.get("total_score", 0)
                grading_task.feedback = state.get("result_text", "")
                grading_task.completed_at = datetime.now()
                
                await self.db.commit()
                logger.info(f"Saved result to database for task {state['task_id']}")
            else:
                logger.warning(f"Grading task not found: {state['task_id']}")
                
        except Exception as e:
            logger.error(f"Failed to save to database: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise


def create_result_assembler_node(db: AsyncSession):
    """
    Factory function to create ResultAssembler node.
    
    Args:
        db: Database session
        
    Returns:
        ResultAssembler instance
    """
    return ResultAssembler(db)

