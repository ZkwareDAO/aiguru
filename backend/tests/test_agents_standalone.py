"""Standalone tests for Phase 2 Agents - 不依赖整个应用"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, AsyncMock


# 测试LocationAnnotationAgent
def test_location_agent_import():
    """测试LocationAnnotationAgent导入"""
    # 设置临时环境变量
    os.environ["OPENROUTER_API_KEY"] = "test_key"

    from app.agents.location_annotation_agent import LocationAnnotationAgent
    agent = LocationAnnotationAgent()
    assert agent is not None


def test_location_agent_build_prompt():
    """测试Prompt构建"""
    from app.agents.location_annotation_agent import LocationAnnotationAgent
    from app.agents.state import BoundingBox
    
    agent = LocationAnnotationAgent()
    
    question_bbox = BoundingBox(x=50, y=100, width=700, height=300)
    error = {
        "type": "计算错误",
        "description": "第二步计算错误",
        "related_text": "x=2"
    }
    
    prompt = agent._build_prompt(800, 1200, question_bbox, error)
    
    assert "800px" in prompt
    assert "1200px" in prompt
    assert "计算错误" in prompt
    assert "x=2" in prompt
    print("✅ Prompt构建测试通过")


def test_location_agent_parse_response():
    """测试响应解析"""
    from app.agents.location_annotation_agent import LocationAnnotationAgent
    
    agent = LocationAnnotationAgent()
    
    content = '''
    {
      "bbox": {"x": 150, "y": 200, "width": 200, "height": 50},
      "type": "area",
      "confidence": 0.95,
      "reasoning": "错误位于第二行"
    }
    '''
    
    result = agent._parse_response(content)
    
    assert result["bbox"]["x"] == 150
    assert result["bbox"]["y"] == 200
    assert result["type"] == "area"
    assert result["confidence"] == 0.95
    print("✅ 响应解析测试通过")


def test_location_agent_validate_result():
    """测试结果验证"""
    from app.agents.location_annotation_agent import LocationAnnotationAgent
    from app.agents.state import BoundingBox, ErrorLocation
    
    agent = LocationAnnotationAgent()
    
    question_bbox = BoundingBox(x=50, y=100, width=700, height=300)
    result = ErrorLocation(
        bbox=BoundingBox(x=150, y=200, width=200, height=50),
        type="area",
        confidence=0.95,
        reasoning="测试"
    )
    
    validated = agent._validate_result(result, 800, 1200, question_bbox)
    
    assert validated["confidence"] > 0
    assert validated["confidence"] <= 1.0
    print("✅ 结果验证测试通过")


def test_location_agent_fallback():
    """测试兜底位置"""
    from app.agents.location_annotation_agent import LocationAnnotationAgent
    from app.agents.state import BoundingBox
    
    agent = LocationAnnotationAgent()
    
    question_bbox = BoundingBox(x=50, y=100, width=700, height=300)
    fallback = agent._get_fallback_location(question_bbox)
    
    assert fallback["confidence"] == 0.3
    assert fallback["type"] == "area"
    assert "中心位置" in fallback["reasoning"]
    print("✅ 兜底位置测试通过")


# 测试QuestionSegmentationAgent
def test_segmentation_agent_import():
    """测试QuestionSegmentationAgent导入"""
    from app.agents.question_segmentation_agent import QuestionSegmentationAgent
    agent = QuestionSegmentationAgent(use_paddle_ocr=False)
    assert agent is not None


def test_segmentation_agent_detect_markers():
    """测试题号识别"""
    from app.agents.question_segmentation_agent import QuestionSegmentationAgent
    
    agent = QuestionSegmentationAgent(use_paddle_ocr=False)
    
    ocr_result = {
        "text": ["1. 题目1", "答案", "2. 题目2", "答案"],
        "boxes": [
            {"x": 50, "y": 100, "width": 200, "height": 30},
            {"x": 50, "y": 140, "width": 150, "height": 25},
            {"x": 50, "y": 300, "width": 200, "height": 30},
            {"x": 50, "y": 340, "width": 150, "height": 25},
        ],
        "confidences": [0.95, 0.92, 0.94, 0.91]
    }
    
    markers = agent._detect_question_markers(ocr_result)
    
    assert len(markers) == 2
    assert markers[0]["text"] == "1. 题目1"
    assert markers[0]["number"] == 1
    assert markers[1]["text"] == "2. 题目2"
    assert markers[1]["number"] == 2
    print("✅ 题号识别测试通过")


def test_segmentation_agent_calculate_bbox():
    """测试边界框计算"""
    from app.agents.question_segmentation_agent import QuestionSegmentationAgent
    
    agent = QuestionSegmentationAgent(use_paddle_ocr=False)
    
    marker = {
        "text": "1. 题目",
        "number": 1,
        "box": {"x": 50, "y": 100, "width": 200, "height": 30},
        "confidence": 0.95
    }
    
    next_marker = {
        "text": "2. 题目",
        "number": 2,
        "box": {"x": 50, "y": 300, "width": 200, "height": 30},
        "confidence": 0.94
    }
    
    bbox = agent._calculate_bbox(marker, next_marker, 800, 1200)
    
    assert bbox["x"] == 0
    assert bbox["y"] >= 90
    assert bbox["width"] == 800
    assert bbox["height"] > 0
    print("✅ 边界框计算测试通过")


def test_segmentation_agent_fallback():
    """测试兜底分段"""
    from app.agents.question_segmentation_agent import QuestionSegmentationAgent
    
    agent = QuestionSegmentationAgent(use_paddle_ocr=False)
    
    segment = agent._create_fallback_segment(
        page_index=0,
        question_index=0,
        image_url="https://example.com/image.jpg",
        image_width=800,
        image_height=1200
    )
    
    assert segment["question_number"] == "第1题"
    assert segment["question_index"] == 0
    assert segment["confidence"] == 0.5
    print("✅ 兜底分段测试通过")


# 运行所有测试
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Phase 2 Agent 独立测试")
    print("="*60 + "\n")
    
    print("📍 LocationAnnotationAgent 测试:")
    print("-" * 60)
    test_location_agent_import()
    test_location_agent_build_prompt()
    test_location_agent_parse_response()
    test_location_agent_validate_result()
    test_location_agent_fallback()
    
    print("\n📝 QuestionSegmentationAgent 测试:")
    print("-" * 60)
    test_segmentation_agent_import()
    test_segmentation_agent_detect_markers()
    test_segmentation_agent_calculate_bbox()
    test_segmentation_agent_fallback()
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)

