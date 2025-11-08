"""LangGraph state definitions for AI grading workflow."""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class GraphState(TypedDict):
    """
    State definition for LangGraph grading workflow.
    
    This state is passed between all nodes in the graph and contains
    all necessary information for the grading process.
    """
    
    # Task identification
    task_id: str
    submission_id: Optional[str]
    assignment_id: Optional[str]
    user_id: Optional[str]
    
    # Input files
    question_files: List[str]  # Paths to question/problem files
    answer_files: List[str]    # Paths to student answer files
    marking_scheme_files: List[str]  # Paths to marking scheme/rubric files
    
    # Processing parameters
    task_type: str  # 'auto', 'with_scheme', 'without_scheme', etc.
    strictness_level: str  # '宽松', '中等', '严格'
    language: str  # 'zh', 'en'
    subject: Optional[str]
    difficulty: Optional[str]
    
    # OCR and document processing results
    ocr_output: Optional[Dict[str, Any]]  # OCR results with text and coordinates
    document_structure: Optional[Dict[str, Any]]  # Detected structure (questions, regions)
    preprocessed_images: Optional[List[str]]  # Paths to preprocessed images
    
    # Rubric and grading criteria
    rubric: Optional[Dict[str, Any]]  # Structured rubric/marking scheme
    rubric_text: Optional[str]  # Raw rubric text
    grading_criteria: Optional[List[str]]  # List of criteria
    max_score: int  # Maximum possible score
    
    # Scoring results
    scores: Optional[Dict[str, Any]]  # Per-question scores and feedback
    total_score: Optional[int]  # Total score
    percentage: Optional[float]  # Score percentage
    grade_level: Optional[str]  # A, B, C, etc.
    
    # Annotations and visualizations
    annotations: Optional[List[Dict[str, Any]]]  # Coordinate-based annotations
    cropped_regions: Optional[List[Dict[str, Any]]]  # Cropped image regions
    annotation_urls: Optional[List[str]]  # URLs to annotation images
    
    # Knowledge and analytics
    knowledge_points: Optional[List[Dict[str, Any]]]  # Identified knowledge points
    weak_areas: Optional[List[Dict[str, Any]]]  # Areas needing improvement
    strengths: Optional[List[str]]  # Student strengths
    suggestions: Optional[List[str]]  # Improvement suggestions
    learning_insights: Optional[Dict[str, Any]]  # Detailed learning analysis
    
    # Final results
    result: Optional[Dict[str, Any]]  # Complete grading result
    result_uri: Optional[str]  # URI to stored result (S3/MinIO)
    result_text: Optional[str]  # Formatted result text
    pdf_uri: Optional[str]  # URI to generated PDF report
    
    # Metadata and tracking
    status: str  # 'pending', 'processing', 'completed', 'failed'
    current_phase: str  # Current processing phase
    progress: int  # Progress percentage (0-100)
    error_message: Optional[str]  # Error message if failed
    retry_count: int  # Number of retries
    
    # Timestamps
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Events and notifications
    events: List[Dict[str, Any]]  # List of processing events
    notifications_sent: List[str]  # List of sent notifications
    
    # Checkpoints for recovery
    checkpoint_data: Optional[Dict[str, Any]]  # Data for checkpoint recovery
    last_successful_node: Optional[str]  # Last successfully completed node


class NodeInput(TypedDict):
    """Input schema for individual nodes."""
    state: GraphState
    config: Optional[Dict[str, Any]]


class NodeOutput(TypedDict):
    """Output schema for individual nodes."""
    state: GraphState
    events: Optional[List[Dict[str, Any]]]
    error: Optional[str]


class GradingEvent(TypedDict):
    """Event emitted during grading process."""
    event_type: str  # 'node_start', 'node_complete', 'progress_update', 'error'
    node_name: str
    task_id: str
    timestamp: datetime
    data: Optional[Dict[str, Any]]
    message: Optional[str]


def create_initial_state(
    task_id: str,
    question_files: List[str],
    answer_files: List[str],
    marking_scheme_files: List[str] = None,
    task_type: str = "auto",
    strictness_level: str = "中等",
    language: str = "zh",
    submission_id: Optional[str] = None,
    assignment_id: Optional[str] = None,
    user_id: Optional[str] = None,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    max_score: int = 100
) -> GraphState:
    """
    Create initial state for LangGraph workflow.
    
    Args:
        task_id: Unique task identifier
        question_files: List of question file paths
        answer_files: List of answer file paths
        marking_scheme_files: List of marking scheme file paths
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
        Initial GraphState
    """
    return GraphState(
        # Task identification
        task_id=task_id,
        submission_id=submission_id,
        assignment_id=assignment_id,
        user_id=user_id,
        
        # Input files
        question_files=question_files or [],
        answer_files=answer_files or [],
        marking_scheme_files=marking_scheme_files or [],
        
        # Processing parameters
        task_type=task_type,
        strictness_level=strictness_level,
        language=language,
        subject=subject,
        difficulty=difficulty,
        
        # OCR and document processing results
        ocr_output=None,
        document_structure=None,
        preprocessed_images=None,
        
        # Rubric and grading criteria
        rubric=None,
        rubric_text=None,
        grading_criteria=None,
        max_score=max_score,
        
        # Scoring results
        scores=None,
        total_score=None,
        percentage=None,
        grade_level=None,
        
        # Annotations and visualizations
        annotations=None,
        cropped_regions=None,
        annotation_urls=None,
        
        # Knowledge and analytics
        knowledge_points=None,
        weak_areas=None,
        strengths=None,
        suggestions=None,
        learning_insights=None,
        
        # Final results
        result=None,
        result_uri=None,
        result_text=None,
        pdf_uri=None,
        
        # Metadata and tracking
        status="pending",
        current_phase="initialized",
        progress=0,
        error_message=None,
        retry_count=0,
        
        # Timestamps
        created_at=datetime.now(),
        started_at=None,
        completed_at=None,
        
        # Events and notifications
        events=[],
        notifications_sent=[],
        
        # Checkpoints
        checkpoint_data=None,
        last_successful_node=None
    )


def update_state_progress(
    state: GraphState,
    phase: str,
    progress: int,
    message: Optional[str] = None
) -> GraphState:
    """
    Update state with progress information.
    
    Args:
        state: Current state
        phase: Current processing phase
        progress: Progress percentage (0-100)
        message: Optional progress message
        
    Returns:
        Updated state
    """
    state["current_phase"] = phase
    state["progress"] = min(100, max(0, progress))
    
    if message:
        event = GradingEvent(
            event_type="progress_update",
            node_name=phase,
            task_id=state["task_id"],
            timestamp=datetime.now(),
            data={"progress": progress},
            message=message
        )
        state["events"].append(event)
    
    return state


def mark_node_complete(
    state: GraphState,
    node_name: str,
    output_data: Optional[Dict[str, Any]] = None
) -> GraphState:
    """
    Mark a node as successfully completed.
    
    Args:
        state: Current state
        node_name: Name of completed node
        output_data: Optional output data from node
        
    Returns:
        Updated state
    """
    state["last_successful_node"] = node_name
    
    event = GradingEvent(
        event_type="node_complete",
        node_name=node_name,
        task_id=state["task_id"],
        timestamp=datetime.now(),
        data=output_data,
        message=f"Node {node_name} completed successfully"
    )
    state["events"].append(event)
    
    return state


def mark_node_error(
    state: GraphState,
    node_name: str,
    error_message: str
) -> GraphState:
    """
    Mark a node as failed with error.
    
    Args:
        state: Current state
        node_name: Name of failed node
        error_message: Error message
        
    Returns:
        Updated state
    """
    state["status"] = "failed"
    state["error_message"] = error_message
    
    event = GradingEvent(
        event_type="error",
        node_name=node_name,
        task_id=state["task_id"],
        timestamp=datetime.now(),
        data=None,
        message=error_message
    )
    state["events"].append(event)
    
    return state

