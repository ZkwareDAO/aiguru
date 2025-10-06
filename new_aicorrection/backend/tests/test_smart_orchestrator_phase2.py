"""Tests for SmartOrchestrator Phase 2"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


def test_orchestrator_import():
    """测试SmartOrchestrator导入"""
    # 设置临时环境变量
    os.environ["OPENROUTER_API_KEY"] = "test_key"

    # Mock FileService
    with patch('app.agents.preprocess_agent.FileService') as mock_file_service:
        mock_file_service.return_value = Mock()

        from app.agents.smart_orchestrator import SmartOrchestrator

        orchestrator = SmartOrchestrator()
        assert orchestrator is not None
        assert orchestrator.segmentation_agent is not None
        assert orchestrator.location_agent is not None
        print("✅ SmartOrchestrator导入测试通过")


def test_workflow_structure():
    """测试工作流结构"""
    os.environ["OPENROUTER_API_KEY"] = "test_key"

    with patch('app.agents.preprocess_agent.FileService') as mock_file_service:
        mock_file_service.return_value = Mock()

        from app.agents.smart_orchestrator import SmartOrchestrator

        orchestrator = SmartOrchestrator()
        workflow = orchestrator.workflow

        assert workflow is not None
        print("✅ 工作流结构测试通过")


def test_extract_image_urls():
    """测试提取图片URL"""
    os.environ["OPENROUTER_API_KEY"] = "test_key"

    with patch('app.agents.preprocess_agent.FileService') as mock_file_service:
        mock_file_service.return_value = Mock()

        from app.agents.smart_orchestrator import SmartOrchestrator
        from app.agents.state import GradingState

        orchestrator = SmartOrchestrator()
    
        state = GradingState(
            submission_id="test-123",
            assignment_id="assignment-456",
            status="pending",
            grading_mode="fast",
            config={},
            max_score=100.0,
            preprocessed_files=[
                {"type": "image", "file_path": "https://example.com/image1.jpg"},
                {"type": "image", "file_path": "https://example.com/image2.jpg"},
                {"type": "text", "file_path": "https://example.com/text.txt"},
            ],
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

        images = orchestrator._extract_image_urls(state)

        assert len(images) == 2
        assert images[0] == "https://example.com/image1.jpg"
        assert images[1] == "https://example.com/image2.jpg"
        print("✅ 提取图片URL测试通过")


def test_create_question_state():
    """测试创建题目状态"""
    os.environ["OPENROUTER_API_KEY"] = "test_key"

    with patch('app.agents.preprocess_agent.FileService') as mock_file_service:
        mock_file_service.return_value = Mock()

        from app.agents.smart_orchestrator import SmartOrchestrator
        from app.agents.state import GradingState, QuestionSegment, BoundingBox

        orchestrator = SmartOrchestrator()
    
    state = GradingState(
        submission_id="test-123",
        assignment_id="assignment-456",
        status="pending",
        grading_mode="fast",
        config={},
        max_score=100.0,
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
    
    segment = QuestionSegment(
        question_number="1. 题目1",
        question_index=0,
        page_index=0,
        bbox=BoundingBox(x=50, y=100, width=700, height=300),
        cropped_image_url="https://example.com/q1.jpg",
        ocr_text="这是题目1的文字",
        confidence=0.95
    )
    
    question_state = orchestrator._create_question_state(state, segment)
    
    assert question_state["submission_id"] == "test-123"
    assert question_state["extracted_text"] == "这是题目1的文字"
    assert question_state["max_score"] == 10.0
    print("✅ 创建题目状态测试通过")


def test_determine_status():
    """测试判断题目状态"""
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    
    from app.agents.smart_orchestrator import SmartOrchestrator
    from app.agents.state import GradingState
    
    orchestrator = SmartOrchestrator()
    
    # 测试正确状态
    state_correct = GradingState(
        submission_id="test",
        assignment_id="test",
        status="completed",
        grading_mode="fast",
        config={},
        max_score=10.0,
        preprocessed_files=[],
        extracted_text="",
        file_metadata={},
        score=9.5,
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
    
    assert orchestrator._determine_status(state_correct) == "correct"
    
    # 测试警告状态
    state_warning = state_correct.copy()
    state_warning["score"] = 6.0
    assert orchestrator._determine_status(state_warning) == "warning"
    
    # 测试错误状态
    state_error = state_correct.copy()
    state_error["score"] = 3.0
    assert orchestrator._determine_status(state_error) == "error"
    
    print("✅ 判断题目状态测试通过")


def test_format_output_phase2():
    """测试Phase 2输出格式"""
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    
    from app.agents.smart_orchestrator import SmartOrchestrator
    from app.agents.state import GradingState, QuestionSegment, QuestionGrading, BoundingBox
    
    orchestrator = SmartOrchestrator()
    
    state = GradingState(
        submission_id="test-123",
        assignment_id="assignment-456",
        status="completed",
        grading_mode="fast",
        config={"complexity": "medium"},
        max_score=100.0,
        preprocessed_files=[],
        extracted_text="",
        file_metadata={},
        score=85.0,
        errors=[],
        annotations=[],
        confidence=0.95,
        feedback_text="",
        suggestions=[],
        knowledge_points=[],
        processing_start_time=datetime.utcnow(),
        processing_end_time=datetime.utcnow(),
        processing_time_ms=5000,
        from_cache=False,
        error_message=None,
        messages=[],
        # Phase 2 字段
        images=["https://example.com/image1.jpg"],
        question_segments=[
            QuestionSegment(
                question_number="1. 题目1",
                question_index=0,
                page_index=0,
                bbox=BoundingBox(x=50, y=100, width=700, height=300),
                cropped_image_url="https://example.com/q1.jpg",
                ocr_text="题目1",
                confidence=0.95
            )
        ],
        grading_results=[
            QuestionGrading(
                question_index=0,
                question_number="1. 题目1",
                page_index=0,
                bbox=BoundingBox(x=50, y=100, width=700, height=300),
                score=8.5,
                max_score=10.0,
                status="correct",
                errors=[],
                correct_parts=[],
                warnings=[],
                feedback="做得很好"
            )
        ],
        annotated_results=[],
    )
    
    output = orchestrator._format_output(state)
    
    assert output["submission_id"] == "test-123"
    assert output["status"] == "completed"
    assert output["score"] == 85.0
    assert "question_segments" in output
    assert "grading_results" in output
    assert "annotated_results" in output
    assert len(output["question_segments"]) == 1
    assert len(output["grading_results"]) == 1
    
    print("✅ Phase 2输出格式测试通过")


# 运行所有测试
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 SmartOrchestrator Phase 2 测试")
    print("="*60 + "\n")
    
    test_orchestrator_import()
    test_workflow_structure()
    test_extract_image_urls()
    test_create_question_state()
    test_determine_status()
    test_format_output_phase2()
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)

