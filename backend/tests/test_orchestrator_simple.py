"""Simple tests for SmartOrchestrator Phase 2"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import Mock, patch

# 设置环境变量
os.environ["OPENROUTER_API_KEY"] = "test_key"

# Mock FileService before importing
with patch('app.services.file_service.FileService'):
    from app.agents.smart_orchestrator import SmartOrchestrator
    from app.agents.state import GradingState, QuestionSegment, BoundingBox, QuestionGrading
    from datetime import datetime


def create_mock_orchestrator():
    """创建Mock的Orchestrator"""
    with patch('app.services.file_service.FileService'):
        return SmartOrchestrator()


def test_import():
    """测试导入"""
    orchestrator = create_mock_orchestrator()
    assert orchestrator is not None
    print("✅ 导入测试通过")


def test_agents_initialized():
    """测试Agents初始化"""
    orchestrator = create_mock_orchestrator()
    assert orchestrator.segmentation_agent is not None
    assert orchestrator.location_agent is not None
    assert orchestrator.unified_agent is not None
    print("✅ Agents初始化测试通过")


def test_extract_image_urls():
    """测试提取图片URL"""
    orchestrator = create_mock_orchestrator()
    
    state = {
        "preprocessed_files": [
            {"type": "image", "file_path": "https://example.com/img1.jpg"},
            {"type": "image", "file_path": "https://example.com/img2.jpg"},
            {"type": "text", "file_path": "https://example.com/text.txt"},
        ]
    }
    
    images = orchestrator._extract_image_urls(state)
    
    assert len(images) == 2
    assert images[0] == "https://example.com/img1.jpg"
    print("✅ 提取图片URL测试通过")


def test_determine_status():
    """测试判断状态"""
    orchestrator = create_mock_orchestrator()
    
    # 正确状态
    state_correct = {"score": 9.5, "max_score": 10.0}
    assert orchestrator._determine_status(state_correct) == "correct"
    
    # 警告状态
    state_warning = {"score": 6.0, "max_score": 10.0}
    assert orchestrator._determine_status(state_warning) == "warning"
    
    # 错误状态
    state_error = {"score": 3.0, "max_score": 10.0}
    assert orchestrator._determine_status(state_error) == "error"
    
    print("✅ 判断状态测试通过")


def test_create_question_state():
    """测试创建题目状态"""
    orchestrator = create_mock_orchestrator()
    
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
    print("✅ 创建题目状态测试通过")


def test_format_output():
    """测试输出格式"""
    orchestrator = create_mock_orchestrator()
    
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
        images=["https://example.com/img1.jpg"],
        question_segments=[],
        grading_results=[],
        annotated_results=[],
    )
    
    output = orchestrator._format_output(state)
    
    assert output["submission_id"] == "test-123"
    assert output["status"] == "completed"
    assert output["score"] == 85.0
    assert "question_segments" in output
    assert "grading_results" in output
    assert "annotated_results" in output
    print("✅ 输出格式测试通过")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 SmartOrchestrator Phase 2 简化测试")
    print("="*60 + "\n")
    
    test_import()
    test_agents_initialized()
    test_extract_image_urls()
    test_determine_status()
    test_create_question_state()
    test_format_output()
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)

