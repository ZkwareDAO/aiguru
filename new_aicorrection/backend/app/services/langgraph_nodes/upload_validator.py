"""UploadValidator node for LangGraph grading workflow."""

import logging
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Submission
from app.services.langgraph_state import GraphState, update_state_progress, mark_node_complete, mark_node_error
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class UploadValidator:
    """
    Validates uploaded files and initializes grading task.
    
    Responsibilities:
    - Validate file existence and formats
    - Check file sizes and types
    - Create initial database records
    - Generate task metadata
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize UploadValidator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        self.supported_doc_formats = {'.pdf', '.doc', '.docx', '.txt'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    async def __call__(self, state: GraphState) -> GraphState:
        """
        Execute upload validation.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Starting upload validation for task {state['task_id']}")
            
            # Update progress
            state = update_state_progress(
                state,
                phase="upload_validation",
                progress=5,
                message="开始验证上传文件..."
            )
            
            # Validate files
            validation_result = await self._validate_files(state)
            
            if not validation_result["valid"]:
                error_msg = validation_result.get("error", "文件验证失败")
                logger.error(f"File validation failed: {error_msg}")
                return mark_node_error(state, "upload_validator", error_msg)
            
            # Create database record
            grading_task = await self._create_grading_task(state)
            
            # Update state with task info
            state["task_id"] = str(grading_task.id)
            state["status"] = "processing"
            state["started_at"] = datetime.now()
            
            # Update progress
            state = update_state_progress(
                state,
                phase="upload_validation",
                progress=10,
                message="文件验证完成，任务已创建"
            )
            
            # Mark node as complete
            state = mark_node_complete(
                state,
                "upload_validator",
                {
                    "task_id": state["task_id"],
                    "files_validated": validation_result["file_count"],
                    "total_size": validation_result["total_size"]
                }
            )
            
            logger.info(f"Upload validation completed for task {state['task_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Upload validation error: {str(e)}", exc_info=True)
            return mark_node_error(state, "upload_validator", f"上传验证失败: {str(e)}")
    
    async def _validate_files(self, state: GraphState) -> Dict[str, Any]:
        """
        Validate all uploaded files.
        
        Args:
            state: Current graph state
            
        Returns:
            Validation result dictionary
        """
        try:
            all_files = []
            all_files.extend(state.get("question_files", []))
            all_files.extend(state.get("answer_files", []))
            all_files.extend(state.get("marking_scheme_files", []))
            
            if not all_files:
                return {
                    "valid": False,
                    "error": "没有提供任何文件"
                }
            
            # Must have at least answer files
            if not state.get("answer_files"):
                return {
                    "valid": False,
                    "error": "必须提供学生答案文件"
                }
            
            total_size = 0
            validated_files = []
            
            for file_path in all_files:
                # Check file exists
                path = Path(file_path)
                if not path.exists():
                    return {
                        "valid": False,
                        "error": f"文件不存在: {file_path}"
                    }
                
                # Check file size
                file_size = path.stat().st_size
                if file_size > self.max_file_size:
                    return {
                        "valid": False,
                        "error": f"文件过大 ({file_size / 1024 / 1024:.2f}MB): {path.name}"
                    }
                
                total_size += file_size
                
                # Check file format
                file_ext = path.suffix.lower()
                if file_ext not in self.supported_image_formats and file_ext not in self.supported_doc_formats:
                    return {
                        "valid": False,
                        "error": f"不支持的文件格式: {file_ext}"
                    }
                
                validated_files.append({
                    "path": file_path,
                    "name": path.name,
                    "size": file_size,
                    "format": file_ext
                })
            
            return {
                "valid": True,
                "file_count": len(validated_files),
                "total_size": total_size,
                "files": validated_files
            }
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}", exc_info=True)
            return {
                "valid": False,
                "error": f"文件验证异常: {str(e)}"
            }
    
    async def _create_grading_task(self, state: GraphState) -> GradingTask:
        """
        Create grading task in database.
        
        Args:
            state: Current graph state
            
        Returns:
            Created GradingTask instance
        """
        try:
            # Create grading task
            grading_task = GradingTask(
                submission_id=state.get("submission_id"),
                task_type=state.get("task_type", "auto_grade"),
                status=GradingTaskStatus.PROCESSING,
                progress=10,
                ai_model="gemini-2.0-flash-exp",  # Default model
                prompt_template="intelligent_grading",
                max_retries=3,
                retry_count=0,
                started_at=datetime.now()
            )
            
            self.db.add(grading_task)
            await self.db.commit()
            await self.db.refresh(grading_task)
            
            logger.info(f"Created grading task: {grading_task.id}")
            return grading_task
            
        except Exception as e:
            logger.error(f"Failed to create grading task: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise ValidationError(f"创建批改任务失败: {str(e)}")
    
    async def _update_submission_status(self, submission_id: str):
        """
        Update submission status to grading.
        
        Args:
            submission_id: Submission ID
        """
        try:
            from app.models.assignment import SubmissionStatus
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()
            
            if submission:
                submission.status = SubmissionStatus.GRADING
                await self.db.commit()
                logger.info(f"Updated submission {submission_id} status to GRADING")
                
        except Exception as e:
            logger.error(f"Failed to update submission status: {str(e)}", exc_info=True)
            # Don't fail the whole process if this fails
            await self.db.rollback()


def create_upload_validator_node(db: AsyncSession):
    """
    Factory function to create UploadValidator node.
    
    Args:
        db: Database session
        
    Returns:
        UploadValidator instance
    """
    return UploadValidator(db)

