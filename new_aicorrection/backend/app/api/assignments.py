"""Assignment management API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    AssignmentNotFoundError,
    InsufficientPermissionError,
    SubmissionNotFoundError,
    ValidationError
)
from app.models.assignment import AssignmentStatus, SubmissionStatus
from app.models.user import User, UserRole
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentFileResponse,
    AssignmentResponse,
    AssignmentStats,
    AssignmentUpdate,
    AssignmentWithClass,
    SubmissionCreate,
    SubmissionFileResponse,
    SubmissionGrade,
    SubmissionResponse,
    SubmissionUpdate,
    SubmissionWithAssignment,
    SubmissionWithStudent
)
from app.services.assignment_service import AssignmentService
from app.services.file_service import FileService

router = APIRouter(prefix="/assignments", tags=["assignments"])


# Assignment CRUD endpoints

@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new assignment. Only teachers can create assignments."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create assignments"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.create_assignment(current_user.id, assignment_data)
        
        return AssignmentResponse(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            subject=assignment.subject,
            topic=assignment.topic,
            difficulty_level=assignment.difficulty_level,
            total_points=assignment.total_points,
            passing_score=assignment.passing_score,
            due_date=assignment.due_date,
            start_date=assignment.start_date,
            allow_late_submission=assignment.allow_late_submission,
            auto_grade=assignment.auto_grade,
            show_correct_answers=assignment.show_correct_answers,
            class_id=assignment.class_id,
            teacher_id=assignment.teacher_id,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            published_at=assignment.published_at,
            submission_count=len(assignment.submissions),
            is_overdue=assignment.is_overdue
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignment by ID."""
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.get_assignment_by_id(assignment_id, current_user.id)
        
        return AssignmentResponse(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            subject=assignment.subject,
            topic=assignment.topic,
            difficulty_level=assignment.difficulty_level,
            total_points=assignment.total_points,
            passing_score=assignment.passing_score,
            due_date=assignment.due_date,
            start_date=assignment.start_date,
            allow_late_submission=assignment.allow_late_submission,
            auto_grade=assignment.auto_grade,
            show_correct_answers=assignment.show_correct_answers,
            class_id=assignment.class_id,
            teacher_id=assignment.teacher_id,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            published_at=assignment.published_at,
            submission_count=len(assignment.submissions),
            is_overdue=assignment.is_overdue
        )
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    update_data: AssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update assignment. Only the assignment creator can update."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can update assignments"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.update_assignment(
            assignment_id, current_user.id, update_data
        )
        
        return AssignmentResponse(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            subject=assignment.subject,
            topic=assignment.topic,
            difficulty_level=assignment.difficulty_level,
            total_points=assignment.total_points,
            passing_score=assignment.passing_score,
            due_date=assignment.due_date,
            start_date=assignment.start_date,
            allow_late_submission=assignment.allow_late_submission,
            auto_grade=assignment.auto_grade,
            show_correct_answers=assignment.show_correct_answers,
            class_id=assignment.class_id,
            teacher_id=assignment.teacher_id,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            published_at=assignment.published_at,
            submission_count=len(assignment.submissions),
            is_overdue=assignment.is_overdue
        )
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete (archive) assignment. Only the assignment creator can delete."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete assignments"
        )
    
    try:
        assignment_service = AssignmentService(db)
        await assignment_service.delete_assignment(assignment_id, current_user.id)
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Assignment status management

@router.post("/{assignment_id}/publish", response_model=AssignmentResponse)
async def publish_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish an assignment to make it active."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can publish assignments"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.publish_assignment(assignment_id, current_user.id)
        
        return AssignmentResponse(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            subject=assignment.subject,
            topic=assignment.topic,
            difficulty_level=assignment.difficulty_level,
            total_points=assignment.total_points,
            passing_score=assignment.passing_score,
            due_date=assignment.due_date,
            start_date=assignment.start_date,
            allow_late_submission=assignment.allow_late_submission,
            auto_grade=assignment.auto_grade,
            show_correct_answers=assignment.show_correct_answers,
            class_id=assignment.class_id,
            teacher_id=assignment.teacher_id,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            published_at=assignment.published_at,
            submission_count=len(assignment.submissions),
            is_overdue=assignment.is_overdue
        )
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{assignment_id}/close", response_model=AssignmentResponse)
async def close_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Close an assignment to stop accepting submissions."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can close assignments"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.close_assignment(assignment_id, current_user.id)
        
        return AssignmentResponse(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            subject=assignment.subject,
            topic=assignment.topic,
            difficulty_level=assignment.difficulty_level,
            total_points=assignment.total_points,
            passing_score=assignment.passing_score,
            due_date=assignment.due_date,
            start_date=assignment.start_date,
            allow_late_submission=assignment.allow_late_submission,
            auto_grade=assignment.auto_grade,
            show_correct_answers=assignment.show_correct_answers,
            class_id=assignment.class_id,
            teacher_id=assignment.teacher_id,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            published_at=assignment.published_at,
            submission_count=len(assignment.submissions),
            is_overdue=assignment.is_overdue
        )
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Assignment listing endpoints

@router.get("/", response_model=List[AssignmentResponse])
async def get_user_assignments(
    class_id: Optional[UUID] = Query(None, description="Filter by class ID"),
    status: Optional[AssignmentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of assignments to return"),
    offset: int = Query(0, ge=0, description="Number of assignments to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignments for the current user."""
    try:
        assignment_service = AssignmentService(db)
        
        if current_user.role == UserRole.TEACHER:
            assignments = await assignment_service.get_teacher_assignments(
                current_user.id, class_id, status, limit, offset
            )
        elif current_user.role == UserRole.STUDENT:
            assignments = await assignment_service.get_student_assignments(
                current_user.id, class_id, status, limit, offset
            )
        else:
            # Parents will be handled later
            assignments = []
        
        return [
            AssignmentResponse(
                id=assignment.id,
                title=assignment.title,
                description=assignment.description,
                instructions=assignment.instructions,
                subject=assignment.subject,
                topic=assignment.topic,
                difficulty_level=assignment.difficulty_level,
                total_points=assignment.total_points,
                passing_score=assignment.passing_score,
                due_date=assignment.due_date,
                start_date=assignment.start_date,
                allow_late_submission=assignment.allow_late_submission,
                auto_grade=assignment.auto_grade,
                show_correct_answers=assignment.show_correct_answers,
                class_id=assignment.class_id,
                teacher_id=assignment.teacher_id,
                status=assignment.status,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
                published_at=assignment.published_at,
                submission_count=len(assignment.submissions) if hasattr(assignment, 'submissions') else 0,
                is_overdue=assignment.is_overdue
            )
            for assignment in assignments
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/class/{class_id}", response_model=List[AssignmentResponse])
async def get_class_assignments(
    class_id: UUID,
    status: Optional[AssignmentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of assignments to return"),
    offset: int = Query(0, ge=0, description="Number of assignments to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignments for a specific class."""
    try:
        assignment_service = AssignmentService(db)
        assignments = await assignment_service.get_class_assignments(
            class_id, current_user.id, status, limit, offset
        )
        
        return [
            AssignmentResponse(
                id=assignment.id,
                title=assignment.title,
                description=assignment.description,
                instructions=assignment.instructions,
                subject=assignment.subject,
                topic=assignment.topic,
                difficulty_level=assignment.difficulty_level,
                total_points=assignment.total_points,
                passing_score=assignment.passing_score,
                due_date=assignment.due_date,
                start_date=assignment.start_date,
                allow_late_submission=assignment.allow_late_submission,
                auto_grade=assignment.auto_grade,
                show_correct_answers=assignment.show_correct_answers,
                class_id=assignment.class_id,
                teacher_id=assignment.teacher_id,
                status=assignment.status,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
                published_at=assignment.published_at,
                submission_count=len(assignment.submissions) if hasattr(assignment, 'submissions') else 0,
                is_overdue=assignment.is_overdue
            )
            for assignment in assignments
        ]
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Assignment statistics

@router.get("/{assignment_id}/stats", response_model=AssignmentStats)
async def get_assignment_stats(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignment statistics."""
    try:
        assignment_service = AssignmentService(db)
        stats = await assignment_service.get_assignment_stats(assignment_id, current_user.id)
        return stats
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Submission endpoints

@router.post("/{assignment_id}/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    assignment_id: UUID,
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new submission for an assignment. Only students can submit."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can create submissions"
        )
    
    # Override assignment_id from URL
    submission_data.assignment_id = assignment_id
    
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.create_submission(current_user.id, submission_data)
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{assignment_id}/submissions", response_model=List[SubmissionWithStudent])
async def get_assignment_submissions(
    assignment_id: UUID,
    status: Optional[SubmissionStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all submissions for an assignment. Only teachers can view all submissions."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view assignment submissions"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.get_assignment_by_id(assignment_id, current_user.id)
        
        # Filter submissions by status if provided
        submissions = assignment.submissions
        if status:
            submissions = [s for s in submissions if s.status == status]
        
        return [
            SubmissionWithStudent(
                id=submission.id,
                assignment_id=submission.assignment_id,
                student_id=submission.student_id,
                content=submission.content,
                notes=submission.notes,
                status=submission.status,
                score=submission.score,
                max_score=submission.max_score,
                feedback=submission.feedback,
                teacher_comments=submission.teacher_comments,
                ai_feedback=submission.ai_feedback,
                submitted_at=submission.submitted_at,
                graded_at=submission.graded_at,
                returned_at=submission.returned_at,
                is_late=submission.is_late,
                needs_review=submission.needs_review,
                created_at=submission.created_at,
                updated_at=submission.updated_at,
                grade_percentage=submission.grade_percentage,
                student_name=submission.student.name,
                student_email=submission.student.email
            )
            for submission in submissions
        ]
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get submission by ID."""
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.get_submission_by_id(submission_id, current_user.id)
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/submissions/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: UUID,
    update_data: SubmissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update submission. Only the submission creator can update."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can update submissions"
        )
    
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.update_submission(
            submission_id, current_user.id, update_data
        )
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Grading endpoints

@router.post("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: UUID,
    grade_data: SubmissionGrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Grade a submission. Only teachers can grade."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can grade submissions"
        )
    
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.grade_submission(
            submission_id, current_user.id, grade_data
        )
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/submissions/{submission_id}/return", response_model=SubmissionResponse)
async def return_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return a graded submission to student. Only teachers can return."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can return submissions"
        )
    
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.return_submission(submission_id, current_user.id)
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# File upload endpoints for assignments and submissions

@router.post("/{assignment_id}/files", response_model=AssignmentFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_assignment_file(
    assignment_id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None, description="File description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file for an assignment (reference materials, templates, etc.). Only teachers can upload."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload assignment files"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.get_assignment_by_id(assignment_id, current_user.id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assignment creator can upload files"
            )
        
        # Upload file
        file_service = FileService(db)
        uploaded_file = await file_service.upload_file(
            file=file,
            user_id=current_user.id,
            file_category="document"
        )
        
        # Link file to assignment
        uploaded_file.assignment_id = assignment_id
        await db.commit()
        await db.refresh(uploaded_file)
        
        return AssignmentFileResponse(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            original_name=uploaded_file.original_name,
            file_type=uploaded_file.mime_type,
            file_size=uploaded_file.file_size,
            file_url=uploaded_file.file_url,
            uploaded_at=uploaded_file.created_at
        )
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{assignment_id}/files", response_model=List[AssignmentFileResponse])
async def get_assignment_files(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all files for an assignment."""
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.get_assignment_by_id(assignment_id, current_user.id)
        
        return [
            AssignmentFileResponse(
                id=file.id,
                filename=file.filename,
                original_name=file.original_name,
                file_type=file.mime_type,
                file_size=file.file_size,
                file_url=file.file_url,
                uploaded_at=file.created_at
            )
            for file in assignment.assignment_files
        ]
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/submissions/{submission_id}/files", response_model=SubmissionFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_submission_file(
    submission_id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None, description="File description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file for a submission. Only the student who created the submission can upload."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can upload submission files"
        )
    
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.get_submission_by_id(submission_id, current_user.id)
        
        # Check if user is the student who created this submission
        if submission.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the submission creator can upload files"
            )
        
        # Check if submission can still be modified
        if submission.status in [SubmissionStatus.GRADED, SubmissionStatus.RETURNED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload files to a graded submission"
            )
        
        # Upload file
        file_service = FileService(db)
        uploaded_file = await file_service.upload_file(
            file=file,
            user_id=current_user.id,
            file_category="document"
        )
        
        # Link file to submission
        uploaded_file.submission_id = submission_id
        await db.commit()
        await db.refresh(uploaded_file)
        
        # Process OCR if it's an image
        ocr_text = None
        if uploaded_file.file_type.value == "image":
            # TODO: Implement OCR processing
            # ocr_text = await process_image_ocr(uploaded_file.storage_path)
            # uploaded_file.ocr_text = ocr_text
            # await db.commit()
            pass
        
        return SubmissionFileResponse(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            original_name=uploaded_file.original_name,
            file_type=uploaded_file.mime_type,
            file_size=uploaded_file.file_size,
            file_url=uploaded_file.file_url,
            ocr_text=uploaded_file.ocr_text,
            uploaded_at=uploaded_file.created_at
        )
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/submissions/{submission_id}/files", response_model=List[SubmissionFileResponse])
async def get_submission_files(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all files for a submission."""
    try:
        assignment_service = AssignmentService(db)
        submission = await assignment_service.get_submission_by_id(submission_id, current_user.id)
        
        return [
            SubmissionFileResponse(
                id=file.id,
                filename=file.filename,
                original_name=file.original_name,
                file_type=file.mime_type,
                file_size=file.file_size,
                file_url=file.file_url,
                ocr_text=file.ocr_text,
                uploaded_at=file.created_at
            )
            for file in submission.files
        ]
    except SubmissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an assignment or submission file."""
    try:
        file_service = FileService(db)
        success = await file_service.delete_file(file_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or insufficient permissions"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Submission with file upload endpoint

@router.post("/{assignment_id}/submissions/with-files", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission_with_files(
    assignment_id: UUID,
    content: Optional[str] = Form(None, description="Submission text content"),
    notes: Optional[str] = Form(None, description="Student notes"),
    files: List[UploadFile] = File(default=[], description="Submission files"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a submission with files. Only students can submit."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can create submissions"
        )
    
    try:
        # Create submission
        assignment_service = AssignmentService(db)
        submission_data = SubmissionCreate(
            assignment_id=assignment_id,
            content=content,
            notes=notes
        )
        
        submission = await assignment_service.create_submission(current_user.id, submission_data)
        
        # Upload files if provided
        file_service = FileService(db)
        uploaded_files = []
        
        for file in files:
            try:
                uploaded_file = await file_service.upload_file(
                    file=file,
                    user_id=current_user.id,
                    file_category="document"
                )
                
                # Link file to submission
                uploaded_file.submission_id = submission.id
                uploaded_files.append(uploaded_file)
                
            except Exception as e:
                # If file upload fails, continue with other files
                # In production, you might want to handle this differently
                continue
        
        await db.commit()
        
        return SubmissionResponse(
            id=submission.id,
            assignment_id=submission.assignment_id,
            student_id=submission.student_id,
            content=submission.content,
            notes=submission.notes,
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            feedback=submission.feedback,
            teacher_comments=submission.teacher_comments,
            ai_feedback=submission.ai_feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
            returned_at=submission.returned_at,
            is_late=submission.is_late,
            needs_review=submission.needs_review,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            grade_percentage=submission.grade_percentage
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
# Notification endpoints

@router.get("/notifications", response_model=List[dict])
async def get_assignment_notifications(
    assignment_id: Optional[UUID] = Query(None, description="Filter by assignment ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignment-related notifications for the current user."""
    try:
        from app.services.notification_service import AssignmentNotificationService
        notification_service = AssignmentNotificationService(db)
        
        notifications = await notification_service.get_assignment_notifications(
            user_id=current_user.id,
            assignment_id=assignment_id,
            limit=limit
        )
        
        return [
            {
                "id": str(notification.id),
                "type": notification.type,
                "title": notification.title,
                "content": notification.content,
                "data": notification.data,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "read_at": notification.read_at.isoformat() if notification.read_at else None
            }
            for notification in notifications
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/notifications/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    notification_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notifications as read."""
    try:
        from app.services.notification_service import AssignmentNotificationService
        notification_service = AssignmentNotificationService(db)
        
        await notification_service.mark_notifications_read(
            user_id=current_user.id,
            notification_ids=notification_ids
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/notifications/unread-count", response_model=dict)
async def get_unread_notifications_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread assignment notifications."""
    try:
        from app.services.notification_service import AssignmentNotificationService
        notification_service = AssignmentNotificationService(db)
        
        count = await notification_service.get_unread_count(
            user_id=current_user.id,
            assignment_related_only=True
        )
        
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Assignment reporting endpoints

@router.get("/{assignment_id}/report", response_model=dict)
async def get_assignment_report(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed assignment report. Only teachers can access."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access assignment reports"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignment = await assignment_service.get_assignment_by_id(assignment_id, current_user.id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assignment creator can access reports"
            )
        
        # Get assignment statistics
        stats = await assignment_service.get_assignment_stats(assignment_id, current_user.id)
        
        # Get all submissions with student details
        submissions = assignment.submissions
        
        # Calculate additional metrics
        submitted_count = len([s for s in submissions if s.is_submitted])
        graded_count = len([s for s in submissions if s.is_graded])
        late_count = len([s for s in submissions if s.is_late])
        
        # Grade distribution
        grades = [s.score for s in submissions if s.score is not None]
        grade_distribution = {}
        if grades:
            grade_distribution = {
                "min": min(grades),
                "max": max(grades),
                "average": sum(grades) / len(grades),
                "median": sorted(grades)[len(grades) // 2] if grades else 0
            }
        
        # Student performance breakdown
        student_performance = []
        for submission in submissions:
            student_performance.append({
                "student_id": str(submission.student_id),
                "student_name": submission.student.name,
                "status": submission.status,
                "score": submission.score,
                "max_score": submission.max_score,
                "grade_percentage": submission.grade_percentage,
                "is_late": submission.is_late,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "graded_at": submission.graded_at.isoformat() if submission.graded_at else None
            })
        
        return {
            "assignment": {
                "id": str(assignment.id),
                "title": assignment.title,
                "total_points": assignment.total_points,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "status": assignment.status,
                "is_overdue": assignment.is_overdue
            },
            "statistics": {
                "total_submissions": stats.total_submissions,
                "pending_submissions": stats.pending_submissions,
                "graded_submissions": stats.graded_submissions,
                "completion_rate": stats.completion_rate,
                "on_time_submissions": stats.on_time_submissions,
                "late_submissions": stats.late_submissions,
                "average_score": stats.average_score
            },
            "grade_distribution": grade_distribution,
            "student_performance": student_performance,
            "summary": {
                "submitted_count": submitted_count,
                "graded_count": graded_count,
                "late_count": late_count,
                "pending_grading": submitted_count - graded_count
            }
        }
    except AssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/class/{class_id}/report", response_model=dict)
async def get_class_assignment_report(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assignment report for a class. Only teachers can access."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access class reports"
        )
    
    try:
        assignment_service = AssignmentService(db)
        assignments = await assignment_service.get_class_assignments(
            class_id, current_user.id
        )
        
        # Calculate class-level statistics
        total_assignments = len(assignments)
        active_assignments = len([a for a in assignments if a.status == AssignmentStatus.ACTIVE])
        overdue_assignments = len([a for a in assignments if a.is_overdue])
        
        # Assignment breakdown
        assignment_summary = []
        for assignment in assignments:
            stats = await assignment_service.get_assignment_stats(assignment.id, current_user.id)
            assignment_summary.append({
                "id": str(assignment.id),
                "title": assignment.title,
                "status": assignment.status,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "is_overdue": assignment.is_overdue,
                "total_submissions": stats.total_submissions,
                "completion_rate": stats.completion_rate,
                "average_score": stats.average_score
            })
        
        return {
            "class_id": str(class_id),
            "summary": {
                "total_assignments": total_assignments,
                "active_assignments": active_assignments,
                "overdue_assignments": overdue_assignments
            },
            "assignments": assignment_summary
        }
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

<<<<<<< HEAD
=======

>>>>>>> b42dfdc87b0c14ed38790b4ae0a68ff39e132e3d
# System administration endpoints

@router.get("/system/summary", response_model=dict)
async def get_assignment_system_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide assignment summary. Only teachers can access."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access system summary"
        )
    
    try:
        from app.services.assignment_scheduler import AssignmentSchedulerService
        scheduler_service = AssignmentSchedulerService(db)
        
        summary = await scheduler_service.get_assignment_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/system/run-daily-tasks", response_model=dict)
async def run_daily_assignment_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run daily assignment maintenance tasks. Only teachers can trigger."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can run system tasks"
        )
    
    try:
        from app.services.assignment_scheduler import AssignmentSchedulerService
        scheduler_service = AssignmentSchedulerService(db)
        
        results = await scheduler_service.run_daily_tasks()
        return results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))