"""State definition for LangGraph grading workflow."""

from typing import TypedDict, List, Dict, Optional, Annotated
from uuid import UUID
from datetime import datetime
from operator import add


class BoundingBox(TypedDict):
    """边界框"""
    x: int
    y: int
    width: int
    height: int


class QuestionSegment(TypedDict):
    """题目分段"""
    question_number: str  # "第1题" 或 "1." 或 "(1)"
    question_index: int  # 0-based索引
    page_index: int  # 所在页面索引
    bbox: BoundingBox  # 题目边界框
    cropped_image_url: Optional[str]  # 题目截图URL
    ocr_text: Optional[str]  # OCR识别的文字
    confidence: float  # 识别置信度 (0-1)


class ErrorLocation(TypedDict):
    """错误位置"""
    bbox: BoundingBox  # 精确的像素坐标
    type: str  # "point" | "line" | "area"
    confidence: float  # 0-1
    reasoning: str  # 定位依据


class QuestionGrading(TypedDict):
    """题目批改结果"""
    question_index: int
    question_number: str
    page_index: int
    bbox: BoundingBox
    score: float
    max_score: float
    status: str  # "correct" | "warning" | "error"
    errors: List[Dict]  # 包含位置信息的错误列表
    correct_parts: List[Dict]
    warnings: List[Dict]
    feedback: str


class GradingState(TypedDict):
    """批改流程状态

    这个状态会在整个LangGraph工作流中传递和更新
    """
    # 基础信息
    submission_id: UUID
    assignment_id: UUID
    status: str  # pending/preprocessing/grading/annotating/completed/failed

    # 配置
    grading_mode: str  # fast/standard/premium
    config: Dict

    # 预处理结果
    preprocessed_files: List[Dict]
    extracted_text: str
    file_metadata: Dict

    # Phase 2: 题目分段结果 (Agent 1 输出)
    images: Optional[List[str]]  # 图片URL列表
    question_segments: Optional[List[QuestionSegment]]  # 题目分段列表

    # Phase 2: 批改结果 (Agent 2 输出)
    grading_results: Optional[List[QuestionGrading]]  # 题目批改列表

    # Phase 2: 标注结果 (Agent 3 输出)
    annotated_results: Optional[List[QuestionGrading]]  # 带位置标注的批改结果

    # 批改结果 (兼容Phase 1)
    score: Optional[float]
    max_score: float
    errors: List[Dict]
    annotations: List[Dict]
    confidence: float

    # 反馈结果
    feedback_text: str
    suggestions: List[str]
    knowledge_points: List[Dict]

    # 元数据
    processing_start_time: datetime
    processing_end_time: Optional[datetime]
    processing_time_ms: Optional[int]
    from_cache: bool
    error_message: Optional[str]

    # 消息历史 (用于LangGraph,使用add操作符合并)
    messages: Annotated[List[Dict], add]


class ErrorDetail(TypedDict):
    """错误详情"""
    type: str  # 错误类型
    location: str  # 错误位置
    description: str  # 错误说明
    correct_answer: str  # 正确答案
    severity: str  # high/medium/low
    deduction: float  # 扣分


class KnowledgePoint(TypedDict):
    """知识点"""
    name: str  # 知识点名称
    mastery_level: int  # 掌握程度 0-100
    suggestion: str  # 学习建议


class Annotation(TypedDict):
    """标注信息"""
    x: int
    y: int
    width: int
    height: int
    label: str
    error_type: str

